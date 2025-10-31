"""
文档加载器：支持 PDF、TXT、图片 (Phase 2: 增加 OCR 支持)
"""
import os
from pathlib import Path
from typing import Union, Optional
import fitz  # PyMuPDF

# Phase 2 Step 4: OCR 支持（可选）
try:
    from paddleocr import PaddleOCR

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class EnhancedDocumentLoader:
    """增强文档加载器：支持 PDF、TXT、图片 (带OCR)"""

    def __init__(self, use_ocr: bool = True, ocr_lang: str = "ch"):
        """
        初始化增强文档加载器

        Args:
            use_ocr: 是否启用 OCR 功能
            ocr_lang: OCR 语言 ('ch' 中文, 'en' 英文)
        """
        self.use_ocr = use_ocr and OCR_AVAILABLE

        # Phase 2 Step 4: 初始化 PaddleOCR
        if self.use_ocr:
            self.ocr = PaddleOCR(
                use_angle_cls=True,  # 启用文字方向检测
                lang=ocr_lang,  # 语言
            )
            print(f"✅ OCR 模块已启用 (语言: {ocr_lang})")
        else:
            self.ocr = None
            if use_ocr and not OCR_AVAILABLE:
                print("⚠️ PaddleOCR 未安装，OCR 功能不可用")

    def load_document(self, file_path: Union[str, Path]) -> str:
        """
        加载文档内容

        Args:
            file_path: 文档路径

        Returns:
            文档文本内容
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 根据文件扩展名选择加载方式
        ext = file_path.suffix.lower()

        if ext == ".txt":
            return self._load_txt(file_path)
        elif ext == ".pdf":
            return self._load_pdf(file_path)
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            return self._load_image(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _load_txt(self, file_path: Path) -> str:
        """加载 TXT 文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_pdf(self, file_path: Path) -> str:
        """
        加载 PDF 文件

        策略：
        1. 先尝试提取文本
        2. 如果文本很少且启用 OCR，则使用 OCR 提取
        """
        doc = fitz.open(file_path)
        text_content = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # 尝试提取文本
            page_text = page.get_text()

            # 如果文本很少（可能是扫描件），使用 OCR
            if self.use_ocr and len(page_text.strip()) < 50:
                print(f"  页面 {page_num + 1}: 检测到扫描内容，使用 OCR...")
                page_image = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2倍分辨率
                img_bytes = page_image.tobytes("png")

                # 保存临时图片
                temp_img = f"/tmp/page_{page_num}.png"
                with open(temp_img, "wb") as f:
                    f.write(img_bytes)

                # OCR 识别
                ocr_result = self._ocr_image(temp_img)
                text_content.append(ocr_result)

                # 删除临时文件
                os.remove(temp_img)
            else:
                text_content.append(page_text)

        doc.close()
        return "\n\n".join(text_content)

    def _load_image(self, file_path: Path) -> str:
        """加载图片文件并使用 OCR 提取文本"""
        if not self.use_ocr:
            raise ValueError("OCR 未启用，无法处理图片文件")

        return self._ocr_image(str(file_path))

    def _ocr_image(self, image_path: str) -> str:
        """
        使用 PaddleOCR 识别图片文本

        Args:
            image_path: 图片路径

        Returns:
            识别的文本
        """
        result = self.ocr.ocr(image_path, cls=True)

        # 提取文本内容
        text_lines = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]  # (bbox, (text, confidence))
                text_lines.append(text)

        return "\n".join(text_lines)


# Phase 1 兼容函数（保持向后兼容）
def load_pdf(file_path: str) -> str:
    """提取PDF文本（使用PyMuPDF）"""
    doc = fitz.open(file_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def load_txt(file_path: str) -> str:
    """加载纯文本文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_document(file_path: str) -> str:
    """根据文件扩展名加载文档（Phase 1 简单版本）"""
    if file_path.endswith(".pdf"):
        return load_pdf(file_path)
    elif file_path.endswith(".txt"):
        return load_txt(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {file_path}")
