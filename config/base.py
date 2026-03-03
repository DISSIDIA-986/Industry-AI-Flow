"""
Base configuration for Industry AI Flow.

Contains common configuration settings shared across all environments.
"""

import os
from pathlib import Path
from typing import Any, Dict


class BaseConfig:
    """Base configuration class with common settings."""

    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent
    BACKEND_ROOT = PROJECT_ROOT / "backend"
    DATA_ROOT = PROJECT_ROOT / "datasets"
    MODELS_ROOT = PROJECT_ROOT / "models"

    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/ai_workflow")
    DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))

    # Vector database settings
    VECTOR_DB_URL = os.getenv("VECTOR_DB_URL", DATABASE_URL)
    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))

    # LLM settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5:9b")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    # Redis settings (for caching and session management)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))

    # API settings
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_WORKERS = int(os.getenv("API_WORKERS", "1"))

    # Logging settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv(
        "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Security settings
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))

    # File upload settings
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(PROJECT_ROOT / "uploads"))

    # OCR settings
    OCR_PROVIDER = os.getenv("OCR_PROVIDER", "paddleocr")
    OCR_LANG = os.getenv("OCR_LANG", "ch")

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        """Get all configuration settings as a dictionary."""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and not callable(getattr(cls, key))
        }
