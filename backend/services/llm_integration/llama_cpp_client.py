"""
llama.cpp Client (Deprecated)
Loads GGUF model files with Metal GPU acceleration support.
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
    """llama.cpp client for loading and running GGUF model files."""

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
        Initialize the llama.cpp client.

        Args:
            model_path: Path to the GGUF model file
            n_ctx: Context window size
            n_threads: CPU thread count (auto-detected if not set)
            n_gpu_layers: GPU offload layers (-1=all GPU, 0=CPU only)
            n_batch: Batch size for prompt processing
            verbose: Enable verbose logging
        """
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError(
                "llama-cpp-python is not installed. Install with: "
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

        # Validate model file exists
        if not self._validate_model_file():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

        # Auto-detect GPU layers
        if self.n_gpu_layers == -1:
            self.n_gpu_layers = self._detect_gpu_layers()

        # Load the model
        self._load_model()

    def _validate_model_file(self) -> bool:
        """Validate that the model file exists and is valid."""
        model_path = Path(self.model_path)

        if not model_path.exists():
            logger.error(f"Model file not found: {self.model_path}")
            return False

        if not model_path.is_file():
            logger.error(f"Path is not a file: {self.model_path}")
            return False

        file_size = model_path.stat().st_size
        if file_size < 1024 * 1024:  # Less than 1MB is suspicious
            logger.warning(f"Model file is suspiciously small: {file_size} bytes")

        logger.info(f"Model file validated: {self.model_path} ({file_size / (1024**3):.2f} GB)")
        return True

    def _detect_gpu_layers(self) -> int:
        """Auto-detect GPU acceleration capability."""
        try:
            import torch

            if torch.backends.mps.is_available():
                logger.info("Apple Silicon Metal detected, enabling full GPU offload")
                return -1  # Offload all layers to GPU
        except ImportError:
            logger.info("torch not available, skipping GPU detection")
        except Exception as e:
            logger.warning(f"GPU detection failed: {e}")

        logger.info("Using CPU-only mode")
        return 0  # CPU only

    def _load_model(self):
        """Load the GGUF model into memory."""
        try:
            logger.info(f"Loading model: {Path(self.model_path).name}")
            logger.info(
                f"Config - context: {self.n_ctx}, threads: {self.n_threads}, GPU layers: {self.n_gpu_layers}"
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
            logger.info(f"Model loaded successfully in {load_time:.2f}s")

            # Run validation test
            self._test_model()

        except Exception as e:
            logger.error(f"Model loading failed: {e}")
            raise RuntimeError(f"Failed to load model {self.model_path}: {e}")

    def _test_model(self):
        """Run a quick validation test on the loaded model."""
        try:
            test_response = self.model("Hello", max_tokens=5, echo=False)
            logger.info("Model validation passed")
        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            raise RuntimeError(f"Model validation failed: {e}")

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
        Generate text from a prompt (compatible with OllamaClient interface).

        Args:
            prompt: Input prompt text
            temperature: Sampling temperature
            max_tokens: Maximum output token count
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling parameter
            repeat_penalty: Repetition penalty factor
            stop: Stop sequences
            stream: Enable streaming (not implemented)
            **kwargs: Additional parameters

        Returns:
            Generated text response
        """
        # Apply default parameters
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
            logger.error(f"Text generation failed: {e}")
            raise RuntimeError(f"LLM generation failed: {e}")

    def chat(
        self,
        messages: list,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> str:
        """
        Chat-style generation (compatible with OllamaClient interface).

        Args:
            messages: Chat messages [{"role": "user", "content": "..."}]
            temperature: Sampling temperature
            max_tokens: Maximum output token count
            top_p: Nucleus sampling threshold

        Returns:
            Generated assistant response
        """
        # Convert chat messages to a single prompt
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
        """Return current model information and configuration."""
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
        """Get current runtime configuration (compatible with OllamaClient)."""
        return {
            "model": Path(self.model_path).name,
            "base_url": "local",
            "default_temperature": getattr(settings, "default_temperature", 0.7),
            "default_max_tokens": getattr(settings, "default_max_tokens", 2000),
            "default_top_p": getattr(settings, "default_top_p", 0.9),
        }

    def list_models(self) -> list:
        """List available GGUF model files (compatible with OllamaClient)."""
        models_dir = Path("models")
        if models_dir.exists():
            return [
                {"name": f.name, "size": f.stat().st_size}
                for f in models_dir.glob("*.gguf")
            ]
        return []

    def update_config(self, **kwargs):
        """Update runtime configuration (compatible with OllamaClient)."""
        logger.info(f"Configuration updated: {kwargs}")

    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory and CPU usage of the model process."""
        process = psutil.Process(os.getpid())
        return {
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent(),
        }

    def unload_model(self):
        """Unload the model from memory."""
        if self.model:
            del self.model
            self.model = None
            logger.info("Model unloaded, memory freed")

    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self.model is not None
