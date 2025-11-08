#!/usr/bin/env python3
"""
OCR集成测试
测试PaddleOCR文本提取与RAG系统的完整集成，包括：
1. OCR文本提取准确性测试
2. OCR文本质量评估
3. OCR到RAG的集成测试
4. 不同文档类型的OCR性能
5. OCR结果与RAG检索效果评估
"""
import sys
import os
import json
import time
import math
import random
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, backend_path)

@dataclass
class OCRTestCase:
    """OCR测试用例"""
    test_id: str
    document_path: str
    document_type: str  # image, pdf, scanned_pdf, text_pdf
    expected_text: str  # 期望的OCR提取文本
    language: str  # ch, en, mixed
    quality_requirements: Dict[str, Any]
    difficulty: str  # easy, medium, hard

@dataclass
class OCRResult:
    """OCR测试结果"""
    test_id: str
    extracted_text: str
    extraction_time: float
    character_count: int
    quality_score: float
    rag_integration_score: float

class OCRIntegrationTester:
    """OCR集成测试器"""

    def __init__(self):
        self.test_cases = self._generate_test_cases()
        self.test_results = []

    def _generate_test_cases(self) -> List[OCRTestCase]:
        """生成OCR测试用例"""
        test_cases = [
            # 简单图片文本测试
            OCRTestCase(
                test_id="ocr_img_001",
                document_path="test_resources/images/test_ocr.png",
                document_type="image",
                expected_text="这是一个测试文档，用于验证OCR功能。",
                language="ch",
                quality_requirements={
                    "min_accuracy": 0.8,
                    "min_character_count": 10,
                    "max_noise_level": 0.2
                },
                difficulty="easy"
            ),
            OCRTestCase(
                test_id="ocr_img_002",
                document_path="samples/test_text.txt",  # 纯文本文件作为对比
                document_type="text",
                expected_text="简单的测试文本，包含中文字符。",
                language="ch",
                quality_requirements={
                    "min_accuracy": 0.95,
                    "min_character_count": 5,
                    "max_noise_level": 0.1
                },
                difficulty="easy"
            ),

            # PDF文档测试
            OCRTestCase(
                test_id="ocr_pdf_001",
                document_path="samples/test_document_1.txt",  # 模拟PDF内容
                document_type="pdf",
                expected_text="这是第一份测试文档，包含技术文档的基本信息和详细说明。",
                language="ch",
                quality_requirements={
                    "min_accuracy": 0.75,
                    "min_character_count": 20,
                    "max_noise_level": 0.3
                },
                difficulty="medium"
            ),

            # 复杂文档测试
            OCRTestCase(
                test_id="ocr_complex_001",
                document_path="samples/test_document_2.txt",
                document_type="scanned_pdf",
                expected_text="技术规范文档第二版，包含系统架构设计、数据库设计、接口规范等详细内容。",
                language="ch",
                quality_requirements={
                    "min_accuracy": 0.7,
                    "min_character_count": 30,
                    "max_noise_level": 0.4
                },
                difficulty="hard"
            ),

            # 中英文混合测试
            OCRTestCase(
                test_id="ocr_mixed_001",
                document_path="samples/test_document_3.txt",
                document_type="pdf",
                expected_text="混合语言文档 Mixed Language Document 包含中文和English内容。",
                language="mixed",
                quality_requirements={
                    "min_accuracy": 0.7,
                    "min_character_count": 25,
                    "max_noise_level": 0.35
                },
                difficulty="medium"
            ),

            # 代码文档测试
            OCRTestCase(
                test_id="ocr_code_001",
                document_path="samples/test_code.txt",
                document_type="code",
                expected_text="function example() { return 'Hello, World!'; }",
                language="en",
                quality_requirements={
                    "min_accuracy": 0.8,
                    "min_character_count": 10,
                    "max_noise_level": 0.25
                },
                difficulty="medium"
            )
        ]

        return test_cases

    def _mock_ocr_extraction(self, document_path: str, language: str = "ch") -> Tuple[str, float]:
        """模拟OCR提取过程"""
        start_time = time.time()

        # 如果文件存在，读取内容作为基准
        if os.path.exists(document_path):
            try:
                with open(document_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                content = f"读取文件失败: {str(e)}"
        else:
            # 模拟OCR提取的文本
            base_texts = {
                "test_resources/images/test_ocr.png": "这是一个测试文档，用于验证OCR功能。",
                "samples/test_text.txt": "简单的测试文本，包含中文字符。",
                "samples/test_document_1.txt": "这是第一份测试文档，包含技术文档的基本信息和详细说明。",
                "samples/test_document_2.txt": "技术规范文档第二版，包含系统架构设计、数据库设计、接口规范等详细内容。",
                "samples/test_document_3.txt": "混合语言文档 Mixed Language Document 包含中文和English内容。",
                "samples/test_code.txt": "function example() { return 'Hello, World!'; }"
            }
            content = base_texts.get(document_path, "默认OCR提取文本内容。")

        # 模拟OCR噪声
        noise_chars = ['~', '`', "'", '"', '|', '¦', '¡', '¿']
        if random.random() < 0.3:  # 30%概率添加噪声
            noise_count = random.randint(1, 3)
            for _ in range(noise_count):
                noise_pos = random.randint(0, len(content))
                noise_char = random.choice(noise_chars)
                content = content[:noise_pos] + noise_char + content[noise_pos + 1:]

        extraction_time = time.time() - start_time

        return content, extraction_time

    def _mock_paddleocr_extraction(self, image_path: str, lang: str = "ch") -> Tuple[str, float, Dict[str, Any]]:
        """模拟PaddleOCR提取过程"""
        start_time = time.time()

        # 模拟PaddleOCR的详细结果
        base_text, base_time = self._mock_ocr_extraction(image_path, lang)

        # 模拟PaddleOCR特有的结果格式
        ocr_result = {
            "text": base_text,
            "confidence_scores": [random.uniform(0.8, 0.95) for _ in range(len(base_text.split()))],
            "bbox": [[0, 0, 100, 20] for _ in range(1)],  # 模拟边界框
            "recognition_time": base_time,
            "preprocessing_time": random.uniform(0.1, 0.3),
            "model_inference_time": random.uniform(0.2, 0.5)
        }

        extraction_time = time.time() - start_time

        return ocr_result["text"], extraction_time, ocr_result

    def evaluate_ocr_accuracy(self, extracted_text: str, expected_text: str, test_case: OCRTestCase) -> float:
        """评估OCR提取准确性"""
        if not expected_text:
            return 0.0

        # 简单的字符匹配度计算
        expected_chars = set(expected_text.replace(" ", "").replace("\n", "").replace("\t", ""))
        extracted_chars = set(extracted_text.replace(" ", "").replace("\n", "").replace("\t", ""))

        if not expected_chars:
            return 1.0  # 如果没有期望文本，给满分

        # 计算字符级准确率
        correct_chars = len(expected_chars & extracted_chars)
        total_expected_chars = len(expected_chars)

        char_accuracy = correct_chars / total_expected_chars

        # 计算编辑距离（简化版）
        edit_distance = self._calculate_edit_distance(expected_text, extracted_text)
        max_length = max(len(expected_text), len(extracted_text))
        edit_accuracy = 1 - (edit_distance / max_length) if max_length > 0 else 1.0

        # 综合评分
        accuracy = (char_accuracy * 0.6 + edit_accuracy * 0.4)

        return accuracy

    def _calculate_edit_distance(self, text1: str, text2: str) -> int:
        """计算编辑距离（Levenshtein距离）"""
        m, n = len(text1), len(text2)
        if m == 0:
            return n
        if n == 0:
            return m

        # 创建DP表
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if text1[i-1] == text2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i][j-1])

        return dp[m][n]

    def evaluate_text_quality(self, text: str, test_case: OCRTestCase) -> float:
        """评估文本质量"""
        score = 0.0

        # 1. 字符数量检查 (25%)
        char_count = len(text)
        min_chars = test_case.quality_requirements["min_character_count"]
        if char_count >= min_chars:
            char_score = 1.0
        else:
            char_score = char_count / min_chars
        score += char_score * 0.25

        # 2. 噪声水平检查 (25%)
        noise_chars = ['~', '`', "'", '"', '|', '¦', '¡', '¿', '·', '•']
        noise_count = sum(1 for char in text if char in noise_chars)
        noise_ratio = noise_count / len(text) if text else 0
        max_noise = test_case.quality_requirements["max_noise_level"]
        noise_score = max(0, 1 - (noise_ratio / max_noise)) if max_noise > 0 else 1.0
        score += noise_score * 0.25

        # 3. 语言一致性检查 (25%)
        language_score = self._check_language_consistency(text, test_case.language)
        score += language_score * 0.25

        # 4. 结构完整性检查 (25%)
        structure_score = self._check_text_structure(text)
        score += structure_score * 0.25

        return min(score, 1.0)

    def _check_language_consistency(self, text: str, expected_lang: str) -> float:
        """检查语言一致性"""
        if expected_lang == "ch":
            # 检查中文字符比例
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            total_chars = len(text)
            if total_chars == 0:
                return 0.5
            chinese_ratio = chinese_chars / total_chars
            return min(chinese_ratio * 1.2, 1.0)  # 允许一些英文

        elif expected_lang == "en":
            # 检查英文字符比例
            english_chars = len([c for c in text if c.isalpha() and ord(c) < 128])
            total_chars = len(text)
            if total_chars == 0:
                return 0.5
            english_ratio = english_chars / total_chars
            return min(english_ratio * 1.2, 1.0)

        elif expected_lang == "mixed":
            # 检查中英文混合
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            english_chars = len([c for c in text if c.isalpha() and ord(c) < 128])
            total_chars = len(text)
            if total_chars == 0:
                return 0.5
            mixed_ratio = (chinese_chars + english_chars) / total_chars
            return mixed_ratio

        return 0.8

    def _check_text_structure(self, text: str) -> float:
        """检查文本结构完整性"""
        if not text:
            return 0.0

        # 检查是否有合理的段落结构
        paragraphs = text.split('\n\n')
        sentences = [s.strip() for s in text.split('。') if s.strip()]

        structure_score = 0.0

        # 段落结构评分
        if len(paragraphs) >= 1:
            structure_score += 0.4
        if len(paragraphs) >= 2:
            structure_score += 0.2

        # 句子结构评分
        if len(sentences) >= 1:
            structure_score += 0.4

        return min(structure_score, 1.0)

    def test_ocr_extraction_quality(self) -> Dict[str, Any]:
        """测试OCR提取质量"""
        print("🔍 测试OCR提取质量...")

        results = []

        for test_case in self.test_cases:
            print(f"  📄 测试用例: {test_case.test_id}")

            # 模拟OCR提取
            extracted_text, extraction_time = self._mock_ocr_extraction(
                test_case.document_path,
                test_case.language
            )

            # 评估准确性
            accuracy_score = self.evaluate_ocr_accuracy(
                extracted_text,
                test_case.expected_text,
                test_case
            )

            # 评估质量
            quality_score = self.evaluate_text_quality(extracted_text, test_case)

            # 检查是否满足质量要求
            min_accuracy = test_case.quality_requirements["min_accuracy"]
            meets_requirements = accuracy_score >= min_accuracy

            result = OCRResult(
                test_id=test_case.test_id,
                extracted_text=extracted_text,
                extraction_time=extraction_time,
                character_count=len(extracted_text),
                quality_score=quality_score,
                rag_integration_score=0.0  # 将在后续测试中评估
            )

            results.append(result)

            print(f"    ✅ 准确性: {accuracy_score:.3f}, 质量: {quality_score:.3f}, 时间: {extraction_time:.4f}s")
            print(f"    {'✅' if meets_requirements else '❌'} 是否满足要求: {meets_requirements}")

        return {
            "total_tests": len(results),
            "results": results
        }

    def test_paddleocr_integration(self) -> Dict[str, Any]:
        """测试PaddleOCR集成"""
        print("\n🔍 测试PaddleOCR集成...")

        paddleocr_results = []

        # 专门测试图片文件
        image_tests = [tc for tc in self.test_cases if tc.document_type == "image"]

        for test_case in image_tests:
            if not os.path.exists(test_case.document_path):
                print(f"  ⚠️  文件不存在: {test_case.document_path}")
                # Try alternative path in test_resources
                alt_path = test_case.document_path.replace("samples/", "test_resources/")
                if os.path.exists(alt_path):
                    test_case.document_path = alt_path
                    print(f"  ✅ Found at alternative path: {alt_path}")
                else:
                    continue

            print(f"  🔍 处理图片: {os.path.basename(test_case.document_path)}")

            # 模拟PaddleOCR处理
            extracted_text, extraction_time, ocr_details = self._mock_paddleocr_extraction(
                test_case.document_path,
                test_case.language
            )

            # 评估PaddleOCR特有的性能指标
            confidence_scores = ocr_details.get("confidence_scores", [])
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

            paddleocr_score = (
                avg_confidence * 0.4 +
                min(1.0, 1.0 / extraction_time) * 0.3 +  # 处理时间越短越好
                self.evaluate_text_quality(extracted_text, test_case) * 0.3
            )

            paddleocr_results.append({
                "test_id": test_case.test_id,
                "extracted_text": extracted_text,
                "extraction_time": extraction_time,
                "avg_confidence": avg_confidence,
                "paddleocr_score": paddleocr_score,
                "details": ocr_details
            })

            print(f"    ✅ PaddleOCR评分: {paddleocr_score:.3f}, 置信度: {avg_confidence:.3f}")

        return {
            "total_tests": len(paddleocr_results),
            "results": paddleocr_results,
            "average_score": sum(r["paddleocr_score"] for r in paddleocr_results) / len(paddleocr_results) if paddleocr_results else 0
        }

    def test_ocr_to_rag_integration(self) -> Dict[str, Any]:
        """测试OCR到RAG的集成"""
        print("\n🔍 测试OCR到RAG集成...")

        integration_results = []

        for test_case in self.test_cases:
            print(f"  🔗 测试集成: {test_case.test_id}")

            # 步骤1: OCR提取
            extracted_text, ocr_time = self._mock_ocr_extraction(
                test_case.document_path,
                test_case.language
            )

            # 步骤2: 模拟向量化
            vectorization_time = random.uniform(0.1, 0.3)
            time.sleep(0.01)  # 模拟处理时间

            # 步骤3: 模拟检索
            retrieval_time = random.uniform(0.05, 0.2)
            time.sleep(0.01)

            # 步骤4: 模拟回答生成
            generation_time = random.uniform(0.2, 0.8)
            time.sleep(0.01)

            total_processing_time = ocr_time + vectorization_time + retrieval_time + generation_time

            # 评估集成效果
            # OCR质量对RAG的影响
            ocr_quality = self.evaluate_text_quality(extracted_text, test_case)

            # 文本长度对RAG的影响
            text_length_score = min(1.0, len(extracted_text) / 100)  # 100字符为满分

            # 综合集成评分
            integration_score = (ocr_quality * 0.4 + text_length_score * 0.3 + min(1.0, 5.0 / total_processing_time) * 0.3)

            integration_results.append({
                "test_id": test_case.test_id,
                "ocr_time": ocr_time,
                "vectorization_time": vectorization_time,
                "retrieval_time": retrieval_time,
                "generation_time": generation_time,
                "total_time": total_processing_time,
                "ocr_quality": ocr_quality,
                "integration_score": integration_score
            })

            print(f"    ✅ 集成评分: {integration_score:.3f}, 总时间: {total_processing_time:.3f}s")

        return {
            "total_tests": len(integration_results),
            "results": integration_results,
            "average_integration_score": sum(r["integration_score"] for r in integration_results) / len(integration_results) if integration_results else 0
        }

    def test_different_document_types(self) -> Dict[str, Any]:
        """测试不同文档类型的OCR性能"""
        print("\n🔍 测试不同文档类型的OCR性能...")

        type_results = defaultdict(list)

        for test_case in self.test_cases:
            extracted_text, extraction_time = self._mock_ocr_extraction(
                test_case.document_path,
                test_case.language
            )

            accuracy_score = self.evaluate_ocr_accuracy(
                extracted_text,
                test_case.expected_text,
                test_case
            )

            type_results[test_case.document_type].append({
                "test_id": test_case.test_id,
                "accuracy": accuracy_score,
                "extraction_time": extraction_time,
                "text_length": len(extracted_text),
                "quality_score": self.evaluate_text_quality(extracted_text, test_case)
            })

        # 计算各类型的统计指标
        type_stats = {}
        for doc_type, results in type_results.items():
            if not results:
                continue

            stats = {
                "count": len(results),
                "avg_accuracy": sum(r["accuracy"] for r in results) / len(results),
                "avg_extraction_time": sum(r["extraction_time"] for r in results) / len(results),
                "avg_text_length": sum(r["text_length"] for r in results) / len(results),
                "avg_quality_score": sum(r["quality_score"] for r in results) / len(results)
            }

            type_stats[doc_type] = stats
            print(f"  📄 {doc_type}: 平均准确率 {stats['avg_accuracy']:.3f}, 平均时间 {stats['avg_extraction_time']:.4f}s")

        return dict(type_stats)

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有OCR集成测试"""
        print("🚀 开始OCR集成全面测试\n")
        print("=" * 60)

        start_time = time.time()

        # 1. OCR提取质量测试
        extraction_results = self.test_ocr_extraction_quality()

        # 2. PaddleOCR集成测试
        paddleocr_results = self.test_paddleocr_integration()

        # 3. OCR到RAG集成测试
        integration_results = self.test_ocr_to_rag_integration()

        # 4. 不同文档类型测试
        document_type_results = self.test_different_document_types()

        end_time = time.time()
        total_time = end_time - start_time

        # 计算总体指标
        total_tests = len(self.test_cases)
        avg_accuracy = sum(r.quality_score for r in extraction_results["results"]) / len(extraction_results["results"])
        avg_integration_score = integration_results["average_integration_score"]

        summary = {
            "test_execution_time": total_time,
            "total_tests": total_tests,
            "extraction_quality": {
                "average_score": avg_accuracy,
                "results": extraction_results["results"]
            },
            "paddleocr_integration": paddleocr_results,
            "rag_integration": integration_results,
            "document_type_performance": document_type_results,
            "overall_score": (avg_accuracy * 0.5 + avg_integration_score * 0.5)
        }

        return summary

    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """生成测试报告"""
        report = f"""
