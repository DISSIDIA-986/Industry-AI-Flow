# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Industry AI Flow is a **SAIT Capstone project** (Integrated AI program) — a concept prototype demonstrating how AI can empower the construction industry. **2-person team**: one with software development background, one with construction industry background. Showcase is approximately late March / early April 2026, presenting to teachers and evaluators (no real client).

**The system has three core capabilities, all of which must work flawlessly during the Capstone Showcase demo:**

### 1. RAG Knowledge QA (Primary Feature)
Users upload construction documents (PDF, images, CSV) → system vectorizes and stores in pgvector → users ask questions → system returns accurate, cited answers via hybrid retrieval (BM25 + vector + RRF + bge-reranker). Currently ~12 construction documents loaded.

### 2. Construction Cost Estimation (ML Prediction)
Uses a partner-provided construction cost dataset with Ridge regression to predict project cost overruns. Standard supervised learning on structured data (features: project_type, sqft, floors, location, contractor_rating, risk_score, etc.).

### 3. Dynamic Data Analysis (Code Generation + Sandbox Execution)
For user-uploaded datasets outside the pre-built cost model: extracts **metadata only** (not raw data — privacy by design) → sends metadata to cloud LLM (Gemini/Qwen/GLM/Claude) for code generation → executes generated Python in local/Docker sandbox → returns results + visualizations. Cloud models used because local models are too weak for reliable code generation. Docker sandbox has received security hardening (TDI rounds 28-36) but **end-to-end integration testing is still limited — significant demo risk.**

### Architecture Innovation
The AI Workflow pipeline is a core innovation with two stages: an **11-node intent classification StateGraph** (intent_workflow.py) handles user input → intent classification → multi-turn clarification → query reformulation → keyword extraction, then routes to a **10-node fixed-order execution pipeline** (graph.py): intent → safety → cost_estimation → retrieval → rerank → prompt → route → code_exec → response → groundedness. Intent recognition is especially critical for RAG routing.

### Multi-Backend LLM Design
Supports Ollama (Qwen3.5:4b/9b), llama.cpp (Metal), and cloud APIs. Rationale: enterprise deployments need local models for data privacy, but current hardware is limited. Hybrid mode: simple tasks use local model, complex code generation uses cloud. Demo backend: Ollama with Qwen3.5:4b (default, ~28 TPS on M1 Max) or Qwen3.5:9b for higher quality.

### Non-Demo Features (Architecture Previews)
- **Multi-tenant isolation** (X-Tenant-ID): future-proofing for enterprise deployment, NOT a demo requirement
- **Prompt A/B testing**: versioned prompt management with performance scoring

### Demo Hardware Candidates
- Mac Studio (M1 Max, 32GB RAM)
- Windows machine (32GB RAM + RTX 5060, ~8GB VRAM)

### Evaluation Criteria
Evaluators care about: stable demo (no crashes), clear presentation, sound architecture, logical technical decisions. **Top priority: system stability during live demo.**

## Critical Environment Requirement

**Python 3.13.x is mandatory.** PaddlePaddle on macOS requires the Developer Nightly Build which only supports Python 3.9-3.13. Python 3.14+ will break PaddleOCR functionality.

```bash
# Recommended: use the locked capstone environment
make capstone-env-setup

# Or manual setup:
python3.13 -m venv venv && source venv/bin/activate
python -m pip install --pre paddlepaddle -i https://www.paddlepaddle.org.cn/packages/nightly/cpu/
export CMAKE_ARGS="-DGGML_METAL=on -DCMAKE_OSX_ARCHITECTURES=arm64"
pip install --no-cache-dir llama-cpp-python==0.2.90
pip install -r backend/requirements.txt
```

## Common Commands

