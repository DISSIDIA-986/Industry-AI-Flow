# Test-Driven Improvement (TDI) — Industry AI Flow

Systematic quality improvement through parallel audit, failing tests, and targeted fixes — tailored for a **SAIT Capstone AI platform** for the construction industry. The primary goal of TDI is **Demo stability**: ensure all three core features work flawlessly during the Capstone Showcase (approx. late March / early April 2026).

## Project Context

Industry AI Flow is a 2-person Capstone project (Integrated AI, SAIT). Python FastAPI backend + Next.js frontend, built on LangChain 1.0 with PostgreSQL/pgvector. Demo to teachers and evaluators — system must not crash.

**Three Core Demo Features (all must work):**

| Feature | Module | What It Does | Demo Risk |
|---------|--------|-------------|-----------|
| **RAG Knowledge QA** | `SimpleRAG`, `HybridRetriever`, `Reranker` | ~12 construction docs in pgvector, hybrid retrieval (BM25 + vector + RRF), bge-reranker, cited answers | Medium — retrieval quality depends on chunk/param tuning |
| **Cost Estimation** | `CostEstimationService`, `cost_estimation_node` | Ridge regression on partner-provided construction cost dataset. Supervised learning, structured data. | Low — self-contained ML, fixed dataset |
| **Dynamic Data Analysis** | `DataAnalysisAgent`, `DockerCodeExecutor` | Upload CSV → extract metadata only (privacy) → cloud LLM generates Python code → sandbox executes | **Medium-High — Docker sandbox security-hardened (TDI rounds 28-36) but E2E integration testing limited, cloud API dependency** |

**Why cloud LLM for code generation**: Local models (Ollama/Qwen3.5:4b-9b) are too weak for reliable code generation. Cloud models (Gemini/Qwen/GLM/Claude) used for code gen; only metadata sent (not raw data) for privacy.

**Demo hardware**: Mac Studio M1 Max 32GB or Windows 32GB+RTX5060 (undecided). Resource exhaustion during demo is a real risk.

**Fixed-Order Execution Pipeline** (10-node, in `graph.py`):
```
intent_node → safety_node → cost_estimation_node → retrieval_node →
rerank_node → prompt_node → route_node → code_exec_node →
response_node → groundedness_node
```

**Intent Classification StateGraph** (11-node, in `intent_workflow.py`): Separate LangGraph state machine handling intent recognition, confidence evaluation, clarification loops (max 2 rounds), query reformulation, and keyword extraction. MAX_CLARIFICATION_ROUNDS=2 prevents infinite recursion.

**Intent Types:** `knowledge_retrieval`, `data_analysis`, `cost_estimation`, `document_processing`, `code_execution`, `unclear_intent`

**Module Dependency Graph** (critical for worktree grouping):
```
main.py → rag_engine, unified_orchestrator, code_executor (lazy singletons)
main.py → audit_logger, query_cache, language_policy, secret_manager
graph.py → all nodes/*.py (changing any node interface breaks the graph)
rag_engine.py → hybrid_search.py, reranker.py, memory/manager.py
dispatch_service.py → llm_client.py, cost_tracker.py, egress_guard.py
code_executor/ (package) — legacy code_executor.py still exists but is shadowed
unified_agent.py → 12 tools (RAG, code exec, analysis, visualization, etc.)
```

## Prerequisites

- **Python 3.13.x** (not 3.14+; PaddleOCR constraint)
- **pytest-asyncio**: `asyncio_mode = auto` is set in root `pytest.ini`, so `@pytest.mark.asyncio` is generally not needed. For compatibility, `asyncio.get_event_loop().run_until_complete()` wrappers also work.
- **pytest.ini**: enforces `--cov-fail-under=70` and `--strict-markers`; TDI changes must not drop below coverage threshold
- **Root markers**: Only `unit`, `integration`, `e2e`, `slow`, `fast`, `asyncio` are declared. Do NOT use `ocr` or `llm` markers from the root.

## Usage

```
/tdi                          # Full flow: audit + test + fix + coverage
/tdi audit                    # Audit only — output defect report
/tdi test <bug-id>            # Write reproduction test for specific bug
/tdi fix <bug-id>             # Fix specific bug and verify
/tdi coverage <module>        # Backfill tests for zero-coverage module
```

## When to Use

