"""
Document Processing Module

Components:
- OCRProcessor: OCR engine (local PaddleOCR with cloud API fallback)
- DocumentExtractor: Multi-format document text extractor
- process_document: Convenience function for document extraction
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

# Global OCR processor singleton (lazy initialization)
import threading

_global_ocr_processor = None
_ocr_lock = threading.Lock()


def get_ocr_processor() -> OCRProcessor:
    """Get or create the global OCR processor singleton (thread-safe)."""
    global _global_ocr_processor
    if _global_ocr_processor is None:
        with _ocr_lock:
            if _global_ocr_processor is None:
                try:
                    _global_ocr_processor = OCRProcessor()
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to initialize OCR processor: {e}")
    return _global_ocr_processor


# Initialize global ocr_processor instance
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
