"""
llama.cpp 简单测试
验证 llama.cpp 客户端功能
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import time


def test_llama_cpp_client():
    """测试 llama.cpp 客户端"""
    print("=" * 80)
    print("llama.cpp 客户端测试")
    print("=" * 80)
    print()

    try:
        from backend.services.llama_cpp_client import LlamaCppClient
        from backend.config import settings

        print(f"[1/4] 配置检查...")
        print(f"   模型路径: {settings.llama_model_path}")
        print(f"   上下文大小: {settings.llama_context_size}")
        print(f"   GPU层数: {settings.llama_gpu_layers}")
        print()

        print(f"[2/4] 初始化客户端...")
        start_time = time.time()
        client = LlamaCppClient()
        init_time = time.time() - start_time
        print(f"✅ 客户端初始化成功 (耗时: {init_time:.2f}秒)")
        print()

        print(f"[3/4] 测试文本生成...")
        test_prompts = [
            "你好",
            "什么是人工智能？",
            "解释一下RAG系统的工作原理。"
        ]

        for i, prompt in enumerate(test_prompts, 1):
            print(f"   测试 {i}/{len(test_prompts)}: {prompt}")

            start_time = time.time()
            response = client.generate(
                prompt=prompt,
                max_tokens=100,
                temperature=0.7
            )
            gen_time = time.time() - start_time

            token_count = len(response.split())
            print(f"   ✅ 生成成功 (耗时: {gen_time:.2f}秒, 词数: {token_count})")
            print(f"   响应: {response[:150]}...")
            print()

        print(f"[4/4] 获取模型信息...")
        model_info = client.get_model_info()
        print(f"✅ 模型信息:")
        for key, value in model_info.items():
            print(f"   {key}: {value}")
        print()

        print("=" * 80)
        print("🎉 llama.cpp 客户端测试通过！")
        print("=" * 80)
        print()
        print("性能特点:")
        print("  • 本地推理，无需网络请求")
        print("  • Apple Silicon Metal 加速")
        print("  • 低延迟，高吞吐量")
        print("  • 直接使用 Ollama 的 GGUF 模型")
        print()

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_llama_cpp_client()
    sys.exit(0 if success else 1)
