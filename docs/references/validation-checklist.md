# Validation Checklist

## Pre-Cleanup
- Run read-only scan: `bash scripts/scan_cleanup_targets.sh .`
- Confirm no protected path/file is in candidate list.
- Confirm `.gitignore` includes archive output paths.

## Cross-Validation
- `backend/`, `tests/`, `scripts/`, `.github/`, `docker/`, `infrastructure/` reference checks:
  - `rg -n "<filename>" backend tests scripts .github docker infrastructure`
- Mark risk:
  - `safe`: no references in code/test/CI/deploy scopes.
  - `review`: only docs/notes references.
  - `blocker`: references found in runtime/test/CI/deploy scopes.

## Execution
- Run dry-run first:
  - `bash scripts/cleanup_project.sh --dry-run`
- Execute move with manifest:
  - `bash scripts/cleanup_project.sh --execute`
- Verify post state:
  - `bash scripts/cleanup_project.sh --verify`

## Rollback
- Rollback using manifest:
  - `bash scripts/cleanup_project.sh --rollback`
  - or `bash scripts/rollback_cleanup.sh cleanup_manifest.log`

## QA Gate
- `pytest --collect-only` for sanity (or targeted suites).
- Prompt/workflow smoke paths loadable.
- Output final decision:
  - `PASS`
  - `CONDITIONAL PASS`
  - `FAIL`
