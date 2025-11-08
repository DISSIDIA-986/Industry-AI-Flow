"""
改进系统集成测试
测试三个关键修复:
1. 意图分类器 - 从0%提升到70-80%准确率
2. 数据分析Agent - 支持CSV/Excel统计分析
3. 智能文档路由 - 结构化数据使用CodeExecutor而非RAG
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import json
import time
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

# 导入新组件
from backend.services.simple_intent_classifier import simple_intent_classifier, IntentType
from backend.services.data_analysis_agent import data_analysis_agent
from backend.services.smart_document_router import smart_document_router


class ImprovedSystemTester:
    """改进系统测试器"""

    def __init__(self):
        self.test_results = []
        self.intent_classifier = simple_intent_classifier
        self.data_agent = data_analysis_agent
        self.doc_router = smart_document_router

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 80)
        print("Industry AI Flow - 改进系统集成测试")
        print("=" * 80)
        print()

        # 测试1: 意图分类器
        print("\n[测试 1/3] 意图分类器准确性测试")
        print("-" * 80)
        intent_results = self.test_intent_classifier()

        # 测试2: 文档路由器
        print("\n[测试 2/3] 智能文档路由测试")
        print("-" * 80)
        routing_results = self.test_document_router()

        # 测试3: 数据分析Agent
        print("\n[测试 3/3] 数据分析Agent测试")
        print("-" * 80)
        analysis_results = self.test_data_analysis_agent()

        # 生成报告
        print("\n" + "=" * 80)
        print("测试汇总报告")
        print("=" * 80)
        self.generate_report(intent_results, routing_results, analysis_results)

    def test_intent_classifier(self) -> Dict[str, Any]:
        """测试意图分类器"""
        test_cases = [
            # 知识检索类
            {
                "query": "What is a RAG system?",
                "expected": IntentType.KNOWLEDGE_RETRIEVAL,
                "difficulty": "simple"
            },
            {
                "query": "解释什么是向量数据库",
                "expected": IntentType.KNOWLEDGE_RETRIEVAL,
                "difficulty": "simple"
            },
            {
                "query": "How does BM25 algorithm work?",
                "expected": IntentType.KNOWLEDGE_RETRIEVAL,
                "difficulty": "medium"
            },

            # 数据分析类
            {
                "query": "What is the average price in the housing dataset?",
                "expected": IntentType.DATA_ANALYSIS,
                "difficulty": "medium"
            },
            {
                "query": "分析失业率的趋势",
                "expected": IntentType.DATA_ANALYSIS,
                "difficulty": "medium"
            },
            {
                "query": "Compare the statistics between two datasets",
                "expected": IntentType.DATA_ANALYSIS,
                "difficulty": "hard"
            },
            {
                "query": "Calculate the correlation between area and price",
                "expected": IntentType.DATA_ANALYSIS,
                "difficulty": "hard"
            },
            {
                "query": "哪个省份的失业率最高?",
                "expected": IntentType.DATA_ANALYSIS,
                "difficulty": "medium"
            },

            # 文档处理类
            {
                "query": "Extract text from this PDF document",
                "expected": IntentType.DOCUMENT_PROCESSING,
                "difficulty": "simple"
            },
            {
                "query": "对这张图片进行OCR识别",
                "expected": IntentType.DOCUMENT_PROCESSING,
                "difficulty": "simple"
            },

            # 代码执行类
            {
                "query": "Run this Python script",
                "expected": IntentType.CODE_EXECUTION,
                "difficulty": "simple"
            },
            {
                "query": "执行数据处理代码",
                "expected": IntentType.CODE_EXECUTION,
                "difficulty": "simple"
            }
        ]

        results = {
            "total": len(test_cases),
            "correct": 0,
            "by_type": {},
            "by_difficulty": {},
            "details": []
        }

        print(f"运行 {len(test_cases)} 个意图分类测试...\n")

        for i, test_case in enumerate(test_cases, 1):
            query = test_case["query"]
            expected = test_case["expected"]
            difficulty = test_case["difficulty"]

            # 执行分类
            start_time = time.time()
            result = self.intent_classifier.classify_intent(query)
            execution_time = (time.time() - start_time) * 1000  # ms

            # 判断是否正确
            is_correct = result.intent == expected

            # 更新统计
            if is_correct:
                results["correct"] += 1

            # 按类型统计
            expected_value = expected.value
            if expected_value not in results["by_type"]:
                results["by_type"][expected_value] = {"total": 0, "correct": 0}
            results["by_type"][expected_value]["total"] += 1
            if is_correct:
                results["by_type"][expected_value]["correct"] += 1

            # 按难度统计
            if difficulty not in results["by_difficulty"]:
                results["by_difficulty"][difficulty] = {"total": 0, "correct": 0}
            results["by_difficulty"][difficulty]["total"] += 1
            if is_correct:
                results["by_difficulty"][difficulty]["correct"] += 1

            # 记录详情
            detail = {
                "query": query,
                "expected": expected_value,
                "predicted": result.intent.value,
                "confidence": result.confidence,
                "correct": is_correct,
                "difficulty": difficulty,
                "execution_time_ms": round(execution_time, 2)
            }
            results["details"].append(detail)

            # 打印结果
            status = "✅" if is_correct else "❌"
            print(f"{status} [{i}/{len(test_cases)}] {query[:50]}...")
            print(f"   预期: {expected_value} | 实际: {result.intent.value} | "
                  f"置信度: {result.confidence:.2f} | {execution_time:.0f}ms")

            if not is_correct:
                print(f"   ⚠️  分类错误! 原因: {result.reasoning}")

            print()

        # 计算准确率
        results["accuracy"] = results["correct"] / results["total"]

        print("\n" + "-" * 80)
        print(f"总体准确率: {results['accuracy']*100:.1f}% ({results['correct']}/{results['total']})")
        print("\n按意图类型:")
        for intent_type, stats in results["by_type"].items():
            acc = stats["correct"] / stats["total"]
            print(f"  {intent_type}: {acc*100:.1f}% ({stats['correct']}/{stats['total']})")

        print("\n按难度:")
        for diff, stats in results["by_difficulty"].items():
            acc = stats["correct"] / stats["total"]
            print(f"  {diff}: {acc*100:.1f}% ({stats['correct']}/{stats['total']})")

        return results

    def test_document_router(self) -> Dict[str, Any]:
        """测试文档路由器"""
        test_files = [
            {"path": "datasets/Housing.csv", "expected_strategy": "data_analysis"},
            {"path": "datasets/Thyroid_Diff.csv", "expected_strategy": "data_analysis"},
            {"path": "datasets/Unemployment_Canada.csv", "expected_strategy": "data_analysis"},
            {"path": "samples/test_document_1.txt", "expected_strategy": "rag_retrieval"},
            {"path": "samples/test_document_2.txt", "expected_strategy": "rag_retrieval"},
        ]

        results = {
            "total": 0,
            "correct": 0,
            "details": []
        }

        print(f"测试 {len(test_files)} 个文档路由决策...\n")

        for test_file in test_files:
            file_path = test_file["path"]
            expected = test_file["expected_strategy"]

            # 检查文件是否存在
            full_path = Path(file_path)
            if not full_path.exists():
                print(f"⚠️  文件不存在，跳过: {file_path}")
                continue

            results["total"] += 1

            # 执行路由
            routing = self.doc_router.route_document(full_path)

            # 判断是否正确
            is_correct = routing["processing_strategy"] == expected

            if is_correct:
                results["correct"] += 1

            # 记录详情
            detail = {
                "file": file_path,
                "expected": expected,
                "predicted": routing["processing_strategy"],
                "correct": is_correct,
                "document_type": routing["document_type"],
                "agent": routing["recommended_agent"]
            }
            results["details"].append(detail)

            # 打印结果
            status = "✅" if is_correct else "❌"
            print(f"{status} {full_path.name}")
            print(f"   类型: {routing['document_type']} → 策略: {routing['processing_strategy']}")
            print(f"   Agent: {routing['recommended_agent']}")
            print(f"   原因: {routing['rationale'][:80]}...")
            print()

        # 计算准确率
        if results["total"] > 0:
            results["accuracy"] = results["correct"] / results["total"]
        else:
            results["accuracy"] = 0.0

        print("-" * 80)
        print(f"路由准确率: {results['accuracy']*100:.1f}% ({results['correct']}/{results['total']})")

        return results

    def test_data_analysis_agent(self) -> Dict[str, Any]:
        """测试数据分析Agent"""
        # 测试数据集
        test_dataset = "datasets/Housing.csv"

        if not os.path.exists(test_dataset):
            print(f"⚠️  测试数据集不存在: {test_dataset}")
            print("请先运行 import_csv_datasets.py 导入数据集")
            return {"skipped": True}

        test_queries = [
            {
                "question": "How many records are in the dataset?",
                "expected_keywords": ["record", "row", "545"],
                "difficulty": "simple"
            },
            {
                "question": "What is the average price?",
                "expected_keywords": ["average", "price", "mean"],
                "difficulty": "medium"
            },
            {
                "question": "What percentage of houses have air conditioning?",
                "expected_keywords": ["percentage", "air", "%"],
                "difficulty": "medium"
            }
        ]

        results = {
            "total": len(test_queries),
            "successful": 0,
            "failed": 0,
            "details": []
        }

        print(f"运行 {len(test_queries)} 个数据分析查询...\n")

        for i, test_query in enumerate(test_queries, 1):
            question = test_query["question"]
            expected_keywords = test_query["expected_keywords"]
            difficulty = test_query["difficulty"]

            print(f"[{i}/{len(test_queries)}] {question}")

            # 执行分析
            start_time = time.time()
            try:
                result = self.data_agent.analyze_query(
                    question=question,
                    data_file_path=test_dataset
                )
                execution_time = (time.time() - start_time) * 1000  # ms

                success = result.get("success", False)

                # 检查答案是否包含期望关键词
                answer = result.get("answer", "").lower()
                keyword_matches = sum(1 for kw in expected_keywords if kw.lower() in answer)
                match_rate = keyword_matches / len(expected_keywords) if expected_keywords else 0

                if success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1

                # 记录详情
                detail = {
                    "question": question,
                    "success": success,
                    "answer": result.get("answer", "N/A"),
                    "keyword_match_rate": match_rate,
                    "execution_time_ms": round(execution_time, 2),
                    "difficulty": difficulty
                }

                if "code" in result:
                    detail["code_generated"] = True

                results["details"].append(detail)

                # 打印结果
                status = "✅" if success else "❌"
                print(f"{status} 执行状态: {'成功' if success else '失败'}")
                print(f"   答案: {result.get('answer', 'N/A')[:100]}...")
                print(f"   关键词匹配: {match_rate*100:.0f}% | 耗时: {execution_time:.0f}ms")

                if not success:
                    print(f"   错误: {result.get('error', 'Unknown error')}")

            except Exception as e:
                results["failed"] += 1
                print(f"❌ 执行异常: {e}")
                results["details"].append({
                    "question": question,
                    "success": False,
                    "error": str(e),
                    "difficulty": difficulty
                })

            print()

        # 计算成功率
        results["success_rate"] = results["successful"] / results["total"] if results["total"] > 0 else 0

        print("-" * 80)
        print(f"成功率: {results['success_rate']*100:.1f}% ({results['successful']}/{results['total']})")

        return results

    def generate_report(
        self,
        intent_results: Dict,
        routing_results: Dict,
        analysis_results: Dict
    ):
        """生成测试报告"""
        print("\n📊 关键指标:")
        print(f"  • 意图分类准确率: {intent_results['accuracy']*100:.1f}% "
              f"(目标: 70-80%, {'✅达标' if intent_results['accuracy'] >= 0.7 else '❌未达标'})")

        if "accuracy" in routing_results:
            print(f"  • 文档路由准确率: {routing_results['accuracy']*100:.1f}% "
                  f"({'✅完美' if routing_results['accuracy'] == 1.0 else '⚠️有误'})")

        if not analysis_results.get("skipped"):
            print(f"  • 数据分析成功率: {analysis_results.get('success_rate', 0)*100:.1f}%")

        # 核心改进验证
        print("\n🎯 核心改进验证:")

        # 1. 意图分类器修复
        if intent_results['accuracy'] >= 0.7:
            print("  ✅ 意图分类器已修复: 从0%提升至{:.1f}%".format(intent_results['accuracy']*100))
        else:
            print("  ⚠️  意图分类器需要进一步优化: 当前{:.1f}%".format(intent_results['accuracy']*100))

        # 2. 结构化数据路由
        csv_routing_correct = all(
            d["correct"] for d in routing_results.get("details", [])
            if ".csv" in d["file"]
        )
        if csv_routing_correct:
            print("  ✅ 结构化数据路由正确: CSV文件使用数据分析Agent")
        else:
            print("  ❌ 结构化数据路由有误")

        # 3. 数据分析能力
        if not analysis_results.get("skipped"):
            if analysis_results.get("success_rate", 0) > 0:
                print("  ✅ 数据分析Agent功能正常")
            else:
                print("  ❌ 数据分析Agent需要检查CodeExecutor配置")

        # 保存详细报告
        report_file = "test_results/improved_system_test_report.json"
        os.makedirs("test_results", exist_ok=True)

        full_report = {
            "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "intent_classification": intent_results,
            "document_routing": routing_results,
            "data_analysis": analysis_results
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存至: {report_file}")


def main():
    """主函数"""
    tester = ImprovedSystemTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
