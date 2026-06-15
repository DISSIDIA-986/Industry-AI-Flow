# Industry AI Flow

**Construction-industry AI platform** built on LangChain 1.0 — combining retrieval-augmented document Q&A, ML-based cost estimation, and sandboxed data analysis behind a single intent-routed workflow.

> 🇨🇳 中文版文档： **[README.zh.md](README.zh.md)**

SAIT Integrated-AI capstone project. The platform turns scattered construction codes, standards, and project data into single-query answers with source citations.

---

## What it does

Three capabilities, one workflow:

1. **RAG knowledge Q&A** — Upload construction documents (PDF, images, CSV); the system vectorizes them into pgvector and answers questions with cited sources via hybrid retrieval (BM25 + vector + RRF fusion + bge-reranker). Loaded corpus: 16 Canadian and US construction codes and standards (NBC 2020, OSHA, BC/Quebec/Ontario codes, etc.).
2. **Cost estimation** — A CatBoost + Ridge dual model predicts cost overrun % and actual cost, with SHAP per-prediction explainability, what-if scenario analysis, and similar-project lookup over a 10,000-project dataset.
3. **Dynamic data analysis** — For user datasets outside the cost model, the system extracts metadata only (privacy by design), asks a cloud LLM to generate Python, and runs it in a hardened Docker/E2B sandbox, returning results and charts.

## Architecture

![Industry AI Flow architecture](docs/ARCHITECTURE_DIAGRAM.drawio.png)

Six-layer design: **UI → API Gateway → Business Services → AI Runtime → Data Stores → Security & Infrastructure**.

The core innovation is a two-stage AI pipeline:

- An **11-node intent-classification state graph** (LangGraph) handles input → classification → multi-turn clarification → query reformulation, routing each query to the right agent with a confidence score. Below the confidence threshold it asks for clarification instead of guessing.
- A **10-node fixed-order execution pipeline**: `intent → safety → cost_estimation → retrieval → rerank → prompt → route → code_exec → response → groundedness`, each node under an individual timeout SLA.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design, [`docs/architecture/SYSTEM_ARCHITECTURE_DETAILED.md`](docs/architecture/SYSTEM_ARCHITECTURE_DETAILED.md) for the layered/container view, and [`docs/architecture/FRONTEND_ARCHITECTURE.md`](docs/architecture/FRONTEND_ARCHITECTURE.md) for the frontend.

## Tech stack

| Layer | Choice |
|-------|--------|
| LLM (local) | Qwen3.5 4b/9b via Ollama (Metal GPU on macOS) |
| LLM (cloud) | Zhipu / Groq — code generation + intent classification, dual fallback |
| Embeddings | nomic-embed-text-v1.5 (768-dim, fastembed) |
| Vector DB | PostgreSQL 14+ with pgvector (IVFFlat index) |
| Retrieval | Hybrid BM25 + vector + RRF, bge-reranker-base cross-encoder |
| Cost ML | CatBoost 1.2 (overrun) + Ridge (cost) + SHAP TreeExplainer |
| OCR | PaddleOCR (requires Python 3.13.x) |
| Backend | FastAPI + LangChain 1.0 (LangGraph state graph) |
| Frontend | Next.js (App Router) + TypeScript + Tailwind |
| Code sandbox | Docker / E2B |

## Quickstart

Requires **Python 3.13.x** (locked: PaddleOCR breaks on 3.14+), PostgreSQL 14+ with pgvector, and [Ollama](https://ollama.com).

```bash
git clone https://github.com/DISSIDIA-986/Industry-AI-Flow.git
cd Industry-AI-Flow

# 1. Environment (creates .venv/ + installs locked deps)
make capstone-env-setup

# 2. Local LLM
ollama pull qwen3.5:4b

# 3. Database (pgvector + migrations + seed)
make db-setup

# 4. Run
make run             # FastAPI on :8000
make frontend-dev    # Next.js on :3123 (separate terminal)
```

Verify the environment with `make capstone-env-check`, or run the offline smoke gate with `make test-demo-smoke-gate`.

## Security & multi-tenancy

Enterprise-grade controls, configured via `.env` (see [`docs/developer/setup-guide.md`](docs/developer/setup-guide.md)):

- **Auth** — Optional API-key gate (`REQUIRE_API_KEY`) and JWT bearer auth with roles/permissions (`REQUIRE_USER_AUTH`).
- **Secrets** — Fernet-encrypted or PBKDF2-hashed API keys via `tools/secure_config.py`.
- **Tenant isolation** — `X-Tenant-ID` header drives per-tenant rate limiting, budget policy, and audit logging.
- **Input safety** — Automatic XSS/SQL keyword detection, upload size/extension limits, filename sanitization.
- **Cost governance** — Per-tenant LLM usage logging and budget thresholds (`/api/v1/llm/usage`, `/api/v1/llm/budget`).
- **Privacy egress guard** — Redaction + egress-policy check before any cloud call, recorded in the audit log.
- **Observability** — Prometheus `/metrics`, structured JSON logs, slow-query tracking, memory guard.

## Project status

Active capstone project. Most original documentation was written in Chinese for the SAIT audience; this English documentation set is the primary reference.

## License

MIT
