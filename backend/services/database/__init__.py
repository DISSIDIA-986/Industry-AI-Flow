"""
Database Module

Provides async database connection pool management.

Created: 2026-02-09
"""

from backend.services.database.pool import get_database_pool, close_database_pool

__all__ = ["get_database_pool", "close_database_pool"]
