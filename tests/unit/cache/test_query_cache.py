"""
EN

ENQueryCacheEN
"""

import pytest
import threading
import time
from unittest.mock import patch
from backend.services.cache.query_cache import QueryCache


class TestQueryCache:
    """QueryCacheEN"""

    @pytest.fixture
    def cache(self):
        """EN"""
        return QueryCache()

    def test_cache_set_and_get(self, cache):
        """EN"""
        # EN
        cache.set("tenant1", "test query", 5, {"result": "cached"})
        
        # EN
        result = cache.get("tenant1", "test query", 5)
        
        assert result == {"result": "cached"}
        assert cache.get("tenant1", "test query", 10) is None  # top_kEN

    def test_cache_miss(self, cache):
        """EN"""
        result = cache.get("tenant1", "nonexistent", 5)
        assert result is None

    def test_cache_tenant_isolation(self, cache):
        """EN"""
        cache.set("tenant1", "query", 5, {"result": "tenant1"})
        cache.set("tenant2", "query", 5, {"result": "tenant2"})
        
        result1 = cache.get("tenant1", "query", 5)
        result2 = cache.get("tenant2", "query", 5)
        
        assert result1["result"] == "tenant1"
        assert result2["result"] == "tenant2"

    def test_cache_ttl_expiration(self, cache):
        """ENTTLEN"""
        # ENTTLEN1EN
        with patch('backend.config.settings.query_cache_ttl_seconds', 1):
            cache = QueryCache()
            cache.set("tenant1", "query", 5, {"result": "cached"})
            
            # EN
            result = cache.get("tenant1", "query", 5)
            assert result is not None
            
            # EN2EN
            time.sleep(2)
            result = cache.get("tenant1", "query", 5)
            assert result is None

    def test_cache_disabled(self, cache):
        """EN"""
        with patch('backend.config.settings.query_cache_enabled', False):
            cache = QueryCache()
            cache.set("tenant1", "query", 5, {"result": "cached"})
            
            result = cache.get("tenant1", "query", 5)
            assert result is None

    def test_cache_clear(self, cache):
        """EN"""
        cache.set("tenant1", "query1", 5, {"result": "data1"})
        cache.set("tenant2", "query2", 5, {"result": "data2"})
        
        # EN
        assert cache.get("tenant1", "query1", 5) is not None
        assert cache.get("tenant2", "query2", 5) is not None
        
        # EN
        cache.clear()
        
        # EN
        assert cache.get("tenant1", "query1", 5) is None
        assert cache.get("tenant2", "query2", 5) is None

    def test_cache_stats(self, cache):
        """EN"""
        stats = cache.stats()
        
        assert "enabled" in stats
        assert "current_size" in stats
        assert "max_size" in stats
        assert "ttl" in stats
        assert "thread_safe" in stats
        assert stats["thread_safe"] is True

    def test_concurrent_cache_access(self):
        """EN"""
        cache = QueryCache()
        errors = []
        
        def concurrent_operation(i):
            try:
                cache.set(f"tenant{i}", f"query{i}", 5, {"data": i})
                result = cache.get(f"tenant{i}", f"query{i}", 5)
                assert result["data"] == i
            except Exception as e:
                errors.append(e)
        
        # EN100EN
        threads = [
            threading.Thread(target=concurrent_operation, args=(i,))
            for i in range(100)
        ]
        
        # EN
        for t in threads:
            t.start()
        
        # EN
        for t in threads:
            t.join()
        
        # EN
        assert len(errors) == 0, f"EN: {errors}"
        
        # EN
        for i in range(100):
            result = cache.get(f"tenant{i}", f"query{i}", 5)
            assert result is not None
            assert result["data"] == i

    def test_cache_key_generation(self, cache):
        """EN"""
        test_cases = [
            ("tenant1", "query1", 5),
            ("tenant2", "query with spaces", 10),
            ("tenant3", "", 3),
            ("", "query4", 5),
            ("tenant5", "query\nwith\nnewlines", 7),
        ]
        
        for tenant_id, question, top_k in test_cases:
            key = cache._key(tenant_id, question, top_k)
            assert isinstance(key, str)
            assert f"{tenant_id}:{top_k}:" in key
            
            # EN
            if "  " in question:
                assert "  " not in key

    def test_cache_with_special_characters(self, cache):
        """EN"""
        special_queries = [
            "query with 'single quotes'",
            'query with "double quotes"',
            "query with `backticks`",
            "query with @symbols",
            "query with #hashtags",
            "query with $dollar",
            "query with %percent",
            "query with &ampersand",
            "query with *asterisk",
            "query with (parentheses)",
            "query with [brackets]",
            "query with {braces}",
        ]
        
        for query in special_queries:
            cache.set("tenant1", query, 5, {"result": "cached"})
            result = cache.get("tenant1", query, 5)
            assert result is not None
            assert result["result"] == "cached"

    @pytest.mark.parametrize("tenant_id,question,top_k", [
        ("tenant1", "query1", 5),
        ("tenant2", "query2", 10),
        ("tenant3", "", 3),
        (None, "query4", 5),
    ])
    def test_cache_parametrized(self, cache, tenant_id, question, top_k):
        """EN"""
        cache.set(tenant_id, question, top_k, {"test": "data"})
        result = cache.get(tenant_id, question, top_k)
        assert result is not None