- **Before Capstone Showcase** — the primary use case: find and fix all P0/P1 bugs to ensure demo stability
- After expert review cycles, to catch what reviewers missed
- When confidence in hidden bug count is low
- After major refactoring (e.g. workflow pipeline changes, LLM client swap)
- After upgrading LangChain, Ollama models, or embedding models

## Demo-Focused Severity Guide

TDI severity should be calibrated to **demo impact**, not theoretical risk:

| Severity | Definition | Example |
|----------|-----------|---------|
| **P0 (Critical)** | Demo crashes or produces visibly wrong output | Docker sandbox fails, RAG returns empty, cost estimation throws exception |
| **P1 (High)** | Feature works but gives poor/incorrect results | Wrong intent routing, hallucinated answer without citations, incorrect cost prediction |
| **P2 (Medium)** | Edge cases that are unlikely during a controlled demo | Concurrent request race condition, unseen project_type in cost model |
| **P3 (Low)** | Code quality issues with no demo impact | EN: placeholders, code style, missing type hints |

**For Capstone prep**: Focus exclusively on P0 and P1. Do not spend time on P2/P3 unless all P0/P1 are resolved.

## Full Workflow (6 Steps)

### Step 0: Baseline Snapshot

Before any changes, record the current test state so regressions can be distinguished from pre-existing failures.

```bash
# Record pre-existing failures
pytest tests/unit/ -v --tb=no 2>&1 | grep FAILED > /tmp/tdi_baseline_failures.txt
pytest --collect-only tests/unit/ -q | tail -1  # Record total test count
pytest tests/unit/ --cov=backend --cov-report=term-missing -q | tail -5  # Record coverage %
```

If an existing `scripts/testing/run_rag_random_benchmark.py` script exists, also record RAG retrieval baseline:
```bash
python scripts/testing/run_rag_random_benchmark.py 2>/dev/null | tail -5 > /tmp/tdi_rag_baseline.txt
```

### Step 1: Parallel Agent Audit

Launch 4 Task agents simultaneously. Each agent receives a **discovery-oriented prompt** plus a reference to the Bug Pattern Catalog (see below) as a starting checklist. Agents should actively look for NEW patterns not in the catalog.

**Agent A — RAG Pipeline & Retrieval Quality**
```
Prompt: "Audit Industry-AI-Flow for hidden bugs in the RAG retrieval system.
Use the Bug Pattern Catalog as a starting checklist, but actively look for novel patterns.

Focus areas (backend/services/rag_engine.py, retrieval/hybrid_search.py, retrieval/reranker.py):
- Embedding dimension consistency: nomic-embed-text-v1.5 (768d) end-to-end through pgvector
- IVFFlat index parameters: verify `lists` count and that `SET ivfflat.probes` is called before
  similarity searches (default probes=1 examines only 1/lists fraction of vectors — severe recall loss)
- BM25 tokenizer language correctness: tokenizer MUST match document language (English). The project
  previously had jieba (Chinese tokenizer) on English docs — verify this regression cannot recur
- RRF fusion formula: must be weight/(k+rank) with k=60, NOT weight/rank
- Reranker: timeout/failure fallback behavior, cross-encoder input format, score distribution sanity
- Query rewriting: if enable_rag_query_rewrite is true, verify rewritten queries preserve intent
- HybridRetriever._get_adaptive_search_weights correctness
- Memory session management: unbounded interaction_history growth, stale summary detection
- Groundedness checker: verify it actually catches unsupported claims (current implementation is
  lexical overlap only — check_groundedness() ignores llm_client parameter entirely)

Report each finding as: BUG-ID | Severity | File:Line | Description | How to reproduce | Known or Novel pattern?"
```

