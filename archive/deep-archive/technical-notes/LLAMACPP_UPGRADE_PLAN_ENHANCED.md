# llama.cpp 升级计划 (增强版)

## 项目背景

当前项目使用 Ollama 作为 LLM 服务，通过 HTTP API 调用。升级到 llama.cpp 可以直接在本地硬件上运行模型，减少网络开销并提高性能，但会增加开发和维护复杂性。

## 当前 Ollama 实现分析

- **Ollama 客户端**: 位于 `backend/services/ollama_client.py`
- **HTTP API 调用**: 使用 requests 库调用 Ollama 服务
- **模型管理**: 依赖 Ollama 服务管理模型
- **配置**: 通过环境变量设置 Ollama 主机和模型

## 升级目标

1. 将 Ollama 客户端替换为直接 llama.cpp 集成
2. 维持现有 API 接口兼容性
3. 提升本地推理性能
4. 保持与 LangChain 组件的兼容性
5. 实现灵活的模型管理
6. **新增**: 强化错误处理、监控和内存管理

## 技术选型

使用 `llama-cpp-python` 作为 Python 绑定库，支持：
- CPU 推理
- CUDA GPU 加速（NVIDIA）
- Metal 加速（Apple Silicon）
- 多种量化格式（GGUF）

## 增强的升级计划

### 第一阶段：环境准备和依赖更新

1. **更新依赖文件** - **ENHANCED**
   ```txt
   # 基础依赖
   fastapi==0.104.1
   uvicorn[standard]==0.24.0
   psycopg2-binary==2.9.9
   pgvector==0.2.5
   sentence-transformers==2.2.2
   PyMuPDF==1.23.8
   requests==2.31.0
   pydantic==1.10.13
   psutil==5.9.6
   python-multipart==0.0.6

   # llama.cpp 相关依赖 - **VERSION SPECIFIED**
   llama-cpp-python==0.2.50  # 指定稳定版本
   huggingface-hub==0.20.3    # 模型管理需要
   torch>=2.0.0               # GPU检测和加速
   ```

2. **系统要求更新**
   ```bash
   # 可选：为GPU加速安装CUDA支持
   CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python==0.2.50
   # 或为Apple Silicon优化
   CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python==0.2.50
   ```

### 第二阶段：llama.cpp 客户端实现 - **ENHANCED ERROR HANDLING**

**目标**: 创建新的 `LlamaCppClient` 替换现有 `OllamaClient`，带强化错误处理

**新实现**: `backend/services/llama_cpp_client.py`

