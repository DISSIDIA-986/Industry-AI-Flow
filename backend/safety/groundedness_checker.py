"""
Groundedness Checker - 检查生成内容的真实性
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class GroundednessLevel(Enum):
    """真实性等级"""
    FULLY_GROUNDED = "fully_grounded"  # 完全基于上下文
    PARTIALLY_GROUNDED = "partially_grounded"  # 部分基于上下文
    NOT_GROUNDED = "not_grounded"  # 不基于上下文
    HALLUCINATION = "hallucination"  # 幻觉/虚构


class ClaimType(Enum):
    """声明类型"""
    FACTUAL = "factual"  # 事实性声明
    NUMERICAL = "numerical"  # 数字性声明
    TEMPORAL = "temporal"  # 时间性声明
    SPATIAL = "spatial"  # 空间性声明
    CAUSAL = "causal"  # 因果性声明
    COMPARATIVE = "comparative"  # 比较性声明


@dataclass
class Claim:
    """声明"""
    text: str
    claim_type: ClaimType
    confidence: float
    start_pos: int
    end_pos: int
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class GroundednessResult:
    """真实性检查结果"""
    claim: Claim
    is_grounded: bool
    supporting_context: List[str]
    confidence_score: float
    details: Dict[str, Any]


class GroundednessChecker:
    """真实性检查器"""
    
    # 事实性声明模式
    FACTUAL_PATTERNS = [
        r"\b(?:is|are|was|were|has|have|had)\b(?:\s+\w+)?(?:\s+(?:a|an|the))?\s*\w*\b",
        r"\b(?:according to|based on|as per)\b\s+\w+\b",
        r"\b(?:shows?|indicates?|demonstrates?|proves?)\b\s+that\b",
    ]
    
    # 数字性声明模式
    NUMERICAL_PATTERNS = [
        r"\b\d+(?:\.\d+)?\s*(?:percent|%|dollars?|\$|years?|months?|days?)\b",
        r"\b(?:increase|decrease|growth|decline)\b\s+of\s+\d+(?:\.\d+)?\b",
        r"\b(?:more than|less than|about|approximately)\b\s+\d+(?:\.\d+)?\b",
    ]
    
    # 时间性声明模式
    TEMPORAL_PATTERNS = [
        r"\b(?:in|on|at|during)\b\s+\d{4}(?:-\d{2})?(?:-\d{2})?\b",
        r"\b(?:before|after|since|until)\b\s+\d{4}(?:-\d{2})?(?:-\d{2})?\b",
        r"\b(?:recently|previously|currently|formerly)\b",
    ]
    
    # 空间性声明模式
    SPATIAL_PATTERNS = [
        r"\b(?:in|at|on|near)\b\s+\w+\s*(?:city|country|region|area)\b",
        r"\b(?:located|situated|positioned)\b\s+(?:in|at|on)\s+\w+\b",
        r"\b(?:from|to)\b\s+\w+\s+(?:to|from)\s+\w+\b",
    ]
    
    # 因果性声明模式
    CAUSAL_PATTERNS = [
        r"\b(?:because|since|as|due to|owing to)\b\s+\w+\b",
        r"\b(?:leads? to|results? in|causes?|triggers?)\b\s+\w+\b",
        r"\b(?:therefore|thus|hence|consequently)\b\s+\w+\b",
    ]
    
    # 比较性声明模式
    COMPARATIVE_PATTERNS = [
        r"\b(?:more|less|better|worse|higher|lower)\b\s+than\s+\w+\b",
        r"\b(?:similar to|different from|compared to)\b\s+\w+\b",
        r"\b(?:as\s+\w+\s+as|not\s+as\s+\w+\s+as)\b",
    ]
    
    def __init__(self, model_name: str = "default") -> None:
        """
        初始化真实性检查器
        
        Args:
            model_name: 模型名称（预留参数）
        """
        self.model_name = model_name
        self._compile_patterns()
        
    def _compile_patterns(self) -> None:
        """编译正则表达式模式"""
        self.patterns = {
            ClaimType.FACTUAL: [re.compile(p, re.IGNORECASE) for p in self.FACTUAL_PATTERNS],
            ClaimType.NUMERICAL: [re.compile(p, re.IGNORECASE) for p in self.NUMERICAL_PATTERNS],
            ClaimType.TEMPORAL: [re.compile(p, re.IGNORECASE) for p in self.TEMPORAL_PATTERNS],
            ClaimType.SPATIAL: [re.compile(p, re.IGNORECASE) for p in self.SPATIAL_PATTERNS],
            ClaimType.CAUSAL: [re.compile(p, re.IGNORECASE) for p in self.CAUSAL_PATTERNS],
            ClaimType.COMPARATIVE: [re.compile(p, re.IGNORECASE) for p in self.COMPARATIVE_PATTERNS],
        }
    
    def extract_claims(self, text: str, check_types: Optional[List[ClaimType]] = None) -> List[Claim]:
        """
        从文本中提取声明
        
        Args:
            text: 输入文本
            check_types: 要检查的声明类型
            
        Returns:
            声明列表
        """
        if check_types is None:
            check_types = list(ClaimType)
        
        claims = []
        
        for claim_type in check_types:
            if claim_type not in self.patterns:
                continue
                
            for pattern in self.patterns[claim_type]:
                for match in pattern.finditer(text):
                    claim_text = match.group(0).strip()
                    
                    # 计算置信度（基于匹配长度和特异性）
                    confidence = min(1.0, len(claim_text) / 100)
                    
                    claim = Claim(
                        text=claim_text,
                        claim_type=claim_type,
                        confidence=confidence,
                        start_pos=match.start(),
                        end_pos=match.end()
                    )
                    claims.append(claim)
        
        # 去重（基于文本和位置）
        unique_claims = []
        seen = set()
        
        for claim in claims:
            key = (claim.text, claim.start_pos, claim.end_pos)
            if key not in seen:
                seen.add(key)
                unique_claims.append(claim)
        
        logger.info(f"Extracted {len(unique_claims)} claims from text")
        return unique_claims
    
    def verify_claim(self, claim: Claim, context: List[str]) -> GroundednessResult:
        """
        验证声明是否在上下文中得到支持
        
        Args:
            claim: 声明
            context: 上下文
            
        Returns:
            真实性检查结果
        """
        supporting_context = []
        confidence_score = 0.0
        
        # 简单的字符串匹配验证
        for ctx in context:
            # 检查声明文本是否在上下文中出现
            if claim.text.lower() in ctx.lower():
                supporting_context.append(ctx)
                confidence_score += 0.3
            
            # 检查关键词是否在上下文中出现
            keywords = self._extract_keywords(claim.text)
            keyword_matches = sum(1 for kw in keywords if kw.lower() in ctx.lower())
            if keyword_matches > 0:
                supporting_context.append(ctx)
                confidence_score += min(0.2, keyword_matches * 0.05)
        
        # 归一化置信度分数
        if supporting_context:
            confidence_score = min(1.0, confidence_score / len(supporting_context))
        
        is_grounded = confidence_score > 0.5
        
        result = GroundednessResult(
            claim=claim,
            is_grounded=is_grounded,
            supporting_context=supporting_context,
            confidence_score=confidence_score,
            details={
                "keyword_matches": len(supporting_context),
                "claim_type": claim.claim_type.value,
                "text_length": len(claim.text)
            }
        )
        
        return result
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表
        """
        # 简单的关键词提取：移除停用词，保留名词和动词
        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall',
            'should', 'may', 'might', 'must', 'can', 'could', 'that', 'this',
            'these', 'those', 'it', 'its', 'they', 'them', 'their', 'we', 'us',
            'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her', 'hers'
        }
        
        # 简单的分词和过滤
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords
    
    def check(self, generated_text: str, context: List[str], 
             threshold: float = 0.7, check_types: Optional[List[ClaimType]] = None) -> Dict[str, Any]:
        """
        检查生成内容的真实性（简化接口，不使用pydantic）
        
        Args:
            generated_text: 生成的文本
            context: 上下文列表
            threshold: 置信度阈值
            check_types: 要检查的声明类型
            
        Returns:
            检查结果字典
        """
        logger.info(f"Checking groundedness for text of length {len(generated_text)}")
        
        # 提取声明
        if check_types is None:
            check_types = list(ClaimType)
        claims = self.extract_claims(generated_text, check_types)
        
        if not claims:
            logger.info("No claims found in generated text")
            return {
                "overall_score": 1.0,
                "groundedness_level": GroundednessLevel.FULLY_GROUNDED.value,
                "grounded_claims": [],
                "ungrounded_claims": [],
                "hallucinated_claims": [],
                "results": [],
                "details": {"message": "No claims found in generated text"}
            }
        
        # 验证每个声明
        results = []
        grounded_claims = []
        ungrounded_claims = []
        hallucinated_claims = []
        
        for claim in claims:
            result = self.verify_claim(claim, context)
            results.append(result)
            
            if result.is_grounded:
                grounded_claims.append(claim)
            elif result.confidence_score < 0.2:
                hallucinated_claims.append(claim)
            else:
                ungrounded_claims.append(claim)
        
        # 计算总体分数
        if claims:
            overall_score = len(grounded_claims) / len(claims)
        else:
            overall_score = 1.0
        
        # 确定真实性等级
        if overall_score >= 0.9:
            groundedness_level = GroundednessLevel.FULLY_GROUNDED
        elif overall_score >= 0.7:
            groundedness_level = GroundednessLevel.PARTIALLY_GROUNDED
        elif overall_score >= 0.3:
            groundedness_level = GroundednessLevel.NOT_GROUNDED
        else:
            groundedness_level = GroundednessLevel.HALLUCINATION
        
        response = {
            "overall_score": overall_score,
            "groundedness_level": groundedness_level.value,
            "grounded_claims": [c.text for c in grounded_claims],
            "ungrounded_claims": [c.text for c in ungrounded_claims],
            "hallucinated_claims": [c.text for c in hallucinated_claims],
            "results": results,
            "details": {
                "total_claims": len(claims),
                "grounded_ratio": overall_score,
                "context_count": len(context),
                "model_name": self.model_name
            }
        }
        
        logger.info(f"Groundedness check completed: {groundedness_level.value} (score: {overall_score:.2f})")
        return response
    
    def check_simple(self, generated_text: str, context: List[str]) -> Tuple[bool, float, List[str]]:
        """
        简单的真实性检查（简化接口）
        
        Args:
            generated_text: 生成的文本
            context: 上下文
            
        Returns:
            (是否真实, 置信度分数, 不真实的声明列表)
        """
        response = self.check(generated_text, context)
        
        ungrounded_texts = response.get("ungrounded_claims", []) + response.get("hallucinated_claims", [])
        
        is_grounded = response["overall_score"] >= 0.7
        
        return is_grounded, response["overall_score"], ungrounded_texts


