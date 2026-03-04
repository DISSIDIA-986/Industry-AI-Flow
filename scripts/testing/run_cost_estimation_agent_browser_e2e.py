#!/usr/bin/env python3
"""Run Cost Estimation browser automation and capture 5 demo screenshots."""

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
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "temp"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:3001"

LOGIN_EMAIL_SELECTOR = 'input[type="email"]'
LOGIN_PASSWORD_SELECTOR = 'input[type="password"]'
LOGIN_BUTTON_SELECTOR = 'button:has-text("Log in")'
LOGOUT_BUTTON_SELECTOR = 'button:has-text("Log out")'
PREDICT_BUTTON_SELECTOR = 'button:has-text("Predict Cost")'
PREDICTING_BUTTON_SELECTOR = 'button:has-text("Predicting...")'
ADD_BATCH_BUTTON_SELECTOR = 'button:has-text("Add Current Project To Batch")'
RUN_BATCH_BUTTON_SELECTOR = 'button:has-text("Run Batch")'
RUNNING_BATCH_BUTTON_SELECTOR = 'button:has-text("Running Batch...")'
CLEAR_QUEUE_BUTTON_SELECTOR = 'button:has-text("Clear Queue")'
ERROR_SELECTOR = "p.error-text"

FIELD_LABELS: Dict[str, str] = {
    "project_type": "Project Type",
    "location": "Location",
    "sqft": "sqft",
    "floors": "floors",
    "num_units": "num_units",
    "planned_duration_weeks": "planned_duration_weeks",
    "estimated_cost_cad": "estimated_cost_cad",
    "contractor_rating": "contractor_rating",
    "complexity_score": "complexity_score",
    "team_experience_years": "team_experience_years",
    "num_change_orders": "num_change_orders",
    "weather_risk_factor": "weather_risk_factor",
    "material_volatility": "material_volatility",
    "num_subcontractors": "num_subcontractors",
    "budget_pressure": "budget_pressure",
    "risk_score": "risk_score",
    "risk_score_original": "risk_score_original",
}

BASE_PROJECT: Dict[str, Any] = {
    "project_type": "commercial_office",
    "location": "Toronto",
    "sqft": 185000,
    "floors": 18,
    "num_units": 1,
    "planned_duration_weeks": 78,
    "estimated_cost_cad": 72000000,
    "contractor_rating": 4.2,
    "complexity_score": 7,
    "team_experience_years": 11,
    "num_change_orders": 5,
    "weather_risk_factor": 0.32,
    "material_volatility": 0.44,
    "num_subcontractors": 16,
    "budget_pressure": 0.58,
    "risk_score": 6.8,
    "risk_score_original": 6.3,
}


@dataclass(frozen=True)
class Case:
    case_id: str
    question: str
    mode: str  # single | batch
    confidence: float
    project: Dict[str, Any] | None = None
    batch_projects: List[Dict[str, Any]] | None = None


def _extract_last_int(text: str) -> int:
    values = re.findall(r"-?\d+", text or "")
    if not values:
        return 0
    return int(values[-1])


def _parse_agent_json_output(raw_output: str) -> Any:
    text = (raw_output or "").strip()
    if not text:
        return None

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


def _run_eval(js: str, timeout: int = 25) -> tuple[bool, str]:
    encoded = base64.b64encode(js.encode("utf-8")).decode("ascii")
    return _run_agent_browser(["eval", "-b", encoded], timeout=timeout)


def _count(selector: str) -> int:
    ok, output = _run_agent_browser(["get", "count", selector], timeout=20)
    if not ok:
        return -1
    return _extract_last_int(output)


def _open_cost_page(frontend_url: str) -> None:
    cost_url = frontend_url.rstrip("/") + "/cost-estimation"
    open_ok, open_out = _run_agent_browser(["open", cost_url], timeout=45)
    if not open_ok:
        raise RuntimeError(f"failed_to_open_cost_page: {open_out}")

    wait_ok, wait_out = _run_agent_browser(["wait", "--load", "networkidle"], timeout=45)
    if not wait_ok:
        _run_agent_browser(["wait", "1500"], timeout=10)
        if "timeout" in (wait_out or "").lower():
            pass


