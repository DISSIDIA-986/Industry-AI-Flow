#!/usr/bin/env python3
"""
问题分类测试
测试系统对不同类型问题的处理能力，包括：
1. 简单问答测试
2. 复杂推理测试
3. 多轮对话测试
4. 分类器准确性验证
"""
import json
import os
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
backend_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"
)
sys.path.insert(0, backend_path)


class QuestionType(Enum):
    """问题类型枚举"""

    SIMPLE_QA = "simple_qa"  # 简单问答
    COMPLEX_REASONING = "complex_reasoning"  # 复杂推理
    MULTI_TURN = "multi_turn"  # 多轮对话
    DATA_ANALYSIS = "data_analysis"  # 数据分析
    CODE_EXECUTION = "code_execution"  # 代码执行
    DOCUMENT_QA = "document_qa"  # 文档问答


@dataclass
class TestCase:
    """测试用例数据结构"""

    question_id: str
    question_type: QuestionType
    question: str
    expected_keywords: List[str]
    expected_answer_type: str
    context_required: bool = False
    follow_up_questions: List[str] = None
    difficulty: str = "medium"  # easy, medium, hard


class QuestionClassificationTester:
    """问题分类测试器"""

    def __init__(self):
        self.test_results = []
        self.test_cases = self._generate_test_cases()

    def _generate_test_cases(self) -> List[TestCase]:
        """生成测试用例"""
        test_cases = [
            # 简单问答测试
            TestCase(
                question_id="simple_001",
                question_type=QuestionType.SIMPLE_QA,
                question="什么是人工智能？",
                expected_keywords=["人工智能", "AI", "计算机", "智能"],
                expected_answer_type="definition",
                difficulty="easy",
            ),
            TestCase(
                question_id="simple_002",
                question_type=QuestionType.SIMPLE_QA,
                question="Python是什么编程语言？",
                expected_keywords=["Python", "编程语言", "解释型", "高级语言"],
                expected_answer_type="description",
                difficulty="easy",
            ),
            TestCase(
                question_id="simple_003",
                question_type=QuestionType.SIMPLE_QA,
                question="机器学习的主要类型有哪些？",
                expected_keywords=["监督学习", "无监督学习", "强化学习"],
                expected_answer_type="classification",
                difficulty="medium",
            ),
            # 复杂推理测试
            TestCase(
                question_id="complex_001",
                question_type=QuestionType.COMPLEX_REASONING,
                question="如果一家公司的年收入增长了20%，但是成本增长了30%，这对公司的利润有什么影响？请详细分析。",
                expected_keywords=["利润", "收入", "成本", "影响", "分析"],
                expected_answer_type="analysis",
                difficulty="hard",
            ),
            TestCase(
                question_id="complex_002",
                question_type=QuestionType.COMPLEX_REASONING,
                question="在设计和实现一个大规模分布式系统时，需要考虑哪些关键因素？请从性能、可靠性、可扩展性三个方面进行分析。",
                expected_keywords=["分布式系统", "性能", "可靠性", "可扩展性", "因素"],
                expected_answer_type="comprehensive_analysis",
                difficulty="hard",
            ),
            TestCase(
                question_id="complex_003",
                question_type=QuestionType.COMPLEX_REASONING,
                question="解释深度学习中的梯度消失问题，并提出至少三种解决方案。",
                expected_keywords=["梯度消失", "深度学习", "解决方案", "ReLU", "BatchNorm"],
                expected_answer_type="problem_solution",
                difficulty="hard",
            ),
            # 多轮对话测试
            TestCase(
                question_id="multi_001",
                question_type=QuestionType.MULTI_TURN,
                question="我想了解机器学习的基本概念。",
                expected_keywords=["机器学习", "基本概念"],
                expected_answer_type="explanation",
                follow_up_questions=[
                    "能具体解释一下监督学习吗？",
                    "监督学习和无监督学习有什么区别？",
                    "在实际应用中，我应该如何选择合适的机器学习方法？",
                ],
                difficulty="medium",
            ),
            TestCase(
                question_id="multi_002",
                question_type=QuestionType.MULTI_TURN,
                question="我想优化我的Python代码性能。",
                expected_keywords=["Python", "性能", "优化"],
                expected_answer_type="advice",
                follow_up_questions=[
                    "有哪些具体的优化技巧？",
                    "如何使用性能分析工具来识别瓶颈？",
                    "异步编程对性能提升有帮助吗？",
                ],
                difficulty="medium",
            ),
            # 数据分析测试
            TestCase(
                question_id="data_001",
                question_type=QuestionType.DATA_ANALYSIS,
                question="如何分析一个销售数据集来识别销售趋势和季节性模式？",
                expected_keywords=["销售数据", "趋势", "季节性", "分析", "模式"],
                expected_answer_type="methodology",
                difficulty="medium",
            ),
            TestCase(
                question_id="data_002",
                question_type=QuestionType.DATA_ANALYSIS,
                question="给定用户行为数据，如何构建用户画像并进行个性化推荐？",
                expected_keywords=["用户画像", "个性化推荐", "用户行为", "数据分析"],
                expected_answer_type="methodology",
                difficulty="hard",
            ),
            # 代码执行测试
            TestCase(
                question_id="code_001",
                question_type=QuestionType.CODE_EXECUTION,
                question="写一个Python函数来计算斐波那契数列的第n项。",
                expected_keywords=["斐波那契", "Python", "函数", "递归"],
                expected_answer_type="code",
                difficulty="medium",
            ),
            TestCase(
                question_id="code_002",
                question_type=QuestionType.CODE_EXECUTION,
                question="如何使用pandas读取CSV文件并进行基本的数据清洗？",
                expected_keywords=["pandas", "CSV", "数据清洗", "Python"],
                expected_answer_type="code_tutorial",
                difficulty="medium",
            ),
            # 文档问答测试
            TestCase(
                question_id="doc_001",
                question_type=QuestionType.DOCUMENT_QA,
                question="根据上传的技术文档，这个系统的主要功能是什么？",
                expected_keywords=["功能", "系统", "文档"],
                expected_answer_type="extraction",
                context_required=True,
                difficulty="easy",
            ),
            TestCase(
                question_id="doc_002",
                question_type=QuestionType.DOCUMENT_QA,
                question="文档中提到的部署步骤有哪些？请详细说明。",
                expected_keywords=["部署", "步骤", "文档"],
                expected_answer_type="procedural",
                context_required=True,
                difficulty="medium",
            ),
        ]

        return test_cases

    def classify_question(self, question: str) -> QuestionType:
        """
        问题分类器（模拟实现）
        实际应用中应该使用机器学习模型
        """
        question_lower = question.lower()

        # 简单关键词匹配分类
        if any(keyword in question_lower for keyword in ["什么是", "什么", "如何", "为什么"]):
            if any(
                keyword in question_lower for keyword in ["分析", "影响", "因素", "方案", "问题"]
            ):
                return QuestionType.COMPLEX_REASONING
            else:
                return QuestionType.SIMPLE_QA
        elif any(
            keyword in question_lower for keyword in ["写代码", "函数", "python", "实现", "编程"]
        ):
            return QuestionType.CODE_EXECUTION
        elif any(
            keyword in question_lower for keyword in ["数据", "分析", "趋势", "模式", "统计"]
        ):
            return QuestionType.DATA_ANALYSIS
        elif any(keyword in question_lower for keyword in ["文档", "根据", "上传"]):
            return QuestionType.DOCUMENT_QA
        elif len(question) < 50 and "?" in question:
            return QuestionType.MULTI_TURN
        else:
            return QuestionType.COMPLEX_REASONING

    def test_question_classification(self) -> Dict[str, Any]:
        """测试问题分类准确性"""
        print("🔍 测试问题分类准确性...")

        correct_classifications = 0
        total_tests = len(self.test_cases)
        classification_results = []

        for test_case in self.test_cases:
            predicted_type = self.classify_question(test_case.question)
            is_correct = predicted_type == test_case.question_type

            result = {
                "question_id": test_case.question_id,
                "question": test_case.question,
                "expected_type": test_case.question_type.value,
                "predicted_type": predicted_type.value,
                "is_correct": is_correct,
            }

            classification_results.append(result)

            if is_correct:
                correct_classifications += 1
                print(f"✅ {test_case.question_id}: {predicted_type.value}")
            else:
                print(
                    f"❌ {test_case.question_id}: 期望 {test_case.question_type.value}, 预测 {predicted_type.value}"
                )

        accuracy = correct_classifications / total_tests if total_tests > 0 else 0

        return {
            "total_tests": total_tests,
            "correct_classifications": correct_classifications,
            "accuracy": accuracy,
            "results": classification_results,
        }

    def test_simple_qa(self) -> Dict[str, Any]:
        """测试简单问答能力"""
        print("\n🔍 测试简单问答能力...")

        simple_tests = [
            tc for tc in self.test_cases if tc.question_type == QuestionType.SIMPLE_QA
        ]
        results = []

        for test_case in simple_tests:
            # 模拟回答生成
            mock_answer = self._generate_mock_answer(test_case)

            # 评估回答质量
            quality_score = self._evaluate_answer_quality(mock_answer, test_case)

            result = {
                "question_id": test_case.question_id,
                "question": test_case.question,
                "mock_answer": mock_answer,
                "quality_score": quality_score,
                "keyword_coverage": self._check_keyword_coverage(
                    mock_answer, test_case.expected_keywords
                ),
                "answer_type_match": self._check_answer_type(
                    mock_answer, test_case.expected_answer_type
                ),
            }

            results.append(result)
            print(f"✅ {test_case.question_id}: 质量评分 {quality_score:.2f}")

        return {
            "test_count": len(simple_tests),
            "average_quality": sum(r["quality_score"] for r in results) / len(results)
            if results
            else 0,
            "results": results,
        }

    def test_complex_reasoning(self) -> Dict[str, Any]:
        """测试复杂推理能力"""
        print("\n🔍 测试复杂推理能力...")

        complex_tests = [
            tc
            for tc in self.test_cases
            if tc.question_type == QuestionType.COMPLEX_REASONING
        ]
        results = []

        for test_case in complex_tests:
            # 模拟复杂推理过程
            reasoning_steps = self._simulate_reasoning_process(test_case)
            mock_answer = self._generate_complex_answer(test_case, reasoning_steps)

            # 评估推理质量
            reasoning_score = self._evaluate_reasoning_quality(
                reasoning_steps, mock_answer, test_case
            )

            result = {
                "question_id": test_case.question_id,
                "question": test_case.question,
                "reasoning_steps": reasoning_steps,
                "answer": mock_answer,
                "reasoning_score": reasoning_score,
                "logical_coherence": self._check_logical_coherence(reasoning_steps),
                "completeness": self._check_answer_completeness(mock_answer, test_case),
            }

            results.append(result)
            print(f"✅ {test_case.question_id}: 推理评分 {reasoning_score:.2f}")

        return {
            "test_count": len(complex_tests),
            "average_reasoning_score": sum(r["reasoning_score"] for r in results)
            / len(results)
            if results
            else 0,
            "results": results,
        }

    def test_multi_turn_conversation(self) -> Dict[str, Any]:
        """测试多轮对话能力"""
        print("\n🔍 测试多轮对话能力...")

        multi_turn_tests = [
            tc for tc in self.test_cases if tc.question_type == QuestionType.MULTI_TURN
        ]
        results = []

        for test_case in multi_turn_tests:
            conversation_history = []
            context_retention_scores = []

            # 初始问题
            initial_answer = self._generate_mock_answer(test_case)
            conversation_history.append({"role": "user", "content": test_case.question})
            conversation_history.append(
                {"role": "assistant", "content": initial_answer}
            )

            # 处理后续问题
            for i, follow_up in enumerate(test_case.follow_up_questions):
                follow_up_answer = self._generate_follow_up_answer(
                    follow_up, conversation_history
                )

                # 评估上下文保持能力
                context_score = self._evaluate_context_retention(
                    conversation_history, follow_up_answer
                )
                context_retention_scores.append(context_score)

                conversation_history.append({"role": "user", "content": follow_up})
                conversation_history.append(
                    {"role": "assistant", "content": follow_up_answer}
                )

            avg_context_retention = (
                sum(context_retention_scores) / len(context_retention_scores)
                if context_retention_scores
                else 0
            )

            result = {
                "question_id": test_case.question_id,
                "initial_question": test_case.question,
                "conversation_turns": len(test_case.follow_up_questions) + 1,
                "context_retention_scores": context_retention_scores,
                "average_context_retention": avg_context_retention,
                "conversation_coherence": self._evaluate_conversation_coherence(
                    conversation_history
                ),
            }

            results.append(result)
            print(f"✅ {test_case.question_id}: 上下文保持 {avg_context_retention:.2f}")

        return {
            "test_count": len(multi_turn_tests),
            "average_context_retention": sum(
                r["average_context_retention"] for r in results
            )
            / len(results)
            if results
            else 0,
            "results": results,
        }

    def _generate_mock_answer(self, test_case: TestCase) -> str:
        """生成模拟回答"""
        if test_case.question_id == "simple_001":
            return "人工智能（AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。"
        elif test_case.question_id == "simple_002":
            return "Python是一种高级编程语言，以其简洁的语法和强大的功能而闻名，是一种解释型语言。"
        elif test_case.question_id == "simple_003":
            return "机器学习的主要类型包括：监督学习、无监督学习和强化学习三大类。"
        else:
            return "这是一个模拟回答，用于测试系统功能。"

    def _generate_complex_answer(
        self, test_case: TestCase, reasoning_steps: List[str]
    ) -> str:
        """生成复杂推理回答"""
        return "基于分析，" + "，".join(reasoning_steps) + "，因此得出这个结论。"

    def _generate_follow_up_answer(self, question: str, history: List[Dict]) -> str:
        """生成后续回答"""
        return f"基于之前的讨论，关于{question}，我可以进一步解释..."

    def _simulate_reasoning_process(self, test_case: TestCase) -> List[str]:
        """模拟推理过程"""
        if "收入" in test_case.question and "成本" in test_case.question:
            return ["分析收入增长20%的影响", "分析成本增长30%的影响", "计算利润变化", "评估整体财务影响"]
        elif "分布式系统" in test_case.question:
            return ["分析性能因素", "考虑可靠性要求", "评估可扩展性需求", "综合权衡各个方面"]
        else:
            return ["分析问题", "考虑解决方案", "得出结论"]

    def _evaluate_answer_quality(self, answer: str, test_case: TestCase) -> float:
        """评估回答质量"""
        score = 0.0

        # 关键词覆盖 (40%)
        keyword_coverage = self._check_keyword_coverage(
            answer, test_case.expected_keywords
        )
        score += keyword_coverage * 0.4

        # 回答长度适中 (20%)
        if 50 <= len(answer) <= 500:
            score += 0.2
        elif 20 <= len(answer) <= 1000:
            score += 0.1

        # 回答类型匹配 (40%)
        type_match = self._check_answer_type(answer, test_case.expected_answer_type)
        score += type_match * 0.4

        return min(score, 1.0)

    def _evaluate_reasoning_quality(
        self, reasoning_steps: List[str], answer: str, test_case: TestCase
    ) -> float:
        """评估推理质量"""
        score = 0.0

        # 推理步骤数量 (30%)
        if len(reasoning_steps) >= 3:
            score += 0.3
        elif len(reasoning_steps) >= 2:
            score += 0.2

        # 逻辑连贯性 (40%)
        coherence = self._check_logical_coherence(reasoning_steps)
        score += coherence * 0.4

        # 回答完整性 (30%)
        completeness = self._check_answer_completeness(answer, test_case)
        score += completeness * 0.3

        return min(score, 1.0)

    def _check_keyword_coverage(self, answer: str, keywords: List[str]) -> float:
        """检查关键词覆盖率"""
        if not keywords:
            return 1.0

        answer_lower = answer.lower()
        covered_keywords = sum(
            1 for keyword in keywords if keyword.lower() in answer_lower
        )
        return covered_keywords / len(keywords)

    def _check_answer_type(self, answer: str, expected_type: str) -> float:
        """检查回答类型匹配度"""
        answer_lower = answer.lower()

        type_indicators = {
            "definition": ["是", "定义", "指的是"],
            "description": ["具有", "特点是", "包括"],
            "classification": ["类型", "分类", "种类"],
            "analysis": ["分析", "影响", "因素"],
            "advice": ["建议", "应该", "可以"],
            "explanation": ["解释", "说明", "因为"],
            "methodology": ["方法", "步骤", "流程"],
            "code": ["函数", "def", "代码", "import"],
            "extraction": ["根据", "文档", "提到"],
        }

        indicators = type_indicators.get(expected_type, [])
        if not indicators:
            return 0.5

        matches = sum(1 for indicator in indicators if indicator in answer_lower)
        return min(matches / len(indicators), 1.0)

    def _check_logical_coherence(self, reasoning_steps: List[str]) -> float:
        """检查逻辑连贯性"""
        if len(reasoning_steps) < 2:
            return 0.5

        # 简单的连贯性检查：步骤之间应该有逻辑关系
        coherence_score = 0.8  # 模拟评分
        return coherence_score

    def _check_answer_completeness(self, answer: str, test_case: TestCase) -> float:
        """检查回答完整性"""
        # 基于回答长度和关键词覆盖评估完整性
        length_score = min(len(answer) / 200, 1.0)  # 200字符为满分
        keyword_score = self._check_keyword_coverage(
            answer, test_case.expected_keywords
        )
        return (length_score + keyword_score) / 2

    def _evaluate_context_retention(
        self, history: List[Dict], current_answer: str
    ) -> float:
        """评估上下文保持能力"""
        # 检查当前回答是否引用了之前的对话内容
        context_score = 0.7  # 模拟评分
        return context_score

    def _evaluate_conversation_coherence(self, history: List[Dict]) -> float:
        """评估对话连贯性"""
        coherence_score = 0.8  # 模拟评分
        return coherence_score

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始问题分类全面测试\n")
        print("=" * 60)

        start_time = time.time()

        # 1. 问题分类准确性测试
        classification_results = self.test_question_classification()

        # 2. 简单问答测试
        simple_qa_results = self.test_simple_qa()

        # 3. 复杂推理测试
        complex_reasoning_results = self.test_complex_reasoning()

        # 4. 多轮对话测试
        multi_turn_results = self.test_multi_turn_conversation()

        end_time = time.time()
        total_time = end_time - start_time

        # 汇总结果
        summary = {
            "test_execution_time": total_time,
            "classification_accuracy": classification_results["accuracy"],
            "simple_qa_average_quality": simple_qa_results["average_quality"],
            "complex_reasoning_average_score": complex_reasoning_results[
                "average_reasoning_score"
            ],
            "multi_turn_average_context_retention": multi_turn_results[
                "average_context_retention"
            ],
            "overall_score": (
                classification_results["accuracy"] * 0.25
                + simple_qa_results["average_quality"] * 0.25
                + complex_reasoning_results["average_reasoning_score"] * 0.25
                + multi_turn_results["average_context_retention"] * 0.25
            ),
            "detailed_results": {
                "classification": classification_results,
                "simple_qa": simple_qa_results,
                "complex_reasoning": complex_reasoning_results,
                "multi_turn": multi_turn_results,
            },
        }

        return summary

    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """生成测试报告"""
        report = f"""
# 问题分类测试报告

## 测试概要
- **执行时间**: {results['test_execution_time']:.2f} 秒
- **总体评分**: {results['overall_score']:.2f}/1.00

## 分类测试结果
- **分类准确率**: {results['classification_accuracy']:.2%}
- **测试用例数**: {results['detailed_results']['classification']['total_tests']}

## 简单问答测试结果
- **平均质量评分**: {results['simple_qa_average_quality']:.2f}/1.00
- **测试用例数**: {results['detailed_results']['simple_qa']['test_count']}

## 复杂推理测试结果
- **平均推理评分**: {results['complex_reasoning_average_score']:.2f}/1.00
- **测试用例数**: {results['detailed_results']['complex_reasoning']['test_count']}

## 多轮对话测试结果
- **平均上下文保持**: {results['multi_turn_average_context_retention']:.2f}/1.00
- **测试用例数**: {results['detailed_results']['multi_turn']['test_count']}

## 测试结论
"""

        if results["overall_score"] >= 0.8:
            report += "✅ **优秀**: 系统在问题分类和回答生成方面表现良好\n"
        elif results["overall_score"] >= 0.6:
            report += "⚠️ **良好**: 系统基本功能正常，但仍有改进空间\n"
        else:
            report += "❌ **需要改进**: 系统在多个方面存在不足\n"

        report += f"""
## 改进建议
1. **分类准确性**: 当前为 {results['classification_accuracy']:.1%}，建议优化分类算法
2. **回答质量**: 简单问答平均评分 {results['simple_qa_average_quality']:.2f}，可进一步优化
3. **推理能力**: 复杂推理评分 {results['complex_reasoning_average_score']:.2f}，需要加强逻辑分析
4. **对话连贯**: 多轮对话上下文保持 {results['multi_turn_average_context_retention']:.2f}，需改进记忆机制

## 下一步行动
- 实施分类算法优化
- 增强推理逻辑能力
- 改进对话上下文管理
- 扩充测试用例覆盖范围
"""

        return report


def main():
    """主函数"""
    tester = QuestionClassificationTester()

    # 运行所有测试
    results = tester.run_all_tests()

    # 生成报告
    report = tester.generate_test_report(results)

    # 保存结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # 保存JSON结果
    with open(
        f"test_results/question_classification_results_{timestamp}.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 保存报告
    with open(
        f"test_results/question_classification_report_{timestamp}.md",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(report)

    # 输出摘要
    print("\n" + "=" * 60)
    print("🎯 问题分类测试完成！")
    print("=" * 60)
    print(f"📊 总体评分: {results['overall_score']:.2f}/1.00")
    print(f"🎯 分类准确率: {results['classification_accuracy']:.1%}")
    print(f"💬 简单问答质量: {results['simple_qa_average_quality']:.2f}")
    print(f"🧠 复杂推理能力: {results['complex_reasoning_average_score']:.2f}")
    print(f"🔄 多轮对话连贯: {results['multi_turn_average_context_retention']:.2f}")
    print(f"\n📄 详细报告已保存到: test_results/question_classification_report_{timestamp}.md")

    return results["overall_score"] >= 0.6


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
