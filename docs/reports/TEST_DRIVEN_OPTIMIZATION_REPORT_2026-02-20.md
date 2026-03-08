# Test-Driven Optimization Report (2026-02-20)

## Summary
This run established a reproducible baseline across RAG, cost estimation, dynamic execution, and frontend-backend connectivity, then used failures to identify P0/P1 issues.

## Baseline Execution Matrix
- PASS: `tests/integration/test_cost_estimation_api.py` (3 passed)
- PASS: `tests/integration/test_workflow_cost_estimation_query_api.py` (3 passed)
- PASS: `tests/unit/test_workflow_orchestrator_pipeline.py` (5 passed before fix, 6 passed after fix)
- PASS: `tests/integration/test_data_analysis_runtime_gate.py` (1 passed)
- PASS: `tests/integration/test_executor_provider_fallback.py` (4 passed)
- PASS: `tests/unit/test_workflow_query_routes.py` (4 passed)
- FAIL: `scripts/testing/run_construction_rag_e2e_validation.py` (exit code 2; overall_pass=false)
- FAIL (before fix): frontend E2E workflow chat scenario
- PASS (after fix): frontend E2E workflow chat scenario
- FAIL (security deep suite): `tests/unit/security/test_redaction_service.py` subset in composite run

Logs:
- `logs/test-driven-optimization/2026-02-20/`
- `logs/construction_rag_e2e_validation_report.json`

## P0/P1 Findings

### [P0] Safety rule bypass in workflow safety node (fixed)
- Component: `backend/services/workflows/nodes/safety_node.py`
- Symptom: `subprocess.Popen` payload was not blocked due case mismatch (`query` lowercased, pattern not lowercased).
- Reproduction:
  1. Send workflow query containing `subprocess.Popen('whoami')`.
  2. Before fix, safety rule did not match this pattern.
- Evidence:
  - New regression test added in `tests/unit/test_workflow_orchestrator_pipeline.py` (`test_workflow_pipeline_safety_block_subprocess_call`).
  - Post-fix run: 6/6 passed.
- Impact:
  - Potential dangerous instruction not blocked in critical path.
- Minimal fix:
  - Normalize pattern to lowercase (`subprocess.popen`).
- Regression method:
  - Run `python -m pytest -q tests/unit/test_workflow_orchestrator_pipeline.py`.

### [P1] Frontend runtime crash on workflow intent payload variant (fixed)
- Component: `frontend/src/lib/api-client.ts` + workflow chat rendering path.
- Symptom: Client crashed with `Objects are not valid as a React child` when `intent` was object-shaped.
- Reproduction:
  1. Run Playwright scenario `workflow chat sends message and renders AI response`.
  2. Mock endpoint returns `intent: {type, confidence, description}`.
  3. Before fix, parsing assumed `intent` is string and produced invalid `description` object.
- Evidence:
  - Failure log: `logs/test-driven-optimization/2026-02-20/09_frontend_e2e_workflow_chat_debug.log`.
  - Error context: `frontend/test-results/.../error-context.md`.
  - Post-fix pass: `logs/test-driven-optimization/2026-02-20/12_frontend_e2e_after_fix.log`.
- Impact:
  - User-facing page crash; end-to-end flow broken.
- Minimal fix:
  - Add `normalizeWorkflowIntent` parser to support both string and object contract.
  - Preserve source/timestamp/confidence fields when present.
- Regression method:
  - Re-run the Playwright scenario above.

### [P1] RAG semantic retrieval mode collapse under embedding fallback (open)
- Component: embedding + semantic retrieval quality gate.
- Symptom: RAG E2E overall failed because semantic retrieval pass-rate was 0.0.
- Reproduction:
  1. Run `python scripts/testing/run_construction_rag_e2e_validation.py`.
  2. Observe `retrieval_modes_pass=false`, `semantic.pass_rate=0.0`.
- Evidence:
  - Report: `logs/construction_rag_e2e_validation_report.json`.
  - Runtime logs show `sentence-transformers is unavailable; using deterministic fallback embeddings`.
- Impact:
  - Retrieval quality instability; semantic branch becomes effectively unusable while other branches may pass.
- Minimal fix options:
  1. Add hard gate in deployment/profile requiring real embedding backend for semantic mode.
  2. Mark semantic retrieval degraded in health/status and route to hybrid/keyword with explicit warning.
  3. Add CI guard that fails when semantic pass-rate < threshold.
- Regression method:
  - Re-run RAG E2E script and check `acceptance.retrieval_mode_breakdown.semantic_pass == true`.

### [P1] Redaction reliability gaps in security deep suite (open)
- Component: `backend/services/security/redaction_service.py` and deep unit tests.
- Symptom:
  - Unicode email case not redacted in deep test.
  - Over-redaction / test-compat issues in some numeric cases.
  - Exception-path tests use non-patchable `re.Pattern.subn` method in Python 3.13.
- Reproduction:
  1. Run composite security suite including `tests/unit/security/test_redaction_service.py`.
  2. Observe 5 failures in this file.
- Evidence:
  - `logs/test-driven-optimization/2026-02-20/07_security_runtime_contracts.log`.
- Impact:
  - Potential sensitive data leakage edge cases; noisy/fragile security test signal.
- Minimal fix options:
  1. Expand email pattern coverage for internationalized addresses.
  2. Tighten phone pattern boundaries to avoid false positives.
  3. Refactor tests to patch wrapper callables rather than `re.Pattern.subn` directly.
- Regression method:
  - Re-run the same security suite and require zero failures.

## Team-Agent Perspective (focus and acceptance)

### Senior Architect
- Focus: end-to-end chain integrity, dependency degradation visibility, operational observability.
- Acceptance: quality degradation must be explicit (not silent), critical path must fail fast or degrade safely.

### Senior QA
- Focus: reproducible baselines, deterministic logs, regression gates for each critical chain.
- Acceptance: every P0/P1 has reproducible steps, objective pass/fail criteria, and stable rerun command.

### AI/RAG Specialist
- Focus: retrieval mode quality, citation-grounded responses, embedding stack readiness.
- Acceptance: semantic/hybrid/keyword all meet threshold; citations map to expected sources.

### LLM Specialist
- Focus: prompt/tool routing safety and fallback behavior under provider outages.
- Acceptance: fallback should preserve safety guarantees; blocked patterns must be case/format robust.

### ML Specialist
- Focus: cost model training/predict contract stability and boundary behavior.
- Acceptance: train/predict/batch paths must be stable with explicit model-not-loaded behavior and interval checks.

## Code Changes Applied in This Run
- `backend/services/workflows/nodes/safety_node.py`
- `tests/unit/test_workflow_orchestrator_pipeline.py`
- `frontend/src/lib/api-client.ts`

## Next Regression Set
1. Re-run full targeted baseline in `docs/TEST_DRIVEN_OPTIMIZATION_PLAN_2026-02-20.md`.
2. Resolve open P1 items (semantic embedding readiness and redaction deep suite), then lock with CI gate.
