#!/usr/bin/env python3
"""
Data Analysis Browser E2E Test (agent-browser)

End-to-end browser automation test for the Dynamic Data Analysis pipeline:
  Upload public dataset → Enable "Include Visualization" toggle →
  Run Analysis (cloud LLM code gen + Docker sandbox + viz) → Validate results + capture screenshots.

Uses agent-browser CLI to drive the /data-analysis frontend page.

Requires:
  - agent-browser CLI in PATH
  - Frontend running on :3001
  - Backend running on :8000
  - Docker running with python:3.12-slim pulled
  - Valid cloud LLM API key (Zhipu or Gemini)
  - CODE_EXECUTION_PROVIDER=docker
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths & defaults
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_ROOT / "test_resources" / "datasets" / "e2e_public"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "temp"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:3123"

LOGIN_EMAIL_SELECTOR = 'input[type="email"]'
LOGIN_PASSWORD_SELECTOR = 'input[type="password"]'
LOGIN_BUTTON_SELECTOR = 'button:has-text("Log in")'
RUN_ANALYSIS_BUTTON_SELECTOR = '[data-testid="run-analysis-btn"]'
INCLUDE_VIZ_CHECKBOX_SELECTOR = '[data-testid="include-viz-toggle"]'
UPLOAD_BUTTON_SELECTOR = 'button:has-text("1) Upload Data")'
PROCESSING_BUTTON_SELECTOR = 'button:has-text("Analyzing...")'
PIPELINE_VIZ_SELECTOR = '[data-testid="analysis-pipeline-viz"]'
ERROR_SELECTOR = "p.error-text"

# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------
DATASETS: dict[str, dict[str, str]] = {
    "tips": {
        "url": "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv",
        "filename": "tips.csv",
    },
    "titanic": {
        "url": "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv",
        "filename": "titanic.csv",
    },
    "penguins": {
        "url": "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv",
        "filename": "penguins.csv",
    },
    "mpg": {
        "url": "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/mpg.csv",
        "filename": "mpg.csv",
    },
    "airline": {
        "url": "https://raw.githubusercontent.com/jbrownlee/Datasets/master/airline-passengers.csv",
        "filename": "airline-passengers.csv",
    },
}

# ---------------------------------------------------------------------------
# Test cases (subset: one per dataset for browser test, keep it focused)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Case:
    case_id: str
    question: str
    analysis_type: str
    chart_type: str
    dataset_key: str
    description: str = ""


BROWSER_CASES: list[Case] = [
    Case(
        case_id="01_tips_eda",
        question="Show the distribution of tip amounts as a histogram and compute basic statistics",
        analysis_type="eda",
        chart_type="histogram",
        dataset_key="tips",
        description="Tips: EDA histogram",
    ),
    Case(
        case_id="02_titanic_classification",
        question="Train a decision tree classifier to predict Survived and show feature importances as a bar chart",
        analysis_type="eda",
        chart_type="bar",
        dataset_key="titanic",
        description="Titanic: decision tree classification",
    ),
    Case(
        case_id="03_penguins_clustering",
        question="Run K-means clustering with 3 clusters on numeric features and visualize with a scatter plot",
        analysis_type="eda",
        chart_type="scatter",
        dataset_key="penguins",
        description="Penguins: K-means clustering",
    ),
    Case(
        case_id="04_mpg_regression",
        question="Predict mpg using linear regression. Show R-squared, RMSE, and a residual plot",
        analysis_type="regression",
        chart_type="scatter",
        dataset_key="mpg",
        description="MPG: linear regression",
    ),
    Case(
        case_id="05_airline_timeseries",
        question="Plot the time series and calculate a 12-month rolling average",
        analysis_type="eda",
        chart_type="line",
        dataset_key="airline",
        description="Airline: time series rolling avg",
    ),
]


# ---------------------------------------------------------------------------
# agent-browser helpers (reused from existing E2E pattern)
# ---------------------------------------------------------------------------
def _extract_last_int(text: str) -> int:
    values = re.findall(r"-?\d+", text or "")
    return int(values[-1]) if values else 0


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
        except Exception:
            break
    match = re.search(r"\{[\s\S]*\}\s*$", text)
    if match:
        try:
            parsed = json.loads(match.group(0).strip())
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
            command, capture_output=True, text=True, timeout=max(8, int(timeout) + 10)
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 124 and timeout_cmd:
            return False, f"agent-browser timeout after {timeout}s"
        return proc.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"agent-browser timeout after {timeout}s"
    except Exception as exc:
        return False, f"agent-browser error: {exc}"


def _run_eval(js: str, timeout: int = 30) -> tuple[bool, str]:
    encoded = base64.b64encode(js.encode("utf-8")).decode("ascii")
    return _run_agent_browser(["eval", "-b", encoded], timeout=timeout)


def _count(selector: str) -> int:
    ok, output = _run_agent_browser(["get", "count", selector], timeout=20)
    return _extract_last_int(output) if ok else -1


# ---------------------------------------------------------------------------
# Dataset download & staging
# ---------------------------------------------------------------------------
def download_and_stage_datasets() -> dict[str, str]:
    """Download datasets and stage them in a temp dir matching backend upload path.

    Returns {dataset_key: staged_file_path}.
    """
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    tmp_root = Path(os.getenv("TMPDIR", "/tmp")).resolve()
    stage_dir = tmp_root / "luncheon_data_e2e_public"
    stage_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, str] = {}
    for key, info in DATASETS.items():
        local_cache = DATASET_DIR / info["filename"]
        if not local_cache.exists() or local_cache.stat().st_size == 0:
            print(f"  [downloading] {key}: {info['url']}")
            try:
                urllib.request.urlretrieve(info["url"], str(local_cache))
            except Exception as e:
                print(f"    FAILED: {e}")
                continue

        staged = stage_dir / info["filename"]
        shutil.copy2(local_cache, staged)
        paths[key] = str(staged.resolve())
        print(f"  [staged] {key}: {staged}")
    return paths


# ---------------------------------------------------------------------------
# Page navigation & login
# ---------------------------------------------------------------------------
def _open_data_page(frontend_url: str) -> None:
    data_url = frontend_url.rstrip("/") + "/data-analysis"
    ok, out = _run_agent_browser(["open", data_url], timeout=45)
    if not ok:
        raise RuntimeError(f"failed_to_open_data_page: {out}")
    wait_ok, wait_out = _run_agent_browser(
        ["wait", "--load", "networkidle"], timeout=45
    )
    if not wait_ok:
        _run_agent_browser(["wait", "1500"], timeout=10)


def _ensure_logged_in(frontend_url: str, email: str, password: str) -> None:
    _open_data_page(frontend_url)
    if _count(RUN_ANALYSIS_BUTTON_SELECTOR) > 0:
        return
    if _count(LOGIN_EMAIL_SELECTOR) > 0 and _count(LOGIN_BUTTON_SELECTOR) > 0:
        _run_agent_browser(["fill", LOGIN_EMAIL_SELECTOR, email], timeout=20)
        _run_agent_browser(["fill", LOGIN_PASSWORD_SELECTOR, password], timeout=20)
        ok, out = _run_agent_browser(["click", LOGIN_BUTTON_SELECTOR], timeout=25)
        if not ok:
            raise RuntimeError(f"failed_to_click_login: {out}")
        _run_agent_browser(["wait", "--load", "networkidle"], timeout=45)
        _run_agent_browser(["wait", "1800"], timeout=10)
        _open_data_page(frontend_url)
    if _count(RUN_ANALYSIS_BUTTON_SELECTOR) <= 0:
        raise RuntimeError("data_analysis_page_not_ready_after_login")


# ---------------------------------------------------------------------------
# Snapshot refs for form fields
# ---------------------------------------------------------------------------
def _snapshot_refs() -> dict[str, str]:
    ok, out = _run_agent_browser(["snapshot", "-i"], timeout=30)
    if not ok:
        return {}
    refs: dict[str, str] = {}
    patterns = {
        "instruction": r'^\-\s+textbox\s+"Analysis Instruction"\s+\[ref=([^\]]+)\]',
        "analysis_type": r'^\-\s+combobox\s+"Analysis Type"\s+\[ref=([^\]]+)\]',
        "chart_type": r'^\-\s+combobox\s+"Chart Type"\s+\[ref=([^\]]+)\]',
        "run_analysis": r'^\-\s+button\s+".*Run Analysis"\s+\[ref=([^\]]+)\]',
        "include_viz": r'^\-\s+checkbox\s+"Include Visualization"\s+\[ref=([^\]]+)\]',
    }
    for line in (out or "").splitlines():
        for key, pattern in patterns.items():
            if key in refs:
                continue
            m = re.search(pattern, line.strip())
            if m:
                refs[key] = f"@{m.group(1)}"
    return refs


# ---------------------------------------------------------------------------
# Form interaction
# ---------------------------------------------------------------------------
def _set_form_values(
    data_file: str,
    analysis_type: str,
    chart_type: str,
    instruction: str,
    refs: dict[str, str],
) -> tuple[bool, str]:
    # Uploaded Path field removed from UI — file path is pre-filled internally
    instruction_target = (
        refs.get("instruction") or 'label:has-text("Analysis Instruction") input'
    )
    analysis_target = (
        refs.get("analysis_type") or 'label:has-text("Analysis Type") select'
    )
    chart_target = refs.get("chart_type") or 'label:has-text("Chart Type") select'

    ok, out = _run_agent_browser(
        ["fill", instruction_target, instruction], timeout=20
    )
    if not ok:
        return False, f"fill_instruction_failed: {out}"

    ok, out = _run_agent_browser(
        ["select", analysis_target, analysis_type], timeout=20
    )
    if not ok:
        return False, f"select_analysis_type_failed: {out}"

    ok, out = _run_agent_browser(["select", chart_target, chart_type], timeout=20)
    if not ok:
        return False, f"select_chart_type_failed: {out}"

    # Verify form values (Uploaded Path field removed — only check analysis/chart type)
    verify_js = r"""