def _ensure_logged_in(frontend_url: str, email: str, password: str) -> None:
    _open_cost_page(frontend_url)

    if _count(LOGOUT_BUTTON_SELECTOR) > 0 and _count(PREDICT_BUTTON_SELECTOR) > 0:
        return

    if _count(LOGIN_EMAIL_SELECTOR) > 0 and _count(LOGIN_BUTTON_SELECTOR) > 0:
        _run_agent_browser(["fill", LOGIN_EMAIL_SELECTOR, email], timeout=20)
        _run_agent_browser(["fill", LOGIN_PASSWORD_SELECTOR, password], timeout=20)
        click_ok, click_out = _run_agent_browser(["click", LOGIN_BUTTON_SELECTOR], timeout=25)
        if not click_ok:
            raise RuntimeError(f"failed_to_click_login_button: {click_out}")
        _run_agent_browser(["wait", "--load", "networkidle"], timeout=45)
        _run_agent_browser(["wait", "1800"], timeout=10)
        _open_cost_page(frontend_url)

    if _count(PREDICT_BUTTON_SELECTOR) <= 0:
        raise RuntimeError("cost_estimation_page_not_ready_after_login")


def _set_form_values(project: Dict[str, Any], confidence: float) -> tuple[bool, str]:
    tag_payload = {"field_labels": FIELD_LABELS}
    tag_payload_json = json.dumps(tag_payload, ensure_ascii=False)
    tag_js = f"""
(() => {{
  const payload = {tag_payload_json};
  const labels = Array.from(document.querySelectorAll('label.field-group'));

  function readLabelName(node) {{
    const textNode = Array.from(node.childNodes || []).find(
      (item) => item && item.nodeType === Node.TEXT_NODE && String(item.textContent || '').trim()
    );
    if (textNode) {{
      return String(textNode.textContent || '').trim();
    }}
    const fullText = String(node.textContent || '').trim();
    return fullText.split('\\n')[0].trim();
  }}

  for (const [field, labelText] of Object.entries(payload.field_labels || {{}})) {{
    const label = labels.find((node) => readLabelName(node) === labelText);
    if (!label) {{
      return JSON.stringify({{ ok: false, error: `label_not_found:${{field}}:${{labelText}}` }});
    }}
    const input = label.querySelector('input');
    if (!input) {{
      return JSON.stringify({{ ok: false, error: `input_not_found:${{field}}` }});
    }}
    input.setAttribute('data-qa-field', field);
  }}
  return JSON.stringify({{ ok: true }});
}})()
"""
    tag_ok, tag_out = _run_eval(tag_js, timeout=20)
    if not tag_ok:
        return False, f"tag_form_fields_failed:{tag_out[:220]}"
    tag_parsed = _parse_agent_json_output(tag_out)
    if not isinstance(tag_parsed, dict) or not tag_parsed.get("ok"):
        return False, f"tag_form_fields_invalid:{tag_out[:220]}"

    ordered_fields = list(FIELD_LABELS.keys())
    for field in ordered_fields:
        if field not in project:
            continue
        selector = f'input[data-qa-field="{field}"]'
        fill_ok, fill_out = _run_agent_browser(
            ["fill", selector, str(project[field])],
            timeout=20,
        )
        if not fill_ok:
            return False, f"fill_failed:{field}:{fill_out[:220]}"

    slider_js = f"""
(() => {{
  const slider = document.querySelector('input[type="range"]');
  if (!slider) {{
    return JSON.stringify({{ ok: false, error: 'confidence_slider_not_found' }});
  }}
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype,
    'value'
  )?.set;
  if (!setter) {{
    return JSON.stringify({{ ok: false, error: 'slider_setter_unavailable' }});
  }}
  setter.call(slider, String({confidence}));
  slider.dispatchEvent(new Event('input', {{ bubbles: true }}));
  slider.dispatchEvent(new Event('change', {{ bubbles: true }}));
  return JSON.stringify({{ ok: true, confidence: slider.value }});
}})()
"""
    slider_ok, slider_out = _run_eval(slider_js, timeout=20)
    if not slider_ok:
        return False, f"set_confidence_failed:{slider_out[:220]}"
    slider_parsed = _parse_agent_json_output(slider_out)
    if not isinstance(slider_parsed, dict) or not slider_parsed.get("ok"):
        return False, f"set_confidence_invalid:{slider_out[:220]}"

    verify_payload = {"field_labels": FIELD_LABELS}
    verify_json = json.dumps(verify_payload, ensure_ascii=False)
    verify_js = f"""
(() => {{
  const payload = {verify_json};
  const labels = Array.from(document.querySelectorAll('label.field-group'));
  function findInputByLabelText(labelText) {{
    const label = labels.find((node) => {{
      const text = String(node.textContent || '').trim();
      return text.startsWith(labelText);
    }});
    return label ? label.querySelector('input') : null;
  }}
  const check = {{}};
  for (const [field, labelText] of Object.entries(payload.field_labels || {{}})) {{
    const input = findInputByLabelText(labelText);
    check[field] = input ? input.value : null;
  }}
  const slider = document.querySelector('input[type="range"]');
  check.confidence = slider ? slider.value : null;
  return JSON.stringify({{ ok: true, check }});
}})()
"""
    verify_ok, verify_out = _run_eval(verify_js, timeout=20)
    if not verify_ok:
        return False, f"verify_form_failed:{verify_out[:220]}"
    verify_parsed = _parse_agent_json_output(verify_out)
    if not isinstance(verify_parsed, dict) or not verify_parsed.get("ok"):
        return False, f"verify_form_invalid:{verify_out[:220]}"

    return True, json.dumps(verify_parsed.get("check", {}), ensure_ascii=False)[:320]


