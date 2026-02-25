# TDO RAG Random Benchmark (2026-02-20)

## Why this was added
- Existing RAG checks were mainly fixed-case smoke tests.
- They were not enough to detect:
  - retrieval drift on real indexed chunks
  - shallow/echoing answers in multi-turn sessions
  - citation/source grounding regressions

## New benchmark
- Script: `scripts/testing/run_rag_random_benchmark.py`
- Data source: random samples from `document_chunks` already stored in pgvector.
- Evaluation layers:
  - Retrieval quality (`semantic` / `hybrid` / `keyword`)
  - Workflow answer quality (`/api/v1/workflow/query`)
  - Multi-turn follow-up anti-echo behavior (same `session_id`)

## Metrics
- Retrieval:
  - `Hit@K`
  - `Recall@K`
  - `MRR`
  - `nDCG@K`
- Workflow:
  - `source_hit_rate`
  - `non_echo_rate`
  - `avg_keyword_coverage`
  - `avg_reference_overlap`
  - `follow_up_non_echo_rate`
  - `follow_up_source_hit_rate`

## Output
- JSON report: `logs/rag_random_benchmark_report.json`
- Includes:
  - sampled case set
  - per-case retrieval/workflow details
  - thresholds and `overall_pass`

## Command
```bash
.venv-regress/bin/python scripts/testing/run_rag_random_benchmark.py \
  --sample-size 30 \
  --top-k 8 \
  --route-mode local_only \
  --pretty \
  --output logs/rag_random_benchmark_report.json
```

## Latest sample run (small smoke)
- Run date: 2026-02-20
- Command: `--sample-size 6 --top-k 8`
- Result snapshot:
  - semantic: `hit@8=0.8333`, `mrr=0.75`
  - hybrid: `hit@8=1.0`, `mrr=0.8056`
  - keyword: `hit@8=1.0`, `mrr=0.9167`
  - workflow source hit: `1.0`
  - workflow non-echo: `1.0`
  - follow-up source hit: `0.8333`
  - overall pass: `true`

## Interpretation guide (root-cause triage)
- `keyword >> semantic`:
  - likely embedding/vector ranking issue (embedding model quality, vector index, chunk embedding distribution).
- `retrieval good but source_hit low`:
  - likely generation/prompt grounding issue (answer synthesis not using retrieved evidence).
- `follow_up_non_echo low`:
  - likely session/context carryover or prompt anti-echo instruction weakness.
- `follow_up_source_hit low`:
  - multi-turn context retained, but grounding continuity is unstable.
