#!/usr/bin/env python3
"""Stage 4: construction-domain realism + edge dtype + follow-up sequences."""
import json
import sys
import time
import hashlib
from pathlib import Path
import urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"
DATA_DIR = Path("/tmp/stress-test-data")

# Auth
_PASSWORD = None
for line in Path("/Users/niuyp/Documents/github.com/Industry-AI-Flow/.env").read_text().splitlines():
    if line.startswith("DEMO_USER_PASSWORD="):
        _PASSWORD = line.split("=", 1)[1]; break
_token = json.loads(urllib.request.urlopen(urllib.request.Request(
    f"{BASE}/api/v1/auth/login",
    data=json.dumps({"email": "demo@example.com", "password": _PASSWORD}).encode(),
    headers={"Content-Type": "application/json"}, method="POST",
), timeout=10).read())["token"]
_AUTH = {"Authorization": f"Bearer {_token}"}
print("auth: OK")

# Each test: (csv, question, expected_signal)
TESTS = [
    # === CONSTRUCTION COST (Capstone domain) ===
    ("construction_projects.csv",
     "What's the average cost overrun percentage by project type?",
     {"code_substr_any": ["groupby", "project_type"], "chart_required": False}),
    ("construction_projects.csv",
     "Show the relationship between contractor_rating and actual_cost / estimated_cost ratio.",
     {"code_substr_any": ["contractor_rating", "scatter"], "chart_required": True}),
    ("construction_projects.csv",
     "Predict actual_cost using sqft, floors, contractor_rating, risk_score as features. Report R-squared and MAE.",
     {"code_substr_any": ["fit", "predict", "r2"], "chart_required": False}),
    ("construction_projects.csv",
     "Which 3 cities have the highest average cost overrun?",
     {"code_substr_any": ["groupby", "city", "sort"], "chart_required": False}),

    # === SAFETY DATA (timestamps + categoricals) ===
    ("safety_incidents.csv",
     "Plot incident counts by month over the full date range.",
     {"code_substr_any": ["resample", "to_datetime", "month"], "chart_required": True}),
    ("safety_incidents.csv",
     "Which trade has the highest average lost_days per incident? Show top 5.",
     {"code_substr_any": ["trade", "groupby", "lost_days"], "chart_required": False}),
    ("safety_incidents.csv",
     "Build a stacked bar chart of severity counts broken down by root_cause.",
     {"code_substr_any": ["stacked", "bar"], "chart_required": True}),

    # === EDGE DTYPE: all-NaN column ===
    ("edge_all_nan_col.csv",
     "Show distribution of the value column",
     {"code_substr_any": ["value", "hist"], "chart_required": True}),

    # === EDGE: duplicate column names (pandas mangles to .1) ===
    ("edge_duplicate_cols.csv",
     "Show the first few rows",
     {"code_substr_any": ["head"], "chart_required": False}),

    # === EDGE: empty data rows (only header) ===
    ("edge_only_header.csv",
     "Summarize the data",
     {"code_substr_any": [], "chart_required": False, "allow_failure": True}),

    # === EDGE: mixed string/numeric in one column ===
    ("edge_mixed_dtype.csv",
     "Show distribution of value_or_text after filtering out non-numeric entries",
     {"code_substr_any": ["to_numeric", "filter", "dropna"], "chart_required": True}),

    # === REALISTIC FOLLOW-UP SEQUENCE (simulates user drilling down) ===
    # round 1: overview
    ("construction_projects.csv",
     "Give me an overview of this dataset.",
     {"code_substr_any": ["describe", "info", "shape"], "chart_required": False}),
    # round 2: focused on what they saw
    ("construction_projects.csv",
     "Now show me the distribution of project_type",
     {"code_substr_any": ["project_type", "value_counts", "hist"], "chart_required": True}),
    # round 3: drill into one
    ("construction_projects.csv",
     "Focus on Commercial projects. What's the cost overrun pattern?",
     {"code_substr_any": ["Commercial", "groupby", "overrun"], "chart_required": False}),

    # === ROBUSTNESS: question doesn't reference any specific column ===
    ("construction_projects.csv",
     "What's the biggest risk for project cost overrun?",
     {"code_substr_any": ["corr", "feature"], "chart_required": False}),
]


def http(method, path, *, data=None, files=None, timeout=180):
    headers = dict(_AUTH)
    body = None
    if files:
        boundary = "----b4"
        parts = []
        for field, (fname, fbytes, mime) in files.items():
            parts.append(f"--{boundary}\r\n".encode())
            parts.append(
                f'Content-Disposition: form-data; name="{field}"; filename="{fname}"\r\n'
                f'Content-Type: {mime}\r\n\r\n'.encode()
            )
            parts.append(fbytes); parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def upload(csv_path):
    st, body = http("POST", "/api/v1/data/upload",
        files={"file": (csv_path.name, csv_path.read_bytes(), "text/csv")}, timeout=60)
    if st != 200: return None
    return json.loads(body).get("file_id") or csv_path.name