```python
import llama_cpp
from llama_cpp import Llama
from backend.config import settings
import os
import psutil
import logging
import time
from typing import Optional, Dict, Any, List
from pathlib import Path


class LlamaCppClient:
    def __init__(
        self,
        model_path: str = None,
        n_ctx: int = None,
        n_threads: int = None,
        n_gpu_layers: int = -1,
        batch_size: int = 512,
        verbose: bool = False
    ):
        """
        初始化 llama.cpp 客户端

        Args:
            model_path: 模型文件路径
            n_ctx: 上下文窗口大小
            n_threads: CPU线程数
            n_gpu_layers: GPU层数 (-1=全部)
            batch_size: 批处理大小
            verbose: 是否输出详细日志
        """
        self.model_path = model_path or settings.llama_model_path
        self.n_ctx = n_ctx or settings.llama_context_size
        self.n_threads = n_threads or settings.llama_threads
        self.n_gpu_layers = n_gpu_layers
        self.batch_size = batch_size
        self.verbose = verbose
        self.model = None

        # **ENHANCED**: 模型文件验证
        if not self._validate_model_file():
            raise FileNotFoundError(f"模型文件不存在或不可读: {self.model_path}")

        # **ENHANCED**: 自动检测并设置GPU
        try:
            self.n_gpu_layers = self._detect_gpu_layers()
        except Exception as e:
            logging.warning(f"GPU检测失败，使用CPU: {e}")
            self.n_gpu_layers = 0

        # **ENHANCED**: 模型加载
        self._load_model()

    def _validate_model_file(self) -> bool:
        """验证模型文件的存在性和可读性"""
        if not os.path.exists(self.model_path):
            logging.error(f"模型文件不存在: {self.model_path}")
            return False

        if not os.access(self.model_path, os.R_OK):
            logging.error(f"模型文件不可读: {self.model_path}")
            return False

        file_size = os.path.getsize(self.model_path)
        if file_size < 1024 * 1024:  # 小于1MB可能不完整
            logging.warning(f"模型文件过小，可能不完整: {file_size} bytes")

        logging.info(f"模型文件验证通过: {self.model_path} ({file_size / (1024**3):.2f} GB)")
        return True

    def _detect_gpu_layers(self) -> int:
        """自动检测并返回适当的GPU层数"""
        # 检查是否为NVIDIA GPU
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                logging.info(f"检测到GPU: {gpu_name}")
                # 根据环境变量或默认值设置GPU层数
                return int(os.getenv("LLAMA_GPU_LAYERS", "-1"))
        except ImportError:
            logging.info("torch未安装，跳过CUDA检测")
        except Exception as e:
            logging.warning(f"CUDA检测失败: {e}")

        # 检查是否为Apple Silicon
        try:
            import torch
            if torch.backends.mps.is_available():
                logging.info("检测到Apple Silicon，启用Metal加速")
                return int(os.getenv("LLAMA_GPU_LAYERS", "-1"))
        except ImportError:
            logging.info("torch未安装，跳过Metal检测")
        except Exception as e:
            logging.warning(f"Metal检测失败: {e}")

        # 没有检测到GPU，返回0
        logging.info("未检测到GPU，将使用CPU推理")
        return 0

    def _load_model(self):
        """加载模型并处理异常"""
        try:
            logging.info(f"开始加载模型: {os.path.basename(self.model_path)}")
            logging.info(f"配置 - 上下文: {self.n_ctx}, 线程: {self.n_threads}, GPU层: {self.n_gpu_layers}")

            start_time = time.time()
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                batch_size=self.batch_size,
                verbose=self.verbose,
                # **ENHANCED**: 额外的安全选项
                logits_all=False,
                embedding=False
            )

            load_time = time.time() - start_time
            logging.info(f"✅ 模型加载成功，耗时: {load_time:.2f}秒")

            # **ENHANCED**: 检查模型是否可以正常工作
            self._test_model()

        except Exception as e:
            logging.error(f"模型加载失败: {e}")
            raise RuntimeError(f"无法加载模型 {self.model_path}: {e}")

    def _test_model(self):
        """测试模型是否可以正常生成"""
        try:
            test_response = self.model("Hello", max_tokens=5, echo=False, stream=False)
            logging.info("✅ 模型功能测试通过")
        except Exception as e:
            logging.error(f"模型功能测试失败: {e}")
            raise RuntimeError(f"模型功能异常: {e}")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
        stop: Optional[List[str]] = None,
        timeout: int = 300,  # **ENHANCED**: 添加超时
        **kwargs
    ) -> str:
        """
        生成文本

        Args:
            prompt: 输入提示
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: top-p 采样
            top_k: top-k 采样
            repeat_penalty: 重复惩罚
            stop: 停止词列表
            timeout: 请求超时（秒）
            **kwargs: 其他参数

        Returns:
            生成的文本
        """
        try:
            # **ENHANCED**: 超时处理
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("模型生成超时")

            if timeout > 0:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)

            try:
                # llama.cpp generate 方法参数映射
                response = self.model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    repeat_penalty=repeat_penalty,
                    stop=stop,
                    echo=False,  # 不回显输入
                    stream=False
                )

                result = response["choices"][0]["text"]

                if timeout > 0:
                    signal.alarm(0)  # 取消超时

                return result

            except Exception as e:
                if timeout > 0:
                    signal.alarm(0)  # 确保取消超时
                raise e

        except TimeoutError:
            logging.error(f"模型生成超时 ({timeout}秒)")
            raise TimeoutError(f"模型生成超时，已取消请求")
        except Exception as e:
            logging.error(f"生成文本时发生错误: {e}")
            raise RuntimeError(f"文本生成失败: {e}")

    def tokenize(self, text: str) -> list[int]:
        """对文本进行token化"""
        try:
            return self.model.tokenize(text.encode("utf-8"))
        except Exception as e:
            logging.error(f"Tokenization失败: {e}")
            raise RuntimeError(f"文本tokenization失败: {e}")

    def detokenize(self, tokens: list[int]) -> str:
        """将tokens转换回文本"""
        try:
            return self.model.detokenize(tokens).decode("utf-8")
        except Exception as e:
            logging.error(f"Detokenization失败: {e}")
            raise RuntimeError(f"tokens转文本失败: {e}")

    def get_token_count(self, text: str) -> int:
        """获取文本的token数量"""
        try:
            tokens = self.tokenize(text)
            return len(tokens)
        except Exception as e:
            logging.error(f"Token计数失败: {e}")
            return 0

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_path": self.model_path,
            "n_ctx": self.n_ctx,
            "n_threads": self.n_threads,
            "n_gpu_layers": self.n_gpu_layers,
            "model_type": "llama.cpp",
            "gpu_acceleration": self.n_gpu_layers > 0,
            "batch_size": self.batch_size
        }

    def get_memory_usage(self) -> Dict[str, float]:
        """获取内存使用情况"""
        process = psutil.Process(os.getpid())
        return {
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent(),
            "model_memory_mb": self._estimate_model_memory()  # **ENHANCED**
        }

    def _estimate_model_memory(self) -> float:
        """估算模型内存使用"""
        # 粗略估算: 模型文件大小 * 1.5 (考虑加载后的内存开销)
        try:
            file_size = os.path.getsize(self.model_path)
            estimated_memory = (file_size * 1.5) / (1024 * 1024)  # MB
            return round(estimated_memory, 2)
        except:
            return 0.0

    def unload_model(self):
        """卸载模型以释放内存"""
        if self.model:
            del self.model
            self.model = None
            logging.info("✅ 模型已卸载，内存已释放")

    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.model is not None
```

### 第三阶段：配置文件更新 - **ENHANCED VALIDATION**

**目标**: 更新配置文件以支持 llama.cpp 特定设置，并添加验证功能

**更新文件**: `backend/config.py`

