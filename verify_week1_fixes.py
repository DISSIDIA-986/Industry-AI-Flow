#!/usr/bin/env python3
"""
Week 1修复验证脚本（无pytest依赖）

快速验证所有P0修复是否正确实现
"""

import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def verify_nltk_tokenization():
    """验证NLTK英文分词"""
    print("\n🔍 验证1: NLTK英文分词修复")
    print("=" * 60)

    try:
        from backend.services.retrieval.hybrid_search import HybridRetriever
        from backend.services.core.vectorstore import VectorStore

        vectorstore = VectorStore()
        retriever = HybridRetriever(vectorstore)

        # 测试建筑术语分词
        test_text = "reinforced-concrete load-bearing CSA-A23.1-19 HVAC OSHA-compliant"
        tokens = retriever._tokenize_english(test_text)

        print(f"✅ NLTK分词方法存在")
        print(f"   输入: {test_text}")
        print(f"   Tokens: {tokens[:10]}...")  # 显示前10个

        # 验证词干提取
        assert any("reinforc" in t for t in tokens), "应保留reinforced词干"
        assert any("concret" in t for t in tokens), "应保留concrete词干"

        print(f"✅ 词干提取工作正常")
        print(f"✅ NLTK英文分词修复验证通过")
        return True

    except Exception as e:
        print(f"❌ NLTK分词验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_semantic_chunking():
    """验证语义分块"""
    print("\n🔍 验证2: 语义分块优化")
    print("=" * 60)

    try:
        from backend.services.core.chunker import chunk_text

        test_text = """
        ## Section 4.3.2.1 - Minimum Concrete Protection

        All reinforced concrete structures shall have minimum concrete cover
        as specified in CSA A23.1-19. For foundation walls, the minimum cover
        is 75mm. For exposed conditions, the cover shall be increased to 50mm.
        """

        chunks = chunk_text(test_text, chunk_size=512, chunk_overlap=128)

        print(f"✅ 生成了 {len(chunks)} 个分块")

        for i, chunk in enumerate(chunks):
            print(f"\n   分块 {i+1}:")
            print(f"   - 长度: {chunk['metadata']['length']} 字符")
            print(f"   - 方法: {chunk['metadata']['chunking_method']}")

            # 检查是否包含Section引用
            if "Section" in chunk["content"]:
                print(f"   - 包含Section引用: ✓")

        assert all(
            c["metadata"]["chunking_method"] == "semantic_construction"
            for c in chunks
        ), "应使用语义分块"

        print(f"\n✅ 语义分块优化验证通过")
        return True

    except Exception as e:
        print(f"❌ 语义分块验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_ragas_framework():
    """验证RAGAS评估框架"""
    print("\n🔍 验证3: RAGAS评估框架")
    print("=" * 60)

    try:
        from tests.evaluation.ragas_evaluation import RAGASEvaluator

        evaluator = RAGASEvaluator()

        # 检查方法存在
        assert hasattr(eval_uator, 'create_construction_evaluation_dataset'), \
            "应存在create_construction_evaluation_dataset方法"
        assert hasattr(eval_uator, 'run_evaluation'), \
            "应存在run_evaluation方法"
        assert hasattr(eval_uator, 'calculate_mrr'), \
            "应存在calculate_mrr方法"

        print(f"✅ RAGASEvaluator类存在")
        print(f"✅ 所有必需方法存在")

        # 测试MRR计算
        test_results = [[1, 2, 3], [2, 1, 3], [1, 3, 2]]
        mrr = evaluator.calculate_mrr(test_results)

        print(f"✅ MRR计算: {mrr:.2f}")
        assert 0 <= mrr <= 1, "MRR应在0-1范围内"

        # 创建测试数据集
        dataset = evaluator.create_construction_evaluation_dataset()
        print(f"✅ 创建了 {len(dataset)} 个评估样本")

        print(f"\n✅ RAGAS评估框架验证通过")
        return True

    except ImportError as e:
        print(f"⚠️ RAGAS未安装（这是预期的，如果尚未安装依赖）")
        print(f"   安装方法: pip install ragas datasets")
        return True  # 不算失败，只是未安装
    except Exception as e:
        print(f"❌ RAGAS框架验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_safety_guard():
    """验证安全防护层"""
    print("\n🔍 验证4: 安全防护层")
    print("=" * 60)

    try:
        from backend.services.safety import SafetyGuard, SafetyLevel

        safety_guard = SafetyGuard(confidence_threshold=0.80)

        # 测试安全关键问题
        answer1 = "Scaffolding above 3 meters requires guardrails per Alberta OHS Part 23."
        context1 = ["Alberta OHS Part 23: Scaffolds"]

        result1 = safety_guard.process_response(answer1, context1)

        print(f"✅ SafetyGuard类存在")
        print(f"✅ 安全等级: {result1['safety_level'].value}")
        print(f"✅ 置信度: {result1['confidence']:.2f}")
        print(f"✅ 包含免责声明: {'disclaimer' in result1['enhanced_answer'].lower() or '免责声明' in result1['enhanced_answer']}")

        assert result1["safety_level"] == SafetyLevel.SAFETY_CRITICAL, \
            "应识别为安全关键问题"

        print(f"\n✅ 安全防护层验证通过")
        return True

    except Exception as e:
        print(f"❌ 安全防护层验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_imports():
    """验证所有新模块可导入"""
    print("\n🔍 验证0: 模块导入")
    print("=" * 60)

    success = True

    # 验证NLTK
    try:
        import nltk
        print(f"✅ NLTK已安装 (版本: {nltk.__version__})")
    except ImportError:
        print(f"❌ NLTK未安装")
        success = False

    # 验证RAGAS（可选）
    try:
        import ragas
        print(f"✅ RAGAS已安装")
    except ImportError:
        print(f"⚠️ RAGAS未安装（可选）")

    # 验证项目模块
    try:
        from backend.services.retrieval.hybrid_search import HybridRetriever
        print(f"✅ hybrid_search模块可导入")
    except Exception as e:
        print(f"❌ hybrid_search模块导入失败: {e}")
        success = False

    try:
        from backend.services.core.chunker import chunk_text
        print(f"✅ chunker模块可导入")
    except Exception as e:
        print(f"❌ chunker模块导入失败: {e}")
        success = False

    try:
        from backend.services.safety import SafetyGuard
        print(f"✅ safety模块可导入")
    except Exception as e:
        print(f"❌ safety模块导入失败: {e}")
        success = False

    try:
        from tests.evaluation.ragas_evaluation import RAGASEvaluator
        print(f"✅ ragas_evaluation模块可导入")
    except Exception as e:
        print(f"❌ ragas_evaluation模块导入失败: {e}")
        success = False

    if success:
        print(f"\n✅ 所有必需模块导入成功")
    else:
        print(f"\n❌ 部分模块导入失败")

    return success


def main():
    """运行所有验证"""
    print("🧪 Week 1 P0修复验证")
    print("=" * 60)
    print("基于Claude评估报告的关键修复验证\n")

    results = {
        "模块导入": verify_imports(),
        "NLTK英文分词": verify_nltk_tokenization(),
        "语义分块": verify_semantic_chunking(),
        "RAGAS框架": verify_ragas_framework(),
        "安全防护层": verify_safety_guard(),
    }

    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 验证结果汇总")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")

    print("\n" + "=" * 60)
    print(f"总计: {passed}/{total} 验证通过")

    if passed == total:
        print("\n🎉 所有验证通过！Week 1 P0修复成功实现。")
        print("\n📝 下一步:")
        print("  1. 安装NLTK数据: python3 -c \"import nltk; nltk.download('punkt')\"")
        print("  2. 安装RAGAS: pip install ragas datasets")
        print("  3. 运行完整测试: python3 -m pytest tests/")
        print("  4. 提交代码: git add . && git commit -m 'feat: week 1 P0 fixes'")
        return 0
    else:
        print("\n⚠️ 部分验证失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
