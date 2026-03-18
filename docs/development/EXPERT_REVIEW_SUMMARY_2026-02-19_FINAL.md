# Industry AI Flow 专家评审总结（老板提交版）

- 评审日期：2026-02-19
- 评审负责人：项目负责人（汇总 Instructor + 项目架构师 + AI/RAG/测试/安全专家意见）
- 评审目标：判断是否具备“部署或交付测试”必要条件；识别 P0/P1 风险；给出可落地的 3-5 项必须整改工作。

## 1. 评审专家团（含项目架构师）

1. Instructor（召集人）
2. 项目架构师（核心成员，负责架构可落地性与技术取舍）
3. LLM/Agent 专家（模型调度、推理可靠性）
4. RAG 专家（检索、重排、知识库质量）
5. QA 负责人（门禁真实性、回归与验收）
6. DevOps/SRE（运行时健康、发布稳定性）
7. 安全与合规负责人（审计、出站策略、最小暴露面）

## 2. 结论（先给老板）

当前版本**可以进入“内部受控测试”**，但**不建议直接进入正式交付测试/对外部署**。

原因不是“门禁全红”，而是“门禁全绿但业务语义仍存在结构性空洞”：

- `make test-release-gate` 在当前环境已通过；
- 但主工作流中的 Agent 调度仍是**模拟响应**，会把“模板化非业务回答”当成功；
- 数据分析链路对执行环境（Docker/Provider）依赖强，且健康信号与真实可执行性存在偏差；
- 部分 release gate 仍偏“结构/契约通过”，不足以证明“真实业务可用”。

## 3. 基于代码与实测的关键事实

### 3.1 正向事实（已修复/已具备）

1. Prompt baseline 已落地并纳入门禁：`scripts/migration/seed_prompt_baseline.py`。
2. `make test-release-gate` 全链路通过（本次复核实跑通过）。
3. `prompts` 表在本地复核时非空（`count(*) = 5`）。

### 3.2 关键风险事实（决定“暂不交付”）

1. 主意图工作流仍使用模拟 Agent 响应：
   - `backend/services/intent_classification/intent_workflow.py:719` 注释明确“模拟调用”；
   - `backend/services/intent_classification/intent_workflow.py:723`-`734` 返回模板化字符串，而非真实 RAG/代码分析执行结果。
2. 工作流成功判定过宽：
   - `backend/services/intent_classification/intent_workflow.py:794` 仅以 `error` 是否为空决定 `success`；
   - 在模拟响应路径下，容易出现“语义降级但 success=true”。
3. data-analysis gate 没有真正执行核心集成用例：
   - `Makefile:260` 对 `tests/integration/test_eda_functionality.py` 仅 `--collect-only`。
4. Docker 执行器健康探针存在乐观偏差：
   - `backend/services/code_executor/providers/docker_provider.py:42`-`43` 直接返回 `healthy: true`，未做真实连通校验。
5. E2E 工作流验收标准偏弱：
   - `scripts/testing/run_construction_rag_e2e_validation.py:249` 与 `:307`，workflow 通过条件仅为 `success && 非空文本`；
   - 现有报告中 `response_preview` 显示模板化回答也会通过（`logs/construction_rag_e2e_validation_report.json:283`）。

## 4. P0/P1 分级（按当前阶段）

### P0（交付前必须完成）

1. **P0-1：主工作流仍含模拟 Agent 响应，不满足真实业务交付定义**
   - 影响：RAG/代码分析能力在最关键入口无法保证“真实执行 + 可追溯依据”。
2. **P0-2：发布门禁未覆盖真实语义验收，存在“假绿灯”风险**
   - 影响：CI 通过不代表用户可用性通过，容易在老板/客户验收环节翻车。

### P1（建议本轮一并收敛）

1. **P1-1：代码执行能力健康信号与真实可用性不一致**（Docker health 总是 true）。
2. **P1-2：部分 Agent 依赖通过兼容层降级，功能质量波动较大**（fallback 模式可返回非检索型回答）。
3. **P1-3：RAG 评估指标偏“检索/格式通过”，缺少答案真实性与引用一致性硬约束。**

## 5. 只能选 3-5 项时，必须做的 5 项

> 以下 5 项按优先级排序；这是本次评审给出的“最小可交付闭环”。

1. **替换主工作流中的模拟 Agent 调度为真实执行链路（P0）**
   - 位置：`backend/services/intent_classification/intent_workflow.py:709` 起。
   - 要求：按 `selected_agent` 调真实 service/tool，不允许模板化 hardcode 作为默认成功输出。
   - 验收：抽样 query 必须产出可追溯上下文/执行结果；无证据回答返回受控失败或澄清。

