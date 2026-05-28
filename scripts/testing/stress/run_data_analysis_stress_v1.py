#!/usr/bin/env python3
"""Honest stress test of /api/v1/data/analyze/start with diverse datasets.

Captures full SSE result envelope including generated code, chart presence,
and any errors. Classifies outcomes by inspecting the actual response, not
prose summaries.
"""
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
import urllib.request

BASE = "http://127.0.0.1:8000"
DATA_DIR = Path("/tmp/stress-test-data")

# (csv basename, question, expected_signal)
# expected_signal = what must appear in generated_code or output for "PASS"
TESTS = [
    # 1. simple distribution on standard ML dataset
    ("iris.csv",
     "Show me the distribution of sepal length",
     {"code_substr_any": ["sepal", "sepal_length"], "chart_required": True}),

    # 2. correlation question — should pick heatmap intent
    ("iris.csv",
     "Show correlation between all numeric features",
     {"code_substr_any": ["corr", "heatmap"], "chart_required": True}),

    # 3. supervised classification
    ("iris.csv",
     "Predict species using sepal and petal measurements",
     {"code_substr_any": ["fit", "predict", "Classifier", "Regression"],
      "chart_required": False}),

    # 4. wide dataset edge case
    ("wide_dataset.csv",
     "Find the most informative features",
     {"code_substr_any": ["feature", "importance", "var"], "chart_required": False}),

    # 5. semicolon-delimited (European CSV)
    ("semicolon_delimited.csv",
     "Summarize the data",
     {"code_substr_any": ["read_csv"],  # any successful read
      "chart_required": False}),

    # 6. high-missing edge case
    ("high_missing.csv",
     "Show missing value pattern",
     {"code_substr_any": ["isna", "missing", "null"],
      "chart_required": True}),

    # 7. PII-looking columns — should NOT crash, should produce safe output
    ("pii_looking.csv",
     "Show income distribution",
     {"code_substr_any": ["income", "hist", "distribution"],
      "chart_required": True}),

    # 8. timeseries
    ("timeseries.csv",
     "Show the trend over time",
     {"code_substr_any": ["plot", "time", "date"], "chart_required": True}),

    # 9. categorical-only (no numeric for plotting)
    ("categorical_only.csv",
     "What's in this dataset?",
     {"code_substr_any": ["value_counts", "head", "describe"],
      "chart_required": False}),

    # 10. weird off-topic question — should degrade gracefully
    ("iris.csv",
     "Translate the column names to French",
     {"code_substr_any": [],  # may not satisfy intent at all
      "chart_required": False,
      "allow_failure": True}),  # explicitly allow non-pass

    # 11. single-column edge case
    ("single_column.csv",
     "Plot the distribution",
     {"code_substr_any": ["hist", "plot"], "chart_required": True}),

    # 12. wine quality (UCI-flavor) advanced question
    ("wine.csv",
     "What factors most influence wine quality?",
     {"code_substr_any": ["importance", "corr", "feature"],
      "chart_required": False}),
]


def http_request(method, path, *, data=None, headers=None, files=None, timeout=120):
    url = f"{BASE}{path}"
    req_headers = dict(headers or {})
    body = None
    if files is not None:
        # multipart upload
        boundary = "----stressformboundary7c3d2"
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


def upload(csv_path: Path) -> str | None:
    status, body = http_request(
        "POST", "/api/v1/data/upload",
        files={"file": (csv_path.name, csv_path.read_bytes(), "text/csv")},
        timeout=30,
    )
    if status != 200:
        return None
    j = json.loads(body)
    return j.get("file_id") or j.get("sanitized_filename") or csv_path.name


def start_analysis(data_file: str, question: str) -> str | None:
    status, body = http_request(
        "POST", "/api/v1/data/analyze/start",
        data={
            "data_file": data_file,
            "analysis_type": "summary",
            "instruction": question,
            "generate_visualization": True,
        },
        timeout=30,
    )
    if status != 200:
        return None
    return json.loads(body).get("job_id")


def poll_sse(job_id: str, total_timeout_s: int = 120) -> dict | None:
    """Parse SSE stream, return final result event payload."""
    url = f"{BASE}/api/v1/data/analyze/stream/{job_id}"
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    deadline = time.time() + total_timeout_s
    try:
        with urllib.request.urlopen(req, timeout=total_timeout_s) as resp:
            buf = b""
            last_data = None
            for chunk in iter(lambda: resp.read(4096), b""):
                if time.time() > deadline:
                    return None
                buf += chunk
                while b"\n\n" in buf:
                    block, buf = buf.split(b"\n\n", 1)
                    block_str = block.decode("utf-8", errors="replace")
                    lines = block_str.splitlines()
                    event_name = None
                    data_lines = []
                    for line in lines:
                        if line.startswith("event:"):
                            event_name = line[6:].strip()
                        elif line.startswith("data:"):
                            data_lines.append(line[5:].strip())
                    if data_lines:
                        try:
                            payload = json.loads("\n".join(data_lines))
                        except Exception:
                            continue
                        if event_name == "result":
                            # The real result envelope. Don't stop on "done"
                            # stage event — the result event comes AFTER it.
                            return payload
                        last_data = payload
            return last_data
    except Exception as e:
        return {"sse_error": str(e)}


