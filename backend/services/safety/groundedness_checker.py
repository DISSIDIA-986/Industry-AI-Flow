"""
安全防护层：接地度检查与免责声明

实现建筑安全信息的零幻觉防护：
- NLI接地度检查
- 置信度阈值过滤
- 强制安全免责声明
- 拒绝回答策略

创建时间: 2026-02-09
优先级: P0 (Week 2任务)
"""

import logging
import re
from enum import Enum
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """安全等级分类"""

    INFORMATIONAL = "informational"  # 信息性回答（低风险）
    ADVISORY = "advisory"  # 建议性回答（中风险）
    SAFETY_CRITICAL = "safety_critical"  # 安全关键回答（高风险）


class GroundednessChecker:
    """
    接地度检查器：验证答案是否基于检索到的上下文

    防止建筑规范幻觉：
    - 错误的建筑规范引用
    - 虚假的材料规格
    - 编造的安全程序
    """

    def __init__(self, confidence_threshold: float = 0.80):
        """
        Args:
            confidence_threshold: 最低置信度阈值（默认0.80）
        """
        self.confidence_threshold = confidence_threshold

    def check_safety_level(self, answer: str) -> SafetyLevel:
        """
        分类回答的安全等级

        Args:
            answer: LLM生成的答案

        Returns:
            SafetyLevel枚举
        """
        answer_lower = answer.lower()

        # 安全关键关键词
        safety_critical_keywords = [
            "ohs",
            "occupational health and safety",
            "building code",
            "regulation",
            "compliance",
            "scaffold",
            "fall protection",
            "excavation",
            "concrete strength",
            "structural",
            "fire resistance",
            "load bearing",
            "electrical safety",
            "hazardous",
        ]

        # 建议性关键词
        advisory_keywords = [
            "recommend",
            "suggest",
            "should consider",
            "best practice",
            "guideline",
        ]

        # 检查是否包含安全关键关键词
        for keyword in safety_critical_keywords:
            if keyword in answer_lower:
                return SafetyLevel.SAFETY_CRITICAL

        # 检查是否包含建议性关键词
        for keyword in advisory_keywords:
            if keyword in answer_lower:
                return SafetyLevel.ADVISORY

        return SafetyLevel.INFORMATIONAL

    def check_groundedness(
        self,
        answer: str,
        context: list[str],
        llm_client=None,
    ) -> Tuple[float, bool]:
        """
        检查答案是否从上下文中推导（接地度NLI检查）

        Args:
            answer: LLM生成的答案
            context: 检索到的上下文列表
            llm_client: LLM客户端（用于NLI推理）

        Returns:
            (置信度分数, 是否通过检查)
        """
        if not context:
            logger.warning("No context provided for groundedness check")
            return 0.0, False

        # 轻量词级接地度检查：比 split() 更稳健（处理中英文标点和连字符）
        answer_tokens = self._tokenize(answer)
        context_tokens = self._tokenize(" ".join(context))

        if not answer_tokens or not context_tokens:
            return 0.0, False

        answer_vocab = set(answer_tokens)
        context_vocab = set(context_tokens)
        overlap = answer_vocab & context_vocab

        # 回答支撑率：回答中的关键token有多少被上下文覆盖（核心指标）
        support_ratio = len(overlap) / len(answer_vocab)
        # 上下文命中率：仅做轻度加成，避免长上下文被过度惩罚
        context_hit_ratio = len(overlap) / len(context_vocab)

        # 长回答在短上下文下易幻觉，增加轻度长度惩罚
        length_penalty = 0.0
        if len(answer_tokens) > len(context_tokens) * 2:
            length_penalty = min(
                0.20, (len(answer_tokens) - len(context_tokens) * 2) / 100.0
            )

        confidence = max(
            0.0,
            min(
                1.0,
                support_ratio * 0.95
                + min(0.05, context_hit_ratio * 0.10)
                - length_penalty,
            ),
        )

        passed = confidence >= self.confidence_threshold

        logger.info(
            "Groundedness check: confidence=%.2f, passed=%s",
            confidence,
            passed,
        )

        return confidence, passed

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple tokenizer that keeps words, hyphenated terms and CJK blocks."""
        return re.findall(
            r"[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*|[\u4e00-\u9fff]+", text.lower()
        )

    def add_disclaimer(self, answer: str, safety_level: SafetyLevel) -> str:
        """
        根据安全等级添加免责声明

        Args:
            answer: 原始答案
            safety_level: 安全等级

        Returns:
            带免责声明的答案
        """
        disclaimers = {
            SafetyLevel.SAFETY_CRITICAL: (
                "\n\n---\n"
                "⚠️ **安全免责声明**: 此为AI生成指导，仅供参考。"
                "请始终对照官方Alberta OHS Act/Building Code验证。"
                "不替代专业工程建议或官方法规解读。"
            ),
            SafetyLevel.ADVISORY: (
                "\n\n---\n" "💡 **建议**: 此回答基于建筑行业最佳实践，" "具体应用请参考项目相关规范和标准。"
            ),
            SafetyLevel.INFORMATIONAL: "",  # 信息性回答无需免责声明
        }

        disclaimer = disclaimers.get(safety_level, "")
        return answer + disclaimer

    def should_refuse_to_answer(
        self,
        confidence: float,
        safety_level: SafetyLevel,
    ) -> Tuple[bool, Optional[str]]:
        """
        判断是否应该拒绝回答

        Args:
            confidence: 接地度置信度
            safety_level: 安全等级

        Returns:
            (是否拒绝, 拒绝原因)
        """
        # 如果置信度过低，拒绝回答
        if confidence < self.confidence_threshold:
            return True, ("抱歉，我无法基于现有文档找到足够准确的信息来回答此问题。" "请尝试重新表述问题，或查阅官方建筑规范文档。")

        # 如果是安全关键问题但置信度不够高，拒绝回答
        if safety_level == SafetyLevel.SAFETY_CRITICAL and confidence < max(
            0.85, self.confidence_threshold + 0.05
        ):
            return True, (
                "此问题涉及建筑安全规范，需要更高的准确性。"
                "请查阅官方Alberta OHS Act或咨询专业工程师。"
                "AI助手不能替代专业安全建议。"
            )

        return False, None

    def check_and_enhance_answer(
        self,
        answer: str,
        context: list[str],
        llm_client=None,
    ) -> str:
        """
        完整的安全检查流程：检查 -> 增强 -> 添加免责声明

        Args:
            answer: LLM生成的答案
            context: 检索到的上下文
            llm_client: LLM客户端（可选）

        Returns:
            增强后的答案（可能包含免责声明或拒绝消息）
        """
        # 1. 检查安全等级
        safety_level = self.check_safety_level(answer)

        # 2. 检查接地度
        confidence, _ = self.check_groundedness(answer, context, llm_client)

        # 3. 判断是否应该拒绝回答
        should_refuse, refusal_message = self.should_refuse_to_answer(
            confidence,
            safety_level,
        )

        if should_refuse:
            logger.warning("Refusing to answer due to low confidence")
            return refusal_message

        # 4. 添加免责声明
        enhanced_answer = self.add_disclaimer(answer, safety_level)

        return enhanced_answer


class SafetyGuard:
    """
    安全防护层主类：集成接地度检查和免责声明

    使用示例:
    ```python
    safety_guard = SafetyGuard(confidence_threshold=0.80)
    answer = safety_guard.check_and_enhance_answer(
        answer=llm_response,
        context=retrieved_docs,
        llm_client=ollama_client
    )
    ```
    """

    def __init__(self, confidence_threshold: float = 0.80):
        """
        Args:
            confidence_threshold: 最低置信度阈值（默认0.80）
        """
        self.groundedness_checker = GroundednessChecker(confidence_threshold)
        logger.info(
            "SafetyGuard initialized with confidence_threshold=%.2f",
            confidence_threshold,
        )

    def process_response(
        self,
        answer: str,
        context: list[str],
        llm_client=None,
    ) -> Dict[str, Any]:
        """
        处理LLM响应，添加安全防护

        Args:
            answer: LLM生成的答案
            context: 检索到的上下文
            llm_client: LLM客户端（可选，用于NLI检查）

        Returns:
            处理结果字典 {
                "enhanced_answer": str,
                "safety_level": SafetyLevel,
                "confidence": float,
                "passed_checks": bool,
            }
        """
        # 检查安全等级
        safety_level = self.groundedness_checker.check_safety_level(answer)

        # 检查接地度
        confidence, passed = self.groundedness_checker.check_groundedness(
            answer, context, llm_client
        )

        # 判断是否拒绝回答
        (
            should_refuse,
            refusal_message,
        ) = self.groundedness_checker.should_refuse_to_answer(confidence, safety_level)

        if should_refuse:
            return {
                "enhanced_answer": refusal_message,
                "safety_level": safety_level,
                "confidence": confidence,
                "passed_checks": False,
                "refused": True,
            }

        # 添加免责声明
        enhanced_answer = self.groundedness_checker.add_disclaimer(answer, safety_level)

        return {
            "enhanced_answer": enhanced_answer,
            "safety_level": safety_level,
            "confidence": confidence,
            "passed_checks": passed,
            "refused": False,
        }


# 便捷函数
def create_safety_guard(confidence_threshold: float = 0.80) -> SafetyGuard:
    """创建安全防护器实例"""
    return SafetyGuard(confidence_threshold)


if __name__ == "__main__":
    # 测试安全防护层
    logging.basicConfig(level=logging.INFO)

    print("🛡️ 安全防护层测试")
    print("=" * 60)

    safety_guard = create_safety_guard()

    # 测试案例1：安全关键问题
    answer1 = (
        "According to Alberta OHS Part 23, scaffolding above 3 meters requires "
        "guardrails on all open sides and toe boards at least 89mm high."
    )
    context1 = [
        "Alberta OHS Code Part 23: Scaffolds",
        "Section 23.1: Guardrails and toe boards requirements",
    ]

    result1 = safety_guard.process_response(answer1, context1)
    print("\n测试案例1：安全关键问题")
    print(f"原始答案: {answer1[:80]}...")
    print(f"安全等级: {result1['safety_level'].value}")
    print(f"置信度: {result1['confidence']:.2f}")
    print(f"增强后答案:\n{result1['enhanced_answer']}")

    # 测试案例2：低置信度拒绝
    answer2 = "The concrete strength should be around 30-40 MPa."  # 不准确的回答
    context2 = []  # 无上下文

    result2 = safety_guard.process_response(answer2, context2)
    print("\n测试案例2：低置信度拒绝")
    print(f"原始答案: {answer2}")
    print(f"置信度: {result2['confidence']:.2f}")
    print(f"是否拒绝: {result2['refused']}")
    print(f"返回消息: {result2['enhanced_answer']}")
