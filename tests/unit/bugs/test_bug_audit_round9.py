"""TDI Round 9 bug reproduction tests.

Each test asserts the CORRECT behavior that is currently broken.
Tests are marked with xfail until the corresponding bug is fixed.

Bugs found: 2026-02-26 | 1 P0, 7 P1 | Categories: RAG, Pipeline, LLM Dispatch,
Groundedness, Cost Routes
"""

from __future__ import annotations

import ast
import asyncio
import re
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# BUG-R9-01: _MemorySession.language_preference defaults to "zh" not "en"
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_memory_session_default_language_is_english():
    """The default language preference for memory sessions must be English,
    matching the construction documents and demo language."""
    source = open("backend/services/rag_engine.py").read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "_MemorySession":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(
                    item.target, ast.Name
                ):
                    if item.target.id == "language_preference":
                        assert isinstance(
                            item.value, ast.Constant
                        ), "language_preference should have a default value"
                        assert item.value.value == "en", (
                            f"language_preference defaults to '{item.value.value}' "
                            "but should be 'en' — project uses English documents"
                        )
                        return
    pytest.fail("Could not find _MemorySession.language_preference in rag_engine.py")


# ---------------------------------------------------------------------------
# BUG-R9-03 (P0): Error response leaks internal policy details
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_error_response_does_not_leak_internal_details():
    """When the pipeline has an error, the response to the user must be
    a generic safe message, not the raw internal error string."""
    source = open("backend/services/workflows/nodes/response_node.py").read()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_default_response":
            func_source = ast.get_source_segment(source, node) or ""
            # The function should NOT return str(state["error"]) directly
            # because that leaks internal error details like
            # "Request blocked by safety policy" or "intent_node failed: ..."
            assert "return str(state" not in func_source, (
                "_build_default_response returns raw state['error'] — "
                "this leaks internal error messages to users. Should return "
                "a generic 'Your request could not be processed' message."
            )
            return
    pytest.fail("Could not find _build_default_response in response_node.py")


# ---------------------------------------------------------------------------
# BUG-R9-04: RRF formula still uses weight/rank instead of weight/(k+rank)
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_rrf_formula_uses_k_constant():
    """Reciprocal Rank Fusion requires weight/(k+rank) with k=60 (standard).
    Using weight/rank gives too much weight to the top result and compresses
    the score range, degrading fusion quality."""
    source = open("backend/services/retrieval/hybrid_search.py").read()

    # The correct RRF formula has a k constant (typically 60)
    # Wrong: vector_weight / rank  (no k constant)
    # Right: vector_weight / (k + rank)  where k is a constant or variable
    wrong_pattern = re.compile(r"(?:vector_weight|bm25_weight)\s*/\s*rank\b")
    # Accept either inline constant or variable: /(60 + rank) or /(rrf_k + rank)
    correct_pattern = re.compile(
        r"(?:vector_weight|bm25_weight)\s*/\s*\(\s*(?:\d+|\w+)\s*\+\s*rank\s*\)"
    )

    has_wrong = bool(wrong_pattern.search(source))
    has_correct = bool(correct_pattern.search(source))

    assert not has_wrong, (
        "RRF formula uses weight/rank (wrong) — " "should be weight/(k+rank) with k=60"
    )
    assert has_correct, "RRF formula does not use the standard weight/(k+rank) pattern"


# ---------------------------------------------------------------------------
# BUG-R9-05: _estimate_confidence is purely length-based
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_estimate_confidence_penalizes_hallucination_markers():
    """_estimate_confidence should not score a hallucinated 600-char
    response at 0.95. Hedging phrases, repetition, and lack of specificity
    should lower confidence."""
    from backend.services.llm_integration.dispatch_service import DispatchService

    # A clearly hallucinated response with hedging language
    hallucinated = (
        "I think the answer might be related to construction costs. "
        "Generally speaking, construction projects can vary widely. "
        "It depends on many factors including location, materials, "
        "and labor costs. Some projects cost more while others cost less. "
        "The overall budget should be carefully considered. "
        "Various aspects need to be taken into account. "
        "Construction is a complex field with many variables. "
        "In my understanding, the costs could range significantly. "
        "There are multiple considerations to keep in mind. "
        "Overall the project cost depends on numerous factors. "
        "Further analysis would be needed for a precise estimate."
    )
    assert len(hallucinated) > 600, "Test data must be >600 chars"

    confidence = DispatchService._estimate_confidence(hallucinated)
    assert confidence < 0.80, (
        f"Hallucinated hedging text scored {confidence} confidence — "
        "should be < 0.80 to trigger cloud fallback in hybrid_auto mode"
    )


