# TDO Workflow Chat RAG Root Cause Report (2026-02-20)

## Scope
- Page: `workflow-chat`
- Focus:
  1. shallow/non-grounded answers
  2. multi-turn conversation degradation (question echo/repetition)
  3. QA coverage depth for RAG critical path

## P0/P1 Findings

### [P1] Multi-turn session continuity is broken by default
- Repro:
  1. Open workflow chat.
  2. Send turn-1 and turn-2 without explicitly passing session info.
- Evidence:
  - Frontend sent only `query` before fix; no `session_id/thread_id` persisted.
  - Backend created new session when `session_id` missing (`trace_id`-based fallback), so conversation context was reset each turn.
- Impact:
  - Context manager and interaction history cannot accumulate per conversation.
  - Multi-turn intent/routing quality drops and responses appear repetitive.

### [P1] Intent-workflow RAG dispatch returned extractive chunk stitching instead of grounded QA generation
- Repro:
  1. Ask knowledge-retrieval question.
  2. Observe response style and depth.
- Evidence:
  - RAG dispatch previously built a fixed "retrieved knowledge" chunk list and returned it directly.
  - User question was not answered by a generation step over retrieved context.
- Impact:
  - Answers look shallow, template-like, and weakly aligned to user intent.

### [P1] Source evidence was not exposed in top-level workflow response contract
- Repro:
  1. Ask query expecting citations.
  2. Frontend source panel stays empty.
- Evidence:
  - Frontend expected `payload.sources`.
  - Backend mainly stored source info under `metadata.agent_execution.sources`.
- Impact:
  - UI loses groundedness transparency.
  - QA cannot reliably assert citation presence from stable contract fields.

### [P1] Intent workflow initialization was brittle on prompt manager/db availability
- Repro:
  1. Trigger prompt manager/db init failure.
  2. Service falls back to lightweight orchestrator.
- Evidence:
  - `_initialize_workflow_service` previously hard-failed on DB/prompt manager init.
- Impact:
  - Runtime silently downgrades behavior and can produce lower quality fallback responses.

## Implemented Fixes

### 1) Session continuity fix (frontend + backend fallback)
- Frontend now generates and reuses stable workflow session/thread ids.
- Backend now resolves session id with priority:
  1. `session_id`
  2. `thread_id`
  3. `user:{user_id}`
  4. `trace_id`

### 2) RAG dispatch quality fix
- Intent workflow RAG dispatch now:
  - performs retrieval + rerank
  - builds grounded prompt with recent conversation history and retrieved chunks
  - calls local LLM generation (`rag.llm_client.generate`)
  - keeps extractive fallback only when generation fails

### 3) Source contract fix
- Workflow response now exposes normalized top-level `sources`.
- Frontend workflow API client now normalizes `sources` from either:
  - top-level payload
  - `metadata.agent_execution.sources`

### 4) Workflow init resilience
- Intent workflow init no longer hard-depends on prompt manager/db.
- Prompt manager is now optional with warning fallback, preventing unnecessary runner downgrade.

## Test Updates

### Added/updated tests
- Backend:
  - `tests/unit/test_intent_workflow_dispatch_runtime.py`
    - verifies RAG dispatch invokes LLM generation
    - verifies source metadata structure and generation mode
  - `tests/unit/test_workflow_query_routes.py`
    - verifies user-scoped session fallback when session id missing
    - verifies source normalization from `metadata.agent_execution`
- Frontend:
  - `frontend/tests/unit/workflow-api.session.spec.ts`
    - verifies request includes `session_id/thread_id/user_id`
    - verifies source normalization contract

## Validation Status
- Passed:
  - `cd frontend && npx vitest run tests/unit/workflow-api.session.spec.ts --reporter=verbose`
  - `cd frontend && npx tsc --noEmit --pretty false`
  - `python3 -m py_compile` on changed backend Python files
- Passed (backend targeted regression in isolated Python 3.13 env):
  - `uv venv .venv-regress --python 3.13`
  - `uv pip install --python .venv-regress/bin/python -r requirements/lock/py313-capstone.txt`
  - `.venv-regress/bin/pytest -q tests/unit/test_intent_workflow_dispatch_runtime.py tests/unit/test_workflow_query_routes.py`
  - Result: `11 passed`
- Remaining gap:
  - Direct `uv run --python 3.13 ...` still resolves from `pyproject.toml` and can be blocked by legacy OCR pins.

## Regression Plan (Independent)

### Coverage
- RAG pipeline correctness:
  - retrieval non-empty
  - grounded generation uses context
  - source contract available at top-level
- Conversation continuity:
  - same session across turns
  - user-scoped fallback behavior
- Degradation safety:
  - generation fallback path emits controlled answer

### Commands
```bash
# Frontend contract checks
cd frontend
npx vitest run tests/unit/workflow-api.session.spec.ts --reporter=verbose
npx tsc --noEmit --pretty false

# Backend targeted (isolated py3.13 env)
uv venv .venv-regress --python 3.13
uv pip install --python .venv-regress/bin/python -r requirements/lock/py313-capstone.txt
.venv-regress/bin/pytest -q \
  tests/unit/test_intent_workflow_dispatch_runtime.py \
  tests/unit/test_workflow_query_routes.py
```

### Acceptance Criteria
- Multi-turn requests keep stable session identity.
- RAG agent response is generation-based, not pure chunk echo.
- Top-level `sources` populated when retrieval has evidence.
- No regression in workflow query route contract (`trace_id/session_id/route_mode`).
