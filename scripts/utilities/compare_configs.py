#!/usr/bin/env python3
"""比较不同RAG配置的性能"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.rag_engine import SimpleRAG


def load_test_cases(file_path: str = "samples/test_questions.json"):
    """加载测试问题集"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate(rag_engine, test_cases, config_name: str):
    """评估配置"""
    correct = 0
    total = len(test_cases)
    latencies = []

    print(f"\n{'='*60}")
    print(f"测试配置: {config_name}")
    print(f"{'='*60}\n")

    for i, case in enumerate(test_cases, 1):
        start = time.time()
        try:
            result = rag_engine.query(case["question"])
            latency = time.time() - start
            latencies.append(latency)

            answer_lower = result["answer"].lower()
            keywords_matched = all(
                keyword.lower() in answer_lower
                for keyword in case.get("expected_keywords", [])
            )

            if keywords_matched:
                correct += 1

        except Exception as e:
            print(f"[{i}/{total}] 错误: {str(e)}")

    accuracy = correct / total
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    print(f"准确率: {accuracy*100:.1f}% ({correct}/{total})")
    print(f"平均延迟: {avg_latency:.2f}秒")
    print(f"P95延迟: {p95_latency:.2f}秒")

    return {
        "config": config_name,
        "accuracy": accuracy,
        "avg_latency": avg_latency,
        "p95_latency": p95_latency,
        "correct": correct,
        "total": total,
    }


if __name__ == "__main__":
    print("📥 加载测试问题集...")
    test_cases = load_test_cases("samples/test_questions.json")
    print(f"   共 {len(test_cases)} 个测试问题\n")

    results = []

    # 配置1: 混合检索 (无重排序)
    print("🚀 初始化配置1: 混合检索...")
    rag1 = SimpleRAG(use_hybrid_search=True, use_reranker=False)
    result1 = evaluate(rag1, test_cases, "混合检索 (BM25+向量)")
    results.append(result1)

    # 配置2: 混合检索 + 重排序
    print("\n🚀 初始化配置2: 混合检索 + 重排序...")
    rag2 = SimpleRAG(use_hybrid_search=True, use_reranker=True)
    result2 = evaluate(rag2, test_cases, "混合检索+重排序")
    results.append(result2)

    # 输出对比结果
    print(f"\n{'='*60}")
    print("📊 配置对比结果")
    print(f"{'='*60}\n")

    for r in results:
        print(f"{r['config']}:")
        print(f"  准确率: {r['accuracy']*100:.1f}%")
        print(f"  平均延迟: {r['avg_latency']:.2f}秒")
        print(f"  P95延迟: {r['p95_latency']:.2f}秒")
        print()

    # 保存结果
    with open("config_comparison.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("📁 对比结果已保存到: config_comparison.json")