# ---------------------------------------------------------------------------
# BUG-R9-06: Groundedness checker ignores llm_client param
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_groundedness_rejects_numeric_magnitude_error():
    """Groundedness checker should FAIL when the answer has a 10x numeric error.
    A claim of '500 kN' when the context says '50 kN' is a safety-critical
    factual error that must not pass groundedness checks."""
    from backend.services.safety.groundedness_checker import GroundednessChecker

    checker = GroundednessChecker(confidence_threshold=0.80)

    # Context says 50 kN but answer claims 500 kN (10x error)
    context = ["The maximum allowable load is 50 kN per anchor bolt."]
    wrong_answer = "The maximum allowable load is 500 kN per anchor bolt."

    wrong_conf, wrong_passed = checker.check_groundedness(wrong_answer, context)

    # A 10x factual error MUST NOT pass groundedness
    assert not wrong_passed, (
        f"Wrong answer '500 kN' (context says '50 kN') passed groundedness "
        f"with confidence {wrong_conf:.2f} — a 10x safety-critical numeric "
        "error should be caught by the groundedness checker"
    )


# ---------------------------------------------------------------------------
# BUG-R9-08: RAG prompt is all "EN" placeholder text
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_rag_prompt_contains_real_instructions():
    """The RAG prompt template must contain actual English instructions,
    not 'EN' placeholder fragments from incomplete i18n."""
    source = open("backend/services/rag_engine.py").read()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_prompt":
            func_source = ast.get_source_segment(source, node) or ""
            # Count "EN" placeholder occurrences vs real English words
            en_placeholder_count = func_source.count('"EN')
            en_placeholder_count += func_source.count("EN.")
            en_placeholder_count += func_source.count("EN,")
            en_placeholder_count += func_source.count("EN:")

            assert en_placeholder_count < 5, (
                f"_build_prompt contains {en_placeholder_count} 'EN' placeholder "
                "fragments — the RAG prompt must have real English instructions "
                "for the LLM to follow during demo"
            )

            # Check for essential RAG instruction keywords
            assert any(
                keyword in func_source.lower()
                for keyword in [
                    "based on the context",
                    "use the following",
                    "answer the question",
                    "cite",
                    "source",
                    "don't know",
                ]
            ), (
                "_build_prompt lacks essential RAG instruction keywords — "
                "must tell the LLM to answer based on context and cite sources"
            )
            return
    pytest.fail("Could not find _build_prompt in rag_engine.py")


# ---------------------------------------------------------------------------
# BUG-R9-10: Train endpoint leaks internal error details
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_cost_estimation_train_error_does_not_leak_details():
    """The /train endpoint's generic exception handler must not expose
    internal error messages (filesystem paths, stack traces) to clients."""
    source = open("backend/api/cost_estimation_routes.py").read()

    # Look for the problematic pattern: detail=f"training failed: {exc}"
    has_leak = bool(re.search(r'detail\s*=\s*f?"[^"]*\{exc\}', source))
    assert not has_leak, (
        "Train endpoint has detail=f'...{exc}' which leaks internal "
        "error messages. Use a generic message instead."
    )


# ---------------------------------------------------------------------------
# BUG-R9-12: _estimate_confidence has "EN" i18n artifact
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_estimate_confidence_no_en_artifact():
    """_estimate_confidence must not penalize text containing the letters 'EN'.
    The check '"EN" in text' is an i18n artifact that lowers confidence for
    any response mentioning 'ENGINE', 'ENABLE', 'ENVIRONMENT' etc."""
    from backend.services.llm_integration.dispatch_service import DispatchService

    # Normal technical text that happens to contain "EN"
    text = (
        "The HVAC system ENABLES efficient energy management. "
        "The ENGINE room requires proper ventilation. "
        "ENVIRONMENTAL considerations include noise levels."
    )
    confidence = DispatchService._estimate_confidence(text)
    # Should NOT be penalized to 0.55 just because text contains "EN"
    assert confidence > 0.55, (
        f"Text containing 'EN' scored {confidence} — the 'EN' i18n artifact "
        "in _estimate_confidence incorrectly penalizes legitimate text"
    )
