# CLAUDE.md

## gstack

Use /browse from gstack for all web browsing. Never use mcp__claude-in-chrome__* tools.
Available skills: /office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review,
/design-consultation, /review, /ship, /browse, /qa, /qa-only, /design-review,
/setup-browser-cookies, /retro, /debug, /document-release.


This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.

## Project Overview

Industry AI Flow is a **SAIT Capstone project** (Integrated AI program) — a concept prototype demonstrating how AI can empower the construction industry. **2-person team**: one with software development background, one with construction industry background. Showcase is approximately late March / early April 2026, presenting to teachers and evaluators (no real client).

**The system has three core capabilities, all of which must work flawlessly during the Capstone Showcase demo:**

### 1. RAG Knowledge QA (Primary Feature)
Users upload construction documents (PDF, images, CSV) → system vectorizes and stores in pgvector → users ask questions → system returns accurate, cited answers via hybrid retrieval (BM25 + vector + RRF + bge-reranker). Currently 28 construction documents loaded (21 processed, 7 missing).

### 2. Construction Cost Estimation (ML Prediction)
Uses a partner-provided construction cost dataset with Ridge regression to predict project cost overruns. Standard supervised learning on structured data (features: project_type, sqft, floors, location, contractor_rating, risk_score, etc.).

### 3. Dynamic Data Analysis (Code Generation + Sandbox Execution)
For user-uploaded datasets outside the pre-built cost model: extracts **metadata only** (not raw data — privacy by design) → sends metadata to cloud LLM (Gemini/Zhipu, with dual fallback) for code generation → executes generated Python in Docker/E2B sandbox → returns results + visualizations. Cloud models used because local models are too weak for reliable code generation. Docker sandbox security-hardened (TDI rounds 28-36). E2B cloud sandbox also supported (`CODE_EXECUTION_PROVIDER=e2b`). **Visualization code gen**: LLM prompt must explicitly list `CodeValidator.BLOCKED_METHOD_NAMES` (`.apply()`, `.agg()`, `.map()`, etc.) so generated code passes strict validation. E2B provider downloads generated image files from `/workspace/` after execution.

### Architecture Innovation
The AI Workflow pipeline is a core innovation with two stages: an **11-node intent classification StateGraph** (intent_workflow.py) handles user input → intent classification → multi-turn clarification → query reformulation → keyword extraction, then routes to a **10-node fixed-order execution pipeline** (graph.py): intent → safety → cost_estimation → retrieval → rerank → prompt → route → code_exec → response → groundedness. Intent recognition is especially critical for RAG routing.

### LLM Backend: Ollama (Primary) + Zhipu (Intent Classification)
**Ollama is the sole local backend for demo.** llama.cpp was evaluated early on but abandoned — Ollama is simpler to manage and its bottom layer is llama.cpp anyway. Cloud APIs (Zhipu/Gemini) are used for code generation tasks **and intent classification** (local 4B model was misclassifying intents). Demo backend: Ollama with Qwen3.5:4b (default) or Qwen3.5:9b for higher quality.

**Performance-critical settings:**
- **Thinking mode (`OLLAMA_ENABLE_THINKING`)**: Default `false`. Qwen3.5 supports a "thinking" mode that significantly increases first-token latency. Keep disabled for demo responsiveness.
- **Metal/MPS acceleration**: Ollama on macOS uses Metal GPU by default — verify with `ollama ps` (should show GPU layers). If model runs on CPU only, performance will be 3-5x slower.
- **Model size tradeoff**: 4B model (~28 TPS on M1 Max) vs 9B (~12 TPS). For live demo, 4B is recommended for faster response times.
- **llama.cpp legacy**: Removed. `llama_cpp_client.py` and all references deleted. Only `ollama` and `zhipu` backends remain.

### Non-Demo Features (Architecture Previews)
- **Multi-tenant isolation** (X-Tenant-ID): future-proofing for enterprise deployment, NOT a demo requirement
- **Prompt A/B testing**: versioned prompt management with performance scoring

