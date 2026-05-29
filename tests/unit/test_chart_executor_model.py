"""Unit tests for chart_executor.execute_model_comparison."""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from backend.services.data_analysis.chart_executor import (
    _build_model_snippet,
    _parse_model_marker,
    execute_model_comparison,
)


def _plan(
    *,
    enabled: bool = True,
    task: str = "classification",
    target: str = "quality",
    models: List[str] | None = None,
    reason: str = "ok",
) -> Dict[str, Any]:
    return {
        "model_comparison": {
            "enabled": enabled,
            "target_column": target,
            "task": task,
            "models": models or ["RandomForestClassifier", "LogisticRegression"],
            "reason": reason,
        }
    }


# --- disabled / skip paths --------------------------------------------


@pytest.mark.unit
class TestDisabledPaths:
    def test_returns_disabled_shape_when_plan_says_so(self):
        plan = _plan(enabled=False, reason="no target detected")
        result = execute_model_comparison(
            plan=plan,
            data_file_path="/tmp/data.csv",
            code_execution_manager=MagicMock(),
        )
        assert result["success"] is False
        assert result["enabled"] is False
        assert result["reason"] == "no target detected"
        assert result["metrics"] == {}
        assert result["image_filename"] is None

    def test_returns_error_when_manager_missing(self):
        plan = _plan(enabled=True)
        result = execute_model_comparison(
            plan=plan,
            data_file_path="/tmp/data.csv",
            code_execution_manager=None,
        )
        assert result["success"] is False
        assert result["enabled"] is True
        assert "manager" in result["reason"].lower() or "unavailable" in result["reason"].lower()


# --- marker parsing ---------------------------------------------------


@pytest.mark.unit
class TestMarkerParsing:
    def test_parses_ok_marker(self):
        stdout = 'noise\nMODEL_OK_JSON={"metrics": {"a": {"acc": 0.9}}, "image_filename": "model_comparison.png"}\nmore\n'
        marker = _parse_model_marker(stdout)
        assert marker is not None
        assert marker["status"] == "ok"
        assert marker["metrics"]["a"]["acc"] == 0.9

    def test_parses_failed_marker(self):
        stdout = 'MODEL_FAILED_JSON={"error": "target not found"}\n'
        marker = _parse_model_marker(stdout)
        assert marker["status"] == "failed"
        assert marker["error"] == "target not found"

    def test_last_marker_wins(self):
        stdout = (
            'MODEL_FAILED_JSON={"error": "e1"}\n'
            'MODEL_OK_JSON={"metrics": {}}\n'
        )
        marker = _parse_model_marker(stdout)
        assert marker["status"] == "ok"

    def test_returns_none_for_empty(self):
        assert _parse_model_marker("") is None
        assert _parse_model_marker(None) is None

    def test_ignores_malformed_json(self):
        # Regex matches but JSON is broken — skip cleanly.
        stdout = 'MODEL_OK_JSON={broken\n'
        assert _parse_model_marker(stdout) is None


# --- snippet assembly -------------------------------------------------


@pytest.mark.unit
class TestSnippetAssembly:
    def test_snippet_is_syntactically_valid_python(self):
        plan = _plan()
        snippet = _build_model_snippet(plan["model_comparison"], "/tmp/data.csv")
        # Compile — this fails on any syntax error, indent bug, etc.
        compile(snippet, "<snippet>", "exec")

    def test_snippet_references_target_column(self):
        plan = _plan(target="quality")
        snippet = _build_model_snippet(plan["model_comparison"], "/tmp/wine.csv")
        assert "'quality'" in snippet or '"quality"' in snippet

    def test_snippet_imports_sklearn(self):
        plan = _plan()
        snippet = _build_model_snippet(plan["model_comparison"], "/tmp/data.csv")
        assert "from sklearn.model_selection import train_test_split" in snippet
        assert "from sklearn.ensemble import" in snippet
        assert "from sklearn.linear_model import" in snippet

    def test_snippet_uses_sep_sniff_for_csv(self):
        # Same sniff treatment as EDA loader — see csv-separator hotfix.
        # The builder uses an explicit per-delimiter sniff loop (robust against
        # single-column CSVs that `sep=None` corrupts, PR #39) rather than the
        # python-engine sniffer.
        plan = _plan()
        snippet = _build_model_snippet(plan["model_comparison"], "/tmp/x.csv")
        assert "_try_sep" in snippet and "sep=_try_sep" in snippet

    def test_snippet_regression_uses_r2(self):
        plan = _plan(
            task="regression",
            models=["RandomForestRegressor", "Ridge"],
        )
        snippet = _build_model_snippet(plan["model_comparison"], "/tmp/x.csv")
        assert "r2_score" in snippet
        assert "mean_squared_error" in snippet

    def test_snippet_classification_uses_confusion_matrix(self):
        plan = _plan(task="classification")
        snippet = _build_model_snippet(plan["model_comparison"], "/tmp/x.csv")
        assert "confusion_matrix" in snippet


