from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.api.prompt_routes import get_prompt_manager, router


class _FakeManager:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.experiment_id = uuid4()
        self.base_experiment = {
            "id": str(self.experiment_id),
            "name": "rag_grounded_qa_exp_v2",
            "description": "rollout v2",
            "prompt_a_id": str(uuid4()),
            "prompt_b_id": str(uuid4()),
            "traffic_split": 0.9,
            "status": "active",
            "metrics": {"target": "success_rate"},
            "created_at": datetime(2026, 2, 10, tzinfo=timezone.utc).isoformat(),
            "created_by": "qa",
            "updated_at": datetime(2026, 2, 10, tzinfo=timezone.utc).isoformat(),
            "prompt_name": "construction_rag_grounded_qa",
            "prompt_category": "rag",
            "prompt_a_version": "1.0.0",
            "prompt_b_version": "1.1.0",
        }

    async def create_experiment(self, **kwargs):
        self.calls.append(("create_experiment", kwargs))
        payload = dict(self.base_experiment)
        payload["traffic_split"] = kwargs["traffic_split"]
        payload["name"] = kwargs["name"]
        return payload

    async def list_experiments(self, **kwargs):
        self.calls.append(("list_experiments", kwargs))
        return [dict(self.base_experiment)], 1

    async def get_experiment(self, experiment_id: UUID):
        self.calls.append(("get_experiment", {"experiment_id": experiment_id}))
        if experiment_id != self.experiment_id:
            return None
        return dict(self.base_experiment)

    async def update_experiment_traffic(self, **kwargs):
        self.calls.append(("update_experiment_traffic", kwargs))
        if kwargs["experiment_id"] != self.experiment_id:
            return None
        payload = dict(self.base_experiment)
        payload["traffic_split"] = kwargs["traffic_split"]
        return payload

    async def update_experiment_status(self, **kwargs):
        self.calls.append(("update_experiment_status", kwargs))
        if kwargs["experiment_id"] != self.experiment_id:
            return None
        payload = dict(self.base_experiment)
        payload["status"] = kwargs["status"]
        return payload


@pytest.mark.asyncio
async def test_prompt_experiment_routes_contract():
    manager = _FakeManager()
    app = FastAPI()
    app.include_router(router)

    async def _override_manager():
        return manager

    app.dependency_overrides[get_prompt_manager] = _override_manager

    create_payload = {
        "name": "rag_grounded_qa_exp_v2",
        "description": "rollout v2",
        "prompt_a_id": manager.base_experiment["prompt_a_id"],
        "prompt_b_id": manager.base_experiment["prompt_b_id"],
        "traffic_split": 0.9,
        "metrics": {"target": "success_rate"},
        "created_by": "qa",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        create_resp = await client.post("/api/prompts/experiments", json=create_payload)
        list_resp = await client.get(
            "/api/prompts/experiments",
            params={"status": "active", "category": "rag", "page": 1, "size": 20},
        )
        detail_resp = await client.get(f"/api/prompts/experiments/{manager.experiment_id}")
        traffic_resp = await client.patch(
            f"/api/prompts/experiments/{manager.experiment_id}/traffic",
            json={"traffic_split": 0.7},
        )
        status_resp = await client.patch(
            f"/api/prompts/experiments/{manager.experiment_id}/status",
            json={"status": "paused"},
        )

    assert create_resp.status_code == 200
    assert create_resp.json()["success"] is True
    assert create_resp.json()["experiment"]["traffic_split"] == 0.9

    assert list_resp.status_code == 200
    list_payload = list_resp.json()
    assert list_payload["success"] is True
    assert list_payload["pagination"]["total"] == 1
    assert len(list_payload["data"]) == 1

    assert detail_resp.status_code == 200
    assert detail_resp.json()["experiment"]["id"] == str(manager.experiment_id)

    assert traffic_resp.status_code == 200
    assert traffic_resp.json()["experiment"]["traffic_split"] == 0.7

    assert status_resp.status_code == 200
    assert status_resp.json()["experiment"]["status"] == "paused"

    assert manager.calls[0][0] == "create_experiment"
    assert manager.calls[1][0] == "list_experiments"
    assert manager.calls[2][0] == "get_experiment"
    assert manager.calls[3][0] == "update_experiment_traffic"
    assert manager.calls[4][0] == "update_experiment_status"
