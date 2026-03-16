"""TDI Round 4 audit findings — reproduction tests.

Covers:
- R4-1 (High): _extract_dataset_info crashes on non-UTF-8 CSV encoding
- R4-2 (High): sanitize_identifier allows null bytes
- R4-3 (High): Old code_executor.py spawns cleanup thread per execution
- R4-4 (Medium): Template code picks wrong numeric column
- R4-5 (Medium): _extract_code_from_response accepts prose as code
- R4-6 (Medium): _record_memory_interaction history trimming edge
- R4-7 (Medium): _build_default_response leaks query/context in non-error path
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.filterwarnings(
    "ignore:datetime\\.datetime\\.utcnow\\(\\) is deprecated.*:DeprecationWarning"
)


# ---------------------------------------------------------------------------
# R4-1 (High): _extract_dataset_info encoding crash
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR4_1_DatasetInfoEncodingCrash:
    """data_analysis_agent._extract_dataset_info calls pd.read_csv()
    without specifying encoding. Non-UTF-8 files (Latin-1, GBK, etc.)
    cause UnicodeDecodeError and return no useful info."""

    def test_latin1_csv_should_not_crash(self, tmp_path):
        """A Latin-1 encoded CSV should be read successfully."""
        csv_path = tmp_path / "latin1.csv"
        csv_path.write_bytes("name,cost\nCafé,100\nRénovation,200\n".encode("latin-1"))

        with (
            patch(
                "backend.services.data_analysis.data_analysis_agent.settings"
            ) as mock_settings,
            patch(
                "backend.services.data_analysis.data_analysis_agent.LLMClientFactory"
            ),
            patch(
                "backend.services.data_analysis.data_analysis_agent.get_code_execution_manager",
                return_value=None,
            ),
            patch(
                "backend.services.data_analysis.data_analysis_agent.code_executor", None
            ),
        ):
            mock_settings.resolved_local_backend = "mock"
            from backend.services.data_analysis.data_analysis_agent import (
                DataAnalysisAgent,
            )

            agent = DataAnalysisAgent.__new__(DataAnalysisAgent)
            agent.llm_client = MagicMock()
            agent.code_execution_manager = None
            agent.code_executor = None

            result = agent._extract_dataset_info(str(csv_path))

        assert (
            "error" not in result
        ), f"R4-1: _extract_dataset_info crashed on Latin-1 CSV: {result.get('error')}"
        assert (
            result.get("rows") == 2
        ), f"R4-1: Expected 2 rows, got {result.get('rows')}"

    def test_utf8_sig_csv_should_not_crash(self, tmp_path):
        """A UTF-8-BOM encoded CSV should be read successfully."""
        csv_path = tmp_path / "bom.csv"
        csv_path.write_bytes(b"\xef\xbb\xbfname,cost\nTest,100\n")

        with (
            patch(
                "backend.services.data_analysis.data_analysis_agent.settings"
            ) as mock_settings,
            patch(
                "backend.services.data_analysis.data_analysis_agent.LLMClientFactory"
            ),
            patch(
                "backend.services.data_analysis.data_analysis_agent.get_code_execution_manager",
                return_value=None,
            ),
            patch(
                "backend.services.data_analysis.data_analysis_agent.code_executor", None
            ),
        ):
            mock_settings.resolved_local_backend = "mock"
            from backend.services.data_analysis.data_analysis_agent import (
                DataAnalysisAgent,
            )

            agent = DataAnalysisAgent.__new__(DataAnalysisAgent)
            agent.llm_client = MagicMock()
            agent.code_execution_manager = None
            agent.code_executor = None

            result = agent._extract_dataset_info(str(csv_path))

        assert (
            "error" not in result
        ), f"R4-1: _extract_dataset_info crashed on UTF-8-BOM CSV: {result.get('error')}"


# ---------------------------------------------------------------------------
# R4-2 (High): sanitize_identifier null byte bypass
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR4_2_SanitizerNullByte:
    """sanitize_identifier blocks '/' and '\\' but allows null bytes
    which can cause path truncation in C-level filesystem operations."""

    def test_rejects_null_byte(self):
        """Null byte embedded in identifier should be rejected."""
        from fastapi import HTTPException

        from backend.security.sanitizer import sanitize_identifier

        with pytest.raises(HTTPException):
            sanitize_identifier("project_type\x00../../etc/passwd", "test_field")

    def test_rejects_percent_encoded_null(self):
        """Percent-encoded null (%00) should also be rejected."""
        from fastapi import HTTPException

        from backend.security.sanitizer import sanitize_identifier

        with pytest.raises(HTTPException):
            sanitize_identifier("project_type%00malicious", "test_field")


# ---------------------------------------------------------------------------
# R4-3 (High): code_executor.py cleanup thread leak
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR4_3_CleanupThreadLeak:
    """Old code_executor.py spawns a new daemon thread per execute_code()
    call for delayed cleanup. Under sustained load this causes thread
    accumulation."""

    def test_old_code_executor_cleanup_spawns_thread_per_call(self):
        """The old standalone code_executor.py spawns a daemon thread
        per execute_code() call for delayed cleanup. This test documents
        the pattern by checking the source code directly."""
        import ast
        import inspect

        # The old module is at backend/services/code_executor.py (standalone file)
        old_module_path = (
            Path(__file__).parent.parent.parent.parent
            / "backend"
            / "services"
            / "code_executor.py"
        )

        if not old_module_path.exists():
            pytest.skip("Old standalone code_executor.py not found")

        source = old_module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Look for threading.Thread creation inside execute_code
        thread_spawns_in_finally = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and (
                getattr(node, "attr", "") == "Thread"
            ):
                thread_spawns_in_finally = True
                break

        # The cleanup pattern should use a bounded approach (queue, executor pool)
        # not raw Thread() per call
        assert not thread_spawns_in_finally, (
            "R4-3: Old code_executor.py still uses threading.Thread per "
            "execution for cleanup. This causes unbounded thread accumulation "
            "under sustained load. Should use a bounded cleanup queue."
        )


# ---------------------------------------------------------------------------
# R4-4 (Medium): Template code picks wrong column
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR4_4_TemplateColumnSelection:
    """Template analysis code (_template_average, etc.) always picks
    numeric_cols[0] regardless of the user's question. If user asks
    about 'cost' but the first numeric column is 'id', wrong analysis."""

    def test_template_average_selects_relevant_column(self):
        """Asking 'average cost' should pick a cost-related column,
        not the first numeric column."""
        with (
            patch(
                "backend.services.data_analysis.data_analysis_agent.settings"
            ) as mock_settings,
            patch(
                "backend.services.data_analysis.data_analysis_agent.LLMClientFactory"
            ),
            patch(
                "backend.services.data_analysis.data_analysis_agent.get_code_execution_manager",
                return_value=None,
            ),
            patch(
                "backend.services.data_analysis.data_analysis_agent.code_executor", None
            ),
        ):
            mock_settings.resolved_local_backend = "mock"
            from backend.services.data_analysis.data_analysis_agent import (
                DataAnalysisAgent,
            )

            agent = DataAnalysisAgent.__new__(DataAnalysisAgent)
            agent.llm_client = MagicMock()

            metadata = {
                "columns_info": [
                    {"name": "id", "type": "int64", "mean": 50},
                    {"name": "sqft", "type": "float64", "mean": 2500},
                    {"name": "cost_cad", "type": "float64", "mean": 450000},
                ],
            }

            code = agent._template_average(
                "data.csv", metadata, "what is the average cost"
            )

            # The code should reference 'cost_cad', not 'id'
            assert "cost_cad" in code, (
                f"R4-4: _template_average picked wrong column. "
                f"Asked about average but code doesn't reference 'cost_cad': {code[:100]}"
            )


# ---------------------------------------------------------------------------
# R4-5 (Medium): _extract_code_from_response lax fallback
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR4_5_ExtractCodeLaxFallback:
    """_extract_code_from_response accepts entire LLM response as code
    if it contains 'import' and 'print', even if it's prose/markdown."""

    def test_rejects_mixed_prose_and_code(self):
        """LLM response with prose + 'import' + 'print' should NOT be
        treated as executable code."""
        with (
            patch(
                "backend.services.data_analysis.data_analysis_agent.settings"
            ) as mock_settings,
            patch(
                "backend.services.data_analysis.data_analysis_agent.LLMClientFactory"
            ),
            patch(
                "backend.services.data_analysis.data_analysis_agent.get_code_execution_manager",
                return_value=None,
            ),
            patch(
                "backend.services.data_analysis.data_analysis_agent.code_executor", None
            ),
        ):
            mock_settings.resolved_local_backend = "mock"
            from backend.services.data_analysis.data_analysis_agent import (
                DataAnalysisAgent,
            )

            agent = DataAnalysisAgent.__new__(DataAnalysisAgent)
            agent.llm_client = MagicMock()

            prose_response = (
                "Here's how you can analyze the data:\n\n"
                "First, import pandas. Then read the CSV file.\n"
                "After that, print the results to see the output.\n\n"
                "This approach works well for construction datasets."
            )

            result = agent._extract_code_from_response(prose_response)

            assert result is None, (
                f"R4-5: _extract_code_from_response accepted prose as code: "
                f"{result[:80] if result else 'None'}"
            )


