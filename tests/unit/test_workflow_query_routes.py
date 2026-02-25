from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

import backend.api.workflow_query_routes as workflow_routes
from backend.api.workflow_query_routes import get_workflow_runner, router
from backend.services.demo_mode_service import (
    DEMO_MODE_LIVE_HYBRID,
    get_demo_mode_service,
)
from backend.services.language_policy import RAG_CHINESE_QUERY_UNSUPPORTED


class _FakeWorkflowRunner:
    async def run_workflow(
        self,
        query,
        session_id,
        user_id=None,
        thread_id=None,
        route_mode=None,
    ):
        return {
            "success": True,
            "agent_response": f"handled: {query}",
            "intent_result": {"intent": "knowledge_retrieval"},
            "metadata": {
                "provider_used": "local",
                "prompt_meta": {"name": "construction_rag_grounded_qa"},
                "routing_path": "hybrid_auto",
                "route_mode": route_mode,
            },
            "error": None,
        }


@pytest.fixture(autouse=True)
def _reset_demo_mode_state():
    service = get_demo_mode_service()
    service.reset_for_tests(mode=DEMO_MODE_LIVE_HYBRID, allow_cloud_override=False)
    yield
    service.reset_for_tests(mode=DEMO_MODE_LIVE_HYBRID, allow_cloud_override=False)


@pytest.mark.asyncio
async def test_workflow_query_contract():
    app = FastAPI()
    app.include_router(router)

    async def _override_runner():
        return _FakeWorkflowRunner()

    app.dependency_overrides[get_workflow_runner] = _override_runner

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/workflow/query",
            json={
                "query": "What is CSA A23.1?",
                "session_id": "s-1",
                "route_mode": "cloud_only",
            },
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    assert payload["session_id"] == "s-1"
    assert payload["intent"] == "knowledge_retrieval"
    assert payload["route_mode"] == "cloud_only"
    assert payload["provider_used"] == "local"
    assert payload["prompt_meta"]["name"] == "construction_rag_grounded_qa"
    assert payload["metadata"]["trace_id"] == payload["trace_id"]
    assert payload["metadata"]["session_id"] == "s-1"


@pytest.mark.asyncio
async def test_workflow_query_generates_session_id_when_missing():
    app = FastAPI()
    app.include_router(router)

    async def _override_runner():
        return _FakeWorkflowRunner()

    app.dependency_overrides[get_workflow_runner] = _override_runner

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/workflow/query",
            json={"query": "Need compliance summary"},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload["session_id"], str)
    assert payload["session_id"]
    assert isinstance(payload["trace_id"], str)
    assert payload["trace_id"]
    assert payload["route_mode"] == "hybrid_auto"


@pytest.mark.asyncio
async def test_workflow_query_uses_user_scoped_session_when_missing():
    app = FastAPI()
    app.include_router(router)

    captured = {"session_id": None}

    class _CapturingRunner:
        async def run_workflow(
            self,
            query,
            session_id,
            user_id=None,
            thread_id=None,
            route_mode=None,
        ):
            del query, user_id, thread_id, route_mode
            captured["session_id"] = session_id
            return {
                "success": True,
                "agent_response": "ok",
                "intent_result": {"intent": "knowledge_retrieval"},
                "metadata": {"provider_used": "local"},
                "error": None,
            }

    async def _override_runner():
        return _CapturingRunner()

    app.dependency_overrides[get_workflow_runner] = _override_runner

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/workflow/query",
            json={"query": "Need compliance summary", "user_id": "u-42"},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["session_id"] == "user:u-42"
    assert captured["session_id"] == "user:u-42"
    assert payload["metadata"]["session_id"] == "user:u-42"