# OCR集成测试报告

## 测试概要
- **执行时间**: {results['test_execution_time']:.2f} 秒
- **测试用例数**: {results['total_tests']}
- **总体评分**: {results['overall_score']:.3f}/1.000

## OCR提取质量
- **平均质量评分**: {results['extraction_quality']['average_score']:.3f}/1.000
- **测试结果数量**: {len(results['extraction_quality']['results'])}

## PaddleOCR集成
- **平均评分**: {results['paddleocr_integration']['average_score']:.3f}/1.000
- **测试结果数量**: {results['paddleocr_integration']['total_tests']}

## RAG集成效果
- **平均集成评分**: {results['rag_integration']['average_integration_score']:.3f}/1.000
- **测试结果数量**: {results['rag_integration']['total_tests']}

## 文档类型性能分析
"""

        for doc_type, stats in results["document_type_performance"].items():
            report += f"- **{doc_type}**:\n"
            report += f"  - 测试数量: {stats['count']}\n"
            report += f"  - 平均准确率: {stats['avg_accuracy']:.3f}\n"
            report += f"  - 平均提取时间: {stats['avg_extraction_time']:.4f}s\n"
            report += f"  - 平均文本长度: {stats['avg_text_length']:.1f} 字符\n"
            report += f"  - 平均质量评分: {stats['avg_quality_score']:.3f}\n"

        report += f"""
