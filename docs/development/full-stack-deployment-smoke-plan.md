# Full Stack Deployment and Smoke Test Plan (Mac Studio M1 Max, 32GB)

## 1. Goal

Bring up the full local stack from zero, validate end-to-end connectivity, and produce a repeatable smoke process that can be used by Dev, QA, and Ops.

Scope:
- Infra dependencies (PostgreSQL + pgvector, Ollama, Python env, Node env)
- Backend runtime
- Frontend runtime
- Frontend-to-backend connectivity
- API-level smoke checks

## 2. Cross-role Alignment (Architecture / Core Dev / QA / Ops)

### Architecture decisions
- Use a single local canonical backend port: `8000`.
- Use frontend proxy route as the default browser path: `/api/backend/...`.
- Keep startup deterministic: infra -> DB init -> backend -> frontend -> smoke.
- Treat smoke as gate:
  - Platform health
  - Workflow health
  - Cost-estimation health
  - Frontend proxy path health

### Core Dev decisions
- Keep `init_database.py` as current schema bootstrap authority.
- Do not depend on Alembic for local zero-to-one setup right now (repository currently has Alembic command references but no Alembic config tree).
- Prefer environment-driven API base URLs to handle historical port drift (`8000/8001/8002`) without blocking local bring-up.

### QA decisions
- Split checks:
  - Runtime smoke: real services and real ports.
  - UI E2E: keep Playwright suite as regression layer (currently mostly mocked paths).
- Use full-stack smoke script as QA handoff precondition.

### Ops decisions
- Provide one command for startup and one for teardown.
- Persist logs under `logs/`.
- Write frontend `.env.local` during bring-up to enforce consistent upstream routing.

## 3. Known Risks and Pre-mitigation

### R1. Port drift across frontend/backend
- Symptom: parts of frontend code default to `8001`, backend default is `8000`.
- Mitigation:
  - Enforce frontend env values at startup (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_REAL_API_URL`, `BACKEND_BASE_URL` -> `8000`).

### R2. Health endpoint drift in old scripts/docs
- Symptom: some scripts check `/api/intent/health` while active backend health is `/api/v1/health`.
- Mitigation:
  - Standardize smoke checks on `/api/v1/health`, `/api/v1/workflow/health`, `/api/v1/cost-estimation/health`.

### R3. Migration toolchain mismatch
- Symptom: `alembic upgrade head` appears in scripts, but no Alembic config directory is present.
- Mitigation:
  - Local deployment flow uses `init_database.py` + SQL extension enablement.
  - If Alembic is introduced later, re-enable as separate gated phase.

### R4. Frontend direct API calls may hit CORS
- Symptom: backend has no explicit CORS middleware; direct browser calls to different origin can fail.
- Mitigation:
  - Prefer Next proxy route (`/api/backend/...`) for browser traffic.

### R5. Optional cloud fallback can fail without key
- Symptom: `HYBRID_MODE=hybrid_auto` with cloud provider `zhipu` may fail if `ZHIPU_API_KEY` missing and local path falls through.
- Mitigation:
  - For local smoke baseline, set route mode to local-only behavior in UI/testing and ensure local model exists.

### R6. WebSocket expectations vs backend reality
- Symptom: frontend has websocket toggle defaults, backend currently does not expose `/ws`.
- Mitigation:
  - Keep websocket checks out of required smoke gate.

## 4. Required Prep Before First Bring-up

### System dependencies
- `python3.13`
- `npm`
- `postgresql` service (Homebrew)
- `ollama`
- `psql`, `createdb`, `curl`

### Configuration
- Root `.env` exists (copy from `.env.example` if missing).
- Frontend `.env.local` is generated during startup with canonical port config.

### Data layer
- Ensure DB exists: `ai_workflow`.
- Ensure extension: `CREATE EXTENSION IF NOT EXISTS vector;`
- `init_database.py` runs at app startup and creates required tables.

## 5. Standard Startup Sequence

### Command (recommended)
```bash
bash scripts/deploy/full_stack_up.sh
```

This script performs:
1. Start/check PostgreSQL service (best-effort Homebrew detection).
2. Ensure database + pgvector extension.
3. Ensure Ollama service and configured model availability.
4. Ensure Python capstone environment exists.
5. Write frontend env to align backend URL/port.
6. Start backend (`uvicorn`) and wait for `/api/v1/health`.
7. Start frontend (`next dev`) and wait for `http://127.0.0.1:3123`.
8. Run full-stack smoke script.

## 6. Smoke Gate Contents

Smoke command:
```bash
bash scripts/testing/run_full_stack_smoke.sh
```

Checks:
- Backend platform health: `/api/v1/health`
- Backend workflow health: `/api/v1/workflow/health`
- Backend cost health: `/api/v1/cost-estimation/health`
- Frontend reachable: `/`
- Frontend proxy -> backend health:
  - `/api/backend/api/v1/health`
  - `/api/backend/api/v1/workflow/health`

## 7. Shutdown Sequence

```bash
bash scripts/deploy/full_stack_down.sh
```

Stops:
- Backend process
- Frontend process
- Removes pid files
- Best-effort kill for orphaned dev processes

## 8. Team Workflow Recommendation

### Daily integration rhythm
1. Developer runs `full_stack_up.sh` before integration coding.
2. QA uses same command before smoke validation.
3. If smoke fails, attach:
   - `logs/backend.log`
   - `logs/frontend.log`
   - failing endpoint and response payload

### Pre-release minimum gate
1. Full-stack smoke: pass.
2. Backend smoke gate: `make test-demo-smoke-live-gate`.
3. Frontend E2E gate (chromium): `cd frontend && npm run test:e2e -- --project=chromium`.

## 9. Immediate Follow-up Backlog (High Priority)

1. Remove or update legacy scripts/docs that still assume `/api/intent/health`.
2. Decide on one migration strategy: either add real Alembic setup or remove Alembic commands from operational scripts.
3. Unify frontend API client defaults to canonical backend port to reduce env coupling.
4. Add explicit CORS policy if direct browser-to-backend calls remain required.