**Agent B — Cost Estimation, Intent & LLM Dispatch**
```
Prompt: "Audit Industry-AI-Flow for hidden bugs in cost estimation, intent routing, and LLM dispatch.
Use the Bug Pattern Catalog as a starting checklist, but actively look for novel patterns.

Cost Estimation (backend/services/cost_estimation_service.py, workflows/nodes/cost_estimation_node.py):
- Ridge regression: data leakage in feature scaling (means/stds computed before or after split?)
- _build_feature_matrix one-hot encoding: unseen category handling at inference
- Feature extraction from natural language (extract_cost_features_from_query regex coverage)
- K-fold cross-validation index generation (_kfold_indices) — off-by-one, empty fold
- Training data quality: duplicates, outliers, target distribution skew
- Concurrent retrain requests on shared _service singleton
- cost_estimation_node shortcut_response flag propagation

Intent Classification (intent_classification/, workflows/nodes/intent_node.py, routing_decision.py):
- Heuristic intent keyword overlap (e.g. 'analyze cost data' → cost_estimation or data_analysis?)
- _call_classifier fallback chain correctness (inspect.signature usage)
- RoutingDecisionEngine._map_intent_to_agent completeness for all IntentType values

LLM Dispatch (backend/services/llm_integration/dispatch_service.py):
- _estimate_confidence() producing false-high scores for hallucinated/verbose content
- hybrid_auto fallback chain: local error → cloud rate-limited → cloud budget-blocked → user gets what?
- Context window overflow: TOP_K=8 docs + system prompt + history can exceed 4096 tokens
- Token counting accuracy differences across Ollama, llama.cpp, and Zhipu backends
- Streaming response handling: partial failures mid-stream

Report each finding as: BUG-ID | Severity | File:Line | Description | How to reproduce | Known or Novel pattern?"
```

**Agent C — Security, API & Multi-Tenant Isolation**
```
Prompt: "Audit Industry-AI-Flow for security vulnerabilities and API correctness.
Use the Bug Pattern Catalog as a starting checklist, but actively look for novel patterns.

FastAPI Endpoints (backend/api/*_routes.py):
- Missing authentication on sensitive endpoints (cost-estimation/train, document upload, prompt admin)
- Input validation gaps in request models
- Path traversal in _resolve_allowed_path — symlink bypass
- Error response detail leakage (str(exc) returned to clients)

Security (backend/security/, backend/middleware/):
- XSS/SQL keyword detection bypass in sanitize_text / sanitize_identifier
- Prompt injection via user queries that manipulate RAG system prompt or template variables
  (Jinja2 template syntax in user query: {{ config }}, {% include %})
- JWT auth: hardcoded fallback secrets, ephemeral secret generation
- Password storage: plaintext vs hashed
- ILIKE wildcard escaping (% and _) in search parameters

Multi-Tenant Isolation:
- Tenant ID header spoofability
- Query cache key collisions without tenant prefix
- Cost estimation model shared across tenants (single _service global)

Code Execution Sandbox (backend/services/code_executor.py, code_executor/):
- _validate_code bypass: importlib.import_module, getattr(__builtins__, '__import__'),
  exec(compile(...)), type metaclass tricks
- Docker timeout enforcement at container level
- Data file path mapping — user-supplied paths leaking to host

Report each finding as: BUG-ID | Severity | File:Line | Description | How to reproduce | Known or Novel pattern?"
```

**Agent D — Workflow Pipeline, Async State & Data Analysis**
```
Prompt: "Audit Industry-AI-Flow for workflow pipeline, async/state, and data analysis issues.
Use the Bug Pattern Catalog as a starting checklist, but actively look for novel patterns.

Workflow Pipeline (backend/services/workflows/graph.py, nodes/*):
- Error propagation: if one node sets state['error'], are downstream nodes properly skipped?
- shortcut_response flag: only safety_node and response_node run — correct?
- prompt_node skip when services.prompt_manager is None — silent behavior
- A/B allocator (ab_allocator.py): boundary condition when split=1.0 returns 'A' instead of 'B'

Data Analysis Agent (backend/services/data_analysis/data_analysis_agent.py):
- Module-level instantiation crash (DataAnalysisAgent() calls LLMClientFactory at import time)
- LLM-generated code safety beyond blacklist (_validate_code)
- _extract_dataset_info failure on malformed CSV/Excel
- Template code fallback logic — wrong column selection

Async & State Management:
- _workflow_lock (asyncio.Lock) in workflow_query_routes — potential deadlock
- _service_lock (threading.Lock) in cost_estimation_routes — mixed async/sync locking
- SimpleRAG._record_memory_interaction — race with session dict mutation (list .copy() needed)
- Session manager shared state across concurrent requests

Prompt Engineering:
- Prompt template injection via user queries passed into template variables
- A/B test allocation correctness and determinism
- Prompt hallucination risk: do RAG prompts include "say I don't know" instructions?

Report each finding as: BUG-ID | Severity | File:Line | Description | How to reproduce | Known or Novel pattern?"
```