(() => {
  const labels = Array.from(document.querySelectorAll('label'));
  let instrInput = null, analysisSelect = null, chartSelect = null;
  for (const label of labels) {
    const t = (label.textContent || '').trim();
    if (!instrInput && t.includes('Analysis Instruction')) instrInput = label.querySelector('input');
    if (!analysisSelect && t.includes('Analysis Type')) analysisSelect = label.querySelector('select');
    if (!chartSelect && t.includes('Chart Type')) chartSelect = label.querySelector('select');
  }
  return JSON.stringify({
    instruction: instrInput ? instrInput.value : null,
    analysis_type: analysisSelect ? analysisSelect.value : null,
    chart_type: chartSelect ? chartSelect.value : null,
  });
})()
"""
    vok, vout = _run_eval(verify_js, timeout=20)
    if not vok:
        return False, f"verify_failed: {vout}"

    parsed = _parse_agent_json_output(vout)
    if isinstance(parsed, dict):
        if (
            parsed.get("analysis_type") != analysis_type
            or parsed.get("chart_type") != chart_type
        ):
            return False, f"form_mismatch: {parsed}"

    return True, "form_set_ok"


# ---------------------------------------------------------------------------
# Wait for processing completion
# ---------------------------------------------------------------------------
def _wait_for_complete(max_wait: int = 180) -> tuple[bool, str]:
    deadline = time.time() + max_wait
    last_state = "unknown"
    while time.time() < deadline:
        if _count(PROCESSING_BUTTON_SELECTOR) > 0:
            last_state = "processing"
            _run_agent_browser(["wait", "1600"], timeout=10)
            continue
        if _count(UPLOAD_BUTTON_SELECTOR) > 0:
            return True, "idle"
        if _count(ERROR_SELECTOR) > 0:
            return True, "error_visible"
        _run_agent_browser(["wait", "1200"], timeout=10)
    return False, last_state


# ---------------------------------------------------------------------------
# Read result payloads from DOM
# ---------------------------------------------------------------------------
def _read_result_payload() -> dict[str, Any]:
    js = r"""
