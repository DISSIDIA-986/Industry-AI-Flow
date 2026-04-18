"""Agentic CRISP-DM loop for Dynamic Data Analysis (Plan Appendix E, W2).

Bounded 2-pass: round 1 single-shot; if round 1 fails per predeclared trigger
AND total elapsed is still within the repair window, one repair round fires.
No more. Hard total budget of 45s prevents runaway cost/latency.

Seeds from `spike_harness` which was built for this reuse (design B.6).
Reuses `llm_client`, `code_executor.validator`, and E2B provider unchanged.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from backend.services.data_analysis.spike_harness import (
    extract_profile,
    extract_summary_json,
    load_dataframe,
    parse_json_response,
    render_prompt,
    run_sandbox,
    validate_code,
)

logger = logging.getLogger(__name__)

# Prompts ship as committed markdown in the same package (W3).
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
SYSTEM_PROMPT_PATH = PROMPT_DIR / "agentic_v1_system.md"
USER_TEMPLATE_PATH = PROMPT_DIR / "agentic_v1_user_template.md"
REPAIR_TEMPLATE_PATH = PROMPT_DIR / "agentic_v1_repair_template.md"

# Budget constants (Plan E.3 W2).
DEFAULT_TOTAL_BUDGET_S: float = 45.0
REPAIR_DECISION_CUTOFF_S: float = 25.0  # past this, skip repair even on failure
DEFAULT_ROUND1_LLM_BUDGET_S: float = 12.0
DEFAULT_ROUND1_SANDBOX_BUDGET_S: float = 20.0
DEFAULT_ROUND2_LLM_BUDGET_S: float = 10.0

# Sampling (Plan A.6.2).
SAMPLING = {"temperature": 0.2, "top_p": 0.95, "max_tokens": 4096}

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
        """Round fully succeeded: code ran, sandbox clean."""
        if not self.parsed:
            return False
        if self.parsed.get("status") == "unanswerable":
            # Unanswerable is a terminal success, not a failure to repair
            return True
        return self.validator_pass and self.sandbox_success


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
# Internal helpers
# ---------------------------------------------------------------------------


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

    # Sandbox (budgeted)
    try:
        exec_result = await asyncio.wait_for(
            run_sandbox(
                code=code,
                csv_files={csv_filename: csv_bytes},
                timeout_s=int(sandbox_budget_s),
            ),
            timeout=sandbox_budget_s + 5,  # hard asyncio wall 5s past sandbox SLA
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
    text, _, _ = render_prompt(
        str(USER_TEMPLATE_PATH),
        {
            "filename": filename,
            "n_rows": profile["n_rows"],
            "n_cols": profile["n_cols"],
            "column_profile_table": profile["column_profile_table"],
            "question": question,
        },
    )
    return text


def _build_repair_prompt(
    filename: str,
    question: str,
    profile: Dict[str, Any],
    previous: RoundRecord,
    trigger: str,
) -> str:
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
    text, _, _ = render_prompt(
        str(REPAIR_TEMPLATE_PATH),
        {
            "repair_trigger_type": trigger,
            "failure_detail": failure_detail,
            "question": question,
            "previous_json": json.dumps(previous_json, ensure_ascii=False, indent=2),
            "filename": filename,
            "n_rows": profile["n_rows"],
            "n_cols": profile["n_cols"],
            "column_profile_table": profile["column_profile_table"],
        },
    )
    return text


def _compose_full_prompt(system_text: str, user_text: str) -> str:
    return f"[SYSTEM]\n{system_text}\n\n[USER]\n{user_text}"


def _default_glm5_caller() -> Callable[[str], Awaitable[str]]:
    """Return an async wrapper around the Zhipu client.

    The client's generate() is synchronous; we offload it to a thread so
    the event loop stays responsive and asyncio.wait_for can interrupt it.
    """
    from backend.services.llm_integration.llm_client import LLMClientFactory

    async def _call(prompt: str) -> str:
        client = LLMClientFactory.create_client("zhipu")
        return await asyncio.to_thread(
            client.generate,
            prompt,
            **SAMPLING,
        )

    return _call


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

    # Load profile
    _emit("code_generation", "running", 0.22, "Analyzing with GLM-5...")
    try:
        df = load_dataframe(data_file_path)
    except Exception as exc:  # noqa: BLE001
        return PlanExecutionResult(
            success=False,
            status="error",
            error_message=f"Failed to load dataset: {exc!s}",
            total_elapsed_s=time.monotonic() - loop_start,
        )
    profile = extract_profile(df, filename=filename, total_rows=len(df))
    csv_bytes = Path(data_file_path).read_bytes()
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
    )
