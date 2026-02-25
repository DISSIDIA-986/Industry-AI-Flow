# Industrial AI Flow TDO Findings (2026-02-20)

## Baseline Summary
- Baseline suite status (after fixes): `40 passed`
- Risk probe status (after fixes): `7 passed`
- Evidence logs:
  - `logs/tdo_baseline_2026-02-20.log`
  - `logs/tdo_risk_probes_2026-02-20.log`
  - `logs/tdo_security_probe_2026-02-20.log`

## P0/P1 Defect List (Fixed)

### P0-1: Dangerous code can reach execution path without validation (Fixed)
- Repro:
  - `tests/unit/test_tdo_risk_probes.py::test_probe_code_execution_tool_rejects_dangerous_payload`
  - `logs/tdo_security_probe_2026-02-20.log`
- Before-fix evidence:
  - `open('/etc/passwd').read()` payload is forwarded to manager path.
  - Probe output shows validator gap (`open_is_valid True`).
- Impact:
  - Dynamic code generation/execution chain.
  - High risk of policy bypass and data access in sandboxed runtime.
- Minimal fix:
  - Enforce `validate_code(..., strict_mode=True)` inside `code_execution_tool` before dispatch.
  - Reject dangerous payloads consistently for both manager and legacy executor paths.
- Regression:
  - Convert probe test to strict passing test.
  - Add negative cases for `open`, `eval`, obfuscated dangerous calls.
- Fix evidence:
  - `tests/unit/test_tdo_risk_probes.py::test_probe_code_execution_tool_rejects_dangerous_payload` now passes.

### P1-1: Safety rule bypass via obfuscated command tokens (Fixed)
- Repro:
  - `tests/unit/test_tdo_risk_probes.py::test_probe_safety_node_blocks_obfuscated_system_call`
  - Input: `os . system('id')`
- Before-fix evidence:
  - `safety_status ok`, `safety_matches None`.
- Impact:
  - Workflow safety gating for code-execution-like prompts.
- Minimal fix:
  - Normalize whitespace/punctuation before pattern matching.
  - Add regex-based signatures for obfuscated dangerous tokens.
- Regression:
  - Keep obfuscation variants as mandatory blocking tests.
- Fix evidence:
  - `logs/tdo_security_probe_2026-02-20.log` shows `safety_status blocked`.

### P1-2: RAG delete chain contract missing (Fixed)
- Repro:
  - `tests/unit/test_tdo_risk_probes.py::test_probe_vectorstore_delete_contract`
  - `has_delete_by_doc_id False` in `logs/tdo_security_probe_2026-02-20.log`
- Before-fix evidence:
  - `SimpleRAG.delete_document()` relies on `vectorstore.delete_by_doc_id()`, but `VectorStore` lacks this method.
- Impact:
  - RAG lifecycle management (document deletion) is functionally broken.
- Minimal fix:
  - Implement `VectorStore.delete_by_doc_id(doc_id)` with transactional delete for `document_chunks` and `documents`.
- Regression:
  - Add integration test: ingest -> delete -> retrieval confirms absence.
- Fix evidence:
  - `logs/tdo_security_probe_2026-02-20.log` shows `has_delete_by_doc_id True`.

### P1-3: Code validator allows direct file read primitive (Fixed)
- Repro:
  - `tests/unit/test_tdo_risk_probes.py::test_probe_code_validator_blocks_builtin_open`
- Before-fix evidence:
  - `validate_code("open('/etc/passwd').read()", strict_mode=True)` returns valid.
- Impact:
  - Weakens sandbox policy defense-in-depth; relies only on runtime isolation.
- Minimal fix:
  - AST-call inspection to block `open(...)` and file-like constructors.
  - Add allowlist only for controlled workspace file access helpers (if needed).
- Regression:
  - Add negative validator tests for direct and aliased file access patterns.
- Fix evidence:
  - `logs/tdo_security_probe_2026-02-20.log` shows `open_is_valid False`.
  - `logs/tdo_security_probe_2026-02-20.log` shows `open_alias_is_valid False`.

## Baseline Chain Coverage (Verified)
- RAG chain:
  - `tests/integration/test_tdo_baseline_paths.py::test_tdo_rag_ingest_retrieve_generate_baseline`
- Cost Estimation/ML chain:
  - `tests/integration/test_tdo_baseline_paths.py::test_tdo_cost_estimation_train_predict_baseline`
- Dynamic code generation/execution chain:
  - `tests/integration/test_tdo_baseline_paths.py::test_tdo_code_generation_execution_baseline`
- Frontend-triggered API roundtrip:
  - `tests/integration/test_tdo_baseline_paths.py::test_tdo_frontend_api_workflow_roundtrip_baseline`
- RAG delete lifecycle:
  - `tests/integration/test_tdo_baseline_paths.py::test_tdo_rag_delete_removes_retrieval_baseline`
