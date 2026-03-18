#!/usr/bin/env python3
"""
Data Analysis Dataset E2E Test

End-to-end validation of the Dynamic Data Analysis pipeline:
  Cloud LLM code generation → Docker sandbox execution → results/visualization

Tests 5 public datasets across EDA, classification, regression, clustering,
and time-series scenarios. Requires:
  - Backend running on :8000
  - Docker running with python:3.12-slim pulled
  - Valid cloud LLM API key (Zhipu or Gemini)
  - CODE_EXECUTION_PROVIDER=docker
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_ROOT / "test_resources" / "datasets" / "e2e_public"
REPORT_DIR = PROJECT_ROOT / "docs" / "testing"

BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")

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
# Test cases
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TestCase:
    case_id: str
    dataset_key: str
    instruction: str
    analysis_type: str = "eda"
    target_column: str | None = None
    description: str = ""


TEST_CASES: list[TestCase] = [
    # TC1: Tips — EDA / visualization
    TestCase(
        case_id="TC1-P1",
        dataset_key="tips",
        instruction="Show the distribution of tip amounts as a histogram",
        analysis_type="eda",
        description="Tips: histogram of tip distribution",
    ),
    TestCase(
        case_id="TC1-P2",
        dataset_key="tips",
        instruction="Create a scatter plot of total_bill vs tip colored by time",
        analysis_type="eda",
        description="Tips: scatter total_bill vs tip by time",
    ),
    TestCase(
        case_id="TC1-P3",
        dataset_key="tips",
        instruction="Generate a correlation heatmap for all numeric columns",
        analysis_type="correlation",
        description="Tips: correlation heatmap",
    ),
    # TC2: Titanic — classification
    TestCase(
        case_id="TC2-P1",
        dataset_key="titanic",
        instruction="Train a decision tree classifier to predict Survived and show feature importances as a bar chart",
        analysis_type="eda",
        target_column="Survived",
        description="Titanic: decision tree feature importance",
    ),
    TestCase(
        case_id="TC2-P2",
        dataset_key="titanic",
        instruction="Build a logistic regression model for survival prediction. Show accuracy and confusion matrix",
        analysis_type="eda",
        target_column="Survived",
        description="Titanic: logistic regression + confusion matrix",
    ),
    # TC3: Penguins — clustering
    TestCase(
        case_id="TC3-P1",
        dataset_key="penguins",
        instruction="Run K-means clustering with 3 clusters on numeric features and visualize with a scatter plot",
        analysis_type="eda",
        description="Penguins: K-means 3 clusters scatter",
    ),
    TestCase(
        case_id="TC3-P2",
        dataset_key="penguins",
        instruction="Show an elbow plot to find the optimal number of clusters",
        analysis_type="eda",
        description="Penguins: elbow plot",
    ),
    # TC4: MPG — regression
    TestCase(
        case_id="TC4-P1",
        dataset_key="mpg",
        instruction="Predict mpg using linear regression. Show R-squared, RMSE, and a residual plot",
        analysis_type="regression",
        target_column="mpg",
        description="MPG: linear regression + residual plot",
    ),
    TestCase(
        case_id="TC4-P2",
        dataset_key="mpg",
        instruction="Compare Ridge regression vs Decision Tree regression performance for predicting mpg",
        analysis_type="regression",
        target_column="mpg",
        description="MPG: Ridge vs Decision Tree comparison",
    ),
    # TC5: Airline — time series
    TestCase(
        case_id="TC5-P1",
        dataset_key="airline",
        instruction="Plot the time series and decompose into trend, seasonal, and residual components",
        analysis_type="eda",
        description="Airline: time series decomposition",
    ),
    TestCase(
        case_id="TC5-P2",
        dataset_key="airline",
        instruction="Calculate and plot the 12-month rolling average",
        analysis_type="eda",
        description="Airline: 12-month rolling average",
    ),
]


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
@dataclass
class TestResult:
    case_id: str
    description: str
    dataset_key: str
    status: str = "NOT_RUN"  # PASS / FAIL / TIMEOUT / ERROR
    upload_ok: bool = False
    analyze_ok: bool = False
    http_status: int | None = None
    response_success: bool | None = None
    has_answer: bool = False
    has_visualization: bool = False
    code_gen_mode: str = ""
    privacy_ok: bool = False
    error_detail: str = ""
    duration_s: float = 0.0
    raw_response: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _post_json(path: str, payload: dict) -> tuple[int, dict]:
    """POST JSON to backend, return (status_code, response_json)."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-Tenant-ID": "e2e-test",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode())
            return resp.status, body
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        try:
            body = json.loads(body_text)
        except Exception:
            body = {"error": body_text}
        return e.code, body
    except urllib.error.URLError as e:
        return 0, {"error": f"Connection failed: {e.reason}"}


