"""
EN

EN,LLMEN
"""

import pytest
import time
from unittest.mock import Mock, patch
from backend.services.cache.query_cache import QueryCache


@pytest.mark.integration
@pytest.mark.cache
class TestCacheIntegration:
    """EN"""

    @pytest.fixture
    def cache(self):
        """EN"""
        return QueryCache()

    def test_cache_with_database_integration(self, cache):
        """EN"""
        # EN
        def fetch_from_db(tenant_id, question, top_k):
            return {
                "tenant_id": tenant_id,
                "question": question,
                "answer": f"Answer to: {question}",
                "top_k": top_k
            }
        
        # EN(EN)
        tenant_id = "tenant1"
        question = "What is Python?"
        top_k = 5
        
        result1 = cache.get(tenant_id, question, top_k)
        assert result1 is None  # EN
        
        # EN
        db_result = fetch_from_db(tenant_id, question, top_k)
        cache.set(tenant_id, question, top_k, db_result)
        
        # EN(EN)
        result2 = cache.get(tenant_id, question, top_k)
        assert result2 is not None
        assert result2["answer"] == f"Answer to: {question}"
        assert result2["tenant_id"] == tenant_id

    def test_cache_ttl_expiration_integration(self, cache):
        """ENTTLEN"""
        with patch('backend.config.settings.query_cache_ttl_seconds', 1):
            cache = QueryCache()
            
            # EN
            cache.set("tenant1", "query", 5, {"result": "cached"})
            
            # EN
            result1 = cache.get("tenant1", "query", 5)
            assert result1 is not None
            
            # EN
            time.sleep(2)
            
            # EN
            result2 = cache.get("tenant1", "query", 5)
            assert result2 is None

    def test_cache_with_llm_integration(self, cache):
        """ENLLMEN"""
        # ENLLMEN
        def call_llm(question):
            return {
                "question": question,
                "answer": f"LLM response to: {question}",
                "tokens": 100
            }
        
        question = "Explain machine learning"
        tenant_id = "tenant1"
        
        # ENLLMEN(EN)
        cache_result = cache.get(tenant_id, question, 5)
        assert cache_result is None
        
        # ENLLM
        llm_result = call_llm(question)
        
        # EN
        cache.set(tenant_id, question, 5, llm_result)
        
        # EN(EN,ENLLM)
        cached_result = cache.get(tenant_id, question, 5)
        assert cached_result is not None
        assert cached_result["answer"] == llm_result["answer"]
        
        # EN
        same_result = cache.get(tenant_id, question, 5)
        assert same_result["answer"] == cached_result["answer"]

    def test_multi_tenant_cache_isolation(self, cache):
        """EN"""
        # EN,EN
        question = "What is AI?"
        
        # EN1EN
        cache.set("tenant1", question, 5, {
            "tenant": "tenant1",
            "answer": "Tenant1's answer"
        })
        
        # EN2EN
        cache.set("tenant2", question, 5, {
            "tenant": "tenant2",
            "answer": "Tenant2's answer"
        })
        
        # EN
        result1 = cache.get("tenant1", question, 5)
        result2 = cache.get("tenant2", question, 5)
        
        assert result1["tenant"] == "tenant1"
        assert result2["tenant"] == "tenant2"
        assert result1["answer"] != result2["answer"]

    def test_cache_with_different_top_k(self, cache):
        """ENtop_kEN"""
        question = "What is Python?"
        tenant_id = "tenant1"
        
        # top_k=5EN
        cache.set(tenant_id, question, 5, {"results": ["a", "b", "c", "d", "e"]})
        
        # top_k=10EN
        cache.set(tenant_id, question, 10, {"results": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]})
        
        # ENtop_kEN
        result5 = cache.get(tenant_id, question, 5)
        result10 = cache.get(tenant_id, question, 10)
        
        assert len(result5["results"]) == 5
        assert len(result10["results"]) == 10
        assert result5 != result10

    def test_cache_clear_integration(self, cache):
        """EN"""
        # EN
        for i in range(10):
            cache.set(f"tenant{i % 3}", f"question{i}", 5, {"data": i})
        
        # EN
        stats_before = cache.stats()
        assert stats_before["current_size"] == 10
        
        # EN
        cache.clear()
        
        # EN
        stats_after = cache.stats()
        assert stats_after["current_size"] == 0
        
        # EN
        for i in range(10):
            result = cache.get(f"tenant{i % 3}", f"question{i}", 5)
            assert result is None

    def test_cache_disabled_integration(self, cache):
        """EN"""
        with patch('backend.config.settings.query_cache_enabled', False):
            cache = QueryCache()
            
            # EN
            cache.set("tenant1", "query", 5, {"result": "data"})
            
            # EN
            result = cache.get("tenant1", "query", 5)
            assert result is None
            
            # EN
            stats = cache.stats()
            assert stats["enabled"] is False

    def test_concurrent_cache_operations(self, cache):
        """EN"""
        import threading
        
        errors = []
        results = []
        
        def concurrent_operation(i):
            try:
                tenant_id = f"tenant{i % 5}"
                question = f"question{i}"
                top_k = 5
                
                # EN
                cache.set(tenant_id, question, top_k, {"data": i})
                
                # EN
                result = cache.get(tenant_id, question, top_k)
                
                results.append((i, result))
            except Exception as e:
                errors.append(e)
        
        # EN100EN
        threads = [
            threading.Thread(target=concurrent_operation, args=(i,))
            for i in range(100)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # EN
        assert len(errors) == 0, f"EN: {errors}"
        
        # EN
        assert len(results) == 100
        
        # EN
        for i, result in results:
            assert result is not None
            assert result["data"] == i

    def test_cache_stats_integration(self, cache):
        """EN"""
        # EN
        stats_initial = cache.stats()
        initial_size = stats_initial["current_size"]
        
        # EN
        for i in range(10):
            cache.set(f"tenant{i}", f"question{i}", 5, {"data": i})
        
        # EN
        stats_after = cache.stats()
        
        assert stats_after["current_size"] == initial_size + 10
        assert stats_after["enabled"] is True
        assert stats_after["max_size"] > 0
        assert stats_after["ttl"] > 0
        assert stats_after["thread_safe"] is True

    def test_cache_with_complex_data(self, cache):
        """EN"""
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
        
        # EN
        cache.set("tenant1", "complex query", 5, complex_data)
        
        # EN
        result = cache.get("tenant1", "complex query", 5)
        
        assert result is not None
        assert result["question"] == complex_data["question"]
        assert len(result["sources"]) == 2
        assert result["metadata"]["confidence"] == 0.95
        assert result["metadata"]["tokens"]["total"] == 150

    def test_cache_question_normalization(self, cache):
        """EN"""
        # EN,EN
        questions = [
            "What is Python?",
            "what is python?",  # EN
            "What   is   Python?",  # EN
            "  What is Python?  ",  # EN
        ]
        
        # EN
        cache.set("tenant1", questions[0], 5, {"answer": "Python is..."})
        
        # EN
        for question in questions:
            result = cache.get("tenant1", question, 5)
            # EN:EN,EN
            # EN
            if question.strip() == questions[0].strip():
                assert result is not None

    def test_cache_with_special_characters(self, cache):
        """EN"""
        special_questions = [
            "What's the meaning of 'life'?",
            "Use <html> tags",
            "Math: 2 + 2 = 4",
            "Emoji: 😀🎉",
            "EN:ENAI?"
        ]
        
        for question in special_questions:
            cache.set("tenant1", question, 5, {"cached": True})
            result = cache.get("tenant1", question, 5)
            assert result is not None
            assert result["cached"] is True

    def test_cache_hit_rate_tracking(self, cache):
        """EN"""
        # EN,ENmiss
        first_round_questions = [f"q{i}" for i in range(1, 7)]
        hits = 0
        misses = 0

        for question in first_round_questions:
            result = cache.get("tenant1", question, 5)
            if result is None:
                misses += 1
                # EN
                cache.set("tenant1", question, 5, {"answer": f"Answer to {question}"})
            else:
                hits += 1

        # EN:ENmiss
        assert hits == 0
        assert misses == 6

        # EN:EN,ENhit
        hits = 0
        misses = 0

        for question in first_round_questions:
            result = cache.get("tenant1", question, 5)
            if result is None:
                misses += 1
            else:
                hits += 1

        # EN:ENhit
        assert hits == 6
        assert misses == 0

    def test_cache_max_size_limit(self, cache):
        """EN"""
        with patch('backend.config.settings.query_cache_maxsize', 5):
            cache = QueryCache()
            
            # EN
            for i in range(10):
                cache.set(f"tenant{i}", f"question{i}", 5, {"data": i})
            
            # EN
            stats = cache.stats()
            assert stats["current_size"] <= stats["max_size"]
            assert stats["max_size"] == 5

    @pytest.mark.parametrize("tenant_id,question,top_k,data", [
        ("tenant1", "q1", 5, {"a": 1}),
        ("tenant2", "q2", 10, {"b": 2}),
        ("tenant3", "q3", 3, {"c": 3}),
    ])
    def test_cache_parametrized_operations(self, cache, tenant_id, question, top_k, data):
        """EN"""
        # EN
        cache.set(tenant_id, question, top_k, data)
        
        # EN
        result = cache.get(tenant_id, question, top_k)
        
        # EN
        assert result is not None
        assert result == data
