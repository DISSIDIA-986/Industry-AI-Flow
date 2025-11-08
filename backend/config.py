import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库（支持本地homebrew PostgreSQL）
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "ai_workflow")
    postgres_user: str = os.getenv("POSTGRES_USER", "")  # 本地PostgreSQL留空使用当前用户
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")  # 本地PostgreSQL无密码

    # Ollama
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    # 智谱AI（支持Anthropic兼容接口）
    zhipu_api_key: str = os.getenv("ZHIPU_API_KEY", "")
    zhipu_base_url: str = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/anthropic")
    zhipu_model: str = os.getenv("ZHIPU_MODEL", "glm-4-plus")
    api_timeout_ms: int = int(os.getenv("API_TIMEOUT_MS", "3000000"))

    # LLM提供商选择
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")  # ollama | zhipu

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

    # 代码执行配置
    code_execution_timeout: int = int(os.getenv("CODE_EXECUTION_TIMEOUT", "300"))  # 执行超时（秒）
    code_execution_memory_limit: str = os.getenv("CODE_EXECUTION_MEMORY_LIMIT", "1G")  # 内存限制
    code_execution_cpu_limit: str = os.getenv("CODE_EXECUTION_CPU_LIMIT", "2")  # CPU限制
    enable_docker_sandbox: bool = os.getenv("ENABLE_DOCKER_SANDBOX", "true").lower() == "true"  # 是否启用Docker沙箱
    docker_image_name: str = os.getenv("DOCKER_IMAGE_NAME", "luncheon/code-analysis:v1.0")  # Docker镜像名
    temp_data_dir: str = os.getenv("TEMP_DATA_DIR", "/tmp/luncheon_data")  # 临时数据目录

    # 可迭代执行配置 (LangChain 1.0 增强)
    enable_iterative_execution: bool = os.getenv("ENABLE_ITERATIVE_EXECUTION", "true").lower() == "true"
    max_code_fix_attempts: int = int(os.getenv("MAX_CODE_FIX_ATTEMPTS", "5"))  # 最大修复尝试次数
    auto_code_fix_enabled: bool = os.getenv("AUTO_CODE_FIX_ENABLED", "true").lower() == "true"
    data_transfer_method: str = os.getenv("DATA_TRANSFER_METHOD", "auto")  # auto, file_mapping, database
    db_connection_timeout: int = int(os.getenv("DB_CONNECTION_TIMEOUT", "30"))  # 数据库连接超时
    enable_error_learning: bool = os.getenv("ENABLE_ERROR_LEARNING", "true").lower() == "true"  # 错误模式学习

    @property
    def database_url(self) -> str:
        # 本地PostgreSQL: postgresql://localhost:5432/ai_workflow
        # Docker PostgreSQL: postgresql://user:password@localhost:5432/ai_workflow
        if self.postgres_user and self.postgres_password:
            return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        else:
            return f"postgresql://{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = Settings()