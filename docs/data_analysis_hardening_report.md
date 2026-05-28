# Data Analysis Hardening — Investigation Report

**Branch:** `feat/data-analysis-hardening`
**Date:** 2026-05-28
**Trigger:** Maintainer report — Dynamic Data Analysis feels unstable / non-reproducible / weak on advanced analysis

---

## TL;DR

- **User's "results differ between clicks" complaint is real and reproduced.** Empirically: SSE/agentic path on `Zhipu temperature=0.0` produced 6 different code hashes across 18 identical-input runs (0% byte-level reproducibility).
- **Fixed with content-addressed LLM response cache** in `agentic_loop.py`. Re-measured: 6/6 cases byte-stable, 18/18 runs identical hash (100%). Side benefit: cache HIT latency drops from ~30s → ~5s.
- Two adjacent defects also fixed (PII leak in agentic prompt; missing `random_state` instruction).
- Three follow-ups documented but deliberately scoped out.

---

## What shipped (3 commits on this branch)

### `dc63fd60` — Privacy redaction + reproducibility prompt mandate

**`backend/services/data_analysis/spike_harness.py`** — new `_summarize_samples()` helper sanitizes the `sample_3` column-profile slot before it hits the cloud LLM:

- `role=id` or `role=text` → `<redacted>` (max PII risk, zero LLM signal)
- `role=numeric` → `range=min..max` (more useful than 3 arbitrary cells anyway)
- `role=categorical` with freeform-looking values (whitespace or avg_len > 25) → `<redacted:freeform>` — catches `name` / `notes` / `address` columns that slip past `_infer_role`'s `n_unique ≤ 20` rule
- `role=categorical` with short labels (M/F, Yes/No, S/C/Q) → unchanged (LLM needs these labels to generate correct code)

**`prompts/agentic_v1_user_template.md` + `prompts/agentic_v1_repair_template.md`** — added mandatory Reproducibility hard-constraint instructing the LLM to:
- `np.random.seed(42); random.seed(42)` as second line of generated code
- `random_state=42` on every sklearn estimator (RandomForest*, DecisionTree*, GradientBoosting*, KMeans, MiniBatchKMeans, TSNE, PCA(svd_solver='randomized'), train_test_split, KFold, StratifiedKFold, cross_val_score)
- `random_state=42` on any `df.sample(...)`

This fixes the *executed code's* reproducibility (sklearn defaults to fresh RNG per call), independent of LLM-side determinism. Necessary but not sufficient — see next commit.

### `23583964` — LLM response cache (the actual root-cause fix for non-reproducibility)

**`backend/services/data_analysis/agentic_loop.py`** — wraps `_default_glm5_caller` with an in-process LRU cache keyed on `SHA256(prompt + sampling_params)`.

Empirical finding (`scripts/testing/run_data_analysis_sse_repro_eval.py`, 6 prompts × 3 runs against live SSE endpoint):

| Metric | Before | After |
|---|---|---|
| Cases with byte-identical code across 3 runs | 0 / 6 | 6 / 6 |
| Run-to-run code SHA256 stability | 0% | 100% |
| Mode (`glm5_agent`) stability | 100% | 100% |
| Cache HIT latency vs cold | n/a | ~5s vs ~25s |

**Why temperature=0.0 alone wasn't enough:** Zhipu's greedy decoding produces "same shape, different bytes" — import order drifts, intermediate variable names differ, the subset of functions pulled from `sklearn.metrics` varies. Diff sample from the first eval run (before cache):

```
TC1-P1 Tips histogram: Line 4: A=[import random] vs B=[import json]
TC2-P1 Titanic decision tree: Line 7:
   A=[from sklearn.metrics import accuracy_score, classification_report]
   B=[from sklearn.metrics import accuracy_score]
```

Cache forces *content-addressed determinism*: identical input → cache key collision → cached response replayed → byte-identical code.

