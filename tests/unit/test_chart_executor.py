"""Tests for chart_executor.

Covers:
- Combined snippet assembly (N charts → one script).
- Column name sanitization via repr() — quotes/backslashes don't escape.
- Stdout marker parsing (ok, failed, malformed, missing).
- Partial failure handling (one chart fails, others surface cleanly).
- Image-file-not-downloaded demotion (savefig ok but not in output_files).
- Empty plan shortcut (no sandbox call).
- Missing manager degraded mode.

Does NOT require a running sandbox; we stub the manager.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from backend.services.data_analysis import chart_executor
from backend.services.data_analysis.chart_executor import (
    execute_eda,
    _build_combined_snippet,
    _parse_chart_markers,
    _extract_chart_idx,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _plan(charts: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "eda": {"charts": charts},
        "model_comparison": {"enabled": False},
        "rationale": "test",
    }


def _chart(idx: int, chart_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": f"chart_{idx:02d}_{chart_type}",
        "type": chart_type,
        "params": params,
        "source_columns": list(
            {
                v
                for v in params.values()
                if isinstance(v, str)
            }
            | set(
                params.get("columns", []) if isinstance(params.get("columns"), list) else []
            )
        ),
    }


def _make_manager(stdout: str = "", output_files=None, success=True, error=None):
    mgr = MagicMock()
    mgr.execute_code.return_value = {
        "success": success,
        "stdout": stdout,
        "stderr": "" if success else (error or "boom"),
        "error": error,
        "execution_time": 0.42,
        "output_files": output_files or {},
        "visualizations": list((output_files or {}).keys()),
    }
    return mgr


# ---------------------------------------------------------------------------
# snippet assembly
# ---------------------------------------------------------------------------


def test_build_snippet_contains_all_chart_blocks():
    charts = [
        _chart(0, "histogram", {"column": "price"}),
        _chart(1, "scatter", {"x": "price", "y": "sqft"}),
        _chart(2, "heatmap", {"columns": ["price", "sqft", "floors"]}),
    ]
    snippet = _build_combined_snippet(charts, "/tmp/data.csv")

    assert "import pandas as _pd" in snippet
    assert "matplotlib.use('Agg')" in snippet
    assert "_DATA_PATH = '/workspace/data.csv'" in snippet
    assert "_pd.read_csv(_DATA_PATH)" in snippet

    # One block per chart, with the savefig wired to chart_id.png
    assert "chart_00_histogram.png" in snippet
    assert "chart_01_scatter.png" in snippet
    assert "chart_02_heatmap.png" in snippet

    # Try/except wrapping — partial failures isolated per chart
    assert snippet.count("except Exception as _exc:") >= 3


def test_build_snippet_handles_xlsx():
    charts = [_chart(0, "histogram", {"column": "a"})]
    snippet = _build_combined_snippet(charts, "/tmp/data.xlsx")
    assert "_pd.read_excel(_DATA_PATH)" in snippet
    assert "_DATA_PATH = '/workspace/data.xlsx'" in snippet


def test_column_names_are_safely_quoted():
    """Column names with quotes/backslashes must not break the snippet.

    repr() is the interpolation primitive — this test pins that contract
    so a future refactor that switches to f-string concatenation breaks
    loudly.
    """
    import ast

    nasty = "foo'; import os; os.system('rm -rf /')  #"
    charts = [_chart(0, "histogram", {"column": nasty})]
    snippet = _build_combined_snippet(charts, "/tmp/data.csv")

    # Snippet must be syntactically valid Python — proves the injection
    # payload did not break out of its string literal and become code.
    ast.parse(snippet)

    # Payload appears only as a repr'd literal (quoted + escaped).
    assert repr(nasty) in snippet
    # The raw payload (unquoted, as code) must NOT appear.
    assert f"'; import os; os.system" not in snippet.replace(repr(nasty), "")


def test_filename_with_quotes_still_produces_valid_python():
    """[regression, codex pass 11] A dataset filename containing a single
    quote (e.g. ``customer's-data.csv``) previously broke snippet
    compilation because _DATA_PATH was built with f-string interpolation.
    Fix: use repr() for the sandbox path, same contract as column names.
    """
    import ast

    charts = [_chart(0, "histogram", {"column": "price"})]
    snippet = _build_combined_snippet(charts, "/tmp/customer's-data.csv")
    # Must still parse as valid Python.
    ast.parse(snippet)
    # Path literal must be present exactly once, as a repr'd string.
    assert repr("/workspace/customer's-data.csv") in snippet


def test_combined_snippet_passes_strict_validator():
    """[regression] All 5 chart scaffolds combined must pass
    CodeValidator strict mode. If one render helper slips in a blocked
    method (.apply/.agg/.map/etc) the whole snippet is rejected and no
    charts render. Worth pinning because the blocked-method list is
    enforced at another layer (validator.py) — easy to miss."""
    from backend.services.code_executor.validator import validate_code

    charts = [
        {"id": "chart_00_histogram", "type": "histogram", "params": {"column": "price"}},
        {"id": "chart_01_scatter", "type": "scatter", "params": {"x": "price", "y": "sqft"}},
        {"id": "chart_02_heatmap", "type": "heatmap", "params": {"columns": ["a", "b", "c"]}},
        {"id": "chart_03_bar", "type": "bar", "params": {"column": "type", "metric": "count"}},
        {"id": "chart_04_boxplot", "type": "boxplot", "params": {"column": "price", "by": "type"}},
    ]
    snippet = _build_combined_snippet(charts, "/tmp/data.csv")
    result = validate_code(snippet, strict_mode=True)
    assert result.is_valid, f"validator rejected snippet: {result.error}"


def test_unsupported_chart_type_emits_failure_marker():
    charts = [
        {"id": "chart_00_violin", "type": "violin", "params": {}, "source_columns": []},
    ]
    snippet = _build_combined_snippet(charts, "/tmp/data.csv")
    assert "unsupported chart type" in snippet
    assert "CHART_FAILED_JSON" in snippet or "_emit('failed'" in snippet


# ---------------------------------------------------------------------------
# marker parsing
# ---------------------------------------------------------------------------


def test_parse_markers_extracts_ok_and_failed():
    stdout = "\n".join(
        [
            "CHART_OK_JSON=" + json.dumps({"idx": 0, "type": "histogram", "status": "ok", "image_filename": "chart_00_histogram.png", "summary": {"count": 100}}),
            "some other noise line",
            "CHART_FAILED_JSON=" + json.dumps({"idx": 1, "type": "scatter", "status": "failed", "error": "boom"}),
        ]
    )
    parsed = _parse_chart_markers(stdout)
    assert 0 in parsed and 1 in parsed
    assert parsed[0]["status"] == "ok"
    assert parsed[0]["image_filename"] == "chart_00_histogram.png"
    assert parsed[1]["status"] == "failed"
    assert parsed[1]["error"] == "boom"


def test_parse_markers_ignores_malformed_json():
    stdout = "CHART_OK_JSON=not json\nCHART_OK_JSON={\"idx\": 0, \"status\": \"ok\"}"
    parsed = _parse_chart_markers(stdout)
    # Malformed line regex won't match (requires {...} shape); valid one does.
    assert 0 in parsed


def test_extract_chart_idx():
    assert _extract_chart_idx("chart_00_histogram") == 0
    assert _extract_chart_idx("chart_12_boxplot") == 12
    with pytest.raises(ValueError):
        _extract_chart_idx("not-a-chart-id")


# ---------------------------------------------------------------------------
# execute_eda integration (with stubbed manager)
# ---------------------------------------------------------------------------


def test_empty_plan_skips_sandbox():
    mgr = MagicMock()
    result = execute_eda(_plan([]), "/tmp/data.csv", mgr)
    assert result["success"] is True
    assert result["charts"] == []
    mgr.execute_code.assert_not_called()


def test_missing_manager_returns_degraded():
    charts = [_chart(0, "histogram", {"column": "price"})]
    result = execute_eda(_plan(charts), "/tmp/data.csv", None)
    assert result["success"] is False
    assert len(result["charts"]) == 1
    assert result["charts"][0]["status"] == "failed"
    assert "unavailable" in result["charts"][0]["error"]


def test_all_charts_ok_returns_populated_result():
    charts = [
        _chart(0, "histogram", {"column": "price"}),
        _chart(1, "bar", {"column": "type", "metric": "count"}),
    ]
    stdout = "\n".join(
        [
            "CHART_OK_JSON="
            + json.dumps(
                {
                    "idx": 0,
                    "type": "histogram",
                    "status": "ok",
                    "image_filename": "chart_00_histogram.png",
                    "summary": {"count": 100},
                }
            ),
            "CHART_OK_JSON="
            + json.dumps(
                {
                    "idx": 1,
                    "type": "bar",
                    "status": "ok",
                    "image_filename": "chart_01_bar.png",
                    "summary": {"categories": ["a", "b"]},
                }
            ),
        ]
    )
    output_files = {
        "chart_00_histogram.png": b"\x89PNG...",
        "chart_01_bar.png": b"\x89PNG...",
    }
    mgr = _make_manager(stdout=stdout, output_files=output_files)

    result = execute_eda(_plan(charts), "/tmp/data.csv", mgr, mode="e2b")

    assert result["success"] is True
    assert len(result["charts"]) == 2
    assert all(c["status"] == "ok" for c in result["charts"])
    assert result["charts"][0]["image_filename"] == "chart_00_histogram.png"
    assert result["charts"][0]["summary"]["count"] == 100
    assert result["charts"][1]["image_filename"] == "chart_01_bar.png"

    # Executor passed the mode through to the manager.
    call = mgr.execute_code.call_args
    assert call.kwargs["mode"] == "e2b"
    assert call.kwargs["data_files"] == ["/tmp/data.csv"]


def test_partial_failure_does_not_poison_other_charts():
    charts = [
        _chart(0, "histogram", {"column": "price"}),
        _chart(1, "scatter", {"x": "nonexistent", "y": "price"}),
    ]
    stdout = "\n".join(
        [
            "CHART_OK_JSON="
            + json.dumps(
                {
                    "idx": 0,
                    "type": "histogram",
                    "status": "ok",
                    "image_filename": "chart_00_histogram.png",
                    "summary": {"count": 50},
                }
            ),
            "CHART_FAILED_JSON="
            + json.dumps(
                {
                    "idx": 1,
                    "type": "scatter",
                    "status": "failed",
                    "error": "columns not in dataset: ['nonexistent']",
                }
            ),
        ]
    )
    output_files = {"chart_00_histogram.png": b"\x89PNG..."}
    mgr = _make_manager(stdout=stdout, output_files=output_files)

    result = execute_eda(_plan(charts), "/tmp/data.csv", mgr, mode="e2b")

    assert result["success"] is True  # sandbox itself ran clean
    statuses = [c["status"] for c in result["charts"]]
    assert statuses == ["ok", "failed"]
    assert "not in dataset" in result["charts"][1]["error"]
    assert result["charts"][1]["image_filename"] is None


def test_missing_image_file_demotes_ok_to_failed():
    """Savefig-succeeded but sandbox didn't return the image → downgrade.

    Prevents the frontend from rendering broken <img> tags.
    """
    charts = [_chart(0, "histogram", {"column": "price"})]
    stdout = "CHART_OK_JSON=" + json.dumps(
        {
            "idx": 0,
            "type": "histogram",
            "status": "ok",
            "image_filename": "chart_00_histogram.png",
            "summary": {"count": 1},
        }
    )
    # Note: output_files is empty — manager lost the file on download.
    mgr = _make_manager(stdout=stdout, output_files={})

    result = execute_eda(_plan(charts), "/tmp/data.csv", mgr)
    assert result["charts"][0]["status"] == "failed"
    assert result["charts"][0]["image_filename"] is None
    assert "not downloaded" in result["charts"][0]["error"]


def test_missing_marker_marks_chart_as_missing():
    """Sandbox crashed mid-script — later charts have no marker."""
    charts = [
        _chart(0, "histogram", {"column": "price"}),
        _chart(1, "scatter", {"x": "a", "y": "b"}),
    ]
    stdout = "CHART_OK_JSON=" + json.dumps(
        {
            "idx": 0,
            "type": "histogram",
            "status": "ok",
            "image_filename": "chart_00_histogram.png",
            "summary": {},
        }
    )
    mgr = _make_manager(
        stdout=stdout,
        output_files={"chart_00_histogram.png": b"\x89PNG..."},
        success=False,
        error="SandboxTimeoutError: killed",
    )

    result = execute_eda(_plan(charts), "/tmp/data.csv", mgr)
    assert result["success"] is False
    assert result["charts"][0]["status"] == "ok"
    assert result["charts"][1]["status"] == "missing"
    assert "killed" in (result["charts"][1]["error"] or "")


def test_mode_defaults_to_settings(monkeypatch):
    """When caller omits mode, fall back to settings.code_execution_provider."""
    charts = [_chart(0, "histogram", {"column": "price"})]
    mgr = _make_manager(stdout="")
    from backend.config import settings

    monkeypatch.setattr(settings, "code_execution_provider", "e2b", raising=False)

    execute_eda(_plan(charts), "/tmp/data.csv", mgr)
    assert mgr.execute_code.call_args.kwargs["mode"] == "e2b"