def classify(result: dict | None, expected: dict) -> tuple[str, str]:
    if result is None:
        return "HARD_FAIL", "no SSE result"
    if "sse_error" in result:
        return "HARD_FAIL", f"SSE: {result['sse_error']}"
    # Inspect result envelope
    success = result.get("success", True)
    if success is False and not expected.get("allow_failure"):
        return "HARD_FAIL", f"success=False: {str(result.get('error') or result.get('answer'))[:120]}"
    gen = result.get("code") or result.get("generated_code") or ""
    if not isinstance(gen, str):
        gen = str(gen)
    # Check substring expectations against the generated code
    substrs = expected.get("code_substr_any") or []
    has_substr = (not substrs) or any(s.lower() in gen.lower() for s in substrs)
    # Check chart: response uses `visualizations` array AND `charts` array
    vizes = result.get("visualizations") or []
    charts = result.get("charts") or []
    has_chart = bool(vizes) or any(c.get("status") == "ok" for c in charts if isinstance(c, dict))
    chart_ok = (not expected.get("chart_required")) or has_chart
    # Has actual answer text?
    answer = (result.get("answer") or "").strip()
    has_answer = bool(answer)
    if has_substr and chart_ok and has_answer:
        return "PASS", f"code={len(gen)}b chart={has_chart} answer={len(answer)}c"
    if has_substr and not chart_ok:
        return "SOFT_FAIL", f"code matched but no chart (had answer={has_answer})"
    if not has_substr and has_chart:
        return "WRONG_BUT_PLAUSIBLE", (
            f"chart rendered but code missed signal {substrs!r} "
            f"(code_len={len(gen)})"
        )
    return "WRONG_BUT_PLAUSIBLE", (
        f"code={len(gen)}b chart={has_chart} answer={has_answer} substr_match={has_substr}"
    )


results = []
for i, (csv_name, question, expected) in enumerate(TESTS, 1):
    csv_path = DATA_DIR / csv_name
    if not csv_path.exists():
        print(f"[{i:2}/{len(TESTS)}] SKIP {csv_name}: file missing")
        continue
    t0 = time.time()
    data_file = upload(csv_path)
    if data_file is None:
        results.append({"i": i, "csv": csv_name, "q": question, "status": "HARD_FAIL",
                        "reason": "upload failed", "elapsed_s": time.time() - t0})
        print(f"[{i:2}/{len(TESTS)}] HARD_FAIL upload {csv_name}")
        continue
    job_id = start_analysis(data_file, question)
    if job_id is None:
        results.append({"i": i, "csv": csv_name, "q": question, "status": "HARD_FAIL",
                        "reason": "start_analysis failed", "elapsed_s": time.time() - t0})
        print(f"[{i:2}/{len(TESTS)}] HARD_FAIL start {csv_name}")
        continue
    result = poll_sse(job_id, total_timeout_s=90)
    elapsed = time.time() - t0
    status, detail = classify(result, expected)
    mode = ""
    intent = ""
    err = ""
    code_len = 0
    chart_count = 0
    if isinstance(result, dict):
        mode = (result.get("code_generation") or {}).get("mode") or result.get("mode") or ""
        # agentic responses don't carry mode at top level; infer from chart type
        if not mode:
            charts = result.get("charts") or []
            for c in charts:
                if isinstance(c, dict) and c.get("type") == "agentic":
                    mode = "agentic"
                    break
            else:
                if charts:
                    mode = "deterministic_planner"
        intent = result.get("intent", "")
        err = str(result.get("error") or "")[:100]
        code_len = len(result.get("code") or "")
        chart_count = len(result.get("visualizations") or [])
    print(f"[{i:2}/{len(TESTS)}] {status:22} {csv_name:24} mode={mode:22} code={code_len:5}b charts={chart_count} {elapsed:5.1f}s :: {detail}")
    results.append({
        "i": i, "csv": csv_name, "q": question, "status": status, "detail": detail,
        "mode": mode, "intent": intent, "elapsed_s": round(elapsed, 2),
        "code_len": code_len, "chart_count": chart_count,
        "error": err,
    })

# summary
from collections import Counter
status_counts = Counter(r["status"] for r in results)
mode_counts = Counter(r.get("mode", "") for r in results)
print("\n========== SUMMARY ==========")
print(f"total: {len(results)}")
for s, n in status_counts.most_common():
    print(f"  {s}: {n}")
print(f"modes: {dict(mode_counts)}")

Path("/tmp/real-stress-results.json").write_text(json.dumps(results, indent=2))
print("\nwritten to /tmp/real-stress-results.json")
