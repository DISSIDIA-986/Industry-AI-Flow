from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.api.prompt_routes import get_prompt_manager, router


class _FakeManager:
    def __init__(self):
        self.calls = []

    async def get_usage_summary(self, *, days: int, category: str | None, top_limit: int):
        self.calls.append(
            {
                "days": days,
                "category": category,
                "top_limit": top_limit,
            }
        )
        return {
            "window_days": days,
            "category": category,
            "totals": {"usage_logs": 12, "success_logs": 10},
            "top_prompts": [],
            "daily": [],
        }


@pytest.mark.asyncio
async def test_prompt_metrics_summary_route_contract():
    app = FastAPI()
    app.include_router(router)
    manager = _FakeManager()

    async def _override_manager():
        return manager

    app.dependency_overrides[get_prompt_manager] = _override_manager

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get(
            "/api/prompts/metrics/summary",
            params={"days": 30, "category": "rag", "top_limit": 5},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["window_days"] == 30
    assert payload["category"] == "rag"
    assert payload["totals"]["usage_logs"] == 12
    assert payload["totals"]["success_logs"] == 10
    assert manager.calls == [{"days": 30, "category": "rag", "top_limit": 5}]
