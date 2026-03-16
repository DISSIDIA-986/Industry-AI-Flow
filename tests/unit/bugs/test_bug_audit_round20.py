"""TDI Round 20 — bug reproduction tests.

Focus: import-time stability for optional runtime dependencies.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(rel_path: str) -> str:
    return (_REPO_ROOT / rel_path).read_text(encoding="utf-8")


class TestB2001MainOptionalUvicorn:
    @pytest.mark.unit
    def test_main_module_has_no_top_level_uvicorn_import(self):
        """P1: backend.main must not hard-import uvicorn at module import time.

        Why: API contract/unit tests import backend.main directly. If uvicorn is
        missing in a minimal test environment, collection crashes before tests run.
        """
        source = _read("backend/main.py")
        tree = ast.parse(source)

        top_level_uvicorn_import = False
        for node in tree.body:
            if isinstance(node, ast.Import):
                names = {alias.name for alias in node.names}
                if "uvicorn" in names:
                    top_level_uvicorn_import = True
            elif isinstance(node, ast.ImportFrom):
                if node.module == "uvicorn":
                    top_level_uvicorn_import = True

        assert top_level_uvicorn_import is False, (
            "backend.main still hard-imports uvicorn at module load time. "
            "Move uvicorn import to __main__ startup path."
        )


class TestB2002OcrProcessorOptionalPillow:
    @pytest.mark.unit
    def test_ocr_processor_has_no_top_level_pillow_import(self):
        """P1: OCR module import should not depend on Pillow being installed."""
        source = _read("backend/services/document_processing/ocr_processor.py")
        tree = ast.parse(source)

        top_level_pillow_import = False
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "PIL":
                top_level_pillow_import = True
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "PIL":
                        top_level_pillow_import = True

        assert top_level_pillow_import is False, (
            "ocr_processor has top-level Pillow import. Optional OCR/image "
            "dependencies should not break module import in test/runtime environments."
        )


class TestB2003DocumentLoaderOptionalPyMuPDF:
    @pytest.mark.unit
    def test_document_loader_has_no_top_level_fitz_import(self):
        """P1: Document loader should not require PyMuPDF at import time."""
        source = _read("backend/services/document_loader.py")
        tree = ast.parse(source)

        top_level_fitz_import = False
        for node in tree.body:
            if isinstance(node, ast.Import):
                names = {alias.name for alias in node.names}
                if "fitz" in names:
                    top_level_fitz_import = True
            elif isinstance(node, ast.ImportFrom) and node.module == "fitz":
                top_level_fitz_import = True

        assert top_level_fitz_import is False, (
            "document_loader has top-level fitz import. Optional PDF dependency "
            "should be imported lazily or behind a guarded import."
        )
