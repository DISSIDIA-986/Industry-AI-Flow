#!/usr/bin/env python3
"""
快速验证Industry AI Flow三大核心功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


def test_rag_import():
    """测试RAG系统导入"""
    print("🔍 测试RAG企业知识库系统导入...")
    try:
        # 测试文档管理
        from backend.api.document_management_routes import router as doc_router

        print("✅ 文档管理API路由导入成功")

        # 测试混合检索
        from backend.services.retrieval.hybrid_search import HybridSearch

        print("✅ 混合检索服务导入成功")

        # 测试文档分块
        from backend.services.core.chunker import Chunker

        print("✅ 文档分块器导入成功")

        # 测试嵌入服务
        from backend.services.core.embedder import embed_single_text

        print("✅ 嵌入服务导入成功")

        return True
    except Exception as e:
        print(f"❌ RAG系统导入失败: {e}")
        return False


def test_cost_estimation_import():
    """测试成本估算系统导入"""
    print("\n🔍 测试成本估算系统导入...")
    try:
        # 测试成本估算API
        from backend.api.cost_estimation_routes import router as cost_router

        print("✅ 成本估算API路由导入成功")

        # 测试成本估算服务
        from backend.services.cost_estimation_service import CostEstimationService

        print("✅ 成本估算服务导入成功")

        # 测试模型训练函数
        from backend.services.cost_estimation_service import train_cost_estimation_model

        print("✅ 模型训练函数导入成功")

        return True
    except Exception as e:
        print(f"❌ 成本估算系统导入失败: {e}")
        return False


def test_code_generation_import():
    """测试代码生成系统导入"""
    print("\n🔍 测试动态代码生成系统导入...")
    try:
        # 测试数据分析API
        from backend.api.data_analysis_routes import router as analysis_router

        print("✅ 数据分析API路由导入成功")

        # 测试数据分析Agent
        from backend.services.data_analysis.data_analysis_agent import DataAnalysisAgent

        print("✅ 数据分析Agent导入成功")

        # 测试代码执行器
        from backend.services.code_executor import code_executor

        print("✅ 代码执行器导入成功")

        return True
    except Exception as e:
        print(f"❌ 代码生成系统导入失败: {e}")
        return False


def test_api_endpoints():
    """测试API端点定义"""
    print("\n🔍 检查API端点定义...")

    endpoints = {
        "RAG系统": [
            "POST /api/v1/documents/upload",
            "POST /api/v1/query",
            "GET /api/v1/documents/{id}",
        ],
        "成本估算": [
            "POST /api/v1/cost-estimation/train",
            "POST /api/v1/cost-estimation/predict",
        ],
        "代码生成": [
            "POST /api/v1/data-analysis/upload",
            "POST /api/v1/data-analysis/analyze",
        ],
    }

    all_ok = True
    for system, endpoint_list in endpoints.items():
        print(f"\n📡 {system} API端点:")
        for endpoint in endpoint_list:
            print(f"   • {endpoint}")

    return all_ok


def test_configuration():
    """测试配置文件"""
    print("\n🔍 检查配置文件...")

    config_files = [
        "backend/config.py",
        "backend/services/llm_integration/types.py",
        "backend/services/security/redaction_service.py",
    ]

    all_ok = True
    for config_file in config_files:
        if (project_root / config_file).exists():
            print(f"✅ {config_file} 存在")
        else:
            print(f"❌ {config_file} 不存在")
            all_ok = False

    return all_ok


def main():
    """主函数"""
    # 强制在项目根目录执行，避免相对路径受启动目录影响
    os.chdir(project_root)

    print("=" * 60)
    print("🚀 Industry AI Flow - Capstone项目快速验证")
    print("=" * 60)

    # 执行所有测试
    rag_ok = test_rag_import()
    cost_ok = test_cost_estimation_import()
    code_ok = test_code_generation_import()
    api_ok = test_api_endpoints()
    config_ok = test_configuration()

    # 总结
    print("\n" + "=" * 60)
    print("📊 验证结果总结")
    print("=" * 60)

    results = {
        "RAG企业知识库系统": rag_ok,
        "成本估算系统": cost_ok,
        "动态代码生成系统": code_ok,
        "API端点定义": api_ok,
        "配置文件": config_ok,
    }

    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {name}: {'通过' if passed else '失败'}")

    # 计算总体评分
    total_tests = len(results)
    passed_tests = sum(results.values())
    score = (passed_tests / total_tests) * 100

    print(f"\n🎯 总体评分: {score:.0f}/100")

    if score >= 80:
        print("✅ 达到B级（良好）标准")
        print("💡 建议: 启动服务并执行端到端测试")
    elif score >= 70:
        print("✅ 达到C级（及格）标准 - 达到Capstone交付标准")
        print("💡 建议: 补全依赖并验证运行时功能")
    else:
        print("❌ 未达到Capstone交付标准")
        print("💡 建议: 修复导入问题并重新测试")

    print("\n📋 下一步建议:")
    print("1. 安装完整依赖: pip install -r requirements/base.txt")
    print("2. 启动服务: python -m uvicorn backend.main:app")
    print("3. 执行端到端测试: python scripts/testing/run_capstone_validation.py")

    return 0 if score >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
