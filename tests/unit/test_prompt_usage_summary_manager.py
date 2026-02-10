from __future__ import annotations

from datetime import date
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
        self.last_calls = []

    async def fetchrow(self, query, *params):
        self.last_calls.append(("fetchrow", query, params))
        return {
            "prompt_count": 2,
            "usage_logs": 10,
            "success_logs": 8,
            "avg_execution_time_ms": 123.5,
            "total_tokens": 2048,
            "avg_feedback": 4.2,
        }

    async def fetch(self, query, *params):
        self.last_calls.append(("fetch", query, params))
        if "GROUP BY p.id, p.name, p.category" in query:
            return [
                {
                    "id": uuid4(),
                    "name": "construction_rag_grounded_qa",
                    "category": "rag",
                    "usage_count": 6,
                    "success_count": 5,
                    "avg_execution_time_ms": 120.0,
                    "total_tokens": 900,
                },
                {
                    "id": uuid4(),
                    "name": "alberta_ohs_compliance_check",
                    "category": "rag",
                    "usage_count": 4,
                    "success_count": 3,
                    "avg_execution_time_ms": 128.0,
                    "total_tokens": 700,
                },
            ]
        return [
            {
                "date": date(2026, 2, 10),
                "usage_count": 10,
                "success_count": 8,
                "avg_execution_time_ms": 123.5,
                "total_tokens": 2048,
            }
        ]


class _FakePool:
    def __init__(self):
        self.conn = _FakeConn()

    def acquire(self):
        return _Acquire(self.conn)


@pytest.mark.asyncio
async def test_prompt_usage_summary_manager_mapping():
    manager = PromptManager(_FakePool())
    summary = await manager.get_usage_summary(days=14, category="rag", top_limit=5)

    assert summary["window_days"] == 14
    assert summary["category"] == "rag"
    assert summary["totals"]["prompt_count"] == 2
    assert summary["totals"]["usage_logs"] == 10
    assert summary["totals"]["success_logs"] == 8
    assert summary["totals"]["success_rate"] == 0.8
    assert len(summary["top_prompts"]) == 2
    assert summary["top_prompts"][0]["usage_count"] == 6
    assert summary["daily"][0]["date"] == "2026-02-10"
