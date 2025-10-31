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

    # 向量化
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "384"))

    # 文档处理
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "300"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # RAG
    top_k: int = int(os.getenv("TOP_K", "5"))

    @property
    def database_url(self) -> str:
        # 本地PostgreSQL: postgresql://localhost:5432/ai_workflow
        # Docker PostgreSQL: postgresql://user:password@localhost:5432/ai_workflow
        if self.postgres_user and self.postgres_password:
            return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        else:
            return f"postgresql://{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = Settings()
