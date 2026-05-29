#!/usr/bin/env python3
"""Rare/edge-case adversarial sweep for the Dynamic Data Analysis pipeline.

Beyond the happy-path ML E2E, this rotates through unusual, vague, sophisticated,
multi-aspect, and out-of-paradigm instructions across edge datasets to surface
robustness gaps (numpy serialization, one-hot hallucination, single-column data,
privacy, non-English, nonexistent columns, RL refusal, timeouts).

Each case carries an expectation class:
  - ok      : must finish with success + >=1 chart
  - refuse  : must refuse (structured unsupported / unanswerable, success=false)
  - observe : record behaviour, never gates (vague/edge/non-English)

Flow per case: login -> upload -> POST analyze/start -> read SSE, with a durable
result-endpoint fallback so timeouts/SSE drops still capture the final payload.

Requires backend on :8000 (E2B + agentic). Creds via env RAG_E2E_LOGIN_EMAIL /
RAG_E2E_LOGIN_PASSWORD (falls back to DEMO_USER_PASSWORD in .env).

Usage: python scripts/testing/run_data_analysis_rare_cases_e2e.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_ROOT / "test_resources" / "datasets" / "e2e_public"
DEFAULT_API = "http://localhost:8000"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "temp"


@dataclass
class Case:
    cid: str
    expect: str  # ok | refuse | observe
    dataset: str
    instruction: str
    note: str = ""


CASES: list[Case] = [
    # --- sophisticated / advanced ---
    Case("01_eda_then_advanced", "ok", "safety_incidents.csv",
         "do EDA first and then advanced analysis",
         "the originally-reported numpy.bool_ serialization case"),
    Case("02_chi_square_hypothesis", "ok", "safety_incidents.csv",
         "Run advanced statistical analysis: chi-square hypothesis tests between "
         "categorical factors and severity, report p-values and which are significant, "
         "and visualize the p-values as a bar chart."),
    Case("03_multi_aspect", "ok", "titanic.csv",
         "In ONE figure: do EDA, train classifiers to predict survival, AND show "
         "ROC curves with AUC for each model."),
    Case("04_imbalanced_metrics", "ok", "titanic.csv",
         "Predict survival treating it as imbalanced: report precision/recall/PR-AUC "
         "and the confusion matrix, with the precision-recall curve."),
    Case("05_cluster_and_pca", "ok", "penguins.csv",
         "Cluster the numeric measurements (no species), pick k by silhouette, AND run "
         "PCA — show both in one figure."),
    Case("06_timeseries_ci", "ok", "airline-passengers.csv",
         "Forecast the next 12 months with ARIMA and plot the forecast with confidence "
         "intervals."),
    Case("07_regression_onehot", "observe", "mpg.csv",
         "Predict mpg using all features including categorical origin (one-hot encode); "
         "report R-squared and the model coefficients.",
         "known one-hot dummy-column hallucination risk"),
    # --- edge data ---
    Case("08_single_column", "observe", "single_column.csv",
         "Summarize this dataset and visualize the distribution.",
         "single-column CSV edge"),
    Case("09_pii_predict", "ok", "pii_looking.csv",
         "Predict income from the other numeric columns, report R-squared, and show a "
         "scatter of predicted vs actual income.",
         "privacy: PII-looking columns must not leak"),
    Case("10_missing_values", "ok", "mpg.csv",
         "Analyze how horsepower and weight relate to mpg, handling any missing values."),
    # --- vague / minimal ---
    Case("11_vague", "observe", "tips.csv", "find something interesting in this data"),
    Case("12_minimal", "observe", "tips.csv", "analyze"),
    # --- non-English (English-only policy) ---
    Case("13_non_english", "observe", "tips.csv",
         "分析小费金额和账单总额的关系并画散点图",
         "English-only policy — observe graceful handling"),
    # --- bad / out-of-paradigm ---
    Case("14_nonexistent_column", "observe", "tips.csv",
         "Predict the customer_satisfaction_score column from the other columns.",
         "column does not exist — expect graceful handling, not a crash loop"),
    Case("15_reinforcement_learning", "refuse", "construction_projects.csv",
         "Train a Q-learning reinforcement learning agent to minimize cost overruns and "
         "plot cumulative reward per episode.",
         "paradigm mismatch — must refuse fast"),
]


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
    req = urllib.request.Request(f"{api}/api/v1/auth/login", data=body,
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


def _await_result(api: str, job_id: str, max_s: int = 150) -> dict:
    """Poll the durable result endpoint until done or timeout."""
    deadline = time.time() + max_s
    while time.time() < deadline:
        time.sleep(3)
        try:
            with urllib.request.urlopen(
                f"{api}/api/v1/data/analyze/result/{job_id}", timeout=10
            ) as r:
                body = json.load(r)
        except Exception:
            continue
        if body.get("status") == "done":
            return body.get("result") or {}
    return {"success": None, "_timeout": True}


def _classify(case: Case, res: dict) -> tuple[str, str]:
    """Return (verdict, detail). Verdict in PASS/FAIL/OBSERVED."""
    cg = res.get("code_generation") or {}
    fallback = cg.get("fallback_reason")
    stderr = str(res.get("stderr") or "")
    charts = res.get("charts") or res.get("visualizations") or []
    n_charts = len([c for c in charts if c.get("status") in (None, "ok")]) if charts else 0
    success = res.get("success")
    serialize_bug = "not JSON serializable" in stderr
    refused = (success is False) and fallback in (
        "unsupported_analysis_type", "model_declared_unanswerable"
    )
    detail = (
        f"success={success} charts={n_charts} rounds={cg.get('rounds')} "
        f"repair={cg.get('repair_trigger_type')} fallback={fallback}"
        + (" SERIALIZE_BUG" if serialize_bug else "")
    )
    if case.expect == "refuse":
        return ("PASS" if refused else "FAIL", detail)
    if case.expect == "ok":
        ok = bool(success) and n_charts >= 1 and not serialize_bug
        return ("PASS" if ok else "FAIL", detail)
    # observe: never gates, but still flag a hard serialize bug as noteworthy
    return ("OBSERVED", detail + (" <-- serialize regression!" if serialize_bug else ""))


def run(api: str, email: str) -> dict:
    token = _login(api, email)
    print(f"[login] token len={len(token)}", flush=True)
    rows = []
    for c in CASES:
        src = DATASET_DIR / c.dataset
        if not src.exists():
            print(f"  SKIP {c.cid}: missing {src}", flush=True)
            continue
        t0 = time.time()
        try:
            fid = _upload(api, token, src)
            job = _start(api, token, fid, c.instruction)
            res = _await_result(api, job)
        except Exception as exc:  # noqa: BLE001
            res = {"success": None, "error": f"harness_exc: {exc}"}
        verdict, detail = _classify(c, res)
        wall = round(time.time() - t0, 1)
        rows.append({"case": c.cid, "expect": c.expect, "verdict": verdict,
                     "wall_s": wall, "detail": detail, "note": c.note})
        tag = {"PASS": "[OK]", "FAIL": "[XX]", "OBSERVED": "[..]"}[verdict]
        print(f"  {tag} {c.cid:26s} ({c.expect:7s}) {detail} wall={wall}s", flush=True)
    return {"rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api-url", default=DEFAULT_API)
    ap.add_argument("--login-email", default=os.getenv("RAG_E2E_LOGIN_EMAIL", "demo@example.com"))
    ap.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    args = ap.parse_args()

    print("=" * 64)
    print("Data Analysis Rare/Edge-Case Adversarial Sweep")
    print("=" * 64)
    report = run(args.api_url, args.login_email)

    out_dir = Path(args.output_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "data_analysis_rare_cases_report.json").write_text(json.dumps(report, indent=2))

    rows = report["rows"]
    gated = [r for r in rows if r["expect"] in ("ok", "refuse")]
    failed = [r for r in gated if r["verdict"] == "FAIL"]
    observed_bugs = [r for r in rows if "SERIALIZE_BUG" in r["detail"]]
    print("-" * 64)
    print(f"Gated: {len(gated) - len(failed)}/{len(gated)} pass | "
          f"Observed: {len([r for r in rows if r['expect']=='observe'])}")
    if failed:
        print("FAILURES:")
        for r in failed:
            print(f"  - {r['case']} ({r['expect']}): {r['detail']} | {r['note']}")
    if observed_bugs:
        print(f"SERIALIZATION REGRESSION in: {[r['case'] for r in observed_bugs]}")
    print(f"Report: {out_dir / 'data_analysis_rare_cases_report.json'}")
    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
