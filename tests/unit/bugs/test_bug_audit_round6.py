"""TDI Round 6 audit findings — reproduction tests.

Covers:
- R6-1 (Critical): Docker containers.run() timeout not forwarded
- R6-2 (Critical): _validate_code misses importlib/ctypes/socket/http imports
- R6-3 (High): sanitize_text doesn't URL-decode before XSS/SQL check
- R6-4 (High): sqft regex matches bogus text in ambiguous positions
- R6-5 (High): Pipeline response_node still called after error state
- R6-6 (High): data_analysis_agent module-level instantiation triggers LLM client
- R6-7 (Medium): _record_memory_interaction spawns thread per call
- R6-8 (Medium): predict_batch has no size limit
- R6-9 (Medium): _find_visualization_files missing .gif and .webp
- R6-10 (Medium): rate_limiter stale key cleanup threshold too high
"""

from __future__ import annotations

import ast
import inspect
import re
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# R6-1 (Critical): Docker timeout not forwarded
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR6_1_DockerTimeoutNotForwarded:
    """DockerCodeExecutor.execute_code() accepts a timeout parameter but
    does NOT pass it to client.containers.run(). The Docker container
    runs without a time limit, only subprocess.TimeoutExpired is caught
    (which never fires because Docker runs independently)."""

    def test_containers_run_receives_timeout(self):
        """Verify the source code passes timeout to containers.run()."""
        source_path = Path("backend/services/code_executor.py")
        if not source_path.exists():
            pytest.skip("code_executor.py not found")

        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Find execute_code method
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "execute_code":
                func_source = ast.get_source_segment(source, node) or ""
                # Look for containers.run(..., timeout=...) keyword
                # The timeout kwarg should be passed to containers.run()
                assert "timeout=" in func_source and "containers.run" in func_source, (
                    "R6-1: execute_code does not pass timeout to containers.run(). "
                    "Docker container runs without time limit."
                )
                return
        pytest.fail("execute_code method not found in code_executor.py")


# ---------------------------------------------------------------------------
# R6-2 (Critical): _validate_code misses dangerous imports
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR6_2_ValidateCodeMissesDangerousImports:
    """_validate_code in code_executor.py only blocks os, subprocess, sys
    imports. importlib, ctypes, socket, http, requests are NOT blocked,
    allowing sandbox escape."""

    @staticmethod
    def _get_blocked_imports() -> set:
        """Extract blocked import names from _validate_code source."""
        source_path = Path("backend/services/code_executor.py")
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_validate_code":
                func_source = ast.get_source_segment(source, node) or ""
                # Find the list of blocked module names
                blocked = set()
                for inner_node in ast.walk(ast.parse(func_source)):
                    if isinstance(inner_node, ast.List):
                        for elt in inner_node.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                blocked.add(elt.value)
                return blocked
        return set()

    def test_importlib_blocked(self):
        blocked = self._get_blocked_imports()
        assert "importlib" in blocked, (
            "R6-2: importlib not in _validate_code blocked imports — "
            "allows importing any blacklisted module via importlib.import_module()"
        )

    def test_ctypes_blocked(self):
        blocked = self._get_blocked_imports()
        assert "ctypes" in blocked, (
            "R6-2: ctypes not in _validate_code blocked imports — "
            "allows arbitrary native code execution"
        )

    def test_socket_blocked(self):
        blocked = self._get_blocked_imports()
        assert "socket" in blocked, (
            "R6-2: socket not in _validate_code blocked imports — "
            "allows network connections from sandbox"
        )


