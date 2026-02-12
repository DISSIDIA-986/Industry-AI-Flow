#!/usr/bin/env python3
"""Device manager with optional torch dependency."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Optional

try:  # pragma: no cover - runtime dependency probe
    import torch  # type: ignore
except Exception:  # pragma: no cover - torch is optional in demo profile
    torch = None  # type: ignore

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """Supported execution devices."""

    MPS = "mps"
    CUDA = "cuda"
    CPU = "cpu"


class DeviceManager:
    """Runtime device resolver (singleton)."""

    _instance: Optional["DeviceManager"] = None
    _device: Optional[Any] = None
    _device_type: Optional[DeviceType] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._device is None:
            self._detect_device()

    def _detect_device(self) -> None:
        if torch is None:
            self._device = "cpu"
            self._device_type = DeviceType.CPU
            logger.warning("Torch is unavailable; falling back to CPU mode")
            return

        # 1) Apple Metal
        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            try:
                torch.tensor([1.0], device="mps")
                self._device = torch.device("mps")
                self._device_type = DeviceType.MPS
                logger.info("Using Apple MPS acceleration")
                return
            except Exception as exc:
                logger.warning("MPS probe failed (%s), trying other devices", exc)

        # 2) CUDA
        if torch.cuda.is_available():
            self._device = torch.device("cuda")
            self._device_type = DeviceType.CUDA
            logger.info("Using CUDA acceleration")
            return

        # 3) CPU
        self._device = torch.device("cpu")
        self._device_type = DeviceType.CPU
        logger.info("Using CPU execution")

    @property
    def device(self) -> Any:
        return self._device

    @property
    def device_type(self) -> DeviceType:
        return self._device_type or DeviceType.CPU

    @property
    def device_name(self) -> str:
        if self.device_type == DeviceType.MPS:
            return "Apple MPS (Metal)"
        if self.device_type == DeviceType.CUDA and torch is not None:
            return f"CUDA GPU ({torch.cuda.get_device_name(0)})"
        return "CPU"

    def get_sentence_transformer_device(self) -> str:
        return self.device_type.value

    def get_torch_device(self) -> Any:
        return self._device

    def optimize_for_inference(self) -> dict:
        config = {
            "device": self.get_sentence_transformer_device(),
            "show_progress_bar": True,
        }

        if self.device_type == DeviceType.MPS:
            config.update(
                {
                    "convert_to_numpy": True,
                    "normalize_embeddings": True,
                }
            )
        elif self.device_type == DeviceType.CUDA:
            config.update(
                {
                    "convert_to_numpy": True,
                    "normalize_embeddings": True,
                    "batch_size": 64,
                }
            )
        else:
            config.update(
                {
                    "convert_to_numpy": True,
                    "normalize_embeddings": True,
                    "batch_size": 16,
                }
            )
        return config

    def print_device_info(self) -> None:
        print("\n" + "=" * 70)
        print("Device probe result")
        print("=" * 70)
        print(f"  Device: {self.device_name}")
        print(f"  Device type: {self.device_type.value}")
        if torch is not None:
            print(f"  Torch version: {torch.__version__}")
        else:
            print("  Torch version: unavailable")
        print("=" * 70 + "\n")


# Global singleton
device_manager = DeviceManager()


def get_device() -> Any:
    return device_manager.device


def get_device_name() -> str:
    return device_manager.device_name


def get_inference_config() -> dict:
    return device_manager.optimize_for_inference()


if __name__ == "__main__":
    device_manager.print_device_info()
