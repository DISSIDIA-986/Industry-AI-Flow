"""
数据库服务模块

提供数据库连接池和相关服务。

创建时间: 2026-02-09
"""

from backend.services.database.pool import get_database_pool, close_database_pool

__all__ = ["get_database_pool", "close_database_pool"]
