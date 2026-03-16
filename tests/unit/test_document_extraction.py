"""Comprehensive tests for document extraction and OCR pipeline.

Covers: PDF extraction, OCR on images, text encoding fallback,
unsupported formats, scanned PDF fallback, batch processing,
and error handling.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.services.document_processing.document_extractor import (
    DocumentContent,
    DocumentExtractor,
    process_document,
)
from backend.services.document_processing.ocr_processor import OCRProcessor, OCRResult

# ---------------------------------------------------------------------------
# Paths to real test resources
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_IMAGES_DIR = PROJECT_ROOT / "test_resources" / "images"
TEST_DOCS_DIR = PROJECT_ROOT / "test_resources" / "documents"
CONSTRUCTION_SEED_DIR = TEST_DOCS_DIR / "construction_seed_2026q1"


# ===========================================================================
# Plain text extraction
# ===========================================================================


class TestTextExtraction:
    def test_utf8_text(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world\nLine two", encoding="utf-8")
        result = process_document(f, use_ocr=False)
        assert "Hello world" in result.text
        assert result.file_type == "text"
        assert result.metadata["encoding"] == "utf-8"
        assert result.metadata["num_lines"] == 2

    def test_markdown_treated_as_text(self, tmp_path: Path):
        f = tmp_path / "readme.md"
        f.write_text("# Title\nSome content", encoding="utf-8")
        result = process_document(f, use_ocr=False)
        assert "# Title" in result.text
        assert result.file_type == "text"

    def test_gbk_encoded_text(self, tmp_path: Path):
        f = tmp_path / "chinese.txt"
        f.write_bytes("你好世界\n第二行".encode("gbk"))
        result = process_document(f, use_ocr=False)
        assert "你好世界" in result.text
        assert result.metadata["encoding"] == "gbk"

    def test_latin1_fallback(self, tmp_path: Path):
        f = tmp_path / "latin.txt"
        content = "café résumé naïve"
        f.write_bytes(content.encode("latin-1"))
        result = process_document(f, use_ocr=False)
        assert "café" in result.text

    def test_empty_text_file(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        result = process_document(f, use_ocr=False)
        assert result.text == ""
        assert result.metadata["num_chars"] == 0

    def test_real_ai_research_paper(self):
        f = TEST_DOCS_DIR / "ai_research_paper.txt"
        if not f.exists():
            pytest.skip("test resource not available")
        result = process_document(f, use_ocr=False)
        assert len(result.text) > 100
        assert result.file_type == "text"


# ===========================================================================
# PDF extraction
# ===========================================================================


class TestPDFExtraction:
    def test_real_pdf_extraction(self):
        """Test extraction from a real construction PDF."""
        pdf = CONSTRUCTION_SEED_DIR / "gsa_core_building_standards_memo_2025.pdf"
        if not pdf.exists():
            pytest.skip("construction seed PDF not available")
        result = process_document(pdf, use_ocr=False)
        assert result.file_type == "pdf"
        assert result.method in ("pymupdf", "pymupdf+ocr")
        assert result.metadata["num_pages"] >= 1
        assert len(result.text) > 50

    def test_pdf_metadata_extracted(self):
        """Verify PDF metadata fields are populated."""
        pdf = CONSTRUCTION_SEED_DIR / "ufgs_toc.pdf"
        if not pdf.exists():
            pytest.skip("PDF not available")
        result = process_document(pdf, use_ocr=False)
        assert "num_pages" in result.metadata
        assert "author" in result.metadata
        assert "title" in result.metadata

    def test_multipage_pdf(self):
        """Verify multi-page PDF extraction joins pages."""
        pdf = CONSTRUCTION_SEED_DIR / "caltrans_2025_standard_plans_digest.pdf"
        if not pdf.exists():
            pytest.skip("PDF not available")
        result = process_document(pdf, use_ocr=False)
        assert result.metadata["num_pages"] > 1
        assert len(result.text) > 200

    def test_pdf_with_mocked_scanned_page(self, tmp_path: Path):
        """Test OCR fallback for a page that has no text layer."""
        import fitz

        # Create a 1-page PDF with an embedded image but no text layer
        doc = fitz.open()
        page = doc.new_page(width=200, height=100)
        # Insert a small colored rectangle (simulates scanned content)
        page.draw_rect(
            fitz.Rect(10, 10, 190, 90), color=(0, 0, 0), fill=(0.9, 0.9, 0.9)
        )
        pdf_path = tmp_path / "scanned.pdf"
        doc.save(str(pdf_path))
        doc.close()

        # With OCR disabled, the scanned page yields empty text
        result = process_document(pdf_path, use_ocr=False)
        assert result.file_type == "pdf"
        # The page has no text layer so text should be empty or minimal
        # (fitz may extract nothing or a tiny artifact)


# ===========================================================================
# OCR on images
# ===========================================================================


class TestOCROnImages:
    @pytest.fixture(autouse=True)
    def _check_ocr(self):
        """Skip OCR tests if PaddleOCR is not available."""
        from backend.services.document_processing import ocr_processor

        if ocr_processor is None or ocr_processor.local_ocr is None:
            pytest.skip("PaddleOCR not available")

    def test_ocr_on_test_image(self):
        """Test OCR on the dedicated test_ocr.png image."""
        img = TEST_IMAGES_DIR / "test_ocr.png"
        if not img.exists():
            pytest.skip("test_ocr.png not available")
        result = process_document(img, use_ocr=True)
        assert result.file_type == "image"
        assert result.method == "ocr"
        assert result.metadata["ocr_method"] == "local"
        assert isinstance(result.metadata["ocr_confidence"], float)

    def test_ocr_on_test_ocr_image(self):
        """Test OCR on test_ocr_image.png."""
        img = TEST_IMAGES_DIR / "test_ocr_image.png"
        if not img.exists():
            pytest.skip("test_ocr_image.png not available")
        result = process_document(img, use_ocr=True)
        assert result.file_type == "image"
        assert len(result.text) > 0

    def test_ocr_on_architectural_plan(self):
        """Test OCR on an architectural floor plan image."""
        img = TEST_IMAGES_DIR / "architectural_floor_plan.png"
        if not img.exists():
            pytest.skip("architectural_floor_plan.png not available")
        result = process_document(img, use_ocr=True)
        assert result.file_type == "image"
        assert result.metadata["width"] > 0
        assert result.metadata["height"] > 0

    def test_ocr_on_chinese_text(self):
        """Test OCR on Chinese text rendering image."""
        img = TEST_IMAGES_DIR / "test_chinese_ocr_image.png"
        if not img.exists():
            pytest.skip("test_chinese_ocr_image.png not available")
        result = process_document(img, use_ocr=True)
        assert result.file_type == "image"
        # Should extract some text (may not be perfect)
        assert isinstance(result.text, str)

    def test_ocr_confidence_range(self):
        """Verify confidence is 0.0-1.0."""
        img = TEST_IMAGES_DIR / "test_ocr.png"
        if not img.exists():
            pytest.skip("test_ocr.png not available")
        result = process_document(img, use_ocr=True)
        conf = result.metadata.get("ocr_confidence", 0.0)
        assert 0.0 <= conf <= 1.0

    def test_ocr_image_dimensions_in_metadata(self):
        """Verify image width/height/mode in metadata."""
        img = TEST_IMAGES_DIR / "price_distribution.png"
        if not img.exists():
            pytest.skip("price_distribution.png not available")
        result = process_document(img, use_ocr=True)
        assert result.metadata["width"] > 0
        assert result.metadata["height"] > 0
        assert result.metadata["mode"] in ("RGB", "RGBA", "L", "P")


# ===========================================================================
# OCRProcessor unit tests
# ===========================================================================


class TestOCRProcessor:
    def test_init_without_gpu(self):
        """Ensure OCRProcessor can initialize with GPU disabled."""
        proc = OCRProcessor(use_gpu=False, use_api_fallback=False)
        assert proc.local_ocr is not None

    def test_process_nonexistent_file(self):
        proc = OCRProcessor(use_gpu=False, use_api_fallback=False)
        with pytest.raises(FileNotFoundError):
            proc.process("/nonexistent/file.png")

    def test_batch_process_with_failure(self, tmp_path: Path):
        """Batch process handles missing files gracefully."""
        good_file = tmp_path / "good.txt"
        good_file.write_text("test")
        proc = OCRProcessor(use_gpu=False, use_api_fallback=False)
        results = proc.batch_process(
            [
                "/nonexistent/bad.png",
                "/nonexistent/also_bad.png",
            ]
        )
        assert len(results) == 2
        assert all(r.method == "failed" for r in results)

    def test_ocr_result_dataclass(self):
        r = OCRResult(
            text="hello", confidence=0.95, boxes=[], method="local", language="en"
        )
        assert r.text == "hello"
        assert r.confidence == 0.95
        assert r.method == "local"


# ===========================================================================
# DocumentExtractor edge cases
# ===========================================================================


class TestDocumentExtractorEdgeCases:
    def test_unsupported_extension(self, tmp_path: Path):
        f = tmp_path / "test.xyz"
        f.write_text("content")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            process_document(f)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            process_document("/nonexistent/path/doc.txt")

    def test_image_without_ocr_raises(self, tmp_path: Path):
        """Extracting an image with OCR disabled should raise."""
        from PIL import Image

        img_path = tmp_path / "test.png"
        Image.new("RGB", (100, 50), color="white").save(img_path)
        with pytest.raises(ValueError, match="OCR is not available"):
            process_document(img_path, use_ocr=False)

    def test_supported_extensions_complete(self):
        extractor = DocumentExtractor(use_ocr=False)
        expected = {
            ".pdf",
            ".docx",
            ".doc",
            ".xlsx",
            ".xls",
            ".txt",
            ".md",
            ".png",
            ".jpg",
            ".jpeg",
            ".bmp",
            ".tiff",
        }
        assert set(extractor.SUPPORTED_EXTENSIONS.keys()) == expected

    def test_extract_returns_document_content(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        result = DocumentExtractor(use_ocr=False).extract(f)
        assert isinstance(result, DocumentContent)
        assert result.text == "content"
        assert result.file_type == "text"
        assert result.method.startswith("text-")


# ===========================================================================
# PDF OCR fallback integration
# ===========================================================================


class TestPDFOCRFallback:
    def test_scanned_pdf_triggers_ocr(self, tmp_path: Path):
        """When a PDF page has no text, OCR should be attempted."""
        import fitz

        doc = fitz.open()
        # Page with no text at all
        page = doc.new_page(width=200, height=100)
        pdf_path = tmp_path / "blank.pdf"
        doc.save(str(pdf_path))
        doc.close()

        # Mock the OCR processor to verify it's called
        mock_ocr = MagicMock()
        mock_ocr.process.return_value = OCRResult(
            text="OCR extracted text",
            confidence=0.85,
            boxes=[],
            method="local",
            language="en",
        )

        extractor = DocumentExtractor(use_ocr=False)
        extractor.use_ocr = True
        extractor.ocr_processor = mock_ocr

        result = extractor.extract(pdf_path)
        assert "OCR extracted text" in result.text
        assert result.method == "pymupdf+ocr"
        assert 1 in result.metadata.get("ocr_pages", [])
        mock_ocr.process.assert_called_once()

    def test_mixed_pdf_text_and_scanned(self, tmp_path: Path):
        """PDF with some text pages and some scanned pages."""
        import fitz

        doc = fitz.open()
        # Page 1: has text
        page1 = doc.new_page(width=200, height=100)
        page1.insert_text((10, 50), "Real text content")
        # Page 2: blank (scanned)
        doc.new_page(width=200, height=100)
        pdf_path = tmp_path / "mixed.pdf"
        doc.save(str(pdf_path))
        doc.close()

        mock_ocr = MagicMock()
        mock_ocr.process.return_value = OCRResult(
            text="Scanned page text",
            confidence=0.8,
            boxes=[],
            method="local",
            language="en",
        )

        extractor = DocumentExtractor(use_ocr=False)
        extractor.use_ocr = True
        extractor.ocr_processor = mock_ocr

        result = extractor.extract(pdf_path)
        assert "Real text content" in result.text
        assert "Scanned page text" in result.text
        assert result.metadata["num_pages"] == 2
        assert result.method == "pymupdf+ocr"

    def test_pdf_ocr_failure_is_graceful(self, tmp_path: Path):
        """If OCR fails on a page, extraction continues without crashing."""
        import fitz

        doc = fitz.open()
        page = doc.new_page(width=200, height=100)
        page.insert_text((10, 50), "Page one text")
        doc.new_page(width=200, height=100)  # blank page
        pdf_path = tmp_path / "ocr_fail.pdf"
        doc.save(str(pdf_path))
        doc.close()

        mock_ocr = MagicMock()
        mock_ocr.process.side_effect = RuntimeError("OCR engine crashed")

        extractor = DocumentExtractor(use_ocr=False)
        extractor.use_ocr = True
        extractor.ocr_processor = mock_ocr

        # Should not raise — OCR failure is logged and skipped
        result = extractor.extract(pdf_path)
        assert "Page one text" in result.text
        assert result.method == "pymupdf"  # no OCR pages succeeded
