# Capstone Optimization Execution Plan (2026-02-12)

## Objective

Land the optimization items defined in `research/capstone_hybrid_strategy_and_versioning_plan.md` with code, tests, docs, and structure governance.

## Scope

1. Demo-first hybrid operation modes
- Live Hybrid
- Local Safe
- Scripted Replay

2. Routing and governance enforcement
- Route mode resolution aligned with demo mode
- Cost-estimation stays local model path
- Cloud fallback/budget behavior remains explicit and observable

3. Python 3.13 and dependency governance
- Toolchain version consistency in `pyproject.toml`
- Layered dependency files for Capstone workflow
- One-command setup/check scripts for Capstone environment

4. Documentation updates
- Capstone demo environment standard
- Demo mode operation and fallback runbook

5. Project structure optimization (soft-delete only)
- Zero-reference scan
- Batch soft migration to `.deprecated/`
- Append move trace to `cleanup_manifest.log`

## Execution Phases

## Phase A: Core capabilities
- [x] Implement demo mode service and scripted replay catalog
- [x] Expose demo mode management API (read/update)
- [x] Integrate demo mode into workflow and dispatch entry routes

## Phase B: Versioning/dependency governance
- [x] Align `pyproject.toml` tool versions to Python 3.13
- [x] Add layered requirements layout (`requirements/base|dev|demo|lock`)
- [x] Add Capstone env setup/check scripts and Make targets

## Phase C: Test and release gate
- [x] Add unit/integration tests for demo mode behavior
- [x] Add mount/contract tests for new router
- [x] Wire new tests into release gate target
- [x] Run required test suite(s)

## Phase D: Structure optimization
- [x] Run zero-reference scan
- [x] Soft-move stale dependency snapshots to `.deprecated/`
- [x] Verify and record changes in manifest

## Phase E: Final verification
- [x] Re-run targeted scans and tests
- [x] Validate no blocker regressions
- [x] Produce completion summary with evidence

## Constraints

- No hard delete.
- Do not move protected runtime directories.
- Keep compatibility with existing API contracts where possible.
