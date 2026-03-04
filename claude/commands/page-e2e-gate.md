---
description: Run screenshot-first page result-driven E2E gate for data_dashboard, cost_estimation, or rag.
argument-hint: "[module=data_dashboard|cost_estimation|rag] [cycles=<N>] [frontend_url=<URL>] [repair='<shell command>'] [rag_questions=<N>]"
allowed-tools: Bash, Read, Grep, Glob, LS, Write
---

Parse `$ARGUMENTS` with defaults:

- `module=data_dashboard`
- `cycles=1`
- `frontend_url=http://127.0.0.1:3001`
- `repair=` (empty, optional)
- `rag_questions=30`

Execution command:

```bash
python3 scripts/testing/run_page_result_driven_gate.py \
  --module ${module} \
  --frontend-url ${frontend_url} \
  --login-email ${RAG_E2E_LOGIN_EMAIL:-demo@example.com} \
  --login-password ${RAG_E2E_LOGIN_PASSWORD:-demo123} \
  --max-cycles ${cycles} \
  --rag-max-questions ${rag_questions} \
  ${repair:+--repair-command "${repair}"}
```

After execution, read and summarize:

- `gate_report=<path>` from command output
- latest cycle report details
- unresolved failures (P0/P1 first)
- screenshot/report artifact paths for presentation usage
