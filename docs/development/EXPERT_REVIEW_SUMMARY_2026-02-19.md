# Industry AI Flow 专家评审总结（提交版）

- 评审日期：2026-02-19
- 面向对象：老板 / 项目管理层
- 评审目标：判断项目是否具备部署或交付测试的必要条件；识别 P0/P1 缺陷；给出可落地改进路径。

## 1. 专家评审团构成（含项目架构师）

1. Instructor（评审召集人）
2. 项目架构师（核心成员，负责整体架构可落地性与技术取舍）
3. AI/LLM 专家（模型路由、推理策略、质量门禁）
4. RAG/知识库专家（检索链路、索引策略、知识运营）
5. QA 负责人（测试门禁、回归策略、交付验收）
6. DevOps/SRE（部署路径、可观测性、发布稳定性）
7. 安全与合规负责人（脱敏、出站策略、审计）

## 2. 执行摘要（结论先行）

当前系统**具备“受控内测”基础能力**，但**尚不满足“正式交付/对外部署”条件**。主要原因是仍存在可复现的 P0 阻断项：

1. `release gate` 失败（核心回退路径测试未通过）。
2. Prompt 基线缺失（数据库 `prompts` 表为空），导致工作流关键节点降级或失败。

建议：先完成 P0 闭环，再进入交付测试。

## 3. 基于代码库与运行证据的现状

### 3.1 已通过的关键门禁（正向证据）

1. `make test-phase1-gate`：42 passed, 1 skipped。
2. `make test-demo-smoke-gate`：通过。
3. `make test-demo-smoke-live-gate`：通过（Postgres/Ollama 可达）。
4. `make test-kpi-gate`：通过（faithfulness/relevancy/cost/safety 指标均过阈值）。
5. `logs/construction_rag_e2e_validation_report.json`（2026-02-19T08:48:18Z）：`acceptance.overall_pass=true`。

### 3.2 阻断项与高风险项（负向证据）

1. `make test-release-gate` 失败：`tests/unit/test_workflow_query_routes.py::test_workflow_query_uses_fallback_runner_when_init_fails`。
2. 数据库核查：`select count(*) from prompts;` 结果为 `0`。
3. 运行日志显示多处 `未找到Prompt`，包括：
   - `Intent/intent_classification`
   - `Intent/intent_clarification`
   - `rag/construction_rag_grounded_qa`
4. 动态数据分析模块导入失败：`backend/services/data_analysis/data_analysis_agent.py` 引用不存在模块 `backend.services.ollama_client`。

## 4. P0 / P1 问题清单（按严重度）

## P0-1：发布门禁未通过，核心回退链路不稳定

- 现象：`release gate` 失败，失败用例期望 fallback runner 在初始化异常时仍返回 `success=true`，实际返回 `false`。
- 代码证据：
  - `tests/unit/test_workflow_query_routes.py:108`
  - `backend/api/workflow_query_routes.py:288`
  - `backend/services/workflows/nodes/prompt_node.py:16`
- 风险：无法宣称“可交付”，回退链路在异常环境下行为不一致。

## P0-2：Prompt 基线缺失，导致工作流核心能力降级

- 现象：`prompts` 表为空，工作流模板选择与意图相关 Prompt 大量 miss。
- 代码证据：
  - `backend/services/workflows/prompting/template_registry.py:14`
  - `backend/services/prompt_manager.py:179`
- 运行证据：查询与 E2E 过程中出现 `未找到Prompt`。
- 风险：回答质量与意图识别稳定性依赖降级逻辑，结果不可控。

## P1-1：动态代码生成/数据分析链路存在直接可复现故障

- 现象：`DataAnalysisAgent` 模块导入即失败（`ModuleNotFoundError: backend.services.ollama_client`）。
- 代码证据：
  - `backend/services/data_analysis/data_analysis_agent.py:19`
- 风险：项目宣称的“动态代码生成与高级数据分析”能力存在实现断裂。

## P1-2：RAG E2E 虽通过，但质量信号显示“可用不稳”

