#!/usr/bin/env python3
"""Stage 2 stress test: harder questions + adversarial inputs.

Goal: push the agentic path to its breaking point, find systemic
weaknesses beyond CSV parsing / random import.
"""
import json
import sys
import time
from pathlib import Path
import os
import urllib.request, urllib.error

# Authenticate at module load — production-like server requires JWT.
_PASSWORD = None
try:
    for line in Path("/Users/niuyp/Documents/github.com/Industry-AI-Flow/.env").read_text().splitlines():
        if line.startswith("DEMO_USER_PASSWORD="):
            _PASSWORD = line.split("=", 1)[1]
            break
except Exception:
    pass
if not _PASSWORD:
    print("FATAL: cannot read DEMO_USER_PASSWORD from .env")
    sys.exit(1)

_login_body = json.dumps({"email": "demo@example.com", "password": _PASSWORD}).encode()
_login_req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/auth/login",
    data=_login_body,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    _AUTH_TOKEN = json.loads(urllib.request.urlopen(_login_req, timeout=10).read())["token"]
    print(f"auth: OK (token {len(_AUTH_TOKEN)} chars)")
except Exception as e:
    print(f"FATAL: login failed: {e}")
    sys.exit(1)
_AUTH_HEADERS = {"Authorization": f"Bearer {_AUTH_TOKEN}"}

BASE = "http://127.0.0.1:8000"
DATA_DIR = Path("/tmp/stress-test-data")

# Stage 2: harder questions designed to push limits.
# Each tuple: (csv, question, expected_signal)
TESTS = [
    # === MULTI-STEP REASONING ===
    ("iris.csv",
     "Train 3 different classifiers on species and compare their AUC. Show ROC curves side by side.",
     {"code_substr_any": ["fit", "predict_proba", "roc"], "chart_required": True}),

    ("wine.csv",
     "Find the 3 most influential features for wine quality using both correlation and a Random Forest, then compare the rankings.",
     {"code_substr_any": ["RandomForest", "corr", "importance"], "chart_required": True}),

    ("heart_disease.csv",
     "Build a logistic regression classifier with 5-fold cross-validation. Report mean AUC and standard deviation.",
     {"code_substr_any": ["LogisticRegression", "cross_val", "KFold"], "chart_required": False}),

    # === EDGE CASES (real datasets but tricky asks) ===
    ("high_missing.csv",
     "After dropping rows with any missing value, what's the correlation between the first two numeric columns?",
     {"code_substr_any": ["dropna", "corr"], "chart_required": False}),

    ("timeseries.csv",
     "Forecast the next 7 days using a simple linear trend model and visualize the forecast vs historical.",
     {"code_substr_any": ["predict", "plot"], "chart_required": True}),

    ("categorical_only.csv",
     "Cross-tabulate the first two categorical columns and show the frequency table.",
     {"code_substr_any": ["crosstab", "groupby"], "chart_required": False}),

    # === AMBIGUOUS / UNDERSPECIFIED ===
    ("iris.csv",
     "Make a great chart",  # vague
     {"code_substr_any": [], "chart_required": True, "allow_failure": False}),

    ("wine.csv",
     "What's interesting?",  # very vague
     {"code_substr_any": [], "chart_required": False, "allow_failure": True}),

    # === DATA QUALITY CHALLENGES ===
    ("pii_looking.csv",
     "Aggregate income by department and show the top 3",
     {"code_substr_any": ["groupby", "sort", "head"], "chart_required": False}),

    # === STRESS THE INTENT CLASSIFIER ===
    ("iris.csv",
     "Predict sepal length from petal length using linear regression",  # regression keyword + predict
     {"code_substr_any": ["LinearRegression", "fit"], "chart_required": False}),

    # === ADVERSARIAL: NON-EXISTENT COLUMNS ===
    ("iris.csv",
     "Show distribution of the 'profit_margin' column",  # column doesn't exist
     {"code_substr_any": [], "chart_required": False, "allow_failure": True}),

    # === MULTI-CHART COMPOSITE REQUEST ===
    ("wine.csv",
     "Show me three things: distribution of alcohol, correlation heatmap of all features, and quality-by-class boxplots — all in one figure.",
     {"code_substr_any": ["subplots", "hist", "heatmap"], "chart_required": True}),

    # === LARGE WIDE DATASET ===
    ("wide_dataset.csv",
     "Run PCA to 2 components and scatter plot the points colored by the first column",
     {"code_substr_any": ["PCA", "scatter"], "chart_required": True}),

    # === SINGLE COLUMN — ADVANCED Q ===
    ("single_column.csv",
     "Compute the rolling mean with a window of 10 and plot it overlaid on the raw data",
     {"code_substr_any": ["rolling", "mean", "plot"], "chart_required": True}),

    # === BREAST CANCER ML CLASSIC ===
    ("breast_cancer.csv",
     "Compare Random Forest vs Gradient Boosting on this binary classification. Report accuracy, AUC, and confusion matrix for both.",
     {"code_substr_any": ["RandomForest", "GradientBoosting", "confusion_matrix"], "chart_required": True}),
]


def http_request(method, path, *, data=None, headers=None, files=None, timeout=120):
    url = f"{BASE}{path}"
    req_headers = dict(headers or {})
    req_headers.update(_AUTH_HEADERS)
    body = None
    if files is not None:
        boundary = "----stressformboundary8d3e4"
        parts = []
        for field, (fname, fbytes, mime) in files.items():
            parts.append(f"--{boundary}\r\n".encode())
            parts.append(
                f'Content-Disposition: form-data; name="{field}"; filename="{fname}"\r\n'
                f'Content-Type: {mime}\r\n\r\n'.encode()
            )
            parts.append(fbytes)
            parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        req_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif data is not None:
        body = json.dumps(data).encode()
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def upload(csv_path: Path):
    status, body = http_request("POST", "/api/v1/data/upload",
        files={"file": (csv_path.name, csv_path.read_bytes(), "text/csv")}, timeout=30)
    if status != 200:
        return None
    return json.loads(body).get("file_id") or csv_path.name


