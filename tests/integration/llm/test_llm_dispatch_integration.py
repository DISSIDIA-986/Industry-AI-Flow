"""
LLMEN

ENLLMEN,EN/ENfallback,EN
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
    """LLMEN"""

    @pytest.fixture
    def mock_clients(self):
        """EN"""
        with patch('backend.services.llm_integration.dispatch_service.LlamaCppClient') as mock_llama, \
             patch('backend.services.llm_integration.dispatch_service.ZhipuClient') as mock_zhipu, \
             patch('backend.services.llm_integration.dispatch_service.OpenAIClient') as mock_openai:
            
            # EN
            local_instance = Mock()
            local_instance.generate.return_value = "Local model response"
            mock_llama.return_value = local_instance
            
            # EN
            zhipu_instance = Mock()
            zhipu_instance.generate.return_value = "Zhipu AI response"
            mock_zhipu.return_value = zhipu_instance
            
            # ENOpenAIEN
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
        """EN"""
        return DispatchService()

    def test_local_only_end_to_end(self, service, mock_clients):
        """EN"""
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="What is the capital of France?",
            route_mode=RouteMode.LOCAL_ONLY,
            max_tokens=100,
            temperature=0.7
        )
        
        result = service.generate(request)
        
        # EN
        assert result.success is True
        assert result.provider == "llama_cpp"
        assert result.text == "Local model response"
        assert result.fallback_triggered is False
        assert result.usage.total_tokens > 0
        assert result.latency_ms > 0
        
        # EN
        stats = service.cost_tracker.get_tenant_usage("test_tenant")
        assert stats["total_requests"] == 1
        assert "llama_cpp" in stats["provider_breakdown"]

    def test_cloud_only_end_to_end(self, service, mock_clients):
        """EN"""
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Explain quantum computing in detail",
            route_mode=RouteMode.CLOUD_ONLY,
            max_tokens=500,
            temperature=0.5
        )
        
        result = service.generate(request)
        
        # EN
        assert result.success is True
        assert result.provider in ["zhipu", "openai"]
        assert result.text in ["Zhipu AI response", "OpenAI response"]
        assert result.usage.total_tokens > 0
        assert result.latency_ms > 0
        
        # EN
        stats = service.cost_tracker.get_tenant_usage("test_tenant")
        assert stats["total_requests"] == 1
        assert result.provider in stats["provider_breakdown"]

    def test_hybrid_mode_local_success_no_fallback(self, service, mock_clients):
        """EN,ENfallback"""
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Simple question",
            route_mode=RouteMode.HYBRID_AUTO,
            local_conf_threshold=0.75
        )
        
        result = service.generate(request)
        
        # EN
        assert result.success is True
        assert result.provider == "llama_cpp"
        assert result.fallback_triggered is False
        
        # EN
        mock_clients["zhipu"].return_value.generate.assert_not_called()
        mock_clients["openai"].return_value.generate.assert_not_called()

    def test_hybrid_mode_cloud_fallback_triggered(self, service, mock_clients):
        """ENfallback"""
        # EN
        local_instance = mock_clients["llama"].return_value
        local_instance.generate.return_value = "I'm not sure about this complex topic"
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Explain the theory of relativity",
            route_mode=RouteMode.HYBRID_AUTO,
            local_conf_threshold=0.99  # ENfallback
        )
        
        result = service.generate(request)
        
        # ENfallbackEN
        assert result.success is True
        assert result.fallback_triggered is True
        assert result.provider in ["zhipu", "openai"]
        
        # EN
        # EN:EN

    def test_redaction_before_cloud_call(self, service, mock_clients):
        """EN"""
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="My email is test@example.com and phone is 13800138000",
            route_mode=RouteMode.CLOUD_ONLY
        )
        
        result = service.generate(request)
        
        # EN
        assert result.success is True
        
        # EN(EN)
        # EN,EN
        cloud_instance = mock_clients["zhipu"].return_value or mock_clients["openai"].return_value
        if cloud_instance.generate.called:
            call_args = cloud_instance.generate.call_args
            # EN
            sent_text = str(call_args)
            assert "test@example.com" not in sent_text or "REDACTED" in sent_text

    def test_cost_tracking_across_multiple_requests(self, service, mock_clients):
        """EN"""
        requests = [
            DispatchRequest(
                tenant_id="test_tenant",
                question=f"Question {i}",
                route_mode=RouteMode.LOCAL_ONLY
            )
            for i in range(10)
        ]
        
        # EN10EN
        for request in requests:
            service.generate(request)
        
        # EN
        stats = service.cost_tracker.get_tenant_usage("test_tenant")
        
        assert stats["total_requests"] == 10
        assert stats["provider_breakdown"]["llama_cpp"]["request_count"] == 10
        assert stats["total_cost_usd"] > 0

    def test_budget_alert_integration(self, service, mock_clients):
        """EN"""
        # EN
        service.cost_tracker.set_budget("test_tenant", 0.000001)
        
        # EN
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test question",
            route_mode=RouteMode.LOCAL_ONLY
        )
        
        service.generate(request)
        
        # EN
        alert = service.cost_tracker.check_budget_alert("test_tenant")
        
        # EN,EN
        # EN
        assert alert is not None
        assert "budget" in alert
        assert "used" in alert

    def test_concurrent_requests(self, service, mock_clients):
        """EN"""
        import threading
        
        errors = []
        results = []
        
        def make_request(i):
            try:
                request = DispatchRequest(
                    tenant_id=f"tenant_{i % 5}",  # 5EN
                    question=f"Concurrent question {i}",
                    route_mode=RouteMode.LOCAL_ONLY
                )
                result = service.generate(request)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # EN50EN
        threads = [
            threading.Thread(target=make_request, args=(i,))
            for i in range(50)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # EN
        assert len(errors) == 0, f"EN: {errors}"
        assert len(results) == 50
        
        # EN
        for result in results:
            assert result.success is True

    def test_error_handling_local_failure_soft_fail(self, service, mock_clients):
        """EN"""
        # EN
        local_instance = mock_clients["llama"].return_value
        local_instance.generate.side_effect = Exception("Local model crashed")
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test question",
            route_mode=RouteMode.LOCAL_ONLY,
            soft_fail=True
        )
        
        result = service.generate(request)
        
        # EN
        assert result.success is False
        assert "Local model crashed" in result.error
        assert result.provider is None

    def test_error_handling_local_failure_with_fallback(self, service, mock_clients):
        """ENfallbackEN"""
        # EN
        local_instance = mock_clients["llama"].return_value
        local_instance.generate.side_effect = Exception("Local model crashed")
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test question",
            route_mode=RouteMode.HYBRID_AUTO
        )
        
        result = service.generate(request)
        
        # ENfallbackEN
        assert result.success is True
        assert result.provider in ["zhipu", "openai"]
        assert result.fallback_triggered is True

    def test_multi_tenant_isolation(self, service, mock_clients):
        """EN"""
        # EN
        tenants = ["tenant1", "tenant2", "tenant3"]
        
        for tenant in tenants:
            for i in range(5):
                request = DispatchRequest(
                    tenant_id=tenant,
                    question=f"Question {i}",
                    route_mode=RouteMode.LOCAL_ONLY
                )
                service.generate(request)
        
        # EN
        for tenant in tenants:
            stats = service.cost_tracker.get_tenant_usage(tenant)
            assert stats["total_requests"] == 5
            assert stats["tenant_id"] == tenant

    def test_latency_tracking(self, service, mock_clients):
        """EN"""
        import time
        
        # EN
        def slow_generate(*args, **kwargs):
            time.sleep(0.01)  # 10msEN
            return "Response"
        
        local_instance = mock_clients["llama"].return_value
        local_instance.generate.side_effect = slow_generate
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test",
            route_mode=RouteMode.LOCAL_ONLY
        )
        
        result = service.generate(request)
        
        # EN
        assert result.latency_ms > 0
        assert result.latency_ms < 100  # EN100ms

    def test_usage_tracking(self, service, mock_clients):
        """EN"""
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test question",
            route_mode=RouteMode.LOCAL_ONLY
        )
        
        result = service.generate(request)
        
        # EN
        assert result.usage.prompt_tokens >= 0
        assert result.usage.completion_tokens >= 0
        assert result.usage.total_tokens > 0

    @pytest.mark.parametrize("route_mode,expected_provider", [
        (RouteMode.LOCAL_ONLY, "llama_cpp"),
        (RouteMode.CLOUD_ONLY, ["zhipu", "openai"]),
        (RouteMode.HYBRID_AUTO, "llama_cpp"),  # EN
    ])
    def test_route_modes_integration(self, service, mock_clients, route_mode, expected_provider):
        """EN"""
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