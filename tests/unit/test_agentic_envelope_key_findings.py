"""Regression tests for agentic_envelope._extract_key_findings synthesis.

Triggered by a live demo bug where a user asked for "do EDA and then apply
different ML comparison, output AUC results" against titanic.csv. GLM-4.7
produced valid code + valid AUC numbers, but emitted the summary as:
    ANALYSIS_SUMMARY_JSON={'model_comparison': {'RandomForest': {'mean_auc': 0.87}, ...}}

with no top-level `key_findings` list. The envelope then returned empty
bullets, blanking the "Key Findings" panel even though the numbers were
right there in the structured summary.

These tests lock in the synthesis fallbacks in the order the envelope
applies them: explicit key_findings → model_comparison → generic
top-level scalars → plan prose.
"""
from __future__ import annotations

from backend.services.data_analysis.agentic_envelope import _extract_key_findings


def test_explicit_key_findings_preserved():
    """When the model emits key_findings, pass through unchanged."""
    summary = {
        "key_findings": ["AUC=0.87 RF best", "75% feature importance from Fare"],
        "model_comparison": {"RandomForest": {"mean_auc": 0.87}},  # ignored
    }
    out = _extract_key_findings(summary, plan={})
    assert out == ["AUC=0.87 RF best", "75% feature importance from Fare"]


def test_synthesize_from_model_comparison_sorted_desc():
    """No key_findings but model_comparison present → synthesize leader
    bullet + per-model AUCs sorted best-first. Matches the live bug shape."""
    summary = {
        "model_comparison": {
            "LogisticRegression": {"mean_auc": 0.8521, "std_auc": 0.0218},
            "RandomForest": {"mean_auc": 0.8735, "std_auc": 0.0236},
            "GradientBoosting": {"mean_auc": 0.8757, "std_auc": 0.0199},
            "SVM": {"mean_auc": 0.8555, "std_auc": 0.0142},
        },
    }
    out = _extract_key_findings(summary, plan={})
    # First bullet is the leader callout (synthetic)
    assert out[0].startswith("Best model: GradientBoosting")
    assert "0.8757" in out[0]
    # Remaining bullets sorted desc by AUC:
    #   GradientBoosting 0.8757 > RandomForest 0.8735 > SVM 0.8555 > LR 0.8521
    assert "GradientBoosting" in out[1]
    assert "RandomForest" in out[2]
    assert "SVM" in out[3]
    assert "LogisticRegression" in out[-1]  # weakest last
    # Std dev threaded in when present
    assert "± 0.020" in out[1] or "± 0.0199" in out[1]


def test_synthesize_from_model_comparison_with_bare_scalars():
    """model_comparison values that are plain floats also work (common
    when a quick comparison prints a flat dict)."""
    summary = {"model_comparison": {"LR": 0.74, "RF": 0.81, "XGB": 0.83}}
    out = _extract_key_findings(summary, plan={})
    assert out[0].startswith("Best model: XGB")
    assert "XGB" in out[1] and "0.8300" in out[1]


def test_synthesize_from_alternate_score_keys():
    """Model entries using `auc` / `roc_auc` / `accuracy` are all detected.

    Codex M1 (2026-04-19): heterogeneous metrics can't be ranked together
    (0.93 accuracy is not 'better than' 0.91 AUC — different scales).
    When labels diverge, the envelope keeps the dominant metric group
    and drops the outlier with a note.
    """
    summary = {
        "model_comparison": {
            "A": {"auc": 0.91},
            "B": {"roc_auc": 0.88},
            "C": {"accuracy": 0.93},
        },
    }
    out = _extract_key_findings(summary, plan={})
    leader = out[0]
    # Dominant metric is AUC (A + B); C's accuracy is excluded.
    assert leader.startswith("Best model: A")
    assert "AUC=0.91" in leader
    # Excluded entry is flagged in a trailing note.
    assert any("excluded" in b.lower() for b in out)


def test_metric_label_preserved_not_hardcoded_as_auc():
    """Codex review fix: when the summary reports accuracy, bullets must
    say `accuracy=0.93`, not `AUC=0.93`. Mislabeling metrics as AUC is
    user-visible misinformation if the user asked for accuracy/R²/etc.
    """
    summary = {
        "model_comparison": {
            "RF": {"accuracy": 0.93, "std": 0.02},
            "LR": {"accuracy": 0.88, "std": 0.03},
        },
    }
    out = _extract_key_findings(summary, plan={})
    assert "accuracy=" in out[0]  # "Best model: RF (accuracy=0.9300 ± 0.020)"
    assert "AUC=" not in out[0]
    for bullet in out[1:]:
        assert "accuracy=" in bullet
        assert "AUC=" not in bullet


