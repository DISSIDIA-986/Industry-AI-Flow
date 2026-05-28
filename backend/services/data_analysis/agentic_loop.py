"""Agentic CRISP-DM loop for Dynamic Data Analysis (Plan Appendix E, W2).

Bounded 2-pass: round 1 single-shot; if round 1 fails per predeclared trigger
AND total elapsed is still within the repair window, one repair round fires.
No more. Hard total budget of 45s prevents runaway cost/latency.

Seeds from `spike_harness` which was built for this reuse (design B.6).
Reuses `llm_client`, `code_executor.validator`, and E2B provider unchanged.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from backend.services.code_executor.providers.base import ExecutionResult
from backend.services.data_analysis.spike_harness import (
    extract_profile,
    extract_summary_json,
    load_dataframe,
    parse_json_response,
    render_prompt,
    validate_code,
)

logger = logging.getLogger(__name__)

# Prompts ship as committed markdown in the same package (W3).
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
SYSTEM_PROMPT_PATH = PROMPT_DIR / "agentic_v1_system.md"
USER_TEMPLATE_PATH = PROMPT_DIR / "agentic_v1_user_template.md"
REPAIR_TEMPLATE_PATH = PROMPT_DIR / "agentic_v1_repair_template.md"

# Budget constants (Plan E.3 W2; widened post-Codex-review 2026-04-18 so
# the outer asyncio.wait_for in _run_one_round accounts for BOTH the
# bootstrap pip install AND the user-code timeout separately. Before
# this, outer wait=sandbox_budget+5 could fire at 35s while the
# sandbox was legitimately spending ~15s on bootstrap + ~25s on user
# code, misclassifying a valid cold-sandbox run as sandbox_timeout).
BOOTSTRAP_BUDGET_S: float = 20.0  # max wall for pip install step inside run_sandbox
# Budgets widened again post-live-demo 2026-04-19. At 12s LLM budget,
# Zhipu's GLM-4.7 frequently blew the wall on heavier requests (ML
# comparison with 4 classifiers + CV), returning "LLM timeout after 10s"
# as a fake failure that actually wasted the repair round too. 25s is
# the 95th-percentile observed latency in live rehearsal; 120s total
# gives both rounds room to breathe with ~25s headroom.
DEFAULT_TOTAL_BUDGET_S: float = 120.0
REPAIR_DECISION_CUTOFF_S: float = 80.0  # past this, skip repair even on failure
DEFAULT_ROUND1_LLM_BUDGET_S: float = 25.0
DEFAULT_ROUND1_SANDBOX_BUDGET_S: float = 30.0   # user code only; bootstrap is separate
DEFAULT_ROUND2_LLM_BUDGET_S: float = 25.0

# Sampling (Plan A.6.2, tightened post-demo-rehearsal 2026-04-19).
#
# Originally temperature=0.2 to match the spike config. In live demo
# rehearsal, 1-in-3 requests hit BLOCKED-module violations (notably
# `import os`) because at 0.2 the model occasionally ignored the hard
# constraints section of the prompt. Dropping to 0.0 (greedy decoding)
# makes generation deterministic per prompt — the same profile +
# question + system prompt produces the same code every time. We lose
# creative-phrasing variance but that's a feature for a demo: the
# operator can rehearse a specific query and trust it stays green.
#
# Trade-off noted: if a specific query happens to land on a bad
# first-shot at temp=0.0, the repair round is the only recovery (no
# second sample will help). Mitigated by the repair prompt's inline
# cookbook + the asymmetric success policy we shipped earlier.
SAMPLING = {"temperature": 0.0, "top_p": 0.95, "max_tokens": 4096}

# Packages pre-installed in every agentic sandbox before user code runs.
# Keep in sync with sandbox_runtime.EXTRA_SANDBOX_PACKAGES — the W1 probe
# verifies these are importable at startup; the loop installs them at
# request time for sandboxes that lack them. The installer is idempotent:
# `pip install -q` is a ~1s no-op when the package is already present.
BOOTSTRAP_PACKAGES: List[str] = ["statsmodels"]

# Predeclared repair trigger set (Plan A.6.4 / E.3 W2).
REPAIR_TRIGGERS = frozenset(
    {
        "validator_rejection",
        "sandbox_runtime_error",
        "sandbox_timeout",
        "summary_json_parse_error",
    }
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class RoundRecord:
    """Outcome of a single LLM → validate → sandbox round."""

    round_num: int
    llm_raw: str = ""
    llm_latency_ms: int = 0
    llm_tokens_in: Optional[int] = None
    llm_tokens_out: Optional[int] = None
    json_schema_valid: bool = False
    parsed: Optional[Dict[str, Any]] = None
    validator_pass: bool = False
    validator_fail_reason: Optional[str] = None
    sandbox_success: bool = False
    sandbox_stdout: str = ""
    sandbox_stderr: str = ""
    sandbox_exception_type: Optional[str] = None
    sandbox_timeout: bool = False
    chart_exists: bool = False
    chart_bytes: Optional[bytes] = None
    summary_emitted: bool = False
    summary_parsed: Optional[Dict[str, Any]] = None
    elapsed_ms: int = 0

    def is_successful(self) -> bool:
        """Round fully succeeded: code ran, sandbox clean, summary line present.

        A sandbox-successful round that completely dropped the required
        ANALYSIS_SUMMARY_JSON line is NOT a success — the frontend
        would render empty key_findings and the repair loop never got
        to re-request the line. Round classification is intentionally
        asymmetric per finding severity:

          summary_emitted=False  → fire repair (model forgot the line)
          summary_emitted=True
            + summary_parsed=None → soft success (model tried, JSON
              malformed; degrade to empty key_findings but keep the
              chart + analysis prose. Better UX than a "failed"
              response over a JSON formatting nit).

        Codex review 2026-04-18 originally flagged both cases as bugs;
        we adopt this middle ground after the v4 gate rerun showed two
        cases where the model emitted a malformed JSON line but
        produced a perfectly good chart — failing them would throw
        away working output over a cosmetic parse issue.
        """
        if not self.parsed:
            return False
        if self.parsed.get("status") == "unanswerable":
            # Unanswerable is a terminal success, not a failure to repair
            return True
        if not (self.validator_pass and self.sandbox_success):
            return False
        if not self.summary_emitted:
            # Model completely omitted the summary marker → repair-worthy.
            return False
        return True


@dataclass
class PlanExecutionResult:
    """Public return type of run_agentic_analysis()."""

    success: bool
    status: str  # "ok" | "unanswerable" | "error"
    rounds: List[RoundRecord] = field(default_factory=list)
    repair_triggered: bool = False
    repair_trigger_type: Optional[str] = None
    repair_recovered: Optional[bool] = None
    time_budget_exhausted: bool = False
    final_code: Optional[str] = None
    final_plan: Optional[Dict[str, Any]] = None
    final_stdout: str = ""
    final_chart_bytes: Optional[bytes] = None
    final_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    total_elapsed_s: float = 0.0
    # Aggregated across all rounds; None when no rounds reported usage
    # (e.g., tests with injected callers, or error paths that returned
    # before the LLM call completed).
    total_tokens_in: Optional[int] = None
    total_tokens_out: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializable view. Omits large binary payload (chart_bytes)."""
        data = asdict(self)
        # Strip chart_bytes from each round and the top-level final_chart_bytes;
        # keep booleans indicating presence.
        data["final_chart_present"] = self.final_chart_bytes is not None
        data["final_chart_bytes"] = None
        for r in data.get("rounds", []):
            r["chart_present"] = r.get("chart_bytes") is not None
            r["chart_bytes"] = None
        return data


