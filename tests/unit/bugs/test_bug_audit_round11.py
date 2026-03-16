"""TDI Round 11 audit findings — reproduction tests.

Covers 13 P1 bugs found by parallel audit agents.

P1:
- R11-01: summary.py build_summary prompt is "EN" placeholder gibberish
- R11-02: extractor.py EXTRACTION_PROMPT is "EN" placeholder gibberish
- R11-03: groundedness_checker.py safety disclaimers/refusals are "EN" gibberish
- R11-04: cost_estimation_service.py regex \\s in capture group causes 500 trillion
- R11-05: routing_decision.py maps cost_estimation to DATA_ANALYSIS_AGENT
- R11-06: prompt_routes.py missing secure_endpoint dependency
- R11-07: feedback_routes.py missing secure_endpoint dependency
- R11-08: intent_classification_routes.py missing secure_endpoint dependency
- R11-09: cost_estimation_routes.py missing secure_endpoint dependency
- R11-10: validator.py exec bypass via list/dict/tuple indirection
- R11-11: data_analysis_agent.py NaN from all-NaN columns breaks JSON
- R11-12: workflow_query_routes.py _RAGRetrieverAdapter.retrieve blocks event loop
- R11-13: workflow_query_routes.py _DispatchResponseBuilder.__call__ blocks event loop
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# R11-01 (P1): summary.py build_summary prompt is "EN" placeholder gibberish
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR11_01_SummaryPromptENPlaceholders:
    """summary.py build_summary() prompt is entirely 'EN' placeholder text.
    The LLM receives gibberish like 'EN,EN200EN.' instead of real English
    instructions, making conversation summarization useless.
    """

    def test_summary_prompt_has_real_english_instructions(self):
        source = Path("backend/services/memory/summary.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "build_summary":
                func_source = ast.get_source_segment(source, node) or ""
                # Extract the f-string prompt — it starts after prompt = f"""
                prompt_start = func_source.find('prompt = f"""')
                prompt_end = (
                    func_source.find('"""', prompt_start + 12)
                    if prompt_start >= 0
                    else -1
                )
                if prompt_start < 0 or prompt_end < 0:
                    pytest.fail("Could not find prompt f-string in build_summary")
                prompt_text = func_source[prompt_start:prompt_end]
                # The prompt template (excluding variable interpolations) should
                # contain real English instruction words, not just "EN" placeholders
                # Strip out f-string interpolation parts
                stripped = re.sub(r"\{[^}]+\}", "", prompt_text)
                has_real_instructions = any(
                    word in stripped.lower()
                    for word in (
                        "summarize",
                        "conversation",
                        "update the summary",
                        "existing summary",
                        "new interactions",
                        "summary of",
                    )
                )
                assert has_real_instructions, (
                    "R11-01: build_summary prompt uses EN placeholder text instead "
                    "of real English instructions. LLM cannot generate useful summaries."
                )
                return
        pytest.fail("Could not find build_summary method")

    def test_summary_interaction_labels_not_en(self):
        source = Path("backend/services/memory/summary.py").read_text()
        # interaction_text should label dialogue as "User:" / "Assistant:",
        # not as "EN:" / "EN:"
        assert '"EN: "' not in source or "'EN: '" not in source, (
            "R11-01: Interaction labels in summary.py use 'EN:' instead of "
            "'User:'/'Assistant:'. LLM cannot identify speaker turns."
        )
        # Positive check: should have User/Assistant labels
        assert (
            "User:" in source or "user:" in source.lower()
        ), "R11-01: summary.py interaction formatting lacks 'User:' label"

    def test_summary_default_language_is_english(self):
        source = Path("backend/services/memory/summary.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "build_summary":
                for arg in node.args.defaults:
                    if isinstance(arg, ast.Constant) and arg.value == "zh":
                        pytest.fail(
                            "R11-01: build_summary default language='zh'. "
                            "All docs are English, should be 'en'."
                        )
                return
        pytest.fail("Could not find build_summary method")


# ---------------------------------------------------------------------------
# R11-02 (P1): extractor.py EXTRACTION_PROMPT is "EN" placeholder gibberish
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR11_02_ExtractorPromptENPlaceholders:
    """EXTRACTION_PROMPT in extractor.py is entirely 'EN' placeholder text.
    The LLM receives gibberish, making structured memory extraction useless.
    """

    def test_extraction_prompt_has_real_english(self):
        source = Path("backend/services/memory/extractor.py").read_text()
        # Find the EXTRACTION_PROMPT string
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "EXTRACTION_PROMPT"
                    ):
                        if isinstance(node.value, ast.Constant):
                            prompt_text = str(node.value.value)
                            # The prompt should have real English sentences, not
                            # "EN.EN,EN,EN JSON EN,EN:" gibberish.
                            # Real prompts contain verbs like "extract", "analyze"
                            # in proper sentences (at least 3+ words together).
                            # Check that the non-placeholder text forms real sentences
                            # by ensuring common instruction words appear outside
                            # of the placeholder pattern "EN"
                            stripped = prompt_text.replace("EN", "").strip()
                            # After removing all "EN" tokens, real English should remain
                            real_words = re.findall(r"[a-zA-Z]{4,}", stripped)
                            assert len(real_words) >= 10, (
                                f"R11-02: EXTRACTION_PROMPT has only {len(real_words)} "
                                "real English words after removing 'EN' placeholders. "
                                "LLM cannot extract structured memories from gibberish."
                            )
                            return
        pytest.fail("Could not find EXTRACTION_PROMPT assignment")

    def test_extractor_dialogue_labels_not_en(self):
        source = Path("backend/services/memory/extractor.py").read_text()
        # Dialogue formatting should use "User:" / "Assistant:", not "EN:"
        assert 'f"EN: {' not in source, (
            "R11-02: Dialogue formatting in extractor.py uses 'EN:' labels "
            "instead of 'User:'/'Assistant:'"
        )


