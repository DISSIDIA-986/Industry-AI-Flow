# TDI Round 20 Findings (2026-02-27)

## 1) P0/P1 Defect List

### B20-01 | P1 | Import-time crash in `backend.main` when `uvicorn` is absent
- Reproduce:
  - Run: `pytest tests/unit/test_auth_routes_contract.py -vv`
- Failure evidence:
  - `ModuleNotFoundError: No module named 'uvicorn'`
  - Log: `logs/tdo/2026-02-27/test_auth_routes_contract_after_fix.xml` (pre-fix run)
- Impact:
  - Contract/runtime tests cannot collect; API module import is brittle in minimal test envs.

### B20-02 | P1 | Import-time hard dependency in OCR module (`Pillow`)
- Reproduce:
  - Run: `pytest tests/unit/test_document_processing.py -vv` in env without Pillow.
- Failure evidence:
  - `ModuleNotFoundError: No module named 'PIL'`
  - Log: `logs/tdo/2026-02-27/test_document_processing_after_fix.xml` (pre-fix run)
- Impact:
  - Document-processing test collection breaks before fallback logic can execute.

### B20-03 | P1 | Import-time hard dependency in document loader (`PyMuPDF/fitz`)
- Reproduce:
  - Run: `pytest tests/unit/test_main_runtime_contracts.py -vv`
- Failure evidence:
  - `ModuleNotFoundError: No module named 'fitz'`
  - Log: `logs/tdo/2026-02-27/test_main_runtime_contracts_after_fix.xml` (pre-fix run)
- Impact:
  - `backend.main` import chain crashes via document manager/loader, blocking runtime contract tests.

### B20-04 | P1 | Chinese-input gate test used English payload (false failure)
- Reproduce:
  - Run: `pytest tests/unit/test_main_runtime_contracts.py::test_rag_query_rejects_chinese_input -vv`
- Failure evidence:
  - Expected `400`, actual `200` because payload was English.
  - Log: `logs/tdo/2026-02-27/test_main_runtime_contracts_after_fix_v2.log`
- Impact:
  - Gate confidence is degraded by a mismatched assertion scenario.

### B20-05 | P1 | Round3 lock regression test asserted stale risk state
- Reproduce:
  - Run: `pytest tests/unit/bugs/test_bug_audit_round3.py::TestAudit3_3_ServiceLockType -vv`
- Failure evidence:
  - Test asserted `_service_lock` must be `threading.Lock`, while runtime uses `asyncio.Lock`.
  - Log: `logs/tdo/2026-02-27/tdo_round20_unit_gate_first_fail.log`
- Impact:
  - Unit gate false-fails and masks real regressions.

### B20-06 | P1 | Round3 groundedness test asserted deprecated placeholder behavior
- Reproduce:
  - Run: `pytest tests/unit/bugs/test_bug_audit_round3.py::TestAudit3_6_GroundednessPlaceholder -vv`
- Failure evidence:
  - Test expected score `1.0` for context-count-only behavior.
  - Current node (correctly) returns `0.0` when answer is empty.
  - Log: `logs/tdo/2026-02-27/tdo_round20_unit_gate_second_fail.log`
- Impact:
  - Legacy test semantics create false negatives.

### B20-07 | P1 | DataAnalysisAgent compatibility hook missing (`code_executor`)
- Reproduce:
  - Run: `pytest tests/unit/bugs/test_bug_audit_round4.py::TestR4_1_DatasetInfoEncodingCrash -vv`
- Failure evidence:
  - `AttributeError: ... data_analysis_agent ... has no attribute 'code_executor'`
  - Log: `logs/tdo/2026-02-27/tdo_round20_unit_gate_third_fail.log`
- Impact:
  - Historical bug-repro tests fail before reaching target assertions.

