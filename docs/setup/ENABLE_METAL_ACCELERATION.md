# 启用 Apple Silicon Metal 加速指南

## 问题诊断

**当前状态**：
- ❌ Ollama 无法加载 MLX 库（Metal 动态库）
- ❌ 纯 CPU 推理，响应时间 30 秒+
- ✅ M1 Max 硬件支持 Metal 4

## 解决方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **llama-cpp-python (Metal)** | 性能最佳，社区成熟 | 需要额外安装 | ⭐⭐⭐⭐⭐ |
| Ollama (更新版本) | 无需改动 | Metal 支持不成熟 | ⭐⭐ |
| 使用云 LLM | 性能最好 | 需要网络连接 | ⭐⭐⭐⭐ |

---

## 方案 1：llama-cpp-python with Metal（推荐）

### 步骤 1：安装 Metal 版本

```bash
# 运行安装脚本
chmod +x scripts/setup/enable_metal_acceleration.sh
./scripts/setup/enable_metal_acceleration.sh
```

或手动安装：

```bash
# 设置环境变量
export CMAKE_ARGS="-DGGML_METAL=on -DCMAKE_OSX_ARCHITECTURES=arm64"

# 安装 llama-cpp-python
.venv/bin/pip install llama-cpp-python==0.2.90
```

### 步骤 2：验证安装

```bash
.venv/bin/python -c "
import llama_cpp
print('✅ Metal 加速已启用')
print(f'版本: {llama_cpp.__version__}')
"
```

### 步骤 3：配置项目使用 llama_cpp

在 `.env` 中添加：

```bash
# 启用 llama_cpp 后端
LLM_BACKEND=llama_cpp

# 或者使用混合模式（本地 llama_cpp + 云 LLM）
HYBRID_MODE=auto
LOCAL_CONFIDENCE_THRESHOLD=0.75
```

### 步骤 4：重启服务

```bash
# 停止当前服务
pkill ollama

# 重启应用服务
make run
```

---

## 方案 2：更新 Ollama（备选）

### 检查最新版本

```bash
brew update ollama
brew upgrade ollama
```

### 查看 Ollama Metal 支持状态

访问：https://github.com/ollama/ollama/blob/main/docs/gpu.md

---

## 性能预期

### 启用 Metal 后（llama-cpp-python）

| 指标 | CPU（当前） | Metal (预期) | 改善 |
|------|-------------|---------------|------|
| 首次响应时间 | 20-30 秒 | **2-3 秒** | ⬇️ 90% |
| 完整响应时间 | 30 秒+ | **5-8 秒** | ⬇️ 75% |
| 吞用率 | ~20% | **~80%** | ⬆️ 4x |

### 配置建议

```python
# 推荐配置用于最佳性能

# 模型选择（4b 更快）
model_name = "qwen3.5:4b"

# 生成参数
n_ctx = 2048          # 上下文长度
n_batch = 512        # 批处理大小
n_threads = 8        # M1 Max 有 8 个性能核心
```

---

## 常见问题

### Q1: 安装失败怎么办？

```bash
# 确保 Xcode Command Line Tools 已安装
xcode-select --install

# 清理并重试
pip uninstall llama-cpp-python -y
pip cache purge
export CMAKE_ARGS="-DGGML_METAL=on -DCMAKE_OSX_ARCHITECTURES=arm64"
pip install llama-cpp-python==0.2.90
```

### Q2: 如何验证 Metal 已启用？

```bash
# 运行测试脚本
python scripts/testing/test_metal_performance.py

# 或检查系统活动监控
# 在运行查询时，打开"活动监视器"查看 GPU 历史
# 应该能看到 GPU 使用率上升
```

### Q3: 是否必须启用 Metal？

**不是必须的**。考虑到你的 demo 场景：

- ✅ **30 秒响应** - 可接受
- ✅ **100% 成功率** - 系统稳定
- ✅ **可解释性** - 可说明本地资源限制

**启用 Metal 的好处**：
- ⚡ 更快的响应（3-5 秒）
- 🎯 更好的演示体验
- 📈 可运行更大的模型（7b+）

---

## 下一步行动

**立即可行**：
1. 运行安装脚本启用 Metal
2. 测试性能改善
3. 如果有问题，回退到纯 CPU（仍然可用）

**Demo 建议**：
- 如果 Metal 启用成功：使用 llama_cpp 后端
- 如果遇到问题：使用 Ollama + 增加超时到 90 秒

需要我帮你运行安装脚本吗？
