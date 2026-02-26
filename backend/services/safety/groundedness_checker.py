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
        Check how well the answer is grounded in the provided context
        using token overlap (with optional NLI enhancement).

        Args:
            answer: The LLM-generated response text
            context: List of retrieved context passages
            llm_client: Optional LLM client for NLI-based checking

        Returns:
            (confidence_score, passed)
        """
        if not context:
            logger.warning("No context provided for groundedness check")
            return 0.0, False

        # Simple approach: use token overlap for scoring
        answer_tokens = self._tokenize(answer)
        context_tokens = self._tokenize(" ".join(context))

        if not answer_tokens or not context_tokens:
            return 0.0, False

        answer_vocab = set(answer_tokens)
        context_vocab = set(context_tokens)
        overlap = answer_vocab & context_vocab

        # Support ratio: fraction of answer tokens found in context
        support_ratio = len(overlap) / len(answer_vocab)
        # Context hit ratio: fraction of context tokens referenced
        context_hit_ratio = len(overlap) / len(context_vocab)

        # Length penalty for excessively long answers
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
                "⚠️ **Important**: This response contains safety-related information. "
                "Always verify against applicable codes and standards "
                "(e.g., Alberta OHS Act, National Building Code) and consult a "
                "qualified professional before making safety-critical decisions."
            ),
            SafetyLevel.ADVISORY: (
                "\n\n---\n"
                "💡 **Note**: This information is provided for reference only. "
                "Please consult relevant standards and professionals for your "
                "specific situation."
            ),
            SafetyLevel.INFORMATIONAL: "",  # No disclaimer needed
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
        # Low confidence: refuse regardless of safety level
        if confidence < self.confidence_threshold:
            return True, (
                "I cannot provide a confident answer to this question based on "
                "the available documents. Please consult a qualified professional "
                "or refer to the relevant standards for accurate information."
            )

        # Safety-critical with borderline confidence: refuse with specific guidance
        if safety_level == SafetyLevel.SAFETY_CRITICAL and confidence < max(
            0.85, self.confidence_threshold + 0.05
        ):
            return True, (
                "I cannot provide a confident answer to this safety-related "
                "question based on the available documents. Please consult the "
                "Alberta OHS Act or a qualified safety professional. "
                "AI-generated responses should not be relied upon for "
                "safety-critical decisions."
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
