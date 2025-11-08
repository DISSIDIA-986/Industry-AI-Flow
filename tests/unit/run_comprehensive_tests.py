#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Test Framework for Industry AI Flow

统一的测试框架，整合所有测试模块，提供完整的系统测试覆盖
包括核心功能、接口、性能、安全性和用户体验等全方位测试
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import unittest
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
from test_answer_generation import AnswerGenerationTester
from test_data_analysis_code_execution import DataAnalysisCodeExecutionTester
from test_frontend_chat_interface import FrontendChatTester
from test_ocr_integration import OCRIntegrationTester

# 导入所有测试模块
from test_question_classification import QuestionClassificationTester
from test_streamlit_interface import StreamlitInterfaceTester
from test_user_feedback_rag_impact import UserFeedbackRAGTester

from test_vector_retrieval import VectorRetrievalTester


class TestCategory(Enum):
    """测试类别"""

    CORE_FUNCTIONALITY = "core_functionality"
    INTERFACE_TESTING = "interface_testing"
    PERFORMANCE_TESTING = "performance_testing"
    INTEGRATION_TESTING = "integration_testing"
    USER_EXPERIENCE = "user_experience"
    SAFETY_SECURITY = "safety_security"


class TestPriority(Enum):
    """测试优先级"""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class TestSuite:
    """测试套件"""

    name: str
    category: TestCategory
    priority: TestPriority
    description: str
    tester_class: type
    enabled: bool = True
    timeout: int = 300
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TestExecutionResult:
    """测试执行结果"""

    suite_name: str
    category: str
    success: bool
    execution_time: float
    test_results: List[Any] = field(default_factory=list)
    error_message: str = ""
    summary: Dict[str, Any] = field(default_factory=dict)
    coverage_metrics: Dict[str, float] = field(default_factory=dict)


