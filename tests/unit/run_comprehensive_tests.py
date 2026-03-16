#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Test Framework for Industry AI Flow

EN,EN,EN
EN,EN,EN,EN
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

# EN
from test_question_classification import QuestionClassificationTester
from test_streamlit_interface import StreamlitInterfaceTester
from test_user_feedback_rag_impact import UserFeedbackRAGTester
from test_vector_retrieval import VectorRetrievalTester


class TestCategory(Enum):
    """EN"""

    CORE_FUNCTIONALITY = "core_functionality"
    INTERFACE_TESTING = "interface_testing"
    PERFORMANCE_TESTING = "performance_testing"
    INTEGRATION_TESTING = "integration_testing"
    USER_EXPERIENCE = "user_experience"
    SAFETY_SECURITY = "safety_security"


class TestPriority(Enum):
    """EN"""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class TestSuite:
    """EN"""

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
    """EN"""

    suite_name: str
    category: str
    success: bool
    execution_time: float
    test_results: List[Any] = field(default_factory=list)
    error_message: str = ""
    summary: Dict[str, Any] = field(default_factory=dict)
    coverage_metrics: Dict[str, float] = field(default_factory=dict)


class ComprehensiveTestRunner:
    """EN"""

    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.dirname(os.path.abspath(__file__))
        self.results: List[TestExecutionResult] = []
        self.test_suites = self._initialize_test_suites()
        self.start_time = None
        self.end_time = None
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """EN"""
        logger = logging.getLogger("ComprehensiveTestRunner")
        logger.setLevel(logging.INFO)

        # EN
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # EN
        log_dir = Path(self.project_root) / "logs"
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        file_handler.setLevel(logging.DEBUG)

        # EN
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def _initialize_test_suites(self) -> List[TestSuite]:
        """EN"""
        return [
            TestSuite(
                name="EN",
                category=TestCategory.CORE_FUNCTIONALITY,
                priority=TestPriority.CRITICAL,
                description="EN,EN,EN,EN",
                tester_class=QuestionClassificationTester,
                timeout=180,
            ),
            TestSuite(
                name="EN",
                category=TestCategory.CORE_FUNCTIONALITY,
                priority=TestPriority.CRITICAL,
                description="EN",
                tester_class=VectorRetrievalTester,
                timeout=240,
            ),
            TestSuite(
                name="EN",
                category=TestCategory.CORE_FUNCTIONALITY,
                priority=TestPriority.HIGH,
                description="ENAIEN,EN,EN,EN",
                tester_class=AnswerGenerationTester,
                timeout=300,
            ),
            TestSuite(
                name="OCREN",
                category=TestCategory.INTEGRATION_TESTING,
                priority=TestPriority.HIGH,
                description="ENPaddleOCRENRAGEN",
                tester_class=OCRIntegrationTester,
                timeout=240,
                dependencies=["paddleocr"],
            ),
            TestSuite(
                name="EN",
                category=TestCategory.CORE_FUNCTIONALITY,
                priority=TestPriority.HIGH,
                description="EN",
                tester_class=DataAnalysisCodeExecutionTester,
                timeout=360,
            ),
            TestSuite(
                name="StreamlitEN",
                category=TestCategory.INTERFACE_TESTING,
                priority=TestPriority.MEDIUM,
                description="ENStreamlitEN",
                tester_class=StreamlitInterfaceTester,
                timeout=300,
                dependencies=["streamlit"],
            ),
            TestSuite(
                name="EN",
                category=TestCategory.INTERFACE_TESTING,
                priority=TestPriority.MEDIUM,
                description="EN",
                tester_class=FrontendChatTester,
                timeout=240,
            ),
            TestSuite(
                name="ENRAGEN",
                category=TestCategory.USER_EXPERIENCE,
                priority=TestPriority.MEDIUM,
                description="ENRAGEN",
                tester_class=UserFeedbackRAGTester,
                timeout=420,
            ),
        ]

    async def run_single_suite(self, suite: TestSuite) -> TestExecutionResult:
        """EN"""
        self.logger.info(f"🚀 EN: {suite.name}")
        start_time = time.time()

        try:
            # EN
            if suite.dependencies:
                missing_deps = self._check_dependencies(suite.dependencies)
                if missing_deps:
                    return TestExecutionResult(
                        suite_name=suite.name,
                        category=suite.category.value,
                        success=False,
                        execution_time=0,
                        error_message=f"EN: {', '.join(missing_deps)}",
                    )

            # EN
            tester = suite.tester_class()

            # EN
            if hasattr(tester, "run_comprehensive_tests"):
                # EN
                result = await tester.run_comprehensive_tests()
            elif hasattr(tester, "run_comprehensive_test"):
                # EN
                result = tester.run_comprehensive_test()
            else:
                raise ValueError(f"EN {suite.tester_class.__name__} EN")

            execution_time = time.time() - start_time
            success = result.get("success", False) if isinstance(result, dict) else True

            # EN
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

            self.logger.info(f"✅ EN {suite.name} EN,EN: {execution_time:.2f}EN")
            return test_result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ EN {suite.name} EN: {str(e)}")
            return TestExecutionResult(
                suite_name=suite.name,
                category=suite.category.value,
                success=False,
                execution_time=execution_time,
                error_message=str(e),
            )

    def _check_dependencies(self, dependencies: List[str]) -> List[str]:
        """EN"""
        missing = []
        for dep in dependencies:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)
        return missing

    def _calculate_coverage_metrics(self, test_result: Any) -> Dict[str, float]:
        """EN"""
        metrics = {
            "test_coverage": 0.0,
            "function_coverage": 0.0,
            "scenario_coverage": 0.0,
            "edge_case_coverage": 0.0,
        }

        if isinstance(test_result, dict):
            summary = test_result.get("summary", {})

            # EN
            if "success_rate" in summary:
                metrics["test_coverage"] = summary["success_rate"]

            if "total_tests" in summary and "successful_tests" in summary:
                total = summary["total_tests"]
                if total > 0:
                    metrics["function_coverage"] = summary["successful_tests"] / total

            # EN
            metrics["scenario_coverage"] = min(1.0, metrics["test_coverage"] * 1.1)
            metrics["edge_case_coverage"] = min(1.0, metrics["test_coverage"] * 0.9)

        return metrics

    async def run_all_tests(
        self,
        categories: List[TestCategory] = None,
        priorities: List[TestPriority] = None,
    ) -> Dict[str, Any]:
        """EN"""
        self.start_time = time.time()
        self.logger.info("🎯 EN")

        # EN
        filtered_suites = self.test_suites
        if categories:
            filtered_suites = [s for s in filtered_suites if s.category in categories]
        if priorities:
            filtered_suites = [s for s in filtered_suites if s.priority in priorities]

        # EN
        filtered_suites.sort(key=lambda x: x.priority.value)

        # EN
        self.results = []
        for suite in filtered_suites:
            if not suite.enabled:
                self.logger.info(f"⏭️ EN: {suite.name}")
                continue

            result = await self.run_single_suite(suite)
            self.results.append(result)

            # EN,EN
            if suite.priority == TestPriority.CRITICAL and not result.success:
                self.logger.error(f"🚨 EN {suite.name} EN,EN")
                break

        self.end_time = time.time()
        return self._generate_final_report()

    async def run_parallel_tests(self, max_workers: int = 3) -> Dict[str, Any]:
        """EN(EN)"""
        self.start_time = time.time()
        self.logger.info("🚀 EN")

        # EN(EN)
        independent_suites = [
            suite
            for suite in self.test_suites
            if suite.enabled
            and not suite.dependencies
            and suite.category
            in [TestCategory.CORE_FUNCTIONALITY, TestCategory.USER_EXPERIENCE]
        ]

        # EN
        self.results = []
        for i in range(0, len(independent_suites), max_workers):
            batch = independent_suites[i : i + max_workers]
            batch_results = await asyncio.gather(
                *[self.run_single_suite(suite) for suite in batch],
                return_exceptions=True,
            )

            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"EN: {result}")
                else:
                    self.results.append(result)

        # EN
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
        """EN"""
        total_time = self.end_time - self.start_time if self.end_time else 0

        # EN
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - successful_tests

        # EN
        category_stats = {}
        for result in self.results:
            category = result.category
            if category not in category_stats:
                category_stats[category] = {"total": 0, "success": 0, "time": 0}
            category_stats[category]["total"] += 1
            if result.success:
                category_stats[category]["success"] += 1
            category_stats[category]["time"] += result.execution_time

        # EN
        overall_success_rate = successful_tests / total_tests if total_tests > 0 else 0
        category_success_rates = {
            cat: stats["success"] / stats["total"] if stats["total"] > 0 else 0
            for cat, stats in category_stats.items()
        }

        # EN
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

        # EN
        failed_test_details = [
            {
                "suite": result.suite_name,
                "error": result.error_message,
                "time": result.execution_time,
            }
            for result in self.results
            if not result.success
        ]

        # EN
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

        # EN
        quality_score = self._calculate_quality_score()

        # EN
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
        """EN"""
        if not self.results:
            return 0.0

        # EN,EN
        success_rate = sum(1 for r in self.results if r.success) / len(self.results)

        avg_coverage = 0.0
        if self.results:
            total_coverage = sum(
                sum(r.coverage_metrics.values()) / len(r.coverage_metrics)
                for r in self.results
                if r.coverage_metrics
            )
            avg_coverage = total_coverage / len(self.results)

        # EN(EN)
        total_time = sum(r.execution_time for r in self.results)
        expected_time = len(self.results) * 180  # EN3EN
        performance_score = (
            min(1.0, expected_time / total_time) if total_time > 0 else 1.0
        )

        # EN
        quality_score = (
            success_rate * 0.5 + avg_coverage * 0.3 + performance_score * 0.2
        )
        return round(quality_score, 3)

    def _generate_recommendations(self) -> List[str]:
        """EN"""
        recommendations = []

        # EN
        success_rate = (
            sum(1 for r in self.results if r.success) / len(self.results)
            if self.results
            else 0
        )
        if success_rate < 0.8:
            recommendations.append(f"EN({success_rate:.1%}),EN")
        elif success_rate < 0.95:
            recommendations.append("EN,EN,EN")

        # EN
        category_rates = {}
        for result in self.results:
            category = result.category
            if category not in category_rates:
                category_rates[category] = []
            category_rates[category].append(result.success)

        for category, successes in category_rates.items():
            rate = sum(successes) / len(successes)
            if rate < 0.7:
                recommendations.append(f"{category}EN,EN")

        # EN
        if self.results:
            avg_test_coverage = sum(
                r.coverage_metrics.get("test_coverage", 0) for r in self.results
            ) / len(self.results)
            if avg_test_coverage < 0.8:
                recommendations.append("EN,EN")

        # EN
        if self.results:
            slow_tests = [r for r in self.results if r.execution_time > 300]  # EN5EN
            if slow_tests:
                recommendations.append(
                    f"EN,EN: {', '.join(r.suite_name for r in slow_tests)}"
                )

        # EN
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
                recommendations.append(f"EN: {common_error},EN")

        if not recommendations:
            recommendations.append("EN,EN")

        return recommendations

    def save_report(self, report: Dict[str, Any], output_path: str = None):
        """EN"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(self.project_root) / "test_reports"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"comprehensive_test_report_{timestamp}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(f"📄 EN: {output_path}")
        return output_path

    def print_summary(self, report: Dict[str, Any]):
        """EN"""
        print("\n" + "=" * 80)
        print("🏭 Industry AI Flow - EN")
        print("=" * 80)

        summary = report["execution_summary"]
        print(f"📊 EN:")
        print(f"  EN: {summary['total_tests']}")
        print(f"  EN: {summary['successful_tests']}")
        print(f"  EN: {summary['failed_tests']}")
        print(f"  EN: {summary['overall_success_rate']:.1%}")
        print(f"  EN: {summary['total_execution_time']:.2f}EN")
        print(f"  EN: {report['quality_score']:.3f}/1.0")

        print(f"\n📈 EN:")
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

        print(f"\n📊 EN:")
        for metric, value in report["coverage_analysis"].items():
            print(f"  {metric}: {value:.1%}")

        if report["failed_tests"]:
            print(f"\n❌ EN:")
            for failed in report["failed_tests"]:
                print(f"  {failed['suite']}: {failed['error']}")

        print(f"\n💡 EN:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"  {i}. {rec}")

        print("\n" + "=" * 80)


# EN
async def main():
    parser = argparse.ArgumentParser(description="Industry AI Flow EN")
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=[cat.value for cat in TestCategory],
        help="EN",
    )
    parser.add_argument(
        "--priorities",
        nargs="+",
        choices=[str(p.value) for p in TestPriority],
        help="EN",
    )
    parser.add_argument("--parallel", action="store_true", help="EN")
    parser.add_argument("--max-workers", type=int, default=3, help="EN")
    parser.add_argument("--output", help="EN")
    parser.add_argument("--verbose", action="store_true", help="EN")
    parser.add_argument("--list-suites", action="store_true", help="EN")

    args = parser.parse_args()

    if args.list_suites:
        runner = ComprehensiveTestRunner()
        print("EN:")
        for suite in runner.test_suites:
            status = "✅" if suite.enabled else "❌"
            print(
                f"  {status} {suite.name} ({suite.category.value}, EN: {suite.priority.name})"
            )
            print(f"    {suite.description}")
        return

    # EN
    runner = ComprehensiveTestRunner()

    # EN
    categories = (
        [TestCategory(cat) for cat in args.categories] if args.categories else None
    )
    priorities = (
        [TestPriority(int(p)) for p in args.priorities] if args.priorities else None
    )

    # EN
    if args.parallel:
        report = await runner.run_parallel_tests(args.max_workers)
    else:
        report = await runner.run_all_tests(categories, priorities)

    # EN
    output_path = runner.save_report(report, args.output)

    # EN
    if args.verbose or not args.parallel:
        runner.print_summary(report)

    # EN
    exit_code = 0 if report["execution_summary"]["overall_success_rate"] >= 0.8 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