### Step 2: Consolidate & Triage

Merge all agent reports into a single defect table:

| ID | Severity | Category | File:Line | Description | Status |
|----|----------|----------|-----------|-------------|--------|
| BUG-1 | Critical | Cost Estimation | cost_estimation_service.py:327 | ... | Novel |

**Severity guide for this project:**
- **Critical**: Wrong cost predictions affecting financial decisions, security breach allowing data exfiltration, safety-critical RAG hallucination (wrong load capacity, wrong material spec)
- **High**: Wrong intent routing, sandbox code escape, retrieval recall loss (IVFFlat probes), data corruption
- **Medium**: Edge cases, logging gaps, EN: placeholder text, UI inconsistencies
- **Low**: Code style, minor optimization opportunities

**Categorize**: RAG Retrieval Quality / RAG Infrastructure / Cost Estimation / Code Execution / Security / Intent & Routing / LLM Dispatch / Workflow Pipeline

#### Triage Gate — Choose Execution Strategy

| Condition | Strategy | Rationale |
|-----------|----------|-----------|
| **Critical+High <= 10** | **Sequential** (single branch) | Moderate overhead; fix in priority order |
| **Critical+High > 10** | **Parallel** (git worktrees) | Group by category, max 8 bugs per worktree |

> **Grouping rules**:
> - Group bugs by category. If two categories touch the same file, merge them into one group.
> - Validate grouping against the Module Dependency Graph above: bugs on the same dependency chain belong in the same group.
> - Cap each worktree at 8 bugs to stay within agent context limits. Split large categories into sub-groups.
> - Split "RAG" into "Retrieval Quality" (tokenizer, RRF, reranking) and "RAG Infrastructure" (embedding storage, index, memory) if both have bugs.

### Step 3: Phase 1 — Write Failing Tests

For each Critical/High bug, write a test that:
- Asserts the **correct** behavior (which currently fails)
- Uses `pytest.mark.xfail(reason="BUG-xxx: description")` so the test suite stays green
- Documents the bug in the test docstring
- Lives in `tests/unit/bugs/test_bug_audit_round<N>.py` (one file per TDI round)

**Test organization:**
```
tests/unit/bugs/
    __init__.py
    conftest.py                    # Shared fixtures (mock LLM, construction data, workflow states)
    test_bug_audit_round3.py       # Round 3 bugs
    ...                            # Rounds 4–19
    test_bug_audit_round20.py      # Round 20 bugs
    ...                            # Rounds 28–36 (security hardening focus)
    test_bug_audit_round36.py      # Round 36 bugs (latest)
    test_bug_code_execution.py     # Categorical: code execution bugs
    test_bug_cost_estimation.py    # Categorical: cost estimation bugs
    test_bug_intent_routing.py     # Categorical: intent routing bugs
    test_bug_rag_pipeline.py       # Categorical: RAG pipeline bugs
    test_bug_security.py           # Categorical: security bugs
    test_deep_reaudit_fixes.py     # Cross-round deep re-audit fixes
    AUDIT_LOG.md                   # Round-over-round metrics
```

**Verify**:
```bash
pytest --collect-only tests/unit/bugs/test_bug_audit_round<N>.py -q  # Collection succeeds
pytest tests/unit/bugs/test_bug_audit_round<N>.py -v                  # xfail tests show as expected failures
```

> Tests are always written on the **main working branch** before branching, so all worktrees inherit them.

### Step 4: Phase 2 — Fix Bugs

#### Path A: Sequential (<=10 bugs)

Fix each bug in priority order: Security → Cost Estimation → RAG Quality → Code Execution → Intent/Routing → Pipeline

After each fix:
1. Remove `xfail` marker from the target test
2. `pytest tests/unit/bugs/test_bug_audit_round<N>.py -v -x` → target test PASSES
3. `pytest tests/unit/ -v --tb=no 2>&1 | grep FAILED > /tmp/tdi_post_failures.txt`
4. `diff /tmp/tdi_baseline_failures.txt /tmp/tdi_post_failures.txt` → no NEW failures
5. `python3.13 -m py_compile <modified_file>` → syntax OK

#### Path B: Parallel via Worktrees (>10 bugs)

