"""Shared fixtures for TDI bug reproduction tests."""

from __future__ import annotations

import pytest


@pytest.fixture()
def sample_construction_project() -> dict:
    """A realistic construction project feature dict for cost estimation."""
    return {
        "project_type": "residential_single_family",
        "location": "Toronto",
        "sqft": 2500.0,
        "floors": 2,
        "num_units": 1,
        "planned_duration_weeks": 24.0,
        "estimated_cost_cad": 450_000.0,
        "contractor_rating": 3.8,
        "complexity_score": 5,
        "team_experience_years": 10.0,
        "num_change_orders": 3,
        "weather_risk_factor": 1.2,
        "material_volatility": 0.8,
        "num_subcontractors": 6,
        "budget_pressure": 0.5,
        "risk_score": 4.0,
        "risk_score_original": 3.5,
    }


@pytest.fixture()
def unseen_category_project(sample_construction_project) -> dict:
    """A project with a category value NOT present in training data."""
    project = dict(sample_construction_project)
    project["project_type"] = "data_center"       # Not in _PROJECT_TYPE_KEYWORDS
    project["location"] = "Yellowknife"            # Not in _LOCATION_KEYWORDS
    return project


@pytest.fixture()
def sample_safe_analysis_code() -> str:
    """Safe Python code for data analysis that should pass validation."""
    return (
        "import pandas as pd\n"
        "import numpy as np\n"
        "\n"
        "df = pd.read_csv('data.csv')\n"
        "print(df.describe())\n"
        "print(f'Row count: {len(df)}')\n"
    )


@pytest.fixture()
def sample_code_with_dunder() -> str:
    """Valid Python code using __name__ dunder — should be allowed."""
    return (
        "import pandas as pd\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    df = pd.read_csv('data.csv')\n"
        "    print(df.shape)\n"
    )
