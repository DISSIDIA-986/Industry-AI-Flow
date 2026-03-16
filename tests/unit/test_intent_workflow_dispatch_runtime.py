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
        self.calls = []

    def search(self, query: str, top_k: int, vector_weight: float, bm25_weight: float):
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "vector_weight": vector_weight,
                "bm25_weight": bm25_weight,
            }
        )
        del top_k, vector_weight, bm25_weight
        return list(self._chunks)


class _FakeLLM:
    def __init__(self, answer: str = "Grounded answer with citations [1]."):
        self.answer = answer
        self.prompts = []

    def generate(self, prompt: str, **kwargs):
        self.prompts.append({"prompt": prompt, "kwargs": kwargs})
        return self.answer


class _FakeRAG:
    def __init__(self, chunks, answer: str = "Grounded answer with citations [1]."):
        self.use_hybrid_search = True
        self.hybrid_retriever = _FakeRetriever(chunks)
        self.use_reranker = False
        self.reranker = None
        self.vectorstore = None
        self.llm_client = _FakeLLM(answer=answer)


class _RewriteAwareFakeLLM(_FakeLLM):
    def __init__(self, answer: str = "Grounded answer with citations [1]."):
        super().__init__(answer=answer)
        self.rewrite_output = '{"rewrites":["concrete curing quality requirements"]}'

    def generate(self, prompt: str, **kwargs):
        self.prompts.append({"prompt": prompt, "kwargs": kwargs})
        if "Rewrite the user query for document retrieval." in prompt:
            return self.rewrite_output
        return self.answer


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
        {
            "doc_id": "doc-a",
            "filename": "spec-a.pdf",
            "content": "Concrete quality control shall be documented.",
            "score": 0.91,
        },
        {
            "doc_id": "doc-b",
            "filename": "spec-b.pdf",
            "content": "Safety checks include PPE and fall protection.",
            "score": 0.88,
        },
    ]
    workflow = _build_workflow()
    rag = _FakeRAG(chunks, answer="Use curing checklist and PPE controls [1][2].")
    monkeypatch.setattr(workflow, "_get_rag_service", lambda: rag)

    result = await workflow._dispatch_to_agent(
        agent_type=AgentType.GENERAL_AGENT,
        query="summarize standards",
        context=QueryContext(
            session_id="s-1",
            interaction_history=[
                {
                    "user_query": "What is CSA A23.1?",
                    "agent_response": "It is a concrete materials standard.",
                }
            ],
        ),
        parameters={},
        system_prompt=None,
        prompt_meta={"id": str(uuid4())},
        route_mode="local_only",
    )

    assert result["response"] == "Use curing checklist and PPE controls [1][2]."
    assert result["metadata"]["source_count"] == 2
    assert result["metadata"]["generation_mode"] == "rag_grounded_llm"
    assert result["metadata"]["sources"][0]["document_name"] == "spec-a.pdf"
    assert rag.llm_client.prompts, "RAG dispatch should call LLM generation"
    prompt = rag.llm_client.prompts[-1]["prompt"]
    assert "summarize standards" in prompt
    assert "Concrete quality control shall be documented." in prompt
    assert "What is CSA A23.1?" in prompt
    assert "It is a concrete materials standard." in prompt
    assert result["metadata"]["query_rewrite_used"] is False
    assert result["metadata"]["retrieval_query_count"] == 1
    assert result["metadata"]["profile_boost_used"] is False
    assert result["metadata"]["document_profiles"] == []
    assert result["metadata"]["suggested_questions"]
    assert rag.hybrid_retriever.calls, "retriever should be called"


@pytest.mark.asyncio
async def test_dispatch_to_agent_uses_query_rewrite_and_fusion(monkeypatch):
    chunks = [
        {
            "doc_id": "doc-a",
            "filename": "spec-a.pdf",
            "content": "Concrete quality control shall be documented.",
            "score": 0.91,
        },
        {
            "doc_id": "doc-b",
            "filename": "spec-b.pdf",
            "content": "Curing windows shall be tracked by checklist.",
            "score": 0.88,
        },
    ]
    workflow = _build_workflow()
    rag = _FakeRAG(chunks, answer="Use curing checklist and quality logs [1][2].")
    rag.llm_client = _RewriteAwareFakeLLM(
        answer="Use curing checklist and quality logs [1][2]."
    )
    monkeypatch.setattr(workflow, "_get_rag_service", lambda: rag)

    result = await workflow._dispatch_to_agent(
        agent_type=AgentType.RAG_AGENT,
        query="how to improve concrete curing checks",
        context=QueryContext(session_id="s-3", interaction_history=[]),
        parameters={
            "enable_query_rewrite": True,
            "query_rewrite_count": 1,
            "keywords": ["concrete", "curing", "quality"],
        },
        system_prompt=None,
        prompt_meta=None,
        route_mode="local_only",
    )

    assert result["metadata"]["query_rewrite_used"] is True
    assert result["metadata"]["retrieval_query_count"] == 2
    queries = [item["query"] for item in rag.hybrid_retriever.calls]
    assert "how to improve concrete curing checks" in queries
    assert "concrete curing quality requirements" in queries


@pytest.mark.asyncio
async def test_dispatch_to_agent_exposes_document_profile_context(monkeypatch):
    chunks = [
        {
            "doc_id": "doc-a",
            "filename": "spec-a.pdf",
            "content": "Concrete quality control shall be documented.",
            "score": 0.91,
        },
        {
            "doc_id": "doc-b",
            "filename": "spec-b.pdf",
            "content": "Curing windows shall be tracked by checklist.",
            "score": 0.88,
        },
    ]
    workflow = _build_workflow()
    rag = _FakeRAG(chunks, answer="Use curing checklist and quality logs [1][2].")
    monkeypatch.setattr(workflow, "_get_rag_service", lambda: rag)

    async def _fake_profile_boost(*, rag, query, chunks, top_k):
        del rag, query, top_k
        return chunks, [
            {
                "doc_id": "doc-a",
                "filename": "spec-a.pdf",
                "summary": "Quality control requirements and inspection cadence.",
                "outline": ["Quality Controls", "Inspection Checklist"],
                "keywords": ["quality", "inspection", "checklist"],
                "profile_score": 0.82,
            }
        ]

    monkeypatch.setattr(workflow, "_boost_chunks_with_profiles", _fake_profile_boost)

    result = await workflow._dispatch_to_agent(
        agent_type=AgentType.RAG_AGENT,
        query="how to improve concrete curing checks",
        context=QueryContext(session_id="s-4", interaction_history=[]),
        parameters={},
        system_prompt=None,
        prompt_meta=None,
        route_mode="local_only",
    )

    assert result["metadata"]["profile_boost_used"] is True
    assert result["metadata"]["document_profiles"][0]["filename"] == "spec-a.pdf"
    assert result["metadata"]["suggested_questions"]
    prompt = rag.llm_client.prompts[-1]["prompt"]
    assert "Document profiles:" in prompt
    assert "DocProfile 1" in prompt


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
    assert "encountered an issue" in str(updated["agent_response"])
    assert updated[
        "messages"
    ], "controlled failure should still emit user-facing response"
