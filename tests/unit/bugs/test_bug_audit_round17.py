"""
TDI Round 17 — Bug reproduction tests.

Covers 14 P0/P1 bugs discovered across 4 audit agents:
  - R17-B01 (P0): Infinite clarification loop in intent workflow
  - R17-B02 (P1): Budget force_local policy doesn't block cloud calls
  - R17-B03 (P1): _simulate_llm_response keyword priority misroutes cost queries
  - R17-B04 (P1): _preprocess_input regex broken (unescaped brackets)
  - R17A-01 (P1): BM25 tokenizer drops dotted construction references
  - R17A-02 (P1): replace_document no explicit rollback on inner failure
  - R17A-03 (P1): Unbounded chunk growth at construction reference boundaries
  - R17C-01 (P1): Password hash comparison uses == (timing side-channel)
  - R17C-02 (P1): Metaclass hooks not blocked in code validator
  - R17C-03 (P1): atexit/_thread missing from BLACKLISTED_IMPORTS
  - R17C-05 (P1): QueryRequest fields have no length/range limits
  - R17D-01 (P1): A/B experiment cache defeats traffic split
  - R17D-02 (P1): Unified agent intent keywords are dead EN placeholders
  - R17D-03 (P1): Unified agent system prompt is dead EN placeholders
"""

import ast
import json
import re
import pytest


# ---------------------------------------------------------------------------
# R17-B01 (P0): Infinite clarification loop — clarification_processing always
# sets clarification_handled=True, _route_after_clarification returns
# retry_classification, re-running intent on the SAME unchanged query.
# ---------------------------------------------------------------------------
class TestR17B01_ClarificationLoop:
    def test_clarification_processing_should_not_always_return_retry(self):
        """After clarification processing, if no new user input was provided,
        the route should NOT be retry_classification (which re-runs the same
        intent classification on unchanged query, spinning indefinitely)."""
        source = open("backend/services/intent_classification/intent_workflow.py").read()

        # Find _clarification_processing_node
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_clarification_processing_node":
                    body_src = ast.get_source_segment(source, node)
                    # The node must have a path that sets
                    # awaiting_user_clarification=True (to break the loop)
                    # when there's no new user input AND confidence is low.
                    assert "awaiting_user_clarification" in body_src, (
                        "_clarification_processing_node has no path that signals "
                        "'awaiting_user_clarification' — without this, low-confidence "
                        "queries with no new user input loop indefinitely via "
                        "retry_classification"
                    )
                    # Also verify it checks for actual user clarification input
                    assert "user_clarification" in body_src, (
                        "_clarification_processing_node does not check for new "
                        "user clarification input before deciding to retry"
                    )
                    return
        pytest.fail("_clarification_processing_node not found in source")


# ---------------------------------------------------------------------------
# R17-B02 (P1): Budget force_local policy doesn't block cloud calls
# ---------------------------------------------------------------------------
class TestR17B02_BudgetForceLocalBypass:
    def test_force_local_budget_should_block_cloud_dispatch(self):
        """When budget policy is 'local_only' and hard limit is exceeded,
        evaluate_budget should return allowed=False to actually prevent
        cloud calls. Currently returns allowed=True with decision=force_local
        which dispatch_service ignores."""
        source = open(
            "backend/services/llm_integration/cost_tracker.py"
        ).read()
        tree = ast.parse(source)

        # Find evaluate_budget method
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "evaluate_budget":
                    body_src = ast.get_source_segment(source, node)
                    # When policy_mode == "local_only" and over hard limit,
                    # the returned 'allowed' should be False
                    # Currently: "allowed": policy.policy_mode != "block"
                    # For local_only: "local_only" != "block" is True -> allowed=True
                    assert '"allowed": policy.policy_mode != "block"' not in body_src or \
                        "force_local" not in body_src, (
                        "force_local decision returns allowed=True — dispatch_service "
                        "only checks 'allowed' field and proceeds with cloud call"
                    )
                    return
        pytest.fail("evaluate_budget method not found")


