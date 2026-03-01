"""TDI Round 35 regression tests.

Focus: document loader import/runtime must degrade safely when Paddle runtime is
unavailable.
"""

from __future__ import annotations

import importlib
import sys

import pytest


class TestR35_DocumentLoaderOptionalPaddleRuntime:
    """Document loader should not crash app import in minimal environments."""

    @pytest.mark.unit
    def test_document_loader_module_import_does_not_require_paddle_runtime(self):
        sys.modules.pop("backend.services.document_loader", None)
        module = importlib.import_module("backend.services.document_loader")
        assert hasattr(module, "DocumentLoader")

    @pytest.mark.unit
    def test_enhanced_loader_falls_back_when_paddleocr_init_fails(self, monkeypatch):
        sys.modules.pop("backend.services.document_loader", None)
        module = importlib.import_module("backend.services.document_loader")

        class _BrokenPaddleOCR:
            def __init__(self, *args, **kwargs):
                raise ModuleNotFoundError("No module named 'paddle'")

        monkeypatch.setattr(module, "OCR_AVAILABLE", True)
        monkeypatch.setattr(module, "PaddleOCR", _BrokenPaddleOCR, raising=True)

        loader = module.EnhancedDocumentLoader(use_ocr=True, ocr_lang="en")
        assert loader.use_ocr is False
        assert loader.ocr is None
