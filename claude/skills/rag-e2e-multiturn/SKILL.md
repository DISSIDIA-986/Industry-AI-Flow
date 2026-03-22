---
name: rag-e2e-multiturn
description: Run reusable RAG end-to-end multi-turn validation from vectorized documents: generate 180-question CSV (20 per doc), execute browser-based workflow-chat checks with agent-browser, compute retrieval and conversation quality metrics, and produce triage-ready reports.
---

# RAG E2E Multi-Turn Skill

Use this skill when you need repeatable quality validation for the Industry-AI-Flow RAG workflow.

## Scope

- Source questions from currently vectorized documents in DB.
- Generate `9 x 20 = 180` questions by default.
- Cover understanding, summary, follow-up, reasoning, and multi-turn action prompts.
- Validate frontend + backend behavior via browser interaction (`agent-browser`).

## Inputs

- Optional runtime arguments (recommended through slash command):
  - `mode=smoke|full`
  - `max_questions=<N>`
  - `parallel=<N>`
  - `nothink=on|off`
  - `frontend_url=<URL>` (default `http://localhost:3123`)
  - `RAG_E2E_LOGIN_EMAIL` / `RAG_E2E_LOGIN_PASSWORD` (override demo login)

## Core Workflow

1. Generate or refresh question bank CSV.

```bash
.venv/bin/python scripts/testing/generate_rag_question_bank_csv.py \
  --output docs/testing/rag_question_bank_180.csv \
  --questions-per-doc 20 \
  --seed 20260303
```

2. Run retrieval/workflow baseline benchmark.

```bash
.venv/bin/python scripts/testing/run_rag_random_benchmark.py \
  --sample-size 180 \
  --conversation-turns 5 \
  --sampling-mode stratified_source \
  --query-style-mode mixed_balanced \
  --route-mode local_only \
  --output logs/rag_random_benchmark_report_180.json \
  --pretty
```

3. Run browser E2E from CSV (required for full-chain validation).

```bash
.venv/bin/python scripts/testing/run_rag_agent_browser_e2e.py \
  --frontend-url http://localhost:3123 \
  --csv docs/testing/rag_question_bank_180.csv \
  --max-questions 180 \
  --login-email ${RAG_E2E_LOGIN_EMAIL:-demo@example.com} \
  --login-password ${RAG_E2E_LOGIN_PASSWORD:-demo123} \
  --output logs/rag_agent_browser_e2e_report.json
```

4. Write summary + triage conclusions.

- Primary artifacts:
  - `docs/testing/rag_question_bank_180.csv`
  - `logs/rag_random_benchmark_report_180.json`
  - `logs/rag_agent_browser_e2e_report.json`
- Recommended summary file:
  - `docs/testing/RAG_E2E_RUN_SUMMARY.md`

## Coverage Checklist

The run must explicitly evaluate:
- Retrieval flow
- Multi-turn dialogue behavior
- Intent recognition signal
- Query rewrite path
- Session/context continuity
- Frontend rendering correctness
- Exception/fallback handling

## Execution Strategy

- `smoke`: serial, low-cost (`max_questions=30`, `parallel=1`).
- `full`: limited parallel (`parallel=2` browser sessions max, avoid local model saturation).
- If host resource pressure appears, force serial rerun.
- For long runs, start backend in stable non-reload profile:
  - `WORKFLOW_RUNNER_MODE=fallback`
  - `DEMO_MODE=local_safe`
  - `ENABLE_RAG_QUERY_REWRITE=false`
  - `OLLAMA_REQUEST_TIMEOUT_SECONDS=20`

## Model Mode Guidance (ollama qwen3.5:9b)

- Functional regression runs: prefer `/set nothink` for speed and throughput.
- Quality deep-dive runs: optional think mode on a small subset only.
- Do not compare performance metrics across think/nothink modes without labeling.

## Output Contract

Always produce:
1. Success/failure summary with counts and rates.
2. Latency summary (TTFB proxy, total render time, p50/p95 where available).
3. Failure classification:
   - model generation
   - retrieval grounding
   - prompt/workflow orchestration
   - frontend rendering/interaction
4. Next-step fix list sorted by severity (P0/P1 first).
