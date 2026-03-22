from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import demo_mode_routes, llm_dispatch_routes, workflow_query_routes
from backend.api.workflow_query_routes import get_workflow_runner
from backend.security.context import TenantContext
from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.services.demo_mode_service import (
    DEMO_MODE_LIVE_HYBRID,
    DEMO_MODE_SCRIPTED_REPLAY,
    get_demo_mode_service,
)
from backend.services.llm_integration.types import (
    CostStats,
    DispatchResponse,
    UsageStats,
)


@dataclass
class _FakeDispatchService:
    last_route_mode: str | None = None

    def generate(self, req):
        self.last_route_mode = req.route_mode
        return DispatchResponse(
            success=True,
            text="ok",
            provider="ollama",
            model="fake-local",
            route_mode="local_only",
            trace_id=req.trace_id,
            latency_ms=1,
            usage=UsageStats(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            cost=CostStats(estimated_cost_usd=0.0),
        )


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
            "metadata": {"provider_used": "local", "route_mode": route_mode},
            "error": None,
        }


@pytest.fixture(autouse=True)
def reset_demo_mode_state():
    service = get_demo_mode_service()
    service.reset_for_tests(mode=DEMO_MODE_LIVE_HYBRID, allow_cloud_override=False)
    yield
    service.reset_for_tests(mode=DEMO_MODE_LIVE_HYBRID, allow_cloud_override=False)


def _build_app(*, roles: list[str] | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(demo_mode_routes.router)
    app.include_router(llm_dispatch_routes.router, prefix="/api/v1")
    app.include_router(workflow_query_routes.router)

    async def _mock_secure():
        return TenantContext(
            tenant_id="tenant-a", user_id="u-1", roles=roles or ["user"]
        )

    async def _mock_tenant():
        return TenantContext(
            tenant_id="tenant-a", user_id="u-1", roles=roles or ["user"]
        )

    async def _mock_workflow_runner():
        return _FakeWorkflowRunner()

    app.dependency_overrides[secure_endpoint] = _mock_secure
    app.dependency_overrides[get_current_tenant] = _mock_tenant
    app.dependency_overrides[get_workflow_runner] = _mock_workflow_runner
    return app


def test_demo_mode_read_and_write_permissions():
    app_user = _build_app(roles=["user"])
    user_client = TestClient(app_user)

    read_resp = user_client.get("/api/v1/demo/mode")
    assert read_resp.status_code == 200
    assert read_resp.json()["mode"] == DEMO_MODE_LIVE_HYBRID

    write_resp = user_client.post(
        "/api/v1/demo/mode",
        json={"mode": DEMO_MODE_SCRIPTED_REPLAY},
    )
    assert write_resp.status_code == 403

    app_admin = _build_app(roles=["admin"])
    admin_client = TestClient(app_admin)
    update_resp = admin_client.post(
        "/api/v1/demo/mode",
        json={"mode": DEMO_MODE_SCRIPTED_REPLAY, "allow_cloud_override": True},
    )
    assert update_resp.status_code == 200
    payload = update_resp.json()
    assert payload["mode"] == DEMO_MODE_SCRIPTED_REPLAY
    assert payload["allow_cloud_override"] is True


def test_dispatch_route_uses_scripted_replay_without_cloud_call(monkeypatch):
    fake_dispatch = _FakeDispatchService()
    monkeypatch.setattr(
        llm_dispatch_routes,
        "get_dispatch_service",
        lambda: fake_dispatch,
    )

    app = _build_app(roles=["admin"])
    client = TestClient(app)

    mode_resp = client.post(
        "/api/v1/demo/mode",
        json={"mode": DEMO_MODE_SCRIPTED_REPLAY},
    )
    assert mode_resp.status_code == 200

    resp = client.post(
        "/api/v1/query/dispatch",
        json={
            "question": "cost estimate for a tower project",
            "route_mode": "cloud_only",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["provider_used"] == "scripted_replay"
    assert payload["demo_mode"] == DEMO_MODE_SCRIPTED_REPLAY
    assert payload["replay_scenario"] == "cost_estimation_showcase"
    assert fake_dispatch.last_route_mode is None


def test_workflow_query_uses_scripted_replay_shortcut():
    app = _build_app(roles=["admin"])
    client = TestClient(app)

    mode_resp = client.post(
        "/api/v1/demo/mode",
        json={"mode": DEMO_MODE_SCRIPTED_REPLAY},
    )
    assert mode_resp.status_code == 200

    resp = client.post(
        "/api/v1/workflow/query",
        json={"query": "please do cost estimate"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["provider_used"] == "scripted_replay"
    assert payload["route_mode"] == "scripted_replay"
    assert payload["metadata"]["demo_mode"] == DEMO_MODE_SCRIPTED_REPLAY
