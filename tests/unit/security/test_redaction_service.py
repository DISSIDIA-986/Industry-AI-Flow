"""
脱敏服务单元测试

测试RedactionService的敏感信息识别和脱敏功能
包含异常处理和降级策略测试
"""

import pytest
from unittest.mock import patch

from backend.services.security.redaction_service import RedactionResult, RedactionService


class _RaisingPattern:
    def __init__(self, message: str):
        self.message = message

    def subn(self, repl, text):
        del repl, text
        raise Exception(self.message)


class TestRedactionService:
    """RedactionService单元测试类"""

    @pytest.fixture
    def service(self):
        """创建脱敏服务实例"""
        return RedactionService()

    def test_redact_empty_text(self, service):
        """测试空文本脱敏"""
        result = service.redact("")
        assert result.text == ""
        assert result.hit_count == 0
        assert result.categories == []
        assert result.replacements == {}

    def test_redact_no_sensitive_info(self, service):
        """测试无敏感信息文本"""
        text = "This is a normal text without any sensitive information."
        result = service.redact(text)
        
        assert result.text == text
        assert result.hit_count == 0
        assert result.categories == []
        assert result.replacements == {}

    def test_redact_email(self, service):
        """测试邮箱脱敏"""
        text = "Contact me at test@example.com for more information."
        result = service.redact(text)
        
        assert "test@example.com" not in result.text
        assert "<REDACTED_EMAIL>" in result.text
        assert result.hit_count == 1
        assert "email" in result.categories
        assert result.replacements["email"] == 1

    def test_redact_multiple_emails(self, service):
        """测试多个邮箱脱敏"""
        text = "Emails: alice@company.com, bob@example.org, charlie@test.net"
        result = service.redact(text)
        
        assert "alice@company.com" not in result.text
        assert "bob@example.org" not in result.text
        assert "charlie@test.net" not in result.text
        assert result.text.count("<REDACTED_EMAIL>") == 3
        assert result.hit_count == 3
        assert result.replacements["email"] == 3

    def test_redact_chinese_phone(self, service):
        """测试中国手机号脱敏"""
        test_cases = [
            "13800138000",
            "+8613800138000",
            "+86-13800138000",
            "86 13800138000",
        ]
        
        for phone in test_cases:
            text = f"My phone is {phone}"
            result = service.redact(text)
            
            assert phone not in result.text
            assert "<REDACTED_PHONE_CN>" in result.text
            assert result.hit_count == 1
            assert "phone_cn" in result.categories

    def test_redact_us_phone(self, service):
        """测试美国手机号脱敏"""
        test_cases = [
            "123-456-7890",
            "(123) 456-7890",
            "123.456.7890",
            "+1-123-456-7890",
        ]
        
        for phone in test_cases:
            text = f"Call me at {phone}"
            result = service.redact(text)
            
            assert phone not in result.text
            assert "<REDACTED_PHONE_US>" in result.text
            assert result.hit_count == 1
            assert "phone_us" in result.categories

    def test_redact_id_like_numbers(self, service):
        """测试身份证号类数字脱敏"""
        test_cases = [
            "123456789012345",  # 15位
            "123456789012345678",  # 18位
            "12345678901234567X",  # 18位带X
            "12345678901234567x",  # 18位带x
        ]
        
        for id_num in test_cases:
            text = f"ID: {id_num}"
            result = service.redact(text)
            
            assert id_num not in result.text
            assert "<REDACTED_ID_LIKE>" in result.text
            assert result.hit_count == 1
            assert "id_like" in result.categories

    def test_redact_ipv4(self, service):
        """测试IPv4地址脱敏"""
        test_cases = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
        ]
        
        for ip in test_cases:
            text = f"Server IP: {ip}"
            result = service.redact(text)
            
            assert ip not in result.text
            assert "<REDACTED_IPV4>" in result.text
            assert result.hit_count == 1
            assert "ipv4" in result.categories

    def test_redact_multiple_categories(self, service):
        """测试多种敏感信息同时脱敏"""
        text = """
        User information:
        Email: user@example.com
        Phone: 13800138000
        IP: 192.168.1.100
        ID: 123456789012345678
        """
        
        result = service.redact(text)
        
        # 验证所有敏感信息都被脱敏
        assert "user@example.com" not in result.text
        assert "13800138000" not in result.text
        assert "192.168.1.100" not in result.text
        assert "123456789012345678" not in result.text
        
        # 验证替换标记
        assert "<REDACTED_EMAIL>" in result.text
        assert "<REDACTED_PHONE_CN>" in result.text
        assert "<REDACTED_IPV4>" in result.text
        assert "<REDACTED_ID_LIKE>" in result.text
        
        # 验证统计
        assert result.hit_count == 4
        assert len(result.categories) == 4
        assert len(result.replacements) == 4

    def test_redact_partial_matches(self, service):
        """测试部分匹配（不应脱敏）"""
        # 这些不应该被匹配为敏感信息
        test_cases = [
            "123",  # 太短
            "12345678901234",  # 14位，不够15位
            "test@example",  # 不完整的邮箱
            "192.168.1",  # 不完整的IP
            "1380013800",  # 10位，不是手机号
        ]
        
        for text in test_cases:
            result = service.redact(text)
            assert result.text == text  # 应该保持不变
            assert result.hit_count == 0

    def test_redact_with_special_characters(self, service):
        """测试特殊字符文本脱敏"""
        text = 'Email: "test@example.com" <test@example.com> (test@example.com)'
        result = service.redact(text)
        
        # 邮箱应该被脱敏，但特殊字符应该保留
        assert "test@example.com" not in result.text
        assert result.text.count("<REDACTED_EMAIL>") == 3
        assert '"' in result.text
        assert '<' in result.text
        assert '>' in result.text
        assert '(' in result.text
        assert ')' in result.text

    def test_redact_unicode_text(self, service):
        """测试Unicode文本脱敏"""
        text = "中文邮箱：测试@例子.com，手机号：13800138000"
        result = service.redact(text)
        
        assert "测试@例子.com" not in result.text
        assert "13800138000" not in result.text
        assert "<REDACTED_EMAIL>" in result.text
        assert "<REDACTED_PHONE_CN>" in result.text
        assert "中文邮箱：" in result.text
        assert "手机号：" in result.text

    def test_redact_large_text(self, service):
        """测试大文本脱敏性能"""
        # 创建包含多个敏感信息的大文本
        base_text = "Email: user{id}@example.com, Phone: 1380013{id:04d}"
        large_text = "\n".join([base_text.format(id=i) for i in range(100)])
        
        result = service.redact(large_text)
        
        # 验证所有敏感信息都被脱敏
        assert result.hit_count == 200  # 100个邮箱 + 100个手机号
        assert result.text.count("<REDACTED_EMAIL>") == 100
        assert result.text.count("<REDACTED_PHONE_CN>") == 100

    def test_redact_exception_handling(self, service):
        """测试异常处理降级策略"""
        # 模拟正则表达式抛出异常
        with patch.dict(
            service.PATTERNS,
            {"email": _RaisingPattern("Pattern error")},
            clear=False,
        ):
            text = "Email: test@example.com"
            result = service.redact(text)
            
            # 降级策略：异常时返回原始文本
            assert result.text == text
            assert result.hit_count == 0
            assert result.categories == []
            assert result.replacements == {}

    def test_redact_multiple_exceptions(self, service):
        """测试多个异常情况"""
        # 模拟多个模式都抛出异常
        with patch.dict(
            service.PATTERNS,
            {
                "email": _RaisingPattern("Email error"),
                "phone_cn": _RaisingPattern("Phone error"),
            },
            clear=False,
        ):
            text = "Email: test@example.com, Phone: 13800138000"
            result = service.redact(text)

            # 降级策略：异常时返回原始文本
            assert result.text == text
            assert result.hit_count == 0

    def test_redact_result_dataclass(self):
        """测试RedactionResult数据类"""
        result = RedactionResult(
            text="脱敏后的文本",
            hit_count=2,
            categories=["email", "phone"],
            replacements={"email": 1, "phone": 1}
        )
        
        assert result.text == "脱敏后的文本"
        assert result.hit_count == 2
        assert result.categories == ["email", "phone"]
        assert result.replacements == {"email": 1, "phone": 1}

    @pytest.mark.parametrize("text,expected_hits", [
        ("", 0),
        ("test@example.com", 1),
        ("test@example.com 13800138000", 2),
        ("test@example.com 13800138000 192.168.1.1", 3),
        ("normal text", 0),
        ("123456789012345678", 1),
        ("+1-123-456-7890", 1),
    ])
    def test_redact_parametrized(self, service, text, expected_hits):
        """参数化测试不同文本"""
        result = service.redact(text)
        assert result.hit_count == expected_hits

    def test_redact_pattern_coverage(self, service):
        """测试模式覆盖完整性"""
        # 验证所有模式都被测试覆盖
        test_cases = {
            "email": "test@example.com",
            "phone_cn": "13800138000",
            "phone_us": "123-456-7890",
            "id_like": "123456789012345678",
            "ipv4": "192.168.1.1",
        }
        
        for category, test_text in test_cases.items():
            result = service.redact(test_text)
            assert result.hit_count == 1
            assert category in result.categories
            assert f"<REDACTED_{category.upper()}>" in result.text