# ---------------------------------------------------------------------------
# R4-6 (Medium): Memory interaction history edge
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR4_6_MemoryHistoryTrimming:
    """_record_memory_interaction trims history to 50 after appending.
    The oldest interactions are silently discarded without summarization,
    losing potentially important conversation context."""

    def test_history_cap_preserves_latest(self):
        """After 55 interactions, history should contain exactly 50
        and the oldest 5 should be gone."""
        with (
            patch("backend.services.rag_engine.VectorStore"),
            patch("backend.services.rag_engine.get_llm_client"),
            patch(
                "backend.services.rag_engine.get_backend_status",
                return_value={"backend": "mock"},
            ),
            patch("backend.services.rag_engine.HybridRetriever"),
            patch("backend.services.rag_engine.Reranker"),
            patch("backend.services.rag_engine.FeedbackManager"),
            patch("backend.services.rag_engine.create_safety_guard", return_value=None),
            patch("backend.services.rag_engine.settings") as mock_settings,
        ):
            mock_settings.enable_safety_guard = False
            mock_settings.enable_conversation_memory = False

            from backend.services.rag_engine import SimpleRAG, _MemorySession

            rag = SimpleRAG.__new__(SimpleRAG)
            rag.memory_manager = None
            rag._memory_sessions = {}
            rag._memory_lock = threading.Lock()

            session = _MemorySession(session_id="trim-test")

            # Record 55 interactions
            for i in range(55):
                rag._record_memory_interaction(session, f"question_{i}", f"answer_{i}")

            assert len(session.interaction_history) == 50, (
                f"R4-6: Expected history capped at 50, got "
                f"{len(session.interaction_history)}"
            )
            # Verify oldest are trimmed — first entry should be question_5
            oldest = session.interaction_history[0]
            assert oldest.user_query == "question_5", (
                f"R4-6: Expected oldest entry to be 'question_5' after "
                f"trimming, got '{oldest.user_query}'"
            )


# ---------------------------------------------------------------------------
# R4-7 (Medium): response_node leaks debug info in non-error path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR4_7_ResponseNodeQueryLeak:
    """_build_default_response includes raw query text, context snippets,
    provider name, intent, and prompt name in the response — even for
    non-error paths. This leaks internal info to end users."""

    @pytest.mark.asyncio
    async def test_non_error_response_should_not_contain_raw_query(self):
        """Non-error response should NOT echo back the raw user query."""
        from backend.services.workflows.nodes.response_node import response_node

        state = {
            "query": "What is the cost of a 2-story residential house in Toronto?",
            "intent": "cost_estimation",
            "provider_used": "ollama",
            "retrieved_context": [
                {"content": "Average residential cost in Toronto is $450/sqft"},
            ],
            "metadata": {},
        }

        result = await response_node(state, SimpleNamespace())
        response_text = result.get("response", "")

        # The raw query should not be echoed back in the response
        assert "What is the cost of a 2-story residential house" not in response_text, (
            "R4-7: response_node echoes raw user query in default response, "
            "leaking user input in the response body"
        )