def _wait_for_single_result(max_wait_seconds: int = 120) -> tuple[bool, str]:
    deadline = time.time() + max_wait_seconds
    last_state = "unknown"

    while time.time() < deadline:
        if _count(PREDICTING_BUTTON_SELECTOR) > 0:
            last_state = "predicting"
            _run_agent_browser(["wait", "1000"], timeout=10)
            continue

        js = r"""
(() => {
  const errorNode = document.querySelector('p.error-text');
  const resultGrid = document.querySelector('.result-grid');
  const hasCards = !!(resultGrid && resultGrid.querySelector('.result-value'));
  return JSON.stringify({
    has_error: !!errorNode,
    error_text: errorNode ? String(errorNode.textContent || '').trim() : '',
    has_result: hasCards,
  });
})()
"""
        ok, out = _run_eval(js, timeout=15)
        if not ok:
            _run_agent_browser(["wait", "700"], timeout=10)
            continue
        parsed = _parse_agent_json_output(out)
        if isinstance(parsed, dict):
            if parsed.get("has_error"):
                return False, f"error_visible:{parsed.get('error_text')}"
            if parsed.get("has_result"):
                return True, "result_ready"
        last_state = "waiting_result"
        _run_agent_browser(["wait", "900"], timeout=10)

    return False, last_state


