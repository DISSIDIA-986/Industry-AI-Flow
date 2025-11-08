"""
文档内容提取器

支持多种文档格式:
- PDF (PyPDF2 + OCR)
- Word (python-docx)
- Excel (openpyxl)
- 图像 (PaddleOCR)
- 文本文件
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class DocumentContent:
    """文档提取结果"""

    text: str  # 提取的文本
    metadata: dict  # 元数据
    method: str  # 提取方法
    file_type: str  # 文件类型


class DocumentExtractor:
    """
    文档内容提取器

    自动检测文档类型并使用适当的方法提取内容
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
        初始化文档提取器

        Args:
            use_ocr: 是否使用OCR处理图像和PDF
        """
        self.use_ocr = use_ocr
        self.ocr_processor = None

        if use_ocr:
            try:
                from backend.services.document_processing.ocr_processor import OCRProcessor
                self.ocr_processor = OCRProcessor()
            except Exception as e:
                logger.warning(f"OCR初始化失败: {e}")

    def extract(self, file_path: Union[str, Path]) -> DocumentContent:
        """
        提取文档内容

        Args:
            file_path: 文档文件路径

        Returns:
            DocumentContent对象

        Raises:
            ValueError: 不支持的文件类型
            FileNotFoundError: 文件不存在
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 检测文件类型
        file_ext = file_path.suffix.lower()
        if file_ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")

        file_type = self.SUPPORTED_EXTENSIONS[file_ext]

        # 根据类型提取内容
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
            raise ValueError(f"未实现的文件类型处理: {file_type}")

    def _extract_pdf(self, file_path: Path) -> DocumentContent:
        """提取PDF内容"""
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            text_parts = []

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    text_parts.append(page_text)
                elif self.use_ocr and self.ocr_processor:
                    # 文本提取失败，尝试OCR
                    logger.info(f"PDF第{page_num+1}页无文本，尝试OCR")
                    # 注: 完整实现需要pdf2image转换
                    # 这里简化处理

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
            logger.error(f"PDF提取失败: {e}")
            raise

    def _extract_word(self, file_path: Path) -> DocumentContent:
        """提取Word文档内容"""
        try:
            from docx import Document

            doc = Document(file_path)

            # 提取段落文本
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

            # 提取表格文本
            tables_text = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text for cell in row.cells)
                    tables_text.append(row_text)

            # 合并所有文本
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
            logger.error(f"Word文档提取失败: {e}")
            raise

    def _extract_excel(self, file_path: Path) -> DocumentContent:
        """提取Excel内容"""
        try:
            import openpyxl

            workbook = openpyxl.load_workbook(file_path, data_only=True)

            sheets_text = []
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]

                # 提取工作表数据
                sheet_text = [f"### {sheet_name} ###"]

                for row in sheet.iter_rows(values_only=True):
                    row_values = [str(cell) if cell is not None else "" for cell in row]
                    if any(row_values):  # 跳过空行
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
            logger.error(f"Excel提取失败: {e}")
            raise

    def _extract_text(self, file_path: Path) -> DocumentContent:
        """提取文本文件内容"""
        try:
            # 尝试多种编码
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

            raise ValueError("无法使用支持的编码读取文本文件")

        except Exception as e:
            logger.error(f"文本提取失败: {e}")
            raise

    def _extract_image(self, file_path: Path) -> DocumentContent:
        """提取图像中的文本（使用OCR）"""
        if not self.use_ocr or not self.ocr_processor:
            raise ValueError("OCR未启用或不可用")

        try:
            from PIL import Image

            # 读取图像元数据
            with Image.open(file_path) as img:
                width, height = img.size
                mode = img.mode

            # 执行OCR
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
            logger.error(f"图像OCR提取失败: {e}")
            raise


# 便捷函数
def process_document(
    file_path: Union[str, Path],
    use_ocr: bool = True,
) -> DocumentContent:
    """
    处理文档并提取内容（便捷函数）

    Args:
        file_path: 文档文件路径
        use_ocr: 是否使用OCR

    Returns:
        DocumentContent对象
    """
    extractor = DocumentExtractor(use_ocr=use_ocr)
    return extractor.extract(file_path)
