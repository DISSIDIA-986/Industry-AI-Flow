#!/usr/bin/env python3
"""
Comprehensive Vector Retrieval Test Suite
Based on test_cases/vector_retrieval_test_cases.md

Tests the vector retrieval system across multiple dimensions:
1. Recall Rate Tests (exact match, synonym-based, conceptual matching)
2. Precision Tests (relevant results density, semantic precision)
3. Different Dataset Tests
4. Query Complexity Tests
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Set

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VectorRetrievalTester:
    """Comprehensive tester for vector retrieval"""

    def __init__(self):
        self.rag_engine = None
        self.test_results = {
            "recall_tests": [],
            "precision_tests": [],
            "dataset_tests": [],
            "complexity_tests": [],
        }
        self.stats = {"total_tests": 0, "passed": 0, "failed": 0, "errors": 0}

    def setup(self):
        """Initialize the RAG engine"""
        try:
            from backend.config import settings
            from backend.services.rag_engine import SimpleRAG

            # Initialize RAG with hybrid search and reranker
            self.rag_engine = SimpleRAG(
                use_hybrid_search=True,
                use_reranker=True,
                enable_feedback=False,  # Disable for testing
            )

            logger.info("✅ RAG engine initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG engine: {e}")
            import traceback

            traceback.print_exc()
            return False

    def load_test_documents(self) -> List[Dict]:
        """Load test documents from test_resources"""
        try:
            docs_dir = Path("test_resources/documents")
            documents = []

            # Load AI research paper
            ai_research = docs_dir / "ai_research_paper.txt"
            if ai_research.exists():
                with open(ai_research, "r", encoding="utf-8") as f:
                    content = f.read()
                    documents.append(
                        {
                            "content": content,
                            "metadata": {
                                "doc_id": "ai_research",
                                "source": "ai_research_paper.txt",
                                "type": "text",
                            },
                        }
                    )

            # Load RAG documentation
            rag_doc = docs_dir / "retrieval_augmented_generation.md"
            if rag_doc.exists():
                with open(rag_doc, "r", encoding="utf-8") as f:
                    content = f.read()
                    documents.append(
                        {
                            "content": content,
                            "metadata": {
                                "doc_id": "rag_doc",
                                "source": "retrieval_augmented_generation.md",
                                "type": "markdown",
                            },
                        }
                    )

            # Load AI basics
            ai_basics = docs_dir / "sample_ai_basics.md"
            if ai_basics.exists():
                with open(ai_basics, "r", encoding="utf-8") as f:
                    content = f.read()
                    documents.append(
                        {
                            "content": content,
                            "metadata": {
                                "doc_id": "ai_basics",
                                "source": "sample_ai_basics.md",
                                "type": "markdown",
                            },
                        }
                    )

            logger.info(f"✅ Loaded {len(documents)} test documents")
            return documents
        except Exception as e:
            logger.warning(f"⚠️ Could not load test documents: {e}")
            return []

    def add_test_documents(self, documents: List[Dict]) -> bool:
        """Add test documents to RAG engine"""
        try:
            if not documents:
                logger.warning("No documents to add")
                return False

            success = self.rag_engine.add_documents(documents)
            if success:
                logger.info(f"✅ Added {len(documents)} documents to RAG engine")
            else:
                logger.error("❌ Failed to add documents")
            return success
        except Exception as e:
            logger.error(f"❌ Error adding documents: {e}")
            import traceback

            traceback.print_exc()
            return False

    def calculate_recall(
        self, retrieved_ids: Set[str], relevant_ids: Set[str]
    ) -> float:
        """Calculate recall: retrieved_relevant / total_relevant"""
        if not relevant_ids:
            return 0.0
        intersection = retrieved_ids.intersection(relevant_ids)
        return len(intersection) / len(relevant_ids)

    def calculate_precision(
        self, retrieved_ids: Set[str], relevant_ids: Set[str]
    ) -> float:
        """Calculate precision: retrieved_relevant / total_retrieved"""
        if not retrieved_ids:
            return 0.0
        intersection = retrieved_ids.intersection(relevant_ids)
        return len(intersection) / len(retrieved_ids)

    # ==================== Test Category 1: Recall Rate Tests ====================

    def test_1_1_exact_match_recall(self):
        """Test Set 1.1: Exact Match Recall"""
        logger.info("\n=== Test Set 1.1: Exact Match Recall ===")

        # Test cases with exact keywords from documents
        test_cases = [
            {
                "query": "What is RAG?",
                "expected_docs": {"rag_doc"},  # Should find RAG documentation
                "min_recall": 0.8,
            },
            {
                "query": "machine learning basics",
                "expected_docs": {"ai_basics", "ai_research"},  # Could be in both
                "min_recall": 0.5,  # At least one should be found
            },
            {
                "query": "artificial intelligence research",
                "expected_docs": {"ai_research", "ai_basics"},
                "min_recall": 0.5,
            },
        ]

        results = []
        for test_case in test_cases:
            query = test_case["query"]
            expected_docs = test_case["expected_docs"]
            min_recall = test_case["min_recall"]

            try:
                # Perform retrieval
                result = self.rag_engine.query(query, top_k=5)
                retrieved_docs = set(
                    [
                        chunk.get("doc_id", "").split("_chunk")[0]
                        for chunk in result.get("retrieved_chunks", [])
                    ]
                )

                # Calculate recall
                recall = self.calculate_recall(retrieved_docs, expected_docs)

                passed = recall >= min_recall
                test_result = {
                    "query": query,
                    "expected_docs": list(expected_docs),
                    "retrieved_docs": list(retrieved_docs),
                    "recall": recall,
                    "min_recall": min_recall,
                    "passed": passed,
                }
                results.append(test_result)

                self.stats["total_tests"] += 1
                if passed:
                    self.stats["passed"] += 1
                    logger.info(
                        f"✅ PASS: '{query}' → Recall: {recall:.2f} (≥{min_recall:.2f})"
                    )
                else:
                    self.stats["failed"] += 1
                    logger.error(
                        f"❌ FAIL: '{query}' → Recall: {recall:.2f} (<{min_recall:.2f})"
                    )

            except Exception as e:
                logger.error(f"❌ ERROR: {query} → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

        self.test_results["recall_tests"].extend(results)
        return results

    def test_1_2_synonym_recall(self):
        """Test Set 1.2: Synonym-Based Recall"""
        logger.info("\n=== Test Set 1.2: Synonym-Based Recall ===")

        # Test cases using synonyms and related terms
        test_cases = [
            {
                "query": "retrieval augmented generation systems",
                "expected_docs": {"rag_doc"},
                "min_recall": 0.7,  # Should find RAG doc even with different phrasing
            },
            {
                "query": "ML fundamentals",  # ML = Machine Learning
                "expected_docs": {"ai_basics", "ai_research"},
                "min_recall": 0.5,
            },
        ]

        results = []
        for test_case in test_cases:
            query = test_case["query"]
            expected_docs = test_case["expected_docs"]
            min_recall = test_case["min_recall"]

            try:
                result = self.rag_engine.query(query, top_k=5)
                retrieved_docs = set(
                    [
                        chunk.get("doc_id", "").split("_chunk")[0]
                        for chunk in result.get("retrieved_chunks", [])
                    ]
                )

                recall = self.calculate_recall(retrieved_docs, expected_docs)
                passed = recall >= min_recall

                test_result = {
                    "query": query,
                    "expected_docs": list(expected_docs),
                    "retrieved_docs": list(retrieved_docs),
                    "recall": recall,
                    "min_recall": min_recall,
                    "passed": passed,
                }
                results.append(test_result)

                self.stats["total_tests"] += 1
                if passed:
                    self.stats["passed"] += 1
                    logger.info(f"✅ PASS: '{query}' → Recall: {recall:.2f}")
                else:
                    self.stats["failed"] += 1
                    logger.error(f"❌ FAIL: '{query}' → Recall: {recall:.2f}")

            except Exception as e:
                logger.error(f"❌ ERROR: {query} → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

        self.test_results["recall_tests"].extend(results)
        return results

    def test_1_3_conceptual_recall(self):
        """Test Set 1.3: Conceptual/Semantic Matching Recall"""
        logger.info("\n=== Test Set 1.3: Conceptual Recall ===")

        # Test cases using conceptual/semantic matching
        test_cases = [
            {
                "query": "How do neural networks learn from data?",
                "expected_docs": {"ai_research", "ai_basics"},
                "min_recall": 0.3,  # Lower threshold for conceptual matching
            },
            {
                "query": "What are the components of an AI system?",
                "expected_docs": {"ai_basics", "ai_research"},
                "min_recall": 0.3,
            },
        ]

        results = []
        for test_case in test_cases:
            query = test_case["query"]
            expected_docs = test_case["expected_docs"]
            min_recall = test_case["min_recall"]

            try:
                result = self.rag_engine.query(query, top_k=5)
                retrieved_docs = set(
                    [
                        chunk.get("doc_id", "").split("_chunk")[0]
                        for chunk in result.get("retrieved_chunks", [])
                    ]
                )

                recall = self.calculate_recall(retrieved_docs, expected_docs)
                passed = recall >= min_recall

                test_result = {
                    "query": query,
                    "expected_docs": list(expected_docs),
                    "retrieved_docs": list(retrieved_docs),
                    "recall": recall,
                    "min_recall": min_recall,
                    "passed": passed,
                }
                results.append(test_result)

                self.stats["total_tests"] += 1
                if passed:
                    self.stats["passed"] += 1
                    logger.info(f"✅ PASS: '{query[:40]}...' → Recall: {recall:.2f}")
                else:
                    self.stats["failed"] += 1
                    logger.warning(
                        f"⚠️ PARTIAL: '{query[:40]}...' → Recall: {recall:.2f}"
                    )

            except Exception as e:
                logger.error(f"❌ ERROR: {query} → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

        self.test_results["recall_tests"].extend(results)
        return results

    # ==================== Test Category 2: Precision Tests ====================

    def test_2_1_relevant_results_density(self):
        """Test Set 2.1: Relevant Results Density"""
        logger.info("\n=== Test Set 2.1: Relevant Results Density ===")

        # Test that top-k results are mostly relevant
        test_cases = [
            {
                "query": "RAG system architecture",
                "expected_docs": {"rag_doc"},
                "top_k": 5,
                "min_precision": 0.6,  # At least 60% of top-5 should be relevant
            },
            {
                "query": "AI and machine learning concepts",
                "expected_docs": {"ai_basics", "ai_research"},
                "top_k": 5,
                "min_precision": 0.4,  # Broad query, lower threshold
            },
        ]

        results = []
        for test_case in test_cases:
            query = test_case["query"]
            expected_docs = test_case["expected_docs"]
            top_k = test_case["top_k"]
            min_precision = test_case["min_precision"]

            try:
                result = self.rag_engine.query(query, top_k=top_k)
                retrieved_chunks = result.get("retrieved_chunks", [])

                # Count relevant chunks
                relevant_count = 0
                for chunk in retrieved_chunks:
                    doc_id = chunk.get("doc_id", "").split("_chunk")[0]
                    if doc_id in expected_docs:
                        relevant_count += 1

                precision = relevant_count / top_k if top_k > 0 else 0
                passed = precision >= min_precision

                test_result = {
                    "query": query,
                    "expected_docs": list(expected_docs),
                    "top_k": top_k,
                    "relevant_count": relevant_count,
                    "precision": precision,
                    "min_precision": min_precision,
                    "passed": passed,
                }
                results.append(test_result)

                self.stats["total_tests"] += 1
                if passed:
                    self.stats["passed"] += 1
                    logger.info(
                        f"✅ PASS: '{query[:40]}...' → Precision: {precision:.2f} ({relevant_count}/{top_k})"
                    )
                else:
                    self.stats["failed"] += 1
                    logger.error(
                        f"❌ FAIL: '{query[:40]}...' → Precision: {precision:.2f} ({relevant_count}/{top_k})"
                    )

            except Exception as e:
                logger.error(f"❌ ERROR: {query} → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

        self.test_results["precision_tests"].extend(results)
        return results

    # ==================== Test Category 3: Query Complexity Tests ====================

    def test_3_1_query_complexity(self):
        """Test Set 3.1: Different Query Complexity Levels"""
        logger.info("\n=== Test Set 3.1: Query Complexity Tests ===")

        test_cases = [
            {"query": "RAG", "complexity": "simple", "top_k": 3},  # Simple keyword
            {
                "query": "How does RAG work?",  # Simple question
                "complexity": "moderate",
                "top_k": 5,
            },
            {
                "query": "Explain the differences between traditional information retrieval and RAG systems, including advantages and limitations",  # Complex query
                "complexity": "complex",
                "top_k": 5,
            },
        ]

        results = []
        for test_case in test_cases:
            query = test_case["query"]
            complexity = test_case["complexity"]
            top_k = test_case["top_k"]

            try:
                start_time = time.time()
                result = self.rag_engine.query(query, top_k=top_k)
                response_time = time.time() - start_time

                retrieved_count = len(result.get("retrieved_chunks", []))
                has_answer = len(result.get("answer", "")) > 0

                # Success criteria: retrieved results and generated answer
                passed = retrieved_count > 0 and has_answer

                test_result = {
                    "query": query,
                    "complexity": complexity,
                    "top_k": top_k,
                    "retrieved_count": retrieved_count,
                    "has_answer": has_answer,
                    "response_time": response_time,
                    "passed": passed,
                }
                results.append(test_result)

                self.stats["total_tests"] += 1
                if passed:
                    self.stats["passed"] += 1
                    logger.info(
                        f"✅ PASS: {complexity} query → {retrieved_count} chunks, {response_time*1000:.1f}ms"
                    )
                else:
                    self.stats["failed"] += 1
                    logger.error(
                        f"❌ FAIL: {complexity} query → {retrieved_count} chunks"
                    )

            except Exception as e:
                logger.error(f"❌ ERROR: {complexity} query → {e}")
                self.stats["total_tests"] += 1
                self.stats["errors"] += 1

        self.test_results["complexity_tests"].extend(results)
        return results

    def run_all_tests(self):
        """Execute all test categories"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 Starting Comprehensive Vector Retrieval Tests")
        logger.info("=" * 80)

        if not self.setup():
            logger.error("❌ Setup failed. Cannot proceed with tests.")
            return False

        # Load and add test documents
        logger.info("\n📚 Loading test documents...")
        documents = self.load_test_documents()
        if not documents:
            logger.error("❌ No test documents loaded. Cannot proceed.")
            return False

        if not self.add_test_documents(documents):
            logger.error("❌ Failed to add documents to RAG engine. Cannot proceed.")
            return False

        # Category 1: Recall Tests
        logger.info("\n" + "=" * 80)
        logger.info("📊 CATEGORY 1: Recall Rate Tests")
        logger.info("=" * 80)
        self.test_1_1_exact_match_recall()
        self.test_1_2_synonym_recall()
        self.test_1_3_conceptual_recall()

        # Category 2: Precision Tests
        logger.info("\n" + "=" * 80)
        logger.info("🎯 CATEGORY 2: Precision Tests")
        logger.info("=" * 80)
        self.test_2_1_relevant_results_density()

        # Category 3: Query Complexity
        logger.info("\n" + "=" * 80)
        logger.info("🧠 CATEGORY 3: Query Complexity Tests")
        logger.info("=" * 80)
        self.test_3_1_query_complexity()

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

        if pass_rate >= 80:
            logger.info(f"\n✅ EXCELLENT: Pass rate {pass_rate:.1f}% (≥80%)")
        elif pass_rate >= 70:
            logger.info(f"\n✅ GOOD: Pass rate {pass_rate:.1f}% (≥70%)")
        elif pass_rate >= 60:
            logger.info(f"\n⚠️ ACCEPTABLE: Pass rate {pass_rate:.1f}% (≥60%)")
        else:
            logger.info(f"\n❌ NEEDS IMPROVEMENT: Pass rate {pass_rate:.1f}% (<60%)")

        logger.info("\n" + "=" * 80)

    def save_results(
        self, output_file: str = "test_results/vector_retrieval_results.json"
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
    tester = VectorRetrievalTester()
    success = tester.run_all_tests()
    tester.save_results()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