- 现象：E2E 总体通过，但工作流响应预览偏模板化，且语义检索中存在命中偏差案例。
- 证据：`logs/construction_rag_e2e_validation_report.json`。
- 风险：演示可过，真实复杂查询可能出现相关性波动。

## P1-3：测试与脚本可移植性不足

- 现象：部分测试包含历史绝对路径（如 `/Users/niuyp/...`）。
- 风险：跨机器复现性弱，影响团队协作与 CI 稳定性。

## 5. 结合 2026-02-19 开源生态的务实建议（先调研、后采纳）

以下为 GitHub 官方 API 快照（评审当日抓取），用于判断“成熟度 + 活跃度 + 落地性”：

| 项目 | Stars | 最近推送 | 最新发布 | 对本项目建议 |
|---|---:|---|---|---|
| [run-llama/llama_index](https://github.com/run-llama/llama_index) | 47060 | 2026-02-18 | v0.14.15 | 可作为 RAG 编排/评估增强候选，优先局部引入 |
| [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | 24237 | 2026-02-19 | v2.24.1 | 企业级 pipeline 能力强，适合做对标 PoC |
| [infiniflow/ragflow](https://github.com/infiniflow/ragflow) | 73405 | 2026-02-14 | v0.24.0 | 产品化程度高，适合借鉴知识运营与评测流程，不建议短期全量迁移 |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 24831 | 2026-02-19 | sdk==0.3.7 | 与现有架构兼容度高，继续沿用并补齐测试/策略层 |
| [BerriAI/litellm](https://github.com/BerriAI/litellm) | 36305 | 2026-02-19 | litellm_1.81.13-dev | 可替代部分自研 dispatch 复杂度，先灰度接入 |
| [qdrant/qdrant](https://github.com/qdrant/qdrant) | 28903 | 2026-02-19 | v1.16.3 | 当前阶段不建议替换 pgvector；可作为中期性能瓶颈备选 |

取舍原则：

1. 当前 Capstone 阶段优先“稳态可交付”，避免全栈重构。
2. 可采纳“低侵入、高收益”组件（如 LLM 网关层标准化、评测框架增强）。
3. 对高迁移成本方案（向量库替换、全平台迁移）仅做 PoC，不进入主线。

## 6. 分阶段落地方案（可执行）

## 阶段 A（T+2 天）：P0 清零

1. 建立 Prompt 基线初始化与启动校验。
2. 修复 fallback runner 在 `cloud_only` 与 Prompt 缺失场景下的契约一致性。
3. 将 `make test-release-gate` 作为交付前强制门禁，确保全绿。

验收标准：

1. `make test-release-gate` 100% 通过。
2. `prompts` 表具备工作流必需模板。
3. `/api/v1/workflow/query` 在初始化异常场景仍满足回退契约。

## 阶段 B（T+1 周）：P1 收敛

1. 修复 `DataAnalysisAgent` 导入链路与依赖引用。
2. 清理硬编码路径，统一相对路径/配置化。
3. 增补“意图-模板-响应质量”端到端回归测试。

验收标准：

1. 动态数据分析主链路可运行并有集成测试。
2. CI 在干净环境可复现通过。

## 阶段 C（T+2~4 周）：前瞻增强（非阻断）

1. 评估接入 LiteLLM（仅网关层灰度），降低多模型调度维护成本。
2. 引入更体系化的 RAG 评测基线（保留现有 KPI gate，扩展样本和误差分层）。
3. 保持 pgvector 主线，除非性能/规模指标触发切换阈值。

## 7. 交付决策建议

当前建议：

1. 可以进入“内部受控测试”（有条件）。
2. 不建议直接进入“正式交付/对外部署”。
3. 先完成阶段 A 再申请下一轮交付评审。

---

## 附：本次评审关键命令（节选）

1. `make test-phase1-gate`
2. `make test-demo-smoke-gate`
3. `make test-demo-smoke-live-gate`
4. `make test-kpi-gate`
5. `make test-release-gate`
6. `psql -d ai_workflow -c "select count(*) from prompts;"`
7. `make test-construction-rag-e2e`
