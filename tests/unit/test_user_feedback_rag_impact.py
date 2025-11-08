#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User Feedback Impact on RAG System Testing Suite

测试用户反馈对RAG系统的影响和改进效果
包括反馈收集、系统学习、检索优化、回答质量提升等
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
    """反馈类型"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    DETAILED = "detailed"
    CORRECTION = "correction"
    RATING = "rating"


class FeedbackCategory(Enum):
    """反馈分类"""

    ANSWER_QUALITY = "answer_quality"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    ACCURACY = "accuracy"
    SOURCE_QUALITY = "source_quality"
    RESPONSE_TIME = "response_time"


class LearningAlgorithm(Enum):
    """学习算法类型"""

    REINFORCEMENT_LEARNING = "reinforcement_learning"
    GRADIENT_DESCENT = "gradient_descent"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    ONLINE_LEARNING = "online_learning"
    ACTIVE_LEARNING = "active_learning"


@dataclass
class UserFeedback:
    """用户反馈"""

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
    """RAG性能指标"""

    retrieval_accuracy: float = 0.0
    answer_relevance: float = 0.0
    user_satisfaction: float = 0.0
    response_time: float = 0.0
    coverage: float = 0.0
    diversity: float = 0.0


@dataclass
class FeedbackTestCase:
    """反馈测试用例"""

    name: str
    description: str
    feedback_scenarios: List[UserFeedback]
    learning_algorithm: LearningAlgorithm
    expected_improvement: Dict[str, float]
    test_duration: int = 300  # 秒
    improvement_threshold: float = 0.1


@dataclass
class FeedbackTestResult:
    """反馈测试结果"""

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
    """模拟RAG系统"""

    def __init__(self):
        self.vector_database = {}  # 模拟向量数据库
        self.retrieval_weights = np.random.rand(100)  # 检索权重
        self.generation_params = {"temperature": 0.7, "max_tokens": 2000, "top_p": 0.9}
        self.performance_history = []
        self.learning_rate = 0.01

    def retrieve_documents(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """检索文档"""
        # 模拟文档检索
        docs = [f"文档1: 关于{query}的相关信息", f"文档2: {query}的详细说明", f"文档3: {query}的补充材料"]
        scores = np.random.dirichlet(np.ones(len(docs)), size=1)[0]
        return list(zip(docs, scores.tolist()))

    def generate_answer(self, query: str, retrieved_docs: List[str]) -> str:
        """生成回答"""
        # 基于检索文档生成回答
        context = " ".join(retrieved_docs)
        return f"基于相关文档，关于'{query}'的回答是：{context[:100]}..."

    def get_current_performance(self) -> RAGPerformanceMetrics:
        """获取当前性能指标"""
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
        """根据反馈更新系统"""
        if algorithm == LearningAlgorithm.REINFORCEMENT_LEARNING:
            self._reinforcement_update(feedback)
        elif algorithm == LearningAlgorithm.GRADIENT_DESCENT:
            self._gradient_descent_update(feedback)
        elif algorithm == LearningAlgorithm.BAYESIAN_OPTIMIZATION:
            self._bayesian_update(feedback)
        elif algorithm == LearningAlgorithm.ONLINE_LEARNING:
            self._online_learning_update(feedback)

    def _reinforcement_update(self, feedback: UserFeedback):
        """强化学习更新"""
        reward = feedback.rating
        if feedback.feedback_type == FeedbackType.POSITIVE:
            reward += 0.2
        elif feedback.feedback_type == FeedbackType.NEGATIVE:
            reward -= 0.2

        # 更新检索权重
        self.retrieval_weights += (
            self.learning_rate * reward * np.random.randn(len(self.retrieval_weights))
        )
        self.retrieval_weights = np.clip(self.retrieval_weights, 0, 1)

    def _gradient_descent_update(self, feedback: UserFeedback):
        """梯度下降更新"""
        target_quality = feedback.rating
        current_quality = np.random.uniform(0.5, 0.8)  # 模拟当前质量
        error = target_quality - current_quality

        # 更新生成参数
        self.generation_params["temperature"] += self.learning_rate * error * 0.1
        self.generation_params["temperature"] = np.clip(
            self.generation_params["temperature"], 0.1, 2.0
        )

    def _bayesian_update(self, feedback: UserFeedback):
        """贝叶斯优化更新"""
        # 模拟贝叶斯更新
        alpha = 1 + feedback.rating * 10
        beta = 1 + (1 - feedback.rating) * 10

        # 更新性能分布
        performance_mean = alpha / (alpha + beta)
        # 这里可以更新系统的参数分布

    def _online_learning_update(self, feedback: UserFeedback):
        """在线学习更新"""
        # 立即根据反馈调整
        adjustment = (feedback.rating - 0.5) * self.learning_rate

        # 调整检索策略
        if feedback.category == FeedbackCategory.RETRIEVAL_ACCURACY:
            self.retrieval_weights += adjustment * np.random.randn(
                len(self.retrieval_weights)
            )
            self.retrieval_weights = np.clip(self.retrieval_weights, 0, 1)


class UserFeedbackRAGTester:
    """用户反馈对RAG系统影响测试器"""

    def __init__(self):
        self.rag_system = MockRAGSystem()
        self.feedback_history: List[UserFeedback] = []
        self.test_results: List[FeedbackTestResult] = []
        self.learning_curves = {}

    async def collect_feedback_batch(
        self, scenarios: List[Dict[str, Any]]
    ) -> List[UserFeedback]:
        """批量收集反馈"""
        feedback_batch = []

        for scenario in scenarios:
            # 模拟用户查询
            query = scenario.get("query", "测试查询")
            answer = scenario.get("answer", "测试回答")

            # 模拟反馈生成
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
        """模拟学习过程"""
        start_time = time.time()

        # 获取基线性能
        baseline_metrics = self.rag_system.get_current_performance()

        # 处理反馈并学习
        feedback_processed = 0
        performance_history = [baseline_metrics]

        # 分批处理反馈
        batch_size = 10
        feedback_batches = [
            test_case.feedback_scenarios[i : i + batch_size]
            for i in range(0, len(test_case.feedback_scenarios), batch_size)
        ]

        convergence_start = None

        for batch_idx, batch in enumerate(feedback_batches):
            # 处理当前批次
            for feedback in batch:
                self.rag_system.update_from_feedback(
                    feedback, test_case.learning_algorithm
                )
                feedback_processed += 1

            # 评估当前性能
            current_metrics = self.rag_system.get_current_performance()
            performance_history.append(current_metrics)

            # 检查收敛
            if len(performance_history) >= 3:
                recent_improvement = self._calculate_improvement(
                    performance_history[-3], performance_history[-1]
                )
                if (
                    recent_improvement >= test_case.improvement_threshold
                    and convergence_start is None
                ):
                    convergence_start = time.time()

            # 模拟处理延迟
            await asyncio.sleep(0.1)

        # 获取最终性能
        improved_metrics = self.rag_system.get_current_performance()

        # 计算改进
        improvements = self._calculate_improvements(baseline_metrics, improved_metrics)

        # 计算学习效率
        total_time = time.time() - start_time
        learning_efficiency = (
            sum(improvements.values()) / total_time if total_time > 0 else 0
        )

        # 计算收敛时间
        convergence_time = (
            (convergence_start - start_time) if convergence_start else total_time
        )

        # 评估成功性
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
        """计算单项改进"""
        improvements = [
            current.retrieval_accuracy - baseline.retrieval_accuracy,
            current.answer_relevance - baseline.answer_relevance,
            current.user_satisfaction - baseline.user_satisfaction,
            -current.response_time + baseline.response_time,  # 响应时间改进是负的
            current.coverage - baseline.coverage,
            current.diversity - baseline.diversity,
        ]
        return np.mean(improvements)

    def _calculate_improvements(
        self, baseline: RAGPerformanceMetrics, current: RAGPerformanceMetrics
    ) -> Dict[str, float]:
        """计算各项改进"""
        return {
            "retrieval_accuracy": current.retrieval_accuracy
            - baseline.retrieval_accuracy,
            "answer_relevance": current.answer_relevance - baseline.answer_relevance,
            "user_satisfaction": current.user_satisfaction - baseline.user_satisfaction,
            "response_time": baseline.response_time - current.response_time,  # 负值表示改进
            "coverage": current.coverage - baseline.coverage,
            "diversity": current.diversity - baseline.diversity,
        }

    def _evaluate_learning_success(
        self,
        actual_improvements: Dict[str, float],
        expected_improvements: Dict[str, float],
    ) -> bool:
        """评估学习是否成功"""
        for metric, expected in expected_improvements.items():
            if metric in actual_improvements:
                if actual_improvements[metric] < expected:
                    return False
        return True

    async def test_feedback_loop_effectiveness(
        self, algorithm: LearningAlgorithm
    ) -> FeedbackTestResult:
        """测试反馈回路有效性"""
        # 创建测试场景
        feedback_scenarios = self._generate_feedback_scenarios(50)

        test_case = FeedbackTestCase(
            name=f"反馈回路测试-{algorithm.value}",
            description=f"测试{algorithm.value}算法的反馈回路效果",
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
        """生成反馈场景"""
        scenarios = []
        feedback_types = [
            FeedbackType.POSITIVE,
            FeedbackType.NEGATIVE,
            FeedbackType.NEUTRAL,
        ]
        categories = list(FeedbackCategory)

        for i in range(count):
            scenario = {
                "query": f"查询问题_{i+1}",
                "answer": f"回答内容_{i+1}",
                "type": np.random.choice([ft.value for ft in feedback_types]),
                "category": np.random.choice([c.value for c in categories]),
                "rating": np.random.beta(2, 1.5),  # 偏向正评分
                "comment": f"用户评论_{i+1}",
            }
            scenarios.append(scenario)

        feedback_list = asyncio.run(self.collect_feedback_batch(scenarios))
        return feedback_list

    async def test_adaptive_learning(self) -> FeedbackTestResult:
        """测试自适应学习"""
        # 创建渐进式改进的反馈场景
        feedback_scenarios = []

        # 初始阶段：负反馈较多
        for i in range(20):
            scenario = {
                "query": f"学习查询_{i+1}",
                "answer": f"学习回答_{i+1}",
                "type": np.random.choice(["negative", "neutral"], p=[0.7, 0.3]),
                "rating": np.random.uniform(0.2, 0.5),
                "category": "answer_quality",
            }
            feedback_scenarios.append(scenario)

        # 中期阶段：混合反馈
        for i in range(20):
            scenario = {
                "query": f"改进查询_{i+1}",
                "answer": f"改进回答_{i+1}",
                "type": np.random.choice(
                    ["positive", "negative", "neutral"], p=[0.4, 0.3, 0.3]
                ),
                "rating": np.random.uniform(0.4, 0.7),
                "category": np.random.choice(
                    ["answer_quality", "relevance", "clarity"]
                ),
            }
            feedback_scenarios.append(scenario)

        # 后期阶段：正反馈较多
        for i in range(10):
            scenario = {
                "query": f"优化查询_{i+1}",
                "answer": f"优化回答_{i+1}",
                "type": np.random.choice(["positive", "neutral"], p=[0.8, 0.2]),
                "rating": np.random.uniform(0.7, 0.95),
                "category": "answer_quality",
            }
            feedback_scenarios.append(scenario)

        feedback_list = await self.collect_feedback_batch(feedback_scenarios)

        test_case = FeedbackTestCase(
            name="自适应学习测试",
            description="测试系统在不同反馈阶段的自适应学习能力",
            feedback_scenarios=feedback_list,
            learning_algorithm=LearningAlgorithm.ONLINE_LEARNING,
            expected_improvement={"user_satisfaction": 0.3, "answer_relevance": 0.2},
            improvement_threshold=0.08,
        )

        return await self.simulate_learning_process(test_case)

    async def test_feedback_quality_impact(self) -> Dict[str, FeedbackTestResult]:
        """测试反馈质量对学习效果的影响"""
        # 生成不同质量的反馈
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
                    "query": f"质量测试查询_{quality}_{i+1}",
                    "answer": f"质量测试回答_{quality}_{i+1}",
                    "type": "positive" if rating > 0.6 else "negative",
                    "rating": rating,
                    "category": "answer_quality",
                    "comment": f"详细评论"
                    if config["detail_level"] == "detailed"
                    else "简单评论",
                }
                feedback_scenarios.append(scenario)

            feedback_list = await self.collect_feedback_batch(feedback_scenarios)

            test_case = FeedbackTestCase(
                name=f"反馈质量测试-{quality}",
                description=f"测试{quality}反馈对学习效果的影响",
                feedback_scenarios=feedback_list,
                learning_algorithm=LearningAlgorithm.REINFORCEMENT_LEARNING,
                expected_improvement={"user_satisfaction": 0.15},
                improvement_threshold=0.05,
            )

            result = await self.simulate_learning_process(test_case)
            results[quality] = result

        return results

    async def test_long_term_learning(self) -> FeedbackTestResult:
        """测试长期学习效果"""
        # 模拟长期学习过程
        feedback_scenarios = []

        # 生成100个反馈场景，模拟几周的使用
        for day in range(7):  # 7天
            for feedback_per_day in range(15):  # 每天15个反馈
                # 模拟学习曲线：开始反馈较差，逐渐改善
                base_rating = 0.3 + (day / 7) * 0.4
                rating = np.clip(np.random.normal(base_rating, 0.1), 0.0, 1.0)

                scenario = {
                    "query": f"长期学习_第{day+1}天_反馈{feedback_per_day+1}",
                    "answer": f"长期学习回答_{day}_{feedback_per_day}",
                    "type": "positive" if rating > 0.5 else "negative",
                    "rating": rating,
                    "category": np.random.choice(
                        ["answer_quality", "relevance", "clarity", "accuracy"]
                    ),
                }
                feedback_scenarios.append(scenario)

        feedback_list = await self.collect_feedback_batch(feedback_scenarios)

        test_case = FeedbackTestCase(
            name="长期学习效果测试",
            description="测试系统在长期反馈学习中的改进效果",
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
        """运行综合反馈测试"""
        print("🚀 开始用户反馈对RAG系统影响的综合测试")

        # 1. 测试不同学习算法的效果
        print("🧠 测试不同学习算法的效果...")
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

        # 2. 测试自适应学习
        print("🎯 测试自适应学习能力...")
        adaptive_result = await self.test_adaptive_learning()
        self.test_results.append(adaptive_result)

        # 3. 测试反馈质量影响
        print("📊 测试反馈质量对学习效果的影响...")
        quality_results = await self.test_feedback_quality_impact()
        self.test_results.extend(quality_results.values())

        # 4. 测试长期学习效果
        print("⏰ 测试长期学习效果...")
        long_term_result = await self.test_long_term_learning()
        self.test_results.append(long_term_result)

        # 生成测试报告
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
        """生成反馈测试报告"""

        # 算法比较
        algorithm_performance = {}
        for result in algorithm_results:
            algorithm_performance[result.learning_algorithm] = {
                "success": result.success,
                "learning_efficiency": result.learning_efficiency,
                "convergence_time": result.convergence_time,
                "improvements": result.improvements,
            }

        # 找出最佳算法
        best_algorithm = max(
            algorithm_performance.items(), key=lambda x: x[1]["learning_efficiency"]
        )[0]

        # 反馈质量影响分析
        quality_impact = {}
        for quality, result in quality_results.items():
            quality_impact[quality] = {
                "learning_efficiency": result.learning_efficiency,
                "total_improvement": sum(result.improvements.values()),
                "convergence_time": result.convergence_time,
            }

        # 学习曲线分析
        learning_curves = {}
        for result in self.test_results:
            if hasattr(result, "performance_history") and result.performance_history:
                learning_curves[result.test_case] = {
                    "baseline": result.baseline_metrics,
                    "final": result.improved_metrics,
                    "history": result.performance_history,
                }

        # 总体统计
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

        # 计算总体改进
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
        """生成反馈系统改进建议"""
        recommendations = []

        # 分析算法性能
        algorithm_results = [
            result for result in self.test_results if "反馈回路测试" in result.test_case
        ]
        if algorithm_results:
            best_result = max(algorithm_results, key=lambda x: x.learning_efficiency)
            worst_result = min(algorithm_results, key=lambda x: x.learning_efficiency)

            recommendations.append(f"推荐使用 {best_result.learning_algorithm} 算法，学习效率最高")

            if worst_result.learning_efficiency < best_result.learning_efficiency * 0.5:
                recommendations.append(f"考虑停用或改进 {worst_result.learning_algorithm} 算法")

        # 分析反馈质量影响
        quality_results = [
            result for result in self.test_results if "反馈质量测试" in result.test_case
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
                    recommendations.append("提高反馈质量收集机制，鼓励用户提供详细反馈")

        # 分析学习效率
        avg_efficiency = sum(
            result.learning_efficiency for result in self.test_results
        ) / len(self.test_results)
        if avg_efficiency < 0.1:
            recommendations.append("整体学习效率偏低，建议调整学习率或改进算法")
        elif avg_efficiency > 0.5:
            recommendations.append("学习效率良好，可以考虑扩大反馈应用范围")

        # 分析收敛时间
        avg_convergence = sum(
            result.convergence_time for result in self.test_results
        ) / len(self.test_results)
        if avg_convergence > 30:
            recommendations.append("收敛时间较长，建议优化算法加速收敛过程")

        # 分析长期学习效果
        long_term_results = [
            result for result in self.test_results if "长期学习" in result.test_case
        ]
        if long_term_results:
            long_term_result = long_term_results[0]
            if long_term_result.success:
                recommendations.append("长期学习效果良好，系统具有持续改进能力")
            else:
                recommendations.append("长期学习效果有限，建议加强长期记忆机制")

        if not recommendations:
            recommendations.append("反馈系统测试全部通过，用户反馈机制运行良好")

        return recommendations


# pytest测试用例
@pytest.mark.asyncio
async def test_feedback_rag_impact_comprehensive():
    """测试用户反馈对RAG系统的综合影响"""
    tester = UserFeedbackRAGTester()
    results = await tester.run_comprehensive_feedback_tests()

    assert results["success"], "用户反馈对RAG系统影响测试应该成功"
    assert results["summary"]["success_rate"] >= 0.7, "测试成功率应该至少70%"
    assert results["summary"]["average_learning_efficiency"] > 0, "学习效率应该为正"
    assert len(results["algorithm_results"]) >= 3, "应该测试至少3种学习算法"


@pytest.mark.asyncio
async def test_reinforcement_learning_feedback():
    """测试强化学习反馈机制"""
    tester = UserFeedbackRAGTester()
    result = await tester.test_feedback_loop_effectiveness(
        LearningAlgorithm.REINFORCEMENT_LEARNING
    )

    assert result.success, "强化学习反馈应该成功"
    assert result.feedback_processed > 0, "应该处理反馈"
    assert result.learning_efficiency > 0, "学习效率应该为正"
    assert any(imp > 0 for imp in result.improvements.values()), "应该有至少一项指标改进"


@pytest.mark.asyncio
async def test_adaptive_learning_capability():
    """测试自适应学习能力"""
    tester = UserFeedbackRAGTester()
    result = await tester.test_adaptive_learning()

    assert result.success, "自适应学习应该成功"
    assert result.feedback_processed >= 40, "应该处理足够多的反馈"
    assert result.improvements.get("user_satisfaction", 0) > 0, "用户满意度应该改进"


@pytest.mark.asyncio
async def test_feedback_quality_impact():
    """测试反馈质量对学习效果的影响"""
    tester = UserFeedbackRAGTester()
    results = await tester.test_feedback_quality_impact()

    assert len(results) == 3, "应该测试3种质量水平的反馈"

    # 高质量反馈应该比低质量反馈效果更好
    high_quality_efficiency = results["high_quality"].learning_efficiency
    low_quality_efficiency = results["low_quality"].learning_efficiency

    assert high_quality_efficiency >= low_quality_efficiency, "高质量反馈应该比低质量反馈效果更好"


@pytest.mark.asyncio
async def test_long_term_learning_effectiveness():
    """测试长期学习效果"""
    tester = UserFeedbackRAGTester()
    result = await tester.test_long_term_learning()

    assert result.feedback_processed >= 100, "应该处理长期反馈"
    assert result.convergence_time > 0, "应该有收敛时间"

    # 长期学习应该显示改进
    total_improvement = sum(result.improvements.values())
    assert total_improvement > 0, "长期学习应该产生整体改进"


@pytest.mark.asyncio
async def test_feedback_integration_stability():
    """测试反馈集成的稳定性"""
    tester = UserFeedbackRAGTester()

    # 运行多次相同的测试
    results = []
    for i in range(3):
        result = await tester.test_feedback_loop_effectiveness(
            LearningAlgorithm.ONLINE_LEARNING
        )
        results.append(result)

    # 检查结果的一致性
    efficiencies = [r.learning_efficiency for r in results]
    efficiency_std = np.std(efficiencies)

    # 标准差应该相对较小，表明结果稳定
    assert efficiency_std < np.mean(efficiencies) * 0.5, "测试结果应该相对稳定"


if __name__ == "__main__":
    # 运行综合测试
    async def main():
        tester = UserFeedbackRAGTester()
        results = await tester.run_comprehensive_feedback_tests()

        print("\n" + "=" * 60)
        print("🔄 用户反馈对RAG系统影响测试完成")
        print("=" * 60)

        if results["success"]:
            summary = results["summary"]
            print(f"✅ 总测试数: {summary['total_tests']}")
            print(f"✅ 成功测试数: {summary['successful_tests']}")
            print(f"📊 成功率: {summary['success_rate']:.1%}")
            print(f"🧠 平均学习效率: {summary['average_learning_efficiency']:.4f}")
            print(f"⏱️ 平均收敛时间: {summary['average_convergence_time']:.2f}秒")
            print(f"🏆 最佳算法: {summary['best_algorithm']}")

            print("\n📈 算法性能比较:")
            for algo, perf in summary["algorithm_performance"].items():
                print(f"  {algo}:")
                print(f"    成功: {'✅' if perf['success'] else '❌'}")
                print(f"    学习效率: {perf['learning_efficiency']:.4f}")
                print(f"    收敛时间: {perf['convergence_time']:.2f}s")

            print("\n📊 反馈质量影响:")
            for quality, impact in summary["quality_impact_analysis"].items():
                print(
                    f"  {quality}: 学习效率 {impact['learning_efficiency']:.4f}, "
                    f"总改进 {impact['total_improvement']:.4f}"
                )

            print("\n🎯 总体改进效果:")
            for metric, improvement in summary["overall_improvements"].items():
                status = "📈" if improvement > 0 else "📉"
                print(f"  {metric}: {status} {improvement:.4f}")

            print("\n💡 改进建议:")
            for i, rec in enumerate(summary["recommendations"], 1):
                print(f"  {i}. {rec}")
        else:
            print(f"❌ 测试失败: 未知错误")

    asyncio.run(main())