### B20-08 | P1 | `sqft` extraction misses space-grouped numbers (`5 000 square feet`)
- Reproduce:
  - Run: `pytest tests/unit/bugs/test_bug_audit_round8.py::TestR8_1_ParseHumanNumberSpacedDigits::test_extract_features_spaced_sqft -vv`
- Failure evidence:
  - Expected `sqft=5000.0`, got `0.0`.
  - Log: `logs/tdo/2026-02-27/tdo_round20_unit_gate_fourth_fail.log`
- Impact:
  - Cost estimation feature extraction loses valid area signals from user input.

### B20-09 | P1 | Workflow error can be hidden by stale response payload
- Reproduce:
  - Run: `pytest tests/unit/bugs/test_bug_audit_round8.py::TestR8_5_PipelineErrorSwallowsStaleResponse -vv`
- Failure evidence:
  - `graph.py` only called `response_node` when response was empty.
  - Log: `logs/tdo/2026-02-27/tdo_round20_unit_gate_fifth_fail.log`
- Impact:
  - Users may receive stale success text even when pipeline failed.

### B20-10 | P1 | `budget 120m` not extracted to `estimated_cost_cad`
- Reproduce:
  - Run: `pytest tests/unit/test_cost_estimation_service.py::test_extract_cost_features_handles_adversarial_noise -vv`
- Failure evidence:
  - `KeyError: 'estimated_cost_cad'` for query containing `budget 120m`.
  - Log: `logs/tdo/2026-02-27/tdo_round20_unit_gate_sixth_fail.log`
- Impact:
  - Cost extraction misses common budget phrasing; downstream prediction quality degrades.

## 2) Fix Summary (Minimal Changes)
- `backend/main.py`: moved `uvicorn` import into `if __name__ == "__main__":`.
- `backend/services/document_processing/ocr_processor.py`: removed unused top-level `numpy` and `PIL` imports.
- `backend/services/document_loader.py`: replaced top-level `fitz` import with lazy import helper `_get_fitz()`.
- `tests/unit/test_main_runtime_contracts.py`: corrected Chinese-gate test input to actual Chinese text.
- `tests/unit/bugs/test_bug_audit_round3.py`: updated outdated lock/groundedness assertions to current secure behavior.
- `backend/services/data_analysis/data_analysis_agent.py`: added compatibility hook for module-level `code_executor` monkeypatching.
- `backend/services/cost_estimation_service.py`:
  - `sqft` regex now captures space-grouped numbers.
  - `estimated_cost_cad` regex now supports bare `budget` phrasing (`budget 120m`).
- `backend/services/workflows/graph.py` + `backend/services/workflows/nodes/response_node.py`:
  - enforce error-first response rendering (error no longer masked by stale response).
- Added regression tests:
  - `tests/unit/bugs/test_bug_audit_round20.py` (B20-01/B20-02/B20-03).

## 3) Regression and Verification
- Bug reproduction:
  - `pytest -q -vv tests/unit/bugs/test_bug_audit_round20.py`
- Incremental round gate:
  - `pytest -q -vv tests/unit/bugs/test_bug_audit_round20.py tests/unit/bugs/test_bug_audit_round3.py tests/unit/bugs/test_bug_audit_round4.py tests/unit/bugs/test_bug_audit_round8.py tests/unit/test_cost_estimation_service.py`
- Contract bundle:
  - `pytest -q -vv tests/unit/test_auth_routes_contract.py tests/unit/test_document_processing.py tests/unit/test_main_runtime_contracts.py`
- TDO baseline bundle:
  - `pytest -q -vv tests/integration/test_tdo_baseline_paths.py tests/unit/test_tdo_risk_probes.py tests/unit/test_tdo_p0_p1_findings.py tests/unit/test_workflow_orchestrator_pipeline.py tests/unit/test_auth_routes_contract.py tests/unit/test_main_runtime_contracts.py`

All above bundles pass in `.venv_tdo` after fix.

## 4) Independent Test Plan
- See: `docs/reports/TDI_TEST_PLAN_2026-02-27_ROUND20.md`
