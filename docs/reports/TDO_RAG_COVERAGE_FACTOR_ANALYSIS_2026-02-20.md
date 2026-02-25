# TDO RAG Coverage & Factor Analysis (2026-02-20)

## Goal
- Increase benchmark coverage and diversity.
- Identify high-impact factors with measurable evidence.

## Coverage upgrades delivered
- Random benchmark now supports:
  - stratified source sampling (`random` / `stratified_source`)
  - mixed query-style generation (`direct/contextual/conversational/telegraphic/noisy`)
  - balanced/style-stress modes (`mixed_balanced`, `hard_focus`) to improve rare-style coverage
  - query difficulty labeling (`easy/medium/hard`) with distribution and group metrics
  - per-source and per-style pass-rate breakdown
  - per-difficulty pass-rate breakdown
  - configurable multi-turn depth (`conversation_turns`) for 2+ turn evaluation
  - follow-up repeat-rate detection (`follow_up_repeat_rate`) for "repeating user question" failures
  - ROUGE-L F1 proxy (`avg_rouge_l_f1`) for objective answer-vs-reference overlap
  - workflow transport mode (`http` / `direct_runner`)
  - workflow rate-limit mitigation (`workflow_request_interval_ms`)
- New factor sweep script:
  - `scripts/testing/run_rag_factor_sweep.py`
  - sweeps `top_k`, `hybrid_vector_weight`, `workflow_query_rewrite_count`, `conversation_turns`
  - outputs objective score and per-factor deltas

## High-coverage run (80 cases, stratified + mixed style)
- Command:
```bash
.venv-regress/bin/python scripts/testing/run_rag_random_benchmark.py \
  --sample-size 80 \
  --top-k 8 \
  --sampling-mode stratified_source \
  --query-style-mode mixed \
  --workflow-enable-query-rewrite true \
  --workflow-query-rewrite-count 1 \
  --workflow-request-interval-ms 80 \
  --pretty \
  --output logs/rag_random_benchmark_report.json
```
- Coverage:
  - sampled cases: 80
  - unique sources: 9
  - source distribution: near-uniform (8-9 per source)
  - query style distribution: contextual 23 / conversational 20 / direct 19 / telegraphic 18
- Key metrics:
  - hybrid retrieval: `hit@8=0.7875`, `mrr=0.5013` (below threshold)
  - workflow source hit: `0.6375` (below threshold)
  - follow-up source hit: `0.2` (below threshold)
  - non-echo rates stayed high (`1.0`)
- Failure concentration:
  - query style:
    - conversational retrieval hit rate: `0.6`
    - conversational workflow pass rate: `0.35`
  - source groups with weaker source-hit:
    - `gsa_core_building_training_2025_04_30`: `0.4444`
    - `ufgs_toc`: `0.4444`
    - `caltrans_2025_standard_specifications_digest`: `0.5`

## Factor sweep (stable matrix)
- Command:
```bash
.venv-regress/bin/python scripts/testing/run_rag_factor_sweep.py \
  --sample-size 16 \
  --seeds 20260220 \
  --top-k-values 4,12 \
  --hybrid-vector-weights 0.5,0.9 \
  --workflow-query-rewrite-counts 0,1 \
  --sampling-mode stratified_source \
  --query-style-mode mixed \
  --workflow-transport http \
  --workflow-request-interval-ms 500 \
  --pretty \
  --output logs/rag_factor_sweep_stable_report.json
```
- Result:
  - best factors: `top_k=12`, `hybrid_vector_weight=0.5`, `hybrid_bm25_weight=0.5`
  - factor deltas:
    - `top_k=12` outperformed `top_k=4` by `+0.028119` objective
    - `vector_weight=0.5` outperformed `0.9` by `+0.026064` objective
    - rewrite count (`0` vs `1`) showed no difference in this HTTP matrix

## Round-2 validation (multi-turn + objective overlap)
- Benchmark command:
```bash
.venv-regress/bin/python scripts/testing/run_rag_random_benchmark.py \
  --sample-size 24 \
  --top-k 8 \
  --sampling-mode stratified_source \
  --query-style-mode mixed \
  --conversation-turns 3 \
  --workflow-enable-query-rewrite true \
  --workflow-query-rewrite-count 1 \
  --workflow-request-interval-ms 120 \
  --timeout 60 \
  --pretty \
  --output logs/rag_random_benchmark_report_v2.json
```
- Key outputs:
  - style coverage includes `noisy`
  - difficulty coverage: `easy/medium/hard`
  - `workflow_follow_up_repeat_rate=0.0` (multi-turn no identical-repeat issue in this run)
  - `workflow_avg_rouge_l_f1=0.0858` (low grounding overlap, still a quality gap)
  - by-style workflow pass: `conversational=0.0` remained worst bucket
  - by-difficulty workflow pass: `medium=0.4444` remained weak bucket