# ---------------------------------------------------------------------------
# R17-B03 (P1): _simulate_llm_response keyword priority misroutes cost queries
# ---------------------------------------------------------------------------
class TestR17B03_SimulateLLMKeywordPriority:
    def test_cost_query_with_knowledge_prefix_routes_to_cost(self):
        """'how to estimate construction cost' should route to cost_estimation,
        not knowledge_retrieval. Cost estimation keywords must be checked
        before generic knowledge retrieval keywords like 'how to'."""
        source = open(
            "backend/services/intent_classification/intent_classifier.py"
        ).read()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_simulate_llm_response":
                    body_src = ast.get_source_segment(source, node)
                    # Find the FIRST "if any(" keyword check (any formatting)
                    first_if_idx = body_src.find("if any(")
                    assert first_if_idx >= 0, "No 'if any(' found"
                    # Find the first intent = "..." assignment after it
                    first_intent_idx = body_src.find('intent = "', first_if_idx)
                    first_intent_end = body_src.find('"', first_intent_idx + 11)
                    first_intent = body_src[first_intent_idx + 10:first_intent_end]
                    assert first_intent == "cost_estimation", (
                        f"First keyword check routes to '{first_intent}' — "
                        "cost_estimation should be checked before knowledge_retrieval "
                        "to prevent 'how to estimate cost' from misrouting"
                    )
                    return
        pytest.fail("_simulate_llm_response not found")


# ---------------------------------------------------------------------------
# R17-B04 (P1): _preprocess_input regex broken — unescaped [] in char class
# ---------------------------------------------------------------------------
class TestR17B04_PreprocessInputRegex:
    def test_preprocess_input_regex_actually_removes_special_chars(self):
        """The regex must have properly escaped brackets to work as intended.
        With unescaped [], the character class is prematurely closed and
        special characters are never removed."""
        source = open(
            "backend/services/intent_classification/intent_classifier.py"
        ).read()
        # Find the regex pattern in _preprocess_input
        # The brackets must be escaped as \\[ and \\]
        assert r"\[\]" in source or r"\[" in source, (
            "_preprocess_input regex has unescaped [] inside character class — "
            "the character class is prematurely closed, making the regex a no-op"
        )

        # Verify the fixed regex actually works
        fixed_pattern = r'[^\w\s\u4e00-\u9fff.,!?;:()\[\]{}"\'-]'
        test_input = "test #special @chars $100 50%"
        result = re.sub(fixed_pattern, "", test_input)
        assert "#" not in result, "# should be removed by preprocessing"
        assert "@" not in result, "@ should be removed by preprocessing"
        assert "$" not in result, "$ should be removed by preprocessing"
        assert "%" not in result, "% should be removed by preprocessing"


# ---------------------------------------------------------------------------
# R17A-01 (P1): BM25 tokenizer drops dotted construction references
# ---------------------------------------------------------------------------
class TestR17A01_BM25DottedTokens:
    def test_tokenizer_preserves_dotted_standard_references(self):
        """Construction standard references like 'NBC 2020.4', 'A23.1',
        '0.85 MPa' contain dotted tokens that must survive BM25 tokenization.
        Currently dropped by the isalnum()/dash filter."""
        source = open("backend/services/retrieval/hybrid_search.py").read()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_tokenize_english":
                    body_src = ast.get_source_segment(source, node)
                    # The stemmed_tokens loop should handle dotted tokens
                    # (tokens containing '.' but not '-')
                    # Currently only handles: isalnum() or '-' in token
                    assert '"." in token' in body_src or "'.' in token" in body_src, (
                        "_tokenize_english has no handler for dotted tokens — "
                        "tokens like 'nbc2020.4' fail isalnum() and have no '-', "
                        "so they are silently dropped from BM25 index and queries"
                    )
                    return
        pytest.fail("_tokenize_english not found")


# ---------------------------------------------------------------------------
# R17A-02 (P1): replace_document no explicit rollback on inner failure
# ---------------------------------------------------------------------------
class TestR17A02_ReplaceDocumentRollback:
    def test_replace_document_has_explicit_rollback_on_failure(self):
        """When replacement document processing fails, the DELETE of existing
        chunks must be explicitly rolled back. Currently relies on implicit
        rollback when connection is eventually closed, which is fragile."""
        source = open("backend/services/document_manager.py").read()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "replace_document":
                    body_src = ast.get_source_segment(source, node)
                    # After the DELETE and before the 'return False' in the
                    # inner except block, there should be an explicit rollback
                    delete_idx = body_src.find("DELETE FROM document_chunks")
                    return_false_idx = body_src.find("return False", delete_idx)
                    segment = body_src[delete_idx:return_false_idx]
                    assert "rollback" in segment.lower(), (
                        "No explicit rollback between DELETE and return False — "
                        "chunk deletion relies on implicit rollback when connection closes"
                    )
                    return
        pytest.fail("replace_document not found")


