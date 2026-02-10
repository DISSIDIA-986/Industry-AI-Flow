# Project Paths

## Protected Paths (Do Not Move)
- `backend/`
- `tests/`
- `scripts/`
- `config/`
- `docs/`
- `infrastructure/`
- `docker/`

## Protected Root Files (Do Not Move)
- `backend/main.py`
- `backend/config.py`
- `Makefile`
- `pyproject.toml`
- `requirements.txt`
- `README.md`
- `AGENTS.md`
- `.env.example`
- `backend/init_database.py`
- `backend/init_comprehensive_database.py`

## Cleanup Target Areas
- Root markdown reports and plans:
  - `*_REPORT*.md`
  - `*_SUMMARY*.md`
  - `*_PLAN*.md`
  - `HOTFIX_*.md`
- Root temporary verification scripts:
  - `verify_*.py`
- Historical temp outputs:
  - `Temp/`
  - `test-results*` style folders

## Archive Layout
```text
Deprecated/
├── root-scripts/
├── artifacts/
└── env-backups/

Temp/
├── reports/
├── guides/
└── session-work/

CN Docs/
```
