# 智谱AI集成指南

## 概述

本系统已集成智谱AI（通过Anthropic兼容接口），支持在本地Ollama和云端智谱AI之间灵活切换。

## 配置步骤

### 1. 获取智谱API密钥

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册/登录账号
3. 创建API密钥

### 2. 配置环境变量

创建 `.env` 文件（基于 `.env.example`）：

```bash
# 复制配置模板
cp .env.example .env
```

编辑 `.env` 文件，添加智谱配置：

```bash
# 智谱AI配置
ZHIPU_API_KEY=你的智谱API密钥
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/anthropic
ZHIPU_MODEL=glm-4-plus  # 推荐使用glm-4-plus，性能最佳
API_TIMEOUT_MS=3000000

# 切换到智谱AI
LLM_PROVIDER=zhipu
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

## 支持的模型

智谱AI提供多个GLM-4系列模型：

| 模型名称 | 特点 | 适用场景 |
|---------|------|---------|
| `glm-4-plus` | 最强性能，支持128K上下文 | 复杂推理、长文档分析 |
| `glm-4-air` | 平衡性能与成本 | 日常对话、文档问答 |
| `glm-4-flash` | 极速响应，低成本 | 简单查询、高并发场景 |

## 使用示例

### 基础使用

```python
from backend.agents.rag_agent import rag_agent

# Agent会自动使用配置的LLM提供商（Ollama或智谱）
result = rag_agent.invoke({
    "messages": [],
    "question": "什么是LangChain 1.0的主要改进？"
})

print(result["final_answer"])
```

### 切换提供商

通过修改 `.env` 文件中的 `LLM_PROVIDER` 变量：

```bash
# 使用本地Ollama
LLM_PROVIDER=ollama

# 使用智谱AI
LLM_PROVIDER=zhipu
```

## API兼容性说明

智谱AI支持两种API格式：

1. **OpenAI兼容接口** (`/v1/chat/completions`)
2. **Anthropic兼容接口** (`/api/anthropic`) ← **本项目采用**

本项目使用Anthropic兼容接口的原因：
- ✅ LangChain原生支持 `langchain-anthropic` 包
- ✅ 无需额外适配，开箱即用
- ✅ 支持流式输出、工具调用等高级特性

## 性能对比

| 特性 | Ollama (本地) | 智谱AI (云端) |
|-----|-------------|--------------|
| 延迟 | <1s (本地推理) | 2-5s (网络延迟) |
| 成本 | 免费 (硬件成本) | 按调用量付费 |
| 模型能力 | Qwen2.5-7B | GLM-4-Plus (更强) |
| 隐私 | 完全本地 | 云端处理 |
| 稳定性 | 依赖本地资源 | 高可用保障 |

## 故障排查

### 问题1：API密钥错误

```
Error: Invalid API key
```

**解决方案**：
1. 检查 `.env` 文件中的 `ZHIPU_API_KEY` 是否正确
2. 确认API密钥未过期
3. 访问智谱AI控制台验证密钥状态

### 问题2：超时错误

```
Error: Request timeout
```

**解决方案**：
1. 增加 `API_TIMEOUT_MS` 值（默认3000000ms = 50分钟）
2. 检查网络连接
3. 降低请求复杂度（减少上下文长度）

### 问题3：模型不存在

```
Error: Model not found
```

**解决方案**：
1. 检查 `ZHIPU_MODEL` 是否为支持的模型名称
2. 访问智谱AI文档确认可用模型列表

## 最佳实践

### 1. 开发阶段
- 使用 `LLM_PROVIDER=ollama` (本地Ollama)
- 快速迭代，无API调用成本
- 适合调试和测试

### 2. 生产阶段
- 使用 `LLM_PROVIDER=zhipu` (智谱AI)
- 模型能力更强，响应质量更高
- 需要监控API调用量和成本

### 3. 混合使用
- Embedding: 使用本地 `sentence-transformers`
- 检索排序: 使用本地BM25 + 重排序模型
- 最终生成: 使用智谱AI GLM-4-Plus

这样可以平衡成本和性能，只在关键步骤使用云端API。

## 相关文档

- [智谱AI官方文档](https://open.bigmodel.cn/dev/api)
- [LangChain Anthropic集成](https://python.langchain.com/docs/integrations/chat/anthropic)
- [LangChain 1.0迁移指南](./LANGCHAIN_1_0_MIGRATION_PROGRESS.md)

## 贡献与反馈

如有问题或建议，请提交Issue或Pull Request。
