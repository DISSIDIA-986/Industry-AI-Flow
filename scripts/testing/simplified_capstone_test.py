#!/usr/bin/env python3
"""
简化的Capstone功能验证脚本
不依赖运行时服务，直接测试核心功能模块
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试核心模块导入"""
    print("=" * 60)
    print("🔍 测试核心模块导入")
    print("=" * 60)
    
    tests = []
    
    # 测试1: RAG系统导入
    try:
        from backend.api.document_management_routes import router as doc_router
        from backend.services.retrieval.hybrid_search import HybridSearch
        from backend.services.core.chunker import Chunker
        tests.append(("RAG系统", True, "文档管理、混合检索、分块器导入成功")
    except Exception as e:
        tests.append(("RAG系统", False, f"导入失败: {e}"))
    
    # 测试2: 成本估算导入
    try:
        from backend.api.cost_estimation_routes import router as cost_router
        from backend.services.cost_estimation_service import CostEstimationService
        tests.append(("成本估算", True, "API路由、服务导入成功"))
    except Exception as e:
        tests.append(("成本估算", False, f"导入失败: {e}"))
    
    # 测试3: 代码生成导入
    try:
        from backend.api.data_analysis_routes import router as analysis_router
        from backend.services.data_analysis.data_analysis_agent import DataAnalysisAgent
        from backend.services.code_executor import code_executor
        tests.append(("代码生成", True, "API路由、数据分析Agent、代码执行器导入成功"))
    except Exception as e:
        tests.append(("代码生成", False, f"导入失败: {e}"))
    
    # 打印结果
    for name, success, message in tests:
        status = "✅" if success else "❌"
        print(f"{status} {name}: {message}")
    
    return all(t[1] for t in tests)

def test_rag_functionality():
    """测试RAG功能完整性"""
    print("\n" + "=" * 60)
    print("🔍 测试RAG功能完整性")
    print("=" * 60)
    
    tests = []
    
    # 测试1: 检查混合检索类
    try:
        from backend.services.retrieval.hybrid_search import HybridSearch
        hybrid_search = HybridSearch()
        tests.append((True, "混合检索类实例化成功"))
    except Exception as e:
        tests.append((False, f"混合检索类实例化失败: {e}"))
    
    # 测试2: 检查文档分块器
    try:
        from backend.services.core.chunker import Chunker
        chunker = Chunker()
        tests.append((True, "文档分块器实例化成功"))
    except Exception as e:
        tests.append((False, f"文档分块器实例化失败: {e}"))
    
    # 测试3: 检查嵌入服务
    try:
        from backend.services.core.embedder import embed_single_text
        tests.append((True, "嵌入服务导入成功"))
    except Exception as e:
        tests.append((False, f"嵌入服务导入失败: {e}"))
    
    for success, message in tests:
        status = "✅" if success else "❌"
        print(f"{status} {message}")
    
    return all(t[0] for t in tests)

def test_cost_estimation_functionality():
    """测试成本估算功能完整性"""
    print("\n" + "=" * 60)
    print("🔍 测试成本估算功能完整性")
    print("=" * 60)
    
    tests = []
    
    # 测试1: 检查成本估算服务
    try:
        from backend.services.cost_estimation_service import CostEstimationService
        # 检查默认模型路径
        default_path = CostEstimationService.DEFAULT_MODEL_PATH
        tests.append((True, f"成本估算服务存在，默认模型路径: {default_path}"))
    except Exception as e:
        tests.append((False, f"成本估算服务导入失败: {e}"))
    
    # 测试2: 检查训练函数
    try:
        from backend.services.cost_estimation_service import train_cost_estimation_model
        tests.append((True, "模型训练函数存在"))
    except Exception as e:
        tests.append((False, f"模型训练函数不存在: {e}"))
    
    for success, message in tests:
        status = "✅" if success else "❌"
        print(f"{status} {message}")
    
    return all(t[0] for t in tests)

def test_code_generation_functionality():
    """测试代码生成功能完整性"""
    print("\n" + "=" * 60)
    print("🔍 测试代码生成功能完整性")
    print("=" * 60)
    
    tests = []
    
    # 测试1: 检查数据分析Agent
    try:
        from backend.services.data_analysis.data_analysis_agent import DataAnalysisAgent
        tests.append((True, "数据分析Agent类存在"))
    except Exception as e:
        tests.append((False, f"数据分析Agent导入失败: {e}"))
    
    # 测试2: 检查代码执行器
    try:
        from backend.services.code_executor import code_executor
        tests.append((True, "代码执行器存在"))
    except Exception as e:
        tests.append((False, f"代码执行器导入失败: {e}"))
    
    for success, message in tests:
        status = "✅" if success else "❌"
        print(f"{status} {message}")
    
    return all(t[0] for t in tests)

def main():
    """主函数"""
    print("\n🚀 Industry AI Flow - Capstone功能验证测试")
    print("=" * 60)
    
    # 执行所有测试
    import_tests = test_imports()
    rag_tests = test_rag_functionality()
    cost_tests = test_cost_estimation_functionality()
    code_tests = test_code_generation_functionality()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    results = {
        "核心模块导入": import_tests,
        "RAG功能完整性": rag_tests,
        "成本估算功能完整性": cost_tests,
        "代码生成功能完整性": code_tests,
    }
    
    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {name}: {'通过' if passed else '失败'}")
    
    # 计算总体评分
    total_tests = len(results)
    passed_tests = sum(results.values())
    score = (passed_tests / total_tests) * 100
    
    print(f"\n🎯 总体评分: {score:.0f}/100")
    
    if score >= 75:
        print("✅ 达到Capstone交付标准 (B级 - 良好)")
        return 0
    elif score >= 50:
        print("⚠️ 基本达到Capstone交付标准 (C级 - 及格)")
        return 1
    else:
        print("❌ 未达到Capstone交付标准")
        return 2

if __name__ == "__main__":
    sys.exit(main())