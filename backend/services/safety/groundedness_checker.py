"""
Groundedness Checker and Safety Guard

Features:
- NLI-based groundedness checking
- Safety level classification
- Disclaimer injection

Date: 2026-02-09
Priority: P0 (Week 2 deliverable)
"""

import logging
import re
from enum import Enum
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """Safety level classification for LLM responses."""

    INFORMATIONAL = "informational"  # General information (low risk)
    ADVISORY = "advisory"  # Advisory content (moderate risk)
    SAFETY_CRITICAL = "safety_critical"  # Safety-critical content (high risk)


class GroundednessChecker:
    """
    Groundedness checker for LLM-generated responses.

    Features:
    - Token overlap-based groundedness scoring
    - Safety level classification
    - Disclaimer injection for safety-critical content
    """

    def __init__(self, confidence_threshold: float = 0.80):
        """
        Args:
            confidence_threshold: Minimum confidence threshold (default 0.80)
        """
        self.confidence_threshold = confidence_threshold

    def check_safety_level(self, answer: str) -> SafetyLevel:
        """
        Classify the safety level of an LLM response.

        Args:
            answer: The LLM-generated response text

        Returns:
            SafetyLevel classification
        """
        answer_lower = answer.lower()

        # Safety-critical keywords
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

        # Advisory keywords
        advisory_keywords = [
            "recommend",
            "suggest",
            "should consider",
            "best practice",
            "guideline",
        ]

        # Check safety-critical keywords first
        for keyword in safety_critical_keywords:
            if keyword in answer_lower:
                return SafetyLevel.SAFETY_CRITICAL

        # Then check advisory keywords
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
            llm_client: LLM client for optional NLI-based checking

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

        if llm_client is not None:
            try:
                verification_prompt = (
                    "Does the following answer accurately reflect the provided context? "
                    "Reply with a confidence score between 0.0 and 1.0.\n\n"
                    f"Context: {' '.join(context[:3])[:1000]}\n\n"
                    f"Answer: {answer[:500]}\n\nScore:"
                )
                llm_response = llm_client.generate(verification_prompt, temperature=0.0, max_tokens=10)
                score_match = re.search(r'(0\.\d+|1\.0|0|1)', str(llm_response))
                if score_match:
                    llm_score = float(score_match.group(1))
                    confidence = confidence * 0.4 + llm_score * 0.6
            except Exception as exc:
                logger.warning("LLM groundedness check failed, using lexical score: %s", exc)

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
        Append a safety disclaimer to the answer based on safety level.

        Args:
            answer: The original answer text
            safety_level: The classified safety level

        Returns:
            Answer text with appropriate disclaimer appended
        """
        disclaimers = {
            SafetyLevel.SAFETY_CRITICAL: (
                "\n\n---\n"
                "⚠️ **Safety Warning**: This AI-generated response is for informational purposes only. "
                "Always verify safety-critical information with qualified professionals and applicable "
                "codes such as the Alberta OHS Act and the National Building Code. "
                "Do not rely solely on AI for safety decisions."
            ),
            SafetyLevel.ADVISORY: (
                "\n\n---\n"
                "💡 **Note**: This response is AI-generated. Please verify important details "
                "with authoritative sources before making decisions."
            ),
            SafetyLevel.INFORMATIONAL: "",
        }

        disclaimer = disclaimers.get(safety_level, "")
        return answer + disclaimer

    def should_refuse_to_answer(
        self,
        confidence: float,
        safety_level: SafetyLevel,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine whether the system should refuse to answer.

        Args:
            confidence: Groundedness confidence score
            safety_level: The classified safety level

        Returns:
            (should_refuse, refusal_message)
        """
        if confidence < self.confidence_threshold:
            return True, (
                "I don't have enough confidence in this answer to provide it reliably. "
                "Please rephrase your question or consult an authoritative source."
            )


        if safety_level == SafetyLevel.SAFETY_CRITICAL and confidence < max(
            0.85, self.confidence_threshold + 0.05
        ):
            return True, (
                "This question involves safety-critical information and my confidence "
                "is too low to provide a reliable answer. Please consult a qualified "
                "professional or refer to the Alberta OHS Act and applicable building codes. "
                "AI-generated answers should not be used for safety-critical decisions."
            )

        return False, None

    def check_and_enhance_answer(
        self,
        answer: str,
        context: list[str],
        llm_client=None,
    ) -> str:
        """
        Full pipeline: check groundedness -> classify safety -> add disclaimer or refuse.

        Args:
            answer: The LLM-generated response text
            context: List of retrieved context passages
            llm_client: Optional LLM client for enhanced checking

        Returns:
            Enhanced answer with disclaimer, or a refusal message
        """
        # 1. Classify safety level
        safety_level = self.check_safety_level(answer)

        # 2. Check groundedness
        confidence, _ = self.check_groundedness(answer, context, llm_client)

        # 3. Determine if we should refuse
        should_refuse, refusal_message = self.should_refuse_to_answer(
            confidence,
            safety_level,
        )

        if should_refuse:
            logger.warning("Refusing to answer due to low confidence")
            return refusal_message

        # 4. Add disclaimer
        enhanced_answer = self.add_disclaimer(answer, safety_level)

        return enhanced_answer


