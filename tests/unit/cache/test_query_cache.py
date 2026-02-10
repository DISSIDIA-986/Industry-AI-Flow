"""
查询缓存单元测试

测试QueryCache的线程安全性和功能正确性
"""

import pytest
import threading
import time
from unittest.mock import patch
from backend.services.cache.query_cache import QueryCache


class TestQueryCache:
    """QueryCache单元测试类"""

    @pytest.fixture
    def cache(self):
        """创建缓存实例"""
        return QueryCache()

    def test_cache_set_and_get(self, cache):
        """测试缓存设置和获取"""
        # 设置缓存
        cache.set("tenant1", "test query", 5, {"result": "cached"})
        
        # 获取缓存
        result = cache.get("tenant1", "test query", 5)
        
        assert result == {"result": "cached"}
        assert cache.get("tenant1", "test query", 10) is None  # top_k不同

    def test_cache_miss(self, cache):
        """测试缓存未命中"""
        result = cache.get("tenant1", "nonexistent", 5)
        assert result is None

    def test_cache_tenant_isolation(self, cache):
        """测试租户隔离"""
        cache.set("tenant1", "query", 5, {"result": "tenant1"})
        cache.set("tenant2", "query", 5, {"result": "tenant2"})
        
        result1 = cache.get("tenant1", "query", 5)
        result2 = cache.get("tenant2", "query", 5)
        
        assert result1["result"] == "tenant1"
        assert result2["result"] == "tenant2"

    def test_cache_ttl_expiration(self, cache):
        """测试TTL过期"""
        # 模拟TTL为1秒
        with patch('backend.config.settings.query_cache_ttl_seconds', 1):
            cache = QueryCache()
            cache.set("tenant1", "query", 5, {"result": "cached"})
            
            # 立即获取应该命中
            result = cache.get("tenant1", "query", 5)
            assert result is not None
            
            # 等待2秒后应该过期
            time.sleep(2)
            result = cache.get("tenant1", "query", 5)
            assert result is None

    def test_cache_disabled(self, cache):
        """测试缓存禁用"""
        with patch('backend.config.settings.query_cache_enabled', False):
            cache = QueryCache()
            cache.set("tenant1", "query", 5, {"result": "cached"})
            
            result = cache.get("tenant1", "query", 5)
            assert result is None

    def test_cache_clear(self, cache):
        """测试清空缓存"""
        cache.set("tenant1", "query1", 5, {"result": "data1"})
        cache.set("tenant2", "query2", 5, {"result": "data2"})
        
        # 清空前应该有数据
        assert cache.get("tenant1", "query1", 5) is not None
        assert cache.get("tenant2", "query2", 5) is not None
        
        # 清空缓存
        cache.clear()
        
        # 清空后应该没有数据
        assert cache.get("tenant1", "query1", 5) is None
        assert cache.get("tenant2", "query2", 5) is None

    def test_cache_stats(self, cache):
        """测试缓存统计"""
        stats = cache.stats()
        
        assert "enabled" in stats
        assert "current_size" in stats
        assert "max_size" in stats
        assert "ttl" in stats
        assert "thread_safe" in stats
        assert stats["thread_safe"] is True

    def test_concurrent_cache_access(self):
        """测试并发缓存访问"""
        cache = QueryCache()
        errors = []
        
        def concurrent_operation(i):
            try:
                cache.set(f"tenant{i}", f"query{i}", 5, {"data": i})
                result = cache.get(f"tenant{i}", f"query{i}", 5)
                assert result["data"] == i
            except Exception as e:
                errors.append(e)
        
        # 创建100个线程并发操作
        threads = [
            threading.Thread(target=concurrent_operation, args=(i,))
            for i in range(100)
        ]
        
        # 启动所有线程
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证没有错误
        assert len(errors) == 0, f"并发访问错误: {errors}"
        
        # 验证缓存一致性
        for i in range(100):
            result = cache.get(f"tenant{i}", f"query{i}", 5)
            assert result is not None
            assert result["data"] == i

    def test_cache_key_generation(self, cache):
        """测试缓存键生成"""
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
            
            # 验证空格被标准化
            if "  " in question:
                assert "  " not in key

    def test_cache_with_special_characters(self, cache):
        """测试特殊字符处理"""
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
        """参数化测试不同输入"""
        cache.set(tenant_id, question, top_k, {"test": "data"})
        result = cache.get(tenant_id, question, top_k)
        assert result is not None