**Setup**: Create one worktree branch per category group (max 8 bugs each):

```bash
git worktree add ../tdi-fix-rag             tdi/fix-rag
git worktree add ../tdi-fix-cost-estimation tdi/fix-cost-estimation
git worktree add ../tdi-fix-security        tdi/fix-security
git worktree add ../tdi-fix-pipeline        tdi/fix-pipeline
```

**Parallel execution**: Launch one Task agent per worktree:

```
Prompt: "In worktree [path], fix the following bugs: [BUG-IDs].
For each fix:
1. Edit the source file to correct the bug
2. Remove the xfail marker from the corresponding test
3. Run: pytest tests/unit/bugs/test_bug_audit_round<N>.py -v -x → PASS
4. Run: diff <(pytest tests/unit/ -v --tb=no 2>&1 | grep FAILED) /tmp/tdi_baseline_failures.txt → no NEW failures
5. Run: python3.13 -m py_compile <modified_file> → syntax OK
Commit each fix with message: fix(tdi): BUG-<ID> <short description>"
```

**Merge back and abort criteria**:

```bash
# Merge each branch. If >2 merge conflicts occur, abandon parallel and fall back to sequential.
git merge tdi/fix-rag             --no-ff -m "fix(tdi): RAG pipeline fixes"
git merge tdi/fix-cost-estimation --no-ff -m "fix(tdi): cost estimation fixes"
git merge tdi/fix-security        --no-ff -m "fix(tdi): security fixes"
git merge tdi/fix-pipeline        --no-ff -m "fix(tdi): workflow pipeline fixes"

# Final validation
pytest tests/unit/ -v --tb=short
diff <(pytest tests/unit/ -v --tb=no 2>&1 | grep FAILED) /tmp/tdi_baseline_failures.txt

# Cleanup worktrees
git worktree remove ../tdi-fix-rag
git worktree remove ../tdi-fix-cost-estimation
git worktree remove ../tdi-fix-security
git worktree remove ../tdi-fix-pipeline
```

### Step 5: Phase 3 — Backfill Zero-Coverage

Identify critical modules with zero test coverage and write targeted tests:
- Focus on public methods that handle cost predictions, document retrieval, code execution, and routing
- Cover happy path, error path, edge cases, and async concurrency
- Use mocks to isolate from PostgreSQL/pgvector, Ollama/llama.cpp, Docker, and Redis

**Priority modules for coverage backfill:**
- `backend/services/cost_estimation_service.py` — training, inference, feature extraction
- `backend/services/rag_engine.py` — query, add_documents, feedback integration
- `backend/services/retrieval/hybrid_search.py` — BM25+vector fusion, weight adaptation
- `backend/services/llm_integration/dispatch_service.py` — confidence estimation, fallback chain, context overflow
- `backend/services/data_analysis/data_analysis_agent.py` — analyze_query, code generation, template fallbacks
- `backend/services/code_executor/docker_executor.py` — execute_code, workspace management, validation
- `backend/services/workflows/nodes/` — each node's skip/execute/error behavior
- `backend/services/routing_decision.py` — make_routing_decision, agent mapping, fallback logic
- `backend/api/workflow_query_routes.py` — workflow_query end-to-end response contracts

**Test file naming**: `tests/unit/test_<module_name>.py`

### Step 6: Test Graduation & Audit Log

After a TDI round stabilizes (zero new regressions across subsequent commits):

1. **Graduate passing bug tests** from `tests/unit/bugs/test_bug_audit_round<N>.py` into the canonical `tests/unit/test_<module>.py` files
2. **Delete the round file** once all tests have been graduated
3. **Move shared fixtures** from `tests/unit/bugs/conftest.py` to `tests/unit/conftest.py` if reused by graduated tests
4. **Update the audit log** in `tests/unit/bugs/AUDIT_LOG.md`:

```markdown
| Round | Date | Bugs Found | Critical | High | Fixed | Graduated | New Patterns |
|-------|------|-----------|----------|------|-------|-----------|-------------|
| 5     | 2026-02-25 | 70  | 8        | 18   | 14    | pending   | 3           |
| ...   | ...        | ... | ...      | ...  | ...   | ...       | ...         |
| 14    | 2026-02-26 | ... | ...      | ...  | ...   | ...       | ...         |
| 15-19 | 2026-02-26 | ... | ...      | ...  | 67+   | ...       | ...         |
| 28-36 | 2026-02-28 | ... | ...      | ...  | ...   | ...       | security hardening |
```
> See `tests/unit/bugs/AUDIT_LOG.md` for the complete history across rounds 3–14.

