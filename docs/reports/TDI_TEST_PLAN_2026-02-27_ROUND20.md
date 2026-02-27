# TDI Round 20 Test Plan (2026-02-27)

## Coverage Scope
- Workflow baseline chain: intent -> safety -> retrieval/rerank -> route -> code execution -> response -> groundedness.
- Security probes: dangerous code payload rejection and safety-node blocking.
- Code execution tool compatibility path: manager mode + legacy executor fallback.
- P0/P1 regression surfaces from prior TDI rounds: workflow route/runtime and code sandbox path checks.
- Import-time resilience for optional dependencies (`uvicorn`, `Pillow`, `PyMuPDF`) in unit/contract environments.
- Cost feature extraction robustness for real-world budget/area phrasing (`5 000 square feet`, `budget 120m`).
- Error-path response determinism when stale response payload exists.

## Test Suite
- `tests/integration/test_tdo_baseline_paths.py`
- `tests/unit/test_tdo_risk_probes.py`
- `tests/unit/test_tdo_p0_p1_findings.py`
- `tests/unit/test_workflow_orchestrator_pipeline.py`
- `tests/unit/test_code_execution_tool_provider_mode.py`
- `tests/unit/bugs/test_bug_audit_round20.py`
- `tests/unit/test_auth_routes_contract.py`
- `tests/unit/test_document_processing.py`
- `tests/unit/test_main_runtime_contracts.py`
- `tests/unit/test_cost_estimation_service.py`
- `tests/unit/bugs/test_bug_audit_round3.py`
- `tests/unit/bugs/test_bug_audit_round4.py`
- `tests/unit/bugs/test_bug_audit_round8.py`

## Execution Commands
```bash
.venv_tdo/bin/python -m pytest -q -vv \
  tests/integration/test_tdo_baseline_paths.py \
  tests/unit/test_tdo_risk_probes.py \
  tests/unit/test_tdo_p0_p1_findings.py \
  --junitxml=logs/tdo/2026-02-27/tdo_regression.xml \
  2>&1 | tee logs/tdo/2026-02-27/tdo_regression.log

.venv_tdo/bin/python -m pytest -q -vv \
  tests/unit/test_workflow_orchestrator_pipeline.py \
  tests/integration/test_tdo_baseline_paths.py \
  tests/unit/test_tdo_risk_probes.py \
  tests/unit/test_tdo_p0_p1_findings.py \
  tests/unit/test_code_execution_tool_provider_mode.py \
  --junitxml=logs/tdo/2026-02-27/tdo_regression_round20_after_groundedness.xml \
  2>&1 | tee logs/tdo/2026-02-27/tdo_regression_round20_after_groundedness.log

.venv_tdo/bin/python -m pytest -q -vv \
  tests/unit/bugs/test_bug_audit_round20.py \
  tests/unit/test_auth_routes_contract.py \
  tests/unit/test_document_processing.py \
  tests/unit/test_main_runtime_contracts.py \
  --junitxml=logs/tdo/2026-02-27/tdo_round20_contract_bundle_after_fix.xml \
  2>&1 | tee logs/tdo/2026-02-27/tdo_round20_contract_bundle_after_fix.log

.venv_tdo/bin/python -m pytest -q -vv \
  tests/unit/bugs/test_bug_audit_round20.py \
  tests/unit/bugs/test_bug_audit_round3.py \
  tests/unit/bugs/test_bug_audit_round4.py \
  tests/unit/bugs/test_bug_audit_round8.py \
  tests/unit/test_cost_estimation_service.py \
  --junitxml=logs/tdo/2026-02-27/tdo_round20_incremental_bundle.xml \
  2>&1 | tee logs/tdo/2026-02-27/tdo_round20_incremental_bundle.log
```

## Pass Criteria
- All listed tests pass with no new failures.
- Reproduced P0/P1 findings are fixed with deterministic assertions.
- Workflow code-execution path keeps response contract (`Code output: ...`) and groundedness metadata remains populated.
- Unit test collection no longer fails on missing optional runtime dependencies.

## Evidence Artifacts
- `logs/tdo/2026-02-27/tdo_regression.log`
- `logs/tdo/2026-02-27/tdo_regression.xml`
- `logs/tdo/2026-02-27/tdo_regression_after_fix.log`
- `logs/tdo/2026-02-27/tdo_regression_after_fix.xml`
- `logs/tdo/2026-02-27/tdo_regression_round20_after_groundedness.log`
- `logs/tdo/2026-02-27/tdo_regression_round20_after_groundedness.xml`
- `logs/tdo/2026-02-27/tdo_round20_bug_repro.log`
- `logs/tdo/2026-02-27/tdo_round20_bug_repro_after_fix_v2.log`
- `logs/tdo/2026-02-27/tdo_round20_contract_bundle_after_fix.log`
- `logs/tdo/2026-02-27/tdo_round20_contract_bundle_after_fix.xml`
- `logs/tdo/2026-02-27/tdo_round20_baseline_bundle_after_fix.log`
- `logs/tdo/2026-02-27/tdo_round20_baseline_bundle_after_fix.xml`
- `logs/tdo/2026-02-27/tdo_round20_unit_gate_first_fail.log`
- `logs/tdo/2026-02-27/tdo_round20_unit_gate_second_fail.log`
- `logs/tdo/2026-02-27/tdo_round20_unit_gate_third_fail.log`
- `logs/tdo/2026-02-27/tdo_round20_unit_gate_fourth_fail.log`
- `logs/tdo/2026-02-27/tdo_round20_unit_gate_fifth_fail.log`
- `logs/tdo/2026-02-27/tdo_round20_unit_gate_sixth_fail.log`
- `logs/tdo/2026-02-27/tdo_round20_incremental_bundle.log`
- `logs/tdo/2026-02-27/tdo_round20_incremental_bundle.xml`
- `logs/tdo/2026-02-27/tdo_round20_regression_bundle_full.log`
- `logs/tdo/2026-02-27/tdo_round20_regression_bundle_full.xml`