```python
import os
import logging
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # 数据库（支持本地homebrew PostgreSQL）
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "ai_workflow")
    postgres_user: str = os.getenv("POSTGRES_USER", "")  # 本地PostgreSQL留空使用当前用户
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")  # 本地PostgreSQL无密码

    # llama.cpp 配置
    llama_model_path: str = os.getenv("LLAMA_MODEL_PATH", "./models/qwen2.5-7b-instruct.Q4_K_M.gguf")
    llama_context_size: int = int(os.getenv("LLAMA_CONTEXT_SIZE", "4096"))
    llama_threads: int = int(os.getenv("LLAMA_THREADS", "8"))
    llama_batch_size: int = int(os.getenv("LLAMA_BATCH_SIZE", "512"))
    llama_gpu_layers: int = int(os.getenv("LLAMA_GPU_LAYERS", "-1"))  # -1 = 全部使用GPU
    llama_backend: str = os.getenv("LLAMA_BACKEND", "llama_cpp")  # 选项: "ollama", "llama_cpp"
    llama_max_tokens: int = int(os.getenv("LLAMA_MAX_TOKENS", "512"))
    llama_temperature: float = float(os.getenv("LLAMA_TEMPERATURE", "0.7"))
    llama_top_p: float = float(os.getenv("LLAMA_TOP_P", "0.9"))
    llama_top_k: int = int(os.getenv("LLAMA_TOP_K", "40"))
    llama_repeat_penalty: float = float(os.getenv("LLAMA_REPEAT_PENALTY", "1.1"))
    llama_generation_timeout: int = int(os.getenv("LLAMA_GENERATION_TIMEOUT", "300"))  # 秒

    # 向量化 (Phase 2: 升级到 nomic-embed-text-v1.5)
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1.5")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "768"))

    # 文档处理
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "300"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # RAG
    top_k: int = int(os.getenv("TOP_K", "5"))

    # OCR (Phase 2: PaddleOCR配置)
    ocr_lang: str = os.getenv("OCR_LANG", "en")  # 'en' 英文, 'ch' 中文, 'en+ch' 混合

    def model_post_init(self, __context):
        """配置验证和初始化后处理"""
        self._validate_config()
        self._setup_logging()

    def _validate_config(self):
        """验证配置参数的有效性"""
        errors = []

        # 验证路径
        if not Path(self.llama_model_path).exists():
            errors.append(f"模型文件不存在: {self.llama_model_path}")

        # 验证数值参数
        if self.llama_context_size <= 0:
            errors.append(f"上下文大小必须大于0: {self.llama_context_size}")

        if self.llama_threads <= 0:
            errors.append(f"线程数必须大于0: {self.llama_threads}")

        if self.llama_batch_size <= 0:
            errors.append(f"批处理大小必须大于0: {self.llama_batch_size}")

        if self.llama_max_tokens <= 0:
            errors.append(f"最大token数必须大于0: {self.llama_max_tokens}")

        # 验证浮点参数
        if not (0.0 <= self.llama_temperature <= 2.0):
            errors.append(f"temperature应在0.0-2.0之间: {self.llama_temperature}")

        if not (0.0 <= self.llama_top_p <= 1.0):
            errors.append(f"top_p应在0.0-1.0之间: {self.llama_top_p}")

        if not (0.0 <= self.llama_repeat_penalty <= 2.0):
            errors.append(f"repeat_penalty应在0.0-2.0之间: {self.llama_repeat_penalty}")

        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(errors)
            logging.error(error_msg)
            raise ValueError(error_msg)

    def _setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    @property
    def database_url(self) -> str:
        # 本地PostgreSQL: postgresql://localhost:5432/ai_workflow
        # Docker PostgreSQL: postgresql://user:password@localhost:5432/ai_workflow
        if self.postgres_user and self.postgres_password:
            return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        else:
            return f"postgresql://{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = Settings()
```

### 第四阶段：客户端抽象层实现 - **ENHANCED ERROR HANDLING**

**目标**: 创建客户端抽象层以支持 Ollama 和 llama.cpp 之间的切换，带错误处理

**新实现**: `backend/services/llm_client.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from backend.config import settings
import logging


class BaseLLMClient(ABC):
    """LLM客户端抽象基类"""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.1,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """生成文本"""
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        """获取模型信息"""
        pass


class LLMClientFactory:
    """LLM客户端工厂类"""

    @staticmethod
    def create_client(backend: str = None) -> BaseLLMClient:
        """
        创建LLM客户端

        Args:
            backend: 后端类型 ("ollama" 或 "llama_cpp")

        Returns:
            LLM客户端实例
        """
        backend = backend or settings.llama_backend

        try:
            if backend == "ollama":
                from .ollama_client import OllamaClient
                logging.info("✅ 使用 Ollama 后端")
                return OllamaClient()
            elif backend == "llama_cpp":
                from .llama_cpp_client import LlamaCppClient
                logging.info("✅ 使用 llama.cpp 后端")
                return LlamaCppClient()
            else:
                raise ValueError(f"不支持的后端: {backend}")
        except ImportError as e:
            logging.error(f"无法导入 {backend} 客户端: {e}")
            raise RuntimeError(f"缺少必要的依赖，请检查安装: {e}")
        except Exception as e:
            logging.error(f"创建 {backend} 客户端失败: {e}")
            raise RuntimeError(f"客户端初始化失败: {e}")


# 便捷函数
def get_llm_client() -> BaseLLMClient:
    """获取LLM客户端实例"""
    try:
        return LLMClientFactory.create_client()
    except Exception as e:
        logging.error(f"获取LLM客户端失败: {e}")
        # **ENHANCED**: 降级策略
        if settings.llama_backend != "ollama":
            logging.info("尝试降级到 Ollama 后端...")
            return LLMClientFactory.create_client("ollama")
        else:
            raise e


def get_backend_status() -> Dict[str, Any]:
    """获取当前后端状态信息"""
    try:
        client = get_llm_client()
        return {
            "status": "success",
            "backend": settings.llama_backend,
            "model_info": client.get_model_info(),
            "is_loaded": hasattr(client, 'is_loaded') and client.is_loaded() if hasattr(client, 'is_loaded') else True
        }
    except Exception as e:
        logging.error(f"获取后端状态失败: {e}")
        return {
            "status": "error",
            "backend": settings.llama_backend,
            "error": str(e)
        }
```

