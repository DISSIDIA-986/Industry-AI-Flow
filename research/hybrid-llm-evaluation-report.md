# 本地 LLM + 云端 LLM 混合方案可行性与成本评估

> **调研日期**: 2026-02-07
> **项目**: Industry-AI-Flow (SAIT Capstone × Construction School)
> **当前架构**: Qwen2.5:7b (Ollama/llama.cpp) + nomic-embed-v1.5 + pgvector + PaddleOCR

---

## 结论先行

**推荐方案：极简混合（Simplified Hybrid）—— 确定性元数据提取 + 云端代码生成 + 本地沙箱执行**

混合方案在你的场景下**技术上完全可行且成本几乎可忽略**，但关键洞察是：

1. **元数据提取不需要 LLM**。用确定性 Python 代码（`df.describe()` + `df.dtypes` + `df.head()`）提取数据特征，比用本地 LLM 更快、更可靠、零幻觉风险。用 LLM 做这一步是「过度设计陷阱」。
2. **云端代码生成极其便宜**。DeepSeek V3.2 API 每百万 token 仅 $0.28（cache miss），500K tokens/月的开销不到 $0.20 CAD。即使用 GPT-4.1（$5/1MT），每月也不超过 $2.50 CAD。
3. **真实数据永不离开本地**——只有列名、类型、统计摘要发送到云端，原始数据留在本地 Docker 沙箱执行。
4. **你的项目已有 80% 的基础设施**：Docker 沙箱执行器、AST 代码验证器、LLM 后端工厂（llama_cpp / ollama / zhipu）都已实现。

**对于毕业项目，建议先保持「全本地」完成核心 RAG 功能，然后用 1-1.5 周时间增加一个「极简版混合代码生成」作为亮点功能。** 这既降低了核心功能的风险，又通过混合架构展示了工程能力。

---

## 1. 业界实践调研

### 1.1 主流混合架构模式

业界在 2024-2026 年间已形成几种成熟的混合模式：

| 模式 | 本地负责 | 云端负责 | 典型项目 |
|------|---------|---------|---------|
| **分层复杂度路由** | 意图分类、简单 Q&A、查询改写 | 复杂推理、高质量代码生成 | RouteLLM, Semantic Router |
| **本地检索 + 云端生成** | 嵌入、向量检索、文档处理 | 基于检索结果的最终生成 | AnythingLLM, PrivateGPT |
| **级联降级** | 首选本地处理 | 本地失败时自动切换到云端 | LiteLLM, LangChain Fallbacks |
| **任务特化路由** | 分类/摘要/工具调用 | 代码生成/多步推理 | LangGraph multi-agent |
| **元数据提取→代码生成** | 提取数据特征和模式描述 | 基于特征生成分析代码 | PandasAI |

### 1.2 关键开源框架

