# RAG E2E Run Summary

Date (UTC): 2026-03-05
Workspace: /Users/openclaw/Documents/github.com/Industry-AI-Flow

## Scope

Full RAG E2E validation after performance optimization round:
1. Question bank generation (180 questions, 9 documents)
2. Backend retrieval/workflow benchmark (180 cases, 5-turn conversations, ~25 min total)
3. Browser E2E multi-turn validation (10-question quick test via agent-browser)

## Environment

| Component | Value |
|-----------|-------|
| Backend | FastAPI :8000, workflow runner: `intent_workflow` |
| Frontend | Next.js :3001 |
| LLM | Ollama `qwen3.5:4b` (thinking mode: off) |
| Hardware | Mac Studio M1 Max, 32GB UMA |
| Database | PostgreSQL + pgvector (9 documents, ~3565 chunks) |

## Recent Optimizations Applied

- Safety guard: lexical-only groundedness check (removed extra LLM call)
- Query cache: integrated into RAG engine (TTL 120s)
- BM25 staleness check: throttled to 30s intervals
- Ollama client: TCP connection reuse via `requests.Session`
- RAG prompt: condensed for Qwen3.5:4b
- BM25 weight: increased from 0.3 to 0.4 for small corpus
- Intent confidence: propagated to frontend via metadata

---

## Step 1: Question Bank Generation

| Metric | Value |
|--------|-------|
| Total questions | 180 |
| Documents covered | 9 |
| Questions per document | 20 (12 for BuildingSmart IFC) |
| Seed | 20260303 |
| Output | `docs/testing/rag_question_bank_180.csv` |

**Status: PASS**

---

## Step 2: Backend Retrieval/Workflow Benchmark

Data source: `logs/rag_random_benchmark_report_180.json` (180 cases, stratified by source, mixed query styles, 5 conversation turns per case).

### Retrieval Metrics

| Metric | Semantic Only | Hybrid (0.7/0.3) |
|--------|--------------|-------------------|
| Hit@8 | 77.8% | **79.4%** |
| Recall@8 | 77.8% | **79.4%** |
| MRR | 0.598 | **0.657** |
| NDCG@8 | 0.642 | **0.691** |
| Avg latency | 90ms | **80ms** |

Hybrid outperforms semantic-only across all metrics.

### Retrieval by Source (Hybrid)

| Source | Hit Rate |
|--------|----------|
| Caltrans Specs | 100% |
| GSA P100 | 95.2% |
| OSHA 1926 | 90.5% |
| UFGS Concrete | 85.7% |
| GSA Training | 71.4% |
| UFGS TOC | 71.4% |
| Caltrans Plans | 66.7% |
| GSA Core Memo | 66.7% |
| BuildingSmart IFC | 58.3% |

### Workflow Metrics

| Metric | Value | Threshold | Pass |
|--------|-------|-----------|------|
| Success rate | 89.4% | -- | -- |
| Source hit rate | 65.6% | >= 70% | FAIL |
| Non-echo rate | 98.3% | >= 80% | PASS |
| Avg keyword coverage | 55.7% | -- | -- |
| Avg reference overlap | 51.3% | -- | -- |
| Avg ROUGE-L F1 | 0.132 | -- | -- |
| Avg latency | 1,609 ms | -- | -- |
| Overall pass rate | 60.6% | -- | -- |
| Follow-up non-echo rate | 99.9% | >= 80% | PASS |
| Follow-up source hit rate | 23.9% | >= 70% | FAIL |
| Follow-up repeat rate | 0.0% | <= 45% | PASS |

### Workflow by Source (Pass Rate)

| Source | Pass Rate |
|--------|-----------|
| Caltrans Specs | 76.2% |
| GSA P100 | 76.2% |
| UFGS Concrete | 76.2% |
| Caltrans Plans | 71.4% |
| OSHA 1926 | 57.1% |
| UFGS TOC | 57.1% |
| BuildingSmart IFC | 50.0% |
| GSA Training | 47.6% |
| GSA Core Memo | 28.6% |

### Workflow by Query Style (Pass Rate)

| Style | Pass Rate |
|-------|-----------|
| noisy | 69.4% |
| telegraphic | 69.4% |
| direct | 63.9% |
| conversational | 58.3% |
| contextual | 41.7% |

### Acceptance Criteria

| Criterion | Result |
|-----------|--------|
| Hybrid hit@8 >= 0.75 | PASS |
| Hybrid MRR >= 0.55 | PASS |
| Workflow source hit >= 0.70 | **FAIL** (0.656) |
| Workflow non-echo >= 0.80 | PASS |
| Follow-up non-echo >= 0.80 | PASS |
| Follow-up source hit >= 0.70 | **FAIL** (0.239) |
| Follow-up repeat <= 0.45 | PASS |
| **Overall** | **FAIL** |

### Errors

10 requests returned HTTP 429 (rate limiting). All were `Too Many Requests` -- benchmark hit the per-tenant rate limit.

**Status: PARTIAL PASS** -- Retrieval metrics strong; workflow source attribution below threshold.

---

## Step 3: Browser E2E (Quick Test)

Data source: `logs/rag_e2e_quick_test.json` (10 questions, 2 conversation groups)

### Pass/Fail Rates

| Metric | Value |
|--------|-------|
| Total turns | 10 |
| Success turns | 3 (30%) |
| Failed turns | 7 (70%) |
| Avg elapsed per turn | 130,506 ms |
| Total elapsed | 1,329,345 ms (~22 min) |

### Failure Breakdown

| Error Type | Count | Root Cause |
|------------|-------|------------|
| `send_or_render_failed` (textarea timeout) | 5 | Frontend textarea not interactable -- blocked by loading state from previous slow query |
| `send_or_render_failed` (fill ok, render timeout) | 2 | Query sent but AI response not rendered within timeout -- backend latency exceeded browser wait |

