"""W5 integration tests: agentic orchestrator + SSE contract + rollback.

Plan Appendix E W5 acceptance — 5 tests covering the wired-up path:

  1. SSE stage sequence matches the 6-node contract end-to-end (drains
     the real PipelineProgressTracker janus queue the production SSE
     endpoint reads from).
  2. Golden: deterministic envelope shape is unchanged by the mere
     presence of the agentic code path (regression guard for W1-W4).
  3. Rollback: flipping USE_GLM5_AGENT mid-session routes to a
     different mode with no shared state leaking between requests.
  4. Degraded: flag on but sandbox probe marked NOT ready → agentic
     branch silently skipped, deterministic path runs, no 503.
  5. Real provider (env-gated): hits Zhipu + E2B for real. Skipped by
     default. Set LIVE_AGENTIC=1 plus ZHIPU_API_KEY and E2B_API_KEY
     to run.

Stubs:
  - run_agentic_analysis: replaced with a coroutine returning a fixed
    PlanExecutionResult + emitting the 3 loop-owned SSE stages.
  - execute_eda / compose_eda_response: replaced with minimal stubs so
    the deterministic path returns a valid envelope without hitting E2B
    or Docker. We care about routing/envelope, not chart rendering.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

from backend.services.data_analysis import data_analysis_agent as daa_module
from backend.services.data_analysis.agentic_loop import (
    PlanExecutionResult,
    RoundRecord,
)
from backend.services.data_analysis.data_analysis_agent import DataAnalysisAgent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {
            "tip": [1.0, 2.0, 3.0, 4.5, 2.8],
            "total_bill": [10.0, 18.0, 21.0, 30.0, 25.0],
            "size": [1, 2, 3, 4, 2],
        }
    )
    path = tmp_path / "tips_sample.csv"
    df.to_csv(path, index=False)
    return path


class _StubExecutionManager:
    """Non-null sentinel so analyze_query's 'no execution provider'
    guard doesn't short-circuit. Deterministic tests stub execute_eda
    directly, so this object's methods are never actually called."""

    def execute_code(self, *args, **kwargs):
        raise AssertionError(
            "execute_code should be stubbed by _install_fake_deterministic"
        )


@pytest.fixture
def agent() -> DataAnalysisAgent:
    a = DataAnalysisAgent.__new__(DataAnalysisAgent)
    a.llm_client = None
    a.code_execution_manager = _StubExecutionManager()
    a.code_executor = None
    return a


def _make_agentic_success(chart_bytes: bytes = b"PNG_STUB") -> PlanExecutionResult:
    rec = RoundRecord(
        round_num=1,
        json_schema_valid=True,
        parsed={
            "status": "ok",
            "business_goal": "Mean tip by party size",
            "analysis_plan": "Group-by + bar chart",
            "produces_chart": True,
            "python_code": "pass",
        },
        validator_pass=True,
        sandbox_success=True,
        sandbox_stdout='ok\nANALYSIS_SUMMARY_JSON={"key_findings": ["size=4 tips highest"]}\n',
        chart_exists=True,
        chart_bytes=chart_bytes,
        summary_emitted=True,
        summary_parsed={"key_findings": ["size=4 tips highest"]},
    )
    return PlanExecutionResult(
        success=True,
        status="ok",
        rounds=[rec],
        final_code="pass",
        final_plan={
            "business_goal": "Mean tip by party size",
            "analysis_plan": "Group-by + bar chart",
            "produces_chart": True,
        },
        final_stdout=rec.sandbox_stdout,
        final_chart_bytes=chart_bytes,
        final_summary={"key_findings": ["size=4 tips highest"]},
        total_elapsed_s=2.71,
    )


def _install_fake_agentic_loop(monkeypatch, fake_result: PlanExecutionResult):
    """Replace run_agentic_analysis with a coroutine that echoes the 3
    loop-owned SSE stages and returns the fixed result."""
    import backend.services.data_analysis.agentic_loop as loop_mod

    async def _fake(**kwargs):
        cb = kwargs.get("on_progress")
        if cb is not None:
            cb("code_generation", "running", 0.22, "Analyzing with GLM-5...")
            cb("code_generation", "completed", 0.40, "Plan generated")
            cb("security_check", "completed", 0.50, "Validated (agentic)")
            cb("sandbox_execution", "completed", 0.85, "Executed")
        return fake_result

    monkeypatch.setattr(loop_mod, "run_agentic_analysis", _fake)