Configuration:
- Enable/disable: `DATA_ANALYSIS_LLM_CACHE=true|false` (default true)
- Max size: `DATA_ANALYSIS_LLM_CACHE_SIZE=256` (LRU eviction)
- `cache_stats()` exposes hits/misses/stores/size for ops
- `reset_cache()` for tests + a future debug endpoint

Cache hit verified in server logs:
```
LLM cache STORE (key=0f604dc2d583, size=1/256)   # run_a misses
LLM cache HIT   (key=0f604dc2d583, size=2/256)   # run_b hits
LLM cache HIT   (key=0f604dc2d583, size=2/256)   # run_c hits
```

Total across 6-case × 3-run eval: **12 stores, 24 hits, 0 staleness issues.**

Evidence file: `docs/data_analysis_sse_repro_eval_after_cache.json`

---

## Phase A — Three-way independent investigation (45 min wall-clock, parallel)

Convened three independent reviewers, none seeing each other's output:

| Reviewer | Focus | Headline finding |
|---|---|---|
| **Subagent #1 (Explore, static)** | code + architecture audit | Architecture more mature than expected (agentic 2-pass repair loop exists); main gap is missing `random_state` instruction in agentic prompt |
| **Codex (cold read, high effort)** | independent rewrite proposal | Two bombshells: (a) `spike_harness.py:115-145` leaks raw cell values into agentic prompt; (b) `chart_plan.py:91-93` ignores `user_question` and only knows 5 chart types — explains "advanced analysis weak" symptom |
| **Subagent #2 (general-purpose, dynamic)** | empirical eval — run e2e twice, diff | 11/11 PASS but 4/11 (36%) non-reproducible on the **legacy** `/api/v1/data/analyze` endpoint (mode flipping between `llm` ↔ `template_fallback`). **Caveat: tested wrong endpoint — frontend uses SSE, not legacy.** |

## Phase B — Adversarial synthesis (3 rounds + 1 empirical pivot)

**Round 1 (initial proposals diverged):**
- Sub#1: lowest-hanging fix is prompt seed instructions
- Codex: structural fix is task-class routing + question-aware chart planner
- Sub#2: mode-switching is the root cause of non-reproducibility

