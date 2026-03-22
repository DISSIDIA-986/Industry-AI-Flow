from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.api.prompt_routes import get_prompt_manager, router
from backend.security.dependencies import secure_endpoint


class _Acquire:
    def __init__(self, conn: Any):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self):
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch(self, query: str, *params: Any):
        self.calls.append((query, params))
        return []


class _FakePool:
    def __init__(self):
        self.conn = _FakeConn()

    def acquire(self):
        return _Acquire(self.conn)


class _FakeManager:
    def __init__(self):
        self.db_pool = _FakePool()


@pytest.mark.asyncio
async def test_search_prompt_sql_params_without_category_single_fetch():
    manager = _FakeManager()
    app = FastAPI()
    app.include_router(router)

    async def _override_manager():
        return manager

    app.dependency_overrides[get_prompt_manager] = _override_manager
    app.dependency_overrides[secure_endpoint] = lambda: None

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/prompts/search", params={"q": "beam"})

    assert resp.status_code == 200
    assert len(manager.db_pool.conn.calls) == 1
    _, params = manager.db_pool.conn.calls[0]
    assert len(params) == 2
    assert params[0] == "%beam%"
    assert params[1] == 10


@pytest.mark.asyncio
async def test_search_prompt_sql_params_with_category_binding_order():
    manager = _FakeManager()
    app = FastAPI()
    app.include_router(router)

    async def _override_manager():
        return manager

    app.dependency_overrides[get_prompt_manager] = _override_manager
    app.dependency_overrides[secure_endpoint] = lambda: None

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get(
            "/api/prompts/search",
            params={"q": "beam", "category": "rag", "limit": 7},
        )

    assert resp.status_code == 200
    assert len(manager.db_pool.conn.calls) == 1
    _, params = manager.db_pool.conn.calls[0]
    assert len(params) == 3
    assert params[0] == "%beam%"
    assert params[1] == "rag"
    assert params[2] == 7