This enables convergence tracking — if each round finds fewer bugs, the system is approaching acceptable quality. Stop running TDI rounds when Critical+High < 3 for two consecutive rounds.

## Bug Pattern Catalog

Patterns discovered across TDI rounds. **Status**: Confirmed = found and fixed in a real round. Theoretical = plausible but not yet encountered.

### RAG Retrieval Quality

| Pattern | Example | Status |
|---------|---------|--------|
| RRF formula error | `weight/rank` instead of `weight/(k+rank)` with k=60 | **Confirmed (Round 5)** |
| BM25 tokenizer language mismatch | jieba (Chinese) tokenizer on English construction docs → zero BM25 recall | **Confirmed (pre-TDI)** |
| IVFFlat probes not set | Default `probes=1` with `lists=10` examines only 10% of vectors → severe recall loss | **Confirmed (Round 10, 13)** — reappeared in LongTermMemoryStore |
| Embedding dimension mismatch | nomic-embed-text-v1.5 (768d) vs pgvector column configured for different dim | Theoretical |
| Reranker timeout fallback | bge-reranker service timeout → empty results vs unreranked fallback behavior undefined | Theoretical |
| Standard number partial match | Query "CSA A23.1" fails to match chunk containing "CSA A23.1-14" | Theoretical |
| Unit system mismatch | Query "3000 psi concrete" misses "20 MPa concrete" documents | Theoretical |
| Construction abbreviation miss | BM25 query "rebar spacing" misses "reinforcing steel bar" documents | Theoretical |

### Cost Estimation & Intent

| Pattern | Example | Status |
|---------|---------|--------|
| Unseen category fallback | `project_type="data_center"` not in training set → all-zero one-hot, silent bad prediction | Theoretical |
| Feature extraction miss | User says "5000 square feet" but regex only matches "sqft" → missing feature, median imputed | Theoretical |
| Intent keyword overlap | "analyze construction costs" triggers both `cost_estimation` and `data_analysis` | **Confirmed (Round 5)** |
| Data leakage in scaling | Feature means/stds computed on full dataset before k-fold split | Theoretical |
| Cost estimation keyword gap | "how much" and "price" not recognized as cost estimation intent | **Confirmed (Round 5)** |

### Security & Sandbox

| Pattern | Example | Status |
|---------|---------|--------|
| _validate_code bypass via importlib | `importlib.import_module('os').system(...)` | **Confirmed (Round 5)** |
| _validate_code bypass via getattr | `getattr(__builtins__, '__import__')('subprocess')` | **Confirmed (Round 5)** |
| XSS pattern detection gap | Event handler attributes `onload=...` and `javascript:` URIs not detected | **Confirmed (Round 5)** |
| SQL tautology detection gap | `' OR '1'='1` and comment-obfuscated UNION SELECT not detected | **Confirmed (Round 5)** |
| ILIKE wildcard injection | `%` and `_` not escaped in LIKE/ILIKE search parameters | **Confirmed (Round 5)** |
| Path traversal via symlink | `_resolve_allowed_path` doesn't resolve symlinks before `_is_subpath` check | Theoretical |
| Tenant cache collision | Cache key is `md5(query)` without tenant prefix | Theoretical |
| JWT hardcoded fallback secret | `"industry-ai-flow-dev-secret"` used when env var missing | **Confirmed (Round 5)** |
| Plaintext password storage | Auth routes stored/compared passwords as plaintext | **Confirmed (Round 5)** |
| Error detail leakage | `detail=str(exc)` returns internal exception messages to clients | **Confirmed (Round 5, 14)** — also via non-HTTPException paths |
| String obfuscation via codecs | `codecs.decode('bfrff','rot13')` reconstructs blocked names without triggering patterns | **Confirmed (Round 14)** |
| chr() dynamic name construction | `chr(95)+chr(95)+'import'+chr(95)+chr(95)` builds dunder names character-by-character | **Confirmed (Round 14)** |
| Container indirection bypass | `[exec][0](...)` and `{"e": exec}["e"](...)` bypass AST-based call validators | **Confirmed (Round 11)** |
| Dunder attribute chain escape | `object.__getattribute__` + `chr()` construction bypasses regex and AST detection | **Confirmed (Round 13)** |
| Missing security response headers | No CORS, X-Content-Type-Options, X-Frame-Options, CSP headers in middleware | **Confirmed (Round 14)** |
| Admin endpoints without role check | LLM config, model switch, document restore lack admin/role authorization | **Confirmed (Round 14)** |