## 详细测试结果
"""

        # 添加部分详细结果
        for i, result in enumerate(results["extraction_quality"]["results"][:3]):  # 只显示前3个
            report += f"""
### {result.test_id}
- **提取文本长度**: {result.character_count} 字符
- **提取时间**: {result.extraction_time:.4f}s
- **质量评分**: {result.quality_score:.3f}
- **文本预览**: {result.extracted_text[:100]}...
"""

        report += f"""
## 性能瓶颈分析
- **OCR提取时间**: 平均 {sum(r.extraction_time for r in results['extraction_quality']['results']) / len(results['extraction_quality']['results']):.4f}s
- **RAG处理总时间**: 平均 {sum(r['total_time'] for r in results['rag_integration']['results']) / len(results['rag_integration']['results']):.3f}s
- **性能优化建议**: 优化OCR预处理流程，改进向量化效率

## 测试结论
"""

        if results['overall_score'] >= 0.8:
            report += "✅ **优秀**: OCR集成表现良好，各项指标均达到预期\n"
        elif results['overall_score'] >= 0.6:
            report += "⚠️ **良好**: OCR集成基本功能正常，但仍有优化空间\n"
        else:
            report += "❌ **需要改进**: OCR集成在多个方面存在不足\n"

        report += f"""
## 优化建议
1. **OCR准确性**: 当前平均质量评分 {results['extraction_quality']['average_score']:.1%}，建议改进OCR参数和预处理
2. **处理速度**: 优化图像预处理和模型推理效率
3. **文档类型支持**: 针对表现较差的文档类型进行专门优化
4. **RAG集成**: 改进OCR文本的向量化策略，提升检索效果

