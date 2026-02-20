# Industrial AI Flow 测试驱动优化方案（TDO）

## 1. 目标与原则
- 目标：以测试为主线优先暴露高价值缺陷（P0/P1），再以最小改动修复并回归验证。
- 原则：可重复、可证据化、可回归；先关键链路，再扩面。
- 执行日期：2026-02-20。

## 2. 范围
- RAG 全链路：入库、分块、向量化、检索、生成、引用。
- Cost Estimation/ML：训练、推理、批量预测、边界输入。
- 动态代码生成与执行：metadata 驱动、沙箱执行、安全边界、超时语义。
- 前后端主通路：页面触发对应 API 路径（以 `/api/v1/workflow/query` 合同与回路为后端判定点）。

## 3. TeamAgents 角色关注点与验收标准
- 资深架构师：
  - 关注：链路连通、错误边界、降级路径、可观测性。
  - 验收：异常路径返回受控响应；关键节点有 trace/session/runner 元数据。
- 资深 QA：
  - 关注：可复现步骤、失败证据、回归稳定性。
  - 验收：每个 P0/P1 缺陷都有固定用例与断言；回归套件可一键执行。
- AI/RAG 专家：
  - 关注：检索-生成一致性、来源可追踪性、检索删除后行为。
  - 验收：RAG 入库检索可证明，删除后不可检索。
- LLM 专家：
  - 关注：执行链路安全闸门、模型异常兜底。
  - 验收：危险代码被拒绝；工作流异常不崩溃并可审计。
- ML 专家：
  - 关注：训练-预测可复现、区间输出合理、输入边界。
  - 验收：同输入预测稳定；区间上下界包含点预测值。

## 4. 基线测试集合（最小关键）
- `tests/integration/test_tdo_baseline_paths.py`
  - `test_tdo_rag_ingest_retrieve_generate_baseline`
  - `test_tdo_rag_delete_removes_retrieval_baseline`
  - `test_tdo_cost_estimation_train_predict_baseline`
  - `test_tdo_code_generation_execution_baseline`
  - `test_tdo_frontend_api_workflow_roundtrip_baseline`
- `tests/unit/test_tdo_risk_probes.py`
  - 安全探针：危险调用阻断、safety_node 阻断、执行工具拒绝危险 payload。

## 5. 缺陷挖掘用例（P0/P1）
- `tests/unit/test_tdo_p0_p1_findings.py`
  - `test_p1_workflow_query_runner_exception_is_controlled`
  - `test_p0_docker_executor_rejects_out_of_workspace_data_files`
  - `test_p1_docker_provider_execute_propagates_timeout`
  - `test_p0_ppio_provider_rejects_out_of_workspace_data_files`
- `tests/unit/test_data_transfer_path_guard.py`
  - `test_data_transfer_rejects_outside_allowed_paths`
  - `test_data_transfer_accepts_workspace_file_and_cleans_up`

## 6. 通过标准
- 功能通过：
  - 基线链路测试全部通过。
  - 缺陷挖掘用例在修复前可失败、修复后全部通过。
- 质量通过：
  - 无新增崩溃型 500（未捕获异常导致）。
  - 代码执行输入文件路径不能越权读取。
  - timeout 参数语义一致（调用层到执行层透传）。

## 7. 日志与证据要求
- 必须留存：
  - pytest 终端日志：`logs/tdo_optimization_regression.log`
  - junit 报告：`logs/tdo_optimization_regression.xml`
- 单条缺陷证据至少包含：
  - 用例名
  - 断言失败/通过结果
  - 复现命令
  - 影响面说明

## 8. 执行命令
```bash
source .venv_tdo/bin/activate
pytest -q -vv \
  tests/integration/test_tdo_baseline_paths.py \
  tests/unit/test_tdo_p0_p1_findings.py \
  tests/unit/test_data_transfer_path_guard.py \
  tests/unit/test_workflow_query_routes.py \
  tests/unit/test_code_execution_tool_provider_mode.py \
  tests/unit/test_tdo_risk_probes.py \
  tests/unit/test_data_analysis_tool_path_mapping.py \
  tests/unit/test_docker_provider_health.py \
  --junitxml=logs/tdo_optimization_regression.xml \
  2>&1 | tee logs/tdo_optimization_regression.log
```

## 9. 回归策略
- 每次涉及以下模块改动必须触发回归：
  - `backend/api/workflow_query_routes.py`
  - `backend/services/code_executor/*`
  - `backend/services/workflows/*`
  - `backend/services/rag_engine.py`
  - `backend/services/cost_estimation_service.py`
- 发布前 Gate：
  - 全部 P0/P1 用例通过。
  - 关键链路基线通过并产出日志工件。