def _install_fake_deterministic(monkeypatch):
    """Stub execute_eda + compose_eda_response so the deterministic path
    returns a legal envelope without hitting E2B/Docker."""
    import backend.services.data_analysis.chart_executor as ce_mod
    import backend.services.data_analysis.report_composer as rc_mod

    def _fake_execute_eda(**kwargs):
        return {
            "success": True,
            "charts": [],
            "output_files": {},
            "stdout": "fake",
            "stderr": "",
            "execution_time": 0.5,
            "code": "# stubbed deterministic snippet",
        }

    def _fake_compose(**kwargs):
        return {
            "success": True,
            "answer": "Stubbed deterministic answer",
            "charts": [],
            "visualizations": [],
            "code": kwargs.get("generated_code") or "",
            "analysis_summary": {"key_findings": [], "rationale": ""},
            "code_generation": {
                "mode": "deterministic_planner",
                "fallback_reason": None,
            },
            "dataset_info": kwargs.get("dataset_metadata") or {},
            "execution_time": 0.5,
            "model_comparison": {"enabled": False},
            "stdout": "fake",
            "stderr": "",
        }

    monkeypatch.setattr(ce_mod, "execute_eda", _fake_execute_eda)
    monkeypatch.setattr(rc_mod, "compose_eda_response", _fake_compose)


def _enable_agentic(monkeypatch, *, ready: bool = True):
    from backend.services.code_executor import sandbox_runtime

    monkeypatch.setattr(daa_module.settings, "use_glm5_agent", True)
    monkeypatch.setattr(sandbox_runtime, "agent_runtime_ready", ready)


# ---------------------------------------------------------------------------
# 1. SSE contract end-to-end (drains the real janus-backed tracker)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_stage_sequence_end_to_end_through_progress_tracker(
    agent, sample_csv, monkeypatch
):
    """Drive analyze_query with a real PipelineProgressTracker as the
    on_progress sink. Drain the async side of the janus queue (the same
    side the real SSE endpoint reads from) and assert the full 6-stage
    contract + terminal sentinel appears in order.

    janus.Queue requires a running event loop at construction, matching
    production where the tracker is created inside a FastAPI handler.
    """
    from backend.services.document_processing.progress_tracker import (
        PipelineProgressTracker,
    )

    _enable_agentic(monkeypatch, ready=True)
    _install_fake_agentic_loop(monkeypatch, _make_agentic_success())

    tracker = PipelineProgressTracker("test_sse_job")
    try:
        # analyze_query is sync; production runs it in an executor to
        # keep the event loop free for the SSE reader. Mirror that here.
        response = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: agent.analyze_query(
                question="Mean tip by size",
                data_file_path=str(sample_csv),
                on_progress=tracker.update,
            ),
        )
        tracker.complete()

        # Drain tracker's async queue — same side the SSE endpoint reads.
        events: List[Dict[str, Any]] = []
        q = tracker.async_queue
        while True:
            event = await asyncio.wait_for(q.get(), timeout=2.0)
            if event is None:  # sentinel
                break
            events.append(event.to_dict())

        assert response["success"] is True
        assert response["code_generation"]["mode"] == "glm5_agent"

        stage_sequence = [e["stage"] for e in events]
        # file_parse + metadata_extract each fire twice (running+completed);
        # loop emits code_generation (running+completed), security_check,
        # sandbox_execution; orchestrator adds terminal result_render.
        expected_unique_order = [
            "file_parse",
            "metadata_extract",
            "code_generation",
            "security_check",
            "sandbox_execution",
            "result_render",
        ]
        observed_unique = []
        for s in stage_sequence:
            if not observed_unique or observed_unique[-1] != s:
                observed_unique.append(s)
        assert observed_unique == expected_unique_order, (
            f"SSE stage contract violated: {observed_unique}"
        )

        # Terminal stage is completed (happy path).
        terminal = [e for e in events if e["stage"] == "result_render"]
        assert terminal and terminal[-1]["status"] == "completed"
    finally:
        tracker.close()


# ---------------------------------------------------------------------------
# 2. Golden: deterministic path is unchanged by W1-W4 additions
# ---------------------------------------------------------------------------


def test_flag_off_produces_deterministic_envelope_unchanged(
    agent, sample_csv, monkeypatch
):
    """Flag default-false → deterministic path runs, envelope matches
    the legacy contract. Regression guard: W4 must not leak agentic
    artifacts into deterministic responses.
    """
    monkeypatch.setattr(daa_module.settings, "use_glm5_agent", False)
    _install_fake_deterministic(monkeypatch)

    response = agent.analyze_query(
        question="Summarize the dataset",
        data_file_path=str(sample_csv),
    )

    assert response["success"] is True
    assert response["code_generation"]["mode"] == "deterministic_planner"
    # No agentic-only telemetry keys should be present.
    assert "repair_triggered" not in response["code_generation"]
    assert "time_budget_exhausted" not in response["code_generation"]
    assert "rounds" not in response["code_generation"]


