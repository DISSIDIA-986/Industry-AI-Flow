from __future__ import annotations

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
        self.prompt_a_id = uuid4()
        self.prompt_b_id = uuid4()
        self.experiment_id = uuid4()
        self.experiment = {
            "id": self.experiment_id,
            "name": "rag_grounded_qa_exp_v2",
            "description": "rollout",
            "prompt_a_id": self.prompt_a_id,
            "prompt_b_id": self.prompt_b_id,
            "traffic_split": 0.9,
            "status": "active",
            "metrics": {"target": "success_rate"},
            "created_at": datetime(2026, 2, 10, tzinfo=timezone.utc),
            "created_by": "qa",
            "updated_at": datetime(2026, 2, 10, tzinfo=timezone.utc),
        }

    async def fetchrow(self, query, *params):
        if "SELECT id, name, category" in query and "FROM prompts" in query:
            prompt_id = params[0]
            if prompt_id == self.prompt_a_id:
                return {
                    "id": prompt_id,
                    "name": "construction_rag_grounded_qa",
                    "category": "rag",
                }
            if prompt_id == self.prompt_b_id:
                return {
                    "id": prompt_id,
                    "name": "construction_rag_grounded_qa",
                    "category": "rag",
                }
            return None

        if "INSERT INTO prompt_experiments" in query:
            self.experiment.update(
                {
                    "name": params[0],
                    "description": params[1],
                    "prompt_a_id": params[2],
                    "prompt_b_id": params[3],
                    "traffic_split": params[4],
                    "metrics": {"target": "success_rate"},
                    "created_by": params[6],
                }
            )
            return dict(self.experiment)

        if "FROM prompt_experiments pe" in query and "WHERE pe.id = $1" in query:
            if params[0] != self.experiment_id:
                return None
            row = dict(self.experiment)
            row.update(
                {
                    "prompt_name": "construction_rag_grounded_qa",
                    "prompt_category": "rag",
                    "prompt_a_version": "1.0.0",
                    "prompt_b_version": "1.1.0",
                }
            )
            return row

        if "UPDATE prompt_experiments" in query and "SET traffic_split" in query:
            if params[0] != self.experiment_id:
                return None
            self.experiment["traffic_split"] = params[1]
            return dict(self.experiment)

        if "UPDATE prompt_experiments" in query and "SET status" in query:
            if params[0] != self.experiment_id:
                return None
            self.experiment["status"] = params[1]
            return dict(self.experiment)

        return None

    async def fetch(self, query, *params):
        if (
            "FROM prompt_experiments pe" in query
            and "ORDER BY pe.created_at DESC" in query
        ):
            row = dict(self.experiment)
            row.update(
                {
                    "prompt_name": "construction_rag_grounded_qa",
                    "prompt_category": "rag",
                    "prompt_a_version": "1.0.0",
                    "prompt_b_version": "1.1.0",
                }
            )
            return [row]
        return []

    async def fetchval(self, query, *params):
        if "COUNT(*)" in query and "FROM prompt_experiments pe" in query:
            return 1
        return 0


class _FakePool:
    def __init__(self):
        self.conn = _FakeConn()

    def acquire(self):
        return _Acquire(self.conn)


@pytest.mark.asyncio
async def test_prompt_experiment_manager_create_list_update_flow():
    pool = _FakePool()
    manager = PromptManager(pool)

    created = await manager.create_experiment(
        name="rag_grounded_qa_exp_v2",
        description="rollout",
        prompt_a_id=pool.conn.prompt_a_id,
        prompt_b_id=pool.conn.prompt_b_id,
        traffic_split=0.9,
        metrics={"target": "success_rate"},
        created_by="qa",
    )
    assert created["name"] == "rag_grounded_qa_exp_v2"
    assert created["traffic_split"] == 0.9
    assert created["status"] == "active"

    experiments, total = await manager.list_experiments(
        status="active", category="rag", limit=20, offset=0
    )
    assert total == 1
    assert experiments[0]["prompt_name"] == "construction_rag_grounded_qa"
    assert experiments[0]["prompt_category"] == "rag"

    updated_traffic = await manager.update_experiment_traffic(
        pool.conn.experiment_id, 0.7
    )
    assert updated_traffic is not None
    assert updated_traffic["traffic_split"] == 0.7

    updated_status = await manager.update_experiment_status(
        pool.conn.experiment_id, "paused"
    )
    assert updated_status is not None
    assert updated_status["status"] == "paused"

    detail = await manager.get_experiment(pool.conn.experiment_id)
    assert detail is not None
    assert detail["prompt_a_version"] == "1.0.0"
    assert detail["prompt_b_version"] == "1.1.0"


@pytest.mark.asyncio
async def test_prompt_experiment_manager_validates_inputs():
    manager = PromptManager(_FakePool())
    same_id = uuid4()

    with pytest.raises(ValueError):
        await manager.create_experiment(
            name="bad",
            prompt_a_id=same_id,
            prompt_b_id=same_id,
            traffic_split=0.5,
        )

    with pytest.raises(ValueError):
        await manager.update_experiment_traffic(uuid4(), 1.0)

    with pytest.raises(ValueError):
        await manager.update_experiment_status(uuid4(), "unknown")