@pytest.mark.asyncio
async def test_workflow_query_uses_fallback_runner_when_init_fails(monkeypatch):
    app = FastAPI()
    app.include_router(router)

    async def _broken_init():
        raise RuntimeError("init failed")

    monkeypatch.setattr(workflow_routes, "_workflow_service", None)
    monkeypatch.setattr(workflow_routes, "_initialize_workflow_service", _broken_init)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/workflow/query",
            json={"query": "summarize safety checklist", "route_mode": "cloud_only"},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    assert payload["route_mode"] == "cloud_only"
    assert payload["provider_used"] in {"cloud", "local_fallback"}
    assert payload["metadata"]["workflow_runner"] == "fallback_orchestrator"


@pytest.mark.asyncio
async def test_workflow_query_normalizes_sources_from_agent_execution():
    app = FastAPI()
    app.include_router(router)

    class _SourceRunner:
        async def run_workflow(
            self,
            query,
            session_id,
            user_id=None,
            thread_id=None,
            route_mode=None,
        ):
            del query, session_id, user_id, thread_id, route_mode
            return {
                "success": True,
                "agent_response": "Grounded answer [1].",
                "intent_result": {"intent": "knowledge_retrieval"},
                "metadata": {
                    "provider_used": "local",
                    "agent_execution": {
                        "sources": [
                            {
                                "doc_id": "doc-1",
                                "filename": "construction-guide.pdf",
                                "score": 0.87,
                                "content": "Guideline excerpt",
                            }
                        ]
                    },
                },
                "error": None,
            }

    async def _override_runner():
        return _SourceRunner()

    app.dependency_overrides[get_workflow_runner] = _override_runner

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/workflow/query",
            json={"query": "Need compliance summary", "session_id": "s-source"},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["sources"]
    first = payload["sources"][0]
    assert first["document_id"] == "doc-1"
    assert first["document_name"] == "construction-guide.pdf"
    assert first["relevance"] == 0.87


@pytest.mark.asyncio
async def test_workflow_query_promotes_suggested_questions_from_agent_execution():
    app = FastAPI()
    app.include_router(router)

    class _SuggestionRunner:
        async def run_workflow(
            self,
            query,
            session_id,
            user_id=None,
            thread_id=None,
            route_mode=None,
        ):
            del query, session_id, user_id, thread_id, route_mode
            return {
                "success": True,
                "agent_response": "Grounded answer [1].",
                "intent_result": {"intent": "knowledge_retrieval"},
                "metadata": {
                    "provider_used": "local",
                    "agent_execution": {
                        "suggested_questions": [
                            "Which section supports this answer?",
                            "What exceptions are listed in the source?",
                        ]
                    },
                },
                "error": None,
            }

    async def _override_runner():
        return _SuggestionRunner()

    app.dependency_overrides[get_workflow_runner] = _override_runner

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/workflow/query",
            json={"query": "Need compliance summary", "session_id": "s-followup"},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["metadata"]["suggested_questions"] == [
        "Which section supports this answer?",
        "What exceptions are listed in the source?",
    ]


@pytest.mark.asyncio
async def test_workflow_query_records_audit_and_metrics(monkeypatch):
    app = FastAPI()
    app.include_router(router)

    recorded = {"audit": [], "metrics": []}

    async def _override_runner():
        return _FakeWorkflowRunner()

    def _fake_audit(**kwargs):
        recorded["audit"].append(kwargs)

    def _fake_metric(**kwargs):
        recorded["metrics"].append(kwargs)

    app.dependency_overrides[get_workflow_runner] = _override_runner
    monkeypatch.setattr(workflow_routes.audit_logger, "log_event", _fake_audit)
    monkeypatch.setattr(workflow_routes, "record_workflow_request", _fake_metric)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/workflow/query",
            json={"query": "Need compliance summary"},
        )

    assert resp.status_code == 200
    assert recorded["audit"]
    assert recorded["audit"][0]["action"] == "workflow.query"
    assert recorded["metrics"]
    assert recorded["metrics"][0]["status"] == "success"


@pytest.mark.asyncio
async def test_workflow_query_rejects_chinese_input():
    app = FastAPI()
    app.include_router(router)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/workflow/query",
            json={"query": "Please help me analyze cost risk"},
        )

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == RAG_CHINESE_QUERY_UNSUPPORTED
    assert "English" in detail["message"]
