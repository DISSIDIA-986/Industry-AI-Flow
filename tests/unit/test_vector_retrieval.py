#!/usr/bin/env python3
"""
EN
ENRAGEN,EN:
1. EN(Recall)EN
2. EN(Precision)EN
3. EN
4. EN
5. EN
"""
import json
import math
import os
import random
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple


@dataclass
class Document:
    """EN"""

    doc_id: str
    title: str
    content: str
    category: str
    keywords: List[str]
    metadata: Dict[str, Any] = None


@dataclass
class Query:
    """EN"""

    query_id: str
    question: str
    expected_doc_ids: List[str]  # ENID
    query_type: str  # factual, conceptual, procedural
    difficulty: str  # easy, medium, hard


@dataclass
class RetrievalResult:
    """EN"""

    query_id: str
    retrieved_doc_ids: List[str]
    similarity_scores: List[float]
    retrieval_time: float


class VectorRetrievalTester:
    """EN"""

    def __init__(self):
        self.documents = self._generate_test_documents()
        self.queries = self._generate_test_queries()
        self.test_results = []

    def _generate_test_documents(self) -> List[Document]:
        """EN"""
        documents = [
            # EN
            Document(
                doc_id="doc_001",
                title="EN",
                content="EN,EN.AIEN,EN,EN.",
                category="ai_basics",
                keywords=["EN", "AI", "EN", "EN", "NLP"],
            ),
            Document(
                doc_id="doc_002",
                title="EN",
                content="ENAIEN,EN,EN.EN,EN,EN.",
                category="machine_learning",
                keywords=["EN", "EN", "EN", "EN", "EN"],
            ),
            Document(
                doc_id="doc_003",
                title="EN",
                content="EN.CNNEN,RNNEN,TransformerEN.",
                category="deep_learning",
                keywords=["EN", "EN", "CNN", "RNN", "Transformer"],
            ),
            # EN
            Document(
                doc_id="doc_004",
                title="PythonEN",
                content="PythonEN,EN.EN,WebEN,EN.",
                category="programming",
                keywords=["Python", "EN", "EN", "WebEN", "EN"],
            ),
            Document(
                doc_id="doc_005",
                title="EN",
                content="EN,EN,EN,EN.EN,EN.",
                category="algorithms",
                keywords=["EN", "EN", "EN", "EN", "EN", "EN"],
            ),
            # EN
            Document(
                doc_id="doc_006",
                title="EN",
                content="EN,EN,EN.CAPEN.",
                category="system_design",
                keywords=["EN", "CAPEN", "EN", "EN", "EN"],
            ),
            Document(
                doc_id="doc_007",
                title="EN",
                content="EN,EN.EN,EN,EN.",
                category="architecture",
                keywords=["EN", "EN", "EN", "EN", "APIEN"],
            ),
            # EN
            Document(
                doc_id="doc_008",
                title="EN",
                content="EN,EN,EN,EN.EN.",
                category="data_science",
                keywords=["EN", "EN", "EN", "EN", "EN"],
            ),
            Document(
                doc_id="doc_009",
                title="EN",
                content="EN.EN,EN,EN,EN.",
                category="statistics",
                keywords=["EN", "EN", "EN", "EN", "EN"],
            ),
            # EN
            Document(
                doc_id="doc_010",
                title="EN",
                content="EN,EN,EN.ScrumENKanbanEN,EN.",
                category="software_engineering",
                keywords=["EN", "Scrum", "Kanban", "EN", "EN"],
            ),
        ]

        return documents

    def _generate_test_queries(self) -> List[Query]:
        """EN"""
        queries = [
            # EN
            Query(
                query_id="query_001",
                question="EN?",
                expected_doc_ids=["doc_001"],
                query_type="factual",
                difficulty="easy",
            ),
            Query(
                query_id="query_002",
                question="EN?",
                expected_doc_ids=["doc_002"],
                query_type="factual",
                difficulty="easy",
            ),
            # EN
            Query(
                query_id="query_003",
                question="EN?",
                expected_doc_ids=["doc_001", "doc_002", "doc_003"],
                query_type="conceptual",
                difficulty="medium",
            ),
            Query(
                query_id="query_004",
                question="EN?",
                expected_doc_ids=["doc_006", "doc_007"],
                query_type="conceptual",
                difficulty="hard",
            ),
            # EN
            Query(
                query_id="query_005",
                question="EN?",
                expected_doc_ids=["doc_008"],
                query_type="procedural",
                difficulty="medium",
            ),
            Query(
                query_id="query_006",
                question="PythonEN?",
                expected_doc_ids=["doc_004", "doc_008"],
                query_type="procedural",
                difficulty="medium",
            ),
            # EN
            Query(
                query_id="query_007",
                question="EN,EN?",
                expected_doc_ids=["doc_002", "doc_003", "doc_005", "doc_006"],
                query_type="complex",
                difficulty="hard",
            ),
            Query(
                query_id="query_008",
                question="EN?",
                expected_doc_ids=["doc_005", "doc_006", "doc_007", "doc_010"],
                query_type="complex",
                difficulty="hard",
            ),
            # EN
            Query(
                query_id="query_009",
                question="EN",
                expected_doc_ids=["doc_001", "doc_004", "doc_010"],
                query_type="cross_domain",
                difficulty="medium",
            ),
            Query(
                query_id="query_010",
                question="EN",
                expected_doc_ids=["doc_008", "doc_009", "doc_002"],
                query_type="cross_domain",
                difficulty="medium",
            ),
        ]

        return queries

    def _mock_vector_embedding(self, text: str) -> List[float]:
        """EN(EN)"""
        # EN
        words = text.lower().split()
        embedding = [0.0] * 128  # 128EN

        # EN
        word_to_dim = {
            "EN": 0,
            "ai": 1,
            "EN": 2,
            "EN": 3,
            "python": 4,
            "EN": 5,
            "EN": 6,
            "EN": 7,
            "EN": 8,
            "EN": 9,
        }

        for word in words:
            for key, dim in word_to_dim.items():
                if key in word:
                    embedding[dim] += 0.1

        # EN
        for i in range(128):
            if embedding[i] == 0:
                embedding[i] = random.uniform(-0.05, 0.05)

        # EN
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def _calculate_cosine_similarity(
        self, vec1: List[float], vec2: List[float]
    ) -> float:
        """EN"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _mock_retrieval(self, query: str, top_k: int = 5) -> RetrievalResult:
        """EN"""
        start_time = time.time()

        # EN
        query_embedding = self._mock_vector_embedding(query)

        # EN
        similarities = []
        for doc in self.documents:
            doc_embedding = self._mock_vector_embedding(doc.title + " " + doc.content)
            similarity = self._calculate_cosine_similarity(
                query_embedding, doc_embedding
            )
            similarities.append((doc.doc_id, similarity))

        # EN
        similarities.sort(key=lambda x: x[1], reverse=True)

        # ENtop_kEN
        retrieved_docs = similarities[:top_k]
        doc_ids = [doc_id for doc_id, _ in retrieved_docs]
        scores = [score for _, score in retrieved_docs]

        retrieval_time = time.time() - start_time

        return RetrievalResult(
            query_id="",
            retrieved_doc_ids=doc_ids,
            similarity_scores=scores,
            retrieval_time=retrieval_time,
        )

    def calculate_metrics(
        self, results: List[RetrievalResult], queries: List[Query]
    ) -> Dict[str, float]:
        """EN"""
        total_precision = 0.0
        total_recall = 0.0
        total_f1 = 0.0
        total_map = 0.0  # Mean Average Precision

        for i, (result, query) in enumerate(zip(results, queries)):
            result.query_id = query.query_id

            # ENPrecision@K
            retrieved_set = set(result.retrieved_doc_ids)
            expected_set = set(query.expected_doc_ids)

            if len(result.retrieved_doc_ids) > 0:
                precision = len(retrieved_set & expected_set) / len(
                    result.retrieved_doc_ids
                )
            else:
                precision = 0.0

            # ENRecall
            if len(expected_set) > 0:
                recall = len(retrieved_set & expected_set) / len(expected_set)
            else:
                recall = 1.0 if len(retrieved_set) == 0 else 0.0

            # ENF1 Score
            if precision + recall > 0:
                f1 = 2 * precision * recall / (precision + recall)
            else:
                f1 = 0.0

            # ENAverage Precision
            ap = self._calculate_average_precision(
                result.retrieved_doc_ids, query.expected_doc_ids
            )

            total_precision += precision
            total_recall += recall
            total_f1 += f1
            total_map += ap

        num_queries = len(queries)
        return {
            "precision": total_precision / num_queries,
            "recall": total_recall / num_queries,
            "f1_score": total_f1 / num_queries,
            "map": total_map / num_queries,
        }

    def _calculate_average_precision(
        self, retrieved_docs: List[str], expected_docs: List[str]
    ) -> float:
        """EN"""
        expected_set = set(expected_docs)
        if not expected_set:
            return 1.0

        precisions = []
        correct_count = 0

        for i, doc_id in enumerate(retrieved_docs):
            if doc_id in expected_set:
                correct_count += 1
                precision = correct_count / (i + 1)
                precisions.append(precision)

        return sum(precisions) / len(expected_set) if precisions else 0.0

    def test_retrieval_performance(self) -> Dict[str, Any]:
        """EN"""
        print("🔍 EN...")

        results = []
        retrieval_times = []

        for query in self.queries:
            result = self._mock_retrieval(query.question, top_k=5)
            results.append(result)
            retrieval_times.append(result.retrieval_time)
            print(f"✅ {query.query_id}: EN {result.retrieval_time:.4f}s")

        # EN
        metrics = self.calculate_metrics(results, self.queries)

        # EN
        avg_retrieval_time = sum(retrieval_times) / len(retrieval_times)
        max_retrieval_time = max(retrieval_times)
        min_retrieval_time = min(retrieval_times)

        return {
            "metrics": metrics,
            "performance": {
                "avg_retrieval_time": avg_retrieval_time,
                "max_retrieval_time": max_retrieval_time,
                "min_retrieval_time": min_retrieval_time,
                "total_queries": len(self.queries),
            },
            "detailed_results": results,
        }

    def test_different_datasets(self) -> Dict[str, Any]:
        """EN"""
        print("\n🔍 EN...")

        # EN
        category_docs = defaultdict(list)
        for doc in self.documents:
            category_docs[doc.category].append(doc)

        category_results = {}

        for category, docs in category_docs.items():
            print(f"  📁 EN: {category}")

            # EN
            category_queries = [
                q
                for q in self.queries
                if any(cat in [d.category for d in docs] for d in docs)
            ]

            if not category_queries:
                continue

            # EN
            results = []
            for query in category_queries:
                result = self._mock_retrieval(query.question, top_k=3)
                results.append(result)

            # EN
            metrics = self.calculate_metrics(results, category_queries)

            category_results[category] = {
                "metrics": metrics,
                "doc_count": len(docs),
                "query_count": len(category_queries),
            }

            print(
                f"    ✅ EN: {metrics['precision']:.3f}, EN: {metrics['recall']:.3f}"
            )

        return category_results

    def test_query_diversity(self) -> Dict[str, Any]:
        """EN"""
        print("\n🔍 EN...")

        # EN
        type_queries = defaultdict(list)
        for query in self.queries:
            type_queries[query.query_type].append(query)

        type_results = {}

        for query_type, queries in type_queries.items():
            print(f"  📝 EN: {query_type}")

            results = []
            for query in queries:
                result = self._mock_retrieval(query.question, top_k=5)
                results.append(result)

            metrics = self.calculate_metrics(results, queries)

            type_results[query_type] = {"metrics": metrics, "query_count": len(queries)}

            print(
                f"    ✅ F1 Score: {metrics['f1_score']:.3f}, MAP: {metrics['map']:.3f}"
            )

        return type_results

    def test_similarity_thresholds(self) -> Dict[str, Any]:
        """EN"""
        print("\n🔍 EN...")

        thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        threshold_results = {}

        for threshold in thresholds:
            print(f"  🎯 EN: {threshold}")

            results = []
            for query in self.queries:
                result = self._mock_retrieval(query.question, top_k=10)

                # EN
                filtered_docs = [
                    doc_id
                    for doc_id, score in zip(
                        result.retrieved_doc_ids, result.similarity_scores
                    )
                    if score >= threshold
                ]

                # EN
                filtered_result = RetrievalResult(
                    query_id=query.query_id,
                    retrieved_doc_ids=filtered_docs,
                    similarity_scores=[],
                    retrieval_time=result.retrieval_time,
                )
                results.append(filtered_result)

            metrics = self.calculate_metrics(results, self.queries)

            threshold_results[threshold] = metrics

            print(
                f"    ✅ EN: {metrics['precision']:.3f}, EN: {metrics['recall']:.3f}"
            )

        # EN(ENF1 Score)
        best_threshold = max(
            threshold_results.keys(), key=lambda t: threshold_results[t]["f1_score"]
        )

        return {
            "threshold_results": threshold_results,
            "best_threshold": best_threshold,
            "best_metrics": threshold_results[best_threshold],
        }

    def test_retrieval_robustness(self) -> Dict[str, Any]:
        """EN"""
        print("\n🔍 EN...")

        # EN
        noise_queries = [
            "EN???",  # EN
            "EN",  # EN
            "EN",  # EN
            "asdfghjkl",  # EN
            "",  # EN
        ]

        robustness_results = []

        for i, noise_query in enumerate(noise_queries):
            if noise_query.strip():  # EN
                result = self._mock_retrieval(noise_query, top_k=5)
                robustness_results.append(
                    {
                        "query": noise_query,
                        "result_count": len(result.retrieved_doc_ids),
                        "retrieval_time": result.retrieval_time,
                    }
                )
                print(f"  ✅ EN {i+1}: EN {len(result.retrieved_doc_ids)} EN")

        return {
            "noise_test_results": robustness_results,
            "avg_results_per_query": sum(r["result_count"] for r in robustness_results)
            / len(robustness_results)
            if robustness_results
            else 0,
        }

    def run_all_tests(self) -> Dict[str, Any]:
        """EN"""
        print("🚀 EN\n")
        print("=" * 60)

        start_time = time.time()

        # 1. EN
        basic_performance = self.test_retrieval_performance()

        # 2. EN
        dataset_performance = self.test_different_datasets()

        # 3. EN
        query_diversity = self.test_query_diversity()

        # 4. EN
        threshold_optimization = self.test_similarity_thresholds()

        # 5. EN
        robustness_test = self.test_retrieval_robustness()

        end_time = time.time()
        total_time = end_time - start_time

        # EN
        summary = {
            "test_execution_time": total_time,
            "basic_performance": basic_performance,
            "dataset_performance": dataset_performance,
            "query_diversity": query_diversity,
            "threshold_optimization": threshold_optimization,
            "robustness_test": robustness_test,
            "overall_score": self._calculate_overall_score(
                basic_performance, dataset_performance, query_diversity
            ),
        }

        return summary

    def _calculate_overall_score(
        self, basic_perf: Dict, dataset_perf: Dict, query_div: Dict
    ) -> float:
        """EN"""
        # EN 40%
        basic_score = (
            basic_perf["metrics"]["precision"]
            + basic_perf["metrics"]["recall"]
            + basic_perf["metrics"]["f1_score"]
        ) / 3

        # EN 30%
        dataset_scores = [d["metrics"]["f1_score"] for d in dataset_perf.values()]
        dataset_score = (
            sum(dataset_scores) / len(dataset_scores) if dataset_scores else 0
        )

        # EN 30%
        query_scores = [q["metrics"]["f1_score"] for q in query_div.values()]
        query_score = sum(query_scores) / len(query_scores) if query_scores else 0

        overall_score = basic_score * 0.4 + dataset_score * 0.3 + query_score * 0.3
        return overall_score

    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """EN"""
        report = f"""
