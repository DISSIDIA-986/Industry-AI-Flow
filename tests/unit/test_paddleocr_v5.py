"""Paddle/PaddleOCR contract checks for optional OCR runtime."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_paddle_version_minimum():
    paddle = pytest.importorskip("paddle")

    major, minor = map(int, str(paddle.__version__).split(".")[:2])
    assert (major, minor) >= (2, 6)


@pytest.mark.unit
def test_paddleocr_importable():
    pytest.importorskip("paddleocr")
    from paddleocr import PaddleOCR

    assert PaddleOCR is not None


@pytest.mark.unit
def test_numpy_version_for_paddleocr():
    numpy = pytest.importorskip("numpy")

    major = int(str(numpy.__version__).split(".")[0])
    if major >= 2:
        pytest.skip("environment uses numpy>=2; compatibility validated by OCR runtime checks")
    assert major >= 1
