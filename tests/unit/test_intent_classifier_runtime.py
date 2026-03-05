from __future__ import annotations

import pytest

from backend.services.intent_classification.intent_classifier import (
    IntentClassifier,
    IntentType,
    QueryContext,
)


class _RecordingLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    def generate(self, prompt: str, **kwargs):
        self.calls.append({"prompt": prompt, "kwargs": kwargs})
        return self.response


class _FailingLLM:
    def generate(self, prompt: str, **kwargs):
        del prompt, kwargs
        raise RuntimeError("synthetic llm failure")


@pytest.mark.asyncio
async def test_classify_intent_uses_llm_when_heuristic_uncertain():
    """LLM is called when the heuristic shortcut cannot classify with high confidence."""
    llm = _RecordingLLM(
        '{"intent":"data_analysis","confidence":0.82,"reasoning":"needs analytics",'
        '"keywords":["csv","trend"],"context_clues":["dataset"],'
        '"suggested_action":"run analysis","uncertainty_factors":[]}'
    )
    classifier = IntentClassifier(prompt_manager=None, llm_client=llm, enable_cache=False)
    context = QueryContext(session_id="s-1")

    # Use an ambiguous query that the heuristic classifies with low confidence
    result = await classifier.classify_intent(
        "Can you help me with this project task?", context
    )

    # Heuristic returns knowledge_retrieval at 0.51 (below 0.85), so LLM is called
    assert llm.calls, "LLM generate should be called when heuristic is uncertain"


@pytest.mark.asyncio
async def test_classify_intent_skips_llm_when_heuristic_confident():
    """Heuristic shortcut skips LLM call when confidence is high."""
    llm = _RecordingLLM('{"intent":"knowledge_retrieval","confidence":0.9}')
    classifier = IntentClassifier(prompt_manager=None, llm_client=llm, enable_cache=False)
    context = QueryContext(session_id="s-1")

    result = await classifier.classify_intent(
        "Analyze csv trend for anomaly detection", context
    )

    assert result.intent == IntentType.DATA_ANALYSIS
    assert result.confidence >= 0.85
    assert not llm.calls, "LLM should NOT be called when heuristic is confident"


@pytest.mark.asyncio
async def test_classify_intent_falls_back_to_heuristic_when_llm_fails():
    classifier = IntentClassifier(
        prompt_manager=None,
        llm_client=_FailingLLM(),
        enable_cache=False,
    )
    context = QueryContext(session_id="s-2")

    result = await classifier.classify_intent(
        "Need cost estimate and budget overrun prediction", context
    )

    assert result.intent == IntentType.COST_ESTIMATION
    assert result.confidence >= 0.8


@pytest.mark.asyncio
async def test_classify_intent_normalizes_alias_intent_values():
    llm = _RecordingLLM(
        '{"intent":"knowledge retrieval","confidence":0.76,"reasoning":"faq lookup",'
        '"keywords":[],"context_clues":[],"suggested_action":"rag","uncertainty_factors":[]}'
    )
    classifier = IntentClassifier(prompt_manager=None, llm_client=llm, enable_cache=False)
    context = QueryContext(session_id="s-3")

    result = await classifier.classify_intent("What does p100 require?", context)

    assert result.intent == IntentType.KNOWLEDGE_RETRIEVAL
    assert result.confidence == pytest.approx(0.76, abs=1e-6)
