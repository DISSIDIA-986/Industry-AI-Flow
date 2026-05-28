#!/usr/bin/env python3
"""
SSE Reproducibility Evaluation for Data Analysis Pipeline

Measures mode stability and code generation consistency across 3 sequential runs
for 6 representative test cases (mix of EDA/ML/timeseries).

Reuses test cases from run_data_analysis_dataset_e2e.py:
  - TC1-P1: Tips histogram (EDA)
  - TC2-P1: Titanic decision tree (ML classification)
  - TC3-P1: Penguins K-means (clustering)
  - TC4-P1: MPG linear regression (regression)
  - TC4-P2: MPG Ridge vs Decision Tree (ML comparison)
  - TC5-P1: Airline time series decomposition (time-series)

Workflow:
  1. POST /api/v1/data/upload (multipart CSV) → get data_file
  2. POST /api/v1/data/analyze/start → get job_id
  3. GET /api/v1/data/analyze/stream/{job_id} (SSE) → capture all events
  4. Parse final "result" event containing code_generation.mode + code
  5. Compute SHA256(code) and mode stability across 3 runs per case
  6. Output: /tmp/sse-repro-eval.json

Output: Per-prompt mode/code stability metrics and aggregate reproducibility rate.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_ROOT / "test_resources" / "datasets" / "e2e_public"

BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")
UPLOAD_ENDPOINT = f"{BASE_URL}/api/v1/data/upload"
ANALYZE_START_ENDPOINT = f"{BASE_URL}/api/v1/data/analyze/start"
ANALYZE_STREAM_ENDPOINT = f"{BASE_URL}/api/v1/data/analyze/stream"

# ---------------------------------------------------------------------------
# Test cases (subset of run_data_analysis_dataset_e2e.py)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TestCase:
    case_id: str
    dataset_key: str
    instruction: str
    analysis_type: str = "eda"
    target_column: Optional[str] = None
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
    # TC2: Titanic — classification
    TestCase(
        case_id="TC2-P1",
        dataset_key="titanic",
        instruction="Train a decision tree classifier to predict Survived and show feature importances as a bar chart",
        analysis_type="eda",
        target_column="Survived",
        description="Titanic: decision tree feature importance",
    ),
    # TC3: Penguins — clustering
    TestCase(
        case_id="TC3-P1",
        dataset_key="penguins",
        instruction="Run K-means clustering with 3 clusters on numeric features and visualize with a scatter plot",
        analysis_type="eda",
        description="Penguins: K-means 3 clusters scatter",
    ),
    # TC4: MPG — regression (run 1)
    TestCase(
        case_id="TC4-P1",
        dataset_key="mpg",
        instruction="Predict mpg using linear regression. Show R-squared, RMSE, and a residual plot",
        analysis_type="regression",
        target_column="mpg",
        description="MPG: linear regression + residual plot",
    ),
    # TC4: MPG — regression (run 2)
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
]

# Dataset download URLs
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
# Result tracking
# ---------------------------------------------------------------------------
@dataclass
class SingleRun:
    """Result of one execution attempt."""
    run_id: str  # "run_a", "run_b", "run_c"
    mode: str = ""
    code: str = ""
    code_hash: str = ""
    duration_s: float = 0.0
    status: str = "NOT_RUN"  # COMPLETED, TIMEOUT, ERROR
    error: str = ""
    http_status: Optional[int] = None


@dataclass
class PromptResult:
    """Results for one test case across 3 runs."""
    case_id: str
    description: str
    dataset_key: str
    instruction: str
    runs: dict[str, SingleRun] = field(default_factory=dict)

    def mode_stability(self) -> bool:
        """Check if mode is consistent across all 3 runs."""
        modes = [r.mode for r in self.runs.values() if r.status == "COMPLETED"]
        if len(modes) < 3:
            return False
        return len(set(modes)) == 1

    def code_stability(self) -> bool:
        """Check if code hash is consistent across all 3 runs."""
        hashes = [r.code_hash for r in self.runs.values() if r.status == "COMPLETED"]
        if len(hashes) < 3:
            return False
        return len(set(hashes)) == 1

    def first_diff_line(self) -> Optional[str]:
        """Find first line where run_a and run_b differ (if codes differ)."""
        if not self.runs.get("run_a") or not self.runs.get("run_b"):
            return None
        code_a = self.runs["run_a"].code
        code_b = self.runs["run_b"].code
        if code_a == code_b:
            return None
        lines_a = code_a.split("\n")
        lines_b = code_b.split("\n")
        for i, (la, lb) in enumerate(zip(lines_a, lines_b)):
            if la != lb:
                return f"Line {i+1}: A=[{la[:60]}...] vs B=[{lb[:60]}...]"
        if len(lines_a) != len(lines_b):
            return f"Line count mismatch: A={len(lines_a)} vs B={len(lines_b)}"
        return None


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def download_dataset(dataset_key: str) -> str:
    """Download dataset to DATASET_DIR. Return local path."""
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    meta = DATASETS[dataset_key]
    local_path = DATASET_DIR / meta["filename"]

    if local_path.exists():
        print(f"  Using cached: {local_path}")
        return str(local_path)

    print(f"  Downloading {dataset_key} from {meta['url']}...")
    try:
        urllib.request.urlretrieve(meta["url"], local_path)
        print(f"  Downloaded: {local_path}")
        return str(local_path)
    except Exception as e:
        print(f"  DOWNLOAD FAILED: {e}")
        raise


def upload_data_file(local_path: str) -> Optional[str]:
    """POST /api/v1/data/upload (multipart). Return file_id from response."""
    try:
        with open(local_path, "rb") as f:
            file_data = f.read()

        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{Path(local_path).name}"\r\n'
            f"Content-Type: text/csv\r\n"
            f"\r\n"
        ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            UPLOAD_ENDPOINT,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            # Backend returns file_id, not data_file
            return result.get("file_id") or result.get("data_file")
    except Exception as e:
        print(f"    UPLOAD FAILED: {e}")
        return None


def start_analysis(
    data_file: str, analysis_type: str, instruction: str, target_column: Optional[str] = None
) -> Optional[str]:
    """POST /api/v1/data/analyze/start. Return job_id from response."""
    try:
        payload = {
            "data_file": data_file,
            "analysis_type": analysis_type,
            "instruction": instruction,
            "generate_visualization": True,
        }
        if target_column:
            payload["target_column"] = target_column

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            ANALYZE_START_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result.get("job_id")
    except Exception as e:
        print(f"    ANALYZE START FAILED: {e}")
        return None


def stream_analysis(job_id: str, timeout_s: int = 90) -> Optional[dict]:
    """
    GET /api/v1/data/analyze/stream/{job_id} (SSE).
    Parse events until "result" event or timeout.
    Return final result dict, or None on error.
    """
    url = f"{ANALYZE_STREAM_ENDPOINT}/{job_id}"
    start = time.time()

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            for line in resp:
                if time.time() - start > timeout_s:
                    print(f"    TIMEOUT after {timeout_s}s")
                    return None

                line = line.decode("utf-8").strip()
                if not line:
                    continue

                if line.startswith("event: result"):
                    # Next line is the data
                    data_line = next(resp).decode("utf-8").strip()
                    if data_line.startswith("data: "):
                        json_str = data_line[6:]
                        return json.loads(json_str)
                elif line.startswith("event: error"):
                    data_line = next(resp).decode("utf-8").strip()
                    if data_line.startswith("data: "):
                        error_data = json.loads(data_line[6:])
                        print(f"    SSE ERROR: {error_data}")
                        return None

        print(f"    STREAM ENDED WITHOUT RESULT EVENT")
        return None

    except HTTPError as e:
        print(f"    HTTP {e.code}: {e.reason}")
        return None
    except URLError as e:
        print(f"    URL ERROR: {e.reason}")
        return None
    except Exception as e:
        print(f"    STREAM FAILED: {e}")
        return None


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------
def run_single_prompt(case: TestCase, run_label: str) -> SingleRun:
    """Execute one run of a test case. Return SingleRun result."""
    print(f"    {run_label}: uploading data...")
    data_file = upload_data_file(str(DATASET_DIR / DATASETS[case.dataset_key]["filename"]))
    if not data_file:
        return SingleRun(run_id=run_label, status="ERROR", error="upload failed")

    print(f"    {run_label}: starting analysis job...")
    job_id = start_analysis(
        data_file=data_file,
        analysis_type=case.analysis_type,
        instruction=case.instruction,
        target_column=case.target_column,
    )
    if not job_id:
        return SingleRun(run_id=run_label, status="ERROR", error="start_analysis failed")

    print(f"    {run_label}: streaming job {job_id[:8]}...")
    start = time.time()
    result = stream_analysis(job_id)
    duration = time.time() - start

    if result is None:
        return SingleRun(run_id=run_label, status="TIMEOUT", duration_s=duration)

    if result.get("error"):
        return SingleRun(
            run_id=run_label,
            status="ERROR",
            error=result.get("error"),
            duration_s=duration,
        )

    # Extract mode and code
    mode = result.get("code_generation", {}).get("mode", "")
    code = result.get("code", "")

    # Compute code hash
    code_hash = hashlib.sha256(code.encode()).hexdigest()

    return SingleRun(
        run_id=run_label,
        mode=mode,
        code=code,
        code_hash=code_hash,
        status="COMPLETED",
        duration_s=duration,
    )


def main():
    """Run reproducibility eval across all test cases."""
    print("=" * 80)
    print("SSE Data Analysis Reproducibility Evaluation")
    print("=" * 80)
    print(f"Backend: {BASE_URL}")
    print(f"Dataset dir: {DATASET_DIR}")
    print()

    # Download all datasets upfront
    print("Downloading datasets...")
    for dataset_key in set(tc.dataset_key for tc in TEST_CASES):
        print(f"  {dataset_key}:")
        try:
            download_dataset(dataset_key)
        except Exception as e:
            print(f"  FAILED TO DOWNLOAD {dataset_key}: {e}")
            sys.exit(1)
    print()

    # Run evaluation
    results: dict[str, PromptResult] = {}

    for case in TEST_CASES:
        print(f"Case: {case.case_id} / {case.description}")
        print(f"  Instruction: {case.instruction[:70]}...")
        print()

        prompt_result = PromptResult(
            case_id=case.case_id,
            description=case.description,
            dataset_key=case.dataset_key,
            instruction=case.instruction,
        )

        # Run 3 times
        for run_label in ["run_a", "run_b", "run_c"]:
            run_result = run_single_prompt(case, run_label)
            prompt_result.runs[run_label] = run_result

            status_str = f"{run_result.status}"
            if run_result.status == "COMPLETED":
                status_str += f" | mode={run_result.mode} | hash={run_result.code_hash[:8]}... | {run_result.duration_s:.1f}s"
            elif run_result.error:
                status_str += f" | {run_result.error}"
            print(f"      {status_str}")

        # Stability checks
        mode_stable = prompt_result.mode_stability()
        code_stable = prompt_result.code_stability()
        diff_line = prompt_result.first_diff_line()

        print(f"  MODE STABILITY: {mode_stable}")
        print(f"  CODE STABILITY: {code_stable}")
        if diff_line:
            print(f"  FIRST DIFF: {diff_line}")
        print()

        results[case.case_id] = prompt_result

    # Aggregate statistics
    print("=" * 80)
    print("AGGREGATE RESULTS")
    print("=" * 80)

    total_prompts = len(results)
    mode_stable_count = sum(1 for r in results.values() if r.mode_stability())
    code_stable_count = sum(1 for r in results.values() if r.code_stability())

    # Collect all modes
    all_modes = []
    for r in results.values():
        for run in r.runs.values():
            if run.status == "COMPLETED" and run.mode:
                all_modes.append(run.mode)

    mode_distribution = {}
    for mode in all_modes:
        mode_distribution[mode] = mode_distribution.get(mode, 0) + 1

    print(f"Total test cases: {total_prompts}")
    print(f"Mode-stable cases: {mode_stable_count}/{total_prompts} ({100*mode_stable_count/total_prompts:.1f}%)")
    print(f"Code-stable cases: {code_stable_count}/{total_prompts} ({100*code_stable_count/total_prompts:.1f}%)")
    print()
    print("Mode distribution across all 18 runs:")
    for mode, count in sorted(mode_distribution.items()):
        print(f"  {mode}: {count}")
    print()

    # Output JSON
    output = {
        "timestamp": time.time(),
        "base_url": BASE_URL,
        "total_test_cases": total_prompts,
        "mode_stability_rate": mode_stable_count / total_prompts if total_prompts > 0 else 0,
        "code_stability_rate": code_stable_count / total_prompts if total_prompts > 0 else 0,
        "total_runs": len(all_modes),
        "mode_distribution": mode_distribution,
        "per_case_results": {
            case_id: {
                "description": result.description,
                "dataset": result.dataset_key,
                "instruction": result.instruction,
                "mode_stable": result.mode_stability(),
                "code_stable": result.code_stability(),
                "first_diff_line": result.first_diff_line(),
                "runs": {
                    run_id: {
                        "status": run.status,
                        "mode": run.mode,
                        "code_hash": run.code_hash,
                        "duration_s": run.duration_s,
                        "error": run.error,
                    }
                    for run_id, run in result.runs.items()
                },
            }
            for case_id, result in results.items()
        },
    }

    output_path = "/tmp/sse-repro-eval.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Output saved to: {output_path}")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
