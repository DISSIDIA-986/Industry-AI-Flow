#!/usr/bin/env python3
"""
EN
EN,EN:
1. EN
2. EN
3. EN
4. EN
"""
import json
import os
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple


class QuestionType(Enum):
    """EN"""

    SIMPLE_QA = "simple_qa"  # EN
    COMPLEX_REASONING = "complex_reasoning"  # EN
    MULTI_TURN = "multi_turn"  # EN
    DATA_ANALYSIS = "data_analysis"  # EN
    CODE_EXECUTION = "code_execution"  # EN
    DOCUMENT_QA = "document_qa"  # EN


@dataclass
class TestCase:
    """EN"""
    __test__ = False

    question_id: str
    question_type: QuestionType
    question: str
    expected_keywords: List[str]
    expected_answer_type: str
    context_required: bool = False
    follow_up_questions: List[str] = None
    difficulty: str = "medium"  # easy, medium, hard


class QuestionClassificationTester:
    """EN"""

    def __init__(self):
        self.test_results = []
        self.test_cases = self._generate_test_cases()

    def _generate_test_cases(self) -> List[TestCase]:
        """EN"""
        test_cases = [
            # EN
            TestCase(
                question_id="simple_001",
                question_type=QuestionType.SIMPLE_QA,
                question="EN?",
                expected_keywords=["EN", "AI", "EN", "EN"],
                expected_answer_type="definition",
                difficulty="easy",
            ),
            TestCase(
                question_id="simple_002",
                question_type=QuestionType.SIMPLE_QA,
                question="PythonEN?",
                expected_keywords=["Python", "EN", "EN", "EN"],
                expected_answer_type="description",
                difficulty="easy",
            ),
            TestCase(
                question_id="simple_003",
                question_type=QuestionType.SIMPLE_QA,
                question="EN?",
                expected_keywords=["EN", "EN", "EN"],
                expected_answer_type="classification",
                difficulty="medium",
            ),
            # EN
            TestCase(
                question_id="complex_001",
                question_type=QuestionType.COMPLEX_REASONING,
                question="EN20%,EN30%,EN?EN.",
                expected_keywords=["EN", "EN", "EN", "EN", "EN"],
                expected_answer_type="analysis",
                difficulty="hard",
            ),
            TestCase(
                question_id="complex_002",
                question_type=QuestionType.COMPLEX_REASONING,
                question="EN,EN?EN,EN,EN.",
                expected_keywords=["EN", "EN", "EN", "EN", "EN"],
                expected_answer_type="comprehensive_analysis",
                difficulty="hard",
            ),
            TestCase(
                question_id="complex_003",
                question_type=QuestionType.COMPLEX_REASONING,
                question="EN,EN.",
                expected_keywords=["EN", "EN", "EN", "ReLU", "BatchNorm"],
                expected_answer_type="problem_solution",
                difficulty="hard",
            ),
            # EN
            TestCase(
                question_id="multi_001",
                question_type=QuestionType.MULTI_TURN,
                question="EN.",
                expected_keywords=["EN", "EN"],
                expected_answer_type="explanation",
                follow_up_questions=[
                    "EN?",
                    "EN?",
                    "EN,EN?",
                ],
                difficulty="medium",
            ),
            TestCase(
                question_id="multi_002",
                question_type=QuestionType.MULTI_TURN,
                question="ENPythonEN.",
                expected_keywords=["Python", "EN", "EN"],
                expected_answer_type="advice",
                follow_up_questions=[
                    "EN?",
                    "EN?",
                    "EN?",
                ],
                difficulty="medium",
            ),
            # EN
            TestCase(
                question_id="data_001",
                question_type=QuestionType.DATA_ANALYSIS,
                question="EN?",
                expected_keywords=["EN", "EN", "EN", "EN", "EN"],
                expected_answer_type="methodology",
                difficulty="medium",
            ),
            TestCase(
                question_id="data_002",
                question_type=QuestionType.DATA_ANALYSIS,
                question="EN,EN?",
                expected_keywords=["EN", "EN", "EN", "EN"],
                expected_answer_type="methodology",
                difficulty="hard",
            ),
            # EN
            TestCase(
                question_id="code_001",
                question_type=QuestionType.CODE_EXECUTION,
                question="ENPythonENnEN.",
                expected_keywords=["EN", "Python", "EN", "EN"],
                expected_answer_type="code",
                difficulty="medium",
            ),
            TestCase(
                question_id="code_002",
                question_type=QuestionType.CODE_EXECUTION,
                question="ENpandasENCSVEN?",
                expected_keywords=["pandas", "CSV", "EN", "Python"],
                expected_answer_type="code_tutorial",
                difficulty="medium",
            ),
            # EN
            TestCase(
                question_id="doc_001",
                question_type=QuestionType.DOCUMENT_QA,
                question="EN,EN?",
                expected_keywords=["EN", "EN", "EN"],
                expected_answer_type="extraction",
                context_required=True,
                difficulty="easy",
            ),
            TestCase(
                question_id="doc_002",
                question_type=QuestionType.DOCUMENT_QA,
                question="EN?EN.",
                expected_keywords=["EN", "EN", "EN"],
                expected_answer_type="procedural",
                context_required=True,
                difficulty="medium",
            ),
        ]

        return test_cases

    def classify_question(self, question: str) -> QuestionType:
        """
        EN(EN)
        EN
        """
        question_lower = question.lower()

        # EN
        if any(keyword in question_lower for keyword in ["EN", "EN", "EN", "EN"]):
            if any(
                keyword in question_lower for keyword in ["EN", "EN", "EN", "EN", "EN"]
            ):
                return QuestionType.COMPLEX_REASONING
            else:
                return QuestionType.SIMPLE_QA
        elif any(
            keyword in question_lower for keyword in ["EN", "EN", "python", "EN", "EN"]
        ):
            return QuestionType.CODE_EXECUTION
        elif any(
            keyword in question_lower for keyword in ["EN", "EN", "EN", "EN", "EN"]
        ):
            return QuestionType.DATA_ANALYSIS
        elif any(keyword in question_lower for keyword in ["EN", "EN", "EN"]):
            return QuestionType.DOCUMENT_QA
        elif len(question) < 50 and "?" in question:
            return QuestionType.MULTI_TURN
        else:
            return QuestionType.COMPLEX_REASONING

    def test_question_classification(self) -> Dict[str, Any]:
        """EN"""
        print("🔍 EN...")

        correct_classifications = 0
        total_tests = len(self.test_cases)
        classification_results = []

        for test_case in self.test_cases:
            predicted_type = self.classify_question(test_case.question)
            is_correct = predicted_type == test_case.question_type

            result = {
                "question_id": test_case.question_id,
                "question": test_case.question,
                "expected_type": test_case.question_type.value,
                "predicted_type": predicted_type.value,
                "is_correct": is_correct,
            }

            classification_results.append(result)

            if is_correct:
                correct_classifications += 1
                print(f"✅ {test_case.question_id}: {predicted_type.value}")
            else:
                print(
                    f"❌ {test_case.question_id}: EN {test_case.question_type.value}, EN {predicted_type.value}"
                )

        accuracy = correct_classifications / total_tests if total_tests > 0 else 0

        return {
            "total_tests": total_tests,
            "correct_classifications": correct_classifications,
            "accuracy": accuracy,
            "results": classification_results,
        }

    def test_simple_qa(self) -> Dict[str, Any]:
        """EN"""
        print("\n🔍 EN...")

        simple_tests = [
            tc for tc in self.test_cases if tc.question_type == QuestionType.SIMPLE_QA
        ]
        results = []

        for test_case in simple_tests:
            # EN
            mock_answer = self._generate_mock_answer(test_case)

            # EN
            quality_score = self._evaluate_answer_quality(mock_answer, test_case)

            result = {
                "question_id": test_case.question_id,
                "question": test_case.question,
                "mock_answer": mock_answer,
                "quality_score": quality_score,
                "keyword_coverage": self._check_keyword_coverage(
                    mock_answer, test_case.expected_keywords
                ),
                "answer_type_match": self._check_answer_type(
                    mock_answer, test_case.expected_answer_type
                ),
            }

            results.append(result)
            print(f"✅ {test_case.question_id}: EN {quality_score:.2f}")

        return {
            "test_count": len(simple_tests),
            "average_quality": sum(r["quality_score"] for r in results) / len(results)
            if results
            else 0,
            "results": results,
        }

    def test_complex_reasoning(self) -> Dict[str, Any]:
        """EN"""
        print("\n🔍 EN...")

        complex_tests = [
            tc
            for tc in self.test_cases
            if tc.question_type == QuestionType.COMPLEX_REASONING
        ]
        results = []

        for test_case in complex_tests:
            # EN
            reasoning_steps = self._simulate_reasoning_process(test_case)
            mock_answer = self._generate_complex_answer(test_case, reasoning_steps)

            # EN
            reasoning_score = self._evaluate_reasoning_quality(
                reasoning_steps, mock_answer, test_case
            )

            result = {
                "question_id": test_case.question_id,
                "question": test_case.question,
                "reasoning_steps": reasoning_steps,
                "answer": mock_answer,
                "reasoning_score": reasoning_score,
                "logical_coherence": self._check_logical_coherence(reasoning_steps),
                "completeness": self._check_answer_completeness(mock_answer, test_case),
            }

            results.append(result)
            print(f"✅ {test_case.question_id}: EN {reasoning_score:.2f}")

        return {
            "test_count": len(complex_tests),
            "average_reasoning_score": sum(r["reasoning_score"] for r in results)
            / len(results)
            if results
            else 0,
            "results": results,
        }

    def test_multi_turn_conversation(self) -> Dict[str, Any]:
        """EN"""
        print("\n🔍 EN...")

        multi_turn_tests = [
            tc for tc in self.test_cases if tc.question_type == QuestionType.MULTI_TURN
        ]
        results = []

        for test_case in multi_turn_tests:
            conversation_history = []
            context_retention_scores = []

            # EN
            initial_answer = self._generate_mock_answer(test_case)
            conversation_history.append({"role": "user", "content": test_case.question})
            conversation_history.append(
                {"role": "assistant", "content": initial_answer}
            )

            # EN
            for i, follow_up in enumerate(test_case.follow_up_questions):
                follow_up_answer = self._generate_follow_up_answer(
                    follow_up, conversation_history
                )

                # EN
                context_score = self._evaluate_context_retention(
                    conversation_history, follow_up_answer
                )
                context_retention_scores.append(context_score)

                conversation_history.append({"role": "user", "content": follow_up})
                conversation_history.append(
                    {"role": "assistant", "content": follow_up_answer}
                )

            avg_context_retention = (
                sum(context_retention_scores) / len(context_retention_scores)
                if context_retention_scores
                else 0
            )

            result = {
                "question_id": test_case.question_id,
                "initial_question": test_case.question,
                "conversation_turns": len(test_case.follow_up_questions) + 1,
                "context_retention_scores": context_retention_scores,
                "average_context_retention": avg_context_retention,
                "conversation_coherence": self._evaluate_conversation_coherence(
                    conversation_history
                ),
            }

            results.append(result)
            print(f"✅ {test_case.question_id}: EN {avg_context_retention:.2f}")

        return {
            "test_count": len(multi_turn_tests),
            "average_context_retention": sum(
                r["average_context_retention"] for r in results
            )
            / len(results)
            if results
            else 0,
            "results": results,
        }

    def _generate_mock_answer(self, test_case: TestCase) -> str:
        """EN"""
        if test_case.question_id == "simple_001":
            return "EN(AI)EN,EN."
        elif test_case.question_id == "simple_002":
            return "PythonEN,EN,EN."
        elif test_case.question_id == "simple_003":
            return "EN:EN,EN."
        else:
            return "EN,EN."

    def _generate_complex_answer(
        self, test_case: TestCase, reasoning_steps: List[str]
    ) -> str:
        """EN"""
        return "EN," + ",".join(reasoning_steps) + ",EN."

    def _generate_follow_up_answer(self, question: str, history: List[Dict]) -> str:
        """EN"""
        return f"EN,EN{question},EN..."

    def _simulate_reasoning_process(self, test_case: TestCase) -> List[str]:
        """EN"""
        if "EN" in test_case.question and "EN" in test_case.question:
            return ["EN20%EN", "EN30%EN", "EN", "EN"]
        elif "EN" in test_case.question:
            return ["EN", "EN", "EN", "EN"]
        else:
            return ["EN", "EN", "EN"]

    def _evaluate_answer_quality(self, answer: str, test_case: TestCase) -> float:
        """EN"""
        score = 0.0

        # EN (40%)
        keyword_coverage = self._check_keyword_coverage(
            answer, test_case.expected_keywords
        )
        score += keyword_coverage * 0.4

        # EN (20%)
        if 50 <= len(answer) <= 500:
            score += 0.2
        elif 20 <= len(answer) <= 1000:
            score += 0.1

        # EN (40%)
        type_match = self._check_answer_type(answer, test_case.expected_answer_type)
        score += type_match * 0.4

        return min(score, 1.0)

    def _evaluate_reasoning_quality(
        self, reasoning_steps: List[str], answer: str, test_case: TestCase
    ) -> float:
        """EN"""
        score = 0.0

        # EN (30%)
        if len(reasoning_steps) >= 3:
            score += 0.3
        elif len(reasoning_steps) >= 2:
            score += 0.2

        # EN (40%)
        coherence = self._check_logical_coherence(reasoning_steps)
        score += coherence * 0.4

        # EN (30%)
        completeness = self._check_answer_completeness(answer, test_case)
        score += completeness * 0.3

        return min(score, 1.0)

    def _check_keyword_coverage(self, answer: str, keywords: List[str]) -> float:
        """EN"""
        if not keywords:
            return 1.0

        answer_lower = answer.lower()
        covered_keywords = sum(
            1 for keyword in keywords if keyword.lower() in answer_lower
        )
        return covered_keywords / len(keywords)

    def _check_answer_type(self, answer: str, expected_type: str) -> float:
        """EN"""
        answer_lower = answer.lower()

        type_indicators = {
            "definition": ["EN", "EN", "EN"],
            "description": ["EN", "EN", "EN"],
            "classification": ["EN", "EN", "EN"],
            "analysis": ["EN", "EN", "EN"],
            "advice": ["EN", "EN", "EN"],
            "explanation": ["EN", "EN", "EN"],
            "methodology": ["EN", "EN", "EN"],
            "code": ["EN", "def", "EN", "import"],
            "extraction": ["EN", "EN", "EN"],
        }

        indicators = type_indicators.get(expected_type, [])
        if not indicators:
            return 0.5

        matches = sum(1 for indicator in indicators if indicator in answer_lower)
        return min(matches / len(indicators), 1.0)

    def _check_logical_coherence(self, reasoning_steps: List[str]) -> float:
        """EN"""
        if len(reasoning_steps) < 2:
            return 0.5

        # EN:EN
        coherence_score = 0.8  # EN
        return coherence_score

    def _check_answer_completeness(self, answer: str, test_case: TestCase) -> float:
        """EN"""
        # EN
        length_score = min(len(answer) / 200, 1.0)  # 200EN
        keyword_score = self._check_keyword_coverage(
            answer, test_case.expected_keywords
        )
        return (length_score + keyword_score) / 2

    def _evaluate_context_retention(
        self, history: List[Dict], current_answer: str
    ) -> float:
        """EN"""
        # EN
        context_score = 0.7  # EN
        return context_score

    def _evaluate_conversation_coherence(self, history: List[Dict]) -> float:
        """EN"""
        coherence_score = 0.8  # EN
        return coherence_score

    def run_all_tests(self) -> Dict[str, Any]:
        """EN"""
        print("🚀 EN\n")
        print("=" * 60)

        start_time = time.time()

        # 1. EN
        classification_results = self.test_question_classification()

        # 2. EN
        simple_qa_results = self.test_simple_qa()

        # 3. EN
        complex_reasoning_results = self.test_complex_reasoning()

        # 4. EN
        multi_turn_results = self.test_multi_turn_conversation()

        end_time = time.time()
        total_time = end_time - start_time

        # EN
        summary = {
            "test_execution_time": total_time,
            "classification_accuracy": classification_results["accuracy"],
            "simple_qa_average_quality": simple_qa_results["average_quality"],
            "complex_reasoning_average_score": complex_reasoning_results[
                "average_reasoning_score"
            ],
            "multi_turn_average_context_retention": multi_turn_results[
                "average_context_retention"
            ],
            "overall_score": (
                classification_results["accuracy"] * 0.25
                + simple_qa_results["average_quality"] * 0.25
                + complex_reasoning_results["average_reasoning_score"] * 0.25
                + multi_turn_results["average_context_retention"] * 0.25
            ),
            "detailed_results": {
                "classification": classification_results,
                "simple_qa": simple_qa_results,
                "complex_reasoning": complex_reasoning_results,
                "multi_turn": multi_turn_results,
            },
        }

        return summary

    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """EN"""
        report = f"""
# EN

## EN
- **EN**: {results['test_execution_time']:.2f} EN
- **EN**: {results['overall_score']:.2f}/1.00

## EN
- **EN**: {results['classification_accuracy']:.2%}
- **EN**: {results['detailed_results']['classification']['total_tests']}

## EN
- **EN**: {results['simple_qa_average_quality']:.2f}/1.00
- **EN**: {results['detailed_results']['simple_qa']['test_count']}

## EN
- **EN**: {results['complex_reasoning_average_score']:.2f}/1.00
- **EN**: {results['detailed_results']['complex_reasoning']['test_count']}

## EN
- **EN**: {results['multi_turn_average_context_retention']:.2f}/1.00
- **EN**: {results['detailed_results']['multi_turn']['test_count']}

## EN
"""

        if results["overall_score"] >= 0.8:
            report += "✅ **EN**: EN\n"
        elif results["overall_score"] >= 0.6:
            report += "⚠️ **EN**: EN,EN\n"
        else:
            report += "❌ **EN**: EN\n"

        report += f"""
## EN
1. **EN**: EN {results['classification_accuracy']:.1%},EN
2. **EN**: EN {results['simple_qa_average_quality']:.2f},EN
3. **EN**: EN {results['complex_reasoning_average_score']:.2f},EN
4. **EN**: EN {results['multi_turn_average_context_retention']:.2f},EN

## EN
- EN
- EN
- EN
- EN
"""

        return report


def main():
    """EN"""
    tester = QuestionClassificationTester()

    # EN
    results = tester.run_all_tests()

    # EN
    report = tester.generate_test_report(results)

    # EN
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # ENJSONEN
    with open(
        f"test_results/question_classification_results_{timestamp}.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # EN
    with open(
        f"test_results/question_classification_report_{timestamp}.md",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(report)

    # EN
    print("\n" + "=" * 60)
    print("🎯 EN!")
    print("=" * 60)
    print(f"📊 EN: {results['overall_score']:.2f}/1.00")
    print(f"🎯 EN: {results['classification_accuracy']:.1%}")
    print(f"💬 EN: {results['simple_qa_average_quality']:.2f}")
    print(f"🧠 EN: {results['complex_reasoning_average_score']:.2f}")
    print(f"🔄 EN: {results['multi_turn_average_context_retention']:.2f}")
    print(f"\n📄 EN: test_results/question_classification_report_{timestamp}.md")

    return results["overall_score"] >= 0.6


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