### 第五阶段：现有组件适配 - **ENHANCED MONITORING**

**目标**: 更新现有组件以使用新的客户端抽象，添加监控功能

**更新文件**: `backend/services/rag_engine.py`

```python
from backend.services.embedder import embed_single_text
from backend.services.vectorstore import VectorStore
from backend.services.llm_client import get_llm_client, BaseLLMClient, get_backend_status
from backend.services.retrieval.hybrid_search import HybridRetriever
from backend.services.retrieval.reranker import Reranker
from backend.config import settings
import time
import logging
from typing import Dict, Any, Optional


class SimpleRAG:
    def __init__(self, use_hybrid_search: bool = True, use_reranker: bool = True):
        """
        初始化 RAG 系统

        Args:
            use_hybrid_search: 是否使用混合检索（BM25 + 向量）
            use_reranker: 是否使用重排序模块
        """
        self.vectorstore = VectorStore()
        self.llm_client = get_llm_client()  # 使用工厂方法获取客户端
        self.use_hybrid_search = use_hybrid_search
        self.use_reranker = use_reranker

        # Phase 2 Step 2: 初始化混合检索器
        if use_hybrid_search:
            self.hybrid_retriever = HybridRetriever(self.vectorstore)
        else:
            self.hybrid_retriever = None

        # Phase 2 Step 3: 初始化重排序器
        if use_reranker:
            self.reranker = Reranker()
        else:
            self.reranker = None

        # **ENHANCED**: 监控初始化
        self._log_initialization()

    def _log_initialization(self):
        """记录初始化信息"""
        backend_info = get_backend_status()
        logging.info(f"RAG引擎初始化完成 - 后端: {backend_info.get('backend', 'unknown')}")
        logging.info(f"混合检索: {self.use_hybrid_search}, 重排序: {self.use_reranker}")

    def query(self, question: str, top_k: int = None) -> Dict[str, Any]:
        """RAG查询流程"""
        start_time = time.time()

        # **ENHANCED**: 记录查询开始
        logging.info(f"开始RAG查询: {question[:50]}...")

        if top_k is None:
            top_k = settings.top_k

        try:
            # Phase 2 Step 2: 使用混合检索或纯向量检索
            retrieve_start = time.time()
            if self.use_hybrid_search and self.hybrid_retriever:
                # 混合检索（BM25 + 向量），先获取更多候选（top_k * 2）
                retrieve_k = top_k * 2 if self.use_reranker else top_k
                similar_chunks = self.hybrid_retriever.search(
                    query=question, top_k=retrieve_k, vector_weight=0.7, bm25_weight=0.3
                )
            else:
                # 纯向量检索（Phase 1 方法）
                retrieve_k = top_k * 2 if self.use_reranker else top_k
                query_embedding = embed_single_text(question)
                similar_chunks = self.vectorstore.similarity_search(query_embedding, top_k=retrieve_k)

            retrieve_time = time.time() - retrieve_start

            # Phase 2 Step 3: 使用重排序器精排
            rerank_time = 0
            if self.use_reranker and self.reranker and similar_chunks:
                rerank_start = time.time()
                similar_chunks = self.reranker.rerank(
                    query=question, documents=similar_chunks, top_k=top_k
                )
                rerank_time = time.time() - rerank_start

            # 3. 构建提示词
            # 为每个文档块添加编号，提高可读性
            context_parts = []
            for i, chunk in enumerate(similar_chunks, 1):
                context_parts.append(f"[文档{i}]\n{chunk['content']}")
            context = "\n\n".join(context_parts)

            # 4. LLM生成答案
            llm_start = time.time()

            # **ENHANCED**: 使用配置中的参数
            answer = self.llm_client.generate(
                context + f"\n\n用户问题：{question}\n\n你的回答：",
                max_tokens=settings.llama_max_tokens,
                temperature=settings.llama_temperature,
                top_p=settings.llama_top_p,
                top_k=settings.llama_top_k,
                repeat_penalty=settings.llama_repeat_penalty,
                timeout=settings.llama_generation_timeout
            )
            llm_time = time.time() - llm_start

            # 5. 返回结果
            result = {
                "question": question,
                "answer": answer,
                "sources": [chunk['doc_id'] for chunk in similar_chunks],
                "retrieved_chunks": similar_chunks,
                # **ENHANCED**: 性能监控数据
                "timing": {
                    "total": round(time.time() - start_time, 2),
                    "retrieve": round(retrieve_time, 2),
                    "rerank": round(rerank_time, 2),
                    "llm": round(llm_time, 2)
                },
                "backend": get_backend_status()
            }

            # **ENHANCED**: 记录性能指标
            logging.info(
                f"RAG查询完成 - 总耗时: {result['timing']['total']:.2f}s, "
                f"检索: {result['timing']['retrieve']:.2f}s, "
                f"重排序: {result['timing']['rerank']:.2f}s, "
                f"LLM: {result['timing']['llm']:.2f}s"
            )

            return result

        except Exception as e:
            logging.error(f"RAG查询失败: {e}")
            # **ENHANCED**: 返回错误信息
            return {
                "question": question,
                "answer": f"处理查询时发生错误: {str(e)}",
                "sources": [],
                "retrieved_chunks": [],
                "error": str(e),
                "timing": {
                    "total": round(time.time() - start_time, 2)
                },
                "backend": get_backend_status()
            }

    def get_backend_info(self) -> Dict[str, Any]:
        """获取当前使用的后端信息"""
        return self.llm_client.get_model_info()

    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            if hasattr(self.llm_client, 'get_memory_usage'):
                return self.llm_client.get_memory_usage()
            else:
                import psutil
                import os
                process = psutil.Process(os.getpid())
                return {
                    "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2)
                }
        except Exception as e:
            logging.error(f"获取内存使用情况失败: {e}")
            return {"error": str(e)}
```