def _wait_for_batch_result(max_wait_seconds: int = 120) -> tuple[bool, str]:
    deadline = time.time() + max_wait_seconds
    last_state = "unknown"

    while time.time() < deadline:
        if _count(RUNNING_BATCH_BUTTON_SELECTOR) > 0:
            last_state = "running_batch"
            _run_agent_browser(["wait", "1000"], timeout=10)
            continue

        js = r"""
(() => {
  const errorNode = document.querySelector('p.error-text');
  const tableRows = Array.from(document.querySelectorAll('tbody tr'));
  return JSON.stringify({
    has_error: !!errorNode,
    error_text: errorNode ? String(errorNode.textContent || '').trim() : '',
    row_count: tableRows.length,
  });
})()
"""
        ok, out = _run_eval(js, timeout=15)
        if not ok:
            _run_agent_browser(["wait", "700"], timeout=10)
            continue
        parsed = _parse_agent_json_output(out)
        if isinstance(parsed, dict):
            if parsed.get("has_error"):
                return False, f"error_visible:{parsed.get('error_text')}"
            if int(parsed.get("row_count") or 0) > 0:
                return True, f"rows={parsed.get('row_count')}"
        last_state = "waiting_batch_rows"
        _run_agent_browser(["wait", "900"], timeout=10)

    return False, last_state


def _read_single_payload() -> Dict[str, Any]:
    js = r"""
(() => {
  const errorNode = document.querySelector('p.error-text');
  const cards = Array.from(document.querySelectorAll('.result-grid > div'));
  const values = {};
  for (const card of cards) {
    const label = card.querySelector('.result-label');
    const value = card.querySelector('.result-value');
    if (!label || !value) continue;
    values[String(label.textContent || '').trim()] = String(value.textContent || '').trim();
  }
  return JSON.stringify({
    ok: true,
    error_text: errorNode ? String(errorNode.textContent || '').trim() : '',
    values,
  });
})()
"""
    ok, out = _run_eval(js, timeout=15)
    if not ok:
        return {"ok": False, "error": out}
    parsed = _parse_agent_json_output(out)
    if isinstance(parsed, dict):
        return parsed
    return {"ok": False, "error": "single_payload_parse_failed", "raw": out.strip()}


def _read_batch_payload() -> Dict[str, Any]:
    js = r"""
(() => {
  const errorNode = document.querySelector('p.error-text');
  const heading = Array.from(document.querySelectorAll('h3'))
    .map((node) => String(node.textContent || '').trim())
    .find((text) => text.startsWith('Batch Prediction Queue')) || '';
  const rows = Array.from(document.querySelectorAll('tbody tr')).map((row) => {
    const cells = Array.from(row.querySelectorAll('td')).map((cell) =>
      String(cell.textContent || '').trim()
    );
    return cells;
  });
  return JSON.stringify({
    ok: true,
    error_text: errorNode ? String(errorNode.textContent || '').trim() : '',
    queue_heading: heading,
    row_count: rows.length,
    rows: rows.slice(0, 5),
  });
})()
"""
    ok, out = _run_eval(js, timeout=15)
    if not ok:
        return {"ok": False, "error": out}
    parsed = _parse_agent_json_output(out)
    if isinstance(parsed, dict):
        return parsed
    return {"ok": False, "error": "batch_payload_parse_failed", "raw": out.strip()}


