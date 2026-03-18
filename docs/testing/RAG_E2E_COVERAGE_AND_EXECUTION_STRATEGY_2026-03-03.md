# RAG E2E Coverage and Execution Strategy (Code-Aligned)

## 1. Scope

This checklist validates whether the current test design matches the real codebase behavior, not an abstract architecture.

Related artifacts:
- Question bank CSV generator:
  - `scripts/testing/generate_rag_question_bank_csv.py`
- Browser E2E runner:
  - `scripts/testing/run_rag_agent_browser_e2e.py`
- Existing randomized benchmark:
  - `scripts/testing/run_rag_random_benchmark.py`
- Existing multi-turn test plan:
  - `docs/testing/RAG_E2E_MULTITURN_AGENT_BROWSER_TEST_PLAN_2026-03-03.md`

## 2. Current Runtime Baseline

From current vector DB snapshot:
- documents: 9
- chunk rows: 3568
- embedding coverage: 100%

Model/runtime context:
- local model: `ollama qwen3.5:9b`
- deep-think mode may increase latency significantly
- `/set nothink` should be used for functional throughput runs

## 3. Coverage Matrix (Requirement -> Code Evidence -> Test Hook)

| Requirement | Code Evidence | Test Hook | Status |
|---|---|---|---|
| Retrieval flow | `backend/services/retrieval/hybrid_search.py`, `backend/services/rag_engine.py` | `run_rag_random_benchmark.py` retrieval metrics | Covered |
| Multi-turn dialogue | frontend sends fixed `session_id/thread_id` per page session in `frontend/src/app/(mvp)/workflow-chat/page.tsx` | CSV grouped by `conversation_group`, 5-turn sequences | Covered |
| Intent recognition | API response includes `intent`; frontend renders "Intent recognition" section | Browser E2E + benchmark `workflow_metrics` | Covered |
| Query rewrite | `enable_rag_query_rewrite`, `rag_query_rewrite_count` in `backend/config.py`; rewrite flow in `intent_workflow.py` | benchmark with rewrite enabled; compare rewrite-on/off runs | Covered |
| Context/session memory | `session_id/thread_id` passed to `/api/v1/workflow/query`; metadata carries session context | grouped turn runs + audit log correlation (`logs/audit.log`) | Covered |
| Frontend rendering | source cards + suggested questions in workflow-chat page component | browser E2E checks `has_source_section`, `has_suggestion_section` | Covered |
| Exception handling | workflow route returns structured error/fallback metadata in `workflow_query_routes.py`; frontend error message fallback | browser report `error` + audit `workflow.query` status | Covered |

## 4. Product-Alignment Review

### 4.1 Alignment with expected product behavior

- Supports document-grounded QA over vectorized corpus.
- Supports multi-turn follow-up behaviors and proactive suggestions.
- Validates frontend rendering and backend interaction end-to-end.
- Produces machine-readable artifacts for repeated regression runs.

### 4.2 Known practical constraints

- RAG query endpoint currently enforces English query policy for this flow.
- Full 180-turn browser runs can be resource-heavy on local model.
- Throughput/latency can vary significantly with think mode.

## 5. Execution Strategy (Serial / Parallel / Hybrid)

## 5.1 Recommended default strategy

Use **hybrid strategy**:

1. Serial preflight (mandatory):
- service health
- docs/chunks/embedding readiness
- CSV generation sanity

2. Parallel backend phase (bounded):
- run benchmark and static checks with `parallel <= 2`

3. Browser E2E phase (bounded or serial):
- default: serial by conversation group
- optional: 2 concurrent browser workers max

## 5.2 Resource control policy

- `parallel > 2` is disallowed for local workstation runs.
- If timeout/error rate spikes, automatically drop to serial mode.
- Prefer smaller smoke pass before full pass:
  - smoke: 30 questions
  - full: 180 questions

## 6. ollama qwen3.5:9b Mode Policy

### 6.1 Functional regression

- Use `/set nothink` before run.
- Goal: maximize execution speed and reduce queue time.

### 6.2 Performance benchmarking

- Run and report mode explicitly:
  - `mode=nothink`
  - `mode=think`
- Do not compare cross-mode latency without labels.

### 6.3 Quality deep-dive

- Optionally enable think mode for a small sampled subset only.
- Keep full-suite runs in nothink mode for repeatability.

## 7. Pass/Fail Gates

Recommended release gate:

1. Question bank generation succeeds (`180` rows expected for current 9-doc corpus).
2. Backend benchmark overall pass is true or exceeds threshold policy.
3. Browser E2E success rate meets threshold (default `>= 0.70`, tunable).
4. No P0 failures in audit or run summary.

## 8. Output Artifacts

- `docs/testing/rag_question_bank_180.csv`
- `logs/rag_random_benchmark_report_180.json`
- `logs/rag_agent_browser_e2e_report_180.json`
- `docs/testing/RAG_E2E_RUN_SUMMARY.md`

## 9. Next Actions

1. Add CI job for nightly smoke (`30 questions`, serial).
2. Add weekly full run (`180 questions`, bounded parallel).
3. Track rolling p50/p95 latency by model mode (`think` vs `nothink`).
