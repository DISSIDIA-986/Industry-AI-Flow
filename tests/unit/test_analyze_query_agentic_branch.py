"""W4 unit tests: analyze_query() agentic branch + envelope composition.

Covers Plan Appendix E W4 acceptance:
  1. Agentic path taken when flag + readiness both true.
  2. Deterministic path taken when flag off (default).
  3. Deterministic path taken when flag on but probe marked runtime not ready.
  4. Envelope shape matches legacy contract on success.
  5. Graceful failure envelope on agentic error (no raised exception).

No real LLM, no real sandbox, no real E2B. All cloud boundaries stubbed.
"""
from __future__ import annotations

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
    df = pd.DataFrame({"tip": [1.0, 2.0, 3.0, 4.5], "size": [1, 2, 3, 4]})
    path = tmp_path / "sample.csv"
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def agent() -> DataAnalysisAgent:
    """Build an agent without initializing LLM or sandbox (W4 never uses them)."""
    a = DataAnalysisAgent.__new__(DataAnalysisAgent)
    a.llm_client = None
    a.code_execution_manager = None
    a.code_executor = None
    return a


def _make_success_result(chart_bytes: bytes | None = b"fake-png-bytes") -> PlanExecutionResult:
    """Build a successful PlanExecutionResult with a chart."""
    rec = RoundRecord(
        round_num=1,
        llm_raw="{}",
        json_schema_valid=True,
        parsed={
            "status": "ok",
            "business_goal": "Count tips by size",
            "analysis_plan": "Group by size, compute mean",
            "produces_chart": True,
            "python_code": "print('hi')",
        },
        validator_pass=True,
        sandbox_success=True,
        sandbox_stdout="hi\nANALYSIS_SUMMARY_JSON={\"key_findings\": [\"Mean tip: 2.6\"]}\n",
        chart_exists=chart_bytes is not None,
        chart_bytes=chart_bytes,
        summary_emitted=True,
        summary_parsed={"key_findings": ["Mean tip: 2.6"]},
    )
    return PlanExecutionResult(
        success=True,
        status="ok",
        rounds=[rec],
        final_code="print('hi')",
        final_plan={
            "business_goal": "Count tips by size",
            "analysis_plan": "Group by size, compute mean",
            "produces_chart": True,
        },
        final_stdout=rec.sandbox_stdout,
        final_chart_bytes=chart_bytes,
        final_summary={"key_findings": ["Mean tip: 2.6"]},
        total_elapsed_s=3.14,
    )


def _make_failure_result() -> PlanExecutionResult:
    rec = RoundRecord(
        round_num=1,
        llm_raw="{}",
        json_schema_valid=True,
        parsed={"status": "ok", "python_code": "x = 1/0", "produces_chart": False},
        validator_pass=True,
        sandbox_success=False,
        sandbox_stderr="ZeroDivisionError",
        sandbox_exception_type="ZeroDivisionError: division by zero",
    )
    return PlanExecutionResult(
        success=False,
        status="error",
        rounds=[rec],
        repair_triggered=True,
        repair_trigger_type="sandbox_runtime_error",
        repair_recovered=False,
        final_code="x = 1/0",
        final_plan={"produces_chart": False},
        error_message="ZeroDivisionError: division by zero",
        total_elapsed_s=5.0,
    )


# ---------------------------------------------------------------------------
# Gating tests
# ---------------------------------------------------------------------------


def test_flag_off_skips_agentic_path(agent, sample_csv, monkeypatch):
    """Default: use_glm5_agent=False → _agentic_path_enabled() must be False."""
    monkeypatch.setattr(daa_module.settings, "use_glm5_agent", False)
    assert agent._agentic_path_enabled() is False


def test_flag_on_but_probe_not_ready_skips_agentic_path(agent, monkeypatch):
    """Flag on but probe said runtime missing packages → still deterministic."""
    monkeypatch.setattr(daa_module.settings, "use_glm5_agent", True)
    from backend.services.code_executor import sandbox_runtime

    monkeypatch.setattr(sandbox_runtime, "agent_runtime_ready", False)
    assert agent._agentic_path_enabled() is False


def test_flag_on_and_probe_ready_takes_agentic_path(agent, monkeypatch):
    monkeypatch.setattr(daa_module.settings, "use_glm5_agent", True)
    from backend.services.code_executor import sandbox_runtime

    monkeypatch.setattr(sandbox_runtime, "agent_runtime_ready", True)
    assert agent._agentic_path_enabled() is True


# ---------------------------------------------------------------------------
# Envelope shape tests
# ---------------------------------------------------------------------------


def _enable_agentic(monkeypatch):
    monkeypatch.setattr(daa_module.settings, "use_glm5_agent", True)
    from backend.services.code_executor import sandbox_runtime

    monkeypatch.setattr(sandbox_runtime, "agent_runtime_ready", True)


