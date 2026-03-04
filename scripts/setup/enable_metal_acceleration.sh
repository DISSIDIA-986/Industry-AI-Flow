#!/bin/bash
# 启用 llama-cpp-python Metal 加速的脚本
# 用于 Apple Silicon (M1/M2/M3) Mac

set -e

echo "=== 安装 llama-cpp-python with Metal 加速 ==="
echo ""

# 1. 设置环境变量
export CMAKE_ARGS="-DGGML_METAL=on -DCMAKE_OSX_ARCHITECTURES=arm64"
export CMAKE_PREFIX_PATH="$(pwd)"

echo "环境变量已设置："
echo "  CMAKE_ARGS=$CMAKE_ARGS"
echo "  CMAKE_PREFIX_PATH=$CMAKE_PREFIX_PATH"
echo ""

# 2. 卸载旧版本（如果存在）
echo "检查并卸载旧版本..."
.venv/bin/pip uninstall llama-cpp-python -y 2>/dev/null || echo "  未安装旧版本"
echo ""

# 3. 安装 Metal 版本
echo "安装 llama-cpp-python (Metal 支持)..."
.venv/bin/pip install --no-cache-dir --force-reinstall llama-cpp-python==0.2.90

echo ""
echo "=== 验证安装 ==="
.venv/bin/python -c "
import llama_cpp
print('✅ llama-cpp-python 安装成功!')
print(f'版本: {llama_cpp.__version__}')

# 检查 Metal 支持
import llama_cpp.llama_cpp as llama
print(f'GGML 版本: {llama.ggml_print_system_info()}')
"

echo ""
echo "=== 配置完成 ==="
echo ""
echo "现在可以使用以下方式启用 Metal 加速："
echo ""
echo "1. 在代码中切换到 llama_cpp 后端："
echo "   export LLM_BACKEND=llama_cpp"
echo ""
echo "2. 在 Ollama 中使用较小的模型："
echo "   export OLLAMA_MODEL=qwen3.5:4b"
echo ""
echo "3. 重启应用服务器"
echo ""
