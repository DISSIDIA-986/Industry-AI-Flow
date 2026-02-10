"""
LLM 客户端抽象层
支持 Ollama 和 llama.cpp 后端切换
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """LLM客户端抽象基类"""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ) -> str:
        """生成文本"""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass


class LLMClientFactory:
    """LLM客户端工厂类"""

    @staticmethod
    def _normalize_backend(backend: Optional[str]) -> str:
        value = (backend or "").strip().lower()
        if value in {"llama_cpp", "ollama", "zhipu"}:
            return value
        # 兼容旧配置：当未显式给出backend时，优先取统一控制平面解析结果
        local_backend = getattr(settings, "resolved_local_backend", "llama_cpp")
        return (
            local_backend if local_backend in {"llama_cpp", "ollama"} else "llama_cpp"
        )

    @staticmethod
    def create_client(backend: str = None) -> BaseLLMClient:
        """
        创建LLM客户端

        Args:
            backend: 后端类型 ("ollama" 或 "llama_cpp")

        Returns:
            LLM客户端实例
        """
        backend = LLMClientFactory._normalize_backend(
            backend or getattr(settings, "llm_backend", "llama_cpp")
        )

        try:
            if backend == "ollama":
                from .ollama_client import OllamaClient

                logger.info("✅ 使用 Ollama 后端")
                return OllamaClient()
            elif backend == "llama_cpp":
                from .llama_cpp_client import LlamaCppClient

                logger.info("✅ 使用 llama.cpp 后端")
                return LlamaCppClient()
            elif backend == "zhipu":
                from .zhipu_client import ZhipuClient

                logger.info("✅ 使用 智谱云端后端")
                return ZhipuClient()
            else:
                raise ValueError(f"不支持的后端: {backend}")

        except ImportError as e:
            logger.error(f"无法导入 {backend} 客户端: {e}")

            # 自动降级策略
            if backend == "llama_cpp":
                logger.warning("llama.cpp 不可用，降级到 Ollama")
                from .ollama_client import OllamaClient

                return OllamaClient()
            if backend == "zhipu":
                raise RuntimeError("智谱客户端不可用，请检查 requests 依赖与配置")
            else:
                raise RuntimeError(f"缺少必要的依赖，请检查安装: {e}")

        except Exception as e:
            logger.error(f"创建 {backend} 客户端失败: {e}")
            raise RuntimeError(f"客户端初始化失败: {e}")


def get_llm_client() -> BaseLLMClient:
    """获取LLM客户端实例"""
    try:
        return LLMClientFactory.create_client()
    except Exception as e:
        logger.error(f"获取LLM客户端失败: {e}")
        raise


def get_backend_status() -> Dict[str, Any]:
    """获取当前后端状态信息"""
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
        logger.error(f"获取后端状态失败: {e}")
        return {
            "status": "error",
            "backend": getattr(settings, "llm_backend", "unknown"),
            "error": str(e),
        }
