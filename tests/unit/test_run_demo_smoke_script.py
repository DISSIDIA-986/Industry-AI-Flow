from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.testing import run_demo_smoke


def _write_dataset(path: Path, *, rows: int = 12) -> None:
    base = {
        "project_type": "commercial_office",
        "location": "Toronto",
        "sqft": 120000.0,
        "floors": 12,
        "num_units": 1,
        "planned_duration_weeks": 80.0,
        "actual_duration_weeks": 84.0,
        "schedule_delay_pct": 5.0,
        "estimated_cost_cad": 50000000.0,
        "actual_cost_cad": 56000000.0,
        "cost_overrun_pct": 12.0,
        "contractor_rating": 4.2,
        "complexity_score": 7,
        "team_experience_years": 10.0,
        "num_change_orders": 4,
        "weather_risk_factor": 0.32,
        "material_volatility": 0.45,
        "num_subcontractors": 15,
        "budget_pressure": 0.55,
        "risk_score": 45.0,
        "risk_score_original": 40.0,
    }
    fieldnames = list(base.keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(rows):
            row = dict(base)
            row["sqft"] = base["sqft"] + (i * 2500.0)
            row["floors"] = int(base["floors"] + (i % 6))
            row["num_units"] = int(base["num_units"] + (i % 4))
            row["planned_duration_weeks"] = base["planned_duration_weeks"] + (i * 1.5)
            row["estimated_cost_cad"] = base["estimated_cost_cad"] + (i * 350000.0)
            row["cost_overrun_pct"] = base["cost_overrun_pct"] + (i % 5) - 2
            row["actual_cost_cad"] = row["estimated_cost_cad"] * (
                1.0 + (row["cost_overrun_pct"] / 100.0)
            )
            row["contractor_rating"] = max(2.5, min(5.0, base["contractor_rating"] - (i * 0.03)))
            row["complexity_score"] = int(max(1, min(10, base["complexity_score"] + (i % 3) - 1)))
            row["team_experience_years"] = base["team_experience_years"] + (i * 0.2)
            row["num_change_orders"] = int(base["num_change_orders"] + (i % 5))
            row["weather_risk_factor"] = min(0.95, base["weather_risk_factor"] + (i * 0.01))
            row["material_volatility"] = min(0.95, base["material_volatility"] + (i * 0.01))
            row["num_subcontractors"] = int(base["num_subcontractors"] + (i % 8))
            row["budget_pressure"] = min(0.95, base["budget_pressure"] + (i * 0.01))
            row["risk_score"] = base["risk_score"] + i
            row["risk_score_original"] = base["risk_score_original"] + (i * 0.8)
            writer.writerow(row)


def test_demo_smoke_script_passes_with_optional_checks_skipped(tmp_path: Path, capsys) -> None:
    dataset_path = tmp_path / "dataset.csv"
    model_path = tmp_path / "model.json"
    _write_dataset(dataset_path)
    model_path.write_text("{}", encoding="utf-8")

    code = run_demo_smoke.main(
        [
            "--dataset-path",
            str(dataset_path),
            "--model-path",
            str(model_path),
            "--allow-non313-python",
            "--skip-postgres-check",
            "--skip-ollama-check",
            "--skip-api-smoke",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["passed"] is True


def test_demo_smoke_script_fails_when_dataset_missing(tmp_path: Path, capsys) -> None:
    model_path = tmp_path / "model.json"
    model_path.write_text("{}", encoding="utf-8")

    code = run_demo_smoke.main(
        [
            "--dataset-path",
            str(tmp_path / "missing.csv"),
            "--model-path",
            str(model_path),
            "--allow-non313-python",
            "--skip-postgres-check",
            "--skip-ollama-check",
            "--skip-api-smoke",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["passed"] is False


def test_demo_smoke_script_fails_when_model_missing_without_train(tmp_path: Path, capsys) -> None:
    dataset_path = tmp_path / "dataset.csv"
    _write_dataset(dataset_path)

    code = run_demo_smoke.main(
        [
            "--dataset-path",
            str(dataset_path),
            "--model-path",
            str(tmp_path / "missing_model.json"),
            "--allow-non313-python",
            "--skip-postgres-check",
            "--skip-ollama-check",
            "--skip-api-smoke",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["required_failed"] >= 1


def test_demo_smoke_script_runs_api_smoke_with_trained_model(
    tmp_path: Path, capsys
) -> None:
    dataset_path = tmp_path / "dataset.csv"
    model_path = tmp_path / "trained_model.json"
    _write_dataset(dataset_path, rows=16)

    code = run_demo_smoke.main(
        [
            "--dataset-path",
            str(dataset_path),
            "--model-path",
            str(model_path),
            "--allow-non313-python",
            "--train-model-if-missing",
            "--skip-postgres-check",
            "--skip-ollama-check",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    api_check = next(item for item in payload["checks"] if item["name"] == "api_smoke")
    assert code == 0
    assert payload["passed"] is True
    assert api_check["passed"] is True
