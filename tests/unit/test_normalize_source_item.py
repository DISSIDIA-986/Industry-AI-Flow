"""Unit tests for citation source normalization (page deep-linking metadata).

Covers `_normalize_source_item` in workflow_query_routes — the function that
shapes RAG source citations returned to the frontend, including the
`page_number` / `chunk_index` fields used for document-preview deep-linking.
"""

import pytest

from backend.api.workflow_query_routes import _normalize_source_item


@pytest.mark.unit
def test_dict_source_carries_page_and_chunk():
    raw = {
        "doc_id": "uuid-123",
        "filename": "nbc_2020.pdf",
        "content": "Section 9.3 concrete cover...",
        "relevance": 0.91,
        "page_number": 719,
        "chunk_index": 6019,
    }
    out = _normalize_source_item(raw)
    assert out["document_id"] == "uuid-123"  # doc_id, NOT filename
    assert out["document_name"] == "nbc_2020.pdf"
    assert out["page_number"] == 719
    assert out["chunk_index"] == 6019
    assert out["relevance"] == pytest.approx(0.91)


@pytest.mark.unit
def test_document_id_prefers_uuid_over_filename():
    # The deep-link target must be the resolvable doc id, never the filename.
    out = _normalize_source_item(
        {"document_id": "uuid-xyz", "filename": "foo.pdf", "content": "x"}
    )
    assert out["document_id"] == "uuid-xyz"


@pytest.mark.unit
def test_chunk_index_falls_back_to_chunk_id():
    out = _normalize_source_item(
        {"doc_id": "d1", "filename": "f.pdf", "chunk_id": 42, "content": "x"}
    )
    assert out["chunk_index"] == 42


@pytest.mark.unit
def test_string_page_and_chunk_coerced_to_int():
    out = _normalize_source_item(
        {"doc_id": "d1", "filename": "f.pdf", "page_number": "5", "chunk_index": "9"}
    )
    assert out["page_number"] == 5
    assert out["chunk_index"] == 9


@pytest.mark.unit
def test_missing_page_and_chunk_are_none():
    out = _normalize_source_item({"doc_id": "d1", "filename": "f.pdf", "content": "x"})
    assert out["page_number"] is None
    assert out["chunk_index"] is None


@pytest.mark.unit
def test_non_numeric_page_is_none_not_crash():
    out = _normalize_source_item(
        {"doc_id": "d1", "filename": "f.pdf", "page_number": "n/a", "chunk_index": []}
    )
    assert out["page_number"] is None
    assert out["chunk_index"] is None


@pytest.mark.unit
def test_string_source_has_null_page_chunk():
    out = _normalize_source_item("nbc_2020.pdf")
    assert out["document_id"] == "nbc_2020.pdf"
    assert out["document_name"] == "nbc_2020.pdf"
    assert out["page_number"] is None
    assert out["chunk_index"] is None


@pytest.mark.unit
def test_blank_and_invalid_sources_dropped():
    assert _normalize_source_item("   ") is None
    assert _normalize_source_item(123) is None
    assert _normalize_source_item({}) is None
