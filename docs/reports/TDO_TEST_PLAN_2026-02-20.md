# Industrial AI Flow Test-Driven Optimization Plan (2026-02-20)

## 1. Objective
- Build a repeatable, evidence-based baseline for three critical chains:
  - RAG end-to-end
  - Cost Estimation / ML train+predict
  - Dynamic code generation + sandbox execution
- Add targeted risk probes for P0/P1 vulnerabilities.
- Ensure frontend-triggered API workflow roundtrip is verifiable.

## 2. Scope
- Backend workflow and service layers under `backend/`
- API contracts under `backend/api/`
- Critical tests under `tests/integration/` and `tests/unit/`

Out of scope:
- Large architecture refactors
- Non-critical historical test suites with weak signal quality

## 3. TeamAgents Focus and Acceptance Criteria
- Senior Architect:
  - Focus: chain continuity, dependency boundary, observability fields.
  - Accept if each chain has testable handoff evidence (input -> node -> output).
- Senior QA:
  - Focus: reproducibility, deterministic outputs, regression layering.
  - Accept if commands are repeatable and logs are persisted.
- AI/RAG Expert:
  - Focus: retrieval relevance, source traceability, citation reliability risks.
  - Accept if RAG chain proves ingest->retrieve->answer path and exposes citation gaps.
- LLM Expert:
  - Focus: prompt injection/tool misuse and fallback behavior.
  - Accept if risky payload probes are codified and tracked.
- ML Expert:
  - Focus: training preconditions, prediction stability, interval sanity.
  - Accept if model training/prediction pass deterministic checks and boundary checks.

## 4. Baseline Test Set (Must Run)
- Chain baseline:
  - `tests/integration/test_tdo_baseline_paths.py`
- Existing high-value suites:
  - `tests/integration/test_cost_estimation_api.py`
  - `tests/integration/test_workflow_cost_estimation_query_api.py`
  - `tests/unit/test_workflow_orchestrator_pipeline.py`
  - `tests/integration/test_demo_mode_api.py`
  - `tests/unit/test_code_execution_tool_provider_mode.py`
  - `tests/integration/test_executor_provider_fallback.py`
  - `tests/unit/test_docker_provider_health.py`
  - `tests/unit/test_intent_workflow_dispatch_runtime.py`

Command:
```bash
.venv_tdo/bin/python -m pytest -q \
  tests/integration/test_tdo_baseline_paths.py \
  tests/integration/test_cost_estimation_api.py \
  tests/integration/test_workflow_cost_estimation_query_api.py \
  tests/unit/test_workflow_orchestrator_pipeline.py \
  tests/integration/test_demo_mode_api.py \
  tests/unit/test_code_execution_tool_provider_mode.py \
  tests/integration/test_executor_provider_fallback.py \
  tests/unit/test_docker_provider_health.py \
  tests/unit/test_intent_workflow_dispatch_runtime.py
```

## 5. Risk Probe Set (P0/P1 Discovery)
- `tests/unit/test_tdo_risk_probes.py` (must-pass security probes)
- Security spot-check script output

Command:
```bash
.venv_tdo/bin/python -m pytest -q tests/unit/test_tdo_risk_probes.py -rxX
```

## 6. Pass/Fail and Priority Rules
- P0:
  - Sandbox/policy bypass enabling dangerous execution or data exposure.
  - Critical chain available in API but functionally non-working in production path.
- P1:
  - Security rule bypass requiring modest obfuscation.
  - Core operation contract missing (delete/update/traceability), causing functional breakage.
- Baseline gate:
  - All baseline tests must pass.
  - Risk probes must pass and remain in CI.

## 7. Evidence and Logging Requirements
- Persist command outputs to log files:
  - `logs/tdo_baseline_2026-02-20.log`
  - `logs/tdo_risk_probes_2026-02-20.log`
  - `logs/tdo_security_probe_2026-02-20.log`
- For each defect, include:
  - Repro command or test name
  - Actual observed behavior
  - Expected behavior
  - Impacted chain/components

## 8. Regression Strategy
- Keep baseline tests mandatory in CI gate.
- Add per-fix negative security tests to prevent bypass regressions.