(() => {
  const payload = { ok: true, result_text: '', error_text: '', parse_error: '' };
  // New layout: JSON is inside <details> with title "Full Response (JSON)"
  const details = Array.from(document.querySelectorAll('.result-stack details'));
  for (const d of details) {
    const summary = d.querySelector('summary');
    if (summary && summary.textContent.includes('Full Response')) {
      d.open = true;
      const code = d.querySelector('code') || d.querySelector('pre');
      payload.result_text = code ? (code.textContent || '').trim() : '';
      break;
    }
  }
  // Fallback: legacy .result-grid layout
  if (!payload.result_text) {
    const sections = Array.from(document.querySelectorAll('.result-grid > div'));
    const section = sections[0];
    if (section) {
      const pre = section.querySelector('pre');
      payload.result_text = pre ? (pre.textContent || '').trim() : '';
    }
  }
  const err = document.querySelector('p.error-text');
  if (err) payload.error_text = (err.textContent || '').trim();
  if (!payload.result_text || payload.result_text.startsWith('No analysis result yet'))
    return JSON.stringify(payload);
  try { payload.result_json = JSON.parse(payload.result_text); }
  catch (e) { payload.parse_error = String(e); }
  return JSON.stringify(payload);
})()
"""
    ok, out = _run_eval(js, timeout=20)
    if not ok:
        return {"ok": False, "error": out}
    parsed = _parse_agent_json_output(out)
    return parsed if isinstance(parsed, dict) else {"ok": False, "raw": out}


def _read_grid_state() -> dict[str, Any]:
    """Count EDA chart tiles and detect model-comparison section.

    Added for Plan-as-JSON multi-chart grid rollout. Returns
    ``{chart_count, ok_count, failed_count, has_model_section, chart_types}``
    so the suite can assert multi-chart rendering instead of the legacy
    single-image check.
    """
    js = r"""
