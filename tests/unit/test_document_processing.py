"""Unit tests for document processing contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.services.document_processing import ocr_processor, process_document
from backend.tools.document_processing import (
    batch_extract_documents,
    extract_document_text,
    ocr_image,
)


def test_ocr_availability():
    if ocr_processor is None:
        pytest.skip("ocr processor unavailable in this environment")

    assert hasattr(ocr_processor, "use_local")
    assert hasattr(ocr_processor, "use_api_fallback")
    assert hasattr(ocr_processor, "lang")


def test_document_extractor():
    from backend.services.document_processing.document_extractor import (
        DocumentExtractor,
    )

    extractor = DocumentExtractor(use_ocr=True)

    assert extractor is not None
    assert isinstance(DocumentExtractor.SUPPORTED_EXTENSIONS, dict)
    assert ".txt" in DocumentExtractor.SUPPORTED_EXTENSIONS


def test_text_extraction(tmp_path: Path):
    test_file = tmp_path / "sample.txt"
    content = "Document extraction test.\nWith multiple lines."
    test_file.write_text(content, encoding="utf-8")

    result = process_document(test_file, use_ocr=False)

    assert result.text.strip() == content.strip()
    assert result.method
    assert isinstance(result.metadata, dict)


def test_langchain_tools(tmp_path: Path):
    test_file = tmp_path / "doc.txt"
    content = "LangChain document processing test"
    test_file.write_text(content, encoding="utf-8")

    result = extract_document_text.invoke(
        {"file_path": str(test_file), "use_ocr": False}
    )

    assert result["success"] is True
    assert result["text"]
    assert result["file_type"] == "text"


def test_batch_processing(tmp_path: Path):
    files = []
    for idx in range(3):
        file_path = tmp_path / f"batch_{idx}.txt"
        file_path.write_text(f"doc-{idx}", encoding="utf-8")
        files.append(str(file_path))

    result = batch_extract_documents.invoke({"file_paths": files, "use_ocr": False})

    assert result["total"] == 3
    assert result["failed"] == 0
    assert result["success"] is True


def test_ocr_integration_contract():
    if ocr_processor is None or ocr_processor.local_ocr is None:
        pytest.skip("local OCR backend unavailable")

    assert callable(ocr_image.invoke)