### Workflow Pipeline & Async

| Pattern | Example | Status |
|---------|---------|--------|
| Error response not set | Pipeline sets `state["error"]` but no `state["response"]` → null response to user | **Confirmed (Round 5)** |
| Module-level instantiation crash | `DataAnalysisAgent()` calls `LLMClientFactory.create_client()` at import time | **Confirmed (Round 5)** |
| Memory session thread safety | `list(session.interaction_history)` not copied before background thread | **Confirmed (Round 5)** |
| Mixed async/sync lock | `threading.Lock` inside async handler blocks event loop | Theoretical |
| Pipeline ordering semantics | Groundedness node positioned before response_node scores 0.0 — must run after | **Confirmed (Round 13)** |
| Snapshot mutation isolation | Summary updates written to deep-copy snapshot silently lost | **Confirmed (Round 13)** |
| Async/sync detection double-exec | Eagerly calling method then checking if awaitable causes sync methods to run twice | **Confirmed (Round 14)** |
| Agent-type misrouting | cost_estimation routed to GENERAL_AGENT which dispatches to RAG | **Confirmed (Round 14)** |
| Pipeline shortcut bypass | `shortcut_response=True` but non-essential nodes still execute | Theoretical |
| A/B allocator boundary | `split=1.0` returns bucket "A" instead of "B" | Theoretical |
| Intent clarification infinite loop | LLM empty response + unclear_intent fallback → endless clarification | **Confirmed (P0, pre-round 37)** — fixed via MAX_CLARIFICATION_ROUNDS=2 |
| Heuristic confidence too low | Single keyword match → 0.1 confidence → unnecessary clarification loop | **Confirmed (pre-round 37)** — fixed by dividing by 30.0 instead of 100 |

### LLM Dispatch & Confidence

| Pattern | Example | Status |
|---------|---------|--------|
| False-high confidence | `_estimate_confidence()` scores verbose hallucinated output at 0.95 | Theoretical |
| Context window overflow | TOP_K=8 docs + system prompt + history > 4096 tokens → truncated input | Theoretical |
| Groundedness checker lexical-only | `check_groundedness()` uses bag-of-words overlap, ignores `llm_client` param; "50 kN" and "500 kN" score identically | Theoretical |
| Prompt template lacks guardrails | RAG prompt missing "say I don't know" instruction → unchecked hallucination | Theoretical |
| EN placeholder contamination | `"EN:EN"`, `"LLMEN"` strings across templates, fallback answers, keyword matching, clarification generators | **Confirmed (pre-TDI, Round 12, 14)** — systemic across 4+ modules |
| Zero-score RRF pollution | Including zero-score BM25 results in RRF fusion gives irrelevant docs non-zero scores from arbitrary rank | **Confirmed (Round 14)** |

## Known Import Hazards

Modules that crash on import without proper mocking. Use these workarounds in tests.

### Module-level side effects
| Module | Crash Cause | Workaround |
|--------|-------------|-----------|
| `data_analysis_agent.py` | Previously crashed at import; now uses lazy init in `__init__()` — **FIXED** | Safe to import, but LLMClientFactory call in `__init__` still requires mocking for unit tests |
| `rag_engine.py` | Triggers database connection setup | `monkeypatch` settings or mock `backend.config.settings` before import |
| `code_executor.py` (legacy) | Initializes Docker client | Use `importlib.util.spec_from_file_location` (see below) |

### Package shadowing
`backend/services/code_executor.py` (legacy file) is shadowed by `backend/services/code_executor/` (package). Standard `import` resolves to the package.

To load the legacy file for testing:
```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "code_executor_legacy",
    "backend/services/code_executor.py",
)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
except Exception:
    pytest.skip("Legacy code_executor.py could not be loaded")
```

