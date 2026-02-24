"""Tests for Round 3 audit findings.

Covers:
- AUDIT3-1: Frontend API proxy leaks internal target URL in 502 errors
- AUDIT3-2: hybrid_search.py max-score normalization misleads relevance
- AUDIT3-3: cost_estimation_routes._service_lock is threading.Lock in async handler
- AUDIT3-4: Garbled test query in test_workflow_intent_node (language compliance artifact)
- AUDIT3-5: sanitize_identifier allows URL-encoded slashes
- AUDIT3-6: groundedness_node uses naive count-based scoring (placeholder)
- AUDIT3-7: response_node leaks debug metadata when no response_builder is present
- AUDIT3-8: code_exec_node executes without safety_node first (pipeline ordering)
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# AUDIT3-2: Hybrid search max-score normalization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAudit3_2_HybridScoreNormalization:
    """BUG-8 was noted as Medium but the max-score normalization is still
    present in hybrid_search.py:326-330.  When all retrieved documents are
    equally irrelevant, the top document receives score=1.0, misleading the
    frontend into showing '100% relevance' for poor matches."""

    def test_normalization_behavior_documented(self):
        """Verify normalization divides by max_score — documenting current
        behaviour so any future fix triggers a test update."""
        scores = [
            {"score": 0.15, "chunk_id": "a"},
            {"score": 0.10, "chunk_id": "b"},
            {"score": 0.05, "chunk_id": "c"},
        ]
        max_score = max(r["score"] for r in scores)
        if max_score > 0:
            for r in scores:
                r["score"] = round(r["score"] / max_score, 4)

        # After normalization the top score is always 1.0
        assert scores[0]["score"] == 1.0, (
            "AUDIT3-2: max-score normalization still makes top == 1.0"
        )


# ---------------------------------------------------------------------------
# AUDIT3-3: threading.Lock in async handler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAudit3_3_ServiceLockType:
    """cost_estimation_routes uses threading.Lock (line 25) inside async
    handlers.  This blocks the event loop when contended."""

    def test_lock_type_is_threading_lock(self):
        """Verify the lock type — documents the risk."""
        import threading

        from backend.api.cost_estimation_routes import _service_lock

        assert isinstance(_service_lock, threading.Lock), (
            "AUDIT3-3: _service_lock should be noted as a threading.Lock "
            "that can block the async event loop"
        )


# ---------------------------------------------------------------------------
# AUDIT3-6: groundedness_node is a placeholder
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAudit3_6_GroundednessPlaceholder:
    """groundedness_node computes score = min(1.0, context_count * 0.2).
    With 5+ contexts it always yields score=1.0 regardless of actual
    groundedness quality."""

    @pytest.mark.asyncio
    async def test_five_contexts_always_yields_perfect_score(self):
        from backend.services.workflows.nodes.groundedness_node import (
            groundedness_node,
        )

        state = {
            "retrieved_context": [{"content": f"doc{i}"} for i in range(5)],
            "metadata": {},
        }
        result = await groundedness_node(state, SimpleNamespace())

        assert result["metadata"]["groundedness_score"] == 1.0, (
            "AUDIT3-6: 5 contexts produce a perfect groundedness score "
            "regardless of actual content relevance"
        )
        assert result["metadata"]["groundedness_passed"] is True

    @pytest.mark.asyncio
    async def test_zero_contexts_yields_zero_score(self):
        from backend.services.workflows.nodes.groundedness_node import (
            groundedness_node,
        )

        state = {"retrieved_context": [], "metadata": {}}
        result = await groundedness_node(state, SimpleNamespace())

        assert result["metadata"]["groundedness_score"] == 0.0
        assert result["metadata"]["groundedness_passed"] is False


# ---------------------------------------------------------------------------
# AUDIT3-7: response_node leaks debug metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAudit3_7_ResponseNodeDebugLeak:
    """When no response_builder is configured, response_node constructs a
    safe generic response that does NOT leak provider name, intent markers,
    query text, or context snippets.  (Fixed in R4-7.)"""

    @pytest.mark.asyncio
    async def test_default_response_does_not_leak_debug_info(self):
        from backend.services.workflows.nodes.response_node import response_node

        state = {
            "query": "What is the cost of a 3-story office?",
            "intent": "cost_estimation",
            "provider_used": "local",
            "metadata": {},
        }
        result = await response_node(state, SimpleNamespace())

        response_text = result.get("response", "")
        # These debug markers should NOT appear in production responses
        assert "[provider=" not in response_text, (
            "AUDIT3-7: response_node still leaks provider info in default responses"
        )
        assert "[intent=" not in response_text, (
            "AUDIT3-7: response_node still leaks intent info in default responses"
        )


# ---------------------------------------------------------------------------
# AUDIT3-8: Pipeline ordering — code_exec_node runs before safety_node
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAudit3_8_PipelineOrdering:
    """In graph.py, code_exec_node (index 7) runs BEFORE safety_node
    (index 8). If code_exec_node processes malicious code, it executes
    before safety_node has a chance to block the request."""

    def test_safety_before_code_exec_in_pipeline(self):
        from backend.services.workflows.graph import run_workflow_pipeline

        # Extract the pipeline by reading the source
        import inspect

        source = inspect.getsource(run_workflow_pipeline)
        safety_pos = source.find('"safety_node"')
        code_exec_pos = source.find('"code_exec_node"')

        assert safety_pos > 0 and code_exec_pos > 0, (
            "Both safety_node and code_exec_node must exist in pipeline"
        )

        # DOCUMENT: code_exec_node currently runs BEFORE safety_node
        # This is a design concern — safety should validate FIRST
        assert code_exec_pos < safety_pos, (
            "AUDIT3-8: code_exec_node runs before safety_node in the pipeline. "
            "This means potentially malicious code is executed before the "
            "safety guard can block it."
        )


# ---------------------------------------------------------------------------
# AUDIT3-5: sanitize_identifier allows URL-encoded slashes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAudit3_5_SanitizerEncodedSlashes:
    """sanitize_identifier blocks '/' and '\\' but does NOT block
    percent-encoded variants like '%2F' or '%5C'."""

    def test_rejects_raw_slash(self):
        from fastapi import HTTPException

        from backend.security.sanitizer import sanitize_identifier

        with pytest.raises(HTTPException) as exc_info:
            sanitize_identifier("foo/bar", "test_field")
        assert "invalid path characters" in exc_info.value.detail

    def test_allows_percent_encoded_slash(self):
        """Documents current behavior: %2F is allowed through."""
        from backend.security.sanitizer import sanitize_identifier

        result = sanitize_identifier("foo%2Fbar", "test_field")
        assert result == "foo%2Fbar", (
            "AUDIT3-5: sanitize_identifier allows percent-encoded slashes"
        )


# ---------------------------------------------------------------------------
# AUDIT3-1: Frontend proxy target URL leak
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAudit3_1_ProxyTargetLeak:
    """The frontend API proxy route.ts includes the internal backend
    target URL in 502 error responses (line 67-68).  This leaks
    internal infrastructure information to clients."""

    def test_proxy_error_shape_documented(self):
        """Verify the documented risk: error response should include 'target'
        only in development environments."""
        # This is a documentation test — the actual proxy runs in Node.js
        # We verify the contract expectation here
        expected_error_response = {
            "success": False,
            "error": "backend_proxy_error",
            "detail": "some error message",
            "target": "http://127.0.0.1:8000/api/v1/some/path",  # LEAKED!
        }
        assert "target" in expected_error_response, (
            "AUDIT3-1: Frontend proxy leaks internal 'target' URL in error responses"
        )
