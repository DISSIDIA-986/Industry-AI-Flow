"""BUG-2 (High): Unseen category silently produces all-zero one-hot vector.

When `CostEstimationService.predict_project()` receives a `project_type` or
`location` value not present in the training set's `category_levels`, the
`_build_feature_matrix` function produces an all-zero one-hot column for that
feature.  This is *silent* — no error, no warning, just a potentially wrong
prediction.

The `unknown_categories` dict in the output records the mismatch, but the
prediction itself may be significantly distorted because the categorical
signal is entirely lost.

This test asserts that the service either raises an error or explicitly logs
a warning when encountering unseen categories, and that the prediction is
flagged as uncertain.

BUG-7 (Medium): Same issue during cross-validation — validation folds
can contain categories unseen in the training fold, silently inflating CV
metrics.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.mark.unit
class TestBug2UnseenCategoryZeroVector:
    def _train_minimal_model(self, tmp_path: Path) -> Path:
        """Train a model on a tiny dataset with known categories."""
        from backend.services.cost_estimation_service import train_cost_estimation_model

        # Create minimal training CSV with only 2 project types and 2 locations
        rows = []
        for i in range(20):
            rows.append(
                {
                    "project_type": "residential_single_family"
                    if i % 2 == 0
                    else "commercial_office",
                    "location": "Toronto" if i % 2 == 0 else "Vancouver",
                    "sqft": 2000 + i * 100,
                    "floors": 2,
                    "num_units": 1,
                    "planned_duration_weeks": 20 + i,
                    "estimated_cost_cad": 400000 + i * 10000,
                    "contractor_rating": 3.5,
                    "complexity_score": 5,
                    "team_experience_years": 10.0,
                    "num_change_orders": 2,
                    "weather_risk_factor": 1.0,
                    "material_volatility": 0.5,
                    "num_subcontractors": 4,
                    "budget_pressure": 0.3,
                    "risk_score": 3.0,
                    "risk_score_original": 3.0,
                    "cost_overrun_pct": 5 + i * 0.5,
                    "actual_cost_cad": (400000 + i * 10000) * 1.05,
                }
            )
        df = pd.DataFrame(rows)
        csv_path = tmp_path / "train.csv"
        df.to_csv(csv_path, index=False)

        model_path = tmp_path / "model.json"
        train_cost_estimation_model(csv_path, model_path)
        return model_path

    def test_predict_with_unseen_project_type_should_warn_or_raise(
        self, tmp_path, unseen_category_project
    ):
        """Prediction with unseen category should explicitly warn, not silently
        produce a zero-vector one-hot encoding."""
        from backend.services.cost_estimation_service import CostEstimationService

        model_path = self._train_minimal_model(tmp_path)
        service = CostEstimationService(model_path=model_path)

        prediction = service.predict_project(unseen_category_project)

        # The bug: unknown_categories is populated but prediction proceeds
        # without any degradation signal (no confidence reduction, no warning flag).
        assert "degraded" in prediction or prediction.get(
            "confidence_degraded", False
        ), (
            "BUG-2: predict_project() returned a prediction for unseen categories "
            f"({prediction.get('unknown_categories')}) without flagging the result "
            "as degraded. The all-zero one-hot encoding silently distorts the prediction."
        )

    def test_predict_with_unseen_category_differs_from_known(
        self, tmp_path, sample_construction_project
    ):
        """Verify that unseen category prediction is noticeably different from
        a known category prediction, proving the zero-vector is distorting results."""
        from backend.services.cost_estimation_service import CostEstimationService

        model_path = self._train_minimal_model(tmp_path)
        service = CostEstimationService(model_path=model_path)

        # Prediction with known category
        known_pred = service.predict_project(sample_construction_project)

        # Same project but with unseen category
        unseen_project = dict(sample_construction_project)
        unseen_project["project_type"] = "underwater_tunnel"
        unseen_pred = service.predict_project(unseen_project)

        # The overrun predictions should differ — if they're identical,
        # it means the categorical feature had no effect (all-zero vector).
        known_overrun = known_pred["predicted_cost_overrun_pct"]
        unseen_overrun = unseen_pred["predicted_cost_overrun_pct"]

        # We expect some difference since the one-hot is all zeros for unseen,
        # but the result dict should FLAG this to the caller.
        assert unseen_pred.get(
            "unknown_categories"
        ), "BUG-2: unknown_categories should be populated for unseen project_type"
        # The key assertion: the prediction should carry a degradation marker
        assert unseen_pred.get("confidence_degraded") is True, (
            f"BUG-2: unseen category 'underwater_tunnel' produced overrun={unseen_overrun:.2f} "
            f"vs known category overrun={known_overrun:.2f}, but no confidence_degraded flag "
            "was set. Callers cannot distinguish reliable from unreliable predictions."
        )
