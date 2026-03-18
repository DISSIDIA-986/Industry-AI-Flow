# Industry AI Flow 评审结论二次复核（Double Check）

- 复核日期：2026-02-19
- 复核目的：对首次专家评审中的关键结论做可执行验证，减少“仅推理结论”风险。
- 复核方式：运行关键门禁、单测、接口探测、数据库核查、静态检查（flake8/mypy）。

## 1. 结论校准总览

| 主题 | 首轮结论 | 二次复核结果 | 结论状态 |
|---|---|---|---|
| release gate 失败 | 失败，属于阻断 | 失败可复现；但可通过向 DB 注入最小 Prompt 集后恢复通过 | 已修正：根因偏“初始化流程缺陷” |
| Prompt 缺失 | Prompt 是主要问题 | `prompts` 表为 0；插入 3 条必需模板后关键失败用例转为通过；删除后再次失败 | 已证实 |
| 数据分析/代码生成链路 | 存在断裂风险 | `DataAnalysisAgent` 导入即报错（缺模块）；`/api/v1/unified/query` 实测返回 success=false（LangChain API 断裂） | 已证实 |
| RAG 能力 | 可用 | construction RAG E2E 报告 overall_pass=true，但 workflow 回复存在明显降级特征 | 已证实（可用但质量需收敛） |
| 测试可移植性 | 有硬编码路径风险 | 多个测试包含 `/Users/niuyp/...` 绝对路径 | 已证实 |

## 2. 关键复核证据

## 2.1 Release Gate 的“可复现失败 + 条件性恢复”

1. 在空 Prompt 数据下：
- `make test-release-gate` 失败（卡在 `test_workflow_query_uses_fallback_runner_when_init_fails`）。

2. 注入最小 Prompt 集（3 条）后：
- 同一失败用例变为通过。
- `make test-release-gate` 全绿。

3. 清理这 3 条 Prompt 后：
- 同一失败用例再次失败。

结论：
- 这是“强状态依赖”问题，不是纯随机失败。
- 当前项目缺乏可靠的 Prompt 启动基线，导致同一代码在不同数据库状态下出现相反结论。

## 2.2 Prompt 初始化流程存在结构性缺陷

1. `make db-setup` 依赖 `scripts/migration/seed_intent_prompts.py`。
2. 脚本实测无法完成初始化：
- 路径注入错误（`project_root` 指向 `scripts/` 而非仓库根）。
- 依赖不存在模块：`backend.services.intent_classifier`。
3. 即便脚本可运行，其内容只覆盖 Intent 类 Prompt，不覆盖工作流模板注册要求的：
- `rag/construction_rag_grounded_qa`
- `ocr/drawing_ocr_structured_parse`
- `analysis/code_exec_data_analysis_explainer`

结论：
- Prompt 引导链路当前不可作为“交付前自动化初始化”使用。

## 2.3 动态代码生成与高级分析能力的实测结果

1. `DataAnalysisAgent` 运行时导入失败：
- `backend/services/data_analysis/data_analysis_agent.py` 引用 `backend.services.ollama_client`（不存在）。

2. `/api/v1/unified/query` 实测：
- 返回 `success=false`。
- 错误为 `cannot import name 'create_agent' from langchain.agents`。

3. `/api/v1/data/analyze` 实测：
- 传入真实相对路径会被请求清洗器拒绝（400）。
- 传入文件名后可返回 200，但业务 `success=false`（代码执行器不可用）。
- 审计日志仍记为 `status=success`，存在观测误导风险。

结论：
- 这条能力链路不是“完全不可用”，但关键入口存在明显断点和错误状态上报偏差。

## 2.4 测试体系真实性复核

1. `tests/unit/test_data_analysis.py`：`pytest` 结果为 `no tests ran`。
2. `tests/integration/test_eda_functionality.py`：收集阶段就因 `create_agent` 导入错误而中断。
3. 多个测试文件硬编码绝对路径 `/Users/niuyp/...`。

