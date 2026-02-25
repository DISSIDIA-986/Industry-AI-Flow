"""
llama.cpp EN
EN GGUF EN,EN Metal EN
"""
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

try:
    from llama_cpp import Llama

    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

from backend.config import settings

logger = logging.getLogger(__name__)


class LlamaCppClient:
    """llama.cpp EN,EN GGUF EN"""

    def __init__(
        self,
        model_path: str = None,
        n_ctx: int = None,
        n_threads: int = None,
        n_gpu_layers: int = -1,
        n_batch: int = 512,
        verbose: bool = False,
    ):
        """
        EN llama.cpp EN

        Args:
            model_path: EN
            n_ctx: EN
            n_threads: CPUEN(EN)
            n_gpu_layers: GPUEN (-1=ENGPU, 0=ENCPU)
            n_batch: EN
            verbose: EN
        """
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError(
                "llama-cpp-python EN.EN: "
                "CMAKE_ARGS='-DGGML_METAL=on' pip install llama-cpp-python"
            )

        self.model_path = model_path or getattr(
            settings, "llama_model_path", "models/qwen2.5-7b-instruct.gguf"
        )
        self.n_ctx = n_ctx or getattr(settings, "llama_context_size", 4096)
        self.n_threads = n_threads or getattr(
            settings, "llama_threads", os.cpu_count() or 8
        )
        self.n_gpu_layers = n_gpu_layers
        self.n_batch = n_batch
        self.verbose = verbose
        self.model = None

        # EN
        if not self._validate_model_file():
            raise FileNotFoundError(f"EN: {self.model_path}")

        # ENGPU
        if self.n_gpu_layers == -1:
            self.n_gpu_layers = self._detect_gpu_layers()

        # EN
        self._load_model()

    def _validate_model_file(self) -> bool:
        """EN"""
        model_path = Path(self.model_path)

        if not model_path.exists():
            logger.error(f"EN: {self.model_path}")
            return False

        if not model_path.is_file():
            logger.error(f"EN: {self.model_path}")
            return False

        file_size = model_path.stat().st_size
        if file_size < 1024 * 1024:  # EN1MBEN
            logger.warning(f"EN,EN: {file_size} bytes")

        logger.info(f"✅ EN: {self.model_path} ({file_size / (1024**3):.2f} GB)")
        return True

    def _detect_gpu_layers(self) -> int:
        """ENGPUEN"""
        try:
            import torch

            if torch.backends.mps.is_available():
                logger.info("✅ EN Apple Silicon Metal,EN GPU EN")
                return -1  # ENGPUEN
        except ImportError:
            logger.info("torch EN,ENGPUEN")
        except Exception as e:
            logger.warning(f"GPUEN: {e}")

        logger.info("ENCPUEN")
        return 0  # ENCPUEN

    def _load_model(self):
        """EN"""
        try:
            logger.info(f"EN: {Path(self.model_path).name}")
            logger.info(
                f"EN - EN: {self.n_ctx}, EN: {self.n_threads}, GPUEN: {self.n_gpu_layers}"
            )

            start_time = time.time()
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                n_batch=self.n_batch,
                verbose=self.verbose,
            )

            load_time = time.time() - start_time
            logger.info(f"✅ EN,EN: {load_time:.2f}EN")

            # EN
            self._test_model()

        except Exception as e:
            logger.error(f"❌ EN: {e}")
            raise RuntimeError(f"EN {self.model_path}: {e}")

    def _test_model(self):
        """EN"""
        try:
            test_response = self.model("Hello", max_tokens=5, echo=False)
            logger.info("✅ EN")
        except Exception as e:
            logger.error(f"❌ EN: {e}")
            raise RuntimeError(f"EN: {e}")

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        stop: Optional[List[str]] = None,
        stream: bool = False,
        **kwargs,
    ) -> str:
        """
        EN(EN OllamaClient EN)

        Args:
            prompt: EN
            temperature: EN
            max_tokens: ENtokenEN
            top_p: nucleusEN
            top_k: top-kEN
            repeat_penalty: EN
            stop: EN
            stream: EN(EN)
            **kwargs: EN

        Returns:
            EN
        """
        # EN
        temperature = (
            temperature
            if temperature is not None
            else getattr(settings, "default_temperature", 0.7)
        )
        max_tokens = (
            max_tokens
            if max_tokens is not None
            else getattr(settings, "default_max_tokens", 2000)
        )
        top_p = top_p if top_p is not None else getattr(settings, "default_top_p", 0.9)
        top_k = top_k if top_k is not None else 40
        repeat_penalty = repeat_penalty if repeat_penalty is not None else 1.1

        try:
            response = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repeat_penalty=repeat_penalty,
                stop=stop,
                echo=False,
            )

            return response["choices"][0]["text"]

        except Exception as e:
            logger.error(f"EN: {e}")
            raise RuntimeError(f"LLM generation failed: {e}")

    def chat(
        self,
        messages: list,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> str:
        """
        EN(EN OllamaClient EN)

        Args:
            messages: EN [{"role": "user", "content": "..."}]
            temperature: EN
            max_tokens: ENtokenEN
            top_p: nucleusEN

        Returns:
            EN
        """
        # EN
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        prompt = "\n".join(prompt_parts) + "\nAssistant:"

        return self.generate(
            prompt=prompt, temperature=temperature, max_tokens=max_tokens, top_p=top_p
        )

    def get_model_info(self) -> Dict[str, Any]:
        """EN"""
        return {
            "model": Path(self.model_path).name,
            "model_path": self.model_path,
            "backend": "llama.cpp",
            "n_ctx": self.n_ctx,
            "n_threads": self.n_threads,
            "n_gpu_layers": self.n_gpu_layers,
            "gpu_acceleration": self.n_gpu_layers > 0,
            "n_batch": self.n_batch,
        }

    def get_current_config(self) -> Dict[str, Any]:
        """EN(EN OllamaClient)"""
        return {
            "model": Path(self.model_path).name,
            "base_url": "local",
            "default_temperature": getattr(settings, "default_temperature", 0.7),
            "default_max_tokens": getattr(settings, "default_max_tokens", 2000),
            "default_top_p": getattr(settings, "default_top_p", 0.9),
        }

    def list_models(self) -> list:
        """EN(EN OllamaClient)"""
        models_dir = Path("models")
        if models_dir.exists():
            return [
                {"name": f.name, "size": f.stat().st_size}
                for f in models_dir.glob("*.gguf")
            ]
        return []

    def update_config(self, **kwargs):
        """EN(EN OllamaClient)"""
        logger.info(f"EN: {kwargs}")

    def get_memory_usage(self) -> Dict[str, float]:
        """EN"""
        process = psutil.Process(os.getpid())
        return {
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent(),
        }

    def unload_model(self):
        """EN"""
        if self.model:
            del self.model
            self.model = None
            logger.info("✅ EN,EN")

    def is_loaded(self) -> bool:
        """EN"""
        return self.model is not None