ProgressCallback = Callable[[str, str, float, str], None]


# ---------------------------------------------------------------------------
# Sandbox runner (with bootstrap pip install)
# ---------------------------------------------------------------------------


async def run_sandbox(
    code: str,
    csv_files: Dict[str, bytes],
    timeout_s: int = 60,
    bootstrap_packages: Optional[List[str]] = None,
) -> ExecutionResult:
    """Run ``code`` in a fresh E2B sandbox, installing bootstrap packages first.

    Distinct from ``spike_harness.run_sandbox`` (no bootstrap) so the V1
    spike runner is untouched and monkeypatch targets stay stable in
    ``tests/unit/test_agentic_loop.py`` (patches ``agentic_loop.run_sandbox``).

    The bootstrap step runs ``pip install -q <packages>`` inside the
    sandbox before user code executes. `pip install -q` is idempotent:
    no-op when the package is already present (E2B default image cases).
    When missing (forecast-family cases needing statsmodels), this
    closes the W6 infra gap at ~10-20s cold-install cost per sandbox.

    Budget accounting: the bootstrap install is counted against the
    caller's ``timeout_s``. Callers budgeting ``timeout_s`` for user
    code only must pad accordingly.
    """
    import time as _time

    from backend.config import settings

    packages = list(bootstrap_packages or BOOTSTRAP_PACKAGES)

    try:
        from e2b_code_interpreter import Sandbox
    except ImportError as exc:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=str(exc),
            error=f"e2b-code-interpreter not installed: {exc!s}",
            execution_time_s=0.0,
            output_files={},
        )

    if not settings.e2b_api_key:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr="E2B_API_KEY not configured",
            error="provider_misconfigured",
            execution_time_s=0.0,
            output_files={},
        )

    start = _time.monotonic()
    sbx = None
    try:
        sbx = await asyncio.to_thread(Sandbox.create, api_key=settings.e2b_api_key)

        # Bootstrap: pip install any packages the sandbox might be missing.
        # Run synchronously in a thread so event loop stays responsive.
        if packages:
            pkg_args = " ".join(packages)
            bootstrap_code = (
                "import subprocess, sys\n"
                f"r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', {', '.join(repr(p) for p in packages)}], "
                "capture_output=True, text=True, timeout=90)\n"
                "if r.returncode != 0:\n"
                "    print('BOOTSTRAP_PIP_FAIL:' + r.stderr[-400:])\n"
                "else:\n"
                f"    print('BOOTSTRAP_PIP_OK:{pkg_args}')\n"
            )
            try:
                await asyncio.to_thread(
                    sbx.run_code, bootstrap_code, timeout=BOOTSTRAP_BUDGET_S
                )
            except Exception as exc:  # noqa: BLE001 — bootstrap failure is non-fatal
                logger.warning("bootstrap pip install raised: %s", exc)
                # Continue anyway — user code will fail naturally on
                # ModuleNotFoundError if the package was actually needed.

        # Upload CSVs into /workspace and /home/user (matches prod paths).
        if csv_files:
            for name, content in csv_files.items():
                await asyncio.to_thread(sbx.files.write, f"/workspace/{name}", content)
                await asyncio.to_thread(sbx.files.write, f"/home/user/{name}", content)

        # Run user code.
        execution = await asyncio.to_thread(
            sbx.run_code, code, timeout=float(timeout_s)
        )

        stdout_parts: List[str] = []
        stderr_parts: List[str] = []
        if hasattr(execution, "logs") and execution.logs:
            stdout_parts = execution.logs.stdout or []
            stderr_parts = execution.logs.stderr or []
        stdout = "".join(stdout_parts) if stdout_parts else (execution.text or "")
        stderr = "".join(stderr_parts)
        error_msg: Optional[str] = None
        if execution.error:
            err = execution.error
            error_msg = str(getattr(err, "traceback", None) or err)
            if not stderr:
                stderr = error_msg

        # Collect generated files (chart PNGs, mainly).
        output_files: Dict[str, bytes] = {}
        try:
            entries = await asyncio.to_thread(sbx.files.list, "/workspace")
            for entry in entries:
                name = getattr(entry, "name", None)
                if not name:
                    continue
                if not name.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".svg", ".html", ".pdf")
                ):
                    continue
                try:
                    content = await asyncio.to_thread(
                        sbx.files.read, f"/workspace/{name}", format="bytes"
                    )
                    if content:
                        output_files[name] = content
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001 — download is best-effort
            pass

        return ExecutionResult(
            success=error_msg is None,
            stdout=stdout,
            stderr=stderr,
            error=error_msg,
            execution_time_s=_time.monotonic() - start,
            output_files=output_files,
        )
    except Exception as exc:  # noqa: BLE001 — surface any sandbox-level failure
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=str(exc)[:500],
            error=f"{type(exc).__name__}: {exc!s}",
            execution_time_s=_time.monotonic() - start,
            output_files={},
        )
    finally:
        if sbx is not None:
            try:
                await asyncio.to_thread(sbx.kill)
            except Exception:  # noqa: BLE001 — cleanup best-effort
                pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


