"""
Document Loader: Supports PDF, TXT, and image files (Phase 2: OCR support added).
"""
import importlib
import logging
import os
from pathlib import Path
from typing import Optional, Union

from backend.config import settings

logger = logging.getLogger(__name__)

# Phase 2 Step 4: OCR support (optional dependency)
try:
    from paddleocr import PaddleOCR

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def _get_fitz():
    """Lazily import PyMuPDF so module import does not hard-require it."""
    try:
        return importlib.import_module("fitz")
    except Exception as exc:
        raise RuntimeError(
            "PyMuPDF (fitz) is required for PDF loading but is not installed."
        ) from exc


class EnhancedDocumentLoader:
    """Enhanced document loader supporting PDF, TXT, and image files with optional OCR."""

    def __init__(self, use_ocr: bool = True, ocr_lang: Optional[str] = None):
        """
        Initialize the enhanced document loader.

        Args:
            use_ocr: Whether to enable OCR for scanned documents and images.
            ocr_lang: OCR language ('en' for English, 'ch' for Chinese, 'en+ch' for both).
                     Defaults to settings.ocr_lang (fallback: 'en').
        """
        # Phase 2: Initialize OCR if available
        if ocr_lang is None:
            ocr_lang = settings.ocr_lang
        self.use_ocr = use_ocr and OCR_AVAILABLE

        # Phase 2 Step 4: Initialize PaddleOCR (3.3.1 API)
        if self.use_ocr:
            try:
                self.ocr = PaddleOCR(
                    use_textline_orientation=True,  # Enable text orientation detection (replaces use_angle_cls)
                    lang=ocr_lang,  # OCR language setting
                )
                logger.info("OCR initialized (PaddleOCR 3.3.1, language: %s)", ocr_lang)
            except Exception as exc:
                self.ocr = None
                self.use_ocr = False
                logger.warning("PaddleOCR initialization failed, OCR disabled: %s", exc)
        else:
            self.ocr = None
            if use_ocr and not OCR_AVAILABLE:
                logger.warning("PaddleOCR not installed, OCR disabled")

    def load_document(self, file_path: Union[str, Path]) -> str:
        """
        Load a document and extract its text content.

        Args:
            file_path: Path to the document file.

        Returns:
            Extracted text content as a string.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine file type by extension
        ext = file_path.suffix.lower()

        if ext == ".txt":
            return self._load_txt(file_path)
        elif ext == ".pdf":
            return self._load_pdf(file_path)
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            return self._load_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _load_txt(self, file_path: Path) -> str:
        """Load a TXT file and return its text content."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_pdf(self, file_path: Path) -> str:
        """
        Load a PDF file and extract text content.

        Strategy:
        1. First attempt direct text extraction.
        2. If text content is sparse and OCR is enabled, use OCR as fallback.
        """
        fitz = _get_fitz()
        doc = fitz.open(file_path)
        text_content = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Extract text directly
            page_text = page.get_text()

            # If text is too short (likely scanned), fall back to OCR
            if self.use_ocr and len(page_text.strip()) < 50:
                logger.debug("Page %s: sparse text detected, using OCR fallback", page_num + 1)
                page_image = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolution
                img_bytes = page_image.tobytes("png")

                # Save temporary image for OCR
                temp_img = f"/tmp/page_{page_num}.png"
                with open(temp_img, "wb") as f:
                    f.write(img_bytes)

                # Run OCR on the image
                ocr_result = self._ocr_image(temp_img)
                text_content.append(ocr_result)

                # Clean up temporary image
                os.remove(temp_img)
            else:
                text_content.append(page_text)

        doc.close()
        return "\n\n".join(text_content)

    def _load_image(self, file_path: Path) -> str:
        """Load an image file using OCR to extract text."""
        if not self.use_ocr:
            raise ValueError("OCR is not available; cannot process image files")

        return self._ocr_image(str(file_path))

    def _ocr_image(self, image_path: str) -> str:
        """
        Extract text from an image using PaddleOCR 3.3.1.

        Args:
            image_path: Path to the image file.

        Returns:
            Extracted text content as a string.
        """
        # PaddleOCR 3.3.1 API: uses predict() instead of the old ocr() method
        result = self.ocr.predict(image_path)

        # Parse OCR results (extract recognized text lines)
        text_lines = []
        if result and len(result) > 0:
            page_result = result[0]
            if "rec_texts" in page_result:
                text_lines = page_result["rec_texts"]

        return "\n".join(text_lines)


# Phase 1 backward-compatible functions
def load_pdf(file_path: str) -> str:
    """Load a PDF file and extract text (uses PyMuPDF)."""
    fitz = _get_fitz()
    doc = fitz.open(file_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def load_txt(file_path: str) -> str:
    """Load a text file and return its content."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_document(file_path: str) -> str:
    """Load a document by file type (Phase 1 compatibility function)."""
    if file_path.endswith(".pdf"):
        return load_pdf(file_path)
    elif file_path.endswith(".txt"):
        return load_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")


class DocumentLoader:
    """Document loader that wraps EnhancedDocumentLoader for LangChain compatibility."""

    def __init__(self):
        self.enhanced_loader = EnhancedDocumentLoader(use_ocr=True)

    def load_document(self, file_path: str) -> list:
        """
        Load a document and return LangChain Document objects.

        Args:
            file_path: Path to the document file.

        Returns:
            List of LangChain Document objects.
        """
        try:
            from langchain_core.documents import Document

            # Extract text content
            text_content = self.enhanced_loader.load_document(file_path)

            # Wrap in LangChain Document objects
            return [
                Document(
                    page_content=text_content,
                    metadata={
                        "source": file_path,
                        "file_type": Path(file_path).suffix.lower(),
                    },
                )
            ]

        except Exception as e:
            logger.error("Error loading document %s: %s", file_path, e)
            return []


class _LazyDocumentLoader:
    """Lazy proxy to avoid import-time OCR initialization side effects."""

    def __init__(self):
        self._instance: Optional[DocumentLoader] = None

    def _get_instance(self) -> DocumentLoader:
        if self._instance is None:
            self._instance = DocumentLoader()
        return self._instance

    def load_document(self, file_path: str) -> list:
        return self._get_instance().load_document(file_path)


# Global document loader instance (lazy initialization)
document_loader = _LazyDocumentLoader()
