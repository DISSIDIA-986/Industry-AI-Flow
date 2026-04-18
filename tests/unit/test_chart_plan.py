"""Unit tests for deterministic chart planner.

Covers the design-doc test cases + the pass-9 codex findings:
- typical mixed / all-numeric / all-categorical / single-column / empty
- row-cap gating for model comparison
- role-based filtering (boolean, datetime, unknown roles rejected)
- ID-like column exclusion (near-unique numeric/categorical dropped)
- invalid top_corr_pair falls back silently
- normalized chart schema shape (id, type, params, source_columns)
- JSON serialization + determinism
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from backend.services.data_analysis.chart_plan import (
    SCHEMA_VERSION,
    eda_plan_from_metadata,
)


def _numeric_col(
    name: str,
    std: float = 1.0,
    *,
    unique: int = 50,
    non_null: int = 100,
    is_id_like: bool = False,
) -> Dict[str, Any]:
    return {
        "name": name,
        "type": "float64",
        "role": "numeric",
        "non_null_count": non_null,
        "null_count": 0,
        "unique_values": unique,
        "is_id_like": is_id_like,
        "mean": 0.0,
        "min": -1.0,
        "max": 1.0,
        "std": std,
    }


def _categorical_col(
    name: str,
    unique: int = 5,
    *,
    non_null: int = 100,
    is_id_like: bool = False,
) -> Dict[str, Any]:
    return {
        "name": name,
        "type": "object",
        "role": "categorical",
        "non_null_count": non_null,
        "null_count": 0,
        "unique_values": unique,
        "is_id_like": is_id_like,
        "top_values": {f"v{i}": 10 for i in range(min(5, unique))},
    }


def _boolean_col(name: str) -> Dict[str, Any]:
    return {
        "name": name,
        "type": "bool",
        "role": "boolean",
        "non_null_count": 100,
        "null_count": 0,
    }


def _datetime_col(name: str) -> Dict[str, Any]:
    return {
        "name": name,
        "type": "datetime64[ns]",
        "role": "datetime",
        "non_null_count": 100,
        "null_count": 0,
    }


def _metadata(
    columns: List[Dict[str, Any]],
    *,
    rows: int = 100,
    top_corr_pair: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    md: Dict[str, Any] = {
        "filename": "fixture.csv",
        "rows": rows,
        "columns": len(columns),
        "column_names": [c["name"] for c in columns],
        "columns_info": columns,
    }
    if top_corr_pair is not None:
        md["top_corr_pair"] = top_corr_pair
    return md


# --- schema shape -------------------------------------------------------


def test_normalized_chart_schema():
    """Every chart MUST have id, type, params, source_columns."""
    cols = [
        _numeric_col("price", std=10.0),
        _numeric_col("sqft", std=100.0),
        _categorical_col("region", unique=5),
    ]
    plan = eda_plan_from_metadata(_metadata(cols))
    for chart in plan["eda"]["charts"]:
        assert set(chart.keys()) == {"id", "type", "params", "source_columns"}
        assert chart["id"].startswith("chart_")
        assert isinstance(chart["params"], dict)
        assert isinstance(chart["source_columns"], list)
        assert all(isinstance(n, str) for n in chart["source_columns"])


def test_chart_ids_are_stable_and_unique():
    cols = [
        _numeric_col("a", std=2.0),
        _numeric_col("b", std=1.0),
        _categorical_col("c", unique=3),
    ]
    plan = eda_plan_from_metadata(_metadata(cols))
    ids = [c["id"] for c in plan["eda"]["charts"]]
    assert len(ids) == len(set(ids))


# --- typical mixed ------------------------------------------------------


def test_typical_mixed_dataset_produces_expected_charts():
    cols = [
        _numeric_col("price", std=50.0),
        _numeric_col("sqft", std=200.0),
        _numeric_col("age", std=10.0),
        _categorical_col("neighborhood", unique=8),
    ]
    plan = eda_plan_from_metadata(_metadata(cols))

    types = [c["type"] for c in plan["eda"]["charts"]]
    assert types.count("histogram") == 3
    assert "scatter" in types
    assert "heatmap" in types
    assert "bar" in types
    assert "boxplot" in types


def test_top_corr_pair_is_used_for_scatter_when_valid():
    cols = [
        _numeric_col("a", std=100.0),
        _numeric_col("b", std=50.0),
        _numeric_col("c", std=200.0),
    ]
    md = _metadata(
        cols, top_corr_pair={"col_a": "a", "col_b": "b", "abs_rho": 0.9}
    )
    plan = eda_plan_from_metadata(md)
    scatter = next(c for c in plan["eda"]["charts"] if c["type"] == "scatter")
    assert scatter["params"]["x"] == "a"
    assert scatter["params"]["y"] == "b"


def test_invalid_top_corr_pair_falls_back_silently():
    """top_corr_pair references columns no longer in the numeric set.

    Previously the planner blindly trusted metadata. With validation, stale
    pairs fall back to the variance-ranked default.
    """
    cols = [_numeric_col("a", std=2.0), _numeric_col("b", std=1.0)]
    md = _metadata(
        cols,
        top_corr_pair={"col_a": "ghost_x", "col_b": "ghost_y", "abs_rho": 0.99},
    )
    plan = eda_plan_from_metadata(md)
    scatter = next(c for c in plan["eda"]["charts"] if c["type"] == "scatter")
    assert scatter["params"]["x"] == "a"  # variance-ranked fallback
    assert scatter["params"]["y"] == "b"


def test_top_corr_pair_with_self_reference_ignored():
    cols = [_numeric_col("a", std=2.0), _numeric_col("b", std=1.0)]
    md = _metadata(
        cols,
        top_corr_pair={"col_a": "a", "col_b": "a"},  # degenerate self-pair
    )
    plan = eda_plan_from_metadata(md)
    scatter = next(c for c in plan["eda"]["charts"] if c["type"] == "scatter")
    assert scatter["params"]["x"] != scatter["params"]["y"]


# --- all-numeric / all-categorical --------------------------------------


def test_all_numeric_dataset_no_bar_no_boxplot():
    cols = [_numeric_col(f"n{i}", std=float(i + 1)) for i in range(4)]
    plan = eda_plan_from_metadata(_metadata(cols))
    types = [c["type"] for c in plan["eda"]["charts"]]
    assert "bar" not in types
    assert "boxplot" not in types
    assert types.count("histogram") == 3
    assert "scatter" in types
    assert "heatmap" in types


def test_all_categorical_dataset_only_bar():
    cols = [
        _categorical_col("color", unique=3),
        _categorical_col("region", unique=10),
        _categorical_col("tier", unique=4),
    ]
    plan = eda_plan_from_metadata(_metadata(cols))
    types = [c["type"] for c in plan["eda"]["charts"]]
    assert types == ["bar"]
    assert plan["eda"]["charts"][0]["params"]["column"] == "color"


# --- ID-like exclusion (pass-9 P1) --------------------------------------


def test_id_like_numeric_excluded_from_histogram_and_scatter():
    """IDs, timestamps-as-int, ZIP codes should NOT drive charts."""
    cols = [
        _numeric_col("user_id", std=10_000.0, unique=100, is_id_like=True),
        _numeric_col("price", std=5.0, unique=30),
        _numeric_col("sqft", std=20.0, unique=40),
    ]
    plan = eda_plan_from_metadata(_metadata(cols))
    source = {col for c in plan["eda"]["charts"] for col in c["source_columns"]}
    assert "user_id" not in source, "ID-like numeric column leaked into a chart"


def test_id_like_categorical_excluded():
    """A categorical with near-unique values (e.g. free-text descriptions)
    should not produce a bar chart even if its unique_count is within range."""
    cols = [
        # Edge case: 20 unique values with 21 non-null → unique/non_null = 0.95 → is_id_like
        _categorical_col("session_id", unique=20, non_null=21, is_id_like=True),
        _categorical_col("region", unique=5, non_null=100),
    ]
    plan = eda_plan_from_metadata(_metadata(cols))
    bars = [c for c in plan["eda"]["charts"] if c["type"] == "bar"]
    assert len(bars) == 1
    assert bars[0]["params"]["column"] == "region"


def test_id_like_numeric_still_counted_for_heatmap_skip():
    """If id_like dominates, we might end up below 3 non-id numerics → no
    heatmap. Verify the exclusion propagates consistently."""
    cols = [
        _numeric_col("pk", std=1000.0, is_id_like=True),
        _numeric_col("a", std=2.0),
        _numeric_col("b", std=1.0),
    ]
    plan = eda_plan_from_metadata(_metadata(cols))
    types = [c["type"] for c in plan["eda"]["charts"]]
    # only 2 non-id-like numerics → no heatmap
    assert "heatmap" not in types
    # still have scatter from the 2 remaining
    assert "scatter" in types


# --- role coverage (pass-9 P1) ------------------------------------------


def test_boolean_and_datetime_and_unknown_roles_ignored():
    """Role filter must reject non-numeric / non-categorical roles so we
    don't try to histogram a bool or heatmap a timestamp."""
    cols = [
        _boolean_col("is_active"),
        _datetime_col("created_at"),
        {
            "name": "mystery",
            "type": "timedelta64[ns]",
            "role": "unknown",
            "non_null_count": 100,
            "null_count": 0,
        },
        _numeric_col("real_numeric", std=5.0),
        _categorical_col("real_cat", unique=4),
    ]
    plan = eda_plan_from_metadata(_metadata(cols))
    source = {col for c in plan["eda"]["charts"] for col in c["source_columns"]}
    for unwanted in ["is_active", "created_at", "mystery"]:
        assert unwanted not in source


