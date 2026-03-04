#!/usr/bin/env python3
"""Run Data Dashboard browser automation and capture 5 demo screenshots."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "temp"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:3001"

LOGIN_EMAIL_SELECTOR = 'input[type="email"]'
LOGIN_PASSWORD_SELECTOR = 'input[type="password"]'
LOGIN_BUTTON_SELECTOR = 'button:has-text("Log in")'
RUN_ANALYSIS_BUTTON_SELECTOR = 'button:has-text("2) Run Analysis")'
GENERATE_VIZ_BUTTON_SELECTOR = 'button:has-text("3) Generate Visualization")'
UPLOAD_BUTTON_SELECTOR = 'button:has-text("1) Upload Data")'
PROCESSING_BUTTON_SELECTOR = 'button:has-text("Processing...")'
ERROR_SELECTOR = "p.error-text"


@dataclass(frozen=True)
class Case:
    case_id: str
    question: str
    analysis_type: str
    chart_type: str
    dataset_key: str


def _extract_last_int(text: str) -> int:
    values = re.findall(r"-?\d+", text or "")
    if not values:
        return 0
    return int(values[-1])


def _parse_agent_json_output(raw_output: str) -> Any:
    text = (raw_output or "").strip()
    if not text:
        return None

    # First, attempt direct and nested JSON decoding.
    current: Any = text
    for _ in range(4):
        if isinstance(current, (dict, list)):
            return current
        if not isinstance(current, str):
            return current
        probe = current.strip()
        if not probe:
            return None
        try:
            current = json.loads(probe)
            continue
        except Exception:
            break

    # Fallback: extract trailing JSON object from mixed output.
    match = re.search(r"\{[\s\S]*\}\s*$", text)
    if match:
        candidate = match.group(0).strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, str):
                return _parse_agent_json_output(parsed)
            return parsed
        except Exception:
            return None

    return None


def _normalize_path(path: str) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).expanduser().resolve())
    except Exception:
        return str(path)


def _run_agent_browser(args: list[str], timeout: int = 45) -> tuple[bool, str]:
    timeout_cmd = shutil.which("timeout")
    command = ["agent-browser", *args]
    if timeout_cmd:
        command = [timeout_cmd, str(max(1, int(timeout))), *command]

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(8, int(timeout) + 10),
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 124 and timeout_cmd:
            return False, f"agent-browser timeout after {timeout}s: {' '.join(args)}"
        return proc.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"agent-browser timeout after {timeout}s: {' '.join(args)}"
    except Exception as exc:
        return False, f"agent-browser execution error: {exc}"


def _run_eval(js: str, timeout: int = 30) -> tuple[bool, str]:
    encoded = base64.b64encode(js.encode("utf-8")).decode("ascii")
    return _run_agent_browser(["eval", "-b", encoded], timeout=timeout)


def _count(selector: str) -> int:
    ok, output = _run_agent_browser(["get", "count", selector], timeout=20)
    if not ok:
        return -1
    return _extract_last_int(output)


def _open_data_page(frontend_url: str) -> None:
    data_url = frontend_url.rstrip("/") + "/data-analysis"
    open_ok, open_out = _run_agent_browser(["open", data_url], timeout=45)
    if not open_ok:
        raise RuntimeError(f"failed_to_open_data_page: {open_out}")

    wait_ok, wait_out = _run_agent_browser(["wait", "--load", "networkidle"], timeout=45)
    if not wait_ok:
        # Some pages keep polling in background, so networkidle can fail.
        _run_agent_browser(["wait", "1500"], timeout=10)
        if "timeout" in (wait_out or "").lower():
            pass


def _snapshot_refs() -> dict[str, str]:
    ok, out = _run_agent_browser(["snapshot", "-i"], timeout=30)
    if not ok:
        return {}

    refs: dict[str, str] = {}
    patterns = {
        "uploaded_path": r'^\-\s+textbox\s+"Uploaded Path"\s+\[ref=([^\]]+)\]',
        "instruction": r'^\-\s+textbox\s+"Analysis Instruction"\s+\[ref=([^\]]+)\]',
        "analysis_type": r'^\-\s+combobox\s+"Analysis Type"\s+\[ref=([^\]]+)\]',
        "chart_type": r'^\-\s+combobox\s+"Chart Type"\s+\[ref=([^\]]+)\]',
        "run_analysis": r'^\-\s+button\s+"2\)\s*Run Analysis"\s+\[ref=([^\]]+)\]',
        "generate_viz": r'^\-\s+button\s+"3\)\s*Generate Visualization"\s+\[ref=([^\]]+)\]',
    }
    lines = (out or "").splitlines()
    for line in lines:
        for key, pattern in patterns.items():
            if key in refs:
                continue
            match = re.search(pattern, line.strip())
            if match:
                refs[key] = f"@{match.group(1)}"
    return refs


def _ensure_logged_in(frontend_url: str, email: str, password: str) -> None:
    _open_data_page(frontend_url)

    if _count(RUN_ANALYSIS_BUTTON_SELECTOR) > 0:
        return

    if _count(LOGIN_EMAIL_SELECTOR) > 0 and _count(LOGIN_BUTTON_SELECTOR) > 0:
        _run_agent_browser(["fill", LOGIN_EMAIL_SELECTOR, email], timeout=20)
        _run_agent_browser(["fill", LOGIN_PASSWORD_SELECTOR, password], timeout=20)
        click_ok, click_out = _run_agent_browser(["click", LOGIN_BUTTON_SELECTOR], timeout=25)
        if not click_ok:
            raise RuntimeError(f"failed_to_click_login_button: {click_out}")
        _run_agent_browser(["wait", "--load", "networkidle"], timeout=45)
        _run_agent_browser(["wait", "1800"], timeout=10)
        _open_data_page(frontend_url)

    if _count(RUN_ANALYSIS_BUTTON_SELECTOR) <= 0:
        raise RuntimeError("data_analysis_page_not_ready_after_login")


def _prepare_demo_datasets() -> dict[str, str]:
    datasets_dir = PROJECT_ROOT / "test_resources" / "datasets"
    src_one = datasets_dir / "architecture_building_projects.csv"
    src_two = datasets_dir / "construction_materials_properties.csv"
    if not src_one.exists() or not src_two.exists():
        raise FileNotFoundError("Required demo datasets are missing in test_resources/datasets")

    tmp_root = Path(os.getenv("TMPDIR", "/tmp")).resolve()
    demo_dir = tmp_root / "luncheon_data_demo"
    demo_dir.mkdir(parents=True, exist_ok=True)

    dst_one = demo_dir / src_one.name
    dst_two = demo_dir / src_two.name
    shutil.copy2(src_one, dst_one)
    shutil.copy2(src_two, dst_two)

    return {
        "projects": str(dst_one.resolve()),
        "materials": str(dst_two.resolve()),
    }


def _set_form_values(
    data_file: str,
    analysis_type: str,
    chart_type: str,
    instruction: str,
    refs: dict[str, str],
) -> tuple[bool, str]:
    path_target = refs.get("uploaded_path") or 'label:has-text("Uploaded Path") input'
    instruction_target = refs.get("instruction") or 'label:has-text("Analysis Instruction") input'
    analysis_target = refs.get("analysis_type") or 'label:has-text("Analysis Type") select'
    chart_target = refs.get("chart_type") or 'label:has-text("Chart Type") select'

    fill_ok, fill_out = _run_agent_browser(["fill", path_target, data_file], timeout=25)
    if not fill_ok:
        return False, f"fill_uploaded_path_failed: {fill_out}"

    instruction_ok, instruction_out = _run_agent_browser(
        ["fill", instruction_target, instruction],
        timeout=20,
    )
    if not instruction_ok:
        return False, f"fill_instruction_failed: {instruction_out}"

    select_ok, select_out = _run_agent_browser(
        ["select", analysis_target, analysis_type],
        timeout=20,
    )
    if not select_ok:
        return False, f"select_analysis_type_failed: {select_out}"

    chart_ok, chart_out = _run_agent_browser(["select", chart_target, chart_type], timeout=20)
    if not chart_ok:
        return False, f"select_chart_type_failed: {chart_out}"

    # Verify displayed values for deterministic runs.
    verify_js = r"""
