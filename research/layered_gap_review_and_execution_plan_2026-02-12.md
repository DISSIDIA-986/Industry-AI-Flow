# Industry AI Flow Layered Gap Review & Execution Plan (2026-02-12)

## 1. Scope and Method

This review inspects the current repository across six layers:
1. UI layer
2. API gateway layer
3. Business service layer
4. AI engine layer
5. Data storage layer
6. Security and technical infrastructure layer

Evidence sources include:
- `frontend/src/app/(mvp)/*`
- `frontend/src/lib/api-client.ts`
- `backend/main.py`, `backend/api/*`
- `backend/services/workflows/*`, `backend/services/intent_classification/*`
- `backend/services/core/vectorstore.py`, `backend/init_database.py`, `backend/services/llm_integration/cost_tracker.py`, `backend/services/memory/store.py`
- `.github/workflows/kpi-gate.yml`, `Makefile`, `requirements/*`
- Current tests under `tests/unit` and `tests/integration`

---

## 2. Layer-by-Layer Findings

## 2.1 UI Layer

Implemented:
- Next.js MVP floors and navigation are in place (`overview`, `workflow-chat`, `cost-estimation`, `documents`, `data-analysis`, `prompt-admin`, `llm-cost-policy`).
- Backend proxy exists at `frontend/src/app/api/backend/[...path]/route.ts`.

Gaps:
- P1: Core pages are operator-style JSON panels; limited demo-grade visual feedback for artifacts (charts/doc outputs) and limited empty/error guidance.

## 2.2 API Gateway Layer

Implemented:
- Unified frontend proxy and backend API routes exist.
- Workflow API (`/api/v1/workflow/query`) and cost-estimation APIs are available.

Gaps:
- P1: Mixed route styles (`/api/v1/*` and unversioned root paths) increase contract drift risk.
- P1: Legacy intent route module exists but is not part of current mounted path, creating discoverability/maintenance confusion.

## 2.3 Business Service Layer

Implemented:
- Workflow orchestrator and node pipeline are present.
- Cost-estimation node and service are integrated.

Gaps:
- P0: Natural-language cost intent detection is still fragile for common phrasing; fallback path may miss cost route and degrade demo outcome.

## 2.4 AI Engine Layer

Implemented:
- RAG + workflow + dispatch + cost-estimation model training/inference are available.
- Demo mode and routing policy are implemented.

Gaps:
- P0: Fallback workflow path does not consistently use a robust intent classifier, so key capstone query forms can route incorrectly.

## 2.5 Data Storage Layer

Implemented:
- PostgreSQL schema bootstrap and prompt/cost/budget tables exist.
- Async pool path exists for prompt/workflow components.

Gaps:
- P0: Runtime modules still hard-import `psycopg2` while lock baseline is `psycopg` v3 (`requirements/lock/py313-capstone.txt`), creating environment break risk.

## 2.6 Security & Technical Infrastructure Layer

Implemented:
- API key, tenant context, rate limiting, redaction/egress guard, memory guard, metrics/audit plumbing are present.

Gaps:
- P0: CI release gate currently installs only `pytest` + `pydantic-settings`; this is insufficient for the selected gate tests and can produce false gate failures.

---

## 3. TeamAgents Consolidated Review

### Senior AI Expert
- Prioritize deterministic intent-to-model routing for cost estimation.
- Avoid relying on weak lexical triggers for demo-critical user prompts.

### Senior LLM Expert
- Keep cost estimation on dedicated structured model path.
- Ensure intent classifier path handles "estimate cost" variants in EN/ZH and fallback mode.

### Senior Architect
- Remove hidden runtime fragility caused by DB driver mismatch.
- Keep fallback path functional under constrained environments.

### Senior QA Engineer
- Add API-level regression tests for natural-language cost routing.
- Ensure release gate installs all dependencies required by gate-selected tests.

Consensus:
- Execute P0 items first: intent routing robustness, DB driver compatibility, and CI gate dependency completeness.
- Then execute P1 improvements for API contract clarity and UI demo polish.

---

## 4. Priority Backlog

## P0
1. Strengthen workflow intent classification path for natural-language cost queries.
2. Ensure fallback workflow runner uses an actual classifier (not only weak heuristics).
3. Add DB driver compatibility layer for `psycopg`/`psycopg2` to avoid startup/runtime break.
4. Fix release-gate dependency bootstrap in CI.

