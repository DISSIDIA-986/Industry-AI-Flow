from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.workflow_query_routes import get_workflow_runner, router as workflow_router
from backend.services.cost_estimation_service import (
    CostEstimationService,
    train_cost_estimation_model,
)
from backend.services.workflows.orchestrator import DefaultWorkflowRunner, WorkflowOrchestrator


def _build_dataset(rows: int = 220, seed: int = 33) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    project_type = rng.choice(
        [
            "residential_single_family",
            "residential_multi_family",
            "commercial_office",
            "industrial_warehouse",
        ],
        size=rows,
    )
    location = rng.choice(
        ["Toronto", "Calgary", "Ottawa", "Vancouver", "Montreal"],
        size=rows,
    )
    sqft = rng.uniform(1500, 400000, size=rows)
    planned_duration_weeks = rng.uniform(18, 1500, size=rows)
    estimated_cost_cad = (sqft * rng.uniform(190, 330, size=rows)) + (
        planned_duration_weeks * rng.uniform(1200, 5200, size=rows)
    )
    num_change_orders = rng.integers(0, 24, size=rows)
    material_volatility = rng.uniform(0.1, 0.9, size=rows)
    budget_pressure = rng.uniform(0.0, 0.8, size=rows)
    contractor_rating = rng.uniform(2.5, 5.0, size=rows)
    team_experience_years = rng.uniform(2.0, 19.0, size=rows)
    complexity_score = rng.integers(2, 10, size=rows)
    overrun = (
        1.1 * num_change_orders
        + 16.0 * material_volatility
        + 8.0 * budget_pressure
        + 0.25 * complexity_score
        - 2.0 * contractor_rating
        - 0.1 * team_experience_years
        + rng.normal(0.0, 2.0, size=rows)
    )
    overrun = np.clip(overrun, -12.0, 55.0)
    actual_cost_cad = estimated_cost_cad * (1.0 + (overrun / 100.0))

    return pd.DataFrame(
        {
            "project_type": project_type,
            "location": location,
            "sqft": sqft,
            "floors": rng.integers(1, 40, size=rows),
            "num_units": rng.integers(0, 240, size=rows),
            "planned_duration_weeks": planned_duration_weeks,
            "actual_duration_weeks": planned_duration_weeks
            * (1.0 + np.clip(overrun / 100.0, -0.1, 0.45)),
            "schedule_delay_pct": np.clip(overrun * 0.5, -10.0, 45.0),
            "estimated_cost_cad": estimated_cost_cad,
            "actual_cost_cad": actual_cost_cad,
            "cost_overrun_pct": overrun,
            "contractor_rating": contractor_rating,
            "complexity_score": complexity_score,
            "team_experience_years": team_experience_years,
            "num_change_orders": num_change_orders,
            "weather_risk_factor": rng.uniform(0.2, 0.7, size=rows),
            "material_volatility": material_volatility,
            "num_subcontractors": rng.integers(3, 100, size=rows),
            "budget_pressure": budget_pressure,
            "risk_score": rng.uniform(20, 75, size=rows),
            "risk_score_original": rng.uniform(5, 65, size=rows),
            "on_budget": overrun <= 5,
            "on_schedule": np.clip(overrun * 0.5, -10.0, 45.0) <= 5,
            "data_source": "synthetic_industry_based",
        }
    )


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    dataset_path = tmp_path / "workflow_train.csv"
    model_path = tmp_path / "workflow_model.json"
    _build_dataset().to_csv(dataset_path, index=False)

    train_cost_estimation_model(
        dataset_path=dataset_path,
        output_model_path=model_path,
        ridge_alpha=8.0,
        folds=4,
        random_seed=11,
    )
    service = CostEstimationService(model_path=model_path)
    service.load(model_path)

    runner = DefaultWorkflowRunner(
        orchestrator=WorkflowOrchestrator(
            services=SimpleNamespace(cost_estimation_service=service)
        )
    )

    app = FastAPI()
    app.include_router(workflow_router)

    async def _override_runner():
        return runner

    app.dependency_overrides[get_workflow_runner] = _override_runner
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_workflow_query_cost_estimation_from_natural_language(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/workflow/query",
        json={
            "query": (
                "请做建筑成本估算: commercial office, location Toronto, sqft 120000, "
                "floors 12, duration 96 weeks, budget 120m, contractor rating 4.1, "
                "complexity 7, team experience 11, change orders 5, weather risk 0.4, "
                "material volatility 0.35, subcontractors 20, budget pressure 0.45, "
                "risk score 52, risk score original 43"
            )
        },
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["success"] is True
    assert payload["intent"] == "cost_estimation"
    assert "Cost estimation result" in payload["response"]
    assert payload["metadata"]["cost_estimation_status"] == "ok"
    assert payload["metadata"]["shortcut_response"] is True
    assert payload["metadata"]["cost_estimation_prediction"]["predicted_actual_cost_cad"] > 0


def test_workflow_query_cost_estimation_requires_budget_feature(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/workflow/query",
        json={
            "query": "帮我估算这个工程成本，commercial office, location Toronto, sqft 80000, floors 10"
        },
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["success"] is True
    assert payload["intent"] == "cost_estimation"
    assert "please provide at least" in payload["response"].lower()
    assert payload["metadata"]["cost_estimation_status"] == "need_features"
    assert payload["metadata"]["shortcut_response"] is True
