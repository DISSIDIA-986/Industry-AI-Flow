from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.services.workflows.nodes.intent_node import intent_node


@pytest.mark.asyncio
async def test_intent_node_detects_estimate_cost_phrase_with_heuristic():
    state = {
        "query": "Estimate cost risk for a 20-floor office project in Toronto.",
        "metadata": {},
    }

    updated = await intent_node(state, SimpleNamespace())

    assert updated["intent"] == "cost_estimation"
    assert updated["metadata"]["intent_source"] == "heuristic"


@pytest.mark.asyncio
async def test_intent_node_supports_classify_intent_interface():
    class _Result:
        intent = SimpleNamespace(value="cost_estimation")
        confidence = 0.92

    class _Classifier:
        def classify_intent(self, query: str, context: dict):  # noqa: ARG002
            return _Result()

    state = {
        "query": "Could you predict the budget overrun for this project?",
        "metadata": {},
    }

    updated = await intent_node(state, SimpleNamespace(intent_classifier=_Classifier()))

    assert updated["intent"] == "cost_estimation"
    assert updated["metadata"]["intent_source"] == "classifier"
    assert updated["metadata"]["intent_confidence"] == 0.92
