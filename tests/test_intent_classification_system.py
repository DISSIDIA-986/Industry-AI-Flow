#!/usr/bin/env python3
"""
意图分类系统完整测试脚本
测试从输入预处理到Agent路由的完整工作流
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.services.intent_workflow import IntentClassificationWorkflow, WorkflowState
from backend.services.intent_classifier import IntentClassifier, QueryContext
from backend.services.context_manager import ContextManager, SessionContext
from backend.services.routing_decision import RoutingDecisionEngine
from backend.services.prompt_manager import PromptManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockLLMClient:
    """模拟LLM客户端"""

    def __init__(self):
        self.call_count = 0

    async def generate_response(self, prompt: str, **kwargs) -> str:
        """模拟LLM响应生成"""
        self.call_count += 1

        # 简单的关键词匹配逻辑
        prompt_lower = prompt.lower()

        if "知识检索" in prompt_lower or "knowledge" in prompt_lower:
            return json.dumps({
                "intent": "knowledge_retrieval",
                "confidence": 0.85,
                "reasoning": "查询包含知识检索相关关键词",
                "keywords": ["知识", "检索"],
                "context_clues": ["询问概念", "寻求信息"],
                "suggested_action": "执行语义检索",
                "uncertainty_factors": []
            }, ensure_ascii=False)

        elif "数据分析" in prompt_lower or "数据" in prompt_lower or "分析" in prompt_lower:
            return json.dumps({
                "intent": "data_analysis",
                "confidence": 0.78,
                "reasoning": "查询涉及数据处理和分析需求",
                "keywords": ["数据", "分析", "统计"],
                "context_clues": ["处理数据集", "生成洞察"],
                "suggested_action": "启动数据分析流程",
                "uncertainty_factors": ["分析类型不明确"]
            }, ensure_ascii=False)

        elif "文档" in prompt_lower or "pdf" in prompt_lower or "ocr" in prompt_lower:
            return json.dumps({
                "intent": "document_processing",
                "confidence": 0.82,
                "reasoning": "查询涉及文档处理需求",
                "keywords": ["文档", "PDF", "提取"],
                "context_clues": ["文件处理", "内容提取"],
                "suggested_action": "执行文档解析",
                "uncertainty_factors": []
            }, ensure_ascii=False)

        elif "代码" in prompt_lower or "运行" in prompt_lower or "计算" in prompt_lower:
            return json.dumps({
                "intent": "code_execution",
                "confidence": 0.79,
                "reasoning": "查询需要执行代码或计算任务",
                "keywords": ["代码", "运行", "计算"],
                "context_clues": ["程序执行", "算法实现"],
                "suggested_action": "启动代码执行环境",
                "uncertainty_factors": ["具体实现不明确"]
            }, ensure_ascii=False)

        else:
            return json.dumps({
                "intent": "knowledge_retrieval",
                "confidence": 0.65,
                "reasoning": "查询意图不明确，默认为知识检索",
                "keywords": ["查询"],
                "context_clues": ["一般性询问"],
                "suggested_action": "执行通用检索",
                "uncertainty_factors": ["意图模糊", "关键词不足"]
            }, ensure_ascii=False)


class MockPromptManager:
    """模拟Prompt管理器"""

    def __init__(self):
        self.prompts = {}

    async def get_prompt(self, name: str, category: str, **kwargs):
        """模拟获取Prompt"""
        if name == "intent_classification":
            return MockPromptInfo("mock_prompt_1"), "这是一个模拟的意图分类Prompt"
        elif name == "intent_clarification":
            return MockPromptInfo("mock_prompt_2"), "这是一个模拟的澄清Prompt"
        else:
            return MockPromptInfo("mock_prompt_default"), "这是一个默认Prompt"

    async def create_prompt(self, **kwargs):
        """模拟创建Prompt"""
        return MockPromptInfo(f"mock_prompt_{len(self.prompts) + 1}")


class MockPromptInfo:
    """模拟Prompt信息"""

    def __init__(self, id: str):
        self.id = id
        self.name = "mock_prompt"
        self.category = "Mock"
        self.version = "1.0.0"


async def create_test_workflow() -> IntentClassificationWorkflow:
    """创建测试工作流"""
    logger.info("创建测试工作流...")

    # 创建模拟服务
    llm_client = MockLLMClient()
    prompt_manager = MockPromptManager()
    context_manager = ContextManager(storage_backend="memory")
    intent_classifier = IntentClassifier(llm_client, prompt_manager)
    routing_engine = RoutingDecisionEngine()

    # 创建工作流
    workflow = IntentClassificationWorkflow(
        intent_classifier=intent_classifier,
        context_manager=context_manager,
        routing_engine=routing_engine,
        prompt_manager=prompt_manager
    )

    logger.info("测试工作流创建完成")
    return workflow


class IntentClassificationTester:
    """意图分类系统测试器"""

    def __init__(self, workflow: IntentClassificationWorkflow):
        self.workflow = workflow
        self.test_results = []

    async def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """运行单个测试用例"""
        logger.info(f"执行测试用例: {test_case['name']}")

        start_time = time.time()

        try:
            # 运行工作流
            result = await self.workflow.run_workflow(
                query=test_case["query"],
                session_id=test_case.get("session_id", f"test_session_{int(time.time())}"),
                user_id=test_case.get("user_id", "test_user"),
                thread_id=test_case.get("thread_id")
            )

            processing_time = (time.time() - start_time) * 1000

            # 评估结果
            evaluation = self._evaluate_result(result, test_case)

            test_result = {
                "test_case": test_case,
                "result": result,
                "evaluation": evaluation,
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"测试用例完成: {test_case['name']}, 成功: {evaluation['passed']}")
            return test_result

        except Exception as e:
            logger.error(f"测试用例失败: {test_case['name']}, 错误: {str(e)}")

            return {
                "test_case": test_case,
                "result": {"success": False, "error": str(e)},
                "evaluation": {"passed": False, "error": str(e)},
                "processing_time_ms": (time.time() - start_time) * 1000,
                "timestamp": datetime.now().isoformat()
            }

    def _evaluate_result(self, result: Dict[str, Any], test_case: Dict[str, Any]) -> Dict[str, Any]:
        """评估测试结果"""
        evaluation = {"passed": True, "issues": []}

        # 检查基本成功状态
        if not result.get("success", False):
            evaluation["passed"] = False
            evaluation["issues"].append(f"工作流执行失败: {result.get('error', '未知错误')}")

        # 检查预期的意图
        expected_intent = test_case.get("expected_intent")
        if expected_intent:
            actual_intent = result.get("intent_result", {}).get("intent")
            if actual_intent != expected_intent:
                evaluation["passed"] = False
                evaluation["issues"].append(f"意图不匹配: 期望 {expected_intent}, 实际 {actual_intent}")

        # 检查置信度阈值
        min_confidence = test_case.get("min_confidence", 0.5)
        actual_confidence = result.get("intent_result", {}).get("confidence", 0.0)
        if actual_confidence < min_confidence:
            evaluation["passed"] = False
            evaluation["issues"].append(f"置信度过低: 期望 >= {min_confidence}, 实际 {actual_confidence}")

        # 检查是否需要澄清
        expected_clarification = test_case.get("expect_clarification", False)
        actual_clarification = result.get("clarification_needed", False)
        if actual_clarification != expected_clarification:
            if not expected_clarification:
                evaluation["issues"].append(f"意外需要澄清: 查询 '{test_case['query']}'")

        # 检查Agent响应
        if not result.get("agent_response"):
            evaluation["passed"] = False
            evaluation["issues"].append("缺少Agent响应")

        return evaluation

    async def run_test_suite(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """运行完整测试套件"""
        logger.info(f"开始运行测试套件，共 {len(test_cases)} 个测试用例")

        start_time = time.time()
        passed_tests = 0
        failed_tests = 0

        for test_case in test_cases:
            result = await self.run_single_test(test_case)
            self.test_results.append(result)

            if result["evaluation"]["passed"]:
                passed_tests += 1
            else:
                failed_tests += 1

        total_time = time.time() - start_time

        # 生成测试报告
        report = {
            "summary": {
                "total_tests": len(test_cases),
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests / len(test_cases) if test_cases else 0.0,
                "total_time_seconds": total_time,
                "average_time_per_test": total_time / len(test_cases) if test_cases else 0.0
            },
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"测试套件完成: {passed_tests}/{len(test_cases)} 通过")
        return report


def create_test_cases() -> List[Dict[str, Any]]:
    """创建测试用例"""
    test_cases = [
        {
            "name": "知识检索 - 概念查询",
            "query": "什么是机器学习？请详细解释基本概念。",
            "expected_intent": "knowledge_retrieval",
            "min_confidence": 0.7,
            "expect_clarification": False
        },
        {
            "name": "数据分析 - 统计需求",
            "query": "帮我分析这份数据，生成统计报告和可视化图表。",
            "expected_intent": "data_analysis",
            "min_confidence": 0.7,
            "expect_clarification": False
        },
        {
            "name": "文档处理 - PDF提取",
            "query": "我有一个PDF文件，需要提取其中的文字内容。",
            "expected_intent": "document_processing",
            "min_confidence": 0.7,
            "expect_clarification": False
        },
        {
            "name": "代码执行 - 计算任务",
            "query": "帮我运行这个Python代码来计算数据结果。",
            "expected_intent": "code_execution",
            "min_confidence": 0.7,
            "expect_clarification": False
        },
        {
            "name": "模糊查询 - 低置信度",
            "query": "你好",
            "expected_intent": "knowledge_retrieval",  # 默认意图
            "min_confidence": 0.4,  # 允许较低置信度
            "expect_clarification": True  # 期望需要澄清
        },
        {
            "name": "复合查询 - 数据分析",
            "query": "请分析上传的数据集并创建可视化展示趋势变化。",
            "expected_intent": "data_analysis",
            "min_confidence": 0.7,
            "expect_clarification": False
        },
        {
            "name": "技术文档 - 知识检索",
            "query": "解释一下深度学习中的反向传播算法原理。",
            "expected_intent": "knowledge_retrieval",
            "min_confidence": 0.7,
            "expect_clarification": False
        },
        {
            "name": "OCR需求 - 文档处理",
            "query": "这张图片里的文字怎么提取出来？",
            "expected_intent": "document_processing",
            "min_confidence": 0.6,  # 可能置信度稍低
            "expect_clarification": False
        }
    ]

    return test_cases


async def main():
    """主测试函数"""
    print("🚀 开始意图分类系统完整测试...")

    try:
        # 创建测试工作流
        workflow = await create_test_workflow()

        # 创建测试器
        tester = IntentClassificationTester(workflow)

        # 创建测试用例
        test_cases = create_test_cases()

        print(f"📋 准备执行 {len(test_cases)} 个测试用例")

        # 运行测试套件
        test_report = await tester.run_test_suite(test_cases)

        # 打印测试结果
        print_test_report(test_report)

        # 保存测试报告
        await save_test_report(test_report)

        # 返回退出码
        return 0 if test_report["summary"]["success_rate"] >= 0.8 else 1

    except Exception as e:
        logger.error(f"测试执行失败: {str(e)}")
        print(f"❌ 测试执行失败: {str(e)}")
        return 1


def print_test_report(report: Dict[str, Any]):
    """打印测试报告"""
    summary = report["summary"]

    print("\n" + "="*60)
    print("📊 意图分类系统测试报告")
    print("="*60)

    print(f"📈 测试统计:")
    print(f"   总测试数: {summary['total_tests']}")
    print(f"   通过测试: {summary['passed_tests']}")
    print(f"   失败测试: {summary['failed_tests']}")
    print(f"   成功率: {summary['success_rate']:.1%}")

    print(f"\n⏱️ 性能指标:")
    print(f"   总耗时: {summary['total_time_seconds']:.2f} 秒")
    print(f"   平均耗时: {summary['average_time_per_test']:.2f} 秒/测试")

    # 详细测试结果
    print(f"\n📋 详细测试结果:")
    for i, result in enumerate(report["test_results"], 1):
        test_case = result["test_case"]
        evaluation = result["evaluation"]

        status = "✅ 通过" if evaluation["passed"] else "❌ 失败"
        intent = result["result"].get("intent_result", {}).get("intent", "N/A")
        confidence = result["result"].get("intent_result", {}).get("confidence", 0.0)
        processing_time = result.get("processing_time_ms", 0)

        print(f"   {i}. {test_case['name']} - {status}")
        print(f"      查询: {test_case['query'][:50]}...")
        print(f"      意图: {intent} (置信度: {confidence:.2f})")
        print(f"      耗时: {processing_time:.0f}ms")

        if evaluation["issues"]:
            for issue in evaluation["issues"]:
                print(f"      ⚠️  {issue}")

    print("\n" + "="*60)


async def save_test_report(report: Dict[str, Any]):
    """保存测试报告"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intent_classification_test_report_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n💾 测试报告已保存到: {filename}")

    except Exception as e:
        logger.error(f"保存测试报告失败: {str(e)}")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)