# Hard cap on dataset size for the agentic path. Beyond this, _load_once
# raises and run_agentic_analysis returns an error result — analyze_query
# then falls back transparently to the deterministic path. Demo-sized
# capstone CSVs are single-digit MB; 100MB is a generous ceiling.
MAX_DATASET_BYTES: int = 100 * 1024 * 1024


def _load_once(data_file_path: str) -> Tuple[Any, bytes]:
    """Read the file once, return (dataframe, raw_bytes).

    Replaces the prior `load_dataframe(path) + Path(path).read_bytes()`
    pair which read the file 2-3 times (load_dataframe itself re-reads
    internally). We do one disk read, parse the bytes via BytesIO for
    pandas, and hand the same buffer to the sandbox upload path.

    Mirrors load_dataframe's encoding fallback chain for CSVs, falls
    back to the original load_dataframe for unsupported types we don't
    want to reimplement (JSON, Parquet later).

    Raises ValueError for files larger than MAX_DATASET_BYTES so the
    API worker doesn't try to hold a 500MB buffer in memory.
    """
    import pandas as pd  # local import to keep module import cheap
    from io import BytesIO

    path = Path(data_file_path)
    size = path.stat().st_size
    if size > MAX_DATASET_BYTES:
        raise ValueError(
            f"Dataset exceeds agentic path size cap "
            f"({size} > {MAX_DATASET_BYTES} bytes). Use deterministic path."
        )

    raw = path.read_bytes()
    name_lower = data_file_path.lower()

    if name_lower.endswith(".csv"):
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                df = pd.read_csv(BytesIO(raw), encoding=enc, sep=None, engine="python")
                return df, raw
            except UnicodeDecodeError:
                continue
            except pd.errors.ParserError:
                try:
                    df = pd.read_csv(BytesIO(raw), encoding=enc)
                    return df, raw
                except UnicodeDecodeError:
                    continue
        raise ValueError(f"Could not decode CSV: {data_file_path}")

    if name_lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(BytesIO(raw))
        return df, raw

    # Uncommon types — delegate to the existing helper. Slightly less
    # efficient (it re-reads from disk) but avoids reimplementing the
    # JSON/other paths here. The page cache should keep this cheap.
    df = load_dataframe(data_file_path)
    return df, raw