# --- single / empty -----------------------------------------------------


def test_single_numeric_column_produces_one_histogram():
    plan = eda_plan_from_metadata(_metadata([_numeric_col("x", std=1.0)]))
    charts = plan["eda"]["charts"]
    assert len(charts) == 1
    assert charts[0]["type"] == "histogram"
    assert charts[0]["params"] == {"column": "x"}
    assert charts[0]["source_columns"] == ["x"]


def test_single_categorical_column_produces_one_bar():
    plan = eda_plan_from_metadata(_metadata([_categorical_col("k", unique=4)]))
    charts = plan["eda"]["charts"]
    assert len(charts) == 1
    assert charts[0]["type"] == "bar"


def test_empty_metadata_returns_empty_plan_with_rationale():
    plan = eda_plan_from_metadata({"rows": 0, "columns": 0, "columns_info": []})
    assert plan["eda"]["charts"] == []
    assert "no" in plan["rationale"].lower()
    assert plan["schema_version"] == SCHEMA_VERSION


def test_zero_variance_numeric_is_skipped():
    cols = [_numeric_col("const", std=0.0), _categorical_col("c", unique=3)]
    plan = eda_plan_from_metadata(_metadata(cols))
    types = [c["type"] for c in plan["eda"]["charts"]]
    assert "histogram" not in types
    assert "scatter" not in types
    assert "bar" in types


