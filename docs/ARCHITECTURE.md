# Industry AI Flow Architecture

推荐先看交互式楼层图：`./ARCHITECTURE_DIAGRAM.html`

## Layer Map (6 Layers)

| Layer | Responsibility | Main code locations |
|---|---|---|
| L1 UI | 用户输入、展示、管理操作 | `frontend/`, API clients |
| L2 API Gateway | 路由、鉴权、参数校验、缓存入口 | `backend/main.py`, `backend/api/` |
| L3 Business Services | 工作流编排、意图识别、提示词策略、路由策略 | `backend/services/workflows/`, `backend/services/intent_classification/`, `backend/services/routing_decision.py`, `backend/services/prompt_manager.py` |
| L4 AI Runtime | RAG、LLM调度、代码执行、成本估算模型 | `backend/services/rag_engine.py`, `backend/services/llm_integration/dispatch_service.py`, `backend/services/code_executor/`, `backend/services/cost_estimation_service.py` |
| L5 Data Storage | 向量检索、提示词/用量/预算、模型工件 | PostgreSQL/pgvector + `workspace/models/cost_estimation/` |
| L6 Security & Platform | 脱敏、出站守卫、审计、指标、配置和发布门禁 | `backend/services/security/`, `backend/observability/`, `scripts/testing/`, `Makefile` |

## Core Flows

### 1) Workflow Query (RAG / Code / Hybrid LLM)
1. Request enters `backend/api/workflow_query_routes.py`.
2. Workflow runs pipeline in `backend/services/workflows/graph.py`.
3. Intent/routing/prompt nodes decide execution path.
4. Runtime calls RAG / dispatch / code execution services.
5. Data read/write through PostgreSQL + pgvector and usage tables.
6. Security/observability are applied across the path.

### 2) Cost Estimation
1. Request enters `backend/api/cost_estimation_routes.py`.
2. Service uses `backend/services/cost_estimation_service.py`.
3. Model artifact loaded from `workspace/models/cost_estimation/*.json`.
4. Prediction + confidence interval returned to API caller.

### 3) Prompt Admin
1. Request enters `backend/api/prompt_routes.py`.
2. Logic handled by `backend/services/prompt_manager.py`.
3. Prompt/experiment/usage metadata persisted in PostgreSQL tables.

## Connection Types

- Request flow: synchronous request path between layers.
- Control flow: orchestration, policy, and route decisions.
- Data flow: retrieval/writeback and artifact I/O.
- Security/observability flow: redaction, audit, metrics, and release gates.

## Mermaid Quick View

```mermaid
flowchart TD
  subgraph L1["L1 UI"]
    U1["Streamlit/Web UI"]
    U2["Prompt Admin UI"]
    U3["External API Client"]
  end

  subgraph L2["L2 API Gateway"]
    A1["FastAPI Routers"]
    A2["Auth + Tenant Scope"]
    A3["Input Validation"]
    A4["Query Cache"]
  end

  subgraph L3["L3 Business Services"]
    B1["Workflow Orchestrator"]
    B2["Intent Classifier"]
    B3["Prompt Selector / Manager"]
    B4["Routing & Budget Policy"]
  end

  subgraph L4["L4 AI Runtime"]
    R1["RAG Engine"]
    R2["LLM Dispatch Service"]
    R3["Code Execution Manager"]
    R4["Cost Estimation Service"]
  end

  subgraph L5["L5 Data Storage"]
    D1["PostgreSQL + pgvector"]
    D2["Prompt/Usage/Budget Tables"]
    D3["Model Artifacts"]
    D4["Document Chunks + Embeddings"]
  end

  subgraph L6["L6 Security & Platform"]
    S1["Redaction + Egress Guard"]
    S2["Observability + Audit"]
    S3["Config + Release Gates"]
    S4["Runtime Infrastructure"]
  end

  U1 --> A1
  U2 --> A1
  U3 --> A1

  A1 --> A2
  A1 --> A3
  A1 --> A4
  A1 --> B1
  A1 --> B3
  A1 --> R4

  B1 --> B2
  B2 --> B4
  B1 --> B3
  B1 --> R1
  B4 --> R2
  B1 --> R3

  R1 -.-> D1
  R1 -.-> D4
  B3 -.-> D2
  R2 -.-> D2
  R4 -.-> D3

  R2 -.-> S1
  B1 -.-> S2
  A1 -.-> S3
  R3 -.-> S4
  S2 -.-> D1
```
