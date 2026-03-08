# Test-Driven Optimization Plan (2026-02-20)

## 1. Goal
Establish a repeatable, evidence-based testing baseline for Industry AI Flow, then use test evidence to identify P0/P1 defects and drive minimal-change quality improvements.

## 2. Scope
- RAG critical chain: ingest -> chunk -> embedding -> PGVector write/read -> retrieval (semantic/keyword/hybrid) -> workflow response -> citation check.
- Cost estimation/ML chain: dataset load -> train -> predict -> batch predict -> workflow shortcut path.
- Dynamic code generation/execution chain: metadata/request -> code execution manager -> sandbox execution -> error/safety path.
- Frontend-backend connectivity: Next.js page action -> API/proxy -> backend workflow -> UI rendering.

## 3. Repeatable Baseline Commands
Use Python from `.venv_capstone/bin/python`.

### 3.1 Cost Estimation / ML
- `python -m pytest -q tests/integration/test_cost_estimation_api.py`
- `python -m pytest -q tests/integration/test_workflow_cost_estimation_query_api.py`

### 3.2 Workflow Core / Code Execution
- `python -m pytest -q tests/unit/test_workflow_orchestrator_pipeline.py`
- `python -m pytest -q tests/integration/test_data_analysis_runtime_gate.py`
- `python -m pytest -q tests/integration/test_executor_provider_fallback.py`

### 3.3 Workflow API Contract
- `python -m pytest -q tests/unit/test_workflow_query_routes.py`

### 3.4 RAG End-to-End Validation
- `python scripts/testing/run_construction_rag_e2e_validation.py`

### 3.5 Frontend E2E Connectivity
From `frontend/`:
- `npm run test:e2e -- tests/e2e/core-user-journeys.spec.ts -g "workflow chat sends message and renders AI response"`

## 4. Pass Criteria
- P0: zero known exploitable safety bypasses on critical path.
- P1: no client crash on normal API payload variants; no major retrieval mode collapse hidden as success.
- RAG storage validation must pass (`pgvector=true`, expected docs present, chunk count > 0).
- Workflow query must return traceable metadata and non-empty response.
- Dynamic execution runtime gate must verify real execution success.
- E2E page must complete send->response rendering without runtime exception.

## 5. Evidence Requirements
For each run keep:
- command line and timestamp,
- pass/fail summary,
- failing assertion/stack trace,
- key I/O snippets (request payload / response fields / citation snippets),
- generated report files.

Required artifact paths for this run:
- `logs/test-driven-optimization/2026-02-20/*.log`
- `logs/construction_rag_e2e_validation_report.json`

## 6. High-Value Targeted Test Set (Regression)
- Safety rule case/normalization regression:
  - Ensure `subprocess.Popen(...)` is blocked.
- Workflow payload compatibility regression:
  - Ensure frontend handles `intent` as string and object payload shapes.
- RAG quality gate:
  - Fail when semantic retrieval pass-rate drops below threshold.
- Redaction edge tests:
  - Unicode email masking,
  - over-redaction prevention for non-sensitive numeric fragments,
  - exception-path resilience tests using mockable pattern wrappers.

## 7. Minimal-Change Optimization Strategy
- Prefer parser/normalization fixes over broad refactors.
- Fix safety pattern matching using normalization, not rule expansion explosion.
- Keep workflow and API contracts backward compatible.
- For dependency-sensitive quality (embedding stack), fail fast in gate/report instead of silently masking quality degradation.

## 8. Regression Execution Order
1. Unit regressions (`workflow_orchestrator_pipeline`, route contracts).
2. Integration gates (cost estimation, code execution runtime).
3. RAG E2E validation report.
4. Frontend E2E smoke.
5. Record final P0/P1 status and unresolved risks.