(() => {
  const labels = Array.from(document.querySelectorAll('label'));
  let pathInput = null;
  let instructionInput = null;
  let analysisSelect = null;
  let chartSelect = null;
  for (const label of labels) {
    const text = (label.textContent || '').trim();
    if (!pathInput && text.includes('Uploaded Path')) {
      pathInput = label.querySelector('input');
    }
    if (!instructionInput && text.includes('Analysis Instruction')) {
      instructionInput = label.querySelector('input');
    }
    if (!analysisSelect && text.includes('Analysis Type')) {
      analysisSelect = label.querySelector('select');
    }
    if (!chartSelect && text.includes('Chart Type')) {
      chartSelect = label.querySelector('select');
    }
  }
  return JSON.stringify({
    path: pathInput ? pathInput.value : null,
    instruction: instructionInput ? instructionInput.value : null,
    analysis_type: analysisSelect ? analysisSelect.value : null,
    chart_type: chartSelect ? chartSelect.value : null,
  });
})()
"""
    verify_ok, verify_out = _run_eval(verify_js, timeout=20)
    if not verify_ok:
        return False, f"verify_form_values_failed: {verify_out}"

    verified_path = ""
    verified_instruction = ""
    verified_type = ""
    verified_chart = ""
    parsed = _parse_agent_json_output(verify_out)
    if isinstance(parsed, dict):
        verified_path = str(parsed.get("path") or "")
        verified_instruction = str(parsed.get("instruction") or "")
        verified_type = str(parsed.get("analysis_type") or "")
        verified_chart = str(parsed.get("chart_type") or "")

    expected_path_norm = _normalize_path(data_file)
    actual_path_norm = _normalize_path(verified_path)
    if (
        actual_path_norm != expected_path_norm
        or verified_type != analysis_type
        or verified_chart != chart_type
        or verified_instruction.strip() != instruction.strip()
    ):
        return (
            False,
            "form_value_mismatch: "
            f"expected_path={expected_path_norm} expected_type={analysis_type} "
            f"expected_chart={chart_type} actual_chart={verified_chart} "
            f"actual_path={actual_path_norm} actual_type={verified_type}",
        )

    return (
        True,
        f"{fill_out[:120]} | {instruction_out[:120]} | {select_out[:90]} | "
        f"{chart_out[:90]} | {verify_out[:220]}",
    )


def _wait_for_analysis_complete(max_wait_seconds: int = 120) -> tuple[bool, str]:
    deadline = time.time() + max_wait_seconds
    last_state = "unknown"

    while time.time() < deadline:
        processing_count = _count(PROCESSING_BUTTON_SELECTOR)
        if processing_count > 0:
            last_state = "processing"
            _run_agent_browser(["wait", "1600"], timeout=10)
            continue

        upload_count = _count(UPLOAD_BUTTON_SELECTOR)
        if upload_count > 0:
            last_state = "idle"
            return True, last_state

        if _count(ERROR_SELECTOR) > 0:
            last_state = "error_visible"
            return True, last_state

        _run_agent_browser(["wait", "1200"], timeout=10)

    return False, last_state


def _read_result_payload() -> dict[str, Any]:
    js = r"""
