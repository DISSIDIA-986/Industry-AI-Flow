"""
OCREN - ENPaddleOCR 3.3.1EN

Features:
- PP-OCRv5: EN5EN (EN/EN/EN/EN/EN)
- PP-StructureV3: PDFEN,ENMarkdown/JSON
- MPSEN: Apple Silicon MENGPUEN (2-5xEN)
- ENOCR APIEN
- EN
- EN

EN:
- PaddlePaddle >= 2.6.0
- PaddleOCR >= 3.3.0
- NumPy < 2.0 (EN)
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCREN"""

    text: str  # EN
    confidence: float  # EN
    boxes: list[list[list[int]]]  # EN
    method: str  # EN (local/api)
    language: str = "ch"  # EN


class OCRProcessor:
    """
    OCREN

    ENPaddleOCR(ENMPSEN),ENAPI
    """

    def __init__(
        self,
        use_local: bool = True,
        use_api_fallback: bool = True,
        lang: str = "ch",
        use_gpu: bool = True,
        ocr_version: str = "PP-OCRv5",
    ):
        """
        ENOCREN

        Args:
            use_local: ENPaddleOCR
            use_api_fallback: ENAPI
            lang: EN ('ch', 'en', 'chinese_cht', 'japan', 'korean')
            use_gpu: ENGPUEN (Apple MPS/NVIDIA CUDA)
            ocr_version: OCREN ('PP-OCRv5', 'PP-OCRv4', 'PP-OCRv3')
        """
        self.use_local = use_local
        self.use_api_fallback = use_api_fallback
        self.lang = lang
        self.ocr_version = ocr_version

        # ENOCR
        self.local_ocr = None
        if use_local:
            self.local_ocr = self._init_local_ocr(use_gpu)

        # ENAPIEN
        self.api_client = None
        if use_api_fallback:
            self.api_client = self._init_api_client()

    def _init_local_ocr(self, use_gpu: bool):
        """ENPaddleOCR 3.3.1"""
        try:
            import paddle
            from paddleocr import PaddleOCR

            # ENMPSEN (PaddleCustomDevice)
            device = "cpu"
            use_gpu_flag = False

            if use_gpu:
                try:
                    # ENMPSEN
                    custom_devices = paddle.device.get_all_custom_device_type()
                    if "mps" in custom_devices:
                        device = "mps"
                        use_gpu_flag = True
                        logger.info("✅ ENApple MPSEN,ENGPUEN (EN2-5xEN)")
                    elif paddle.device.is_compiled_with_cuda():
                        device = "gpu"
                        use_gpu_flag = True
                        logger.info("✅ ENNVIDIA CUDAEN,ENGPUEN")
                    else:
                        logger.info("⚠️  ENGPUEN,ENCPU")
                except Exception as e:
                    logger.warning(f"GPUEN: {e},ENCPU")

            # ENPaddleOCR 3.3.1
            # PP-OCRv5EN: ch (EN), en, chinese_cht, japan, korean
            ocr = PaddleOCR(
                use_angle_cls=True,  # EN
                lang=self.lang,  # PP-OCRv5EN
                use_gpu=use_gpu_flag,  # GPUEN
                show_log=False,
                # PP-OCRv5EN
                use_mp=True,  # EN
                total_process_num=2,  # EN
                # EN
                det_db_thresh=0.3,  # EN
                det_db_box_thresh=0.6,  # EN
                rec_batch_num=6,  # EN
            )

            logger.info(f"✅ PaddleOCR 3.3.1EN")
            logger.info(f"   - EN: {self.ocr_version}")
            logger.info(f"   - EN: {device}")
            logger.info(f"   - EN: {self.lang}")
            logger.info(f"   - EN: PP-OCRv5EN (EN/EN/EN/EN/EN)")

            return ocr

        except Exception as e:
            logger.warning(f"ENPaddleOCREN: {e}")
            logger.info("EN: EN PaddlePaddle>=2.6.0, PaddleOCR>=3.3.0, NumPy<2.0")
            return None

    def _init_api_client(self):
        """ENOCR APIEN"""
        try:
            from aip import AipOcr

            # ENAPIEN
            app_id = os.getenv("BAIDU_OCR_APP_ID")
            api_key = os.getenv("BAIDU_OCR_API_KEY")
            secret_key = os.getenv("BAIDU_OCR_SECRET_KEY")

            if not all([app_id, api_key, secret_key]):
                logger.warning("ENOCR APIEN,APIEN")
                return None

            client = AipOcr(app_id, api_key, secret_key)
            logger.info("ENOCR APIEN")
            return client

        except ImportError:
            logger.warning("ENAI SDK (baidu-aip)EN,APIEN")
            return None
        except Exception as e:
            logger.warning(f"ENOCR APIEN: {e}")
            return None

    def process(
        self,
        image_path: Union[str, Path],
    ) -> OCRResult:
        """
        EN

        Args:
            image_path: EN

        Returns:
            OCRResultEN

        Raises:
            ValueError: ENOCREN
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"EN: {image_path}")

        # ENOCR
        if self.local_ocr:
            try:
                return self._process_local(image_path)
            except Exception as e:
                logger.warning(f"ENOCREN: {e}")
                if not self.use_api_fallback:
                    raise

        # ENAPI
        if self.api_client:
            try:
                return self._process_api(image_path)
            except Exception as e:
                logger.error(f"API OCREN: {e}")
                raise

        raise ValueError("ENOCREN")

    def _process_local(self, image_path: Path) -> OCRResult:
        """ENPaddleOCREN"""
        # ENOCR
        result = self.local_ocr.ocr(str(image_path), cls=True)

        # EN
        if not result or not result[0]:
            return OCRResult(
                text="",
                confidence=0.0,
                boxes=[],
                method="local",
                language=self.lang,
            )

        # EN
        texts = []
        confidences = []
        boxes = []

        for line in result[0]:
            box, (text, confidence) = line
            texts.append(text)
            confidences.append(confidence)
            boxes.append(box)

        # EN
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
        """ENOCR APIEN"""
        # EN
        with open(image_path, "rb") as f:
            image_data = f.read()

        # ENAPI
        if self.lang == "en":
            result = self.api_client.basicGeneral(image_data)
        else:
            result = self.api_client.general(image_data)

        # EN
        if "error_code" in result:
            raise RuntimeError(f"ENAPIEN: {result.get('error_msg', 'Unknown')}")

        # EN
        words_result = result.get("words_result", [])

        if not words_result:
            return OCRResult(
                text="",
                confidence=0.0,
                boxes=[],
                method="api",
                language=self.lang,
            )

        # EN
        texts = [item["words"] for item in words_result]
        full_text = "\n".join(texts)

        # APIEN,EN
        return OCRResult(
            text=full_text,
            confidence=0.95,  # APIEN
            boxes=[],  # APIEN
            method="api",
            language=self.lang,
        )

    def batch_process(
        self,
        image_paths: list[Union[str, Path]],
    ) -> list[OCRResult]:
        """
        EN

        Args:
            image_paths: EN

        Returns:
            OCRResultEN
        """
        results = []
        for path in image_paths:
            try:
                result = self.process(path)
                results.append(result)
            except Exception as e:
                logger.error(f"EN {path} EN: {e}")
                # EN
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


# EN
def process_image_with_ocr(
    image_path: Union[str, Path],
    lang: str = "ch",
    use_gpu: bool = True,
) -> OCRResult:
    """
    EN(EN)

    Args:
        image_path: EN
        lang: EN
        use_gpu: ENGPU

    Returns:
        OCRResultEN
    """
    processor = OCRProcessor(lang=lang, use_gpu=use_gpu)
    return processor.process(image_path)