def _classify_repair_trigger(record: RoundRecord) -> Optional[str]:
    """Map a failed round to one of the predeclared repair trigger types.

    Returns None when the round either succeeded, claimed 'unanswerable'
    (no repair), or failed in a way not on the predeclared list.
    """
    if record.parsed is None or not record.json_schema_valid:
        return "summary_json_parse_error"
    if record.parsed.get("status") == "unanswerable":
        return None  # respect the model's declaration
    if record.parsed.get("python_code") is None:
        # status=ok but no code → schema violation → treat as parse error
        return "summary_json_parse_error"
    if not record.validator_pass:
        return "validator_rejection"
    if record.sandbox_timeout:
        return "sandbox_timeout"
    if record.sandbox_success and not record.summary_emitted:
        # Sandbox ran clean but model completely forgot the required
        # ANALYSIS_SUMMARY_JSON line. Fires summary_json_parse_error so
        # round 2 gets a chance to re-emit the summary (Codex 2026-04-18).
        # Malformed-but-emitted JSON is treated as soft success by
        # is_successful — we keep the chart rather than fail over nits.
        return "summary_json_parse_error"
    if not record.sandbox_success:
        return "sandbox_runtime_error"
    return None  # round was actually successful


async def _run_one_round(
    round_num: int,
    full_prompt: str,
    csv_bytes: bytes,
    csv_filename: str,
    llm_budget_s: float,
    sandbox_budget_s: float,
    llm_caller: Callable[[str], Awaitable[str]],
) -> RoundRecord:
    """Execute LLM → parse → validate → sandbox for a single round.

    Both LLM and sandbox are wrapped in per-stage asyncio timeouts so a
    single stalled call can't blow the total budget of the outer loop.
    """
    rec = RoundRecord(round_num=round_num)
    t0 = time.monotonic()

    # LLM
    try:
        raw = await asyncio.wait_for(llm_caller(full_prompt), timeout=llm_budget_s)
        rec.llm_raw = raw
    except asyncio.TimeoutError:
        rec.llm_raw = ""
        rec.sandbox_exception_type = f"LLM timeout after {llm_budget_s:.0f}s"
        rec.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return rec
    except Exception as exc:  # noqa: BLE001
        rec.sandbox_exception_type = f"LLM error: {type(exc).__name__}: {exc!s}"
        rec.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return rec

    rec.llm_latency_ms = int((time.monotonic() - t0) * 1000)

    # Token usage — populated only when the default Zhipu caller is in
    # use (see _default_glm5_caller). Injected test callers leave the
    # slot untouched, so tokens stay None in unit tests by design.
    rec.llm_tokens_in = _last_call_usage.get("input")
    rec.llm_tokens_out = _last_call_usage.get("output")
    # Clear so a subsequent round in the same request can't accidentally
    # inherit the prior round's counts if that round's caller bypasses
    # the default (e.g., a future hybrid-caller path).
    _last_call_usage["input"] = None
    _last_call_usage["output"] = None

    # Parse
    parsed = parse_json_response(raw)
    if parsed is None:
        rec.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return rec
    rec.json_schema_valid = True
    rec.parsed = parsed

    # Unanswerable: short-circuit, do not execute
    if parsed.get("status") == "unanswerable":
        rec.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return rec

    code = parsed.get("python_code")
    if not code:
        rec.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return rec

    # Validate
    outcome = validate_code(code)
    rec.validator_pass = outcome.ok
    rec.validator_fail_reason = outcome.reason
    if not outcome.ok:
        rec.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return rec

    # Sandbox (budgeted). `sandbox_budget_s` is the budget for the USER
    # code only; bootstrap pip install inside run_sandbox has its own
    # BOOTSTRAP_BUDGET_S wall. The outer asyncio.wait_for must cover
    # BOTH, plus a small slack for file upload and result download,
    # otherwise a cold-sandbox run spending most of its budget on real
    # work gets preempted and misclassified as sandbox_timeout.
    outer_wait_s = BOOTSTRAP_BUDGET_S + sandbox_budget_s + 5
    try:
        exec_result = await asyncio.wait_for(
            run_sandbox(
                code=code,
                csv_files={csv_filename: csv_bytes},
                timeout_s=int(sandbox_budget_s),
            ),
            timeout=outer_wait_s,
        )
        rec.sandbox_success = exec_result.success
        rec.sandbox_stdout = exec_result.stdout
        rec.sandbox_stderr = exec_result.stderr
        rec.sandbox_exception_type = exec_result.error
        if exec_result.execution_time_s >= sandbox_budget_s:
            rec.sandbox_timeout = True

        chart = (exec_result.output_files or {}).get("analysis_chart.png")
        if chart:
            rec.chart_exists = len(chart) > 0
            rec.chart_bytes = chart if rec.chart_exists else None

        emitted, parsed_ok, obj = extract_summary_json(exec_result.stdout)
        rec.summary_emitted = emitted
        if parsed_ok:
            rec.summary_parsed = obj
    except asyncio.TimeoutError:
        rec.sandbox_timeout = True
        rec.sandbox_exception_type = "sandbox asyncio timeout"
    except Exception as exc:  # noqa: BLE001
        rec.sandbox_exception_type = f"{type(exc).__name__}: {exc!s}"

    rec.elapsed_ms = int((time.monotonic() - t0) * 1000)
    return rec


