#!/usr/bin/env python3
"""
简化的 RAG 测试脚本 - 直接使用 SimpleRAG 类

避免后端 API 启动问题，直接测试 RAG 核心功能。
"""

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SimpleTestResult:
    """简化的测试结果"""
    question_id: int
    question: str
    category: str
    response_time_ms: float
    success: bool
    answer: str = ""
    answer_length: int = 0
    has_citation: bool = False
    error_message: str = ""


# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 30 个测试问题
TEST_QUESTIONS = [
    # GSA P100
    (1, "GSA P100 标准中关于项目交付的主要阶段有哪些？", "gsa_p100"),
    (2, "根据 GSA P100，项目管理中的关键利益相关者包括哪些？", "gsa_p100"),
    (3, "GSA P100 中对建筑性能评估有哪些要求？", "gsa_p100"),
    (4, "按照 GSA P100 标准，设计审查流程应该如何进行？", "gsa_p100"),
    (5, "GSA P100 对可持续建筑设计有什么要求？", "gsa_p100"),
    (6, "根据 GSA P100，项目风险管理的最佳实践是什么？", "gsa_p100"),
    (7, "GSA P100 中关于成本控制的指导原则是什么？", "gsa_p100"),
    (8, "按照 GSA P100，项目沟通计划应该包含哪些要素？", "gsa_p100"),

    # UFGS 现浇混凝土
    (9, "UFGS 对现浇混凝土的强度等级有什么要求？", "ufgs_concrete"),
    (10, "根据 UFGS，混凝土浇筑过程中的温度控制要求是什么？", "ufgs_concrete"),
    (11, "UFGS 中关于混凝土养护的标准做法是什么？", "ufgs_concrete"),
    (12, "按照 UFGS，现浇混凝土的钢筋间距有什么要求？", "ufgs_concrete"),
    (13, "UFGS 对混凝土样品检测有哪些要求？", "ufgs_concrete"),
    (14, "根据 UFGS，现浇混凝土施工中的模板要求是什么？", "ufgs_concrete"),
    (15, "UFGS 中关于混凝土接缝处理的要求是什么？", "ufgs_concrete"),

    # OSHA 安全规范
    (16, "OSHA 1926 标准中关于施工现场个人防护装备的要求是什么？", "osha"),
    (17, "根据 OSHA 1926，高空作业的安全规范有哪些？", "osha"),
    (18, "OSHA 对施工用电安全有什么要求？", "osha"),
    (19, "按照 OSHA 1926，施工现场消防安全要求是什么？", "osha"),
    (20, "OSHA 对施工机械操作的安全规定有哪些？", "osha"),

    # Caltrans
    (21, "Caltrans 标准规范中对材料质量有什么要求？", "caltrans"),
    (22, "根据 Caltrans，道路施工的交通控制要求是什么？", "caltrans"),
    (23, "Caltrans 规范中对排水系统的要求是什么？", "caltrans"),
    (24, "按照 Caltrans，路面平整度的标准是什么？", "caltrans"),

    # IFC
    (25, "IFC 4.3 标准中建筑元素的基本属性有哪些？", "ifc"),
    (26, "根据 IFC 4.3，几何表示的方法有哪些？", "ifc"),

    # 综合问题
    (27, "施工项目中如何平衡成本、质量和时间？", "general"),
    (28, "建筑工程中的可持续性最佳实践是什么？", "general"),
    (29, "如何有效管理施工项目的风险？", "general"),
    (30, "施工项目中的质量保证和质量控制有什么区别？", "general"),
]


