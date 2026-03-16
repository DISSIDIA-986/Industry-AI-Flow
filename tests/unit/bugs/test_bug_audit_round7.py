"""TDI Round 7 audit findings — reproduction tests.

Covers:
- R7-1 (High): graph.py skips response_node upon error state, leaving response empty
- R7-2 (High): cost_estimation_routes.py uses synchronous blocking code in async handlers
- R7-3 (Medium): reranker.py returns raw logits instead of normalized sigmoid [0, 1] scores
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# R7-1 (High): graph.py skips response_node on error
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR7_1_GraphSkipsResponseNodeOnError:
    """graph.py has a condition:
    if not state.get("response") and not state.get("error"):
        state = await response_node(state, services)
    This incorrectly skips response_node when an error occurs, causing the API
    to return a null/empty response instead of the error message.
    """

    @pytest.mark.asyncio
    async def test_pipeline_formats_response_on_error(self):
        """Pipeline should still populate state['response'] even if an error occurred."""
        from backend.services.workflows.graph import run_workflow_pipeline
        from backend.services.workflows.state import WorkflowState

        # Mock the pipeline so safety_node triggers an error
        state = WorkflowState(
            query="dangerous query",
            intent="unknown",
            route_mode="local_only",
            history=[],
            response="",
            metadata={},
        )

        # We need a fake services object
        class FakeServices:
            pass

        # We will mock safety_node to inject an error
        with patch("backend.services.workflows.graph.safety_node") as mock_safety:

            async def _fake_safety(st, svcs):
                st["error"] = "Blocked by safety policy"
                return st

            mock_safety.side_effect = _fake_safety

            # Run the pipeline
            # The pipeline should break at safety_node due to error,
            # and then SHOULD call response_node to format the error message.
            final_state = await run_workflow_pipeline(state, FakeServices())

            # The response should not be empty. It should be the default error response.
            assert final_state.get("response"), (
                "R7-1: state['response'] is empty. graph.py incorrectly "
                "skipped response_node after an error occurred."
            )
            # Response should be a user-friendly message, NOT the raw internal error
            response = final_state.get("response", "")
            assert (
                "Blocked by safety policy" not in response
            ), "Response should not leak raw internal error messages"
            assert response, "Response should not be empty after error"


# ---------------------------------------------------------------------------
# R7-2 (High): cost_estimation_routes.py locks event loop
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR7_2_CostEstimationRoutesLockLoop:
    """cost_estimation_routes.py uses threading.Lock and synchronous CPU-bound
    predict_project() inside async route handlers, blocking the asyncio event loop.
    """

    def test_routes_do_not_use_threading_lock(self):
        """Verify the synchronous threading.Lock is replaced with asyncio mechanics
        or run_in_threadpool."""
        source_path = Path("backend/api/cost_estimation_routes.py")
        source = source_path.read_text(encoding="utf-8")

        # Look for threading.Lock
        assert "threading.Lock()" not in source, (
            "R7-2: cost_estimation_routes.py still uses threading.Lock() "
            "which blocks the asyncio event loop in async handlers."
        )

        tree = ast.parse(source)
        # Verify predict_project is run in threadpool or service is accessed asynchronously
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.AsyncFunctionDef)
                and node.name == "predict_cost_estimation"
            ):
                func_source = ast.get_source_segment(source, node) or ""
                assert any(
                    x in func_source
                    for x in (
                        "run_in_threadpool",
                        "await service.predict_project_async",
                        "asyncio.to_thread",
                    )
                ), (
                    "R7-2: predict_cost_estimation calls CPU-bound predict_project synchronously, "
                    "blocking the event loop."
                )


# ---------------------------------------------------------------------------
# R7-3 (Medium): reranker.py logits not normalized
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR7_3_RerankerLogitsNotNormalized:
    """reranker.py uses raw output logits from bge-reranker model (which can be unbounded).
    It must normalize them to [0, 1] using torch.sigmoid() so the ui/rag engine can trust the score.
    """

    def test_reranker_uses_sigmoid(self):
        """Verify reranker applies sigmoid to scores."""
        source_path = Path("backend/services/retrieval/reranker.py")
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        has_sigmoid = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "rerank":
                func_source = ast.get_source_segment(source, node) or ""
                if "sigmoid" in func_source.lower() or "exp(" in func_source.lower():
                    has_sigmoid = True

        assert has_sigmoid, (
            "R7-3: reranker.py does not apply sigmoid to raw model logits. "
            "Scores are unbounded and violate the [0, 1] contract."
        )
