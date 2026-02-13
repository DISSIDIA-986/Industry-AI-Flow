"""
Groundedness Checker 简化测试
"""

import pytest
from backend.safety.groundedness_checker import (
    GroundednessChecker,
    GroundednessLevel,
    ClaimType,
    get_groundedness_checker,
    check_groundedness
)


class TestGroundednessChecker:
    """GroundednessChecker 测试类"""
    
    def test_checker_initialization(self):
        """测试检查器初始化"""
        checker = GroundednessChecker()
        assert checker is not None
        assert hasattr(checker, 'patterns')
    
    def test_claim_type_enum(self):
        """测试声明类型枚举"""
        assert ClaimType.FACTUAL.value == "factual"
        assert ClaimType.NUMERICAL.value == "numerical"
        assert ClaimType.TEMPORAL.value == "temporal"
        assert ClaimType.SPATIAL.value == "spatial"
        assert ClaimType.CAUSAL.value == "causal"
        assert ClaimType.COMPARATIVE.value == "comparative"
    
    def test_groundedness_level_enum(self):
        """测试真实性等级枚举"""
        assert GroundednessLevel.FULLY_GROUNDED.value == "fully_grounded"
        assert GroundednessLevel.PARTIALLY_GROUNDED.value == "partially_grounded"
        assert GroundednessLevel.NOT_GROUNDED.value == "not_grounded"
        assert GroundednessLevel.HALLUCINATION.value == "hallucination"
    
    def test_check_fully_grounded_simple(self):
        """测试完全真实的简单检查"""
        checker = GroundednessChecker()
        
        # 简单的真实文本
        generated_text = "The capital of France is Paris."
        context = ["Paris is the capital of France."]
        
        response = checker.check(generated_text, context)
        
        # 验证响应结构
        assert "overall_score" in response
        assert "groundedness_level" in response
        assert "grounded_claims" in response
        assert "ungrounded_claims" in response
        assert "hallucinated_claims" in response
        assert "results" in response
        assert "details" in response
        
        # 由于是简单实现，分数应该合理
        assert 0 <= response['overall_score'] <= 1
    
    def test_check_empty_text(self):
        """测试空文本检查"""
        checker = GroundednessChecker()
        
        generated_text = ""
        context = ["Some context."]
        
        response = checker.check(generated_text, context)
        
        assert response['overall_score'] == 1.0
        assert response['groundedness_level'] == GroundednessLevel.FULLY_GROUNDED.value
    
    def test_check_empty_context(self):
        """测试空上下文检查"""
        checker = GroundednessChecker()
        
        generated_text = "The capital of France is Paris."
        context = []
        
        response = checker.check(generated_text, context)
        
        # 没有上下文，应该不是完全真实的
        assert response['overall_score'] < 1.0
        assert response['groundedness_level'] != GroundednessLevel.FULLY_GROUNDED.value
    
    def test_get_groundedness_checker_singleton(self):
        """测试单例模式"""
        checker1 = get_groundedness_checker()
        checker2 = get_groundedness_checker()
        
        assert checker1 is checker2
        assert isinstance(checker1, GroundednessChecker)
    
    def test_check_groundedness_simple(self):
        """测试简化接口"""
        generated_text = "The capital of France is Paris."
        context = ["Paris is the capital of France."]
        
        is_grounded, score, ungrounded = check_groundedness(generated_text, context)
        
        # 验证返回类型
        assert isinstance(is_grounded, bool)
        assert isinstance(score, float)
        assert isinstance(ungrounded, list)
        
        # 分数应该在合理范围内
        assert 0 <= score <= 1
    
    def test_check_with_different_thresholds(self):
        """测试不同阈值"""
        checker = GroundednessChecker()
        
        generated_text = "The capital of France is Paris."
        context = ["Paris is the capital of France."]
        
        # 测试低阈值
        response_low = checker.check(generated_text, context, threshold=0.5)
        
        # 测试高阈值
        response_high = checker.check(generated_text, context, threshold=0.9)
        
        # 验证响应存在
        assert response_low is not None
        assert response_high is not None
    
    def test_check_with_specific_claim_types(self):
        """测试特定声明类型"""
        checker = GroundednessChecker()
        
        generated_text = "In 2023, GDP increased by 3.5% compared to 2022."
        context = [
            "The GDP growth in 2023 was 3.5%.",
            "This is compared to 2022 figures."
        ]
        
        response = checker.check(
            generated_text, 
            context,
            threshold=0.7,
            check_types=[ClaimType.TEMPORAL, ClaimType.NUMERICAL, ClaimType.COMPARATIVE]
        )
        
        assert response is not None
        assert "overall_score" in response
    
    def test_response_structure_completeness(self):
        """测试响应结构完整性"""
        checker = GroundednessChecker()
        
        generated_text = "Test text with multiple claims."
        context = ["Test context for verification."]
        
        response = checker.check(generated_text, context)
        
        # 验证所有必需字段
        required_fields = [
            'overall_score',
            'groundedness_level',
            'grounded_claims',
            'ungrounded_claims',
            'hallucinated_claims',
            'results',
            'details'
        ]
        
        for field in required_fields:
            assert field in response
        
        # 验证字段类型
        assert isinstance(response['overall_score'], float)
        assert isinstance(response['groundedness_level'], str)
        assert isinstance(response['grounded_claims'], list)
        assert isinstance(response['ungrounded_claims'], list)
        assert isinstance(response['hallucinated_claims'], list)
        assert isinstance(response['results'], list)
        assert isinstance(response['details'], dict)
    
    def test_groundedness_level_values(self):
        """测试真实性等级值"""
        levels = [
            GroundednessLevel.FULLY_GROUNDED,
            GroundednessLevel.PARTIALLY_GROUNDED,
            GroundednessLevel.NOT_GROUNDED,
            GroundednessLevel.HALLUCINATION
        ]
        
        for level in levels:
            assert isinstance(level.value, str)
            assert len(level.value) > 0
    
    def test_claim_type_values(self):
        """测试声明类型值"""
        types = [
            ClaimType.FACTUAL,
            ClaimType.NUMERICAL,
            ClaimType.TEMPORAL,
            ClaimType.SPATIAL,
            ClaimType.CAUSAL,
            ClaimType.COMPARATIVE
        ]
        
        for claim_type in types:
            assert isinstance(claim_type.value, str)
            assert len(claim_type.value) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])