def _upload_file(filepath: Path) -> tuple[int, dict]:
    """Multipart upload a file to the backend."""
    url = f"{BASE_URL}/api/v1/data/upload"
    boundary = "----E2EBoundary"
    filename = filepath.name
    file_data = filepath.read_bytes()

    body_parts = []
    body_parts.append(f"--{boundary}".encode())
    body_parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode()
    )
    body_parts.append(b"Content-Type: text/csv")
    body_parts.append(b"")
    body_parts.append(file_data)
    body_parts.append(f"--{boundary}--".encode())
    body = b"\r\n".join(body_parts)

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Tenant-ID": "e2e-test",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_body = json.loads(resp.read().decode())
            return resp.status, resp_body
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        try:
            resp_body = json.loads(body_text)
        except Exception:
            resp_body = {"error": body_text}
        return e.code, resp_body
    except urllib.error.URLError as e:
        return 0, {"error": f"Connection failed: {e.reason}"}


# ---------------------------------------------------------------------------
# Dataset download
# ---------------------------------------------------------------------------
def download_datasets() -> dict[str, Path]:
    """Download all datasets to local cache. Returns {key: local_path}."""
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for key, info in DATASETS.items():
        local_path = DATASET_DIR / info["filename"]
        if local_path.exists() and local_path.stat().st_size > 0:
            print(f"  [cached] {key}: {local_path.name}")
        else:
            print(f"  [downloading] {key}: {info['url']}")
            try:
                urllib.request.urlretrieve(info["url"], str(local_path))
                print(f"    -> {local_path.stat().st_size:,} bytes")
            except Exception as e:
                print(f"    FAILED: {e}")
                continue
        paths[key] = local_path
    return paths


# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
def preflight_check() -> bool:
    """Verify backend is reachable."""
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/health",
            headers={"X-Tenant-ID": "e2e-test"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"  Backend reachable at {BASE_URL}")
                return True
    except Exception:
        pass
    # Try root path as fallback
    try:
        req = urllib.request.Request(f"{BASE_URL}/")
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"  Backend reachable at {BASE_URL} (root)")
            return True
    except Exception as e:
        print(f"  ERROR: Cannot reach backend at {BASE_URL}: {e}")
        return False


# ---------------------------------------------------------------------------
# Core test runner
# ---------------------------------------------------------------------------
def run_single_test(tc: TestCase, dataset_path: Path) -> TestResult:
    """Execute a single test case: upload → analyze → validate."""
    result = TestResult(
        case_id=tc.case_id,
        description=tc.description,
        dataset_key=tc.dataset_key,
    )
    t0 = time.monotonic()

    # Step 1: Upload
    print(f"    Uploading {dataset_path.name}...")
    status, resp = _upload_file(dataset_path)
    if status != 200 or resp.get("status") != "success":
        result.status = "FAIL"
        result.error_detail = f"Upload failed: HTTP {status} - {resp}"
        result.duration_s = time.monotonic() - t0
        return result
    result.upload_ok = True
    file_id = resp.get("file_id") or resp.get("sanitized_filename", "")

    # Step 2: Analyze
    print(f"    Analyzing with prompt: {tc.instruction[:60]}...")
    payload: dict[str, Any] = {
        "data_file": file_id,
        "analysis_type": tc.analysis_type,
        "instruction": tc.instruction,
    }
    if tc.target_column:
        payload["target_column"] = tc.target_column

    status, resp = _post_json("/api/v1/data/analyze", payload)
    result.http_status = status
    result.raw_response = resp
    result.duration_s = time.monotonic() - t0

    # Step 3: Validate
    if status != 200:
        result.status = "FAIL"
        result.error_detail = f"HTTP {status}: {resp.get('error', resp.get('detail', ''))}"
        return result

    result.analyze_ok = True
    result.response_success = resp.get("success", False)

    # Check answer content
    answer = resp.get("answer", "")
    result.has_answer = bool(answer and len(str(answer)) > 10)

    # Check visualization artifacts
    viz = resp.get("visualizations", [])
    result.has_visualization = bool(viz and len(viz) > 0)

    # Check code generation mode
    code_gen = resp.get("code_generation", {})
    result.code_gen_mode = code_gen.get("mode", "unknown")

    # Privacy check
    llm_policy = resp.get("llm_input_policy", {})
    result.privacy_ok = llm_policy.get("raw_data_sent_to_llm") is False

    # Check for code validator rejection or Docker errors
    error_field = resp.get("error", "")
    if error_field:
        if "validator" in str(error_field).lower():
            result.status = "FAIL"
            result.error_detail = f"Code validator rejection: {error_field}"
            return result
        if "timeout" in str(error_field).lower():
            result.status = "TIMEOUT"
            result.error_detail = f"Execution timeout: {error_field}"
            return result

    # Determine pass/fail
    if result.response_success and result.has_answer:
        result.status = "PASS"
    elif result.response_success is False and error_field:
        result.status = "FAIL"
        result.error_detail = str(error_field)
    elif result.has_answer:
        # success field missing but got an answer — treat as pass
        result.status = "PASS"
    else:
        result.status = "FAIL"
        result.error_detail = "No meaningful answer returned"

    return result