### 第六阶段：并发处理和队列机制 - **NEW ENHANCED FEATURE**

**目标**: 实现请求队列机制处理并发访问

**新文件**: `backend/services/llm_queue.py`

```python
import asyncio
import logging
from typing import Callable, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import threading
import time


class LLMRequestQueue:
    """LLM请求队列，处理并发请求"""

    def __init__(self, max_workers: int = 1, queue_size: int = 10):
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.request_queue = Queue(maxsize=queue_size)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.is_running = False
        self.worker_thread = None

    def start(self):
        """启动队列处理器"""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
            logging.info(f"LLM请求队列启动: {self.max_workers} 工作线程, 队列大小: {self.queue_size}")

    def stop(self):
        """停止队列处理器"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        self.executor.shutdown(wait=True)
        logging.info("LLM请求队列已停止")

    def submit_request(self, func: Callable, *args, **kwargs) -> asyncio.Future:
        """提交请求到队列"""
        future = self.executor.submit(func, *args, **kwargs)
        return future

    def _process_queue(self):
        """处理队列中的请求"""
        while self.is_running:
            try:
                if not self.request_queue.empty():
                    task = self.request_queue.get(timeout=1)
                    if task is None:
                        break
                    # 执行任务
                    func, args, kwargs = task
                    try:
                        result = func(*args, **kwargs)
                        logging.debug("请求处理完成")
                    except Exception as e:
                        logging.error(f"请求处理失败: {e}")
                    finally:
                        self.request_queue.task_done()
                else:
                    time.sleep(0.1)  # 避免CPU占用过高
            except Exception as e:
                logging.error(f"队列处理异常: {e}")

    def get_queue_status(self) -> dict:
        """获取队列状态"""
        return {
            "pending_requests": self.request_queue.qsize(),
            "max_workers": self.max_workers,
            "queue_size": self.queue_size,
            "is_running": self.is_running
        }


# 全局队列实例
llm_queue = LLMRequestQueue(max_workers=1)  # 对于llama.cpp，单线程处理可能更好


def get_llm_queue() -> LLMRequestQueue:
    """获取全局队列实例"""
    return llm_queue
```

### 第七阶段：增强测试框架 - **ENHANCED**

**目标**: 增加单元测试和集成测试

**更新文件**: `scripts/test_rag_enhanced.py`