(() => {
  const grid = document.querySelector('[data-testid="eda-chart-grid"]');
  const tiles = grid ? Array.from(grid.querySelectorAll('[data-testid^="eda-chart-"]')) : [];
  const types = tiles.map(t => t.getAttribute('data-chart-type') || '').filter(Boolean);
  const statuses = tiles.map(t => t.getAttribute('data-chart-status') || 'unknown');
  const okCount = statuses.filter(s => s === 'ok').length;
  const failedCount = statuses.filter(s => s === 'failed').length;
  const model = document.querySelector('[data-testid="model-comparison-section"]');
  return JSON.stringify({
    chart_count: tiles.length,
    ok_count: okCount,
    failed_count: failedCount,
    has_model_section: !!model,
    chart_types: types,
  });
})()
"""
    ok, out = _run_eval(js, timeout=15)
    if not ok:
        return {"chart_count": 0, "error": out}
    parsed = _parse_agent_json_output(out)
    return parsed if isinstance(parsed, dict) else {"chart_count": 0, "raw": out}


def _read_viz_payload() -> dict[str, Any]:
    js = r"""
(() => {
  const payload = { ok: true, result_text: '', error_text: '', parse_error: '' };
  // New layout: JSON is inside <details> with title "Visualization Response (JSON)"
  const details = Array.from(document.querySelectorAll('.result-stack details'));
  for (const d of details) {
    const summary = d.querySelector('summary');
    if (summary && summary.textContent.includes('Visualization Response')) {
      d.open = true;
      const code = d.querySelector('code') || d.querySelector('pre');
      payload.result_text = code ? (code.textContent || '').trim() : '';
      break;
    }
  }
  // Fallback: legacy .result-grid layout
  if (!payload.result_text) {
    const sections = Array.from(document.querySelectorAll('.result-grid > div'));
    const section = sections[1];
    if (section) {
      const pre = section.querySelector('pre');
      payload.result_text = pre ? (pre.textContent || '').trim() : '';
    }
  }
  const err = document.querySelector('p.error-text');
  if (err) payload.error_text = (err.textContent || '').trim();
  if (!payload.result_text || payload.result_text.startsWith('No visualization result yet'))
    return JSON.stringify(payload);
  try { payload.result_json = JSON.parse(payload.result_text); }
  catch (e) { payload.parse_error = String(e); }
  return JSON.stringify(payload);
})()
"""
    ok, out = _run_eval(js, timeout=20)
    if not ok:
        return {"ok": False, "error": out}
    parsed = _parse_agent_json_output(out)
    return parsed if isinstance(parsed, dict) else {"ok": False, "raw": out}


# ---------------------------------------------------------------------------
# Summary builders
# ---------------------------------------------------------------------------
def _build_analysis_summary(payload: dict[str, Any]) -> str:
    rj = payload.get("result_json")
    if isinstance(rj, dict):
        success = rj.get("success")
        atype = rj.get("analysis_type")
        cg = rj.get("code_generation", {})
        mode = cg.get("mode", "") if isinstance(cg, dict) else ""
        lp = rj.get("llm_input_policy", {})
        raw_sent = lp.get("raw_data_sent_to_llm") if isinstance(lp, dict) else None
        answer = str(rj.get("answer") or "")[:150]
        error = str(rj.get("error") or "")
        if error:
            return f"success={success}; type={atype}; mode={mode}; raw_sent={raw_sent}; error={error[:200]}"
        return f"success={success}; type={atype}; mode={mode}; raw_sent={raw_sent}; answer={answer}"
    err = payload.get("error_text", "")
    if err:
        return f"ui_error={err[:300]}"
    return str(payload.get("result_text", ""))[:300] or "No result"


def _build_viz_summary(payload: dict[str, Any]) -> str:
    rj = payload.get("result_json")
    if isinstance(rj, dict):
        success = rj.get("success")
        ci = rj.get("chart_info", {})
        ct = ci.get("chart_type") if isinstance(ci, dict) else rj.get("chart_type")
        fp = str(rj.get("file_path") or "")
        if not fp and isinstance(ci, dict):
            fp = str(ci.get("output_file") or "")
        cg = rj.get("code_generation", {})
        mode = cg.get("mode", "") if isinstance(cg, dict) else ""
        lp = rj.get("llm_input_policy", {})
        raw_sent = lp.get("raw_data_sent_to_llm") if isinstance(lp, dict) else None
        return f"success={success}; chart={ct}; mode={mode}; raw_sent={raw_sent}; file={fp}"
    err = payload.get("error_text", "")
    if err:
        return f"ui_error={err[:300]}"
    return str(payload.get("result_text", ""))[:300] or "No viz result"


# ---------------------------------------------------------------------------
# Inject QA banner for screenshot
# ---------------------------------------------------------------------------
def _inject_banner(case_id: str, question: str, answer: str) -> None:
    payload = json.dumps({"case_id": case_id, "question": question, "answer": answer})
    js = f"""