# 全局实例
_groundedness_checker = None


def get_groundedness_checker() -> GroundednessChecker:
    """
    获取全局真实性检查器实例
    
    Returns:
        真实性检查器实例
    """
    global _groundedness_checker
    if _groundedness_checker is None:
        _groundedness_checker = GroundednessChecker()
    return _groundedness_checker


def check_groundedness(generated_text: str, context: List[str]) -> Tuple[bool, float, List[str]]:
    """
    检查生成内容的真实性（简化接口）
    
    Args:
        generated_text: 生成的文本
        context: 上下文
        
    Returns:
        (是否真实, 置信度分数, 不真实的声明列表)
    """
    checker = get_groundedness_checker()
    return checker.check_simple(generated_text, context)


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建检查器
    checker = GroundednessChecker()
    
    # 测试数据
    generated_text = "The capital of France is Paris. The population is 2.1 million people."
    context = [
        "France is a country in Europe.",
        "Paris is the capital of France.",
        "The population of Paris is about 2.1 million."
    ]
    
    # 执行检查
    response = checker.check(generated_text, context)
    
    # 打印结果
    print(f"Overall Score: {response['overall_score']:.2f}")
    print(f"Groundedness Level: {response['groundedness_level']}")
    print(f"Grounded Claims: {len(response['grounded_claims'])}")
    print(f"Ungrounded Claims: {len(response['ungrounded_claims'])}")
    print(f"Hallucinated Claims: {len(response['hallucinated_claims'])}")
    
    # 打印不真实的声明
    if response['ungrounded_claims'] or response['hallucinated_claims']:
        print("\nUngrounded/Hallucinated Claims:")
        for claim in response['ungrounded_claims'] + response['hallucinated_claims']:
            print(f"  - {claim} ({claim.claim_type.value if hasattr(claim, 'claim_type') else 'unknown'})")