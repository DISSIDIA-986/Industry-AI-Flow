#!/usr/bin/env python3
"""
向量检索测试
测试RAG系统的向量检索能力，包括：
1. 召回率（Recall）评估
2. 精确率（Precision）评估
3. 不同数据集的检索性能
4. 查询多样性测试
5. 相似度阈值优化
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
    """文档数据结构"""

    doc_id: str
    title: str
    content: str
    category: str
    keywords: List[str]
    metadata: Dict[str, Any] = None


@dataclass
class Query:
    """查询数据结构"""

    query_id: str
    question: str
    expected_doc_ids: List[str]  # 期望检索到的文档ID
    query_type: str  # factual, conceptual, procedural
    difficulty: str  # easy, medium, hard


@dataclass
class RetrievalResult:
    """检索结果数据结构"""

    query_id: str
    retrieved_doc_ids: List[str]
    similarity_scores: List[float]
    retrieval_time: float


class VectorRetrievalTester:
    """向量检索测试器"""

    def __init__(self):
        self.documents = self._generate_test_documents()
        self.queries = self._generate_test_queries()
        self.test_results = []

    def _generate_test_documents(self) -> List[Document]:
        """生成测试文档集"""
        documents = [
            # 人工智能基础
            Document(
                doc_id="doc_001",
                title="人工智能基础概念",
                content="人工智能是计算机科学的一个分支，致力于创建能够模拟人类智能的系统。AI包括机器学习、深度学习、自然语言处理等多个子领域。",
                category="ai_basics",
                keywords=["人工智能", "AI", "机器学习", "深度学习", "NLP"],
            ),
            Document(
                doc_id="doc_002",
                title="机器学习算法概述",
                content="机器学习是AI的核心技术，主要分为监督学习、无监督学习和强化学习。常用算法包括线性回归、决策树、神经网络等。",
                category="machine_learning",
                keywords=["机器学习", "监督学习", "无监督学习", "强化学习", "算法"],
            ),
            Document(
                doc_id="doc_003",
                title="深度学习与神经网络",
                content="深度学习使用多层神经网络来学习数据的复杂模式。CNN适合图像处理，RNN适合序列数据，Transformer是目前最先进的架构。",
                category="deep_learning",
                keywords=["深度学习", "神经网络", "CNN", "RNN", "Transformer"],
            ),
            # 编程技术
            Document(
                doc_id="doc_004",
                title="Python编程语言特性",
                content="Python是一种高级编程语言，具有简洁的语法和强大的库支持。广泛应用于数据科学、Web开发、自动化脚本等领域。",
                category="programming",
                keywords=["Python", "编程语言", "数据科学", "Web开发", "自动化"],
            ),
            Document(
                doc_id="doc_005",
                title="数据结构与算法",
                content="常见的数据结构包括数组、链表、树、图等。算法复杂度分析包括时间复杂度和空间复杂度，是优化程序性能的基础。",
                category="algorithms",
                keywords=["数据结构", "算法", "复杂度", "性能优化", "数组", "链表"],
            ),
            # 系统架构
            Document(
                doc_id="doc_006",
                title="分布式系统设计原则",
                content="分布式系统需要考虑一致性、可用性、分区容错性。CAP定理指出在分布式系统中只能同时满足其中两个特性。",
                category="system_design",
                keywords=["分布式系统", "CAP定理", "一致性", "可用性", "分区容错"],
            ),
            Document(
                doc_id="doc_007",
                title="微服务架构模式",
                content="微服务架构将应用拆分为多个小型服务，每个服务独立部署和扩展。优点包括技术栈灵活性、独立部署、故障隔离等。",
                category="architecture",
                keywords=["微服务", "架构", "分布式", "容器化", "API网关"],
            ),
            # 数据科学
            Document(
                doc_id="doc_008",
                title="数据预处理技术",
                content="数据预处理包括数据清洗、缺失值处理、异常值检测、特征工程等步骤。高质量的数据是机器学习模型成功的关键。",
                category="data_science",
                keywords=["数据预处理", "数据清洗", "缺失值", "特征工程", "数据质量"],
            ),
            Document(
                doc_id="doc_009",
                title="统计分析方法",
                content="统计分析包括描述性统计和推断性统计。常用方法有回归分析、假设检验、方差分析等，帮助从数据中发现规律。",
                category="statistics",
                keywords=["统计分析", "回归分析", "假设检验", "方差分析", "数据挖掘"],
            ),
            # 软件工程
            Document(
                doc_id="doc_010",
                title="敏捷开发方法论",
                content="敏捷开发强调迭代开发、客户协作、响应变化。Scrum和Kanban是流行的敏捷框架，提高团队效率和产品质量。",
                category="software_engineering",
                keywords=["敏捷开发", "Scrum", "Kanban", "迭代开发", "团队协作"],
            ),
        ]

        return documents

    def _generate_test_queries(self) -> List[Query]:
        """生成测试查询集"""
        queries = [
            # 简单事实查询
            Query(
                query_id="query_001",
                question="什么是人工智能？",
                expected_doc_ids=["doc_001"],
                query_type="factual",
                difficulty="easy",
            ),
            Query(
                query_id="query_002",
                question="机器学习有哪些主要类型？",
                expected_doc_ids=["doc_002"],
                query_type="factual",
                difficulty="easy",
            ),
            # 概念性查询
            Query(
                query_id="query_003",
                question="深度学习和机器学习有什么区别？",
                expected_doc_ids=["doc_001", "doc_002", "doc_003"],
                query_type="conceptual",
                difficulty="medium",
            ),
            Query(
                query_id="query_004",
                question="分布式系统设计中需要考虑哪些因素？",
                expected_doc_ids=["doc_006", "doc_007"],
                query_type="conceptual",
                difficulty="hard",
            ),
            # 程序性查询
            Query(
                query_id="query_005",
                question="如何进行数据预处理？",
                expected_doc_ids=["doc_008"],
                query_type="procedural",
                difficulty="medium",
            ),
            Query(
                query_id="query_006",
                question="Python在数据科学中的应用有哪些？",
                expected_doc_ids=["doc_004", "doc_008"],
                query_type="procedural",
                difficulty="medium",
            ),
            # 复杂查询
            Query(
                query_id="query_007",
                question="在构建机器学习系统时，如何选择合适的算法和架构？",
                expected_doc_ids=["doc_002", "doc_003", "doc_005", "doc_006"],
                query_type="complex",
                difficulty="hard",
            ),
            Query(
                query_id="query_008",
                question="如何评估和改进软件系统的性能？",
                expected_doc_ids=["doc_005", "doc_006", "doc_007", "doc_010"],
                query_type="complex",
                difficulty="hard",
            ),
            # 跨领域查询
            Query(
                query_id="query_009",
                question="人工智能在软件开发中的应用",
                expected_doc_ids=["doc_001", "doc_004", "doc_010"],
                query_type="cross_domain",
                difficulty="medium",
            ),
            Query(
                query_id="query_010",
                question="数据科学项目的工作流程",
                expected_doc_ids=["doc_008", "doc_009", "doc_002"],
                query_type="cross_domain",
                difficulty="medium",
            ),
        ]

        return queries

    def _mock_vector_embedding(self, text: str) -> List[float]:
        """模拟向量嵌入（实际应用中使用真实的嵌入模型）"""
        # 简单的基于词汇的模拟嵌入
        words = text.lower().split()
        embedding = [0.0] * 128  # 128维向量

        # 为每个词分配不同的维度
        word_to_dim = {
            "人工智能": 0,
            "ai": 1,
            "机器学习": 2,
            "深度学习": 3,
            "python": 4,
            "算法": 5,
            "数据": 6,
            "系统": 7,
            "架构": 8,
            "开发": 9,
        }

        for word in words:
            for key, dim in word_to_dim.items():
                if key in word:
                    embedding[dim] += 0.1

        # 添加一些随机性
        for i in range(128):
            if embedding[i] == 0:
                embedding[i] = random.uniform(-0.05, 0.05)

        # 归一化
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def _calculate_cosine_similarity(
        self, vec1: List[float], vec2: List[float]
    ) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _mock_retrieval(self, query: str, top_k: int = 5) -> RetrievalResult:
        """模拟向量检索过程"""
        start_time = time.time()

        # 生成查询向量
        query_embedding = self._mock_vector_embedding(query)

        # 计算与所有文档的相似度
        similarities = []
        for doc in self.documents:
            doc_embedding = self._mock_vector_embedding(doc.title + " " + doc.content)
            similarity = self._calculate_cosine_similarity(
                query_embedding, doc_embedding
            )
            similarities.append((doc.doc_id, similarity))

        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        # 取top_k结果
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
        """计算检索指标"""
        total_precision = 0.0
        total_recall = 0.0
        total_f1 = 0.0
        total_map = 0.0  # Mean Average Precision

        for i, (result, query) in enumerate(zip(results, queries)):
            result.query_id = query.query_id

            # 计算Precision@K
            retrieved_set = set(result.retrieved_doc_ids)
            expected_set = set(query.expected_doc_ids)

            if len(result.retrieved_doc_ids) > 0:
                precision = len(retrieved_set & expected_set) / len(
                    result.retrieved_doc_ids
                )
            else:
                precision = 0.0

            # 计算Recall
            if len(expected_set) > 0:
                recall = len(retrieved_set & expected_set) / len(expected_set)
            else:
                recall = 1.0 if len(retrieved_set) == 0 else 0.0

            # 计算F1 Score
            if precision + recall > 0:
                f1 = 2 * precision * recall / (precision + recall)
            else:
                f1 = 0.0

            # 计算Average Precision
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
        """计算平均精度"""
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
        """测试检索性能"""
        print("🔍 测试向量检索性能...")

        results = []
        retrieval_times = []

        for query in self.queries:
            result = self._mock_retrieval(query.question, top_k=5)
            results.append(result)
            retrieval_times.append(result.retrieval_time)
            print(f"✅ {query.query_id}: 检索时间 {result.retrieval_time:.4f}s")

        # 计算指标
        metrics = self.calculate_metrics(results, self.queries)

        # 计算性能统计
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
        """测试不同数据集的检索性能"""
        print("\n🔍 测试不同数据集的检索性能...")

        # 按类别分组文档
        category_docs = defaultdict(list)
        for doc in self.documents:
            category_docs[doc.category].append(doc)

        category_results = {}

        for category, docs in category_docs.items():
            print(f"  📁 测试类别: {category}")

            # 创建该类别的专用查询
            category_queries = [
                q
                for q in self.queries
                if any(cat in [d.category for d in docs] for d in docs)
            ]

            if not category_queries:
                continue

            # 模拟检索
            results = []
            for query in category_queries:
                result = self._mock_retrieval(query.question, top_k=3)
                results.append(result)

            # 计算指标
            metrics = self.calculate_metrics(results, category_queries)

            category_results[category] = {
                "metrics": metrics,
                "doc_count": len(docs),
                "query_count": len(category_queries),
            }

            print(
                f"    ✅ 精确率: {metrics['precision']:.3f}, 召回率: {metrics['recall']:.3f}"
            )

        return category_results

    def test_query_diversity(self) -> Dict[str, Any]:
        """测试查询多样性"""
        print("\n🔍 测试查询多样性...")

        # 按查询类型分组
        type_queries = defaultdict(list)
        for query in self.queries:
            type_queries[query.query_type].append(query)

        type_results = {}

        for query_type, queries in type_queries.items():
            print(f"  📝 测试查询类型: {query_type}")

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
        """测试相似度阈值优化"""
        print("\n🔍 测试相似度阈值优化...")

        thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        threshold_results = {}

        for threshold in thresholds:
            print(f"  🎯 测试阈值: {threshold}")

            results = []
            for query in self.queries:
                result = self._mock_retrieval(query.question, top_k=10)

                # 应用阈值过滤
                filtered_docs = [
                    doc_id
                    for doc_id, score in zip(
                        result.retrieved_doc_ids, result.similarity_scores
                    )
                    if score >= threshold
                ]

                # 创建过滤后的结果
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
                f"    ✅ 精确率: {metrics['precision']:.3f}, 召回率: {metrics['recall']:.3f}"
            )

        # 找到最佳阈值（基于F1 Score）
        best_threshold = max(
            threshold_results.keys(), key=lambda t: threshold_results[t]["f1_score"]
        )

        return {
            "threshold_results": threshold_results,
            "best_threshold": best_threshold,
            "best_metrics": threshold_results[best_threshold],
        }

    def test_retrieval_robustness(self) -> Dict[str, Any]:
        """测试检索鲁棒性"""
        print("\n🔍 测试检索鲁棒性...")

        # 测试噪声查询
        noise_queries = [
            "什么是人工智能？？？",  # 多余标点
            "机器学习算法",  # 过短查询
            "如何在构建大规模分布式系统时考虑性能和可扩展性的平衡以及数据一致性问题",  # 过长查询
            "asdfghjkl",  # 无意义查询
            "",  # 空查询
        ]

        robustness_results = []

        for i, noise_query in enumerate(noise_queries):
            if noise_query.strip():  # 跳过空查询
                result = self._mock_retrieval(noise_query, top_k=5)
                robustness_results.append(
                    {
                        "query": noise_query,
                        "result_count": len(result.retrieved_doc_ids),
                        "retrieval_time": result.retrieval_time,
                    }
                )
                print(f"  ✅ 噪声查询 {i+1}: 检索到 {len(result.retrieved_doc_ids)} 个结果")

        return {
            "noise_test_results": robustness_results,
            "avg_results_per_query": sum(r["result_count"] for r in robustness_results)
            / len(robustness_results)
            if robustness_results
            else 0,
        }

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有检索测试"""
        print("🚀 开始向量检索全面测试\n")
        print("=" * 60)

        start_time = time.time()

        # 1. 基础检索性能测试
        basic_performance = self.test_retrieval_performance()

        # 2. 不同数据集测试
        dataset_performance = self.test_different_datasets()

        # 3. 查询多样性测试
        query_diversity = self.test_query_diversity()

        # 4. 相似度阈值优化测试
        threshold_optimization = self.test_similarity_thresholds()

        # 5. 鲁棒性测试
        robustness_test = self.test_retrieval_robustness()

        end_time = time.time()
        total_time = end_time - start_time

        # 汇总结果
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
        """计算总体评分"""
        # 基础性能权重 40%
        basic_score = (
            basic_perf["metrics"]["precision"]
            + basic_perf["metrics"]["recall"]
            + basic_perf["metrics"]["f1_score"]
        ) / 3

        # 数据集性能权重 30%
        dataset_scores = [d["metrics"]["f1_score"] for d in dataset_perf.values()]
        dataset_score = (
            sum(dataset_scores) / len(dataset_scores) if dataset_scores else 0
        )

        # 查询多样性权重 30%
        query_scores = [q["metrics"]["f1_score"] for q in query_div.values()]
        query_score = sum(query_scores) / len(query_scores) if query_scores else 0

        overall_score = basic_score * 0.4 + dataset_score * 0.3 + query_score * 0.3
        return overall_score

    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """生成测试报告"""
        report = f"""
# 向量检索测试报告

## 测试概要
- **执行时间**: {results['test_execution_time']:.2f} 秒
- **总体评分**: {results['overall_score']:.3f}/1.000

## 基础检索性能
- **精确率**: {results['basic_performance']['metrics']['precision']:.3f}
- **召回率**: {results['basic_performance']['metrics']['recall']:.3f}
- **F1 Score**: {results['basic_performance']['metrics']['f1_score']:.3f}
- **MAP**: {results['basic_performance']['metrics']['map']:.3f}
- **平均检索时间**: {results['basic_performance']['performance']['avg_retrieval_time']:.4f}s

## 数据集性能分析
"""

        for category, perf in results["dataset_performance"].items():
            report += f"- **{category}**: F1={perf['metrics']['f1_score']:.3f}, 文档数={perf['doc_count']}\n"

        report += "\n## 查询类型性能分析\n"

        for query_type, perf in results["query_diversity"].items():
            report += f"- **{query_type}**: F1={perf['metrics']['f1_score']:.3f}, MAP={perf['metrics']['map']:.3f}\n"

        report += f"""
## 相似度阈值优化
- **最佳阈值**: {results['threshold_optimization']['best_threshold']}
- **最佳F1 Score**: {results['threshold_optimization']['best_metrics']['f1_score']:.3f}

## 鲁棒性测试
- **噪声查询平均结果数**: {results['robustness_test']['avg_results_per_query']:.1f}

## 测试结论
"""

        if results["overall_score"] >= 0.8:
            report += "✅ **优秀**: 向量检索系统表现良好，各项指标均达到预期\n"
        elif results["overall_score"] >= 0.6:
            report += "⚠️ **良好**: 检索系统基本功能正常，但仍有优化空间\n"
        else:
            report += "❌ **需要改进**: 检索系统在多个方面存在不足\n"

        report += f"""
## 优化建议
1. **阈值调整**: 推荐使用相似度阈值 {results['threshold_optimization']['best_threshold']}
2. **数据集优化**: 针对表现较差的类别进行专门的向量优化
3. **查询处理**: 改进复杂查询的向量化策略
4. **性能优化**: 当前平均检索时间 {results['basic_performance']['performance']['avg_retrieval_time']:.4f}s，可进一步优化

## 下一步行动
- 实施最佳相似度阈值
- 优化低性能类别的向量化策略
- 增强复杂查询处理能力
- 扩大测试数据集规模
"""

        return report


