"""
Production environment configuration.

Settings optimized for production deployment with security and performance.
"""

from .base import BaseConfig


class ProductionConfig(BaseConfig):
    """Production configuration with security and performance optimizations."""

    # Debug settings
    DEBUG = False
    RELOAD = False

    # Database settings for production
    DATABASE_URL = os.getenv("DATABASE_URL")  # Must be set in production
    DATABASE_POOL_SIZE = 20
    DATABASE_MAX_OVERFLOW = 30
    DATABASE_POOL_TIMEOUT = 30
    DATABASE_POOL_RECYCLE = 3600

    # Logging for production
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # API settings for production
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    API_WORKERS = int(os.getenv("API_WORKERS", "4"))  # Multiple workers

    # LLM settings for production
    LLM_TEMPERATURE = 0.3  # More conservative for production
    LLM_MAX_TOKENS = 2048

    # Cache settings for production
    REDIS_CACHE_TTL = 7200  # 2 hours
    REDIS_URL = os.getenv("REDIS_URL")  # Must be set in production
    REDIS_CONNECTION_POOL_SIZE = 10

    # File upload settings for production
    MAX_UPLOAD_SIZE = 52428800  # 50MB
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")

    # OCR settings for production
    OCR_PROVIDER = "paddleocr"
    OCR_LANG = os.getenv("OCR_LANG", "ch")

    # Security settings
    SECRET_KEY = os.getenv("SECRET_KEY")  # Must be set in production
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = 30

    # CORS settings for production
    ENABLE_CORS = True
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")

    # Rate limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW = 60

    # SSL and HTTPS
    FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() == "true"
    SSL_CERT_PATH = os.getenv("SSL_CERT_PATH")
    SSL_KEY_PATH = os.getenv("SSL_KEY_PATH")

    # Monitoring and observability
    ENABLE_METRICS = True
    ENABLE_REQUEST_LOGGING = True
    ENABLE_PROFILING = False

    # Performance settings
    ENABLE_CACHING = True
    CACHE_BACKEND = "redis"
    COMPRESSION_ENABLED = True

    # Health check settings
    HEALTH_CHECK_ENDPOINT = "/health"
    METRICS_ENDPOINT = "/metrics"

    # Backup and recovery
    AUTO_BACKUP_ENABLED = os.getenv("AUTO_BACKUP_ENABLED", "false").lower() == "true"
    BACKUP_INTERVAL = int(os.getenv("BACKUP_INTERVAL", "86400"))  # 24 hours

    # Resource limits
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "1000"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))  # 30 seconds

    # External service integration
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
