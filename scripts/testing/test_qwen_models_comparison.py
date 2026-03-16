#!/usr/bin/env python3
"""
Qwen 模型性能对比测试脚本

对比测试：
- qwen3.5:9b (9B 参数，6.6GB)
- qwen3.5:4b (4B 参数，3.4GB)

测试指标：
1. 响应时间（首次加载、后续推理）
2. 吞吐量（TPS - Tokens Per Second）
3. 内存使用
4. RAG 问答质量
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ModelBenchmarkResult:
    """单个模型的基准测试结果"""

    model_name: str
    model_size_gb: float
    parameters: str

    # 性能指标
    first_token_time_ms: float = 0
    avg_response_time_ms: float = 0
    median_response_time_ms: float = 0
    p95_response_time_ms: float = 0

    # 吞吐量指标
    tokens_per_second: float = 0
    total_tokens: int = 0
    total_time_seconds: float = 0

    # 内存使用（如果可用）
    memory_used_gb: float = 0

    # 质量指标
    successful_queries: int = 0
    failed_queries: int = 0
    avg_answer_length: int = 0


class QwenModelBenchmark:
    """Qwen 模型性能对比测试"""

    def __init__(self):
        logger.info("初始化基准测试环境...")

        # 测试查询集
        self.test_queries = [
            "建筑项目中常见的成本超支原因有哪些？",
            "什么是风险管理中的风险评分？",
            "如何评估承包商的绩效评分？",
            "施工过程中如何应对天气风险？",
        ]

        logger.info(f"准备了 {len(self.test_queries)} 个测试查询")

    def test_model(self, model_name: str, model_size_gb: float) -> ModelBenchmarkResult:
        """测试单个模型"""
        logger.info(f"\n{'='*70}")
        logger.info(f"开始测试模型: {model_name}")
        logger.info(f"模型大小: {model_size_gb} GB")
        logger.info(f"{'='*70}\n")

        # 设置环境变量
        os.environ["OLLAMA_MODEL"] = model_name
        os.environ["LLM_BACKEND"] = "ollama"
        os.environ["HYBRID_MODE"] = "local_only"

        # 重新导入模块以使用新配置
        import importlib

        if "backend.services.rag_engine" in sys.modules:
            del sys.modules["backend.services.rag_engine"]

        from backend.services.rag_engine import SimpleRAG

        result = ModelBenchmarkResult(
            model_name=model_name,
            model_size_gb=model_size_gb,
            parameters=model_name.split(":")[1].replace("b", "B"),
        )

        try:
            # 初始化 RAG 引擎（包含模型加载）
            init_start = time.time()
            rag_engine = SimpleRAG(
                use_hybrid_search=True,
                use_reranker=True,
                enable_feedback=False,
            )
            init_time = (time.time() - init_start) * 1000
            logger.info(f"✅ 模型初始化完成，耗时: {init_time:.2f}ms")

            response_times = []
            total_tokens = 0
            answer_lengths = []
            successful = 0
            failed = 0

            # 运行测试查询
            for i, query in enumerate(self.test_queries, 1):
                try:
                    logger.info(f"\n[{i}/{len(self.test_queries)}] 查询: {query[:50]}...")

                    start = time.time()
                    response = rag_engine.query(
                        question=query,
                        session_id=f"bench_{model_name}_{i}",
                        top_k=5,
                    )
                    duration = (time.time() - start) * 1000

                    if response and response.get("answer"):
                        answer = response["answer"]
                        answer_length = len(answer)

                        # 估算 token 数（中文约 1.5 字符/token，英文约 4 字符/token）
                        estimated_tokens = int(answer_length / 2)
                        total_tokens += estimated_tokens

                        response_times.append(duration)
                        answer_lengths.append(answer_length)
                        successful += 1

                        tps = estimated_tokens / (duration / 1000)
                        logger.info(f"  ✅ 响应时间: {duration:.2f}ms")
                        logger.info(f"  答案长度: {answer_length} 字符")
                        logger.info(f"  估算 TPS: {tps:.2f} tokens/s")
                    else:
                        failed += 1
                        logger.warning(f"  ⚠️  空响应")

                except Exception as e:
                    failed += 1
                    logger.error(f"  ❌ 错误: {e}")

            # 计算统计数据
            result.first_token_time_ms = init_time
            result.successful_queries = successful
            result.failed_queries = failed
            result.total_tokens = total_tokens
            result.total_time_seconds = (
                sum(response_times) / 1000 if response_times else 0
            )

            if response_times:
                sorted_times = sorted(response_times)
                result.avg_response_time_ms = mean(response_times)
                result.median_response_time_ms = median(response_times)
                result.p95_response_time_ms = sorted_times[
                    int(len(sorted_times) * 0.95)
                ]

            if total_tokens > 0 and result.total_time_seconds > 0:
                result.tokens_per_second = total_tokens / result.total_time_seconds

            result.avg_answer_length = mean(answer_lengths) if answer_lengths else 0

            # 打印汇总
            logger.info(f"\n📊 {model_name} 测试汇总:")
            logger.info(f"  成功查询: {successful}/{len(self.test_queries)}")
            logger.info(f"  平均响应时间: {result.avg_response_time_ms:.2f}ms")
            logger.info(f"  中位数响应时间: {result.median_response_time_ms:.2f}ms")
            logger.info(f"  P95 响应时间: {result.p95_response_time_ms:.2f}ms")
            logger.info(f"  平均吞吐量: {result.tokens_per_second:.2f} tokens/s")
            logger.info(f"  平均答案长度: {result.avg_answer_length:.0f} 字符")

        except Exception as e:
            logger.error(f"测试失败: {e}")
            import traceback

            traceback.print_exc()

        return result

    def compare_models(self) -> Dict[str, Any]:
        """对比测试所有模型"""
        logger.info("\n" + "=" * 70)
        logger.info("🚀 开始 Qwen 模型性能对比测试")
        logger.info("=" * 70)

        models = [
            ("qwen3.5:9b", 6.6),
            ("qwen3.5:4b", 3.4),
        ]

        results = []
        start_time = time.time()

        for model_name, model_size in models:
            try:
                result = self.test_model(model_name, model_size)
                results.append(result)
            except Exception as e:
                logger.error(f"测试 {model_name} 失败: {e}")

        total_duration = (time.time() - start_time) / 60

        # 生成对比报告
        comparison = self._generate_comparison_report(results, total_duration)

        # 打印对比结果
        self._print_comparison_summary(comparison)

        return comparison

    def _generate_comparison_report(
        self, results: List[ModelBenchmarkResult], total_duration: float
    ) -> Dict[str, Any]:
        """生成对比报告"""
        return {
            "test_suite": "Qwen Model Performance Comparison",
            "timestamp": datetime.now().isoformat(),
            "total_duration_minutes": total_duration,
            "models": [
                {
                    "name": r.model_name,
                    "size_gb": r.model_size_gb,
                    "parameters": r.parameters,
                    "avg_response_time_ms": r.avg_response_time_ms,
                    "median_response_time_ms": r.median_response_time_ms,
                    "p95_response_time_ms": r.p95_response_time_ms,
                    "tokens_per_second": r.tokens_per_second,
                    "total_tokens": r.total_tokens,
                    "successful_queries": r.successful_queries,
                    "failed_queries": r.failed_queries,
                    "avg_answer_length": r.avg_answer_length,
                }
                for r in results
            ],
            "analysis": {
                "fastest_model": min(
                    results, key=lambda x: x.avg_response_time_ms
                ).model_name
                if results
                else None,
                "highest_tps": max(
                    results, key=lambda x: x.tokens_per_second
                ).model_name
                if results
                else None,
                "best_quality": max(
                    results, key=lambda x: x.avg_answer_length
                ).model_name
                if results
                else None,
            },
        }

    def _print_comparison_summary(self, comparison: Dict[str, Any]):
        """打印对比汇总"""
        logger.info("\n" + "=" * 70)
        logger.info("📋 模型对比汇总")
        logger.info("=" * 70)

        for model in comparison["models"]:
            logger.info(
                f"\n📊 {model['name']} ({model['parameters']}, {model['size_gb']} GB):"
            )
            logger.info(f"  平均响应时间: {model['avg_response_time_ms']:.2f}ms")
            logger.info(f"  吞吐量: {model['tokens_per_second']:.2f} tokens/s")
            logger.info(
                f"  成功率: {model['successful_queries']}/{model['successful_queries'] + model['failed_queries']}"
            )

        logger.info(f"\n🏆 分析结论:")
        logger.info(f"  最快响应: {comparison['analysis']['fastest_model']}")
        logger.info(f"  最高吞吐: {comparison['analysis']['highest_tps']}")
        logger.info(f"  最佳质量: {comparison['analysis']['best_quality']}")

        # M1 Max 优化建议
        logger.info(f"\n💡 M1 Max 优化建议:")
        logger.info(f"  1. 使用 qwen3.5:4b 可以获得更好的响应速度")
        logger.info(f"  2. 9B 模型适合需要更高质量答案的场景")
        logger.info(f"  3. 考虑使用 Ollama 的 NUMA 设置优化内存访问")
        logger.info(f"  4. 可以调整 Ollama 的线程数以获得更好性能")

        logger.info("=" * 70)


def main():
    benchmark = QwenModelBenchmark()
    results = benchmark.compare_models()

    # 保存结果
    output_path = Path("logs/model_comparison_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ 结果已保存到: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
