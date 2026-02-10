# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: main FastAPI application (API routes, agents, services, security, observability).
- `tests/`: automated tests organized by `unit/`, `integration/`, `performance/`, and `evaluation/`.
- `scripts/`: setup, migration, testing, deployment, and utility scripts.
- `config/`: environment-specific Python config modules (`development.py`, `testing.py`, `production.py`).
- `docs/`: architecture, development notes, and operational guides.
- `test_resources/`: static fixtures (images/documents) used by OCR and integration tests.

## Build, Test, and Development Commands
- `make install-dev`: install runtime + developer tooling (Black, isort, Flake8, MyPy, pytest).
- `make run`: start local API server via `uvicorn backend.main:app --reload`.
- `make test`: run full pytest suite with coverage for `backend/`.
- `make test-unit` / `make test-integration`: run focused suites.
- `make test-phase1-gate`: run the current quality gate for dispatch/privacy/cost APIs.
- `make format` and `make lint`: format and static-check code before opening a PR.
- `make db-setup`: initialize pgvector + run migrations + seed prompts.

## Coding Style & Naming Conventions
- Python target is **3.13 only** (`>=3.13,<3.14`).
- Use 4-space indentation, PEP 8 defaults, and type hints for new/changed code.
- Formatting: Black (`line-length = 88`) and isort (`profile = "black"`).
- Lint/type checks: Flake8 + MyPy (`mypy backend/`).
- Naming: `snake_case` for functions/files, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.

## Testing Guidelines
- Framework: `pytest` with markers (`unit`, `integration`, `performance`, `ocr`, `llm`, `slow`).
- Test files follow `test_*.py`; keep tests close to target behavior (`tests/unit/test_<feature>.py`).
- Run quick local checks with `pytest tests/unit -v`; run broader validation with `make test`.
- Add or update tests for every functional change, especially API contracts and security-sensitive paths.

## Commit & Pull Request Guidelines
- Follow existing prefix style seen in history: `feat:`, `fix:`, `docs:`, `test:`, `security:`, `chore:`.
- Keep commit subjects short and specific (optionally include scope, e.g., `fix(api): ...`).
- PRs should include: purpose, key changes, test evidence (commands/results), and linked issue(s).
- Include request/response examples or screenshots when behavior/UI/output changes.
