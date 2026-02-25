# Industrial AI Flow TDO 缺陷发现与优化反推报告（2026-02-20）

## 1. P0/P1 缺陷清单

### 缺陷 A（P0）：代码执行数据文件可越权读取宿主机路径
- 优先级：P0（安全）
- 复现步骤：
  1. 运行 `pytest -q -vv tests/unit/test_tdo_p0_p1_findings.py::test_p0_docker_executor_rejects_out_of_workspace_data_files`
  2. 用例向 `DockerExecutor.execute_code` 传入 `data_files=["/etc/hosts"]`
- 失败证据（修复前）：
  - 断言失败：`assert result["success"] is False`
  - 实际：`result["success"] == True`，说明系统尝试读取并透传了越权路径文件。
- 影响范围：
  - 代码执行链路（动态代码生成/执行、数据分析工具）存在宿主机敏感文件泄漏风险。
- 最小修复：
  - 在 `backend/services/code_executor/docker_executor.py` 增加 `_resolve_allowed_data_file`。
  - 限制可读路径到：项目工作目录、`TEMP_DATA_DIR`、系统临时目录。
- 回归验证：
  - `tests/unit/test_tdo_p0_p1_findings.py::test_p0_docker_executor_rejects_out_of_workspace_data_files` 必须通过。

### 缺陷 B（P1）：workflow runner 异常导致 API 500 崩溃
- 优先级：P1（稳定性/可运维）
- 复现步骤：
  1. 运行 `pytest -q -vv tests/unit/test_tdo_p0_p1_findings.py::test_p1_workflow_query_runner_exception_is_controlled`
  2. 注入一个抛出异常的 fake runner 调用 `/api/v1/workflow/query`
- 失败证据（修复前）：
  - 断言失败：`assert response.status_code == 200`
  - 实际：`500 Internal Server Error`
- 影响范围：
  - 前端调用链路在后端 runner 异常时直接崩溃，缺乏受控降级与可观测错误结构。
- 最小修复：
  - 在 `backend/api/workflow_query_routes.py` 对 `workflow.run_workflow(...)` 增加 `try/except`。
  - 统一返回 `success=False`、`error="workflow execution failed"`，并保留 trace/session 元数据及审计/指标。
- 回归验证：
  - `tests/unit/test_tdo_p0_p1_findings.py::test_p1_workflow_query_runner_exception_is_controlled` 必须通过。
  - `tests/unit/test_workflow_query_routes.py` 全通过。

### 缺陷 C（P1）：provider 层未透传 timeout，执行超时语义失真
- 优先级：P1（稳定性/正确性）
- 复现步骤：
  1. 运行 `pytest -q -vv tests/unit/test_tdo_p0_p1_findings.py::test_p1_docker_provider_execute_propagates_timeout`
  2. 使用 fake executor 观察 `timeout` 入参
- 失败证据（修复前）：
  - 断言失败：`assert fake_executor.timeout_seen == 7`
  - 实际：`None`
- 影响范围：
  - 执行超时配置在 manager/provider 之间失效，可能导致长时间阻塞。
- 最小修复：
  - `backend/services/code_executor/providers/docker_provider.py` 透传 `timeout_s` 到 `executor.execute(..., timeout=timeout_s)`。
  - `backend/services/code_executor/docker_executor.py` 的 `execute`/`_run_container` 支持 `timeout` 参数并应用到 `container.wait(...)`。
- 回归验证：
  - `tests/unit/test_tdo_p0_p1_findings.py::test_p1_docker_provider_execute_propagates_timeout` 必须通过。

### 缺陷 D（P0）：数据传递服务可复制任意宿主机路径文件
- 优先级：P0（安全）
- 复现步骤：
  1. 运行 `pytest -q -vv tests/unit/test_data_transfer_path_guard.py::test_data_transfer_rejects_outside_allowed_paths`
  2. 调用 `DataFileTransfer.transfer_file_for_docker("/etc/hosts", "file_mapping")`
- 失败证据（修复前）：
  - 函数会进入复制流程，具备将任意路径文件转存到 `TEMP_DATA_DIR` 的能力。
- 影响范围：
  - 迭代代码执行与数据预处理链路可绕过下游执行器路径校验，实现宿主机文件外带。
- 最小修复：
  - 在 `backend/services/data_transfer.py` 增加 `_resolve_allowed_source_file` 白名单校验。
  - 白名单限定为：项目工作目录、`TEMP_DATA_DIR`、系统临时目录。
- 回归验证：
  - `tests/unit/test_data_transfer_path_guard.py` 全通过。

## 2. 修复后回归结果
- 回归命令见：`docs/TDO_TEST_PLAN.md` 第 8 节。
- 实测结果：
  - 38 passed / 0 failed
  - 证据文件：
    - `logs/tdo_optimization_regression.log`
    - `logs/tdo_optimization_regression.xml`

## 3. 反推优化建议（最小改动优先）
- 统一代码执行文件路径策略：
  - 将 path allowlist 下沉为共享函数，覆盖 Docker/PPIO/legacy executor，避免策略漂移。
- workflow 错误契约标准化：
  - 将 `trace_id/session_id/error_class` 统一纳入失败响应 schema 与告警字段，便于前端和 SRE 处理。
- 超时/重试策略一致性：
  - 明确 API 层、workflow 层、provider 层、容器层的 timeout 优先级并写成契约测试。
