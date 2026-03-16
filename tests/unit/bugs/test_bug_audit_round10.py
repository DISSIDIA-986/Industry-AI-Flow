"""TDI Round 10 audit findings — reproduction tests.

Covers 14 P0/P1 bugs found by parallel audit agents.

P0:
- R10-01: rerank_node passes wrong kwargs to Reranker.rerank()
- R10-02: SQL_PATTERN in sanitizer blocks semicolons and -- in normal queries

P1:
- R10-03: IVFFlat probes never set before similarity_search
- R10-04: Memory manager language fallback still "zh"
- R10-05: _format_memory_payload uses "EN" placeholders
- R10-06: feedback_manager INTERVAL parameterization broken
- R10-07: Load balancing always overrides intent routing
- R10-08: $ prefix breaks cost estimation regex
- R10-09: Whitespace before ( bypasses DANGEROUS_PATTERNS
- R10-10: type() metaclass trick not blocked by validator
- R10-11: Redaction fail-open leaks PII on exception
- R10-12: Safety block bypassed when cost_estimation_node sets response
- R10-13: code_exec_node blocks event loop with synchronous call
- R10-14: retrieval_node retrieve() blocks event loop
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# R10-01 (P0): rerank_node passes wrong kwargs to Reranker.rerank()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_01_RerankNodeWrongKwargs:
    """rerank_node.py calls reranker.rerank(query=..., contexts=..., metadata=...)
    but Reranker.rerank() signature is rerank(query, documents, top_k).
    """

    def test_rerank_node_uses_documents_kwarg(self):
        source = Path("backend/services/workflows/nodes/rerank_node.py").read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            # Find reranker.rerank(...) call
            if isinstance(node.func, ast.Attribute) and node.func.attr == "rerank":
                kwarg_names = [kw.arg for kw in node.keywords]
                assert (
                    "documents" in kwarg_names
                ), "R10-01: rerank_node passes contexts= but Reranker expects documents="
                assert (
                    "contexts" not in kwarg_names
                ), "R10-01: rerank_node should not pass contexts= kwarg"
                assert (
                    "metadata" not in kwarg_names
                ), "R10-01: rerank_node should not pass metadata= kwarg"
                return  # Found the call, test passes

        pytest.fail("Could not find reranker.rerank() call in source")


# ---------------------------------------------------------------------------
# R10-02 (P0): SQL_PATTERN blocks ; and -- in normal queries
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_02_SqlPatternBlocksNormalText:
    """SQL_PATTERN regex includes `|;` and `|--` which match normal English
    text like 'cost -- including labor' or queries with semicolons.
    """

    def test_normal_text_with_double_dash_not_blocked(self):
        from backend.security.sanitizer import SQL_PATTERN

        normal_text = "What is the cost -- including labor and materials"
        assert not SQL_PATTERN.search(
            normal_text
        ), "R10-02: SQL_PATTERN blocks normal English text containing --"

    def test_normal_text_with_semicolon_not_blocked(self):
        from backend.security.sanitizer import SQL_PATTERN

        normal_text = "concrete mix; rebar spacing; foundation depth"
        assert not SQL_PATTERN.search(
            normal_text
        ), "R10-02: SQL_PATTERN blocks normal English text containing semicolons"


# ---------------------------------------------------------------------------
# R10-03 (P1): IVFFlat probes never set before similarity_search
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_03_IvfflatProbesNotSet:
    """vectorstore.py never calls SET ivfflat.probes before similarity_search.
    Default probes=1 with lists>1 examines only a fraction of vectors.
    """

    def test_similarity_search_sets_probes(self):
        source = Path("backend/services/core/vectorstore.py").read_text()
        # Look for SET ivfflat.probes in the similarity_search method
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "similarity_search":
                func_source = ast.get_source_segment(source, node) or ""
                assert "ivfflat.probes" in func_source.lower(), (
                    "R10-03: similarity_search does not set ivfflat.probes. "
                    "Default probes=1 misses ~90% of vectors with IVFFlat index."
                )
                return
        pytest.fail("Could not find similarity_search method")


# ---------------------------------------------------------------------------
# R10-04 (P1): Memory manager language fallback still "zh"
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_04_MemoryManagerLanguageFallback:
    """ConversationMemoryManager._update_summary passes
    `session.language_preference or 'zh'` — should be 'en'.
    """

    def test_summary_language_fallback_is_english(self):
        source = Path("backend/services/memory/manager.py").read_text()
        # Find the language_preference or "zh" pattern
        assert 'or "zh"' not in source and "or 'zh'" not in source, (
            "R10-04: manager.py uses 'zh' as language fallback. "
            "Should be 'en' since all docs are English."
        )


# ---------------------------------------------------------------------------
# R10-05 (P1): _format_memory_payload uses "EN" placeholders
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_05_FormatMemoryPayloadENPlaceholders:
    """rag_engine.py _format_memory_payload returns 'EN.' when empty,
    and uses labels like '- EN:', '- EN:' instead of proper English.
    """

    def test_format_memory_no_en_placeholders(self):
        source = Path("backend/services/rag_engine.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_format_memory_payload"
            ):
                func_source = ast.get_source_segment(source, node) or ""
                # Check for "EN" as a standalone label (not part of longer words)
                en_matches = re.findall(r'"EN[.:]?"', func_source)
                assert (
                    not en_matches
                ), f"R10-05: _format_memory_payload contains EN placeholders: {en_matches}"
                return
        pytest.fail("Could not find _format_memory_payload method")


# ---------------------------------------------------------------------------
# R10-06 (P1): feedback_manager INTERVAL parameterization broken
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_06_FeedbackIntervalParam:
    """feedback_manager.py uses INTERVAL '%s days' with parameterized %s.
    PostgreSQL doesn't allow parameter substitution inside INTERVAL literals.
    """

    def test_interval_not_parameterized_inside_literal(self):
        source = Path(
            "backend/services/feedback_system/feedback_manager.py"
        ).read_text()
        # The pattern INTERVAL '%s days' is wrong — %s inside a string literal
        # is not replaced by parameterized queries. Should use:
        # INTERVAL '1 day' * %s or NOW() - %s * INTERVAL '1 day'
        bad_patterns = [
            r"INTERVAL\s+'%s\s+days?'",
            r"INTERVAL\s+'%s\s+hours?'",
        ]
        for pattern in bad_patterns:
            match = re.search(pattern, source, re.IGNORECASE)
            assert not match, (
                f"R10-06: Found broken INTERVAL parameterization: {match.group(0)}. "
                "PostgreSQL does not substitute %s inside string literals."
            )


# ---------------------------------------------------------------------------
# R10-07 (P1): Load balancing always overrides intent routing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_07_LoadBalancingOverridesIntent:
    """RoutingDecisionEngine.make_routing_decision with enable_load_balancing=True
    passes [primary_agent] + fallback_agents to get_least_loaded_agent, which
    can return a fallback agent even when confidence is high.
    """

    def test_high_confidence_not_overridden_by_load_balancing(self):
        import asyncio

        from backend.services.routing_decision import AgentType, RoutingDecisionEngine

        engine = RoutingDecisionEngine()

        # Intent result with high confidence for data_analysis
        intent_result = {
            "intent": "data_analysis",
            "confidence": 0.95,
            "reasoning": "User wants data analysis",
        }

        decision = asyncio.run(engine.make_routing_decision(intent_result, {}))

        # With confidence 0.95, the primary agent (DATA_ANALYSIS_AGENT) should be selected
        # not overridden by load balancing
        assert decision.selected_agent == AgentType.DATA_ANALYSIS_AGENT, (
            f"R10-07: Expected DATA_ANALYSIS_AGENT but got {decision.selected_agent}. "
            "Load balancing overrode high-confidence intent routing."
        )


# ---------------------------------------------------------------------------
# R10-08 (P1): $ prefix breaks cost estimation regex
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_08_DollarPrefixBreaksCostRegex:
    """extract_cost_features_from_query cannot parse '$500000' because the
    regex expects digits to start immediately: [0-9][0-9,.]*
    """

    def test_dollar_prefix_parsed(self):
        from backend.services.cost_estimation_service import (
            extract_cost_features_from_query,
        )

        result = extract_cost_features_from_query(
            "residential project budget $500000 in Toronto"
        )
        assert "estimated_cost_cad" in result, (
            "R10-08: extract_cost_features_from_query fails to parse '$500000'. "
            "The regex does not handle $ prefix."
        )
        assert result["estimated_cost_cad"] == pytest.approx(
            500000, rel=0.01
        ), f"R10-08: Parsed value {result.get('estimated_cost_cad')} != 500000"


# ---------------------------------------------------------------------------
# R10-09 (P1): Whitespace before ( bypasses DANGEROUS_PATTERNS
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_09_WhitespaceBypassesDangerousPatterns:
    """DANGEROUS_PATTERNS use patterns like r'getattr\\(' which require
    ( immediately after the name. 'getattr (' bypasses the check.
    """

    def test_whitespace_before_paren_detected(self):
        from backend.services.code_executor.validator import CodeValidator

        validator = CodeValidator(strict_mode=False)

        # These should all be blocked
        evasion_codes = [
            "getattr (obj, 'secret')",
            "globals ()",
            "locals ()",
            "vars ()",
        ]
        for code in evasion_codes:
            result = validator.validate(code)
            assert (
                not result.is_valid
            ), f"R10-09: '{code}' bypassed DANGEROUS_PATTERNS via whitespace before ("


# ---------------------------------------------------------------------------
# R10-10 (P1): type() metaclass trick not blocked
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_10_TypeMetaclassTrickNotBlocked:
    """type('X', (object,), {'__init__': lambda self: ...}) can create
    arbitrary classes that bypass the validator.
    """

    def test_type_metaclass_creation_blocked(self):
        from backend.services.code_executor.validator import CodeValidator

        validator = CodeValidator(strict_mode=False)
        code = "Evil = type('Evil', (object,), {'run': lambda self: None})"
        result = validator.validate(code)
        assert (
            not result.is_valid
        ), "R10-10: type() used as metaclass constructor is not blocked by validator"


# ---------------------------------------------------------------------------
# R10-11 (P1): Redaction fail-open leaks PII
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_11_RedactionFailOpenLeaksPII:
    """RedactionService.redact() returns original text on exception,
    meaning a regex error leaks PII to cloud LLM.
    """

    def test_redaction_failure_does_not_leak_text(self):
        from backend.services.security.redaction_service import RedactionService

        svc = RedactionService()
        text_with_pii = "Contact john@example.com for details"

        # Force an exception in redaction
        with patch.object(
            svc,
            "PATTERNS",
            property(lambda self: (_ for _ in ()).throw(RuntimeError("boom"))),
        ):
            result = svc.redact(text_with_pii)

        # On failure, the result should NOT contain the original PII text
        assert "john@example.com" not in result.text, (
            "R10-11: Redaction failure returns original text including PII. "
            "Should return empty string or raise to prevent cloud egress."
        )


# ---------------------------------------------------------------------------
# R10-12 (P1): Safety block bypassed when cost_estimation_node sets response
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_12_SafetyBypassedWithShortcutResponse:
    """When cost_estimation_node sets shortcut_response=True, the pipeline
    skips most nodes but still runs safety_node. However, if cost_estimation_node
    already set state['response'], and the query contains a safety violation,
    the response is already filled and safety_node's block may be ignored
    since response_node sees existing response.
    """

    def test_safety_node_runs_even_with_shortcut_response(self):
        """Verify graph.py pipeline structure: when shortcut_response is True,
        safety_node is in the allowed set. But the pipeline also runs
        cost_estimation_node BEFORE safety_node. If cost_estimation_node succeeds
        and sets a response + shortcut_response, then a dangerous query like
        'rm -rf' gets a cost estimation response instead of being blocked.

        The root issue: cost_estimation_node runs before safety_node in the pipeline.
        A dangerous query with cost intent gets a response before safety checks.
        """
        source = Path("backend/services/workflows/graph.py").read_text()
        tree = ast.parse(source)

        # Find the pipeline list in run_workflow_pipeline
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.AsyncFunctionDef)
                and node.name == "run_workflow_pipeline"
            ):
                func_source = ast.get_source_segment(source, node) or ""
                # Find the pipeline order
                cost_idx = func_source.find("cost_estimation_node")
                safety_idx = func_source.find("safety_node")
                assert (
                    cost_idx > 0 and safety_idx > 0
                ), "Could not find nodes in pipeline"
                # safety_node should come BEFORE cost_estimation_node to prevent
                # dangerous queries from getting responses
                assert safety_idx < cost_idx, (
                    "R10-12: safety_node runs AFTER cost_estimation_node in the pipeline. "
                    "A dangerous query with cost intent gets a cost response before "
                    "safety checks can block it."
                )
                return
        pytest.fail("Could not find run_workflow_pipeline")


# ---------------------------------------------------------------------------
# R10-13 (P1): code_exec_node blocks event loop
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_13_CodeExecNodeBlocksEventLoop:
    """code_exec_node calls manager.execute_code() synchronously inside
    an async function, blocking the event loop.
    """

    def test_code_exec_node_uses_async_execution(self):
        source = Path("backend/services/workflows/nodes/code_exec_node.py").read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "code_exec_node":
                func_source = ast.get_source_segment(source, node) or ""
                has_async_exec = any(
                    x in func_source
                    for x in (
                        "await",
                        "run_in_executor",
                        "asyncio.to_thread",
                        "run_in_threadpool",
                    )
                    if "execute_code" in func_source
                    and x != "await result"  # not just awaiting the result check
                )
                # The function must use async execution for manager.execute_code
                assert "await" in func_source and (
                    "run_in_executor" in func_source
                    or "asyncio.to_thread" in func_source
                    or "run_in_threadpool" in func_source
                    or "await manager" in func_source
                ), (
                    "R10-13: code_exec_node calls manager.execute_code() synchronously. "
                    "Should use asyncio.to_thread or run_in_executor."
                )
                return
        pytest.fail("Could not find code_exec_node async function")


# ---------------------------------------------------------------------------
# R10-14 (P1): retrieval_node blocks event loop
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR10_14_RetrievalNodeBlocksEventLoop:
    """retrieval_node calls retriever.retrieve() which may be synchronous.
    It checks hasattr(result, '__await__') but the call itself still blocks
    the event loop before the await check.
    """

    def test_retrieval_node_handles_sync_retriever(self):
        source = Path("backend/services/workflows/nodes/retrieval_node.py").read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "retrieval_node":
                func_source = ast.get_source_segment(source, node) or ""
                # Should use run_in_executor or asyncio.to_thread for sync retrievers
                has_thread_safety = any(
                    x in func_source
                    for x in (
                        "run_in_executor",
                        "asyncio.to_thread",
                        "run_in_threadpool",
                    )
                )
                assert has_thread_safety, (
                    "R10-14: retrieval_node calls retriever.retrieve() which blocks "
                    "the event loop if retriever is synchronous. Should offload to "
                    "thread pool."
                )
                return
        pytest.fail("Could not find retrieval_node async function")
