"""TDI Round 18 bug reproduction tests.

Bugs discovered 2026-02-27 via 4-agent parallel audit.
Focus: RAG pipeline consistency, workflow response propagation,
security validator gaps, intent heuristic precision.
"""

from __future__ import annotations

import ast
import importlib.util

import pytest


def _load_module(name: str, path: str):
    """Load a module directly by file path, bypassing package __init__.py chains
    that pull in unavailable dependencies (pydantic_settings, requests, etc.)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_validator():
    return _load_module("validator", "backend/services/code_executor/validator.py").validate_code


def _load_heuristic_intent():
    import sys
    import types
    # Pre-register packages so intent_node's "from backend.services.workflows.state"
    # import resolves without triggering workflows/__init__.py (which needs pydantic_settings).
    for pkg in [
        "backend", "backend.services", "backend.services.workflows",
        "backend.services.workflows.nodes",
    ]:
        if pkg not in sys.modules:
            sys.modules[pkg] = types.ModuleType(pkg)
    # Load state.py first (needed by intent_node)
    state_mod = _load_module("backend.services.workflows.state",
                             "backend/services/workflows/state.py")
    sys.modules["backend.services.workflows.state"] = state_mod
    intent_mod = _load_module("backend.services.workflows.nodes.intent_node",
                              "backend/services/workflows/nodes/intent_node.py")
    return intent_mod._heuristic_intent


# ---------------------------------------------------------------------------
# R18-12 (P0): Fallback runner sets state["response"], but workflow_query_routes
# reads result.get("agent_response") — user gets None response.
# ---------------------------------------------------------------------------
class TestR18_12_FallbackRunnerResponseKey:
    """graph.py response_node sets state['response'] but
    workflow_query_routes.py:449 reads result.get('agent_response').
    When using fallback orchestrator, the user receives no response text."""

    def test_workflow_query_routes_reads_response_key(self):
        """The WorkflowQueryResponse constructor should use
        result.get('response') or fall back to result.get('agent_response'),
        not exclusively read 'agent_response'."""
        source = open("backend/api/workflow_query_routes.py").read()
        tree = ast.parse(source)

        # Find the WorkflowQueryResponse(...) constructor call inside workflow_query()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not (isinstance(node.func, ast.Name) and node.func.id == "WorkflowQueryResponse"):
                continue
            # Find the 'response' keyword argument
            for kw in node.keywords:
                if kw.arg == "response":
                    # Check if it reads ONLY "agent_response" from result
                    src_segment = ast.dump(kw.value)
                    if "agent_response" in src_segment and "response" not in src_segment.replace("agent_response", ""):
                        pytest.fail(
                            "WorkflowQueryResponse.response reads only result.get('agent_response') — "
                            "but fallback runner (graph.py) sets state['response']. "
                            "Should read result.get('response') or result.get('agent_response')."
                        )


# ---------------------------------------------------------------------------
# R18-04 (P1): f-string expressions bypass code validator
# ---------------------------------------------------------------------------
class TestR18_04_FStringBypassValidator:
    """f-string containing __import__ bypasses all validator checks because
    the dangerous pattern exists inside an ast.FormattedValue node."""

    def test_fstring_import_blocked(self):
        validate_code = _load_validator()

        malicious = 'result = f"{__import__(\'os\').getcwd()}"'
        result = validate_code(malicious, strict_mode=True)
        assert not result.is_valid, (
            "f-string containing __import__ should be blocked by validator"
        )

    def test_fstring_eval_blocked(self):
        validate_code = _load_validator()

        malicious = "x = f\"{eval('1+1')}\""
        result = validate_code(malicious, strict_mode=True)
        assert not result.is_valid, (
            "f-string containing eval() should be blocked by validator"
        )


# ---------------------------------------------------------------------------
# R18-05 (P1): bleach.clean runs on un-decoded input
# ---------------------------------------------------------------------------
class TestR18_05_BleachRunsOnUndecoded:
    """sanitize_text URL-decodes for pattern checks but runs bleach.clean
    on the original stripped value, not the decoded version."""

    def test_bleach_should_operate_on_decoded(self):
        """Verify via source inspection that bleach.clean receives the
        URL-decoded text, not the raw input."""
        source = open("backend/security/sanitizer.py").read()
        tree = ast.parse(source)

        # Find the sanitize_text function
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef) and node.name == "sanitize_text"):
                continue
            # Find bleach.clean() call and check its first argument
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                if isinstance(child.func, ast.Attribute) and child.func.attr == "clean":
                    first_arg = child.args[0] if child.args else None
                    if isinstance(first_arg, ast.Name) and first_arg.id == "stripped":
                        pytest.fail(
                            "bleach.clean receives 'stripped' (raw input) instead of 'decoded' "
                            "(URL-decoded input). Double-encoded HTML entities survive sanitization."
                        )


# ---------------------------------------------------------------------------
# R18-07 (P1): "analyze construction costs" misroutes to data_analysis
# ---------------------------------------------------------------------------
class TestR18_07_AnalyzeCostsMisroute:
    """Query 'analyze construction costs in Calgary' should route to
    cost_estimation but gets data_analysis because 'analyze' matches first
    after cost patterns fail."""

    def test_analyze_costs_routes_to_cost_estimation(self):
        _heuristic_intent = _load_heuristic_intent()

        intent = _heuristic_intent("analyze construction costs in Calgary")
        assert intent == "cost_estimation", (
            f"Expected cost_estimation, got {intent} — "
            "'analyze construction costs' should be cost_estimation"
        )


# ---------------------------------------------------------------------------
# R18-14 (P1): "analyze" too broad in heuristic intent
# ---------------------------------------------------------------------------
class TestR18_14_AnalyzeToBroad:
    """Query 'analyze why the concrete failed' should be knowledge_retrieval
    not data_analysis — no dataset/csv context."""

    def test_analyze_concrete_failure_is_knowledge(self):
        _heuristic_intent = _load_heuristic_intent()

        intent = _heuristic_intent("analyze why the concrete failed")
        assert intent == "knowledge_retrieval", (
            f"Expected knowledge_retrieval, got {intent} — "
            "'analyze why X failed' is a knowledge question, not data analysis"
        )


# ---------------------------------------------------------------------------
# R18-11 (P1): Local LLM context window hardcoded to 4096
# ---------------------------------------------------------------------------
class TestR18_11_LocalContextWindowHardcoded:
    """dispatch_service._run_local hardcodes context_window=4096 regardless
    of actual model capability — unnecessarily truncating prompts."""

    def test_local_context_not_hardcoded_4096(self):
        source = open("backend/services/llm_integration/dispatch_service.py").read()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_run_local":
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute) and child.func.attr == "_truncate_prompt":
                            for kw in child.keywords:
                                if kw.arg == "context_window":
                                    if isinstance(kw.value, ast.Constant) and kw.value.value == 4096:
                                        pytest.fail(
                                            "context_window is hardcoded to 4096 in _run_local — "
                                            "should read from model/settings config"
                                        )


# ---------------------------------------------------------------------------
# R18-09 (P1): __reduce__ method definition not caught by validator
# ---------------------------------------------------------------------------
class TestR18_09_ReduceMethodDefinition:
    """A class defining __reduce__ can be pickled to execute arbitrary code.
    The DANGEROUS_PATTERNS regex only catches .(__reduce__) attribute access,
    not method definitions inside a class."""

    def test_reduce_method_definition_blocked(self):
        validate_code = _load_validator()

        malicious = (
            "class Evil:\n"
            "    def __reduce__(self):\n"
            "        return (print, ('pwned',))\n"
            "e = Evil()\n"
        )
        result = validate_code(malicious, strict_mode=True)
        assert not result.is_valid, (
            "Class with __reduce__ method should be blocked — "
            "enables arbitrary code execution via pickle protocol"
        )

    def test_reduce_ex_method_definition_blocked(self):
        validate_code = _load_validator()

        malicious = (
            "class Evil:\n"
            "    def __reduce_ex__(self, protocol):\n"
            "        return (print, ('pwned',))\n"
        )
        result = validate_code(malicious, strict_mode=True)
        assert not result.is_valid, (
            "Class with __reduce_ex__ method should be blocked — "
            "enables arbitrary code execution via pickle protocol"
        )


# ---------------------------------------------------------------------------
# R18-03 (P1): response_builder returning None raises TypeError on await
# ---------------------------------------------------------------------------
class TestR18_03_ResponseBuilderNoneAwait:
    """If services.response_builder returns None, `await None` raises TypeError."""

    def test_response_builder_returns_none_handled(self):
        """Verify response_node handles None return from response_builder.
        Check via source: `await result if hasattr(result, '__await__')` — if
        result is None, hasattr(None, '__await__') is False so no await happens.
        BUT then state['response'] = None which is falsy."""
        source = open("backend/services/workflows/nodes/response_node.py").read()
        # response_builder returns None → state["response"] = None
        # Then the node returns with response=None, which is empty
        # The caller (graph.py:102) checks `if not state.get("response"):`
        # and re-runs response_node — but this time response_builder returns
        # None again, causing an infinite re-run mitigated only by the 120s timeout.
        # Actually graph.py line 102 runs response_node once more; on second run
        # state already has response=None but _build_default_response returns a string.
        # Net effect: user gets a generic "processed" message instead of LLM response.
        # Check that response_node validates None return and falls through to default.
        assert "if result is None" in source or "is not None" in source or "or _build_default_response" in source, (
            "response_node does not handle None return from response_builder — "
            "falls through silently setting state['response'] = None"
        )


# ---------------------------------------------------------------------------
# R18-01 (P1): get_feedback_statistics returns error string in dict
# ---------------------------------------------------------------------------
class TestR18_01_FeedbackStatsErrorDict:
    """rag_engine.get_feedback_statistics returns {"error": str(e)} on exception
    which leaks internal error details to API callers."""

    def test_feedback_stats_error_no_leak(self):
        """Verify via source inspection that the error path does not
        expose raw exception strings."""
        source = open("backend/services/rag_engine.py").read()
        # After fix: should NOT return raw str(e) to callers
        assert 'return {"error": str(e)}' not in source, (
            "get_feedback_statistics still leaks raw error string via str(e) — "
            "can contain DB addresses, internal paths, etc."
        )


# ---------------------------------------------------------------------------
# R18-13 (P1): Fallback embeddings produce random retrieval without warning
# ---------------------------------------------------------------------------
class TestR18_13_FallbackEmbeddingsNoWarning:
    """When no ML embedding model is available, hash-based fallback embeddings
    produce semantically meaningless vectors but the RAG response does not
    indicate degraded quality."""

    def test_rag_query_response_missing_embedding_quality_key(self):
        """The dict returned by rag_engine.query() should contain an
        'embedding_quality' or 'embedding_backend' key so downstream consumers
        know if fallback (hash) embeddings were used."""
        source = open("backend/services/rag_engine.py").read()
        # Extract the return dict in query() — look for the return { block
        # The query method returns a dict with keys like query_id, question, etc.
        # It should also include an embedding quality signal
        assert "embedding_backend" in source or "embedding_quality" in source, (
            "rag_engine.query() does not propagate embedding backend status — "
            "when fallback hash embeddings are active, users get random retrieval "
            "results with no indication of degraded quality"
        )