# EN

## EN
- **EN**: {results['test_execution_time']:.2f} EN
- **EN**: {results['overall_score']:.3f}/1.000

## EN
- **EN**: {results['basic_performance']['metrics']['precision']:.3f}
- **EN**: {results['basic_performance']['metrics']['recall']:.3f}
- **F1 Score**: {results['basic_performance']['metrics']['f1_score']:.3f}
- **MAP**: {results['basic_performance']['metrics']['map']:.3f}
- **EN**: {results['basic_performance']['performance']['avg_retrieval_time']:.4f}s

## EN
"""

        for category, perf in results["dataset_performance"].items():
            report += f"- **{category}**: F1={perf['metrics']['f1_score']:.3f}, EN={perf['doc_count']}\n"

        report += "\n## EN\n"

        for query_type, perf in results["query_diversity"].items():
            report += f"- **{query_type}**: F1={perf['metrics']['f1_score']:.3f}, MAP={perf['metrics']['map']:.3f}\n"

        report += f"""
## EN
- **EN**: {results['threshold_optimization']['best_threshold']}
- **ENF1 Score**: {results['threshold_optimization']['best_metrics']['f1_score']:.3f}

## EN
- **EN**: {results['robustness_test']['avg_results_per_query']:.1f}

## EN
"""

        if results["overall_score"] >= 0.8:
            report += "✅ **EN**: EN,EN\n"
        elif results["overall_score"] >= 0.6:
            report += "⚠️ **EN**: EN,EN\n"
        else:
            report += "❌ **EN**: EN\n"

        report += f"""
