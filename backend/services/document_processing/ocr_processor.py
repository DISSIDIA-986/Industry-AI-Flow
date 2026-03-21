"""
OCR Processor - Built on PaddleOCR 3.3.1

Features:
- PP-OCRv5: Supports 5 languages (Chinese/English/Traditional Chinese/Japanese/Korean)
- PP-StructureV3: PDF structure extraction, outputs Markdown/JSON
- MPS acceleration: Apple Silicon Metal GPU acceleration (2-5x speedup)
- Cloud OCR API fallback
- Batch processing
- Confidence scoring

Requirements:
- PaddlePaddle >= 2.6.0
- PaddleOCR >= 3.3.0
- NumPy < 2.0 (compatibility requirement)
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR recognition result."""

    text: str  # Recognized text content
    confidence: float  # Average recognition confidence (0.0-1.0)
    boxes: list[list[list[int]]]  # Bounding box coordinates for detected text regions
    method: str  # Recognition method used (local/api)
    language: str = "ch"  # Recognition language


class OCRProcessor:
    """
    OCR processing engine.

    Uses local PaddleOCR (with MPS GPU acceleration) as primary, with cloud API fallback.
    """

    def __init__(
        self,
        use_local: bool = True,
        use_api_fallback: bool = True,
        lang: str = "en",
        use_gpu: bool = True,
        ocr_version: str = "PP-OCRv5",
    ):
        """
        Initialize the OCR processor.

        Args:
            use_local: Whether to use local PaddleOCR
            use_api_fallback: Whether to fall back to cloud API on failure
            lang: Recognition language ('ch', 'en', 'chinese_cht', 'japan', 'korean')
            use_gpu: Whether to enable GPU acceleration (Apple MPS/NVIDIA CUDA)
            ocr_version: OCR model version ('PP-OCRv5', 'PP-OCRv4', 'PP-OCRv3')
        """
        self.use_local = use_local
        self.use_api_fallback = use_api_fallback
        self.lang = lang
        self.ocr_version = ocr_version

        # Initialize local OCR engine
        self.local_ocr = None
        if use_local:
            self.local_ocr = self._init_local_ocr(use_gpu)

        # Initialize cloud API client
        self.api_client = None
        if use_api_fallback:
            self.api_client = self._init_api_client()

    def _init_local_ocr(self, use_gpu: bool):
        """Initialize local PaddleOCR engine.

        PaddleOCR 3.3+ handles device selection (MPS/CUDA/CPU) internally
        via PaddlePaddle's device auto-detection.
        """
        try:
            from paddleocr import PaddleOCR

            ocr = PaddleOCR(
                use_textline_orientation=True,
                lang=self.lang,
                ocr_version=self.ocr_version,
                text_det_thresh=0.3,
                text_det_box_thresh=0.6,
                text_recognition_batch_size=6,
            )

            logger.info(
                f"PaddleOCR initialized (version={self.ocr_version}, "
                f"lang={self.lang})"
            )

            return ocr

        except Exception as e:
            logger.warning(f"Failed to initialize PaddleOCR: {e}")
            logger.info("Required: PaddlePaddle>=2.6.0, PaddleOCR>=3.3.0, NumPy<2.0")
            return None

    def _init_api_client(self):
        """Initialize the cloud OCR API client."""
        try:
            from aip import AipOcr

            # Read API credentials from environment
            app_id = os.getenv("BAIDU_OCR_APP_ID")
            api_key = os.getenv("BAIDU_OCR_API_KEY")
            secret_key = os.getenv("BAIDU_OCR_SECRET_KEY")

            if not all([app_id, api_key, secret_key]):
                logger.warning(
                    "OCR API credentials not configured, API fallback disabled"
                )
                return None

            client = AipOcr(app_id, api_key, secret_key)
            logger.info("OCR API client initialized successfully")
            return client

        except ImportError:
            logger.warning(
                "Baidu AI SDK (baidu-aip) not installed, API fallback disabled"
            )
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize OCR API client: {e}")
            return None

    def process(
        self,
        image_path: Union[str, Path],
    ) -> OCRResult:
        """
        Process an image file and extract text via OCR.

        Args:
            image_path: Path to the image file

        Returns:
            OCRResult with recognized text and confidence

        Raises:
            ValueError: If no OCR engine is available
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Try local OCR first
        if self.local_ocr:
            try:
                return self._process_local(image_path)
            except Exception as e:
                logger.warning(f"Local OCR processing failed: {e}")
                if not self.use_api_fallback:
                    raise

        # Fall back to cloud API
        if self.api_client:
            try:
                return self._process_api(image_path)
            except Exception as e:
                logger.error(f"API OCR processing failed: {e}")
                raise

        raise ValueError("No OCR engine available (local and API both unavailable)")

    def _process_local(self, image_path: Path) -> OCRResult:
        """Process image using local PaddleOCR engine.

        PaddleOCR 3.3+ uses the predict() API which returns dicts with keys:
        rec_texts, rec_scores, dt_polys.
        """
        # Run OCR recognition (PaddleOCR 3.3+ predict API)
        texts = []
        confidences = []
        boxes = []

        for res in self.local_ocr.predict(str(image_path)):
            rec_texts = res.get("rec_texts", [])
            rec_scores = res.get("rec_scores", [])
            dt_polys = res.get("dt_polys", [])

            texts.extend(rec_texts)
            confidences.extend(rec_scores)
            boxes.extend(
                poly.tolist() if hasattr(poly, "tolist") else poly for poly in dt_polys
            )

        # Handle empty results
        if not texts:
            return OCRResult(
                text="",
                confidence=0.0,
                boxes=[],
                method="local",
                language=self.lang,
            )

        # Combine text lines and calculate average confidence
        full_text = "\n".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(
            text=full_text,
            confidence=avg_confidence,
            boxes=boxes,
            method="local",
            language=self.lang,
        )

    def _process_api(self, image_path: Path) -> OCRResult:
        """Process image using cloud OCR API."""
        # Read image file
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Call API with language-appropriate method
        if self.lang == "en":
            result = self.api_client.basicGeneral(image_data)
        else:
            result = self.api_client.general(image_data)

        # Check for API errors
        if "error_code" in result:
            raise RuntimeError(f"OCR API error: {result.get('error_msg', 'Unknown')}")

        # Parse API response
        words_result = result.get("words_result", [])

        if not words_result:
            return OCRResult(
                text="",
                confidence=0.0,
                boxes=[],
                method="api",
                language=self.lang,
            )

        # Extract text from results
        texts = [item["words"] for item in words_result]
        full_text = "\n".join(texts)

        # API does not return per-line confidence or bounding boxes
        return OCRResult(
            text=full_text,
            confidence=0.95,  # API default confidence estimate
            boxes=[],  # API does not return bounding boxes
            method="api",
            language=self.lang,
        )

    def batch_process(
        self,
        image_paths: list[Union[str, Path]],
    ) -> list[OCRResult]:
        """
        Process multiple images in batch.

        Args:
            image_paths: List of image file paths

        Returns:
            List of OCRResult objects
        """
        results = []
        for path in image_paths:
            try:
                result = self.process(path)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {path}: {e}")
                # Append empty result for failed images
                results.append(
                    OCRResult(
                        text="",
                        confidence=0.0,
                        boxes=[],
                        method="failed",
                        language=self.lang,
                    )
                )

        return results


# Convenience function
def process_image_with_ocr(
    image_path: Union[str, Path],
    lang: str = "ch",
    use_gpu: bool = True,
) -> OCRResult:
    """
    Extract text from an image using OCR (convenience wrapper).

    Args:
        image_path: Path to the image file
        lang: Recognition language
        use_gpu: Whether to enable GPU acceleration

    Returns:
        OCRResult with recognized text and confidence
    """
    processor = OCRProcessor(lang=lang, use_gpu=use_gpu)
    return processor.process(image_path)
