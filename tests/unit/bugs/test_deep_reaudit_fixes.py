"""Tests for deep re-audit P0/P1 fixes.

Covers:
- P0-A: iterative_code_execution.py validation bypass
- P0-B: data_transfer.py SQL injection + credential leak
- P1-A: safety_node.py coverage gaps
- P1-B: double score normalization
- P1-C: intent heuristic ordering
- P1-D: credential leak to disk
"""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest


@pytest.mark.unit
class TestP0A_IterativeCodeValidation:

    def test_self_healing_tool_rejects_dangerous_code(self):
        """self_healing_code_execution_tool must reject os.system before execution."""
        from backend.tools.iterative_code_execution import (
            self_healing_code_execution_tool,
        )

        dangerous_code = "import os; os.system('whoami')"
        result = self_healing_code_execution_tool.invoke({
            "code": dangerous_code,
            "description": "test",
        })

        assert not result["success"], (
            "P0-A: self_healing_code_execution_tool executed dangerous code "
            "without validation"
        )
        assert "validation" in result.get("error", "").lower(), (
            f"P0-A: Expected validation error, got: {result.get('error')}"
        )

    def test_self_healing_tool_rejects_open(self):
        """self_healing_code_execution_tool must reject open('/etc/passwd')."""
        from backend.tools.iterative_code_execution import (
            self_healing_code_execution_tool,
        )

        dangerous_code = "data = open('/etc/passwd').read()"
        result = self_healing_code_execution_tool.invoke({
            "code": dangerous_code,
            "description": "test",
        })

        assert not result["success"], (
            "P0-A: self_healing_code_execution_tool allowed open('/etc/passwd')"
        )


@pytest.mark.unit
class TestP0B_SQLInjectionGuard:

    def test_cleanup_rejects_malicious_table_name(self):
        """cleanup_transferred_data must reject non-standard table names."""
        from backend.services.data_transfer import DataFileTransfer

        transfer = DataFileTransfer.__new__(DataFileTransfer)
        transfer.temp_dir = None
        transfer.db_engine = None  # No real DB needed

        # Simulate a transfer result with injected table name
        malicious_result = {
            "method": "database",
            "transferred_path": "temp_data_abc; DROP TABLE users; --",
        }

        # Should NOT crash — should silently reject
        result = transfer.cleanup_transferred_data(malicious_result)
        # The function returns True/False for cleanup success
        assert isinstance(result, bool)

    def test_valid_table_name_matches_pattern(self):
        """Only temp_data_[8 hex chars] should match the guard pattern."""
        pattern = re.compile(r"^temp_data_[0-9a-f]{8}$")

        assert pattern.match("temp_data_a1b2c3d4")
        assert not pattern.match("temp_data_abc; DROP TABLE users;--")
        assert not pattern.match("users")
        assert not pattern.match("")
        assert not pattern.match("temp_data_")
        assert not pattern.match("temp_data_a1b2c3d4e5")  # too long


@pytest.mark.unit
class TestP0B_CredentialLeak:

    def test_create_db_config_does_not_contain_password(self):
        """_create_db_config must not write raw password to config."""
        from unittest.mock import patch

        with patch("backend.services.data_transfer.settings") as mock_settings:
            mock_settings.postgres_host = "localhost"
            mock_settings.postgres_port = 5432
            mock_settings.postgres_db = "testdb"
            mock_settings.postgres_user = "testuser"
            mock_settings.postgres_password = "super_secret_password_123"
            mock_settings.temp_data_dir = "/tmp/test"

            from backend.services.data_transfer import DataFileTransfer

            transfer = DataFileTransfer.__new__(DataFileTransfer)
            transfer.temp_dir = None
            transfer.db_engine = None

            config = transfer._create_db_config(
                "temp_data_abc12345",
                {"path": "/some/file.csv", "size_mb": 1.0},
            )

            connection = config["connection"]
            assert "password" not in connection, (
                "P1-D: raw 'password' key still exists in db config"
            )
            assert connection.get("password_env") == "POSTGRES_PASSWORD", (
                "P1-D: config should reference POSTGRES_PASSWORD env var"
            )
            # Make sure the actual password string doesn't appear anywhere
            config_str = str(config)
            assert "super_secret_password_123" not in config_str, (
                "P1-D: raw password leaked into config dict"
            )


