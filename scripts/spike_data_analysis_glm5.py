#!/usr/bin/env python
"""Spike: is GLM-5 capable of dynamic CRISP-DM code generation from CSVs?

Pre-plan go/no-go experiment. Single-shot V1 only. 10 cases
(5 datasets × 2 questions). No V2 repair loop, no blinded review, no SHA
tracking — this is a go/no-go signal, not a benchmark harness.

Run:
    .venv/bin/python scripts/spike_data_analysis_glm5.py [--limit N]

Output:
    test_resources/benchmarks/spike_glm5_YYYYMMDD.jsonl  (one line per case)
    test_resources/benchmarks/spike_glm5_YYYYMMDD_summary.txt  (aggregate)

Decision rule (Stage 2):
    pass_rate >= 70% AND no task_family at 0/2 → proceed to Plan with single-shot
    pass_rate 50-70%  → Plan should evaluate V2 repair loop
    pass_rate <  50%  → P3 is false; defend deterministic production default
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.data_analysis.spike_harness import (  # noqa: E402
    extract_profile,
    extract_summary_json,
    load_dataframe,
    parse_json_response,
    render_prompt,
    run_sandbox,
    validate_code,
)
from backend.services.llm_integration.llm_client import LLMClientFactory  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("spike")

DATA_DIR = PROJECT_ROOT / "test_resources" / "datasets" / "e2e_public"
BENCH_DIR = PROJECT_ROOT / "test_resources" / "benchmarks"
PROMPT_DIR = PROJECT_ROOT / "scripts" / "prompts"

SAMPLING = {"temperature": 0.2, "top_p": 0.95, "max_tokens": 4096}
INTER_CASE_SLEEP_S = 3
SANDBOX_TIMEOUT_S = 60

# 10 cases: 5 datasets × 2 questions, per design doc Appendix A.4
CASES: List[Dict[str, Any]] = [
    ("tips.csv",              "Q1", "descriptive",    "How does mean tip vary with party size?"),
    ("tips.csv",              "Q2", "regression",     "Predict tip from total_bill, size, and time of day."),
    ("mpg.csv",               "Q1", "correlation",    "Which numeric features correlate most strongly with mpg?"),
    ("mpg.csv",               "Q2", "regression",     "Predict mpg from weight, horsepower, and model_year."),
    ("penguins.csv",          "Q1", "descriptive",    "What are the differences in body measurements between the three species?"),
    ("penguins.csv",          "Q2", "classification", "Classify penguin species using bill_length, bill_depth, and flipper_length."),
    ("titanic.csv",           "Q1", "descriptive",    "Which factors are associated with survival? Handle missing Age values."),
    ("titanic.csv",           "Q2", "classification", "Classify survival from Pclass, Sex, Age, and Fare."),
    ("airline-passengers.csv","Q1", "time-series",    "Describe the trend and seasonality in monthly passenger counts."),
    ("airline-passengers.csv","Q2", "forecast",       "Forecast the next 12 months of passenger counts."),
]


def call_glm5(prompt: str) -> str:
    """One GLM-5 call. No retry — if Zhipu is flaky the spike is invalid anyway."""
    client = LLMClientFactory.create_client("zhipu")
    return client.generate(prompt, **SAMPLING)


async def run_case(dataset: str, q_id: str, task_family: str, question: str,
                   system_text: str, user_template: Path) -> Dict[str, Any]:
    """Run one case end-to-end. Returns a flat record."""
    case_id = f"{dataset.replace('.csv','')}-{q_id}"
    t0 = time.monotonic()

    csv_path = DATA_DIR / dataset
    df = load_dataframe(str(csv_path))
    profile = extract_profile(df, filename=dataset, total_rows=len(df))

    user_text, _, _ = render_prompt(str(user_template), {
        **profile, "question": question,
    })
    prompt = f"[SYSTEM]\n{system_text}\n\n[USER]\n{user_text}"

    rec: Dict[str, Any] = {
        "case_id": case_id, "dataset": dataset, "q_id": q_id,
        "task_family": task_family, "question": question,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": None, "fail_mode": None,
        "validator_pass": False, "sandbox_success": False,
        "produces_chart": None, "chart_exists": False,
        "summary_emitted": False, "summary_parsed": None,
        "generated_code": None, "sandbox_stdout": "", "sandbox_stderr": "",
        "latency_ms": 0,
    }

    # 1. GLM-5
    try:
        raw = call_glm5(prompt)
    except Exception as exc:  # noqa: BLE001
        rec.update(status="error", fail_mode=f"llm_error: {exc!s}")
        rec["latency_ms"] = int((time.monotonic() - t0) * 1000)
        return rec

    # 2. Parse
    parsed = parse_json_response(raw)
    if not parsed:
        rec.update(status="error", fail_mode="json_parse_error", llm_raw=raw[:500])
        rec["latency_ms"] = int((time.monotonic() - t0) * 1000)
        return rec

    rec["produces_chart"] = bool(parsed.get("produces_chart"))
    rec["generated_code"] = parsed.get("python_code")

    if parsed.get("status") == "unanswerable":
        rec.update(status="unanswerable", fail_mode=None,
                   reason=parsed.get("reason"), suggestion=parsed.get("suggestion"))
        rec["latency_ms"] = int((time.monotonic() - t0) * 1000)
        return rec

    code = parsed.get("python_code")
    if not code:
        rec.update(status="error", fail_mode="empty_code_on_ok_status")
        rec["latency_ms"] = int((time.monotonic() - t0) * 1000)
        return rec

    # 3. Validate
    outcome = validate_code(code)
    rec["validator_pass"] = outcome.ok
    if not outcome.ok:
        rec.update(status="fail", fail_mode=f"validator: {outcome.reason}")
        rec["latency_ms"] = int((time.monotonic() - t0) * 1000)
        return rec

    # 4. Sandbox
    try:
        exec_result = await run_sandbox(
            code=code, csv_files={dataset: csv_path.read_bytes()},
            timeout_s=SANDBOX_TIMEOUT_S,
        )
        rec["sandbox_success"] = exec_result.success
        rec["sandbox_stdout"] = exec_result.stdout
        rec["sandbox_stderr"] = exec_result.stderr
        if "analysis_chart.png" in (exec_result.output_files or {}):
            rec["chart_exists"] = len(exec_result.output_files["analysis_chart.png"]) > 0
        emitted, parsed_ok, obj = extract_summary_json(exec_result.stdout)
        rec["summary_emitted"] = emitted
        rec["summary_parsed"] = obj if parsed_ok else None
        if not exec_result.success:
            rec.update(status="fail", fail_mode=f"sandbox: {exec_result.error or 'execution failed'}")
        else:
            rec["status"] = "ok"
    except Exception as exc:  # noqa: BLE001
        rec.update(status="error", fail_mode=f"sandbox_exception: {type(exc).__name__}")

    rec["latency_ms"] = int((time.monotonic() - t0) * 1000)
    return rec


async def run_spike(output_jsonl: Path, summary_path: Path, limit: int | None) -> None:
    system_text = (PROMPT_DIR / "spike_v1_system.md").read_text(encoding="utf-8")
    user_template = PROMPT_DIR / "spike_v1_user_template.md"

    # Resume
    completed: set[str] = set()
    if output_jsonl.exists():
        with output_jsonl.open() as fp:
            for line in fp:
                try:
                    completed.add(json.loads(line)["case_id"])
                except (json.JSONDecodeError, KeyError):
                    continue

    cases = CASES[:limit] if limit else CASES
    with output_jsonl.open("a", encoding="utf-8") as fp:
        for i, (dataset, q_id, task_family, question) in enumerate(cases, 1):
            case_id = f"{dataset.replace('.csv','')}-{q_id}"
            if case_id in completed:
                logger.info("[%d/%d] SKIP %s", i, len(cases), case_id)
                continue
            logger.info("[%d/%d] RUN  %s (%s)", i, len(cases), case_id, task_family)
            rec = await run_case(dataset, q_id, task_family, question, system_text, user_template)
            fp.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            fp.flush()
            logger.info("  → status=%s  validator=%s  sandbox=%s  chart=%s  fail=%s",
                        rec["status"], rec["validator_pass"], rec["sandbox_success"],
                        rec["chart_exists"], rec["fail_mode"])
            if i < len(cases):
                time.sleep(INTER_CASE_SLEEP_S)

    write_summary(output_jsonl, summary_path)


def write_summary(jsonl_path: Path, summary_path: Path) -> None:
    """Read the JSONL and emit a terse per-task-family pass/fail summary."""
    records: List[Dict[str, Any]] = []
    with jsonl_path.open() as fp:
        for line in fp:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    total = len(records)
    overall_pass = sum(1 for r in records if r.get("status") == "ok")
    by_family: Dict[str, List[bool]] = defaultdict(list)
    fail_modes: Dict[str, int] = defaultdict(int)
    for r in records:
        by_family[r["task_family"]].append(r.get("status") == "ok")
        if r.get("fail_mode"):
            fail_modes[r["fail_mode"].split(":")[0]] += 1

    lines = [
        f"Spike summary  (generated {datetime.now(timezone.utc).isoformat()})",
        f"Source: {jsonl_path}",
        "",
        f"Overall pass: {overall_pass}/{total} ({overall_pass/total*100:.0f}%)" if total else "No records",
        "",
        "By task_family:",
    ]
    for fam, outcomes in sorted(by_family.items()):
        n_pass = sum(outcomes)
        lines.append(f"  {fam:15s}: {n_pass}/{len(outcomes)}")

    lines.append("")
    if fail_modes:
        lines.append("Fail modes:")
        for mode, count in sorted(fail_modes.items(), key=lambda x: -x[1]):
            lines.append(f"  {mode:25s}: {count}")
    else:
        lines.append("No failures.")

    lines.append("")
    pct = (overall_pass / total * 100) if total else 0
    if pct >= 70 and all(sum(v) > 0 for v in by_family.values()):
        verdict = "PROCEED (single-shot) — Plan the refactor"
    elif pct >= 50:
        verdict = "PARTIAL — Plan should evaluate V2 repair loop"
    else:
        verdict = "STOP — P3 is false; defend deterministic default"
    lines.append(f"VERDICT: {verdict}")

    summary = "\n".join(lines) + "\n"
    summary_path.write_text(summary, encoding="utf-8")
    print("\n" + summary)


def main() -> None:
    parser = argparse.ArgumentParser(description="GLM-5 Dynamic Data Analysis spike (10 cases, single-shot).")
    parser.add_argument("--limit", type=int, default=None, help="Cap cases (smoke: --limit 2).")
    parser.add_argument("--output", type=str, default=None, help="Output JSONL path.")
    args = parser.parse_args()

    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    tag = datetime.now(timezone.utc).strftime("%Y%m%d")
    jsonl = Path(args.output) if args.output else BENCH_DIR / f"spike_glm5_{tag}.jsonl"
    summary = BENCH_DIR / f"spike_glm5_{tag}_summary.txt"

    asyncio.run(run_spike(jsonl, summary, limit=args.limit))


if __name__ == "__main__":
    main()
