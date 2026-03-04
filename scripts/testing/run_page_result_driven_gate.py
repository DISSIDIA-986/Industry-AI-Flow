#!/usr/bin/env python3
"""Result-driven page E2E gate with screenshot-first validation loops."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FRONTEND_URL = "http://127.0.0.1:3001"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "temp"


@dataclass(frozen=True)
class ModuleAdapter:
    module: str
    script_path: Path
    report_filename: str | None
    default_threshold: float


MODULE_ADAPTERS: Dict[str, ModuleAdapter] = {
    "data_dashboard": ModuleAdapter(
        module="data_dashboard",
        script_path=PROJECT_ROOT / "scripts" / "testing" / "run_data_dashboard_agent_browser_e2e.py",
        report_filename="data_dashboard_agent_report.json",
        default_threshold=1.0,
    ),
    "cost_estimation": ModuleAdapter(
        module="cost_estimation",
        script_path=PROJECT_ROOT / "scripts" / "testing" / "run_cost_estimation_agent_browser_e2e.py",
        report_filename="cost_estimation_agent_report.json",
        default_threshold=1.0,
    ),
    "rag": ModuleAdapter(
        module="rag",
        script_path=PROJECT_ROOT / "scripts" / "testing" / "run_rag_agent_browser_e2e.py",
        report_filename=None,
        default_threshold=0.7,
    ),
}


def _run_command(command: List[str], *, timeout_seconds: int) -> Tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=max(30, int(timeout_seconds)),
    )
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def _run_shell(command: str, *, timeout_seconds: int) -> Tuple[int, str]:
    proc = subprocess.run(
        [os.environ.get("SHELL", "/bin/zsh"), "-lc", command],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=max(30, int(timeout_seconds)),
    )
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def _parse_kv_output(raw: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line in (raw or "").splitlines():
        text = line.strip()
        if "=" not in text:
            continue
        if text.count("=") > 6 and "http" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip()
        if re.fullmatch(r"[A-Za-z0-9_]+", key):
            values[key] = value
    return values


def _resolve_report_path(
    *,
    module: str,
    adapter: ModuleAdapter,
    kv: Dict[str, str],
    known_rag_output: Path | None,
) -> Path:
    if module == "rag":
        if "report" in kv:
            return Path(kv["report"]).expanduser().resolve()
        if known_rag_output is not None:
            return known_rag_output.resolve()
        raise FileNotFoundError("Unable to resolve rag report path from command output.")

    output_dir = kv.get("output_dir")
    if not output_dir:
        raise FileNotFoundError("Missing output_dir in module command output.")
    root = Path(output_dir).expanduser().resolve()
    if not adapter.report_filename:
        raise FileNotFoundError("Module adapter missing report_filename.")
    return root / adapter.report_filename


def _safe_rate(success: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(float(success) / float(total), 4)


def _evaluate_data_dashboard(report: Dict[str, Any], min_rate: float) -> Dict[str, Any]:
    total = int(report.get("total_cases") or 0)
    success = int(report.get("success_cases") or 0)
    success_rate = float(report.get("success_rate") or _safe_rate(success, total))
    cases = report.get("cases") if isinstance(report.get("cases"), list) else []
    failures = []
    for row in cases:
        if isinstance(row, dict) and not row.get("success"):
            failures.append(
                {
                    "case_id": row.get("case_id"),
                    "error": row.get("error"),
                    "summary": row.get("answer_summary"),
                }
            )
    passed = bool(total > 0 and success == total and success_rate >= min_rate)
    return {
        "total": total,
        "success": success,
        "success_rate": round(success_rate, 4),
        "passed": passed,
        "failures": failures[:8],
        "artifact_output_dir": report.get("output_dir"),
    }


def _evaluate_cost_estimation(report: Dict[str, Any], min_rate: float) -> Dict[str, Any]:
    total = int(report.get("total_cases") or 0)
    success = int(report.get("success_cases") or 0)
    success_rate = float(report.get("success_rate") or _safe_rate(success, total))
    cases = report.get("cases") if isinstance(report.get("cases"), list) else []
    failures = []
    for row in cases:
        if isinstance(row, dict) and not row.get("success"):
            failures.append(
                {
                    "case_id": row.get("case_id"),
                    "error": row.get("error"),
                    "summary": row.get("summary"),
                }
            )

    clear_queue = report.get("clear_queue_validation")
    clear_queue_ok = bool(isinstance(clear_queue, dict) and clear_queue.get("ok"))
    if not clear_queue_ok:
        failures.append({"case_id": "clear_queue_validation", "error": clear_queue, "summary": ""})

    passed = bool(
        total > 0 and success == total and success_rate >= min_rate and clear_queue_ok
    )
    return {
        "total": total,
        "success": success,
        "success_rate": round(success_rate, 4),
        "passed": passed,
        "failures": failures[:8],
        "artifact_output_dir": report.get("output_dir"),
        "clear_queue_validation": clear_queue,
    }


def _evaluate_rag(report: Dict[str, Any], min_rate: float) -> Dict[str, Any]:
    total = int(report.get("total_turns") or 0)
    success = int(report.get("success_turns") or 0)
    success_rate = float(report.get("success_rate") or _safe_rate(success, total))
    turns = report.get("turns") if isinstance(report.get("turns"), list) else []
    failures = []
    for row in turns:
        if not isinstance(row, dict):
            continue
        turn_index = int(row.get("turn_index") or 0)
        if turn_index <= 0:
            continue
        if row.get("success"):
            continue
        failures.append(
            {
                "question_id": row.get("question_id"),
                "conversation_group": row.get("conversation_group"),
                "turn_index": turn_index,
                "error": row.get("error"),
                "question_text": row.get("question_text"),
            }
        )

    passed = bool(total > 0 and success_rate >= min_rate)
    return {
        "total": total,
        "success": success,
        "success_rate": round(success_rate, 4),
        "passed": passed,
        "failures": failures[:12],
        "artifact_report_path": report.get("output_path"),
        "artifact_screenshot_dir": report.get("screenshot_dir"),
    }


def _evaluate_report(module: str, report: Dict[str, Any], min_rate: float) -> Dict[str, Any]:
    if module == "data_dashboard":
        return _evaluate_data_dashboard(report, min_rate)
    if module == "cost_estimation":
        return _evaluate_cost_estimation(report, min_rate)
    if module == "rag":
        return _evaluate_rag(report, min_rate)
    raise ValueError(f"Unsupported module: {module}")


def _build_module_command(
    *,
    module: str,
    adapter: ModuleAdapter,
    frontend_url: str,
    login_email: str,
    login_password: str,
    output_root: Path,
    rag_csv: Path,
    rag_max_questions: int,
    cycle_dir: Path,
) -> Tuple[List[str], Path | None]:
    python_exec = sys.executable or "python3"
    base = [python_exec, str(adapter.script_path)]

    if module in {"data_dashboard", "cost_estimation"}:
        cmd = [
            *base,
            "--frontend-url",
            frontend_url,
            "--login-email",
            login_email,
            "--login-password",
            login_password,
            "--output-root",
            str(output_root),
        ]
        return cmd, None

    rag_report_path = cycle_dir / f"rag_agent_browser_e2e_cycle.json"
    cmd = [
        *base,
        "--frontend-url",
        frontend_url,
        "--csv",
        str(rag_csv),
        "--output",
        str(rag_report_path),
        "--max-questions",
        str(max(1, int(rag_max_questions))),
        "--login-email",
        login_email,
        "--login-password",
        login_password,
    ]
    return cmd, rag_report_path


def _write_summary_markdown(report: Dict[str, Any], summary_path: Path) -> None:
    lines: List[str] = [
        "# Page Result-Driven Gate Summary",
        "",
        f"- Generated at (UTC): {report.get('generated_at_utc')}",
        f"- Module: {report.get('module')}",
        f"- Final passed: {report.get('passed')}",
        f"- Cycles used: {report.get('cycles_used')}/{report.get('max_cycles')}",
        f"- Min success rate: {report.get('min_success_rate')}",
        "",
    ]

    cycles = report.get("cycles") if isinstance(report.get("cycles"), list) else []
    for cycle in cycles:
        if not isinstance(cycle, dict):
            continue
        lines.append(f"## Cycle {cycle.get('cycle')}")
        lines.append(f"- Passed: {cycle.get('passed')}")
        lines.append(f"- Return code: {cycle.get('returncode')}")
        lines.append(f"- Report path: {cycle.get('report_path')}")
        lines.append(f"- Success rate: {cycle.get('success_rate')}")
        lines.append(f"- Success/Total: {cycle.get('success')}/{cycle.get('total')}")
        failures = cycle.get("failures") if isinstance(cycle.get("failures"), list) else []
        lines.append(f"- Failure count: {len(failures)}")
        if failures:
            lines.append(f"- First failure: {failures[0]}")
        lines.append("")

    summary_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run result-driven page E2E loops with screenshot-based gating.",
    )
    parser.add_argument(
        "--module",
        required=True,
        choices=sorted(MODULE_ADAPTERS.keys()),
        help="Target module: data_dashboard | cost_estimation | rag",
    )
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL)
    parser.add_argument("--login-email", default=os.getenv("RAG_E2E_LOGIN_EMAIL", "demo@example.com"))
    parser.add_argument(
        "--login-password",
        default=os.getenv("RAG_E2E_LOGIN_PASSWORD", "demo123"),
    )
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--max-cycles", type=int, default=3)
    parser.add_argument("--min-success-rate", type=float, default=-1.0)
    parser.add_argument(
        "--repair-command",
        default="",
        help="Optional shell command to run between failed cycles.",
    )
    parser.add_argument(
        "--cycle-timeout-seconds",
        type=int,
        default=2400,
        help="Timeout for one cycle command execution.",
    )
    parser.add_argument(
        "--repair-timeout-seconds",
        type=int,
        default=1800,
        help="Timeout for repair command execution.",
    )
    parser.add_argument(
        "--rag-csv",
        default=str(PROJECT_ROOT / "docs" / "testing" / "rag_question_bank_180.csv"),
    )
    parser.add_argument("--rag-max-questions", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    module = str(args.module)
    adapter = MODULE_ADAPTERS[module]
    min_success_rate = (
        float(args.min_success_rate)
        if float(args.min_success_rate) >= 0
        else adapter.default_threshold
    )

    output_root = Path(str(args.output_root)).expanduser().resolve()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    gate_root = output_root / "page_result_driven" / f"{module}_{timestamp}"
    gate_root.mkdir(parents=True, exist_ok=True)

    rag_csv = Path(str(args.rag_csv)).expanduser().resolve()
    if module == "rag" and not rag_csv.exists():
        raise FileNotFoundError(f"RAG CSV does not exist: {rag_csv}")

    cycles: List[Dict[str, Any]] = []
    overall_passed = False
    started = time.perf_counter()

    max_cycles = max(1, int(args.max_cycles))
    for cycle in range(1, max_cycles + 1):
        cycle_dir = gate_root / f"cycle_{cycle:02d}"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        command, known_rag_output = _build_module_command(
            module=module,
            adapter=adapter,
            frontend_url=str(args.frontend_url),
            login_email=str(args.login_email),
            login_password=str(args.login_password),
            output_root=output_root,
            rag_csv=rag_csv,
            rag_max_questions=int(args.rag_max_questions),
            cycle_dir=cycle_dir,
        )

        returncode: int
        raw_output: str
        try:
            returncode, raw_output = _run_command(
                command,
                timeout_seconds=max(120, int(args.cycle_timeout_seconds)),
            )
        except subprocess.TimeoutExpired:
            cycle_result = {
                "cycle": cycle,
                "command": command,
                "returncode": -9,
                "passed": False,
                "error": f"cycle_timeout>{args.cycle_timeout_seconds}s",
                "report_path": "",
                "success_rate": 0.0,
                "success": 0,
                "total": 0,
                "failures": [],
                "raw_output_tail": "",
            }
            cycles.append(cycle_result)
            break

        kv = _parse_kv_output(raw_output)
        report_path = ""
        report_obj: Dict[str, Any] = {}
        eval_result: Dict[str, Any] = {
            "passed": False,
            "success_rate": 0.0,
            "success": 0,
            "total": 0,
            "failures": [],
        }
        error_text = ""

        try:
            resolved_report = _resolve_report_path(
                module=module,
                adapter=adapter,
                kv=kv,
                known_rag_output=known_rag_output,
            )
            report_path = str(resolved_report)
            if not resolved_report.exists():
                raise FileNotFoundError(f"report_not_found:{resolved_report}")
            report_obj = json.loads(resolved_report.read_text(encoding="utf-8"))
            eval_result = _evaluate_report(module, report_obj, min_success_rate)
        except Exception as exc:
            error_text = str(exc)

        cycle_result = {
            "cycle": cycle,
            "command": command,
            "returncode": returncode,
            "passed": bool(eval_result.get("passed")),
            "report_path": report_path,
            "success_rate": eval_result.get("success_rate"),
            "success": eval_result.get("success"),
            "total": eval_result.get("total"),
            "failures": eval_result.get("failures"),
            "raw_output_tail": raw_output[-4000:],
            "kv_output": kv,
            "error": error_text,
            "artifacts": {
                "artifact_output_dir": eval_result.get("artifact_output_dir"),
                "artifact_report_path": eval_result.get("artifact_report_path"),
                "artifact_screenshot_dir": eval_result.get("artifact_screenshot_dir"),
            },
        }
        cycles.append(cycle_result)

        if cycle_result["passed"]:
            overall_passed = True
            break

        if cycle >= max_cycles:
            break

        repair_command = str(args.repair_command or "").strip()
        if not repair_command:
            break

        try:
            repair_code, repair_output = _run_shell(
                repair_command,
                timeout_seconds=max(120, int(args.repair_timeout_seconds)),
            )
            cycle_result["repair"] = {
                "command": repair_command,
                "returncode": repair_code,
                "output_tail": repair_output[-4000:],
            }
            if repair_code != 0:
                break
        except subprocess.TimeoutExpired:
            cycle_result["repair"] = {
                "command": repair_command,
                "returncode": -9,
                "output_tail": "",
                "error": f"repair_timeout>{args.repair_timeout_seconds}s",
            }
            break

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    final_cycle = cycles[-1] if cycles else {}
    gate_report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "module": module,
        "frontend_url": str(args.frontend_url),
        "output_root": str(output_root),
        "gate_root": str(gate_root),
        "max_cycles": max_cycles,
        "cycles_used": len(cycles),
        "min_success_rate": min_success_rate,
        "passed": overall_passed,
        "elapsed_ms": elapsed_ms,
        "final_report_path": final_cycle.get("report_path"),
        "final_success_rate": final_cycle.get("success_rate"),
        "final_success": final_cycle.get("success"),
        "final_total": final_cycle.get("total"),
        "cycles": cycles,
    }

    report_path = gate_root / f"{module}_gate_report.json"
    report_path.write_text(json.dumps(gate_report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = gate_root / f"{module}_gate_summary.md"
    _write_summary_markdown(gate_report, summary_path)

    print("Page result-driven gate run complete.")
    print(f"module={module}")
    print(f"passed={overall_passed}")
    print(f"cycles_used={len(cycles)}")
    print(f"final_success_rate={gate_report.get('final_success_rate')}")
    print(f"gate_report={report_path}")
    print(f"gate_summary={summary_path}")
    if final_cycle.get("report_path"):
        print(f"module_report={final_cycle.get('report_path')}")

    return 0 if overall_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