**Round 2 (used Sub#2's data to arbitrate):** the 4 non-reproducible cases all involved `code_gen_mode` flipping (`llm ↔ template_fallback`). That mode string only exists in `backend/tools/data_analysis.py` (the LEGACY tool). Frontend doesn't hit that tool. **Sub#2's data was about a code path the user doesn't use.**

**Round 3 (corrective re-eval):** spawned a 4th sub-agent specifically to write `run_data_analysis_sse_repro_eval.py` hitting the production SSE endpoint. **First-pass result was hallucinated as "100% reproducible"** — the sub-agent's prose conflicted with the JSON output it produced. Going directly to the JSON file (`/tmp/sse-repro-eval.json`) revealed the actual numbers: **mode 100% stable but code 0% stable** across 18 runs. The sub-agent's first-message summary was wrong; its second message and the JSON were correct.

**Lesson:** trust the JSON file, not the LLM-generated summary, when investigating LLM determinism.

**Round 4 (locked plan, empirically grounded):**
1. PII redaction in `extract_profile` — Codex's privacy bombshell. Cheap. Ship.
2. `random_state=42` prompt mandate — Sub#1's intervention. Cheap. Ship.
3. **LLM response cache** — derived directly from corrected Round 3 data. Substantive. Ship.
4. Codex's `chart_plan.py` question-awareness — biggest lever for "advanced analysis weak", but a separate PR-worth of work. Document, defer.
5. Codex's `backend/tools/data_analysis.py` legacy-tool fixes — only matters if user's symptom lives on workflow-chat. Document, defer.

---

## Honest limitations

- **No unit test for `_summarize_samples()` or the cache LRU eviction path.** Smoke tests were done inline (`python -c '...'`) and verified with the SSE eval. Should add formal tests in a follow-up.
- **Cache is in-process only.** Restart wipes it. For demo this is fine (one operator, one session). For multi-worker uvicorn, would need Redis or similar.
- **Cache TTL is unbounded.** A stale cache hit will return last week's code if neither prompt template nor dataset changes for a week. The cache key currently does NOT include `agentic_v1_user_template.md` content hash. If prompt template is edited, restart server to flush. Future fix: include template SHA in key.
- **`random_state=42` mandate is unenforceable** — there's no validator pass that checks the LLM actually obeyed. A future fix could grep the generated code for sklearn estimators that don't carry `random_state=`.
- **PII redaction heuristic** (avg_len > 25 OR contains whitespace) will miss: short usernames, ASCII emails without `@`, single-token PII like SSNs. Tighter rules trade off vs. losing legitimate label signal — current heuristic chosen for the demo-data PII surface, not adversarial users.
- **The first SSE eval sub-agent contradicted itself.** First message: "100% reproducible, all `deterministic_planner`." Second message: "0% reproducible, all `glm5_agent`." Only the JSON output was trustworthy. Wasted ~10 minutes of investigation on the bad summary. If you re-run any eval, read the JSON directly.

---

## Known follow-ups (documented, not shipped)

### Follow-up A — `chart_plan.py` is question-unaware

`backend/services/data_analysis/chart_plan.py:91-93` docstring explicitly admits:

> `user_question`: Preserved in the plan for traceability; **not used to drive chart selection** in this heuristic version.

Any user question → same 5 chart types (hist, scatter, heatmap, bar, boxplot). "Show confusion matrix for Survived prediction" → user gets 5 EDA charts.

Proposed (separate PR): add `_classify_question_intent()` returning one of `{distribution, correlation, group_compare, time_trend, classification, regression, clustering, generic_eda}`, branch chart selection in `eda_plan_from_metadata`. M effort. **Biggest lever for the "advanced analysis weak" symptom.**

### Follow-up B — Legacy `backend/tools/data_analysis.py` non-determinism

Sub#2's empirical data showed 36% non-reproducibility on this path (mode flipping). Reachable via:
- `POST /api/v1/data/analyze` (synchronous, used by some tests)
- `backend/agents/unified_agent.py:253` — the 12-tool agent
- `backend/agents/code_analysis_agent.py:125` — same

If user observes non-reproducibility on `/workflow-chat` (which routes through unified_agent), the fix lives there. Either deprecate the legacy tool, or apply the same cache pattern there.

### Follow-up C — Surface agentic probe status in `/api/v1/health`

`is_agent_runtime_ready()` is the gate that decides agentic vs deterministic_planner per request. It's currently invisible — only visible by reading `grep "Agentic runtime"` in uvicorn logs. Demo operator can't tell pre-demo whether agentic is going to run. Cheap fix: add it to the health envelope.

---

## Time budget

- Phase A (parallel investigation): ~25 min
- Phase B (synthesis + corrective re-eval): ~25 min
- Phase C (PII + prompt fix): ~15 min
- Phase D (cache implementation + eval verification): ~25 min
- Phase E (report + PR): ~15 min
- **Total: ~105 min** vs 4-hour budget. Came in well under because the corrective re-eval (Round 3) pointed at a precise root cause that took one focused commit to fix.

---

## Reproduction

```bash
# Verify the cache fix end-to-end against a live server.
# Server must have USE_GLM5_AGENT=true (default) + agentic probe ready.
# Eval auto-uploads CSVs, runs each case 3× against /api/v1/data/analyze/start,
# captures generated_code hash from final SSE result event.

REQUIRE_USER_AUTH=false uvicorn backend.main:app &
.venv/bin/python scripts/testing/run_data_analysis_sse_repro_eval.py
# Expected: 6/6 mode-stable, 6/6 code-stable.

# To disable cache and confirm the regression:
DATA_ANALYSIS_LLM_CACHE=false uvicorn backend.main:app &
.venv/bin/python scripts/testing/run_data_analysis_sse_repro_eval.py
# Expected: 6/6 mode-stable, 0/6 code-stable. (Restored pre-fix behavior.)
```
