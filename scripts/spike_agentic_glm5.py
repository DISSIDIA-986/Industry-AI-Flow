#!/usr/bin/env python
"""W6 spike gate rerun: agentic_loop against the frozen 10-case benchmark.

Same 10 CRISP-DM cases as the V1 single-shot spike (`spike_glm5_YYYYMMDD.jsonl`)
but this time invoking the bounded 2-pass `run_agentic_analysis` built in W2.
Decision rule upgraded to reflect the repair loop:

    >= 9/10    PROCEED   — flip USE_GLM5_AGENT=true for the demo
    7-8/10     HOLD      — keep deterministic default, iterate prompt
    <  7/10    REGRESSION vs V1; agentic loop not ready

Runtime: ~4-6 min wall clock. Cost: ~$0.05 on Zhipu pricing (2x V1 worst case).

Run:
    .venv/bin/python scripts/spike_agentic_glm5.py [--limit N]

Output:
    test_resources/benchmarks/agentic_glm5_YYYYMMDD.jsonl
    test_resources/benchmarks/agentic_glm5_YYYYMMDD_summary.txt
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

from backend.services.data_analysis.agentic_loop import run_agentic_analysis  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("agentic-spike")

DATA_DIR = PROJECT_ROOT / "test_resources" / "datasets" / "e2e_public"
BENCH_DIR = PROJECT_ROOT / "test_resources" / "benchmarks"

INTER_CASE_SLEEP_S = 3
TOTAL_BUDGET_S = 45.0  # matches agentic_loop's default, hard wall per case

# Frozen cases — identical to scripts/spike_data_analysis_glm5.py so the
# agentic-vs-V1 delta is apples-to-apples.
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


async def run_case(
    dataset: str, q_id: str, task_family: str, question: str
) -> Dict[str, Any]:
    """Run one case through the bounded 2-pass agentic loop."""
    case_id = f"{dataset.replace('.csv', '')}-{q_id}"
    csv_path = DATA_DIR / dataset
    t0 = time.monotonic()

    rec: Dict[str, Any] = {
        "case_id": case_id,
        "dataset": dataset,
        "q_id": q_id,
        "task_family": task_family,
        "question": question,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": None,
        "fail_mode": None,
        "rounds": 0,
        "repair_triggered": False,
        "repair_trigger_type": None,
        "repair_recovered": None,
        "time_budget_exhausted": False,
        "validator_pass": False,
        "sandbox_success": False,
        "chart_exists": False,
        "summary_emitted": False,
        "summary_parsed": None,
        "error_message": None,
        "total_elapsed_s": 0.0,
        "latency_ms": 0,
    }

    try:
        result = await run_agentic_analysis(
            question=question,
            data_file_path=str(csv_path),
            total_budget_s=TOTAL_BUDGET_S,
        )
    except Exception as exc:  # noqa: BLE001
        rec.update(
            status="error",
            fail_mode=f"agentic_loop_exception: {type(exc).__name__}: {exc!s}",
            latency_ms=int((time.monotonic() - t0) * 1000),
        )
        return rec

    rec["rounds"] = len(result.rounds)
    rec["repair_triggered"] = result.repair_triggered
    rec["repair_trigger_type"] = result.repair_trigger_type
    rec["repair_recovered"] = result.repair_recovered
    rec["time_budget_exhausted"] = result.time_budget_exhausted
    rec["total_elapsed_s"] = round(result.total_elapsed_s, 2)
    rec["error_message"] = result.error_message

    if result.rounds:
        terminal = result.rounds[-1]
        rec["validator_pass"] = terminal.validator_pass
        rec["sandbox_success"] = terminal.sandbox_success
        rec["chart_exists"] = terminal.chart_exists
        rec["summary_emitted"] = terminal.summary_emitted
        rec["summary_parsed"] = terminal.summary_parsed

    # Pass/fail semantics: status="ok" AND sandbox executed AND (chart OR summary).
    # Match the V1 spike: "ok" means end-to-end green; "unanswerable" counts as
    # terminal success (same as V1). Everything else is fail/error.
    if result.status == "ok" and result.success:
        rec["status"] = "ok"
    elif result.status == "unanswerable":
        rec["status"] = "unanswerable"
        rec["fail_mode"] = "model_declared_unanswerable"
    else:
        rec["status"] = "fail"
        rec["fail_mode"] = (
            result.error_message
            or (result.rounds[-1].sandbox_exception_type if result.rounds else None)
            or "unknown"
        )
        if result.time_budget_exhausted:
            rec["fail_mode"] = f"time_budget_exhausted: {rec['fail_mode']}"

    rec["latency_ms"] = int((time.monotonic() - t0) * 1000)
    return rec


async def run_gate(output_jsonl: Path, summary_path: Path, limit: int | None) -> None:
    # Resume support — skip cases already recorded.
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
            case_id = f"{dataset.replace('.csv', '')}-{q_id}"
            if case_id in completed:
                logger.info("[%d/%d] SKIP %s (already recorded)", i, len(cases), case_id)
                continue
            logger.info("[%d/%d] RUN  %s (%s)", i, len(cases), case_id, task_family)
            rec = await run_case(dataset, q_id, task_family, question)
            fp.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            fp.flush()
            logger.info(
                "  → status=%s rounds=%d repair=%s recovered=%s elapsed=%.1fs fail=%s",
                rec["status"],
                rec["rounds"],
                rec["repair_triggered"],
                rec["repair_recovered"],
                rec["total_elapsed_s"],
                rec["fail_mode"],
            )
            if i < len(cases):
                time.sleep(INTER_CASE_SLEEP_S)

    write_summary(output_jsonl, summary_path)


def write_summary(jsonl_path: Path, summary_path: Path) -> None:
    records: List[Dict[str, Any]] = []
    with jsonl_path.open() as fp:
        for line in fp:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    total = len(records)
    overall_pass = sum(1 for r in records if r.get("status") == "ok")

    # Repair telemetry — the whole point of W2 is the repair loop value-add.
    repair_triggered = sum(1 for r in records if r.get("repair_triggered"))
    repair_recovered = sum(
        1 for r in records if r.get("repair_triggered") and r.get("repair_recovered")
    )

    by_family: Dict[str, List[bool]] = defaultdict(list)
    fail_modes: Dict[str, int] = defaultdict(int)
    for r in records:
        by_family[r["task_family"]].append(r.get("status") == "ok")
        if r.get("fail_mode"):
            fail_modes[r["fail_mode"].split(":")[0]] += 1

    lines = [
        f"Agentic spike gate summary  (generated {datetime.now(timezone.utc).isoformat()})",
        f"Source: {jsonl_path}",
        "",
        (
            f"Overall pass: {overall_pass}/{total} ({overall_pass / total * 100:.0f}%)"
            if total
            else "No records"
        ),
        f"Repair rounds triggered: {repair_triggered}/{total}",
        f"Repair rounds recovered: {repair_recovered}/{repair_triggered}"
        if repair_triggered
        else "Repair rounds recovered: N/A (no repairs needed)",
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
            lines.append(f"  {mode:32s}: {count}")
    else:
        lines.append("No failures.")

    lines.append("")
    pct = (overall_pass / total * 100) if total else 0
    if pct >= 90 and all(sum(v) > 0 for v in by_family.values()):
        verdict = "PROCEED — flip USE_GLM5_AGENT=true for demo"
    elif pct >= 70:
        verdict = "HOLD — keep deterministic default, iterate prompt / fix infra gaps"
    else:
        verdict = "REGRESSION vs V1 single-shot — investigate repair loop"
    lines.append(f"VERDICT: {verdict}")

    summary = "\n".join(lines) + "\n"
    summary_path.write_text(summary, encoding="utf-8")
    print("\n" + summary)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="W6 agentic spike gate (10 cases, bounded 2-pass)."
    )
    parser.add_argument("--limit", type=int, default=None, help="Cap cases (smoke: --limit 2).")
    parser.add_argument("--output", type=str, default=None, help="Output JSONL path.")
    args = parser.parse_args()

    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    tag = datetime.now(timezone.utc).strftime("%Y%m%d")
    jsonl = Path(args.output) if args.output else BENCH_DIR / f"agentic_glm5_{tag}.jsonl"
    summary = BENCH_DIR / f"agentic_glm5_{tag}_summary.txt"

    asyncio.run(run_gate(jsonl, summary, limit=args.limit))


if __name__ == "__main__":
    main()
