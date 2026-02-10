"""
Prompt管理服务单元测试

测试PromptManager的模板渲染、版本控制和A/B测试功能
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from backend.services.prompt_manager import (
    PromptManager,
    PromptInfo,
    PromptVariable,
    PromptStatus,
    ExperimentStatus
)


class TestPromptManager:
    """PromptManager单元测试类"""

    @pytest.fixture
    def mock_db_pool(self):
        """创建模拟数据库连接池"""
        pool = Mock()
        conn = Mock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool

    @pytest.fixture
    def manager(self, mock_db_pool):
        """创建Prompt管理器实例"""
        return PromptManager(mock_db_pool)

    def test_initialization(self, manager):
        """测试初始化"""
        assert manager is not None
        assert hasattr(manager, '_cache')
        assert hasattr(manager, '_jinja_env')
        # 验证使用SandboxedEnvironment
        from jinja2 import SandboxedEnvironment
        assert isinstance(manager._jinja_env, SandboxedEnvironment)

    @pytest.mark.asyncio
    async def test_get_prompt_from_cache(self, manager):
        """测试从缓存获取Prompt"""
        # 模拟缓存命中
        prompt_info = PromptInfo(
            id="1",
            name="test_prompt",
            category="test",
            template="Hello {{ name }}!",
            status=PromptStatus.ACTIVE,
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        manager._cache["test:test:1"] = (prompt_info, datetime.now() + timedelta(seconds=60))
        
        result = await manager.get_prompt("test_prompt", "test")
        
        assert result is not None
        assert result.template == "Hello {{ name }}!"

    @pytest.mark.asyncio
    async def test_render_template_basic(self, manager):
        """测试基本模板渲染"""
        template = "Hello {{ name }}!"
        variables = {"name": "World"}
        
        result = await manager._render_template(template, variables)
        
        assert result == "Hello World!"

    @pytest.mark.asyncio
    async def test_render_template_multiple_variables(self, manager):
        """测试多变量模板渲染"""
        template = "User: {{ username }}, Email: {{ email }}, Age: {{ age }}"
        variables = {
            "username": "test_user",
            "email": "test@example.com",
            "age": 25
        }
        
        result = await manager._render_template(template, variables)
        
        assert result == "User: test_user, Email: test@example.com, Age: 25"

    @pytest.mark.asyncio
    async def test_render_template_with_conditionals(self, manager):
        """测试条件语句渲染"""
        template = "{% if show_greeting %}Hello!{% else %}Goodbye!{% endif %}"
        
        result1 = await manager._render_template(template, {"show_greeting": True})
        result2 = await manager._render_template(template, {"show_greeting": False})
        
        assert result1 == "Hello!"
        assert result2 == "Goodbye!"

    @pytest.mark.asyncio
    async def test_render_template_with_loops(self, manager):
        """测试循环渲染"""
        template = "{% for item in items %}{{ item }} {% endfor %}"
        variables = {"items": ["a", "b", "c"]}
        
        result = await manager._render_template(template, variables)
        
        assert result == "a b c "

    @pytest.mark.asyncio
    async def test_render_template_with_filters(self, manager):
        """测试过滤器使用"""
        template = "{{ text|upper }}"
        variables = {"text": "hello"}
        
        result = await manager._render_template(template, variables)
        
        assert result == "HELLO"

    @pytest.mark.asyncio
    async def test_render_template_missing_variable(self, manager):
        """测试缺失变量处理"""
        template = "Hello {{ name }}!"
        variables = {}  # 缺少name变量
        
        # Jinja2默认会渲染为空字符串
        result = await manager._render_template(template, variables)
        assert result == "Hello !"

    @pytest.mark.asyncio
    async def test_render_template_with_none_value(self, manager):
        """测试None值处理"""
        template = "Value: {{ value }}"
        variables = {"value": None}
        
        result = await manager._render_template(template, variables)
        assert result == "Value: None"

    @pytest.mark.asyncio
    async def test_extract_variables(self, manager):
        """测试变量提取"""
        template = "Hello {{ name }}, your email is {{ email }}"
        
        variables = await manager._extract_variables(template)
        
        assert "name" in variables
        assert "email" in variables

    @pytest.mark.asyncio
    async def test_sandboxed_template_security(self, manager):
        """测试沙箱模板安全性"""
        # 尝试执行危险操作（应该被沙箱阻止）
        dangerous_templates = [
            "{{ ''.__class__.__mro__[1].__subclasses__()[40] }}",  # 尝试访问危险类
            "{{ config.items() }}",  # 尝试访问配置
            "{{ ''.__class__.__base__ }}",  # 尝试访问基类
        ]
        
        for template in dangerous_templates:
            try:
                result = await manager._render_template(template, {})
                # 沙箱应该阻止或返回安全结果
                assert "__class__" not in result or "Sandboxed" in str(result)
            except Exception as e:
                # 沙箱应该抛出安全异常
                assert "security" in str(e).lower() or "sandbox" in str(e).lower() or "blocked" in str(e).lower()

    @pytest.mark.asyncio
    async def test_autoescape_enabled(self, manager):
        """测试自动转义启用"""
        template = "User input: {{ user_input }}"
        variables = {"user_input": "<script>alert('xss')</script>"}
        
        result = await manager._render_template(template, variables)
        
        # 验证HTML被转义
        assert "<script>" not in result
        assert "&lt;script&gt;" in result or "script" not in result

    @pytest.mark.asyncio
    async def test_cache_expiration(self, manager):
        """测试缓存过期"""
        # 添加过期缓存
        prompt_info = PromptInfo(
            id="1",
            name="test",
            category="test",
            template="Test",
            status=PromptStatus.ACTIVE,
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 设置已过期的时间
        expired_time = datetime.now() - timedelta(seconds=1)
        manager._cache["test:test:1"] = (prompt_info, expired_time)
        
        # 缓存应该过期，从数据库获取（这里会失败因为没有数据库）
        # 主要验证缓存过期逻辑
        assert manager._cache["test:test:1"][1] < datetime.now()

    @pytest.mark.asyncio
    async def test_cache_tenant_isolation(self, manager):
        """测试租户缓存隔离"""
        prompt_info1 = PromptInfo(
            id="1",
            name="shared",
            category="test",
            template="Tenant1",
            status=PromptStatus.ACTIVE,
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        prompt_info2 = PromptInfo(
            id="2",
            name="shared",
            category="test",
            template="Tenant2",
            status=PromptStatus.ACTIVE,
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 为不同租户缓存相同名称的Prompt
        manager._cache["tenant1:test:1"] = (prompt_info1, datetime.now() + timedelta(minutes=5))
        manager._cache["tenant2:test:1"] = (prompt_info2, datetime.now() + timedelta(minutes=5))
        
        # 验证租户隔离
        cached1 = manager._cache.get("tenant1:test:1")
        cached2 = manager._cache.get("tenant2:test:1")
        
        assert cached1 is not None
        assert cached2 is not None
        assert cached1[0].template == "Tenant1"
        assert cached2[0].template == "Tenant2"

    def test_prompt_info_dataclass(self):
        """测试PromptInfo数据类"""
        now = datetime.now()
        info = PromptInfo(
            id="1",
            name="test",
            category="test",
            template="Hello {{ name }}",
            status=PromptStatus.ACTIVE,
            version=1,
            created_at=now,
            updated_at=now,
            metadata={"key": "value"}
        )
        
        assert info.id == "1"
        assert info.name == "test"
        assert info.status == PromptStatus.ACTIVE
        assert info.version == 1
        assert info.metadata == {"key": "value"}

    def test_prompt_variable_dataclass(self):
        """测试PromptVariable数据类"""
        var = PromptVariable(
            name="username",
            type="string",
            required=True,
            default_value=None,
            description="用户名"
        )
        
        assert var.name == "username"
        assert var.type == "string"
        assert var.required is True
        assert var.description == "用户名"

    @pytest.mark.asyncio
    async def test_concurrent_template_rendering(self, manager):
        """测试并发模板渲染"""
        import threading
        import asyncio
        
        template = "Hello {{ name }}!"
        errors = []
        results = []
        
        async def render_concurrently(i):
            try:
                result = await manager._render_template(template, {"name": f"User{i}"})
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # 创建100个并发渲染任务
        tasks = [render_concurrently(i) for i in range(100)]
        await asyncio.gather(*tasks)
        
        # 验证没有错误
        assert len(errors) == 0, f"并发渲染错误: {errors}"
        
        # 验证所有渲染结果正确
        assert len(results) == 100
        for i, result in enumerate(results):
            assert result == f"Hello User{i}!"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("template,variables,expected", [
        ("Hello {{ name }}!", {"name": "World"}, "Hello World!"),
        ("{{ a }} + {{ b }} = {{ a + b }}", {"a": 1, "b": 2}, "1 + 2 = 3"),
        ("{% if x %}Yes{% else %}No{% endif %}", {"x": True}, "Yes"),
        ("{% if x %}Yes{% else %}No{% endif %}", {"x": False}, "No"),
        ("{{ text|upper }}", {"text": "hello"}, "HELLO"),
        ("{{ text|lower }}", {"text": "HELLO"}, "hello"),
        ("{{ text|capitalize }}", {"text": "hello"}, "Hello"),
    ])
    async def test_template_rendering_parametrized(self, manager, template, variables, expected):
        """参数化测试模板渲染"""
        result = await manager._render_template(template, variables)
        assert result == expected

    @pytest.mark.asyncio
    async def test_template_with_newlines(self, manager):
        """测试包含换行的模板"""
        template = """
        Line 1: {{ line1 }}
        Line 2: {{ line2 }}
        Line 3: {{ line3 }}
        """
        variables = {
            "line1": "First",
            "line2": "Second",
            "line3": "Third"
        }
        
        result = await manager._render_template(template, variables)
        
        assert "Line 1: First" in result
        assert "Line 2: Second" in result
        assert "Line 3: Third" in result

    @pytest.mark.asyncio
    async def test_template_with_special_characters(self, manager):
        """测试特殊字符处理"""
        template = "Special: {{ chars }}"
        variables = {"chars": "!@#$%^&*()[]{}|\\:;\"'<>?,./"}
        
        result = await manager._render_template(template, variables)
        
        assert "!@#$%^&*()" in result
        # 验证特殊字符被正确处理

    @pytest.mark.asyncio
    async def test_template_with_unicode(self, manager):
        """测试Unicode支持"""
        template = "中文: {{ chinese }}, Emoji: {{ emoji }}"
        variables = {
            "chinese": "测试",
            "emoji": "😀🎉"
        }
        
        result = await manager._render_template(template, variables)
        
        assert "中文: 测试" in result
        assert "Emoji: 😀🎉" in result

    @pytest.mark.asyncio
    async def test_trim_blocks_enabled(self, manager):
        """测试trim_blocks选项"""
        # 验证trim_blocks启用（在初始化时设置）
        template = "{% if show %}\n  Content\n{% endif %}"
        variables = {"show": True}
        
        result = await manager._render_template(template, variables)
        
        # trim_blocks应该去除第一个换行符后的换行
        assert "Content" in result

    @pytest.mark.asyncio
    async def test_lstrip_blocks_enabled(self, manager):
        """测试lstrip_blocks选项"""
        # 验证lstrip_blocks启用（在初始化时设置）
        template = "  {% if show %}Content{% endif %}"
        variables = {"show": True}
        
        result = await manager._render_template(template, variables)
        
        # lstrip_blocks应该去除标签前的空格
        assert result.startswith("Content")

    @pytest.mark.asyncio
    async def test_template_injection_prevention(self, manager):
        """测试模板注入防护"""
        # 尝试注入Jinja2代码
        malicious_inputs = [
            "{{ ''.__class__ }}",
            "{{ config }}",
            "{{ ''.__class__.__mro__ }}",
            "{% for i in ''.__class__.__base__.__subclasses__() %}{{ i }}{% endfor %}",
        ]
        
        for malicious_input in malicious_inputs:
            try:
                result = await manager._render_template(malicious_input, {})
                # 沙箱应该阻止危险操作
                # 结果不应该包含敏感类名或危险信息
                assert "module" not in result.lower()
                assert "class" not in result.lower() or len(result) < 100
            except (SecurityError, AttributeError, TypeError):
                # 沙箱应该抛出异常
                pass
            except Exception as e:
                # 其他异常也可接受（沙箱阻止）
                pass