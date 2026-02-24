# TDO RAG Query Rewrite + Intent Runtime Upgrade (2026-02-20)

## Scope
- Improve retrieval robustness for noisy/random user phrasing.
- Remove dependence on simulated intent-classification response path.

## Changes

### 1) Intent classifier now prefers real model inference
- File: `backend/services/intent_classification/intent_classifier.py`
- Key updates:
  - skip prompt fetch when `prompt_manager` is unavailable (avoid null-call noise)
  - use `llm_client.generate(...)` as primary classification path
  - fallback to heuristic simulator only when model call fails/empty
  - normalize alias intent labels (for example `"knowledge retrieval"` -> `knowledge_retrieval`)
  - replaced weak request template with strict JSON output contract prompt

### 2) RAG retrieval query rewrite + fusion
- File: `backend/services/intent_classification/intent_workflow.py`
- Key updates:
  - generate retrieval rewrites (JSON only) before retrieval
  - run retrieval on original query + rewrites
  - fuse multi-query retrieval results with weighted RRF
  - preserve reranker stage on fused candidates
  - expose metadata:
    - `retrieval_queries`
    - `retrieval_query_count`
    - `query_rewrite_used`

### 3) Config toggles
- File: `backend/config.py`
- New settings:
  - `ENABLE_RAG_QUERY_REWRITE` (default `true`)
  - `RAG_QUERY_REWRITE_COUNT` (default `1`)

## Tests

- New: `tests/unit/test_intent_classifier_runtime.py`
  - LLM-first classification path
  - fallback classification when LLM call fails
  - alias intent normalization

- Updated: `tests/unit/test_intent_workflow_dispatch_runtime.py`
  - verify rewrite path triggers additional retrieval query
  - verify metadata reports rewrite usage and retrieval-query count

## Validation executed
- `python3 -m py_compile backend/services/intent_classification/intent_classifier.py backend/services/intent_classification/intent_workflow.py tests/unit/test_intent_classifier_runtime.py tests/unit/test_intent_workflow_dispatch_runtime.py`
- `.venv-regress/bin/pytest -q tests/unit/test_intent_classifier_runtime.py tests/unit/test_intent_workflow_dispatch_runtime.py tests/unit/test_workflow_query_routes.py`
  - result: `15 passed`
- `.venv-regress/bin/python scripts/testing/run_rag_random_benchmark.py --sample-size 6 --top-k 8 --pretty --output logs/rag_random_benchmark_report.json`
  - result: `overall_pass=true`
- `.venv-regress/bin/python scripts/testing/run_rag_random_benchmark.py --sample-size 30 --top-k 8 --route-mode local_only --pretty --output logs/rag_random_benchmark_report.json`
  - semantic: `hit@8=0.9333`, `mrr=0.8108`
  - hybrid: `hit@8=1.0`, `mrr=0.8444`
  - keyword: `hit@8=1.0`, `mrr=0.9667`
  - follow-up source hit: `0.9667`
  - overall: `true`

## Note
- `tests/evaluation/ragas_evaluation.py` is still a placeholder-style implementation and should be replaced with a true runtime RAGAS pipeline for objective faithfulness/relevancy tracking.
