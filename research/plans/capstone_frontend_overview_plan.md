# Industry AI Flow 前端概要规划（Capstone）

## 1. 结论先行（推荐方案）

建议采用：**FastAPI 后端 + Next.js（React）前端（前后端分离）**。  
同时保留你们已有的 Streamlit 工具页作为内部调试/管理入口（不作为主展示界面）。

原因（按你当前目标排序）：
1. Capstone 展示更看重视觉表现与交互质感，Next.js 显著优于 Streamlit/Flask 模板页。
2. 你们后端 API 已经比较完整，适合直接被前端消费，不需要重写业务逻辑。
3. 后续组员协作时，前后端边界清晰，能并行推进。

---

## 2. 方案权衡（高层）

### A) Streamlit
- 优点：开发快，Python 同栈，上手成本低。
- 缺点：UI 个性化和复杂交互上限低；Capstone 展示“设计感”不占优。
- 结论：适合作为**内部工具/应急 fallback**，不建议作为主前端。

### B) Flask + HTML（一体化）
- 优点：简单直接，部署路径短。
- 缺点：前端工程能力弱，后续复杂交互和视觉升级成本高。
- 结论：适合极简 demo，不适合你当前“重展示效果”的方向。

### C) React / Next.js（前后端分离）
- 优点：UI/交互天花板高；组件化和页面组织清晰；更符合现代展示预期。
- 缺点：前端工程复杂度更高，需要明确 API 契约。
- 结论：**最优平衡**，推荐作为主路线。

---

## 3. 推荐的前端信息架构（IA）

建议主导航（左侧菜单）：
1. `Overview`（系统状态与能力总览）
2. `AI Workflow Chat`（自然语言入口，统一问答/路由）
3. `Cost Estimation`（成本估算主页面）
4. `Documents`（文档上传与版本管理）
5. `Data Analysis`（数据分析与可视化）
6. `Prompt Admin`（Prompt 管理与实验）
7. `LLM Cost & Policy`（调用成本和预算策略）

建议角色分层：
1. `Demo User`：看核心能力（Chat、Cost、Documents、Data Analysis）。
2. `Admin/Operator`：额外看到 Prompt 与预算策略页面。

---

## 4. 核心页面定义（概要）

## 4.1 Overview
- 展示：系统健康、当前路由模式、近期调用量、演示快捷入口。
- 目标：答辩开场 30 秒内让评委看懂系统组成与状态。

## 4.2 AI Workflow Chat（统一入口）
- 输入自然语言问题，显示：意图、模型路由、答案、引用/trace 信息。
- 这里是“AI 赋能建筑行业”的主叙事入口。

## 4.3 Cost Estimation
- 单条预测：表单输入项目特征 -> 返回预测成本和区间。
- 批量预测：上传 CSV -> 返回批量结果（表格 + 导出）。
- 训练入口建议只对 Admin 可见（避免误操作影响演示稳定性）。

## 4.4 Documents
- 上传、替换、软删除、恢复版本、查看操作日志/统计。
- 支撑 RAG 知识库可维护性。

## 4.5 Data Analysis
- 上传数据、触发分析与可视化生成、查看结果文件。
- 用于展示“AI workflow + 动态分析执行”能力。

## 4.6 Prompt Admin
- Prompt 列表、编辑、测试、实验流量、指标查看。
- 你们现有 `tools/prompt-admin` 可以作为过渡参考实现。

## 4.7 LLM Cost & Policy
- 租户用量统计、预算查看与策略更新。
- 对“本地+云端混合成本治理”形成可视化闭环。

---

## 5. 页面与后端 API 对接矩阵（基于当前代码）

| 页面 | 首选 API | 备注 |
|---|---|---|
| Overview | `GET /health`, `GET /api/v1/workflow/health`, `GET /api/v1/cost-estimation/health` | 组合健康状态卡片 |
| AI Workflow Chat | `POST /api/v1/workflow/query` | 统一编排入口，优先使用 |
| AI Workflow Chat（备选） | `POST /api/v1/query`, `POST /query/dispatch` | 分别对应增强 RAG 与调度直连 |
| Cost Estimation | `POST /api/v1/cost-estimation/predict`, `POST /api/v1/cost-estimation/predict/batch` | 主功能 API |
| Cost Estimation（Admin） | `POST /api/v1/cost-estimation/train` | 训练操作建议加权限门禁 |
| Documents | `POST /documents/upload`, `POST /api/v1/documents/update`, `POST /api/v1/documents/replace`, `DELETE /api/v1/documents/{doc_id}` | 上传与版本管理并存 |
| Documents | `GET /api/v1/documents/operations/log`, `GET /api/v1/documents/statistics`, `POST /api/v1/documents/{doc_id}/restore/{version}` | 运维与回滚 |
| Data Analysis | `POST /data/upload`, `POST /data/analyze`, `POST /visualization/generate`, `GET /files/visualizations/{filename}` | 展示分析到图表闭环 |
| Prompt Admin | `/api/prompts/*` | 已有完整 CRUD + 实验 API |
| LLM Cost & Policy | `GET /llm/usage`, `GET /llm/budget/{tenant_id}`, `POST /llm/budget/{tenant_id}` | 成本治理 |
| Feedback（可嵌入 Chat） | `POST /api/v1/feedback` | 回答后“有帮助/无帮助” |

说明：
1. 当前接口前缀存在历史并存（`/api/v1/*` 与无前缀路径并存），前端建议先通过一个 `apiClient` 统一封装，避免页面层硬编码。
2. 后续可再做“统一前缀治理”，但不作为当前 Capstone 前端启动阻塞项。

---

## 6. 实施节奏（不阻塞后端开发）

## Phase 0（1-2天）：前端骨架与契约冻结
1. 确定技术栈：Next.js + TypeScript + UI 组件库（如 shadcn/ui）。
2. 建立页面路由壳和导航，不接真实 API（先用 mock）。
3. 冻结一版前端所需 API 契约（字段级别）。

## Phase 1（2-4天）：主链路打通（答辩最关键）
1. 打通 `AI Workflow Chat`。
2. 打通 `Cost Estimation`（单条 + 批量）。
3. 做错误态与加载态，保证演示连贯。

## Phase 2（2-4天）：能力补全
1. 打通 Documents 和 Data Analysis 页面。
2. 接入 LLM Cost & Policy 页面（展示混合策略与预算控制）。

## Phase 3（1-3天）：展示优化
1. 视觉统一（颜色、层级、卡片与图表风格）。
2. 演示脚本化（预置样例输入、可复现流程）。
3. 准备 fallback：保留 Streamlit 作为应急入口。

---

## 7. 对你提出流程的校正建议

你给出的流程很完整，但对 Capstone 建议改为“**契约优先 + 垂直切片**”：
1. 明确展示场景与核心用户路径（先定义故事线）。
2. 锁定关键 API 契约（不必等待所有后端完成）。
3. 先做可演示的前端骨架与主链路页面。
4. 再补数据模型细化和次要能力。

这能避免“后端全部完成后才开始前端”，导致展示准备时间不足。

---

## 8. 最小可执行决策（现在就可以定）

1. 主前端选型：`Next.js + TypeScript`。  
2. 主入口：`/api/v1/workflow/query`（自然语言统一入口）。  
3. 成本估算入口：`/api/v1/cost-estimation/predict` 与 `/predict/batch`。  
4. Streamlit 保留为内部工具和答辩应急 fallback，不作为主 UI。  
5. 本周目标：先完成页面骨架 + Chat + Cost 两条主链路。