```python
import time
import json
import unittest
from unittest.mock import Mock, patch
from backend.services.rag_engine import SimpleRAG
from backend.services.llm_client import get_llm_client, get_backend_status
from backend.config import settings
import psutil
import os


class LlamaCppClientTest(unittest.TestCase):
    """llama.cpp 客户端单元测试"""

    def setUp(self):
        """测试前准备"""
        self.client = get_llm_client()

    def test_model_info(self):
        """测试模型信息获取"""
        info = self.client.get_model_info()
        self.assertIn('model_path', info)
        self.assertIn('model_type', info)
        self.assertIsNotNone(info['model_path'])

    def test_generate_text(self):
        """测试文本生成"""
        response = self.client.generate(
            "你好",
            max_tokens=20,
            temperature=0.1
        )
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_tokenization(self):
        """测试token化功能"""
        text = "Hello world"
        tokens = self.client.tokenize(text)
        self.assertIsInstance(tokens, list)
        self.assertGreater(len(tokens), 0)

        decoded = self.client.detokenize(tokens)
        self.assertEqual(decoded.strip(), text)

    def test_token_count(self):
        """测试token计数"""
        text = "Hello world"
        count = self.client.get_token_count(text)
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)


class RAGIntegrationTest(unittest.TestCase):
    """RAG系统集成测试"""

    def setUp(self):
        """测试前准备"""
        self.rag = SimpleRAG()

    def test_backend_status(self):
        """测试后端状态"""
        status = get_backend_status()
        self.assertIn('status', status)
        self.assertIn('backend', status)

    def test_memory_usage(self):
        """测试内存使用获取"""
        memory_info = self.rag.get_memory_usage()
        self.assertIsInstance(memory_info, dict)

    @patch('backend.services.vectorstore.VectorStore.similarity_search')
    def test_query_with_mock_retrieval(self, mock_search):
        """测试查询功能（模拟检索）"""
        # 模拟检索结果
        mock_chunks = [
            {
                "doc_id": "test_id",
                "content": "这是一个测试文档",
                "distance": 0.1,
                "filename": "test.pdf"
            }
        ]
        mock_search.return_value = mock_chunks

        result = self.rag.query("测试问题")

        self.assertIn('question', result)
        self.assertIn('answer', result)
        self.assertIn('timing', result)
        self.assertEqual(result['question'], "测试问题")
        self.assertIsInstance(result['timing'], dict)

    def test_performance_monitoring(self):
        """测试性能监控"""
        start_time = time.time()
        result = self.rag.query("性能测试问题")
        end_time = time.time()

        # 验证时间记录
        self.assertIn('timing', result)
        timing = result['timing']
        self.assertIn('total', timing)
        self.assertGreaterEqual(timing['total'], 0)

        # 验证总时间与实际时间的合理关系
        actual_time = end_time - start_time
        self.assertLessEqual(timing['total'], actual_time + 1)  # 允许1秒误差


def run_performance_benchmark():
    """性能基准测试"""
    print("\n📊 性能基准测试...")

    try:
        rag = SimpleRAG()

        # 准备测试数据
        test_prompts = [
            "什么是人工智能?",
            "介绍一下机器学习的基本概念",
            "RAG系统如何工作?",
            "向量数据库有什么优势?",
            "如何优化大语言模型的性能?"
        ]

        total_time = 0
        total_tokens = 0
        success_count = 0

        for i, prompt in enumerate(test_prompts):
            print(f"  测试 {i+1}/5: {prompt[:30]}...")

            start_time = time.time()
            try:
                result = rag.query(prompt)
                end_time = time.time()

                response_time = end_time - start_time
                total_time += response_time
                if 'answer' in result:
                    total_tokens += len(result['answer'].split())

                success_count += 1
                print(f"    耗时: {response_time:.2f}秒, 生成 {len(result.get('answer', '').split())} 个词")

            except Exception as e:
                print(f"    ❌ 失败: {e}")

        if success_count > 0:
            avg_time = total_time / success_count
            avg_tokens_per_sec = total_tokens / total_time if total_time > 0 else 0

            print(f"\n📈 性能统计:")
            print(f"  成功请求: {success_count}/{len(test_prompts)}")
            print(f"  平均响应时间: {avg_time:.2f}秒")
            print(f"  平均吞吐量: {avg_tokens_per_sec:.2f} 词/秒")
            print(f"  总生成词数: {total_tokens}")

        return success_count == len(test_prom
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        return False


def run_stress_test():
    """压力测试"""
    print("\n💪 压力测试...")

    try:
        import threading
        import time

        rag = SimpleRAG()
        results = []
        errors = []

        def worker(prompt, worker_id):
            start_time = time.time()
            try:
                result = rag.query(prompt)
                end_time = time.time()
                results.append({
                    'worker_id': worker_id,
                    'response_time': end_time - start_time,
                    'success': True
                })
            except Exception as e:
                end_time = time.time()
                errors.append({
                    'worker_id': worker_id,
                    'error': str(e),
                    'response_time': end_time - start_time
                })

        # 创建多个线程并发请求
        threads = []
        test_prompts = ["测试"] * 5  # 5个并发请求
        for i, prompt in enumerate(test_prompts):
            thread = threading.Thread(target=worker, args=(prompt, i))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        print(f"  总请求: {len(test_prompts)}")
        print(f"  成功: {len(results)}")
        print(f"  失败: {len(errors)}")

        if results:
            avg_time = sum(r['response_time'] for r in results) / len(results)
            print(f"  平均响应时间: {avg_time:.2f}秒")

        return len(errors) == 0

    except Exception as e:
        print(f"❌ 压力测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 llama.cpp 增强版集成测试开始")
    print(f"📊 当前后端配置: {settings.llama_backend}")
    print(f"📂 模型路径: {settings.llama_model_path}")

    # 运行单元测试
    print("\n🧪 运行单元测试...")
    loader = unittest.TestLoader()

    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加客户端测试
    try:
        client_tests = loader.loadTestsFromTestCase(LlamaCppClientTest)
        suite.addTests(client_tests)
    except Exception as e:
        print(f"❌ 客户端测试加载失败: {e}")

    # 添加集成测试
    try:
        integration_tests = loader.loadTestsFromTestCase(RAGIntegrationTest)
        suite.addTests(integration_tests)
    except Exception as e:
        print(f"❌ 集成测试加载失败: {e}")

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 运行性能测试
    print(f"\n{'='*50}")
    performance_passed = run_performance_benchmark()

    # 运行压力测试
    print(f"\n{'='*50}")
    stress_passed = run_stress_test()

    # 汇总结果
    print(f"\n{'='*50}")
    print("📋 测试结果汇总:")
    print(f"  单元测试: {'✅ 通过' if result.wasSuccessful() else '❌ 失败'} ({result.testsRun} 个测试)")
    print(f"  性能测试: {'✅ 通过' if performance_passed else '❌ 失败'}")
    print(f"  压力测试: {'✅ 通过' if stress_passed else '❌ 失败'}")

    all_passed = result.wasSuccessful() and performance_passed and stress_passed

    if all_passed:
        print("\n🎉 所有测试通过！llama.cpp 集成成功")
    else:
        print("\n⚠️  部分测试失败，请检查实现")

    return all_passed


if __name__ == "__main__":
    main()
```