def _build_user_prompt(filename: str, question: str, profile: Dict[str, Any]) -> str:
    """Render the round-1 user prompt via .replace() substitution.

    Symmetric with `_build_repair_prompt`: avoids `str.format_map` so
    slot values (specifically `column_profile_table`, which embeds raw
    sample cell values) can contain arbitrary `{word}` text without
    tripping render_prompt's leftover-placeholder guard. A CSV cell
    literally reading "hello {name}" would otherwise blow up the
    agentic path with a ValueError and silently fall back to
    deterministic for that dataset (Codex review finding, 2026-04-18).
    """
    slots: Dict[str, str] = {
        "filename": str(filename),
        "n_rows": str(profile["n_rows"]),
        "n_cols": str(profile["n_cols"]),
        "column_profile_table": str(profile["column_profile_table"]),
        "question": str(question),
    }
    text = USER_TEMPLATE_PATH.read_text(encoding="utf-8")
    for name, value in slots.items():
        text = text.replace("{" + name + "}", value)
    return text


def _build_repair_prompt(
    filename: str,
    question: str,
    profile: Dict[str, Any],
    previous: RoundRecord,
    trigger: str,
) -> str:
    """Render the repair prompt without going through str.format_map.

    The repair prompt embeds the model's previous round-1 output
    (``previous_json``) and its failure detail verbatim. Both commonly
    contain Python f-strings like ``f"Peak month: {peak_month}"`` that
    would trip ``render_prompt``'s leftover-placeholder guard. V1 never
    hit this because V1 has no repair loop. Using ``.replace()``
    substitution sidesteps format_map's brace-handling entirely — slot
    values can now contain arbitrary ``{word}`` text safely, and the
    static template still has no way to reference an unfilled slot
    because every known slot is explicitly substituted below.
    """
    previous_json = {
        "status": (previous.parsed or {}).get("status"),
        "business_goal": (previous.parsed or {}).get("business_goal"),
        "analysis_plan": (previous.parsed or {}).get("analysis_plan"),
        "assumptions": (previous.parsed or {}).get("assumptions"),
        "python_code": (previous.parsed or {}).get("python_code"),
    }
    failure_detail = (
        previous.validator_fail_reason
        or previous.sandbox_stderr
        or previous.sandbox_exception_type
        or "unspecified failure"
    )

    slots: Dict[str, str] = {
        "repair_trigger_type": str(trigger),
        "failure_detail": str(failure_detail),
        "question": str(question),
        "previous_json": json.dumps(previous_json, ensure_ascii=False, indent=2),
        "filename": str(filename),
        "n_rows": str(profile["n_rows"]),
        "n_cols": str(profile["n_cols"]),
        "column_profile_table": str(profile["column_profile_table"]),
    }

    text = REPAIR_TEMPLATE_PATH.read_text(encoding="utf-8")
    for name, value in slots.items():
        text = text.replace("{" + name + "}", value)
    return text


def _compose_full_prompt(system_text: str, user_text: str) -> str:
    return f"[SYSTEM]\n{system_text}\n\n[USER]\n{user_text}"


