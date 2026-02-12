# Capstone Optimization Completion Report (2026-02-12)

## Summary

Optimization work based on `research/capstone_hybrid_strategy_and_versioning_plan.md` is implemented and validated.

## Delivered

1. Demo-first hybrid operation modes landed
- Added `backend/services/demo_mode_service.py`
- Added mode profiles: `live_hybrid`, `local_safe`, `scripted_replay`
- Added scripted replay scenario catalog and deterministic fallback response

2. Demo mode API landed
- Added `backend/api/demo_mode_routes.py`
- `GET /api/v1/demo/mode`
- `POST /api/v1/demo/mode` (admin/ops/platform_admin)
- `GET /api/v1/demo/replay/health`

3. Workflow/dispatch integration landed
- `backend/api/workflow_query_routes.py` now resolves effective route mode via demo mode service
- Scripted replay short-circuit added for workflow endpoint
- `backend/api/llm_dispatch_routes.py` now honors demo mode and supports scripted replay output
- `backend/services/llm_integration/dispatch_service.py` now enforces demo-mode cloud allowance and local forcing

4. Runtime wiring landed
- Mounted demo router in `backend/main.py`

5. Python/dependency governance landed
- `pyproject.toml`: Black target version set to `py313`; MyPy version set to `3.13`
- Added layered dependency layout:
  - `requirements/base.txt`
  - `requirements/dev.txt`
  - `requirements/demo.txt`
  - `requirements/lock/py313-capstone.txt`
- Added Capstone env scripts:
  - `scripts/setup/check_capstone_env.py`
  - `scripts/setup/setup_capstone_env.sh`
- Added Make targets:
  - `capstone-env-check`
  - `capstone-env-setup`
  - `test-demo-mode-gate`

6. Frontend alignment landed
- Added demo mode read/update API client calls (`frontend/src/lib/api-client.ts`)
- Added demo mode controls in shell header (`frontend/src/components/dashboard-shell.tsx`)

7. Structure optimization (soft move only)
- Moved stale dependency snapshots to `.deprecated`:
  - `requirements_old_multi_version.txt`
  - `requirements_python313.txt`
- Destination:
  - `.deprecated/dependency-snapshots/2026-02-12/`
- Recorded in `cleanup_manifest.log`
- Zero-reference scan rerun (`cleanup_scan_report.tsv`: total 0 candidates)

## Testing Evidence

1. Demo mode gate
- `make test-demo-mode-gate`
- Result: PASS (`17 passed`)

2. Cost-estimation core regression gate subset
- `venv_test/bin/python -m py_compile ...`
- `venv_test/bin/python -m pytest -q tests/integration/test_cost_estimation_api.py tests/integration/test_workflow_cost_estimation_query_api.py tests/unit/test_cost_estimation_service.py tests/unit/test_cost_estimation_workflow_intent.py tests/unit/test_workflow_orchestrator_pipeline.py tests/unit/test_main_cost_estimation_router_mount_contract.py`
- Result: PASS (`18 passed`)

3. Frontend build and lint
- `npm run lint`
- `npm run build`
- Result: PASS

## Multi-Angle Review (TeamAgency-style)

1. Senior AI Expert view
- Cost estimation remains local structured model path (correct separation from LLM free-form estimation).
- Scripted replay provides deterministic presentation resilience.

2. Senior Architect view
- Demo mode control-plane is isolated in service + API + route integration.
- Existing API contracts preserved while adding mode governance metadata.

3. LLM Expert view
- Hybrid routing is now explicitly demo-governed.
- Local-safe and replay behavior reduce cloud dependency risk during live demo.

4. Senior QA Engineer view
- New unit/integration tests cover demo mode API permissions, replay shortcuts, and forced-local behavior.
- Regression suites for cost estimation path remain green.

## Residual Notes

- `capstone-env-check` on this machine reports advisory warnings because active interpreter is not Python 3.13 and lock packages are not fully installed in system Python.
- For strict compliance, run in `.venv_capstone` with Python 3.13 via `make capstone-env-setup`.
