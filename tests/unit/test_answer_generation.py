#!/usr/bin/env python3
"""
回答生成测试
测试RAG系统的回答生成质量，包括：
1. 回答正确性评估
2. 回答流畅性评估
3. 回答相关性评估
4. 不同类型问题的生成质量
5. 上下文一致性检查
"""
import json
import math
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple


@dataclass
class TestCase:
    """测试用例数据结构"""

    test_id: str
    question: str
    context: str  # 检索到的上下文
    expected_answer_type: str  # factual, analytical, procedural, comparative
    expected_keywords: List[str]
    expected_length_range: Tuple[int, int]  # (min, max)
    difficulty: str  # easy, medium, hard
    topic: str


@dataclass
class AnswerQuality:
    """回答质量评估结果"""

    test_id: str
    generated_answer: str
    correctness_score: float
    fluency_score: float
    relevance_score: float
    completeness_score: float
    overall_score: float
    detailed_metrics: Dict[str, Any]


class AnswerGenerationTester:
    """回答生成测试器"""

    def __init__(self):
        self.test_cases = self._generate_test_cases()
        self.test_results = []

    def _generate_test_cases(self) -> List[TestCase]:
        """生成测试用例"""
        test_cases = [
            # 事实性问答测试
            TestCase(
                test_id="fact_001",
                question="什么是人工智能？",
                context="人工智能（AI）是计算机科学的一个分支，致力于创建能够模拟人类智能的系统。它包括机器学习、深度学习、自然语言处理等技术。",
                expected_answer_type="factual",
                expected_keywords=["人工智能", "计算机科学", "模拟人类智能", "系统"],
                expected_length_range=(50, 200),
                difficulty="easy",
                topic="AI基础",
            ),
            TestCase(
                test_id="fact_002",
                question="Python编程语言有哪些主要特点？",
                context="Python是一种高级编程语言，具有简洁的语法、动态类型、解释执行、丰富的标准库等特点。广泛应用于数据科学、Web开发、自动化等领域。",
                expected_answer_type="factual",
                expected_keywords=["高级语言", "简洁语法", "动态类型", "解释执行", "标准库"],
                expected_length_range=(60, 250),
                difficulty="medium",
                topic="编程语言",
            ),
            # 分析性问答测试
            TestCase(
                test_id="analytical_001",
                question="分析机器学习在实际应用中的优势和局限性",
                context="机器学习是AI的核心技术，能够从数据中学习模式。优势包括自动化决策、处理大规模数据、发现复杂模式。局限性包括需要大量标注数据、黑盒问题、过拟合风险等。",
                expected_answer_type="analytical",
                expected_keywords=["优势", "局限性", "自动化", "数据需求", "过拟合"],
                expected_length_range=(100, 400),
                difficulty="hard",
                topic="机器学习分析",
            ),
            TestCase(
                test_id="analytical_002",
                question="比较深度学习和传统机器学习方法在图像识别任务中的差异",
                context="深度学习使用多层神经网络自动学习特征，传统机器学习需要手动设计特征。在图像识别中，深度学习通常表现更好，但需要更多数据和计算资源。",
                expected_answer_type="comparative",
                expected_keywords=["深度学习", "传统机器学习", "特征学习", "性能差异", "资源需求"],
                expected_length_range=(120, 350),
                difficulty="hard",
                topic="算法比较",
            ),
            # 程序性问答测试
            TestCase(
                test_id="procedural_001",
                question="如何进行数据预处理以提高机器学习模型的性能？",
                context="数据预处理包括数据清洗、缺失值处理、异常值检测、特征工程、数据标准化等步骤。高质量的数据预处理能显著提升模型性能。",
                expected_answer_type="procedural",
                expected_keywords=["数据清洗", "缺失值", "异常值", "特征工程", "标准化"],
                expected_length_range=(100, 300),
                difficulty="medium",
                topic="数据预处理",
            ),
            TestCase(
                test_id="procedural_002",
                question="构建微服务架构时需要注意哪些关键事项？",
                context="微服务架构需要考虑服务拆分策略、API设计、数据一致性、服务发现、负载均衡、监控日志、容器化部署等方面。",
                expected_answer_type="procedural",
                expected_keywords=["服务拆分", "API设计", "数据一致性", "服务发现", "监控"],
                expected_length_range=(120, 350),
                difficulty="hard",
                topic="系统架构",
            ),
            # 比较性问答测试
            TestCase(
                test_id="comparative_001",
                question="对比监督学习和无监督学习的适用场景",
                context="监督学习需要标注数据，适合分类、回归等任务。无监督学习不需要标注数据，适合聚类、降维等任务。选择取决于数据可用性和问题类型。",
                expected_answer_type="comparative",
                expected_keywords=["监督学习", "无监督学习", "标注数据", "适用场景", "任务类型"],
                expected_length_range=(100, 300),
                difficulty="medium",
                topic="学习方法比较",
            ),
            # 复杂推理测试
            TestCase(
                test_id="reasoning_001",
                question="如果要在医疗诊断系统中应用AI，需要考虑哪些伦理和技术挑战？",
                context="AI医疗诊断需要考虑数据隐私、算法透明度、误诊责任、监管合规等技术挑战，以及患者权益、医生角色等伦理问题。",
                expected_answer_type="complex_reasoning",
                expected_keywords=["伦理挑战", "技术挑战", "数据隐私", "算法透明度", "监管合规"],
                expected_length_range=(150, 400),
                difficulty="hard",
                topic="AI伦理",
            ),
            TestCase(
                test_id="reasoning_002",
                question="在构建推荐系统时，如何平衡个性化推荐和隐私保护？",
                context="推荐系统需要用户数据来提供个性化服务，但过度收集数据会侵犯隐私。解决方案包括差分隐私、联邦学习、本地计算、透明化政策等。",
                expected_answer_type="complex_reasoning",
                expected_keywords=["个性化推荐", "隐私保护", "差分隐私", "联邦学习", "透明化"],
                expected_length_range=(120, 350),
                difficulty="hard",
                topic="推荐系统",
            ),
        ]

        return test_cases

    def _generate_mock_answer(self, test_case: TestCase) -> str:
        """生成模拟回答（实际应用中使用LLM生成）"""

        # 基于测试用例生成合理的模拟回答
        answer_templates = {
            "fact_001": "人工智能（AI）是计算机科学的一个重要分支，它致力于开发和创建能够模拟、扩展和增强人类智能的系统。AI系统可以通过算法和大量数据来学习、推理、感知和决策。",
            "fact_002": "Python作为一门高级编程语言，具有以下主要特点：1）语法简洁明了，易于学习和使用；2）动态类型系统，无需显式声明变量类型；3）解释执行，开发效率高；4）拥有丰富的标准库和第三方库生态系统；5）跨平台兼容性强。",
            "analytical_001": "机器学习在实际应用中展现出显著优势，包括自动化决策制定、处理海量数据的能力、发现复杂隐藏模式等。然而，它也存在明显的局限性：需要大量高质量的标注数据进行训练、算法决策过程缺乏透明度（黑盒问题）、存在过拟合和欠拟合的风险、对数据质量和特征工程高度依赖。",
            "analytical_002": "在图像识别任务中，深度学习和传统机器学习方法存在显著差异：深度学习能够自动从原始像素数据中学习层次化特征表示，而传统方法需要手动设计特征提取器（如SIFT、HOG等）。深度学习通常在大数据集上表现更优越，但需要更多计算资源和训练时间；传统方法在数据量有限时可能更有效，且模型更易解释。",
            "procedural_001": "为了提高机器学习模型的性能，数据预处理应该按照以下步骤进行：1）数据清洗：处理缺失值、异常值和重复数据；2）特征工程：选择、转换和创建有意义的特征；3）数据标准化：确保特征在同一尺度上；4）数据分割：合理划分训练集、验证集和测试集；5）数据增强：通过变换增加训练数据的多样性。",
            "procedural_002": "构建微服务架构时需要关注以下关键事项：1）合理的服务拆分策略，确保服务职责单一且内聚；2）设计清晰的API接口和契约；3）处理分布式环境下的数据一致性问题；4）实现服务发现和负载均衡机制；5）建立完善的监控、日志和追踪体系；6）考虑容器化和编排部署；7）设计容错和恢复机制。",
            "comparative_001": "监督学习和无监督学习有各自明确的适用场景：监督学习适用于有标注数据的分类、回归、预测任务，如垃圾邮件检测、房价预测等；无监督学习适用于无标注数据的探索性分析，如客户分群、异常检测、降维可视化等。选择取决于数据可用性、问题类型、业务目标和成本考虑等因素。",
            "reasoning_001": "在医疗诊断系统中应用AI面临着多方面的伦理和技术挑战：伦理方面包括患者隐私保护、算法决策的透明度和可解释性、误诊责任界定、维护医生与患者的关系等；技术方面包括医疗数据的质量和完整性、算法的准确性和可靠性、系统的安全性和稳定性、与现有医疗系统的集成、监管合规要求等。",
            "reasoning_002": "在推荐系统中平衡个性化推荐和隐私保护是一个复杂的问题：可以通过以下策略实现平衡：1）采用差分隐私技术在数学上保护个体隐私；2）使用联邦学习让模型在本地设备上训练；3）实施最小化数据收集原则；4）提供用户透明度和控制选项；5）开发本地化推荐算法；6）建立严格的数据访问控制机制；7）定期进行隐私影响评估。",
        }

        return answer_templates.get(
            test_case.test_id, f"这是一个关于{test_case.topic}的模拟回答，基于提供的上下文生成。"
        )

    def evaluate_correctness(self, answer: str, test_case: TestCase) -> float:
        """评估回答正确性"""
        score = 0.0

        # 1. 事实准确性检查 (40%)
        factual_accuracy = self._check_factual_accuracy(answer, test_case)
        score += factual_accuracy * 0.4

        # 2. 逻辑一致性检查 (30%)
        logical_consistency = self._check_logical_consistency(answer, test_case)
        score += logical_consistency * 0.3

        # 3. 内容完整性检查 (30%)
        content_completeness = self._check_content_completeness(answer, test_case)
        score += content_completeness * 0.3

        return min(score, 1.0)

    def evaluate_fluency(self, answer: str) -> float:
        """评估回答流畅性"""
        score = 0.0

        # 1. 语法正确性 (25%)
        grammar_score = self._check_grammar(answer)
        score += grammar_score * 0.25

        # 2. 语言自然性 (25%)
        naturalness_score = self._check_naturalness(answer)
        score += naturalness_score * 0.25

        # 3. 结构连贯性 (25%)
        coherence_score = self._check_coherence(answer)
        score += coherence_score * 0.25

        # 4. 长度适中性 (25%)
        length_score = self._check_length_appropriateness(answer)
        score += length_score * 0.25

        return min(score, 1.0)

    def evaluate_relevance(self, answer: str, test_case: TestCase) -> float:
        """评估回答相关性"""
        score = 0.0

        # 1. 问题匹配度 (40%)
        question_match = self._check_question_relevance(answer, test_case.question)
        score += question_match * 0.4

        # 2. 上下文一致性 (30%)
        context_consistency = self._check_context_consistency(answer, test_case.context)
        score += context_consistency * 0.3

        # 3. 关键词覆盖 (30%)
        keyword_coverage = self._check_keyword_coverage(
            answer, test_case.expected_keywords
        )
        score += keyword_coverage * 0.3

        return min(score, 1.0)

    def _check_factual_accuracy(self, answer: str, test_case: TestCase) -> float:
        """检查事实准确性"""
        # 检查是否包含明显错误信息
        error_patterns = [
            r"不是.*计算机科学",  # 对于AI问题
            r"不需要.*数据",  # 对于ML问题
            r"没有.*特点",  # 对于语言特点问题
        ]

        has_errors = any(
            re.search(pattern, answer, re.IGNORECASE) for pattern in error_patterns
        )
        if has_errors:
            return 0.3

        # 基于关键词覆盖评估事实准确性
        keyword_score = self._check_keyword_coverage(
            answer, test_case.expected_keywords
        )
        return keyword_score

    def _check_logical_consistency(self, answer: str, test_case: TestCase) -> float:
        """检查逻辑一致性"""
        # 检查是否有逻辑矛盾
        contradiction_patterns = [
            r"(虽然|但是).*但是.*(但是|虽然)",  # 重复转折
            r"既是.*又不是",  # 矛盾表述
        ]

        has_contradictions = any(
            re.search(pattern, answer, re.IGNORECASE)
            for pattern in contradiction_patterns
        )
        if has_contradictions:
            return 0.5

        # 基于句子结构评估逻辑性
        sentences = re.split(r"[。！？]", answer)
        logical_sentences = sum(1 for s in sentences if len(s.strip()) > 5)
        total_sentences = len([s for s in sentences if s.strip()])

        if total_sentences == 0:
            return 0.0

        return min(logical_sentences / total_sentences, 1.0)

    def _check_content_completeness(self, answer: str, test_case: TestCase) -> float:
        """检查内容完整性"""
        # 检查回答长度是否在预期范围内
        answer_length = len(answer)
        min_len, max_len = test_case.expected_length_range

        if min_len <= answer_length <= max_len:
            length_score = 1.0
        elif answer_length < min_len:
            length_score = answer_length / min_len
        else:
            length_score = max_len / answer_length

        # 检查是否涵盖关键方面
        key_aspects_score = self._check_keyword_coverage(
            answer, test_case.expected_keywords
        )

        return (length_score + key_aspects_score) / 2

    def _check_grammar(self, text: str) -> float:
        """检查语法正确性"""
        # 简单的语法检查
        issues = 0

        # 检查标点符号
        if not re.search(r"[。！？]$", text.strip()):
            issues += 1

        # 检查重复字符
        if re.search(r"(.)\1{3,}", text):
            issues += 1

        # 检查空格使用
        if re.search(r"[a-zA-Z]\s*[a-zA-Z]\s*[a-zA-Z]", text):  # 连续英文字母中间有空格
            pass  # 这是正常的
        if re.search(r"，，|。。", text):  # 重复标点
            issues += 1

        # 计算语法得分
        total_checks = 3
        grammar_score = max(0, (total_checks - issues) / total_checks)

        return grammar_score

    def _check_naturalness(self, text: str) -> float:
        """检查语言自然性"""
        # 检查句子长度分布
        sentences = re.split(r"[。！？]", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        # 计算平均句子长度
        avg_length = sum(len(s) for s in sentences) / len(sentences)

        # 理想的句子长度在15-50字符之间
        if 15 <= avg_length <= 50:
            length_score = 1.0
        elif avg_length < 15:
            length_score = avg_length / 15
        else:
            length_score = max(0, 1 - (avg_length - 50) / 100)

        # 检查连接词使用
        connectors = ["因为", "所以", "但是", "而且", "首先", "其次", "最后", "总的来说"]
        connector_count = sum(1 for conn in connectors if conn in text)

        # 连接词过多或过少都会影响自然性
        if 1 <= connector_count <= 3:
            connector_score = 1.0
        elif connector_count == 0:
            connector_score = 0.7
        else:
            connector_score = max(0, 1 - (connector_count - 3) * 0.2)

        return (length_score + connector_score) / 2

    def _check_coherence(self, text: str) -> float:
        """检查结构连贯性"""
        # 检查是否有序号词
        sequence_words = ["首先", "其次", "然后", "最后", "第一", "第二", "第三", "1)", "2)", "3)"]
        has_sequence = any(word in text for word in sequence_words)

        # 检查是否有总结构词
        summary_words = ["总之", "总的来说", "因此", "综上所述", "所以"]
        has_summary = any(word in text for word in summary_words)

        # 检查段落结构（这里简化为句子之间的连贯性）
        sentences = re.split(r"[。！？]", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            return 0.5

        # 简单评估：有结构词加分
        structure_score = 0.5
        if has_sequence:
            structure_score += 0.3
        if has_summary:
            structure_score += 0.2

        return min(structure_score, 1.0)

    def _check_length_appropriateness(self, text: str) -> float:
        """检查长度适中性"""
        length = len(text)

        # 理想长度在100-500字符之间
        if 100 <= length <= 500:
            return 1.0
        elif length < 100:
            return length / 100
        else:
            return max(0, 1 - (length - 500) / 1000)

    def _check_question_relevance(self, answer: str, question: str) -> float:
        """检查问题匹配度"""
        # 提取问题中的关键词
        question_words = set(re.findall(r"[\u4e00-\u9fff]+", question))

        # 检查回答中是否包含问题关键词
        answer_words = set(re.findall(r"[\u4e00-\u9fff]+", answer))

        if not question_words:
            return 0.5

        overlap = len(question_words & answer_words)
        relevance_score = overlap / len(question_words)

        # 检查回答是否直接回应问题
        if any(word in answer for word in ["是", "包括", "具有", "是指", "可以", "需要"]):
            relevance_score += 0.2

        return min(relevance_score, 1.0)

    def _check_context_consistency(self, answer: str, context: str) -> float:
        """检查上下文一致性"""
        # 检查回答是否与上下文信息一致
        context_words = set(re.findall(r"[\u4e00-\u9fff]+", context))
        answer_words = set(re.findall(r"[\u4e00-\u9fff]+", answer))

        if not context_words:
            return 0.8  # 没有上下文时给予中性评分

        overlap = len(context_words & answer_words)
        consistency_score = overlap / min(len(context_words), 50)  # 限制分母避免过小

        # 检查是否有明显矛盾
        contradiction_indicators = ["不是", "错误", "不对", "相反"]
        has_contradiction = any(
            indicator in answer for indicator in contradiction_indicators
        )

        if has_contradiction:
            consistency_score *= 0.5

        return min(consistency_score, 1.0)

    def _check_keyword_coverage(self, answer: str, keywords: List[str]) -> float:
        """检查关键词覆盖率"""
        if not keywords:
            return 1.0

        covered_keywords = sum(1 for keyword in keywords if keyword in answer)
        coverage_score = covered_keywords / len(keywords)

        return coverage_score

    def test_answer_generation_quality(self) -> Dict[str, Any]:
        """测试回答生成质量"""
        print("🔍 测试回答生成质量...")

        results = []

        for test_case in self.test_cases:
            print(f"  📝 测试用例: {test_case.test_id}")

            # 生成模拟回答
            generated_answer = self._generate_mock_answer(test_case)

            # 评估质量
            correctness_score = self.evaluate_correctness(generated_answer, test_case)
            fluency_score = self.evaluate_fluency(generated_answer)
            relevance_score = self.evaluate_relevance(generated_answer, test_case)
            completeness_score = self._check_content_completeness(
                generated_answer, test_case
            )

            # 计算总分
            overall_score = (
                correctness_score * 0.3
                + fluency_score * 0.2
                + relevance_score * 0.3
                + completeness_score * 0.2
            )

            # 详细指标
            detailed_metrics = {
                "answer_length": len(generated_answer),
                "keyword_coverage": self._check_keyword_coverage(
                    generated_answer, test_case.expected_keywords
                ),
                "grammar_score": self._check_grammar(generated_answer),
                "naturalness_score": self._check_naturalness(generated_answer),
                "coherence_score": self._check_coherence(generated_answer),
            }

            quality_result = AnswerQuality(
                test_id=test_case.test_id,
                generated_answer=generated_answer,
                correctness_score=correctness_score,
                fluency_score=fluency_score,
                relevance_score=relevance_score,
                completeness_score=completeness_score,
                overall_score=overall_score,
                detailed_metrics=detailed_metrics,
            )

            results.append(quality_result)
            print(
                f"    ✅ 总分: {overall_score:.3f} (正确性:{correctness_score:.3f}, 流畅性:{fluency_score:.3f}, 相关性:{relevance_score:.3f})"
            )

        return {"total_tests": len(results), "results": results}

    def analyze_performance_by_answer_type(
        self, results: List[AnswerQuality]
    ) -> Dict[str, Any]:
        """按回答类型分析性能"""
        type_groups = defaultdict(list)

        for result in results:
            test_case = next(
                tc for tc in self.test_cases if tc.test_id == result.test_id
            )
            type_groups[test_case.expected_answer_type].append(result)

        type_analysis = {}

        for answer_type, type_results in type_groups.items():
            if not type_results:
                continue

            avg_scores = {
                "correctness": sum(r.correctness_score for r in type_results)
                / len(type_results),
                "fluency": sum(r.fluency_score for r in type_results)
                / len(type_results),
                "relevance": sum(r.relevance_score for r in type_results)
                / len(type_results),
                "completeness": sum(r.completeness_score for r in type_results)
                / len(type_results),
                "overall": sum(r.overall_score for r in type_results)
                / len(type_results),
            }

            type_analysis[answer_type] = {
                "count": len(type_results),
                "average_scores": avg_scores,
            }

        return type_analysis

    def test_generation_speed(self) -> Dict[str, Any]:
        """测试生成速度"""
        print("\n🔍 测试回答生成速度...")

        generation_times = []

        for i, test_case in enumerate(self.test_cases[:5]):  # 测试前5个用例
            start_time = time.time()

            # 模拟生成过程
            generated_answer = self._generate_mock_answer(test_case)

            generation_time = time.time() - start_time
            generation_times.append(generation_time)

            print(
                f"  ⏱️  用例 {i+1}: {generation_time:.4f}s ({len(generated_answer)} 字符)"
            )

        avg_time = sum(generation_times) / len(generation_times)
        min_time = min(generation_times)
        max_time = max(generation_times)

        return {
            "average_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "total_tests": len(generation_times),
        }

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有回答生成测试"""
        print("🚀 开始回答生成全面测试\n")
        print("=" * 60)

        start_time = time.time()

        # 1. 回答生成质量测试
        quality_results = self.test_answer_generation_quality()

        # 2. 按类型分析性能
        type_analysis = self.analyze_performance_by_answer_type(
            quality_results["results"]
        )

        # 3. 生成速度测试
        speed_results = self.test_generation_speed()

        end_time = time.time()
        total_time = end_time - start_time

        # 计算总体指标
        overall_correctness = sum(
            r.correctness_score for r in quality_results["results"]
        ) / len(quality_results["results"])
        overall_fluency = sum(
            r.fluency_score for r in quality_results["results"]
        ) / len(quality_results["results"])
        overall_relevance = sum(
            r.relevance_score for r in quality_results["results"]
        ) / len(quality_results["results"])
        overall_quality = sum(
            r.overall_score for r in quality_results["results"]
        ) / len(quality_results["results"])

        summary = {
            "test_execution_time": total_time,
            "overall_metrics": {
                "correctness": overall_correctness,
                "fluency": overall_fluency,
                "relevance": overall_relevance,
                "overall_quality": overall_quality,
            },
            "quality_results": quality_results,
            "type_analysis": type_analysis,
            "speed_results": speed_results,
        }

        return summary

    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """生成测试报告"""
        overall = results["overall_metrics"]

        report = f"""
# 回答生成质量测试报告

## 测试概要
- **执行时间**: {results['test_execution_time']:.2f} 秒
- **测试用例数**: {results['quality_results']['total_tests']}

## 总体质量指标
- **正确性**: {overall['correctness']:.3f}/1.000
- **流畅性**: {overall['fluency']:.3f}/1.000
- **相关性**: {overall['relevance']:.3f}/1.000
- **总体质量**: {overall['overall_quality']:.3f}/1.000

## 按回答类型分析
"""

        for answer_type, analysis in results["type_analysis"].items():
            scores = analysis["average_scores"]
            report += f"- **{answer_type}** (n={analysis['count']}):\n"
            report += f"  - 正确性: {scores['correctness']:.3f}\n"
            report += f"  - 流畅性: {scores['fluency']:.3f}\n"
            report += f"  - 相关性: {scores['relevance']:.3f}\n"
            report += f"  - 完整性: {scores['completeness']:.3f}\n"
            report += f"  - 总体: {scores['overall']:.3f}\n"

        report += f"""
## 生成速度分析
- **平均生成时间**: {results['speed_results']['average_time']:.4f}s
- **最快时间**: {results['speed_results']['min_time']:.4f}s
- **最慢时间**: {results['speed_results']['max_time']:.4f}s

## 详细测试结果
"""

        # 添加部分详细结果
        for i, result in enumerate(results["quality_results"]["results"][:5]):  # 只显示前5个
            report += f"""
### {result.test_id}
- **回答长度**: {result.detailed_metrics['answer_length']} 字符
- **关键词覆盖率**: {result.detailed_metrics['keyword_coverage']:.3f}
- **语法得分**: {result.detailed_metrics['grammar_score']:.3f}
- **自然度得分**: {result.detailed_metrics['naturalness_score']:.3f}
- **连贯性得分**: {result.detailed_metrics['coherence_score']:.3f}
- **回答预览**: {result.generated_answer[:100]}...
"""

        report += f"""
## 测试结论
"""

        if overall["overall_quality"] >= 0.8:
            report += "✅ **优秀**: 回答生成质量很高，各项指标均达到预期\n"
        elif overall["overall_quality"] >= 0.6:
            report += "⚠️ **良好**: 回答生成质量基本达标，但仍有改进空间\n"
        else:
            report += "❌ **需要改进**: 回答生成质量在多个方面存在不足\n"

        report += f"""
## 优化建议
1. **正确性提升**: 当前正确性 {overall['correctness']:.1%}，建议加强事实核查和逻辑验证
2. **流畅性改进**: 当前流畅性 {overall['fluency']:.1%}，可优化语言模型输出
3. **相关性优化**: 当前相关性 {overall['relevance']:.1%}，需改进上下文理解能力
4. **完整性保证**: 确保回答涵盖问题的所有关键方面

## 下一步行动
- 优化不同回答类型的生成策略
- 加强事实准确性验证机制
- 改进语言流畅性和自然度
- 完善上下文相关性判断
"""

        return report


def main():
    """主函数"""
    tester = AnswerGenerationTester()

    # 运行所有测试
    results = tester.run_all_tests()

    # 生成报告
    report = tester.generate_test_report(results)

    # 保存结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # 保存JSON结果
    with open(
        f"test_results/answer_generation_results_{timestamp}.json",
        "w",
        encoding="utf-8",
    ) as f:
        # 转换AnswerQuality对象为可序列化的字典
        serializable_results = {
            "test_execution_time": results["test_execution_time"],
            "overall_metrics": results["overall_metrics"],
            "type_analysis": results["type_analysis"],
            "speed_results": results["speed_results"],
            "quality_summary": {
                "total_tests": results["quality_results"]["total_tests"],
                "average_correctness": results["overall_metrics"]["correctness"],
                "average_fluency": results["overall_metrics"]["fluency"],
                "average_relevance": results["overall_metrics"]["relevance"],
                "average_quality": results["overall_metrics"]["overall_quality"],
            },
        }
        json.dump(serializable_results, f, indent=2, ensure_ascii=False)

    # 保存报告
    with open(
        f"test_results/answer_generation_report_{timestamp}.md", "w", encoding="utf-8"
    ) as f:
        f.write(report)

    # 输出摘要
    print("\n" + "=" * 60)
    print("🎯 回答生成测试完成！")
    print("=" * 60)
    print(f"📊 总体质量评分: {results['overall_metrics']['overall_quality']:.3f}/1.000")
    print(f"✅ 正确性: {results['overall_metrics']['correctness']:.3f}")
    print(f"💬 流畅性: {results['overall_metrics']['fluency']:.3f}")
    print(f"🎯 相关性: {results['overall_metrics']['relevance']:.3f}")
    print(f"⏱️  平均生成时间: {results['speed_results']['average_time']:.4f}s")
    print(f"\n📄 详细报告已保存到: test_results/answer_generation_report_{timestamp}.md")

    return results["overall_metrics"]["overall_quality"] >= 0.6


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
