"""
LLM Client Factory
Supports Ollama and llama.cpp backends.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ) -> str:
        """Generate a response from the given prompt."""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Return model information and configuration."""
        pass


class LLMClientFactory:
    """Factory for creating LLM client instances."""

    @staticmethod
    def _normalize_backend(backend: Optional[str]) -> str:
        value = (backend or "").strip().lower()
        if value in {"llama_cpp", "ollama", "zhipu"}:
            return value
        # Fallback: unrecognized backend value, use resolved local backend
        local_backend = getattr(settings, "resolved_local_backend", "llama_cpp")
        return (
            local_backend if local_backend in {"llama_cpp", "ollama"} else "llama_cpp"
        )

    @staticmethod
    def create_client(backend: str = None) -> BaseLLMClient:
        """
        Create an LLM client for the specified backend.

        Args:
            backend: Backend type ("ollama" or "llama_cpp")

        Returns:
            An initialized LLM client instance
        """
        backend = LLMClientFactory._normalize_backend(
            backend or getattr(settings, "llm_backend", "llama_cpp")
        )

        try:
            if backend == "ollama":
                from .ollama_client import OllamaClient

                logger.info("Using Ollama backend")
                return OllamaClient()
            elif backend == "llama_cpp":
                from .llama_cpp_client import LlamaCppClient

                logger.info("Using llama.cpp backend")
                return LlamaCppClient()
            elif backend == "zhipu":
                from .zhipu_client import ZhipuClient

                logger.info("Using Zhipu cloud backend")
                return ZhipuClient()
            else:
                raise ValueError(f"Unsupported LLM backend: {backend}")

        except ImportError as e:
            logger.error(f"Failed to import {backend} client: {e}")

            # Fallback logic
            if backend == "llama_cpp":
                logger.warning("llama.cpp client unavailable, falling back to Ollama")
                from .ollama_client import OllamaClient

                return OllamaClient()
            if backend == "zhipu":
                raise RuntimeError("Zhipu client requires the requests library")
            else:
                raise RuntimeError(f"Failed to create LLM client: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize {backend} client: {e}")
            raise RuntimeError(f"LLM client initialization failed: {e}")


def get_llm_client() -> BaseLLMClient:
    """Get the default LLM client based on configuration."""
    try:
        return LLMClientFactory.create_client()
    except Exception as e:
        logger.error(f"Failed to create LLM client: {e}")
        raise


def get_backend_status() -> Dict[str, Any]:
    """Get the current LLM backend status and model info."""
    try:
        client = get_llm_client()
        backend = getattr(settings, "llm_backend", "unknown")

        return {
            "status": "success",
            "backend": backend,
            "model_info": client.get_model_info(),
            "is_loaded": client.is_loaded() if hasattr(client, "is_loaded") else True,
        }
    except Exception as e:
        logger.error(f"Failed to get backend status: {e}")
        return {
            "status": "error",
            "backend": getattr(settings, "llm_backend", "unknown"),
            "error": str(e),
        }