### 第八阶段：监控和告警 - **NEW ENHANCED FEATURE**

**目标**: 添加系统监控和告警功能

**新文件**: `backend/services/monitoring.py`

```python
import psutil
import time
import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading


@dataclass
class SystemMetrics:
    """系统指标数据类"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float


@dataclass
class ModelMetrics:
    """模型指标数据类"""
    timestamp: datetime
    backend: str
    generation_time: float
    input_tokens: int
    output_tokens: int
    memory_used_mb: float
    gpu_utilization: float if hasattr(psutil, 'sensors_temperatures') else None


class SystemMonitor:
    """系统监控器"""

    def __init__(self, monitor_interval: int = 5):
        self.monitor_interval = monitor_interval
        self.metrics_history: List[SystemMetrics] = []
        self.is_monitoring = False
        self.monitor_thread = None
        self._lock = threading.Lock()

    def start_monitoring(self):
        """开始监控"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logging.info(f"系统监控启动，间隔: {self.monitor_interval}秒")

    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logging.info("系统监控已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                metrics = self._collect_system_metrics()
                with self._lock:
                    self.metrics_history.append(metrics)
                    # 保留最近100条记录
                    if len(self.metrics_history) > 100:
                        self.metrics_history = self.metrics_history[-100:]
                time.sleep(self.monitor_interval)
            except Exception as e:
                logging.error(f"系统监控收集数据失败: {e}")
                time.sleep(self.monitor_interval)

    def _collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        net_io = psutil.net_io_counters()

        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_percent=psutil.virtual_memory().percent,
            memory_used_mb=psutil.virtual_memory().used / (1024**2),
            memory_available_mb=psutil.virtual_memory().available / (1024**2),
            disk_percent=psutil.disk_usage('/').percent,
            network_sent_mb=net_io.bytes_sent / (1024**2),
            network_recv_mb=net_io.bytes_recv / (1024**2)
        )

    def get_current_metrics(self) -> SystemMetrics:
        """获取当前系统指标"""
        return self._collect_system_metrics()

    def get_average_metrics(self, minutes: int = 5) -> Dict[str, float]:
        """获取指定时间内的平均指标"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.metrics_history
            if m.timestamp >= cutoff_time
        ]

        if not recent_metrics:
            return {}

        avg_metrics = {
            'cpu_percent': sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            'memory_percent': sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            'disk_percent': sum(m.disk_percent for m in recent_metrics) / len(recent_metrics)
        }

        return avg_metrics

    def get_alerts(self) -> List[str]:
        """检查是否需要告警"""
        alerts = []
        current = self.get_current_metrics()

        # CPU使用率告警
        if current.cpu_percent > 90:
            alerts.append(f"⚠️ CPU使用率过高: {current.cpu_percent}%")

        # 内存使用率告警
        if current.memory_percent > 90:
            alerts.append(f"⚠️ 内存使用率过高: {current.memory_percent}%")

        # 磁盘使用率告警
        if current.disk_percent > 90:
            alerts.append(f"⚠️ 磁盘使用率过高: {current.disk_percent}%")

        return alerts


class ModelMonitor:
    """模型监控器"""

    def __init__(self):
        self.metrics_history: List[ModelMetrics] = []
        self._lock = threading.Lock()

    def record_generation(
        self,
        generation_time: float,
        input_tokens: int,
        output_tokens: int,
        backend: str
    ):
        """记录生成指标"""
        # 获取内存使用情况
        process = psutil.Process()
        memory_used_mb = process.memory_info().rss / (1024**2)

        metrics = ModelMetrics(
            timestamp=datetime.now(),
            backend=backend,
            generation_time=generation_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            memory_used_mb=memory_used_mb,
            gpu_utilization=self._get_gpu_utilization() if self._gpu_available() else 0
        )

        with self._lock:
            self.metrics_history.append(metrics)
            # 保留最近100条记录
            if len(self.metrics_history) > 100:
                self.metrics_history = self.metrics_history[-100:]

    def _gpu_available(self) -> bool:
        """检查GPU是否可用"""
        try:
            import torch
            return torch.cuda.is_available() or torch.backends.mps.is_available()
        except ImportError:
            return False

    def _get_gpu_utilization(self) -> float:
        """获取GPU利用率"""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.utilization() if hasattr(torch.cuda, 'utilization') else 0
            elif torch.backends.mps.is_available():
                # Apple Silicon GPU监控较为复杂，返回估算值
                return 0  # MPS没有直接的利用率API
        except Exception:
            return 0

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        if not self.metrics_history:
            return {}

        # 计算平均值
        avg_gen_time = sum(m.generation_time for m in self.metrics_history) / len(self.metrics_history)
        avg_input_tokens = sum(m.input_tokens for m in self.metrics_history) / len(self.metrics_history)
        avg_output_tokens = sum(m.output_tokens for m in self.metrics_history) / len(self.metrics_history)
        avg_memory = sum(m.memory_used_mb for m in self.metrics_history) / len(self.metrics_history)

        # 计算吞吐量 (tokens/second)
        total_time = sum(m.generation_time for m in self.metrics_history)
        total_tokens = sum(m.output_tokens for m in self.metrics_history)
        throughput = total_tokens / total_time if total_time > 0 else 0

        return {
            'avg_generation_time': round(avg_gen_time, 2),
            'avg_input_tokens': round(avg_input_tokens),
            'avg_output_tokens': round(avg_output_tokens),
            'avg_memory_mb': round(avg_memory, 2),
            'avg_throughput': round(throughput, 2),  # tokens per second
            'total_requests': len(self.metrics_history),
            'time_window_minutes': (datetime.now() - self.metrics_history[0].timestamp).total_seconds() / 60
        }

    def get_alerts(self) -> List[str]:
        """检查模型性能告警"""
        alerts = []
        if not self.metrics_history:
            return alerts

        # 检查生成时间是否异常
        recent_metrics = self.metrics_history[-10:]  # 最近10次请求
        if recent_metrics:
            avg_recent_time = sum(m.generation_time for m in recent_metrics) / len(recent_metrics)
            overall_avg_time = sum(m.generation_time for m in self.metrics_history) / len(self.metrics_history)

            if avg_recent_time > overall_avg_time * 2:  # 如果最近平均时间是总体平均时间的2倍以上
                alerts.append(f"⚠️ 生成时间异常增加: 最近平均 {avg_recent_time:.2f}s vs 总体平均 {overall_avg_time:.2f}s")

        return alerts


# 全局监控实例
system_monitor = SystemMonitor()
model_monitor = ModelMonitor()


def get_system_monitor() -> SystemMonitor:
    """获取系统监控实例"""
    return system_monitor


def get_model_monitor() -> ModelMonitor:
    """获取模型监控实例"""
    return model_monitor
```