# ---------------------------------------------------------------------------
# 3. Rollback: flag flip between requests routes to different modes
# ---------------------------------------------------------------------------


def test_flag_rollback_between_requests_switches_modes(
    agent, sample_csv, monkeypatch
):
    """Request A with flag on → glm5_agent mode.
    Request B with flag off (rollback) → deterministic_planner mode.
    No shared state leaks between calls (agentic rounds/elapsed
    telemetry must not appear on the deterministic response).
    """
    _install_fake_agentic_loop(monkeypatch, _make_agentic_success())
    _install_fake_deterministic(monkeypatch)

    # Request A — agentic enabled + ready.
    _enable_agentic(monkeypatch, ready=True)
    resp_a = agent.analyze_query(
        question="Q A",
        data_file_path=str(sample_csv),
    )
    assert resp_a["success"] is True
    assert resp_a["code_generation"]["mode"] == "glm5_agent"
    assert resp_a["code_generation"]["rounds"] == 1

    # Rollback: flag back to false.
    monkeypatch.setattr(daa_module.settings, "use_glm5_agent", False)
    resp_b = agent.analyze_query(
        question="Q B",
        data_file_path=str(sample_csv),
    )
    assert resp_b["success"] is True
    assert resp_b["code_generation"]["mode"] == "deterministic_planner"
    # Verify deterministic carries zero agentic telemetry — a shared
    # mutable dict bug would leak the previous call's rounds/elapsed here.
    for k in ("rounds", "repair_triggered", "time_budget_exhausted", "elapsed_s"):
        assert k not in resp_b["code_generation"], (
            f"agentic telemetry key {k!r} leaked into deterministic envelope"
        )


# ---------------------------------------------------------------------------
# 4. Degraded: flag on + probe NOT ready → deterministic path, no 503
# ---------------------------------------------------------------------------


def test_flag_on_but_probe_not_ready_falls_back_silently(
    agent, sample_csv, monkeypatch
):
    """W1 contract: if the startup probe reports missing packages, the
    runtime stays not-ready and analyze_query routes to deterministic.
    No exception, no 503, and the agentic loop never runs.
    """
    _enable_agentic(monkeypatch, ready=False)  # flag on, probe says nope
    _install_fake_deterministic(monkeypatch)

    # Also install a tripwire loop that would explode if called.
    import backend.services.data_analysis.agentic_loop as loop_mod

    async def _must_not_run(**kwargs):
        raise AssertionError("agentic loop must not run when probe is not ready")

    monkeypatch.setattr(loop_mod, "run_agentic_analysis", _must_not_run)

    response = agent.analyze_query(
        question="Describe the data",
        data_file_path=str(sample_csv),
    )

    assert response["success"] is True
    assert response["code_generation"]["mode"] == "deterministic_planner"


# ---------------------------------------------------------------------------
# 5. Real provider (env-gated): actual Zhipu + E2B end-to-end
# ---------------------------------------------------------------------------


_REAL_ENABLED = (
    os.getenv("LIVE_AGENTIC") == "1"
    and bool(os.getenv("ZHIPU_API_KEY"))
    and bool(os.getenv("E2B_API_KEY"))
)


@pytest.mark.slow
@pytest.mark.skipif(
    not _REAL_ENABLED,
    reason="LIVE_AGENTIC=1 and ZHIPU_API_KEY and E2B_API_KEY required",
)
def test_real_agentic_provider_end_to_end(agent, sample_csv, monkeypatch):
    """Hits Zhipu GLM-5 and E2B for real. Verifies the full wired path
    produces a legal envelope. Latency budget: the loop's own 45s total
    cap, plus E2B cold-start slack."""
    _enable_agentic(monkeypatch, ready=True)

    response = agent.analyze_query(
        question="What is the average tip by party size?",
        data_file_path=str(sample_csv),
    )

    assert isinstance(response, dict)
    assert response["code_generation"]["mode"] == "glm5_agent"
    # Either succeeded or failed gracefully — never raised.
    assert "success" in response
    assert response["code_generation"]["rounds"] in (1, 2)
    assert response["execution_time"] > 0.0
