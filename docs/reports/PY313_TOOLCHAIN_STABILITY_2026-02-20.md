# Python 3.13 Toolchain Stability Analysis (2026-02-20)

## Summary
- Python runtime is stable on `3.13.x` and remains unchanged.
- The failure source was tooling mismatch, not interpreter mismatch:
  - `black==23.7.0` does not support `target-version = ['py313']`.
  - Some global binaries (for example `/usr/local/bin/pytest`) referenced removed Python 3.9 paths.

## Root Cause
1. Config/dependency contradiction:
   - `pyproject.toml` uses `target-version = ['py313']`.
   - Dev dependencies pinned `black==23.7.0` (no `py313` target support).
2. PATH/shebang fragility:
   - Invoking bare `pytest`/`black` can resolve to stale global executables outside the project venv.

## Implemented Fix (No Python Version Change)
1. Upgraded Black toolchain to a `py313`-aware version:
   - `black==24.10.0` in `requirements/dev.txt` and `requirements/lock/py313-capstone.txt`.
   - `pyproject.toml` dev extra updated to `black>=24.10.0,<25.0.0`.
2. Hardened Makefile command execution:
   - Added shared resolvers:
     - `PYTHON_BIN` (prefers `.venv_capstone`, then `venv_test`, then `python3.13`).
     - `PYTHON_BIN_ARM64` (prefers `.venv_capstone_arm64` for arm64-only targets).
   - Switched commands to `$(PYTHON_BIN)` / `$(PYTHON_BIN) -m ...`:
     - `pip`, `pytest`, `black`, `isort`, `flake8`, `mypy`.
     - gate scripts, seed/export scripts, intent checks, and demo utilities.
   - This removes dependence on stale global script shebangs.

## Verification
```bash
# Confirm black supports py313 target
./.venv_capstone/bin/python -m black --version
./.venv_capstone/bin/python -m black --check backend/main.py

# Compile and tests
./.venv_capstone/bin/python -m py_compile backend/main.py backend/config.py backend/init_database.py
./.venv_capstone/bin/python -m pytest -q tests/unit/test_main_runtime_contracts.py tests/unit/test_main_api_version_alias_routes.py

# Makefile end-to-end command-path checks
make capstone-env-check
make test-kpi-gate
```

## Operational Guidance
- Keep Python pinned to `3.13` (no downgrade required).
- Use venv-based module execution for all local/CI quality gates.
- If a local tool fails unexpectedly, verify with:
  - `./.venv_capstone/bin/python -m pip show <tool>`
  - `./.venv_capstone/bin/python -m <tool> --version`