结论：
- 数据分析相关测试覆盖存在“名义覆盖 > 实际覆盖”的情况。

## 2.5 静态检查工具复核

- `flake8 backend/services/data_analysis/data_analysis_agent.py`：大量风格与可维护性问题。
- `mypy backend/services/data_analysis/data_analysis_agent.py`：暴露多处类型与依赖问题（并连带 code_executor 区域）。

说明：
- 这些结果不直接等价于生产故障，但支持“该链路成熟度不足”的判断。

## 3. 复核后风险分级（修订版）

## P0（必须先解决）

1. Prompt 启动基线不可自动化重建。
2. `db-setup` 所依赖的 seed 脚本失效且覆盖不足。
3. release 结论依赖 DB 隐式状态，缺少可重复初始化与验收前置条件。

## P1（本轮交付前强烈建议解决）

1. `/api/v1/unified/query` 入口在当前依赖组合下稳定失败。
2. 数据分析主链路存在入口校验与执行环境耦合问题；失败态审计标记不准确。
3. 数据分析相关测试未有效纳入门禁（no tests ran / collection error）。
4. 测试可移植性问题（硬编码绝对路径）。

## 4. “先规划、再执行”的落地计划（复核版）

## 阶段 A（T+2 天，先恢复可重复性）

1. 新建“工作流必需 Prompt 基线”初始化脚本（直接覆盖 rag/ocr/analysis + intent 关键模板）。
2. 在 `db-setup` 中替换失效 seed 脚本并增加执行后校验（缺任一模板即 fail）。
3. 将 `test-release-gate` 放在“初始化完成之后”执行，形成固定流水线。

验收：
1. 在空数据库上一次性执行后，`test-release-gate` 稳定通过。
2. `prompts` 表中必需模板齐全且可查询。

## 阶段 B（T+1 周，修复核心能力断点）

1. 修复 unified agent 对 LangChain API 的兼容实现（或锁定兼容版本并在依赖中固化）。
2. 修复 `DataAnalysisAgent` 错误导入与数据分析接口的输入契约（路径/文件映射策略统一）。
3. 修正审计状态：业务失败不得记为 success。

验收：
1. `/api/v1/unified/query` 与 `/api/v1/data/analyze` 至少各有 1 条稳定通过的集成用例。
2. 失败路径 audit 与 HTTP 语义一致。

## 阶段 C（T+2 周，补齐门禁真实性）

1. 把当前“脚本式测试”改成可被 pytest 收集的正式测试。
2. 清理 `/Users/...` 绝对路径，统一夹具路径与临时目录。
3. 把数据分析链路加入 release gate（最小冒烟 + 回归）。

## 5. 管理层决策建议（复核后）

1. 可以继续内部研发与受控演示，但不建议在现状态直接进入正式交付测试。 
2. 先完成阶段 A，再触发下一次评审；阶段 A 不通过时，不进入阶段 B 开发扩展。 
3. 所有后续改造建议须附“可执行证据”（命令 + 输出 + 验收门槛），避免方向性误判。

## 6. 本次复核已执行的关键命令（节选）

1. `.venv_capstone/bin/python -m pytest -q tests/unit/test_workflow_query_routes.py::test_workflow_query_uses_fallback_runner_when_init_fails`
2. `make test-release-gate`
3. `psql -d ai_workflow -c "select count(*) from prompts;"`
4. `PYTHONPATH=. .venv_capstone/bin/python scripts/migration/seed_intent_prompts.py`
5. `PYTHONPATH=. .venv_capstone/bin/python - <<...>>`（最小 Prompt 注入与回归验证）
6. `PYTHONPATH=. .venv_capstone/bin/python - <<...>>`（`/api/v1/unified/query`、`/api/v1/data/analyze` 接口探测）
7. `.venv_capstone/bin/flake8 backend/services/data_analysis/data_analysis_agent.py`
8. `.venv_capstone/bin/mypy backend/services/data_analysis/data_analysis_agent.py`
9. `rg -n "/Users/" tests scripts backend docs`

