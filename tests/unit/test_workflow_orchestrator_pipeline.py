from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.services.workflows.graph import run_workflow_pipeline
from backend.services.workflows.orchestrator import DefaultWorkflowRunner, WorkflowOrchestrator


@dataclass
class _PromptInfo:
    id: str
    name: str
    category: str
    version: str


class _FakePromptManager:
    async def get_prompt(self, **kwargs):
        info = _PromptInfo(
            id=str(uuid4()),
            name=kwargs["name"],
            category=kwargs["category"],
            version="1.0.1",
        )
        rendered = f"SYSTEM::{kwargs['variables']['query']}"
        return info, rendered


class _FakeRetriever:
    async def retrieve(self, query: str, top_k: int, metadata: dict):
        del query, top_k, metadata
        return [
            {"content": "B context", "score": 0.2},
            {"content": "A context", "score": 0.9},
        ]


class _FakeCodeManager:
    def execute_code(self, **kwargs):
        del kwargs
        return {
            "success": True,
            "stdout": "code_ok",
            "stderr": "",
            "error": None,
            "exit_code": 0,
            "execution_time": 0.03,
            "visualizations": [],
            "output_files": {},
        }


class _FakeCostEstimationService:
    def predict_project(self, project, confidence_quantile=0.9):
        del project, confidence_quantile
        return {
            "predicted_cost_overrun_pct": 12.5,
            "predicted_actual_cost_cad": 1125000.0,
            "estimated_cost_cad": 1000000.0,
            "prediction_interval_cad": {
                "confidence_quantile": 0.9,
                "lower": 980000.0,
                "upper": 1260000.0,
            },
            "uncertainty": {"ape_quantile": 0.12},
            "unknown_categories": {},
        }


@pytest.mark.asyncio
async def test_workflow_pipeline_full_path():
    services = SimpleNamespace(
        retriever=_FakeRetriever(),
        prompt_manager=_FakePromptManager(),
        code_execution_manager=_FakeCodeManager(),
    )
    state = {
        "query": "Run python analysis for csv",
        "metadata": {
            "requested_route_mode": "cloud_only",
            "monthly_spend_usd": 20,
            "monthly_budget_usd": 100,
            "requires_code_execution": True,
            "code_to_execute": "print('ok')",
        },
        "metrics": {},
    }

    updated = await run_workflow_pipeline(state, services)

    assert updated["intent"] == "code_execution"
    assert updated["retrieved_context"][0]["content"] == "A context"
    assert updated["prompt_meta"]["name"] == "code_exec_data_analysis_explainer"
    assert updated["route_mode"] == "cloud_only"
    assert updated["provider_used"] == "cloud"
    assert updated["metadata"]["code_exec_status"] == "ok"
    assert "Code output: code_ok" in (updated["response"] or "")
    assert updated["metrics"]["retrieved_count"] == 2
    assert updated["metrics"]["reranked_count"] == 2
    assert updated["metrics"]["groundedness_score"] >= 0.4
    assert "node_latency_ms" in updated["metrics"]
    assert "intent_node" in updated["metrics"]["node_latency_ms"]
    assert "response_node" in updated["metadata"]["completed_nodes"]


@pytest.mark.asyncio
async def test_workflow_pipeline_cost_estimation_shortcut():
    services = SimpleNamespace(cost_estimation_service=_FakeCostEstimationService())
    state = {
        "query": "please provide a cost estimate with estimated cost 1000000 and sqft 12000",
        "metadata": {},
        "metrics": {},
    }

    updated = await run_workflow_pipeline(state, services)

    assert updated["intent"] == "cost_estimation"
    assert "Cost estimation result" in (updated["response"] or "")
    assert updated["metadata"]["cost_estimation_status"] == "ok"
    assert updated["metadata"]["shortcut_response"] is True
    assert updated["metrics"]["cost_estimation_executed"] is True


@pytest.mark.asyncio
async def test_workflow_pipeline_safety_block():
    services = SimpleNamespace()
    state = {"query": "please run rm -rf / on this host", "metadata": {}, "metrics": {}}

    updated = await run_workflow_pipeline(state, services)

    assert updated["error"] == "Request blocked by safety policy"
    assert updated["metadata"]["safety_status"] == "blocked"
    assert "could not be processed" in (updated["response"] or "").lower()


@pytest.mark.asyncio
async def test_workflow_orchestrator_sets_latency_metric():
    orchestrator = WorkflowOrchestrator(services=SimpleNamespace())
    state = {"query": "What is CSA A23.1?", "metadata": {}, "metrics": {}}

    updated = await orchestrator.run(state)

    assert "orchestrator_latency_ms" in updated["metrics"]
    assert updated["response"]


@pytest.mark.asyncio
async def test_default_workflow_runner_injects_prompt_experiments_flag(monkeypatch):
    from backend.services.workflows import orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module.settings,
        "prompt_experiments_enabled",
        True,
    )
    runner = DefaultWorkflowRunner(orchestrator=WorkflowOrchestrator(services=SimpleNamespace()))

    result = await runner.run_workflow(
        query="Summarize concrete standard",
        session_id="s-rollback",
    )

    assert result["success"] is True
    assert result["metadata"]["prompt_experiments_enabled"] is True
