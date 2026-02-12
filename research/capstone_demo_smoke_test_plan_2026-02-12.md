# Industry AI Flow Demo Gap Analysis & Smoke Test Plan (Mac Studio)

Date: 2026-02-12  
Scope: Capstone demo-readiness, local full-chain run, and smoke-test plan

## 0. P0 Landing Update (2026-02-12)

Completed in this iteration:
1. Merged dataset branch into `main`:
- merge commit: `4481519`
- added file: `datasets/unified_construction_projects_enhanced.csv`
2. Added executable smoke runner:
- `scripts/testing/run_demo_smoke.py`
- includes: Python/dataset/model/Postgres/Ollama preflight + FastAPI `TestClient` API smoke
3. Added Make target:
- `make test-demo-smoke`
4. Reworked environment verification script:
- `scripts/setup/verify_env.sh` now validates dynamic `OLLAMA_MODEL`, `psycopg` compatibility, and Postgres reachability.
5. Added unit tests for smoke runner:
- `tests/unit/test_run_demo_smoke_script.py`
6. Updated `.env.example` defaults for local demo path:
- explicit `LLM_BACKEND=ollama`
- `LOCAL_PRIMARY_BACKEND=ollama`

Remaining operator actions on local machine:
1. Start PostgreSQL server process (client exists, server currently not running).
2. Align Ollama model with env (`OLLAMA_MODEL`) or pull the configured model.
3. Bootstrap Python 3.13 lock env (`make capstone-env-setup`) before live rehearsal.

## 1. Current Readiness Snapshot

### 1.1 Verified status on current machine
- Python:
  - `python3` = 3.9.6
  - `python3.13` = 3.13.12 (available)
- Ollama:
  - service is running
  - installed model: `deepseek-r1:8b`
  - project configured model: `qwen2.5:7b`
- PostgreSQL:
  - `psql` installed (14.20)
  - DB service is **not running** (`localhost:5432 - no response`)
- Cost-estimation training dataset:
  - no matching CSV found in current branch/worktree for required schema
- Capstone lock env:
  - Python 3.13 is present, but lock dependencies are not installed in a dedicated 3.13 venv yet

### 1.2 Immediate conclusion
A complete local end-to-end demo run is **not ready yet**, but it is feasible on this Mac Studio after environment bootstrap and data/model preparation.

---

## 2. Demo-Critical Missing Items (P0/P1)

## P0 (must finish before demo rehearsal)
1. Cost model training input is missing in current branch.
- Impact: `/api/v1/cost-estimation/predict` and NL cost route cannot provide real model output unless a model artifact is trained/loaded.

2. PostgreSQL service is not running.
- Impact: RAG/document/vector and workflow startup paths degrade or fail.

3. Local LLM model mismatch.
- Config expects `qwen2.5:7b`, installed is `deepseek-r1:8b`.
- Impact: local dispatch or RAG generation can fail if model is not present.

4. Python runtime environment is inconsistent with project baseline.
- Project baseline is Python 3.13, but existing venvs are mixed (`3.9` broken-arch env and `3.14` env).
- Impact: dependency/runtime drift risk and unstable demo behavior.

## P1 (should finish for smoother demo)
1. Unify env defaults for embedding (`.env` vs `backend/config.py` defaults) to avoid confusion.
2. Add a dedicated smoke-test command/script for one-click verification.
3. Refresh README setup snippets to align with capstone lock workflow.

---

## 3. Commercial LLM Config Audit

## 3.1 What the code supports now
- Cloud provider in control plane currently resolves to `zhipu`.
- Required vars for cloud path:
  - `ZHIPU_API_KEY`
  - `ZHIPU_BASE_URL` (Anthropic-compatible endpoint)
  - `ZHIPU_MODEL`

## 3.2 Current config correctness check
- `.env` currently has no `ZHIPU_API_KEY` and no `ZHIPU_MODEL` override.
- Result:
  - local-only path is still usable.
  - any forced cloud path (`cloud_only`) will fail unless cloud config is added.

## 3.3 Recommendation for demo
- Keep default demo path as `live_hybrid` or `local_safe` first.
- Only enable cloud fallback after verifying `ZHIPU_API_KEY` + a real cloud test call.

---

## 4. Python Environment Strategy (Answer to venv vs conda)

Recommendation: use **venv** as project standard for this repo.

Reason:
1. Existing capstone scripts already assume `venv` (`scripts/setup/setup_capstone_env.sh`).
2. Project baseline is explicitly Python 3.13.
3. Reduces cross-tool variance during demo rehearsal.

Standard command:
```bash
make capstone-env-setup
```
This creates `.venv_capstone` and installs the locked dependencies.

---

## 5. TeamAgent-style Consolidated Smoke Plan