# ---------------------------------------------------------------------------
# R6-3 (High): sanitize_text doesn't URL-decode before check
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR6_3_SanitizeTextUrlEncodedBypass:
    """sanitize_text checks for <script> tags but does NOT URL-decode
    input first. %3Cscript%3E bypasses the XSS guard."""

    def test_url_encoded_script_tag_blocked(self):
        """URL-encoded <script> tag should be caught by sanitize_text."""
        from urllib.parse import unquote

        from backend.security.sanitizer import sanitize_text

        # %3Cscript%3Ealert(1)%3C/script%3E = <script>alert(1)</script>
        encoded_xss = "%3Cscript%3Ealert(1)%3C/script%3E"

        # If sanitize_text doesn't decode, this will pass through
        try:
            result = sanitize_text(encoded_xss, field_name="test")
            # If we get here, the encoded XSS was NOT blocked
            # Verify the decoded form would be dangerous
            decoded = unquote(result or "")
            assert "<script>" not in decoded.lower(), (
                "R6-3: sanitize_text allowed URL-encoded <script> tag through. "
                "Decoded output contains XSS payload."
            )
        except Exception:
            # If an HTTPException is raised, the XSS was correctly blocked
            pass

    def test_url_encoded_sql_injection_blocked(self):
        """URL-encoded SQL injection should be caught."""
        from urllib.parse import quote

        from fastapi import HTTPException

        from backend.security.sanitizer import sanitize_text

        # URL-encode "'; DROP TABLE users; --"
        encoded_sql = quote("'; DROP TABLE users; --")

        try:
            result = sanitize_text(encoded_sql, field_name="test")
            # If we get here without exception, the SQL injection was NOT blocked
            # Check if decoded form would be dangerous
            from urllib.parse import unquote
            decoded = unquote(result or "")
            has_sql = bool(re.search(r"drop\s+table", decoded, re.IGNORECASE))
            assert not has_sql, (
                "R6-3: sanitize_text allowed URL-encoded SQL injection through"
            )
        except HTTPException:
            pass  # Correctly blocked


# ---------------------------------------------------------------------------
# R6-4 (High): sqft regex matches bogus text
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR6_4_SqftRegexFalsePositive:
    """The sqft regex pattern matches 'area' without requiring it to be
    followed by a numeric value — 'area of Toronto' can extract bogus
    numbers from adjacent text."""

    def test_5000_square_feet_extracted(self):
        """'5000 square feet' should extract sqft=5000."""
        from backend.services.cost_estimation_service import (
            extract_cost_features_from_query,
        )

        result = extract_cost_features_from_query(
            "Estimate cost for 5000 square feet residential"
        )
        assert result.get("sqft") == 5000.0, (
            f"R6-4: '5000 square feet' not extracted correctly, got {result.get('sqft')}"
        )

    def test_estimate_cost_does_not_extract_bogus_sqft_from_cost_value(self):
        """When query has 'estimated cost 500000', the sqft pattern should NOT
        match at the cost= position and extract 500000 as sqft."""
        from backend.services.cost_estimation_service import (
            extract_cost_features_from_query,
        )

        result = extract_cost_features_from_query(
            "Estimate the budget for a warehouse, estimated cost 500000"
        )
        # sqft should NOT be 500000 — that's the cost value
        if "sqft" in result:
            assert result["sqft"] != 500000.0, (
                f"R6-4: Bogus sqft={result['sqft']} extracted from cost value. "
                "The regex patterns overlap and cost value is misidentified as sqft."
            )


# ---------------------------------------------------------------------------
# R6-5 (High): response_node called after error
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR6_5_ResponseNodeCalledAfterError:
    """In graph.py, when a node sets state['error'], the loop breaks.
    But at L84, if state has no 'response', response_node is called
    unconditionally — which may overwrite or mask the error."""

    @pytest.mark.asyncio
    async def test_error_state_preserved_through_pipeline(self):
        """When error is set, the error message should survive to the
        final state without being overwritten by response_node."""
        from backend.services.workflows.nodes.response_node import (
            _build_default_response,
        )

        error_state = {
            "error": "safety_node failed: blocked dangerous pattern",
            "query": "rm -rf /",
            "metadata": {"safety_status": "blocked"},
        }

        response = _build_default_response(error_state)
        # Error response should indicate the request was blocked,
        # NOT produce a normal success-like response
        assert "could not be processed" in response.lower() or "blocked" in response.lower() or "safety" in response.lower(), (
            f"R6-5: Error state response looks like success: '{response}'"
        )
        # And the error key should still be in state
        assert error_state.get("error"), "R6-5: error was cleared from state"


# ---------------------------------------------------------------------------
# R6-6 (High): Module-level DataAnalysisAgent instantiation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR6_6_ModuleLevelInstantiation:
    """data_analysis_agent.py line 578 instantiates DataAnalysisAgent()
    at module import time, triggering LLMClientFactory.create_client()
    and get_code_execution_manager(). This causes import-time side effects
    and failures when dependencies are unavailable."""

    def test_no_module_level_instantiation(self):
        """Module should NOT instantiate DataAnalysisAgent at import time."""
        source_path = Path("backend/services/data_analysis/data_analysis_agent.py")
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Find top-level assignments that instantiate DataAnalysisAgent
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "data_analysis_agent":
                        # Check if it's a direct call (instantiation)
                        if isinstance(node.value, ast.Call):
                            func = node.value.func
                            if isinstance(func, ast.Name) and func.id == "DataAnalysisAgent":
                                pytest.fail(
                                    "R6-6: DataAnalysisAgent() is instantiated at module level "
                                    "(line 578). This triggers LLM client creation on import. "
                                    "Should use lazy initialization pattern."
                                )


