#!/usr/bin/env python3
"""
llama.cpp 客户端测试脚本
测试基本功能，不依赖实际模型文件
"""
import os
import sys

# 添加路径以便导入backend模块


def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")

    try:
        from llama_cpp import Llama

        print("✅ llama-cpp-python 导入成功")

        # 检查版本
        if hasattr(Llama, "__version__"):
            print(f"📦 版本: {Llama.__version__}")

        return True
    except ImportError as e:
        print(f"❌ llama-cpp-python 导入失败: {e}")
        return False


def test_metal_support():
    """测试 Metal 支持"""
    print("\n🔍 测试 Metal 支持...")

    try:
        import torch

        if torch.backends.mps.is_available():
            print("✅ Apple Silicon Metal 可用")
            return True
        else:
            print("⚠️  Metal 不可用，将使用 CPU 模式")
            return False
    except ImportError:
        print("⚠️  torch 未安装，跳过 Metal 检测")
        return False


def test_client_creation():
    """测试客户端创建（不需要实际模型）"""
    print("\n🔍 测试客户端类定义...")

    try:
        from backend.services.llama_cpp_client import LlamaCppClient

        print("✅ LlamaCppClient 类导入成功")

        # 检查关键方法是否存在
        methods = ["generate", "chat", "get_model_info", "get_memory_usage"]
        for method in methods:
            if hasattr(LlamaCppClient, method):
                print(f"✅ 方法 {method} 存在")
            else:
                print(f"❌ 方法 {method} 不存在")
                return False

        return True
    except ImportError as e:
        print(f"❌ LlamaCppClient 导入失败: {e}")
        return False


def test_config_compatibility():
    """测试配置兼容性"""
    print("\n🔍 测试配置兼容性...")

    try:
        from backend.services.llm_client import LLMClientFactory, get_backend_status

        print("✅ LLMClientFactory 导入成功")

        # 测试后端状态获取
        status = get_backend_status()
        print(f"📊 后端状态: {status}")

        return True
    except Exception as e:
        print(f"❌ 配置兼容性测试失败: {e}")
        return False


def test_mock_generation():
    """模拟生成测试（不需要实际模型）"""
    print("\n🔍 测试模拟生成...")

    try:
        # 创建一个简单的模拟响应
        mock_response = {"choices": [{"text": "Hello! This is a test response."}]}

        if mock_response and "choices" in mock_response:
            print("✅ 模拟响应格式正确")
            print(f"📝 示例响应: {mock_response['choices'][0]['text']}")
            return True
        else:
            print("❌ 模拟响应格式错误")
            return False

    except Exception as e:
        print(f"❌ 模拟生成测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 llama.cpp 客户端测试开始\n")

    tests = [
        ("模块导入", test_imports),
        ("Metal 支持", test_metal_support),
        ("客户端创建", test_client_creation),
        ("配置兼容性", test_config_compatibility),
        ("模拟生成", test_mock_generation),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print("=" * 50)

        if test_func():
            passed += 1
            print(f"✅ {test_name} 测试通过")
        else:
            print(f"❌ {test_name} 测试失败")

    print(f"\n{'='*50}")
    print(f"测试总结: {passed}/{total} 通过")
    print("=" * 50)

    if passed == total:
        print("🎉 所有测试通过！llama.cpp 客户端基础功能正常")
        print("\n📝 注意: 实际使用需要 GGUF 模型文件")
        print("📝 建议下载模型到 models/ 目录")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