def start_job(df, q):
    st, body = http("POST", "/api/v1/data/analyze/start",
        data={"data_file": df, "analysis_type": "summary", "instruction": q,
              "generate_visualization": True}, timeout=30)
    if st != 200: return None
    return json.loads(body).get("job_id")


def poll(job, timeout=180):
    url = f"{BASE}/api/v1/data/analyze/stream/{job}"
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream", **_AUTH})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            buf = b""
            for chunk in iter(lambda: resp.read(4096), b""):
                buf += chunk
                while b"\n\n" in buf:
                    block, buf = buf.split(b"\n\n", 1)
                    bstr = block.decode("utf-8", errors="replace")
                    event_name = None; data_lines = []
                    for line in bstr.splitlines():
                        if line.startswith("event:"): event_name = line[6:].strip()
                        elif line.startswith("data:"): data_lines.append(line[5:].strip())
                    if data_lines and event_name == "result":
                        try: return json.loads("\n".join(data_lines))
                        except: return None
            return None
    except Exception as e:
        return {"sse_error": str(e)}


def classify(res, expected):
    if not res or "sse_error" in res:
        return "HARD_FAIL", f"no SSE: {res}"
    if res.get("success") is False:
        if expected.get("allow_failure"):
            return "GRACEFUL_FAIL", str(res.get("error",""))[:120]
        return "HARD_FAIL", f"success=False: {(res.get('error') or res.get('answer'))[:120]}"
    gen = res.get("code") or ""
    if not isinstance(gen, str): gen = str(gen)
    substrs = expected.get("code_substr_any") or []
    has_sub = (not substrs) or any(s.lower() in gen.lower() for s in substrs)
    vizes = res.get("visualizations") or []
    charts = res.get("charts") or []
    has_chart = bool(vizes) or any(c.get("status") == "ok" for c in charts if isinstance(c, dict))
    chart_ok = (not expected.get("chart_required")) or has_chart
    has_ans = bool((res.get("answer") or "").strip())
    if has_sub and chart_ok and has_ans:
        return "PASS", f"code={len(gen)}b chart={has_chart} ans={len((res.get('answer') or '').strip())}c"
    if has_sub and not chart_ok:
        return "SOFT_FAIL", "code matched but no chart"
    if not has_sub and has_chart:
        return "WRONG_BUT_PLAUSIBLE", f"chart but missed signal {substrs!r}"
    return "WRONG_BUT_PLAUSIBLE", f"code={len(gen)}b chart={has_chart} substr_match={has_sub}"


results = []
for i, (csv_name, q, expected) in enumerate(TESTS, 1):
    csv_path = DATA_DIR / csv_name
    if not csv_path.exists():
        print(f"[{i:2}/{len(TESTS)}] SKIP {csv_name}: missing"); continue
    t0 = time.time()
    df = upload(csv_path)
    if df is None:
        results.append({"i": i, "csv": csv_name, "q": q, "status": "HARD_FAIL", "reason": "upload"})
        print(f"[{i:2}/{len(TESTS)}] HARD_FAIL upload {csv_name}"); continue
    job = start_job(df, q)
    if job is None:
        results.append({"i": i, "csv": csv_name, "q": q, "status": "HARD_FAIL", "reason": "start"})
        print(f"[{i:2}/{len(TESTS)}] HARD_FAIL start {csv_name}"); continue
    res = poll(job, timeout=180)
    elapsed = time.time() - t0
    status, detail = classify(res, expected)
    code_len = len(res.get("code") or "") if isinstance(res, dict) else 0
    print(f"[{i:2}/{len(TESTS)}] {status:18} {csv_name:32} {elapsed:5.1f}s :: q={q[:42]!r} :: {detail[:80]}")
    results.append({
        "i": i, "csv": csv_name, "q": q, "status": status, "detail": detail,
        "code_len": code_len, "elapsed_s": round(elapsed, 2),
    })

for r in results:
    r.setdefault("elapsed_s", 0)

from collections import Counter
print("\n========== STAGE 4 SUMMARY ==========")
print(f"total: {len(results)}")
sc = Counter(r["status"] for r in results)
for s, n in sorted(sc.items()):
    print(f"  {s}: {n}")
print(f"mean latency: {sum(r['elapsed_s'] for r in results)/len(results):.1f}s")
Path("/tmp/stage4-stress-results.json").write_text(json.dumps(results, indent=2))
print("\nwritten to /tmp/stage4-stress-results.json")
