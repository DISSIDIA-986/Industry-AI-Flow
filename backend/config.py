import os
from pathlib import Path
from typing import Optional, Set

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库（支持本地homebrew PostgreSQL）
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "ai_workflow")
    postgres_user: str = os.getenv("POSTGRES_USER", "")  # 本地PostgreSQL留空使用当前用户
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")  # 本地PostgreSQL无密码

    # 数据库连接池配置（P0修复：支持Prompt API）
    db_pool_min_size: int = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
    db_pool_max_size: int = int(os.getenv("DB_POOL_MAX_SIZE", "10"))
    db_command_timeout: int = int(os.getenv("DB_COMMAND_TIMEOUT", "30"))

    # Ollama (备用后端)
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    # llama.cpp (主要后端)
    llama_model_path: str = os.getenv(
        "LLAMA_MODEL_PATH", "models/qwen2.5-7b-instruct.gguf"
    )
    llama_context_size: int = int(os.getenv("LLAMA_CONTEXT_SIZE", "4096"))
    llama_threads: int = int(os.getenv("LLAMA_THREADS", str(os.cpu_count() or 8)))
    llama_batch_size: int = int(os.getenv("LLAMA_BATCH_SIZE", "512"))
    llama_gpu_layers: int = int(os.getenv("LLAMA_GPU_LAYERS", "-1"))  # -1 = 全部使用GPU

    # LLM后端选择
    llm_backend: str = os.getenv(
        "LLM_BACKEND", "llama_cpp"
    )  # llama_cpp | ollama | zhipu

    # 智谱AI（支持Anthropic兼容接口）
    zhipu_api_key: str = os.getenv("ZHIPU_API_KEY", "")
    zhipu_base_url: str = os.getenv(
        "ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/anthropic"
    )
    zhipu_model: str = os.getenv("ZHIPU_MODEL", "glm-4-plus")
    api_timeout_ms: int = int(os.getenv("API_TIMEOUT_MS", "3000000"))

    # LLM提供商选择（保持兼容）
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")  # ollama | zhipu

    # Hybrid dispatch control-plane (Phase 1 corrected plan)
    hybrid_mode: str = os.getenv(
        "HYBRID_MODE", "local_only"
    )  # local_only | hybrid_auto | cloud_only
    local_primary_backend: str = os.getenv("LOCAL_PRIMARY_BACKEND", "llama_cpp")
    cloud_provider: str = os.getenv("CLOUD_PROVIDER", "zhipu")
    fallback_on_error: bool = os.getenv("FALLBACK_ON_ERROR", "true").lower() == "true"
    local_confidence_threshold: float = float(
        os.getenv("LOCAL_CONFIDENCE_THRESHOLD", "0.75")
    )
    max_cloud_calls_per_minute: int = int(
        os.getenv("MAX_CLOUD_CALLS_PER_MINUTE", "120")
    )

    # 向量化 (Phase 2: 升级到 nomic-embed-text-v1.5)
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1.5"
    )
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "768"))

    # 文档处理
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "300"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # RAG
    top_k: int = int(os.getenv("TOP_K", "5"))

    # LLM Parameters
    default_temperature: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
    default_max_tokens: int = int(os.getenv("DEFAULT_MAX_TOKENS", "2000"))
    default_top_p: float = float(os.getenv("DEFAULT_TOP_P", "0.9"))

    # Feedback System
    enable_feedback_system: bool = (
        os.getenv("ENABLE_FEEDBACK_SYSTEM", "true").lower() == "true"
    )
    feedback_weight_threshold: float = float(
        os.getenv("FEEDBACK_WEIGHT_THRESHOLD", "0.5")
    )
    min_feedback_for_optimization: int = int(
        os.getenv("MIN_FEEDBACK_FOR_OPTIMIZATION", "5")
    )

    # Document Management
    enable_document_update: bool = (
        os.getenv("ENABLE_DOCUMENT_UPDATE", "true").lower() == "true"
    )
    enable_document_deletion: bool = (
        os.getenv("ENABLE_DOCUMENT_DELETION", "true").lower() == "true"
    )

    # OCR (Phase 2: PaddleOCR配置)
    ocr_lang: str = os.getenv("OCR_LANG", "en")  # 'en' 英文, 'ch' 中文, 'en+ch' 混合

    # 代码执行配置
    code_execution_timeout: int = int(
        os.getenv("CODE_EXECUTION_TIMEOUT", "300")
    )  # 执行超时（秒）
    code_execution_memory_limit: str = os.getenv(
        "CODE_EXECUTION_MEMORY_LIMIT", "1G"
    )  # 内存限制
    code_execution_cpu_limit: str = os.getenv("CODE_EXECUTION_CPU_LIMIT", "2")  # CPU限制
    enable_docker_sandbox: bool = (
        os.getenv("ENABLE_DOCKER_SANDBOX", "true").lower() == "true"
    )  # 是否启用Docker沙箱
    docker_image_name: str = os.getenv(
        "DOCKER_IMAGE_NAME", "luncheon/code-analysis:v1.0"
    )  # Docker镜像名
    temp_data_dir: str = os.getenv("TEMP_DATA_DIR", "/tmp/luncheon_data")  # 临时数据目录

    # 可迭代执行配置 (LangChain 1.0 增强)
    enable_iterative_execution: bool = (
        os.getenv("ENABLE_ITERATIVE_EXECUTION", "true").lower() == "true"
    )
    max_code_fix_attempts: int = int(
        os.getenv("MAX_CODE_FIX_ATTEMPTS", "5")
    )  # 最大修复尝试次数
    auto_code_fix_enabled: bool = (
        os.getenv("AUTO_CODE_FIX_ENABLED", "true").lower() == "true"
    )
    data_transfer_method: str = os.getenv(
        "DATA_TRANSFER_METHOD", "auto"
    )  # auto, file_mapping, database
    db_connection_timeout: int = int(
        os.getenv("DB_CONNECTION_TIMEOUT", "30")
    )  # 数据库连接超时
    enable_error_learning: bool = (
        os.getenv("ENABLE_ERROR_LEARNING", "true").lower() == "true"
    )  # 错误模式学习

    # API & Security
    require_api_key: bool = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"
    api_keys_raw: str = os.getenv("API_KEYS", "")
    api_key_header: str = os.getenv("API_KEY_HEADER", "X-API-Key")
    tenant_header: str = os.getenv("TENANT_HEADER", "X-Tenant-ID")
    multi_tenant_mode: bool = os.getenv("MULTI_TENANT_MODE", "true").lower() == "true"
    default_tenant_id: str = os.getenv("DEFAULT_TENANT_ID", "public")
    allow_anonymous_tenants: bool = (
        os.getenv("ALLOW_ANONYMOUS_TENANTS", "false").lower() == "true"
    )
    api_rate_limit_per_minute: int = int(os.getenv("API_RATE_LIMIT_PER_MINUTE", "120"))
    api_rate_limit_burst: int = int(os.getenv("API_RATE_LIMIT_BURST", "20"))
    audit_log_path: str = os.getenv("AUDIT_LOG_PATH", str(Path("logs") / "audit.log"))
    max_upload_size_bytes: int = int(
        os.getenv("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024))
    )
    allowed_upload_extensions: str = os.getenv(
        "ALLOWED_UPLOAD_EXTENSIONS",
        ".pdf,.doc,.docx,.ppt,.pptx,.txt,.md,.csv,.json,.xlsx,.xls",
    )
    secret_encryption_key: str = os.getenv("SECRET_ENCRYPTION_KEY", "")
    api_keys_encrypted: str = os.getenv("API_KEYS_ENCRYPTED", "")
    api_key_hashes_raw: str = os.getenv("API_KEY_HASHES", "")
    secret_hash_salt: str = os.getenv("SECRET_HASH_SALT", "")
    secret_hash_iterations: int = int(os.getenv("SECRET_HASH_ITERATIONS", "120000"))
    memory_guard_limit_mb: int = int(os.getenv("MEMORY_GUARD_LIMIT_MB", "4096"))
    memory_guard_soft_limit_mb: int = int(
        os.getenv("MEMORY_GUARD_SOFT_LIMIT_MB", "3072")
    )
    require_user_auth: bool = os.getenv("REQUIRE_USER_AUTH", "false").lower() == "true"
    auth_jwt_secret: str = os.getenv("AUTH_JWT_SECRET", "")
    auth_jwt_algorithm: str = os.getenv("AUTH_JWT_ALGORITHM", "HS256")
    auth_jwt_issuer: str = os.getenv("AUTH_JWT_ISSUER", "")
    auth_jwt_audience: str = os.getenv("AUTH_JWT_AUDIENCE", "")
    default_user_roles: str = os.getenv("DEFAULT_USER_ROLES", "user")
    log_format_json: bool = os.getenv("LOG_FORMAT_JSON", "true").lower() == "true"
    enable_metrics: bool = (
        os.getenv("ENABLE_PROMETHEUS_METRICS", "true").lower() == "true"
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv(
        "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    enable_conversation_memory: bool = (
        os.getenv("ENABLE_CONVERSATION_MEMORY", "true").lower() == "true"
    )
    memory_short_term_window: int = int(os.getenv("MEMORY_SHORT_TERM_WINDOW", "6"))
    memory_summary_trigger_messages: int = int(
        os.getenv("MEMORY_SUMMARY_TRIGGER_MESSAGES", "4")
    )
    memory_summary_backend: str = os.getenv("MEMORY_SUMMARY_BACKEND", "")
    memory_summary_max_tokens: int = int(os.getenv("MEMORY_SUMMARY_MAX_TOKENS", "512"))
    memory_long_term_top_k: int = int(os.getenv("MEMORY_LONG_TERM_TOP_K", "5"))
    memory_long_term_min_relevance: float = float(
        os.getenv("MEMORY_LONG_TERM_MIN_RELEVANCE", "0.45")
    )
    query_cache_enabled: bool = (
        os.getenv("QUERY_CACHE_ENABLED", "true").lower() == "true"
    )
    query_cache_ttl_seconds: int = int(os.getenv("QUERY_CACHE_TTL_SECONDS", "120"))
    query_cache_maxsize: int = int(os.getenv("QUERY_CACHE_MAXSIZE", "256"))
    enable_safety_guard: bool = (
        os.getenv("ENABLE_SAFETY_GUARD", "true").lower() == "true"
    )
    safety_confidence_threshold: float = float(
        os.getenv("SAFETY_CONFIDENCE_THRESHOLD", "0.8")
    )
    db_query_slow_threshold_ms: int = int(
        os.getenv("DB_QUERY_SLOW_THRESHOLD_MS", "750")
    )

    @property
    def database_url(self) -> str:
        # 本地PostgreSQL: postgresql://localhost:5432/ai_workflow
        # Docker PostgreSQL: postgresql://user:password@localhost:5432/ai_workflow
        if self.postgres_user and self.postgres_password:
            return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        else:
            return f"postgresql://{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def api_key_set(self) -> Set[str]:
        """Return allowed API keys as a cached set."""
        if not hasattr(self, "_api_key_cache"):
            tokens = [
                token.strip() for token in self.api_keys_raw.split(",") if token.strip()
            ]
            if self.api_keys_encrypted:
                from backend.security.secret_manager import SecretManager

                manager = self.secret_manager
                tokens.extend(manager.decrypt_list(self.api_keys_encrypted))
            self._api_key_cache = set(tokens)
        return self._api_key_cache

    @property
    def api_key_hashes(self) -> Set[str]:
        if not hasattr(self, "_api_key_hash_cache"):
            hashes = {
                token.strip()
                for token in self.api_key_hashes_raw.split(",")
                if token.strip()
            }
            self._api_key_hash_cache = hashes
        return self._api_key_hash_cache

    @property
    def audit_log_file(self) -> Path:
        """Return audit log path, creating directory if needed."""
        path = Path(self.audit_log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def upload_extension_whitelist(self) -> Set[str]:
        """Allowed upload extensions as a cached set."""
        if not hasattr(self, "_upload_ext_cache"):
            tokens = []
            for raw in self.allowed_upload_extensions.split(","):
                token = raw.strip().lower()
                if not token:
                    continue
                if not token.startswith("."):
                    token = f".{token}"
                tokens.append(token)
            self._upload_ext_cache = set(tokens)
        return self._upload_ext_cache

    @property
    def default_roles_list(self):
        if not hasattr(self, "_default_roles"):
            roles = [
                role.strip()
                for role in self.default_user_roles.split(",")
                if role.strip()
            ]
            self._default_roles = roles or ["user"]
        return self._default_roles

    @property
    def secret_manager(self):
        if not hasattr(self, "_secret_manager"):
            from backend.security.secret_manager import SecretManager

            self._secret_manager = SecretManager(
                encryption_key=self.secret_encryption_key or None,
                hash_salt=self.secret_hash_salt or None,
                hash_iterations=self.secret_hash_iterations,
            )
        return self._secret_manager

    def is_api_key_allowed(self, api_key: str) -> bool:
        """Check plaintext and hashed API keys in constant time."""
        if not api_key:
            return False
        if api_key in self.api_key_set:
            return True
        if self.api_key_hashes:
            return self.secret_manager.verify_against_hashes(
                api_key, self.api_key_hashes
            )
        return False

    @staticmethod
    def _normalize_token(value: Optional[str]) -> str:
        return (value or "").strip().lower()

    @property
    def resolved_hybrid_mode(self) -> str:
        mode = self._normalize_token(self.hybrid_mode)
        if mode in {"local_only", "hybrid_auto", "cloud_only"}:
            return mode
        return "local_only"

    @property
    def resolved_local_backend(self) -> str:
        # Prefer dedicated local setting, then legacy backend/provider knobs.
        candidates = (
            self.local_primary_backend,
            self.llm_backend,
            self.llm_provider,
        )
        for candidate in candidates:
            value = self._normalize_token(candidate)
            if value in {"llama_cpp", "ollama"}:
                return value
        return "llama_cpp"

    @property
    def resolved_cloud_provider(self) -> str:
        # Prefer dedicated cloud setting, then legacy provider/backend knobs.
        candidates = (
            self.cloud_provider,
            self.llm_provider,
            self.llm_backend,
        )
        for candidate in candidates:
            value = self._normalize_token(candidate)
            if value in {"zhipu"}:
                return value
        return "zhipu"


settings = Settings()