def test_metric_label_auc_still_works_for_auc_summaries():
    """AUC summaries still render with AUC label — this is the common
    live-demo path, must not regress from the label generalization."""
    summary = {
        "model_comparison": {
            "RF": {"mean_auc": 0.87, "std_auc": 0.02},
            "GB": {"mean_auc": 0.89, "std_auc": 0.019},
        },
    }
    out = _extract_key_findings(summary, plan={})
    assert out[0].startswith("Best model: GB")
    assert "AUC=0.89" in out[0]
    assert "± 0.019" in out[0]


def test_error_metric_ranks_ascending():
    """MAE / RMSE are error metrics (lower is better). The header bullet
    should identify the lowest-error model as 'Best'."""
    summary = {
        "model_comparison": {
            "LinReg": {"mae": 3.4},
            "RF": {"mae": 2.1},
            "XGB": {"mae": 2.8},
        },
    }
    out = _extract_key_findings(summary, plan={})
    # Best MAE is 2.1 (RF), which should lead.
    assert out[0].startswith("Best model: RF")
    assert "MAE=2.1" in out[0]
    # Bullets should be sorted ascending (lowest error first).
    assert "RF" in out[1]  # 2.1
    assert "XGB" in out[2]  # 2.8
    assert "LinReg" in out[3]  # 3.4


def test_generic_fallback_for_simple_scalar_summary():
    """No key_findings, no model_comparison, but a single numeric top-level
    field → synthesize a single 'key: value' bullet so the panel isn't
    blank."""
    summary = {"tip_mean": 2.99, "chart_type": "bar"}
    out = _extract_key_findings(summary, plan={})
    assert len(out) == 1
    assert "tip_mean" in out[0] and "2.99" in out[0]


def test_plan_fallback_when_summary_is_empty():
    """No usable summary fields at all → fall back to plan prose so the
    user at least sees what the model was trying to do."""
    summary: dict = {}
    plan = {
        "business_goal": "Classify passenger survival",
        "analysis_plan": "Train 4 models, compare AUC via 5-fold CV",
    }
    out = _extract_key_findings(summary, plan)
    assert len(out) == 2
    assert out[0].startswith("Goal:")
    assert "Classify passenger survival" in out[0]
    assert out[1].startswith("Approach:")


def test_nan_and_inf_scores_skipped():
    """Codex M2: NaN/Inf must not produce 'AUC=nan' bullets."""
    summary = {
        "model_comparison": {
            "Broken": {"mean_auc": float("nan")},
            "AlsoBroken": {"mean_auc": float("inf")},
            "Good": {"mean_auc": 0.85},
        },
    }
    out = _extract_key_findings(summary, plan={})
    assert out[0].startswith("Best model: Good")
    for b in out:
        assert "nan" not in b.lower()
        assert "inf" not in b.lower()


def test_bool_scores_rejected():
    """Codex M2: bool is a subclass of int — float(True)==1.0 would
    mis-rank a broken entry as the best model."""
    summary = {
        "model_comparison": {
            "Buggy": {"mean_auc": True},
            "Real": {"mean_auc": 0.87},
        },
    }
    out = _extract_key_findings(summary, plan={})
    assert out[0].startswith("Best model: Real")
    for b in out:
        assert "Buggy" not in b


def test_bullet_count_capped():
    """Codex M3: don't flood the UI with 30+ model bullets."""
    mc = {f"M{i:02d}": {"mean_auc": 0.5 + i * 0.01} for i in range(30)}
    out = _extract_key_findings({"model_comparison": mc}, plan={})
    # 1 leader + 10 models + 1 truncation note = 12
    assert len(out) <= 12
    assert any("more model" in b for b in out)


def test_synthesis_does_not_mask_explicit_key_findings():
    """Priority check: even with rich model_comparison, if the model
    also emitted explicit key_findings, the explicit list wins and
    model_comparison is NOT synthesized over it."""
    summary = {
        "key_findings": ["Custom bullet 1", "Custom bullet 2"],
        "model_comparison": {"A": {"mean_auc": 0.9}},
    }
    out = _extract_key_findings(summary, plan={"business_goal": "unused"})
    assert out == ["Custom bullet 1", "Custom bullet 2"]
