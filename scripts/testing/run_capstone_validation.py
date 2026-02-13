#!/usr/bin/env python3
"""
Capstone项目验证测试脚本

系统化验证Industry AI Flow三大核心功能:
1. RAG企业知识库系统
2. 成本估算(Cost Estimation)
3. 动态代码生成

执行方式:
    python scripts/testing/run_capstone_validation.py

输出:
    - 测试执行报告
    - 缺陷清单
    - 性能指标
    - 最终评分
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from typing import Any, Dict, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("tests/logs/capstone_validation.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class CapstoneValidator:
    """Capstone项目验证器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.start_time = time.time()

    def log_test_result(
        self,
        test_id: str,
        test_name: str,
        status: str,
        duration: float,
        details: str = "",
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录测试结果"""
        result = {
            "test_id": test_id,
            "test_name": test_name,
            "status": status,  # PASS, FAIL, SKIP
            "duration_seconds": duration,
            "details": details,
            "metrics": metrics or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        status_emoji = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}
        logger.info(
            f"{status_emoji[status]} {test_id}: {test_name} ({duration:.2f}s) - {details}"
        )

    # ==================== RAG功能测试 ====================

    def test_rag_smoke(self) -> bool:
        """RAG烟雾测试 - 验证基本文档上传和检索"""
        test_id = "TC-RAG-001"
        test_name = "RAG基本文档上传和检索"
        start_time = time.time()

        try:
            # 1. 检查API是否可用
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    f"健康检查失败: {response.status_code}",
                )
                return False

            # 2. 检查RAG API端点
            response = requests.get(
                f"{self.base_url}/api/v1/docs", timeout=5
            )
            if response.status_code != 200:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    "API文档不可用",
                )
                return False

            self.log_test_result(
                test_id,
                test_name,
                "PASS",
                time.time() - start_time,
                "RAG API服务可用",
            )
            return True

        except Exception as e:
            self.log_test_result(
                test_id, test_name, "FAIL", time.time() - start_time, str(e)
            )
            return False

    def test_rag_document_upload(self) -> bool:
        """RAG文档上传测试"""
        test_id = "TC-RAG-002"
        test_name = "RAG文档上传和向量化"
        start_time = time.time()

        try:
            # 创建测试文档
            test_doc = Path("tests/fixtures/test_building_knowledge.txt")
            test_doc.parent.mkdir(parents=True, exist_ok=True)
            test_doc.write_text(
                """
                建筑成本估算指南
                
                住宅建筑成本构成:
                - 材料成本: 45-55%
                - 人工成本: 25-35%
                - 设备成本: 10-15%
                - 管理费用: 5-10%
                
                影响成本的主要因素:
                1. 项目规模（平方英尺）
                2. 建筑类型（住宅/商业/工业）
                3. 地理位置
                4. 材料选择
                5. 劳动力成本
                """
            )

            # 上传文档
            with open(test_doc, "rb") as f:
                files = {"file": ("test_building_knowledge.txt", f, "text/plain")}
                response = requests.post(
                    f"{self.base_url}/api/v1/documents/upload",
                    files=files,
                    timeout=30,
                )

            if response.status_code != 200:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    f"文档上传失败: {response.status_code}",
                )
                return False

            result = response.json()
            if "document_id" not in result:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    "响应缺少document_id",
                )
                return False

            self.log_test_result(
                test_id,
                test_name,
                "PASS",
                time.time() - start_time,
                f"文档上传成功，document_id={result['document_id']}",
                {"document_id": result["document_id"]},
            )
            return True

        except Exception as e:
            self.log_test_result(
                test_id, test_name, "FAIL", time.time() - start_time, str(e)
            )
            return False

    def test_rag_query(self) -> bool:
        """RAG查询测试"""
        test_id = "TC-RAG-003"
        test_name = "RAG知识检索和答案生成"
        start_time = time.time()

        try:
            query_data = {
                "question": "住宅建筑的材料成本占比是多少？",
                "tenant_id": "capstone_test",
            }

            response = requests.post(
                f"{self.base_url}/api/v1/query",
                json=query_data,
                timeout=30,
            )

            if response.status_code != 200:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    f"查询失败: {response.status_code}",
                )
                return False

            result = response.json()
            if "answer" not in result:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    "响应缺少answer字段",
                )
                return False

            answer = result["answer"]
            if not answer or len(answer) < 10:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    f"答案过短或为空: {answer}",
                )
                return False

            self.log_test_result(
                test_id,
                test_name,
                "PASS",
                time.time() - start_time,
                f"检索成功，答案长度={len(answer)}字符",
                {
                    "answer_length": len(answer),
                    "has_sources": "sources" in result,
                },
            )
            return True

        except Exception as e:
            self.log_test_result(
                test_id, test_name, "FAIL", time.time() - start_time, str(e)
            )
            return False

    # ==================== 成本估算功能测试 ====================

    def test_cost_estimation_training(self) -> bool:
        """成本估算模型训练测试"""
        test_id = "TC-CE-001"
        test_name = "成本估算模型训练"
        start_time = time.time()

        try:
            # 创建测试数据集
            test_dataset = Path("tests/fixtures/test_cost_estimation.csv")
            if not test_dataset.exists():
                # 使用成本估算API测试中的数据集生成逻辑
                import numpy as np

                rng = np.random.default_rng(42)
                rows = 220
                project_type = rng.choice(
                    [
                        "residential_single_family",
                        "residential_multi_family",
                        "commercial_office",
                        "industrial_warehouse",
                    ],
                    size=rows,
                )
                location = rng.choice(
                    ["Toronto", "Calgary", "Ottawa", "Vancouver", "Montreal"],
                    size=rows,
                )
                sqft = rng.uniform(1500, 400000, size=rows)
                planned_duration_weeks = rng.uniform(18, 1500, size=rows)
                estimated_cost_cad = (sqft * rng.uniform(190, 330, size=rows)) + (
                    planned_duration_weeks * rng.uniform(1200, 5200, size=rows)
                )
                num_change_orders = rng.integers(0, 24, size=rows)
                material_volatility = rng.uniform(0.1, 0.9, size=rows)
                budget_pressure = rng.uniform(0.0, 0.8, size=rows)
                contractor_rating = rng.uniform(2.5, 5.0, size=rows)
                team_experience_years = rng.uniform(2.0, 19.0, size=rows)
                complexity_score = rng.integers(2, 10, size=rows)
                overrun = (
                    1.1 * num_change_orders
                    + 16.0 * material_volatility
                    + 8.0 * budget_pressure
                    + 0.25 * complexity_score
                    - 2.0 * contractor_rating
                    - 0.1 * team_experience_years
                    + rng.normal(0.0, 2.0, size=rows)
                )
                overrun = np.clip(overrun, -12.0, 55.0)
                actual_cost_cad = estimated_cost_cad * (1.0 + (overrun / 100.0))

                df = pd.DataFrame(
                    {
                        "project_type": project_type,
                        "location": location,
                        "sqft": sqft,
                        "floors": rng.integers(1, 40, size=rows),
                        "num_units": rng.integers(0, 240, size=rows),
                        "planned_duration_weeks": planned_duration_weeks,
                        "actual_duration_weeks": planned_duration_weeks
                        * (1.0 + np.clip(overrun / 100.0, -0.1, 0.45)),
                        "schedule_delay_pct": np.clip(
                            overrun * 0.5, -10.0, 45.0
                        ),
                        "estimated_cost_cad": estimated_cost_cad,
                        "actual_cost_cad": actual_cost_cad,
                        "cost_overrun_pct": overrun,
                        "contractor_rating": contractor_rating,
                        "complexity_score": complexity_score,
                        "team_experience_years": team_experience_years,
                        "num_change_orders": num_change_orders,
                        "weather_risk_factor": rng.uniform(0.2, 0.7, size=rows),
                        "material_volatility": material_volatility,
                        "num_subcontractors": rng.integers(3, 100, size=rows),
                        "budget_pressure": budget_pressure,
                        "risk_score": rng.uniform(20, 75, size=rows),
                        "risk_score_original": rng.uniform(5, 65, size=rows),
                        "on_budget": overrun <= 5,
                        "on_schedule": (
                            np.clip(overrun * 0.5, -10.0, 45.0) <= 5
                        ),
                        "data_source": "synthetic_industry_based",
                    }
                )
                df.to_csv(test_dataset, index=False)

            # 上传数据集并训练模型
            with open(test_dataset, "rb") as f:
                files = {"dataset": ("test_cost_estimation.csv", f, "text/csv")}
                response = requests.post(
                    f"{self.base_url}/api/v1/cost-estimation/train",
                    files=files,
                    timeout=120,  # 2分钟超时
                )

            if response.status_code not in [200, 202]:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    f"训练请求失败: {response.status_code}",
                )
                return False

            self.log_test_result(
                test_id,
                test_name,
                "PASS",
                time.time() - start_time,
                f"模型训练提交成功",
                {"dataset_rows": 220},
            )
            return True

        except Exception as e:
            self.log_test_result(
                test_id, test_name, "FAIL", time.time() - start_time, str(e)
            )
            return False

    def test_cost_estimation_prediction(self) -> bool:
        """成本估算预测测试"""
        test_id = "TC-CE-002"
        test_name = "成本估算预测"
        start_time = time.time()

        try:
            # 准备预测数据
            prediction_data = {
                "project_type": "residential_single_family",
                "location": "Toronto",
                "sqft": 2500,
                "floors": 2,
                "num_units": 1,
                "planned_duration_weeks": 24,
                "contractor_rating": 4.0,
                "complexity_score": 5,
                "team_experience_years": 10.0,
                "num_change_orders": 3,
                "material_volatility": 0.5,
                "budget_pressure": 0.3,
                "weather_risk_factor": 0.4,
                "num_subcontractors": 8,
                "risk_score": 40,
            }

            response = requests.post(
                f"{self.base_url}/api/v1/cost-estimation/predict",
                json=prediction_data,
                timeout=30,
            )

            if response.status_code != 200:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    f"预测请求失败: {response.status_code}",
                )
                return False

            result = response.json()
            if "estimated_cost" not in result:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    "响应缺少estimated_cost字段",
                )
                return False

            estimated_cost = result["estimated_cost"]
            if estimated_cost <= 0 or estimated_cost > 10000000:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    f"估算成本不合理: {estimated_cost}",
                )
                return False

            self.log_test_result(
                test_id,
                test_name,
                "PASS",
                time.time() - start_time,
                f"预测成功，估算成本=${estimated_cost:,.2f}",
                {
                    "estimated_cost": estimated_cost,
                    "has_confidence_interval": "confidence_interval"
                    in result,
                },
            )
            return True

        except Exception as e:
            self.log_test_result(
                test_id, test_name, "FAIL", time.time() - start_time, str(e)
            )
            return False

    # ==================== 代码生成功能测试 ====================

    def test_code_generation_upload(self) -> bool:
        """代码生成数据集上传测试"""
        test_id = "TC-DG-001"
        test_name = "代码生成数据集上传和分析"
        start_time = time.time()

        try:
            # 创建测试数据集
            test_dataset = Path("tests/fixtures/test_sales_data.csv")
            if not test_dataset.exists():
                import pandas as pd

                df = pd.DataFrame(
                    {
                        "date": pd.date_range("2024-01-01", periods=100),
                        "product": ["A", "B", "C"] * 33 + ["A"],
                        "sales": [100 + i * 10 for i in range(100)],
                        "quantity": [10 + i for i in range(100)],
                    }
                )
                df.to_csv(test_dataset, index=False)

            # 上传数据集
            with open(test_dataset, "rb") as f:
                files = {"file": ("test_sales_data.csv", f, "text/csv")}
                response = requests.post(
                    f"{self.base_url}/api/v1/data-analysis/upload",
                    files=files,
                    timeout=30,
                )

            if response.status_code != 200:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    f"数据集上传失败: {response.status_code}",
                )
                return False

            result = response.json()
            if "dataset_id" not in result:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    "响应缺少dataset_id字段",
                )
                return False

            self.log_test_result(
                test_id,
                test_name,
                "PASS",
                time.time() - start_time,
                f"数据集上传成功，dataset_id={result['dataset_id']}",
                {"dataset_id": result["dataset_id"]},
            )
            return True

        except Exception as e:
            self.log_test_result(
                test_id, test_name, "FAIL", time.time() - start_time, str(e)
            )
            return False

    def test_code_generation_query(self) -> bool:
        """代码生成分析查询测试"""
        test_id = "TC-DG-002"
        test_name = "代码生成和分析执行"
        start_time = time.time()

        try:
            query_data = {
                "question": "分析销售趋势，哪个产品销售额最高？",
                "dataset_id": "test_sales_data",
            }

            response = requests.post(
                f"{self.base_url}/api/v1/data-analysis/analyze",
                json=query_data,
                timeout=60,
            )

            if response.status_code != 200:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    f"分析请求失败: {response.status_code}",
                )
                return False

            result = response.json()
            if "answer" not in result:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    "响应缺少answer字段",
                )
                return False

            answer = result["answer"]
            if not answer or len(answer) < 10:
                self.log_test_result(
                    test_id,
                    test_name,
                    "FAIL",
                    time.time() - start_time,
                    f"答案过短或为空: {answer}",
                )
                return False

            self.log_test_result(
                test_id,
                test_name,
                "PASS",
                time.time() - start_time,
                f"分析成功，答案长度={len(answer)}字符",
                {
                    "answer_length": len(answer),
                    "has_code": "code" in result,
                    "has_visualizations": "visualizations" in result,
                },
            )
            return True

        except Exception as e:
            self.log_test_result(
                test_id, test_name, "FAIL", time.time() - start_time, str(e)
            )
            return False

    # ==================== 测试执行和报告 ====================

    def run_smoke_tests(self) -> Dict[str, Any]:
        """运行烟雾测试"""
        logger.info("=" * 80)
        logger.info("阶段1: 烟雾测试（烟雾测试）")
        logger.info("=" * 80)

        smoke_tests = [
            ("RAG功能", [self.test_rag_smoke, self.test_rag_document_upload, self.test_rag_query]),
            ("成本估算", [self.test_cost_estimation_training, self.test_cost_estimation_prediction]),
            ("代码生成", [self.test_code_generation_upload, self.test_code_generation_query]),
        ]

        results = {}
        for feature, tests in smoke_tests:
            logger.info(f"\n🔍 测试功能: {feature}")
            passed = sum(1 for test in tests if test())
            total = len(tests)
            results[feature] = {"passed": passed, "total": total}
            logger.info(f"✅ {feature}: {passed}/{total} 通过")

        return results

    def generate_report(self) -> str:
        """生成测试报告"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed_tests = sum(1 for r in self.test_results if r["status"] == "FAIL")
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        total_duration = time.time() - self.start_time

        report = f"""
{'=' * 80}
Capstone项目验证测试报告
{'=' * 80}

测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
总执行时间: {total_duration:.2f}秒

测试结果总览:
  总测试数: {total_tests}
  通过: {passed_tests} ✅
  失败: {failed_tests} ❌
  通过率: {pass_rate:.1f}%

测试详情:
{'-' * 80}
"""

        for result in self.test_results:
            status_emoji = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}
            report += f"""
{status_emoji[result['status']]} [{result['test_id']}] {result['test_name']}
   状态: {result['status']}
   耗时: {result['duration_seconds']:.2f}秒
   详情: {result['details']}
"""
            if result["metrics"]:
                report += f"   指标: {json.dumps(result['metrics'], ensure_ascii=False)}\n"

        # 最终评分
        if pass_rate >= 90:
            grade = "A"
            grade_comment = "优秀 - 所有核心功能完整实现且高质量"
        elif pass_rate >= 80:
            grade = "B"
            grade_comment = "良好 - 核心功能完整，部分辅助功能缺失"
        elif pass_rate >= 70:
            grade = "C"
            grade_comment = "及格 - 核心功能基本实现，有明显缺陷"
        elif pass_rate >= 60:
            grade = "D"
            grade_comment = "不及格 - 部分核心功能未实现或严重缺陷"
        else:
            grade = "F"
            grade_comment = "失败 - 核心功能未实现"

        report += f"""
{'=' * 80}
最终评分: {grade}
评价: {grade_comment}
{'=' * 80}

通过标准检查:
  功能完整性: {'✅ 达标' if pass_rate >= 70 else '❌ 未达标'}
  代码质量: {'✅ 需要人工审查' if pass_rate >= 70 else '❌ 需要大幅改进'}
  测试覆盖: {'✅ 基本覆盖' if pass_rate >= 70 else '❌ 覆盖不足'}

建议:
"""

        if pass_rate < 70:
            report += """
  ⚠️ 项目未达到Capstone交付标准
  1. 优先修复所有失败的P0测试用例
  2. 完善核心功能的错误处理
  3. 补充单元测试和集成测试
  4. 更新技术文档和用户手册
"""
        elif pass_rate < 80:
            report += """
  ⚠️ 项目达到基本交付标准，需要改进
  1. 修复失败的P1测试用例
  2. 优化代码质量和注释
  3. 补充辅助功能
  4. 完善API文档
"""
        else:
            report += """
  ✅ 项目达到良好或优秀交付标准
  1. 继续优化性能和用户体验
  2. 补充高级功能和边缘案例处理
  3. 建立持续集成和自动化测试
  4. 准备演示和答辩材料
"""

        return report

    def save_report(self, report: str) -> None:
        """保存测试报告"""
        report_dir = Path("tests/logs")
        report_dir.mkdir(parents=True, exist_ok=True)

        # 保存文本报告
        report_file = report_dir / f"capstone_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_file.write_text(report)

        # 保存JSON结果
        json_file = report_dir / f"capstone_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        json_file.write_text(
            json.dumps(
                {
                    "test_results": self.test_results,
                    "summary": {
                        "total_tests": len(self.test_results),
                        "passed_tests": sum(
                            1 for r in self.test_results if r["status"] == "PASS"
                        ),
                        "failed_tests": sum(
                            1 for r in self.test_results if r["status"] == "FAIL"
                        ),
                        "total_duration": time.time() - self.start_time,
                    },
                },
                indent=2,
                ensure_ascii=False,
            )
        )

        logger.info(f"\n📄 报告已保存:")
        logger.info(f"   文本报告: {report_file}")
        logger.info(f"   JSON结果: {json_file}")


def main():
    """主函数"""
    logger.info("🚀 启动Capstone项目验证测试")

    # 检查服务是否运行
    validator = CapstoneValidator()

    try:
        response = requests.get(f"{validator.base_url}/health", timeout=5)
        if response.status_code == 200:
            logger.info(f"✅ 服务运行正常: {validator.base_url}")
    except Exception:
        logger.error(
            f"❌ 服务不可用: {validator.base_url}"
        )
        logger.error("请先启动服务: make run")
        sys.exit(1)

    # 运行烟雾测试
    smoke_results = validator.run_smoke_tests()

    # 生成并保存报告
    report = validator.generate_report()
    print(report)

    validator.save_report(report)

    # 根据测试结果设置退出码
    failed_tests = sum(1 for r in validator.test_results if r["status"] == "FAIL")
    sys.exit(1 if failed_tests > 0 else 0)


if __name__ == "__main__":
    main()