def test_high_cardinality_categorical_skipped():
    cols = [_categorical_col("user_id", unique=5000)]
    plan = eda_plan_from_metadata(_metadata(cols))
    assert plan["eda"]["charts"] == []


# --- model comparison gating --------------------------------------------


def test_model_comparison_disabled_by_default_with_reason():
    cols = [_numeric_col("x"), _numeric_col("y")]
    plan = eda_plan_from_metadata(_metadata(cols, rows=1000))
    mc = plan["model_comparison"]
    assert mc["enabled"] is False
    assert "stretch" in mc["reason"].lower()


def test_model_comparison_reason_mentions_row_cap_when_over_50k():
    cols = [_numeric_col("x")]
    plan = eda_plan_from_metadata(_metadata(cols, rows=75_000))
    reason = plan["model_comparison"]["reason"].lower()
    assert "50" in reason
    assert "row" in reason


# --- serialization / determinism ----------------------------------------


def test_schema_version_always_present():
    plan = eda_plan_from_metadata({"rows": 0, "columns": 0, "columns_info": []})
    assert plan["schema_version"] == 1


def test_planner_is_deterministic():
    cols = [
        _numeric_col("a", std=1.0),
        _numeric_col("b", std=2.0),
        _categorical_col("c", unique=3),
    ]
    md = _metadata(cols)
    assert eda_plan_from_metadata(md) == eda_plan_from_metadata(md)


def test_user_question_preserved_truncated():
    cols = [_numeric_col("x")]
    long_q = "why is " + ("the sky " * 200)
    plan = eda_plan_from_metadata(_metadata(cols), user_question=long_q)
    assert len(plan["user_question"]) <= 500


def test_plan_is_json_serializable():
    import json

    cols = [
        _numeric_col("a", std=3.0),
        _numeric_col("b", std=1.5),
        _numeric_col("c", std=0.5),
        _categorical_col("d", unique=4),
    ]
    plan = eda_plan_from_metadata(_metadata(cols))
    assert json.loads(json.dumps(plan)) == plan