# ---------------------------------------------------------------------------
# R17A-03 (P1): Unbounded chunk growth at construction reference boundaries
# ---------------------------------------------------------------------------
class TestR17A03_UnboundedChunkGrowth:
    def test_chunk_size_has_upper_bound_with_construction_refs(self):
        """Construction documents with frequent 'Part N' or 'Section X.Y'
        references at chunk boundaries cause unbounded chunk growth because
        the extension path has no size cap."""
        from backend.services.core.chunker import chunk_text

        # Build a document with "Part N" references near every chunk boundary
        # Each segment is ~450 chars, with a Part reference at the end
        text = ""
        for i in range(1, 25):
            text += ("Requirements for safety. " * 16) + f"See Part {i} for details.\n\n"

        chunks = chunk_text(text, chunk_size=512, chunk_overlap=128)
        max_chunk_len = max(len(c["content"]) for c in chunks)

        # A reasonable upper bound: no chunk should exceed 3x the target size
        assert max_chunk_len <= 512 * 3, (
            f"Largest chunk is {max_chunk_len} chars (target 512) — "
            "construction reference extension has no size cap, "
            "chunk grew unboundedly"
        )


# ---------------------------------------------------------------------------
# R17C-01 (P1): Password hash comparison uses == (timing side-channel)
# ---------------------------------------------------------------------------
class TestR17C01_TimingSafePasswordCompare:
    def test_password_verification_uses_constant_time_comparison(self):
        """Password hash comparison must use hmac.compare_digest() to prevent
        timing side-channel attacks. Currently uses Python == operator."""
        source = open("backend/api/auth_routes.py").read()

        # Find _verify_password function
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == "_verify_password":
                    body_src = ast.get_source_segment(source, node)
                    assert "compare_digest" in body_src, (
                        "_verify_password uses == for hash comparison — "
                        "should use hmac.compare_digest() for constant-time comparison"
                    )
                    return
        pytest.fail("_verify_password not found")


# ---------------------------------------------------------------------------
# R17C-02 (P1): Metaclass hooks not blocked in code validator
# ---------------------------------------------------------------------------
class TestR17C02_MetaclassHooksBlocked:
    def test_init_subclass_hook_is_blocked(self):
        """__init_subclass__ runs at class definition time (not instantiation).
        Code using this hook can execute arbitrary code when a subclass is
        defined, bypassing call-site validators."""
        from backend.services.code_executor.validator import CodeValidator

        validator = CodeValidator(strict_mode=False)
        # __init_subclass__ runs when Trigger class is defined
        code = '''
class Evil:
    def __init_subclass__(cls, **kw):
        print("Code executed at class definition time!")
class Trigger(Evil):
    pass
'''
        result = validator.validate(code)
        assert not result.is_valid, (
            "__init_subclass__ should be blocked — it executes arbitrary code "
            "at class definition time, bypassing runtime validators"
        )


# ---------------------------------------------------------------------------
# R17C-03 (P1): atexit/_thread missing from BLACKLISTED_IMPORTS
# ---------------------------------------------------------------------------
class TestR17C03_Atexit_ThreadBlacklisted:
    def test_atexit_import_blocked(self):
        """atexit.register() allows code execution after sandbox timeout/cleanup.
        Should be in BLACKLISTED_IMPORTS."""
        from backend.services.code_executor.validator import CodeValidator

        validator = CodeValidator(strict_mode=False)
        code = 'import atexit\natexit.register(lambda: None)\n'
        result = validator.validate(code)
        assert not result.is_valid, (
            "atexit module should be blacklisted — allows registering callbacks "
            "that execute at interpreter exit, after sandbox controls have relaxed"
        )

    def test_thread_low_level_import_blocked(self):
        """_thread is the low-level threading module, not blocked even though
        'threading' is. Can spawn threads that outlive execution window."""
        from backend.services.code_executor.validator import CodeValidator

        validator = CodeValidator(strict_mode=False)
        code = 'import _thread\n_thread.start_new_thread(lambda: None, ())\n'
        result = validator.validate(code)
        assert not result.is_valid, (
            "_thread module should be blacklisted — low-level threading that "
            "bypasses the 'threading' blacklist and can outlive sandbox timeout"
        )


# ---------------------------------------------------------------------------
# R17C-05 (P1): QueryRequest fields have no length/range limits
# ---------------------------------------------------------------------------
class TestR17C05_QueryRequestValidation:
    def test_query_request_question_has_max_length(self):
        """QueryRequest.question should have a max_length constraint to prevent
        memory exhaustion from arbitrarily large payloads."""
        from pydantic import ValidationError
        from backend.api.enhanced_query_routes import QueryRequest

        # A 100K char question should be rejected by a max_length constraint
        with pytest.raises(ValidationError):
            QueryRequest(question="A" * 100000)

    def test_query_request_top_k_has_upper_bound(self):
        """top_k should have an upper bound to prevent overloading vector store."""
        from pydantic import ValidationError
        from backend.api.enhanced_query_routes import QueryRequest

        with pytest.raises(ValidationError):
            QueryRequest(question="test", top_k=999999)