(() => {
  const sections = Array.from(document.querySelectorAll('.result-grid > div'));
  const resultSection = sections[0];
  const payload = {
    ok: true,
    result_text: '',
    error_text: '',
    parse_error: '',
  };

  if (resultSection) {
    const pre = resultSection.querySelector('pre');
    payload.result_text = pre ? (pre.textContent || '').trim() : '';
  }

  const errorNode = document.querySelector('p.error-text');
  if (errorNode) {
    payload.error_text = (errorNode.textContent || '').trim();
  }

  if (!payload.result_text) {
    return JSON.stringify(payload);
  }

  if (payload.result_text.startsWith('No analysis result yet')) {
    return JSON.stringify(payload);
  }

  try {
    payload.result_json = JSON.parse(payload.result_text);
  } catch (err) {
    payload.parse_error = String(err);
  }

  return JSON.stringify(payload);
})()
"""
    ok, out = _run_eval(js, timeout=20)
    if not ok:
        return {"ok": False, "error": out}

    parsed = _parse_agent_json_output(out)
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, str):
        return {
            "ok": False,
            "error": "result_payload_is_string",
            "result_text": parsed.strip(),
            "error_text": "",
            "parse_error": "",
        }
    return {"ok": False, "error": "unable_to_parse_result_payload", "raw": out.strip()}


def _read_viz_payload() -> dict[str, Any]:
    js = r"""
