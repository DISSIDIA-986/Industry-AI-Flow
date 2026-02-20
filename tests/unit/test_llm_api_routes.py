"""API route tests for phase-1 dispatch/cost/compatibility endpoints."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.api import enhanced_query_routes, llm_cost_routes, llm_dispatch_routes
from backend.services.demo_mode_service import (
    DEMO_MODE_LIVE_HYBRID,
    DEMO_MODE_LOCAL_SAFE,
    get_demo_mode_service,
)
from backend.services.language_policy import RAG_CHINESE_QUERY_UNSUPPORTED
from backend.security.context import TenantContext
from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.services.llm_integration.types import (
    CostStats,
    DispatchResponse,
    UsageStats,
)


def _build_app(
    *,
    tenant_id: str = "tenant-a",
    roles: list[str] | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(llm_dispatch_routes.router, prefix="/api/v1")
    app.include_router(llm_cost_routes.router, prefix="/api/v1")
    app.include_router(enhanced_query_routes.router, prefix="/api/v1")

    async def _mock_secure():
        return TenantContext(
            tenant_id=tenant_id, user_id="u-1", roles=roles or ["user"]
        )

    async def _mock_tenant():
        return TenantContext(
            tenant_id=tenant_id, user_id="u-1", roles=roles or ["user"]
        )

    app.dependency_overrides[secure_endpoint] = _mock_secure
    app.dependency_overrides[get_current_tenant] = _mock_tenant
    return app


@pytest.fixture(autouse=True)
def _reset_demo_mode_state():
    service = get_demo_mode_service()
    service.reset_for_tests(mode=DEMO_MODE_LIVE_HYBRID, allow_cloud_override=False)
    yield
    service.reset_for_tests(mode=DEMO_MODE_LIVE_HYBRID, allow_cloud_override=False)


@pytest.mark.asyncio
async def test_dispatch_route_success(monkeypatch):
    class _FakeDispatchService:
        def generate(self, req):
            return DispatchResponse(
                success=True,
                text="ok",
                provider="llama_cpp",
                model="fake-local",
                route_mode="local_only",
                trace_id=req.trace_id,
                latency_ms=12,
                usage=UsageStats(prompt_tokens=2, completion_tokens=3, total_tokens=5),
                cost=CostStats(estimated_cost_usd=0.0),
            )

    monkeypatch.setattr(
        llm_dispatch_routes, "get_dispatch_service", lambda: _FakeDispatchService()
    )

    app = _build_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/query/dispatch",
            json={"question": "hello", "route_mode": "local_only"},
        )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["answer"] == "ok"
    assert payload["provider_used"] == "llama_cpp"
    assert payload["usage"]["total_tokens"] == 5


@pytest.mark.asyncio
async def test_dispatch_route_failure(monkeypatch):
    class _FakeDispatchService:
        def generate(self, req):
            return DispatchResponse(
                success=False,
                text="",
                provider="zhipu",
                model="glm-4-plus",
                route_mode="cloud_only",
                trace_id=req.trace_id,
                latency_ms=9,
                policy_decision="block_cloud",
                error="blocked",
            )

    monkeypatch.setattr(
        llm_dispatch_routes, "get_dispatch_service", lambda: _FakeDispatchService()
    )

    app = _build_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post("/api/v1/query/dispatch", json={"question": "hello"})
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert detail["policy_decision"] == "block_cloud"


@pytest.mark.asyncio
async def test_dispatch_route_forces_local_under_local_safe_mode(monkeypatch):
    observed = {}

    class _FakeDispatchService:
        def generate(self, req):
            observed["route_mode"] = req.route_mode
            return DispatchResponse(
                success=True,
                text="forced local",
                provider="llama_cpp",
                model="fake-local",
                route_mode="local_only",
                trace_id=req.trace_id,
                latency_ms=10,
                usage=UsageStats(prompt_tokens=1, completion_tokens=1, total_tokens=2),
                cost=CostStats(estimated_cost_usd=0.0),
            )

    get_demo_mode_service().set_mode(DEMO_MODE_LOCAL_SAFE)
    monkeypatch.setattr(
        llm_dispatch_routes, "get_dispatch_service", lambda: _FakeDispatchService()
    )

    app = _build_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/query/dispatch",
            json={"question": "hello", "route_mode": "cloud_only"},
        )
    assert resp.status_code == 200
    payload = resp.json()
    assert observed["route_mode"] == "local_only"
    assert payload["route_mode"] == "local_only"


@pytest.mark.asyncio
async def test_enhanced_query_compat_route(monkeypatch):
    observed = {}

    class _FakeRAG:
        def query(self, question, top_k=None, temperature=None, max_tokens=None):
            observed["question"] = question
            observed["top_k"] = top_k
            observed["temperature"] = temperature
            observed["max_tokens"] = max_tokens
            return {
                "query_id": "q-1",
                "question": question,
                "answer": "compat answer",
                "sources": ["doc-1"],
                "retrieved_chunks": [
                    {"doc_id": "doc-1", "content": "ctx", "score": 0.9}
                ],
                "search_weights": {"vector_weight": 0.7, "bm25_weight": 0.3},
            }

    monkeypatch.setattr(enhanced_query_routes, "get_rag_instance", lambda: _FakeRAG())

    app = _build_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/query",
            json={
                "question": "legacy client question",
                "top_k": 5,
                "temperature": 0.2,
                "max_tokens": 128,
            },
        )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["answer"] == "compat answer"
    assert payload["sources"] == ["doc-1"]
    assert len(payload["retrieved_chunks"]) == 1
    assert observed["top_k"] == 5
    assert observed["temperature"] == 0.2
    assert observed["max_tokens"] == 128


@pytest.mark.asyncio
async def test_enhanced_query_rejects_chinese_input(monkeypatch):
    class _FakeRAG:
        def query(self, question, top_k=None, temperature=None, max_tokens=None):
            return {
                "query_id": "q-blocked",
                "question": question,
                "answer": "should-not-run",
                "sources": [],
                "retrieved_chunks": [],
                "search_weights": {"vector_weight": 0.7, "bm25_weight": 0.3},
            }

    monkeypatch.setattr(enhanced_query_routes, "get_rag_instance", lambda: _FakeRAG())

    app = _build_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/query",
            json={"question": "请分析这个工程项目"},
        )

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == RAG_CHINESE_QUERY_UNSUPPORTED
    assert "English" in detail["message"]


@pytest.mark.asyncio
async def test_usage_route_requires_tenant_scope(monkeypatch):
    monkeypatch.setattr(
        llm_cost_routes.cost_tracker,
        "get_usage_summary",
        lambda **kwargs: {"ok": True, **kwargs},
    )
    app = _build_app(tenant_id="tenant-a", roles=["user"])
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/v1/llm/usage", params={"tenant_id": "tenant-b"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_usage_and_budget_routes_admin_scope(monkeypatch):
    monkeypatch.setattr(
        llm_cost_routes.cost_tracker,
        "get_usage_summary",
        lambda **kwargs: {"tenant_id": kwargs["tenant_id"], "summary": []},
    )
    monkeypatch.setattr(
        llm_cost_routes.cost_tracker,
        "get_budget_policy",
        lambda tenant_id: None,
    )
    monkeypatch.setattr(
        llm_cost_routes.cost_tracker,
        "get_monthly_spend",
        lambda tenant_id: 1.23,
    )
    monkeypatch.setattr(
        llm_cost_routes.cost_tracker,
        "evaluate_budget",
        lambda tenant_id: {"allowed": True, "decision": "allow"},
    )
    monkeypatch.setattr(
        llm_cost_routes.cost_tracker,
        "upsert_budget_policy",
        lambda policy: policy,
    )

    app = _build_app(tenant_id="tenant-a", roles=["admin"])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        usage = await client.get("/api/v1/llm/usage", params={"tenant_id": "tenant-b"})
    assert usage.status_code == 200
    assert usage.json()["tenant_id"] == "tenant-b"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        budget_get = await client.get("/api/v1/llm/budget/tenant-b")
    assert budget_get.status_code == 200
    assert budget_get.json()["tenant_id"] == "tenant-b"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        budget_set = await client.post(
            "/api/v1/llm/budget/tenant-b",
            json={
                "monthly_budget_usd": 50,
                "soft_limit_ratio": 0.8,
                "hard_limit_ratio": 1.0,
                "policy_mode": "local_only",
            },
        )
    assert budget_set.status_code == 200
    assert budget_set.json()["success"] is True