```bash
# Run API server
make run                            # uvicorn with --reload on :8000

# Testing
make test                           # All tests with coverage (70% threshold)
make test-unit                      # Unit tests only
pytest tests/unit/test_cost_estimation_service.py -v  # Single test file
pytest tests/ -k "test_name" -v           # Pattern match

# Quality gates (CI)
make test-release-gate              # Full pre-release validation (11 gates)
make test-demo-smoke-gate           # CI-friendly smoke (no Postgres/Ollama needed)
make test-demo-smoke-live-gate      # Full integration smoke (needs Postgres/Ollama)

# Code quality
make format                         # black + isort
make lint                           # flake8 + mypy (strict mode)
make format-check                   # Check only, no changes

# Database
make db-setup                       # Init pgvector + migrations + seed prompts

# Frontend
make frontend-dev                   # Next.js dev server
make frontend-build                 # Production build
```

## Test Markers

```bash
pytest -m unit           # Unit tests
pytest -m integration    # Integration tests
pytest -m "not slow"     # Skip slow tests
pytest -m e2e            # End-to-end tests
pytest -m asyncio        # Async tests
```

> **Note**: Root `pytest.ini` uses `--strict-markers`. Only markers declared there (`unit`, `integration`, `e2e`, `slow`, `fast`, `asyncio`) are valid when running from the project root.

Coverage minimum: 70% (enforced via `pytest.ini --cov-fail-under=70`). Formatting: black (line-length 88, target py313). Typing: mypy strict mode.

## Architecture

### Request Flow

```
Client → FastAPI (main.py)
       → Tenant Isolation (X-Tenant-ID header)
       → Intent Classification (11-node LangChain State Graph)
           → confidence >= 0.8: route directly
           → confidence < 0.8: clarification loop
       → Agent Dispatch:
           Path A (RAG): hybrid_search → reranker → LLM generate
           Path B (Workflow): 10-node pipeline with prompt management
           Path C (Agent): unified agent with 12 tools
       → Memory Update (short-term → summary → long-term)
       → Response with source citations
```

### Key Modules

| Module | Path | Purpose |
|--------|------|---------|
| FastAPI entry | `backend/main.py` | Router mounting, global singletons with thread-safe lazy init |
| Config | `backend/config.py` | Pydantic BaseSettings, all env vars |
| RAG Engine | `backend/services/rag_engine.py` | Hybrid retrieval orchestration |
| Hybrid Search | `backend/services/retrieval/hybrid_search.py` | BM25 + vector + RRF fusion |
| Reranker | `backend/services/retrieval/reranker.py` | bge-reranker-base cross-encoder |
| Intent Workflow | `backend/services/intent_classification/intent_workflow.py` | 11-node State Graph |
| LLM Client | `backend/services/llm_integration/llm_client.py` | Factory: llama_cpp / ollama / zhipu |
| LLM Dispatch | `backend/services/llm_integration/dispatch_service.py` | Hybrid local+cloud routing |
| Memory Manager | `backend/services/memory/manager.py` | 3-layer memory orchestration |
| Prompt Manager | `backend/services/prompt_manager.py` | Versioned prompts with A/B testing |
| Routing Decision | `backend/services/routing_decision.py` | Agent type routing engine |
| Unified Agent | `backend/agents/unified_agent.py` | 12-tool agent (RAG, code exec, analysis) |
| Workflow Graph | `backend/services/workflows/graph.py` | 10-node fixed-order pipeline |
| Workflow Nodes | `backend/services/workflows/nodes/` | Individual pipeline node handlers |
| Cost Estimation | `backend/services/cost_estimation_service.py` | Ridge regression ML service |
| Code Executor | `backend/services/code_executor/` | Package: manager, docker, validator, providers |
| Data Analysis | `backend/services/data_analysis/data_analysis_agent.py` | Cloud LLM code gen + sandbox |
| Core Embedder | `backend/services/core/embedder.py` | fastembed/sentence-transformers backend |
| Safety | `backend/services/safety/groundedness_checker.py` | RAG output quality checking |
| Security | `backend/security/` | Auth, rate limiting, sanitizer, secret manager |
| Observability | `backend/observability/metrics.py` | Prometheus metrics |
| Audit Logger | `backend/services/audit_logger.py` | Tenant-aware audit logging |
| Query Cache | `backend/services/cache/query_cache.py` | Response caching |
| Language Policy | `backend/services/language_policy.py` | English-only enforcement |

### API Routes

