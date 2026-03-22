"""
Development environment configuration.

Settings optimized for local development and debugging.
"""

from .base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """Development configuration with debugging enabled."""

    # Debug settings
    DEBUG = True
    RELOAD = True

    # Database settings for development
    DATABASE_URL = "postgresql://localhost/ai_workflow_dev"
    DATABASE_POOL_SIZE = 5
    DATABASE_MAX_OVERFLOW = 10

    # Logging for development
    LOG_LEVEL = "DEBUG"

    # API settings for development
    API_HOST = "127.0.0.1"
    API_PORT = 8000
    API_WORKERS = 1  # Single worker for debugging

    # LLM settings for development (faster responses)
    LLM_TEMPERATURE = 0.8
    LLM_MAX_TOKENS = 1024

    # Cache settings for development
    REDIS_CACHE_TTL = 1800  # 30 minutes

    # File upload settings for development
    MAX_UPLOAD_SIZE = 52428800  # 50MB for testing
    UPLOAD_DIR = str(BaseConfig.PROJECT_ROOT / "uploads" / "dev")

    # OCR settings for development
    OCR_PROVIDER = "paddleocr"
    OCR_LANG = "ch"  # Chinese text recognition

    # Development-specific settings
    ENABLE_CORS = True
    CORS_ORIGINS = ["http://localhost:3123", "http://127.0.0.1:3123"]

    # Rate limiting (relaxed for development)
    RATE_LIMIT_ENABLED = False
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW = 60

    # Monitoring and profiling
    ENABLE_PROFILING = True
    ENABLE_REQUEST_LOGGING = True
