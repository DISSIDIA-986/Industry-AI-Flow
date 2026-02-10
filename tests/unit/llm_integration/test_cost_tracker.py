"""
成本追踪单元测试

测试CostTracker的成本计算、预算告警和租户隔离功能
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from backend.services.llm_integration.cost_tracker import CostTracker, LLMUsage, LLMCost


class TestCostTracker:
    """CostTracker单元测试类"""

    @pytest.fixture
    def tracker(self):
        """创建成本追踪器实例"""
        return CostTracker()

    def test_initialization(self, tracker):
        """测试初始化"""
        assert tracker is not None
        assert hasattr(tracker, '_usage_records')
        assert hasattr(tracker, '_budgets')

    def test_record_usage_basic(self, tracker):
        """测试基本使用记录"""
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
        """测试智谱AI成本计算"""
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )
        
        cost = tracker.calculate_cost("zhipu", usage)
        
        # 智谱AI定价：prompt 0.5元/百万tokens，completion 1.5元/百万tokens
        expected_prompt_cost = 1000 / 1_000_000 * 0.5  # 0.0005元
        expected_completion_cost = 500 / 1_000_000 * 1.5  # 0.00075元
        expected_total = expected_prompt_cost + expected_completion_cost
        
        assert abs(cost.usd - expected_total) < 0.0001
        assert cost.currency == "CNY"

    def test_calculate_cost_openai(self, tracker):
        """测试OpenAI成本计算"""
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )
        
        cost = tracker.calculate_cost("openai", usage)
        
        # OpenAI定价（GPT-4）：prompt 30美元/百万tokens，completion 60美元/百万tokens
        expected_prompt_cost = 1000 / 1_000_000 * 30  # 0.03美元
        expected_completion_cost = 500 / 1_000_000 * 60  # 0.03美元
        expected_total = expected_prompt_cost + expected_completion_cost
        
        assert abs(cost.usd - expected_total) < 0.001
        assert cost.currency == "USD"

    def test_calculate_cost_unknown_provider(self, tracker):
        """测试未知提供商成本计算"""
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )
        
        cost = tracker.calculate_cost("unknown_provider", usage)
        
        # 未知提供商应返回0成本
        assert cost.usd == 0.0
        assert cost.currency == "USD"

    def test_get_tenant_usage_empty(self, tracker):
        """测试空租户使用记录"""
        usage = tracker.get_tenant_usage("nonexistent_tenant")
        
        assert usage["tenant_id"] == "nonexistent_tenant"
        assert usage["total_requests"] == 0
        assert usage["total_cost_usd"] == 0.0
        assert usage["provider_breakdown"] == {}

    def test_get_tenant_usage_with_records(self, tracker):
        """测试有记录的租户使用统计"""
        # 添加多条使用记录
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
        """测试租户隔离"""
        # 租户1的使用记录
        tracker.record_usage(
            tenant_id="tenant1",
            provider="zhipu",
            model="glm-4",
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        )
        
        # 租户2的使用记录
        tracker.record_usage(
            tenant_id="tenant2",
            provider="openai",
            model="gpt-4",
            usage=LLMUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        )
        
        # 验证租户1的统计
        stats1 = tracker.get_tenant_usage("tenant1")
        assert stats1["total_requests"] == 1
        assert stats1["provider_breakdown"]["zhipu"]["request_count"] == 1
        
        # 验证租户2的统计
        stats2 = tracker.get_tenant_usage("tenant2")
        assert stats2["total_requests"] == 1
        assert stats2["provider_breakdown"]["openai"]["request_count"] == 1
        
        # 验证互不影响
        assert stats1["total_cost_usd"] != stats2["total_cost_usd"]

    def test_set_budget(self, tracker):
        """测试设置预算"""
        tracker.set_budget("tenant1", 100.0)
        
        assert "tenant1" in tracker._budgets
        assert tracker._budgets["tenant1"] == 100.0

    def test_check_budget_alert_no_budget(self, tracker):
        """测试无预算时的告警检查"""
        alert = tracker.check_budget_alert("tenant1")
        
        assert alert is None

    def test_check_budget_alert_under_budget(self, tracker):
        """测试未超预算时的告警检查"""
        tracker.set_budget("tenant1", 100.0)
        
        # 添加少量使用记录（约0.00015元）
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
        """测试超预算时的告警检查"""
        tracker.set_budget("tenant1", 0.00001)  # 设置极低预算
        
        # 添加使用记录（约0.00015元）
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
        """测试空使用历史"""
        history = tracker.get_usage_history("tenant1", limit=10)
        
        assert history == []

    def test_get_usage_history_with_records(self, tracker):
        """测试获取使用历史"""
        # 添加多条记录
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
        # 验证是最近的3条记录
        for record in history:
            assert record["tenant_id"] == "tenant1"

    def test_get_usage_history_limit(self, tracker):
        """测试历史记录限制"""
        # 添加10条记录
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
        
        # 请求5条记录
        history = tracker.get_usage_history("tenant1", limit=5)
        
        assert len(history) == 5

    def test_multiple_providers_breakdown(self, tracker):
        """测试多提供商统计"""
        # 添加不同提供商的使用记录
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
        """测试并发记录使用"""
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
        
        # 创建100个线程并发记录
        threads = [
            threading.Thread(target=record_concurrently, args=(i,))
            for i in range(100)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证没有错误
        assert len(errors) == 0, f"并发记录错误: {errors}"
        
        # 验证记录总数
        assert len(tracker._usage_records) == 100

    def test_usage_total_tokens_calculation(self, tracker):
        """测试总token数计算"""
        usage = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50
        )
        
        # 验证total_tokens自动计算
        assert usage.total_tokens == 150
        
        # 如果明确指定total_tokens，使用指定的值
        usage2 = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=200
        )
        assert usage2.total_tokens == 200

    def test_cost_dataclass(self):
        """测试LLMCost数据类"""
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
        """参数化测试不同使用记录场景"""
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
        
        # 验证记录已添加
        assert len(tracker._usage_records) > 0

    def test_clear_tenant_records(self, tracker):
        """测试清除租户记录"""
        # 添加记录
        tracker.record_usage(
            tenant_id="tenant1",
            provider="zhipu",
            model="glm-4",
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        )
        
        # 验证记录存在
        stats = tracker.get_tenant_usage("tenant1")
        assert stats["total_requests"] == 1
        
        # 清除记录
        tracker.clear_tenant_records("tenant1")
        
        # 验证记录已清除
        stats = tracker.get_tenant_usage("tenant1")
        assert stats["total_requests"] == 0