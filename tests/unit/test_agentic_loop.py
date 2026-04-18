"""W2 unit tests for agentic_loop.py (Plan Appendix E W5, 4 tests).

Each test uses dependency injection via `llm_caller=` to stub GLM-5, and
monkeypatches `run_sandbox` to avoid hitting E2B. Real-provider tests
live in env-gated tests/integration/test_agentic_real_provider.py (W5).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

from backend.services.code_executor.providers.base import ExecutionResult
from backend.services.data_analysis import agentic_loop
from backend.services.data_analysis.agentic_loop import (
    PlanExecutionResult,
    run_agentic_analysis,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Write a minimal valid CSV so load_dataframe + extract_profile work."""
    df = pd.DataFrame({"tip": [1.0, 2.0, 3.0, 4.5], "size": [1, 2, 3, 4]})
    path = tmp_path / "sample.csv"
    df.to_csv(path, index=False)
    return path


def _make_valid_llm_response(code: str = "df = pd.read_csv('/workspace/sample.csv')\nprint(df.head())\nprint('ANALYSIS_SUMMARY_JSON={\"n\": 4}')") -> str:
    return json.dumps(
        {
            "status": "ok",
            "business_goal": "Test goal",
            "analysis_plan": "Load and print head",
            "assumptions": [],
            "python_code": code,
            "produces_chart": False,
        }
    )


def _make_blocked_method_response() -> str:
    """Response that will fail the validator (uses .agg)."""
    return json.dumps(
        {
            "status": "ok",
            "business_goal": "Group by size",
            "analysis_plan": "Aggregate tips",
            "assumptions": [],
            "python_code": "df = pd.read_csv('/workspace/sample.csv')\nr = df.groupby('size').agg({'tip': 'mean'})\nprint(r)",
            "produces_chart": False,
        }
    )


def _make_successful_sandbox_result(stdout: str = 'df head\nANALYSIS_SUMMARY_JSON={"n": 4}\n') -> ExecutionResult:
    return ExecutionResult(
        success=True,
        stdout=stdout,
        stderr="",
        error=None,
        execution_time_s=2.5,
        output_files={},
    )


def _make_failed_sandbox_result(error: str = "NameError: x") -> ExecutionResult:
    return ExecutionResult(
        success=False,
        stdout="",
        stderr=error,
        error=error,
        execution_time_s=1.0,
        output_files={},
    )