def run_simple_rag_test() -> dict:
    """运行简化的 RAG 测试"""
    logger.info("\n" + "="*80)
    logger.info("🚀 开始 RAG 系统 30 问简化测试")
    logger.info("="*80)

    try:
        from backend.services.rag_engine import SimpleRAG
    except Exception as e:
        logger.error(f"无法导入 SimpleRAG: {e}")
        logger.error("请确保在正确的 Python 环境中运行此脚本")
        return {"error": "Cannot import SimpleRAG"}

    # 初始化 RAG 引擎
    logger.info("\n初始化 RAG 引擎...")
    init_start = time.time()

    try:
        rag_engine = SimpleRAG(
            use_hybrid_search=True,
            use_reranker=True,
            enable_feedback=False,
        )
        init_time = (time.time() - init_start) * 1000
        logger.info(f"✅ RAG 引擎初始化完成，耗时: {init_time:.2f}ms")
    except Exception as e:
        logger.error(f"❌ RAG 引擎初始化失败: {e}")
        return {"error": f"RAG initialization failed: {e}"}

    # 运行测试
    results = []
    start_time = time.time()

    for i, (qid, question, category) in enumerate(TEST_QUESTIONS, 1):
        logger.info(f"\n[{i}/30] {category}: {question[:50]}...")

        try:
            query_start = time.time()
            response = rag_engine.query(
                question=question,
                session_id=f"test_30qa_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                top_k=5,
            )
            query_time = (time.time() - query_start) * 1000

            if response and response.get("answer"):
                answer = response["answer"]
                results.append(SimpleTestResult(
                    question_id=qid,
                    question=question,
                    category=category,
                    response_time_ms=query_time,
                    success=True,
                    answer=answer,
                    answer_length=len(answer),
                    has_citation="[Sources:" in answer or "[Sources: " in answer,
                ))
                logger.info(f"  ✅ 响应时间: {query_time:.2f}ms, 长度: {len(answer)} 字符")
            else:
                results.append(SimpleTestResult(
                    question_id=qid,
                    question=question,
                    category=category,
                    response_time_ms=query_time,
                    success=False,
                    error_message="空响应",
                ))
                logger.warning(f"  ⚠️  空响应")

        except Exception as e:
            query_time = (time.time() - query_start) * 1000
            results.append(SimpleTestResult(
                question_id=qid,
                question=question,
                category=category,
                response_time_ms=query_time,
                success=False,
                error_message=str(e)[:100],
            ))
            logger.error(f"  ❌ 错误: {e}")

        time.sleep(0.5)  # 避免过快请求

    total_time = time.time() - start_time

    # 生成报告
    report = generate_report(results, total_time, init_time)

    return report


def generate_report(results: List[SimpleTestResult], total_time: float, init_time: float) -> dict:
    """生成测试报告"""

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    response_times = [r.response_time_ms for r in successful]
    avg_response_time = mean(response_times) if response_times else 0
    median_response_time = median(response_times) if response_times else 0

    with_citation = sum(1 for r in successful if r.has_citation)
    citation_rate = with_citation / len(successful) if successful else 0

    report = {
        "test_suite": "RAG System 30-Question Simplified Test",
        "timestamp": datetime.now().isoformat(),
        "rag_engine_init_time_ms": init_time,
        "total_test_duration_seconds": total_time,
        "summary": {
            "total_questions": len(results),
            "success_count": len(successful),
            "failed_count": len(failed),
            "success_rate": len(successful) / len(results) if results else 0,
            "avg_response_time_ms": avg_response_time,
            "median_response_time_ms": median_response_time,
            "citation_rate": citation_rate,
            "avg_answer_length": mean([r.answer_length for r in successful]) if successful else 0,
        },
        "results": [
            {
                "question_id": r.question_id,
                "question": r.question,
                "category": r.category,
                "response_time_ms": r.response_time_ms,
                "success": r.success,
                "answer_length": r.answer_length,
                "has_citation": r.has_citation,
                "error": r.error_message if not r.success else None,
                "answer_preview": r.answer[:200] + "..." if len(r.answer) > 200 else r.answer,
            }
            for r in results
        ],
    }

    # 打印汇总
    print_summary(report)

    return report


def print_summary(report: dict):
    """打印测试汇总"""
    logger.info("\n" + "="*80)
    logger.info("📋 30 问测试汇总")
    logger.info("="*80)

    s = report["summary"]

    logger.info(f"\n总体结果:")
    logger.info(f"  总问题数: {s['total_questions']}")
    logger.info(f"  成功: {s['success_count']}, 失败: {s['failed_count']}")
    logger.info(f"  成功率: {s['success_rate']:.1%}")

    logger.info(f"\n性能指标:")
    logger.info(f"  RAG 初始化: {report['rag_engine_init_time_ms']:.2f}ms")
    logger.info(f"  平均响应时间: {s['avg_response_time_ms']:.2f}ms")
    logger.info(f"  中位数响应时间: {s['median_response_time_ms']:.2f}ms")
    logger.info(f"  总测试时间: {report['total_test_duration_seconds']:.2f}秒")

    logger.info(f"\n质量指标:")
    logger.info(f"  Citation 率: {s['citation_rate']:.1%}")
    logger.info(f"  平均答案长度: {s['avg_answer_length']:.0f} 字符")

    logger.info("="*80)


def main():
    """主函数"""
    report = run_simple_rag_test()

    if "error" in report:
        logger.error(f"测试失败: {report['error']}")
        return 1

    # 保存结果
    output_path = Path("logs/rag_30qa_simple_test_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ 测试报告已保存到: {output_path}")

    return 0 if report["summary"]["success_rate"] >= 0.7 else 1


if __name__ == "__main__":
    sys.exit(main())