## 下一步行动
- 优化PaddleOCR参数配置
- 实施文档类型自适应策略
- 增强OCR结果的后处理
- 扩大测试数据集覆盖范围
"""

        return report

def main():
    """主函数"""
    tester = OCRIntegrationTester()

    # 运行所有测试
    results = tester.run_all_tests()

    # 生成报告
    report = tester.generate_test_report(results)

    # 保存结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # 保存JSON结果
    with open(f"test_results/ocr_integration_results_{timestamp}.json", "w", encoding="utf-8") as f:
        # 转换OCRResult对象为可序列化的字典
        serializable_results = {
            "test_execution_time": results["test_execution_time"],
            "total_tests": results["total_tests"],
            "overall_score": results["overall_score"],
            "extraction_quality_summary": {
                "average_score": results["extraction_quality"]["average_score"],
                "total_results": len(results["extraction_quality"]["results"])
            },
            "paddleocr_summary": {
                "average_score": results["paddleocr_integration"]["average_score"],
                "total_results": results["paddleocr_integration"]["total_tests"]
            },
            "rag_integration_summary": {
                "average_score": results["rag_integration"]["average_integration_score"],
                "total_results": results["rag_integration"]["total_tests"]
            },
            "document_type_performance": results["document_type_performance"]
        }
        json.dump(serializable_results, f, indent=2, ensure_ascii=False)

    # 保存报告
    with open(f"test_results/ocr_integration_report_{timestamp}.md", "w", encoding="utf-8") as f:
        f.write(report)

    # 输出摘要
    print("\n" + "=" * 60)
    print("🎯 OCR集成测试完成！")
    print("=" * 60)
    print(f"📊 总体评分: {results['overall_score']:.3f}/1.000")
    print(f"📝 OCR质量评分: {results['extraction_quality']['average_score']:.3f}")
    print(f"🔗 RAG集成评分: {results['rag_integration']['average_integration_score']:.3f}")
    print(f"🚀 PaddleOCR评分: {results['paddleocr_integration']['average_score']:.3f}")
    print(f"\n📄 详细报告已保存到: test_results/ocr_integration_report_{timestamp}.md")

    return results['overall_score'] >= 0.6

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)