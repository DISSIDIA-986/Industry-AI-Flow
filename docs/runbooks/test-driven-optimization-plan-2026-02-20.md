# Industrial AI Flow 测试驱动优化方案（2026-02-20）

## 1. 目标与原则

- 目标：优先通过测试发现高价值缺陷（P0/P1），再以最小改动完成修复与回归闭环。
- 原则：先证据、后结论；先关键链路、后扩展覆盖；每个结论必须可复现。

## 2. 覆盖范围（关键链路）

- RAG 全链路：文档入库 -> chunk/metadata -> embedding -> PGVector -> 检索（语义/关键词/混合）-> 生成 -> 引用验证
- Cost Estimation/ML：数据集加载 -> 训练/推理 -> 新输入预测 -> 稳定性与边界输入
- 动态代码生成与执行：metadata 输入 -> 代码生成 -> 沙箱执行 -> 结果返回 -> 异常/边界处理
- 前后端联通：Next.js 页面交互 -> API -> 后端 workflow -> 返回渲染
- 安全与可运维：脱敏、安全拦截、健康检查、降级可观测性

## 3. TeamAgents 共识（测试重点与判定标准）

### 资深架构师

- 关注点：链路真实连通、降级路径可见、依赖状态可观测。
- 判定：健康接口必须暴露执行与 embedding 后端状态；E2E 报告必须包含存储/检索/workflow 三段。

### 资深 QA

- 关注点：可重复执行、故障可定位、回归可自动化。
- 判定：每条关键链路至少 1 条稳定自动化用例；失败日志能直接定位到测试名与失败断言。

### AI/RAG 专家

- 关注点：检索质量、引用可信、模板化回复误判。
- 判定：semantic/hybrid/keyword 设定 pass-rate 门槛；workflow 回答必须带可匹配引用。

### LLM 专家

- 关注点：注入/危险调用拦截、模型降级兜底。
- 判定：危险模式必须被 safety node 拦截；缺失模型依赖时仍可受控退化并可观测。

### ML 专家

- 关注点：成本估算链路可验证、输入边界稳定、结果可回归。
- 判定：成本估算 API+workflow 集成用例通过；边界输入不应导致崩溃或不可解释错误。

## 4. 基线执行集（最小但关键）

```bash
# 1) 安全/稳定性（脱敏 + workflow 关键节点）
.venv_capstone/bin/python -m pytest -q \
  tests/unit/security/test_redaction_service.py \
  tests/unit/test_redaction_service.py \
  tests/unit/test_main_runtime_contracts.py \
  tests/unit/test_workflow_orchestrator_pipeline.py

# 2) 成本估算（ML 关键路径）
.venv_capstone/bin/python -m pytest -q \
  tests/integration/test_cost_estimation_api.py \
  tests/integration/test_workflow_cost_estimation_query_api.py

# 3) 动态执行（代码执行与沙箱门禁）
.venv_capstone/bin/python -m pytest -q \
  tests/integration/test_data_analysis_runtime_gate.py \
  tests/integration/test_executor_provider_fallback.py

# 4) RAG 全链路 E2E（含引用质量）
RAG_E2E_REQUIRE_EMBEDDING_READY=true \
.venv_capstone/bin/python scripts/testing/run_construction_rag_e2e_validation.py

# 5) 前后端联通 smoke
cd frontend
npm run test:e2e -- tests/e2e/core-user-journeys.spec.ts \
  -g "workflow chat sends message and renders AI response"
```

## 5. 用例集合与通过标准

### A. RAG E2E

- 存储通过：`storage_pass = true`
- embedding 后端通过：`embedding_ready_pass = true`
- 检索通过：`semantic>=0.5`、`hybrid>=0.75`、`keyword>=0.75`
- Workflow 通过：`workflow_api_pass = true`
- 质量通过：`workflow_quality_pass = true`（非模板、含引用、引用可匹配）

### B. Cost Estimation/ML

- API 用例全部通过
- workflow 查询链路可返回稳定结构与有效预测结果

### C. 动态执行

- 运行时 gate 要求真实执行成功条件成立
- provider fallback 行为符合预期，不出现未处理异常

### D. 安全与联通

- 脱敏：邮箱/手机号/ID/IP 在中英文与大文本场景正确处理
- 安全拦截：危险调用（如 `subprocess.Popen`）被阻断
- 前后端：workflow chat e2e 用例通过

## 6. 日志与证据要求

- 每次执行输出到 `logs/test-driven-optimization/YYYY-MM-DD/NN_*.log`
- 每个 P0/P1 缺陷必须附：
  - 复现命令
  - 失败日志路径
  - 通过日志路径（修复后）
  - 影响范围与优先级
- RAG 必须保留结构化报告：
  - `logs/construction_rag_e2e_validation_report.json`

## 7. 回归策略

- 每次修复后执行对应最小回归集；
- 每日执行 `make test-phase1-gate` 作为交付门禁；
- 发布前执行完整基线五步并归档日志。