# --- end-to-end happy path with mocked sandbox ------------------------


@pytest.mark.unit
class TestMockedSandbox:
    def test_successful_run_returns_metrics_and_image(self):
        fake_image = b"\x89PNG\r\n\x1a\nfake"
        manager = MagicMock()
        manager.execute_code.return_value = {
            "success": True,
            "execution_time": 1.2,
            "stdout": (
                'MODEL_OK_JSON={"metrics": {'
                '"RandomForestClassifier": {"accuracy": 0.87}, '
                '"LogisticRegression": {"accuracy": 0.75}}, '
                '"image_filename": "model_comparison.png", '
                '"n_train": 400, "n_test": 100, "n_features": 11, '
                '"dropped_columns": [], "encoded_columns": []}'
            ),
            "stderr": "",
            "output_files": {"model_comparison.png": fake_image},
        }

        plan = _plan()
        result = execute_model_comparison(
            plan=plan,
            data_file_path="/tmp/wine.csv",
            code_execution_manager=manager,
        )
        assert result["success"] is True
        assert result["enabled"] is True
        assert result["image_filename"] == "model_comparison.png"
        assert result["metrics"]["RandomForestClassifier"]["accuracy"] == 0.87
        assert result["target_column"] == "quality"
        assert result["output_files"] == {"model_comparison.png": fake_image}

    def test_failed_marker_returns_failure(self):
        manager = MagicMock()
        manager.execute_code.return_value = {
            "success": True,
            "execution_time": 0.3,
            "stdout": 'MODEL_FAILED_JSON={"error": "target column not found"}',
            "stderr": "",
            "output_files": {},
        }
        plan = _plan()
        result = execute_model_comparison(
            plan=plan,
            data_file_path="/tmp/x.csv",
            code_execution_manager=manager,
        )
        assert result["success"] is False
        assert result["image_filename"] is None
        assert result["metrics"] == {}

    def test_sandbox_failure_returns_failure(self):
        manager = MagicMock()
        manager.execute_code.return_value = {
            "success": False,
            "execution_time": 12.5,
            "stdout": "",
            "stderr": "Sandbox timeout after 12s",
            "output_files": {},
        }
        plan = _plan()
        result = execute_model_comparison(
            plan=plan,
            data_file_path="/tmp/x.csv",
            code_execution_manager=manager,
        )
        assert result["success"] is False

    def test_image_missing_from_output_files_degrades_to_failure(self):
        # Marker claims ok, but the sandbox didn't return the image file —
        # defensive path so the frontend doesn't render <img src=""/>.
        manager = MagicMock()
        manager.execute_code.return_value = {
            "success": True,
            "execution_time": 1.0,
            "stdout": (
                'MODEL_OK_JSON={"metrics": {"a": {"r2": 0.5}}, '
                '"image_filename": "model_comparison.png"}'
            ),
            "stderr": "",
            "output_files": {},  # file claimed but not returned
        }
        plan = _plan()
        result = execute_model_comparison(
            plan=plan,
            data_file_path="/tmp/x.csv",
            code_execution_manager=manager,
        )
        assert result["success"] is False
        assert result["image_filename"] is None
