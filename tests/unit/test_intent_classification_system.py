#!/usr/bin/env python3
"""
EN
ENAgentEN
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# ENPythonEN
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.services.context_manager import ContextManager, SessionContext
from backend.services.intent_classifier import IntentClassifier, QueryContext
from backend.services.intent_workflow import IntentClassificationWorkflow, WorkflowState
from backend.services.prompt_manager import PromptManager
from backend.services.routing_decision import RoutingDecisionEngine

# EN
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockLLMClient:
    """ENLLMEN"""

    def __init__(self):
        self.call_count = 0

    async def generate_response(self, prompt: str, **kwargs) -> str:
        """ENLLMEN"""
        self.call_count += 1

        # EN
        prompt_lower = prompt.lower()

        if "EN" in prompt_lower or "knowledge" in prompt_lower:
            return json.dumps(
                {
                    "intent": "knowledge_retrieval",
                    "confidence": 0.85,
                    "reasoning": "EN",
                    "keywords": ["EN", "EN"],
                    "context_clues": ["EN", "EN"],
                    "suggested_action": "EN",
                    "uncertainty_factors": [],
                },
                ensure_ascii=False,
            )

        elif "EN" in prompt_lower or "EN" in prompt_lower or "EN" in prompt_lower:
            return json.dumps(
                {
                    "intent": "data_analysis",
                    "confidence": 0.78,
                    "reasoning": "EN",
                    "keywords": ["EN", "EN", "EN"],
                    "context_clues": ["EN", "EN"],
                    "suggested_action": "EN",
                    "uncertainty_factors": ["EN"],
                },
                ensure_ascii=False,
            )

        elif "EN" in prompt_lower or "pdf" in prompt_lower or "ocr" in prompt_lower:
            return json.dumps(
                {
                    "intent": "document_processing",
                    "confidence": 0.82,
                    "reasoning": "EN",
                    "keywords": ["EN", "PDF", "EN"],
                    "context_clues": ["EN", "EN"],
                    "suggested_action": "EN",
                    "uncertainty_factors": [],
                },
                ensure_ascii=False,
            )

        elif "EN" in prompt_lower or "EN" in prompt_lower or "EN" in prompt_lower:
            return json.dumps(
                {
                    "intent": "code_execution",
                    "confidence": 0.79,
                    "reasoning": "EN",
                    "keywords": ["EN", "EN", "EN"],
                    "context_clues": ["EN", "EN"],
                    "suggested_action": "EN",
                    "uncertainty_factors": ["EN"],
                },
                ensure_ascii=False,
            )

        else:
            return json.dumps(
                {
                    "intent": "knowledge_retrieval",
                    "confidence": 0.65,
                    "reasoning": "EN,EN",
                    "keywords": ["EN"],
                    "context_clues": ["EN"],
                    "suggested_action": "EN",
                    "uncertainty_factors": ["EN", "EN"],
                },
                ensure_ascii=False,
            )


class MockPromptManager:
    """ENPromptEN"""

    def __init__(self):
        self.prompts = {}

    async def get_prompt(self, name: str, category: str, **kwargs):
        """ENPrompt"""
        if name == "intent_classification":
            return MockPromptInfo("mock_prompt_1"), "ENPrompt"
        elif name == "intent_clarification":
            return MockPromptInfo("mock_prompt_2"), "ENPrompt"
        else:
            return MockPromptInfo("mock_prompt_default"), "ENPrompt"

    async def create_prompt(self, **kwargs):
        """ENPrompt"""
        return MockPromptInfo(f"mock_prompt_{len(self.prompts) + 1}")


class MockPromptInfo:
    """ENPromptEN"""

    def __init__(self, id: str):
        self.id = id
        self.name = "mock_prompt"
        self.category = "Mock"
        self.version = "1.0.0"


async def create_test_workflow() -> IntentClassificationWorkflow:
    """EN"""
    logger.info("EN...")

    # EN
    llm_client = MockLLMClient()
    prompt_manager = MockPromptManager()
    context_manager = ContextManager(storage_backend="memory")
    intent_classifier = IntentClassifier(llm_client, prompt_manager)
    routing_engine = RoutingDecisionEngine()

    # EN
    workflow = IntentClassificationWorkflow(
        intent_classifier=intent_classifier,
        context_manager=context_manager,
        routing_engine=routing_engine,
        prompt_manager=prompt_manager,
    )

    logger.info("EN")
    return workflow


class IntentClassificationTester:
    """EN"""

    def __init__(self, workflow: IntentClassificationWorkflow):
        self.workflow = workflow
        self.test_results = []

    async def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """EN"""
        logger.info(f"EN: {test_case['name']}")

        start_time = time.time()

        try:
            # EN
            result = await self.workflow.run_workflow(
                query=test_case["query"],
                session_id=test_case.get(
                    "session_id", f"test_session_{int(time.time())}"
                ),
                user_id=test_case.get("user_id", "test_user"),
                thread_id=test_case.get("thread_id"),
            )

            processing_time = (time.time() - start_time) * 1000

            # EN
            evaluation = self._evaluate_result(result, test_case)

            test_result = {
                "test_case": test_case,
                "result": result,
                "evaluation": evaluation,
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"EN: {test_case['name']}, EN: {evaluation['passed']}")
            return test_result

        except Exception as e:
            logger.error(f"EN: {test_case['name']}, EN: {str(e)}")

            return {
                "test_case": test_case,
                "result": {"success": False, "error": str(e)},
                "evaluation": {"passed": False, "error": str(e)},
                "processing_time_ms": (time.time() - start_time) * 1000,
                "timestamp": datetime.now().isoformat(),
            }

    def _evaluate_result(
        self, result: Dict[str, Any], test_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        """EN"""
        evaluation = {"passed": True, "issues": []}

        # EN
        if not result.get("success", False):
            evaluation["passed"] = False
            evaluation["issues"].append(f"EN: {result.get('error', 'EN')}")

        # EN
        expected_intent = test_case.get("expected_intent")
        if expected_intent:
            actual_intent = result.get("intent_result", {}).get("intent")
            if actual_intent != expected_intent:
                evaluation["passed"] = False
                evaluation["issues"].append(
                    f"EN: EN {expected_intent}, EN {actual_intent}"
                )

        # EN
        min_confidence = test_case.get("min_confidence", 0.5)
        actual_confidence = result.get("intent_result", {}).get("confidence", 0.0)
        if actual_confidence < min_confidence:
            evaluation["passed"] = False
            evaluation["issues"].append(
                f"EN: EN >= {min_confidence}, EN {actual_confidence}"
            )

        # EN
        expected_clarification = test_case.get("expect_clarification", False)
        actual_clarification = result.get("clarification_needed", False)
        if actual_clarification != expected_clarification:
            if not expected_clarification:
                evaluation["issues"].append(f"EN: EN '{test_case['query']}'")

        # ENAgentEN
        if not result.get("agent_response"):
            evaluation["passed"] = False
            evaluation["issues"].append("ENAgentEN")

        return evaluation

    async def run_test_suite(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """EN"""
        logger.info(f"EN,EN {len(test_cases)} EN")

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

        # EN
        report = {
            "summary": {
                "total_tests": len(test_cases),
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests / len(test_cases) if test_cases else 0.0,
                "total_time_seconds": total_time,
                "average_time_per_test": total_time / len(test_cases)
                if test_cases
                else 0.0,
            },
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"EN: {passed_tests}/{len(test_cases)} EN")
        return report


def create_test_cases() -> List[Dict[str, Any]]:
    """EN"""
    test_cases = [
        {
            "name": "EN - EN",
            "query": "EN?EN.",
            "expected_intent": "knowledge_retrieval",
            "min_confidence": 0.7,
            "expect_clarification": False,
        },
        {
            "name": "EN - EN",
            "query": "EN,EN.",
            "expected_intent": "data_analysis",
            "min_confidence": 0.7,
            "expect_clarification": False,
        },
        {
            "name": "EN - PDFEN",
            "query": "ENPDFEN,EN.",
            "expected_intent": "document_processing",
            "min_confidence": 0.7,
            "expect_clarification": False,
        },
        {
            "name": "EN - EN",
            "query": "ENPythonEN.",
            "expected_intent": "code_execution",
            "min_confidence": 0.7,
            "expect_clarification": False,
        },
        {
            "name": "EN - EN",
            "query": "EN",
            "expected_intent": "knowledge_retrieval",  # EN
            "min_confidence": 0.4,  # EN
            "expect_clarification": True,  # EN
        },
        {
            "name": "EN - EN",
            "query": "EN.",
            "expected_intent": "data_analysis",
            "min_confidence": 0.7,
            "expect_clarification": False,
        },
        {
            "name": "EN - EN",
            "query": "EN.",
            "expected_intent": "knowledge_retrieval",
            "min_confidence": 0.7,
            "expect_clarification": False,
        },
        {
            "name": "OCREN - EN",
            "query": "EN?",
            "expected_intent": "document_processing",
            "min_confidence": 0.6,  # EN
            "expect_clarification": False,
        },
    ]

    return test_cases


async def main():
    """EN"""
    print("🚀 EN...")

    try:
        # EN
        workflow = await create_test_workflow()

        # EN
        tester = IntentClassificationTester(workflow)

        # EN
        test_cases = create_test_cases()

        print(f"📋 EN {len(test_cases)} EN")

        # EN
        test_report = await tester.run_test_suite(test_cases)

        # EN
        print_test_report(test_report)

        # EN
        await save_test_report(test_report)

        # EN
        return 0 if test_report["summary"]["success_rate"] >= 0.8 else 1

    except Exception as e:
        logger.error(f"EN: {str(e)}")
        print(f"❌ EN: {str(e)}")
        return 1


def print_test_report(report: Dict[str, Any]):
    """EN"""
    summary = report["summary"]

    print("\n" + "=" * 60)
    print("📊 EN")
    print("=" * 60)

    print(f"📈 EN:")
    print(f"   EN: {summary['total_tests']}")
    print(f"   EN: {summary['passed_tests']}")
    print(f"   EN: {summary['failed_tests']}")
    print(f"   EN: {summary['success_rate']:.1%}")

    print(f"\n⏱️ EN:")
    print(f"   EN: {summary['total_time_seconds']:.2f} EN")
    print(f"   EN: {summary['average_time_per_test']:.2f} EN/EN")

    # EN
    print(f"\n📋 EN:")
    for i, result in enumerate(report["test_results"], 1):
        test_case = result["test_case"]
        evaluation = result["evaluation"]

        status = "✅ EN" if evaluation["passed"] else "❌ EN"
        intent = result["result"].get("intent_result", {}).get("intent", "N/A")
        confidence = result["result"].get("intent_result", {}).get("confidence", 0.0)
        processing_time = result.get("processing_time_ms", 0)

        print(f"   {i}. {test_case['name']} - {status}")
        print(f"      EN: {test_case['query'][:50]}...")
        print(f"      EN: {intent} (EN: {confidence:.2f})")
        print(f"      EN: {processing_time:.0f}ms")

        if evaluation["issues"]:
            for issue in evaluation["issues"]:
                print(f"      ⚠️  {issue}")

    print("\n" + "=" * 60)


async def save_test_report(report: Dict[str, Any]):
    """EN"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intent_classification_test_report_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n💾 EN: {filename}")

    except Exception as e:
        logger.error(f"EN: {str(e)}")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
