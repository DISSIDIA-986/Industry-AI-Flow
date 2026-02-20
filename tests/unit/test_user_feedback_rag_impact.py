#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User Feedback Impact on RAG System Testing Suite

ENRAGEN
EN,EN,EN,EN
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest


class FeedbackType(Enum):
    """EN"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    DETAILED = "detailed"
    CORRECTION = "correction"
    RATING = "rating"


class FeedbackCategory(Enum):
    """EN"""

    ANSWER_QUALITY = "answer_quality"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    ACCURACY = "accuracy"
    SOURCE_QUALITY = "source_quality"
    RESPONSE_TIME = "response_time"


class LearningAlgorithm(Enum):
    """EN"""

    REINFORCEMENT_LEARNING = "reinforcement_learning"
    GRADIENT_DESCENT = "gradient_descent"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    ONLINE_LEARNING = "online_learning"
    ACTIVE_LEARNING = "active_learning"


@dataclass
class UserFeedback:
    """EN"""

    id: str
    query: str
    answer: str
    feedback_type: FeedbackType
    category: FeedbackCategory
    rating: float  # 0.0-1.0
    comment: str = ""
    correction: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    user_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGPerformanceMetrics:
    """RAGEN"""

    retrieval_accuracy: float = 0.0
    answer_relevance: float = 0.0
    user_satisfaction: float = 0.0
    response_time: float = 0.0
    coverage: float = 0.0
    diversity: float = 0.0


@dataclass
class FeedbackTestCase:
    """EN"""

    name: str
    description: str
    feedback_scenarios: List[UserFeedback]
    learning_algorithm: LearningAlgorithm
    expected_improvement: Dict[str, float]
    test_duration: int = 300  # EN
    improvement_threshold: float = 0.1


@dataclass
class FeedbackTestResult:
    """EN"""

    test_case: str
    learning_algorithm: str
    baseline_metrics: RAGPerformanceMetrics
    improved_metrics: RAGPerformanceMetrics
    improvements: Dict[str, float]
    learning_efficiency: float
    convergence_time: float
    success: bool
    feedback_processed: int
    error_message: str = ""


class MockRAGSystem:
    """ENRAGEN"""

    def __init__(self):
        self.vector_database = {}  # EN
        self.retrieval_weights = np.random.rand(100)  # EN
        self.generation_params = {"temperature": 0.7, "max_tokens": 2000, "top_p": 0.9}
        self.performance_history = []
        self.learning_rate = 0.01

    def retrieve_documents(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """EN"""
        # EN
        docs = [f"EN1: EN{query}EN", f"EN2: {query}EN", f"EN3: {query}EN"]
        scores = np.random.dirichlet(np.ones(len(docs)), size=1)[0]
        return list(zip(docs, scores.tolist()))

    def generate_answer(self, query: str, retrieved_docs: List[str]) -> str:
        """EN"""
        # EN
        context = " ".join(retrieved_docs)
        return f"EN,EN'{query}'EN:{context[:100]}..."

    def get_current_performance(self) -> RAGPerformanceMetrics:
        """EN"""
        return RAGPerformanceMetrics(
            retrieval_accuracy=np.random.uniform(0.6, 0.9),
            answer_relevance=np.random.uniform(0.5, 0.8),
            user_satisfaction=np.random.uniform(0.4, 0.7),
            response_time=np.random.uniform(0.5, 2.0),
            coverage=np.random.uniform(0.7, 0.9),
            diversity=np.random.uniform(0.6, 0.8),
        )

    def update_from_feedback(
        self, feedback: UserFeedback, algorithm: LearningAlgorithm
    ):
        """EN"""
        if algorithm == LearningAlgorithm.REINFORCEMENT_LEARNING:
            self._reinforcement_update(feedback)
        elif algorithm == LearningAlgorithm.GRADIENT_DESCENT:
            self._gradient_descent_update(feedback)
        elif algorithm == LearningAlgorithm.BAYESIAN_OPTIMIZATION:
            self._bayesian_update(feedback)
        elif algorithm == LearningAlgorithm.ONLINE_LEARNING:
            self._online_learning_update(feedback)

    def _reinforcement_update(self, feedback: UserFeedback):
        """EN"""
        reward = feedback.rating
        if feedback.feedback_type == FeedbackType.POSITIVE:
            reward += 0.2
        elif feedback.feedback_type == FeedbackType.NEGATIVE:
            reward -= 0.2

        # EN
        self.retrieval_weights += (
            self.learning_rate * reward * np.random.randn(len(self.retrieval_weights))
        )
        self.retrieval_weights = np.clip(self.retrieval_weights, 0, 1)

    def _gradient_descent_update(self, feedback: UserFeedback):
        """EN"""
        target_quality = feedback.rating
        current_quality = np.random.uniform(0.5, 0.8)  # EN
        error = target_quality - current_quality

        # EN
        self.generation_params["temperature"] += self.learning_rate * error * 0.1
        self.generation_params["temperature"] = np.clip(
            self.generation_params["temperature"], 0.1, 2.0
        )

    def _bayesian_update(self, feedback: UserFeedback):
        """EN"""
        # EN
        alpha = 1 + feedback.rating * 10
        beta = 1 + (1 - feedback.rating) * 10

        # EN
        performance_mean = alpha / (alpha + beta)
        # EN

    def _online_learning_update(self, feedback: UserFeedback):
        """EN"""
        # EN
        adjustment = (feedback.rating - 0.5) * self.learning_rate

        # EN
        if feedback.category == FeedbackCategory.RETRIEVAL_ACCURACY:
            self.retrieval_weights += adjustment * np.random.randn(
                len(self.retrieval_weights)
            )
            self.retrieval_weights = np.clip(self.retrieval_weights, 0, 1)


class UserFeedbackRAGTester:
    """ENRAGEN"""

    def __init__(self):
        self.rag_system = MockRAGSystem()
        self.feedback_history: List[UserFeedback] = []
        self.test_results: List[FeedbackTestResult] = []
        self.learning_curves = {}

    async def collect_feedback_batch(
        self, scenarios: List[Dict[str, Any]]
    ) -> List[UserFeedback]:
        """EN"""
        feedback_batch = []

        for scenario in scenarios:
            # EN
            query = scenario.get("query", "EN")
            answer = scenario.get("answer", "EN")

            # EN
            feedback = UserFeedback(
                id=str(uuid.uuid4()),
                query=query,
                answer=answer,
                feedback_type=FeedbackType(scenario.get("type", "positive")),
                category=FeedbackCategory(scenario.get("category", "answer_quality")),
                rating=scenario.get("rating", np.random.uniform(0.3, 1.0)),
                comment=scenario.get("comment", ""),
                correction=scenario.get("correction", ""),
                session_id=str(uuid.uuid4()),
                user_id=f"user_{np.random.randint(1, 100)}",
            )

            feedback_batch.append(feedback)

        return feedback_batch

    async def simulate_learning_process(
        self, test_case: FeedbackTestCase
    ) -> FeedbackTestResult:
        """EN"""
        start_time = time.time()

        # EN
        baseline_metrics = self.rag_system.get_current_performance()

        # EN
        feedback_processed = 0
        performance_history = [baseline_metrics]

        # EN
        batch_size = 10
        feedback_batches = [
            test_case.feedback_scenarios[i : i + batch_size]
            for i in range(0, len(test_case.feedback_scenarios), batch_size)
        ]

        convergence_start = None

        for batch_idx, batch in enumerate(feedback_batches):
            # EN
            for feedback in batch:
                self.rag_system.update_from_feedback(
                    feedback, test_case.learning_algorithm
                )
                feedback_processed += 1

            # EN
            current_metrics = self.rag_system.get_current_performance()
            performance_history.append(current_metrics)

            # EN
            if len(performance_history) >= 3:
                recent_improvement = self._calculate_improvement(
                    performance_history[-3], performance_history[-1]
                )
                if (
                    recent_improvement >= test_case.improvement_threshold
                    and convergence_start is None
                ):
                    convergence_start = time.time()

            # EN
            await asyncio.sleep(0.1)

        # EN
        improved_metrics = self.rag_system.get_current_performance()

        # EN
        improvements = self._calculate_improvements(baseline_metrics, improved_metrics)

        # EN
        total_time = time.time() - start_time
        learning_efficiency = (
            sum(improvements.values()) / total_time if total_time > 0 else 0
        )

        # EN
        convergence_time = (
            (convergence_start - start_time) if convergence_start else total_time
        )

        # EN
        success = self._evaluate_learning_success(
            improvements, test_case.expected_improvement
        )

        return FeedbackTestResult(
            test_case=test_case.name,
            learning_algorithm=test_case.learning_algorithm.value,
            baseline_metrics=baseline_metrics,
            improved_metrics=improved_metrics,
            improvements=improvements,
            learning_efficiency=learning_efficiency,
            convergence_time=convergence_time,
            success=success,
            feedback_processed=feedback_processed,
            performance_history=performance_history,
        )

    def _calculate_improvement(
        self, baseline: RAGPerformanceMetrics, current: RAGPerformanceMetrics
    ) -> float:
        """EN"""
        improvements = [
            current.retrieval_accuracy - baseline.retrieval_accuracy,
            current.answer_relevance - baseline.answer_relevance,
            current.user_satisfaction - baseline.user_satisfaction,
            -current.response_time + baseline.response_time,  # EN
            current.coverage - baseline.coverage,
            current.diversity - baseline.diversity,
        ]
        return np.mean(improvements)

    def _calculate_improvements(
        self, baseline: RAGPerformanceMetrics, current: RAGPerformanceMetrics
    ) -> Dict[str, float]:
        """EN"""
        return {
            "retrieval_accuracy": current.retrieval_accuracy
            - baseline.retrieval_accuracy,
            "answer_relevance": current.answer_relevance - baseline.answer_relevance,
            "user_satisfaction": current.user_satisfaction - baseline.user_satisfaction,
            "response_time": baseline.response_time - current.response_time,  # EN
            "coverage": current.coverage - baseline.coverage,
            "diversity": current.diversity - baseline.diversity,
        }

    def _evaluate_learning_success(
        self,
        actual_improvements: Dict[str, float],
        expected_improvements: Dict[str, float],
    ) -> bool:
        """EN"""
        for metric, expected in expected_improvements.items():
            if metric in actual_improvements:
                if actual_improvements[metric] < expected:
                    return False
        return True

    async def test_feedback_loop_effectiveness(
        self, algorithm: LearningAlgorithm
    ) -> FeedbackTestResult:
        """EN"""
        # EN
        feedback_scenarios = self._generate_feedback_scenarios(50)

        test_case = FeedbackTestCase(
            name=f"EN-{algorithm.value}",
            description=f"EN{algorithm.value}EN",
            feedback_scenarios=feedback_scenarios,
            learning_algorithm=algorithm,
            expected_improvement={
                "retrieval_accuracy": 0.1,
                "answer_relevance": 0.15,
                "user_satisfaction": 0.2,
            },
            improvement_threshold=0.05,
        )

        return await self.simulate_learning_process(test_case)

    def _generate_feedback_scenarios(self, count: int) -> List[UserFeedback]:
        """EN"""
        scenarios = []
        feedback_types = [
            FeedbackType.POSITIVE,
            FeedbackType.NEGATIVE,
            FeedbackType.NEUTRAL,
        ]
        categories = list(FeedbackCategory)

        for i in range(count):
            scenario = {
                "query": f"EN_{i+1}",
                "answer": f"EN_{i+1}",
                "type": np.random.choice([ft.value for ft in feedback_types]),
                "category": np.random.choice([c.value for c in categories]),
                "rating": np.random.beta(2, 1.5),  # EN
                "comment": f"EN_{i+1}",
            }
            scenarios.append(scenario)

        feedback_list = asyncio.run(self.collect_feedback_batch(scenarios))
        return feedback_list

    async def test_adaptive_learning(self) -> FeedbackTestResult:
        """EN"""
        # EN
        feedback_scenarios = []

        # EN:EN
        for i in range(20):
            scenario = {
                "query": f"EN_{i+1}",
                "answer": f"EN_{i+1}",
                "type": np.random.choice(["negative", "neutral"], p=[0.7, 0.3]),
                "rating": np.random.uniform(0.2, 0.5),
                "category": "answer_quality",
            }
            feedback_scenarios.append(scenario)

        # EN:EN
        for i in range(20):
            scenario = {
                "query": f"EN_{i+1}",
                "answer": f"EN_{i+1}",
                "type": np.random.choice(
                    ["positive", "negative", "neutral"], p=[0.4, 0.3, 0.3]
                ),
                "rating": np.random.uniform(0.4, 0.7),
                "category": np.random.choice(
                    ["answer_quality", "relevance", "clarity"]
                ),
            }
            feedback_scenarios.append(scenario)

        # EN:EN
        for i in range(10):
            scenario = {
                "query": f"EN_{i+1}",
                "answer": f"EN_{i+1}",
                "type": np.random.choice(["positive", "neutral"], p=[0.8, 0.2]),
                "rating": np.random.uniform(0.7, 0.95),
                "category": "answer_quality",
            }
            feedback_scenarios.append(scenario)

        feedback_list = await self.collect_feedback_batch(feedback_scenarios)

        test_case = FeedbackTestCase(
            name="EN",
            description="EN",
            feedback_scenarios=feedback_list,
            learning_algorithm=LearningAlgorithm.ONLINE_LEARNING,
            expected_improvement={"user_satisfaction": 0.3, "answer_relevance": 0.2},
            improvement_threshold=0.08,
        )

        return await self.simulate_learning_process(test_case)

    async def test_feedback_quality_impact(self) -> Dict[str, FeedbackTestResult]:
        """EN"""
        # EN
        quality_levels = {
            "high_quality": {"rating_range": (0.8, 1.0), "detail_level": "detailed"},
            "medium_quality": {"rating_range": (0.5, 0.8), "detail_level": "simple"},
            "low_quality": {"rating_range": (0.2, 0.5), "detail_level": "minimal"},
        }

        results = {}

        for quality, config in quality_levels.items():
            feedback_scenarios = []
            for i in range(30):
                rating = np.random.uniform(*config["rating_range"])
                scenario = {
                    "query": f"EN_{quality}_{i+1}",
                    "answer": f"EN_{quality}_{i+1}",
                    "type": "positive" if rating > 0.6 else "negative",
                    "rating": rating,
                    "category": "answer_quality",
                    "comment": f"EN"
                    if config["detail_level"] == "detailed"
                    else "EN",
                }
                feedback_scenarios.append(scenario)

            feedback_list = await self.collect_feedback_batch(feedback_scenarios)

            test_case = FeedbackTestCase(
                name=f"EN-{quality}",
                description=f"EN{quality}EN",
                feedback_scenarios=feedback_list,
                learning_algorithm=LearningAlgorithm.REINFORCEMENT_LEARNING,
                expected_improvement={"user_satisfaction": 0.15},
                improvement_threshold=0.05,
            )

            result = await self.simulate_learning_process(test_case)
            results[quality] = result

        return results

    async def test_long_term_learning(self) -> FeedbackTestResult:
        """EN"""
        # EN
        feedback_scenarios = []

        # EN100EN,EN
        for day in range(7):  # 7EN
            for feedback_per_day in range(15):  # EN15EN
                # EN:EN,EN
                base_rating = 0.3 + (day / 7) * 0.4
                rating = np.clip(np.random.normal(base_rating, 0.1), 0.0, 1.0)

                scenario = {
                    "query": f"EN_EN{day+1}EN_EN{feedback_per_day+1}",
                    "answer": f"EN_{day}_{feedback_per_day}",
                    "type": "positive" if rating > 0.5 else "negative",
                    "rating": rating,
                    "category": np.random.choice(
                        ["answer_quality", "relevance", "clarity", "accuracy"]
                    ),
                }
                feedback_scenarios.append(scenario)

        feedback_list = await self.collect_feedback_batch(feedback_scenarios)

        test_case = FeedbackTestCase(
            name="EN",
            description="EN",
            feedback_scenarios=feedback_list,
            learning_algorithm=LearningAlgorithm.BAYESIAN_OPTIMIZATION,
            expected_improvement={
                "retrieval_accuracy": 0.25,
                "answer_relevance": 0.3,
                "user_satisfaction": 0.35,
            },
            improvement_threshold=0.15,
            test_duration=600,
        )

        return await self.simulate_learning_process(test_case)

    async def run_comprehensive_feedback_tests(self) -> Dict[str, Any]:
        """EN"""
        print("🚀 ENRAGEN")

        # 1. EN
        print("🧠 EN...")
        algorithm_results = []
        algorithms = [
            LearningAlgorithm.REINFORCEMENT_LEARNING,
            LearningAlgorithm.GRADIENT_DESCENT,
            LearningAlgorithm.BAYESIAN_OPTIMIZATION,
            LearningAlgorithm.ONLINE_LEARNING,
        ]

        for algorithm in algorithms:
            result = await self.test_feedback_loop_effectiveness(algorithm)
            algorithm_results.append(result)
            self.test_results.append(result)

        # 2. EN
        print("🎯 EN...")
        adaptive_result = await self.test_adaptive_learning()
        self.test_results.append(adaptive_result)

        # 3. EN
        print("📊 EN...")
        quality_results = await self.test_feedback_quality_impact()
        self.test_results.extend(quality_results.values())

        # 4. EN
        print("⏰ EN...")
        long_term_result = await self.test_long_term_learning()
        self.test_results.append(long_term_result)

        # EN
        report = self._generate_feedback_test_report(
            algorithm_results, adaptive_result, quality_results, long_term_result
        )

        return {
            "success": True,
            "test_results": self.test_results,
            "summary": report,
            "algorithm_results": algorithm_results,
            "adaptive_result": adaptive_result,
            "quality_results": quality_results,
            "long_term_result": long_term_result,
        }

    def _generate_feedback_test_report(
        self,
        algorithm_results: List[FeedbackTestResult],
        adaptive_result: FeedbackTestResult,
        quality_results: Dict[str, FeedbackTestResult],
        long_term_result: FeedbackTestResult,
    ) -> Dict[str, Any]:
        """EN"""

        # EN
        algorithm_performance = {}
        for result in algorithm_results:
            algorithm_performance[result.learning_algorithm] = {
                "success": result.success,
                "learning_efficiency": result.learning_efficiency,
                "convergence_time": result.convergence_time,
                "improvements": result.improvements,
            }

        # EN
        best_algorithm = max(
            algorithm_performance.items(), key=lambda x: x[1]["learning_efficiency"]
        )[0]

        # EN
        quality_impact = {}
        for quality, result in quality_results.items():
            quality_impact[quality] = {
                "learning_efficiency": result.learning_efficiency,
                "total_improvement": sum(result.improvements.values()),
                "convergence_time": result.convergence_time,
            }

        # EN
        learning_curves = {}
        for result in self.test_results:
            if hasattr(result, "performance_history") and result.performance_history:
                learning_curves[result.test_case] = {
                    "baseline": result.baseline_metrics,
                    "final": result.improved_metrics,
                    "history": result.performance_history,
                }

        # EN
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result.success)
        avg_learning_efficiency = (
            sum(result.learning_efficiency for result in self.test_results)
            / total_tests
            if total_tests > 0
            else 0
        )
        avg_convergence_time = (
            sum(result.convergence_time for result in self.test_results) / total_tests
            if total_tests > 0
            else 0
        )

        # EN
        overall_improvements = {}
        metrics = [
            "retrieval_accuracy",
            "answer_relevance",
            "user_satisfaction",
            "response_time",
            "coverage",
            "diversity",
        ]
        for metric in metrics:
            improvements = [
                result.improvements.get(metric, 0)
                for result in self.test_results
                if metric in result.improvements
            ]
            if improvements:
                overall_improvements[metric] = np.mean(improvements)
            else:
                overall_improvements[metric] = 0.0

        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "average_learning_efficiency": avg_learning_efficiency,
            "average_convergence_time": avg_convergence_time,
            "best_algorithm": best_algorithm,
            "algorithm_performance": algorithm_performance,
            "quality_impact_analysis": quality_impact,
            "learning_curves": learning_curves,
            "overall_improvements": overall_improvements,
            "adaptive_learning_result": {
                "success": adaptive_result.success,
                "learning_efficiency": adaptive_result.learning_efficiency,
                "improvements": adaptive_result.improvements,
            },
            "long_term_learning_result": {
                "success": long_term_result.success,
                "learning_efficiency": long_term_result.learning_efficiency,
                "total_feedback_processed": long_term_result.feedback_processed,
                "improvements": long_term_result.improvements,
            },
            "recommendations": self._generate_feedback_recommendations(),
        }

    def _generate_feedback_recommendations(self) -> List[str]:
        """EN"""
        recommendations = []

        # EN
        algorithm_results = [
            result for result in self.test_results if "EN" in result.test_case
        ]
        if algorithm_results:
            best_result = max(algorithm_results, key=lambda x: x.learning_efficiency)
            worst_result = min(algorithm_results, key=lambda x: x.learning_efficiency)

            recommendations.append(f"EN {best_result.learning_algorithm} EN,EN")

            if worst_result.learning_efficiency < best_result.learning_efficiency * 0.5:
                recommendations.append(f"EN {worst_result.learning_algorithm} EN")

        # EN
        quality_results = [
            result for result in self.test_results if "EN" in result.test_case
        ]
        if quality_results:
            high_quality = next(
                (r for r in quality_results if "high_quality" in r.test_case), None
            )
            low_quality = next(
                (r for r in quality_results if "low_quality" in r.test_case), None
            )

            if high_quality and low_quality:
                if (
                    high_quality.learning_efficiency
                    > low_quality.learning_efficiency * 1.5
                ):
                    recommendations.append("EN,EN")

        # EN
        avg_efficiency = sum(
            result.learning_efficiency for result in self.test_results
        ) / len(self.test_results)
        if avg_efficiency < 0.1:
            recommendations.append("EN,EN")
        elif avg_efficiency > 0.5:
            recommendations.append("EN,EN")

        # EN
        avg_convergence = sum(
            result.convergence_time for result in self.test_results
        ) / len(self.test_results)
        if avg_convergence > 30:
            recommendations.append("EN,EN")

        # EN
        long_term_results = [
            result for result in self.test_results if "EN" in result.test_case
        ]
        if long_term_results:
            long_term_result = long_term_results[0]
            if long_term_result.success:
                recommendations.append("EN,EN")
            else:
                recommendations.append("EN,EN")

        if not recommendations:
            recommendations.append("EN,EN")

        return recommendations


# pytestEN
@pytest.mark.asyncio
async def test_feedback_rag_impact_comprehensive():
    """ENRAGEN"""
    tester = UserFeedbackRAGTester()
    results = await tester.run_comprehensive_feedback_tests()

    assert results["success"], "ENRAGEN"
    assert results["summary"]["success_rate"] >= 0.7, "EN70%"
    assert results["summary"]["average_learning_efficiency"] > 0, "EN"
    assert len(results["algorithm_results"]) >= 3, "EN3EN"


@pytest.mark.asyncio
async def test_reinforcement_learning_feedback():
    """EN"""
    tester = UserFeedbackRAGTester()
    result = await tester.test_feedback_loop_effectiveness(
        LearningAlgorithm.REINFORCEMENT_LEARNING
    )

    assert result.success, "EN"
    assert result.feedback_processed > 0, "EN"
    assert result.learning_efficiency > 0, "EN"
    assert any(imp > 0 for imp in result.improvements.values()), "EN"


@pytest.mark.asyncio
async def test_adaptive_learning_capability():
    """EN"""
    tester = UserFeedbackRAGTester()
    result = await tester.test_adaptive_learning()

    assert result.success, "EN"
    assert result.feedback_processed >= 40, "EN"
    assert result.improvements.get("user_satisfaction", 0) > 0, "EN"


@pytest.mark.asyncio
async def test_feedback_quality_impact():
    """EN"""
    tester = UserFeedbackRAGTester()
    results = await tester.test_feedback_quality_impact()

    assert len(results) == 3, "EN3EN"

    # EN
    high_quality_efficiency = results["high_quality"].learning_efficiency
    low_quality_efficiency = results["low_quality"].learning_efficiency

    assert high_quality_efficiency >= low_quality_efficiency, "EN"


@pytest.mark.asyncio
async def test_long_term_learning_effectiveness():
    """EN"""
    tester = UserFeedbackRAGTester()
    result = await tester.test_long_term_learning()

    assert result.feedback_processed >= 100, "EN"
    assert result.convergence_time > 0, "EN"

    # EN
    total_improvement = sum(result.improvements.values())
    assert total_improvement > 0, "EN"


@pytest.mark.asyncio
async def test_feedback_integration_stability():
    """EN"""
    tester = UserFeedbackRAGTester()

    # EN
    results = []
    for i in range(3):
        result = await tester.test_feedback_loop_effectiveness(
            LearningAlgorithm.ONLINE_LEARNING
        )
        results.append(result)

    # EN
    efficiencies = [r.learning_efficiency for r in results]
    efficiency_std = np.std(efficiencies)

    # EN,EN
    assert efficiency_std < np.mean(efficiencies) * 0.5, "EN"


if __name__ == "__main__":
    # EN
    async def main():
        tester = UserFeedbackRAGTester()
        results = await tester.run_comprehensive_feedback_tests()

        print("\n" + "=" * 60)
        print("🔄 ENRAGEN")
        print("=" * 60)

        if results["success"]:
            summary = results["summary"]
            print(f"✅ EN: {summary['total_tests']}")
            print(f"✅ EN: {summary['successful_tests']}")
            print(f"📊 EN: {summary['success_rate']:.1%}")
            print(f"🧠 EN: {summary['average_learning_efficiency']:.4f}")
            print(f"⏱️ EN: {summary['average_convergence_time']:.2f}EN")
            print(f"🏆 EN: {summary['best_algorithm']}")

            print("\n📈 EN:")
            for algo, perf in summary["algorithm_performance"].items():
                print(f"  {algo}:")
                print(f"    EN: {'✅' if perf['success'] else '❌'}")
                print(f"    EN: {perf['learning_efficiency']:.4f}")
                print(f"    EN: {perf['convergence_time']:.2f}s")

            print("\n📊 EN:")
            for quality, impact in summary["quality_impact_analysis"].items():
                print(
                    f"  {quality}: EN {impact['learning_efficiency']:.4f}, "
                    f"EN {impact['total_improvement']:.4f}"
                )

            print("\n🎯 EN:")
            for metric, improvement in summary["overall_improvements"].items():
                status = "📈" if improvement > 0 else "📉"
                print(f"  {metric}: {status} {improvement:.4f}")

            print("\n💡 EN:")
            for i, rec in enumerate(summary["recommendations"], 1):
                print(f"  {i}. {rec}")
        else:
            print(f"❌ EN: EN")

    asyncio.run(main())
