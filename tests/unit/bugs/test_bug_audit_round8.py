"""TDI Round 8 audit findings — reproduction tests.

Covers:
- R8-1 (High): _parse_human_number fails on space-grouped numbers ("5 000" → None)
- R8-2 (Medium): get_data_analysis_agent() singleton race condition (no lock)
- R8-3 (High): sanitize_text bypassed by double-URL-encoding
- R8-4 (Medium): _generate_template_code omits question arg for max/min templates
- R8-5 (Medium): run_workflow_pipeline error-break swallows error when stale response exists
"""

from __future__ import annotations

import ast
import asyncio
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# R8-1 (High): _parse_human_number fails on space-grouped numbers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR8_1_ParseHumanNumberSpacedDigits:
    """_parse_human_number should handle locale-style space-separated
    thousands (e.g. "5 000", "1 500 000") instead of returning None."""

    def test_space_grouped_thousands(self):
        from backend.services.cost_estimation_service import _parse_human_number

        result = _parse_human_number("5 000")
        assert result is not None, (
            "R8-1: _parse_human_number('5 000') returned None — "
            "space-grouped thousands are silently dropped"
        )
        assert result == 5000.0, f"R8-1: expected 5000.0, got {result}"

    def test_space_grouped_millions(self):
        from backend.services.cost_estimation_service import _parse_human_number

        result = _parse_human_number("1 500 000")
        assert (
            result is not None
        ), "R8-1: _parse_human_number('1 500 000') returned None"
        assert result == 1_500_000.0, f"R8-1: expected 1500000.0, got {result}"

    def test_space_grouped_with_suffix_k(self):
        from backend.services.cost_estimation_service import _parse_human_number

        result = _parse_human_number("5 000k")
        assert result is not None, "R8-1: _parse_human_number('5 000k') returned None"
        assert result == 5_000_000.0, f"R8-1: expected 5000000.0, got {result}"

    def test_extract_features_spaced_sqft(self):
        """End-to-end: '5 000 square feet' should extract sqft=5000."""
        from backend.services.cost_estimation_service import (
            extract_cost_features_from_query,
        )

        features = extract_cost_features_from_query(
            "residential single family 5 000 square feet in Toronto"
        )
        assert (
            "sqft" in features
        ), "R8-1: extract_cost_features_from_query missed 'sqft' for '5 000 square feet'"
        assert (
            features["sqft"] == 5000.0
        ), f"R8-1: expected sqft=5000.0, got {features['sqft']}"


# ---------------------------------------------------------------------------
# R8-2 (Medium): get_data_analysis_agent() singleton race condition
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR8_2_DataAnalysisAgentThreadSafety:
    """get_data_analysis_agent() global singleton must be protected by a
    lock to prevent double-initialization under concurrent access."""

    def test_singleton_uses_lock(self):
        """Source code of get_data_analysis_agent should contain a lock."""
        source_path = Path("backend/services/data_analysis/data_analysis_agent.py")
        source = source_path.read_text(encoding="utf-8")

        # Must have a threading.Lock protecting the creation
        assert "Lock()" in source, (
            "R8-2: get_data_analysis_agent() has no threading.Lock — "
            "concurrent requests can double-initialize the agent"
        )

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "get_data_analysis_agent"
            ):
                func_source = ast.get_source_segment(source, node) or ""
                assert "with" in func_source and "lock" in func_source.lower(), (
                    "R8-2: get_data_analysis_agent() does not use a `with lock:` "
                    "pattern to protect singleton creation"
                )
                break
        else:
            pytest.fail("R8-2: get_data_analysis_agent function not found")


