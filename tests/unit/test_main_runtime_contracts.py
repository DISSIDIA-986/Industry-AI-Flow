from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

import backend.main as main_module
from backend.main import app


@pytest.mark.asyncio
async def test_data_analyze_rejects_untrusted_absolute_path(monkeypatch):
    recorded: list[dict[str, Any]] = []

    def _fake_audit(**kwargs):
        recorded.append(kwargs)

    monkeypatch.setattr(main_module.audit_logger, "log_event", _fake_audit)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/data/analyze",
            json={"data_file": "/tmp/not_allowed/data.csv", "analysis_type": "eda"},
        )

    assert resp.status_code == 400
    assert "outside allowed upload locations" in resp.json()["detail"]
    assert recorded
    assert recorded[-1]["action"] == "data.analyze"
    assert recorded[-1]["status"] == "error"


@pytest.mark.asyncio
async def test_data_analyze_records_error_audit_when_tool_returns_business_failure(
    monkeypatch,
):
    recorded: list[dict[str, Any]] = []

    def _fake_audit(**kwargs):
        recorded.append(kwargs)

    def _fake_invoke(payload):
        return {
            "success": False,
            "error": "mocked failure",
            "analysis_type": payload.get("analysis_type", "eda"),
        }

    class _FakeTool:
        @staticmethod
        def invoke(payload):
            return _fake_invoke(payload)

    monkeypatch.setattr(main_module.audit_logger, "log_event", _fake_audit)
    monkeypatch.setattr("backend.tools.data_analysis.data_analysis_tool", _FakeTool())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/data/analyze",
            json={"data_file": "housing.csv", "analysis_type": "eda"},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is False
    assert payload["error"] == "mocked failure"
    assert recorded
    assert recorded[-1]["action"] == "data.analyze"
    assert recorded[-1]["status"] == "error"


@pytest.mark.asyncio
async def test_unified_query_records_error_audit_when_business_result_fails(monkeypatch):
    recorded: list[dict[str, Any]] = []

    class _FakeOrchestrator:
        def process_request(self, question: str, **kwargs):
            return {
                "success": False,
                "error": "mock unified failure",
                "question": question,
            }

    def _fake_audit(**kwargs):
        recorded.append(kwargs)

    monkeypatch.setattr(main_module, "get_unified_orchestrator", lambda: _FakeOrchestrator())
    monkeypatch.setattr(main_module.audit_logger, "log_event", _fake_audit)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/unified/query",
            json={"question": "test unified request"},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is False
    assert recorded
    assert recorded[-1]["action"] == "unified.query"
    assert recorded[-1]["status"] == "error"


@pytest.mark.asyncio
async def test_health_reports_execution_provider_health_snapshot(monkeypatch):
    class _FakeManager:
        def health_snapshot(self, mode: str = "docker") -> dict:
            return {
                "healthy": False,
                "mode": mode,
                "selected_provider": "docker",
                "providers": {
                    "docker": {"provider": "docker", "healthy": False, "status": "daemon_unreachable"},
                    "ppio": None,
                },
            }

    monkeypatch.setattr(
        "backend.services.code_executor.get_code_execution_manager",
        lambda: _FakeManager(),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/v1/health")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["docker_available"] is False
    assert payload["code_execution_available"] is False
    assert payload["code_execution"]["providers"]["docker"]["status"] == "daemon_unreachable"


@pytest.mark.asyncio
async def test_health_reports_embedding_backend_status(monkeypatch):
    monkeypatch.setattr(
        "backend.services.core.embedder.embedding_backend_status",
        lambda: {
            "ready": False,
            "backend": "fallback_hash",
            "fallback_active": True,
            "reason": "sentence_transformers_unavailable",
            "loaded": False,
            "model": "mock-model",
            "dimension": 768,
        },
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/v1/health")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["embedding"]["backend"] == "fallback_hash"
    assert payload["embedding"]["fallback_active"] is True
