#!/usr/bin/env python3
"""RAG系统测试脚本"""

import json
import os
import sys
import time

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.rag_engine import SimpleRAG


def load_test_cases(file_path: str = "samples/test_questions.json"):
    """加载测试问题集"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_accuracy(rag_engine, test_cases):
    """评估准确率"""
    correct = 0
    total = len(test_cases)
    latencies = []
    results_detail = []

    print("=" * 60)
    print("开始RAG测试评估")
    print("=" * 60)
    print()

    for i, case in enumerate(test_cases, 1):
        print(f"[{i}/{total}] 测试问题: {case['question']}")

        start = time.time()
        try:
            result = rag_engine.query(case["question"])
            latency = time.time() - start
            latencies.append(latency)

            # 判断：答案中包含所有期望关键词
            answer_lower = result["answer"].lower()
            keywords_matched = all(
                keyword.lower() in answer_lower
                for keyword in case.get("expected_keywords", [])
            )

            if keywords_matched:
                correct += 1
                print(f"  ✅ 正确")
            else:
                print(f"  ❌ 错误")
                print(f"     期望关键词: {case.get('expected_keywords', [])}")
                print(f"     实际答案: {result['answer'][:100]}...")

            print(f"  ⏱️  延迟: {latency:.2f}秒")

            results_detail.append(
                {
                    "question": case["question"],
                    "expected_keywords": case.get("expected_keywords", []),
                    "answer": result["answer"],
                    "correct": keywords_matched,
                    "latency": latency,
                }
            )

        except Exception as e:
            print(f"  ❌ 错误: {str(e)}")
            results_detail.append(
                {
                    "question": case["question"],
                    "error": str(e),
                    "correct": False,
                    "latency": 0,
                }
            )

        print()

    accuracy = correct / total
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    print("=" * 60)
    print("📊 评估结果")
    print("=" * 60)
    print(f"准确率: {accuracy*100:.1f}% ({correct}/{total})")
    print(f"平均延迟: {avg_latency:.2f}秒")
    print(f"P95延迟: {p95_latency:.2f}秒")

    # 验收标准检查
    print()
    print("=" * 60)
    print("✅ 验收标准检查")
    print("=" * 60)
    print(f"准确率>70%: {'✅ 通过' if accuracy > 0.7 else '❌ 未通过'} ({accuracy*100:.1f}%)")
    print(f"P95延迟<10秒: {'✅ 通过' if p95_latency < 10 else '❌ 未通过'} ({p95_latency:.2f}秒)")

    return {
        "accuracy": accuracy,
        "avg_latency": avg_latency,
        "p95_latency": p95_latency,
        "correct": correct,
        "total": total,
        "details": results_detail,
    }


if __name__ == "__main__":
    # 加载测试问题集
    test_file = "samples/test_questions.json"
    if len(sys.argv) > 1:
        test_file = sys.argv[1]

    print("📥 加载测试问题集...")
    test_cases = load_test_cases(test_file)
    print(f"   共 {len(test_cases)} 个测试问题")
    print()

    # 初始化RAG引擎
    print("🚀 初始化RAG引擎...")
    rag_engine = SimpleRAG()
    print("   ✅ RAG引擎初始化完成")
    print()

    # 执行评估
    results = evaluate_accuracy(rag_engine, test_cases)

    # 保存结果
    output_file = "evaluation_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print()
    print(f"📁 评估结果已保存到: {output_file}")
