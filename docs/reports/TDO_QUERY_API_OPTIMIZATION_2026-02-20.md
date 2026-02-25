# TDO Query API Integration Optimization Plan (2026-02-20)

## 1) P0/P1 Defect List

### P0 - Query API test is coupled to unstable external inference path
- Reproduction:
  1. Open `/api-integration-test`.
  2. Run all tests.
  3. Step `3. QueryAPItest` calls `/api/v1/query`.
- Failure evidence:
  - `logs/backend.manual.log` shows Ollama timeout and request failure:
    - `Ollama API request failed ... Read timed out. (read timeout=60)`
    - `POST /api/v1/query ... 500 Internal Server Error`
  - Frontend client timeout is `30000ms`, which is shorter than backend Ollama timeout window.
- Impact:
  - Frequent false-negative integration failures.
  - Test result depends on local model service latency/availability instead of API contract correctness.

### P1 - Document API test has false-positive behavior
- Reproduction:
  1. Run the API integration page tests.
  2. Step `4. documentAPItest` reports success even when backend documents endpoint is unavailable.
- Failure evidence:
  - `frontend/src/lib/api-client.ts` returns static values for `getDocuments()` (`[]`) without backend call.
  - `logs/frontend.manual.log` and `logs/backend.manual.log` include `/api/v1/documents 404`.
- Impact:
  - Integration page can show "pass" while real backend route is missing.

### P1 - E2E `/api/v1/query` mock response schema drift
- Reproduction:
  1. Inspect Playwright route mock for `/api/v1/query`.
  2. Compare with `queryApi.sendQuery` expected payload fields.
- Failure evidence:
  - Mock used `{id, query, response}` while client expects `{query_id, question, answer}`.
- Impact:
  - E2E can hide contract mismatch regressions.

## 2) Minimal Fixes (Implemented + Recommended)

### Implemented
- Switched API integration page test-3 from `queryApi.sendQuery` (`/api/v1/query`) to `workflowApi.sendQuery` (`/api/v1/workflow/query`) with `routeMode=local_only`.
- Updated diagnostic label to explicitly show `(/workflow/query)`.
- Aligned Playwright `/api/v1/query` mock payload with the frontend client contract.
- Changed `documentApi.getDocuments()` from static stub to real backend request (`GET /api/v1/documents`) with response-shape compatibility.
- Added backend list route aliases: `GET /api/v1/documents` and `GET /documents`.
- Added persistent backend metadata table `uploaded_documents_index`; uploads now write metadata to DB and document listing reads from DB by `tenant_id` (survives backend restart).
- Replaced document file persistence from OS temp folders with configurable durable storage root (`DOCUMENTS_STORAGE_DIR`, default `workspace/uploads/documents`).
- Added conservative cleanup policy (interval-based):
  - Mark metadata `missing` when referenced files disappear.
  - Purge stale `missing/deleted` metadata after retention window.
  - Remove orphan files under storage root after retention window.
- Added dependency preflight and skip semantics in API integration page:
  - Query test now checks `/api/v1/health` and `/api/v1/workflow/health` first.
  - Document test still handles `404` as explicit skip for older environments.
  - UI now distinguishes `pass` vs `fail` vs `skipped` and surfaces degraded dependency status.

### Recommended next
- For single-machine Capstone demos, keep storage local and durable (`DOCUMENTS_STORAGE_DIR`) and avoid temp directories.
- Split integration checks into:
  - Contract smoke (deterministic, no external LLM dependency).
  - Live dependency smoke (requires Ollama/Postgres readiness).
- Add backend dependency readiness preflight before running live query checks.
- Optional (future multi-instance): add object-storage adapter (S3/MinIO) when cross-machine consistency is required.

### Cross-team best-practice path (Architecture / Dev / Ops)
- Architecture:
  - Keep document metadata and files persistent across backend restarts.
  - Treat `/api/v1/workflow/query` as the primary integration contract path for demo/runtime checks.
- Development:
  - Keep API integration UI status tri-state (`pass` / `fail` / `skipped`) and surface degraded dependencies explicitly.
  - Keep contract tests (`frontend` integration + backend unit contracts) separate from live dependency tests.
- Operations:
  - Run `make capstone-env-check` before demo to verify Python 3.13 + locked dependencies.
  - Use `make test-demo-smoke-gate` as pre-demo health gate; use `make test-demo-smoke-live-gate` only when external dependencies are up.

## 3) Regression / Verification

### Executed in this change
```bash
./.venv_capstone/bin/python -m pytest -q \
  tests/unit/test_main_runtime_contracts.py \
  tests/unit/test_main_api_version_alias_routes.py

cd frontend
npm run test:integration -- tests/integration/api-proxy.contract.spec.ts
PW_FRONTEND_PORT=3100 npm run test:e2e -- tests/e2e/core-user-journeys.spec.ts -g "api integration page executes checks and shows pass state"
```

### Recommended full verification
```bash
# Frontend contract + integration checks
cd frontend
npm run test:integration

# Backend workflow query regression
cd ..
pytest -q tests/integration/test_workflow_cost_estimation_query_api.py
```

## 4) Test Plan (Independent)

### Coverage
- API integration page test flow: register -> login -> query -> documents.
- Workflow query path contract: `/api/v1/workflow/query`.
- Mock/contract parity for `/api/v1/query`.

### Case Set
- Success path: workflow query returns `200` and structured payload.
- Failure path: model/backend unavailable should return controlled error and visible cause.
- Contract path: frontend parser keys and mock keys remain consistent.

### Pass Criteria
- `3. QueryAPItest (/workflow/query)` becomes stable under normal local setup.
- No schema mismatch between mocks and frontend parsers.
- Integration page does not mark missing backend document route as a hidden pass.

### Evidence
- Logs:
  - `logs/backend.manual.log`
  - `logs/frontend.manual.log`
- Tests:
  - `frontend/tests/integration/api-proxy.contract.spec.ts`
  - `tests/integration/test_workflow_cost_estimation_query_api.py`