| Effective Prefix | Router file | Mounted via |
|-----------------|------------|-------------|
| `/api/v1/workflow` | `workflow_query_routes.py` | Router-level prefix |
| `/api/v1/query` | `enhanced_query_routes.py` | `app.include_router(prefix="/api/v1")` |
| `/api/v1/cost-estimation` | `cost_estimation_routes.py` | Router-level prefix |
| `/api/v1/auth` | `auth_routes.py` | Router-level prefix |
| `/api/v1/demo` | `demo_mode_routes.py` | Router-level prefix |
| `/api/v1/feedback` | `feedback_routes.py` | `app.include_router(prefix="/api/v1")` |
| `/api/prompts` | `prompt_routes.py` | Router-level prefix (no `/v1/`) |
| `/api/v1/documents` | `document_management_routes.py` | `app.include_router(prefix="/api/v1")` |
| (no prefix) | `llm_dispatch_routes.py` | Direct mount, endpoints: `/query/dispatch` |
| (no prefix) | `llm_cost_routes.py` | Direct mount, endpoints: `/llm/usage`, `/llm/budget/` |

### Key Design Patterns

- **10-node workflow pipeline** (fixed order in `graph.py`): `intent → safety → cost_estimation → retrieval → rerank → prompt → route → code_exec → response → groundedness`
- **Thread-safe lazy singletons**: Global `rag_engine`, `unified_orchestrator`, `code_executor` initialized with `threading.Lock()` double-checked locking in `main.py`
- **Multi-tenant isolation**: `X-Tenant-ID` header → `TenantContext` → per-tenant rate limiting + audit logging
- **LLM backend abstraction**: `LLMClientFactory.create_client(backend)` with `LLM_BACKEND` env var (`llama_cpp|ollama|zhipu`)
- **Hybrid dispatch**: `hybrid_mode` config (`local_only|hybrid_auto|cloud_only`) with confidence-based fallback (`local_confidence_threshold: 0.75`)
- **Memory guard**: `MEMORY_GUARD_LIMIT_MB` setting triggers GC or request rejection

### Database Schema

PostgreSQL 14+ with pgvector extension. Schema managed via `backend/init_database.py` (inline SQL with `CREATE TABLE IF NOT EXISTS`):
- `document_chunks`: `embedding vector(768)` column (nomic-embed-v1.5)
- `prompts` + `prompt_versions`: Versioned prompt management with performance scoring
- `conversation_memories`: 3-layer memory storage with optional vector embedding
- `llm_usage_logs`: Cost tracking per tenant/provider/model
- Docker: `docker-compose-postgres.yml` runs `pgvector/pgvector:pg16` on port 5433

### Frontend

Next.js App Router in `frontend/`. Backend API proxy at `src/app/api/backend/[...path]/route.ts`. Run with `make frontend-dev`.

## Configuration

Key environment variables (in `.env`):

```bash
LLM_BACKEND=ollama                  # llama_cpp | ollama | zhipu
OLLAMA_HOST=http://localhost:11434
POSTGRES_HOST=localhost
POSTGRES_DB=ai_workflow
CHUNK_SIZE=512                      # Character-based chunking
CHUNK_OVERLAP=128
TOP_K=8                             # Retrieval count
OCR_LANG=en                         # en | ch | en+ch
REQUIRE_API_KEY=false
ENABLE_PROMETHEUS_METRICS=true
CODE_EXECUTION_PROVIDER=docker      # docker | auto | ppio
```

## Tech Stack

- **LLM**: Qwen3.5:4b/9b via Ollama or llama.cpp (Metal acceleration) or Zhipu AI cloud
- **Embeddings**: nomic-embed-text-v1.5 (768-dim, local)
- **Vector DB**: PostgreSQL + pgvector (IVFFlat index)
- **Reranking**: bge-reranker-base cross-encoder
- **OCR**: PaddleOCR (requires Python 3.13.x)
- **Backend**: FastAPI + LangChain 1.0 (langgraph State Graph)
- **Frontend**: Next.js + TypeScript
- **Formatting**: black (88 chars) + isort (black profile)
- **Type checking**: mypy (strict)
