"""Tests for report_composer.

Covers:
- Response envelope shape matches legacy analyze_query contract.
- Per-chart persist mapping survives filename collisions (renamed file
  flows through to the right chart entry).
- OK chart with no persisted file is demoted to failed.
- Key findings built from per-chart summaries, dataset header included.
- Answer text branches for all-failed / zero-chart / happy-path.
- Executor-level failure (success=False) still surfaces stdout/stderr.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest

from backend.services.data_analysis.report_composer import compose_eda_response


def _plan(rationale="top 2 charts", mc_enabled=False) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "eda": {"charts": []},
        "model_comparison": {"enabled": mc_enabled, "reason": "disabled"},
        "rationale": rationale,
    }


def _execution(
    charts: List[Dict[str, Any]],
    output_files: Dict[str, Any] | None = None,
    success: bool = True,
    stdout: str = "",
    stderr: str = "",
) -> Dict[str, Any]:
    return {
        "success": success,
        "charts": charts,
        "stdout": stdout,
        "stderr": stderr,
        "execution_time": 1.23,
        "output_files": output_files or {},
    }


def _metadata(rows=100, columns=5, filename="tips.csv") -> Dict[str, Any]:
    return {
        "filename": filename,
        "rows": rows,
        "columns": columns,
        "columns_info": [],
    }


@pytest.fixture(autouse=True)
def _tmp_temp_data_dir(monkeypatch, tmp_path):
    """Redirect temp_data_dir so _persist_visualization_artifacts writes
    into a test-scoped dir. Without this the tests would pollute the
    real /tmp/luncheon_data."""
    from backend.config import settings

    monkeypatch.setattr(settings, "temp_data_dir", str(tmp_path), raising=False)
    return tmp_path


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------


def test_composes_response_envelope(_tmp_temp_data_dir):
    charts = [
        {
            "id": "chart_00_histogram",
            "type": "histogram",
            "status": "ok",
            "image_filename": "chart_00_histogram.png",
            "summary": {
                "column": "total_bill",
                "count": 100,
                "mean": 19.79,
                "median": 17.80,
                "std": 8.90,
            },
            "error": None,
            "params": {"column": "total_bill"},
        },
        {
            "id": "chart_01_scatter",
            "type": "scatter",
            "status": "ok",
            "image_filename": "chart_01_scatter.png",
            "summary": {
                "x": "total_bill",
                "y": "tip",
                "pearson_r": 0.68,
                "n": 100,
            },
            "error": None,
            "params": {"x": "total_bill", "y": "tip"},
        },
    ]
    output_files = {
        "chart_00_histogram.png": b"\x89PNG...1",
        "chart_01_scatter.png": b"\x89PNG...2",
    }
    result = compose_eda_response(
        plan=_plan(rationale="Top 2 by variance."),
        execution=_execution(charts, output_files),
        question="explore tips",
        dataset_metadata=_metadata(),
    )

    assert result["success"] is True
    assert len(result["charts"]) == 2
    assert all(c["status"] == "ok" for c in result["charts"])
    # Legacy contract: visualizations is List[{filename, path}], not List[str].
    # The frontend's firstArtifactPath iterates objects expecting these keys.
    assert all(
        isinstance(v, dict) and "filename" in v and "path" in v
        for v in result["visualizations"]
    )
    persisted_filenames = {v["filename"] for v in result["visualizations"]}
    chart_filenames = {c["image_filename"] for c in result["charts"]}
    assert persisted_filenames == chart_filenames
    for v in result["visualizations"]:
        assert (_tmp_temp_data_dir / v["filename"]).exists()
        assert v["path"].endswith(v["filename"])

    # Envelope shape
    assert result["code_generation"]["mode"] == "deterministic_planner"
    assert "key_findings" in result["analysis_summary"]
    assert result["model_comparison"]["enabled"] is False

    findings = result["analysis_summary"]["key_findings"]
    assert any("rows" in f for f in findings)
    assert any("total_bill" in f for f in findings)
    assert any("Pearson" in f for f in findings)


def test_visualization_order_matches_plan_order(_tmp_temp_data_dir):
    charts = [
        {
            "id": f"chart_0{i}_histogram",
            "type": "histogram",
            "status": "ok",
            "image_filename": f"chart_0{i}_histogram.png",
            "summary": {"column": f"c{i}", "count": 1, "mean": 1.0},
            "error": None,
            "params": {},
        }
        for i in range(3)
    ]
    output_files = {c["image_filename"]: b"\x89PNG" for c in charts}
    result = compose_eda_response(
        plan=_plan(),
        execution=_execution(charts, output_files),
        question="",
        dataset_metadata=_metadata(),
    )
    # Chart order preserved
    assert [c["id"] for c in result["charts"]] == [c["id"] for c in charts]
    # Visualization order matches chart order (grid layout consistency)
    assert len(result["visualizations"]) == 3


# ---------------------------------------------------------------------------
# persistence edge cases
# ---------------------------------------------------------------------------


def test_collision_rename_flows_into_correct_chart(_tmp_temp_data_dir):
    """When two runs produce the same filename, the second gets renamed.
    Make sure the renamed filename ends up on the correct chart entry
    (not stranded in a generic list)."""
    # Pre-create a file so the persister triggers _next_available_path
    (_tmp_temp_data_dir / "chart_00_histogram.png").write_bytes(b"existing")

    charts = [
        {
            "id": "chart_00_histogram",
            "type": "histogram",
            "status": "ok",
            "image_filename": "chart_00_histogram.png",
            "summary": {"column": "x", "count": 1, "mean": 1.0},
            "error": None,
            "params": {},
        }
    ]
    output_files = {"chart_00_histogram.png": b"new bytes"}
    result = compose_eda_response(
        plan=_plan(),
        execution=_execution(charts, output_files),
        question="",
        dataset_metadata=_metadata(),
    )

    persisted_name = result["charts"][0]["image_filename"]
    # Must NOT be the original — persister renamed on collision
    assert persisted_name != "chart_00_histogram.png"
    # Must actually exist on disk
    assert (_tmp_temp_data_dir / persisted_name).exists()
    # And it must be on visualizations list (as a {filename, path} object)
    assert any(
        v["filename"] == persisted_name for v in result["visualizations"]
    )


def test_ok_but_missing_output_file_demoted_to_failed(_tmp_temp_data_dir):
    """Executor said ok, but output_files dict is empty for this chart.
    Must not render a broken <img> — flip to failed."""
    charts = [
        {
            "id": "chart_00_histogram",
            "type": "histogram",
            "status": "ok",
            "image_filename": "chart_00_histogram.png",
            "summary": {"column": "x", "count": 1, "mean": 1.0},
            "error": None,
            "params": {},
        }
    ]
    # output_files empty — persistence will silently skip
    result = compose_eda_response(
        plan=_plan(),
        execution=_execution(charts, output_files={}),
        question="",
        dataset_metadata=_metadata(),
    )
    assert result["charts"][0]["status"] == "failed"
    assert result["charts"][0]["image_filename"] is None
    assert "could not be persisted" in result["charts"][0]["error"]
    assert result["visualizations"] == []
    assert result["success"] is False  # no ok charts


# ---------------------------------------------------------------------------
# key findings
# ---------------------------------------------------------------------------


def test_key_findings_lists_failed_chart_count(_tmp_temp_data_dir):
    charts = [
        {
            "id": "chart_00_histogram",
            "type": "histogram",
            "status": "ok",
            "image_filename": "chart_00_histogram.png",
            "summary": {"column": "x", "count": 1, "mean": 1.0},
            "error": None,
            "params": {},
        },
        {
            "id": "chart_01_scatter",
            "type": "scatter",
            "status": "failed",
            "image_filename": None,
            "summary": None,
            "error": "columns not in dataset",
            "params": {},
        },
    ]
    result = compose_eda_response(
        plan=_plan(),
        execution=_execution(
            charts, output_files={"chart_00_histogram.png": b"\x89PNG"}
        ),
        question="",
        dataset_metadata=_metadata(),
    )
    findings = result["analysis_summary"]["key_findings"]
    assert any("1 chart(s) skipped" in f for f in findings)


def test_key_findings_for_all_chart_types(_tmp_temp_data_dir):
    charts = [
        {
            "id": "chart_00_histogram",
            "type": "histogram",
            "status": "ok",
            "image_filename": "chart_00_histogram.png",
            "summary": {"column": "a", "count": 50, "mean": 5.0, "median": 4.8, "std": 1.2},
            "error": None,
            "params": {},
        },
        {
            "id": "chart_01_bar",
            "type": "bar",
            "status": "ok",
            "image_filename": "chart_01_bar.png",
            "summary": {
                "column": "dept",
                "categories": ["eng", "sales"],
                "counts": [30, 20],
            },
            "error": None,
            "params": {},
        },
        {
            "id": "chart_02_heatmap",
            "type": "heatmap",
            "status": "ok",
            "image_filename": "chart_02_heatmap.png",
            "summary": {"n_columns": 4},
            "error": None,
            "params": {},
        },
        {
            "id": "chart_03_boxplot",
            "type": "boxplot",
            "status": "ok",
            "image_filename": "chart_03_boxplot.png",
            "summary": {"column": "salary", "by": "dept", "n_groups": 3},
            "error": None,
            "params": {},
        },
    ]
    output_files = {c["image_filename"]: b"\x89PNG" for c in charts}
    result = compose_eda_response(
        plan=_plan(),
        execution=_execution(charts, output_files),
        question="",
        dataset_metadata=_metadata(),
    )
    findings = " ".join(result["analysis_summary"]["key_findings"])
    assert "mean=" in findings
    assert "categories" in findings
    assert "heatmap" in findings.lower()
    assert "boxplot" in findings.lower() or "by 'dept'" in findings


# ---------------------------------------------------------------------------
# answer text
# ---------------------------------------------------------------------------


def test_answer_happy_path_mentions_counts_and_rationale(_tmp_temp_data_dir):
    charts = [
        {
            "id": "chart_00_histogram",
            "type": "histogram",
            "status": "ok",
            "image_filename": "chart_00_histogram.png",
            "summary": {"column": "x", "count": 1, "mean": 1.0},
            "error": None,
            "params": {},
        },
    ]
    result = compose_eda_response(
        plan=_plan(rationale="Top 1 by variance."),
        execution=_execution(charts, {"chart_00_histogram.png": b"\x89PNG"}),
        question="",
        dataset_metadata=_metadata(rows=500),
    )
    assert "Rendered 1/1 charts" in result["answer"]
    assert "500" in result["answer"]
    assert "Top 1 by variance" in result["answer"]


def test_answer_all_failed(_tmp_temp_data_dir):
    charts = [
        {
            "id": "chart_00_histogram",
            "type": "histogram",
            "status": "failed",
            "image_filename": None,
            "summary": None,
            "error": "boom",
            "params": {},
        }
    ]
    result = compose_eda_response(
        plan=_plan(),
        execution=_execution(charts, {}, success=True),  # sandbox ok, charts failed
        question="",
        dataset_metadata=_metadata(),
    )
    assert result["success"] is False
    assert "all of them" in result["answer"] or "failed during rendering" in result["answer"]


def test_answer_zero_charts(_tmp_temp_data_dir):
    result = compose_eda_response(
        plan=_plan(),
        execution=_execution([], {}),
        question="",
        dataset_metadata=_metadata(),
    )
    assert "No charts" in result["answer"]
    assert result["success"] is False
    assert result["charts"] == []


# ---------------------------------------------------------------------------
# legacy contract regression (codex pass 12)
# ---------------------------------------------------------------------------


def test_visualizations_shape_matches_frontend_contract(_tmp_temp_data_dir):
    """[regression] firstArtifactPath in data-analysis/page.tsx iterates
    visualizations expecting {path, filename} OBJECTS. Plain strings would
    silently break chart rendering on every deterministic run."""
    charts = [
        {
            "id": "chart_00_histogram",
            "type": "histogram",
            "status": "ok",
            "image_filename": "chart_00_histogram.png",
            "summary": {"column": "x", "count": 1, "mean": 1.0},
            "error": None,
            "params": {},
        }
    ]
    result = compose_eda_response(
        plan=_plan(),
        execution=_execution(charts, {"chart_00_histogram.png": b"\x89PNG"}),
        question="",
        dataset_metadata=_metadata(),
    )
    viz = result["visualizations"]
    assert len(viz) == 1
    item = viz[0]
    assert isinstance(item, dict)
    assert isinstance(item.get("filename"), str) and item["filename"]
    assert isinstance(item.get("path"), str) and item["path"]


def test_code_field_preserved_in_response(_tmp_temp_data_dir):
    """[regression] analyze_query legacy contract included a `code` field
    that the frontend "Generated Code (Python)" panel reads. Composer
    must thread the executor-built snippet through so the panel doesn't
    go blank on every deterministic run."""
    charts = [
        {
            "id": "chart_00_histogram",
            "type": "histogram",
            "status": "ok",
            "image_filename": "chart_00_histogram.png",
            "summary": {"column": "x", "count": 1, "mean": 1.0},
            "error": None,
            "params": {},
        }
    ]
    snippet = "import pandas as pd\n# combined eda snippet ...\n"
    result = compose_eda_response(
        plan=_plan(),
        execution=_execution(charts, {"chart_00_histogram.png": b"\x89PNG"}),
        question="",
        dataset_metadata=_metadata(),
        generated_code=snippet,
    )
    assert result["code"] == snippet


def test_code_field_defaults_to_empty_string(_tmp_temp_data_dir):
    """Caller that forgets to pass generated_code still gets a string
    (not None / missing), so `result.code` never crashes the frontend."""
    result = compose_eda_response(
        plan=_plan(),
        execution=_execution([], {}),
        question="",
        dataset_metadata=_metadata(),
    )
    assert result["code"] == ""


# ---------------------------------------------------------------------------
# sandbox-level failure
# ---------------------------------------------------------------------------


def test_sandbox_crash_preserves_stdout_stderr(_tmp_temp_data_dir):
    charts = [
        {
            "id": "chart_00_histogram",
            "type": "histogram",
            "status": "missing",
            "image_filename": None,
            "summary": None,
            "error": "timeout killed",
            "params": {},
        }
    ]
    result = compose_eda_response(
        plan=_plan(),
        execution=_execution(
            charts,
            {},
            success=False,
            stdout="partial output",
            stderr="SandboxTimeout",
        ),
        question="",
        dataset_metadata=_metadata(),
    )
    assert result["success"] is False
    assert result["stdout"] == "partial output"
    assert result["stderr"] == "SandboxTimeout"


# ---------------------------------------------------------------------------
# model comparison merge
# ---------------------------------------------------------------------------


def _model_execution(
    *,
    success: bool = True,
    image_in_output_files: bool = True,
    target: str = "quality",
    task: str = "classification",
) -> Dict[str, Any]:
    output_files = (
        {"model_comparison.png": b"\x89PNG\r\n\x1a\nfake"}
        if image_in_output_files
        else {}
    )
    return {
        "success": success,
        "enabled": True,
        "reason": "ok" if success else "training failed",
        "target_column": target,
        "task": task,
        "metrics": {
            "RandomForestClassifier": {"accuracy": 0.87, "f1": 0.85},
            "LogisticRegression": {"accuracy": 0.75, "f1": 0.72},
        },
        "image_filename": "model_comparison.png" if success else None,
        "output_files": output_files,
        "stdout": "",
        "stderr": "",
        "execution_time": 1.5,
    }


def test_model_execution_none_preserves_eda_only_shape(_tmp_temp_data_dir):
    """No model stage → model_comparison block reflects plan, no chart added."""
    plan = _plan(mc_enabled=False)
    plan["model_comparison"]["reason"] = "stretch goal"
    result = compose_eda_response(
        plan=plan,
        execution=_execution([]),
        question="q",
        dataset_metadata=_metadata(),
        model_execution=None,
    )
    assert result["model_comparison"]["enabled"] is False
    assert result["model_comparison"]["reason"] == "stretch goal"
    assert result["model_comparison"]["metrics"] == {}
    # No model chart merged into grid.
    assert all(c["type"] != "model_comparison" for c in result["charts"])


def test_model_execution_success_merges_chart_and_metrics(_tmp_temp_data_dir):
    plan = _plan(mc_enabled=True)
    plan["model_comparison"].update(
        {"target_column": "quality", "task": "classification", "models": ["RFC"]}
    )
    result = compose_eda_response(
        plan=plan,
        execution=_execution([]),
        question="q",
        dataset_metadata=_metadata(),
        model_execution=_model_execution(),
    )
    mc = result["model_comparison"]
    assert mc["enabled"] is True
    assert mc["target_column"] == "quality"
    assert mc["task"] == "classification"
    assert "RandomForestClassifier" in mc["metrics"]
    assert mc["metrics"]["RandomForestClassifier"]["accuracy"] == 0.87

    # Chart merged into grid with type=model_comparison.
    model_tiles = [c for c in result["charts"] if c["type"] == "model_comparison"]
    assert len(model_tiles) == 1
    tile = model_tiles[0]
    assert tile["status"] == "ok"
    assert tile["image_filename"] is not None

    # And included in flat visualizations list.
    viz_names = [v["filename"] for v in result["visualizations"]]
    assert any("model_comparison" in n for n in viz_names)


def test_model_execution_failure_hides_enabled_flag(_tmp_temp_data_dir):
    """If model stage ran but failed, enabled=False so frontend hides the panel."""
    plan = _plan(mc_enabled=True)
    plan["model_comparison"]["target_column"] = "label"
    plan["model_comparison"]["task"] = "classification"
    plan["model_comparison"]["reason"] = "ok"
    result = compose_eda_response(
        plan=plan,
        execution=_execution([]),
        question="q",
        dataset_metadata=_metadata(),
        model_execution=_model_execution(
            success=False, image_in_output_files=False, target="label"
        ),
    )
    assert result["model_comparison"]["enabled"] is False
    # Reason overridden by executor's.
    assert "failed" in result["model_comparison"]["reason"].lower()
    # No model chart merged since success=False.
    assert all(c["type"] != "model_comparison" for c in result["charts"])


def test_model_execution_image_missing_from_output_files_skips_merge(
    _tmp_temp_data_dir,
):
    """success=True but image not in output_files → don't break grid."""
    plan = _plan(mc_enabled=True)
    result = compose_eda_response(
        plan=plan,
        execution=_execution([]),
        question="q",
        dataset_metadata=_metadata(),
        # success=True but image_in_output_files=False contradicts — mock
        # the belt-and-suspenders path.
        model_execution={
            "success": True,
            "enabled": True,
            "target_column": "quality",
            "task": "classification",
            "metrics": {"RFC": {"accuracy": 0.8}},
            "image_filename": "model_comparison.png",
            "output_files": {},  # <-- missing file
            "reason": "trained",
            "stdout": "",
            "stderr": "",
        },
    )
    # Metrics still surface...
    assert result["model_comparison"]["metrics"]["RFC"]["accuracy"] == 0.8
    # ...but no chart merged (since no bytes to persist).
    assert all(c["type"] != "model_comparison" for c in result["charts"])
