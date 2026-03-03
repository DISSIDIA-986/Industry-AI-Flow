#!/usr/bin/env python3
"""
llama.cpp + Metal 性能基准测试

测试 qwen3.5-4b GGUF 模型在 M1 Max 上的实际性能
"""

import json
import logging
import time
from pathlib import Path
from statistics import mean
from typing import Dict, Any

from llama_cpp import Llama

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LlamaMetalBenchmark:
    """llama.cpp + Metal 性能基准测试"""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.llm = None

        # 测试查询
        self.test_queries = [
            "建筑项目中常见的成本超支原因有哪些？",
            "什么是风险管理中的风险评分？",
            "如何评估承包商的绩效评分？",
        ]

    def initialize_model(self, n_gpu_layers: int = 32) -> float:
        """初始化模型并返回加载时间"""
        logger.info(f"\n{'='*70}")
        logger.info(f"初始化 llama.cpp + Metal 模型")
        logger.info(f"模型路径: {self.model_path}")
        logger.info(f"GPU 层数: {n_gpu_layers}")
        logger.info(f"{'='*70}\n")

        start_time = time.time()

        self.llm = Llama(
            model_path=self.model_path,
            n_gpu_layers=n_gpu_layers,  # 将所有层加载到 GPU
            n_ctx=2048,                  # 上下文大小
            n_threads=8,                 # CPU 线程数
            verbose=False,               # 关闭详细输出
        )

        load_time = time.time() - start_time
        logger.info(f"✅ 模型加载完成，耗时: {load_time:.2f}秒")

        return load_time

    def benchmark_single_query(self, query: str, max_tokens: int = 256) -> Dict[str, Any]:
        """测试单个查询的性能"""
        logger.info(f"\n查询: {query[:50]}...")

        # 记录开始时间
        start_time = time.time()
        first_token_time = None

        # 生成响应（流式输出以获取首个 token 时间）
        response_text = ""
        token_count = 0

        output = self.llm(
            query,
            max_tokens=max_tokens,
            stop=["<|endoftext|>", "<|im_end|>"],
            stream=False,  # 简化测试，使用非流式
        )

        response_time = time.time() - start_time
        response_text = output["choices"][0]["text"]
        token_count = output.get("usage", {}).get("completion_tokens", len(response_text) // 2)

        # 估算 TPS
        tps = token_count / response_time if response_time > 0 else 0

        result = {
            "query": query,
            "response_time_seconds": response_time,
            "response_time_ms": response_time * 1000,
            "token_count": token_count,
            "tps": tps,
            "answer_length": len(response_text),
            "answer": response_text[:100] + "..." if len(response_text) > 100 else response_text,
        }

        logger.info(f"  ✅ 响应时间: {response_time:.2f}秒")
        logger.info(f"  Token 数量: {token_count}")
        logger.info(f"  吞吐量: {tps:.2f} tokens/s")
        logger.info(f"  答案长度: {len(response_text)} 字符")

        return result

    def run_benchmark(self) -> Dict[str, Any]:
        """运行完整的基准测试"""
        logger.info("\n" + "="*70)
        logger.info("🚀 llama.cpp + Metal 性能基准测试")
        logger.info("="*70)

        # 1. 初始化模型
        init_time = self.initialize_model(n_gpu_layers=32)

        # 2. 运行测试查询
        results = []
        start_time = time.time()

        for i, query in enumerate(self.test_queries, 1):
            logger.info(f"\n[{i}/{len(self.test_queries)}] 测试查询")
            result = self.benchmark_single_query(query)
            results.append(result)
            time.sleep(1)  # 冷却时间

        total_time = time.time() - start_time

        # 3. 生成报告
        report = self._generate_report(init_time, results, total_time)

        return report

    def _generate_report(self, init_time: float, results: list, total_time: float) -> Dict[str, Any]:
        """生成测试报告"""
        # 计算统计数据
        avg_response_time = mean([r["response_time_seconds"] for r in results])
        avg_tps = mean([r["tps"] for r in results])
        avg_tokens = mean([r["token_count"] for r in results])
        total_tokens = sum([r["token_count"] for r in results])

        report = {
            "test_suite": "llama.cpp + Metal Performance Benchmark",
            "timestamp": time.time(),
            "model_path": self.model_path,
            "hardware": "Mac Studio M1 Max (32GB)",
            "backend": "llama.cpp + Metal (GPU offloading)",
            "initialization_time_seconds": init_time,
            "total_test_time_seconds": total_time,
            "total_queries": len(results),
            "statistics": {
                "avg_response_time_seconds": avg_response_time,
                "avg_response_time_ms": avg_response_time * 1000,
                "avg_tps": avg_tps,
                "avg_tokens_per_query": avg_tokens,
                "total_tokens_generated": total_tokens,
            },
            "results": results,
        }

        # 打印汇总
        logger.info("\n" + "="*70)
        logger.info("📋 测试汇总")
        logger.info("="*70)
        logger.info(f"  初始化时间: {init_time:.2f}秒")
        logger.info(f"  总查询数: {len(results)}")
        logger.info(f"  总耗时: {total_time:.2f}秒")
        logger.info(f"  平均响应时间: {avg_response_time:.2f}秒")
        logger.info(f"  平均吞吐量: {avg_tps:.2f} tokens/s")
        logger.info(f"  总生成 Token: {total_tokens}")
        logger.info("="*70)

        # 性能对比
        logger.info("\n📊 性能对比:")
        logger.info(f"  llama.cpp + Metal: {avg_tps:.2f} tokens/s")
        logger.info(f"  Ollama (qwen3.5:4b): ~20-30 tokens/s (估计)")
        logger.info(f"  Ollama (qwen3.5:9b): ~8-12 tokens/s (估计)")
        logger.info("="*70)

        return report


def main():
    """主函数"""
    model_path = "models/gguf/qwen3.5-4b/Qwen3-4B-Q4_K_M.gguf"

    # 检查模型文件
    if not Path(model_path).exists():
        logger.error(f"❌ 模型文件不存在: {model_path}")
        return 1

    benchmark = LlamaMetalBenchmark(model_path)
    report = benchmark.run_benchmark()

    # 保存结果
    output_path = Path("logs/llama_metal_benchmark_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ 测试结果已保存到: {output_path}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
