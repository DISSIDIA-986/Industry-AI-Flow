"""
EN:EN

EN:
- NLIEN
- EN
- EN
- EN

EN: 2026-02-09
EN: P0 (Week 2EN)
"""

import logging
import re
from enum import Enum
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """EN"""

    INFORMATIONAL = "informational"  # EN(EN)
    ADVISORY = "advisory"  # EN(EN)
    SAFETY_CRITICAL = "safety_critical"  # EN(EN)


class GroundednessChecker:
    """
    EN:EN

    EN:
    - EN
    - EN
    - EN
    """

    def __init__(self, confidence_threshold: float = 0.80):
        """
        Args:
            confidence_threshold: EN(EN0.80)
        """
        self.confidence_threshold = confidence_threshold

    def check_safety_level(self, answer: str) -> SafetyLevel:
        """
        EN

        Args:
            answer: LLMEN

        Returns:
            SafetyLevelEN
        """
        answer_lower = answer.lower()

        # EN
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

        # EN
        advisory_keywords = [
            "recommend",
            "suggest",
            "should consider",
            "best practice",
            "guideline",
        ]

        # EN
        for keyword in safety_critical_keywords:
            if keyword in answer_lower:
                return SafetyLevel.SAFETY_CRITICAL

        # EN
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
        Check groundedness of an answer against retrieved context.

        Uses bag-of-words overlap with numeric-aware comparison:
        numbers in the answer that differ from context numbers incur
        a penalty proportional to the magnitude difference.

        Args:
            answer: LLM-generated answer
            context: Retrieved context passages
            llm_client: LLM client (reserved for future NLI-based checking)

        Returns:
            (confidence_score, passed_threshold)
        """
        if not context:
            logger.warning("No context provided for groundedness check")
            return 0.0, False

        answer_tokens = self._tokenize(answer)
        context_tokens = self._tokenize(" ".join(context))

        if not answer_tokens or not context_tokens:
            return 0.0, False

        answer_vocab = set(answer_tokens)
        context_vocab = set(context_tokens)
        overlap = answer_vocab & context_vocab

        support_ratio = len(overlap) / len(answer_vocab)
        context_hit_ratio = len(overlap) / len(context_vocab)

        length_penalty = 0.0
        if len(answer_tokens) > len(context_tokens) * 2:
            length_penalty = min(
                0.20, (len(answer_tokens) - len(context_tokens) * 2) / 100.0
            )

        # Numeric mismatch penalty: numbers in the answer that are NOT
        # in the context may indicate hallucinated or wrong figures.
        numeric_penalty = self._numeric_mismatch_penalty(answer_tokens, context_tokens)

        confidence = max(
            0.0,
            min(
                1.0,
                support_ratio * 0.95
                + min(0.05, context_hit_ratio * 0.10)
                - length_penalty
                - numeric_penalty,
            ),
        )

        passed = confidence >= self.confidence_threshold

        logger.info(
            "Groundedness check: confidence=%.2f, passed=%s, numeric_penalty=%.2f",
            confidence,
            passed,
            numeric_penalty,
        )

        return confidence, passed

    @staticmethod
    def _numeric_mismatch_penalty(
        answer_tokens: list[str], context_tokens: list[str]
    ) -> float:
        """Penalize numeric tokens in the answer that differ from context numbers."""
        import re as _re

        _num_re = _re.compile(r"^\d+(?:\.\d+)?$")
        answer_nums = {t for t in answer_tokens if _num_re.match(t)}
        context_nums = {t for t in context_tokens if _num_re.match(t)}

        if not answer_nums:
            return 0.0

        mismatched = answer_nums - context_nums
        if not mismatched:
            return 0.0

        # For each mismatched number, check if there is a close context number
        penalty = 0.0
        for num_str in mismatched:
            try:
                num_val = float(num_str)
            except ValueError:
                continue
            # Find closest context number
            best_ratio = float("inf")
            for ctx_str in context_nums:
                try:
                    ctx_val = float(ctx_str)
                except ValueError:
                    continue
                if ctx_val == 0:
                    continue
                ratio = abs(num_val - ctx_val) / max(abs(ctx_val), 1.0)
                best_ratio = min(best_ratio, ratio)

            if best_ratio == float("inf"):
                # Number not in context at all — moderate penalty
                penalty += 0.10
            elif best_ratio > 0.5:
                # Large magnitude difference (e.g., 500 vs 50)
                penalty += 0.15
            elif best_ratio > 0.1:
                # Moderate difference
                penalty += 0.05

        return min(0.50, penalty)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple tokenizer that keeps words, hyphenated terms and CJK blocks."""
        return re.findall(
            r"[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*|[\u4e00-\u9fff]+", text.lower()
        )

    def add_disclaimer(self, answer: str, safety_level: SafetyLevel) -> str:
        """
        EN

        Args:
            answer: EN
            safety_level: EN

        Returns:
            EN
        """
        disclaimers = {
            SafetyLevel.SAFETY_CRITICAL: (
                "\n\n---\n"
                "⚠️ **EN**: ENAIEN,EN."
                "ENAlberta OHS Act/Building CodeEN."
                "EN."
            ),
            SafetyLevel.ADVISORY: (
                "\n\n---\n" "💡 **EN**: EN," "EN."
            ),
            SafetyLevel.INFORMATIONAL: "",  # EN
        }

        disclaimer = disclaimers.get(safety_level, "")
        return answer + disclaimer

    def should_refuse_to_answer(
        self,
        confidence: float,
        safety_level: SafetyLevel,
    ) -> Tuple[bool, Optional[str]]:
        """
        EN

        Args:
            confidence: EN
            safety_level: EN

        Returns:
            (EN, EN)
        """
        # EN,EN
        if confidence < self.confidence_threshold:
            return True, ("EN,EN." "EN,EN.")

        # EN,EN
        if safety_level == SafetyLevel.SAFETY_CRITICAL and confidence < max(
            0.85, self.confidence_threshold + 0.05
        ):
            return True, (
                "EN,EN."
                "ENAlberta OHS ActEN."
                "AIEN."
            )

        return False, None

    def check_and_enhance_answer(
        self,
        answer: str,
        context: list[str],
        llm_client=None,
    ) -> str:
        """
        EN:EN -> EN -> EN

        Args:
            answer: LLMEN
            context: EN
            llm_client: LLMEN(EN)

        Returns:
            EN(EN)
        """
        # 1. EN
        safety_level = self.check_safety_level(answer)

        # 2. EN
        confidence, _ = self.check_groundedness(answer, context, llm_client)

        # 3. EN
        should_refuse, refusal_message = self.should_refuse_to_answer(
            confidence,
            safety_level,
        )

        if should_refuse:
            logger.warning("Refusing to answer due to low confidence")
            return refusal_message

        # 4. EN
        enhanced_answer = self.add_disclaimer(answer, safety_level)

        return enhanced_answer