### Source code inspection pattern
When import is impossible, read and analyze source code as text:
```python
import ast
source = open("backend/services/some_module.py").read()
tree = ast.parse(source)
# Analyze AST for patterns (e.g., verify blacklist contents)
```

## Test Writing Guidelines

1. **Environment isolation**: Tests inherit `REQUIRE_API_KEY=false` from `tests/conftest.py`. Use `monkeypatch.setenv()` for `OLLAMA_MODEL`, `POSTGRES_HOST`, `COST_ESTIMATION_MODEL_PATH`, etc.

2. **Mock external services**: Mock Ollama/llama.cpp responses, pgvector queries, Docker daemon, and Redis via `unittest.mock.patch` or `pytest-mock`. **Never** make real LLM calls or start Docker containers in unit tests. Three tiers:
   - **Tier 1 (Unit)**: Mock with fixed strings. Tests code paths, error handling, parsing.
   - **Tier 2 (Integration)**: Use recorded LLM responses (golden snapshots). Tests prompt-response compatibility.
   - **Tier 3 (Evaluation)**: Real LLM calls against a golden QA set. Mark with `@pytest.mark.llm` and `@pytest.mark.slow`.

3. **Use existing fixtures**: Leverage `mock_llm_response`, `sample_document`, `sample_query` from `tests/conftest.py`.

4. **Construction domain test data**: Use realistic construction features in fixtures: `project_type="residential_single_family"`, `location="Toronto"`, `sqft=2500`, `estimated_cost_cad=450000`, etc. For RAG tests, include construction standard references: `"CSA A23.1-14"`, `"NBC 2020 Part 4"`.

5. **Async test support**: Root `pytest.ini` sets `asyncio_mode = auto`, so async test functions are auto-detected. Both approaches work:
   ```python
   # Approach 1: Direct async (preferred, auto-detected)
   async def test_async_node(self):
       result = await some_async_function(args)
       assert result == expected

   # Approach 2: Sync wrapper (fallback)
   def test_async_node_sync(self):
       import asyncio
       result = asyncio.get_event_loop().run_until_complete(
           some_async_function(args)
       )
       assert result == expected
   ```

6. **Module import safety**: See "Known Import Hazards" above. Always check if a module has import-time side effects before writing `from backend.services.X import Y`.

7. **Fixture reuse**: Put common test data (sample embeddings, construction project features, mock workflow state dicts) in `tests/unit/bugs/conftest.py`.

8. **Assertion clarity**: Always include a business-context message, e.g. `assert prediction["predicted_cost_overrun_pct"] >= 0, "Cost overrun cannot be negative — would indicate model error"`.

9. **Marker usage**: Tag bug tests with `pytest.mark.xfail(reason="BUG-xxx")` until fixed. Use `@pytest.mark.unit` (always), `@pytest.mark.integration` and `@pytest.mark.slow` where appropriate.

10. **WorkflowState fixtures**: Create minimal `WorkflowState` dicts for testing individual nodes in isolation — see `backend/services/workflows/state.py` for the TypedDict shape.

11. **Baseline-aware regression checking**: Always diff test results against `/tmp/tdi_baseline_failures.txt` to distinguish pre-existing failures from new regressions.

## Verification Commands

```bash
# Step 0: Baseline snapshot (run BEFORE any changes)
pytest tests/unit/ -v --tb=no 2>&1 | grep FAILED > /tmp/tdi_baseline_failures.txt
pytest --collect-only tests/unit/ -q | tail -1

# Step 3: Test collection (must not crash)
pytest --collect-only tests/unit/bugs/test_bug_audit_round<N>.py -q

# Step 3: Bug reproduction (xfail expected)
pytest tests/unit/bugs/ -v --tb=long

# Step 4: After fixes (expect PASS)
pytest tests/unit/bugs/ -v -x

# Step 4: Regression check (diff against baseline)
diff <(pytest tests/unit/ -v --tb=no 2>&1 | grep FAILED | sort) <(sort /tmp/tdi_baseline_failures.txt)

# Step 5: Coverage backfill
pytest tests/unit/ --cov=backend --cov-fail-under=70 -q

# Full validation (using Makefile)
make test-unit

# Quick smoke test (CI-friendly, no Postgres/Ollama needed)
make test-demo-smoke-gate

# RAG quality check (if retrieval bugs were fixed)
python scripts/testing/run_rag_random_benchmark.py 2>/dev/null
```
