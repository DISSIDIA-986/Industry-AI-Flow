"""
Testing environment configuration.

Settings optimized for automated testing and CI/CD pipelines.
"""

from .base import BaseConfig


class TestingConfig(BaseConfig):
    """Testing configuration with isolated resources."""

    # Debug settings for testing
    DEBUG = False

    # Database settings for testing
    DATABASE_URL = "postgresql://localhost/ai_workflow_test"
    DATABASE_POOL_SIZE = 1
    DATABASE_MAX_OVERFLOW = 0

    # Logging for testing
    LOG_LEVEL = "WARNING"  # Reduce log noise in tests

    # API settings for testing
    API_HOST = "127.0.0.1"
    API_PORT = 8001  # Different port to avoid conflicts
    API_WORKERS = 1

    # LLM settings for testing (mock or fast models)
    LLM_PROVIDER = "mock"  # Use mock LLM for testing
    LLM_MODEL = "test-model"
    LLM_TEMPERATURE = 0.0  # Deterministic responses
    LLM_MAX_TOKENS = 512

    # Cache settings for testing
    REDIS_CACHE_TTL = 60  # Short cache for testing
    REDIS_URL = "redis://localhost:6379/1"  # Different database

    # File upload settings for testing
    MAX_UPLOAD_SIZE = 1048576  # 1MB for testing
    UPLOAD_DIR = str(BaseConfig.PROJECT_ROOT / "uploads" / "test")

    # OCR settings for testing
    OCR_PROVIDER = "mock"  # Use mock OCR for testing

    # Testing-specific settings
    TESTING = True
    TEST_DATA_DIR = str(BaseConfig.PROJECT_ROOT / "tests" / "fixtures")

    # Disable unnecessary features for testing
    ENABLE_CORS = False
    RATE_LIMIT_ENABLED = False

    # Mock external services
    MOCK_EXTERNAL_APIS = True
    MOCK_LLM_RESPONSES = True
    MOCK_OCR_RESPONSES = True

    # Database testing settings
    TEST_DATABASE_CREATE = True
    TEST_DATABASE_DROP = True

    # Performance testing settings
    ENABLE_PROFILING = False
    ENABLE_REQUEST_LOGGING = False