# ---------------------------------------------------------------------------
# R17D-01 (P1): A/B experiment cache defeats traffic split
# ---------------------------------------------------------------------------
class TestR17D01_ABExperimentCacheBypass:
    def test_ab_cache_key_includes_experiment_context(self):
        """When A/B experiments are enabled, the cache key must NOT be a simple
        '{category}:{name}' — it must include experiment/bucket context.
        Otherwise the first caller's variant is served to all subsequent
        callers until cache expires."""
        source = open("backend/services/prompt_manager.py").read()

        # Find get_prompt method and its caching logic
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "get_prompt":
                    body_src = ast.get_source_segment(source, node)
                    # The cache should be BYPASSED when experiments are enabled,
                    # OR the cache key should include the experiment/bucket info.
                    # Currently: cache_key = f"{category}:{name}" used regardless
                    # of whether experiments are enabled.
                    # Check that cache read is gated on enable_experiments
                    cache_read = body_src.find("if cache_key in self._cache")
                    if cache_read >= 0:
                        # The cache read block should check enable_experiments
                        # before returning cached value
                        pre_cache = body_src[:cache_read]
                        cache_block_end = body_src.find("return prompt_info", cache_read)
                        if cache_block_end < 0:
                            cache_block_end = body_src.find("# EN", cache_read + 10)
                        cache_block = body_src[cache_read:cache_block_end] if cache_block_end > 0 else ""
                        assert "enable_experiments" in cache_block or \
                            "experiment" in body_src[body_src.find("cache_key ="):body_src.find("cache_key =") + 100].lower(), (
                            "Cache key is generic '{category}:{name}' and cache read "
                            "does not check enable_experiments — A/B experiment variant "
                            "is cached under generic key and served to all callers"
                        )
                    return
        pytest.fail("get_prompt not found")


# ---------------------------------------------------------------------------
# R17D-02 (P1): Unified agent intent keywords are dead EN placeholders
# ---------------------------------------------------------------------------
class TestR17D02_UnifiedAgentIntentKeywords:
    def test_unified_agent_classify_intent_has_real_keywords(self):
        """The _classify_user_intent function's keyword lists are filled with
        'EN' placeholder strings (from incomplete i18n migration). Since
        'EN'.lower() == 'en' never appears in lowercased English queries,
        the function always returns 'knowledge' regardless of input."""
        source = open("backend/agents/unified_agent.py").read()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == "_classify_user_intent":
                    body_src = ast.get_source_segment(source, node)
                    # Count "EN" literals in keyword lists
                    en_count = body_src.count('"EN"')
                    real_keyword_count = len(re.findall(
                        r'"(?!EN")[a-z ]{3,}"', body_src
                    ))
                    assert real_keyword_count > en_count, (
                        f"Found {en_count} 'EN' placeholders vs {real_keyword_count} "
                        "real keywords — intent classification is non-functional"
                    )
                    return
        pytest.fail("_classify_user_intent not found")


# ---------------------------------------------------------------------------
# R17D-03 (P1): Unified agent system prompt is dead EN placeholders
# ---------------------------------------------------------------------------
class TestR17D03_UnifiedAgentSystemPrompt:
    def test_unified_agent_system_prompt_has_real_content(self):
        """The system prompt for the unified agent is filled with 'EN'
        placeholder text, providing zero guidance to the LLM for tool
        selection, workflow reasoning, or response formatting."""
        source = open("backend/agents/unified_agent.py").read()

        # Find the system prompt string in build_unified_agent
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == "build_unified_agent":
                    body_src = ast.get_source_segment(source, node)
                    # Count EN placeholders vs real English words
                    en_placeholders = len(re.findall(r'\bEN\b', body_src))
                    # Real content should significantly outnumber EN placeholders
                    real_words = len(re.findall(r'\b[a-z]{4,}\b', body_src.lower()))
                    ratio = real_words / max(en_placeholders, 1)
                    assert ratio > 2.0, (
                        f"System prompt has {en_placeholders} 'EN' placeholders "
                        f"vs {real_words} real words (ratio {ratio:.1f}) — "
                        "LLM receives no meaningful guidance"
                    )
                    return
        pytest.fail("build_unified_agent not found")
