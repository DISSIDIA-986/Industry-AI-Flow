from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.services.prompt_manager import PromptManager


class _Acquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self):
        self.a_id = uuid4()
        self.b_id = uuid4()

    async def fetchrow(self, query, *params):
        if "FROM prompt_experiments pe" in query:
            return {
                "id": uuid4(),
                "a_id": self.a_id,
                "b_id": self.b_id,
                "traffic_split": 0.1,
            }
        if "WHERE p.id = $1" in query:
            target_id = params[0]
            return {
                "id": target_id,
                "name": "construction_rag_grounded_qa",
                "category": "rag",
                "subcategory": None,
                "version": "1.1.0" if target_id == self.b_id else "1.0.0",
                "content": "answer with {{ query }}",
                "variables": json.dumps([]),
                "metadata": json.dumps({}),
                "is_active": True,
                "is_latest": True,
                "priority": 10,
                "performance_score": 0.9,
                "usage_count": 0,
                "success_count": 0,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "created_by": "qa",
                "updated_by": "qa",
                "tags": ["rag"],
            }
        return None


class _FakePool:
    def __init__(self):
        self.conn = _FakeConn()

    def acquire(self):
        return _Acquire(self.conn)


@pytest.mark.asyncio
async def test_experiment_allocation_uses_deterministic_allocator(monkeypatch):
    manager = PromptManager(_FakePool())

    # If random allocation was still used, split=0.1 + random=0 would pick A.
    monkeypatch.setattr("random.random", lambda: 0.0)

    from backend.services.workflows.prompting.ab_allocator import ABAllocator

    monkeypatch.setattr(ABAllocator, "allocate", lambda self, key, split=0.5: "B")

    prompt = await manager._get_prompt_with_experiment(
        name="construction_rag_grounded_qa",
        category="rag",
        context={"session_id": "s-001"},
    )

    assert prompt is not None
    assert prompt.id == manager.db_pool.conn.b_id
    assert prompt.version == "1.1.0"