# ---------------------------------------------------------------------------
# LLM response cache (deterministic-by-content fix for non-reproducibility)
# ---------------------------------------------------------------------------
#
# Empirical finding 2026-05-28: Zhipu temperature=0.0 does NOT actually
# yield byte-identical code across runs (verified by SSE repro eval,
# 6 cases × 3 runs, 0% byte-level code reproducibility). Provider's
# greedy decoding is sufficient for "same shape" but not "same bytes" —
# import order, intermediate variable names, etc. drift.
#
# Cache key is the full prompt + sampling params. Same input → same
# cached response → byte-identical code → byte-identical chart (when
# combined with the random_state=42 mandate in the prompt). Bounded
# size with LRU eviction so a long-running demo session doesn't grow
# memory unbounded.
#
# Disable via DATA_ANALYSIS_LLM_CACHE=false (e.g. for benchmarking the
# raw provider behavior). Max size via DATA_ANALYSIS_LLM_CACHE_SIZE.

_LLM_CACHE_ENABLED: bool = (
    os.getenv("DATA_ANALYSIS_LLM_CACHE", "true").lower() == "true"
)
_LLM_CACHE_MAX_ENTRIES: int = int(
    os.getenv("DATA_ANALYSIS_LLM_CACHE_SIZE", "256")
)

# Two values per key: response text, AND the captured token usage dict
# at cache-store time — so a cache hit can replay the same token-count
# metrics into _last_call_usage instead of leaving them empty. Stored
# as a tuple (response_text, usage_dict) to keep one OrderedDict.
_llm_response_cache: "OrderedDict[str, Tuple[str, Dict[str, Optional[int]]]]" = (
    OrderedDict()
)

# Counters for observability — surfaced via cache_stats() and useful
# in tests to assert "second identical call was a hit, not a miss".
_cache_stats: Dict[str, int] = {"hits": 0, "misses": 0, "stores": 0}


