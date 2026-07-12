#!/usr/bin/env python3
"""Advanced-analysis method-router E2E (real cloud LLM + real E2B sandbox).

Validates the deterministic method planner added in analysis_planner.py end to
end through the live `/api/v1/data/analyze` endpoint:

  - Statistical / temporal questions route to the right method card and the
    GENERATED CODE actually runs the named scipy/statsmodels/sklearn test.
  - `envelope.analysis_methods` reports the routed cards.
  - A plain EDA request routes to NO method (default-off / purely additive):
    the planner must never escalate a "show me a histogram" request.

Requires the backend running on :8000 with LLM_BACKEND=zhipu (or groq) and
CODE_EXECUTION_PROVIDER=e2b|docker, exactly like run_data_analysis_dataset_e2e.py.
This exercises the REAL model + REAL sandbox — no mocks.

Exit code 0 iff every case passes.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_ROOT / "test_resources" / "datasets" / "e2e_public"
BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")
ANALYZE_TIMEOUT_S = 180

# Auth (REQUIRE_USER_AUTH=true): log in as the demo user and bearer every call.
DEMO_EMAIL = os.environ.get("E2E_DEMO_EMAIL", "demo@example.com")
DEMO_PASSWORD = os.environ.get("E2E_DEMO_PASSWORD", "")
_AUTH_TOKEN: str = ""


def _login() -> str:
    """Return a bearer token, or '' if auth is disabled / login fails."""
    if not DEMO_PASSWORD:
        # Fall back to reading .env so the script is runnable standalone.
        env = PROJECT_ROOT / ".env"
        pw = ""
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("DEMO_USER_PASSWORD="):
                    pw = line.split("=", 1)[1].strip()
                    break
    else:
        pw = DEMO_PASSWORD
    if not pw:
        return ""
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/login",
        data=json.dumps({"email": DEMO_EMAIL, "password": pw}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            return str(body.get("access_token") or body.get("token") or "")
    except Exception as exc:  # noqa: BLE001
        print(f"  login failed: {exc}")
        return ""


def _auth_headers() -> dict:
    h = {"X-Tenant-ID": "methods-e2e"}
    if _AUTH_TOKEN:
        h["Authorization"] = f"Bearer {_AUTH_TOKEN}"
    return h


@dataclass(frozen=True)
class Case:
    case_id: str
    dataset: str
    instruction: str
    # method-router expectations
    expect_methods: tuple[str, ...]  # kinds that MUST appear (empty = must be [])
    expect_code_any: tuple[str, ...]  # >=1 of these substrings in generated code
    expect_finding_any: tuple[str, ...] = ()  # soft: >=1 in answer/findings (lower)
    forbid_methods: tuple[str, ...] = ()  # kinds that must NOT appear


CASES: list[Case] = [
    # Two-group comparison: tip by time (Lunch/Dinner) → Welch t-test + MWU.
    Case(
        case_id="M1-group-2",
        dataset="tips.csv",
        instruction=(
            "Does the tip amount differ significantly between Lunch and Dinner? "
            "Run the appropriate statistical test and report the p-value."
        ),
        expect_methods=("group_comparison",),
        expect_code_any=("ttest_ind", "mannwhitneyu"),
        expect_finding_any=("p-value", "p =", "p=", "significan", "p <", "p<"),
    ),
    # Correlation significance: total_bill vs tip → pearsonr / spearmanr.
    Case(
        case_id="M2-correlation",
        dataset="tips.csv",
        instruction=(
            "Is there a statistically significant correlation between total_bill "
            "and tip? Report r and the p-value."
        ),
        expect_methods=("correlation",),
        expect_code_any=("pearsonr", "spearmanr"),
        expect_finding_any=("p-value", "p =", "p=", "correlat", "significan"),
    ),
    # Time-series forecast: airline passengers (Month is a date-named object col).
    Case(
        case_id="M3-timeseries",
        dataset="airline-passengers.csv",
        instruction=(
            "Forecast the passenger numbers trend over time for the next 12 months."
        ),
        expect_methods=("timeseries",),
        expect_code_any=(
            "ARIMA",
            "ExponentialSmoothing",
            "STLForecast",
            "STL(",
            "SARIMAX",
        ),
        expect_finding_any=("forecast", "trend", "baseline", "MAE", "RMSE"),
    ),
    # Multi-group ANOVA on construction data: actual_cost across project_type.
    Case(
        case_id="M4-anova",
        dataset="construction_projects.csv",
        instruction=(
            "Does actual_cost differ significantly across the different "
            "project_type categories? Run a statistical test."
        ),
        expect_methods=("group_comparison",),
        expect_code_any=("f_oneway", "kruskal", "ttest_ind", "mannwhitneyu"),
        expect_finding_any=("p-value", "p =", "p=", "significan", "anova"),
    ),
    # DEFAULT-OFF guard: a plain EDA histogram must route to NO method card.
    Case(
        case_id="M5-eda-default-off",
        dataset="tips.csv",
        instruction="Show the distribution of tip amounts as a histogram.",
        expect_methods=(),  # must be exactly empty
        expect_code_any=(),  # no code assertion
        forbid_methods=(
            "group_comparison",
            "correlation",
            "timeseries",
            "cat_association",
            "feature_importance",
        ),
    ),
]


@dataclass
class Result:
    case_id: str
    status: str = "NOT_RUN"
    detail: str = ""
    methods: list[str] = field(default_factory=list)
    duration_s: float = 0.0


def _upload(path: Path) -> tuple[int, dict]:
    boundary = "----MethodsE2E"
    filename = path.name
    parts: list[bytes] = []
    parts.append(f"--{boundary}".encode())
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode()
    )
    parts.append(b"Content-Type: text/csv")
    parts.append(b"")
    parts.append(path.read_bytes())
    parts.append(f"--{boundary}--".encode())
    parts.append(b"")
    body = b"\r\n".join(parts)
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/data/upload",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            **_auth_headers(),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {"error": (e.read().decode() if e.fp else "")}
    except urllib.error.URLError as e:
        return 0, {"error": f"connection failed: {e.reason}"}


def _analyze(payload: dict) -> tuple[int, dict]:
    """Run analysis through the SSE job path (start → poll result).

    The demo frontend uses `/analyze/start` + `/analyze/stream|result`, which
    routes through DataAnalysisAgent.analyze_query → the agentic loop (where the
    method planner lives). The synchronous `/analyze` endpoint uses a different
    legacy tool path that never touches the agentic loop, so we MUST exercise
    the job path to validate method routing end to end.
    """
    start = urllib.request.Request(
        f"{BASE_URL}/api/v1/data/analyze/start",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **_auth_headers()},
    )
    try:
        with urllib.request.urlopen(start, timeout=30) as resp:
            job = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        txt = e.read().decode() if e.fp else ""
        try:
            return e.code, json.loads(txt)
        except Exception:
            return e.code, {"error": txt}
    except urllib.error.URLError as e:
        return 0, {"error": f"connection failed: {e.reason}"}

    job_id = job.get("job_id")
    if not job_id:
        return 500, {"error": f"no job_id in start response: {job}"}

    deadline = time.monotonic() + ANALYZE_TIMEOUT_S
    while time.monotonic() < deadline:
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/data/analyze/result/{job_id}",
            headers=_auth_headers(),
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, {"error": (e.read().decode() if e.fp else "")}
        except urllib.error.URLError as e:
            return 0, {"error": f"connection failed: {e.reason}"}
        if body.get("status") == "done":
            return 200, body.get("result") or {}
        time.sleep(2)
    return 504, {"error": f"job {job_id} did not finish within {ANALYZE_TIMEOUT_S}s"}


def _run(case: Case) -> Result:
    r = Result(case_id=case.case_id)
    t0 = time.monotonic()
    ds = DATASET_DIR / case.dataset
    if not ds.exists():
        r.status, r.detail = "ERROR", f"dataset missing: {ds}"
        return r

    st, up = _upload(ds)
    if st != 200 or up.get("status") != "success":
        r.status, r.detail = "FAIL", f"upload failed HTTP {st}: {up}"
        r.duration_s = time.monotonic() - t0
        return r
    file_id = up.get("file_id") or up.get("sanitized_filename", "")

    st, resp = _analyze(
        {
            "data_file": file_id,
            "analysis_type": "eda",
            "instruction": case.instruction,
        }
    )
    r.duration_s = time.monotonic() - t0
    if st != 200:
        r.status = "FAIL"
        r.detail = f"analyze HTTP {st}: {resp.get('error', resp.get('detail', ''))}"
        return r

    methods = resp.get("analysis_methods") or []
    r.methods = list(methods)
    code = str(resp.get("code") or "")
    findings = resp.get("analysis_summary", {}).get("key_findings") or []
    answer = str(resp.get("answer") or "")
    haystack = (" ".join(str(f) for f in findings) + " " + answer).lower()
    code_gen_mode = resp.get("code_generation", {}).get("mode", "")

    problems: list[str] = []

    # Method routing must be present.
    for kind in case.expect_methods:
        if kind not in methods:
            problems.append(f"missing routed method {kind!r} (got {methods})")
    # Default-off: forbidden methods must be absent.
    for kind in case.forbid_methods:
        if kind in methods:
            problems.append(f"unexpected method {kind!r} on an EDA-only request")
    # Exact-empty when expect_methods is empty and no forbid list overlap intended.
    if not case.expect_methods and case.forbid_methods and methods:
        problems.append(f"EDA request routed methods {methods}, expected none")

    # The generated code must actually call the named test (only when the
    # agentic path owned the response — the deterministic fallback path does not
    # honor the directive, so skip the code assertion there but flag it).
    agentic = code_gen_mode == "glm5_agent"
    if case.expect_code_any:
        if not agentic:
            problems.append(
                f"non-agentic path (mode={code_gen_mode!r}); directive not applied"
            )
        elif not any(tok in code for tok in case.expect_code_any):
            problems.append(
                f"code missing any of {case.expect_code_any}; "
                f"code head={code[:200]!r}"
            )

    # Soft: findings mention the statistical quantity (warn only, not fail).
    soft = ""
    if case.expect_finding_any and not any(
        tok.lower() in haystack for tok in case.expect_finding_any
    ):
        soft = f" (soft: findings lack any of {case.expect_finding_any})"

    if not resp.get("success", False) and case.expect_methods:
        problems.append("envelope success=false")

    if problems:
        r.status = "FAIL"
        r.detail = "; ".join(problems)
    else:
        r.status = "PASS"
        r.detail = f"methods={methods}, mode={code_gen_mode}{soft}"
    return r


def main() -> int:
    global _AUTH_TOKEN
    print(f"Advanced-analysis method-router E2E → {BASE_URL}")
    print("=" * 72)
    _AUTH_TOKEN = _login()
    print(f"auth: {'bearer token acquired' if _AUTH_TOKEN else 'no token (open mode)'}")
    results: list[Result] = []
    for case in CASES:
        print(f"\n[{case.case_id}] {case.instruction[:64]}...")
        res = _run(case)
        results.append(res)
        mark = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}.get(res.status, "?")
        print(f"  {mark} {res.status} ({res.duration_s:.1f}s) — {res.detail}")

    passed = sum(1 for r in results if r.status == "PASS")
    total = len(results)
    print("\n" + "=" * 72)
    print(f"RESULT: {passed}/{total} passed")
    for r in results:
        if r.status != "PASS":
            print(f"  - {r.case_id}: {r.status} — {r.detail}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
