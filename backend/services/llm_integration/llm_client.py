"""
LLM EN
EN Ollama EN llama.cpp EN
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """LLMEN"""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ) -> str:
        """EN"""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """EN"""
        pass


class LLMClientFactory:
    """LLMEN"""

    @staticmethod
    def _normalize_backend(backend: Optional[str]) -> str:
        value = (backend or "").strip().lower()
        if value in {"llama_cpp", "ollama", "zhipu"}:
            return value
        # EN:ENbackendEN,EN
        local_backend = getattr(settings, "resolved_local_backend", "llama_cpp")
        return (
            local_backend if local_backend in {"llama_cpp", "ollama"} else "llama_cpp"
        )

    @staticmethod
    def create_client(backend: str = None) -> BaseLLMClient:
        """
        ENLLMEN

        Args:
            backend: EN ("ollama" EN "llama_cpp")

        Returns:
            LLMEN
        """
        backend = LLMClientFactory._normalize_backend(
            backend or getattr(settings, "llm_backend", "llama_cpp")
        )

        try:
            if backend == "ollama":
                from .ollama_client import OllamaClient

                logger.info("✅ EN Ollama EN")
                return OllamaClient()
            elif backend == "llama_cpp":
                from .llama_cpp_client import LlamaCppClient

                logger.info("✅ EN llama.cpp EN")
                return LlamaCppClient()
            elif backend == "zhipu":
                from .zhipu_client import ZhipuClient

                logger.info("✅ EN EN")
                return ZhipuClient()
            else:
                raise ValueError(f"Unsupported LLM backend: {backend}")

        except ImportError as e:
            logger.error(f"EN {backend} EN: {e}")

            # EN
            if backend == "llama_cpp":
                logger.warning("llama.cpp EN,EN Ollama")
                from .ollama_client import OllamaClient

                return OllamaClient()
            if backend == "zhipu":
                raise RuntimeError("Zhipu client requires the requests library")
            else:
                raise RuntimeError(f"Failed to create LLM client: {e}")

        except Exception as e:
            logger.error(f"EN {backend} EN: {e}")
            raise RuntimeError(f"LLM client initialization failed: {e}")


def get_llm_client() -> BaseLLMClient:
    """ENLLMEN"""
    try:
        return LLMClientFactory.create_client()
    except Exception as e:
        logger.error(f"ENLLMEN: {e}")
        raise


def get_backend_status() -> Dict[str, Any]:
    """EN"""
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
        logger.error(f"EN: {e}")
        return {
            "status": "error",
            "backend": getattr(settings, "llm_backend", "unknown"),
            "error": str(e),
        }
