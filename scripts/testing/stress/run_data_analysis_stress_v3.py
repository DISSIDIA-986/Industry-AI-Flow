#!/usr/bin/env python3
"""Stage 3: language diversity + scale + repeatability + pathological inputs."""
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
    "http://127.0.0.1:8000/api/v1/auth/login",
    data=json.dumps({"email": "demo@example.com", "password": _PASSWORD}).encode(),
    headers={"Content-Type": "application/json"}, method="POST",
), timeout=10).read())["token"]
_AUTH = {"Authorization": f"Bearer {_token}"}
print(f"auth: OK")

TESTS = [
    # === SCALE: 50K row dataset ===
    ("large_50k.csv",
     "Compute summary statistics for all numeric features.",
     {"code_substr_any": ["describe", "mean"], "chart_required": False}),
    ("large_50k.csv",
     "Train a random forest classifier on target. Report accuracy and the top 5 important features.",
     {"code_substr_any": ["RandomForest", "importance"], "chart_required": False}),
    # === I18N: Chinese-named columns + values ===
    ("utf8_bom_special.csv",
     "What is the average price by city?",
     {"code_substr_any": ["groupby", "mean"], "chart_required": False}),
    ("utf8_bom_special.csv",
     "Show the distribution of ratings as a histogram.",
     {"code_substr_any": ["hist", "rating", "评分"], "chart_required": True}),
    # === I18N: question itself in Chinese ===
    ("utf8_bom_special.csv",
     "按城市统计平均价格并画柱状图",  # group by city, mean price, bar chart
     {"code_substr_any": ["groupby", "mean"], "chart_required": True}),
    ("iris.csv",
     "用随机森林预测物种，输出特征重要性条形图",  # RF predict species + importance bar
     {"code_substr_any": ["RandomForest", "importance"], "chart_required": True}),
    # === PATHOLOGICAL: messy quoting + mixed line endings ===
    ("messy_quoted.csv",
     "Show how many rows have each score range",
     {"code_substr_any": ["score"], "chart_required": False, "allow_failure": True}),
    # === REPEATABILITY: same question twice, check cache hit ===
    ("iris.csv",
     "Show distribution of sepal length",
     {"code_substr_any": ["sepal"], "chart_required": True}),  # warmup (may miss cache)
    ("iris.csv",
     "Show distribution of sepal length",
     {"code_substr_any": ["sepal"], "chart_required": True, "expect_cache": True}),  # should HIT
    # === MULTI-FILE confusion: upload one, ask about other ===
    ("wine.csv",
     "Show distribution of sepal length",  # iris's column, asked on wine
     {"code_substr_any": [], "chart_required": False, "allow_failure": True}),
    # === LARGE-DATA INTERACTION: subset filter ===
    ("large_50k.csv",
     "Filter to rows where target=1, then show the correlation heatmap of the numeric features.",
     {"code_substr_any": ["heatmap", "corr"], "chart_required": True}),
    # === EXTREME EDGE: ask for a bunch of stats ===
    ("breast_cancer.csv",
     "For each feature, compute mean, std, skewness, and kurtosis. Print as a table.",
     {"code_substr_any": ["mean", "std", "skew"], "chart_required": False}),
    # === Demo-relevant: simulate evaluator clicking through ===
    ("wine.csv",
     "Which feature has the strongest correlation with quality?",
     {"code_substr_any": ["corr", "quality"], "chart_required": False}),
    ("wine.csv",
     "Show me the top 10 rows.",
     {"code_substr_any": ["head"], "chart_required": False}),
    # === ADVERSARIAL: ask system to do something it shouldn't ===
    ("iris.csv",
     "Delete the dataset from disk.",  # malicious
     {"code_substr_any": [], "chart_required": False, "allow_failure": True}),
]


def http(method, path, *, data=None, files=None, timeout=120):
    headers = dict(_AUTH)
    body = None
    if files:
        boundary = "----b3"
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


def classify(res, expected, elapsed):
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
    # Cache check: if expect_cache=True, latency should be << 5s
    cache_note = ""
    if expected.get("expect_cache") and elapsed > 5:
        cache_note = f" [CACHE_MISS expected hit but {elapsed:.1f}s]"
    if has_sub and chart_ok and has_ans:
        return "PASS", f"code={len(gen)}b chart={has_chart} ans={len((res.get('answer') or '').strip())}c{cache_note}"
    if has_sub and not chart_ok:
        return "SOFT_FAIL", "code matched but no chart"
    if not has_sub and has_chart:
        return "WRONG_BUT_PLAUSIBLE", f"chart but missed signal {substrs!r}{cache_note}"
    return "WRONG_BUT_PLAUSIBLE", f"code={len(gen)}b chart={has_chart} substr_match={has_sub}{cache_note}"


results = []
last_iris_hash = None
for i, (csv_name, q, expected) in enumerate(TESTS, 1):
    csv_path = DATA_DIR / csv_name
    if not csv_path.exists():
        print(f"[{i:2}/{len(TESTS)}] SKIP {csv_name}: missing"); continue
    t0 = time.time()
    df = upload(csv_path)
    if df is None:
        results.append({"i": i, "csv": csv_name, "q": q, "status": "HARD_FAIL", "reason": "upload"})
        print(f"[{i:2}/{len(TESTS)}] HARD_FAIL upload"); continue
    job = start_job(df, q)
    if job is None:
        results.append({"i": i, "csv": csv_name, "q": q, "status": "HARD_FAIL", "reason": "start"})
        print(f"[{i:2}/{len(TESTS)}] HARD_FAIL start"); continue
    res = poll(job, timeout=180)
    elapsed = time.time() - t0
    status, detail = classify(res, expected, elapsed)
    code_len = len(res.get("code") or "") if isinstance(res, dict) else 0
    code_hash = hashlib.sha256((res.get("code") or "").encode()).hexdigest()[:10] if isinstance(res, dict) else ""
    print(f"[{i:2}/{len(TESTS)}] {status:18} {csv_name:22} {elapsed:5.1f}s hash={code_hash:10} :: {detail[:90]}")
    results.append({
        "i": i, "csv": csv_name, "q": q, "status": status, "detail": detail,
        "code_len": code_len, "code_hash": code_hash,
        "elapsed_s": round(elapsed, 2),
    })

for r in results:
    r.setdefault("elapsed_s", 0)

from collections import Counter
print("\n========== STAGE 3 SUMMARY ==========")
print(f"total: {len(results)}")
sc = Counter(r["status"] for r in results)
for s, n in sorted(sc.items()):
    print(f"  {s}: {n}")
print(f"mean latency: {sum(r['elapsed_s'] for r in results)/len(results):.1f}s")
# Cache check: compare iris repeat questions
iris_runs = [r for r in results if r["csv"] == "iris.csv" and "sepal length" in r["q"]]
if len(iris_runs) >= 2:
    print(f"\ncache check on 'Show distribution of sepal length':")
    print(f"  run 1: hash={iris_runs[0]['code_hash']} elapsed={iris_runs[0]['elapsed_s']}s")
    print(f"  run 2: hash={iris_runs[1]['code_hash']} elapsed={iris_runs[1]['elapsed_s']}s")
    print(f"  same hash: {iris_runs[0]['code_hash'] == iris_runs[1]['code_hash']}")
Path("/tmp/stage3-stress-results.json").write_text(json.dumps(results, indent=2))
print("\nwritten to /tmp/stage3-stress-results.json")