# ---------------------------------------------------------------------------
# R11-03 (P1): groundedness_checker.py disclaimers/refusals are "EN" gibberish
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR11_03_GroundednessENDisclaimers:
    """Safety disclaimers and refusal messages in groundedness_checker.py
    are "EN" placeholder text shown directly to users.
    """

    def test_safety_disclaimers_are_real_english(self):
        source = Path("backend/services/safety/groundedness_checker.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "add_disclaimer":
                func_source = ast.get_source_segment(source, node) or ""
                # The SAFETY_CRITICAL disclaimer should contain real warning text
                # like "warning", "professional", "consult", "verify", etc.
                # not "ENAIEN,EN." gibberish
                # Extract the disclaimers dict section
                disclaimers_start = func_source.find("disclaimers")
                disclaimers_section = (
                    func_source[disclaimers_start:] if disclaimers_start >= 0 else ""
                )
                # Check that disclaimer text has real English words
                # (excluding variable names / code structure)
                string_literals = re.findall(r'"([^"]*)"', disclaimers_section)
                all_text = " ".join(string_literals)
                real_words = re.findall(r"[a-zA-Z]{4,}", all_text.replace("EN", ""))
                assert len(real_words) >= 5, (
                    f"R11-03: Safety disclaimers have only {len(real_words)} real "
                    "English words after removing 'EN' placeholders. "
                    "Users see nonsensical safety warnings."
                )
                return
        pytest.fail("Could not find add_disclaimer method")

    def test_refusal_messages_are_real_english(self):
        source = Path("backend/services/safety/groundedness_checker.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "should_refuse_to_answer"
            ):
                func_source = ast.get_source_segment(source, node) or ""
                # The refusal messages should contain real English
                # Check that we don't have "EN,EN." patterns as user-facing text
                en_gibberish = re.findall(r'"EN,EN[.!?]?"', func_source)
                assert not en_gibberish, (
                    f"R11-03: Refusal messages contain EN gibberish: {en_gibberish}. "
                    "Users see nonsensical refusal responses."
                )
                return
        pytest.fail("Could not find should_refuse_to_answer method")


# ---------------------------------------------------------------------------
# R11-04 (P1): cost_estimation_service.py regex \s in capture group
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR11_04_CostRegexWhitespaceInCapture:
    r"""Regex patterns for estimated_cost_cad and other numeric fields
    include \s in the capture group: ([0-9][0-9,.\s]*[kmb]?)
    This causes "budget 500000 budget pressure" to capture "500000 b"
    (the space + 'b' from 'budget') and interpret it as 500 billion.
    """

    def test_estimated_cost_no_whitespace_in_capture_group(self):
        source = Path("backend/services/cost_estimation_service.py").read_text()
        # Find all regex patterns in the _NUMERIC_PATTERNS dict that have
        # \s inside a capture group alongside [kmb] suffix
        # Pattern: ([0-9][0-9,.\s]*[kmb]?) — the \s allows whitespace inside
        # the captured value, so "500000 b" from "budget" matches as 500B
        matches = re.findall(r'r"[^"]*\([^)]*\\s[^)]*\[kmb\][^)]*\)[^"]*"', source)
        assert not matches, (
            r"R11-04: Found regex capture group(s) with \s before [kmb] suffix: "
            f"{matches}. 'budget 500000 budget pressure' captures '500000 b' as 500 billion."
        )

    def test_numeric_patterns_no_whitespace_with_kmb_suffix(self):
        source = Path("backend/services/cost_estimation_service.py").read_text()
        # Capture groups that have BOTH \s AND [kmb] suffix are dangerous:
        # "500000 b" from "budget" would match as 500 billion.
        # Patterns with \s but NO [kmb] suffix (like sqft) are safe since
        # they only capture space-grouped digits (e.g. "5 000").
        pattern_matches = re.findall(r"\(([^)]*\\s[^)]*\[kmb\][^)]*)\)", source)
        for match in pattern_matches:
            assert not match, (
                f"R11-04: Found \\s + [kmb] in same capture group: ({match}). "
                "Whitespace before [kmb] causes false K/M/B suffix matches."
            )


# ---------------------------------------------------------------------------
# R11-05 (P1): routing_decision.py maps cost_estimation to DATA_ANALYSIS_AGENT
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR11_05_CostEstimationWrongAgentMapping:
    """_map_intent_to_agent maps 'cost_estimation' to DATA_ANALYSIS_AGENT.
    This causes cost estimation queries to be routed to the data analysis
    agent, which may not have the cost model loaded and can crash.
    """

    def test_cost_estimation_not_routed_to_data_analysis(self):
        source = Path("backend/services/routing_decision.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_map_intent_to_agent"
            ):
                func_source = ast.get_source_segment(source, node) or ""
                # cost_estimation should NOT map to DATA_ANALYSIS_AGENT
                # It should map to GENERAL_AGENT or a dedicated cost agent
                if (
                    "cost_estimation" in func_source
                    and "DATA_ANALYSIS_AGENT" in func_source
                ):
                    # Verify the mapping is direct, not just in fallback
                    lines = func_source.split("\n")
                    for line in lines:
                        if "cost_estimation" in line and "DATA_ANALYSIS_AGENT" in line:
                            pytest.fail(
                                "R11-05: 'cost_estimation' maps to DATA_ANALYSIS_AGENT. "
                                "Cost estimation queries crash because DataAnalysisAgent "
                                "expects CSV files, not cost model inference."
                            )
                return
        pytest.fail("Could not find _map_intent_to_agent method")


# ---------------------------------------------------------------------------
# R11-06 to R11-09 (P1): Missing secure_endpoint on API routes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR11_06_PromptRoutesNoAuth:
    """prompt_routes.py router has no dependencies=[Depends(secure_endpoint)]."""

    def test_prompt_routes_has_secure_endpoint(self):
        source = Path("backend/api/prompt_routes.py").read_text()
        assert "secure_endpoint" in source, (
            "R11-06: prompt_routes.py does not import or use secure_endpoint. "
            "All prompt CRUD/admin endpoints are unauthenticated."
        )


@pytest.mark.unit
class TestR11_07_FeedbackRoutesNoAuth:
    """feedback_routes.py router has no dependencies=[Depends(secure_endpoint)]."""

    def test_feedback_routes_has_secure_endpoint(self):
        source = Path("backend/api/feedback_routes.py").read_text()
        assert "secure_endpoint" in source, (
            "R11-07: feedback_routes.py does not import or use secure_endpoint. "
            "Feedback submission endpoints are unauthenticated."
        )


@pytest.mark.unit
class TestR11_08_IntentRoutesNoAuth:
    """intent_classification_routes.py router has no secure_endpoint."""

    def test_intent_routes_has_secure_endpoint(self):
        source = Path("backend/api/intent_classification_routes.py").read_text()
        assert "secure_endpoint" in source, (
            "R11-08: intent_classification_routes.py does not import or use secure_endpoint. "
            "Intent classification endpoints are unauthenticated."
        )


@pytest.mark.unit
class TestR11_09_CostEstimationRoutesNoAuth:
    """cost_estimation_routes.py router has no secure_endpoint."""

    def test_cost_estimation_routes_has_secure_endpoint(self):
        source = Path("backend/api/cost_estimation_routes.py").read_text()
        assert "secure_endpoint" in source, (
            "R11-09: cost_estimation_routes.py does not import or use secure_endpoint. "
            "Cost estimation training/prediction endpoints are unauthenticated."
        )


# ---------------------------------------------------------------------------
# R11-10 (P1): validator.py exec bypass via list/dict/tuple indirection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR11_10_ValidatorExecBypassIndirection:
    """_validate_blocked_calls only checks ast.Name and ast.Attribute targets.
    Blocked functions hidden in containers like [exec][0](...), {"e": exec}["e"](...),
    or tuple unpacking bypass the validator.
    """

    def test_exec_in_list_subscript_blocked(self):
        from backend.services.code_executor.validator import CodeValidator

        validator = CodeValidator(strict_mode=False)
        code = "[exec][0]('print(1)')"
        result = validator.validate(code)
        assert not result.is_valid, (
            "R11-10: [exec][0]('print(1)') bypassed validator. "
            "exec hidden in list subscript is not detected."
        )

    def test_exec_in_dict_value_blocked(self):
        from backend.services.code_executor.validator import CodeValidator

        validator = CodeValidator(strict_mode=False)
        code = '{"e": exec}["e"]("print(1)")'
        result = validator.validate(code)
        assert not result.is_valid, (
            "R11-10: {'e': exec}['e']('print(1)') bypassed validator. "
            "exec hidden in dict value is not detected."
        )


# ---------------------------------------------------------------------------
# R11-11 (P1): data_analysis_agent.py NaN breaks JSON serialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR11_11_DataAnalysisNaNBreaksJSON:
    """_extract_dataset_info produces float('nan') for all-NaN numeric columns.
    json.dumps() raises ValueError on NaN, breaking the API response.
    """

    def test_extract_dataset_info_no_nan_in_output(self):
        source = Path(
            "backend/services/data_analysis/data_analysis_agent.py"
        ).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_extract_dataset_info"
            ):
                func_source = ast.get_source_segment(source, node) or ""
                # The function computes float(df[col].mean()) etc. but when ALL
                # values in a column are NaN, mean() returns NaN. The function
                # checks `if not df[col].empty` but an all-NaN column is not empty.
                # It needs explicit NaN handling like:
                #   math.isnan, pd.isna, np.isnan, or a NaN→0/None replacement
                # Check for NaN-aware guards around the stat computations
                has_nan_guard = any(
                    x in func_source
                    for x in (
                        "isnan(",
                        "isna(",
                        "notna(",
                        "fillna(",
                        "isnull().all()",
                        "all_nan",
                        "nanmean",
                        "_safe_float",
                        "!= f)",
                        "math.nan",
                    )
                )
                assert has_nan_guard, (
                    "R11-11: _extract_dataset_info does not guard against NaN from "
                    "all-NaN columns. df[col].mean() returns float('nan'), and "
                    "float(nan) breaks json.dumps() with ValueError."
                )
                return
        pytest.fail("Could not find _extract_dataset_info method")