## 5.1 Senior Architect view (system connectivity)
Focus:
1. Verify layer-to-layer connectivity is intact (UI -> API proxy -> backend routes -> workflow/AI engine -> DB/storage).
2. Validate route-mode governance (`local_only`, `hybrid_auto`, `cloud_only`) and demo mode behavior.
3. Ensure fallback paths are deterministic for live demo.

Must-pass connectivity checks:
1. Frontend proxy can reach backend (`/api/backend/api/v1/health`).
2. Workflow route works (`/api/v1/workflow/query`) and returns trace/session metadata.
3. Cost-estimation route health is loaded after training (`/api/v1/cost-estimation/health`).
4. Data-analysis and visualization endpoints can complete one happy-path call.

## 5.2 Senior QA view (smoke cases)
Smoke suite (minimal but full-chain):
1. Health checks:
- `GET /api/v1/health`
- `GET /api/v1/workflow/health`
- `GET /api/v1/cost-estimation/health`

2. Workflow NL entry:
- `POST /api/v1/workflow/query` with cost-estimation natural language query.
- Expect `intent=cost_estimation` and successful response.

3. Cost model API:
- `POST /api/v1/cost-estimation/train`
- `POST /api/v1/cost-estimation/predict`
- `POST /api/v1/cost-estimation/predict/batch`

4. Data flow:
- upload CSV -> analyze -> generate visualization -> fetch visualization file.

5. Demo mode:
- switch/read mode and verify scripted replay route behavior.

6. Frontend sanity:
- open MVP pages and execute one core action per page.

## 5.3 LLM Expert view (routing/model quality)
Focus checks:
1. Local model availability and response speed under demo prompt length.
2. Natural-language cost intent robustness (EN/ZH phrasing variants).
3. Hybrid fallback correctness:
- local confidence low -> cloud fallback (only if cloud key configured)
- cloud disabled -> safe local behavior
4. Token/cost policy endpoints return sane values.

## 5.4 Senior AI Engineer view (ML artifact integrity)
Focus checks:
1. Dataset schema completeness for cost-estimation training.
2. Training artifact creation under `workspace/models/cost_estimation/latest.json`.
3. Artifact metadata contains training rows/metrics.
4. Inference output includes interval and uncertainty fields.

---

## 6. Step-by-Step Smoke Execution (Mac Studio)

## Phase A: Environment bootstrap
1. Create standard env and install lock deps:
```bash
make capstone-env-setup
```
2. Start PostgreSQL and verify:
```bash
brew services start postgresql@14 || brew services start postgresql
pg_isready -h localhost -p 5432
```
3. Ensure Ollama model alignment (choose one):
- Option A: pull configured model
```bash
ollama pull qwen2.5:7b
```
- Option B: keep current model and update `.env` `OLLAMA_MODEL=deepseek-r1:8b`

## Phase B: Data/model prep
1. Place training CSV in workspace (same schema as cost-estimation service expects).
2. Train model:
```bash
python scripts/utilities/train_cost_estimation_model.py \
  --dataset-path <path-to-training-csv> \
  --output-model-path workspace/models/cost_estimation/latest.json
```
3. Verify artifact exists and health endpoint reports `loaded=true`.

## Phase C: Backend + frontend startup
1. Backend:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
2. Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Phase D: Smoke run
Execute in order:
1. Overview page health refresh.
2. Workflow chat cost NL query.
3. Cost-estimation single + batch prediction.
4. Documents upload + stats/log check.
5. Data analysis upload + analysis + visualization fetch.
6. Demo mode toggle and scripted replay query.

## Phase E: Gate-level quick regression
Run existing gates:
```bash
make test-demo-mode-gate
make test-cost-estimation-gate
```
Optional full gate:
```bash
make test-release-gate
```

---

## 7. Pass/Fail Criteria

Pass when all are true:
1. All three health endpoints return `status=ok`.
2. Workflow NL query returns a valid response and trace metadata.
3. Cost model is loaded and both single/batch prediction succeed.
4. Data upload -> analysis -> visualization chain completes without manual patching.
5. Frontend MVP core pages execute one real action each.
6. Demo mode switch works and scripted replay returns deterministic response.

Fail if any P0 blocker remains.

---

## 8. Recommended Next Implementation Batch

1. Re-introduce or commit a canonical demo training CSV into an allowed tracked path (or provide a deterministic data generation script for demo).
2. Add a dedicated one-command smoke script (e.g., `scripts/testing/run_demo_smoke.py`) and a Make target (`make test-demo-smoke`).
3. Align `.env.example`, README, and backend defaults into one canonical capstone profile.
4. Keep demo fallback plan explicit: `live_hybrid` primary, `local_safe` backup, `scripted_replay` emergency.
