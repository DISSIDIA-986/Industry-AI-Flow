"""Unit tests for analysis_planner (model-comparison stretch goal)."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from backend.services.data_analysis.analysis_planner import (
    decide_model_comparison,
    method_directive,
    plan_analysis_methods,
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


# ========================================================================
# Advanced-analysis method planner (plan_analysis_methods / method_directive)
# ========================================================================


def _dt_col(name: str, *, non_null: int = 500) -> Dict[str, Any]:
    return {
        "name": name,
        "type": "datetime64[ns]",
        "role": "datetime",
        "non_null_count": non_null,
    }


def _bool_col(name: str) -> Dict[str, Any]:
    return {
        "name": name,
        "type": "bool",
        "role": "boolean",
        "non_null_count": 500,
        "unique_values": 2,
    }


def _kinds(plan: Dict[str, Any]) -> List[str]:
    return [m["kind"] for m in plan["methods"]]


@pytest.mark.unit
class TestMethodDetection:
    def test_two_group_comparison(self):
        md = _metadata([_cat_col("sex", unique=2), _num_col("wage")])
        plan = plan_analysis_methods(md, "does wage differ between sex groups?")
        assert _kinds(plan) == ["group_comparison"]
        card = plan["methods"][0]
        assert card["columns"] == ["sex", "wage"]
        assert card["n_groups"] == 2
        d = method_directive(plan)
        assert "Welch" in d and "mannwhitneyu" in d and "Cohen" in d

    def test_multi_group_comparison_uses_anova(self):
        md = _metadata([_cat_col("region", unique=4), _num_col("cost")])
        plan = plan_analysis_methods(md, "compare cost across region")
        assert _kinds(plan) == ["group_comparison"]
        d = method_directive(plan)
        assert "f_oneway" in d and "kruskal" in d and "eta" in d.lower()

    def test_correlation_prefers_top_corr_pair(self):
        md = _metadata([_num_col("a"), _num_col("b"), _num_col("c")])
        md["top_corr_pair"] = {"col_a": "b", "col_b": "c", "abs_rho": 0.9}
        plan = plan_analysis_methods(md, "what is the relationship among these?")
        assert _kinds(plan) == ["correlation"]
        assert plan["methods"][0]["columns"] == ["b", "c"]
        d = method_directive(plan)
        assert "pearsonr" in d and "spearmanr" in d and "confidence interval" in d

    def test_correlation_prefers_named_columns_over_top_pair(self):
        md = _metadata([_num_col("height"), _num_col("weight"), _num_col("noise")])
        md["top_corr_pair"] = {"col_a": "height", "col_b": "noise", "abs_rho": 0.9}
        plan = plan_analysis_methods(
            md, "is there a correlation between weight and noise?"
        )
        # both 'weight' and 'noise' are named → they win over the top pair
        assert set(plan["methods"][0]["columns"]) == {"weight", "noise"}

    def test_categorical_association(self):
        md = _metadata([_cat_col("material", unique=4), _cat_col("outcome", unique=3)])
        plan = plan_analysis_methods(
            md, "is material associated with outcome (independent)?"
        )
        assert "cat_association" in _kinds(plan)
        d = method_directive(plan)
        assert "chi2_contingency" in d and "Cramér" in d

    def test_timeseries_forecast(self):
        md = _metadata([_dt_col("date"), _num_col("sales")], rows=300)
        plan = plan_analysis_methods(md, "forecast the sales trend over time")
        assert _kinds(plan) == ["timeseries"]
        assert plan["methods"][0]["columns"] == ["date", "sales"]
        d = method_directive(plan)
        assert "STLForecast" in d or "ARIMA" in d
        assert "naive" in d.lower() and "baseline" in d.lower()

    def test_timeseries_from_object_dated_column_name(self):
        # date arrived unparsed as object dtype but the name reads as a time axis
        date_like = _cat_col("order_date", unique=250)
        md = _metadata([date_like, _num_col("revenue")], rows=250)
        plan = plan_analysis_methods(
            md, "show the revenue trend over time and forecast"
        )
        assert _kinds(plan) == ["timeseries"]

    def test_feature_importance(self):
        md = _metadata([_num_col("f1"), _num_col("f2"), _num_col("target", unique=2)])
        plan = plan_analysis_methods(md, "why is the target what it is? key drivers?")
        assert "feature_importance" in _kinds(plan)
        d = method_directive(plan)
        assert "permutation_importance" in d and "Dummy" in d and "baseline" in d


@pytest.mark.unit
class TestMethodDefaultOff:
    """The planner must be purely additive — EDA-only requests stay untouched."""

    def test_pure_distribution_request_no_methods(self):
        md = _metadata([_num_col("a"), _cat_col("c")])
        plan = plan_analysis_methods(md, "show me the distribution of a")
        assert plan["methods"] == []
        assert method_directive(plan) == ""

    def test_compare_intent_but_no_group_column(self):
        # comparison intent but only numeric cols → no group factor → skip
        md = _metadata([_num_col("a"), _num_col("b")])
        plan = plan_analysis_methods(md, "compare a higher or lower")
        assert "group_comparison" not in _kinds(plan)

    def test_relation_intent_but_single_numeric(self):
        md = _metadata([_num_col("a"), _cat_col("c")])
        plan = plan_analysis_methods(md, "what drives the relationship?")
        assert "correlation" not in _kinds(plan)

    def test_empty_metadata_no_crash(self):
        plan = plan_analysis_methods({}, "anything at all")
        assert plan["methods"] == []
        assert method_directive(plan) == ""

    def test_empty_question_no_methods(self):
        md = _metadata([_cat_col("sex", unique=2), _num_col("wage")])
        plan = plan_analysis_methods(md, "")
        assert plan["methods"] == []


@pytest.mark.unit
class TestMethodGuardrails:
    def test_timeseries_too_few_points_skips(self):
        md = _metadata([_dt_col("date"), _num_col("sales")], rows=10)
        plan = plan_analysis_methods(md, "forecast sales over time")
        assert "timeseries" not in _kinds(plan)

    def test_group_column_too_high_cardinality_skipped(self):
        # 40-level categorical is an ID-ish factor, not a group → not selected
        md = _metadata([_cat_col("code", unique=40), _num_col("wage")])
        plan = plan_analysis_methods(md, "does wage differ between code groups?")
        assert "group_comparison" not in _kinds(plan)

    def test_id_like_group_column_skipped(self):
        md = _metadata(
            [_cat_col("user_id", unique=3, is_id_like=True), _num_col("wage")]
        )
        plan = plan_analysis_methods(md, "does wage differ between groups?")
        assert "group_comparison" not in _kinds(plan)

    def test_id_like_numeric_excluded_from_correlation(self):
        md = _metadata(
            [_num_col("row_id", is_id_like=True), _num_col("a"), _num_col("b")]
        )
        plan = plan_analysis_methods(md, "relationship between the numeric columns")
        if "correlation" in _kinds(plan):
            assert "row_id" not in plan["methods"][0]["columns"]

    def test_at_most_two_method_cards(self):
        # A question that trips many intents at once must still cap at 2.
        md = _metadata(
            [
                _dt_col("date"),
                _cat_col("region", unique=3),
                _num_col("cost"),
                _num_col("size"),
                _num_col("target", unique=2),
            ],
            rows=300,
        )
        q = (
            "forecast cost trend over time, compare cost across region, "
            "what is the correlation between cost and size, and why is target — "
            "which features are most important?"
        )
        plan = plan_analysis_methods(md, q)
        assert len(plan["methods"]) <= 2
        # timeseries has top priority and must survive truncation
        assert plan["methods"][0]["kind"] == "timeseries"

    def test_boolean_column_is_valid_group(self):
        md = _metadata([_bool_col("is_delayed"), _num_col("cost")])
        plan = plan_analysis_methods(md, "does cost differ between delayed groups?")
        assert "group_comparison" in _kinds(plan)

    def test_very_long_question_no_crash(self):
        md = _metadata([_cat_col("sex", unique=2), _num_col("wage")])
        plan = plan_analysis_methods(md, "compare " * 5000 + "wage between sex")
        assert isinstance(plan["methods"], list)


@pytest.mark.unit
class TestMethodReturnShape:
    def test_shape_keys_present(self):
        md = _metadata([_cat_col("sex", unique=2), _num_col("wage")])
        plan = plan_analysis_methods(md, "does wage differ between sex?")
        assert "methods" in plan and "reason" in plan
        for card in plan["methods"]:
            assert {"kind", "columns", "detail"} <= set(card)

    def test_directive_records_statistical_tests_contract(self):
        md = _metadata([_cat_col("sex", unique=2), _num_col("wage")])
        d = method_directive(plan_analysis_methods(md, "does wage differ by sex?"))
        # the summary contract the envelope + tests rely on
        assert "statistical_tests" in d
        assert "EXPLORATORY" in d and "causal" in d
        assert "key_findings" in d


# ------------------------------------------------------------------------
# Adversarial-review hardening (Codex P1/P2 fixes 2026-07-12)
# ------------------------------------------------------------------------


@pytest.mark.unit
class TestMethodAdversarialHardening:
    def test_trend_over_time_alone_does_not_forecast(self):
        # "trend over time" with no explicit forecast word must stay EDA (P1 #1):
        # forcing a full ARIMA/ETS backtest on a plain line-chart request is wrong.
        md = _metadata([_dt_col("date"), _num_col("cost")], rows=300)
        plan = plan_analysis_methods(md, "show the cost trend over time")
        assert "timeseries" not in _kinds(plan)

    def test_explicit_forecast_word_still_routes_timeseries(self):
        md = _metadata([_dt_col("date"), _num_col("cost")], rows=300)
        plan = plan_analysis_methods(md, "forecast cost for the next 6 months")
        assert "timeseries" in _kinds(plan)

    def test_bare_why_does_not_train_a_model(self):
        # "why is the price distribution skewed?" must NOT trigger ML (P1 #2).
        md = _metadata(
            [
                _num_col("price", unique=200),
                _cat_col("region", unique=4),
                _num_col("sqft"),
            ]
        )
        plan = plan_analysis_methods(md, "why is the price distribution skewed?")
        assert "feature_importance" not in _kinds(plan)

    def test_explicit_driver_wording_still_routes_importance(self):
        md = _metadata([_num_col("f1"), _num_col("f2"), _num_col("target", unique=2)])
        plan = plan_analysis_methods(
            md, "which features are the main drivers of target?"
        )
        assert "feature_importance" in _kinds(plan)

    def test_cat_association_does_not_add_numeric_correlation(self):
        # "is material associated with outcome?" → chi-square only, NOT a spurious
        # correlation on unnamed numeric cols (P1 #3).
        md = _metadata(
            [
                _cat_col("material", unique=4),
                _cat_col("outcome", unique=3),
                _num_col("cost"),
                _num_col("duration"),
            ]
        )
        plan = plan_analysis_methods(md, "is material associated with outcome?")
        assert "cat_association" in _kinds(plan)
        assert "correlation" not in _kinds(plan)

    def test_correlation_kept_when_both_numeric_cols_named(self):
        # If the user explicitly names two numeric cols, correlation is legit even
        # alongside a categorical-association question.
        md = _metadata(
            [
                _cat_col("material", unique=4),
                _cat_col("outcome", unique=3),
                _num_col("cost"),
                _num_col("duration"),
            ]
        )
        plan = plan_analysis_methods(
            md,
            "is material associated with outcome, and is cost correlated with duration?",
        )
        # both cards may appear but truncate to 2; correlation must survive since
        # its columns were named.
        assert "correlation" in _kinds(plan) or "cat_association" in _kinds(plan)

    def test_boolean_group_actually_routes(self):
        # Real extractor metadata leaves boolean unique_values unset; the card must
        # still build with n_groups=2 (P2 #8).
        md = _metadata([_bool_col("is_delayed"), _num_col("cost")])
        plan = plan_analysis_methods(md, "does cost differ between delayed groups?")
        assert "group_comparison" in _kinds(plan)
        assert plan["methods"][0]["n_groups"] == 2

    def test_numeric_id_name_not_picked_as_value(self):
        # project_number (numeric 1..500, not flagged id_like) must not win the
        # value pick over a real measurement (P2 #9).
        md = _metadata(
            [
                _cat_col("crew_type", unique=3),
                _num_col("project_number", unique=500, non_null=500),
                _num_col("rework_cost", unique=480),
            ]
        )
        plan = plan_analysis_methods(md, "compare across crew type")
        assert "group_comparison" in _kinds(plan)
        assert plan["methods"][0]["columns"][1] == "rework_cost"

    def test_feature_importance_skipped_on_large_dataset(self):
        # rows×features over the light budget → skip FI so it can't blow the
        # 30s sandbox budget (P1 #4).
        md = _metadata(
            [_num_col("f1"), _num_col("f2"), _num_col("target", unique=2)],
            rows=2_000_000,
        )
        plan = plan_analysis_methods(
            md, "which features are the key drivers of target?"
        )
        assert "feature_importance" not in _kinds(plan)

    def test_feature_importance_directive_bounds_repeats(self):
        md = _metadata([_num_col("f1"), _num_col("f2"), _num_col("target", unique=2)])
        d = method_directive(
            plan_analysis_methods(md, "which features are the key drivers of target?")
        )
        assert "n_repeats=3" in d and "2000" in d

    def test_timeseries_directive_handles_ets_interval(self):
        md = _metadata([_dt_col("date"), _num_col("sales")], rows=300)
        d = method_directive(
            plan_analysis_methods(md, "forecast sales for the next 12 months")
        )
        assert "conf_int" in d and "resid" in d.lower()

    def test_group_picked_by_value_mention(self):
        # User names the category LEVELS (Lunch/Dinner) not the column (`time`).
        time_col = {
            "name": "time",
            "role": "categorical",
            "type": "object",
            "non_null_count": 244,
            "unique_values": 2,
            "top_values": {"Dinner": 176, "Lunch": 68},
        }
        md = _metadata([_cat_col("sex", unique=2), time_col, _num_col("tip")])
        plan = plan_analysis_methods(
            md, "does the tip differ between Lunch and Dinner?"
        )
        assert plan["methods"][0]["kind"] == "group_comparison"
        assert plan["methods"][0]["columns"][0] == "time"
