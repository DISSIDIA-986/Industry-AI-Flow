# Claude Code Configuration for Industry AI Flow

SAIT Capstone project — construction-industry AI platform. Showcase: late March / early April 2026.

## Skills (Auto-Discovered)

| Skill | Path | Purpose |
|-------|------|---------|
| **TDI** | `skills/test-driven-improvement/skill.md` | Systematic quality improvement: parallel audit, failing tests, targeted fixes. 36 rounds completed. |
| **Codebase Cleanup** | `skills/codebase-cleanup/SKILL.md` | Soft-delete archiving, module boundary enforcement, demo-readiness verification. |
| **RAG E2E Multiturn** | `skills/rag-e2e-multiturn/SKILL.md` | 180-question CSV generation + browser-based workflow-chat validation + retrieval metrics. |
| **Page Result-Driven E2E** | `skills/page-result-driven-e2e/SKILL.md` | Screenshot-first browser E2E for data_dashboard, cost_estimation, rag modules. |

## Commands (Slash Commands)

| Command | Path | Purpose |
|---------|------|---------|
| `/rag-e2e` | `commands/rag-e2e.md` | Run RAG multi-turn E2E validation from vectorized docs. |
| `/page-e2e-gate` | `commands/page-e2e-gate.md` | Run page result-driven E2E gate for specific modules. |

## Project Context

- **Python 3.13.x** mandatory (PaddleOCR constraint)
- **LLM**: Qwen3.5:4b/9b via Ollama (default), llama.cpp (Metal), or cloud APIs
- **Three demo features**: RAG Knowledge QA, Cost Estimation, Dynamic Data Analysis
- **Pipelines**: 11-node intent classification StateGraph + 10-node fixed-order execution pipeline
- See root `CLAUDE.md` for full project documentation
