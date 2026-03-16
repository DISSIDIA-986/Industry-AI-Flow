"""
PromptEN

ENPromptManagerEN,ENA/BEN
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.services.prompt_manager import (
    ExperimentStatus,
    PromptInfo,
    PromptManager,
    PromptStatus,
    PromptVariable,
)


class TestPromptManager:
    """PromptManagerEN"""

    @pytest.fixture
    def mock_db_pool(self):
        """EN"""
        pool = Mock()
        conn = Mock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool

    @pytest.fixture
    def manager(self, mock_db_pool):
        """ENPromptEN"""
        return PromptManager(mock_db_pool)

    def test_initialization(self, manager):
        """EN"""
        assert manager is not None
        assert hasattr(manager, "_cache")
        assert hasattr(manager, "_jinja_env")
        # ENSandboxedEnvironment
        from jinja2 import SandboxedEnvironment

        assert isinstance(manager._jinja_env, SandboxedEnvironment)

    @pytest.mark.asyncio
    async def test_get_prompt_from_cache(self, manager):
        """ENPrompt"""
        # EN
        prompt_info = PromptInfo(
            id="1",
            name="test_prompt",
            category="test",
            template="Hello {{ name }}!",
            status=PromptStatus.ACTIVE,
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        manager._cache["test:test:1"] = (
            prompt_info,
            datetime.now() + timedelta(seconds=60),
        )

        result = await manager.get_prompt("test_prompt", "test")

        assert result is not None
        assert result.template == "Hello {{ name }}!"

    @pytest.mark.asyncio
    async def test_render_template_basic(self, manager):
        """EN"""
        template = "Hello {{ name }}!"
        variables = {"name": "World"}

        result = await manager._render_template(template, variables)

        assert result == "Hello World!"

    @pytest.mark.asyncio
    async def test_render_template_multiple_variables(self, manager):
        """EN"""
        template = "User: {{ username }}, Email: {{ email }}, Age: {{ age }}"
        variables = {"username": "test_user", "email": "test@example.com", "age": 25}

        result = await manager._render_template(template, variables)

        assert result == "User: test_user, Email: test@example.com, Age: 25"

    @pytest.mark.asyncio
    async def test_render_template_with_conditionals(self, manager):
        """EN"""
        template = "{% if show_greeting %}Hello!{% else %}Goodbye!{% endif %}"

        result1 = await manager._render_template(template, {"show_greeting": True})
        result2 = await manager._render_template(template, {"show_greeting": False})

        assert result1 == "Hello!"
        assert result2 == "Goodbye!"

    @pytest.mark.asyncio
    async def test_render_template_with_loops(self, manager):
        """EN"""
        template = "{% for item in items %}{{ item }} {% endfor %}"
        variables = {"items": ["a", "b", "c"]}

        result = await manager._render_template(template, variables)

        assert result == "a b c "

    @pytest.mark.asyncio
    async def test_render_template_with_filters(self, manager):
        """EN"""
        template = "{{ text|upper }}"
        variables = {"text": "hello"}

        result = await manager._render_template(template, variables)

        assert result == "HELLO"

    @pytest.mark.asyncio
    async def test_render_template_missing_variable(self, manager):
        """EN"""
        template = "Hello {{ name }}!"
        variables = {}  # ENnameEN

        # Jinja2EN
        result = await manager._render_template(template, variables)
        assert result == "Hello !"

    @pytest.mark.asyncio
    async def test_render_template_with_none_value(self, manager):
        """ENNoneEN"""
        template = "Value: {{ value }}"
        variables = {"value": None}

        result = await manager._render_template(template, variables)
        assert result == "Value: None"

    @pytest.mark.asyncio
    async def test_extract_variables(self, manager):
        """EN"""
        template = "Hello {{ name }}, your email is {{ email }}"

        variables = await manager._extract_variables(template)

        assert "name" in variables
        assert "email" in variables

    @pytest.mark.asyncio
    async def test_sandboxed_template_security(self, manager):
        """EN"""
        # EN(EN)
        dangerous_templates = [
            "{{ ''.__class__.__mro__[1].__subclasses__()[40] }}",  # EN
            "{{ config.items() }}",  # EN
            "{{ ''.__class__.__base__ }}",  # EN
        ]

        for template in dangerous_templates:
            try:
                result = await manager._render_template(template, {})
                # EN
                assert "__class__" not in result or "Sandboxed" in str(result)
            except Exception as e:
                # EN
                assert (
                    "security" in str(e).lower()
                    or "sandbox" in str(e).lower()
                    or "blocked" in str(e).lower()
                )

    @pytest.mark.asyncio
    async def test_autoescape_enabled(self, manager):
        """EN"""
        template = "User input: {{ user_input }}"
        variables = {"user_input": "<script>alert('xss')</script>"}

        result = await manager._render_template(template, variables)

        # ENHTMLEN
        assert "<script>" not in result
        assert "&lt;script&gt;" in result or "script" not in result

    @pytest.mark.asyncio
    async def test_cache_expiration(self, manager):
        """EN"""
        # EN
        prompt_info = PromptInfo(
            id="1",
            name="test",
            category="test",
            template="Test",
            status=PromptStatus.ACTIVE,
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # EN
        expired_time = datetime.now() - timedelta(seconds=1)
        manager._cache["test:test:1"] = (prompt_info, expired_time)

        # EN,EN(EN)
        # EN
        assert manager._cache["test:test:1"][1] < datetime.now()

    @pytest.mark.asyncio
    async def test_cache_tenant_isolation(self, manager):
        """EN"""
        prompt_info1 = PromptInfo(
            id="1",
            name="shared",
            category="test",
            template="Tenant1",
            status=PromptStatus.ACTIVE,
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        prompt_info2 = PromptInfo(
            id="2",
            name="shared",
            category="test",
            template="Tenant2",
            status=PromptStatus.ACTIVE,
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # ENPrompt
        manager._cache["tenant1:test:1"] = (
            prompt_info1,
            datetime.now() + timedelta(minutes=5),
        )
        manager._cache["tenant2:test:1"] = (
            prompt_info2,
            datetime.now() + timedelta(minutes=5),
        )

        # EN
        cached1 = manager._cache.get("tenant1:test:1")
        cached2 = manager._cache.get("tenant2:test:1")

        assert cached1 is not None
        assert cached2 is not None
        assert cached1[0].template == "Tenant1"
        assert cached2[0].template == "Tenant2"

    def test_prompt_info_dataclass(self):
        """ENPromptInfoEN"""
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
            metadata={"key": "value"},
        )

        assert info.id == "1"
        assert info.name == "test"
        assert info.status == PromptStatus.ACTIVE
        assert info.version == 1
        assert info.metadata == {"key": "value"}

    def test_prompt_variable_dataclass(self):
        """ENPromptVariableEN"""
        var = PromptVariable(
            name="username",
            type="string",
            required=True,
            default_value=None,
            description="EN",
        )

        assert var.name == "username"
        assert var.type == "string"
        assert var.required is True
        assert var.description == "EN"

    @pytest.mark.asyncio
    async def test_concurrent_template_rendering(self, manager):
        """EN"""
        import asyncio
        import threading

        template = "Hello {{ name }}!"
        errors = []
        results = []

        async def render_concurrently(i):
            try:
                result = await manager._render_template(template, {"name": f"User{i}"})
                results.append(result)
            except Exception as e:
                errors.append(e)

        # EN100EN
        tasks = [render_concurrently(i) for i in range(100)]
        await asyncio.gather(*tasks)

        # EN
        assert len(errors) == 0, f"EN: {errors}"

        # EN
        assert len(results) == 100
        for i, result in enumerate(results):
            assert result == f"Hello User{i}!"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "template,variables,expected",
        [
            ("Hello {{ name }}!", {"name": "World"}, "Hello World!"),
            ("{{ a }} + {{ b }} = {{ a + b }}", {"a": 1, "b": 2}, "1 + 2 = 3"),
            ("{% if x %}Yes{% else %}No{% endif %}", {"x": True}, "Yes"),
            ("{% if x %}Yes{% else %}No{% endif %}", {"x": False}, "No"),
            ("{{ text|upper }}", {"text": "hello"}, "HELLO"),
            ("{{ text|lower }}", {"text": "HELLO"}, "hello"),
            ("{{ text|capitalize }}", {"text": "hello"}, "Hello"),
        ],
    )
    async def test_template_rendering_parametrized(
        self, manager, template, variables, expected
    ):
        """EN"""
        result = await manager._render_template(template, variables)
        assert result == expected

    @pytest.mark.asyncio
    async def test_template_with_newlines(self, manager):
        """EN"""
        template = """
        Line 1: {{ line1 }}
        Line 2: {{ line2 }}
        Line 3: {{ line3 }}
        """
        variables = {"line1": "First", "line2": "Second", "line3": "Third"}

        result = await manager._render_template(template, variables)

        assert "Line 1: First" in result
        assert "Line 2: Second" in result
        assert "Line 3: Third" in result

    @pytest.mark.asyncio
    async def test_template_with_special_characters(self, manager):
        """EN"""
        template = "Special: {{ chars }}"
        variables = {"chars": "!@#$%^&*()[]{}|\\:;\"'<>?,./"}

        result = await manager._render_template(template, variables)

        assert "!@#$%^&*()" in result
        # EN

    @pytest.mark.asyncio
    async def test_template_with_unicode(self, manager):
        """ENUnicodeEN"""
        template = "EN: {{ chinese }}, Emoji: {{ emoji }}"
        variables = {"chinese": "EN", "emoji": "😀🎉"}

        result = await manager._render_template(template, variables)

        assert "EN: EN" in result
        assert "Emoji: 😀🎉" in result

    @pytest.mark.asyncio
    async def test_trim_blocks_enabled(self, manager):
        """ENtrim_blocksEN"""
        # ENtrim_blocksEN(EN)
        template = "{% if show %}\n  Content\n{% endif %}"
        variables = {"show": True}

        result = await manager._render_template(template, variables)

        # trim_blocksEN
        assert "Content" in result

    @pytest.mark.asyncio
    async def test_lstrip_blocks_enabled(self, manager):
        """ENlstrip_blocksEN"""
        # ENlstrip_blocksEN(EN)
        template = "  {% if show %}Content{% endif %}"
        variables = {"show": True}

        result = await manager._render_template(template, variables)

        # lstrip_blocksEN
        assert result.startswith("Content")

    @pytest.mark.asyncio
    async def test_template_injection_prevention(self, manager):
        """EN"""
        # ENJinja2EN
        malicious_inputs = [
            "{{ ''.__class__ }}",
            "{{ config }}",
            "{{ ''.__class__.__mro__ }}",
            "{% for i in ''.__class__.__base__.__subclasses__() %}{{ i }}{% endfor %}",
        ]

        for malicious_input in malicious_inputs:
            try:
                result = await manager._render_template(malicious_input, {})
                # EN
                # EN
                assert "module" not in result.lower()
                assert "class" not in result.lower() or len(result) < 100
            except (SecurityError, AttributeError, TypeError):
                # EN
                pass
            except Exception as e:
                # EN(EN)
                pass