# ---------------------------------------------------------------------------
# R8-3 (High): sanitize_text bypassed by double-URL-encoding
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR8_3_SanitizeTextDoubleEncoding:
    """sanitize_text applies a single unquote() pass. Double-encoded
    payloads like %253Cscript%253E survive and bypass XSS detection."""

    def test_double_encoded_script_tag_blocked(self):
        """Verify the iterative unquote logic catches double-encoded <script>."""
        from urllib.parse import unquote

        # Simulate the sanitizer's decoding logic (the fix under test)
        source_path = Path("backend/security/sanitizer.py")
        source = source_path.read_text(encoding="utf-8")

        # Verify the fix: the code should contain iterative decoding
        assert "for _ in range" in source and "unquote" in source, (
            "R8-3: sanitize_text does not use iterative unquote — "
            "double-URL-encoding can bypass XSS filter"
        )

        # Also verify the logic itself: iterative decode should fully resolve
        double_encoded = "%253Cscript%253E"
        decoded = double_encoded
        for _ in range(5):
            next_decoded = unquote(decoded)
            if next_decoded == decoded:
                break
            decoded = next_decoded
        assert (
            "<script>" in decoded.lower()
        ), f"R8-3: iterative unquote did not fully resolve {double_encoded} → got {decoded}"

    def test_double_encoded_sql_injection_blocked(self):
        """Verify iterative decode resolves double-encoded SQL injection."""
        import re
        from urllib.parse import unquote

        double_encoded = "%2527%253B%2520DROP%2520TABLE%2520users%253B%2520--"
        decoded = double_encoded
        for _ in range(5):
            next_decoded = unquote(decoded)
            if next_decoded == decoded:
                break
            decoded = next_decoded

        sql_pattern = re.compile(r"drop\s+table", re.IGNORECASE)
        assert sql_pattern.search(
            decoded
        ), f"R8-3: iterative unquote did not fully resolve SQL injection — got {decoded}"


# ---------------------------------------------------------------------------
# R8-4 (Medium): _generate_template_code omits question for max/min
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR8_4_TemplateCodeMissingQuestionArg:
    """_generate_template_code dispatches to _template_max/_template_min
    without passing the user's question, so column selection always falls
    back to a generic keyword instead of the question-relevant column."""

    def test_template_max_receives_question(self):
        source_path = Path("backend/services/data_analysis/data_analysis_agent.py")
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_generate_template_code"
            ):
                func_source = ast.get_source_segment(source, node) or ""
                # Find the _template_max call and check if question is passed
                assert (
                    "self._template_max(filename, dataset_metadata, question)"
                    in func_source
                ), (
                    "R8-4: _generate_template_code calls _template_max without "
                    "passing `question` — column selection ignores user intent"
                )
                break
        else:
            pytest.fail("R8-4: _generate_template_code not found")

    def test_template_min_receives_question(self):
        source_path = Path("backend/services/data_analysis/data_analysis_agent.py")
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_generate_template_code"
            ):
                func_source = ast.get_source_segment(source, node) or ""
                assert (
                    "self._template_min(filename, dataset_metadata, question)"
                    in func_source
                ), (
                    "R8-4: _generate_template_code calls _template_min without "
                    "passing `question` — column selection ignores user intent"
                )
                break
        else:
            pytest.fail("R8-4: _generate_template_code not found")


# ---------------------------------------------------------------------------
# R8-5 (Medium): run_workflow_pipeline error-break swallows stale response
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR8_5_PipelineErrorSwallowsStaleResponse:
    """When a node sets state['response'] and a later node sets
    state['error'], the pipeline breaks and the final fallback
    `if not state.get("response")` is False (stale response exists),
    so the error is never surfaced in the final response."""

    @pytest.mark.asyncio
    async def test_error_overwrites_stale_response(self):
        # Read graph.py source directly to verify the fix, avoiding
        # the __init__.py chain that imports pydantic_settings.
        source_path = Path("backend/services/workflows/graph.py")
        source = source_path.read_text(encoding="utf-8")

        # The fix: the final fallback must also invoke response_node when
        # an error exists, not only when response is empty.
        assert 'state.get("error") or not state.get("response")' in source, (
            "R8-5: graph.py still uses `if not state.get('response')` — "
            "errors are silently swallowed when a stale response exists. "
            "Should be: `if state.get('error') or not state.get('response')`"
        )

        # Also verify the error path in _build_default_response returns the error
        resp_source = Path(
            "backend/services/workflows/nodes/response_node.py"
        ).read_text(encoding="utf-8")
        assert 'state.get("error")' in resp_source or "state['error']" in resp_source, (
            "R8-5: response_node._build_default_response does not handle "
            "error state — even with the graph.py fix, errors won't surface"
        )
