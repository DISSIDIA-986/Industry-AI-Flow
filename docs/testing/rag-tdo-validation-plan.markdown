# RAG TDO Validation Plan

## Scope
- Storage readiness: pgvector extension, document/chunk presence, embedding dimension.
- Retrieval pipeline: semantic, hybrid, and BM25 keyword modes.
- Workflow path: `/api/v1/workflow/health` and `/api/v1/workflow/query`.
- Grounding quality: non-template responses, citation presence, expected-source citation match.
- Regression guard: RAG unit/integration subset under `tests/unit` and `tests/integration`.

## Test Suite
- End-to-end validation:
  - `python scripts/testing/run_construction_rag_e2e_validation.py`
- Focused regression:
  - `pytest -q -vv tests/unit/test_vector_retrieval.py`
  - `pytest -q -vv tests/unit/bugs/test_bug_rag_pipeline.py`
  - `pytest -q -vv tests/integration/test_rag_agent.py`
  - `pytest -q -vv tests/integration/test_complete_rag_system.py`

## Pass Criteria
- E2E acceptance (`construction_rag_e2e_validation_report.json`):
  - `storage_pass=true`
  - `retrieval_modes_pass=true`
  - `workflow_api_pass=true`
  - `workflow_quality_pass=true`
  - `overall_pass=true`
- Regression suite:
  - all selected pytest cases pass
  - junit report generated without collection/runtime errors

## Evidence Requirements
- E2E run log:
  - `logs/tdo_rag_e2e_validation.log`
- Optional environment-controlled E2E comparison:
  - `logs/tdo_rag_e2e_validation_ollama4b.log`
- E2E structured report:
  - `logs/construction_rag_e2e_validation_report.json`
- Regression log:
  - `logs/tdo_rag_regression.log`
- Regression junit:
  - `logs/tdo_rag_regression.xml`
