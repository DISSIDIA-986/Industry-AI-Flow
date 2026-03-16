from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import cost_estimation_routes


def _build_dataset(rows: int = 220, seed: int = 19) -> pd.DataFrame:
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
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    model_path = tmp_path / "latest.json"
    monkeypatch.setenv("COST_ESTIMATION_MODEL_PATH", str(model_path))
    monkeypatch.setenv("ADMIN_KEY", "integration-admin-key")
    cost_estimation_routes._service = None

    app = FastAPI()
    app.include_router(cost_estimation_routes.router)
    with TestClient(app) as test_client:
        yield test_client

    cost_estimation_routes._service = None


def _sample_project_payload(df: pd.DataFrame, idx: int = 0) -> dict:
    row = df.iloc[idx]
    return {
        "project_type": str(row["project_type"]),
        "location": str(row["location"]),
        "sqft": float(row["sqft"]),
        "floors": int(row["floors"]),
        "num_units": int(row["num_units"]),
        "planned_duration_weeks": float(row["planned_duration_weeks"]),
        "estimated_cost_cad": float(row["estimated_cost_cad"]),
        "contractor_rating": float(row["contractor_rating"]),
        "complexity_score": int(row["complexity_score"]),
        "team_experience_years": float(row["team_experience_years"]),
        "num_change_orders": int(row["num_change_orders"]),
        "weather_risk_factor": float(row["weather_risk_factor"]),
        "material_volatility": float(row["material_volatility"]),
        "num_subcontractors": int(row["num_subcontractors"]),
        "budget_pressure": float(row["budget_pressure"]),
        "risk_score": float(row["risk_score"]),
        "risk_score_original": float(row["risk_score_original"]),
    }


def test_cost_estimation_api_train_predict_batch_health(
    client: TestClient, tmp_path: Path
) -> None:
    dataset = _build_dataset()
    dataset_path = tmp_path / "training.csv"
    model_path = tmp_path / "model.json"
    dataset.to_csv(dataset_path, index=False)

    train_resp = client.post(
        "/api/v1/cost-estimation/train",
        json={
            "dataset_path": str(dataset_path),
            "output_model_path": str(model_path),
            "ridge_alpha": 8.0,
            "folds": 4,
            "random_seed": 11,
        },
        headers={"X-Admin-Key": "integration-admin-key"},
    )
    assert train_resp.status_code == 200
    train_payload = train_resp.json()
    assert train_payload["success"] is True
    assert Path(train_payload["model_path"]).exists()

    health_resp = client.get("/api/v1/cost-estimation/health")
    assert health_resp.status_code == 200
    health_payload = health_resp.json()
    assert health_payload["model"]["loaded"] is True

    predict_resp = client.post(
        "/api/v1/cost-estimation/predict",
        json={
            "project": _sample_project_payload(dataset, idx=1),
            "confidence_quantile": 0.9,
        },
    )
    assert predict_resp.status_code == 200
    prediction = predict_resp.json()["prediction"]
    assert prediction["predicted_actual_cost_cad"] > 0
    assert (
        prediction["prediction_interval_cad"]["lower"]
        <= prediction["predicted_actual_cost_cad"]
    )
    assert (
        prediction["prediction_interval_cad"]["upper"]
        >= prediction["predicted_actual_cost_cad"]
    )

    batch_resp = client.post(
        "/api/v1/cost-estimation/predict/batch",
        json={
            "projects": [
                _sample_project_payload(dataset, idx=2),
                _sample_project_payload(dataset, idx=3),
            ],
            "confidence_quantile": 0.95,
        },
    )
    assert batch_resp.status_code == 200
    batch_payload = batch_resp.json()
    assert batch_payload["success"] is True
    assert batch_payload["count"] == 2


def test_cost_estimation_predict_requires_loaded_model(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/cost-estimation/predict",
        json={
            "project": {
                "project_type": "commercial_office",
                "location": "Toronto",
                "sqft": 120000,
                "floors": 12,
                "num_units": 0,
                "planned_duration_weeks": 540.0,
                "estimated_cost_cad": 120000000,
                "contractor_rating": 4.2,
                "complexity_score": 7,
                "team_experience_years": 12.0,
                "num_change_orders": 9,
                "weather_risk_factor": 0.45,
                "material_volatility": 0.6,
                "num_subcontractors": 20,
                "budget_pressure": 0.4,
                "risk_score": 52.0,
                "risk_score_original": 43.0,
            }
        },
    )
    assert resp.status_code == 400
    assert "Prediction request invalid" in resp.json()["detail"]


def test_cost_estimation_train_rejects_disallowed_path(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/cost-estimation/train",
        json={
            "dataset_path": "/etc/passwd",
        },
        headers={"X-Admin-Key": "integration-admin-key"},
    )
    assert resp.status_code == 400
    assert "project workspace" in resp.json()["detail"]


def test_cost_estimation_train_missing_dataset_does_not_leak_abs_path(
    client: TestClient, tmp_path: Path
) -> None:
    missing_path = tmp_path / "missing_training.csv"
    resp = client.post(
        "/api/v1/cost-estimation/train",
        json={
            "dataset_path": str(missing_path),
        },
        headers={"X-Admin-Key": "integration-admin-key"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "path does not exist"
