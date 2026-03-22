# Industry AI Flow Frontend (MVP)

Next.js + TypeScript frontend for Capstone demo.

## Scope

This MVP focuses on:
- Workflow Chat (`/api/v1/workflow/query`)
- Cost Estimation (`/api/v1/cost-estimation/predict` + `/predict/batch`)
- Support floors: documents, data analysis, prompt snapshot, LLM cost policy

## Run Locally

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3123](http://localhost:3123).

## Backend Proxy

Frontend calls backend through `src/app/api/backend/[...path]/route.ts`.

Set backend URL via environment variable:

```bash
# frontend/.env.local
BACKEND_BASE_URL=http://127.0.0.1:8000
```

If omitted, proxy defaults to `http://127.0.0.1:8000`.

## Build Check

```bash
cd frontend
npm run lint
npm run build
```