### Demo Hardware & Deployment (Confirmed)
- **Mac Studio (M1 Max, 32GB RAM)** — sole demo machine
- **Public URL**: `https://iai.dissidia.me/` via Cloudflare Tunnel → `localhost:3123` (Next.js frontend)
- Stable internet at venue (cloud APIs + Cloudflare Tunnel accessible)
- Docker installed and required (`CODE_EXECUTION_PROVIDER=docker`)
- Single-operator demo (evaluators watch, don't interact directly)

### Demo-Critical Requirements
- **Source citations MUST appear on every RAG answer** — backend must always return `sources` field
- **Suggested follow-up questions MUST appear on every RAG answer** — backend must always return `suggested_questions`
- **Cost estimation needs reasonableness validation** — predicted values within dataset range
- **Cloud LLM dual fallback** — Data Analysis must work with both Gemini and Zhipu; auto-fallback if one fails
- **Intent classification uses Zhipu cloud LLM** — local 4B model had misclassification issues (e.g. RAG queries routed to code_execution); heuristic shortcut (confidence >= 0.85) skips LLM for clear-cut queries
- **Pre-warm before demo** — user will open system beforehand; first-query cold start ~49s is avoided

### Evaluation Criteria
Evaluators care about: stable demo (no crashes), clear presentation, sound architecture, logical technical decisions. **Top priority: system stability during live demo.**

### E2E Test Sync Rule
When frontend pages are modified (CSS classes, form labels, DOM structure), the E2E browser automation scripts in `scripts/testing/run_*_browser_e2e.py` **MUST be updated in the same change**. Run `run_page_result_driven_gate.py --module <module>` to validate. See `scripts/testing/` for module runners.

## Python Environment

### Python Version

**Python 3.13.x is mandatory** (`requires-python = ">=3.13,<3.14"` in `pyproject.toml`). PaddlePaddle on macOS requires the Developer Nightly Build which only supports Python 3.9-3.13. **Python 3.14+ will break PaddleOCR.**

### Virtual Environment

The project uses a **single canonical venv** at `.venv/` (standard `python -m venv`). No Conda, no pyenv, no Poetry — just `venv` + `pip`.

- **Locked dependencies**: `requirements/lock/py313-capstone.txt` — the single source of truth
- **Dependency chain**: `requirements.txt` → `requirements/base.txt` → `requirements/lock/py313-capstone.txt`
- **Makefile auto-detection**: `PYTHON_BIN` resolves `.venv/bin/python` first, then falls back to system `python3.13`

```bash
# Recommended: create the canonical .venv with locked deps
make capstone-env-setup    # Creates .venv/ with Python 3.13 + locked deps

# Or manual setup:
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements/lock/py313-capstone.txt
# PaddleOCR nightly (if OCR features needed):
python -m pip install --pre paddlepaddle -i https://www.paddlepaddle.org.cn/packages/nightly/cpu/

# Ollama setup (required for LLM features):
# Install from https://ollama.com, then:
ollama pull qwen3.5:4b        # Default demo model
ollama pull nomic-embed-text   # Embedding model (optional, system uses fastembed)
```

### Rules
- **Do NOT create additional venvs** (no `.venv_test`, `venv_capstone`, etc.). Use `.venv/` only.
- **Do NOT use Python 3.14+** — it breaks PaddleOCR.
- **Do NOT use `requirements.txt` directly for installing** — it just redirects to the lock file. Add new dependencies to `requirements/lock/py313-capstone.txt`.
- On Apple Silicon, ensure the venv uses the **arm64** Python (not Rosetta x86_64). Verify: `python -c "import platform; print(platform.machine())"` should print `arm64`.

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

# Data Analysis E2E (5 public datasets, needs Docker or E2B + cloud LLM)
python scripts/testing/run_data_analysis_dataset_e2e.py   # API-level, 11 prompts
python scripts/testing/run_data_analysis_browser_e2e.py   # Browser (agent-browser), 5 cases

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
| LLM Client | `backend/services/llm_integration/llm_client.py` | Factory: ollama / zhipu / groq |
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
| Capability Registry | `backend/services/intent_classification/capability_registry.py` | YAML-driven heuristic classification with exclusive_keywords |

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
- **LLM backend abstraction**: `LLMClientFactory.create_client(backend)` with `LLM_BACKEND` env var (`ollama|zhipu|groq`)
- **Hybrid dispatch**: `hybrid_mode` config (`local_only|hybrid_auto|cloud_only`) with confidence-based fallback (`local_confidence_threshold: 0.75`)
- **Memory guard**: `MEMORY_GUARD_LIMIT_MB` setting triggers GC or request rejection
- **Intent workflow lifecycle**: Initialized in `main.py` `lifespan()` via `initialize_intent_routes()` — required for `/api/intent/classify` endpoint to work

### Database Schema

PostgreSQL 14+ with pgvector extension. Schema managed via `backend/init_database.py` (inline SQL with `CREATE TABLE IF NOT EXISTS`):
- `document_chunks`: `embedding vector(768)` column (nomic-embed-v1.5)
- `prompts` + `prompt_versions`: Versioned prompt management with performance scoring
- `conversation_memories`: 3-layer memory storage with optional vector embedding
- `llm_usage_logs`: Cost tracking per tenant/provider/model
- Docker: `docker-compose-postgres.yml` runs `pgvector/pgvector:pg16` on port 5433

### Frontend

Next.js App Router in `frontend/`. Backend API proxy at `src/app/api/backend/[...path]/route.ts`. Run with `make frontend-dev`.

**Navigation**: Navbar uses two-tier layout — 5 primary items (Dashboard, Workflow Chat, Documents, Dynamic Analytics, Cost Estimation) + "More" dropdown (Intent Demo, System Overview). Login page is a clean form (no auto-fill, no credential hints) — use 1Password or browser auto-fill for demo credentials. Registration page removed; Register link removed from navbar.

**Dashboard** (`/simple-dashboard`): Pipeline Flow visualization — 10-node dark hero section with per-node SVG icons, sequential animation using real `node_latency_ms` data from workflow metadata. "Live Demo" button (amber accent) auto-runs on page load, sends real RAG query, replays pipeline execution. 3 status cards (Knowledge Base doc count, LLM Engine model, System Health) from real health endpoints. Recent Pipeline Executions table. `PipelineFlowViz.tsx` component + `usePipelineAnimation()` hook. When queries go through `intent_workflow` (not the 10-node pipeline), node states are inferred from metadata timestamps and agent type.

**System Overview** (`/data-dashboard`): Four-module operations center showing real-time health for Intent Classifier, RAG Knowledge Base, Cost Estimation, and Dynamic Data Analysis. Dark hero banner (same `#1a1a2e` as Pipeline Dashboard) with system-wide status dot + memory/docker/embedding info. 2x2 module card grid with SVG icons from PipelineFlowViz, color-coded left borders (blue/green/amber/purple), and health badges (Healthy/Degraded/Unavailable). Each card has a hero metric (e.g., "87% Direct Routing Rate", "21/28 Documents") + supporting metrics. Data from 5 existing endpoints: `/api/v1/health`, `/api/intent/stats/workflow`, `/api/v1/documents/statistics`, `/api/v1/feedback/statistics`, `/api/v1/cost-estimation/health`. All API client methods already exist in `dashboardApi`. DRY `ModuleCard` component shared across all 4 cards. Responsive: 2x2 grid at ≥1024px, 1-column below. Previously "Data Dashboard" with unrelated metrics — renamed in navbar to "System Overview".

**Cost Estimation page** (`/cost-estimation`): Ridge regression ML prediction with 3 collapsible field groups (Project Overview / Construction Details / Risk Assessment). String-backed inputs fix NaN-on-keystroke issue. 3 preset confidence pills (Low 80% / Medium 90% / High 95%) replace continuous slider. Model metrics badge (MAPE/R²) from `/api/v1/cost-estimation/health`. Overrun color coding (green <5%, amber 5-15%, red >15%). Batch prediction with CSV export, mutation guard (snapshot + disable during API flight). Warning banner for unknown project categories. Backend quantile resolution: selects >= requested confidence (not closest). `RequestValidationError` handler with field-level errors.

**Intent Debugger** (`/intent-demo`): Real-time 11-node intent classification pipeline visualization. Dark hero section (#1a1a2e) with `IntentFlowViz` component — 9 visible nodes (2 clarification nodes skipped on high-confidence paths) with diamond shapes for decision nodes (confidence_evaluation, clarification_step) and sequential animation using per-node timing data from `@_trace_node` decorator. `useIntentAnimation()` hook animates nodes proportionally over 4 seconds. Left panel: query input, example queries loaded from API (`/api/intent/capabilities`), classification history (last 10). Right panel: `IntentResultCard` showing intent badge, confidence bar (4-tier color), keyword highlights (`<mark>` tags), decision path badges (Heuristic/LLM), capability scores breakdown (5-bar horizontal chart with winner highlighted). Comparison mode toggle: side-by-side dual-query with independent sessions (blue=A, amber=B), pre-loaded comparison pairs. Backend: `classify_heuristic_detailed()` returns all 5 capability scores with `exclusive_keywords` penalty (score ×0.5 + conf -0.3 when query matches keywords but lacks exclusive keywords). `bypass_cache` parameter for fresh classification. API response extended with `node_trace`, `capability_scores`, `matched_keywords` fields. Shared constants in `intent-constants.ts`. All interactive elements have `data-testid` attributes. Previously "Intent Demo" with static 8-node pills — redesigned as "Intent Debugger" with animated 11-node flow in PR #11.

**Data Analysis page** (`/data-analysis`): "Include Visualization" toggle replaces old "3) Generate Visualization" button — one click runs analysis + optional visualization. 8 chart types (line, bar, scatter, histogram, box, heatmap, violin, pie). Chart Type dropdown only visible when toggle is ON. Backend `/api/v1/data/analyze` accepts `generate_visualization` and `chart_type` params. Key Metrics grid uses a whitelist (`success`, `analysis_type`, `code_gen_mode`, `execution_time`) — hidden when no fields present. Success field shows colored dot (green/red). Uploaded Path field removed from UI (backend auto-handles paths; state kept internally for API calls, pre-filled with `tips.csv`). Results use `CollapsibleCode` for Generated Code (`generated_code_preview` fallback), Analysis Output (`raw_output` fallback), and Full Response JSON. E2E selectors in `run_data_analysis_browser_e2e.py` use checkbox selector for viz toggle.

**Workflow Chat page** (`/workflow-chat`): Primary demo interaction surface — dark hero header (#1a1a2e) matching Dashboard and Intent Debugger, with API status indicator. Sidebar uses `lg:grid-cols-4` layout (3/4 chat, 1/4 sidebar). **Golden Questions** accordion in sidebar: 6 document categories (NBC 2020, Ontario Reg 213/91, Canada OHS, BC Building Code 2024, Quebec Safety Code, Canada Labour Code Part II) with 16 curated questions and 18 static follow-up chains for primary questions. Data in `frontend/src/lib/golden-questions.ts`, UI component `GoldenQuestions.tsx` with `data-testid` attributes. **CompactPipelineViz** sticky at sidebar bottom: dark vertical pipeline with sequential node animation during query, `response_node` holds active with elapsed timer until API responds, then snaps to real `completed_nodes` data. Handles `intent_workflow` metadata without `completed_nodes` via inference (same pattern as Dashboard). **Hybrid follow-up**: ref-based (`lastClickedGQRef`) Golden Question tracking — first GQ response gets static follow-ups, subsequent rounds use backend `suggested_questions`. Source citations always visible (compact single-line format, per CLAUDE.md demo requirement). Follow-up pills use blue-600 outline style. Mobile: Golden Questions collapse to toggle button, Pipeline hidden. Legacy `workflow-quick-tips.ts` removed (replaced by Golden Questions).

## Configuration

Key environment variables (in `.env`):

```bash
LLM_BACKEND=ollama                  # ollama | zhipu | groq
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
DEMO_USER_PASSWORD=<strong>         # Required — no fallback, crash if missing
AUTH_JWT_SECRET=<strong>             # Required when REQUIRE_USER_AUTH=true
REQUIRE_USER_AUTH=true              # Enforce JWT auth on all non-public endpoints
ALLOW_REGISTRATION=false            # Disable /register endpoint
```

## Tech Stack

- **LLM**: Qwen3.5:4b/9b via Ollama (Metal GPU on macOS) or Zhipu AI cloud
- **Embeddings**: nomic-embed-text-v1.5 (768-dim, local)
- **Vector DB**: PostgreSQL + pgvector (IVFFlat index)
- **Reranking**: bge-reranker-base cross-encoder
- **OCR**: PaddleOCR (requires Python 3.13.x)
- **Backend**: FastAPI + LangChain 1.0 (langgraph State Graph)
- **Frontend**: Next.js + TypeScript
- **Formatting**: black (88 chars) + isort (black profile)
- **Type checking**: mypy (strict)