def main():
    """主函数"""
    tester = VectorRetrievalTester()

    # 运行所有测试
    results = tester.run_all_tests()

    # 生成报告
    report = tester.generate_test_report(results)

    # 保存结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # 保存JSON结果
    with open(
        f"test_results/vector_retrieval_results_{timestamp}.json", "w", encoding="utf-8"
    ) as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 保存报告
    with open(
        f"test_results/vector_retrieval_report_{timestamp}.md", "w", encoding="utf-8"
    ) as f:
        f.write(report)

    # 输出摘要
    print("\n" + "=" * 60)
    print("🎯 向量检索测试完成！")
    print("=" * 60)
    print(f"📊 总体评分: {results['overall_score']:.3f}/1.000")
    print(f"🎯 基础F1 Score: {results['basic_performance']['metrics']['f1_score']:.3f}")
    print(f"📈 MAP: {results['basic_performance']['metrics']['map']:.3f}")
    print(
        f"⏱️  平均检索时间: {results['basic_performance']['performance']['avg_retrieval_time']:.4f}s"
    )
    print(f"🎚️  最佳阈值: {results['threshold_optimization']['best_threshold']}")
    print(f"\n📄 详细报告已保存到: test_results/vector_retrieval_report_{timestamp}.md")

    return results["overall_score"] >= 0.6


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