## EN
1. **EN**: EN {results['threshold_optimization']['best_threshold']}
2. **EN**: EN
3. **EN**: EN
4. **EN**: EN {results['basic_performance']['performance']['avg_retrieval_time']:.4f}s,EN

## EN
- EN
- EN
- EN
- EN
"""

        return report


def main():
    """EN"""
    tester = VectorRetrievalTester()

    # EN
    results = tester.run_all_tests()

    # EN
    report = tester.generate_test_report(results)

    # EN
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # ENJSONEN
    with open(
        f"test_results/vector_retrieval_results_{timestamp}.json", "w", encoding="utf-8"
    ) as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # EN
    with open(
        f"test_results/vector_retrieval_report_{timestamp}.md", "w", encoding="utf-8"
    ) as f:
        f.write(report)

    # EN
    print("\n" + "=" * 60)
    print("🎯 EN!")
    print("=" * 60)
    print(f"📊 EN: {results['overall_score']:.3f}/1.000")
    print(f"🎯 ENF1 Score: {results['basic_performance']['metrics']['f1_score']:.3f}")
    print(f"📈 MAP: {results['basic_performance']['metrics']['map']:.3f}")
    print(
        f"⏱️  EN: {results['basic_performance']['performance']['avg_retrieval_time']:.4f}s"
    )
    print(f"🎚️  EN: {results['threshold_optimization']['best_threshold']}")
    print(f"\n📄 EN: test_results/vector_retrieval_report_{timestamp}.md")

    return results["overall_score"] >= 0.6


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