(() => {
  const sections = Array.from(document.querySelectorAll('.result-grid > div'));
  const vizSection = sections[1];
  const payload = {
    ok: true,
    result_text: '',
    error_text: '',
    parse_error: '',
  };

  if (vizSection) {
    const pre = vizSection.querySelector('pre');
    payload.result_text = pre ? (pre.textContent || '').trim() : '';
  }

  const errorNode = document.querySelector('p.error-text');
  if (errorNode) {
    payload.error_text = (errorNode.textContent || '').trim();
  }

  if (!payload.result_text) {
    return JSON.stringify(payload);
  }

  if (payload.result_text.startsWith('No visualization result yet')) {
    return JSON.stringify(payload);
  }

  try {
    payload.result_json = JSON.parse(payload.result_text);
  } catch (err) {
    payload.parse_error = String(err);
  }

  return JSON.stringify(payload);
})()
"""
    ok, out = _run_eval(js, timeout=20)
    if not ok:
        return {"ok": False, "error": out}

    parsed = _parse_agent_json_output(out)
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, str):
        return {
            "ok": False,
            "error": "viz_payload_is_string",
            "result_text": parsed.strip(),
            "error_text": "",
            "parse_error": "",
        }
    return {"ok": False, "error": "unable_to_parse_viz_payload", "raw": out.strip()}


def _build_answer_summary(payload: Any) -> str:
    if not isinstance(payload, dict):
        return str(payload)[:320] if payload is not None else "No result returned."

    result_json = payload.get("result_json")
    error_text = str(payload.get("error_text") or "").strip()
    parse_error = str(payload.get("parse_error") or "").strip()

    if isinstance(result_json, dict):
        success = result_json.get("success")
        analysis_type = result_json.get("analysis_type")
        answer = str(result_json.get("answer") or "").strip()
        backend_error = str(result_json.get("error") or "").strip()
        code_generation = result_json.get("code_generation")
        code_mode = (
            str(code_generation.get("mode") or "")
            if isinstance(code_generation, dict)
            else ""
        )
        metadata_extraction = result_json.get("metadata_extraction")
        metadata_status = (
            str(metadata_extraction.get("status") or "")
            if isinstance(metadata_extraction, dict)
            else ""
        )
        llm_policy = result_json.get("llm_input_policy")
        raw_data_sent = (
            llm_policy.get("raw_data_sent_to_llm")
            if isinstance(llm_policy, dict)
            else None
        )

        if backend_error:
            return (
                f"success={success}; analysis_type={analysis_type}; code_mode={code_mode}; "
                f"metadata={metadata_status}; raw_data_sent={raw_data_sent}; "
                f"error={backend_error[:220]}"
            )
        if answer:
            return (
                f"success={success}; analysis_type={analysis_type}; code_mode={code_mode}; "
                f"metadata={metadata_status}; raw_data_sent={raw_data_sent}; "
                f"answer={answer[:180]}"
            )

        snippet = json.dumps(result_json, ensure_ascii=False)[:320]
        return (
            f"success={success}; analysis_type={analysis_type}; code_mode={code_mode}; "
            f"metadata={metadata_status}; raw_data_sent={raw_data_sent}; result={snippet}"
        )

    if error_text:
        return f"ui_error={error_text[:320]}"
    if parse_error:
        return f"parse_error={parse_error[:320]}"

    raw = str(payload.get("result_text") or "").strip()
    if raw:
        return raw[:320]
    return "No result returned."


def _build_viz_summary(payload: Any) -> str:
    if not isinstance(payload, dict):
        return str(payload)[:320] if payload is not None else "No visualization returned."

    result_json = payload.get("result_json")
    error_text = str(payload.get("error_text") or "").strip()
    parse_error = str(payload.get("parse_error") or "").strip()

    if isinstance(result_json, dict):
        success = result_json.get("success")
        file_path = str(result_json.get("file_path") or "")
        chart_info = result_json.get("chart_info")
        chart_type = (
            chart_info.get("chart_type") if isinstance(chart_info, dict) else result_json.get("chart_type")
        )
        code_generation = result_json.get("code_generation")
        code_mode = (
            str(code_generation.get("mode") or "")
            if isinstance(code_generation, dict)
            else ""
        )
        metadata_extraction = result_json.get("metadata_extraction")
        metadata_status = (
            str(metadata_extraction.get("status") or "")
            if isinstance(metadata_extraction, dict)
            else ""
        )
        llm_policy = result_json.get("llm_input_policy")
        raw_data_sent = (
            llm_policy.get("raw_data_sent_to_llm")
            if isinstance(llm_policy, dict)
            else None
        )
        if file_path:
            return (
                f"success={success}; chart_type={chart_type}; code_mode={code_mode}; "
                f"metadata={metadata_status}; raw_data_sent={raw_data_sent}; file_path={file_path}"
            )
        backend_error = str(result_json.get("error") or "").strip()
        if backend_error:
            return (
                f"success={success}; chart_type={chart_type}; code_mode={code_mode}; "
                f"metadata={metadata_status}; raw_data_sent={raw_data_sent}; "
                f"error={backend_error[:200]}"
            )
        return (
            f"success={success}; chart_type={chart_type}; code_mode={code_mode}; "
            f"metadata={metadata_status}; raw_data_sent={raw_data_sent}; result_ready=true"
        )

    if error_text:
        return f"ui_error={error_text[:320]}"
    if parse_error:
        return f"parse_error={parse_error[:320]}"
    raw = str(payload.get("result_text") or "").strip()
    if raw:
        return raw[:320]
    return "No visualization returned."


def _inject_qa_banner(question: str, answer: str, case_id: str) -> tuple[bool, str]:
    payload = json.dumps({"question": question, "answer": answer, "case_id": case_id})
    js = f"""
