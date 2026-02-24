# TDO RAG Workflow Validation (2026-02-20)

## Scope
- Target: workflow-chat RAG quality related changes (document profile context + follow-up suggestions) and affected regression surfaces.
- Focused layers:
  - Backend unit tests (workflow dispatch, query routes, intent runtime, profile service, benchmark scripts).
  - Backend integration tests (RAG baseline paths, workflow prompt preparation, workflow query path).
  - Frontend unit/integration tests (workflow API contract + proxy contract).
  - Frontend E2E (core user journeys with workflow-chat and cost-estimation path).

## Test Suites and Commands
- Backend unit baseline:
  - `.venv_capstone/bin/python -m pytest -q -vv tests/unit/test_document_profile_service.py tests/unit/test_intent_workflow_dispatch_runtime.py tests/unit/test_workflow_query_routes.py tests/unit/test_intent_classifier_runtime.py tests/unit/test_run_rag_random_benchmark_script.py tests/unit/test_run_rag_factor_sweep_script.py tests/unit/test_main_runtime_contracts.py tests/unit/test_main_api_version_alias_routes.py --junitxml=logs/tdo/unit_rag_workflow.xml`
- Backend integration baseline:
  - `.venv_capstone/bin/python -m pytest -q -vv tests/integration/test_tdo_baseline_paths.py tests/integration/test_intent_workflow_prompt_preparation.py tests/integration/test_workflow_cost_estimation_query_api.py --junitxml=logs/tdo/integration_rag_workflow.xml`
- Frontend unit/integration:
  - `cd frontend && npx vitest run tests/unit/workflow-api.session.spec.ts tests/integration/api-proxy.contract.spec.ts --reporter=verbose`
- Frontend E2E:
  - `cd frontend && PW_FRONTEND_PORT=3100 npx playwright test tests/e2e/core-user-journeys.spec.ts`

## Results Summary
- Backend unit: 43 passed, 0 failed.
- Backend integration: 10 passed, 0 failed.
- Frontend vitest: 5 passed, 0 failed.
- Frontend E2E: 9 passed, 0 failed (after fixing one stale assertion/mocking mismatch).

## P0/P1 Findings
- P1: stale E2E mock path caused false failure in batch prediction journey.
  - Evidence: `frontend/tests/e2e/core-user-journeys.spec.ts` failed at batch result visibility.
  - Root cause: mocked route used legacy path `.../predict-batch`, while runtime client uses `.../predict/batch`.
  - Fix:
    - Updated mock path and response contract in `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/tests/e2e/utils/session.ts`.
    - Relaxed currency cell assertion to avoid hardcoding symbol variant in `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/tests/e2e/core-user-journeys.spec.ts`.

## Test Updates Applied
- `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/tests/e2e/core-user-journeys.spec.ts`
  - Added workflow-chat check for suggested follow-up questions display and click-to-fill behavior.
  - Updated batch prediction assertion to match current currency rendering.
- `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/tests/e2e/utils/session.ts`
  - Added `metadata.suggested_questions` in workflow query mock.
  - Corrected batch prediction mock route to `/api/v1/cost-estimation/predict/batch`.
  - Added `success`/`count` fields to match current API contract.

## Artifacts
- Backend unit log/xml:
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/unit_rag_workflow.log`
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/unit_rag_workflow.xml`
- Backend integration log/xml:
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/integration_rag_workflow.log`
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/integration_rag_workflow.xml`
- Frontend logs/reports:
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/frontend_vitest_rag_workflow.log`
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/frontend_e2e_core_user_journeys_port3100_rerun2.log`
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/junit-results.xml`
  - `/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/playwright-results.json`

## Pass Criteria
- All targeted suites pass.
- One known stale E2E failure source was eliminated with contract-aligned mocks and assertions.
- Workflow-chat follow-up suggestion UX now has explicit E2E coverage.

## Extended Gate and Benchmark (continued)

### Additional Commands
- Demo-mode gate:
  - `make test-demo-mode-gate`
- Randomized RAG benchmark (small control run):
  - `.venv_capstone/bin/python scripts/testing/run_rag_random_benchmark.py --sample-size 8 --seed 20260220 --top-k 4 --sampling-mode stratified_source --query-style-mode mixed_balanced --conversation-turns 2 --workflow-transport http --base-url http://127.0.0.1:8000 --workflow-enable-query-rewrite false --timeout 20 --output logs/tdo/rag_random_benchmark_http_2026-02-20.json --pretty`
