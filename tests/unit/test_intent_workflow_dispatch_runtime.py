from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.services.intent_classification.intent_classifier import QueryContext
from backend.services.intent_classification.intent_workflow import (
    IntentClassificationWorkflow,
)
from backend.services.routing_decision import AgentType


class _FakeRetriever:
    def __init__(self, chunks):
        self._chunks = chunks

    def search(self, query: str, top_k: int, vector_weight: float, bm25_weight: float):
        del query, top_k, vector_weight, bm25_weight
        return list(self._chunks)


class _FakeRAG:
    def __init__(self, chunks):
        self.use_hybrid_search = True
        self.hybrid_retriever = _FakeRetriever(chunks)
        self.use_reranker = False
        self.reranker = None
        self.vectorstore = None


def _build_workflow() -> IntentClassificationWorkflow:
    return IntentClassificationWorkflow(
        intent_classifier=SimpleNamespace(),
        context_manager=SimpleNamespace(),
        routing_engine=SimpleNamespace(),
        prompt_manager=None,
    )


@pytest.mark.asyncio
async def test_dispatch_to_agent_returns_grounded_rag_response(monkeypatch):
    chunks = [
        {"doc_id": "doc-a", "content": "Concrete quality control shall be documented."},
        {"doc_id": "doc-b", "content": "Safety checks include PPE and fall protection."},
    ]
    workflow = _build_workflow()
    monkeypatch.setattr(workflow, "_get_rag_service", lambda: _FakeRAG(chunks))

    result = await workflow._dispatch_to_agent(
        agent_type=AgentType.GENERAL_AGENT,
        query="summarize standards",
        context=QueryContext(session_id="s-1"),
        parameters={},
        system_prompt=None,
        prompt_meta={"id": str(uuid4())},
        route_mode="local_only",
    )

    assert "Based on retrieved construction knowledge" in result["response"]
    assert "[sources: doc-a, doc-b]" in result["response"]
    assert result["metadata"]["source_count"] == 2


@pytest.mark.asyncio
async def test_dispatch_to_agent_raises_when_retrieval_is_empty(monkeypatch):
    workflow = _build_workflow()
    monkeypatch.setattr(workflow, "_get_rag_service", lambda: _FakeRAG([]))

    with pytest.raises(RuntimeError, match="empty context"):
        await workflow._dispatch_to_agent(
            agent_type=AgentType.RAG_AGENT,
            query="summarize standards",
            context=QueryContext(session_id="s-2"),
            parameters={},
            system_prompt=None,
            prompt_meta=None,
            route_mode="local_only",
        )


@pytest.mark.asyncio
async def test_response_processing_marks_error_for_empty_agent_response():
    workflow = _build_workflow()
    state = {
        "agent_response": None,
        "messages": [],
        "metadata": {},
        "workflow_complete": False,
    }

    updated = await workflow._response_processing_node(state)
    assert updated["error"] == "Agent returned empty response"


@pytest.mark.asyncio
async def test_response_processing_returns_controlled_failure_when_error_exists():
    workflow = _build_workflow()
    state = {
        "agent_response": None,
        "messages": [],
        "metadata": {},
        "workflow_complete": False,
        "error": "RAG retrieval returned empty context",
    }

    updated = await workflow._response_processing_node(state)
    assert updated["workflow_complete"] is True
    assert "EN" in str(updated["agent_response"])
    assert updated["messages"], "controlled failure should still emit user-facing response"