## Round-2 factor sweep (conversation turns included)
- Command:
```bash
.venv-regress/bin/python scripts/testing/run_rag_factor_sweep.py \
  --sample-size 12 \
  --seeds 20260220 \
  --top-k-values 8,12 \
  --hybrid-vector-weights 0.5,0.9 \
  --workflow-query-rewrite-counts 0,1 \
  --conversation-turn-values 2,3 \
  --sampling-mode stratified_source \
  --query-style-mode mixed \
  --workflow-transport http \
  --workflow-request-interval-ms 300 \
  --timeout 60 \
  --pretty \
  --output logs/rag_factor_sweep_report_v2.json
```
- Result:
  - total runs: `16`, successful: `16`
  - best factors: `top_k=8`, `hybrid_vector_weight=0.5`, `workflow_query_rewrite_count=0`, `conversation_turns=3`
  - factor effects vs global mean:
    - `hybrid_vector_weight=0.5`: `+0.024681` (largest positive factor)
    - `top_k=12`: `+0.012238`
    - `conversation_turns=3`: `+0.006876`
    - rewrite count `0` vs `1`: near-neutral (`+0.002711`)

## Turn-depth micro A/B (2 vs 3 vs 4)
- Command:
```bash
.venv-regress/bin/python scripts/testing/run_rag_factor_sweep.py \
  --sample-size 10 \
  --seeds 20260220 \
  --top-k-values 8 \
  --hybrid-vector-weights 0.5 \
  --workflow-query-rewrite-counts 0 \
  --conversation-turn-values 2,3,4 \
  --sampling-mode stratified_source \
  --query-style-mode mixed_balanced \
  --workflow-transport http \
  --workflow-request-interval-ms 250 \
  --timeout 60 \
  --pretty \
  --output logs/rag_factor_sweep_turns_2_3_4.json
```
- Result:
  - turns=2: objective `0.542009`
  - turns=3: objective `0.547009` (best)
  - turns=4: objective `0.545339`
- Interpretation:
  - in current stack, 3 turns gives best quality/cost balance.
  - 4 turns does not improve objective further in this micro A/B.

## Round-2 targeted stress runs (style-isolated)
- Conversational-only:
```bash
.venv-regress/bin/python scripts/testing/run_rag_random_benchmark.py \
  --sample-size 24 \
  --top-k 8 \
  --sampling-mode stratified_source \
  --query-style-mode conversational \
  --conversation-turns 3 \
  --workflow-enable-query-rewrite true \
  --workflow-query-rewrite-count 1 \
  --workflow-request-interval-ms 120 \
  --timeout 60 \
  --pretty \
  --output logs/rag_random_benchmark_report_conversational.json
```
- Noisy-only:
```bash
.venv-regress/bin/python scripts/testing/run_rag_random_benchmark.py \
  --sample-size 24 \
  --top-k 8 \
  --sampling-mode stratified_source \
  --query-style-mode noisy \
  --conversation-turns 3 \
  --workflow-enable-query-rewrite true \
  --workflow-query-rewrite-count 1 \
  --workflow-request-interval-ms 120 \
  --timeout 60 \
  --pretty \
  --output logs/rag_random_benchmark_report_noisy.json
```
- Hard-focus mixed mode:
```bash
.venv-regress/bin/python scripts/testing/run_rag_random_benchmark.py \
  --sample-size 24 \
  --top-k 8 \
  --sampling-mode stratified_source \
  --query-style-mode hard_focus \
  --conversation-turns 3 \
  --workflow-enable-query-rewrite true \
  --workflow-query-rewrite-count 1 \
  --workflow-request-interval-ms 120 \
  --timeout 60 \
  --pretty \
  --output logs/rag_random_benchmark_report_hard_focus.json
```
- Stress comparison summary:
  - mixed: `workflow_source_hit=0.6667`, `workflow_pass=0.5`, `rouge_l=0.0858`
  - conversational-only: `workflow_source_hit=0.6667`, `workflow_pass=0.5833`, `rouge_l=0.078`
  - noisy-only: `workflow_source_hit=0.5417`, `workflow_pass=0.5417`, `rouge_l=0.0783`
  - hard-focus: `workflow_source_hit=0.625`, `workflow_pass=0.5833`, `rouge_l=0.0884`
- Coverage comparison:
  - mixed difficulty: `easy=5, medium=18, hard=1`
  - hard-focus difficulty: `medium=20, hard=4` (hard-case share improved)
- Interpretation:
  - noisy user-expression is currently the strongest degradation axis for source hit.
  - follow-up repeat remained `0.0` in all runs, so "multi-turn echo" was not reproduced in this batch.

## Important caveats observed
- `HTTP 429` remained in high-volume API runs (rate-limit noise).
- `direct_runner` large runs were degraded by local Ollama read timeouts.
- In current API contract, query-rewrite toggles are not explicitly exposed on workflow query request payload, so rewrite-factor isolation through HTTP is limited.

## Actionable conclusions
1. **Primary tuning direction (confirmed):**
   - Increase `top_k` toward 12.
   - Shift hybrid blend toward stronger BM25 (`vector_weight ~0.5`).
2. **Prompt/query robustness priority:**
   - noisy-style queries currently show the strongest source-hit degradation (`0.5417`).
   - add noisy/conversational rewrite prompts, typo normalization, and alias/abbreviation expansion.
3. **Answer grounding priority (new evidence):**
   - low `ROUGE-L` indicates answer detail often diverges from reference chunk phrasing.
   - optimize chunk granularity + citation-constrained generation prompt.
4. **Source-quality priority:**
   - focus chunking/metadata cleanup on low-performing sources:
     - `gsa_core_building_training_2025_04_30`
     - `ufgs_toc`
     - `caltrans_2025_standard_specifications_digest`
5. **Evaluation hygiene:**
   - run high-volume benchmark with either:
     - lower request concurrency + larger interval, or
     - direct non-HTTP evaluation path with stabilized local model runtime.