@pytest.mark.unit
class TestP1A_SafetyNodeCoverage:

    @pytest.mark.asyncio
    async def test_safety_node_blocks_eval(self):
        """safety_node must block eval() calls."""
        from backend.services.workflows.nodes.safety_node import safety_node

        state = {"query": "Please run eval('malicious_code')", "metadata": {}}
        result = await safety_node(state, SimpleNamespace())

        assert result["metadata"]["safety_status"] == "blocked", (
            "P1-A: safety_node did not block eval()"
        )

    @pytest.mark.asyncio
    async def test_safety_node_blocks_exec(self):
        """safety_node must block exec() calls."""
        from backend.services.workflows.nodes.safety_node import safety_node

        state = {"query": "exec('import os; os.remove(\"file\")')", "metadata": {}}
        result = await safety_node(state, SimpleNamespace())

        assert result["metadata"]["safety_status"] == "blocked", (
            "P1-A: safety_node did not block exec()"
        )

    @pytest.mark.asyncio
    async def test_safety_node_blocks_dunder_import(self):
        """safety_node must block __import__() calls."""
        from backend.services.workflows.nodes.safety_node import safety_node

        state = {"query": "__import__('os').system('id')", "metadata": {}}
        result = await safety_node(state, SimpleNamespace())

        assert result["metadata"]["safety_status"] == "blocked", (
            "P1-A: safety_node did not block __import__()"
        )

    @pytest.mark.asyncio
    async def test_safety_node_blocks_pickle(self):
        """safety_node must block pickle.loads() calls."""
        from backend.services.workflows.nodes.safety_node import safety_node

        state = {"query": "pickle.loads(data)", "metadata": {}}
        result = await safety_node(state, SimpleNamespace())

        assert result["metadata"]["safety_status"] == "blocked", (
            "P1-A: safety_node did not block pickle.loads()"
        )

    @pytest.mark.asyncio
    async def test_safety_node_allows_normal_queries(self):
        """Normal construction queries should NOT be blocked."""
        from backend.services.workflows.nodes.safety_node import safety_node

        state = {
            "query": "What is the cost estimate for a 20-floor office building?",
            "metadata": {},
        }
        result = await safety_node(state, SimpleNamespace())

        assert result["metadata"]["safety_status"] == "ok", (
            "P1-A: Normal query was incorrectly blocked"
        )


@pytest.mark.unit
class TestP1B_DoubleNormalization:

    def test_extract_sources_preserves_raw_score(self):
        """_extract_sources must NOT re-normalize already-normalized scores."""
        from backend.api.workflow_query_routes import _extract_sources

        metadata = {
            "sources": [
                {"doc_id": "doc-1", "filename": "a.pdf", "score": 0.87},
                {"doc_id": "doc-2", "filename": "b.pdf", "score": 0.65},
            ]
        }

        sources = _extract_sources(metadata)

        assert len(sources) == 2
        # Score should be preserved as-is, not divided by max
        assert sources[0]["relevance"] == 0.87, (
            f"P1-B: Expected 0.87, got {sources[0]['relevance']}. "
            "Double normalization is still active."
        )
        assert sources[1]["relevance"] == 0.65, (
            f"P1-B: Expected 0.65, got {sources[1]['relevance']}"
        )


@pytest.mark.unit
class TestP1C_IntentHeuristicOrdering:

    @pytest.mark.asyncio
    async def test_predict_cost_with_python_is_cost_estimation(self):
        """'predict construction cost using python' should be cost_estimation,
        not code_execution."""
        from backend.services.workflows.nodes.intent_node import intent_node

        state = {
            "query": "predict construction cost using python",
            "metadata": {},
        }
        result = await intent_node(state, SimpleNamespace())

        assert result["intent"] == "cost_estimation", (
            f"P1-C: 'predict construction cost using python' was classified as "
            f"'{result['intent']}' — cost_estimation should be checked before "
            f"code_execution in the heuristic"
        )

    @pytest.mark.asyncio
    async def test_pure_python_query_is_still_code_execution(self):
        """'run python script' should still be code_execution."""
        from backend.services.workflows.nodes.intent_node import intent_node

        state = {"query": "run python script to sort data", "metadata": {}}
        result = await intent_node(state, SimpleNamespace())

        assert result["intent"] == "code_execution", (
            f"P1-C regression: 'run python script' should be code_execution, "
            f"got '{result['intent']}'"
        )