class SafetyGuard:
    """
    EN:EN

    EN:
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
            confidence_threshold: EN(EN0.80)
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
        ENLLMEN,EN

        Args:
            answer: LLMEN
            context: EN
            llm_client: LLMEN(EN,ENNLIEN)

        Returns:
            EN {
                "enhanced_answer": str,
                "safety_level": SafetyLevel,
                "confidence": float,
                "passed_checks": bool,
            }
        """
        # EN
        safety_level = self.groundedness_checker.check_safety_level(answer)

        # EN
        confidence, passed = self.groundedness_checker.check_groundedness(
            answer, context, llm_client
        )

        # EN
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

        # EN
        enhanced_answer = self.groundedness_checker.add_disclaimer(answer, safety_level)

        return {
            "enhanced_answer": enhanced_answer,
            "safety_level": safety_level,
            "confidence": confidence,
            "passed_checks": passed,
            "refused": False,
        }


# EN
def create_safety_guard(confidence_threshold: float = 0.80) -> SafetyGuard:
    """EN"""
    return SafetyGuard(confidence_threshold)


if __name__ == "__main__":
    # EN
    logging.basicConfig(level=logging.INFO)

    print("🛡️ EN")
    print("=" * 60)

    safety_guard = create_safety_guard()

    # EN1:EN
    answer1 = (
        "According to Alberta OHS Part 23, scaffolding above 3 meters requires "
        "guardrails on all open sides and toe boards at least 89mm high."
    )
    context1 = [
        "Alberta OHS Code Part 23: Scaffolds",
        "Section 23.1: Guardrails and toe boards requirements",
    ]

    result1 = safety_guard.process_response(answer1, context1)
    print("\nEN1:EN")
    print(f"EN: {answer1[:80]}...")
    print(f"EN: {result1['safety_level'].value}")
    print(f"EN: {result1['confidence']:.2f}")
    print(f"EN:\n{result1['enhanced_answer']}")

    # EN2:EN
    answer2 = "The concrete strength should be around 30-40 MPa."  # EN
    context2 = []  # EN

    result2 = safety_guard.process_response(answer2, context2)
    print("\nEN2:EN")
    print(f"EN: {answer2}")
    print(f"EN: {result2['confidence']:.2f}")
    print(f"EN: {result2['refused']}")
    print(f"EN: {result2['enhanced_answer']}")