2. **升级 release gate：把“collect-only”改为真实执行 + 结果断言（P0）**
   - 位置：`Makefile:245`-`260`。
   - 要求：`test_eda_functionality` 至少执行 1 条真实数据分析路径并断言 `success=true` 与关键字段。
   - 验收：缺 Docker/Provider 或执行失败时，release gate 必须失败。

3. **修正运行时健康语义：健康探针必须反映真实可用性（P1）**
   - 位置：`backend/services/code_executor/providers/docker_provider.py:42`。
   - 要求：health 检查 Docker daemon 可达、最小执行沙箱可运行；失败时标记 unhealthy。
   - 验收：`/api/v1/environment` 与审计日志可准确反映可执行状态。

4. **补齐“答案真实性”验收，而非仅“非空文本”验收（P1）**
   - 位置：`scripts/testing/run_construction_rag_e2e_validation.py:249`/`:307`。
   - 要求：新增 groundedness/citation 一致性断言；至少验证 answer 包含可匹配引用证据。
   - 验收：模板化兜底文本不得通过 workflow_api_validation。

5. **收敛模型调度层复杂度：优先网关化，而非全栈迁移（P1）**
   - 建议：保留现有 LangGraph/pgvector 主线，灰度引入 LiteLLM 类统一网关能力（路由、成本、回退、审计一致化），减少自研分叉。
   - 验收：统一入口可观测、可限流、可预算控制，且 fallback 行为可测试。

## 6. 对 2026 开源生态的务实取舍（已调研）

调研时间：2026-02-19（以 GitHub API/官方仓库为准）。

| 项目 | Stars（快照） | 最近活跃 | 最新发布（快照） | 对本项目建议 |
|---|---:|---|---|---|
| `run-llama/llama_index` | 47060 | 2026-02-18 | v0.14.15 (2026-02-18) | 增强检索评估与数据连接层 |
| `deepset-ai/haystack` | 24237 | 2026-02-19 | v2.24.1 (2026-02-12) | 做 pipeline/评测对标 |
| `langchain-ai/langgraph` | 24835 | 2026-02-19 | sdk==0.3.7 (2026-02-18) | 继续沿用（与现架构兼容） |
| `BerriAI/litellm` | 36307 | 2026-02-19 | v1.81.3.oauth.dev (2026-02-19) | 优先灰度引入统一网关能力 |
| `explodinggradients/ragas` | 12653 | 2026-01-31 | v0.4.3 (2026-01-13) | 补齐答案质量量化门禁 |
| `infiniflow/ragflow` | 73406 | 2026-02-14 | v0.24.0 (2026-02-10) | 借鉴流程，不做短期全量迁移 |

**取舍原则**：

1. Capstone 当前阶段不做全栈重构；
2. 仅引入低侵入、高收益能力（网关、评测、可观测）；
3. 高迁移成本组件（向量库整体替换、平台整体迁移）只做 PoC，不进主线交付。

来源链接（官方仓库/API）：

1. https://github.com/run-llama/llama_index
2. https://github.com/deepset-ai/haystack
3. https://github.com/langchain-ai/langgraph
4. https://github.com/BerriAI/litellm
5. https://github.com/explodinggradients/ragas
6. https://github.com/infiniflow/ragflow

## 7. 交付建议与时间表

### T+2 天（必须完成）

1. 完成模拟 Agent 替换为真实执行。
2. 调整 release gate，取消关键链路 collect-only。
3. 修复 Docker/provider health 真实性。

### T+1 周（建议完成）

1. 新增 groundedness/citation 硬门禁。
2. 灰度引入统一 LLM 网关能力（先旁路，不一次切主）。

### 管理层决策建议

1. 允许继续内部受控测试（范围可控、明确非正式交付）。
2. 在上述 5 项至少完成前 3 项前，不建议进入正式交付测试。
3. 下一轮评审以“真实链路证据 + 门禁结果 + 线上回放样本”三件套作为准入条件。

---

## 附：本次复核关键执行证据（节选）

1. `make test-release-gate`（当前通过）
2. `psql -d ai_workflow -c "select count(*) from prompts;"`（本次为 5）
3. `/api/v1/data/analyze` 实测（当前环境下返回 `success=false`，错误为代码执行器不可用）
4. `/api/v1/workflow/query` 实测（返回 `success=true` 但响应可为模板化文本）