def start_job(data_file: str, question: str):
    status, body = http_request("POST", "/api/v1/data/analyze/start",
        data={"data_file": data_file, "analysis_type": "summary",
              "instruction": question, "generate_visualization": True},
        timeout=30)
    if status != 200:
        return None
    return json.loads(body).get("job_id")


def poll_sse(job_id: str, total_timeout_s: int = 120):
    url = f"{BASE}/api/v1/data/analyze/stream/{job_id}"
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    try:
        with urllib.request.urlopen(req, timeout=total_timeout_s) as resp:
            buf = b""
            for chunk in iter(lambda: resp.read(4096), b""):
                buf += chunk
                while b"\n\n" in buf:
                    block, buf = buf.split(b"\n\n", 1)
                    block_str = block.decode("utf-8", errors="replace")
                    event_name = None
                    data_lines = []
                    for line in block_str.splitlines():
                        if line.startswith("event:"):
                            event_name = line[6:].strip()
                        elif line.startswith("data:"):
                            data_lines.append(line[5:].strip())
                    if data_lines and event_name == "result":
                        try:
                            return json.loads("\n".join(data_lines))
                        except Exception:
                            return None
            return None
    except Exception as e:
        return {"sse_error": str(e)}


def classify(result, expected):
    if result is None or "sse_error" in (result or {}):
        return "HARD_FAIL", f"no SSE: {result}"
    success = result.get("success", True)
    answer = (result.get("answer") or "").strip()
    if success is False:
        if expected.get("allow_failure"):
            return "GRACEFUL_FAIL", str(result.get("error", ""))[:120]
        return "HARD_FAIL", f"success=False: {(result.get('error') or answer)[:120]}"
    gen = result.get("code") or ""
    if not isinstance(gen, str):
        gen = str(gen)
    substrs = expected.get("code_substr_any") or []
    has_substr = (not substrs) or any(s.lower() in gen.lower() for s in substrs)
    vizes = result.get("visualizations") or []
    charts = result.get("charts") or []
    has_chart = bool(vizes) or any(c.get("status") == "ok" for c in charts if isinstance(c, dict))
    chart_ok = (not expected.get("chart_required")) or has_chart
    has_answer = bool(answer)
    if has_substr and chart_ok and has_answer:
        return "PASS", f"code={len(gen)}b chart={has_chart} answer={len(answer)}c"
    if has_substr and not chart_ok:
        return "SOFT_FAIL", "code matched signal but no chart rendered"
    if not has_substr and has_chart:
        return "WRONG_BUT_PLAUSIBLE", f"chart rendered but missed signals {substrs!r}"
    return "WRONG_BUT_PLAUSIBLE", f"code={len(gen)}b chart={has_chart} substr_match={has_substr}"


results = []
for i, (csv_name, question, expected) in enumerate(TESTS, 1):
    csv_path = DATA_DIR / csv_name
    if not csv_path.exists():
        print(f"[{i:2}/{len(TESTS)}] SKIP {csv_name}: missing")
        continue
    t0 = time.time()
    df = upload(csv_path)
    if df is None:
        results.append({"i": i, "csv": csv_name, "q": question, "status": "HARD_FAIL", "reason": "upload"})
        print(f"[{i:2}/{len(TESTS)}] HARD_FAIL upload {csv_name}")
        continue
    job = start_job(df, question)
    if job is None:
        results.append({"i": i, "csv": csv_name, "q": question, "status": "HARD_FAIL", "reason": "start"})
        print(f"[{i:2}/{len(TESTS)}] HARD_FAIL start {csv_name}")
        continue
    res = poll_sse(job, total_timeout_s=120)
    elapsed = time.time() - t0
    status, detail = classify(res, expected)
    mode = ""
    code_len = 0
    chart_count = 0
    err = ""
    if isinstance(res, dict):
        mode = (res.get("code_generation") or {}).get("mode") or ""
        if not mode:
            for c in res.get("charts", []):
                if isinstance(c, dict) and c.get("type") == "agentic":
                    mode = "agentic"; break
        code_len = len(res.get("code") or "")
        chart_count = len(res.get("visualizations") or [])
        err = str(res.get("error") or "")[:120]
    print(f"[{i:2}/{len(TESTS)}] {status:20} {csv_name:24} q={question[:34]!r:38} mode={mode:10} code={code_len:5}b ch={chart_count} {elapsed:5.1f}s :: {detail[:80]}")
    results.append({
        "i": i, "csv": csv_name, "q": question, "status": status, "detail": detail,
        "mode": mode, "code_len": code_len, "chart_count": chart_count,
        "elapsed_s": round(elapsed, 2), "error": err,
    })

# Add elapsed_s=0 to upload-fail results so summary doesn't crash
for r in results:
    r.setdefault("elapsed_s", 0)

from collections import Counter
print("\n========== STAGE 2 SUMMARY ==========")
print(f"total: {len(results)}")
status_counts = Counter(r["status"] for r in results)
for s, n in sorted(status_counts.items()):
    print(f"  {s}: {n}")
print(f"modes: {dict(Counter(r.get('mode','') for r in results))}")
print(f"mean latency: {sum(r['elapsed_s'] for r in results)/len(results):.1f}s")

Path("/tmp/stage2-stress-results.json").write_text(json.dumps(results, indent=2))
print("\nwritten to /tmp/stage2-stress-results.json")
