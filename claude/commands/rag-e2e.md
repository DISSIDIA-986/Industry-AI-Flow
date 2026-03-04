---
description: Run RAG multi-turn E2E validation from vectorized docs (question generation + benchmark + agent-browser).
argument-hint: "[mode=smoke|full] [max_questions=<N>] [parallel=<N>] [nothink=on|off] [frontend_url=<URL>]"
allowed-tools: Bash, Read, Grep, Glob, LS, Write
---

Parse `$ARGUMENTS` with defaults:
- `mode=full`
- `max_questions=180`
- `parallel=2`
- `nothink=on`
- `frontend_url=http://localhost:3000`

Execution policy:
- If `mode=smoke`: set `max_questions=min(max_questions,30)` and `parallel=1`.
- Cap browser concurrency to `parallel<=2`.

If `nothink=on`, remind user to run `/set nothink` before execution for `ollama qwen3.5:9b`.

For long smoke/full runs, prefer stable backend process mode (avoid `--reload`) and set:
- `WORKFLOW_RUNNER_MODE=fallback`
- `DEMO_MODE=local_safe`
- `ENABLE_RAG_QUERY_REWRITE=false`
- `OLLAMA_REQUEST_TIMEOUT_SECONDS=20`

Run in order:

1. Generate question bank CSV.
```bash
.venv/bin/python scripts/testing/generate_rag_question_bank_csv.py \
  --output docs/testing/rag_question_bank_180.csv \
  --questions-per-doc 20 \
  --seed 20260303
```

2. Run backend retrieval/workflow benchmark.
```bash
.venv/bin/python scripts/testing/run_rag_random_benchmark.py \
  --sample-size ${max_questions} \
  --conversation-turns 5 \
  --sampling-mode stratified_source \
  --query-style-mode mixed_balanced \
  --route-mode local_only \
  --output logs/rag_random_benchmark_report_${max_questions}.json \
  --pretty
```

3. Run browser E2E (full-chain validation).
```bash
.venv/bin/python scripts/testing/run_rag_agent_browser_e2e.py \
  --frontend-url ${frontend_url} \
  --csv docs/testing/rag_question_bank_180.csv \
  --max-questions ${max_questions} \
  --login-email ${RAG_E2E_LOGIN_EMAIL:-demo@example.com} \
  --login-password ${RAG_E2E_LOGIN_PASSWORD:-demo123} \
  --output logs/rag_agent_browser_e2e_report_${max_questions}.json
```

4. Summarize results in `docs/testing/RAG_E2E_RUN_SUMMARY.md`.

The summary must include:
- pass/fail rates
- key latency metrics
- failures grouped by: retrieval, model, workflow/prompt, frontend rendering
- prioritized action list (P0/P1 first)