def run_all_tests(dataset_paths: dict[str, Path]) -> list[TestResult]:
    """Run all test cases and return results."""
    results: list[TestResult] = []
    for tc in TEST_CASES:
        dataset_path = dataset_paths.get(tc.dataset_key)
        if not dataset_path:
            r = TestResult(
                case_id=tc.case_id,
                description=tc.description,
                dataset_key=tc.dataset_key,
                status="ERROR",
                error_detail=f"Dataset '{tc.dataset_key}' not available",
            )
            results.append(r)
            continue

        print(f"  [{tc.case_id}] {tc.description}")
        r = run_single_test(tc, dataset_path)
        status_icon = {"PASS": "✓", "FAIL": "✗", "TIMEOUT": "⏱", "ERROR": "!"}.get(
            r.status, "?"
        )
        extra = ""
        if r.status == "PASS":
            extra = f" (mode={r.code_gen_mode}, viz={'yes' if r.has_visualization else 'no'}, {r.duration_s:.1f}s)"
        else:
            extra = f" ({r.error_detail[:80]})"
        print(f"    [{status_icon}] {r.status}{extra}")
        results.append(r)

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_report(results: list[TestResult]) -> str:
    """Generate a markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(results)
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    timeout = sum(1 for r in results if r.status == "TIMEOUT")
    errors = sum(1 for r in results if r.status in ("ERROR", "NOT_RUN"))
    pass_rate = (passed / total * 100) if total else 0

    lines: list[str] = []
    lines.append("# Data Analysis Dataset E2E Report")
    lines.append("")
    lines.append(f"**Generated**: {now}")
    lines.append(f"**Backend**: {BASE_URL}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total test cases | {total} |")
    lines.append(f"| PASS | {passed} |")
    lines.append(f"| FAIL | {failed} |")
    lines.append(f"| TIMEOUT | {timeout} |")
    lines.append(f"| ERROR/NOT_RUN | {errors} |")
    lines.append(f"| **Pass rate** | **{pass_rate:.0f}%** |")
    threshold_met = "YES" if pass_rate >= 83 else "NO"
    lines.append(f"| Threshold (≥83%) | {threshold_met} |")
    lines.append("")
    lines.append("## Detailed Results")
    lines.append("")
    lines.append("| Case | Dataset | Status | Mode | Viz | Privacy | Time | Error |")
    lines.append("|------|---------|--------|------|-----|---------|------|-------|")
    for r in results:
        viz = "yes" if r.has_visualization else "no"
        priv = "ok" if r.privacy_ok else "-"
        err = r.error_detail[:50].replace("|", "/") if r.error_detail else ""
        lines.append(
            f"| {r.case_id} | {r.dataset_key} | {r.status} | "
            f"{r.code_gen_mode or '-'} | {viz} | {priv} | "
            f"{r.duration_s:.1f}s | {err} |"
        )

    # Failure details
    failures = [r for r in results if r.status != "PASS"]
    if failures:
        lines.append("")
        lines.append("## Failure Details")
        lines.append("")
        for r in failures:
            lines.append(f"### {r.case_id}: {r.description}")
            lines.append(f"- **Status**: {r.status}")
            lines.append(f"- **Error**: {r.error_detail}")
            if r.raw_response:
                # Show truncated generated code preview if available
                preview = r.raw_response.get("generated_code_preview", "")
                if preview:
                    lines.append(f"- **Code preview**: `{preview[:200]}...`")
                fallback = r.raw_response.get("code_generation", {}).get(
                    "fallback_reason", ""
                )
                if fallback:
                    lines.append(f"- **Fallback reason**: {fallback}")
            lines.append("")

    # Triage guidance
    lines.append("## Triage Guide")
    lines.append("")
    lines.append("| Symptom | Likely Cause | Action |")
    lines.append("|---------|-------------|--------|")
    lines.append(
        "| mode=template_fallback | Cloud LLM unreachable/failed | Check API keys, network |"
    )
    lines.append(
        "| TIMEOUT | Docker execution >30s | Check Docker health, simplify prompt |"
    )
    lines.append(
        "| Code validator rejection | Generated code uses banned imports | Review validator allowlist |"
    )
    lines.append(
        "| No visualization | LLM didn't generate plot code | Adjust prompt wording |"
    )
    lines.append(
        '| NaN/missing data crash | Dataset has nulls | Ensure code handles `dropna()` |'
    )
    lines.append("")

    return "\n".join(lines)


def generate_json_report(results: list[TestResult]) -> dict:
    """Generate a machine-readable JSON report."""
    total = len(results)
    passed = sum(1 for r in results if r.status == "PASS")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE_URL,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total * 100, 1) if total else 0,
        "threshold_met": passed / total >= 0.83 if total else False,
        "results": [
            {
                "case_id": r.case_id,
                "description": r.description,
                "dataset": r.dataset_key,
                "status": r.status,
                "upload_ok": r.upload_ok,
                "analyze_ok": r.analyze_ok,
                "http_status": r.http_status,
                "success": r.response_success,
                "has_answer": r.has_answer,
                "has_visualization": r.has_visualization,
                "code_gen_mode": r.code_gen_mode,
                "privacy_ok": r.privacy_ok,
                "duration_s": round(r.duration_s, 1),
                "error": r.error_detail or None,
            }
            for r in results
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 60)
    print("Data Analysis Dataset E2E Test")
    print("=" * 60)

    # Preflight
    print("\n[1/4] Preflight checks...")
    if not preflight_check():
        print("\nABORTED: Backend not reachable. Start it with `make run`.")
        return 1

    # Download datasets
    print("\n[2/4] Downloading datasets...")
    dataset_paths = download_datasets()
    if not dataset_paths:
        print("\nABORTED: No datasets available.")
        return 1
    print(f"  {len(dataset_paths)}/{len(DATASETS)} datasets ready")

    # Run tests
    print(f"\n[3/4] Running {len(TEST_CASES)} test cases...")
    print("-" * 60)
    results = run_all_tests(dataset_paths)
    print("-" * 60)

    # Summary
    passed = sum(1 for r in results if r.status == "PASS")
    total = len(results)
    pass_rate = passed / total * 100 if total else 0
    print(f"\n  Results: {passed}/{total} PASS ({pass_rate:.0f}%)")
    threshold_ok = pass_rate >= 83
    print(f"  Threshold (≥83%): {'MET' if threshold_ok else 'NOT MET'}")

    # Generate reports
    print("\n[4/4] Generating reports...")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    md_report = generate_report(results)
    md_path = REPORT_DIR / "data_analysis_dataset_e2e_report.md"
    md_path.write_text(md_report, encoding="utf-8")
    print(f"  Markdown: {md_path}")

    json_report = generate_json_report(results)
    json_path = REPORT_DIR / "data_analysis_dataset_e2e_report.json"
    json_path.write_text(json.dumps(json_report, indent=2), encoding="utf-8")
    print(f"  JSON: {json_path}")

    print("\nDone.")
    return 0 if threshold_ok else 1


if __name__ == "__main__":
    sys.exit(main())
