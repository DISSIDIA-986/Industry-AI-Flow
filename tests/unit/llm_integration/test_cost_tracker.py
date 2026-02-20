"""
EN

ENCostTrackerEN,EN
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from backend.services.llm_integration.cost_tracker import CostTracker, LLMUsage, LLMCost


class TestCostTracker:
    """CostTrackerEN"""

    @pytest.fixture
    def tracker(self):
        """EN"""
        return CostTracker()

    def test_initialization(self, tracker):
        """EN"""
        assert tracker is not None
        assert hasattr(tracker, '_usage_records')
        assert hasattr(tracker, '_budgets')

    def test_record_usage_basic(self, tracker):
        """EN"""
        usage = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        
        tracker.record_usage(
            tenant_id="tenant1",
            provider="zhipu",
            model="glm-4",
            usage=usage
        )
        
        assert len(tracker._usage_records) == 1
        record = tracker._usage_records[0]
        assert record["tenant_id"] == "tenant1"
        assert record["provider"] == "zhipu"
        assert record["model"] == "glm-4"

    def test_calculate_cost_zhipu(self, tracker):
        """ENAIEN"""
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )
        
        cost = tracker.calculate_cost("zhipu", usage)
        
        # ENAIEN:prompt 0.5EN/ENtokens,completion 1.5EN/ENtokens
        expected_prompt_cost = 1000 / 1_000_000 * 0.5  # 0.0005EN
        expected_completion_cost = 500 / 1_000_000 * 1.5  # 0.00075EN
        expected_total = expected_prompt_cost + expected_completion_cost
        
        assert abs(cost.usd - expected_total) < 0.0001
        assert cost.currency == "CNY"

    def test_calculate_cost_openai(self, tracker):
        """ENOpenAIEN"""
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )
        
        cost = tracker.calculate_cost("openai", usage)
        
        # OpenAIEN(GPT-4):prompt 30EN/ENtokens,completion 60EN/ENtokens
        expected_prompt_cost = 1000 / 1_000_000 * 30  # 0.03EN
        expected_completion_cost = 500 / 1_000_000 * 60  # 0.03EN
        expected_total = expected_prompt_cost + expected_completion_cost
        
        assert abs(cost.usd - expected_total) < 0.001
        assert cost.currency == "USD"

    def test_calculate_cost_unknown_provider(self, tracker):
        """EN"""
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )
        
        cost = tracker.calculate_cost("unknown_provider", usage)
        
        # EN0EN
        assert cost.usd == 0.0
        assert cost.currency == "USD"

    def test_get_tenant_usage_empty(self, tracker):
        """EN"""
        usage = tracker.get_tenant_usage("nonexistent_tenant")
        
        assert usage["tenant_id"] == "nonexistent_tenant"
        assert usage["total_requests"] == 0
        assert usage["total_cost_usd"] == 0.0
        assert usage["provider_breakdown"] == {}

    def test_get_tenant_usage_with_records(self, tracker):
        """EN"""
        # EN
        for i in range(5):
            usage = LLMUsage(
                prompt_tokens=100 * (i + 1),
                completion_tokens=50 * (i + 1),
                total_tokens=150 * (i + 1)
            )
            tracker.record_usage(
                tenant_id="tenant1",
                provider="zhipu",
                model="glm-4",
                usage=usage
            )
        
        stats = tracker.get_tenant_usage("tenant1")
        
        assert stats["tenant_id"] == "tenant1"
        assert stats["total_requests"] == 5
        assert stats["total_cost_usd"] > 0
        assert "zhipu" in stats["provider_breakdown"]
        assert stats["provider_breakdown"]["zhipu"]["request_count"] == 5

    def test_tenant_isolation(self, tracker):
        """EN"""
        # EN1EN
        tracker.record_usage(
            tenant_id="tenant1",
            provider="zhipu",
            model="glm-4",
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        )
        
        # EN2EN
        tracker.record_usage(
            tenant_id="tenant2",
            provider="openai",
            model="gpt-4",
            usage=LLMUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        )
        
        # EN1EN
        stats1 = tracker.get_tenant_usage("tenant1")
        assert stats1["total_requests"] == 1
        assert stats1["provider_breakdown"]["zhipu"]["request_count"] == 1
        
        # EN2EN
        stats2 = tracker.get_tenant_usage("tenant2")
        assert stats2["total_requests"] == 1
        assert stats2["provider_breakdown"]["openai"]["request_count"] == 1
        
        # EN
        assert stats1["total_cost_usd"] != stats2["total_cost_usd"]

    def test_set_budget(self, tracker):
        """EN"""
        tracker.set_budget("tenant1", 100.0)
        
        assert "tenant1" in tracker._budgets
        assert tracker._budgets["tenant1"] == 100.0

    def test_check_budget_alert_no_budget(self, tracker):
        """EN"""
        alert = tracker.check_budget_alert("tenant1")
        
        assert alert is None

    def test_check_budget_alert_under_budget(self, tracker):
        """EN"""
        tracker.set_budget("tenant1", 100.0)
        
        # EN(EN0.00015EN)
        tracker.record_usage(
            tenant_id="tenant1",
            provider="zhipu",
            model="glm-4",
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        )
        
        alert = tracker.check_budget_alert("tenant1")
        
        assert alert is not None
        assert alert["exceeded"] is False
        assert alert["budget"] == 100.0
        assert alert["used"] < 100.0

    def test_check_budget_alert_over_budget(self, tracker):
        """EN"""
        tracker.set_budget("tenant1", 0.00001)  # EN
        
        # EN(EN0.00015EN)
        tracker.record_usage(
            tenant_id="tenant1",
            provider="zhipu",
            model="glm-4",
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        )
        
        alert = tracker.check_budget_alert("tenant1")
        
        assert alert is not None
        assert alert["exceeded"] is True
        assert alert["budget"] == 0.00001
        assert alert["used"] > 0.00001

    def test_get_usage_history_empty(self, tracker):
        """EN"""
        history = tracker.get_usage_history("tenant1", limit=10)
        
        assert history == []

    def test_get_usage_history_with_records(self, tracker):
        """EN"""
        # EN
        for i in range(5):
            tracker.record_usage(
                tenant_id="tenant1",
                provider="zhipu",
                model="glm-4",
                usage=LLMUsage(
                    prompt_tokens=100 * (i + 1),
                    completion_tokens=50 * (i + 1),
                    total_tokens=150 * (i + 1)
                )
            )
        
        history = tracker.get_usage_history("tenant1", limit=3)
        
        assert len(history) == 3
        # EN3EN
        for record in history:
            assert record["tenant_id"] == "tenant1"

    def test_get_usage_history_limit(self, tracker):
        """EN"""
        # EN10EN
        for i in range(10):
            tracker.record_usage(
                tenant_id="tenant1",
                provider="zhipu",
                model="glm-4",
                usage=LLMUsage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150
                )
            )
        
        # EN5EN
        history = tracker.get_usage_history("tenant1", limit=5)
        
        assert len(history) == 5

    def test_multiple_providers_breakdown(self, tracker):
        """EN"""
        # EN
        tracker.record_usage(
            tenant_id="tenant1",
            provider="zhipu",
            model="glm-4",
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        )
        
        tracker.record_usage(
            tenant_id="tenant1",
            provider="openai",
            model="gpt-4",
            usage=LLMUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300)
        )
        
        stats = tracker.get_tenant_usage("tenant1")
        
        assert stats["total_requests"] == 2
        assert "zhipu" in stats["provider_breakdown"]
        assert "openai" in stats["provider_breakdown"]
        assert stats["provider_breakdown"]["zhipu"]["request_count"] == 1
        assert stats["provider_breakdown"]["openai"]["request_count"] == 1

    def test_concurrent_record_usage(self):
        """EN"""
        import threading
        
        tracker = CostTracker()
        errors = []
        
        def record_concurrently(i):
            try:
                tracker.record_usage(
                    tenant_id=f"tenant{i % 10}",
                    provider="zhipu",
                    model="glm-4",
                    usage=LLMUsage(
                        prompt_tokens=100,
                        completion_tokens=50,
                        total_tokens=150
                    )
                )
            except Exception as e:
                errors.append(e)
        
        # EN100EN
        threads = [
            threading.Thread(target=record_concurrently, args=(i,))
            for i in range(100)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # EN
        assert len(errors) == 0, f"EN: {errors}"
        
        # EN
        assert len(tracker._usage_records) == 100

    def test_usage_total_tokens_calculation(self, tracker):
        """ENtokenEN"""
        usage = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50
        )
        
        # ENtotal_tokensEN
        assert usage.total_tokens == 150
        
        # ENtotal_tokens,EN
        usage2 = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=200
        )
        assert usage2.total_tokens == 200

    def test_cost_dataclass(self):
        """ENLLMCostEN"""
        cost = LLMCost(usd=0.001234, currency="USD")
        
        assert cost.usd == 0.001234
        assert cost.currency == "USD"

    @pytest.mark.parametrize("tenant_id,provider,model,prompt_tokens,completion_tokens", [
        ("tenant1", "zhipu", "glm-4", 100, 50),
        ("tenant2", "openai", "gpt-4", 1000, 500),
        ("tenant3", "zhipu", "glm-4", 0, 0),
        ("tenant4", "unknown", "unknown", 100, 50),
    ])
    def test_record_usage_parametrized(self, tracker, tenant_id, provider, model, prompt_tokens, completion_tokens):
        """EN"""
        usage = LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
        
        tracker.record_usage(
            tenant_id=tenant_id,
            provider=provider,
            model=model,
            usage=usage
        )
        
        # EN
        assert len(tracker._usage_records) > 0

    def test_clear_tenant_records(self, tracker):
        """EN"""
        # EN
        tracker.record_usage(
            tenant_id="tenant1",
            provider="zhipu",
            model="glm-4",
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        )
        
        # EN
        stats = tracker.get_tenant_usage("tenant1")
        assert stats["total_requests"] == 1
        
        # EN
        tracker.clear_tenant_records("tenant1")
        
        # EN
        stats = tracker.get_tenant_usage("tenant1")
        assert stats["total_requests"] == 0