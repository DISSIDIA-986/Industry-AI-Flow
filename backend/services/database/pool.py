"""
数据库连接池配置

提供异步数据库连接池工厂函数，支持Prompt API和Workflow系统。
修复prompt_routes依赖断裂问题。

创建时间: 2026-02-09
参考: research/rag-workflow-implementation-details.md
"""

import asyncpg
import logging
from backend.config import settings

logger = logging.getLogger(__name__)

_db_pool = None


async def get_database_pool() -> asyncpg.Pool:
    """
    获取数据库连接池（单例模式）

    Returns:
        asyncpg.Pool: 数据库连接池

    Raises:
        Exception: 连接池创建失败
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
    """关闭数据库连接池"""
    global _db_pool

    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("Database pool closed")
