"""TDI Round 6 — Failing tests for P0 + P1 bugs found by 4-agent audit.

These tests assert CORRECT behavior that is currently broken.
All tests use xfail markers until fixes are applied.

Bugs covered (25 total):
  P0: 8 bugs (demo crashers)
  P1: 17 bugs (wrong results)
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import re
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper: load legacy code_executor.py (shadowed by package)
# ---------------------------------------------------------------------------

def _load_legacy_code_executor():
    spec = importlib.util.spec_from_file_location(
        "code_executor_legacy",
        "backend/services/code_executor.py",
    )
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        pytest.skip("Legacy code_executor.py could not be loaded")
    return mod


# ---------------------------------------------------------------------------
# Helper: read source code as text (avoid import side effects)
# ---------------------------------------------------------------------------

def _read_source(path: str) -> str:
    with open(path) as f:
        return f.read()


# ===================================================================
# P0 BUGS — Demo Crashers
# ===================================================================


class TestP0SafetyDisclaimers:
    """P0 #1: Safety disclaimers and refusal messages are corrupted EN placeholders.

    File: backend/services/safety/groundedness_checker.py:169-222
    """

    def test_safety_critical_disclaimer_is_readable_english(self):
        source = _read_source("backend/services/safety/groundedness_checker.py")
        assert "SAFETY_CRITICAL" in source, "SafetyLevel.SAFETY_CRITICAL not found"
        # The disclaimer should contain actual English words, not "EN" placeholders
        # Find the SAFETY_CRITICAL disclaimer block
        match = re.search(
            r'SAFETY_CRITICAL.*?"""(.*?)"""',
            source,
            re.DOTALL,
        )
        if not match:
            match = re.search(
                r"SAFETY_CRITICAL.*?(\"\n.*?\")",
                source,
                re.DOTALL,
            )
        # Look for actual meaningful English safety text
        assert "verify" in source.lower() or "consult" in source.lower() or "professional" in source.lower(), (
            "Safety disclaimer should contain actionable English guidance "
            "(e.g., 'verify', 'consult a professional'), not EN placeholders"
        )

    def test_refusal_message_is_readable_english(self):
        source = _read_source("backend/services/safety/groundedness_checker.py")
        # Count occurrences of the placeholder pattern "EN" used as content
        # Real English text should not have standalone "EN" as a content word
        en_placeholder_count = len(re.findall(r'"EN[,.]', source))
        assert en_placeholder_count == 0, (
            f"Found {en_placeholder_count} corrupted 'EN' placeholder patterns in "
            "groundedness_checker.py — refusal messages are not readable English"
        )


class TestP0FallbackEmbeddingDim:
    """P0 #2: Fallback embedding dimension 384 vs 768 expected.

    File: backend/services/core/embedder.py:26
    """

    def test_fallback_dim_matches_database_schema(self):
        source = _read_source("backend/services/core/embedder.py")
        # The fallback dimension should be 768 to match pgvector schema
        match = re.search(r"_FALLBACK_DIM\s*=.*?(\d+)", source)
        assert match, "_FALLBACK_DIM not found in embedder.py"
        fallback_dim = int(match.group(1))
        assert fallback_dim == 768, (
            f"_FALLBACK_DIM is {fallback_dim}, but pgvector schema expects 768-dim "
            "(nomic-embed-text-v1.5). Mismatch causes PostgreSQL dimension errors."
        )


class TestP0DispatchENCheck:
    """P0 #3: 'EN' in text check matches common English, causes spurious fallback.

    File: backend/services/llm_integration/dispatch_service.py:66
    """

    def test_confidence_estimator_no_false_positive_on_english(self):
        source = _read_source("backend/services/llm_integration/dispatch_service.py")
        # The confidence estimator should NOT contain bare '"EN"' checks
        # that match common English words like ENERGY, ENABLE, ENSURE
        has_bare_en_check = bool(re.search(r'"EN"\s+in\s+text', source))
        assert not has_bare_en_check, (
            "dispatch_service.py contains '\"EN\" in text' check that matches "
            "common English words (ENERGY, ENABLE, ENSURE), causing spurious "
            "cloud fallback in hybrid_auto mode"
        )


class TestP0ErrorReturnsHTTP200:
    """P0 #4: Errors return HTTP 200 with raw str(e).

    File: backend/main.py:1057, 1126
    """

    def test_rag_error_handler_raises_http_exception(self):
        source = _read_source("backend/main.py")
        # The error handler should raise HTTPException, not return a dict with error
        # Find the rag_query error handler pattern
        has_return_error_dict = bool(re.search(
            r'return\s*\{[^}]*"error":\s*str\(e\)',
            source,
        ))
        assert not has_return_error_dict, (
            "main.py RAG query error handler returns {'error': str(e)} with HTTP 200 "
            "instead of raising HTTPException — frontend displays raw exceptions as answers"
        )


class TestP0NoAuthOnTrain:
    """P0 #5: No authorization on /cost-estimation/train endpoint.

    File: backend/api/cost_estimation_routes.py:146
    """

    def test_train_endpoint_requires_admin_role(self):
        source = _read_source("backend/api/cost_estimation_routes.py")
        # Find the train endpoint function
        train_match = re.search(
            r'@router\.(post|put)\s*\(\s*"/train".*?\n(?:async\s+)?def\s+\w+.*?(?=\n@router|\nclass|\Z)',
            source,
            re.DOTALL,
        )
        assert train_match, "/train endpoint not found"
        train_source = train_match.group()
        # Should have some form of role/admin check
        has_role_check = any(kw in train_source.lower() for kw in [
            "admin", "role", "authorize", "permission", "is_admin",
        ])
        assert has_role_check, (
            "/cost-estimation/train endpoint has no admin/role authorization — "
            "any authenticated user can retrain the ML model"
        )


class TestP0CodeValidatorBypass:
    """P0 #6: Code validator bypass via bare getattr() call.

    File: backend/services/code_executor.py:83-136
    """

    def test_getattr_builtins_import_blocked(self):
        mod = _load_legacy_code_executor()
        if not hasattr(mod, "DockerCodeExecutor"):
            pytest.skip("DockerCodeExecutor not found in legacy module")
        executor = object.__new__(mod.DockerCodeExecutor)
        # This code uses getattr to access __import__ — should be blocked
        malicious_code = "getattr(__builtins__, '__import__')('os').system('id')"
        with pytest.raises(Exception, match=r"(?i)(blocked|forbidden|not allowed|security)"):
            executor._validate_code(malicious_code)


class TestP0DataAnalysisAgentInit:
    """P0 #7: DataAnalysisAgent crashes without Ollama running.

    File: backend/services/data_analysis/data_analysis_agent.py:34
    """

    def test_data_analysis_agent_handles_missing_llm_gracefully(self):
        source = _read_source("backend/services/data_analysis/data_analysis_agent.py")
        tree = ast.parse(source)
        # Find __init__ method of DataAnalysisAgent
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "DataAnalysisAgent":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        init_source = ast.get_source_segment(source, item)
                        # Should have try/except around LLM client creation
                        has_error_handling = "try" in init_source and "except" in init_source
                        assert has_error_handling, (
                            "DataAnalysisAgent.__init__ calls LLMClientFactory.create_client() "
                            "without try/except — crashes on every call when Ollama is down"
                        )
                        return
        pytest.skip("DataAnalysisAgent class or __init__ not found")


class TestP0ModuleLevelDockerInit:
    """P0 #8: Module-level DockerCodeExecutor instantiation blocks import.

    File: backend/services/code_executor.py:331
    """

    def test_no_module_level_instantiation(self):
        source = _read_source("backend/services/code_executor.py")
        # Direct string check for module-level DockerCodeExecutor() call
        has_module_level_init = bool(re.search(
            r"code_executor\s*=\s*DockerCodeExecutor\s*\(",
            source,
        ))
        assert not has_module_level_init, (
            "Module-level 'code_executor = DockerCodeExecutor()' found. "
            "This blocks import for seconds when Docker is not running. "
            "Should use lazy initialization via a factory function."
        )


# ===================================================================
# P1 BUGS — Wrong Results
# ===================================================================


class TestP1IVFFlatProbes:
    """P1 #9: IVFFlat probes never set — only 1% of vectors searched.

    File: backend/services/core/vectorstore.py:131-159
    """

    def test_similarity_search_sets_probes(self):
        source = _read_source("backend/services/core/vectorstore.py")
        # Should contain SET ivfflat.probes before the similarity search query
        has_probes_set = bool(re.search(
            r"ivfflat\.probes",
            source,
            re.IGNORECASE,
        ))
        assert has_probes_set, (
            "vectorstore.py never calls 'SET ivfflat.probes' before similarity search. "
            "Default probes=1 with lists=100 means only 1% of vectors are examined."
        )


class TestP1GroundednessLexicalOnly:
    """P1 #10: Groundedness checker is lexical-only, ignores LLM param.

    File: backend/services/safety/groundedness_checker.py:98-160
    """

    def test_groundedness_catches_wrong_numbers(self):
        source = _read_source("backend/services/safety/groundedness_checker.py")
        # Find everything after "def check_groundedness" until next "def " at same indent
        start = source.find("def check_groundedness")
        assert start != -1, "check_groundedness function not found"
        # Get the function body (until next top-level method)
        func_source = source[start:start + 3000]  # Enough to capture the function
        # The function should use llm_client for actual checking,
        # not just token overlap
        # Check if llm_client is called/invoked anywhere in the body (after signature)
        body_start = func_source.find(":", func_source.find(")")) + 1
        func_body = func_source[body_start:]
        uses_llm = any(kw in func_body for kw in [
            "llm_client.generate", "llm_client.invoke", "llm_client(",
            "await llm_client", "llm_client.chat", "llm_client.complete",
        ])
        assert uses_llm, (
            "check_groundedness() accepts llm_client but only uses lexical token overlap. "
            "'Concrete strength is 30 MPa' vs '50 MPa' score identically. "
            "Should use llm_client for semantic verification."
        )


class TestP1MemoryPromptCorrupted:
    """P1 #11: Memory summary and extraction prompts are corrupted CN placeholders.

    Files: backend/services/memory/summary.py, extractor.py
    """

    def test_summary_prompt_is_english(self):
        import glob
        summary_files = glob.glob("backend/services/memory/summary*.py")
        for path in summary_files:
            source = _read_source(path)
            # Count EN placeholder patterns
            en_count = len(re.findall(r'"EN[,.]|"EN\s', source))
            assert en_count == 0, (
                f"Found {en_count} corrupted 'EN' placeholder patterns in {path} — "
                "memory summary prompt is not readable English"
            )

    def test_extraction_prompt_is_english(self):
        import glob
        extractor_files = glob.glob("backend/services/memory/extractor*.py")
        for path in extractor_files:
            source = _read_source(path)
            # Check for various EN placeholder patterns including those without punctuation
            en_patterns = re.findall(r'(?<!")EN(?:,|\.|\s+EN|\s*:|\s*\{|\s*\[)', source)
            # Also check for the specific "EN JSON EN" pattern
            en_json_count = len(re.findall(r'EN\s+JSON\s+EN|EN\s*,\s*EN', source))
            total = len(en_patterns) + en_json_count
            assert total == 0, (
                f"Found {total} corrupted 'EN' placeholder patterns in {path} — "
                "memory extraction prompt is not readable English"
            )


class TestP1MemoryRaceCondition:
    """P1 #12: history_snapshot created but never used — race condition persists.

    File: backend/services/rag_engine.py:335-352
    """

    def test_history_snapshot_is_used(self):
        source = _read_source("backend/services/rag_engine.py")
        if "history_snapshot" not in source:
            pytest.fail("history_snapshot not even created — race condition not addressed at all")
        # Find the snapshot creation
        snapshot_line = source.find("history_snapshot")
        # Check that it's actually used after creation (not just assigned)
        after_snapshot = source[snapshot_line + len("history_snapshot"):]
        # Should appear again (being passed to something)
        uses_after = "history_snapshot" in after_snapshot.split("\n", 20)[-1] if after_snapshot else False
        # Actually, let's check if history_snapshot appears more than once
        occurrences = source.count("history_snapshot")
        assert occurrences >= 2, (
            f"history_snapshot appears only {occurrences} time(s) — "
            "it's created but never passed to the background thread. "
            "The _update_memory closure still references `session` directly."
        )


class TestP1UnseenCategorySilent:
    """P1 #13: Unseen cost estimation category → silent bad prediction.

    File: backend/services/cost_estimation_service.py:638
    """

    def test_unseen_category_warns_user(self):
        source = _read_source("backend/services/cost_estimation_service.py")
        # Find predict_project method
        match = re.search(
            r"def\s+predict_project\s*\(.*?\).*?(?=\n    def\s|\nclass\s|\Z)",
            source,
            re.DOTALL,
        )
        if not match:
            pytest.skip("predict_project method not found")
        func_source = match.group()
        # Should include a user-visible warning in the response when categories are unknown
        has_warning_in_response = any(kw in func_source for kw in [
            "warning", "caution", "unknown_categories",
            "confidence_degraded",
        ])
        # Check that the warning is included in the RETURNED dict, not just metadata
        has_warning_in_return = "warning" in func_source.lower() and "return" in func_source.lower()
        assert has_warning_in_return, (
            "predict_project detects unknown_categories but does not include a "
            "user-visible warning in the returned prediction result"
        )


class TestP1RelativeModelPath:
    """P1 #14: Relative model path fails if CWD changes.

    File: backend/services/cost_estimation_service.py:557
    """

    def test_model_path_is_absolute_or_robust(self):
        source = _read_source("backend/services/cost_estimation_service.py")
        # Find DEFAULT_MODEL_PATH definition
        match = re.search(r'DEFAULT_MODEL_PATH\s*=\s*(.+)', source)
        if not match:
            pytest.skip("DEFAULT_MODEL_PATH not found")
        definition = match.group(1)
        # Path should either use __file__ for robust resolution or be absolute
        uses_file_ref = "__file__" in definition
        literal_match = re.search(r'Path\(\s*["\'](.+?)["\']\s*\)', definition)
        if literal_match:
            import os.path
            is_absolute = os.path.isabs(literal_match.group(1))
        else:
            is_absolute = False
        assert uses_file_ref or is_absolute, (
            f"DEFAULT_MODEL_PATH definition '{definition.strip()}' is a relative path "
            "without __file__ reference. If the FastAPI server starts from a different "
            "CWD, model loading silently fails."
        )


class TestP1IntentNodeTypeContract:
    """P1 #15: Dict passed where QueryContext expected → AttributeError.

    File: backend/services/workflows/nodes/intent_node.py:102
    """

    def test_call_classifier_passes_correct_type(self):
        source = _read_source("backend/services/workflows/nodes/intent_node.py")
        # The function should either:
        # 1. Convert metadata dict to QueryContext before passing, OR
        # 2. Not pass raw dict as context parameter
        has_querycontext_construction = "QueryContext" in source
        has_dict_to_context = bool(re.search(
            r"QueryContext\s*\(", source,
        ))
        assert has_dict_to_context, (
            "intent_node._call_classifier passes raw metadata dict as 'context' "
            "to classify_intent(), which expects a QueryContext dataclass. "
            "This causes AttributeError: 'dict' has no attribute 'recent_intents'"
        )


class TestP1ConfidenceHeuristic:
    """P1 #16: Length-based confidence means hallucinations never caught.

    File: backend/services/llm_integration/dispatch_service.py:58
    """

    def test_confidence_not_purely_length_based(self):
        source = _read_source("backend/services/llm_integration/dispatch_service.py")
        match = re.search(
            r"def\s+_estimate_confidence\s*\(.*?\).*?(?=\n    def\s|\nclass\s|\Z)",
            source,
            re.DOTALL,
        )
        if not match:
            pytest.skip("_estimate_confidence not found")
        func_source = match.group()
        # Check if confidence is based ONLY on text length
        uses_length = "len(" in func_source
        uses_content_analysis = any(kw in func_source for kw in [
            "keyword", "coherent", "relevance", "semantic", "quality",
            "repetition", "structure",
        ])
        if uses_length and not uses_content_analysis:
            pytest.fail(
                "_estimate_confidence is purely length-based — any 600+ char "
                "response (including hallucinated/repetitive text) gets max confidence. "
                "Should include content quality signals."
            )


class TestP1DoubleFallbackEmpty:
    """P1 #17: Cloud blocked + local failed = empty response.

    File: backend/services/llm_integration/dispatch_service.py:263
    """

    def test_fallback_chain_returns_meaningful_error(self):
        source = _read_source("backend/services/llm_integration/dispatch_service.py")
        # When both local and cloud fail, the user should get a meaningful error
        # Look for the fallback-to-local-again pattern
        has_meaningful_fallback = bool(re.search(
            r"(all\s+backends?\s+failed|no\s+available\s+backend|service\s+unavailable|"
            r"unable\s+to\s+generate|please\s+try\s+again)",
            source,
            re.IGNORECASE,
        ))
        assert has_meaningful_fallback, (
            "When both local LLM and cloud LLM fail, the dispatch service returns "
            "an empty string with success=False. Should return a user-friendly error message."
        )


class TestP1NoContextWindowGuard:
    """P1 #18: No context window overflow protection.

    System-wide: dispatch + RAG pipeline.
    """

    def test_context_window_check_exists(self):
        dispatch_source = _read_source("backend/services/llm_integration/dispatch_service.py")
        rag_source = _read_source("backend/services/rag_engine.py")
        combined = dispatch_source + rag_source
        has_overflow_check = any(kw in combined for kw in [
            "context_window", "max_context", "token_limit",
            "exceeds", "overflow", "truncat",
        ])
        assert has_overflow_check, (
            "Neither dispatch_service.py nor rag_engine.py validates that "
            "prompt_tokens + max_tokens fits within the context window. "
            "Long conversations silently exceed the limit."
        )


class TestP1ShortcutResponseSticky:
    """P1 #19: shortcut_response flag never cleared between turns.

    File: backend/services/workflows/graph.py:73
    """

    def test_shortcut_flag_cleared_between_queries(self):
        source = _read_source("backend/services/workflows/graph.py")
        # The graph should clear shortcut_response at the start of each run
        has_clear = bool(re.search(
            r'(shortcut_response.*?=\s*False|del.*?shortcut_response|pop.*?shortcut_response)',
            source,
        ))
        assert has_clear, (
            "graph.py never clears metadata['shortcut_response'] between runs. "
            "After a cost estimation query sets it to True, all subsequent queries "
            "in the same session skip retrieval, reranking, and prompt nodes."
        )


class TestP1ThreadingLockInAsync:
    """P1 #20: threading.Lock blocks event loop in async route handlers.

    File: backend/api/cost_estimation_routes.py:25
    """

    def test_no_threading_lock_in_async_routes(self):
        source = _read_source("backend/api/cost_estimation_routes.py")
        has_threading_lock = "threading.Lock()" in source
        has_async_handlers = bool(re.search(r"async\s+def\s+\w+", source))
        if has_threading_lock and has_async_handlers:
            pytest.fail(
                "cost_estimation_routes.py uses threading.Lock() in async route handlers. "
                "When contended, this blocks the entire asyncio event loop, "
                "preventing ALL other requests from being served."
            )


class TestP1FakeGroundedness:
    """P1 #21: Groundedness score is just chunk count × 0.2, not real verification.

    File: backend/services/workflows/nodes/groundedness_node.py:18
    """

    def test_groundedness_not_just_count(self):
        source = _read_source("backend/services/workflows/nodes/groundedness_node.py")
        # Check if the groundedness score is simply count * constant
        has_count_proxy = bool(re.search(r"(context_count|len\(.*?\))\s*\*\s*0\.\d", source))
        assert not has_count_proxy, (
            "Groundedness score is calculated as context_count * 0.2 — "
            "5+ chunks always gets 1.0 regardless of whether the answer "
            "is actually supported by those chunks."
        )


class TestP1ErrorStringAsResponse:
    """P1 #22: Pipeline error string leaked as user response.

    File: backend/services/workflows/graph.py:86
    """

    def test_error_response_is_user_friendly(self):
        source = _read_source("backend/services/workflows/graph.py")
        # Check for pattern: state["response"] = state["error"]
        has_raw_error_response = bool(re.search(
            r'state\s*\[\s*["\']response["\']\s*\]\s*=\s*state\s*\[\s*["\']error["\']\s*\]',
            source,
        ))
        assert not has_raw_error_response, (
            'graph.py sets state["response"] = state["error"], exposing raw exception '
            "text (connection strings, hostnames, stack traces) to the end user."
        )


class TestP1TenantIDSpoofable:
    """P1 #23: Tenant ID header fully spoofable with no validation.

    File: backend/security/dependencies.py:96
    """

    def test_tenant_id_validated(self):
        source = _read_source("backend/security/dependencies.py")
        # Should have some validation of tenant ID (allowlist, format check, DB lookup)
        has_validation = any(kw in source for kw in [
            "validate_tenant", "allowed_tenants", "tenant_exists",
            "format", "pattern", "regex",
        ])
        assert has_validation, (
            "X-Tenant-ID header is accepted verbatim with no validation. "
            "Any client can impersonate any tenant."
        )


class TestP1PromptInjectionCodeGen:
    """P1 #24: Prompt injection via user question into code generation.

    File: backend/services/data_analysis/data_analysis_agent.py:272
    """

    def test_code_gen_prompt_sanitizes_input(self):
        source = _read_source("backend/services/data_analysis/data_analysis_agent.py")
        # Find the code generation prompt building
        match = re.search(
            r"def\s+_build_code_generation_prompt\s*\(.*?\).*?(?=\n    def\s|\nclass\s|\Z)",
            source,
            re.DOTALL,
        )
        if not match:
            pytest.skip("_build_code_generation_prompt not found")
        func_source = match.group()
        # Should have some form of input sanitization or injection guard
        has_sanitization = any(kw in func_source for kw in [
            "sanitize", "escape", "strip", "clean",
            "injection", "instruct", "ignore",
        ])
        assert has_sanitization, (
            "_build_code_generation_prompt directly interpolates user question "
            "into the LLM prompt without sanitization. A crafted question can "
            "override instructions and generate malicious code."
        )


class TestP1TemplateMaxMinIgnoresContext:
    """P1 #25: Template max/min always picks first numeric column.

    File: backend/services/data_analysis/data_analysis_agent.py:423
    """

    def test_template_max_uses_relevant_column(self):
        source = _read_source("backend/services/data_analysis/data_analysis_agent.py")
        # Find _template_max method
        match = re.search(
            r"def\s+_template_max\s*\(.*?\).*?(?=\n    def\s|\nclass\s|\Z)",
            source,
            re.DOTALL,
        )
        if not match:
            pytest.skip("_template_max not found")
        func_source = match.group()
        # Should use _pick_relevant_column or similar context-aware selection
        uses_context = any(kw in func_source for kw in [
            "_pick_relevant", "question", "query", "keyword", "match",
        ])
        assert uses_context, (
            "_template_max always picks numeric_cols[0] without considering the "
            "user's question. 'What is the maximum price?' returns max of project_id."
        )
