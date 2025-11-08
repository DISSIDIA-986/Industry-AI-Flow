#!/usr/bin/env python3
"""
测试 RAG 数据分析节点的基础 EDA 功能
使用 Housing.csv 数据集进行验证
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from backend.tools.iterative_code_execution import iterative_code_analysis_tool
from backend.agents.code_execution_agent import iterative_code_agent
from backend.services.data_transfer import data_transfer

async def test_basic_eda():
    """测试基础探索性数据分析功能"""
    print("="*60)
    print("🔬 测试基础 EDA 功能 - Housing 数据集")
    print("="*60)

    data_file = "/Users/niuyp/Documents/github.com/Industry-AI-Flow/test_resources/datasets/Housing.csv"

    # 测试请求
    eda_request = """
    对房价数据集进行完整的探索性数据分析（EDA），包括：
    1. 数据概览和基本信息
    2. 缺失值统计和分析
    3. 数值特征的描述性统计
    4. 分类变量的分布分析
    5. 相关性分析和热力图
    6. 关键特征与房价的关系分析
    """

    print("📊 开始执行基础 EDA 分析...")
    print(f"📁 数据文件: {data_file}")
    print(f"🎯 分析请求: {eda_request.strip()}")
    print("-" * 60)

    try:
        # 使用可迭代代码分析工具
        result = iterative_code_analysis_tool.invoke({
            "request": eda_request,
            "data_file": data_file,
            "analysis_type": "eda",
            "max_attempts": 3,
            "transfer_method": "auto"
        })

        # 输出结果
        print("📈 EDA 分析结果:")
        print(f"✅ 执行成功: {result['success']}")
        print(f"🔄 尝试次数: {result.get('attempts', 0)}")

        if result['success']:
            print("\n📋 分析摘要:")
            summary = result.get('summary', {})
            if summary:
                print(f"   总尝试次数: {summary.get('total_attempts', 0)}")
                print(f"   执行成功: {summary.get('success', False)}")
                print(f"   错误次数: {summary.get('error_count', 0)}")
                print(f"   应用修复: {summary.get('fixes_applied', 0)}")

            print("\n💻 执行输出:")
            execution_result = result.get('execution_result', {})
            stdout = execution_result.get('stdout', '')
            if stdout:
                print("   标准输出:")
                for line in stdout.split('\n')[:20]:  # 只显示前20行
                    if line.strip():
                        print(f"   {line}")
                if len(stdout.split('\n')) > 20:
                    print("   ... (输出已截断)")

            print("\n📊 生成的可视化:")
            visualizations = execution_result.get('visualizations', [])
            if visualizations:
                print(f"   生成了 {len(visualizations)} 个可视化文件:")
                for viz in visualizations[:5]:  # 显示前5个
                    print(f"   - {viz.get('filename', 'unknown')} ({viz.get('type', 'unknown')})")
                if len(visualizations) > 5:
                    print(f"   ... 还有 {len(visualizations) - 5} 个文件")
            else:
                print("   未生成可视化文件")

            print("\n🔧 性能指标:")
            metrics = result.get('performance_metrics', {})
            if metrics:
                print(f"   执行时间: {metrics.get('execution_time', 0):.2f}秒")
                print(f"   可视化数量: {metrics.get('visualizations_generated', 0)}")
        else:
            print("\n❌ 分析失败:")
            print(f"   错误信息: {result.get('error', 'Unknown error')}")

            error_analysis = result.get('error_analysis', {})
            if error_analysis:
                print(f"   错误类型: {error_analysis.get('error_type', 'Unknown')}")
                suggestions = error_analysis.get('suggestions', [])
                if suggestions:
                    print("   修复建议:")
                    for suggestion in suggestions:
                        print(f"   - {suggestion}")

        return result

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return {"success": False, "error": str(e)}

def test_data_transfer():
    """测试数据传递功能"""
    print("\n" + "="*60)
    print("📦 测试数据传递功能")
    print("="*60)

    data_file = "/Users/niuyp/Documents/github.com/Industry-AI-Flow/test_resources/datasets/Housing.csv"

    try:
        # 测试文件传递
        print("🔄 测试文件传递...")
        transfer_result = data_transfer.transfer_file_for_docker(data_file, "auto")

        if transfer_result["success"]:
            print("✅ 数据传递成功!")
            print(f"   传递方式: {transfer_result['method']}")
            print(f"   文件大小: {transfer_result['file_info']['size_mb']} MB")
            print(f"   传递路径: {transfer_result['transferred_path']}")

            # 清理测试数据
            cleanup_success = data_transfer.cleanup_transferred_data(transfer_result)
            print(f"   清理成功: {cleanup_success}")

            return True
        else:
            print(f"❌ 数据传递失败: {transfer_result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ 数据传递测试异常: {e}")
        return False

def test_code_execution():
    """测试基础代码执行"""
    print("\n" + "="*60)
    print("⚙️ 测试基础代码执行")
    print("="*60)

    simple_code = """
import pandas as pd
import numpy as np

# 创建测试数据
data = {
    'A': [1, 2, 3, 4, 5],
    'B': [10, 20, 30, 40, 50],
    'C': ['X', 'Y', 'Z', 'X', 'Y']
}

df = pd.DataFrame(data)
print("数据形状:", df.shape)
print("\\n数据描述:")
print(df.describe())
print("\\n数据类型:")
print(df.dtypes)
"""

    try:
        from backend.tools.iterative_code_execution import self_healing_code_execution_tool

        print("🔄 执行基础 Python 代码...")
        result = self_healing_code_execution_tool.invoke({
            "code": simple_code,
            "description": "创建简单的测试数据集并显示基本信息"
        })

        print(f"✅ 执行成功: {result['success']}")
        print(f"🔄 尝试次数: {result['attempts']}")

        if result['success']:
            print("\n💻 执行输出:")
            stdout = result['execution_result']['stdout']
            if stdout:
                for line in stdout.split('\n'):
                    if line.strip():
                        print(f"   {line}")

            fixes = result.get('fixes_applied', [])
            if fixes:
                print(f"\n🔧 应用的修复: {fixes}")
        else:
            print(f"❌ 执行失败: {result.get('error', 'Unknown error')}")

        return result['success']

    except Exception as e:
        print(f"❌ 代码执行测试异常: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始 RAG 数据分析节点功能测试")
    print(f"📍 测试数据: Housing.csv")
    print(f"🔧 Python 版本: {sys.version}")

    # 测试1: 数据传递功能
    print("\n" + "="*60)
    print("测试 1/4: 数据传递功能")
    print("="*60)
    transfer_success = test_data_transfer()

    # 测试2: 基础代码执行
    print("\n" + "="*60)
    print("测试 2/4: 基础代码执行")
    print("="*60)
    code_exec_success = test_code_execution()

    # 测试3: 基础 EDA
    print("\n" + "="*60)
    print("测试 3/4: 基础 EDA 功能")
    print("="*60)
    eda_result = await test_basic_eda()

    # 测试总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    print(f"✅ 数据传递: {'成功' if transfer_success else '失败'}")
    print(f"✅ 代码执行: {'成功' if code_exec_success else '失败'}")
    print(f"✅ EDA 功能: {'成功' if eda_result.get('success', False) else '失败'}")

    overall_success = transfer_success and code_exec_success and eda_result.get('success', False)

    if overall_success:
        print("\n🎉 所有测试通过! RAG 数据分析节点功能正常")
        print("📈 系统已准备好进行高级数据分析任务")
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试")

    return overall_success

if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())
    sys.exit(0 if success else 1)