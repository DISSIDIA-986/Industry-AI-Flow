# RAG Workflow 修复计划（2026-03-03）

## 1. 背景与问题摘要

在 `Ollama + qwen3.5:4b` 场景下，RAG 全流程门禁仍失败，核心症状如下：

1. `intent_workflow` 在低置信度澄清分支进入重复分类，最终触发 `GRAPH_RECURSION_LIMIT`。
2. 本地 LLM 请求频繁 `Read timed out (60s)`，workflow 退化为无价值 fallback 响应。
3. 响应文本未稳定输出 citation 尾注，导致 `run_construction_rag_e2e_validation.py` 的质量门禁失败。
4. 部分集成测试用例通过 `try/except` 吞掉异常，出现“测试绿但链路坏”。

---

## 2. 修复目标与验收标准

### 2.1 目标

1. `logs/construction_rag_e2e_validation_report.json` 中：
   - `workflow_api_pass=true`
   - `workflow_quality_pass=true`
   - `overall_pass=true`
2. 三条 workflow 探针问题全部返回：
   - `success=true`
   - 非模板回答
   - 含有效 citation（`[Sources: ...]`）
   - citation 命中期望 source hint。
3. 日志中不再出现 `GRAPH_RECURSION_LIMIT`。
4. RAG 相关集成测试改为断言失败模式，不再吞异常。

### 2.2 验收工件

1. `logs/tdo_rag_e2e_validation.log`
2. `logs/construction_rag_e2e_validation_report.json`
3. `logs/tdo_rag_regression.log`
4. `logs/tdo_rag_regression.xml`

---

## 3. 公开接口与配置变更

### 3.1 API 契约扩展（向后兼容）

扩展 `WorkflowQueryResponse`：

1. `clarification_needed: bool = false`
2. `clarification_message: Optional[str] = null`

目的：在低置信度但未收到用户补充时，显式返回“需要澄清”状态，避免服务端内部循环重试。

### 3.2 citation 文本契约

知识检索路径最终 `response` 必须带标准尾注：

`[Sources: source_a, source_b, ...]`

若模型回答已包含 citation 则去重，不重复追加。

### 3.3 配置项新增

1. `OLLAMA_CONNECT_TIMEOUT_SECONDS=10`
2. `OLLAMA_REQUEST_TIMEOUT_SECONDS=90`
3. `WORKFLOW_DISPATCH_MAX_TOKENS=512`
4. `WORKFLOW_RECURSION_LIMIT=12`

并保持默认模型口径一致：`qwen3.5:4b`。

---

## 4. 实施方案（按优先级）

## Phase A: P0 稳定性止血

### A1. 修复澄清分支重试环

目标文件：`backend/services/intent_classification/intent_workflow.py`

变更点：

1. `_clarification_processing_node` 仅在存在 `user_clarification_input` 时设置 `clarification_handled=true` 并允许 `retry_classification`。
2. 无用户补充输入时直接设置 `awaiting_user_clarification=true` 并结束当前运行（不重试）。
3. `run_workflow` / `continue_workflow` 的 `ainvoke` 增加 `recursion_limit=settings.workflow_recursion_limit`。
4. 递归异常返回受控错误文案，不泄露内部错误栈。

### A2. 控制本地 LLM 超时退化

目标文件：

1. `backend/services/llm_integration/ollama_client.py`
2. `backend/api/workflow_query_routes.py`

变更点：

1. `requests.post` 改为可配置 connect/read timeout，不使用硬编码 `60`。
2. `DispatchResponseBuilder` 默认 `max_tokens` 使用 `WORKFLOW_DISPATCH_MAX_TOKENS`（默认 512），降低超时概率。
3. dispatch 失败时不返回模板字符串，改为“基于检索上下文的 extractive fallback + sources”。

## Phase B: P1 质量提升

### B1. 提升 intent fallback 识别准确性

目标文件：`backend/services/intent_classification/intent_classifier.py`

变更点：

1. 强化 `_simulate_llm_response` 的 query 提取逻辑（避免读取错段）。
2. 增加 construction 领域关键词：`osha`, `ufgs`, `ifc`, `p100`, `standards`, `requirements`, `compliance` 等。
3. 对语义明确但未命中其他专用类型的问题优先归到 `knowledge_retrieval`，减少误判 `unclear_intent`。

### B2. 固化 citation 输出

目标文件：`backend/services/intent_classification/intent_workflow.py`

变更点：

1. `_dispatch_rag_query` 最终 response 一律保证 `[Sources: ...]`。
2. LLM 生成失败的 extractive fallback 路径同样加 citation 尾注。
3. source 列表按 `document_name/filename` 去重，保留前 3-5 项。

## Phase C: P1 测试可信度修复

### C1. 修复“吞异常假通过”集成测试

目标文件：

1. `tests/integration/test_complete_rag_system.py`
2. `tests/integration/test_rag_agent.py`

变更点：

1. 移除 `try/except` 的“仅打印不失败”行为。
2. 改为显式断言 `success`、响应非空、关键字段存在。

### C2. 新增回归测试

新增/增强单测场景：

1. clarification 无用户补充时不会 retry。
2. dispatch fallback 产物包含有效 sources/citation。
3. `_dispatch_rag_query` 输出统一 citation 尾注。
4. `WorkflowQueryResponse` 新字段向后兼容。

---

## 5. 执行与回归命令

## 5.1 关键单测

```bash
.venv/bin/python -m pytest -q \
  tests/unit/test_intent_workflow_dispatch_runtime.py \
  tests/unit/test_workflow_query_routes.py
```

## 5.2 RAG 集成回归

```bash
.venv/bin/python -m pytest -q -vv \
  tests/integration/test_rag_agent.py \
  tests/integration/test_complete_rag_system.py \
  --junitxml=logs/tdo_rag_regression.xml \
  2>&1 | tee logs/tdo_rag_regression.log
```

## 5.3 全链路 E2E 验证

```bash
LLM_BACKEND=ollama \
LLM_PROVIDER=ollama \
OLLAMA_MODEL=qwen3.5:4b \
LOCAL_PRIMARY_BACKEND=ollama \
HYBRID_MODE=local_only \
.venv/bin/python scripts/testing/run_construction_rag_e2e_validation.py \
2>&1 | tee logs/tdo_rag_e2e_validation.log
```

---

## 6. 风险与回滚

## 6.1 风险

1. 超时调小可能导致边界长问题被提前中断。
2. citation 统一尾注可能影响前端文本展示样式。
3. fallback 回答从“模板句”改为“extractive 回答”后，回答风格会变化。

## 6.2 回滚策略

1. 保留 `WORKFLOW_RUNNER_MODE=fallback` 作为紧急保活开关。
2. 所有配置变更通过 `.env` 可逆回滚，不涉及 DB schema 迁移。
3. 若新策略异常，回退至上一稳定提交并强制 fallback 模式。

---

## 7. 假设与默认决策

1. 本轮不做架构重写（不替换 workflow 框架，不重构 RAG 主链）。
2. 默认模型固定 `qwen3.5:4b`，`9b` 仅通过显式环境变量覆盖。
3. 质量门禁以当前 `run_construction_rag_e2e_validation.py` 判定逻辑为准。
4. 先保证“可稳定通过门禁 + 可观察 + 可回滚”，再考虑二阶段性能优化。