def _install_fake_loop(monkeypatch, fake_result: PlanExecutionResult):
    """Swap run_agentic_analysis with a coroutine that returns a fixed result."""
    import backend.services.data_analysis.agentic_loop as loop_mod

    async def _fake(**kwargs):
        # Echo the progress contract the real loop emits, so the test
        # proves analyze_query's _run_agentic_path doesn't swallow it.
        cb = kwargs.get("on_progress")
        if cb is not None:
            cb("code_generation", "completed", 0.40, "Plan generated")
            cb("security_check", "completed", 0.50, "Validated (agentic)")
            cb("sandbox_execution", "completed", 0.85, "Executed")
        return fake_result

    monkeypatch.setattr(loop_mod, "run_agentic_analysis", _fake)


def test_agentic_success_envelope_matches_legacy_shape(
    agent, sample_csv, monkeypatch
):
    _enable_agentic(monkeypatch)
    _install_fake_loop(monkeypatch, _make_success_result(chart_bytes=b"chart-bytes"))

    events: List[Dict[str, Any]] = []

    def on_progress(stage, status, progress, detail):
        events.append({"stage": stage, "status": status, "progress": progress})

    response = agent.analyze_query(
        question="Mean tip by size",
        data_file_path=str(sample_csv),
        on_progress=on_progress,
    )

    # Success + legacy top-level keys present.
    assert response["success"] is True
    for key in (
        "answer",
        "charts",
        "visualizations",
        "code",
        "analysis_summary",
        "code_generation",
        "dataset_info",
        "execution_time",
        "model_comparison",
        "stdout",
        "stderr",
    ):
        assert key in response, f"missing top-level key: {key}"

    # Mode marker identifies the agentic run.
    assert response["code_generation"]["mode"] == "glm5_agent"
    assert response["code_generation"]["rounds"] == 1
    assert response["code_generation"]["time_budget_exhausted"] is False

    # analysis_summary.key_findings ported through from summary JSON.
    assert response["analysis_summary"]["key_findings"] == ["Mean tip: 2.6"]

    # Visualization persisted to disk and entry is {filename, path}.
    vizs = response["visualizations"]
    assert len(vizs) == 1
    assert set(vizs[0].keys()) == {"filename", "path"}
    assert Path(vizs[0]["path"]).read_bytes() == b"chart-bytes"

    # Chart entry matches legacy chart envelope shape.
    chart = response["charts"][0]
    for k in ("id", "type", "status", "image_filename", "summary", "error", "params"):
        assert k in chart
    assert chart["status"] == "ok"
    assert chart["image_filename"] == vizs[0]["filename"]

    # SSE contract: all 4 agentic+terminal stages emitted in order.
    stages_seen = [e["stage"] for e in events]
    assert stages_seen == [
        "file_parse",
        "file_parse",
        "metadata_extract",
        "metadata_extract",
        "code_generation",
        "security_check",
        "sandbox_execution",
        "result_render",
    ]
    # Terminal stage closed with status=completed.
    assert events[-1]["status"] == "completed"


def test_agentic_failure_returns_graceful_envelope_not_exception(
    agent, sample_csv, monkeypatch
):
    _enable_agentic(monkeypatch)
    _install_fake_loop(monkeypatch, _make_failure_result())

    events: List[Dict[str, Any]] = []

    def on_progress(stage, status, progress, detail):
        events.append((stage, status))

    response = agent.analyze_query(
        question="Question that will fail",
        data_file_path=str(sample_csv),
        on_progress=on_progress,
    )

    # Graceful: no exception bubbled, envelope carries failure info.
    assert response["success"] is False
    assert response["code_generation"]["mode"] == "glm5_agent"
    assert response["code_generation"]["repair_triggered"] is True
    assert response["code_generation"]["repair_recovered"] is False
    assert "ZeroDivisionError" in response["stderr"]
    # Terminal stage was emitted with failed status.
    assert events[-1] == ("result_render", "failed")


def test_agentic_import_failure_falls_back_to_deterministic(
    agent, sample_csv, monkeypatch
):
    """If the agentic module can't be imported, analyze_query must still work."""
    _enable_agentic(monkeypatch)

    # Force the import inside _run_agentic_path to raise. We do this by
    # nuking agentic_loop from sys.modules AND blocking re-import.
    import sys

    monkeypatch.delitem(sys.modules, "backend.services.data_analysis.agentic_loop", raising=False)
    monkeypatch.delitem(sys.modules, "backend.services.data_analysis.agentic_envelope", raising=False)

    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__

    def _blocking_import(name, *a, **kw):
        if name.endswith("agentic_loop") or name.endswith("agentic_envelope"):
            raise ImportError(f"blocked for test: {name}")
        return real_import(name, *a, **kw)

    monkeypatch.setattr("builtins.__import__", _blocking_import)

    # Unit-level check: _run_agentic_path returns None → fall-through.
    result = agent._run_agentic_path(
        question="Q",
        data_file_path=str(sample_csv),
        dataset_metadata={"rows": 4, "columns": 2, "columns_info": []},
        on_progress=None,
    )
    assert result is None
