"""
EN:EN PDF,TXT,EN (Phase 2: EN OCR EN)
"""
import logging
import os
from pathlib import Path
from typing import Optional, Union

import fitz  # PyMuPDF

from backend.config import settings

logger = logging.getLogger(__name__)

# Phase 2 Step 4: OCR EN(EN)
try:
    from paddleocr import PaddleOCR

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class EnhancedDocumentLoader:
    """EN:EN PDF,TXT,EN (ENOCR)"""

    def __init__(self, use_ocr: bool = True, ocr_lang: Optional[str] = None):
        """
        EN

        Args:
            use_ocr: EN OCR EN
            ocr_lang: OCR EN ('en' EN, 'ch' EN, 'en+ch' EN)
                     EN (settings.ocr_lang,EN 'en')
        """
        # Phase 2 EN: ENOCR,EN
        if ocr_lang is None:
            ocr_lang = settings.ocr_lang
        self.use_ocr = use_ocr and OCR_AVAILABLE

        # Phase 2 Step 4: EN PaddleOCR (3.3.1 ENAPI)
        if self.use_ocr:
            self.ocr = PaddleOCR(
                use_textline_orientation=True,  # EN (ENuse_angle_cls)
                lang=ocr_lang,  # EN
            )
            logger.info("OCR EN (PaddleOCR 3.3.1, EN: %s)", ocr_lang)
        else:
            self.ocr = None
            if use_ocr and not OCR_AVAILABLE:
                logger.warning("PaddleOCR EN,OCR EN")

    def load_document(self, file_path: Union[str, Path]) -> str:
        """
        EN

        Args:
            file_path: EN

        Returns:
            EN
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"EN: {file_path}")

        # EN
        ext = file_path.suffix.lower()

        if ext == ".txt":
            return self._load_txt(file_path)
        elif ext == ".pdf":
            return self._load_pdf(file_path)
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            return self._load_image(file_path)
        else:
            raise ValueError(f"EN: {ext}")

    def _load_txt(self, file_path: Path) -> str:
        """EN TXT EN"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_pdf(self, file_path: Path) -> str:
        """
        EN PDF EN

        EN:
        1. EN
        2. EN OCR,EN OCR EN
        """
        doc = fitz.open(file_path)
        text_content = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # EN
            page_text = page.get_text()

            # EN(EN),EN OCR
            if self.use_ocr and len(page_text.strip()) < 50:
                logger.debug("EN %s: EN,EN OCR", page_num + 1)
                page_image = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2EN
                img_bytes = page_image.tobytes("png")

                # EN
                temp_img = f"/tmp/page_{page_num}.png"
                with open(temp_img, "wb") as f:
                    f.write(img_bytes)

                # OCR EN
                ocr_result = self._ocr_image(temp_img)
                text_content.append(ocr_result)

                # EN
                os.remove(temp_img)
            else:
                text_content.append(page_text)

        doc.close()
        return "\n\n".join(text_content)

    def _load_image(self, file_path: Path) -> str:
        """EN OCR EN"""
        if not self.use_ocr:
            raise ValueError("OCR EN,EN")

        return self._ocr_image(str(file_path))

    def _ocr_image(self, image_path: str) -> str:
        """
        EN PaddleOCR 3.3.1 EN

        Args:
            image_path: EN

        Returns:
            EN
        """
        # PaddleOCR 3.3.1 ENAPI: ENpredict()ENocr()
        result = self.ocr.predict(image_path)

        # EN (EN)
        text_lines = []
        if result and len(result) > 0:
            page_result = result[0]
            if "rec_texts" in page_result:
                text_lines = page_result["rec_texts"]

        return "\n".join(text_lines)


# Phase 1 EN(EN)
def load_pdf(file_path: str) -> str:
    """ENPDFEN(ENPyMuPDF)"""
    doc = fitz.open(file_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def load_txt(file_path: str) -> str:
    """EN"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_document(file_path: str) -> str:
    """EN(Phase 1 EN)"""
    if file_path.endswith(".pdf"):
        return load_pdf(file_path)
    elif file_path.endswith(".txt"):
        return load_txt(file_path)
    else:
        raise ValueError(f"EN: {file_path}")


class DocumentLoader:
    """EN"""

    def __init__(self):
        self.enhanced_loader = EnhancedDocumentLoader(use_ocr=True)

    def load_document(self, file_path: str) -> list:
        """
        ENLangChain DocumentEN

        Args:
            file_path: EN

        Returns:
            LangChain DocumentEN
        """
        try:
            from langchain_core.documents import Document

            # EN
            text_content = self.enhanced_loader.load_document(file_path)

            # ENDocumentEN
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


# EN,EN
document_loader = DocumentLoader()