| 框架 | GitHub Stars | 用途 | 适合度 |
|------|-------------|------|--------|
| [LiteLLM](https://github.com/BerriAI/litellm) | 16K+ | 统一代理，支持 100+ 后端，带降级链和成本追踪 | 生产级，对学生项目偏重 |
| [RouteLLM](https://github.com/lm-sys/RouteLLM) | — | LMSYS 出品，训练路由器动态选择强/弱模型 | 学术参考，实现成本高 |
| [Semantic Router](https://github.com/aurelio-labs/semantic-router) | — | 基于嵌入的亚毫秒级路由 | 轻量，适合明确分类场景 |
| [LangChain](https://github.com/langchain-ai/langchain) | 98K+ | `RunnableWithFallbacks` + `RunnableBranch` | **你的项目已在用** |
| [PandasAI](https://github.com/Sinaptik-AI/pandas-ai) | 15K+ | 元数据→代码生成管线的参考实现 | **核心参考** |

### 1.3 社区反馈（Reddit r/LocalLLaMA, r/LangChain）

**支持混合方案的观点**：
- 本地 7B 模型做分类/路由已经足够好（Qwen 2.5、Llama 3.x 以来）
- 隐私是第一驱动力——企业/行业场景必须保证数据不出境
- 简单任务本地处理节省成本且无网络延迟

**反对/谨慎观点**：
- 管理两套系统的配置复杂度对小团队来说负担较大
- 本地和云端模型的响应格式不一致，需要额外的归一化处理
- 延迟差异（本地 1-5s vs 云端 3-15s）导致用户体验不连贯
- 对于 hobby/学生项目，很多人认为「复杂度不值得」

**社区共识（对小团队/学生项目）**：
> 用 LangChain 的 `with_fallbacks()` 做最简单的本地优先-云端降级，不要过度工程化路由逻辑。

---

## 2. 你的场景的技术可行性

### 2.1 「元数据提取 → 代码生成」链路分析

```
用户问题: "哪些材料的抗压强度超过 30 MPa 且适合用于基础工程？"
                    |
                    v
  ┌─────────────────────────────────┐
  │  Step 1: 确定性元数据提取（本地）   │  ← 不需要 LLM！
  │  Python: df.describe() + dtypes  │
  │  输出: JSON metadata (~200 tokens)│
  └─────────────────────────────────┘
                    |
                    v
  ┌─────────────────────────────────┐
  │  Step 2: 代码生成（云端 API）      │  ← DeepSeek/GPT-4.1
  │  输入: metadata + 用户问题        │
  │  输出: Python/Pandas 分析代码     │
  └─────────────────────────────────┘
                    |
                    v
  ┌─────────────────────────────────┐
  │  Step 3: AST 验证（本地）          │  ← 已有 validator.py
  │  语法检查 + import 黑名单          │
  └─────────────────────────────────┘
                    |
                    v
  ┌─────────────────────────────────┐
  │  Step 4: Docker 沙箱执行（本地）   │  ← 已有 docker_executor.py
  │  网络隔离 + 资源限制 + 超时        │
  │  原始数据在容器内，永不上传        │
  └─────────────────────────────────┘
                    |
                    v
  ┌─────────────────────────────────┐
  │  Step 5: 结果展示（Streamlit）    │
  │  表格 + 图表 + 生成的代码         │
  └─────────────────────────────────┘
```

**关键设计决策：为什么元数据提取不应使用 LLM？**

| 方法 | 延迟 | 准确性 | 幻觉风险 | 成本 |
|------|------|--------|---------|------|
| `df.describe()` + `df.dtypes` + `df.head(3)` | <10ms | 100% | 零 | 零 |
| 本地 Qwen2.5:7B 提取元数据 | 2-5s | 85-95% | 存在 | 电费 |
| 云端 GPT-4.1 提取元数据 | 3-10s | 95-99% | 极低 | API 费 |

**确定性 Python 代码在这一步完胜 LLM**——更快、更准、零成本、零幻觉。LLM 的价值在于「理解用户意图并生成分析代码」，而不是「读取 CSV 的列名」。

### 2.2 隐私安全分析

**发送到云端的内容（安全）**：
- 列名：`["material_name", "compressive_strength_mpa", "density", "application"]`
- 数据类型：`{"material_name": "object", "compressive_strength_mpa": "float64"}`
- 统计摘要：`{"mean": 35.2, "std": 12.1, "min": 10.0, "max": 80.0}`
- 样本行（前 3 行，可选脱敏）
- 用户的自然语言问题

**永不发送到云端的内容（保留在本地）**：
- 完整的原始数据文件
- 具体的项目名称、合同编号、业主信息
- 施工人员 PII（姓名、工号、联系方式）
- 图纸和技术文档的原始内容
- 安全事故报告的具体细节

**信息脱敏边界示例**：

| 原始数据 | 发送到云端的脱敏版本 |
|---------|-------------------|
| 项目"Calgary Tower Phase 2"的混凝土强度记录 | "一个建筑项目的混凝土强度测试数据，600条记录" |
| 承包商"ABC Construction Ltd"的安全事故报告 | "安全事故记录，包含日期、类型、严重程度字段" |
| 工人 John Smith 的培训记录 | "培训记录数据，含 employee_id(匿名), course_name, completion_date" |

### 2.3 与你项目现有架构的集成

你的项目已经具备混合架构的核心组件：

| 组件 | 状态 | 文件位置 |
|------|------|---------|
| LLM 后端工厂（llama_cpp/ollama/zhipu） | ✅ 已有 | `backend/services/llm_integration/` |
| Docker 沙箱执行器 | ✅ 已有 | `backend/services/code_executor/docker_executor.py` |
| AST 代码验证器 | ✅ 已有 | `backend/services/code_executor/validator.py` |
| Intent 分类（LangGraph State Graph） | ✅ 已有 | `backend/services/intent_classification/` |
| 元数据提取模块 | ❌ 需新建 | ~100 行 Python |
| 代码生成 Prompt 工程 | ❌ 需新建 | ~150 行 Python |
| Streamlit 结果展示 | ❌ 需新建 | ~200 行 Python |
| DeepSeek/OpenAI API 集成 | ⚠️ 部分有（zhipu） | 扩展 `LLMClientFactory` |

**新增代码量估计：~300-500 行 Python，约 1-1.5 周工作量（2 人）。**

---

## 3. 三种方案对比

### 3.1 综合对比表

| 维度 | A. 完全本地 | B. 极简混合 | C. 完全云端 |
|------|-----------|-----------|-----------|
| **实现复杂度** | ⭐⭐ 低 | ⭐⭐⭐ 中 | ⭐⭐ 低 |
| **代码生成质量** | ⭐⭐ 中等（7B 模型） | ⭐⭐⭐⭐⭐ 优秀 | ⭐⭐⭐⭐⭐ 优秀 |
| **数据隐私** | ⭐⭐⭐⭐⭐ 完美 | ⭐⭐⭐⭐ 很好（仅元数据出境） | ⭐⭐ 差（原始数据上传） |
| **网络依赖** | 无 | 代码生成步骤需网络 | 全部需网络 |
| **月成本（500K tok）** | ~$0.03 | ~$0.05-$0.52 | ~$0.18-$4.50 |
| **Demo Day 稳定性** | ⭐⭐⭐⭐⭐ 零网络风险 | ⭐⭐⭐⭐ 需备降级方案 | ⭐⭐⭐ 完全依赖网络 |
| **开发周期** | 2-3 周 | 3-4 周 | 2-3 周 |
| **对 Capstone 的展示价值** | 一般 | **很高**（展示工程能力） | 一般 |
| **适合 1-2 人团队** | ✅ 很适合 | ✅ 适合（如果时间充裕） | ✅ 很适合 |

### 3.2 各方案详细分析

**方案 A：完全本地**
```
用户问题 → 本地 Qwen2.5-Coder:7b → 代码生成 → Docker 执行
```
- **优点**：零成本、零延迟、完全离线、架构最简单
- **缺点**：7B 模型代码生成可靠性约 70-80%，复杂分析（透视表、统计检验、时间序列）能力明显不足
- **适用**：如果时间紧张（<3 周），优先选此方案

**方案 B：极简混合（推荐）**
```
用户问题 → 确定性元数据提取 → DeepSeek API 代码生成 → Docker 执行
```
- **优点**：代码质量接近 GPT-4 水平、成本几乎为零、数据不出境、展示工程能力
- **缺点**：需要 API key 管理、网络依赖（需备降级到本地模型）
- **适用**：如果时间充裕（4+ 周），推荐此方案

**方案 C：完全云端**
```
用户问题 + 数据摘要 → DeepSeek/GPT-4.1 API → 代码 → 本地执行
```
- **优点**：实现最简单、代码质量最好
- **缺点**：失去「本地优先」的隐私叙事，对建筑行业数据合规不利
- **适用**：如果不在意隐私叙事，且追求最快完成

### 3.3 开发周期对比（1-2 人，基于现有代码库）

| 阶段 | 方案 A | 方案 B | 方案 C |
|------|--------|--------|--------|
| 元数据提取模块 | 2 天 | 2 天 | 2 天 |
| Prompt 工程与调试 | 3-5 天 | 3-5 天 | 3-5 天 |
| API 集成 | 0 天 | 1-2 天 | 1-2 天 |
| 降级逻辑 | 0 天 | 1 天 | 0 天 |
| Streamlit 展示 | 2-3 天 | 2-3 天 | 2-3 天 |
| 端到端测试 | 2-3 天 | 2-3 天 | 2-3 天 |
| **合计** | **9-13 天** | **11-16 天** | **10-15 天** |

---

## 4. 成本与性能详算

### 4.1 云端 API 定价对比（2025-2026，每百万 token）

| 模型 | 输入 | 输出 | 缓存命中输入 | 代码生成质量 |
|------|------|------|------------|------------|
| **DeepSeek V3.2** | $0.28 | $0.42 | $0.028 | ⭐⭐⭐⭐⭐ 优秀 |
| Gemini 2.0 Flash | $0.10 | $0.40 | — | ⭐⭐⭐⭐ 好 |
| GPT-4.1-nano | $0.10 | $0.40 | $0.025 | ⭐⭐⭐⭐ 好 |
| GPT-4o-mini | $0.15 | $0.60 | $0.075 | ⭐⭐⭐⭐ 好 |
| Gemini 2.5 Flash | $0.15-$0.30 | $0.60-$1.80 | — | ⭐⭐⭐⭐ 很好 |
| Groq Llama 3.3 70B | $0.59 | $0.79 | — | ⭐⭐⭐⭐ 好 |
| Claude Haiku 4.5 | $1.00 | $5.00 | $0.10 | ⭐⭐⭐⭐ 好 |
| **GPT-4.1** | **$2.00** | **$8.00** | $0.50 | ⭐⭐⭐⭐⭐ 优秀 |
| Gemini 2.5 Pro | $1.25 | $10.00 | — | ⭐⭐⭐⭐⭐ 优秀 |
| Claude Sonnet 4.5 | $3.00 | $15.00 | $0.375 | ⭐⭐⭐⭐⭐ 优秀 |
| GPT-4o | $2.50 | $10.00 | $1.25 | ⭐⭐⭐⭐⭐ 优秀 |
| Claude Opus 4 | $15.00 | $75.00 | $1.875 | ⭐⭐⭐⭐⭐ 顶级 |

> **数据来源**: [OpenAI Pricing](https://openai.com/api/pricing/), [Anthropic Pricing](https://platform.claude.com/docs/en/about-claude/pricing), [DeepSeek Pricing](https://api-docs.deepseek.com/quick_start/pricing), [Google Gemini Pricing](https://ai.google.dev/gemini-api/docs/pricing)

### 4.2 本地推理性能（Apple Silicon + Ollama）

| 模型 | 大小 | Mac Studio M2 Max | 代码生成质量 |
|------|------|-------------------|------------|
| Qwen2.5:7B (Q4_K_M) | ~4.5 GB | 45-55 tok/s | ⭐⭐⭐ 中等 |
| Qwen2.5-Coder:7B | ~4.5 GB | 45-55 tok/s | ⭐⭐⭐⭐ 好 |
| Qwen2.5-Coder:32B | ~19 GB | 15-22 tok/s | ⭐⭐⭐⭐ 很好 |
| Llama 3.3:70B | ~40 GB | 8-12 tok/s | ⭐⭐⭐⭐⭐ 优秀 |

> **数据来源**: [llama.cpp Apple Silicon Discussion](https://github.com/ggml-org/llama.cpp/discussions/4167), [Qwen2.5 Speed Benchmark](https://qwen.readthedocs.io/en/v2.5/benchmark/speed_benchmark.html), [Apple Silicon LLM Analysis (arxiv)](https://arxiv.org/pdf/2511.05502)

**MLX 框架在 Apple Silicon 上可达 ~230 tok/s**（vs Ollama ~50 tok/s），但 Ollama 的易用性更适合项目。

### 4.3 月度成本估算

假设：代码生成任务平均每次 ~500 input tokens (元数据+问题) + ~300 output tokens (代码)

| 方案 | 50K tok/月 | 200K tok/月 | 500K tok/月 |
|------|-----------|-------------|-------------|
| **A: 纯本地 (Qwen2.5:7B)** | <$0.01 | <$0.01 | ~$0.03 |
| **B: 混合 (本地 RAG + DeepSeek 代码生成)** | ~$0.01 | ~$0.02 | ~$0.05 |
| **B: 混合 (本地 RAG + GPT-4.1 代码生成)** | ~$0.05 | ~$0.21 | ~$0.52 |
| **C: 纯云端 (DeepSeek V3.2)** | ~$0.02 | ~$0.07 | ~$0.18 |
| **C: 纯云端 (GPT-4.1)** | ~$0.25 | ~$1.00 | ~$2.50 |
| **C: 纯云端 (Claude Sonnet 4.5)** | ~$0.45 | ~$1.80 | ~$4.50 |

### 4.4 关键洞察

> **在学生级使用量下（50K-500K tokens/月），所有方案的成本都几乎为零。** 即使最贵的 Claude Sonnet 4.5 全量使用，每月也不到 $5 CAD。
>
> **选择混合方案的核心理由不是省钱，而是：**
> 1. 数据隐私（建筑行业数据不出境）
> 2. Demo Day 稳定性（核心 RAG 功能不依赖网络）
> 3. 工程能力展示（混合架构是加分项）
> 4. 代码生成质量（云端模型远优于本地 7B）

### 4.5 混合方案何时「划算」vs「得不偿失」

| 场景 | 判断 | 理由 |
|------|------|------|
| 500K tok/月，需要高质量代码 | ✅ 划算 | 云端代码生成质量远超本地 7B，成本 <$1 |
| <50K tok/月，简单数据查询 | ❌ 得不偿失 | 本地 7B 够用，增加复杂度无实质收益 |
| 建筑行业敏感数据 | ✅ 必要 | 隐私合规要求数据不出境 |
| Demo Day 现场展示 | ⚠️ 需要降级方案 | 必须有全本地 fallback，否则网络问题会毁掉演示 |
| >5M tok/月（生产环境） | ✅ 明显划算 | GPT-4.1 月费约 $25，远低于自建 GPU 服务器 |

---

## 5. 免费资源与学生优惠

| 资源 | 免费额度 | 获取方式 |
|------|---------|---------|
| **Google Gemini 2.0 Flash** | 15 RPM / 1M TPM / 1500 RPD **永久免费** | [ai.google.dev](https://ai.google.dev) 注册 |
| **GitHub Copilot** | 学生完全免费 | GitHub Education 验证（.edu 邮箱或学生证） |
| **DeepSeek** | 注册赠送 credits | [platform.deepseek.com](https://platform.deepseek.com) |
| **OpenAI** | $5 注册赠金（3 个月有效） | 新账号注册 |
| **Anthropic** | $5 注册赠金 | 新账号注册 |
| **Google Cloud** | 学生 $50-$300 credits | 通过学校的 Google Cloud Education 计划 |
| **Azure for Students** | $100 credits | .edu 邮箱验证 |
| **Groq** | 免费层（限速） | [console.groq.com](https://console.groq.com) 注册 |
| **Ollama（本地）** | 完全免费 | 已在用 |

**最佳组合推荐**：Ollama 本地（RAG/路由） + Gemini 2.0 Flash 免费层（轻量 API 实验） + DeepSeek V3.2（需要更强代码生成时） + GitHub Copilot（日常开发）

---

## 6. 风险评估

### 6.1 混合方案主要风险

| 风险 | 概率 | 影响 | 缓解策略 |
|------|------|------|---------|
| **Demo Day 网络不可用** | 中 | 高 | 实现全本地 fallback 到 Qwen2.5-Coder:7b |
| **API 定价变动** | 低 | 低 | DeepSeek 目前极便宜，价格翻倍仍可接受 |
| **API 响应格式不一致** | 中 | 中 | 健壮的代码块提取解析（regex + 多模式匹配） |
| **云端模型生成的代码有安全问题** | 中 | 高 | AST 验证器 + import 黑名单（已有） + Docker 隔离（已有） |
| **元数据意外包含敏感信息** | 低 | 高 | 脱敏检查层：正则匹配姓名/电话/地址模式，阻止发送 |
| **LangChain/LangGraph API 变动** | 中 | 中 | 锁定版本，使用稳定 API |
| **调试复杂度增加** | 确定 | 中 | 统一日志记录每步输入/输出，便于追踪 |
| **本地 vs 云端 Prompt 格式差异** | 低 | 低 | LangChain 抽象层已处理（Ollama/ChatOpenAI 自动转换） |

### 6.2 LangChain 多模型路由实现示例

你的项目已使用 LangGraph State Graph，扩展为多模型非常自然：

```python
# 不同 graph 节点使用不同 LLM
from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI

# 本地模型：意图分类、RAG 摘要
local_llm = Ollama(model="qwen2.5:7b")

# 云端模型：代码生成（仅在需要时调用）
cloud_llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="sk-..."
)

# LangGraph 节点可分别绑定不同模型
def classify_intent(state):
    return local_llm.invoke(state["query"])  # 本地

def generate_code(state):
    return cloud_llm.invoke(state["metadata_prompt"])  # 云端

# 降级逻辑
cloud_with_fallback = cloud_llm.with_fallbacks([local_llm])
```

---

## 7. 最终推荐

### 推荐策略：分阶段实施

```
Phase 1（第 1-3 周）：完成核心 RAG + 全本地  ← 保证基本功能
    - 修复 Jieba 分词 bug
    - 设置 RAGAS 评估
    - 建设 Streamlit 前端
    - 代码生成用本地 Qwen2.5-Coder:7b

Phase 2（第 4-5 周）：增加极简混合代码生成  ← 亮点功能
    - 添加确定性元数据提取模块
    - 集成 DeepSeek API 作为代码生成后端
    - 实现「本地 fallback」降级逻辑
    - 用户可选：本地生成 vs 云端生成

Phase 3（第 6 周）：Demo 打磨  ← 展示准备
    - 端到端测试（建筑材料分析、安全记录统计）
    - Demo Day 全本地模式验证
    - 文档和演示 PPT
```

### 一句话结论

> **不要为了「混合」而混合**。先确保全本地 RAG 核心功能完整可靠，然后用 1 周时间加一个「用户点击'高质量分析'按钮时调用 DeepSeek API」的极简混合功能。这既是安全的增量改进，又能在 Capstone 展示时作为架构亮点。成本每月不到 $1 CAD，复杂度增量约 300 行代码。

---

## 参考来源

- [OpenAI API Pricing](https://openai.com/api/pricing/) - GPT-4.1, GPT-4o 系列定价
- [Anthropic Claude Pricing](https://platform.claude.com/docs/en/about-claude/pricing) - Claude 4.5 系列定价
- [DeepSeek API Pricing](https://api-docs.deepseek.com/quick_start/pricing) - DeepSeek V3.2 定价（2026-02 确认）
- [Google Gemini Pricing](https://ai.google.dev/gemini-api/docs/pricing) - Gemini 2.x 系列定价和免费层
- [LiteLLM](https://github.com/BerriAI/litellm) - 统一 LLM 代理框架
- [RouteLLM](https://github.com/lm-sys/RouteLLM) - LMSYS 智能路由
- [PandasAI](https://github.com/Sinaptik-AI/pandas-ai) - 元数据→代码生成参考实现
- [Semantic Router](https://github.com/aurelio-labs/semantic-router) - 亚毫秒级语义路由
- [llama.cpp Apple Silicon Benchmarks](https://github.com/ggml-org/llama.cpp/discussions/4167) - 本地推理性能
- [Apple Silicon LLM Inference (arXiv)](https://arxiv.org/pdf/2511.05502) - MLX vs Ollama 性能对比
- [Qwen2.5 Speed Benchmark](https://qwen.readthedocs.io/en/v2.5/benchmark/speed_benchmark.html) - 官方速度基准
- [pricepertoken.com](https://pricepertoken.com/) - LLM API 价格聚合对比
