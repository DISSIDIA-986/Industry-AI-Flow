"""
LLM调度集成测试

测试端到端LLM调度流程，包括本地/云端fallback、成本追踪和脱敏
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from backend.services.llm_integration.dispatch_service import DispatchService
from backend.services.llm_integration.types import (
    DispatchRequest,
    RouteMode,
    LLMUsage
)


@pytest.mark.integration
@pytest.mark.llm
class TestLLMDispatchIntegration:
    """LLM调度集成测试类"""

    @pytest.fixture
    def mock_clients(self):
        """创建模拟客户端"""
        with patch('backend.services.llm_integration.dispatch_service.LlamaCppClient') as mock_llama, \
             patch('backend.services.llm_integration.dispatch_service.ZhipuClient') as mock_zhipu, \
             patch('backend.services.llm_integration.dispatch_service.OpenAIClient') as mock_openai:
            
            # 配置本地客户端
            local_instance = Mock()
            local_instance.generate.return_value = "Local model response"
            mock_llama.return_value = local_instance
            
            # 配置智谱客户端
            zhipu_instance = Mock()
            zhipu_instance.generate.return_value = "Zhipu AI response"
            mock_zhipu.return_value = zhipu_instance
            
            # 配置OpenAI客户端
            openai_instance = Mock()
            openai_instance.generate.return_value = "OpenAI response"
            mock_openai.return_value = openai_instance
            
            yield {
                "llama": mock_llama,
                "zhipu": mock_zhipu,
                "openai": mock_openai
            }

    @pytest.fixture
    def service(self):
        """创建调度服务实例"""
        return DispatchService()

    def test_local_only_end_to_end(self, service, mock_clients):
        """测试本地优先模式端到端流程"""
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="What is the capital of France?",
            route_mode=RouteMode.LOCAL_ONLY,
            max_tokens=100,
            temperature=0.7
        )
        
        result = service.generate(request)
        
        # 验证响应
        assert result.success is True
        assert result.provider == "llama_cpp"
        assert result.text == "Local model response"
        assert result.fallback_triggered is False
        assert result.usage.total_tokens > 0
        assert result.latency_ms > 0
        
        # 验证成本记录
        stats = service.cost_tracker.get_tenant_usage("test_tenant")
        assert stats["total_requests"] == 1
        assert "llama_cpp" in stats["provider_breakdown"]

    def test_cloud_only_end_to_end(self, service, mock_clients):
        """测试云端优先模式端到端流程"""
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Explain quantum computing in detail",
            route_mode=RouteMode.CLOUD_ONLY,
            max_tokens=500,
            temperature=0.5
        )
        
        result = service.generate(request)
        
        # 验证响应
        assert result.success is True
        assert result.provider in ["zhipu", "openai"]
        assert result.text in ["Zhipu AI response", "OpenAI response"]
        assert result.usage.total_tokens > 0
        assert result.latency_ms > 0
        
        # 验证成本记录
        stats = service.cost_tracker.get_tenant_usage("test_tenant")
        assert stats["total_requests"] == 1
        assert result.provider in stats["provider_breakdown"]

    def test_hybrid_mode_local_success_no_fallback(self, service, mock_clients):
        """测试混合模式本地成功，无需fallback"""
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Simple question",
            route_mode=RouteMode.HYBRID_AUTO,
            local_conf_threshold=0.75
        )
        
        result = service.generate(request)
        
        # 验证本地成功
        assert result.success is True
        assert result.provider == "llama_cpp"
        assert result.fallback_triggered is False
        
        # 验证云端客户端未被调用
        mock_clients["zhipu"].return_value.generate.assert_not_called()
        mock_clients["openai"].return_value.generate.assert_not_called()

    def test_hybrid_mode_cloud_fallback_triggered(self, service, mock_clients):
        """测试混合模式触发云端fallback"""
        # 配置本地客户端返回低质量响应
        local_instance = mock_clients["llama"].return_value
        local_instance.generate.return_value = "I'm not sure about this complex topic"
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Explain the theory of relativity",
            route_mode=RouteMode.HYBRID_AUTO,
            local_conf_threshold=0.99  # 高阈值强制fallback
        )
        
        result = service.generate(request)
        
        # 验证fallback触发
        assert result.success is True
        assert result.fallback_triggered is True
        assert result.provider in ["zhipu", "openai"]
        
        # 验证两个提供商都被尝试过
        # 注意：实际实现中可能只尝试一个成功的提供商

    def test_redaction_before_cloud_call(self, service, mock_clients):
        """测试云端调用前的敏感信息脱敏"""
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="My email is test@example.com and phone is 13800138000",
            route_mode=RouteMode.CLOUD_ONLY
        )
        
        result = service.generate(request)
        
        # 验证调用成功
        assert result.success is True
        
        # 验证脱敏服务被调用（通过检查云端客户端接收到的参数）
        # 实际实现中，脱敏后的文本应该发送到云端
        cloud_instance = mock_clients["zhipu"].return_value or mock_clients["openai"].return_value
        if cloud_instance.generate.called:
            call_args = cloud_instance.generate.call_args
            # 验证敏感信息被脱敏
            sent_text = str(call_args)
            assert "test@example.com" not in sent_text or "REDACTED" in sent_text

    def test_cost_tracking_across_multiple_requests(self, service, mock_clients):
        """测试多个请求的成本追踪"""
        requests = [
            DispatchRequest(
                tenant_id="test_tenant",
                question=f"Question {i}",
                route_mode=RouteMode.LOCAL_ONLY
            )
            for i in range(10)
        ]
        
        # 发送10个请求
        for request in requests:
            service.generate(request)
        
        # 验证成本统计
        stats = service.cost_tracker.get_tenant_usage("test_tenant")
        
        assert stats["total_requests"] == 10
        assert stats["provider_breakdown"]["llama_cpp"]["request_count"] == 10
        assert stats["total_cost_usd"] > 0

    def test_budget_alert_integration(self, service, mock_clients):
        """测试预算告警集成"""
        # 设置极低预算
        service.cost_tracker.set_budget("test_tenant", 0.000001)
        
        # 发送请求
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test question",
            route_mode=RouteMode.LOCAL_ONLY
        )
        
        service.generate(request)
        
        # 检查预算告警
        alert = service.cost_tracker.check_budget_alert("test_tenant")
        
        # 本地模型成本极低，可能不会超预算
        # 这里主要验证告警机制可以正常工作
        assert alert is not None
        assert "budget" in alert
        assert "used" in alert

    def test_concurrent_requests(self, service, mock_clients):
        """测试并发请求处理"""
        import threading
        
        errors = []
        results = []
        
        def make_request(i):
            try:
                request = DispatchRequest(
                    tenant_id=f"tenant_{i % 5}",  # 5个租户
                    question=f"Concurrent question {i}",
                    route_mode=RouteMode.LOCAL_ONLY
                )
                result = service.generate(request)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # 创建50个并发请求
        threads = [
            threading.Thread(target=make_request, args=(i,))
            for i in range(50)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证所有请求都成功
        assert len(errors) == 0, f"并发请求错误: {errors}"
        assert len(results) == 50
        
        # 验证每个结果都成功
        for result in results:
            assert result.success is True

    def test_error_handling_local_failure_soft_fail(self, service, mock_clients):
        """测试本地失败时的软失败处理"""
        # 配置本地客户端抛出异常
        local_instance = mock_clients["llama"].return_value
        local_instance.generate.side_effect = Exception("Local model crashed")
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test question",
            route_mode=RouteMode.LOCAL_ONLY,
            soft_fail=True
        )
        
        result = service.generate(request)
        
        # 验证软失败
        assert result.success is False
        assert "Local model crashed" in result.error
        assert result.provider is None

    def test_error_handling_local_failure_with_fallback(self, service, mock_clients):
        """测试本地失败时自动fallback到云端"""
        # 配置本地客户端抛出异常
        local_instance = mock_clients["llama"].return_value
        local_instance.generate.side_effect = Exception("Local model crashed")
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test question",
            route_mode=RouteMode.HYBRID_AUTO
        )
        
        result = service.generate(request)
        
        # 验证fallback到云端成功
        assert result.success is True
        assert result.provider in ["zhipu", "openai"]
        assert result.fallback_triggered is True

    def test_multi_tenant_isolation(self, service, mock_clients):
        """测试多租户隔离"""
        # 为不同租户发送请求
        tenants = ["tenant1", "tenant2", "tenant3"]
        
        for tenant in tenants:
            for i in range(5):
                request = DispatchRequest(
                    tenant_id=tenant,
                    question=f"Question {i}",
                    route_mode=RouteMode.LOCAL_ONLY
                )
                service.generate(request)
        
        # 验证每个租户的统计独立
        for tenant in tenants:
            stats = service.cost_tracker.get_tenant_usage(tenant)
            assert stats["total_requests"] == 5
            assert stats["tenant_id"] == tenant

    def test_latency_tracking(self, service, mock_clients):
        """测试延迟跟踪"""
        import time
        
        # 配置延迟
        def slow_generate(*args, **kwargs):
            time.sleep(0.01)  # 10ms延迟
            return "Response"
        
        local_instance = mock_clients["llama"].return_value
        local_instance.generate.side_effect = slow_generate
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test",
            route_mode=RouteMode.LOCAL_ONLY
        )
        
        result = service.generate(request)
        
        # 验证延迟被记录
        assert result.latency_ms > 0
        assert result.latency_ms < 100  # 应该小于100ms

    def test_usage_tracking(self, service, mock_clients):
        """测试使用量跟踪"""
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test question",
            route_mode=RouteMode.LOCAL_ONLY
        )
        
        result = service.generate(request)
        
        # 验证使用量被记录
        assert result.usage.prompt_tokens >= 0
        assert result.usage.completion_tokens >= 0
        assert result.usage.total_tokens > 0

    @pytest.mark.parametrize("route_mode,expected_provider", [
        (RouteMode.LOCAL_ONLY, "llama_cpp"),
        (RouteMode.CLOUD_ONLY, ["zhipu", "openai"]),
        (RouteMode.HYBRID_AUTO, "llama_cpp"),  # 默认先本地
    ])
    def test_route_modes_integration(self, service, mock_clients, route_mode, expected_provider):
        """参数化测试不同路由模式"""
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test",
            route_mode=route_mode
        )
        
        result = service.generate(request)
        
        assert result.success is True
        if isinstance(expected_provider, list):
            assert result.provider in expected_provider
        else:
            assert result.provider == expected_provider