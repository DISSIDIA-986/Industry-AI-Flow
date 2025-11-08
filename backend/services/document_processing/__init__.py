"""
文档处理服务包初始化

导出核心组件:
- OCRProcessor: OCR处理器（支持本地PaddleOCR和API）
- DocumentExtractor: 文档内容提取器
- process_document: 便捷处理函数
"""

from backend.services.document_processing.ocr_processor import (
    OCRProcessor,
    OCRResult,
    process_image_with_ocr,
)
from backend.services.document_processing.document_extractor import (
    DocumentExtractor,
    process_document,
)


# 创建全局OCR处理器实例（延迟初始化）
_global_ocr_processor = None


def get_ocr_processor() -> OCRProcessor:
    """获取全局OCR处理器实例（单例模式）"""
    global _global_ocr_processor
    if _global_ocr_processor is None:
        try:
            _global_ocr_processor = OCRProcessor()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"无法初始化OCR处理器: {e}")
            _global_ocr_processor = None
    return _global_ocr_processor


# 为向后兼容性提供ocr_processor别名
ocr_processor = get_ocr_processor()


__all__ = [
    "OCRProcessor",
    "OCRResult",
    "DocumentExtractor",
    "process_image_with_ocr",
    "process_document",
    "get_ocr_processor",
    "ocr_processor",
]