## P1
1. Improve API path consistency and reduce legacy route ambiguity.
2. Improve UI artifact rendering and guided error/empty states for demo flow.

---

## 5. Phased Execution Plan

## Phase 1 (P0-A): Intent Routing Hardening
- Update workflow intent node to support `classify_intent()`-style classifiers and broaden heuristic coverage.
- Inject a lightweight classifier into fallback runner.
- Add/extend tests for “natural language cost” queries (including phrasing like "estimate cost risk").

Acceptance criteria:
- Workflow query with common EN/ZH cost phrasing yields `intent=cost_estimation` and reaches cost-estimation node.

## Phase 2 (P0-B): DB Driver Compatibility
- Introduce shared DB driver compatibility helpers.
- Migrate core runtime modules (`init_database`, `vectorstore`, `memory/store`, `cost_tracker`) to compatibility helpers.

Acceptance criteria:
- Runtime modules import and execute with either `psycopg` v3 or `psycopg2` available.

## Phase 3 (P0-C): Release Gate Reliability
- Add dedicated release-gate dependency manifest.
- Update CI workflow to install the manifest before running `make test-release-gate`.

Acceptance criteria:
- CI gate environment has all required Python deps for selected gate tests.

## Phase 4 (P1): UX/API Consistency Follow-up
- Keep as next iteration after P0 completion.

---

## 6. Validation Plan

1. Run targeted unit/integration tests for intent + workflow + cost-estimation APIs.
2. Run release gate subset or full gate depending on environment resources.
3. Perform plan-to-implementation checklist verification:
- P0-A done
- P0-B done
- P0-C done
- Any deferred P1 explicitly listed

---

## 7. Execution Status (This Iteration)

Completed:
- P0-A Intent routing hardening:
  - Updated `backend/services/workflows/nodes/intent_node.py` to support `classify_intent` and broader cost-query phrasing.
  - Updated `backend/api/workflow_query_routes.py` fallback runner to inject `SimpleIntentClassifier`.
  - Added tests:
    - `tests/unit/test_workflow_intent_node.py`
    - Extended `tests/integration/test_workflow_cost_estimation_query_api.py` with NL phrase regression.
  - Added new test to gate list in `Makefile` (`test-cost-estimation-gate`).

Completed:
- P0-B DB driver compatibility:
  - Added `backend/services/database/driver_compat.py`.
  - Migrated runtime modules:
    - `backend/init_database.py`
    - `backend/services/core/vectorstore.py`
    - `backend/services/memory/store.py`
    - `backend/services/llm_integration/cost_tracker.py`

Completed:
- P0-C Release gate dependency bootstrap:
  - Added `requirements/release-gate.txt`.
  - Updated `.github/workflows/kpi-gate.yml` to install gate requirements from this file.

Deferred to next iteration (P1):
- UI artifact rendering/polish and deeper API route normalization.

Completed (Phase 4 partial, P1):
- API consistency:
  - Added `/api/v1/*` aliases for core legacy root endpoints in `backend/main.py` while preserving backward compatibility.
  - Updated frontend API client to consume versioned paths for platform health, uploads, analysis, and visualization.
  - Added regression test `tests/unit/test_main_api_version_alias_routes.py` and wired it into `test-demo-mode-gate`.
- UI readability:
  - Improved MVP `data-analysis` and `documents` pages with summary cards and artifact/log previews.

---

## 8. Audit Remediation (Round 2)

Completed:
- Dependency baseline unification (P0):
  - Updated `requirements/base.txt` to use `requirements/lock/py313-capstone.txt` as canonical runtime source.
  - Updated `backend/requirements.txt` as a compatibility shim to root base requirements.
  - Updated `Makefile` install targets (`install`, `dev-setup`, `install-dev`) to install from root layered requirements instead of stale backend-only spec.
- DB compatibility extension coverage (P1):
  - Updated `backend/init_comprehensive_database.py` to remove direct `psycopg2` hard dependency and use `backend/services/database/driver_compat.py`.
- Intent boundary hardening (P1):
  - Tightened `backend/services/workflows/nodes/intent_node.py` Chinese cost heuristics to reduce generic "成本/预算" false positives while preserving reverse-order phrasing support.
  - Added regression tests in `tests/unit/test_workflow_intent_node.py` for:
    - Chinese reverse-order positive case
    - non-estimation cost-governance negative case

Validation evidence:
- `make test-cost-estimation-gate` passed.
- `make test-release-gate` passed.
