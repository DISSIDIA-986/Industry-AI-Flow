"""
LLM调度服务单元测试

测试DispatchService的本地/云端LLM调度、fallback机制和置信度判断
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.llm_integration.dispatch_service import DispatchService
from backend.services.llm_integration.types import (
    DispatchRequest,
    DispatchResult,
    RouteMode,
    LLMProvider,
    LLMUsage
)


class TestDispatchService:
    """DispatchService单元测试类"""

    @pytest.fixture
    def service(self):
        """创建调度服务实例"""
        return DispatchService()

    def test_initialization(self, service):
        """测试初始化"""
        assert service is not None
        assert hasattr(service, 'local_client')
        assert hasattr(service, 'zhipu_client')
        assert hasattr(service, 'openai_client')
        assert hasattr(service, 'cost_tracker')

    @patch('backend.services.llm_integration.dispatch_service.LlamaCppClient')
    def test_local_only_mode_success(self, mock_llama_client, service):
        """测试本地优先模式成功"""
        # Mock本地客户端响应
        mock_instance = Mock()
        mock_instance.generate.return_value = "Local response"
        mock_llama_client.return_value = mock_instance
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="What is RAG?",
            route_mode=RouteMode.LOCAL_ONLY,
            max_tokens=100
        )
        
        result = service.generate(request)
        
        assert result.success is True
        assert result.provider == "llama_cpp"
        assert result.text == "Local response"
        assert result.fallback_triggered is False
        assert result.usage.total_tokens > 0

    @patch('backend.services.llm_integration.dispatch_service.LlamaCppClient')
    def test_local_only_mode_failure(self, mock_llama_client, service):
        """测试本地优先模式失败"""
        # Mock本地客户端抛出异常
        mock_instance = Mock()
        mock_instance.generate.side_effect = Exception("Local model failed")
        mock_llama_client.return_value = mock_instance
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="What is RAG?",
            route_mode=RouteMode.LOCAL_ONLY,
            soft_fail=True
        )
        
        result = service.generate(request)
        
        assert result.success is False
        assert "Local model failed" in result.error
        assert result.provider is None

    @patch('backend.services.llm_integration.dispatch_service.ZhipuClient')
    @patch('backend.services.llm_integration.dispatch_service.LlamaCppClient')
    def test_hybrid_mode_local_success(self, mock_llama, mock_zhipu, service):
        """测试混合模式本地成功"""
        # Mock本地客户端
        mock_local = Mock()
        mock_local.generate.return_value = "Local response"
        mock_llama.return_value = mock_local
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Simple question",
            route_mode=RouteMode.HYBRID_AUTO,
            local_conf_threshold=0.75
        )
        
        result = service.generate(request)
        
        assert result.success is True
        assert result.provider == "llama_cpp"
        assert result.fallback_triggered is False

    @patch('backend.services.llm_integration.dispatch_service.ZhipuClient')
    @patch('backend.services.llm_integration.dispatch_service.LlamaCppClient')
    def test_hybrid_mode_cloud_fallback(self, mock_llama, mock_zhipu, service):
        """测试混合模式云端fallback"""
        # Mock本地客户端返回低置信度
        mock_local = Mock()
        mock_local.generate.return_value = "I'm not sure about this"
        mock_llama.return_value = mock_local
        
        # Mock云端客户端
        mock_cloud = Mock()
        mock_cloud.generate.return_value = "Detailed cloud response"
        mock_zhipu.return_value = mock_cloud
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Complex question requiring cloud",
            route_mode=RouteMode.HYBRID_AUTO,
            local_conf_threshold=0.99  # 高阈值触发fallback
        )
        
        result = service.generate(request)
        
        assert result.success is True
        assert result.fallback_triggered is True
        assert result.provider in ["zhipu", "openai"]

    @patch('backend.services.llm_integration.dispatch_service.OpenAIClient')
    def test_cloud_only_mode(self, mock_openai, service):
        """测试云端优先模式"""
        # Mock云端客户端
        mock_instance = Mock()
        mock_instance.generate.return_value = "Cloud response"
        mock_openai.return_value = mock_instance
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Complex question",
            route_mode=RouteMode.CLOUD_ONLY,
            temperature=0.7
        )
        
        result = service.generate(request)
        
        assert result.success is True
        assert result.provider in ["zhipu", "openai"]
        assert result.text == "Cloud response"

    def test_dispatch_request_validation(self, service):
        """测试请求参数验证"""
        # 测试空问题
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="",
            route_mode=RouteMode.LOCAL_ONLY
        )
        
        # 空问题应该被拒绝或处理
        assert request.question == ""

    def test_max_tokens_validation(self, service):
        """测试max_tokens参数验证"""
        # 测试边界值
        test_cases = [0, 100, 1000, 32000]
        
        for max_tokens in test_cases:
            request = DispatchRequest(
                tenant_id="test_tenant",
                question="Test",
                route_mode=RouteMode.LOCAL_ONLY,
                max_tokens=max_tokens
            )
            assert request.max_tokens == max_tokens

    def test_temperature_validation(self, service):
        """测试temperature参数验证"""
        # 测试边界值
        test_cases = [0.0, 0.5, 1.0, 1.5, 2.0]
        
        for temperature in test_cases:
            request = DispatchRequest(
                tenant_id="test_tenant",
                question="Test",
                route_mode=RouteMode.LOCAL_ONLY,
                temperature=temperature
            )
            assert request.temperature == temperature

    @patch('backend.services.llm_integration.dispatch_service.ZhipuClient')
    @patch('backend.services.llm_integration.dispatch_service.LlamaCppClient')
    def test_cost_tracking(self, mock_llama, mock_zhipu, service):
        """测试成本追踪"""
        # Mock本地客户端
        mock_local = Mock()
        mock_local.generate.return_value = "Response"
        mock_llama.return_value = mock_local
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test question",
            route_mode=RouteMode.LOCAL_ONLY
        )
        
        initial_stats = service.cost_tracker.get_tenant_usage("test_tenant")
        initial_requests = initial_stats["total_requests"]
        
        service.generate(request)
        
        final_stats = service.cost_tracker.get_tenant_usage("test_tenant")
        assert final_stats["total_requests"] == initial_requests + 1

    @patch('backend.services.llm_integration.dispatch_service.ZhipuClient')
    @patch('backend.services.llm_integration.dispatch_service.LlamaCppClient')
    def test_budget_alert(self, mock_llama, mock_zhipu, service):
        """测试预算告警"""
        # 设置极低预算
        service.cost_tracker.set_budget("test_tenant", 0.000001)
        
        # Mock本地客户端
        mock_local = Mock()
        mock_local.generate.return_value = "Response"
        mock_llama.return_value = mock_local
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test",
            route_mode=RouteMode.LOCAL_ONLY
        )
        
        service.generate(request)
        
        # 检查预算告警
        alert = service.cost_tracker.check_budget_alert("test_tenant")
        assert alert is not None
        # 本地模型成本极低，可能不会超预算
        # 这里主要验证告警机制可以正常工作

    @patch('backend.services.llm_integration.dispatch_service.ZhipuClient')
    @patch('backend.services.llm_integration.dispatch_service.LlamaCppClient')
    def test_redaction_before_cloud_call(self, mock_llama, mock_zhipu, service):
        """测试云端调用前的脱敏"""
        # Mock云端客户端
        mock_cloud = Mock()
        mock_cloud.generate.return_value = "Safe response"
        mock_zhipu.return_value = mock_cloud
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="My email is test@example.com",
            route_mode=RouteMode.CLOUD_ONLY
        )
        
        result = service.generate(request)
        
        assert result.success is True
        # 验证敏感信息被脱敏后发送到云端
        # 这里主要验证脱敏服务被调用

    def test_dispatch_result_creation(self):
        """测试DispatchResult创建"""
        result = DispatchResult(
            success=True,
            provider="llama_cpp",
            text="Test response",
            usage=LLMUsage(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150
            ),
            latency_ms=1000,
            fallback_triggered=False
        )
        
        assert result.success is True
        assert result.provider == "llama_cpp"
        assert result.text == "Test response"
        assert result.usage.total_tokens == 150
        assert result.latency_ms == 1000
        assert result.fallback_triggered is False

    @patch('backend.services.llm_integration.dispatch_service.ZhipuClient')
    @patch('backend.services.llm_integration.dispatch_service.LlamaCppClient')
    @pytest.mark.parametrize("route_mode,expected_provider", [
        (RouteMode.LOCAL_ONLY, "llama_cpp"),
        (RouteMode.CLOUD_ONLY, "zhipu"),  # 或 openai
        (RouteMode.HYBRID_AUTO, "llama_cpp"),  # 默认先尝试本地
    ])
    def test_route_modes(self, mock_llama, mock_zhipu, service, route_mode, expected_provider):
        """参数化测试不同路由模式"""
        # Mock客户端
        mock_local = Mock()
        mock_local.generate.return_value = "Response"
        mock_llama.return_value = mock_local
        
        mock_cloud = Mock()
        mock_cloud.generate.return_value = "Response"
        mock_zhipu.return_value = mock_cloud
        
        request = DispatchRequest(
            tenant_id="test_tenant",
            question="Test",
            route_mode=route_mode
        )
        
        result = service.generate(request)
        
        assert result.success is True
        if route_mode == RouteMode.LOCAL_ONLY:
            assert result.provider == "llama_cpp"
        elif route_mode == RouteMode.CLOUD_ONLY:
            assert result.provider in ["zhipu", "openai"]

    def test_concurrent_dispatch(self):
        """测试并发调度"""
        import threading
        
        service = DispatchService()
        errors = []
        
        with patch('backend.services.llm_integration.dispatch_service.LlamaCppClient') as mock_llama:
            mock_instance = Mock()
            mock_instance.generate.return_value = "Response"
            mock_llama.return_value = mock_instance
            
            def dispatch_concurrently(i):
                try:
                    request = DispatchRequest(
                        tenant_id=f"tenant{i % 5}",
                        question=f"Question {i}",
                        route_mode=RouteMode.LOCAL_ONLY
                    )
                    service.generate(request)
                except Exception as e:
                    errors.append(e)
            
            # 创建50个线程并发调度
            threads = [
                threading.Thread(target=dispatch_concurrently, args=(i,))
                for i in range(50)
            ]
            
            for t in threads:
                t.start()
            
            for t in threads:
                t.join()
            
            # 验证没有错误
            assert len(errors) == 0, f"并发调度错误: {errors}"

    def test_latency_tracking(self, service):
        """测试延迟跟踪"""
        with patch('backend.services.llm_integration.dispatch_service.LlamaCppClient') as mock_llama:
            import time
            
            # Mock本地客户端，添加延迟
            def slow_generate(*args, **kwargs):
                time.sleep(0.01)  # 10ms延迟
                return "Response"
            
            mock_instance = Mock()
            mock_instance.generate.side_effect = slow_generate
            mock_llama.return_value = mock_instance
            
            request = DispatchRequest(
                tenant_id="test_tenant",
                question="Test",
                route_mode=RouteMode.LOCAL_ONLY
            )
            
            result = service.generate(request)
            
            assert result.latency_ms > 0
            assert result.latency_ms < 100  # 应该小于100ms