def _cache_key(prompt: str, sampling: Dict[str, Any]) -> str:
    payload = prompt + "\x00" + json.dumps(sampling, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cache_stats() -> Dict[str, Any]:
    """Return current cache hit/miss/store counters + size. For ops + tests."""
    return {
        **_cache_stats,
        "size": len(_llm_response_cache),
        "max_size": _LLM_CACHE_MAX_ENTRIES,
        "enabled": _LLM_CACHE_ENABLED,
    }


def reset_cache() -> None:
    """Wipe cache + counters. Tests call this between cases; ops can call
    via a debug endpoint if the user wants fresh LLM responses."""
    _llm_response_cache.clear()
    _cache_stats["hits"] = 0
    _cache_stats["misses"] = 0
    _cache_stats["stores"] = 0


def _default_glm5_caller() -> Callable[[str], Awaitable[str]]:
    """Return an async wrapper around the Zhipu client.

    The client's generate() is synchronous; we offload it to a thread so
    the event loop stays responsive and asyncio.wait_for can interrupt it.

    Captures ZhipuClient.last_usage into the module-level
    ``_last_call_usage`` slot so ``_run_one_round`` can attach token
    counts to the RoundRecord without changing the caller signature
    (keeping dependency injection for tests untouched).

    Wrapped with a content-addressed response cache (see _LLM_CACHE_ENABLED).
    Same prompt → same cached response → byte-identical generated code.
    """
    from backend.services.llm_integration.llm_client import LLMClientFactory

    async def _call(prompt: str) -> str:
        # Cache lookup (must mirror the cache-store path's usage handling).
        if _LLM_CACHE_ENABLED:
            key = _cache_key(prompt, SAMPLING)
            cached = _llm_response_cache.get(key)
            if cached is not None:
                # LRU touch.
                _llm_response_cache.move_to_end(key)
                _cache_stats["hits"] += 1
                text_cached, usage_cached = cached
                _last_call_usage["input"] = usage_cached.get("input")
                _last_call_usage["output"] = usage_cached.get("output")
                logger.info(
                    "LLM cache HIT (key=%s, size=%d/%d)",
                    key[:12], len(_llm_response_cache), _LLM_CACHE_MAX_ENTRIES,
                )
                return text_cached
            _cache_stats["misses"] += 1

        # Real call.
        client = LLMClientFactory.create_client("zhipu")
        text = await asyncio.to_thread(
            client.generate,
            prompt,
            **SAMPLING,
        )
        # Snapshot usage into the shared slot — read by _run_one_round
        # right after it awaits the caller. Safe under asyncio because
        # a single round awaits exactly one caller call sequentially.
        usage = getattr(client, "last_usage", {}) or {}
        _last_call_usage["input"] = usage.get("input_tokens")
        _last_call_usage["output"] = usage.get("output_tokens")

        # Cache store with LRU eviction.
        if _LLM_CACHE_ENABLED:
            key = _cache_key(prompt, SAMPLING)
            _llm_response_cache[key] = (
                text,
                {"input": _last_call_usage["input"], "output": _last_call_usage["output"]},
            )
            _cache_stats["stores"] += 1
            while len(_llm_response_cache) > _LLM_CACHE_MAX_ENTRIES:
                evicted_key, _ = _llm_response_cache.popitem(last=False)
                logger.debug("LLM cache evicted oldest entry %s", evicted_key[:12])
            logger.info(
                "LLM cache STORE (key=%s, size=%d/%d)",
                key[:12], len(_llm_response_cache), _LLM_CACHE_MAX_ENTRIES,
            )

        return text

    return _call


# Module-level slot holding the most recent LLM call's token usage.
# Populated only when the default Zhipu caller is used; stays empty
# when tests inject a stub caller. _run_one_round reads this right
# after the caller returns so there's no cross-call contamination.
_last_call_usage: Dict[str, Optional[int]] = {"input": None, "output": None}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_agentic_analysis(
    question: str,
    data_file_path: str,
    dataset_metadata: Optional[Dict[str, Any]] = None,
    on_progress: Optional[ProgressCallback] = None,
    total_budget_s: float = DEFAULT_TOTAL_BUDGET_S,
    llm_caller: Optional[Callable[[str], Awaitable[str]]] = None,
) -> PlanExecutionResult:
    """Run the bounded 2-pass agentic loop.

    Args:
        question: user's analysis question
        data_file_path: local path to the CSV (uploaded to sandbox as /workspace/<name>)
        dataset_metadata: pre-extracted metadata (unused here except for filename hint;
            profile is re-extracted locally because agentic loop needs its own schema)
        on_progress: optional SSE-style callback (stage, status, progress, detail)
        total_budget_s: hard wall-clock cap. Default 45s per Plan E.3 W2.
        llm_caller: dependency injection for tests. Default uses Zhipu via LLMClientFactory.

    Returns:
        PlanExecutionResult. success=False with time_budget_exhausted=True when
        the budget blows mid-flight; success=False with error_message otherwise.
    """
    caller = llm_caller if llm_caller is not None else _default_glm5_caller()

    def _emit(stage: str, status: str, progress: float, detail: str) -> None:
        if on_progress is not None:
            try:
                on_progress(stage, status, progress, detail)
            except Exception as exc:  # noqa: BLE001
                logger.warning("on_progress callback failed: %s", exc)

    loop_start = time.monotonic()
    filename = Path(data_file_path).name

    # Load profile — single read for both pandas and sandbox upload.
    #
    # Before this refactor the agentic path read the file up to 3x:
    # spike_harness.load_dataframe itself re-reads internally, and then
    # run_agentic_analysis called Path.read_bytes() again for the
    # sandbox upload. With USE_GLM5_AGENT default=true that put every
    # upload through multiple full-file reads in the API worker, which
    # was a latency + OOM risk on large CSVs (Codex review finding,
    # 2026-04-18). _load_once reads bytes once and uses BytesIO for
    # the dataframe, sharing the same buffer with the sandbox upload.
    _emit("code_generation", "running", 0.22, "Analyzing with GLM-4.7...")
    try:
        df, csv_bytes = _load_once(data_file_path)
    except Exception as exc:  # noqa: BLE001
        return PlanExecutionResult(
            success=False,
            status="error",
            error_message=f"Failed to load dataset: {exc!s}",
            total_elapsed_s=time.monotonic() - loop_start,
        )
    profile = extract_profile(df, filename=filename, total_rows=len(df))
    system_text = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    # ------- Round 1 -------
    user_text_r1 = _build_user_prompt(filename, question, profile)
    full_prompt_r1 = _compose_full_prompt(system_text, user_text_r1)

    elapsed_before_r1 = time.monotonic() - loop_start
    r1_total_remaining = total_budget_s - elapsed_before_r1
    r1_llm_budget = min(DEFAULT_ROUND1_LLM_BUDGET_S, max(1.0, r1_total_remaining - 1.0))
    r1_sandbox_budget = min(
        DEFAULT_ROUND1_SANDBOX_BUDGET_S,
        max(1.0, r1_total_remaining - r1_llm_budget - 1.0),
    )

    r1 = await _run_one_round(
        round_num=1,
        full_prompt=full_prompt_r1,
        csv_bytes=csv_bytes,
        csv_filename=filename,
        llm_budget_s=r1_llm_budget,
        sandbox_budget_s=r1_sandbox_budget,
        llm_caller=caller,
    )

    elapsed_after_r1 = time.monotonic() - loop_start

    # Happy path or terminal unanswerable → return
    if r1.is_successful():
        _emit("code_generation", "completed", 0.40, "Plan generated")
        _emit("security_check", "completed", 0.50, "Validated (agentic)")
        _emit("sandbox_execution", "completed", 0.85, "Executed")
        return _finalize(r1, [r1], time.monotonic() - loop_start)

    # Decide: repair or not?
    trigger = _classify_repair_trigger(r1)

    if trigger is None or trigger not in REPAIR_TRIGGERS:
        # Either model declared unanswerable (handled above as success), or
        # failure mode is outside the predeclared trigger set. No repair.
        _emit("code_generation", "failed", 0.35, f"Generation failed: {r1.sandbox_exception_type or 'unknown'}")
        return _finalize(r1, [r1], time.monotonic() - loop_start, repair_triggered=False)

    if elapsed_after_r1 >= REPAIR_DECISION_CUTOFF_S:
        # Too late to repair without risking total-budget blow
        _emit("code_generation", "failed", 0.35, "Time budget tight; skipping repair")
        return _finalize(
            r1, [r1], time.monotonic() - loop_start,
            repair_triggered=False,
        )

    # ------- Round 2 (repair) -------
    _emit("code_generation", "running", 0.32, "Refining approach...")
    remaining = total_budget_s - elapsed_after_r1
    r2_llm_budget = min(DEFAULT_ROUND2_LLM_BUDGET_S, max(1.0, remaining - 3.0))
    r2_sandbox_budget = max(1.0, remaining - r2_llm_budget - 1.0)

    user_text_r2 = _build_repair_prompt(filename, question, profile, r1, trigger)
    full_prompt_r2 = _compose_full_prompt(system_text, user_text_r2)

    r2 = await _run_one_round(
        round_num=2,
        full_prompt=full_prompt_r2,
        csv_bytes=csv_bytes,
        csv_filename=filename,
        llm_budget_s=r2_llm_budget,
        sandbox_budget_s=r2_sandbox_budget,
        llm_caller=caller,
    )

    total_elapsed = time.monotonic() - loop_start
    budget_exhausted = total_elapsed > total_budget_s

    if r2.is_successful():
        _emit("code_generation", "completed", 0.40, "Plan refined successfully")
        _emit("security_check", "completed", 0.50, "Validated (agentic)")
        _emit("sandbox_execution", "completed", 0.85, "Executed")
        return _finalize(
            r2, [r1, r2], total_elapsed,
            repair_triggered=True, repair_trigger_type=trigger,
            repair_recovered=True,
        )

    # Both rounds failed
    _emit("sandbox_execution", "failed", 0.55, "Analysis could not complete")
    return _finalize(
        r2, [r1, r2], total_elapsed,
        repair_triggered=True, repair_trigger_type=trigger,
        repair_recovered=False,
        time_budget_exhausted=budget_exhausted,
    )


def _finalize(
    terminal: RoundRecord,
    rounds: List[RoundRecord],
    total_elapsed_s: float,
    *,
    repair_triggered: bool = False,
    repair_trigger_type: Optional[str] = None,
    repair_recovered: Optional[bool] = None,
    time_budget_exhausted: bool = False,
) -> PlanExecutionResult:
    """Build the final PlanExecutionResult from the terminal round."""
    parsed = terminal.parsed or {}
    status_raw = parsed.get("status")

    if status_raw == "unanswerable":
        status = "unanswerable"
        success = True  # graceful non-answer is still a successful flow
        error_message = parsed.get("reason")
    elif terminal.is_successful():
        status = "ok"
        success = True
        error_message = None
    else:
        status = "error"
        success = False
        error_message = (
            terminal.validator_fail_reason
            or terminal.sandbox_exception_type
            or terminal.sandbox_stderr[:500]
            or "Analysis failed"
        )

    # Aggregate token usage across rounds. None if no round populated
    # usage (injected-caller tests, or pre-LLM error paths).
    tok_in_vals = [r.llm_tokens_in for r in rounds if r.llm_tokens_in is not None]
    tok_out_vals = [r.llm_tokens_out for r in rounds if r.llm_tokens_out is not None]
    total_tokens_in = sum(tok_in_vals) if tok_in_vals else None
    total_tokens_out = sum(tok_out_vals) if tok_out_vals else None

    return PlanExecutionResult(
        success=success,
        status=status,
        rounds=rounds,
        repair_triggered=repair_triggered,
        repair_trigger_type=repair_trigger_type,
        repair_recovered=repair_recovered,
        time_budget_exhausted=time_budget_exhausted,
        final_code=parsed.get("python_code"),
        final_plan={
            k: parsed.get(k)
            for k in ("business_goal", "analysis_plan", "assumptions", "produces_chart", "reason", "suggestion")
        } if parsed else None,
        final_stdout=terminal.sandbox_stdout,
        final_chart_bytes=terminal.chart_bytes,
        final_summary=terminal.summary_parsed,
        error_message=error_message,
        total_elapsed_s=total_elapsed_s,
        total_tokens_in=total_tokens_in,
        total_tokens_out=total_tokens_out,
    )
