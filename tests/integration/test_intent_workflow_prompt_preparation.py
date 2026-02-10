from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

langgraph = pytest.importorskip("langgraph")
from backend.services.intent_classification.intent_workflow import IntentClassificationWorkflow


class _FakePromptManager:
    async def get_prompt(self, **kwargs):
        info = SimpleNamespace(
            id=uuid4(),
            name=kwargs["name"],
            category=kwargs["category"],
            version="1.0.0",
        )
        return info, "SYSTEM TEMPLATE"


@pytest.mark.asyncio
async def test_prompt_preparation_node_sets_prompt_fields():
    workflow = IntentClassificationWorkflow(
        intent_classifier=SimpleNamespace(),
        context_manager=SimpleNamespace(),
        routing_engine=SimpleNamespace(),
        prompt_manager=_FakePromptManager(),
    )

    state = {
        "session_id": "s1",
        "user_id": "u1",
        "current_query": "What is CSA A23.1?",
        "intent_result": SimpleNamespace(intent=SimpleNamespace(value="knowledge_retrieval")),
        "query_context": SimpleNamespace(interaction_history=[]),
        "metadata": {},
    }

    updated = await workflow._prompt_preparation_node(state)

    assert updated["metadata"]["prompt_status"] == "ok"
    assert updated["system_prompt"] == "SYSTEM TEMPLATE"
    assert updated["prompt_meta"]["name"] == "construction_rag_grounded_qa"


@pytest.mark.asyncio
async def test_prompt_preparation_node_disabled_without_manager():
    workflow = IntentClassificationWorkflow(
        intent_classifier=SimpleNamespace(),
        context_manager=SimpleNamespace(),
        routing_engine=SimpleNamespace(),
        prompt_manager=None,
    )

    state = {"metadata": {}}
    updated = await workflow._prompt_preparation_node(state)

    assert updated["metadata"]["prompt_status"] == "disabled"
