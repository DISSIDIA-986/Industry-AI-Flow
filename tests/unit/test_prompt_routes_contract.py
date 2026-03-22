from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

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
    async def fetch(self, query: str, *params: Any):
        if "FROM prompts p" in query:
            return [
                {
                    "id": uuid4(),
                    "name": "construction_rag_grounded_qa",
                    "category": "rag",
                    "subcategory": None,
                    "version": "1.0.0",
                    "content": "answer with {{ query }}",
                    "variables": json.dumps([]),
                    "metadata": json.dumps({}),
                    "is_active": True,
                    "is_latest": True,
                    "priority": 10,
                    "performance_score": 0.91,
                    "usage_count": 20,
                    "success_count": 18,
                    "created_at": "2026-02-10T00:00:00",
                    "updated_at": "2026-02-10T00:00:00",
                    "created_by": "qa",
                    "updated_by": "qa",
                    "tags": ["construction"],
                }
            ]
        return []

    async def fetchval(self, query: str, *params: Any):
        return 1


class _FakePool:
    def __init__(self):
        self.conn = _FakeConn()

    def acquire(self):
        return _Acquire(self.conn)


class _FakeManager:
    def __init__(self):
        self.db_pool = _FakePool()


@pytest.mark.asyncio
async def test_list_prompts_contract_returns_page_payload():
    app = FastAPI()
    app.include_router(router)

    async def _override_manager():
        return _FakeManager()

    app.dependency_overrides[get_prompt_manager] = _override_manager
    app.dependency_overrides[secure_endpoint] = lambda: None

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/prompts/", params={"page": 1, "size": 20})

    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, dict)
    assert "data" in payload
    assert "pagination" in payload
    assert payload["pagination"]["total"] == 1
    assert len(payload["data"]) == 1
