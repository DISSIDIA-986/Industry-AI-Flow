#!/usr/bin/env python3
"""
Ollama vs llama.cpp 性能对比测试

对比指标：
1. TPS (Tokens Per Second) - 吞吐量
2. 首个 Token 时间 (TTFT - Time To First Token)
3. 总推理时间
4. 内存占用
5. CPU/GPU 使用率
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Dict, List, Optional

import psutil
import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """单次测试结果"""

    backend: str  # "ollama" or "llama.cpp"
    model: str
    query: str

    # 时间指标
    init_time_ms: float = 0  # 模型加载时间
    ttft_ms: float = 0  # Time to First Token
    total_time_ms: float = 0  # 总推理时间
    time_per_output_token_ms: float = 0  # 每个输出 token 的平均时间

    # 吞吐量指标
    prompt_tokens: int = 0
    output_tokens: int = 0
    tps: float = 0  # Tokens Per Second

    # 系统资源
    memory_mb: float = 0
    cpu_percent: float = 0

    # 答案质量
    answer_length: int = 0
    answer: str = ""

    def to_dict(self) -> Dict:
        return {
            "backend": self.backend,
            "model": self.model,
            "query": self.query,
            "init_time_ms": self.init_time_ms,
            "ttft_ms": self.ttft_ms,
            "total_time_ms": self.total_time_ms,
            "time_per_output_token_ms": self.time_per_output_token_ms,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "tps": self.tps,
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
            "answer_length": self.answer_length,
            "answer_preview": self.answer[:100] + "..."
            if len(self.answer) > 100
            else self.answer,
        }


class OllamaBenchmark:
    """Ollama 性能测试"""

    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen3.5:4b"):
        self.host = host
        self.model = model
        self.api_url = f"{host}/api/generate"

    def test_query(self, query: str, max_tokens: int = 256) -> BenchmarkResult:
        """测试单个查询"""
        logger.info(f"\n[Ollama] 查询: {query[:50]}...")

        # 记录初始内存
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        start_time = time.time()
        first_token_time = None
        full_response = ""
        output_tokens = 0

        try:
            # 使用 stream=True 来获取首个 token 时间
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": query,
                    "stream": True,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7,
                    },
                },
                stream=True,
                timeout=120,
            )

            first_chunk = True
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if data.get("done"):
                        # 最终响应包含统计信息
                        output_tokens = data.get("prompt_eval_count", 0) + data.get(
                            "eval_count", 0
                        )
                    else:
                        content = data.get("response", "")
                        if content and first_chunk:
                            first_token_time = time.time()
                            first_chunk = False
                        full_response += content

        except Exception as e:
            logger.error(f"Ollama 查询失败: {e}")
            return BenchmarkResult(
                backend="ollama",
                model=self.model,
                query=query,
            )

        total_time = time.time() - start_time

        # 计算指标
        ttft = (
            (first_token_time - start_time) * 1000
            if first_token_time
            else total_time * 1000
        )
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_used = final_memory - initial_memory

        # 估算 TPS
        tps = output_tokens / total_time if total_time > 0 and output_tokens > 0 else 0
        time_per_token = (total_time * 1000) / output_tokens if output_tokens > 0 else 0

        result = BenchmarkResult(
            backend="ollama",
            model=self.model,
            query=query,
            ttft_ms=ttft,
            total_time_ms=total_time * 1000,
            time_per_output_token_ms=time_per_token,
            output_tokens=output_tokens,
            tps=tps,
            memory_mb=memory_used,
            cpu_percent=process.cpu_percent(),
            answer_length=len(full_response),
            answer=full_response,
        )

        logger.info(f"  ✅ 总时间: {total_time:.2f}秒")
        logger.info(f"  TTFT: {ttft:.2f}ms")
        logger.info(f"  输出 tokens: {output_tokens}")
        logger.info(f"  TPS: {tps:.2f} tokens/s")
        logger.info(f"  内存增量: {memory_used:.2f}MB")

        return result


class LlamaCppBenchmark:
    """llama.cpp 性能测试"""

    def __init__(self, model_path: str, n_gpu_layers: int = 32):
        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.llm = None

    def initialize(self) -> float:
        """初始化模型，返回加载时间（毫秒）"""
        logger.info(f"\n[llama.cpp] 初始化模型...")
        logger.info(f"  模型路径: {self.model_path}")
        logger.info(f"  GPU 层数: {self.n_gpu_layers}")

        start_time = time.time()

        try:
            from llama_cpp import Llama

            self.llm = Llama(
                model_path=self.model_path,
                n_gpu_layers=self.n_gpu_layers,
                n_ctx=2048,
                n_threads=8,
                verbose=True,  # 启用详细输出以查看 Metal 状态
            )

        except Exception as e:
            logger.error(f"llama.cpp 初始化失败: {e}")
            raise

        load_time = (time.time() - start_time) * 1000
        logger.info(f"  ✅ 模型加载完成: {load_time:.2f}ms")

        return load_time

    def test_query(self, query: str, max_tokens: int = 256) -> BenchmarkResult:
        """测试单个查询"""
        if self.llm is None:
            init_time = self.initialize()
        else:
            init_time = 0

        logger.info(f"\n[llama.cpp] 查询: {query[:50]}...")

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024

        start_time = time.time()

        try:
            output = self.llm(
                query,
                max_tokens=max_tokens,
                stop=["", "<|im_end|>"],
                stream=False,
            )

            response_text = output["choices"][0]["text"]
            total_time = time.time() - start_time

            # 从 usage 获取 token 数
            usage = output.get("usage", {})
            output_tokens = usage.get("completion_tokens", len(response_text) // 2)

            # 计算 TPS
            tps = output_tokens / total_time if total_time > 0 else 0
            time_per_token = (
                (total_time * 1000) / output_tokens if output_tokens > 0 else 0
            )

            final_memory = process.memory_info().rss / 1024 / 1024
            memory_used = final_memory - initial_memory

            result = BenchmarkResult(
                backend="llama.cpp",
                model=Path(self.model_path).name,
                query=query,
                init_time_ms=init_time,
                ttft_ms=total_time * 1000,  # llama.cpp 不容易获取 TTFT
                total_time_ms=total_time * 1000,
                time_per_output_token_ms=time_per_token,
                output_tokens=output_tokens,
                tps=tps,
                memory_mb=memory_used,
                cpu_percent=process.cpu_percent(),
                answer_length=len(response_text),
                answer=response_text,
            )

            logger.info(f"  ✅ 总时间: {total_time:.2f}秒")
            logger.info(f"  输出 tokens: {output_tokens}")
            logger.info(f"  TPS: {tps:.2f} tokens/s")
            logger.info(f"  内存增量: {memory_used:.2f}MB")

            return result

        except Exception as e:
            logger.error(f"llama.cpp 查询失败: {e}")
            import traceback

            traceback.print_exc()
            return BenchmarkResult(
                backend="llama.cpp",
                model=Path(self.model_path).name,
                query=query,
            )


class ComparisonBenchmark:
    """对比测试"""

    def __init__(self):
        # 测试查询集
        self.test_queries = [
            "建筑项目中常见的成本超支原因有哪些？请简要回答。",
            "什么是风险管理中的风险评分？",
            "如何评估承包商的绩效评分？",
        ]

        # 后端配置
        self.ollama = OllamaBenchmark(model="qwen3.5:4b")
        self.llama_cpp = None  # 如果需要测试 llama.cpp，手动初始化

    def run_ollama_benchmark(self) -> List[BenchmarkResult]:
        """运行 Ollama 测试"""
        logger.info("\n" + "=" * 70)
        logger.info("🚀 Ollama 性能测试")
        logger.info("=" * 70)

        results = []
        for i, query in enumerate(self.test_queries, 1):
            logger.info(f"\n[{i}/{len(self.test_queries)}] 测试查询")
            result = self.ollama.test_query(query)
            results.append(result)
            time.sleep(2)  # 冷却时间

        return results

    def run_llama_cpp_benchmark(self, model_path: str) -> List[BenchmarkResult]:
        """运行 llama.cpp 测试"""
        logger.info("\n" + "=" * 70)
        logger.info("🚀 llama.cpp 性能测试")
        logger.info("=" * 70)

        try:
            self.llama_cpp = LlamaCppBenchmark(model_path, n_gpu_layers=32)

            results = []
            for i, query in enumerate(self.test_queries, 1):
                logger.info(f"\n[{i}/{len(self.test_queries)}] 测试查询")
                result = self.llama_cpp.test_query(query)
                results.append(result)
                time.sleep(2)

            return results

        except Exception as e:
            logger.error(f"llama.cpp 测试失败: {e}")
            return []

    def generate_comparison_report(
        self,
        ollama_results: List[BenchmarkResult],
        llama_results: List[BenchmarkResult],
    ) -> Dict:
        """生成对比报告"""

        if not ollama_results:
            logger.error("Ollama 结果为空")
            return {}

        # 计算 Ollama 统计
        ollama_tps = [r.tps for r in ollama_results if r.tps > 0]
        ollama_time = [r.total_time_ms for r in ollama_results if r.total_time_ms > 0]
        ollama_ttft = [r.ttft_ms for r in ollama_results if r.ttft_ms > 0]

        ollama_stats = {
            "avg_tps": mean(ollama_tps) if ollama_tps else 0,
            "avg_total_time_ms": mean(ollama_time) if ollama_time else 0,
            "avg_ttft_ms": mean(ollama_ttft) if ollama_ttft else 0,
            "median_tps": median(ollama_tps) if ollama_tps else 0,
            "total_queries": len(ollama_results),
        }

        report = {
            "test_suite": "Ollama vs llama.cpp Performance Comparison",
            "timestamp": datetime.now().isoformat(),
            "hardware": "Mac Studio M1 Max (32GB)",
            "ollama": {
                "model": "qwen3.5:4b",
                "stats": ollama_stats,
                "results": [r.to_dict() for r in ollama_results],
            },
            "llama_cpp": {
                "enabled": len(llama_results) > 0,
                "stats": {},
                "results": [r.to_dict() for r in llama_results],
            }
            if llama_results
            else None,
        }

        # 如果有 llama.cpp 结果，计算统计
        if llama_results:
            llama_tps = [r.tps for r in llama_results if r.tps > 0]
            llama_time = [r.total_time_ms for r in llama_results if r.total_time_ms > 0]

            report["llama_cpp"]["stats"] = {
                "avg_tps": mean(llama_tps) if llama_tps else 0,
                "avg_total_time_ms": mean(llama_time) if llama_time else 0,
                "median_tps": median(llama_tps) if llama_tps else 0,
                "total_queries": len(llama_results),
            }

            # 性能对比
            if (
                ollama_stats["avg_tps"] > 0
                and report["llama_cpp"]["stats"]["avg_tps"] > 0
            ):
                tps_diff = (
                    report["llama_cpp"]["stats"]["avg_tps"] / ollama_stats["avg_tps"]
                    - 1
                ) * 100
                report["comparison"] = {
                    "tps_diff_percent": tps_diff,
                    "faster_backend": "llama.cpp" if tps_diff > 0 else "Ollama",
                }

        # 打印汇总
        self._print_summary(report)

        return report

    def _print_summary(self, report: Dict):
        """打印测试汇总"""
        logger.info("\n" + "=" * 70)
        logger.info("📋 性能对比汇总")
        logger.info("=" * 70)

        ollama_stats = report["ollama"]["stats"]

        logger.info(f"\n🔵 Ollama (qwen3.5:4b):")
        logger.info(f"  平均 TPS: {ollama_stats['avg_tps']:.2f} tokens/s")
        logger.info(f"  中位数 TPS: {ollama_stats['median_tps']:.2f} tokens/s")
        logger.info(f"  平均总时间: {ollama_stats['avg_total_time_ms']:.2f}ms")
        logger.info(f"  平均 TTFT: {ollama_stats['avg_ttft_ms']:.2f}ms")

        if report.get("llama_cpp") and report["llama_cpp"]["stats"]:
            llama_stats = report["llama_cpp"]["stats"]
            logger.info(f"\n🟢 llama.cpp:")
            logger.info(f"  平均 TPS: {llama_stats['avg_tps']:.2f} tokens/s")
            logger.info(f"  中位数 TPS: {llama_stats['median_tps']:.2f} tokens/s")
            logger.info(f"  平均总时间: {llama_stats['avg_total_time_ms']:.2f}ms")

            if report.get("comparison"):
                comp = report["comparison"]
                logger.info(f"\n🏆 对比结果:")
                logger.info(f"  TPS 差异: {comp['tps_diff_percent']:+.1f}%")
                logger.info(f"  更快: {comp['faster_backend']}")

        logger.info("=" * 70)


def main():
    """主函数"""
    benchmark = ComparisonBenchmark()

    # 1. 测试 Ollama
    ollama_results = benchmark.run_ollama_benchmark()

    # 2. 测试 llama.cpp (可选，如果模型文件存在)
    llama_model_path = "models/gguf/qwen3.5-4b/Qwen3-4B-Q4_K_M.gguf"
    llama_results = []

    if Path(llama_model_path).exists():
        try:
            llama_results = benchmark.run_llama_cpp_benchmark(llama_model_path)
        except Exception as e:
            logger.warning(f"llama.cpp 测试跳过: {e}")

    # 3. 生成对比报告
    report = benchmark.generate_comparison_report(ollama_results, llama_results)

    # 4. 保存结果
    output_path = Path("logs/ollama_vs_llama_benchmark.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ 测试结果已保存到: {output_path}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
