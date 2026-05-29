#!/usr/bin/env python3
"""Advanced-ML capability E2E for the Dynamic Data Analysis pipeline.

API-level (not browser) battery that exercises the agentic path beyond EDA:
supervised (multiclass / imbalanced / regression), unsupervised
(KMeans+silhouette / PCA / DBSCAN), anomaly detection, time-series — plus three
ADVERSARIAL probes (xgboost unavailable, GridSearch compute blow-up, RL paradigm
mismatch) that document governance gaps from the 2026-05-29 review
(docs/data_analysis_ml_adversarial_review.md).

Flow per scenario: login -> upload dataset -> POST /api/v1/data/analyze/start ->
read SSE -> inspect the terminal `result` event.

Capability scenarios must PASS (success + >=1 chart). Adversarial scenarios are
OBSERVATIONS (recorded, never gating) — they capture current behaviour so a
regression (e.g. xgboost stops repairing, or RL starts crashing) is visible.

Requires the backend on :8000 (E2B + agentic). Credentials via env:
  RAG_E2E_LOGIN_EMAIL (default demo@example.com)
  RAG_E2E_LOGIN_PASSWORD (falls back to DEMO_USER_PASSWORD in .env)

Usage:
  python scripts/testing/run_data_analysis_ml_e2e.py
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_ROOT / "test_resources" / "datasets" / "e2e_public"
DEFAULT_API = "http://localhost:8000"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "temp"


@dataclass
class Scenario:
    sid: str
    kind: str  # "capability" | "adversarial"
    dataset: str  # filename under DATASET_DIR, or "__anomaly__" (synthesized)
    instruction: str
    expect: str = ""  # human note on expected outcome (adversarial)


SCENARIOS: list[Scenario] = [
    Scenario("01_supervised_multiclass", "capability", "penguins.csv",
             "Classify penguin species from the numeric measurements. Report "
             "macro-averaged F1 and show the confusion matrix as a heatmap."),
    Scenario("02_supervised_imbalanced", "capability", "titanic.csv",
             "Predict survival as an imbalanced problem: report precision, recall "
             "and PR-AUC for the positive class (not just accuracy), and plot the "
             "precision-recall curve."),
    Scenario("03_regression_mixed", "capability", "mpg.csv",
             "Predict mpg using all features including categorical ones (one-hot "
             "encode). Report R-squared and RMSE on a held-out test set and show a "
             "predicted-vs-actual scatter plot."),
    Scenario("04_unsupervised_kmeans", "capability", "penguins.csv",
             "Cluster the penguins using only the numeric measurements (NOT species). "
             "Choose k via the silhouette score, report it, and visualize the clusters."),
    Scenario("05_unsupervised_pca", "capability", "penguins.csv",
             "Run PCA on the numeric measurements. Report the explained variance ratio "
             "and plot the data on the first two principal components colored by species."),
    Scenario("06_unsupervised_dbscan", "capability", "penguins.csv",
             "Use DBSCAN on the numeric measurements; report cluster and noise-point "
             "counts with a scatter plot."),
    Scenario("07_anomaly_isolationforest", "capability", "__anomaly__",
             "Detect anomalous rows using Isolation Forest. Report how many anomalies "
             "were flagged and visualize them on a scatter plot of the two features."),
    Scenario("08_timeseries_arima", "capability", "airline-passengers.csv",
             "This is a monthly airline passenger time series. Fit an ARIMA model and "
             "forecast the next 12 months, plotting history and forecast."),
    Scenario("09_adv_xgboost", "adversarial", "titanic.csv",
             "Train an XGBoost classifier (use the xgboost library) to predict survival. "
             "Report accuracy and XGBoost feature importances with a bar chart.",
             expect="xgboost not in E2B → repair to sklearn (rounds=2). Silent "
                    "substitution: success+chart but final libs=sklearn, no disclosure."),
    Scenario("10_adv_gridsearch", "adversarial", "titanic.csv",
             "Tune a RandomForestClassifier for survival with GridSearchCV over a large "
             "grid (n_estimators [100,200,400,800], max_depth [3,5,8,12,None], "
             "min_samples_split [2,5,10]) and 5-fold CV. Report best params and score.",
             expect="No compute guard → hits ~120s budget → often success=None / empty "
                    "result (no graceful payload). SLA risk."),
    Scenario("11_adv_reinforcement_learning", "adversarial", "construction_projects.csv",
             "Train a reinforcement learning agent with Q-learning to learn an optimal "
             "policy for minimizing construction cost overruns, plotting cumulative "
             "reward per episode.",
             expect="RL is a paradigm mismatch with static data. LLM usually declines "
                    "honestly BUT reports success=true + 0 charts (no refusal status)."),
]

ANOMALY_FILENAME = "ml_e2e_anomaly.csv"
_ML_LIBS = ("sklearn", "xgboost", "lightgbm", "statsmodels", "scipy")


def _password() -> str:
    pw = os.getenv("RAG_E2E_LOGIN_PASSWORD")
    if pw:
        return pw
    env = PROJECT_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("DEMO_USER_PASSWORD="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("No password: set RAG_E2E_LOGIN_PASSWORD or DEMO_USER_PASSWORD in .env")


def _login(api: str, email: str) -> str:
    body = json.dumps({"email": email, "password": _password()}).encode()
    req = urllib.request.Request(
        f"{api}/api/v1/auth/login", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["token"]


def _upload(api: str, token: str, path: Path) -> str:
    out = subprocess.run(
        ["curl", "-s", "-X", "POST", f"{api}/api/v1/data/upload",
         "-H", f"Authorization: Bearer {token}", "-F", f"file=@{path}"],
        capture_output=True, text=True, timeout=60).stdout
    return json.loads(out)["file_id"]


def _start(api: str, token: str, data_file: str, instruction: str) -> str:
    body = json.dumps({"data_file": data_file, "instruction": instruction,
                       "generate_visualization": True}).encode()
    req = urllib.request.Request(
        f"{api}/api/v1/data/analyze/start", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["job_id"]


def _stream(api: str, job_id: str, max_s: int = 130) -> dict:
    out = subprocess.run(
        ["curl", "-sN", "--max-time", str(max_s),
         f"{api}/api/v1/data/analyze/stream/{job_id}"],
        capture_output=True, text=True, timeout=max_s + 10).stdout
    result: dict = {"_stream_error": ""}
    for block in out.split("\n\n"):
        if "event: result" in block:
            m = re.search(r"data: (.+)", block, re.S)
            if m:
                try:
                    result = json.loads(m.group(1))
                except Exception as exc:  # noqa: BLE001
                    result = {"_parse_error": str(exc)}
        elif "event: error" in block:
            m = re.search(r"data: (.+)", block, re.S)
            if m:
                result["_stream_error"] = m.group(1)[:300]
    return result


def _make_anomaly_csv(dest: Path) -> None:
    try:
        import numpy as np
    except ImportError:
        # Deterministic hand-rolled fallback if numpy is absent in the runner.
        import random
        random.seed(42)
        rows = [("x", "y")]
        for _ in range(290):
            rows.append((round(random.gauss(0, 1), 4), round(random.gauss(0, 1), 4)))
        for _ in range(10):
            rows.append((round(random.uniform(-8, 8), 4), round(random.uniform(-8, 8), 4)))
    else:
        rng = np.random.RandomState(42)
        normal = rng.normal(0, 1, size=(290, 2))
        outliers = rng.uniform(-8, 8, size=(10, 2))
        rows = [("x", "y")] + [(round(a, 4), round(b, 4))
                               for a, b in list(map(tuple, normal)) + list(map(tuple, outliers))]
    with open(dest, "w", newline="") as f:
        csv.writer(f).writerows(rows)


def _summarize(s: Scenario, res: dict, wall: float) -> dict:
    code = str(res.get("code") or "")
    imports = sorted({m for m in re.findall(
        r"(?:^|\n)\s*(?:import|from)\s+([a-zA-Z0-9_]+)", code)})
    charts = res.get("charts") or res.get("visualizations") or []
    n_charts = len([c for c in charts if c.get("status") in (None, "ok")]) if charts else 0
    cg = res.get("code_generation") or {}
    return {
        "scenario": s.sid,
        "kind": s.kind,
        "dataset": s.dataset,
        "expect": s.expect,
        "success": res.get("success"),
        "n_charts": n_charts,
        "ml_libs": [i for i in imports if i in _ML_LIBS],
        "mode": cg.get("mode"),
        "rounds": cg.get("rounds"),
        "repair_triggered": cg.get("repair_triggered"),
        "exec_time_s": res.get("execution_time"),
        "wall_s": round(wall, 1),
        "answer": str(res.get("answer") or "")[:200],
        "stream_error": res.get("_stream_error", ""),
    }


def _verdict(s: Scenario, row: dict) -> str:
    if s.kind == "capability":
        return "PASS" if (row["success"] and row["n_charts"] >= 1) else "FAIL"
    return "OBSERVED"  # adversarial probes never gate the run


def run(api: str, email: str) -> dict:
    token = _login(api, email)
    print(f"[2/3] logged in (token len={len(token)})", flush=True)

    anomaly_path = Path(DEFAULT_OUTPUT_ROOT) / ANOMALY_FILENAME
    anomaly_path.parent.mkdir(parents=True, exist_ok=True)
    _make_anomaly_csv(anomaly_path)

    rows: list[dict] = []
    print("[3/3] running scenarios...", flush=True)
    for s in SCENARIOS:
        src = anomaly_path if s.dataset == "__anomaly__" else DATASET_DIR / s.dataset
        if not src.exists():
            print(f"  SKIP {s.sid}: missing {src}", flush=True)
            continue
        t0 = time.time()
        try:
            fid = _upload(api, token, src)
            job = _start(api, token, fid, s.instruction)
            res = _stream(api, job)
        except Exception as exc:  # noqa: BLE001
            res = {"success": None, "_stream_error": f"harness_exc: {exc}"}
        row = _summarize(s, res, time.time() - t0)
        row["verdict"] = _verdict(s, row)
        rows.append(row)
        tag = {"PASS": "[OK]", "FAIL": "[XX]", "OBSERVED": "[..]"}[row["verdict"]]
        print(f"  {tag} {s.sid:34s} success={row['success']} charts={row['n_charts']} "
              f"libs={row['ml_libs']} rounds={row['rounds']} wall={row['wall_s']}s", flush=True)

    cap = [r for r in rows if r["kind"] == "capability"]
    cap_pass = [r for r in cap if r["verdict"] == "PASS"]
    report = {
        "total": len(rows),
        "capability_total": len(cap),
        "capability_pass": len(cap_pass),
        "adversarial": [r for r in rows if r["kind"] == "adversarial"],
        "rows": rows,
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api-url", default=DEFAULT_API)
    ap.add_argument("--login-email", default=os.getenv("RAG_E2E_LOGIN_EMAIL", "demo@example.com"))
    ap.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    args = ap.parse_args()

    print("=" * 60)
    print("Data Analysis Advanced-ML E2E (API)")
    print("=" * 60)
    print("[1/3] datasets:", DATASET_DIR)

    report = run(args.api_url, args.login_email)

    out_dir = Path(args.output_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "data_analysis_ml_e2e_report.json"
    report_path.write_text(json.dumps(report, indent=2))

    print("-" * 60)
    print(f"Capability: {report['capability_pass']}/{report['capability_total']} PASS")
    print("Adversarial observations:")
    for r in report["adversarial"]:
        print(f"  - {r['scenario']}: success={r['success']} charts={r['n_charts']} "
              f"libs={r['ml_libs']} rounds={r['rounds']} | expected: {r['expect']}")
    print(f"Report: {report_path}")

    # Gate only on capability scenarios; adversarial probes are observations.
    return 0 if report["capability_pass"] == report["capability_total"] else 2


if __name__ == "__main__":
    sys.exit(main())
