#!/usr/bin/env python3
"""
EN
ENRAGEN,EN:
1. EN
2. EN
3. EN
4. EN
5. EN
"""
import json
import math
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple


@dataclass
class TestCase:
    """EN"""

    __test__ = False

    test_id: str
    question: str
    context: str  # EN
    expected_answer_type: str  # factual, analytical, procedural, comparative
    expected_keywords: List[str]
    expected_length_range: Tuple[int, int]  # (min, max)
    difficulty: str  # easy, medium, hard
    topic: str


@dataclass
class AnswerQuality:
    """EN"""

    test_id: str
    generated_answer: str
    correctness_score: float
    fluency_score: float
    relevance_score: float
    completeness_score: float
    overall_score: float
    detailed_metrics: Dict[str, Any]


class AnswerGenerationTester:
    """EN"""

    def __init__(self):
        self.test_cases = self._generate_test_cases()
        self.test_results = []

    def _generate_test_cases(self) -> List[TestCase]:
        """EN"""
        test_cases = [
            # EN
            TestCase(
                test_id="fact_001",
                question="EN?",
                context="EN(AI)EN,EN.EN,EN,EN.",
                expected_answer_type="factual",
                expected_keywords=["EN", "EN", "EN", "EN"],
                expected_length_range=(50, 200),
                difficulty="easy",
                topic="AIEN",
            ),
            TestCase(
                test_id="fact_002",
                question="PythonEN?",
                context="PythonEN,EN,EN,EN,EN.EN,WebEN,EN.",
                expected_answer_type="factual",
                expected_keywords=["EN", "EN", "EN", "EN", "EN"],
                expected_length_range=(60, 250),
                difficulty="medium",
                topic="EN",
            ),
            # EN
            TestCase(
                test_id="analytical_001",
                question="EN",
                context="ENAIEN,EN.EN,EN,EN.EN,EN,EN.",
                expected_answer_type="analytical",
                expected_keywords=["EN", "EN", "EN", "EN", "EN"],
                expected_length_range=(100, 400),
                difficulty="hard",
                topic="EN",
            ),
            TestCase(
                test_id="analytical_002",
                question="EN",
                context="EN,EN.EN,EN,EN.",
                expected_answer_type="comparative",
                expected_keywords=["EN", "EN", "EN", "EN", "EN"],
                expected_length_range=(120, 350),
                difficulty="hard",
                topic="EN",
            ),
            # EN
            TestCase(
                test_id="procedural_001",
                question="EN?",
                context="EN,EN,EN,EN,EN.EN.",
                expected_answer_type="procedural",
                expected_keywords=["EN", "EN", "EN", "EN", "EN"],
                expected_length_range=(100, 300),
                difficulty="medium",
                topic="EN",
            ),
            TestCase(
                test_id="procedural_002",
                question="EN?",
                context="EN,APIEN,EN,EN,EN,EN,EN.",
                expected_answer_type="procedural",
                expected_keywords=["EN", "APIEN", "EN", "EN", "EN"],
                expected_length_range=(120, 350),
                difficulty="hard",
                topic="EN",
            ),
            # EN
            TestCase(
                test_id="comparative_001",
                question="EN",
                context="EN,EN,EN.EN,EN,EN.EN.",
                expected_answer_type="comparative",
                expected_keywords=["EN", "EN", "EN", "EN", "EN"],
                expected_length_range=(100, 300),
                difficulty="medium",
                topic="EN",
            ),
            # EN
            TestCase(
                test_id="reasoning_001",
                question="ENAI,EN?",
                context="AIEN,EN,EN,EN,EN,EN.",
                expected_answer_type="complex_reasoning",
                expected_keywords=["EN", "EN", "EN", "EN", "EN"],
                expected_length_range=(150, 400),
                difficulty="hard",
                topic="AIEN",
            ),
            TestCase(
                test_id="reasoning_002",
                question="EN,EN?",
                context="EN,EN.EN,EN,EN,EN.",
                expected_answer_type="complex_reasoning",
                expected_keywords=["EN", "EN", "EN", "EN", "EN"],
                expected_length_range=(120, 350),
                difficulty="hard",
                topic="EN",
            ),
        ]

        return test_cases

    def _generate_mock_answer(self, test_case: TestCase) -> str:
        """EN(ENLLMEN)"""

        # EN
        answer_templates = {
            "fact_001": "EN(AI)EN,EN,EN.AIEN,EN,EN.",
            "fact_002": "PythonEN,EN:1)EN,EN;2)EN,EN;3)EN,EN;4)EN;5)EN.",
            "analytical_001": "EN,EN,EN,EN.EN,EN:EN,EN(EN),EN,EN.",
            "analytical_002": "EN,EN:EN,EN(ENSIFT,HOGEN).EN,EN;EN,EN.",
            "procedural_001": "EN,EN:1)EN:EN,EN;2)EN:EN,EN;3)EN:EN;4)EN:EN,EN;5)EN:EN.",
            "procedural_002": "EN:1)EN,EN;2)ENAPIEN;3)EN;4)EN;5)EN,EN;6)EN;7)EN.",
            "comparative_001": "EN:EN,EN,EN,EN,EN;EN,EN,EN,EN.EN,EN,EN.",
            "reasoning_001": "ENAIEN:EN,EN,EN,EN;EN,EN,EN,EN,EN.",
            "reasoning_002": "EN:EN:1)EN;2)EN;3)EN;4)EN;5)EN;6)EN;7)EN.",
        }

        return answer_templates.get(test_case.test_id, f"EN{test_case.topic}EN,EN.")

    def evaluate_correctness(self, answer: str, test_case: TestCase) -> float:
        """EN"""
        score = 0.0

        # 1. EN (40%)
        factual_accuracy = self._check_factual_accuracy(answer, test_case)
        score += factual_accuracy * 0.4

        # 2. EN (30%)
        logical_consistency = self._check_logical_consistency(answer, test_case)
        score += logical_consistency * 0.3

        # 3. EN (30%)
        content_completeness = self._check_content_completeness(answer, test_case)
        score += content_completeness * 0.3

        return min(score, 1.0)

    def evaluate_fluency(self, answer: str) -> float:
        """EN"""
        score = 0.0

        # 1. EN (25%)
        grammar_score = self._check_grammar(answer)
        score += grammar_score * 0.25

        # 2. EN (25%)
        naturalness_score = self._check_naturalness(answer)
        score += naturalness_score * 0.25

        # 3. EN (25%)
        coherence_score = self._check_coherence(answer)
        score += coherence_score * 0.25

        # 4. EN (25%)
        length_score = self._check_length_appropriateness(answer)
        score += length_score * 0.25

        return min(score, 1.0)

    def evaluate_relevance(self, answer: str, test_case: TestCase) -> float:
        """EN"""
        score = 0.0

        # 1. EN (40%)
        question_match = self._check_question_relevance(answer, test_case.question)
        score += question_match * 0.4

        # 2. EN (30%)
        context_consistency = self._check_context_consistency(answer, test_case.context)
        score += context_consistency * 0.3

        # 3. EN (30%)
        keyword_coverage = self._check_keyword_coverage(
            answer, test_case.expected_keywords
        )
        score += keyword_coverage * 0.3

        return min(score, 1.0)

    def _check_factual_accuracy(self, answer: str, test_case: TestCase) -> float:
        """EN"""
        # EN
        error_patterns = [
            r"EN.*EN",  # ENAIEN
            r"EN.*EN",  # ENMLEN
            r"EN.*EN",  # EN
        ]

        has_errors = any(
            re.search(pattern, answer, re.IGNORECASE) for pattern in error_patterns
        )
        if has_errors:
            return 0.3

        # EN
        keyword_score = self._check_keyword_coverage(
            answer, test_case.expected_keywords
        )
        return keyword_score

    def _check_logical_consistency(self, answer: str, test_case: TestCase) -> float:
        """EN"""
        # EN
        contradiction_patterns = [
            r"(EN|EN).*EN.*(EN|EN)",  # EN
            r"EN.*EN",  # EN
        ]

        has_contradictions = any(
            re.search(pattern, answer, re.IGNORECASE)
            for pattern in contradiction_patterns
        )
        if has_contradictions:
            return 0.5

        # EN
        sentences = re.split(r"[.!?]", answer)
        logical_sentences = sum(1 for s in sentences if len(s.strip()) > 5)
        total_sentences = len([s for s in sentences if s.strip()])

        if total_sentences == 0:
            return 0.0

        return min(logical_sentences / total_sentences, 1.0)

    def _check_content_completeness(self, answer: str, test_case: TestCase) -> float:
        """EN"""
        # EN
        answer_length = len(answer)
        min_len, max_len = test_case.expected_length_range

        if min_len <= answer_length <= max_len:
            length_score = 1.0
        elif answer_length < min_len:
            length_score = answer_length / min_len
        else:
            length_score = max_len / answer_length

        # EN
        key_aspects_score = self._check_keyword_coverage(
            answer, test_case.expected_keywords
        )

        return (length_score + key_aspects_score) / 2

    def _check_grammar(self, text: str) -> float:
        """EN"""
        # EN
        issues = 0

        # EN
        if not re.search(r"[.!?]$", text.strip()):
            issues += 1

        # EN
        if re.search(r"(.)\1{3,}", text):
            issues += 1

        # EN
        if re.search(r"[a-zA-Z]\s*[a-zA-Z]\s*[a-zA-Z]", text):  # EN
            pass  # EN
        if re.search(r",,|..", text):  # EN
            issues += 1

        # EN
        total_checks = 3
        grammar_score = max(0, (total_checks - issues) / total_checks)

        return grammar_score

    def _check_naturalness(self, text: str) -> float:
        """EN"""
        # EN
        sentences = re.split(r"[.!?]", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        # EN
        avg_length = sum(len(s) for s in sentences) / len(sentences)

        # EN15-50EN
        if 15 <= avg_length <= 50:
            length_score = 1.0
        elif avg_length < 15:
            length_score = avg_length / 15
        else:
            length_score = max(0, 1 - (avg_length - 50) / 100)

        # EN
        connectors = ["EN", "EN", "EN", "EN", "EN", "EN", "EN", "EN"]
        connector_count = sum(1 for conn in connectors if conn in text)

        # EN
        if 1 <= connector_count <= 3:
            connector_score = 1.0
        elif connector_count == 0:
            connector_score = 0.7
        else:
            connector_score = max(0, 1 - (connector_count - 3) * 0.2)

        return (length_score + connector_score) / 2

    def _check_coherence(self, text: str) -> float:
        """EN"""
        # EN
        sequence_words = ["EN", "EN", "EN", "EN", "EN", "EN", "EN", "1)", "2)", "3)"]
        has_sequence = any(word in text for word in sequence_words)

        # EN
        summary_words = ["EN", "EN", "EN", "EN", "EN"]
        has_summary = any(word in text for word in summary_words)

        # EN(EN)
        sentences = re.split(r"[.!?]", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            return 0.5

        # EN:EN
        structure_score = 0.5
        if has_sequence:
            structure_score += 0.3
        if has_summary:
            structure_score += 0.2

        return min(structure_score, 1.0)

    def _check_length_appropriateness(self, text: str) -> float:
        """EN"""
        length = len(text)

        # EN100-500EN
        if 100 <= length <= 500:
            return 1.0
        elif length < 100:
            return length / 100
        else:
            return max(0, 1 - (length - 500) / 1000)

    def _check_question_relevance(self, answer: str, question: str) -> float:
        """EN"""
        # EN
        question_words = set(re.findall(r"[\u4e00-\u9fff]+", question))

        # EN
        answer_words = set(re.findall(r"[\u4e00-\u9fff]+", answer))

        if not question_words:
            return 0.5

        overlap = len(question_words & answer_words)
        relevance_score = overlap / len(question_words)

        # EN
        if any(word in answer for word in ["EN", "EN", "EN", "EN", "EN", "EN"]):
            relevance_score += 0.2

        return min(relevance_score, 1.0)

    def _check_context_consistency(self, answer: str, context: str) -> float:
        """EN"""
        # EN
        context_words = set(re.findall(r"[\u4e00-\u9fff]+", context))
        answer_words = set(re.findall(r"[\u4e00-\u9fff]+", answer))

        if not context_words:
            return 0.8  # EN

        overlap = len(context_words & answer_words)
        consistency_score = overlap / min(len(context_words), 50)  # EN

        # EN
        contradiction_indicators = ["EN", "EN", "EN", "EN"]
        has_contradiction = any(
            indicator in answer for indicator in contradiction_indicators
        )

        if has_contradiction:
            consistency_score *= 0.5

        return min(consistency_score, 1.0)

    def _check_keyword_coverage(self, answer: str, keywords: List[str]) -> float:
        """EN"""
        if not keywords:
            return 1.0

        covered_keywords = sum(1 for keyword in keywords if keyword in answer)
        coverage_score = covered_keywords / len(keywords)

        return coverage_score

    def test_answer_generation_quality(self) -> Dict[str, Any]:
        """EN"""
        print("🔍 EN...")

        results = []

        for test_case in self.test_cases:
            print(f"  📝 EN: {test_case.test_id}")

            # EN
            generated_answer = self._generate_mock_answer(test_case)

            # EN
            correctness_score = self.evaluate_correctness(generated_answer, test_case)
            fluency_score = self.evaluate_fluency(generated_answer)
            relevance_score = self.evaluate_relevance(generated_answer, test_case)
            completeness_score = self._check_content_completeness(
                generated_answer, test_case
            )

            # EN
            overall_score = (
                correctness_score * 0.3
                + fluency_score * 0.2
                + relevance_score * 0.3
                + completeness_score * 0.2
            )

            # EN
            detailed_metrics = {
                "answer_length": len(generated_answer),
                "keyword_coverage": self._check_keyword_coverage(
                    generated_answer, test_case.expected_keywords
                ),
                "grammar_score": self._check_grammar(generated_answer),
                "naturalness_score": self._check_naturalness(generated_answer),
                "coherence_score": self._check_coherence(generated_answer),
            }

            quality_result = AnswerQuality(
                test_id=test_case.test_id,
                generated_answer=generated_answer,
                correctness_score=correctness_score,
                fluency_score=fluency_score,
                relevance_score=relevance_score,
                completeness_score=completeness_score,
                overall_score=overall_score,
                detailed_metrics=detailed_metrics,
            )

            results.append(quality_result)
            print(
                f"    ✅ EN: {overall_score:.3f} (EN:{correctness_score:.3f}, EN:{fluency_score:.3f}, EN:{relevance_score:.3f})"
            )

        return {"total_tests": len(results), "results": results}

    def analyze_performance_by_answer_type(
        self, results: List[AnswerQuality]
    ) -> Dict[str, Any]:
        """EN"""
        type_groups = defaultdict(list)

        for result in results:
            test_case = next(
                tc for tc in self.test_cases if tc.test_id == result.test_id
            )
            type_groups[test_case.expected_answer_type].append(result)

        type_analysis = {}

        for answer_type, type_results in type_groups.items():
            if not type_results:
                continue

            avg_scores = {
                "correctness": sum(r.correctness_score for r in type_results)
                / len(type_results),
                "fluency": sum(r.fluency_score for r in type_results)
                / len(type_results),
                "relevance": sum(r.relevance_score for r in type_results)
                / len(type_results),
                "completeness": sum(r.completeness_score for r in type_results)
                / len(type_results),
                "overall": sum(r.overall_score for r in type_results)
                / len(type_results),
            }

            type_analysis[answer_type] = {
                "count": len(type_results),
                "average_scores": avg_scores,
            }

        return type_analysis

    def test_generation_speed(self) -> Dict[str, Any]:
        """EN"""
        print("\n🔍 EN...")

        generation_times = []

        for i, test_case in enumerate(self.test_cases[:5]):  # EN5EN
            start_time = time.time()

            # EN
            generated_answer = self._generate_mock_answer(test_case)

            generation_time = time.time() - start_time
            generation_times.append(generation_time)

            print(
                f"  ⏱️  EN {i+1}: {generation_time:.4f}s ({len(generated_answer)} EN)"
            )

        avg_time = sum(generation_times) / len(generation_times)
        min_time = min(generation_times)
        max_time = max(generation_times)

        return {
            "average_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "total_tests": len(generation_times),
        }

    def run_all_tests(self) -> Dict[str, Any]:
        """EN"""
        print("🚀 EN\n")
        print("=" * 60)

        start_time = time.time()

        # 1. EN
        quality_results = self.test_answer_generation_quality()

        # 2. EN
        type_analysis = self.analyze_performance_by_answer_type(
            quality_results["results"]
        )

        # 3. EN
        speed_results = self.test_generation_speed()

        end_time = time.time()
        total_time = end_time - start_time

        # EN
        overall_correctness = sum(
            r.correctness_score for r in quality_results["results"]
        ) / len(quality_results["results"])
        overall_fluency = sum(
            r.fluency_score for r in quality_results["results"]
        ) / len(quality_results["results"])
        overall_relevance = sum(
            r.relevance_score for r in quality_results["results"]
        ) / len(quality_results["results"])
        overall_quality = sum(
            r.overall_score for r in quality_results["results"]
        ) / len(quality_results["results"])

        summary = {
            "test_execution_time": total_time,
            "overall_metrics": {
                "correctness": overall_correctness,
                "fluency": overall_fluency,
                "relevance": overall_relevance,
                "overall_quality": overall_quality,
            },
            "quality_results": quality_results,
            "type_analysis": type_analysis,
            "speed_results": speed_results,
        }

        return summary

    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """EN"""
        overall = results["overall_metrics"]

        report = f"""
# EN

## EN
- **EN**: {results['test_execution_time']:.2f} EN
- **EN**: {results['quality_results']['total_tests']}

## EN
- **EN**: {overall['correctness']:.3f}/1.000
- **EN**: {overall['fluency']:.3f}/1.000
- **EN**: {overall['relevance']:.3f}/1.000
- **EN**: {overall['overall_quality']:.3f}/1.000

## EN
"""

        for answer_type, analysis in results["type_analysis"].items():
            scores = analysis["average_scores"]
            report += f"- **{answer_type}** (n={analysis['count']}):\n"
            report += f"  - EN: {scores['correctness']:.3f}\n"
            report += f"  - EN: {scores['fluency']:.3f}\n"
            report += f"  - EN: {scores['relevance']:.3f}\n"
            report += f"  - EN: {scores['completeness']:.3f}\n"
            report += f"  - EN: {scores['overall']:.3f}\n"

        report += f"""
## EN
- **EN**: {results['speed_results']['average_time']:.4f}s
- **EN**: {results['speed_results']['min_time']:.4f}s
- **EN**: {results['speed_results']['max_time']:.4f}s

## EN
"""

        # EN
        for i, result in enumerate(results["quality_results"]["results"][:5]):  # EN5EN
            report += f"""
### {result.test_id}
- **EN**: {result.detailed_metrics['answer_length']} EN
- **EN**: {result.detailed_metrics['keyword_coverage']:.3f}
- **EN**: {result.detailed_metrics['grammar_score']:.3f}
- **EN**: {result.detailed_metrics['naturalness_score']:.3f}
- **EN**: {result.detailed_metrics['coherence_score']:.3f}
- **EN**: {result.generated_answer[:100]}...
"""

        report += f"""
## EN
"""

        if overall["overall_quality"] >= 0.8:
            report += "✅ **EN**: EN,EN\n"
        elif overall["overall_quality"] >= 0.6:
            report += "⚠️ **EN**: EN,EN\n"
        else:
            report += "❌ **EN**: EN\n"

        report += f"""
## EN
1. **EN**: EN {overall['correctness']:.1%},EN
2. **EN**: EN {overall['fluency']:.1%},EN
3. **EN**: EN {overall['relevance']:.1%},EN
4. **EN**: EN

## EN
- EN
- EN
- EN
- EN
"""

        return report


def main():
    """EN"""
    tester = AnswerGenerationTester()

    # EN
    results = tester.run_all_tests()

    # EN
    report = tester.generate_test_report(results)

    # EN
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # ENJSONEN
    with open(
        f"test_results/answer_generation_results_{timestamp}.json",
        "w",
        encoding="utf-8",
    ) as f:
        # ENAnswerQualityEN
        serializable_results = {
            "test_execution_time": results["test_execution_time"],
            "overall_metrics": results["overall_metrics"],
            "type_analysis": results["type_analysis"],
            "speed_results": results["speed_results"],
            "quality_summary": {
                "total_tests": results["quality_results"]["total_tests"],
                "average_correctness": results["overall_metrics"]["correctness"],
                "average_fluency": results["overall_metrics"]["fluency"],
                "average_relevance": results["overall_metrics"]["relevance"],
                "average_quality": results["overall_metrics"]["overall_quality"],
            },
        }
        json.dump(serializable_results, f, indent=2, ensure_ascii=False)

    # EN
    with open(
        f"test_results/answer_generation_report_{timestamp}.md", "w", encoding="utf-8"
    ) as f:
        f.write(report)

    # EN
    print("\n" + "=" * 60)
    print("🎯 EN!")
    print("=" * 60)
    print(f"📊 EN: {results['overall_metrics']['overall_quality']:.3f}/1.000")
    print(f"✅ EN: {results['overall_metrics']['correctness']:.3f}")
    print(f"💬 EN: {results['overall_metrics']['fluency']:.3f}")
    print(f"🎯 EN: {results['overall_metrics']['relevance']:.3f}")
    print(f"⏱️  EN: {results['speed_results']['average_time']:.4f}s")
    print(f"\n📄 EN: test_results/answer_generation_report_{timestamp}.md")

    return results["overall_metrics"]["overall_quality"] >= 0.6


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
