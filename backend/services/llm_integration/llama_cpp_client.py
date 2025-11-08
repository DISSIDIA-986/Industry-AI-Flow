"""
llama.cpp 客户端实现
提供本地 GGUF 模型推理功能，支持 Metal 加速
"""
import os
import logging
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
import psutil

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

from backend.config import settings

logger = logging.getLogger(__name__)


class LlamaCppClient:
    """llama.cpp 客户端，支持 GGUF 格式模型"""

    def __init__(
        self,
        model_path: str = None,
        n_ctx: int = None,
        n_threads: int = None,
        n_gpu_layers: int = -1,
        n_batch: int = 512,
        verbose: bool = False
    ):
        """
        初始化 llama.cpp 客户端

        Args:
            model_path: 模型文件路径
            n_ctx: 上下文窗口大小
            n_threads: CPU线程数（默认自动检测）
            n_gpu_layers: GPU层数 (-1=全部使用GPU, 0=纯CPU)
            n_batch: 批处理大小
            verbose: 是否输出详细日志
        """
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError(
                "llama-cpp-python 未安装。请运行: "
                "CMAKE_ARGS='-DGGML_METAL=on' pip install llama-cpp-python"
            )

        self.model_path = model_path or getattr(settings, 'llama_model_path', 'models/qwen2.5-7b-instruct.gguf')
        self.n_ctx = n_ctx or getattr(settings, 'llama_context_size', 4096)
        self.n_threads = n_threads or getattr(settings, 'llama_threads', os.cpu_count() or 8)
        self.n_gpu_layers = n_gpu_layers
        self.n_batch = n_batch
        self.verbose = verbose
        self.model = None

        # 验证模型文件
        if not self._validate_model_file():
            raise FileNotFoundError(f"模型文件不存在或不可读: {self.model_path}")

        # 自动检测GPU
        if self.n_gpu_layers == -1:
            self.n_gpu_layers = self._detect_gpu_layers()

        # 加载模型
        self._load_model()

    def _validate_model_file(self) -> bool:
        """验证模型文件"""
        model_path = Path(self.model_path)

        if not model_path.exists():
            logger.error(f"模型文件不存在: {self.model_path}")
            return False

        if not model_path.is_file():
            logger.error(f"模型路径不是文件: {self.model_path}")
            return False

        file_size = model_path.stat().st_size
        if file_size < 1024 * 1024:  # 小于1MB可能不完整
            logger.warning(f"模型文件过小，可能不完整: {file_size} bytes")

        logger.info(f"✅ 模型文件验证通过: {self.model_path} ({file_size / (1024**3):.2f} GB)")
        return True

    def _detect_gpu_layers(self) -> int:
        """自动检测GPU并返回适当的层数"""
        try:
            import torch
            if torch.backends.mps.is_available():
                logger.info("✅ 检测到 Apple Silicon Metal，启用 GPU 加速")
                return -1  # 使用所有GPU层
        except ImportError:
            logger.info("torch 未安装，跳过GPU检测")
        except Exception as e:
            logger.warning(f"GPU检测失败: {e}")

        logger.info("使用CPU推理模式")
        return 0  # 纯CPU模式

    def _load_model(self):
        """加载模型"""
        try:
            logger.info(f"开始加载模型: {Path(self.model_path).name}")
            logger.info(f"配置 - 上下文: {self.n_ctx}, 线程: {self.n_threads}, GPU层: {self.n_gpu_layers}")

            start_time = time.time()
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                n_batch=self.n_batch,
                verbose=self.verbose
            )

            load_time = time.time() - start_time
            logger.info(f"✅ 模型加载成功，耗时: {load_time:.2f}秒")

            # 测试模型
            self._test_model()

        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            raise RuntimeError(f"无法加载模型 {self.model_path}: {e}")

    def _test_model(self):
        """测试模型功能"""
        try:
            test_response = self.model("Hello", max_tokens=5, echo=False)
            logger.info("✅ 模型功能测试通过")
        except Exception as e:
            logger.error(f"❌ 模型功能测试失败: {e}")
            raise RuntimeError(f"模型功能异常: {e}")

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
        **kwargs
    ) -> str:
        """
        生成文本（兼容 OllamaClient 接口）

        Args:
            prompt: 输入提示词
            temperature: 温度参数
            max_tokens: 最大生成token数
            top_p: nucleus采样参数
            top_k: top-k采样参数
            repeat_penalty: 重复惩罚
            stop: 停止词列表
            stream: 是否流式输出（暂不支持）
            **kwargs: 其他参数

        Returns:
            生成的文本
        """
        # 使用传入参数或默认值
        temperature = temperature if temperature is not None else getattr(settings, 'default_temperature', 0.7)
        max_tokens = max_tokens if max_tokens is not None else getattr(settings, 'default_max_tokens', 2000)
        top_p = top_p if top_p is not None else getattr(settings, 'default_top_p', 0.9)
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
                echo=False
            )

            return response["choices"][0]["text"]

        except Exception as e:
            logger.error(f"文本生成失败: {e}")
            raise RuntimeError(f"LLM generation failed: {e}")

    def chat(
        self,
        messages: list,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None
    ) -> str:
        """
        对话模式生成（兼容 OllamaClient 接口）

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            top_p: nucleus采样参数

        Returns:
            生成的回复
        """
        # 将消息列表转换为提示词
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
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model": Path(self.model_path).name,
            "model_path": self.model_path,
            "backend": "llama.cpp",
            "n_ctx": self.n_ctx,
            "n_threads": self.n_threads,
            "n_gpu_layers": self.n_gpu_layers,
            "gpu_acceleration": self.n_gpu_layers > 0,
            "n_batch": self.n_batch
        }

    def get_current_config(self) -> Dict[str, Any]:
        """获取当前配置（兼容 OllamaClient）"""
        return {
            "model": Path(self.model_path).name,
            "base_url": "local",
            "default_temperature": getattr(settings, 'default_temperature', 0.7),
            "default_max_tokens": getattr(settings, 'default_max_tokens', 2000),
            "default_top_p": getattr(settings, 'default_top_p', 0.9)
        }

    def list_models(self) -> list:
        """列出可用模型（兼容 OllamaClient）"""
        models_dir = Path("models")
        if models_dir.exists():
            return [
                {"name": f.name, "size": f.stat().st_size}
                for f in models_dir.glob("*.gguf")
            ]
        return []

    def update_config(self, **kwargs):
        """更新配置（兼容 OllamaClient）"""
        logger.info(f"更新配置: {kwargs}")

    def get_memory_usage(self) -> Dict[str, float]:
        """获取内存使用情况"""
        process = psutil.Process(os.getpid())
        return {
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent()
        }

    def unload_model(self):
        """卸载模型以释放内存"""
        if self.model:
            del self.model
            self.model = None
            logger.info("✅ 模型已卸载，内存已释放")

    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.model is not None