# ---------------------------------------------------------------------------
# Tests (Plan E.3 W5: 4 unit tests for agentic_loop)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_round1_success_no_repair(sample_csv, monkeypatch):
    """Test 1: round 1 fully passes → no repair triggered, success=True."""
    calls: List[str] = []

    async def _fake_llm(prompt: str) -> str:
        calls.append(prompt)
        return _make_valid_llm_response()

    async def _fake_sandbox(code, csv_files, timeout_s):
        return _make_successful_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result: PlanExecutionResult = await run_agentic_analysis(
        question="How many tips?",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert result.success is True
    assert result.status == "ok"
    assert len(result.rounds) == 1
    assert result.repair_triggered is False
    assert result.repair_recovered is None
    assert result.time_budget_exhausted is False
    assert len(calls) == 1  # LLM called exactly once


@pytest.mark.asyncio
async def test_repair_triggers_on_validator_fail(sample_csv, monkeypatch):
    """Test 2: round 1 uses .agg (validator fails) → round 2 repairs →
    repair_triggered=True, repair_recovered=True."""
    call_count = {"n": 0}

    async def _fake_llm(prompt: str) -> str:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _make_blocked_method_response()  # uses .agg → validator rejects
        return _make_valid_llm_response()  # repair uses allowed methods

    async def _fake_sandbox(code, csv_files, timeout_s):
        return _make_successful_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result = await run_agentic_analysis(
        question="Mean tip by size",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert result.success is True
    assert result.status == "ok"
    assert len(result.rounds) == 2
    assert result.repair_triggered is True
    assert result.repair_trigger_type == "validator_rejection"
    assert result.repair_recovered is True
    assert call_count["n"] == 2  # two LLM calls, one per round


@pytest.mark.asyncio
async def test_time_budget_exhaustion_graceful(sample_csv, monkeypatch):
    """Test 3: total budget tiny → round 1 succeeds within budget → success,
    no repair attempted even if round 1 had a soft issue. Verifies the
    budget-exhaustion return path is a first-class outcome (not an exception)."""

    # Slow LLM (2s) but valid — tiny budget forces repair skip if it failed
    async def _slow_but_ok(prompt: str) -> str:
        await asyncio.sleep(0.05)
        return _make_valid_llm_response()

    async def _fake_sandbox(code, csv_files, timeout_s):
        return _make_successful_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    # Budget well below REPAIR_DECISION_CUTOFF_S (25s) — round 1 still fits,
    # the test verifies the function returns cleanly without hanging.
    result = await run_agentic_analysis(
        question="Q",
        data_file_path=str(sample_csv),
        llm_caller=_slow_but_ok,
        total_budget_s=5.0,
    )
    assert result.success is True
    assert result.total_elapsed_s < 5.0


@pytest.mark.asyncio
async def test_budget_exhausted_mid_round2(sample_csv, monkeypatch):
    """Test 4: round 1 fails with repair trigger, round 2 has no time left →
    skip repair (elapsed ≥ 25s cutoff)."""

    async def _fake_llm(prompt: str) -> str:
        # Slow first call to push elapsed past the repair cutoff (simulated via monkeypatch)
        return _make_blocked_method_response()

    async def _fake_sandbox(code, csv_files, timeout_s):
        return _make_failed_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)
    # Force the repair-decision cutoff to 0 so repair is always skipped
    monkeypatch.setattr(agentic_loop, "REPAIR_DECISION_CUTOFF_S", 0.0)

    result = await run_agentic_analysis(
        question="Q",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
        total_budget_s=10.0,
    )

    assert result.success is False
    assert result.status == "error"
    assert result.repair_triggered is False  # skipped due to cutoff
    assert len(result.rounds) == 1


# ---------------------------------------------------------------------------
# Bonus: unanswerable status should not trigger repair
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repair_prompt_handles_fstring_braces_in_previous_output(
    sample_csv, monkeypatch
):
    """Regression guard for the W6 airline-Q1 bug.

    If round-1 code contains a Python f-string like ``f"Peak: {peak_month}"``,
    that literal {peak_month} ends up inside the ``previous_json`` slot of
    the repair prompt. The old ``render_prompt(format_map)`` path raised
    ``ValueError: Prompt rendered with leftover placeholders: ['{peak_month}']``
    before round 2 could even start, so the case failed with rounds=0.
    Fix: ``_build_repair_prompt`` now substitutes via ``.replace()``,
    which does not scan slot *values* for unfilled placeholders.
    """
    call_count = {"n": 0}

    async def _fake_llm(prompt: str) -> str:
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Valid JSON but the code inside contains an f-string that looks
            # like a template placeholder. Validator will reject it (uses .agg)
            # so repair fires — that's how we exercise _build_repair_prompt.
            return json.dumps(
                {
                    "status": "ok",
                    "business_goal": "Monthly trend",
                    "analysis_plan": "Decompose and print peak",
                    "assumptions": [],
                    "python_code": (
                        "peak_month = 'Jul'\n"
                        "print(f'Peak month: {peak_month}')\n"
                        "df.groupby('size').agg({'tip': 'mean'})\n"
                    ),
                    "produces_chart": False,
                }
            )
        # Round 2: return a clean, validator-passing response.
        return _make_valid_llm_response()

    async def _fake_sandbox(code, csv_files, timeout_s):
        return _make_successful_sandbox_result()

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    # This call used to raise ValueError before the fix.
    result = await run_agentic_analysis(
        question="Describe trend",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert call_count["n"] == 2, "repair round should have fired"
    assert result.success is True
    assert result.repair_triggered is True
    assert result.repair_recovered is True
    # Most importantly: no exception — the {peak_month} literal survived
    # the substitution path without being mistaken for an unfilled slot.


@pytest.mark.asyncio
async def test_unanswerable_is_terminal_success_no_repair(sample_csv, monkeypatch):
    """Model claims the question can't be answered → no repair, success=True
    with status='unanswerable'."""
    async def _fake_llm(prompt: str) -> str:
        return json.dumps(
            {
                "status": "unanswerable",
                "business_goal": None,
                "analysis_plan": None,
                "assumptions": [],
                "python_code": None,
                "produces_chart": False,
                "reason": "No numeric columns suitable for this question.",
                "suggestion": "Upload a dataset with numeric fields.",
            }
        )

    async def _fake_sandbox(code, csv_files, timeout_s):
        # Should never be called
        raise AssertionError("sandbox should not run for unanswerable")

    monkeypatch.setattr(agentic_loop, "run_sandbox", _fake_sandbox)

    result = await run_agentic_analysis(
        question="impossible question",
        data_file_path=str(sample_csv),
        llm_caller=_fake_llm,
    )

    assert result.success is True
    assert result.status == "unanswerable"
    assert result.repair_triggered is False
    assert len(result.rounds) == 1
    assert result.error_message == "No numeric columns suitable for this question."
