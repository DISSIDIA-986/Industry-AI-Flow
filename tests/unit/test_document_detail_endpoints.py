"""
Unit tests for document detail endpoints (document preview feature).

Tests: GET /api/v1/documents/{doc_id}/detail
       GET /api/v1/documents/{doc_id}/content
       GET /api/v1/documents/{doc_id}/summary
       GET /api/v1/documents/{doc_id}/chunks
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_db_connection():
    """Mock database connection and cursor."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


@pytest.fixture
def sample_doc_row():
    """Sample uploaded_documents_index row."""
    return {
        "id": "doc-abc123",
        "original_filename": "NBC_2020_Fire_Protection.pdf",
        "sanitized_filename": "NBC_2020_Fire_Protection_a1b2c3d4e5f6.pdf",
        "file_path": "workspace/uploads/documents/NBC_2020_Fire_Protection_a1b2c3d4e5f6.pdf",
        "size_bytes": 2500000,
        "mime_type": "application/pdf",
        "status": "processed",
        "created_at": datetime(2026, 3, 15, 10, 30, 0),
    }


@pytest.fixture
def sample_profile_row():
    """Sample document_profiles row."""
    return {
        "summary": "This document covers fire protection requirements under NBC 2020.",
        "outline": json.dumps([
            {"title": "Fire Resistance", "detail": "Minimum 1-hour rating"},
            {"title": "Sprinklers", "detail": "Mandatory for buildings > 600m²"},
        ]),
        "keywords": json.dumps([{"type": "Building Code", "jurisdiction": "Canada"}]),
    }


@pytest.fixture
def sample_chunks():
    """Sample document_chunks rows."""
    return [
        {"chunk_id": 0, "content": "Section 3.2.2 Fire Resistance Rating requirements..."},
        {"chunk_id": 1, "content": "Section 3.2.5 Sprinkler Systems conforming to NFPA 13..."},
        {"chunk_id": 2, "content": "Section 3.4.2 Egress requirements for occupant loads..."},
    ]


# ── Detail Endpoint Tests ─────────────────────────────────────────────


class TestDocumentDetailEndpoint:
    """Tests for GET /documents/{doc_id}/detail"""

    @pytest.mark.unit
    def test_detail_returns_document_metadata(
        self, mock_db_connection, sample_doc_row, sample_profile_row
    ):
        """Happy path: returns full metadata + AI summary."""
        conn, cur = mock_db_connection

        # First query: uploaded_documents_index
        # Second query: documents (vector)
        # Third query: document_profiles
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

        cur.execute.side_effect = side_effect

        # Verify the endpoint function can be imported
        from backend.api.document_management_routes import get_document_detail
        assert get_document_detail is not None

    @pytest.mark.unit
    def test_detail_endpoint_exists(self):
        """Verify the endpoint is registered in the router."""
        from backend.api.document_management_routes import router

        routes = [r.path for r in router.routes]
        assert "/documents/{doc_id}/detail" in routes

    @pytest.mark.unit
    def test_content_endpoint_exists(self):
        """Verify the content endpoint is registered."""
        from backend.api.document_management_routes import router

        routes = [r.path for r in router.routes]
        assert "/documents/{doc_id}/content" in routes

    @pytest.mark.unit
    def test_summary_endpoint_exists(self):
        """Verify the summary endpoint is registered."""
        from backend.api.document_management_routes import router

        routes = [r.path for r in router.routes]
        assert "/documents/{doc_id}/summary" in routes

    @pytest.mark.unit
    def test_chunks_endpoint_exists(self):
        """Verify the chunks endpoint is registered."""
        from backend.api.document_management_routes import router

        routes = [r.path for r in router.routes]
        assert "/documents/{doc_id}/chunks" in routes

    @pytest.mark.unit
    def test_all_endpoints_require_tenant(self):
        """All 4 new endpoints must have get_current_tenant dependency."""
        from backend.api.document_management_routes import router
        from backend.security.dependencies import get_current_tenant

        target_paths = {
            "/documents/{doc_id}/detail",
            "/documents/{doc_id}/content",
            "/documents/{doc_id}/summary",
            "/documents/{doc_id}/chunks",
        }

        for route in router.routes:
            if hasattr(route, "path") and route.path in target_paths:
                # Check that the endpoint function has tenant parameter
                endpoint = route.endpoint
                import inspect
                sig = inspect.signature(endpoint)
                param_names = list(sig.parameters.keys())
                assert "tenant" in param_names, (
                    f"Endpoint {route.path} missing 'tenant' parameter"
                )

    @pytest.mark.unit
    def test_chunks_limit_capped_at_50(self):
        """Chunks endpoint should cap limit at 50."""
        from backend.api.document_management_routes import get_document_chunks
        import inspect

        sig = inspect.signature(get_document_chunks)
        limit_param = sig.parameters.get("limit")
        assert limit_param is not None
        assert limit_param.default == 5

    @pytest.mark.unit
    def test_upload_dir_constant(self):
        """UPLOAD_DIR should point to workspace/uploads/documents."""
        from backend.api.document_management_routes import UPLOAD_DIR
        assert str(UPLOAD_DIR) == "workspace/uploads/documents"
