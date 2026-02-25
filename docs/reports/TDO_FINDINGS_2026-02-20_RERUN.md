# Industrial AI Flow TDO Findings (2026-02-20 Rerun)

## 1. Baseline Execution Summary
- TDO baseline + risk probes:
  - Result: `16 passed, 0 failed`
  - Evidence:
    - `logs/tdo/2026-02-20/tdo_regression.log`
    - `logs/tdo/2026-02-20/tdo_regression.xml`
- Expanded phase-1 gate regression:
  - Result: `43 passed, 1 skipped, 0 failed`
  - Evidence:
    - `logs/tdo/2026-02-20/tdo_phase1_regression.log`
    - `logs/tdo/2026-02-20/tdo_phase1_regression.xml`

## 2. P0/P1 Defect List
- No new P0/P1 defects reproduced in this rerun.
- No failing assertions were observed in the executed baseline, risk probes, or phase-1 gate suites.

## 3. Minimal Optimization Suggestions (No Code Change Required Now)
- Keep `tests/unit/test_tdo_risk_probes.py` and `tests/unit/test_tdo_p0_p1_findings.py` in required CI gates to prevent policy/sandbox regressions.
- Convert the currently skipped retrieval test in `tests/integration/test_week1_fixes.py` to a runnable fixture-backed integration check when test data provisioning is available.
- Keep JUnit XML artifacts in CI uploads to preserve traceability for future P0/P1 triage.

## 4. Regression and Verification Method
```bash
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

## 5. Residual Risk Notes
- One skipped test (`tests/integration/test_week1_fixes.py::TestWeek1Fixes::test_end_to_end_retrieval_with_nltk`) still depends on seeded DB fixtures; end-to-end retrieval confidence is therefore not fully demonstrated in this rerun.
