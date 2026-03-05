"""
Database Connection Pool

Provides async connection pool for Prompt API and Workflow database operations.
Used by prompt_routes and other database-dependent modules.

Created: 2026-02-09
Reference: research/architecture/rag-workflow-implementation-details.md
"""

import asyncpg
import logging
from backend.config import settings

logger = logging.getLogger(__name__)

_db_pool = None


async def get_database_pool() -> asyncpg.Pool:
    """
    Get or create the shared async database connection pool (lazy singleton).

    Returns:
        asyncpg.Pool: Shared connection pool instance

    Raises:
        Exception: If pool creation fails due to connection or configuration errors
    """
    global _db_pool

    if _db_pool is None:
        logger.info(f"Creating database pool: {settings.postgres_host}:{settings.postgres_port}")
        _db_pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("Database pool created successfully")

    return _db_pool


async def close_database_pool():
    """Close the shared database connection pool and release all connections."""
    global _db_pool

    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("Database pool closed")