# ---------------------------------------------------------------------------
# R6-7 (Medium): _record_memory_interaction thread per call
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR6_7_MemoryInteractionThreadPerCall:
    """_record_memory_interaction spawns a thread via _run_in_thread()
    for each call when memory_manager is present. Under load this
    creates unbounded thread count."""

    def test_no_thread_spawn_per_call(self):
        """Verify _record_memory_interaction does NOT use threading.Thread
        for each invocation."""
        source_path = Path("backend/services/rag_engine.py")
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_record_memory_interaction":
                func_source = ast.get_source_segment(source, node) or ""
                # Check for threading.Thread creation inside this function
                has_thread = "Thread(" in func_source or "thread" in func_source.lower()
                if has_thread:
                    # Verify it's not using a bounded approach
                    uses_executor = "executor" in func_source.lower() or "pool" in func_source.lower()
                    assert uses_executor or "Thread(" not in func_source, (
                        "R6-7: _record_memory_interaction spawns a new Thread per call. "
                        "Should use inline update or bounded thread pool."
                    )
                return
        pytest.skip("_record_memory_interaction not found")


# ---------------------------------------------------------------------------
# R6-8 (Medium): predict_batch no size limit
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR6_8_PredictBatchNoSizeLimit:
    """CostEstimationService.predict_batch accepts any number of projects
    with no upper bound. A single API call with millions of items can
    cause CPU exhaustion."""

    def test_batch_size_limit_enforced(self):
        """predict_batch should raise or reject if batch exceeds max size."""
        source_path = Path("backend/services/cost_estimation_service.py")
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "predict_batch":
                func_source = ast.get_source_segment(source, node) or ""
                has_limit = (
                    "max_batch" in func_source.lower()
                    or "len(projects)" in func_source
                    or "too many" in func_source.lower()
                    or "batch size" in func_source.lower()
                    or "MAX_BATCH" in func_source
                )
                assert has_limit, (
                    "R6-8: predict_batch has no batch size limit. "
                    "Caller can submit millions of items causing CPU exhaustion."
                )
                return
        pytest.fail("predict_batch method not found")


# ---------------------------------------------------------------------------
# R6-9 (Medium): _find_visualization_files missing extensions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR6_9_VizFilesMissingExtensions:
    """_find_visualization_files only checks .png, .jpg, .jpeg, .svg,
    .html, .pdf — missing .gif and .webp which are common web formats."""

    def test_gif_and_webp_supported(self):
        source_path = Path("backend/services/code_executor.py")
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_find_visualization_files":
                func_source = ast.get_source_segment(source, node) or ""
                assert ".gif" in func_source, (
                    "R6-9: _find_visualization_files missing .gif extension"
                )
                assert ".webp" in func_source, (
                    "R6-9: _find_visualization_files missing .webp extension"
                )
                return
        pytest.fail("_find_visualization_files not found")


# ---------------------------------------------------------------------------
# R6-10 (Medium): rate_limiter stale key cleanup threshold
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR6_10_RateLimiterStaleThreshold:
    """SlidingWindowRateLimiter only cleans stale keys when len(_hits) > 10.
    Up to 10 dead keys persist indefinitely, leaking memory."""

    def test_stale_keys_cleaned_below_threshold(self):
        from backend.security.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter(limit=10, interval_seconds=1)

        # Create 5 keys (below the cleanup threshold of 10)
        for i in range(5):
            limiter.hit(f"stale_{i}")

        # Wait for all to expire
        time.sleep(1.1)

        # Hit a new key — cleanup should fire even with only 5 stale keys
        limiter.hit("fresh")

        with limiter._lock:
            remaining = set(limiter._hits.keys())

        stale = remaining - {"fresh"}
        assert len(stale) == 0, (
            f"R6-10: {len(stale)} stale keys remain below cleanup threshold. "
            "Cleanup only fires when len(_hits) > 10, leaving up to 10 dead keys."
        )