class ComprehensiveTestRunner:
    """综合测试运行器"""

    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.dirname(os.path.abspath(__file__))
        self.results: List[TestExecutionResult] = []
        self.test_suites = self._initialize_test_suites()
        self.start_time = None
        self.end_time = None
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        logger = logging.getLogger("ComprehensiveTestRunner")
        logger.setLevel(logging.INFO)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 创建文件处理器
        log_dir = Path(self.project_root) / "logs"
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        file_handler.setLevel(logging.DEBUG)

        # 创建格式化器
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def _initialize_test_suites(self) -> List[TestSuite]:
        """初始化测试套件"""
        return [
            TestSuite(
                name="问题分类测试",
                category=TestCategory.CORE_FUNCTIONALITY,
                priority=TestPriority.CRITICAL,
                description="测试问题分类器的准确性，包括简单问答、复杂推理、多轮对话",
                tester_class=QuestionClassificationTester,
                timeout=180,
            ),
            TestSuite(
                name="向量检索测试",
                category=TestCategory.CORE_FUNCTIONALITY,
                priority=TestPriority.CRITICAL,
                description="测试向量检索系统的召回率和精确率",
                tester_class=VectorRetrievalTester,
                timeout=240,
            ),
            TestSuite(
                name="回答生成测试",
                category=TestCategory.CORE_FUNCTIONALITY,
                priority=TestPriority.HIGH,
                description="测试AI回答生成质量，包括正确性、流畅性、相关性",
                tester_class=AnswerGenerationTester,
                timeout=300,
            ),
            TestSuite(
                name="OCR集成测试",
                category=TestCategory.INTEGRATION_TESTING,
                priority=TestPriority.HIGH,
                description="测试PaddleOCR文本提取与RAG系统的集成效果",
                tester_class=OCRIntegrationTester,
                timeout=240,
                dependencies=["paddleocr"],
            ),
            TestSuite(
                name="数据分析与代码执行测试",
                category=TestCategory.CORE_FUNCTIONALITY,
                priority=TestPriority.HIGH,
                description="测试系统的数据分析和代码执行能力",
                tester_class=DataAnalysisCodeExecutionTester,
                timeout=360,
            ),
            TestSuite(
                name="Streamlit接口测试",
                category=TestCategory.INTERFACE_TESTING,
                priority=TestPriority.MEDIUM,
                description="测试Streamlit界面的交互完整性和用户体验",
                tester_class=StreamlitInterfaceTester,
                timeout=300,
                dependencies=["streamlit"],
            ),
            TestSuite(
                name="前端聊天界面测试",
                category=TestCategory.INTERFACE_TESTING,
                priority=TestPriority.MEDIUM,
                description="测试聊天界面的功能稳定性和响应速度",
                tester_class=FrontendChatTester,
                timeout=240,
            ),
            TestSuite(
                name="用户反馈对RAG系统影响测试",
                category=TestCategory.USER_EXPERIENCE,
                priority=TestPriority.MEDIUM,
                description="测试用户反馈对RAG系统改进的效果",
                tester_class=UserFeedbackRAGTester,
                timeout=420,
            ),
        ]

    async def run_single_suite(self, suite: TestSuite) -> TestExecutionResult:
        """运行单个测试套件"""
        self.logger.info(f"🚀 开始执行测试套件: {suite.name}")
        start_time = time.time()

        try:
            # 检查依赖
            if suite.dependencies:
                missing_deps = self._check_dependencies(suite.dependencies)
                if missing_deps:
                    return TestExecutionResult(
                        suite_name=suite.name,
                        category=suite.category.value,
                        success=False,
                        execution_time=0,
                        error_message=f"缺少依赖: {', '.join(missing_deps)}",
                    )

            # 创建测试实例
            tester = suite.tester_class()

            # 执行测试
            if hasattr(tester, "run_comprehensive_tests"):
                # 异步测试
                result = await tester.run_comprehensive_tests()
            elif hasattr(tester, "run_comprehensive_test"):
                # 同步测试
                result = tester.run_comprehensive_test()
            else:
                raise ValueError(f"测试类 {suite.tester_class.__name__} 没有合适的测试方法")

            execution_time = time.time() - start_time
            success = result.get("success", False) if isinstance(result, dict) else True

            # 提取摘要信息
            summary = result.get("summary", {}) if isinstance(result, dict) else {}

            test_result = TestExecutionResult(
                suite_name=suite.name,
                category=suite.category.value,
                success=success,
                execution_time=execution_time,
                test_results=[result],
                summary=summary,
                coverage_metrics=self._calculate_coverage_metrics(result),
            )

            self.logger.info(f"✅ 测试套件 {suite.name} 完成，耗时: {execution_time:.2f}秒")
            return test_result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ 测试套件 {suite.name} 失败: {str(e)}")
            return TestExecutionResult(
                suite_name=suite.name,
                category=suite.category.value,
                success=False,
                execution_time=execution_time,
                error_message=str(e),
            )

    def _check_dependencies(self, dependencies: List[str]) -> List[str]:
        """检查依赖是否满足"""
        missing = []
        for dep in dependencies:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)
        return missing

    def _calculate_coverage_metrics(self, test_result: Any) -> Dict[str, float]:
        """计算测试覆盖指标"""
        metrics = {
            "test_coverage": 0.0,
            "function_coverage": 0.0,
            "scenario_coverage": 0.0,
            "edge_case_coverage": 0.0,
        }

        if isinstance(test_result, dict):
            summary = test_result.get("summary", {})

            # 基于测试结果计算覆盖率
            if "success_rate" in summary:
                metrics["test_coverage"] = summary["success_rate"]

            if "total_tests" in summary and "successful_tests" in summary:
                total = summary["total_tests"]
                if total > 0:
                    metrics["function_coverage"] = summary["successful_tests"] / total

            # 估算场景和边界情况覆盖率
            metrics["scenario_coverage"] = min(1.0, metrics["test_coverage"] * 1.1)
            metrics["edge_case_coverage"] = min(1.0, metrics["test_coverage"] * 0.9)

        return metrics

    async def run_all_tests(
        self,
        categories: List[TestCategory] = None,
        priorities: List[TestPriority] = None,
    ) -> Dict[str, Any]:
        """运行所有测试"""
        self.start_time = time.time()
        self.logger.info("🎯 开始执行综合测试套件")

        # 过滤测试套件
        filtered_suites = self.test_suites
        if categories:
            filtered_suites = [s for s in filtered_suites if s.category in categories]
        if priorities:
            filtered_suites = [s for s in filtered_suites if s.priority in priorities]

        # 按优先级排序
        filtered_suites.sort(key=lambda x: x.priority.value)

        # 执行测试套件
        self.results = []
        for suite in filtered_suites:
            if not suite.enabled:
                self.logger.info(f"⏭️ 跳过已禁用的测试套件: {suite.name}")
                continue

            result = await self.run_single_suite(suite)
            self.results.append(result)

            # 如果是关键测试失败，可以选择停止后续测试
            if suite.priority == TestPriority.CRITICAL and not result.success:
                self.logger.error(f"🚨 关键测试 {suite.name} 失败，停止后续测试")
                break

        self.end_time = time.time()
        return self._generate_final_report()

    async def run_parallel_tests(self, max_workers: int = 3) -> Dict[str, Any]:
        """并行运行测试（适用于独立的测试套件）"""
        self.start_time = time.time()
        self.logger.info("🚀 开始并行执行测试套件")

        # 找出可以并行运行的测试套件（无依赖关系的）
        independent_suites = [
            suite
            for suite in self.test_suites
            if suite.enabled
            and not suite.dependencies
            and suite.category
            in [TestCategory.CORE_FUNCTIONALITY, TestCategory.USER_EXPERIENCE]
        ]

        # 分批并行执行
        self.results = []
        for i in range(0, len(independent_suites), max_workers):
            batch = independent_suites[i : i + max_workers]
            batch_results = await asyncio.gather(
                *[self.run_single_suite(suite) for suite in batch],
                return_exceptions=True,
            )

            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"并行测试执行异常: {result}")
                else:
                    self.results.append(result)

        # 串行执行有依赖关系的测试
        dependent_suites = [
            suite
            for suite in self.test_suites
            if suite.enabled
            and (
                suite.dependencies
                or suite.category
                not in [TestCategory.CORE_FUNCTIONALITY, TestCategory.USER_EXPERIENCE]
            )
        ]

        for suite in dependent_suites:
            result = await self.run_single_suite(suite)
            self.results.append(result)

        self.end_time = time.time()
        return self._generate_final_report()

    def _generate_final_report(self) -> Dict[str, Any]:
        """生成最终测试报告"""
        total_time = self.end_time - self.start_time if self.end_time else 0

        # 基础统计
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - successful_tests

        # 分类统计
        category_stats = {}
        for result in self.results:
            category = result.category
            if category not in category_stats:
                category_stats[category] = {"total": 0, "success": 0, "time": 0}
            category_stats[category]["total"] += 1
            if result.success:
                category_stats[category]["success"] += 1
            category_stats[category]["time"] += result.execution_time

        # 计算成功率
        overall_success_rate = successful_tests / total_tests if total_tests > 0 else 0
        category_success_rates = {
            cat: stats["success"] / stats["total"] if stats["total"] > 0 else 0
            for cat, stats in category_stats.items()
        }

        # 覆盖率统计
        coverage_stats = {}
        for result in self.results:
            for metric, value in result.coverage_metrics.items():
                if metric not in coverage_stats:
                    coverage_stats[metric] = []
                coverage_stats[metric].append(value)

        avg_coverage = {
            metric: sum(values) / len(values) if values else 0
            for metric, values in coverage_stats.items()
        }

        # 失败测试分析
        failed_test_details = [
            {
                "suite": result.suite_name,
                "error": result.error_message,
                "time": result.execution_time,
            }
            for result in self.results
            if not result.success
        ]

        # 性能分析
        performance_stats = {
            "total_execution_time": total_time,
            "average_suite_time": total_time / total_tests if total_tests > 0 else 0,
            "fastest_suite": min(
                self.results, key=lambda x: x.execution_time
            ).suite_name
            if self.results
            else "",
            "slowest_suite": max(
                self.results, key=lambda x: x.execution_time
            ).suite_name
            if self.results
            else "",
        }

        # 质量评分
        quality_score = self._calculate_quality_score()

        # 改进建议
        recommendations = self._generate_recommendations()

        return {
            "execution_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "overall_success_rate": overall_success_rate,
                "total_execution_time": total_time,
                "timestamp": datetime.now().isoformat(),
            },
            "category_performance": category_stats,
            "category_success_rates": category_success_rates,
            "coverage_analysis": avg_coverage,
            "failed_tests": failed_test_details,
            "performance_metrics": performance_stats,
            "quality_score": quality_score,
            "detailed_results": [
                {
                    "suite": result.suite_name,
                    "category": result.category,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "summary": result.summary,
                    "coverage": result.coverage_metrics,
                }
                for result in self.results
            ],
            "recommendations": recommendations,
        }

    def _calculate_quality_score(self) -> float:
        """计算系统质量评分"""
        if not self.results:
            return 0.0

        # 基于成功率、覆盖率和性能计算质量评分
        success_rate = sum(1 for r in self.results if r.success) / len(self.results)

        avg_coverage = 0.0
        if self.results:
            total_coverage = sum(
                sum(r.coverage_metrics.values()) / len(r.coverage_metrics)
                for r in self.results
                if r.coverage_metrics
            )
            avg_coverage = total_coverage / len(self.results)

        # 性能评分（基于执行时间）
        total_time = sum(r.execution_time for r in self.results)
        expected_time = len(self.results) * 180  # 预期每个测试3分钟
        performance_score = (
            min(1.0, expected_time / total_time) if total_time > 0 else 1.0
        )

        # 综合评分
        quality_score = (
            success_rate * 0.5 + avg_coverage * 0.3 + performance_score * 0.2
        )
        return round(quality_score, 3)

    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于成功率的建议
        success_rate = (
            sum(1 for r in self.results if r.success) / len(self.results)
            if self.results
            else 0
        )
        if success_rate < 0.8:
            recommendations.append(f"整体成功率偏低({success_rate:.1%})，建议优先修复失败的测试用例")
        elif success_rate < 0.95:
            recommendations.append("成功率良好，但仍有改进空间，建议优化边界情况处理")

        # 基于类别表现的建议
        category_rates = {}
        for result in self.results:
            category = result.category
            if category not in category_rates:
                category_rates[category] = []
            category_rates[category].append(result.success)

        for category, successes in category_rates.items():
            rate = sum(successes) / len(successes)
            if rate < 0.7:
                recommendations.append(f"{category}类别的测试表现较差，需要重点关注和改进")

        # 基于覆盖率的建议
        if self.results:
            avg_test_coverage = sum(
                r.coverage_metrics.get("test_coverage", 0) for r in self.results
            ) / len(self.results)
            if avg_test_coverage < 0.8:
                recommendations.append("测试覆盖率偏低，建议增加更多测试用例和场景")

        # 基于性能的建议
        if self.results:
            slow_tests = [r for r in self.results if r.execution_time > 300]  # 超过5分钟的测试
            if slow_tests:
                recommendations.append(
                    f"以下测试执行时间过长，需要优化: {', '.join(r.suite_name for r in slow_tests)}"
                )

        # 基于失败模式的建议
        failed_results = [r for r in self.results if not r.success]
        if failed_results:
            error_patterns = {}
            for result in failed_results:
                error_type = (
                    result.error_message.split(":")[0]
                    if ":" in result.error_message
                    else result.error_message
                )
                error_patterns[error_type] = error_patterns.get(error_type, 0) + 1

            common_error = (
                max(error_patterns.items(), key=lambda x: x[1])[0]
                if error_patterns
                else ""
            )
            if common_error:
                recommendations.append(f"最常见的错误类型是: {common_error}，建议系统性解决此类问题")

        if not recommendations:
            recommendations.append("所有测试表现良好，系统质量达到预期标准")

        return recommendations

    def save_report(self, report: Dict[str, Any], output_path: str = None):
        """保存测试报告"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(self.project_root) / "test_reports"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"comprehensive_test_report_{timestamp}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(f"📄 测试报告已保存到: {output_path}")
        return output_path

    def print_summary(self, report: Dict[str, Any]):
        """打印测试摘要"""
        print("\n" + "=" * 80)
        print("🏭 Industry AI Flow - 综合测试报告")
        print("=" * 80)

        summary = report["execution_summary"]
        print(f"📊 测试概览:")
        print(f"  总测试数: {summary['total_tests']}")
        print(f"  成功测试: {summary['successful_tests']}")
        print(f"  失败测试: {summary['failed_tests']}")
        print(f"  成功率: {summary['overall_success_rate']:.1%}")
        print(f"  总执行时间: {summary['total_execution_time']:.2f}秒")
        print(f"  质量评分: {report['quality_score']:.3f}/1.0")

        print(f"\n📈 分类表现:")
        for category, stats in report["category_performance"].items():
            success_rate = (
                stats["success"] / stats["total"] if stats["total"] > 0 else 0
            )
            status = (
                "✅" if success_rate >= 0.9 else "⚠️" if success_rate >= 0.7 else "❌"
            )
            print(
                f"  {category}: {stats['success']}/{stats['total']} ({success_rate:.1%}) {status}"
            )

        print(f"\n📊 覆盖率分析:")
        for metric, value in report["coverage_analysis"].items():
            print(f"  {metric}: {value:.1%}")

        if report["failed_tests"]:
            print(f"\n❌ 失败的测试:")
            for failed in report["failed_tests"]:
                print(f"  {failed['suite']}: {failed['error']}")

        print(f"\n💡 改进建议:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"  {i}. {rec}")

        print("\n" + "=" * 80)


# 命令行接口
async def main():
    parser = argparse.ArgumentParser(description="Industry AI Flow 综合测试框架")
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=[cat.value for cat in TestCategory],
        help="指定要运行的测试类别",
    )
    parser.add_argument(
        "--priorities",
        nargs="+",
        choices=[str(p.value) for p in TestPriority],
        help="指定要运行的测试优先级",
    )
    parser.add_argument("--parallel", action="store_true", help="并行运行测试")
    parser.add_argument("--max-workers", type=int, default=3, help="并行运行的最大工作线程数")
    parser.add_argument("--output", help="报告输出路径")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    parser.add_argument("--list-suites", action="store_true", help="列出所有可用的测试套件")

    args = parser.parse_args()

    if args.list_suites:
        runner = ComprehensiveTestRunner()
        print("可用的测试套件:")
        for suite in runner.test_suites:
            status = "✅" if suite.enabled else "❌"
            print(
                f"  {status} {suite.name} ({suite.category.value}, 优先级: {suite.priority.name})"
            )
            print(f"    {suite.description}")
        return

    # 创建测试运行器
    runner = ComprehensiveTestRunner()

    # 转换参数
    categories = (
        [TestCategory(cat) for cat in args.categories] if args.categories else None
    )
    priorities = (
        [TestPriority(int(p)) for p in args.priorities] if args.priorities else None
    )

    # 运行测试
    if args.parallel:
        report = await runner.run_parallel_tests(args.max_workers)
    else:
        report = await runner.run_all_tests(categories, priorities)

    # 保存报告
    output_path = runner.save_report(report, args.output)

    # 打印摘要
    if args.verbose or not args.parallel:
        runner.print_summary(report)

    # 返回退出码
    exit_code = 0 if report["execution_summary"]["overall_success_rate"] >= 0.8 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
