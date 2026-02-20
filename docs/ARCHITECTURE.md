# Industry AI Flow - System Architecture

## Architecture Overview

Industry AI Flow adopts a six-layer layered architecture with clear responsibilities and well-defined dependency relationships from user interface to infrastructure.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     User Interface Layer                           │
│  Streamlit Web UI | Prompt Admin UI | External API Client          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                             │
│  FastAPI Routers | Authentication | Tenant Isolation | Validation   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Business Services Layer                           │
│  Workflow Orchestrator | Intent Classifier | Prompt Selector |      │
│  Routing Strategy | Budget Control                                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AI Runtime Layer                              │
│  RAG Engine | LLM Dispatch | Code Execution | Cost Estimation       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Data Storage Layer                             │
│  PostgreSQL + pgvector | Prompt Library | Usage Data | Models       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Security & Platform Layer                          │
│  Data Redaction | Egress Guard | Observability | Audit | Config     │
└─────────────────────────────────────────────────────────────────────┘
```

## Layer Details

### 1. User Interface Layer (L1 - UI Layer)

**Responsibility**: User interaction, data presentation, operation entry points

**Core Components**:
- **Next.js Web Application**: Modern React-based frontend with server-side rendering
  - User authentication and session management
  - Real-time chat interface for AI queries
  - Document management and visualization
  - Data analytics and cost estimation dashboards
  - Prompt management with version control
- **External API Client**: RESTful API supporting third-party integration

**Tech Stack**: Next.js 14, React 18, TypeScript, Tailwind CSS

**Main Code Locations**: `frontend/` (Next.js application), API client examples

**Key Features**:
- Server-side rendering for optimal performance
- Responsive design for mobile and desktop
- JWT-based authentication
- Real-time updates via WebSocket
- Comprehensive component library

---

### 2. API Gateway Layer (L2 - API Gateway Layer)

**Responsibility**: Route distribution, authentication, request validation, caching strategy

**Core Components**:
- **FastAPI Routers**: Unified API entry points
  - `/api/v1/workflow/query` - Workflow query
  - `/api/v1/cost/estimate` - Cost estimation
  - `/api/v1/prompts/*` - Prompt management
- **Authentication**: JWT token validation, tenant context management
- **Input Validation**: Pydantic model validation for request parameters
- **Query Cache**: Redis caching to reduce duplicate query costs

**Tech Stack**: FastAPI, Pydantic, Redis, JWT

**Main Code Locations**:
- `backend/main.py` - Application entry
- `backend/api/` - All route definitions
- `backend/middleware/` - Authentication middleware

---

### 3. Business Services Layer (L3 - Business Services Layer)

**Responsibility**: Business logic orchestration, intent recognition, intelligent routing

**Core Components**:
- **Workflow Orchestrator**: Manages complex query execution flows
- **Intent Classifier**: Identifies user query types (RAG/Code/Hybrid)
- **Prompt Selector**: Dynamically selects optimal prompt templates
- **Routing Strategy**: Intelligent routing based on cost, performance, and budget
- **Budget Control**: Usage monitoring and budget enforcement

**Tech Stack**: Python, LangGraph, Business Rules Engine

**Main Code Locations**:
- `backend/services/workflows/` - Workflow definitions
- `backend/services/intent_classification/` - Intent recognition
- `backend/services/routing_decision.py` - Routing logic
- `backend/services/prompt_manager.py` - Prompt management

---

### 4. AI Runtime Layer (L4 - AI Runtime Layer)

**Responsibility**: AI model execution, data processing, cost calculation

**Core Components**:
- **RAG Engine**:
  - Document embedding (OpenAI/Cohere embeddings)
  - Vector retrieval (pgvector)
  - Hybrid retrieval (BM25 + Semantic)
  - Reranking (Cohere Rerank)
- **LLM Dispatch Service**:
  - Multi-provider support (OpenAI, Anthropic, Cohere)
  - Intelligent failover
  - Cost tracking
- **Code Execution Manager**:
  - Docker container isolation
  - Sandbox execution
  - Timeout control
- **Cost Estimation Service**:
  - Linear regression model
  - Confidence interval calculation
  - Model version management

**Tech Stack**: LangChain, PostgreSQL + pgvector, Docker, scikit-learn

**Main Code Locations**:
- `backend/services/rag_engine.py` - RAG core logic
- `backend/services/llm_integration/dispatch_service.py` - LLM dispatch
- `backend/services/code_executor/` - Code execution
- `backend/services/cost_estimation_service.py` - Cost estimation

---

### 5. Data Storage Layer (L5 - Data Storage Layer)

**Responsibility**: Data persistence, vector storage, model artifact management

**Core Components**:
- **PostgreSQL + pgvector**: Primary database with vector retrieval support
  - `documents` - Document chunks and embeddings
  - `prompts` - Prompt templates
  - `usage` - Usage statistics
  - `budgets` - Budget configuration
- **Vector Index**: HNSW index for accelerated similarity search
- **Model Artifacts**: Persistent storage for cost estimation models

**Tech Stack**: PostgreSQL 15+, pgvector, File System

**Main Code Locations**:
- `backend/services/core/vectorstore.py` - Vector database operations
- `backend/services/core/embedder.py` - Document embedding
- `workspace/models/cost_estimation/` - Model artifacts

---

### 6. Security & Platform Layer (L6 - Security & Platform Layer)

**Responsibility**: Security protection, observability, operational support

**Core Components**:
- **Data Redaction**: Automatic PII identification and redaction
- **Egress Guard**: External API call monitoring and filtering
- **Observability**: Metrics, logging, tracing
- **Audit Logging**: Complete operational audit trail
- **Configuration Management**: Environment configuration, secret management
- **Release Gates**: CI/CD quality gates

**Tech Stack**: Prometheus, Grafana, ELK Stack, Vault

**Main Code Locations**:
- `backend/services/security/` - Security services
- `backend/observability/` - Observability
- `.github/workflows/` - CI/CD pipelines

---

## Core Business Flows

### 1. RAG Query Flow

```
User Query (L1)
    ↓
API Gateway Validation (L2)
    ↓
Intent Recognition (L3) → Identified as RAG query
    ↓
Prompt Selection (L3) → Select RAG prompt template
    ↓
RAG Engine (L4)
    ├─ Document Embedding
    ├─ Vector Retrieval (L5)
    ├─ Reranking
    └─ Context Building
    ↓
LLM Dispatch (L4) → Generate response
    ↓
Data Redaction (L6)
    ↓
Return Result (L1)
```

### 2. Code Analysis Flow

```
User Upload Data (L1)
    ↓
API Gateway Validation (L2)
    ↓
Intent Recognition (L3) → Identified as code analysis request
    ↓
Workflow Orchestration (L3)
    ├─ Data Preprocessing
    └─ Code Generation Plan
    ↓
Code Execution Manager (L4)
    ├─ Docker Container Start
    ├─ Code Execution
    └─ Result Collection
    ↓
Return Result (L1)
```

### 3. Cost Estimation Flow

```
User Request Estimation (L1)
    ↓
API Gateway Validation (L2)
    ↓
Cost Estimation Service (L4)
    ├─ Feature Extraction
    ├─ Model Inference (L5)
    └─ Confidence Interval Calculation
    ↓
Return Estimation Result (L1)
```

## Data Flow Diagram

```
┌─────────────┐
│  User Input │
└──────┬──────┘
       │
       ▼
┌───────────────────────────────────────┐
│  API Gateway Layer - Auth, Validate, Route │
└──────┬──────────────────────────────┘
       │
       ├─────────────────┬─────────────────┬──────────────┐
       ▼                 ▼                 ▼              ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ RAG Query   │  │ Code Analysis│  │ Cost Estimation│ │ Prompt Mgmt  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │                │
       ▼                ▼                ▼                ▼
┌──────────────────────────────────────────────────────────────┐
│  AI Runtime Layer - LLM Dispatch, Code Execution, Model Inference │
└──────┬─────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  Data Storage Layer - PostgreSQL + pgvector                 │
└──────┬─────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  Security & Platform Layer - Redaction, Audit, Monitoring     │
└──────────────────────────────────────────────────────────────┘
```

## Dependency Relationships

- L1 depends on L2 (API calls)
- L2 depends on L3 (Business logic)
- L3 depends on L4 (AI capabilities)
- L4 depends on L5 (Data access)
- All layers depend on L6 (Security/Platform services)

## Scalability Design

### Horizontal Scaling
- API Gateway Layer: Stateless, supports multi-instance load balancing
- AI Runtime Layer: Task queue + worker pool

### Vertical Scaling
- Data Storage Layer: Read-write splitting, vector index optimization
- AI Model Layer: Model serving deployment

### Plugin Architecture
- Add new LLM providers: Implement unified interface
- Add new intent types: Extend intent classifier
- Add new data sources: Implement data adapter

## Security Design

### Authentication & Authorization
- JWT token authentication
- Tenant-level data isolation
- RBAC permission control

### Data Security
- Transport encryption (TLS)
- Sensitive data redaction
- Audit log integrity

### Runtime Security
- Code sandbox isolation (Docker)
- Egress traffic control
- Resource quota limits

## Observability

### Metrics Monitoring
- API response time
- LLM call success rate
- Cost tracking
- Cache hit rate

### Log Management
- Structured logging (JSON)
- Log aggregation (ELK)
- Error tracking (Sentry)

### Distributed Tracing
- Request path tracing
- Performance bottleneck analysis
- Dependency visualization

## Interactive Architecture Diagram

View the interactive layered architecture diagram: [ARCHITECTURE_DIAGRAM.html](./ARCHITECTURE_DIAGRAM.html)