- Factor sweep (focused grid):
  - `.venv_capstone/bin/python scripts/testing/run_rag_factor_sweep.py --sample-size 6 --seeds 20260220 --top-k-values 3,5 --hybrid-vector-weights 0.5,0.7 --workflow-query-rewrite-counts 1,3 --conversation-turn-values 1,2 --sampling-mode stratified_source --query-style-mode mixed_balanced --workflow-transport http --base-url http://127.0.0.1:8000 --timeout 20 --output logs/tdo/rag_factor_sweep_http_2026-02-20.json --pretty`
- Randomized RAG benchmark (higher coverage run):
  - `.venv_capstone/bin/python scripts/testing/run_rag_random_benchmark.py --sample-size 30 --seed 20260220 --top-k 4 --sampling-mode stratified_source --query-style-mode mixed_balanced --conversation-turns 2 --workflow-transport http --base-url http://127.0.0.1:8000 --workflow-enable-query-rewrite false --timeout 20 --output logs/tdo/rag_random_benchmark_http_s30_2026-02-20.json --pretty`

### Extended Results Summary
- `make test-demo-mode-gate`: 29 passed, 0 failed.
- Random benchmark (`sample_size=8`):
  - `hybrid_retrieval_hit_at_k=0.75`, `hybrid_retrieval_mrr=0.3542`
  - `workflow_source_hit_rate=0.75`, `workflow_non_echo_rate=1.0`
  - `workflow_follow_up_source_hit_rate=0.25`, `workflow_follow_up_repeat_rate=0.0`
  - `overall_pass=false` (MRR and follow-up source-hit below threshold).
- Factor sweep (`16 runs`):
  - `best_objective_score=0.652607`
  - best factors: `top_k=3`, `hybrid_vector_weight=0.5`, `workflow_query_rewrite_count=1`, `conversation_turns=2`
  - strongest effect in this grid: `conversation_turns=2` (+0.016665 vs global mean), then `hybrid_vector_weight=0.5` (+0.012495).
- Random benchmark (`sample_size=30`, higher coverage):
  - `sampled_unique_sources=9`, query styles fully covered (`contextual|conversational|direct|noisy|telegraphic`)
  - `hybrid_retrieval_hit_at_k=0.6667` (threshold 0.75 not met)
  - `hybrid_retrieval_mrr=0.4111` (threshold 0.55 not met)
  - `workflow_source_hit_rate=0.7333` (threshold met)
  - `workflow_non_echo_rate=0.9667` (threshold met)
  - `workflow_follow_up_source_hit_rate=0.2333` (threshold 0.7 not met)
  - `workflow_follow_up_repeat_rate=0.0` (threshold met)
  - `overall_pass=false`

### Key Diagnosis from Benchmarks
- Primary gap is now retrieval ranking quality and follow-up source grounding, not query echo:
  - Multi-turn repetition risk appears controlled (`follow_up_repeat_rate=0.0`).
  - Follow-up answers frequently lose source alignment (`follow_up_source_hit_rate` low in both runs).
  - Retrieval ranking threshold is not met on broader coverage (`hit@k` and `MRR` below gate).
- Document-specific instability remains:
  - `ufgs_03_30_00_cast_in_place_concrete.pdf` is strong.
  - `gsa_core_building_training_2025-04-30.pdf` and `ufgs_toc.pdf` show weaker pass/source behavior in workflow evaluation.

### Additional Artifacts
- `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/demo_mode_gate_2026-02-20.log`
- `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/rag_random_benchmark_http_2026-02-20.log`
- `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/rag_random_benchmark_http_2026-02-20.json`
- `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/rag_factor_sweep_http_2026-02-20.log`
- `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/rag_factor_sweep_http_2026-02-20.json`
- `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/rag_random_benchmark_http_s30_2026-02-20.log`
- `/Users/openclaw/Documents/github.com/Industry-AI-Flow/logs/tdo/rag_random_benchmark_http_s30_2026-02-20.json`