(() => {{
  const payload = {payload};
  const old = document.getElementById('qa-capture-banner');
  if (old) old.remove();

  const banner = document.createElement('section');
  banner.id = 'qa-capture-banner';
  banner.style.position = 'sticky';
  banner.style.top = '0';
  banner.style.zIndex = '9999';
  banner.style.background = '#ffffff';
  banner.style.border = '2px solid #1e40af';
  banner.style.borderRadius = '10px';
  banner.style.padding = '12px 14px';
  banner.style.margin = '10px 0 14px 0';
  banner.style.boxShadow = '0 6px 16px rgba(15, 23, 42, 0.12)';

  const title = document.createElement('div');
  title.style.fontWeight = '700';
  title.style.fontSize = '14px';
  title.style.marginBottom = '8px';
  title.textContent = `Data Dashboard Demo - ${{payload.case_id}}`;
  banner.appendChild(title);

  const q = document.createElement('div');
  q.style.fontSize = '13px';
  q.style.lineHeight = '1.5';
  q.style.marginBottom = '8px';
  q.innerHTML = '<strong>Question:</strong> ' + String(payload.question || '');
  banner.appendChild(q);

  const a = document.createElement('div');
  a.style.fontSize = '13px';
  a.style.lineHeight = '1.5';
  a.innerHTML = '<strong>Answer:</strong> ' + String(payload.answer || '');
  banner.appendChild(a);

  const panel = document.querySelector('.panel-card');
  if (!panel || !panel.parentElement) {{
    return 'panel_not_found';
  }}

  panel.parentElement.insertBefore(banner, panel);

  // Improve capture coverage: slightly zoom out and keep page top visible.
  document.body.style.zoom = '0.85';
  window.scrollTo({{ top: 0, left: 0, behavior: 'instant' }});

  return 'ok';
}})()
"""
    return _run_eval(js, timeout=20)


def _run_case(case: Case, data_files: dict[str, str], screenshot_path: Path) -> dict[str, Any]:
    data_file = data_files[case.dataset_key]
    refs: dict[str, str] = {}
    set_out = ""
    analysis_click_out = ""
    viz_click_out = ""
    analysis_done_ok = False
    analysis_done_state = "unknown"
    viz_done_ok = False
    viz_done_state = "unknown"
    analysis_payload: dict[str, Any] = {}
    viz_payload: dict[str, Any] = {}
    analysis_answer = ""
    viz_answer = ""
    shot_ok = False
    shot_out = ""
    analysis_backend_success: Any = None
    viz_backend_success: Any = None
    analysis_match = False
    viz_chart_match = False
    analysis_ui_error_text = ""
    viz_ui_error_text = ""
    viz_file_path = ""
    attempt_used = 0

    for attempt in range(1, 4):
        attempt_used = attempt
        refs = _snapshot_refs()
        set_ok, set_out = _set_form_values(
            data_file=data_file,
            analysis_type=case.analysis_type,
            chart_type=case.chart_type,
            instruction=case.question,
            refs=refs,
        )
        if not set_ok:
            if attempt < 3:
                _run_agent_browser(["wait", "1000"], timeout=10)
                continue
            return {
                "case_id": case.case_id,
                    "question": case.question,
                    "analysis_type": case.analysis_type,
                    "chart_type": case.chart_type,
                    "data_file": data_file,
                    "success": False,
                    "attempt_used": attempt_used,
                    "error": f"set_form_failed: {set_out}",
                    "screenshot_path": "",
                }

        run_analysis_target = refs.get("run_analysis") or RUN_ANALYSIS_BUTTON_SELECTOR
        analysis_click_ok, analysis_click_out = _run_agent_browser(
            ["click", run_analysis_target],
            timeout=25,
        )
        if not analysis_click_ok:
            if attempt < 3:
                _run_agent_browser(["wait", "1000"], timeout=10)
                continue
            return {
                "case_id": case.case_id,
                "question": case.question,
                "analysis_type": case.analysis_type,
                "chart_type": case.chart_type,
                "data_file": data_file,
                "success": False,
                "attempt_used": attempt_used,
                "error": f"click_run_analysis_failed: {analysis_click_out}",
                "screenshot_path": "",
            }

        analysis_done_ok, analysis_done_state = _wait_for_analysis_complete(max_wait_seconds=180)
        analysis_payload = _read_result_payload()
        analysis_answer = _build_answer_summary(analysis_payload)

        analysis_result_json = (
            analysis_payload.get("result_json") if isinstance(analysis_payload, dict) else None
        )
        analysis_ui_error_text = (
            str(analysis_payload.get("error_text") or "").strip()
            if isinstance(analysis_payload, dict)
            else ""
        )
        analysis_backend_success = None
        analysis_match = False
        analysis_has_result = False
        if isinstance(analysis_result_json, dict):
            analysis_backend_success = analysis_result_json.get("success")
            analysis_match = (
                str(analysis_result_json.get("analysis_type") or "") == case.analysis_type
            )
            analysis_has_result = analysis_backend_success is not False and analysis_match

        if (
            not analysis_done_ok
            or not analysis_has_result
        ):
            if attempt < 3 and "Upload data file first" in analysis_ui_error_text:
                _run_agent_browser(["wait", "900"], timeout=10)
                continue
            if attempt < 3:
                _run_agent_browser(["wait", "900"], timeout=10)
                continue
            break

        generate_viz_target = refs.get("generate_viz") or GENERATE_VIZ_BUTTON_SELECTOR
        viz_click_ok, viz_click_out = _run_agent_browser(
            ["click", generate_viz_target],
            timeout=25,
        )
        if not viz_click_ok:
            if attempt < 3:
                _run_agent_browser(["wait", "1000"], timeout=10)
                continue
            break

        viz_done_ok, viz_done_state = _wait_for_analysis_complete(max_wait_seconds=180)
        viz_payload = _read_viz_payload()
        viz_answer = _build_viz_summary(viz_payload)

        viz_result_json = viz_payload.get("result_json") if isinstance(viz_payload, dict) else None
        viz_ui_error_text = (
            str(viz_payload.get("error_text") or "").strip() if isinstance(viz_payload, dict) else ""
        )
        viz_backend_success = None
        viz_chart_match = False
        viz_file_path = ""
        viz_has_result = False
        if isinstance(viz_result_json, dict):
            viz_backend_success = viz_result_json.get("success")
            chart_info = viz_result_json.get("chart_info")
            reported_chart_type = (
                str(chart_info.get("chart_type") or "")
                if isinstance(chart_info, dict)
                else str(viz_result_json.get("chart_type") or "")
            )
            viz_chart_match = reported_chart_type == case.chart_type
            viz_file_path = str(viz_result_json.get("file_path") or "")
            if not viz_file_path and isinstance(chart_info, dict):
                viz_file_path = str(chart_info.get("output_file") or "")
            viz_has_result = (
                viz_backend_success is not False and viz_chart_match and bool(viz_file_path)
            )

        if (
            viz_done_ok
            and viz_has_result
        ):
            break

        if attempt < 3:
            _run_agent_browser(["wait", "900"], timeout=10)
            continue

    final_answer = f"{analysis_answer} | Visualization: {viz_answer}".strip()
    _inject_qa_banner(question=case.question, answer=final_answer, case_id=case.case_id)
    _run_agent_browser(["wait", "700"], timeout=10)
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    shot_ok, shot_out = _run_agent_browser(
        ["screenshot", str(screenshot_path), "--full"],
        timeout=50,
    )

    analysis_result_json = (
        analysis_payload.get("result_json") if isinstance(analysis_payload, dict) else None
    )
    viz_result_json = viz_payload.get("result_json") if isinstance(viz_payload, dict) else None
    overall_success = bool(
        analysis_done_ok
        and viz_done_ok
        and shot_ok
        and isinstance(analysis_result_json, dict)
        and isinstance(viz_result_json, dict)
        and analysis_match
        and viz_chart_match
        and analysis_backend_success is not False
        and viz_backend_success is not False
        and bool(viz_file_path)
    )

    return {
        "case_id": case.case_id,
        "question": case.question,
        "analysis_type": case.analysis_type,
        "chart_type": case.chart_type,
        "data_file": data_file,
        "attempt_used": attempt_used,
        "refs": refs,
        "analysis_wait_complete": analysis_done_ok,
        "analysis_wait_state": analysis_done_state,
        "viz_wait_complete": viz_done_ok,
        "viz_wait_state": viz_done_state,
        "analysis_match": analysis_match,
        "viz_chart_match": viz_chart_match,
        "analysis_backend_success": analysis_backend_success,
        "viz_backend_success": viz_backend_success,
        "analysis_answer_summary": analysis_answer,
        "viz_answer_summary": viz_answer,
        "answer_summary": final_answer,
        "viz_file_path": viz_file_path,
        "success": overall_success,
        "set_form_output": set_out[:300],
        "analysis_click_output": analysis_click_out[:300],
        "viz_click_output": viz_click_out[:300],
        "screenshot_output": shot_out[:240],
        "screenshot_path": str(screenshot_path) if shot_ok else "",
        "analysis_payload": analysis_payload,
        "visualization_payload": viz_payload,
    }


def run_suite(
    *,
    frontend_url: str,
    login_email: str,
    login_password: str,
    output_root: Path,
) -> dict[str, Any]:
    if shutil.which("agent-browser") is None:
        raise RuntimeError("agent-browser CLI is not installed or not in PATH")

    data_files = _prepare_demo_datasets()
    cases = [
        Case(
            case_id="01_overview_summary",
            question="Provide a quick dataset overview including row, column, and key field types.",
            analysis_type="summary",
            chart_type="bar",
            dataset_key="projects",
        ),
        Case(
            case_id="02_numeric_stats_summary",
            question="Run simple EDA and summarize numeric distributions and missing values.",
            analysis_type="eda",
            chart_type="histogram",
            dataset_key="projects",
        ),
        Case(
            case_id="03_cost_regression",
            question="Run a simple regression-style analysis to inspect cost-related signal patterns.",
            analysis_type="regression",
            chart_type="scatter",
            dataset_key="projects",
        ),
        Case(
            case_id="04_category_profile_summary",
            question="Profile categorical fields and provide practical observations for planning decisions.",
            analysis_type="summary",
            chart_type="line",
            dataset_key="projects",
        ),
        Case(
            case_id="05_repeatability_regression",
            question="Run one more summary-style pass to validate repeatable dynamic code execution.",
            analysis_type="summary",
            chart_type="bar",
            dataset_key="projects",
        ),
    ]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = output_root / f"data_dashboard_agent_test_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    _ensure_logged_in(frontend_url=frontend_url, email=login_email, password=login_password)

    case_results: list[dict[str, Any]] = []
    started = time.perf_counter()
    for idx, case in enumerate(cases, start=1):
        _open_data_page(frontend_url)
        screenshot_path = out_dir / f"{idx:02d}_{case.case_id}.png"
        case_result = _run_case(case=case, data_files=data_files, screenshot_path=screenshot_path)
        case_results.append(case_result)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    success_count = sum(1 for row in case_results if row.get("success"))
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "frontend_url": frontend_url,
        "output_dir": str(out_dir),
        "total_cases": len(case_results),
        "success_cases": success_count,
        "success_rate": round(success_count / len(case_results), 4) if case_results else 0.0,
        "elapsed_ms": elapsed_ms,
        "data_files": data_files,
        "cases": case_results,
    }

    report_path = out_dir / "data_dashboard_agent_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    case_index_lines = [
        "# Data Dashboard Screenshot Case Index",
        "",
        f"- Generated at (UTC): {report['generated_at_utc']}",
        f"- Success: {success_count}/{len(case_results)}",
        "",
    ]
    for row in case_results:
        case_index_lines.append(f"## {row.get('case_id')}")
        case_index_lines.append(f"- Question: {row.get('question')}")
        case_index_lines.append(f"- Analysis type: {row.get('analysis_type')}")
        case_index_lines.append(f"- Chart type: {row.get('chart_type')}")
        case_index_lines.append(f"- Success: {row.get('success')}")
        case_index_lines.append(f"- Screenshot: {row.get('screenshot_path')}")
        case_index_lines.append(
            f"- Analysis summary: {row.get('analysis_answer_summary', row.get('answer_summary'))}"
        )
        case_index_lines.append(f"- Visualization summary: {row.get('viz_answer_summary')}")
        case_index_lines.append(f"- Visualization file: {row.get('viz_file_path')}")
        case_index_lines.append("")

    (out_dir / "CASE_INDEX.md").write_text(
        "\n".join(case_index_lines).strip() + "\n",
        encoding="utf-8",
    )

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Data Dashboard browser test and capture 5 screenshots in temp.",
    )
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL)
    parser.add_argument("--login-email", default=os.getenv("RAG_E2E_LOGIN_EMAIL", "demo@example.com"))
    parser.add_argument("--login-password", default=os.getenv("RAG_E2E_LOGIN_PASSWORD", "demo123"))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_suite(
        frontend_url=str(args.frontend_url),
        login_email=str(args.login_email),
        login_password=str(args.login_password),
        output_root=Path(args.output_root),
    )
    print("Data Dashboard agent-browser run complete.")
    print(f"output_dir={report['output_dir']}")
    print(f"success={report['success_cases']}/{report['total_cases']}")
    print(f"success_rate={report['success_rate']}")
    return 0 if report["success_cases"] == report["total_cases"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