# ---------------------------------------------------------------------------
# R11-12 (P1): _RAGRetrieverAdapter.retrieve blocks event loop
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR11_12_RAGRetrieverAdapterBlocksLoop:
    """_RAGRetrieverAdapter.retrieve is async but calls
    hybrid_retriever.search() synchronously. This bypasses Round 10's
    asyncio.to_thread fallback in retrieval_node because retrieval_node
    sees an awaitable retrieve() and awaits it directly.
    """

    def test_rag_adapter_uses_thread_for_sync_search(self):
        source = Path("backend/api/workflow_query_routes.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "_RAGRetrieverAdapter":
                class_source = ast.get_source_segment(source, node) or ""
                # The retrieve method should use asyncio.to_thread or
                # run_in_executor to avoid blocking the event loop
                has_async_offload = any(
                    x in class_source
                    for x in (
                        "asyncio.to_thread",
                        "run_in_executor",
                        "run_in_threadpool",
                    )
                )
                assert has_async_offload, (
                    "R11-12: _RAGRetrieverAdapter.retrieve() calls "
                    "hybrid_retriever.search() synchronously inside async def. "
                    "Should use asyncio.to_thread to avoid blocking the event loop."
                )
                return
        pytest.fail("Could not find _RAGRetrieverAdapter class")


# ---------------------------------------------------------------------------
# R11-13 (P1): _DispatchResponseBuilder.__call__ blocks event loop
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestR11_13_DispatchResponseBuilderBlocksLoop:
    """_DispatchResponseBuilder.__call__ is synchronous and calls
    dispatch_service.generate() which performs LLM inference.
    When called from response_node (async), it blocks the event loop.
    """

    def test_dispatch_builder_is_async_or_offloaded(self):
        source = Path("backend/api/workflow_query_routes.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "_DispatchResponseBuilder"
            ):
                class_source = ast.get_source_segment(source, node) or ""
                # __call__ should either be async or use thread offloading
                is_async_call = "async def __call__" in class_source
                has_thread_offload = any(
                    x in class_source
                    for x in (
                        "asyncio.to_thread",
                        "run_in_executor",
                        "run_in_threadpool",
                    )
                )
                assert is_async_call or has_thread_offload, (
                    "R11-13: _DispatchResponseBuilder.__call__ is synchronous and "
                    "calls dispatch_service.generate() which performs LLM inference. "
                    "Should be async or offload to thread pool."
                )
                return
        pytest.fail("Could not find _DispatchResponseBuilder class")
