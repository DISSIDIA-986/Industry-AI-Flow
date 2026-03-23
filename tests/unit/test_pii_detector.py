"""Unit tests for PII column name detector and prompt payload privacy."""

import pytest

from backend.services.data_analysis.pii_detector import detect_pii_columns


class TestDetectPiiColumns:
    """Tests for detect_pii_columns()."""

    def test_detects_ssn(self):
        assert detect_pii_columns(["id", "ssn", "value"]) == ["ssn"]

    def test_detects_email(self):
        assert detect_pii_columns(["name", "email", "age"]) == ["email"]

    def test_detects_phone(self):
        assert detect_pii_columns(["phone_number"]) == ["phone_number"]

    def test_detects_credit_card(self):
        assert detect_pii_columns(["credit_card", "amount"]) == ["credit_card"]

    def test_detects_passport(self):
        assert detect_pii_columns(["passport_id"]) == ["passport_id"]

    def test_detects_driver_license(self):
        assert detect_pii_columns(["driver_license"]) == ["driver_license"]
        assert detect_pii_columns(["drivers_licence"]) == ["drivers_licence"]

    def test_detects_dob(self):
        assert detect_pii_columns(["dob"]) == ["dob"]
        assert detect_pii_columns(["date_of_birth"]) == ["date_of_birth"]

    def test_detects_address(self):
        assert detect_pii_columns(["home_address"]) == ["home_address"]

    def test_detects_salary_income(self):
        result = detect_pii_columns(["salary", "income", "wage"])
        assert result == ["salary", "income", "wage"]

    def test_detects_patient_id(self):
        assert detect_pii_columns(["patient_id"]) == ["patient_id"]

    def test_detects_sin_canada(self):
        assert detect_pii_columns(["sin"]) == ["sin"]

    def test_case_insensitive(self):
        assert detect_pii_columns(["SSN", "Email", "PHONE"]) == ["SSN", "Email", "PHONE"]

    def test_no_false_positives_on_safe_columns(self):
        safe_cols = [
            "id", "name", "age", "project_type", "sqft", "floors",
            "location", "contractor_rating", "risk_score", "total_bill",
            "tip", "sex", "day", "time", "size",
        ]
        assert detect_pii_columns(safe_cols) == []

    def test_empty_list(self):
        assert detect_pii_columns([]) == []

    def test_multiple_pii_columns(self):
        cols = ["name", "ssn", "email", "age", "phone"]
        result = detect_pii_columns(cols)
        assert result == ["ssn", "email", "phone"]


class TestPromptPayloadExclusion:
    """Regression tests: assert LLM prompt never includes raw data values.

    The prompt built by _build_code_generation_prompt() must only contain
    column names and types — never top_values, sample_rows, or raw data.
    This prevents future regressions from accidentally leaking data to cloud LLMs.
    """

    def test_prompt_excludes_top_values(self):
        """The LLM prompt must not contain raw categorical values."""
        from backend.services.data_analysis.data_analysis_agent import (
            DataAnalysisAgent,
        )

        agent = DataAnalysisAgent.__new__(DataAnalysisAgent)

        metadata = {
            "filename": "test.csv",
            "rows": 100,
            "columns": 3,
            "column_names": ["sex", "age", "score"],
            "columns_info": [
                {
                    "name": "sex",
                    "type": "object",
                    "unique_values": 2,
                    "top_values": {"Male": 60, "Female": 40},
                },
                {"name": "age", "type": "int64", "mean": 30.0},
                {"name": "score", "type": "float64", "mean": 85.5},
            ],
        }

        prompt = agent._build_code_generation_prompt(
            question="What is the average score?",
            data_file_path="/workspace/test.csv",
            dataset_metadata=metadata,
        )

        # Raw categorical values must NOT appear in prompt
        assert "Male" not in prompt
        assert "Female" not in prompt
        assert "top_values" not in prompt

        # Column names and types SHOULD appear
        assert "sex" in prompt
        assert "age" in prompt
        assert "score" in prompt
        assert "object" in prompt
        assert "int64" in prompt

    def test_prompt_excludes_sample_rows(self):
        """The LLM prompt must not contain sample_rows data."""
        from backend.services.data_analysis.data_analysis_agent import (
            DataAnalysisAgent,
        )

        agent = DataAnalysisAgent.__new__(DataAnalysisAgent)

        metadata = {
            "filename": "test.csv",
            "rows": 5,
            "columns": 2,
            "column_names": ["name", "value"],
            "columns_info": [
                {"name": "name", "type": "object"},
                {"name": "value", "type": "int64"},
            ],
            "sample_rows": [
                {"name": "Alice", "value": 100},
                {"name": "Bob", "value": 200},
            ],
        }

        prompt = agent._build_code_generation_prompt(
            question="Show statistics",
            data_file_path="/workspace/test.csv",
            dataset_metadata=metadata,
        )

        # Raw row data must NOT appear in prompt
        assert "Alice" not in prompt
        assert "Bob" not in prompt
        assert "sample_rows" not in prompt
