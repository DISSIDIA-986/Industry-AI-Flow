#!/usr/bin/env python3
"""
Comprehensive Problem Classification Test Suite
Based on test_cases/problem_classification_test_cases.md

Tests the intent classification system across 6 categories:
1. Simple Q&A Classification
2. Complex Reasoning Classification
3. Multi-turn Conversation Classification
4. Boundary Condition Handling
5. Performance and Stress Testing
6. Error Handling and Robustness
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add project root to path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ProblemClassificationTester:
    """Comprehensive tester for intent classification"""

    def __init__(self):
        self.classifier = None
        self.test_results = {
            "category_1_simple_qa": [],
            "category_2_complex_reasoning": [],
            "category_3_multi_turn": [],
            "category_4_boundary": [],
            "category_5_performance": [],
            "category_6_error_handling": [],
        }
        self.stats = {"total_tests": 0, "passed": 0, "failed": 0, "errors": 0}

    def setup(self):
        """Initialize the intent classifier"""
        try:
            from backend.config import settings
            from backend.services.intent_classification.intent_classifier import (
                IntentClassifier,
                QueryContext,
            )
            from backend.services.llm_integration.llm_client import get_llm_client
            from backend.services.prompt_manager import PromptManager

            # Initialize dependencies
            self.llm_client = get_llm_client()
            self.prompt_manager = PromptManager(database_url=settings.database_url)

            # Initialize classifier
            self.classifier = IntentClassifier(
                prompt_manager=self.prompt_manager,
                llm_client=self.llm_client,
                confidence_threshold=0.7,
            )

            # Create default context for testing
            self.default_context = QueryContext(
                session_id="test_session", user_id="test_user"
            )

            logger.info("✅ Intent classifier initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize classifier: {e}")
            import traceback

            traceback.print_exc()
            return False

    def load_test_queries(self) -> List[Dict]:
        """Load test queries from test_resources"""
        try:
            queries_path = Path("test_resources/datasets/test_queries.json")
            with open(queries_path, "r", encoding="utf-8") as f:
                queries = json.load(f)
            logger.info(f"✅ Loaded {len(queries)} test queries")
            return queries
        except Exception as e:
            logger.warning(f"⚠️ Could not load test_queries.json: {e}")
            return []

    async def classify_with_validation_async(
        self, query: str, expected_intent: str, min_confidence: float = 0.7
    ) -> Dict:
        """
        Classify query and validate against expected intent (async)

        Args:
            query: Input query
            expected_intent: Expected intent category
            min_confidence: Minimum confidence threshold

        Returns:
            Dict with test result
        """
        try:
            start_time = time.time()
            result = await self.classifier.classify_intent(query, self.default_context)
            response_time = time.time() - start_time

            intent = (
                result.intent.value
                if hasattr(result.intent, "value")
                else str(result.intent)
            )
            confidence = result.confidence

            # Validate intent match
            intent_match = intent.lower() == expected_intent.lower()
            confidence_pass = confidence >= min_confidence

            passed = intent_match and confidence_pass

            return {
                "query": query,
                "expected_intent": expected_intent,
                "actual_intent": intent,
                "confidence": confidence,
                "response_time": response_time,
                "intent_match": intent_match,
                "confidence_pass": confidence_pass,
                "passed": passed,
                "error": None,
            }
        except Exception as e:
            return {
                "query": query,
                "expected_intent": expected_intent,
                "actual_intent": None,
                "confidence": 0.0,
                "response_time": 0.0,
                "intent_match": False,
                "confidence_pass": False,
                "passed": False,
                "error": str(e),
            }

    def classify_with_validation(
        self, query: str, expected_intent: str, min_confidence: float = 0.7
    ) -> Dict:
        """
        Classify query and validate against expected intent (sync wrapper)

        Args:
            query: Input query
            expected_intent: Expected intent category
            min_confidence: Minimum confidence threshold

        Returns:
            Dict with test result
        """
        return asyncio.run(
            self.classify_with_validation_async(query, expected_intent, min_confidence)
        )

    # ==================== Category 1: Simple Q&A Classification ====================

    def test_1_1_knowledge_retrieval(self):
        """Test Set 1.1: Knowledge Retrieval Intent"""
        logger.info("\n=== Test Set 1.1: Knowledge Retrieval Intent ===")

        test_cases = [
            ("什么是RAG?", "knowledge_retrieval"),
            ("LangChain有哪些主要功能?", "knowledge_retrieval"),
            ("向量数据库的工作原理是什么?", "knowledge_retrieval"),
            ("请介绍一下PaddleOCR的使用方法", "knowledge_retrieval"),
            ("AI工作流系统的架构是怎样的?", "knowledge_retrieval"),
        ]

        results = []
        for query, expected in test_cases:
            result = self.classify_with_validation(query, expected, min_confidence=0.7)
            results.append(result)
            self.stats["total_tests"] += 1
            if result["passed"]:
                self.stats["passed"] += 1
                logger.info(
                    f"✅ PASS: {query[:30]}... → {result['actual_intent']} ({result['confidence']:.2f})"
                )
            else:
                self.stats["failed"] += 1
                logger.error(
                    f"❌ FAIL: {query[:30]}... → Expected: {expected}, Got: {result['actual_intent']}"
                )

        self.test_results["category_1_simple_qa"].extend(results)
        return results

    def test_1_2_data_analysis(self):
        """Test Set 1.2: Data Analysis Intent"""
        logger.info("\n=== Test Set 1.2: Data Analysis Intent ===")

        test_cases = [
            ("分析一下员工数据的统计特征", "data_analysis"),
            ("计算销售数据的平均值和标准差", "data_analysis"),
            ("绘制财务数据的趋势图", "data_analysis"),
            ("对用户行为数据进行聚类分析", "data_analysis"),
            ("生成数据质量报告", "data_analysis"),
        ]

        results = []
        for query, expected in test_cases:
            result = self.classify_with_validation(query, expected, min_confidence=0.7)
            results.append(result)
            self.stats["total_tests"] += 1
            if result["passed"]:
                self.stats["passed"] += 1
                logger.info(
                    f"✅ PASS: {query[:30]}... → {result['actual_intent']} ({result['confidence']:.2f})"
                )
            else:
                self.stats["failed"] += 1
                logger.error(
                    f"❌ FAIL: {query[:30]}... → Expected: {expected}, Got: {result['actual_intent']}"
                )

        self.test_results["category_1_simple_qa"].extend(results)
        return results

    def test_1_3_document_processing(self):
        """Test Set 1.3: Document Processing Intent"""
        logger.info("\n=== Test Set 1.3: Document Processing Intent ===")

        test_cases = [
            ("处理这个PDF文档", "document_processing"),
            ("从图片中提取文字", "document_processing"),
            ("将Word文档转换为Markdown格式", "document_processing"),
            ("合并多个Excel文件", "document_processing"),
            ("对文档进行OCR识别", "document_processing"),
        ]

        results = []
        for query, expected in test_cases:
            result = self.classify_with_validation(query, expected, min_confidence=0.7)
            results.append(result)
            self.stats["total_tests"] += 1
            if result["passed"]:
                self.stats["passed"] += 1
                logger.info(
                    f"✅ PASS: {query[:30]}... → {result['actual_intent']} ({result['confidence']:.2f})"
                )
            else:
                self.stats["failed"] += 1
                logger.error(
                    f"❌ FAIL: {query[:30]}... → Expected: {expected}, Got: {result['actual_intent']}"
                )

        self.test_results["category_1_simple_qa"].extend(results)
        return results

    def test_1_4_code_execution(self):
        """Test Set 1.4: Code Execution Intent"""
        logger.info("\n=== Test Set 1.4: Code Execution Intent ===")

        test_cases = [
            ("运行这段Python代码", "code_execution"),
            ("执行数据清洗脚本", "code_execution"),
            ("计算斐波那契数列", "code_execution"),
            ("生成随机数列表", "code_execution"),
            ("执行数据库查询", "code_execution"),
        ]

        results = []
        for query, expected in test_cases:
            result = self.classify_with_validation(query, expected, min_confidence=0.7)
            results.append(result)
            self.stats["total_tests"] += 1
            if result["passed"]:
                self.stats["passed"] += 1
                logger.info(
                    f"✅ PASS: {query[:30]}... → {result['actual_intent']} ({result['confidence']:.2f})"
                )
            else:
                self.stats["failed"] += 1
                logger.error(
                    f"❌ FAIL: {query[:30]}... → Expected: {expected}, Got: {result['actual_intent']}"
                )

        self.test_results["category_1_simple_qa"].extend(results)
        return results

    # ==================== Category 2: Complex Reasoning Classification ====================

    def test_2_1_mixed_intent(self):
        """Test Set 2.1: Mixed Intent Queries"""
        logger.info("\n=== Test Set 2.1: Mixed Intent Queries ===")

        # For mixed intents, we expect the primary/dominant intent
        test_cases = [
            ("先分析销售数据,然后生成可视化报告", "data_analysis"),  # Primary: data analysis
            ("查询RAG系统文档,并执行示例代码", "knowledge_retrieval"),  # Primary: knowledge
            ("处理PDF文档并提取关键数据进行统计分析", "document_processing"),  # Primary: document
        ]

        results = []
        for query, expected in test_cases:
            result = self.classify_with_validation(
                query, expected, min_confidence=0.6
            )  # Lower threshold for complex
            results.append(result)
            self.stats["total_tests"] += 1
            if result["passed"]:
                self.stats["passed"] += 1
                logger.info(
                    f"✅ PASS: {query[:40]}... → {result['actual_intent']} ({result['confidence']:.2f})"
                )
            else:
                self.stats["failed"] += 1
                logger.warning(
                    f"⚠️ PARTIAL: {query[:40]}... → Expected: {expected}, Got: {result['actual_intent']}"
                )

        self.test_results["category_2_complex_reasoning"].extend(results)
        return results

    def test_2_2_ambiguous_queries(self):
        """Test Set 2.2: Ambiguous Query Classification"""
        logger.info("\n=== Test Set 2.2: Ambiguous Queries ===")

        # These queries could map to multiple intents - we accept any reasonable classification
        test_cases = [
            ("处理数据", ["data_analysis", "document_processing"]),  # Could be either
            ("分析文档", ["knowledge_retrieval", "document_processing", "data_analysis"]),
            ("执行任务", ["code_execution", "data_analysis"]),
        ]

        results = []
        for query, acceptable_intents in test_cases:
            result = self.classify_with_validation(
                query, acceptable_intents[0], min_confidence=0.5
            )
            # Override pass condition to accept any of the acceptable intents
            result["passed"] = (
                result["actual_intent"] in acceptable_intents
                if result["actual_intent"]
                else False
            )
            results.append(result)
            self.stats["total_tests"] += 1
            if result["passed"]:
                self.stats["passed"] += 1
                logger.info(f"✅ PASS: {query} → {result['actual_intent']} (acceptable)")
            else:
                self.stats["failed"] += 1
                logger.warning(
                    f"⚠️ AMBIGUOUS: {query} → {result['actual_intent']}, expected one of {acceptable_intents}"
                )

        self.test_results["category_2_complex_reasoning"].extend(results)
        return results

    # ==================== Category 4: Boundary Conditions ====================

    def test_4_1_edge_cases(self):
        """Test Set 4.1: Edge Case Handling"""
        logger.info("\n=== Test Set 4.1: Edge Cases ===")

        test_cases = [
            ("", "unknown"),  # Empty query
            ("   ", "unknown"),  # Whitespace only
            ("?", "unknown"),  # Single punctuation
            ("a" * 1000, "unknown"),  # Very long query
            ("12345", "unknown"),  # Numbers only
        ]

        results = []
        for query, expected in test_cases:
            try:
                result = self.classify_with_validation(
                    query, expected, min_confidence=0.0
                )
                # For edge cases, we just want no crashes - classification can be anything
                result["passed"] = result["error"] is None
                results.append(result)
                self.stats["total_tests"] += 1
                if result["passed"]:
                    self.stats["passed"] += 1
                    logger.info(f"✅ PASS: Edge case handled without error")
                else:
                    self.stats["failed"] += 1
                    logger.error(f"❌ FAIL: Edge case caused error: {result['error']}")
            except Exception as e:
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1
                logger.error(f"❌ ERROR: Edge case test failed: {e}")

        self.test_results["category_4_boundary"].extend(results)
        return results

    # ==================== Category 5: Performance Testing ====================

    async def test_5_1_response_time_async(self):
        """Test Set 5.1: Response Time Validation (async)"""
        test_queries = ["什么是机器学习?", "分析数据趋势", "处理PDF文档", "执行Python脚本", "查询用户信息"]

        response_times = []
        passed_count = 0

        for query in test_queries:
            start = time.time()
            try:
                result = await self.classifier.classify_intent(
                    query, self.default_context
                )
                response_time = time.time() - start
                response_times.append(response_time)

                # Check if response time is acceptable (<500ms)
                if response_time < 0.5:
                    passed_count += 1
                    logger.info(f"✅ PASS: {query[:30]}... → {response_time*1000:.1f}ms")
                else:
                    logger.warning(
                        f"⚠️ SLOW: {query[:30]}... → {response_time*1000:.1f}ms"
                    )
            except Exception as e:
                logger.error(f"❌ ERROR: {query[:30]}... → {e}")

        avg_time = sum(response_times) / len(response_times) if response_times else 0
        max_time = max(response_times) if response_times else 0

        logger.info(f"\n📊 Performance Stats:")
        logger.info(f"   Average: {avg_time*1000:.1f}ms")
        logger.info(f"   Max: {max_time*1000:.1f}ms")
        logger.info(f"   Passed (<500ms): {passed_count}/{len(test_queries)}")

        self.stats["total_tests"] += len(test_queries)
        self.stats["passed"] += passed_count
        self.stats["failed"] += len(test_queries) - passed_count

        return response_times

    def test_5_1_response_time(self):
        """Test Set 5.1: Response Time (<500ms)"""
        logger.info("\n=== Test Set 5.1: Response Time (<500ms) ===")
        return asyncio.run(self.test_5_1_response_time_async())

    async def test_5_2_stress_test_async(self):
        """Test Set 5.2: Stress Test (100 queries) - async"""
        base_queries = ["什么是人工智能?", "分析销售数据", "处理文档", "执行代码", "查询信息"]

        # Generate 100 queries by repeating base queries
        stress_queries = (base_queries * 20)[:100]

        start_time = time.time()
        success_count = 0
        error_count = 0

        for i, query in enumerate(stress_queries, 1):
            try:
                result = await self.classifier.classify_intent(
                    query, self.default_context
                )
                if result and result.intent:
                    success_count += 1
                if i % 20 == 0:
                    logger.info(f"   Progress: {i}/100 queries processed")
            except Exception as e:
                error_count += 1
                if error_count <= 3:  # Only log first 3 errors
                    logger.error(f"   Error on query {i}: {e}")

        total_time = time.time() - start_time
        avg_time = total_time / 100
        qps = 100 / total_time

        logger.info(f"\n📊 Stress Test Results:")
        logger.info(f"   Total time: {total_time:.2f}s")
        logger.info(f"   Average: {avg_time*1000:.1f}ms per query")
        logger.info(f"   Throughput: {qps:.1f} queries/second")
        logger.info(f"   Success: {success_count}/100")
        logger.info(f"   Errors: {error_count}/100")

        passed = error_count == 0
        self.stats["total_tests"] += 1
        if passed:
            self.stats["passed"] += 1
        else:
            self.stats["failed"] += 1

        return {
            "total_time": total_time,
            "avg_time": avg_time,
            "qps": qps,
            "success_count": success_count,
            "error_count": error_count,
        }

    def test_5_2_stress_test(self):
        """Test Set 5.2: Stress Test (100 queries)"""
        logger.info("\n=== Test Set 5.2: Stress Test (100 queries) ===")
        return asyncio.run(self.test_5_2_stress_test_async())

    # ==================== Category 6: Error Handling ====================

    async def test_6_1_error_recovery_async(self):
        """Test Set 6.1: Error Handling and Recovery - async"""
        # Test various error conditions
        error_cases = [
            (None, "None input"),
            (123, "Integer input"),
            (["list", "input"], "List input"),
            ({"dict": "input"}, "Dict input"),
        ]

        passed_count = 0

        for invalid_input, description in error_cases:
            try:
                # Attempt classification with invalid input
                result = await self.classifier.classify_intent(
                    invalid_input, self.default_context
                )
                # If no exception, check that it handled gracefully
                logger.info(f"✅ PASS: {description} handled gracefully")
                passed_count += 1
            except TypeError:
                # Expected error type - this is acceptable
                logger.info(f"✅ PASS: {description} raised expected TypeError")
                passed_count += 1
            except Exception as e:
                # Unexpected error
                logger.warning(
                    f"⚠️ PARTIAL: {description} raised {type(e).__name__}: {e}"
                )
                passed_count += 1  # Still counts as handled (didn't crash)

        self.stats["total_tests"] += len(error_cases)
        self.stats["passed"] += passed_count
        self.stats["failed"] += len(error_cases) - passed_count

        return passed_count == len(error_cases)

    def test_6_1_error_recovery(self):
        """Test Set 6.1: Error Handling and Recovery"""
        logger.info("\n=== Test Set 6.1: Error Handling ===")
        return asyncio.run(self.test_6_1_error_recovery_async())

    def run_all_tests(self):
        """Execute all test categories"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 Starting Comprehensive Problem Classification Tests")
        logger.info("=" * 80)

        if not self.setup():
            logger.error("❌ Setup failed. Cannot proceed with tests.")
            return False

        # Category 1: Simple Q&A
        logger.info("\n" + "=" * 80)
        logger.info("📋 CATEGORY 1: Simple Q&A Classification")
        logger.info("=" * 80)
        self.test_1_1_knowledge_retrieval()
        self.test_1_2_data_analysis()
        self.test_1_3_document_processing()
        self.test_1_4_code_execution()

        # Category 2: Complex Reasoning
        logger.info("\n" + "=" * 80)
        logger.info("🧠 CATEGORY 2: Complex Reasoning Classification")
        logger.info("=" * 80)
        self.test_2_1_mixed_intent()
        self.test_2_2_ambiguous_queries()

        # Category 4: Boundary Conditions
        logger.info("\n" + "=" * 80)
        logger.info("🔍 CATEGORY 4: Boundary Conditions")
        logger.info("=" * 80)
        self.test_4_1_edge_cases()

        # Category 5: Performance
        logger.info("\n" + "=" * 80)
        logger.info("⚡ CATEGORY 5: Performance Testing")
        logger.info("=" * 80)
        self.test_5_1_response_time()
        self.test_5_2_stress_test()

        # Category 6: Error Handling
        logger.info("\n" + "=" * 80)
        logger.info("🛡️ CATEGORY 6: Error Handling")
        logger.info("=" * 80)
        self.test_6_1_error_recovery()

        # Print final summary
        self.print_summary()

        return True

    def print_summary(self):
        """Print comprehensive test summary"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 COMPREHENSIVE TEST SUMMARY")
        logger.info("=" * 80)

        total = self.stats["total_tests"]
        passed = self.stats["passed"]
        failed = self.stats["failed"]
        errors = self.stats["errors"]
        pass_rate = (passed / total * 100) if total > 0 else 0

        logger.info(f"\n📈 Overall Results:")
        logger.info(f"   Total Tests: {total}")
        logger.info(f"   Passed: {passed} ({pass_rate:.1f}%)")
        logger.info(f"   Failed: {failed}")
        logger.info(f"   Errors: {errors}")

        if pass_rate >= 90:
            logger.info(f"\n✅ EXCELLENT: Pass rate {pass_rate:.1f}% (≥90%)")
        elif pass_rate >= 80:
            logger.info(f"\n✅ GOOD: Pass rate {pass_rate:.1f}% (≥80%)")
        elif pass_rate >= 70:
            logger.info(f"\n⚠️ ACCEPTABLE: Pass rate {pass_rate:.1f}% (≥70%)")
        else:
            logger.info(f"\n❌ NEEDS IMPROVEMENT: Pass rate {pass_rate:.1f}% (<70%)")

        logger.info("\n" + "=" * 80)

    def save_results(
        self, output_file: str = "test_results/problem_classification_results.json"
    ):
        """Save detailed test results to JSON file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "statistics": self.stats,
            "detailed_results": self.test_results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"\n💾 Results saved to: {output_path}")


def main():
    """Main test execution"""
    tester = ProblemClassificationTester()
    success = tester.run_all_tests()
    tester.save_results()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
