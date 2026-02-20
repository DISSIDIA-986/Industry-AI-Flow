# Industrial AI Flow TDO Test Plan (2026-02-20 Rerun)

## 1. Coverage Scope
- RAG chain: ingest -> retrieval -> answer generation -> delete lifecycle.
- Cost Estimation chain: train -> load model -> deterministic predict -> interval sanity.
- Dynamic code execution chain: workflow code-execution branch and sandbox/policy checks.
- Frontend/API workflow chain: `POST /api/v1/workflow/query` roundtrip contract.
- Phase-1 gate chain: dispatch/privacy/cost/workflow route and service contracts.

## 2. Test Suite
- Baseline and risk probes:
  - `tests/integration/test_tdo_baseline_paths.py`
  - `tests/unit/test_tdo_risk_probes.py`
  - `tests/unit/test_tdo_p0_p1_findings.py`
- Expanded phase-1 gate suite:
  - `tests/unit/test_dispatch_service.py`
  - `tests/unit/test_redaction_service.py`
  - `tests/unit/test_llm_api_routes.py`
  - `tests/unit/test_cost_tracker_budget_logic.py`
  - `tests/unit/test_llm_config_resolution.py`
  - `tests/unit/test_cost_estimation_service.py`
  - `tests/unit/test_cost_estimation_workflow_intent.py`
  - `tests/unit/test_workflow_orchestrator_pipeline.py`
  - `tests/unit/test_main_cost_estimation_router_mount_contract.py`
  - `tests/integration/test_cost_estimation_api.py`
  - `tests/integration/test_workflow_cost_estimation_query_api.py`
  - `tests/integration/test_week1_fixes.py`

## 3. Execution Commands
```bash
mkdir -p logs/tdo/2026-02-20

.venv_tdo/bin/pytest -q -vv \
  tests/integration/test_tdo_baseline_paths.py \
  tests/unit/test_tdo_risk_probes.py \
  tests/unit/test_tdo_p0_p1_findings.py \
  --junitxml=logs/tdo/2026-02-20/tdo_regression.xml \
  2>&1 | tee logs/tdo/2026-02-20/tdo_regression.log

.venv_capstone/bin/python -m pytest -q -vv \
  tests/unit/test_dispatch_service.py \
  tests/unit/test_redaction_service.py \
  tests/unit/test_llm_api_routes.py \
  tests/unit/test_cost_tracker_budget_logic.py \
  tests/unit/test_llm_config_resolution.py \
  tests/unit/test_cost_estimation_service.py \
  tests/unit/test_cost_estimation_workflow_intent.py \
  tests/unit/test_workflow_orchestrator_pipeline.py \
  tests/unit/test_main_cost_estimation_router_mount_contract.py \
  tests/integration/test_cost_estimation_api.py \
  tests/integration/test_workflow_cost_estimation_query_api.py \
  tests/integration/test_week1_fixes.py \
  --junitxml=logs/tdo/2026-02-20/tdo_phase1_regression.xml \
  2>&1 | tee logs/tdo/2026-02-20/tdo_phase1_regression.log
```

## 4. Pass Criteria
- No failed assertions in baseline/risk probe suites.
- No failed assertions in expanded phase-1 gate suite.
- Security probes remain blocking for dangerous payloads and obfuscated calls.
- Workflow query API returns controlled error payload (no unhandled 500) when runner fails.
- Out-of-workspace data file access is rejected in both Docker and PPIO provider paths.

## 5. Evidence Requirements
- Required artifacts:
  - `logs/tdo/2026-02-20/tdo_regression.log`
  - `logs/tdo/2026-02-20/tdo_regression.xml`
  - `logs/tdo/2026-02-20/tdo_phase1_regression.log`
  - `logs/tdo/2026-02-20/tdo_phase1_regression.xml`
- For every P0/P1 issue (if present), capture:
  - exact failing test id,
  - assertion/error snippet,
  - reproduction command,
  - impacted module path.
