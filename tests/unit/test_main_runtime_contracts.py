from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

import backend.main as main_module
from backend.main import app
from backend.services.database.driver_compat import connect as connect_db
from backend.services.language_policy import RAG_CHINESE_QUERY_UNSUPPORTED


def _cleanup_uploaded_documents_index(*tenant_ids: str) -> None:
    main_module._ensure_uploaded_documents_index_table()
    conn = connect_db(main_module.settings.database_url)
    cur = conn.cursor()
    file_paths: list[str] = []
    try:
        for tenant_id in tenant_ids:
            cur.execute(
                "SELECT file_path FROM uploaded_documents_index WHERE tenant_id = %s",
                (tenant_id,),
            )
            file_paths.extend(str(row[0]) for row in cur.fetchall() if row and row[0])
            cur.execute(
                "DELETE FROM uploaded_documents_index WHERE tenant_id = %s",
                (tenant_id,),
            )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    for file_path in file_paths:
        try:
            resolved = main_module._normalize_file_path(file_path)
            if resolved.exists():
                resolved.unlink()
        except OSError:
            continue


@pytest.mark.asyncio
async def test_documents_list_returns_empty_array_when_no_uploads():
    tenant_id = "tenant-doc-empty"
    _cleanup_uploaded_documents_index(tenant_id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/v1/documents", headers={"X-Tenant-ID": tenant_id})

    assert resp.status_code == 200
    assert resp.json() == []
    _cleanup_uploaded_documents_index(tenant_id)


@pytest.mark.asyncio
async def test_documents_list_falls_back_to_indexed_docs_for_default_tenant(monkeypatch):
    tenant_id = main_module.settings.default_tenant_id or "public"
    _cleanup_uploaded_documents_index(tenant_id)

    indexed_docs = [
        {
            "id": "seed-doc-1",
            "name": "seed_reference.pdf",
            "type": "PDF",
            "size": 1024,
            "uploaded_at": "2026-02-20T00:00:00+00:00",
            "status": "processed",
            "original_filename": "seed_reference.pdf",
            "file_path": "/tmp/seed_reference.pdf",
            "source": "vector_index",
        }
    ]
    monkeypatch.setattr(
        main_module,
        "_load_indexed_documents_fallback",
        lambda limit=200: indexed_docs,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/v1/documents", headers={"X-Tenant-ID": tenant_id})

    assert resp.status_code == 200
    assert resp.json() == indexed_docs
    _cleanup_uploaded_documents_index(tenant_id)


@pytest.mark.asyncio
async def test_documents_list_does_not_fallback_to_indexed_docs_for_non_default_tenant(
    monkeypatch,
):
    tenant_id = "tenant-doc-no-index-fallback"
    _cleanup_uploaded_documents_index(tenant_id)

    monkeypatch.setattr(
        main_module,
        "_load_indexed_documents_fallback",
        lambda limit=200: [{"id": "seed-doc-1"}],
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/v1/documents", headers={"X-Tenant-ID": tenant_id})

    assert resp.status_code == 200
    assert resp.json() == []
    _cleanup_uploaded_documents_index(tenant_id)


@pytest.mark.asyncio
async def test_documents_upload_then_list_returns_document_for_same_tenant():
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"
    _cleanup_uploaded_documents_index(tenant_a, tenant_b)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        upload = await client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "contract_note.txt",
                    b"scope and budget baseline",
                    "text/plain",
                )
            },
            headers={"X-Tenant-ID": tenant_a},
        )
        assert upload.status_code == 200

        tenant_a_docs = await client.get(
            "/api/v1/documents", headers={"X-Tenant-ID": tenant_a}
        )
        tenant_b_docs = await client.get(
            "/api/v1/documents", headers={"X-Tenant-ID": tenant_b}
        )

    assert tenant_a_docs.status_code == 200
    docs_payload = tenant_a_docs.json()
    assert isinstance(docs_payload, list)
    assert len(docs_payload) == 1
    assert docs_payload[0]["name"] == "contract_note.txt"
    assert docs_payload[0]["type"] == "TXT"
    assert docs_payload[0]["status"] == "processed"
    assert docs_payload[0]["size"] > 0

    assert tenant_b_docs.status_code == 200
    assert tenant_b_docs.json() == []
    _cleanup_uploaded_documents_index(tenant_a, tenant_b)


@pytest.mark.asyncio
async def test_documents_list_persists_after_metadata_cache_reset(monkeypatch):
    tenant_id = "tenant-doc-persist"
    _cleanup_uploaded_documents_index(tenant_id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        upload = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("restart_check.txt", b"persistence smoke", "text/plain")},
            headers={"X-Tenant-ID": tenant_id},
        )
        assert upload.status_code == 200

    monkeypatch.setattr(main_module, "_uploaded_documents_index_ready", False)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/v1/documents", headers={"X-Tenant-ID": tenant_id})

    assert resp.status_code == 200
    docs_payload = resp.json()
    assert len(docs_payload) == 1
    assert docs_payload[0]["name"] == "restart_check.txt"
    _cleanup_uploaded_documents_index(tenant_id)


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
async def test_unified_query_records_error_audit_when_business_result_fails(
    monkeypatch,
):
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

    monkeypatch.setattr(
        main_module, "get_unified_orchestrator", lambda: _FakeOrchestrator()
    )
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
                    "docker": {
                        "provider": "docker",
                        "healthy": False,
                        "status": "daemon_unreachable",
                    },
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
    assert (
        payload["code_execution"]["providers"]["docker"]["status"]
        == "daemon_unreachable"
    )


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


@pytest.mark.asyncio
async def test_rag_query_rejects_chinese_input():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/v1/rag/query",
            json={"question": "请总结招标文件", "top_k": 3},
        )

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == RAG_CHINESE_QUERY_UNSUPPORTED
    assert "English" in detail["message"]
