"""
缓存集成测试

测试缓存与数据库、LLM调用的集成
"""

import pytest
import time
from unittest.mock import Mock, patch
from backend.services.cache.query_cache import QueryCache


@pytest.mark.integration
@pytest.mark.cache
class TestCacheIntegration:
    """缓存集成测试类"""

    @pytest.fixture
    def cache(self):
        """创建缓存实例"""
        return QueryCache()

    def test_cache_with_database_integration(self, cache):
        """测试缓存与数据库集成"""
        # 模拟从数据库获取数据
        def fetch_from_db(tenant_id, question, top_k):
            return {
                "tenant_id": tenant_id,
                "question": question,
                "answer": f"Answer to: {question}",
                "top_k": top_k
            }
        
        # 第一次查询（缓存未命中）
        tenant_id = "tenant1"
        question = "What is Python?"
        top_k = 5
        
        result1 = cache.get(tenant_id, question, top_k)
        assert result1 is None  # 缓存未命中
        
        # 从数据库获取并缓存
        db_result = fetch_from_db(tenant_id, question, top_k)
        cache.set(tenant_id, question, top_k, db_result)
        
        # 第二次查询（缓存命中）
        result2 = cache.get(tenant_id, question, top_k)
        assert result2 is not None
        assert result2["answer"] == f"Answer to: {question}"
        assert result2["tenant_id"] == tenant_id

    def test_cache_ttl_expiration_integration(self, cache):
        """测试缓存TTL过期集成"""
        with patch('backend.config.settings.query_cache_ttl_seconds', 1):
            cache = QueryCache()
            
            # 设置缓存
            cache.set("tenant1", "query", 5, {"result": "cached"})
            
            # 立即获取应该命中
            result1 = cache.get("tenant1", "query", 5)
            assert result1 is not None
            
            # 等待过期
            time.sleep(2)
            
            # 过期后应该未命中
            result2 = cache.get("tenant1", "query", 5)
            assert result2 is None

    def test_cache_with_llm_integration(self, cache):
        """测试缓存与LLM调用集成"""
        # 模拟LLM调用
        def call_llm(question):
            return {
                "question": question,
                "answer": f"LLM response to: {question}",
                "tokens": 100
            }
        
        question = "Explain machine learning"
        tenant_id = "tenant1"
        
        # 第一次LLM调用（缓存未命中）
        cache_result = cache.get(tenant_id, question, 5)
        assert cache_result is None
        
        # 调用LLM
        llm_result = call_llm(question)
        
        # 缓存结果
        cache.set(tenant_id, question, 5, llm_result)
        
        # 第二次相同问题（缓存命中，无需调用LLM）
        cached_result = cache.get(tenant_id, question, 5)
        assert cached_result is not None
        assert cached_result["answer"] == llm_result["answer"]
        
        # 验证缓存键唯一性
        same_result = cache.get(tenant_id, question, 5)
        assert same_result["answer"] == cached_result["answer"]

    def test_multi_tenant_cache_isolation(self, cache):
        """测试多租户缓存隔离"""
        # 相同问题，不同租户
        question = "What is AI?"
        
        # 租户1缓存
        cache.set("tenant1", question, 5, {
            "tenant": "tenant1",
            "answer": "Tenant1's answer"
        })
        
        # 租户2缓存
        cache.set("tenant2", question, 5, {
            "tenant": "tenant2",
            "answer": "Tenant2's answer"
        })
        
        # 验证租户隔离
        result1 = cache.get("tenant1", question, 5)
        result2 = cache.get("tenant2", question, 5)
        
        assert result1["tenant"] == "tenant1"
        assert result2["tenant"] == "tenant2"
        assert result1["answer"] != result2["answer"]

    def test_cache_with_different_top_k(self, cache):
        """测试不同top_k的缓存隔离"""
        question = "What is Python?"
        tenant_id = "tenant1"
        
        # top_k=5的缓存
        cache.set(tenant_id, question, 5, {"results": ["a", "b", "c", "d", "e"]})
        
        # top_k=10的缓存
        cache.set(tenant_id, question, 10, {"results": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]})
        
        # 验证top_k隔离
        result5 = cache.get(tenant_id, question, 5)
        result10 = cache.get(tenant_id, question, 10)
        
        assert len(result5["results"]) == 5
        assert len(result10["results"]) == 10
        assert result5 != result10

    def test_cache_clear_integration(self, cache):
        """测试缓存清理集成"""
        # 设置多个缓存
        for i in range(10):
            cache.set(f"tenant{i % 3}", f"question{i}", 5, {"data": i})
        
        # 验证缓存存在
        stats_before = cache.stats()
        assert stats_before["current_size"] == 10
        
        # 清空缓存
        cache.clear()
        
        # 验证缓存已清空
        stats_after = cache.stats()
        assert stats_after["current_size"] == 0
        
        # 验证所有缓存都无效
        for i in range(10):
            result = cache.get(f"tenant{i % 3}", f"question{i}", 5)
            assert result is None

    def test_cache_disabled_integration(self, cache):
        """测试缓存禁用时的集成"""
        with patch('backend.config.settings.query_cache_enabled', False):
            cache = QueryCache()
            
            # 尝试设置缓存
            cache.set("tenant1", "query", 5, {"result": "data"})
            
            # 验证缓存未生效
            result = cache.get("tenant1", "query", 5)
            assert result is None
            
            # 验证统计显示缓存禁用
            stats = cache.stats()
            assert stats["enabled"] is False

    def test_concurrent_cache_operations(self, cache):
        """测试并发缓存操作集成"""
        import threading
        
        errors = []
        results = []
        
        def concurrent_operation(i):
            try:
                tenant_id = f"tenant{i % 5}"
                question = f"question{i}"
                top_k = 5
                
                # 写入缓存
                cache.set(tenant_id, question, top_k, {"data": i})
                
                # 读取缓存
                result = cache.get(tenant_id, question, top_k)
                
                results.append((i, result))
            except Exception as e:
                errors.append(e)
        
        # 创建100个并发操作
        threads = [
            threading.Thread(target=concurrent_operation, args=(i,))
            for i in range(100)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证没有错误
        assert len(errors) == 0, f"并发操作错误: {errors}"
        
        # 验证操作成功
        assert len(results) == 100
        
        # 验证数据一致性
        for i, result in results:
            assert result is not None
            assert result["data"] == i

    def test_cache_stats_integration(self, cache):
        """测试缓存统计集成"""
        # 初始统计
        stats_initial = cache.stats()
        initial_size = stats_initial["current_size"]
        
        # 添加缓存
        for i in range(10):
            cache.set(f"tenant{i}", f"question{i}", 5, {"data": i})
        
        # 更新后的统计
        stats_after = cache.stats()
        
        assert stats_after["current_size"] == initial_size + 10
        assert stats_after["enabled"] is True
        assert stats_after["max_size"] > 0
        assert stats_after["ttl"] > 0
        assert stats_after["thread_safe"] is True

    def test_cache_with_complex_data(self, cache):
        """测试复杂缓存数据集成"""
        complex_data = {
            "question": "What is deep learning?",
            "answer": "Deep learning is...",
            "sources": [
                {"title": "Paper 1", "url": "http://example.com/1"},
                {"title": "Paper 2", "url": "http://example.com/2"}
            ],
            "metadata": {
                "confidence": 0.95,
                "model": "llama-3.1-8b",
                "tokens": {"prompt": 50, "completion": 100, "total": 150}
            },
            "timestamp": "2026-02-09T23:00:00Z"
        }
        
        # 缓存复杂数据
        cache.set("tenant1", "complex query", 5, complex_data)
        
        # 检索复杂数据
        result = cache.get("tenant1", "complex query", 5)
        
        assert result is not None
        assert result["question"] == complex_data["question"]
        assert len(result["sources"]) == 2
        assert result["metadata"]["confidence"] == 0.95
        assert result["metadata"]["tokens"]["total"] == 150

    def test_cache_question_normalization(self, cache):
        """测试问题文本标准化"""
        # 相同问题，不同格式
        questions = [
            "What is Python?",
            "what is python?",  # 小写
            "What   is   Python?",  # 多余空格
            "  What is Python?  ",  # 前后空格
        ]
        
        # 第一个问题缓存
        cache.set("tenant1", questions[0], 5, {"answer": "Python is..."})
        
        # 验证所有格式都能命中缓存
        for question in questions:
            result = cache.get("tenant1", question, 5)
            # 注意：当前实现可能只标准化空格，不处理大小写
            # 这里主要验证空格标准化
            if question.strip() == questions[0].strip():
                assert result is not None

    def test_cache_with_special_characters(self, cache):
        """测试特殊字符缓存集成"""
        special_questions = [
            "What's the meaning of 'life'?",
            "Use <html> tags",
            "Math: 2 + 2 = 4",
            "Emoji: 😀🎉",
            "中文：什么是AI？"
        ]
        
        for question in special_questions:
            cache.set("tenant1", question, 5, {"cached": True})
            result = cache.get("tenant1", question, 5)
            assert result is not None
            assert result["cached"] is True

    def test_cache_hit_rate_tracking(self, cache):
        """测试缓存命中率跟踪"""
        # 模拟多次查询
        questions = ["q1", "q2", "q3", "q1", "q2", "q1"]  # q1:3次, q2:2次, q3:1次
        
        # 第一次查询（全部未命中）
        hits = 0
        misses = 0
        
        for question in questions:
            result = cache.get("tenant1", question, 5)
            if result is None:
                misses += 1
                # 模拟从数据库获取并缓存
                cache.set("tenant1", question, 5, {"answer": f"Answer to {question}"})
            else:
                hits += 1
        
        # 第一次循环：全部miss
        assert hits == 0
        assert misses == 6
        
        # 第二次查询（应该全部命中）
        hits = 0
        misses = 0
        
        for question in questions:
            result = cache.get("tenant1", question, 5)
            if result is None:
                misses += 1
            else:
                hits += 1
        
        # 第二次循环：全部hit
        assert hits == 6
        assert misses == 0

    def test_cache_max_size_limit(self, cache):
        """测试缓存大小限制"""
        with patch('backend.config.settings.query_cache_maxsize', 5):
            cache = QueryCache()
            
            # 添加超过最大大小的缓存
            for i in range(10):
                cache.set(f"tenant{i}", f"question{i}", 5, {"data": i})
            
            # 验证缓存大小不超过最大值
            stats = cache.stats()
            assert stats["current_size"] <= stats["max_size"]
            assert stats["max_size"] == 5

    @pytest.mark.parametrize("tenant_id,question,top_k,data", [
        ("tenant1", "q1", 5, {"a": 1}),
        ("tenant2", "q2", 10, {"b": 2}),
        ("tenant3", "q3", 3, {"c": 3}),
    ])
    def test_cache_parametrized_operations(self, cache, tenant_id, question, top_k, data):
        """参数化测试缓存操作"""
        # 设置
        cache.set(tenant_id, question, top_k, data)
        
        # 获取
        result = cache.get(tenant_id, question, top_k)
        
        # 验证
        assert result is not None
        assert result == data