def _build_single_summary(payload: Dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return "single_result_unavailable"
    if payload.get("error_text"):
        return f"ui_error={str(payload.get('error_text'))[:220]}"
    values = payload.get("values")
    if not isinstance(values, dict) or not values:
        return "no_single_result_cards"
    cost = str(values.get("Predicted Actual Cost") or "")
    overrun = str(values.get("Predicted Overrun") or "")
    interval = str(values.get("Prediction Interval") or "")
    return f"cost={cost}; overrun={overrun}; interval={interval}"


def _build_batch_summary(payload: Dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return "batch_result_unavailable"
    if payload.get("error_text"):
        return f"ui_error={str(payload.get('error_text'))[:220]}"
    heading = str(payload.get("queue_heading") or "")
    row_count = int(payload.get("row_count") or 0)
    rows = payload.get("rows")
    first_row = rows[0] if isinstance(rows, list) and rows else []
    return f"{heading}; rows={row_count}; first_row={first_row}"


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
  banner.style.border = '2px solid #0f766e';
  banner.style.borderRadius = '10px';
  banner.style.padding = '12px 14px';
  banner.style.margin = '10px 0 14px 0';
  banner.style.boxShadow = '0 6px 16px rgba(15, 23, 42, 0.12)';

  const title = document.createElement('div');
  title.style.fontWeight = '700';
  title.style.fontSize = '14px';
  title.style.marginBottom = '8px';
  title.textContent = `Cost Estimation Demo - ${{payload.case_id}}`;
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
  document.body.style.zoom = '0.86';
  window.scrollTo({{ top: 0, left: 0, behavior: 'instant' }});
  return 'ok';
}})()
"""
    return _run_eval(js, timeout=20)


def _single_case_flow(case: Case) -> Dict[str, Any]:
    if not isinstance(case.project, dict):
        return {"success": False, "error": "single_case_missing_project"}

    set_ok, set_out = _set_form_values(case.project, case.confidence)
    if not set_ok:
        return {"success": False, "error": f"set_form_failed:{set_out}"}

    click_ok, click_out = _run_agent_browser(["click", PREDICT_BUTTON_SELECTOR], timeout=25)
    if not click_ok:
        return {"success": False, "error": f"click_predict_failed:{click_out}"}

    wait_ok, wait_state = _wait_for_single_result(max_wait_seconds=120)
    payload = _read_single_payload()
    summary = _build_single_summary(payload)

    success = bool(wait_ok and isinstance(payload.get("values"), dict) and payload.get("values"))
    return {
        "success": success,
        "set_output": set_out,
        "click_output": click_out[:220],
        "wait_ok": wait_ok,
        "wait_state": wait_state,
        "payload": payload,
        "summary": summary,
    }


def _batch_case_flow(case: Case) -> Dict[str, Any]:
    if not case.batch_projects:
        return {"success": False, "error": "batch_case_missing_projects"}

    _run_agent_browser(["click", CLEAR_QUEUE_BUTTON_SELECTOR], timeout=20)
    _run_agent_browser(["wait", "500"], timeout=10)

    add_steps: List[str] = []
    for idx, project in enumerate(case.batch_projects, start=1):
        set_ok, set_out = _set_form_values(project, case.confidence)
        if not set_ok:
            return {"success": False, "error": f"set_form_failed_at_{idx}:{set_out}"}
        add_ok, add_out = _run_agent_browser(["click", ADD_BATCH_BUTTON_SELECTOR], timeout=20)
        if not add_ok:
            return {"success": False, "error": f"add_to_batch_failed_at_{idx}:{add_out}"}
        add_steps.append(f"item_{idx}:{set_out[:120]}")
        _run_agent_browser(["wait", "350"], timeout=10)

    run_ok, run_out = _run_agent_browser(["click", RUN_BATCH_BUTTON_SELECTOR], timeout=20)
    if not run_ok:
        return {"success": False, "error": f"click_run_batch_failed:{run_out}"}

    wait_ok, wait_state = _wait_for_batch_result(max_wait_seconds=120)
    payload = _read_batch_payload()
    summary = _build_batch_summary(payload)
    row_count = int(payload.get("row_count") or 0) if isinstance(payload, dict) else 0
    success = bool(wait_ok and row_count >= len(case.batch_projects))

    return {
        "success": success,
        "set_output": " | ".join(add_steps),
        "click_output": run_out[:220],
        "wait_ok": wait_ok,
        "wait_state": wait_state,
        "payload": payload,
        "summary": summary,
    }


def _validate_clear_queue_behavior() -> Dict[str, Any]:
    _run_agent_browser(["click", CLEAR_QUEUE_BUTTON_SELECTOR], timeout=20)
    _run_agent_browser(["wait", "700"], timeout=10)
    js = r"""
