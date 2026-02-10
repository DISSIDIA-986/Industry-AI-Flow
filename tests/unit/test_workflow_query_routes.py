from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

import backend.api.workflow_query_routes as workflow_routes
from backend.api.workflow_query_routes import get_workflow_runner, router


class _FakeWorkflowRunner:
    async def run_workflow(self, query, session_id, user_id=None, thread_id=None):
        return {
            "success": True,
            "agent_response": f"handled: {query}",
            "intent_result": {"intent": "knowledge_retrieval"},
            "metadata": {
                "provider_used": "local",
                "prompt_meta": {"name": "construction_rag_grounded_qa"},
                "routing_path": "hybrid_auto",
            },
            "error": None,
        }


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
