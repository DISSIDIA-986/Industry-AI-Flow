from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.api.prompt_routes import get_prompt_manager, router
from backend.services.prompt_manager import PromptVariable


@dataclass
class _PromptDTO:
    id: UUID
    name: str
    category: str
    subcategory: str | None
    version: str
    content: str
    variables: list[PromptVariable]
    metadata: dict[str, Any]
    is_active: bool
    is_latest: bool
    priority: int
    performance_score: float
    usage_count: int
    success_count: int
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None
    tags: list[str]

    def to_dict(self):
        payload = asdict(self)
        payload["id"] = str(self.id)
        payload["variables"] = [asdict(v) for v in self.variables]
        return payload


class _Acquire:
    def __init__(self, conn: Any):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self, manager):
        self.manager = manager

    async def fetch(self, query: str, *params: Any):
        if "FROM prompts p" in query and "LIMIT" in query:
            rows = []
            for p in self.manager.items.values():
                rows.append(
                    {
                        "id": p.id,
                        "name": p.name,
                        "category": p.category,
                        "subcategory": p.subcategory,
                        "version": p.version,
                        "content": p.content,
                        "variables": json.dumps([asdict(v) for v in p.variables]),
                        "metadata": json.dumps(p.metadata),
                        "is_active": p.is_active,
                        "is_latest": p.is_latest,
                        "priority": p.priority,
                        "performance_score": p.performance_score,
                        "usage_count": p.usage_count,
                        "success_count": p.success_count,
                        "created_at": p.created_at.isoformat(),
                        "updated_at": p.updated_at.isoformat(),
                        "created_by": p.created_by,
                        "updated_by": p.updated_by,
                        "tags": p.tags,
                    }
                )
            return rows
        if "FROM prompt_usage_logs" in query:
            return []
        if "FROM prompt_versions" in query:
            return []
        return []

    async def fetchval(self, query: str, *params: Any):
        if "COUNT(DISTINCT p.id)" in query:
            return len(self.manager.items)
        return 0


class _FakePool:
    def __init__(self, manager):
        self.conn = _FakeConn(manager)

    def acquire(self):
        return _Acquire(self.conn)


class _FakePromptManager:
    def __init__(self):
        self.items: dict[UUID, _PromptDTO] = {}
        self.db_pool = _FakePool(self)

    async def create_prompt(self, **kwargs):
        pid = uuid4()
        now = datetime.now(UTC)
        prompt = _PromptDTO(
            id=pid,
            name=kwargs["name"],
            category=kwargs["category"],
            subcategory=kwargs.get("subcategory"),
            version=kwargs.get("version", "1.0.0"),
            content=kwargs["content"],
            variables=kwargs.get("variables") or [],
            metadata=kwargs.get("metadata") or {},
            is_active=True,
            is_latest=True,
            priority=kwargs.get("priority", 0),
            performance_score=0.0,
            usage_count=0,
            success_count=0,
            created_at=now,
            updated_at=now,
            created_by=kwargs.get("created_by"),
            updated_by=None,
            tags=kwargs.get("tags") or [],
        )
        self.items[pid] = prompt
        return prompt

    async def update_prompt(self, prompt_id, **kwargs):
        prompt = self.items[prompt_id]
        if kwargs.get("content") is not None:
            prompt.content = kwargs["content"]
        if kwargs.get("updated_by") is not None:
            prompt.updated_by = kwargs["updated_by"]
        prompt.updated_at = datetime.now(UTC)
        return prompt

    async def _get_prompt_by_id(self, prompt_id):
        return self.items.get(prompt_id)

    async def get_prompt_performance(self, prompt_id):
        if prompt_id not in self.items:
            return {}
        return {"usage_count": 0, "success_count": 0}

    async def record_usage_log(self, usage_log):
        return None


@pytest.mark.asyncio
async def test_prompt_api_create_update_list_flow():
    manager = _FakePromptManager()

    app = FastAPI()
    app.include_router(router)

    async def _override_manager():
        return manager

    app.dependency_overrides[get_prompt_manager] = _override_manager

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        create_resp = await client.post(
            "/api/prompts/",
            json={
                "name": "construction_rag_grounded_qa",
                "category": "rag",
                "content": "answer: {{ query }}",
                "created_by": "qa",
            },
        )
    assert create_resp.status_code == 200
    created = create_resp.json()["prompt"]
    prompt_id = created["id"]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        update_resp = await client.put(
            f"/api/prompts/{prompt_id}",
            json={"content": "patched {{ query }}", "updated_by": "qa2"},
        )
    assert update_resp.status_code == 200
    assert update_resp.json()["prompt"]["updated_by"] == "qa2"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        list_resp = await client.get("/api/prompts/")
    assert list_resp.status_code == 200
    payload = list_resp.json()
    assert payload["pagination"]["total"] == 1
    assert payload["data"][0]["name"] == "construction_rag_grounded_qa"
