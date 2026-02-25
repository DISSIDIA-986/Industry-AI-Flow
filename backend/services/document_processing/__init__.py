"""
EN

EN:
- OCRProcessor: OCREN(ENPaddleOCRENAPI)
- DocumentExtractor: EN
- process_document: EN
"""

from backend.services.document_processing.document_extractor import (
    DocumentExtractor,
    process_document,
)
from backend.services.document_processing.ocr_processor import (
    OCRProcessor,
    OCRResult,
    process_image_with_ocr,
)

# ENOCREN(EN)
_global_ocr_processor = None


def get_ocr_processor() -> OCRProcessor:
    """ENOCREN(EN)"""
    global _global_ocr_processor
    if _global_ocr_processor is None:
        try:
            _global_ocr_processor = OCRProcessor()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"ENOCREN: {e}")
            _global_ocr_processor = None
    return _global_ocr_processor


# ENocr_processorEN
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
