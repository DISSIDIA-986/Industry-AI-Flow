"""
EN

EN:
- PDF (PyPDF2 + OCR)
- Word (python-docx)
- Excel (openpyxl)
- EN (PaddleOCR)
- EN
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class DocumentContent:
    """EN"""

    text: str  # EN
    metadata: dict  # EN
    method: str  # EN
    file_type: str  # EN


class DocumentExtractor:
    """
    EN

    EN
    """

    SUPPORTED_EXTENSIONS = {
        ".pdf": "pdf",
        ".docx": "word",
        ".doc": "word",
        ".xlsx": "excel",
        ".xls": "excel",
        ".txt": "text",
        ".md": "text",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".bmp": "image",
        ".tiff": "image",
    }

    def __init__(self, use_ocr: bool = True):
        """
        EN

        Args:
            use_ocr: ENOCRENPDF
        """
        self.use_ocr = use_ocr
        self.ocr_processor = None

        if use_ocr:
            try:
                from backend.services.document_processing.ocr_processor import (
                    OCRProcessor,
                )

                self.ocr_processor = OCRProcessor()
            except Exception as e:
                logger.warning(f"OCREN: {e}")

    def extract(self, file_path: Union[str, Path]) -> DocumentContent:
        """
        EN

        Args:
            file_path: EN

        Returns:
            DocumentContentEN

        Raises:
            ValueError: EN
            FileNotFoundError: EN
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_ext = file_path.suffix.lower()
        if file_ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension: {file_ext}")

        file_type = self.SUPPORTED_EXTENSIONS[file_ext]

        # EN
        if file_type == "pdf":
            return self._extract_pdf(file_path)
        elif file_type == "word":
            return self._extract_word(file_path)
        elif file_type == "excel":
            return self._extract_excel(file_path)
        elif file_type == "text":
            return self._extract_text(file_path)
        elif file_type == "image":
            return self._extract_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _extract_pdf(self, file_path: Path) -> DocumentContent:
        """ENPDFEN"""
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            text_parts = []

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    text_parts.append(page_text)
                elif self.use_ocr and self.ocr_processor:
                    # EN,ENOCR
                    logger.info(f"PDFEN{page_num+1}EN,ENOCR")
                    # EN: ENpdf2imageEN
                    # EN

            full_text = "\n\n".join(text_parts)

            metadata = {
                "num_pages": len(reader.pages),
                "author": reader.metadata.get("/Author", "Unknown"),
                "title": reader.metadata.get("/Title", "Unknown"),
            }

            return DocumentContent(
                text=full_text,
                metadata=metadata,
                method="pypdf2",
                file_type="pdf",
            )

        except Exception as e:
            logger.error(f"PDFEN: {e}")
            raise

    def _extract_word(self, file_path: Path) -> DocumentContent:
        """ENWordEN"""
        try:
            from docx import Document

            doc = Document(file_path)

            # EN
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

            # EN
            tables_text = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text for cell in row.cells)
                    tables_text.append(row_text)

            # EN
            all_text = "\n".join(paragraphs)
            if tables_text:
                all_text += "\n\n" + "\n".join(tables_text)

            metadata = {
                "num_paragraphs": len(paragraphs),
                "num_tables": len(doc.tables),
            }

            return DocumentContent(
                text=all_text,
                metadata=metadata,
                method="python-docx",
                file_type="word",
            )

        except Exception as e:
            logger.error(f"WordEN: {e}")
            raise

    def _extract_excel(self, file_path: Path) -> DocumentContent:
        """ENExcelEN"""
        try:
            import openpyxl

            workbook = openpyxl.load_workbook(file_path, data_only=True)

            sheets_text = []
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]

                # EN
                sheet_text = [f"### {sheet_name} ###"]

                for row in sheet.iter_rows(values_only=True):
                    row_values = [str(cell) if cell is not None else "" for cell in row]
                    if any(row_values):  # EN
                        sheet_text.append(" | ".join(row_values))

                sheets_text.append("\n".join(sheet_text))

            full_text = "\n\n".join(sheets_text)

            metadata = {
                "num_sheets": len(workbook.sheetnames),
                "sheet_names": workbook.sheetnames,
            }

            return DocumentContent(
                text=full_text,
                metadata=metadata,
                method="openpyxl",
                file_type="excel",
            )

        except Exception as e:
            logger.error(f"ExcelEN: {e}")
            raise

    def _extract_text(self, file_path: Path) -> DocumentContent:
        """EN"""
        try:
            # EN
            encodings = ["utf-8", "gbk", "gb2312", "latin-1"]

            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        text = f.read()

                    metadata = {
                        "encoding": encoding,
                        "num_lines": len(text.splitlines()),
                        "num_chars": len(text),
                    }

                    return DocumentContent(
                        text=text,
                        metadata=metadata,
                        method=f"text-{encoding}",
                        file_type="text",
                    )

                except UnicodeDecodeError:
                    continue

            raise ValueError("EN")

        except Exception as e:
            logger.error(f"EN: {e}")
            raise

    def _extract_image(self, file_path: Path) -> DocumentContent:
        """EN(ENOCR)"""
        if not self.use_ocr or not self.ocr_processor:
            raise ValueError("OCREN")

        try:
            from PIL import Image

            # EN
            with Image.open(file_path) as img:
                width, height = img.size
                mode = img.mode

            # ENOCR
            ocr_result = self.ocr_processor.process(file_path)

            metadata = {
                "width": width,
                "height": height,
                "mode": mode,
                "ocr_confidence": ocr_result.confidence,
                "ocr_method": ocr_result.method,
            }

            return DocumentContent(
                text=ocr_result.text,
                metadata=metadata,
                method="ocr",
                file_type="image",
            )

        except Exception as e:
            logger.error(f"ENOCREN: {e}")
            raise


# EN
def process_document(
    file_path: Union[str, Path],
    use_ocr: bool = True,
) -> DocumentContent:
    """
    EN(EN)

    Args:
        file_path: EN
        use_ocr: ENOCR

    Returns:
        DocumentContentEN
    """
    extractor = DocumentExtractor(use_ocr=use_ocr)
    return extractor.extract(file_path)
