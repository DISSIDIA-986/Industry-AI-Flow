from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.services.rag_engine as rag_engine_module
from backend.api.workflow_query_routes import (
    get_workflow_runner,
    router as workflow_router,
)
from backend.services.cost_estimation_service import (
    CostEstimationService,
    train_cost_estimation_model,
)
from backend.services.workflows.graph import run_workflow_pipeline


def _build_training_dataset(rows: int = 60, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    estimated = rng.uniform(800_000, 2_000_000, size=rows)
    overrun = rng.normal(loc=9.0, scale=2.0, size=rows)
    actual = estimated * (1.0 + overrun / 100.0)
    return pd.DataFrame(
        {
            "sqft": rng.integers(12_000, 95_000, size=rows),
            "floors": rng.integers(2, 35, size=rows),
            "num_units": rng.integers(10, 220, size=rows),
            "planned_duration_weeks": rng.uniform(26, 130, size=rows),
            "estimated_cost_cad": estimated,
            "contractor_rating": rng.uniform(2.4, 4.8, size=rows),
            "complexity_score": rng.integers(2, 10, size=rows),
            "team_experience_years": rng.uniform(4, 25, size=rows),
            "num_change_orders": rng.integers(0, 30, size=rows),
            "weather_risk_factor": rng.uniform(0.1, 2.0, size=rows),
            "material_volatility": rng.uniform(0.1, 1.7, size=rows),
            "num_subcontractors": rng.integers(2, 16, size=rows),
            "budget_pressure": rng.uniform(0.2, 2.1, size=rows),
            "risk_score": rng.uniform(0.3, 3.2, size=rows),
            "risk_score_original": rng.uniform(0.3, 3.2, size=rows),
            "project_type": rng.choice(
                ["commercial_office", "commercial_retail", "industrial_warehouse"],
                size=rows,
            ),
            "location": rng.choice(["Toronto", "Calgary", "Vancouver"], size=rows),
            "cost_overrun_pct": overrun,
            "actual_cost_cad": actual,
        }
    )


def test_tdo_rag_ingest_retrieve_generate_baseline(monkeypatch) -> None:
    evidence: dict = {}

    class _FakeVectorStore:
        def __init__(self) -> None:
            self.records: list[dict] = []

        def store_document_with_chunks(
            self,
            filename: str,
            filepath: str,
            chunks: list[str],
            embeddings: list[list[float]],
        ) -> str:
            evidence["stored_filename"] = filename
            evidence["stored_filepath"] = filepath
            evidence["stored_chunk_count"] = len(chunks)
            evidence["stored_embedding_count"] = len(embeddings)
            self.records.append(
                {
                    "filename": filename,
                    "filepath": filepath,
                    "chunks": chunks,
                }
            )
            return "stored-doc-1"

        def similarity_search(
            self, query_embedding: list[float], top_k: int = 3
        ) -> list[dict]:
            evidence["query_embedding_dim"] = len(query_embedding)
            evidence["top_k"] = top_k
            first_chunk = self.records[0]["chunks"][0]
            return [
                {
                    "chunk_id": "chunk-1",
                    "doc_id": "stored-doc-1",
                    "content": first_chunk,
                    "distance": 0.01,
                    "filename": "spec.md",
                }
            ]

    class _FakeLlmClient:
        def generate(self, prompt: str, temperature=None, max_tokens=None) -> str:
            del temperature, max_tokens
            evidence["prompt_contains_question"] = "防火等级" in prompt
            return "根据文档，钢梁需要满足防火等级要求。"

    monkeypatch.setattr(rag_engine_module, "VectorStore", _FakeVectorStore)
    monkeypatch.setattr(rag_engine_module, "get_llm_client", lambda: _FakeLlmClient())
    monkeypatch.setattr(
        rag_engine_module,
        "get_backend_status",
        lambda: {"backend": "mock"},
    )
    monkeypatch.setattr(
        rag_engine_module,
        "embed_query_text",
        lambda _: [0.1, 0.2, 0.3],
    )
    monkeypatch.setattr(rag_engine_module.settings, "enable_conversation_memory", False)
    monkeypatch.setattr(rag_engine_module.settings, "enable_safety_guard", False)
    monkeypatch.setattr(rag_engine_module.settings, "top_k", 2)
    monkeypatch.setattr(
        "backend.services.core.embedder.embed_texts",
        lambda texts: [[0.2, 0.3, 0.4] for _ in texts],
    )

    rag = rag_engine_module.SimpleRAG(
        use_hybrid_search=False,
        use_reranker=False,
        enable_feedback=False,
    )
    ok = rag.add_documents(
        [
            {
                "content": "钢梁防火等级应符合规范，建议至少满足 2 小时耐火要求。",
                "metadata": {"doc_id": "manual-doc-1", "source": "spec.md"},
            }
        ]
    )
    assert ok is True

    response = rag.query("这个钢梁应该满足什么防火等级？", top_k=1)

    assert UUID(response["query_id"])
    assert response["sources"] == ["stored-doc-1"]
    assert response["retrieved_chunks"]
    assert response["answer"]
    assert evidence["stored_chunk_count"] >= 1
    assert evidence["stored_chunk_count"] == evidence["stored_embedding_count"]
    assert evidence["query_embedding_dim"] == 3
    assert evidence["prompt_contains_question"] is True


def test_tdo_rag_delete_removes_retrieval_baseline(monkeypatch) -> None:
    class _FakeVectorStore:
        def __init__(self) -> None:
            self.rows: dict[str, list[str]] = {}

        def store_document_with_chunks(
            self,
            filename: str,
            filepath: str,
            chunks: list[str],
            embeddings: list[list[float]],
        ) -> str:
            del filename, filepath, embeddings
            self.rows["manual-doc-delete"] = list(chunks)
            return "manual-doc-delete"

        def similarity_search(
            self, query_embedding: list[float], top_k: int = 3
        ) -> list[dict]:
            del query_embedding, top_k
            if "manual-doc-delete" not in self.rows:
                return []
            return [
                {
                    "chunk_id": "chunk-1",
                    "doc_id": "manual-doc-delete",
                    "content": self.rows["manual-doc-delete"][0],
                    "distance": 0.01,
                    "filename": "spec-delete.md",
                }
            ]

        def delete_by_doc_id(self, doc_id: str) -> None:
            self.rows.pop(doc_id, None)

    class _FakeLlmClient:
        def generate(self, prompt: str, temperature=None, max_tokens=None) -> str:
            del prompt, temperature, max_tokens
            return "ok"

    monkeypatch.setattr(rag_engine_module, "VectorStore", _FakeVectorStore)
    monkeypatch.setattr(rag_engine_module, "get_llm_client", lambda: _FakeLlmClient())
    monkeypatch.setattr(
        rag_engine_module,
        "get_backend_status",
        lambda: {"backend": "mock"},
    )
    monkeypatch.setattr(
        rag_engine_module,
        "embed_query_text",
        lambda _: [0.1, 0.2, 0.3],
    )
    monkeypatch.setattr(rag_engine_module.settings, "enable_conversation_memory", False)
    monkeypatch.setattr(rag_engine_module.settings, "enable_safety_guard", False)
    monkeypatch.setattr(
        "backend.services.core.embedder.embed_texts",
        lambda texts: [[0.2, 0.3, 0.4] for _ in texts],
    )

    rag = rag_engine_module.SimpleRAG(
        use_hybrid_search=False,
        use_reranker=False,
        enable_feedback=False,
    )
    rag.add_documents(
        [
            {
                "content": "删除前可检索的规范片段。",
                "metadata": {"doc_id": "manual-doc-delete", "source": "spec-delete.md"},
            }
        ]
    )
    before_delete = rag.query("删除前", top_k=1)
    assert before_delete["sources"] == ["manual-doc-delete"]

    deleted = rag.delete_document("manual-doc-delete")
    assert deleted is True

    after_delete = rag.query("删除后", top_k=1)
    assert after_delete["sources"] == []
    assert after_delete["retrieved_chunks"] == []


def test_tdo_cost_estimation_train_predict_baseline(tmp_path: Path) -> None:
    dataset = _build_training_dataset()
    dataset_path = tmp_path / "cost_train.csv"
    model_path = tmp_path / "cost_model.json"
    dataset.to_csv(dataset_path, index=False)

    training = train_cost_estimation_model(
        dataset_path=dataset_path,
        output_model_path=model_path,
        ridge_alpha=8.0,
        folds=3,
        random_seed=11,
    )

    service = CostEstimationService(model_path=model_path)
    sample_project = dataset.iloc[0].to_dict()
    pred_1 = service.predict_project(sample_project, confidence_quantile=0.9)
    pred_2 = service.predict_project(sample_project, confidence_quantile=0.9)

    assert training["success"] is True
    assert training["training_rows"] == len(dataset)
    assert service.metadata()["loaded"] is True
    assert pred_1 == pred_2
    assert pred_1["predicted_actual_cost_cad"] > 0
    assert (
        pred_1["prediction_interval_cad"]["lower"]
        <= pred_1["predicted_actual_cost_cad"]
        <= pred_1["prediction_interval_cad"]["upper"]
    )


def test_tdo_code_generation_execution_baseline() -> None:
    class _FakeCodeManager:
        def execute_code(self, **kwargs):
            del kwargs
            return {
                "success": True,
                "stdout": "analysis_ok",
                "stderr": "",
                "error": None,
                "exit_code": 0,
                "execution_time": 0.02,
                "visualizations": [],
                "output_files": {},
            }

    state = {
        "query": "Please run python script to analyze this csv file",
        "metadata": {
            "requires_code_execution": True,
            "code_to_execute": "print('analysis_ok')",
            "code_execution_mode": "auto",
        },
        "metrics": {},
    }
    services = SimpleNamespace(code_execution_manager=_FakeCodeManager())

    updated = asyncio.run(run_workflow_pipeline(state, services))

    assert updated["intent"] == "code_execution"
    assert updated["metadata"]["code_exec_status"] == "ok"
    assert updated["metadata"]["code_exec_result"]["stdout"] == "analysis_ok"
    assert "Code output: analysis_ok" in (updated.get("response") or "")


def test_tdo_frontend_api_workflow_roundtrip_baseline() -> None:
    class _FakeRunner:
        async def run_workflow(
            self,
            query: str,
            session_id: str,
            user_id=None,
            thread_id=None,
            route_mode=None,
        ):
            del user_id, thread_id
            return {
                "success": True,
                "agent_response": f"handled:{query}",
                "intent_result": {"intent": "knowledge_retrieval"},
                "metadata": {
                    "workflow_runner": "tdo_fake_runner",
                    "provider_used": "local",
                    "route_mode": route_mode or "local_only",
                    "session_id": session_id,
                },
                "error": None,
            }

    app = FastAPI()
    app.include_router(workflow_router)

    async def _override_runner():
        return _FakeRunner()

    app.dependency_overrides[get_workflow_runner] = _override_runner
    client = TestClient(app)

    response = client.post(
        "/api/v1/workflow/query",
        json={"query": "frontend baseline ping", "session_id": "tdo-session-1"},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["response"] == "handled:frontend baseline ping"
    assert payload["metadata"]["workflow_runner"] == "tdo_fake_runner"
    assert payload["metadata"]["trace_id"] == payload["trace_id"]
    assert payload["metadata"]["session_id"] == "tdo-session-1"
