# Project Structure Optimization Plan (2026-02-12)

## 1. Context and Goal
Recent iterations introduced many new code, tests, and documentation files. Root-level documentation clutter increased and reduced signal-to-noise for active engineering work.

This plan follows a safe-cleanup policy:
- no hard delete
- only soft-delete by moving files
- keep all runtime-critical paths unchanged
- keep rollback traceability

## 2. Scope
In scope:
- root-level non-runtime reports with zero references
- documentation classification and archival structure
- verification of prior implementation plan completion (cost-estimation API + workflow intent + release gates)

Out of scope:
- moving `backend/`, `tests/`, `scripts/`, `config/`, `docs/`, `infrastructure/`, `docker/`
- changing API contracts in this cleanup cycle
- deleting files permanently

## 3. Phase Plan

### Phase A: Baseline Audit (completed)
1. Read `research/` core planning docs and implementation notes.
2. Inspect recent Git commits (`git log -n 20`) to identify active change streams.
3. Verify prior plan landing status with gate checks.

Exit criteria:
- prior plan is either fully complete or explicit gaps are listed.

### Phase B: TeamAgency Multi-Angle Review (completed)
Roles and focus:
1. Senior AI Expert: model/data workflow consistency and feature engineering risks.
2. Senior Architect: module boundaries and route-to-service layering.
3. LLM Expert: intent routing, prompting path, fallback behavior.
4. Senior QA Engineer: API-level and gate-level test adequacy.

Exit criteria:
- findings are categorized: structural-safe / review-needed / blocker.

### Phase C: Safe Cleanup Execution (this cycle)
Candidate files (safe, zero references found in scoped scan):
1. `AUDIT_FIX_PLAN.md`
2. `COMPREHENSIVE_AUDIT_REPORT.md`
3. `UNTRACKED_FILES_RESOLUTION_REPORT.md`
4. `UNTRACKED_FILES_ANALYSIS.md` (added by manual reference verification)

Action:
- move to `.deprecated/reports/2026-02-12/`
- append entries into `cleanup_manifest.log`

Exit criteria:
- root clutter reduced
- moved files remain versioned and recoverable
- no runtime/test references broken

### Phase D: Verification and Recheck (this cycle)
1. Verify references (`rg`) for moved files.
2. Run focused gate checks:
   - `make test-cost-estimation-gate`
   - `make test-phase1-gate`
3. Re-list top-level markdown files and confirm reduction.

Exit criteria:
- gates pass
- no broken references
- optimization checklist marked complete

## 4. Risk Controls
1. Strict soft-delete only (`.deprecated/` move).
2. No changes to runtime-critical files during cleanup execution.
3. Every move recorded in `cleanup_manifest.log`.

## 5. Deliverables
1. This implementation plan.
2. Archived files under `.deprecated/reports/2026-02-12/`.
3. Updated `cleanup_manifest.log` entries.
4. Final validation summary against this plan.
