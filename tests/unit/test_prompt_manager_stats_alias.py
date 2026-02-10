from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from backend.services.prompt_manager import PromptManager


class _Acquire:
    def __init__(self, conn: Any):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    async def fetchrow(self, query: str, prompt_id):
        return {
            "usage_count": 12,
            "success_count": 10,
            "performance_score": 0.88,
            "total_logs": 12,
            "avg_execution_time": 132.0,
            "min_execution_time": 100,
            "max_execution_time": 220,
            "avg_user_feedback": 4.5,
            "total_tokens": 2048,
            "recent_success_count": 6,
            "recent_usage_count": 7,
        }


class _FakePool:
    def acquire(self):
        return _Acquire(_FakeConn())


@pytest.mark.asyncio
async def test_prompt_manager_stats_alias_mapping():
    manager = PromptManager(_FakePool())
    stats = await manager.get_prompt_performance(uuid4())

    assert stats["min_execution_time_ms"] == 100
    assert stats["max_execution_time_ms"] == 220
    assert stats["avg_execution_time_ms"] == 132.0