**Status: FAIL** -- 70% failure rate driven by latency cascading into browser timeouts.

---

## Failures Grouped by Category

### P0 -- Follow-Up Source Attribution (Acceptance Blocker)

**Finding: Follow-up source hit rate is 23.9%, far below 70% threshold.**

Root causes:
1. **Multi-turn context dilution** -- Follow-up questions lack the specific keywords from the original source. The RAG engine retrieves different documents for the reformulated follow-up.
2. **No conversation-aware retrieval** -- Each turn is retrieved independently; the system doesn't carry forward which source was relevant in earlier turns.
3. **10 HTTP 429 errors** -- Rate limiting caused some follow-up turns to fail entirely, dragging down the metric.

**Recommended actions:**
1. Increase per-tenant rate limit for benchmark runs (or add benchmark API key bypass).
2. Consider injecting previous-turn source hints into follow-up retrieval queries.
3. Lower threshold to 0.50 if follow-up source tracking is out of scope for demo.

### P0 -- Workflow Source Hit Rate (Acceptance Blocker)

**Finding: First-turn source hit rate is 65.6%, just below the 70% threshold.**

Root causes:
1. **GSA Core Memo has 33.3% source hit** -- document content may not be well-chunked or embedded for the generated query styles.
2. **GSA Training at 47.6%** -- similar issue with document-query alignment.
3. **Contextual query style underperforms** (41.7% pass rate) -- these queries wrap the topic in enterprise framing that dilutes keyword signal.

**Recommended actions:**
1. Re-chunk GSA Core Memo and GSA Training with smaller chunk sizes or overlap tuning.
2. Add document-specific metadata to chunks for better source attribution.
3. For demo: use direct/telegraphic query style examples that match higher-performing patterns.

### P1 -- Frontend Rendering (Browser E2E)

**Finding: 70% browser test failure rate from latency-induced timeouts.**

Root causes:
1. Browser E2E script searches for chat container using a selector that doesn't match the new flex-based layout.
2. Textarea timeout after previous query is still loading -- no debounce or loading-state check in E2E script.

**Recommended actions:**
1. Update browser E2E selectors to match new chat layout structure.
2. Add explicit wait for loading indicator to disappear before attempting next input.
3. Use `WORKFLOW_RUNNER_MODE=fallback` to reduce latency and prevent timeout cascade.

### P2 -- Minor Issues

- 10 queries returned HTTP 429 (rate limiting) -- increase rate limit for test runs
- Some browser screenshots show `capture_layout_output: "chat_container_not_found"` even on success turns
- ROUGE-L F1 of 0.132 is low but expected -- generated answers use different phrasing than reference text

---

## Prioritized Action List

| Priority | Action | Expected Impact | Effort |
|----------|--------|-----------------|--------|
| **P0** | Set `WORKFLOW_RUNNER_MODE=fallback` for demo | Skip intent workflow, reduce latency ~50-70% | 1 env var |
| **P0** | Reduce `DEFAULT_MAX_TOKENS=1024` for demo | Faster LLM generation | 1 env var |
| **P0** | Re-chunk GSA Core Memo + GSA Training docs | Improve source hit from 33%/48% to >70% | 1-2 hours |
| **P1** | Tune intent classifier for construction queries | Reduce `unclear_intent` misclassification | 2-4 hours |
| **P1** | Update browser E2E selectors for new chat layout | Fix 70% browser test failures | 1-2 hours |
| **P1** | Enable Ollama streaming for perceived responsiveness | User sees incremental response | 2-3 hours |
| **P2** | Increase rate limit for benchmark API key | Eliminate 429 errors in testing | 1 config change |
| **P2** | Add loading-state awareness to browser E2E script | More reliable automated testing | 1-2 hours |

---

## Quick-Win Demo Configuration

For immediate demo improvement, apply these environment variables to the backend:

```bash
WORKFLOW_RUNNER_MODE=fallback
DEMO_MODE=local_safe
ENABLE_RAG_QUERY_REWRITE=false
DEFAULT_MAX_TOKENS=1024
OLLAMA_REQUEST_TIMEOUT_SECONDS=120
OLLAMA_ENABLE_THINKING=false
```

Expected effect: latency drops from median 32s to ~8-12s per query.

---

## Raw Benchmark Numbers

| Category | Metric | Value |
|----------|--------|-------|
| Dataset | Sampled cases | 180 |
| Dataset | Unique sources | 9 |
| Dataset | Candidate chunks | 3,565 |
| Dataset | Query styles | 5 (contextual, conversational, direct, noisy, telegraphic) |
| Dataset | Difficulty levels | 3 (easy: 33, medium: 137, hard: 10) |
| Retrieval (hybrid) | Hit@8 | 0.7944 |
| Retrieval (hybrid) | MRR | 0.6571 |
| Retrieval (hybrid) | NDCG@8 | 0.6906 |
| Retrieval (hybrid) | Avg latency | 80ms |
| Workflow | Success rate | 89.4% |
| Workflow | Source hit rate | 65.6% |
| Workflow | Non-echo rate | 98.3% |
| Workflow | Avg ROUGE-L F1 | 0.1324 |
| Workflow | Avg latency | 1,609ms |
| Workflow | Pass rate | 60.6% |
| Workflow | Follow-up source hit | 23.9% |
| Workflow | Follow-up non-echo | 99.9% |
| Workflow | Follow-up repeat | 0.0% |
| Benchmark | Total elapsed | ~25 min |
| Browser E2E | Success rate | 30% (3/10) |
| Browser E2E | Avg turn latency | 130s |
