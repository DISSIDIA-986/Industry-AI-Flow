#!/usr/bin/env python3
"""Run a focused Data Dashboard metadata-flow browser test with staged screenshots."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "temp"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:3001"


def _load_base_module():
    base_path = PROJECT_ROOT / "scripts" / "testing" / "run_data_dashboard_agent_browser_e2e.py"
    spec = importlib.util.spec_from_file_location("data_dashboard_agent_base", base_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load base agent-browser test module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _bool_check(payload: Dict[str, Any], *, require_file: bool = False) -> Dict[str, Any]:
    result_json = payload.get("result_json") if isinstance(payload, dict) else None
    if not isinstance(result_json, dict):
        return {
            "ok": False,
            "reason": "result_json_missing",
            "code_mode": "",
            "metadata_status": "",
            "raw_data_sent_to_llm": None,
            "file_path": "",
        }

    code_generation = result_json.get("code_generation")
    code_mode = str(code_generation.get("mode") or "") if isinstance(code_generation, dict) else ""

    metadata_extraction = result_json.get("metadata_extraction")
    metadata_status = (
        str(metadata_extraction.get("status") or "") if isinstance(metadata_extraction, dict) else ""
    )

    llm_input_policy = result_json.get("llm_input_policy")
    raw_data_sent = (
        llm_input_policy.get("raw_data_sent_to_llm")
        if isinstance(llm_input_policy, dict)
        else None
    )
    policy_mode = str(llm_input_policy.get("mode") or "") if isinstance(llm_input_policy, dict) else ""

    file_path = str(result_json.get("file_path") or "")
    if not file_path:
        chart_info = result_json.get("chart_info")
        if isinstance(chart_info, dict):
            file_path = str(chart_info.get("output_file") or "")

    success = result_json.get("success") is not False
    metadata_ok = metadata_status == "ok"
    policy_ok = policy_mode == "metadata_only" and raw_data_sent is False
    code_ok = bool(code_mode)
    file_ok = (not require_file) or bool(file_path)

    ok = bool(success and metadata_ok and policy_ok and code_ok and file_ok)
    reason_parts = []
    if not success:
        reason_parts.append("result_success_false")
    if not metadata_ok:
        reason_parts.append("metadata_not_ok")
    if not policy_ok:
        reason_parts.append("policy_not_metadata_only")
    if not code_ok:
        reason_parts.append("code_mode_missing")
    if not file_ok:
        reason_parts.append("file_path_missing")

    return {
        "ok": ok,
        "reason": ",".join(reason_parts) if reason_parts else "ok",
        "code_mode": code_mode,
        "metadata_status": metadata_status,
        "raw_data_sent_to_llm": raw_data_sent,
        "file_path": file_path,
    }


def run_suite(
    *,
    frontend_url: str,
    login_email: str,
    login_password: str,
    output_root: Path,
) -> Dict[str, Any]:
    base = _load_base_module()
    if base.shutil.which("agent-browser") is None:
        raise RuntimeError("agent-browser CLI is not installed or not in PATH")

    data_files = base._prepare_demo_datasets()
    data_file = data_files["projects"]
    question = (
        "Use metadata to generate dynamic analysis code and provide a concise project dataset summary."
    )
    analysis_type = "summary"
    chart_type = "scatter"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = output_root / f"data_dashboard_metadata_flow_test_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    base._ensure_logged_in(frontend_url=frontend_url, email=login_email, password=login_password)
    base._open_data_page(frontend_url)

    refs = base._snapshot_refs()
    set_ok, set_out = base._set_form_values(
        data_file=data_file,
        analysis_type=analysis_type,
        chart_type=chart_type,
        instruction=question,
        refs=refs,
    )
    if not set_ok:
        raise RuntimeError(f"set_form_values_failed: {set_out}")

    # Step 1: form ready screenshot
    form_shot = out_dir / "01_form_ready.png"
    base._run_agent_browser(["screenshot", str(form_shot), "--full"], timeout=50)

    # Step 2: run analysis and verify metadata extraction + LLM policy
    run_analysis_target = refs.get("run_analysis") or base.RUN_ANALYSIS_BUTTON_SELECTOR
    click_ok, click_out = base._run_agent_browser(["click", run_analysis_target], timeout=25)
    if not click_ok:
        raise RuntimeError(f"click_run_analysis_failed: {click_out}")

    done_ok, done_state = base._wait_for_analysis_complete(max_wait_seconds=180)
    analysis_payload = base._read_result_payload()
    analysis_check = _bool_check(analysis_payload, require_file=False)
    analysis_summary = (
        f"analysis_ok={analysis_check['ok']}; reason={analysis_check['reason']}; "
        f"code_mode={analysis_check['code_mode']}; metadata={analysis_check['metadata_status']}; "
        f"raw_data_sent={analysis_check['raw_data_sent_to_llm']}; wait={done_ok}/{done_state}"
    )
    base._inject_qa_banner(question=question, answer=analysis_summary, case_id="metadata_flow_analysis")
    base._run_agent_browser(["wait", "700"], timeout=10)
    analysis_shot = out_dir / "02_analysis_metadata_checks.png"
    base._run_agent_browser(["screenshot", str(analysis_shot), "--full"], timeout=50)

    # Step 3: run visualization and verify metadata extraction + LLM policy + artifact
    refs = base._snapshot_refs()
    generate_viz_target = refs.get("generate_viz") or base.GENERATE_VIZ_BUTTON_SELECTOR
    viz_click_ok, viz_click_out = base._run_agent_browser(["click", generate_viz_target], timeout=25)
    if not viz_click_ok:
        raise RuntimeError(f"click_generate_viz_failed: {viz_click_out}")

    viz_done_ok, viz_done_state = base._wait_for_analysis_complete(max_wait_seconds=180)
    viz_payload = base._read_viz_payload()
    viz_check = _bool_check(viz_payload, require_file=True)
    viz_summary = (
        f"viz_ok={viz_check['ok']}; reason={viz_check['reason']}; "
        f"code_mode={viz_check['code_mode']}; metadata={viz_check['metadata_status']}; "
        f"raw_data_sent={viz_check['raw_data_sent_to_llm']}; file={viz_check['file_path']}; "
        f"wait={viz_done_ok}/{viz_done_state}"
    )
    merged_summary = f"{analysis_summary} | {viz_summary}"
    base._inject_qa_banner(question=question, answer=merged_summary, case_id="metadata_flow_viz")
    base._run_agent_browser(["wait", "700"], timeout=10)
    viz_shot = out_dir / "03_visualization_metadata_checks.png"
    base._run_agent_browser(["screenshot", str(viz_shot), "--full"], timeout=50)

    # Step 4: final state screenshot
    base._run_agent_browser(["wait", "500"], timeout=10)
    final_shot = out_dir / "04_final_state.png"
    base._run_agent_browser(["screenshot", str(final_shot), "--full"], timeout=50)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "frontend_url": frontend_url,
        "output_dir": str(out_dir),
        "question": question,
        "analysis_type": analysis_type,
        "chart_type": chart_type,
        "data_file": data_file,
        "analysis_done": {"ok": done_ok, "state": done_state},
        "viz_done": {"ok": viz_done_ok, "state": viz_done_state},
        "analysis_check": analysis_check,
        "viz_check": viz_check,
        "analysis_payload": analysis_payload,
        "visualization_payload": viz_payload,
        "screenshots": [
            str(form_shot),
            str(analysis_shot),
            str(viz_shot),
            str(final_shot),
        ],
    }

    report["overall_success"] = bool(analysis_check["ok"] and viz_check["ok"])
    report_path = out_dir / "metadata_flow_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    case_index = out_dir / "CASE_INDEX.md"
    case_index.write_text(
        (
            "# Data Dashboard Metadata Flow Verification\n\n"
            f"- Generated at (UTC): {report['generated_at_utc']}\n"
            f"- Overall success: {report['overall_success']}\n"
            f"- Analysis check: {analysis_summary}\n"
            f"- Visualization check: {viz_summary}\n\n"
            "## Screenshots\n"
            f"- {form_shot}\n"
            f"- {analysis_shot}\n"
            f"- {viz_shot}\n"
            f"- {final_shot}\n"
        ),
        encoding="utf-8",
    )

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run focused Data Dashboard metadata-flow browser test and screenshots.",
    )
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL)
    parser.add_argument("--login-email", default=os.getenv("RAG_E2E_LOGIN_EMAIL", "demo@example.com"))
    parser.add_argument("--login-password", default=os.getenv("RAG_E2E_LOGIN_PASSWORD", "demo123"))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    report = run_suite(
        frontend_url=str(args.frontend_url),
        login_email=str(args.login_email),
        login_password=str(args.login_password),
        output_root=Path(args.output_root),
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    print("Data Dashboard metadata-flow run complete.")
    print(f"output_dir={report['output_dir']}")
    print(f"overall_success={report['overall_success']}")
    print(f"elapsed_ms={elapsed_ms}")
    return 0 if report["overall_success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
