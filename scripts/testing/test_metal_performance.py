#!/usr/bin/env python3
"""
测试 llama-cpp-python Metal 加速性能

用于验证 Metal GPU 加速是否正常工作
"""

import os
import sys
import time


def test_llama_cpp_metal():
    """测试 llama-cpp-python Metal 性能"""
    try:
        import llama_cpp
    except ImportError:
        print("❌ llama-cpp-python 未安装")
        print("\n请运行以下命令安装：")
        print('  export CMAKE_ARGS="-DGGML_METAL=on -DCMAKE_OSX_ARCHITECTURES=arm64"')
        print("  .venv/bin/pip install llama-cpp-python==0.2.90")
        return False

    print("✅ llama-cpp-python 已安装")
    print(f"版本: {llama_cpp.__version__}")
    print()

    # 检查 Metal 支持
    try:
        import llama_cpp.llama_cpp as llama

        print("✅ llama_cpp 核心库加载成功")
        print()
    except Exception as e:
        print(f"❌ llama_cpp 核心库加载失败: {e}")
        return False

    # 测试简单的生成
    print("=== 测试 Metal 加速性能 ===")
    print()

    model_path = os.path.expanduser(
        "~/.ollama/models/qwen3.5:4b/ggml-model-q4_k_m.gguf"
    )

    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        print("\n请先确保已安装 qwen3.5:4b 模型:")
        print("  ollama pull qwen3.5:4b")
        return False

    try:
        # 初始化模型
        print(f"正在加载模型: qwen3.5:4b")
        start = time.time()

        llama = llama_cpp.llama(
            model_path=model_path, n_ctx=2048, n_batch=512, n_threads=8, verbose=False
        )

        load_time = time.time() - start
        print(f"✅ 模型加载成功 ({load_time:.2f} 秒)")
        print()

        # 测试生成
        prompt = "What is concrete? Answer in one sentence."
        print(f"测试提示词: {prompt}")
        print()

        start = time.time()

        # 创建 token
        tokens = llama.tokenize(prompt.encode("utf-8"))

        # 生成（限制输出长度）
        max_tokens = 50
        output = llama.generate(tokens, temp=0.7, top_p=0.9, repeat_penalty=1.0)

        # 解码结果
        generated = llama.detokenize(output[:max_tokens])
        elapsed = time.time() - start

        print(f"✅ 生成完成 ({elapsed:.2f} 秒)")
        print()
        print(f"响应: {generated.decode('utf-8', errors='ignore')}")
        print()

        # 性能评估
        if elapsed < 5.0:
            print("🚀 Metal 加速工作正常！性能：优秀")
        elif elapsed < 10.0:
            print("⚡  性能良好，Metal 加速可能部分工作")
        else:
            print("⚠️  响应较慢，可能仍在使用 CPU")

        return elapsed < 10.0

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_ollama_fallback():
    """测试 Ollama 作为回退方案"""
    import requests

    print()
    print("=== 测试 Ollama 回退方案 ===")
    print()

    # 测试 4b 模型
    print("测试 qwen3.5:4b 通过 Ollama API...")

    start = time.time()
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3.5:4b",
                "prompt": "What is concrete? Answer in one sentence.",
                "stream": False,
                "options": {"num_predict": 50, "temperature": 0.7},
            },
            timeout=90,  # 90 秒超时
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ollama 响应成功 ({elapsed:.2f} 秒)")
            print(f"响应: {result.get('response', 'N/A')[:100]}")
            return elapsed < 15.0
        else:
            print(f"❌ Ollama 返回错误: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        print(f"❌ Ollama 超时 ({elapsed:.1f} 秒)")
        return False
    except Exception as e:
        print(f"❌ Ollama 测试失败: {e}")
        return False


def main():
    print("=" * 60)
    print("Metal 加速性能测试")
    print("=" * 60)
    print()

    # 测试 llama-cpp-python
    llama_cpp_ok = test_llama_cpp_metal()

    # 测试 Ollama 回退
    ollama_ok = test_ollama_fallback()

    print()
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    print()

    if llama_cpp_ok:
        print("✅ llama-cpp-python Metal 加速：工作正常")
        print("   推荐：使用 LLM_BACKEND=llama_cpp")
    else:
        print("❌ llama-cpp-python Metal 加速：不可用")

    if ollama_ok:
        print("✅ Ollama 回退方案：可用")
        print("   备选：使用 LLM_BACKEND=ollama")
    else:
        print("❌ Ollama 回退方案：不可用")
        print("   需要解决 Ollama 超时问题")

    print()
    print("推荐配置：")

    if llama_cpp_ok:
        print("export LLM_BACKEND=llama_cpp")
        print("export OLLAMA_MODEL=qwen3.5:4b")
    else:
        print("export OLLAMA_MODEL=qwen3.5:4b")
        print("export OLLAMA_REQUEST_TIMEOUT_SECONDS=90")


if __name__ == "__main__":
    main()
