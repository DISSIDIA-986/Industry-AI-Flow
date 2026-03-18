# 2026-02-19 前端专家评审总结（提交老板版）

## 1. 评审结论（Go / No-Go）

**结论：No-Go（暂不具备部署或交付测试条件）**。

当前前端存在明确的 P0 阻断项：生产构建失败、核心接口契约漂移、错误被 mock fallback 掩盖，导致“页面可操作”与“真实后端可用”不一致。  
在未完成下文 Must-Change 之前，不建议进入交付测试。

---

## 2. 专家评审团组成

- 项目架构师（主席）：负责架构一致性、取舍与最终技术裁决
- 前端负责人：负责页面、组件、工程治理和可构建性
- 后端 API 负责人：负责接口契约和版本治理
- AI/RAG 专家：负责知识库与推理链路可落地性评估
- 测试与安全负责人：负责发布门禁、集成测试与安全基线

---

## 3. 评审范围与方法

- 页面设计与交互一致性
- 组件复用与代码质量
- 前后端 API / Endpoint 交互正确性
- 前端侧安全风险
- 可部署性实证（`npm run build` / `npm run lint`）

---

## 4. 关键发现（按严重级别）

### P0-1：前端当前不可构建，发布链路阻断

- `next build` 失败（Turbopack 报 29 个错误）。
- 证据：
  - 页面依赖不存在组件：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/app/(mvp)/documents-new/page.tsx:7`
  - 图表导入名与实际导出不一致：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/app/(simple)/simple-dashboard/page.tsx:6` vs `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/components/charts/index.tsx:17`
  - 页面导入了 `api-client` 中不存在的导出（如 `runDataAnalysis` / `uploadDataFile` / `getLlmBudget` / `listPrompts`）：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/app/(mvp)/data-analysis/page.tsx:6`, `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/app/(mvp)/llm-cost-policy/page.tsx:6`, `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/app/(mvp)/prompt-admin/page.tsx:6`

### P0-2：前后端接口契约漂移，核心业务请求将失败

- 批量成本预测路径不一致：前端 `/predict-batch`，后端 `/predict/batch`。
  - 前端：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/api-client.ts:445`
  - 后端：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/backend/api/cost_estimation_routes.py:194`
- 成本预测请求体不一致：前端直接传 `features`，后端要求 `{ project, confidence_quantile }`，且 `project` 需要更多必填字段（不止前端定义的 6 个）。
  - 前端：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/api-client.ts:434`
  - 后端：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/backend/api/cost_estimation_routes.py:81`
- 前端 `authApi` 调用的 `/api/v1/auth/*` 在当前后端路由中不存在（登录/注册/登出/me 均缺失），真实请求将 404。
  - 前端：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/api-client.ts:112`
  - 后端路由注册：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/backend/main.py:155`
- 文档上传字段不一致：前端 `files`（复数），后端 `file`（单数）。
  - 前端：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/api-client.ts:179`
  - 后端：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/backend/main.py:377`
- `upload()` 仍走统一 `request()`，默认带 `Content-Type: application/json`，会破坏 `FormData` 上传语义。
  - `request()`：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/api-client.ts:13`
  - `upload()`：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/api-client.ts:84`

### P1-1：生产路径存在“真实请求失败后自动 mock”机制，掩盖真实故障

- 登录、查询、文档、成本接口均出现 catch 后回退 mock 的模式，导致假通过。
  - 示例：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/api-client.ts:117`, `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/api-client.ts:157`, `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/api-client.ts:183`, `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/lib/api-client.ts:437`
- E2E 也对核心端点做了广泛 mock，且包含错误路径 `/predict-batch`，无法证明真实集成可用。
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/tests/e2e/utils/session.ts:139`

### P1-2：前端安全基线不足（密钥/内部信息暴露风险）

- `apiKey` 与 token 持久化到 `localStorage`，XSS 下容易被窃取。
  - API key：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/components/app-config-context.tsx:45`
  - token：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/contexts/AuthContext.tsx:43`
- 代理报错返回 `target`（上游地址），暴露内部网络与路由细节。
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/app/api/backend/[...path]/route.ts:67`

### P1-3：工程与架构治理不收敛，造成交付风险

- 同仓存在双前端形态（`frontend/` 与 `frontend/nextjs/`），且 `lint` 扫到 `frontend/nextjs/.next/**` 生成物，噪音显著。
  - ESLint ignore 仅覆盖根 `.next`：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/eslint.config.mjs:11`
- 页面多版本并存（`documents` / `documents-new` / `documents-integrated` 等），用户体验与维护口径不一致。
- 架构文档仍保留 `Streamlit Web UI` 主入口描述，与当前 Next.js 主线不一致。
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/docs/ARCHITECTURE.md:10`
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/docs/ARCHITECTURE_DIAGRAM.html:426`

---

## 5. 维度化评审摘要

### 5.1 前端页面设计与交互

- 发现明显一致性问题：同类页面多版本并存，交互和信息架构不统一。
- 存在“能点但不一定真实可用”的体验风险（mock fallback 导致）。

### 5.2 组件复用与代码质量

- 组件命名/导出不一致，反映复用治理失效（非单一组件契约）。
- `lint` 当前为 **108 errors / 65 warnings**，不满足交付门槛。

### 5.3 前后端交互逻辑

- 多处 endpoint 与 payload 不一致，且缺少统一契约生成流程。
- 当前状态无法证明“端到端真实数据流”符合预期设计。

### 5.4 安全性

- 密钥与令牌持久化策略偏弱。
- 代理错误返回泄露上游目标信息。
- 安全问题未到“立即失陷”，但对交付阶段属于高优先级整改项。

---

## 6. Must-Change（仅保留 5 项，按优先级）

### MC-1（P0）：恢复单一可构建前端主线

- 收敛页面与组件依赖，移除/隔离不可编译页面分支。
- **退出标准**：`npm run build` 通过，主导航全链路可访问。

### MC-2（P0）：冻结 API 契约并自动生成前端类型客户端

- 以 OpenAPI 为唯一真源（SSOT），前后端同版发布。
- **退出标准**：`/cost-estimation`、`/documents/upload`、`/query`、`/auth` 契约一致并有契约测试。

### MC-3（P1）：移除生产路径 mock fallback

- mock 仅保留在测试环境开关下。
- **退出标准**：生产构建中任一 API 失败均可观测、可告警、不可“静默假成功”。

### MC-4（P1）：安全加固（密钥与代理）

- API key 不再持久化 `localStorage`；token 改为 HttpOnly Cookie 或最小暴露策略。
- 代理错误响应去除 `target` 等内部信息。
- **退出标准**：通过一次前端安全基线检查（XSS/信息泄露项）。

### MC-5（P1）：建立真实后端集成 Gate（CI）

- 增加“真实后端 + 前端 + 数据库”最小集成流水线，禁止仅 mock 绿灯。
- **退出标准**：关键用户旅程（登录/查询/上传/成本估算）在 CI 真实环境通过。

---

## 7. 与 2026 开源 RAG 现状对齐（务实路线）

### 建议采纳（务实、可落地）

- **评估与观测优先补齐**：先引入 RAG 评估基线（如 Ragas）和契约化测试，不先做大规模底座迁移。
- **工作流编排可渐进借鉴**：LangGraph 已进入 1.0 稳定线，可用于复杂多步骤流程编排，但建议“局部替换、逐步验证”。
- **检索栈避免重复造轮子**：可择一评估 Haystack 2.x 或 LlamaIndex 当前稳定线的组件能力，用于补齐可观测与检索管道标准化。

### 建议暂缓

- 对处于 **RC/预览** 的能力（如 Dify 1.14.0-rc1）仅做 PoC，不直接进入本项目生产主线。

---

## 8. 建议里程碑（两周版本）

- **第 1 周**：完成 MC-1 / MC-2（构建恢复 + 契约统一）
- **第 2 周**：完成 MC-3 / MC-4 / MC-5（去 mock、加固安全、补 CI Gate）
- 通过后再评估是否进入交付测试（Go/No-Go 二次评审）

---

## 9. 外部参考（2026-02-19 检索）

- LangGraph releases: https://github.com/langchain-ai/langgraph/releases
- LlamaIndex releases: https://github.com/run-llama/llama_index/releases
- Haystack releases: https://github.com/deepset-ai/haystack/releases
- Haystack 1.x EOL 公告: https://github.com/deepset-ai/haystack/discussions/8935
- Haystack PyPI（2.x 近期版本）: https://pypi.org/project/haystack-ai/
- Dify releases: https://github.com/langgenius/dify/releases
- Ragas releases: https://github.com/explodinggradients/ragas/releases

---

## 10. Double Check 复核记录（2026-02-19）

已用可执行验证补强关键结论（非纯推断）：

- 构建复测：`frontend` 下 `npm run build` 仍失败（29 errors，含缺失组件与不存在导出）。
- Lint 复测：`npm run lint` 仍失败（108 errors / 65 warnings）。
- 路由枚举（`.venv_capstone_arm64` + FastAPI app）：
  - 存在：`/api/v1/cost-estimation/predict`、`/api/v1/cost-estimation/predict/batch`、`/api/v1/query`、`/api/v1/workflow/query`
  - 缺失：`/api/v1/auth/login`、`/api/v1/auth/register`、`/api/v1/auth/logout`、`/api/v1/auth/me`
- 请求回放（FastAPI `TestClient`）：
  - `POST /api/v1/cost-estimation/predict`（前端当前 payload）=> `422`
  - `POST /api/v1/cost-estimation/predict-batch` => `404`
  - `POST /api/v1/query` body=`{query}` => `422`（缺 `question`）
  - `POST /api/v1/documents/upload` field=`files` => `422`
  - `POST /api/v1/documents/upload` field=`file` => `200`
- 默认安全门禁复核：
  - `GET /api/v1/health` 在默认配置下返回 `401`（缺 API key）
  - 配置来源：`/Users/openclaw/Documents/github.com/Industry-AI-Flow/backend/config.py:168`
