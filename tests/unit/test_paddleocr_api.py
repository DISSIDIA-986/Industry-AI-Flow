"""PaddleOCR API smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_paddleocr_api_smoke():
    paddleocr = pytest.importorskip("paddleocr")
    pytest.importorskip("paddle")
    from paddleocr import PaddleOCR

    assert hasattr(paddleocr, "__version__")

    image_path = Path("test_resources/images/architectural_floor_plan.png")
    if not image_path.exists():
        pytest.skip(f"sample image not found: {image_path}")

    try:
        ocr = PaddleOCR(lang="en")
    except ModuleNotFoundError as exc:
        pytest.skip(f"Paddle runtime unavailable: {exc}")
    result = ocr.predict(str(image_path))

    assert ocr is not None
    assert result is not None