## 性能优化策略 - **ENHANCED**

### 1. 内存管理 - **IMPROVED**
- 使用适当的上下文窗口大小 (n_ctx)
- 合理设置批处理大小 (batch_size)
- 实现模型缓存和卸载机制
- 添加内存使用监控

### 2. 硬件加速 - **IMPROVED**
- 自动检测并启用 GPU 加速 (CUDA/Metal)
- 适当的 GPU 层设置 (n_gpu_layers)
- GPU利用率监控

### 3. 并发处理 - **NEW**
- 请求队列机制处理并发访问
- 线程安全的模型实例管理
- 性能基准和压力测试

## 部署指南 - **ENHANCED**

### 本地部署
1. 下载合适的 GGUF 模型文件
2. 更新配置文件中的模型路径
3. 设置后端为 "llama_cpp"
4. 启动应用，监控系统资源使用

### 环境变量配置 - **ENHANCED**
```bash
# 选择后端
LLAMA_BACKEND=llama_cpp

# 模型路径
LLAMA_MODEL_PATH=./models/qwen2.5-7b-instruct-q4_k_m.gguf

# 性能参数
LLAMA_CONTEXT_SIZE=4096
LLAMA_THREADS=8
LLAMA_BATCH_SIZE=512
LLAMA_GPU_LAYERS=-1  # 使用所有GPU层，设为0则使用CPU

# 生成参数
LLAMA_MAX_TOKENS=512
LLAMA_TEMPERATURE=0.7
LLAMA_TOP_P=0.9
LLAMA_TOP_K=40
LLAMA_REPEAT_PENALTY=1.1
LLAMA_GENERATION_TIMEOUT=300  # 5分钟超时
```

## 监控和告警

### 系统监控
- CPU、内存、磁盘使用率监控
- 网络IO监控
- 实时告警（高使用率时）

### 模型监控
- 生成时间监控
- 吞吐量监控
- 内存使用监控
- 性能异常检测

## 实施优先级 - **ADJUSTED**

1. **高优先级**: 阶段1-4（基础环境、客户端实现、配置、抽象层、错误处理）
2. **中优先级**: 阶段5-6（现有组件适配、并发处理）
3. **低优先级**: 阶段7-8（测试验证、监控告警）

## 风险缓解 - **ENHANCED**

1. **渐进式迁移**: 先在开发环境完整测试
2. **性能基准**: 在迁移前建立 Ollama 的性能基准数据
3. **监控机制**: 实施后添加详细的性能和错误监控
4. **降级策略**: 自动降级到 Ollama 后端
5. **配置验证**: 启动时验证配置参数有效性

## 预期收益

1. **性能提升**:
   - 减少网络调用延迟
   - 更直接的硬件访问
   - 优化的内存管理
   - 实时性能监控

2. **稳定性增强**:
   - 更强的错误处理
   - 详细的日志记录
   - 自动降级机制
   - 系统资源监控

3. **可维护性提升**:
   - 更好的测试覆盖
   - 并发处理能力
   - 详细的配置验证
   - 实时告警系统

## 预期实施时间

- **阶段1-4 (基础实现)**: 3-4天
- **阶段5-6 (适配和并发)**: 2-3天
- **阶段7-8 (测试和监控)**: 3-4天
- **整体测试和优化**: 2-3天
- **总计**: 10-14天 (比原计划稍长，但系统更健壮)

这个增强版计划包含了您建议的所有改进点，提供了更加健壮和可维护的llama.cpp集成方案。
