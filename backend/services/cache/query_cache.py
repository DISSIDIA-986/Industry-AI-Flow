"""
Query Cache

Thread-safe TTL cache for RAG query results to reduce redundant LLM calls.
Uses cachetools TTLCache with configurable size and expiration.

Created: 2026-02-09
Reference: research/summary-and-next-steps.md (implementation-plan-corrected.md)
"""

import logging
import threading  # Thread-safe cache access

from cachetools import TTLCache

from backend.config import settings

logger = logging.getLogger(__name__)


class QueryCache:
    """Thread-safe TTL cache for query results with configurable size and expiration."""

    def __init__(self):
        self.enabled = settings.query_cache_enabled
        self.cache = TTLCache(
            maxsize=settings.query_cache_maxsize,
            ttl=settings.query_cache_ttl_seconds,
        )
        self.lock = threading.RLock()  # Reentrant lock for thread safety
        logger.info(
            "QueryCache initialized: enabled=%s, maxsize=%d, ttl=%ds, thread_safe=True",
            self.enabled,
            settings.query_cache_maxsize,
            settings.query_cache_ttl_seconds,
        )

    def _key(self, tenant_id: str, question: str, top_k: int) -> str:
        """
        Generate a normalized cache key.

        Args:
            tenant_id: Tenant identifier
            question: User query string
            top_k: Number of results requested

        Returns:
            Normalized cache key string
        """
        # Normalize whitespace for consistent cache hits
        q = " ".join((question or "").strip().split())
        return f"{tenant_id}:{top_k}:{q}"

    def get(self, tenant_id: str, question: str, top_k: int):
        """
        Look up a cached query result (thread-safe).

        Args:
            tenant_id: Tenant identifier
            question: User query string
            top_k: Number of results requested

        Returns:
            Cached payload dict if found, otherwise None
        """
        if not self.enabled:
            return None

        with self.lock:  # Thread-safe read
            result = self.cache.get(self._key(tenant_id, question, top_k))

        if result:
            logger.debug("Cache hit for tenant=%s, question=%s", tenant_id, question[:50])

        return result

    def set(self, tenant_id: str, question: str, top_k: int, payload: dict):
        """
        Store a query result in cache (thread-safe).

        Args:
            tenant_id: Tenant identifier
            question: User query string
            top_k: Number of results requested
            payload: Result data to cache
        """
        if not self.enabled:
            return

        with self.lock:  # Thread-safe write
            self.cache[self._key(tenant_id, question, top_k)] = payload
            logger.debug("Cache set for tenant=%s, question=%s", tenant_id, question[:50])

    def clear(self):
        """Clear all cached entries (thread-safe)."""
        if not self.enabled:
            return

        with self.lock:  # Thread-safe clear
            self.cache.clear()
            logger.info("QueryCache cleared")

    def stats(self) -> dict:
        """
        Get cache statistics (thread-safe).

        Returns:
            Dictionary with cache status and metrics
        """
        with self.lock:  # Thread-safe stats read
            return {
                "enabled": self.enabled,
                "current_size": len(self.cache),
                "max_size": self.cache.maxsize,
                "ttl": self.cache.ttl,
                "thread_safe": True,
            }


# Global singleton instance
query_cache = QueryCache()