class SafetyGuard:
    """
    High-level safety guard combining groundedness checking and disclaimers.

    Usage:
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
            confidence_threshold: Minimum confidence threshold (default 0.80)
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
        Process an LLM response through safety checks and enhancement.

        Args:
            answer: The LLM-generated response text
            context: List of retrieved context passages
            llm_client: Optional LLM client for NLI-based checking

        Returns:
            Dict with enhanced_answer, safety_level, confidence, passed_checks
        """
        # Classify safety level
        safety_level = self.groundedness_checker.check_safety_level(answer)

        # Check groundedness
        confidence, passed = self.groundedness_checker.check_groundedness(
            answer, context, llm_client
        )

        # Determine if we should refuse
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

        # Add disclaimer
        enhanced_answer = self.groundedness_checker.add_disclaimer(answer, safety_level)

        return {
            "enhanced_answer": enhanced_answer,
            "safety_level": safety_level,
            "confidence": confidence,
            "passed_checks": passed,
            "refused": False,
        }


# Factory function
def create_safety_guard(confidence_threshold: float = 0.80) -> SafetyGuard:
    """Create a SafetyGuard instance with the given confidence threshold."""
    return SafetyGuard(confidence_threshold)


if __name__ == "__main__":
    # Demo / self-test
    logging.basicConfig(level=logging.INFO)

    print("Safety Guard Demo")
    print("=" * 60)

    safety_guard = create_safety_guard()

    # Test 1: Safety-critical response with good context
    answer1 = (
        "According to Alberta OHS Part 23, scaffolding above 3 meters requires "
        "guardrails on all open sides and toe boards at least 89mm high."
    )
    context1 = [
        "Alberta OHS Code Part 23: Scaffolds",
        "Section 23.1: Guardrails and toe boards requirements",
    ]

    result1 = safety_guard.process_response(answer1, context1)
    print("\nTest 1: Safety-critical with context")
    print(f"Answer: {answer1[:80]}...")
    print(f"Safety level: {result1['safety_level'].value}")
    print(f"Confidence: {result1['confidence']:.2f}")
    print(f"Result:\n{result1['enhanced_answer']}")

    # Test 2: Safety-critical response without context
    answer2 = "The concrete strength should be around 30-40 MPa."
    context2 = []  # No context

    result2 = safety_guard.process_response(answer2, context2)
    print("\nTest 2: Safety-critical without context")
    print(f"Answer: {answer2}")
    print(f"Confidence: {result2['confidence']:.2f}")
    print(f"Refused: {result2['refused']}")
    print(f"Result: {result2['enhanced_answer']}")
