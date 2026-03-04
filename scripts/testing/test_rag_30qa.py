#!/usr/bin/env python3
"""
RAG 系统 30 问性能与准确性测试

基于已嵌入的施工行业标准文档，设计 30 个问题进行多轮测试，
评估响应速度、答案质量和 citation 准确性。
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, List

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TestQuestion:
    """测试问题"""
    id: int
    question: str
    category: str
    expected_keywords: List[str]
    expected_source_hint: str  # 预期来源文档提示


@dataclass
class TestResult:
    """单次测试结果"""
    question_id: int
    question: str
    category: str
    start_time: float
    end_time: float
    response_time_ms: float
    ttft_ms: float = 0  # Time to First Token
    success: bool = False
    answer: str = ""
    answer_length: int = 0
    has_citation: bool = False
    citation_sources: List[str] = field(default_factory=list)
    keyword_matches: List[str] = field(default_factory=list)
    keyword_match_rate: float = 0.0
    error_message: str = ""
    error_type: str = ""  # timeout, recursion_error, other


class RAGPerformanceTester:
    """RAG 性能和准确性测试"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_endpoint = f"{base_url}/api/v1/workflow/query"

        # 设计 30 个测试问题（基于已嵌入的文档）
        self.test_questions = self._design_test_questions()

    def _design_test_questions(self) -> List[TestQuestion]:
        """设计 30 个测试问题，覆盖不同文档和场景"""

        questions = [
            # GSA P100 文档 (建筑项目管理标准)
            TestQuestion(1, "GSA P100 标准中关于项目交付的主要阶段有哪些？",
                       "project_delivery", ["planning", "design", "construction", "commissioning"], "gsa_p100"),
            TestQuestion(2, "根据 GSA P100，项目管理中的关键利益相关者包括哪些？",
                       "stakeholder", ["owner", "architect", "contractor", "user"], "gsa_p100"),
            TestQuestion(3, "GSA P100 中对建筑性能评估有哪些要求？",
                       "performance", ["evaluation", "assessment", "criteria", "standards"], "gsa_p100"),
            TestQuestion(4, "按照 GSA P100 标准，设计审查流程应该如何进行？",
                       "design_review", ["review", "process", "approval", "documentation"], "gsa_p100"),
            TestQuestion(5, "GSA P100 对可持续建筑设计有什么要求？",
                       "sustainability", ["sustainable", "green", "environmental", "energy"], "gsa_p100"),
            TestQuestion(6, "根据 GSA P100，项目风险管理的最佳实践是什么？",
                       "risk_management", ["risk", "mitigation", "assessment", "contingency"], "gsa_p100"),
            TestQuestion(7, "GSA P100 中关于成本控制的指导原则是什么？",
                       "cost_control", ["budget", "cost", "control", "estimate"], "gsa_p100"),
            TestQuestion(8, "按照 GSA P100，项目沟通计划应该包含哪些要素？",
                       "communication", ["stakeholder", "communication", "reporting", "meetings"], "gsa_p100"),

            # UFGS 现浇混凝土规范
            TestQuestion(9, "UFGS 对现浇混凝土的强度等级有什么要求？",
                       "concrete_strength", ["compressive", "strength", "psi", "concrete"], "ufgs_concrete"),
            TestQuestion(10, "根据 UFGS，混凝土浇筑过程中的温度控制要求是什么？",
                        "temperature", ["temperature", "curing", "protection", "weather"], "ufgs_concrete"),
            TestQuestion(11, "UFGS 中关于混凝土养护的标准做法是什么？",
                        "curing", ["curing", "moisture", "time", "protection"], "ufgs_concrete"),
            TestQuestion(12, "按照 UFGS，现浇混凝土的钢筋间距有什么要求？",
                        "reinforcement", ["rebar", "spacing", "cover", "concrete"], "ufgs_concrete"),
            TestQuestion(13, "UFGS 对混凝土样品检测有哪些要求？",
                        "testing", ["test", "sample", "compressive", "frequency"], "ufgs_concrete"),
            TestQuestion(14, "根据 UFGS，现浇混凝土施工中的模板要求是什么？",
                        "formwork", ["formwork", "shoring", "bracing", "removal"], "ufgs_concrete"),
            TestQuestion(15, "UFGS 中关于混凝土接缝处理的要求是什么？",
                        "joints", ["joint", "expansion", "contraction", "sealant"], "ufgs_concrete"),

            # OSHA 安全规范
            TestQuestion(16, "OSHA 1926 标准中关于施工现场个人防护装备的要求是什么？",
                        "ppe", ["PPE", "safety", "protection", "equipment"], "osha"),
            TestQuestion(17, "根据 OSHA 1926，高空作业的安全规范有哪些？",
                        "fall_protection", ["fall", "protection", "harness", "guardrail"], "osha"),
            TestQuestion(18, "OSHA 对施工用电安全有什么要求？",
                        "electrical", ["electrical", "grounding", "gfci", "safety"], "osha"),
            TestQuestion(19, "按照 OSHA 1926，施工现场消防安全要求是什么？",
                        "fire_safety", ["fire", "extinguisher", "prevention", "emergency"], "osha"),
            TestQuestion(20, "OSHA 对施工机械操作的安全规定有哪些？",
                        "equipment_safety", ["equipment", "operator", "training", "certification"], "osha"),

            # Caltrans 标准规范
            TestQuestion(21, "Caltrans 标准规范中对材料质量有什么要求？",
                        "materials", ["quality", "specification", "testing", "approval"], "caltrans"),
            TestQuestion(22, "根据 Caltrans，道路施工的交通控制要求是什么？",
                        "traffic_control", ["traffic", "control", "signing", "barrier"], "caltrans"),
            TestQuestion(23, "Caltrans 规范中对排水系统的要求是什么？",
                        "drainage", ["drainage", "stormwater", "culvert", "channel"], "caltrans"),
            TestQuestion(24, "按照 Caltrans，路面平整度的标准是什么？",
                        "pavement", ["smoothness", "profile", "roughness", "specification"], "caltrans"),

            # IFC 建筑数据标准
            TestQuestion(25, "IFC 4.3 标准中建筑元素的基本属性有哪些？",
                        "ifc_elements", ["attribute", "property", "classification", "type"], "ifc"),
            TestQuestion(26, "根据 IFC 4.3，几何表示的方法有哪些？",
                        "geometry", ["geometry", "representation", "extrusion", "brep"], "ifc"),

            # 综合问题
            TestQuestion(27, "施工项目中如何平衡成本、质量和时间？",
                        "project_triple_constraint", ["cost", "quality", "time", "trade-off"], "general"),
            TestQuestion(28, "建筑工程中的可持续性最佳实践是什么？",
                        "sustainability_best_practices", ["sustainability", "green", "leed", "efficiency"], "general"),
            TestQuestion(29, "如何有效管理施工项目的风险？",
                        "risk_management_best", ["identify", "assess", "mitigate", "monitor"], "general"),
            TestQuestion(30, "施工项目中的质量保证和质量控制有什么区别？",
                        "qa_vs_qc", ["quality assurance", "quality control", "process", "product"], "general"),
        ]

        return questions

    def test_single_question(self, question: TestQuestion) -> TestResult:
        """测试单个问题"""
        logger.info(f"\n[{question.id}/30] 测试问题: {question.question[:60]}...")

        result = TestResult(
            question_id=question.id,
            question=question.question,
            category=question.category,
            start_time=time.time(),
            end_time=0.0,
            response_time_ms=0.0,
        )

        try:
            # 发送请求
            request_payload = {
                "query": question.question,  # P0 修复: 使用正确的字段名
                "session_id": f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            }

            response = requests.post(
                self.api_endpoint,
                json=request_payload,
                timeout=(10, 120)  # (connect, read) timeout
            )

            result.end_time = time.time()
            result.response_time_ms = (result.end_time - result.start_time) * 1000

            if response.status_code == 200:
                data = response.json()

                # 提取答案
                answer = data.get("agent_response", "")
                if not answer:
                    answer = data.get("response", "")

                result.success = data.get("success", True)
                result.answer = answer
                result.answer_length = len(answer)

                # 检查 citation
                result.has_citation = "[Sources:" in answer or "[Sources: " in answer
                if result.has_citation:
                    # 提取 sources
                    import re
                    citation_match = re.search(r'\[Sources:\s*(.*?)\]', answer)
                    if citation_match:
                        sources_text = citation_match.group(1)
                        result.citation_sources = [s.strip() for s in sources_text.split(",")]

                # 检查关键词匹配
                result.keyword_matches = [
                    kw for kw in question.expected_keywords
                    if kw.lower() in answer.lower()
                ]
                result.keyword_match_rate = len(result.keyword_matches) / len(question.expected_keywords)

                logger.info(f"  ✅ 响应时间: {result.response_time_ms:.2f}ms")
                logger.info(f"  答案长度: {result.answer_length} 字符")
                logger.info(f"  有 citation: {result.has_citation}")
                logger.info(f"  关键词匹配: {result.keyword_match_rate:.1%} ({len(result.keyword_matches)}/{len(question.expected_keywords)})")

            else:
                result.success = False
                result.error_type = "http_error"
                result.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"  ❌ HTTP 错误: {result.error_message}")

        except requests.exceptions.Timeout as e:
            result.end_time = time.time()
            result.response_time_ms = (result.end_time - result.start_time) * 1000
            result.success = False
            result.error_type = "timeout"
            result.error_message = str(e)
            logger.error(f"  ❌ 超时: {result.response_time_ms/1000:.2f}秒")

        except Exception as e:
            result.end_time = time.time()
            result.response_time_ms = (result.end_time - result.start_time) * 1000
            result.success = False
            result.error_type = "other"
            result.error_message = str(e)
            logger.error(f"  ❌ 错误: {e}")

        return result

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有 30 个测试"""
        logger.info("\n" + "="*80)
        logger.info("🚀 开始 RAG 系统 30 问性能与准确性测试")
        logger.info("="*80)

        results = []
        start_time = time.time()

        for i, question in enumerate(self.test_questions, 1):
            result = self.test_single_question(question)
            results.append(result)
            time.sleep(1)  # 避免过快请求

        total_duration = time.time() - start_time

        # 生成测试报告
        report = self._generate_report(results, total_duration)

        return report

    def _generate_report(self, results: List[TestResult], total_duration: float) -> Dict[str, Any]:
        """生成测试报告"""

        # 成功率统计
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        success_rate = len(successful) / len(results) if results else 0

        # 性能统计
        response_times = [r.response_time_ms for r in successful]
        avg_response_time = mean(response_times) if response_times else 0
        median_response_time = median(response_times) if response_times else 0
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0

        # 质量统计
        with_citation = sum(1 for r in successful if r.has_citation)
        citation_rate = with_citation / len(successful) if successful else 0

        avg_keyword_match = mean([r.keyword_match_rate for r in successful]) if successful else 0

        # 错误统计
        error_types = {}
        for r in failed:
            error_types[r.error_type] = error_types.get(r.error_type, 0) + 1

        report = {
            "test_suite": "RAG System 30-Question Performance & Accuracy Test",
            "timestamp": datetime.now().isoformat(),
            "test_environment": {
                "api_endpoint": self.api_endpoint,
                "total_questions": len(results),
            },
            "summary": {
                "total_duration_seconds": total_duration,
                "success_count": len(successful),
                "failed_count": len(failed),
                "success_rate": success_rate,
                "avg_response_time_ms": avg_response_time,
                "median_response_time_ms": median_response_time,
                "p95_response_time_ms": p95_response_time,
                "citation_rate": citation_rate,
                "avg_keyword_match_rate": avg_keyword_match,
            },
            "performance_by_category": self._analyze_by_category(successful),
            "errors": error_types,
            "detailed_results": [
                {
                    "question_id": r.question_id,
                    "question": r.question,
                    "category": r.category,
                    "success": r.success,
                    "response_time_ms": r.response_time_ms,
                    "answer_length": r.answer_length,
                    "has_citation": r.has_citation,
                    "citation_sources": r.citation_sources,
                    "keyword_match_rate": r.keyword_match_rate,
                    "keyword_matches": r.keyword_matches,
                    "error_type": r.error_type if not r.success else None,
                    "error_message": r.error_message if not r.success else None,
                    "answer_preview": r.answer[:200] + "..." if len(r.answer) > 200 else r.answer,
                }
                for r in results
            ],
        }

        # 打印汇总
        self._print_summary(report)

        return report

    def _analyze_by_category(self, results: List[TestResult]) -> Dict[str, Dict]:
        """按类别分析性能"""
        categories = {}

        for r in results:
            if r.category not in categories:
                categories[r.category] = {
                    "count": 0,
                    "success_count": 0,
                    "response_times": [],
                    "keyword_matches": [],
                }

            cat = categories[r.category]
            cat["count"] += 1
            if r.success:
                cat["success_count"] += 1
                cat["response_times"].append(r.response_time_ms)
                cat["keyword_matches"].append(r.keyword_match_rate)

        # 计算统计
        for cat_name, cat_data in categories.items():
            cat_data["success_rate"] = cat_data["success_count"] / cat_data["count"]
            if cat_data["response_times"]:
                cat_data["avg_response_time_ms"] = mean(cat_data["response_times"])
                cat_data["avg_keyword_match_rate"] = mean(cat_data["keyword_matches"])

        return categories

    def _print_summary(self, report: Dict[str, Any]):
        """打印测试汇总"""
        logger.info("\n" + "="*80)
        logger.info("📋 30 问测试汇总")
        logger.info("="*80)

        summary = report["summary"]

        logger.info(f"\n总体结果:")
        logger.info(f"  总问题数: {report['test_environment']['total_questions']}")
        logger.info(f"  成功: {summary['success_count']}, 失败: {summary['failed_count']}")
        logger.info(f"  成功率: {summary['success_rate']:.1%}")

        logger.info(f"\n性能指标:")
        logger.info(f"  平均响应时间: {summary['avg_response_time_ms']:.2f}ms")
        logger.info(f"  中位数响应时间: {summary['median_response_time_ms']:.2f}ms")
        logger.info(f"  P95 响应时间: {summary['p95_response_time_ms']:.2f}ms")

        logger.info(f"\n质量指标:")
        logger.info(f"  Citation 率: {summary['citation_rate']:.1%}")
        logger.info(f"  平均关键词匹配率: {summary['avg_keyword_match_rate']:.1%}")

        if report["errors"]:
            logger.info(f"\n错误类型统计:")
            for error_type, count in report["errors"].items():
                logger.info(f"  {error_type}: {count}")

        logger.info(f"\n分类性能:")
        for cat_name, cat_data in report["performance_by_category"].items():
            logger.info(f"  {cat_name}:")
            logger.info(f"    成功率: {cat_data['success_rate']:.1%}")
            logger.info(f"    平均响应: {cat_data.get('avg_response_time_ms', 0):.2f}ms")
            logger.info(f"    关键词匹配: {cat_data.get('avg_keyword_match_rate', 0):.1%}")

        logger.info("="*80)


def main():
    """主函数"""
    tester = RAGPerformanceTester()

    # 运行测试
    report = tester.run_all_tests()

    # 保存结果
    output_path = Path("logs/rag_30qa_test_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ 测试报告已保存到: {output_path}")

    # 返回退出码
    return 0 if report["summary"]["success_rate"] >= 0.8 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