(() => {{
  const p = {payload};
  const old = document.getElementById('qa-capture-banner');
  if (old) old.remove();
  const b = document.createElement('section');
  b.id = 'qa-capture-banner';
  b.style.cssText = 'position:sticky;top:0;z-index:9999;background:#fff;border:2px solid #1e40af;border-radius:10px;padding:12px;margin:10px 0 14px;box-shadow:0 6px 16px rgba(15,23,42,.12)';
  b.innerHTML = '<div style="font-weight:700;font-size:14px;margin-bottom:8px">Data Analysis E2E - ' + p.case_id + '</div>'
    + '<div style="font-size:13px;line-height:1.5;margin-bottom:8px"><strong>Prompt:</strong> ' + p.question + '</div>'
    + '<div style="font-size:13px;line-height:1.5"><strong>Result:</strong> ' + p.answer + '</div>';
  const panel = document.querySelector('.panel-card');
  if (panel && panel.parentElement) panel.parentElement.insertBefore(b, panel);
  document.body.style.zoom = '0.85';
  window.scrollTo({{top:0,left:0,behavior:'instant'}});
  return 'ok';
}})()
"""
    _run_eval(js, timeout=20)


# ---------------------------------------------------------------------------
# Run single case
# ---------------------------------------------------------------------------
def _run_case(
    case: Case, data_files: dict[str, str], screenshot_path: Path
) -> dict[str, Any]:
    data_file = data_files[case.dataset_key]
    result: dict[str, Any] = {
        "case_id": case.case_id,
        "description": case.description,
        "dataset_key": case.dataset_key,
        "question": case.question,
        "analysis_type": case.analysis_type,
        "chart_type": case.chart_type,
        "data_file": data_file,
        "success": False,
    }

    for attempt in range(1, 4):
        result["attempt_used"] = attempt
        refs = _snapshot_refs()

        # Fill form
        set_ok, set_out = _set_form_values(
            data_file, case.analysis_type, case.chart_type, case.question, refs
        )
        if not set_ok:
            if attempt < 3:
                _run_agent_browser(["wait", "1000"], timeout=10)
                continue
            result["error"] = f"set_form_failed: {set_out}"
            return result

        # Check "Include Visualization" toggle before running analysis
        viz_toggle = refs.get("include_viz") or INCLUDE_VIZ_CHECKBOX_SELECTOR
        _run_agent_browser(["click", viz_toggle], timeout=15)
        _run_agent_browser(["wait", "500"], timeout=10)

        # Click Run Analysis (now includes visualization)
        run_target = refs.get("run_analysis") or RUN_ANALYSIS_BUTTON_SELECTOR
        ok, out = _run_agent_browser(["click", run_target], timeout=25)
        if not ok:
            if attempt < 3:
                _run_agent_browser(["wait", "1000"], timeout=10)
                continue
            result["error"] = f"click_analysis_failed: {out}"
            return result

        # Wait for combined analysis + visualization
        done_ok, done_state = _wait_for_complete(max_wait=180)
        analysis_payload = _read_result_payload()
        analysis_summary = _build_analysis_summary(analysis_payload)
        result["analysis_summary"] = analysis_summary

        rj = analysis_payload.get("result_json")
        analysis_ok = (
            isinstance(rj, dict)
            and rj.get("success") is not False
            and done_ok
        )

        if not analysis_ok:
            ui_err = str(analysis_payload.get("error_text") or "")
            if attempt < 3 and "Upload data file first" in ui_err:
                _run_agent_browser(["wait", "900"], timeout=10)
                continue
            if attempt < 3:
                _run_agent_browser(["wait", "900"], timeout=10)
                continue
            break

        # Extract analysis checks
        if isinstance(rj, dict):
            result["analysis_success"] = rj.get("success")
            cg = rj.get("code_generation", {})
            result["code_gen_mode"] = cg.get("mode") if isinstance(cg, dict) else None
            lp = rj.get("llm_input_policy", {})
            result["privacy_ok"] = (
                lp.get("raw_data_sent_to_llm") is False
                if isinstance(lp, dict)
                else None
            )
            result["has_answer"] = bool(rj.get("answer"))

        # Extract visualization from combined response
        viz_payload = _read_viz_payload()
        viz_summary = _build_viz_summary(viz_payload)
        result["viz_summary"] = viz_summary

        vrj = viz_payload.get("result_json")
        viz_file = ""
        if isinstance(vrj, dict):
            viz_file = str(vrj.get("file_path") or "")
            ci = vrj.get("chart_info")
            if not viz_file and isinstance(ci, dict):
                viz_file = str(ci.get("output_file") or "")
            result["viz_file_path"] = viz_file
            result["viz_success"] = vrj.get("success")

        # DOM-level multi-chart grid check (Plan-as-JSON rollout).
        # Soft floor of 1 chart tolerates single-column edge cases like
        # airline-passengers.csv (2 columns); a warning is logged when
        # count < 3 so regressions surface in the report.
        grid_state = _read_grid_state()
        result["eda_chart_count"] = int(grid_state.get("chart_count") or 0)
        result["eda_ok_count"] = int(grid_state.get("ok_count") or 0)
        result["eda_failed_count"] = int(grid_state.get("failed_count") or 0)
        result["has_model_section"] = bool(grid_state.get("has_model_section"))
        result["eda_chart_types"] = grid_state.get("chart_types") or []
        grid_ok = result["eda_ok_count"] >= 1
        if result["eda_ok_count"] < 3:
            result["grid_warning"] = (
                f"only {result['eda_ok_count']} chart(s) rendered — "
                "multi-chart EDA expected >= 3"
            )

        if (
            done_ok
            and isinstance(rj, dict)
            and rj.get("success") is not False
            and grid_ok
        ):
            result["success"] = True
            break
        if not grid_ok:
            result["error"] = result.get("error") or "no_charts_rendered"

        if attempt < 3:
            _run_agent_browser(["wait", "900"], timeout=10)

    # Screenshot
    combined = f"{analysis_summary} | Viz: {result.get('viz_summary', 'N/A')}"
    _inject_banner(case.case_id, case.question, combined)
    _run_agent_browser(["wait", "700"], timeout=10)
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    shot_ok, _ = _run_agent_browser(
        ["screenshot", str(screenshot_path), "--full"], timeout=50
    )
    result["screenshot_path"] = str(screenshot_path) if shot_ok else ""

    return result


# ---------------------------------------------------------------------------
# Main suite
# ---------------------------------------------------------------------------
def run_suite(
    *,
    frontend_url: str,
    login_email: str,
    login_password: str,
    output_root: Path,
    cases: list[Case] | None = None,
) -> dict[str, Any]:
    if shutil.which("agent-browser") is None:
        raise RuntimeError("agent-browser CLI not in PATH")

    print("[1/4] Downloading & staging datasets...")
    data_files = download_and_stage_datasets()
    if not data_files:
        raise RuntimeError("No datasets available")

    if cases is None:
        cases = BROWSER_CASES

    # Filter cases to available datasets
    cases = [c for c in cases if c.dataset_key in data_files]
    print(f"  {len(data_files)} datasets, {len(cases)} test cases")

    print("\n[2/4] Logging in...")
    _ensure_logged_in(frontend_url, login_email, login_password)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = output_root / f"data_analysis_browser_e2e_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[3/4] Running {len(cases)} browser test cases...")
    print("-" * 60)
    case_results: list[dict[str, Any]] = []
    started = time.perf_counter()

    for idx, case in enumerate(cases, 1):
        print(f"  [{idx}/{len(cases)}] {case.case_id}: {case.description}")
        _open_data_page(frontend_url)
        screenshot_path = out_dir / f"{idx:02d}_{case.case_id}.png"
        r = _run_case(case, data_files, screenshot_path)
        icon = "✓" if r["success"] else "✗"
        extra = ""
        if r["success"]:
            mode = r.get("code_gen_mode", "?")
            priv = "ok" if r.get("privacy_ok") else "?"
            charts = r.get("eda_ok_count", 0)
            failed = r.get("eda_failed_count", 0)
            warn = r.get("grid_warning")
            chart_info = f"charts={charts}" + (f"/failed={failed}" if failed else "")
            extra = f" (mode={mode}, {chart_info}, privacy={priv})"
            if warn:
                extra += f" [WARN: {warn}]"
        else:
            extra = f" ({r.get('error', r.get('analysis_summary', ''))[:60]})"
        print(f"    [{icon}] {'PASS' if r['success'] else 'FAIL'}{extra}")
        case_results.append(r)

    elapsed_s = time.perf_counter() - started
    print("-" * 60)

    success_count = sum(1 for r in case_results if r.get("success"))
    total = len(case_results)
    rate = success_count / total if total else 0

    # Generate report
    print(f"\n[4/4] Results: {success_count}/{total} PASS ({rate*100:.0f}%)")

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "frontend_url": frontend_url,
        "output_dir": str(out_dir),
        "total_cases": total,
        "success_cases": success_count,
        "success_rate": round(rate, 4),
        "elapsed_s": round(elapsed_s, 1),
        "data_files": data_files,
        "cases": case_results,
    }

    report_path = out_dir / "data_analysis_browser_e2e_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  Report: {report_path}")
    # Emitted in key=value form so run_page_result_driven_gate.py can parse
    # the adapter output and locate the report file.
    print(f"output_dir={out_dir}")

    # Case index markdown
    lines = [
        "# Data Analysis Browser E2E — Case Index",
        "",
        f"- Generated: {report['generated_at_utc']}",
        f"- Success: {success_count}/{total} ({rate*100:.0f}%)",
        f"- Elapsed: {elapsed_s:.1f}s",
        "",
    ]
    for r in case_results:
        lines.append(f"## {r['case_id']}: {r.get('description', '')}")
        lines.append(f"- Dataset: {r['dataset_key']}")
        lines.append(f"- Prompt: {r['question']}")
        lines.append(f"- Success: {r['success']}")
        lines.append(f"- Analysis: {r.get('analysis_summary', 'N/A')}")
        lines.append(f"- Visualization: {r.get('viz_summary', 'N/A')}")
        lines.append(f"- Screenshot: {r.get('screenshot_path', '')}")
        if r.get("error"):
            lines.append(f"- Error: {r['error']}")
        lines.append("")

    (out_dir / "CASE_INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"  Index: {out_dir / 'CASE_INDEX.md'}")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Data Analysis browser E2E test with 5 public datasets"
    )
    p.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL)
    p.add_argument(
        "--login-email",
        default=os.getenv("RAG_E2E_LOGIN_EMAIL", "demo@example.com"),
    )
    p.add_argument(
        "--login-password",
        default=os.getenv("RAG_E2E_LOGIN_PASSWORD", "demo123"),
    )
    p.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    print("=" * 60)
    print("Data Analysis Browser E2E (agent-browser)")
    print("=" * 60)

    try:
        report = run_suite(
            frontend_url=args.frontend_url,
            login_email=args.login_email,
            login_password=args.login_password,
            output_root=Path(args.output_root),
        )
    except RuntimeError as e:
        print(f"\nABORTED: {e}")
        return 1

    print("\nDone.")
    return 0 if report["success_cases"] == report["total_cases"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
