from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.testing import run_demo_smoke


def _write_dataset(path: Path) -> None:
    row = {
        "project_type": "commercial_office",
        "location": "Toronto",
        "sqft": "120000",
        "floors": "12",
        "num_units": "1",
        "planned_duration_weeks": "80",
        "actual_duration_weeks": "84",
        "schedule_delay_pct": "5",
        "estimated_cost_cad": "50000000",
        "actual_cost_cad": "56000000",
        "cost_overrun_pct": "12",
        "contractor_rating": "4.2",
        "complexity_score": "7",
        "team_experience_years": "10",
        "num_change_orders": "4",
        "weather_risk_factor": "0.32",
        "material_volatility": "0.45",
        "num_subcontractors": "15",
        "budget_pressure": "0.55",
        "risk_score": "45",
        "risk_score_original": "40",
    }
    fieldnames = list(row.keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
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