(() => {
  const heading = Array.from(document.querySelectorAll('h3'))
    .map((node) => String(node.textContent || '').trim())
    .find((text) => text.startsWith('Batch Prediction Queue')) || '';
  const rows = Array.from(document.querySelectorAll('tbody tr')).length;
  const hasHint = String(document.body.innerText || '').includes(
    'Add projects from the form above to run batch mode.'
  );
  return JSON.stringify({
    heading,
    rows,
    has_hint: hasHint,
  });
})()
"""
    ok, out = _run_eval(js, timeout=15)
    if not ok:
        return {"ok": False, "error": out}
    parsed = _parse_agent_json_output(out)
    if not isinstance(parsed, dict):
        return {"ok": False, "error": f"invalid_clear_queue_payload:{out[:200]}"}

    heading = str(parsed.get("heading") or "")
    rows = int(parsed.get("rows") or 0)
    has_hint = bool(parsed.get("has_hint"))
    ok_state = ("(0)" in heading) and rows == 0 and has_hint
    return {
        "ok": ok_state,
        "heading": heading,
        "rows": rows,
        "has_hint": has_hint,
    }


def _run_case(case: Case, screenshot_path: Path) -> Dict[str, Any]:
    if case.mode == "single":
        flow_result = _single_case_flow(case)
    elif case.mode == "batch":
        flow_result = _batch_case_flow(case)
    else:
        flow_result = {"success": False, "error": f"unsupported_mode:{case.mode}"}

    summary = str(flow_result.get("summary") or flow_result.get("error") or "").strip()
    _inject_qa_banner(question=case.question, answer=summary, case_id=case.case_id)
    _run_agent_browser(["wait", "650"], timeout=10)

    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    shot_ok, shot_out = _run_agent_browser(
        ["screenshot", str(screenshot_path), "--full"],
        timeout=50,
    )
    flow_result["screenshot_output"] = shot_out[:220]
    flow_result["screenshot_path"] = str(screenshot_path) if shot_ok else ""
    flow_result["success"] = bool(flow_result.get("success") and shot_ok)
    flow_result["summary"] = summary
    return flow_result


def _case_project(overrides: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(BASE_PROJECT)
    payload.update(overrides)
    return payload


def run_suite(
    *,
    frontend_url: str,
    login_email: str,
    login_password: str,
    output_root: Path,
) -> Dict[str, Any]:
    if shutil.which("agent-browser") is None:
        raise RuntimeError("agent-browser CLI is not installed or not in PATH")

    cases = [
        Case(
            case_id="01_office_baseline_single",
            question="Predict baseline Toronto commercial office project cost and overrun.",
            mode="single",
            confidence=0.90,
            project=_case_project({}),
        ),
        Case(
            case_id="02_residential_multi_family_single",
            question="Estimate Vancouver residential multi-family scenario with medium complexity.",
            mode="single",
            confidence=0.90,
            project=_case_project(
                {
                    "project_type": "residential_multi_family",
                    "location": "Vancouver",
                    "sqft": 98000,
                    "floors": 24,
                    "num_units": 210,
                    "planned_duration_weeks": 92,
                    "estimated_cost_cad": 51000000,
                    "complexity_score": 8,
                    "risk_score": 7.2,
                    "risk_score_original": 6.7,
                }
            ),
        ),
        Case(
            case_id="03_hospital_high_risk_single",
            question="Estimate Montreal hospital project under high volatility and schedule pressure.",
            mode="single",
            confidence=0.95,
            project=_case_project(
                {
                    "project_type": "healthcare_hospital",
                    "location": "Montreal",
                    "sqft": 240000,
                    "floors": 14,
                    "num_units": 1,
                    "planned_duration_weeks": 130,
                    "estimated_cost_cad": 165000000,
                    "complexity_score": 9,
                    "num_change_orders": 12,
                    "weather_risk_factor": 0.61,
                    "material_volatility": 0.72,
                    "budget_pressure": 0.76,
                    "risk_score": 8.8,
                    "risk_score_original": 8.3,
                }
            ),
        ),
        Case(
            case_id="04_industrial_low_risk_single",
            question="Estimate Calgary industrial warehouse scenario with lower risk profile.",
            mode="single",
            confidence=0.80,
            project=_case_project(
                {
                    "project_type": "industrial_warehouse",
                    "location": "Calgary",
                    "sqft": 210000,
                    "floors": 3,
                    "num_units": 1,
                    "planned_duration_weeks": 64,
                    "estimated_cost_cad": 68000000,
                    "contractor_rating": 4.6,
                    "complexity_score": 5,
                    "num_change_orders": 2,
                    "weather_risk_factor": 0.21,
                    "material_volatility": 0.27,
                    "budget_pressure": 0.35,
                    "risk_score": 4.6,
                    "risk_score_original": 4.4,
                }
            ),
        ),
        Case(
            case_id="05_batch_three_projects",
            question="Run batch estimation for office, education, and bridge projects and compare outputs.",
            mode="batch",
            confidence=0.90,
            batch_projects=[
                _case_project(
                    {
                        "project_type": "commercial_office",
                        "location": "Toronto",
                        "sqft": 140000,
                        "floors": 20,
                        "estimated_cost_cad": 76000000,
                        "risk_score": 6.5,
                        "risk_score_original": 6.1,
                    }
                ),
                _case_project(
                    {
                        "project_type": "education_school",
                        "location": "Ottawa",
                        "sqft": 85000,
                        "floors": 6,
                        "estimated_cost_cad": 39000000,
                        "complexity_score": 6,
                        "risk_score": 5.4,
                        "risk_score_original": 5.0,
                    }
                ),
                _case_project(
                    {
                        "project_type": "infrastructure_bridge",
                        "location": "Vancouver",
                        "sqft": 60000,
                        "floors": 2,
                        "estimated_cost_cad": 91000000,
                        "complexity_score": 9,
                        "weather_risk_factor": 0.58,
                        "material_volatility": 0.66,
                        "risk_score": 8.1,
                        "risk_score_original": 7.6,
                    }
                ),
            ],
        ),
    ]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = output_root / f"cost_estimation_agent_test_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    _ensure_logged_in(frontend_url=frontend_url, email=login_email, password=login_password)

    case_results: List[Dict[str, Any]] = []
    started = time.perf_counter()
    for index, case in enumerate(cases, start=1):
        _open_cost_page(frontend_url)
        screenshot_path = out_dir / f"{index:02d}_{case.case_id}.png"
        result = _run_case(case=case, screenshot_path=screenshot_path)
        result.update(
            {
                "case_id": case.case_id,
                "question": case.question,
                "mode": case.mode,
                "confidence": case.confidence,
            }
        )
        case_results.append(result)

    clear_queue_validation = _validate_clear_queue_behavior()
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
        "clear_queue_validation": clear_queue_validation,
        "cases": case_results,
    }

    report_path = out_dir / "cost_estimation_agent_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Cost Estimation Screenshot Case Index",
        "",
        f"- Generated at (UTC): {report['generated_at_utc']}",
        f"- Success: {success_count}/{len(case_results)}",
        f"- Clear queue validation: {clear_queue_validation}",
        "",
    ]
    for row in case_results:
        lines.append(f"## {row.get('case_id')}")
        lines.append(f"- Mode: {row.get('mode')}")
        lines.append(f"- Question: {row.get('question')}")
        lines.append(f"- Success: {row.get('success')}")
        lines.append(f"- Screenshot: {row.get('screenshot_path')}")
        lines.append(f"- Summary: {row.get('summary')}")
        lines.append("")

    (out_dir / "CASE_INDEX.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Cost Estimation browser test and capture 5 screenshots in temp.",
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
    print("Cost Estimation agent-browser run complete.")
    print(f"output_dir={report['output_dir']}")
    print(f"success={report['success_cases']}/{report['total_cases']}")
    print(f"success_rate={report['success_rate']}")
    print(f"clear_queue_validation={report['clear_queue_validation']}")
    return 0 if report["success_cases"] == report["total_cases"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
