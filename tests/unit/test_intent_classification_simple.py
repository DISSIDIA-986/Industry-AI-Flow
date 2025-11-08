#!/usr/bin/env python3
"""
意图分类系统简化测试脚本
测试核心分类逻辑和路由决策（不依赖LangChain）
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleIntentClassifier:
    """简化的意图分类器"""

    def __init__(self):
        self.intent_patterns = {
            "knowledge_retrieval": ["什么是", "如何", "解释", "定义", "概念", "原理", "what is", "how to"],
            "data_analysis": ["分析", "数据", "统计", "图表", "可视化", "analyze", "statistics", "visualization"],
            "document_processing": ["文档", "PDF", "提取", "OCR", "扫描", "document", "extract", "scan"],
            "code_execution": ["运行", "代码", "计算", "执行", "编程", "run", "code", "execute", "compute"]
        }

    async def classify_intent(self, query: str) -> Dict[str, Any]:
        """分类意图"""
        query_lower = query.lower()

        # 计算每个意图的匹配分数
        intent_scores = {}
        for intent, keywords in self.intent_patterns.items():
            score = 0
            for keyword in keywords:
                if keyword in query_lower:
                    score += 1
            intent_scores[intent] = score

        # 选择得分最高的意图
        if max(intent_scores.values()) == 0:
            # 没有匹配的关键词，返回默认意图
            return {
                "intent": "knowledge_retrieval",
                "confidence": 0.4,
                "reasoning": "没有明确的关键词匹配，默认为知识检索",
                "keywords": [],
                "context_clues": ["一般性查询"],
                "suggested_action": "执行通用检索",
                "uncertainty_factors": ["意图模糊"]
            }

        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        max_score = best_intent[1]

        # 基于匹配关键词数量计算置信度
        confidence = min(0.9, 0.4 + (max_score * 0.15))

        return {
            "intent": best_intent[0],
            "confidence": confidence,
            "reasoning": f"基于关键词匹配选择意图 {best_intent[0]}",
            "keywords": [kw for kw in self.intent_patterns[best_intent[0]] if kw in query_lower],
            "context_clues": [best_intent[0]],
            "suggested_action": f"路由到{best_intent[0]}处理器",
            "uncertainty_factors": [] if confidence > 0.7 else ["关键词较少"]
        }


class SimpleRoutingEngine:
    """简化的路由决策引擎"""

    def __init__(self):
        self.agent_mapping = {
            "knowledge_retrieval": "rag_agent",
            "data_analysis": "data_analysis_agent",
            "document_processing": "document_processing_agent",
            "code_execution": "code_execution_agent"
        }

    async def make_routing_decision(self, intent_result: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """做出路由决策"""
        intent = intent_result.get("intent")
        confidence = intent_result.get("confidence", 0.0)

        selected_agent = self.agent_mapping.get(intent, "general_agent")

        # 置信度评估
        if confidence >= 0.8:
            routing_path = "direct"
            requires_clarification = False
        elif confidence <= 0.5:
            routing_path = "clarification"
            requires_clarification = True
        else:
            routing_path = "verified"
            requires_clarification = False

        return {
            "selected_agent": selected_agent,
            "routing_path": routing_path,
            "confidence": confidence,
            "reasoning": f"基于意图'{intent}'和置信度{confidence:.2f}路由到{selected_agent}",
            "requires_clarification": requires_clarification,
            "estimated_processing_time": self._estimate_processing_time(selected_agent),
            "clarification_questions": self._generate_clarification_questions(intent) if requires_clarification else []
        }

    def _estimate_processing_time(self, agent: str) -> int:
        """估算处理时间"""
        time_mapping = {
            "rag_agent": 30,
            "data_analysis_agent": 120,
            "document_processing_agent": 60,
            "code_execution_agent": 90,
            "general_agent": 45
        }
        return time_mapping.get(agent, 60)

    def _generate_clarification_questions(self, intent: str) -> List[str]:
        """生成澄清问题"""
        question_mapping = {
            "knowledge_retrieval": [
                "您是想了解具体的概念解释，还是查找特定信息？",
                "您希望我帮您检索哪个领域的知识？"
            ],
            "data_analysis": [
                "您希望进行哪种类型的数据分析？是统计分析还是可视化？",
                "您是否已经上传了需要分析的数据？"
            ],
            "document_processing": [
                "您需要处理什么类型的文档？是PDF还是图片？",
                "您希望从文档中提取什么内容？"
            ],
            "code_execution": [
                "您希望运行什么类型的代码？",
                "您的具体计算需求是什么？"
            ]
        }
        return question_mapping.get(intent, ["请提供更多详细信息"])


class SimpleWorkflowTester:
    """简化的工作流测试器"""

    def __init__(self):
        self.intent_classifier = SimpleIntentClassifier()
        self.routing_engine = SimpleRoutingEngine()

    async def process_query(self, query: str) -> Dict[str, Any]:
        """处理单个查询"""
        start_time = time.time()

        # 意图分类
        intent_result = await self.intent_classifier.classify_intent(query)

        # 路由决策
        routing_decision = await self.routing_engine.make_routing_decision(intent_result)

        # 模拟Agent响应
        agent_response = self._generate_agent_response(routing_decision["selected_agent"], query)

        processing_time = (time.time() - start_time) * 1000

        return {
            "query": query,
            "intent_result": intent_result,
            "routing_decision": routing_decision,
            "agent_response": agent_response,
            "processing_time_ms": processing_time,
            "success": True
        }

    def _generate_agent_response(self, agent: str, query: str) -> str:
        """生成模拟Agent响应"""
        response_mapping = {
            "rag_agent": f"根据您的查询'{query}'，我为您检索到相关的知识信息...",
            "data_analysis_agent": f"针对您的数据分析需求，我建议采用以下方法进行分析...",
            "document_processing_agent": f"关于文档处理，我可以帮您提取文本内容、识别表格等...",
            "code_execution_agent": f"我将帮您执行相关代码任务来解决您的问题...",
            "general_agent": f"我理解您的需求是'{query}'，让我为您提供有用的建议..."
        }
        return response_mapping.get(agent, "我正在处理您的请求...")

    def _evaluate_result(self, test_case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """评估测试结果"""
        evaluation = {"passed": True, "issues": []}

        # 检查预期的意图
        if "expected_intent" in test_case:
            actual_intent = result["intent_result"]["intent"]
            if actual_intent != test_case["expected_intent"]:
                evaluation["passed"] = False
                evaluation["issues"].append(f"意图不匹配: 期望 {test_case['expected_intent']}, 实际 {actual_intent}")

        # 检查置信度阈值
        min_confidence = test_case.get("min_confidence", 0.5)
        actual_confidence = result["intent_result"]["confidence"]
        if actual_confidence < min_confidence:
            evaluation["passed"] = False
            evaluation["issues"].append(f"置信度过低: 期望 >= {min_confidence}, 实际 {actual_confidence:.2f}")

        # 检查澄清需求
        if "expect_clarification" in test_case:
            actual_clarification = result["routing_decision"]["requires_clarification"]
            if actual_clarification != test_case["expect_clarification"]:
                if not test_case["expect_clarification"]:
                    evaluation["issues"].append(f"意外需要澄清: {test_case['query']}")
                else:
                    evaluation["issues"].append(f"期望需要澄清但未触发: {test_case['query']}")

        return evaluation

    async def run_test_suite(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """运行测试套件"""
        logger.info(f"开始运行 {len(test_cases)} 个测试用例")

        start_time = time.time()
        test_results = []
        passed_tests = 0

        for test_case in test_cases:
            logger.info(f"执行测试: {test_case['name']}")

            try:
                result = await self.process_query(test_case["query"])
                evaluation = self._evaluate_result(test_case, result)

                test_result = {
                    "test_case": test_case,
                    "result": result,
                    "evaluation": evaluation,
                    "timestamp": datetime.now().isoformat()
                }

                test_results.append(test_result)

                if evaluation["passed"]:
                    passed_tests += 1
                    logger.info(f"✅ 测试通过: {test_case['name']}")
                else:
                    logger.warning(f"❌ 测试失败: {test_case['name']}")
                    for issue in evaluation["issues"]:
                        logger.warning(f"   - {issue}")

            except Exception as e:
                logger.error(f"测试异常: {test_case['name']}, 错误: {str(e)}")
                test_results.append({
                    "test_case": test_case,
                    "result": {"success": False, "error": str(e)},
                    "evaluation": {"passed": False, "error": str(e)},
                    "timestamp": datetime.now().isoformat()
                })

        total_time = time.time() - start_time

        return {
            "summary": {
                "total_tests": len(test_cases),
                "passed_tests": passed_tests,
                "failed_tests": len(test_cases) - passed_tests,
                "success_rate": passed_tests / len(test_cases) if test_cases else 0.0,
                "total_time_seconds": total_time
            },
            "test_results": test_results,
            "timestamp": datetime.now().isoformat()
        }


def create_test_cases() -> List[Dict[str, Any]]:
    """创建测试用例"""
    return [
        {
            "name": "知识检索 - 概念查询",
            "query": "什么是机器学习？请详细解释基本概念。",
            "expected_intent": "knowledge_retrieval",
            "min_confidence": 0.6,
            "expect_clarification": False
        },
        {
            "name": "数据分析 - 统计需求",
            "query": "帮我分析这份数据，生成统计报告和可视化图表。",
            "expected_intent": "data_analysis",
            "min_confidence": 0.6,
            "expect_clarification": False
        },
        {
            "name": "文档处理 - PDF提取",
            "query": "我有一个PDF文件，需要提取其中的文字内容。",
            "expected_intent": "document_processing",
            "min_confidence": 0.6,
            "expect_clarification": False
        },
        {
            "name": "代码执行 - 计算任务",
            "query": "帮我运行这个Python代码来计算数据结果。",
            "expected_intent": "code_execution",
            "min_confidence": 0.6,
            "expect_clarification": False
        },
        {
            "name": "模糊查询 - 低置信度",
            "query": "你好，能帮我吗？",
            "expected_intent": "knowledge_retrieval",  # 默认意图
            "min_confidence": 0.3,  # 允许较低置信度
            "expect_clarification": True  # 期望需要澄清
        },
        {
            "name": "复合查询 - 数据分析",
            "query": "请分析上传的数据集并创建可视化展示趋势变化。",
            "expected_intent": "data_analysis",
            "min_confidence": 0.6,
            "expect_clarification": False
        },
        {
            "name": "英文查询 - 知识检索",
            "query": "What is artificial intelligence?",
            "expected_intent": "knowledge_retrieval",
            "min_confidence": 0.6,
            "expect_clarification": False
        },
        {
            "name": "模糊技术查询",
            "query": "我想处理一些东西",
            "expected_intent": "knowledge_retrieval",
            "min_confidence": 0.3,
            "expect_clarification": True
        }
    ]


def print_test_report(report: Dict[str, Any]):
    """打印测试报告"""
    summary = report["summary"]

    print("\n" + "="*60)
    print("🧠 意图分类系统测试报告")
    print("="*60)

    print(f"📊 测试统计:")
    print(f"   总测试数: {summary['total_tests']}")
    print(f"   通过测试: {summary['passed_tests']}")
    print(f"   失败测试: {summary['failed_tests']}")
    print(f"   成功率: {summary['success_rate']:.1%}")
    print(f"   总耗时: {summary['total_time_seconds']:.2f} 秒")

    print(f"\n📋 详细测试结果:")
    for i, test_result in enumerate(report["test_results"], 1):
        test_case = test_result["test_case"]
        evaluation = test_result["evaluation"]
        result = test_result.get("result", {})

        status = "✅ 通过" if evaluation["passed"] else "❌ 失败"

        if result.get("success"):
            intent = result.get("intent_result", {}).get("intent", "N/A")
            confidence = result.get("intent_result", {}).get("confidence", 0.0)
            agent = result.get("routing_decision", {}).get("selected_agent", "N/A")
            processing_time = result.get("processing_time_ms", 0)

            print(f"   {i}. {test_case['name']} - {status}")
            print(f"      查询: {test_case['query'][:50]}...")
            print(f"      意图: {intent} (置信度: {confidence:.2f})")
            print(f"      路由: {agent}")
            print(f"      耗时: {processing_time:.0f}ms")
        else:
            print(f"   {i}. {test_case['name']} - {status}")
            print(f"      错误: {result.get('error', '未知错误')}")

        if evaluation.get("issues"):
            for issue in evaluation["issues"]:
                print(f"      ⚠️  {issue}")

    print("\n" + "="*60)


async def main():
    """主测试函数"""
    print("🚀 开始意图分类系统测试...")

    try:
        # 创建测试器
        tester = SimpleWorkflowTester()

        # 创建测试用例
        test_cases = create_test_cases()

        print(f"📋 准备执行 {len(test_cases)} 个测试用例")

        # 运行测试套件
        test_report = await tester.run_test_suite(test_cases)

        # 打印测试报告
        print_test_report(test_report)

        # 保存测试报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intent_classification_test_report_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(test_report, f, ensure_ascii=False, indent=2)

        print(f"\n💾 测试报告已保存到: {filename}")

        # 返回退出码
        success_rate = test_report["summary"]["success_rate"]
        return 0 if success_rate >= 0.75 else 1

    except Exception as e:
        logger.error(f"测试执行失败: {str(e)}")
        print(f"❌ 测试执行失败: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)