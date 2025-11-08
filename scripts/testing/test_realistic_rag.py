#!/usr/bin/env python3
"""
Realistic RAG System Test with Dataset-Specific Questions
Tests both Intent Classification and RAG retrieval quality with actual dataset queries
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from dotenv import load_dotenv
load_dotenv()

from backend.services.rag_engine import SimpleRAG


# 测试问题集 - 基于实际数据集设计
TEST_QUESTIONS = {
    "housing_dataset": {
        "description": "Housing.csv - 房价数据集 (in test_resources/datasets/)",
        "questions": [
            {
                "question": "What features are included in the housing dataset?",
                "difficulty": "简单",
                "expected_intent": "knowledge_retrieval",
                "keywords": ["price", "area", "bedrooms", "bathrooms"]
            },
            {
                "question": "How many bedrooms do most expensive houses have?",
                "difficulty": "中等",
                "expected_intent": "data_analysis",
                "keywords": ["bedrooms", "price", "expensive"]
            },
            {
                "question": "Is there a correlation between house area and price?",
                "difficulty": "中等",
                "expected_intent": "data_analysis",
                "keywords": ["correlation", "area", "price"]
            },
            {
                "question": "Compare furnished vs unfurnished houses in terms of average price",
                "difficulty": "困难",
                "expected_intent": "data_analysis",
                "keywords": ["furnished", "unfurnished", "average", "price"]
            },
            {
                "question": "What percentage of houses have air conditioning?",
                "difficulty": "中等",
                "expected_intent": "data_analysis",
                "keywords": ["percentage", "air conditioning"]
            }
        ]
    },
    "thyroid_dataset": {
        "description": "Thyroid_Diff.csv - 甲状腺疾病数据集 (in test_resources/datasets/)",
        "questions": [
            {
                "question": "What medical information is captured in the thyroid dataset?",
                "difficulty": "简单",
                "expected_intent": "knowledge_retrieval",
                "keywords": ["thyroid", "medical", "pathology", "stage"]
            },
            {
                "question": "What is the recurrence rate for thyroid patients?",
                "difficulty": "中等",
                "expected_intent": "data_analysis",
                "keywords": ["recurrence", "rate", "patients"]
            },
            {
                "question": "How does smoking history affect thyroid disease outcomes?",
                "difficulty": "困难",
                "expected_intent": "data_analysis",
                "keywords": ["smoking", "outcomes", "disease"]
            },
            {
                "question": "What is the distribution of thyroid cancer stages?",
                "difficulty": "中等",
                "expected_intent": "data_analysis",
                "keywords": ["distribution", "stage", "cancer"]
            },
            {
                "question": "Are there gender differences in thyroid disease presentation?",
                "difficulty": "困难",
                "expected_intent": "data_analysis",
                "keywords": ["gender", "differences", "presentation"]
            }
        ]
    },
    "unemployment_dataset": {
        "description": "Unemployment_Canada_1976_present.csv - 加拿大失业数据 (in test_resources/datasets/)",
        "questions": [
            {
                "question": "What time period does the Canada unemployment data cover?",
                "difficulty": "简单",
                "expected_intent": "knowledge_retrieval",
                "keywords": ["1976", "time", "period", "canada"]
            },
            {
                "question": "Which province had the highest unemployment in 1976?",
                "difficulty": "中等",
                "expected_intent": "data_analysis",
                "keywords": ["province", "highest", "unemployment", "1976"]
            },
            {
                "question": "How has youth unemployment (15-24) changed over time in Alberta?",
                "difficulty": "困难",
                "expected_intent": "data_analysis",
                "keywords": ["youth", "15-24", "unemployment", "alberta", "trend"]
            },
            {
                "question": "Compare employment rates between males and females in British Columbia",
                "difficulty": "困难",
                "expected_intent": "data_analysis",
                "keywords": ["employment rate", "males", "females", "british columbia"]
            },
            {
                "question": "What is the average participation rate across all age groups?",
                "difficulty": "中等",
                "expected_intent": "data_analysis",
                "keywords": ["average", "participation rate", "age groups"]
            }
        ]
    },
    "general_rag": {
        "description": "通用RAG系统问题",
        "questions": [
            {
                "question": "How does a RAG system work?",
                "difficulty": "简单",
                "expected_intent": "knowledge_retrieval",
                "keywords": ["rag", "retrieval", "generation", "system"]
            },
            {
                "question": "What is the difference between BM25 and vector search?",
                "difficulty": "中等",
                "expected_intent": "knowledge_retrieval",
                "keywords": ["bm25", "vector", "search", "difference"]
            },
            {
                "question": "Explain the role of embeddings in semantic search",
                "difficulty": "中等",
                "expected_intent": "knowledge_retrieval",
                "keywords": ["embeddings", "semantic", "search", "vectors"]
            }
        ]
    }
}


class RealisticRAGTester:
    """Realistic RAG system tester with intent classification validation"""

    def __init__(self):
        self.rag = SimpleRAG(use_hybrid_search=True, use_reranker=True)
        self.results = []
        self.intent_classifier = None

        # Try to load intent classifier
        try:
            from backend.services.intent_classifier import IntentClassifier
            self.intent_classifier = IntentClassifier()
        except Exception as e:
            print(f"⚠️ Intent classifier not available: {e}")

    def classify_intent(self, question: str) -> Dict:
        """Classify question intent"""
        if not self.intent_classifier:
            return {"intent": "unknown", "confidence": 0.0}

        try:
            result = self.intent_classifier.classify(question)
            return {
                "intent": result.get("intent", "unknown"),
                "confidence": result.get("confidence", 0.0)
            }
        except Exception as e:
            return {"intent": "error", "confidence": 0.0, "error": str(e)}

    def test_question(self, dataset: str, q_data: Dict) -> Dict:
        """Test a single question"""
        question = q_data["question"]
        print(f"\n{'='*60}")
        print(f"数据集: {dataset}")
        print(f"问题: {question}")
        print(f"难度: {q_data['difficulty']}")
        print(f"预期意图: {q_data['expected_intent']}")
        print(f"{'='*60}")

        # 1. Intent Classification
        intent_start = time.time()
        intent_result = self.classify_intent(question)
        intent_time = time.time() - intent_start

        print(f"\n🎯 意图分类:")
        print(f"   识别意图: {intent_result.get('intent', 'N/A')}")
        print(f"   置信度: {intent_result.get('confidence', 0.0):.2f}")
        print(f"   分类时间: {intent_time:.3f}s")

        # Check intent match
        intent_correct = intent_result.get('intent') == q_data['expected_intent']
        if intent_correct:
            print(f"   ✅ 意图识别正确")
        else:
            print(f"   ❌ 意图识别错误 (预期: {q_data['expected_intent']})")

        # 2. RAG Retrieval
        rag_start = time.time()
        try:
            rag_response = self.rag.query(question, top_k=5)
            rag_time = time.time() - rag_start

            print(f"\n📚 RAG检索:")
            print(f"   检索文档: {len(rag_response.get('sources', []))} 个")
            print(f"   答案长度: {len(rag_response.get('answer', ''))} 字符")
            print(f"   检索时间: {rag_time:.3f}s")

            # Check keyword relevance
            answer = rag_response.get('answer', '').lower()
            keywords_found = [kw for kw in q_data['keywords']
                            if kw.lower() in answer]
            keyword_match_rate = len(keywords_found) / len(q_data['keywords'])

            print(f"\n🔍 相关性检查:")
            print(f"   关键词匹配: {len(keywords_found)}/{len(q_data['keywords'])} ({keyword_match_rate*100:.1f}%)")
            if keywords_found:
                print(f"   匹配关键词: {', '.join(keywords_found)}")

            # Display retrieved chunks
            print(f"\n📄 检索到的文档块:")
            for i, chunk in enumerate(rag_response.get('retrieved_chunks', [])[:3], 1):
                content_preview = chunk.get('content', '')[:100]
                score = chunk.get('score', 0)
                print(f"   [{i}] (得分: {score:.4f}) {content_preview}...")

            # Display answer
            print(f"\n💬 生成答案:")
            print(f"   {rag_response.get('answer', 'N/A')[:300]}...")

            return {
                "question": question,
                "dataset": dataset,
                "difficulty": q_data['difficulty'],
                "intent_expected": q_data['expected_intent'],
                "intent_actual": intent_result.get('intent'),
                "intent_confidence": intent_result.get('confidence', 0.0),
                "intent_correct": intent_correct,
                "intent_time": intent_time,
                "rag_time": rag_time,
                "sources_count": len(rag_response.get('sources', [])),
                "answer_length": len(rag_response.get('answer', '')),
                "keywords_matched": len(keywords_found),
                "keywords_total": len(q_data['keywords']),
                "keyword_match_rate": keyword_match_rate,
                "answer": rag_response.get('answer', ''),
                "status": "success"
            }

        except Exception as e:
            print(f"\n❌ RAG查询失败: {str(e)}")
            return {
                "question": question,
                "dataset": dataset,
                "difficulty": q_data['difficulty'],
                "status": "failed",
                "error": str(e)
            }

    def run_all_tests(self):
        """Run all test questions"""
        print("\n" + "="*60)
        print("🧪 开始真实场景RAG系统测试")
        print("="*60)

        total_questions = sum(len(cat['questions']) for cat in TEST_QUESTIONS.values())
        current = 0

        for dataset_name, dataset_info in TEST_QUESTIONS.items():
            print(f"\n\n{'#'*60}")
            print(f"# 测试数据集: {dataset_info['description']}")
            print(f"{'#'*60}")

            for q_data in dataset_info['questions']:
                current += 1
                print(f"\n[{current}/{total_questions}]", end=" ")
                result = self.test_question(dataset_name, q_data)
                self.results.append(result)
                time.sleep(1)  # Rate limiting

        self.generate_report()

    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n\n" + "="*60)
        print("📊 测试结果汇总")
        print("="*60)

        # Overall stats
        total = len(self.results)
        successful = sum(1 for r in self.results if r.get('status') == 'success')
        failed = total - successful

        print(f"\n总测试问题: {total}")
        print(f"成功: {successful}")
        print(f"失败: {failed}")
        print(f"成功率: {successful/total*100:.1f}%")

        if successful > 0:
            # Intent classification accuracy
            intent_results = [r for r in self.results
                            if r.get('status') == 'success' and 'intent_correct' in r]
            if intent_results:
                intent_correct = sum(1 for r in intent_results if r.get('intent_correct'))
                intent_accuracy = intent_correct / len(intent_results) * 100
                avg_confidence = sum(r.get('intent_confidence', 0) for r in intent_results) / len(intent_results)

                print(f"\n🎯 意图分类准确率:")
                print(f"   正确: {intent_correct}/{len(intent_results)} ({intent_accuracy:.1f}%)")
                print(f"   平均置信度: {avg_confidence:.2f}")

            # RAG performance by difficulty
            print(f"\n📚 RAG性能 (按难度):")
            for difficulty in ["简单", "中等", "困难"]:
                diff_results = [r for r in self.results
                              if r.get('difficulty') == difficulty and r.get('status') == 'success']
                if diff_results:
                    avg_time = sum(r.get('rag_time', 0) for r in diff_results) / len(diff_results)
                    avg_match = sum(r.get('keyword_match_rate', 0) for r in diff_results) / len(diff_results)
                    print(f"   {difficulty}: {len(diff_results)}题, "
                          f"平均耗时 {avg_time:.2f}s, "
                          f"关键词匹配率 {avg_match*100:.1f}%")

            # Performance by dataset
            print(f"\n📊 各数据集表现:")
            for dataset_name in TEST_QUESTIONS.keys():
                ds_results = [r for r in self.results
                            if r.get('dataset') == dataset_name and r.get('status') == 'success']
                if ds_results:
                    avg_match = sum(r.get('keyword_match_rate', 0) for r in ds_results) / len(ds_results)
                    avg_sources = sum(r.get('sources_count', 0) for r in ds_results) / len(ds_results)
                    print(f"   {dataset_name}: {len(ds_results)}题, "
                          f"关键词匹配 {avg_match*100:.1f}%, "
                          f"平均检索文档 {avg_sources:.1f}个")

            # Timing analysis
            rag_times = [r.get('rag_time', 0) for r in self.results if r.get('status') == 'success']
            if rag_times:
                print(f"\n⏱️ 响应时间分析:")
                print(f"   平均: {sum(rag_times)/len(rag_times):.2f}s")
                print(f"   最快: {min(rag_times):.2f}s")
                print(f"   最慢: {max(rag_times):.2f}s")
                print(f"   P95: {sorted(rag_times)[int(len(rag_times)*0.95)]:.2f}s")

        # Save detailed results
        output_file = "test_results/realistic_rag_test_results.json"
        Path("test_results").mkdir(exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total": total,
                    "successful": successful,
                    "failed": failed,
                    "success_rate": f"{successful/total*100:.1f}%"
                },
                "results": self.results
            }, f, indent=2, ensure_ascii=False)

        print(f"\n📁 详细结果已保存到: {output_file}")


if __name__ == "__main__":
    tester = RealisticRAGTester()
    tester.run_all_tests()
