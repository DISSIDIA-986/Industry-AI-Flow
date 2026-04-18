"""Unit tests for analysis_planner (model-comparison stretch goal)."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from backend.services.data_analysis.analysis_planner import (
    decide_model_comparison,
)


def _num_col(
    name: str,
    *,
    unique: int = 50,
    non_null: int = 500,
    is_id_like: bool = False,
) -> Dict[str, Any]:
    return {
        "name": name,
        "type": "float64",
        "role": "numeric",
        "non_null_count": non_null,
        "unique_values": unique,
        "is_id_like": is_id_like,
    }


def _cat_col(
    name: str,
    *,
    unique: int = 3,
    is_id_like: bool = False,
) -> Dict[str, Any]:
    return {
        "name": name,
        "type": "object",
        "role": "categorical",
        "non_null_count": 500,
        "unique_values": unique,
        "is_id_like": is_id_like,
    }


def _metadata(columns: List[Dict[str, Any]], *, rows: int = 500) -> Dict[str, Any]:
    return {"rows": rows, "columns": len(columns), "columns_info": columns}


# --- target detection by name pattern -----------------------------------


@pytest.mark.unit
class TestTargetDetection:
    def test_exact_match_target(self):
        md = _metadata([_num_col("x"), _num_col("target", unique=3)])
        plan = decide_model_comparison(md)
        assert plan["enabled"] is True
        assert plan["target_column"] == "target"

    def test_quality_column_matches_winequality(self):
        md = _metadata(
            [_num_col("alcohol"), _num_col("pH"), _num_col("quality", unique=6)],
            rows=1599,
        )
        plan = decide_model_comparison(md)
        assert plan["enabled"] is True
        assert plan["target_column"] == "quality"
        assert plan["task"] == "classification"  # 6 < 10 → classification

    def test_survived_column_matches_titanic(self):
        md = _metadata(
            [_num_col("age"), _cat_col("sex", unique=2), _num_col("survived", unique=2)]
        )
        plan = decide_model_comparison(md)
        assert plan["target_column"] == "survived"
        assert plan["task"] == "classification"

    def test_suffix_match_label(self):
        md = _metadata([_num_col("f1"), _cat_col("user_label", unique=4)])
        plan = decide_model_comparison(md)
        assert plan["target_column"] == "user_label"

    def test_last_column_fallback_when_no_name_match(self):
        md = _metadata([_num_col("a"), _num_col("b"), _num_col("c", unique=4)])
        plan = decide_model_comparison(md)
        assert plan["enabled"] is True
        assert plan["target_column"] == "c"

    def test_last_column_refused_when_id_like(self):
        md = _metadata(
            [_num_col("a"), _num_col("b"), _num_col("row_id", is_id_like=True)]
        )
        plan = decide_model_comparison(md)
        assert plan["enabled"] is False
        assert "target" in plan["reason"].lower()

    def test_target_column_skipped_when_id_like(self):
        md = _metadata(
            [
                _num_col("f1"),
                _num_col("label", is_id_like=True),  # name matches but id-like
                _num_col("score", unique=30),  # fallback-last
            ]
        )
        plan = decide_model_comparison(md)
        # id-like label refused → falls through to last-column (score) or
        # keeps searching. Either way, not 'label'.
        assert plan["target_column"] != "label"


# --- task classification ------------------------------------------------


@pytest.mark.unit
class TestTaskClassification:
    def test_numeric_with_many_unique_is_regression(self):
        md = _metadata([_num_col("f"), _num_col("price", unique=200)])
        assert decide_model_comparison(md)["task"] == "regression"

    def test_numeric_with_few_unique_is_classification(self):
        md = _metadata([_num_col("f"), _num_col("class", unique=3)])
        assert decide_model_comparison(md)["task"] == "classification"

    def test_categorical_is_classification(self):
        md = _metadata([_num_col("f"), _cat_col("target", unique=3)])
        assert decide_model_comparison(md)["task"] == "classification"

    def test_boolean_target_is_classification(self):
        md = _metadata(
            [
                _num_col("f"),
                {
                    "name": "target",
                    "role": "boolean",
                    "type": "bool",
                    "non_null_count": 100,
                    "unique_values": 2,
                },
            ]
        )
        assert decide_model_comparison(md)["task"] == "classification"


# --- guardrails ---------------------------------------------------------


@pytest.mark.unit
class TestGuardrails:
    def test_row_cap_exceeded_disables(self):
        md = _metadata([_num_col("f"), _num_col("target", unique=3)], rows=100_000)
        plan = decide_model_comparison(md)
        assert plan["enabled"] is False
        assert "50" in plan["reason"]

    def test_too_few_rows_disables(self):
        md = _metadata([_num_col("f"), _num_col("target", unique=3)], rows=5)
        plan = decide_model_comparison(md)
        assert plan["enabled"] is False
        assert "20" in plan["reason"]

    def test_single_column_disables(self):
        md = _metadata([_num_col("only")], rows=500)
        plan = decide_model_comparison(md)
        assert plan["enabled"] is False

    def test_classification_too_many_classes_disables(self):
        # 25 unique categorical values — exceeds cardinality cap.
        md = _metadata([_num_col("f"), _cat_col("label", unique=25)])
        plan = decide_model_comparison(md)
        assert plan["enabled"] is False
        assert "cap" in plan["reason"].lower() or "class" in plan["reason"].lower()

    def test_degenerate_target_one_unique_disables(self):
        md = _metadata([_num_col("f"), _num_col("target", unique=1)])
        plan = decide_model_comparison(md)
        assert plan["enabled"] is False


# --- models list --------------------------------------------------------


@pytest.mark.unit
class TestModelsList:
    def test_classification_models(self):
        md = _metadata([_num_col("f"), _cat_col("label", unique=3)])
        plan = decide_model_comparison(md)
        assert plan["models"] == ["RandomForestClassifier", "LogisticRegression"]

    def test_regression_models(self):
        md = _metadata([_num_col("f"), _num_col("price", unique=200)])
        plan = decide_model_comparison(md)
        assert plan["models"] == ["RandomForestRegressor", "Ridge"]


# --- shape --------------------------------------------------------------


@pytest.mark.unit
class TestReturnShape:
    def test_always_has_required_keys(self):
        # Even when disabled, every key must be present so downstream
        # consumers (report_composer) never hit KeyError.
        md = _metadata([])
        plan = decide_model_comparison(md)
        for k in ("enabled", "target_column", "task", "models", "reason"):
            assert k in plan, f"missing key: {k}"

    def test_disabled_always_null_fields(self):
        md = _metadata([_num_col("only")])  # single column → disabled
        plan = decide_model_comparison(md)
        assert plan["enabled"] is False
        assert plan["target_column"] is None
        assert plan["task"] is None
        assert plan["models"] == []
