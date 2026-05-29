# Dynamic Data Analysis — Advanced-ML Adversarial Review

**Date:** 2026-05-29
**Scope:** Can the Dynamic Data Analysis pipeline do *advanced* ML (supervised / unsupervised / RL), beyond EDA? Where should the "do advanced analysis?" decision live, and is it latency-safe and honest enough for the Capstone demo?
**Method:** four independent evidence sources — (1) capability map of the code, (2) agentic-path verification, (3) dataset/RL paradigm research, (4) Codex adversarial static review — cross-checked against **live empirical probes** (11 ML instructions run through the real backend on the demo config: E2B + GLM agentic path) and **validator unit-probes**.

---

## 1. Headline

The pipeline is already a capable ML platform, not just EDA. Supervised (multiclass / imbalanced / regression), unsupervised (KMeans+silhouette / PCA / DBSCAN), anomaly detection (IsolationForest) and time-series (ARIMA) **all run end-to-end on the demo config**. The risk is **governance, not capability**: heavy analysis can hang for 120s and return *nothing recoverable*, capability downgrades happen *silently*, and the "should we do advanced analysis?" decision is made implicitly by the LLM with no latency awareness.

The user's instinct — make advanced analysis a metadata-driven, latency-aware, autonomous decision — is correct. But the proposed locus (the Intent Classifier) is wrong, and the decision already exists in two weak forms.

---

## Implementation status (2026-05-29, enterprise-prioritized)

Shipped + verified this pass (security & honesty first — an enterprise user cannot tolerate confidently-wrong output or data exfiltration):

- ✅ **P1 validator I/O hardening** (`validator.py::_validate_io_safety`): alias-resistant blocks for `numpy.load`/`fromfile`, `scipy.io.loadmat/savemat`, `sklearn.datasets.fetch_*`; path/URL args to readers + `savefig` constrained to `/workspace` or relative (no URLs, no abs-path escape). Verified: 8 gadget snippets blocked, 8 legit generated-code shapes still allowed, **capability E2E unchanged at 8/8** (no regression). Tests: `tests/unit/test_data_analysis_ml_contracts.py::TestValidatorMlGadgets` + `TestValidatorAllowsLegitMl`.
- ✅ **P1 whitelist honesty**: `xgboost`/`lightgbm` removed from `WHITELISTED_IMPORTS` (not installed in E2B → previously silent sklearn substitution). Now fail-fast; sklearn `GradientBoosting*` preserves the capability. Test: `TestLibraryAvailabilityContract`.
- ✅ **P2 honesty label**: hardcoded "Docker Sandbox" → "Sandboxed Execution" (actual provider is E2B) in `data-analysis` hero, `overview` card, and this CLAUDE.md doc.

Phase 2 (reliability + honesty), shipped + verified:

- ✅ **P1 durable result-by-`job_id`**: the SSE stream no longer *pops* the result (was consumed on first read, so a dropped connection lost it permanently). New auth-exempt `GET /api/v1/data/analyze/result/{job_id}` returns `{status: done|running, result}`; the frontend recovers via this endpoint (polls ~120s) when the SSE drops instead of showing "Connection lost". Directly fixes the empirical GridSearch "120s → nothing" failure. Verified: running→done→durable (repeat-fetch), 404 for unknown, SSE happy-path unchanged. `backend/main.py`, `dependencies.py`, `frontend/src/lib/api-client.ts::fetchDataAnalysisResult`, `data-analysis/page.tsx`.
- ✅ **P1 repair/downgrade disclosure**: the response envelope already carried `repair_triggered`/`repair_trigger_type`/`repair_recovered`; the UI now renders a `repair-notice` ("results are from an automatically repaired attempt, which may use a different method/library than requested") — closes the silent xgboost→sklearn substitution. Reliably triggers (verified: xgboost probe → `repair_triggered=true`).
- ◐ **P2 unanswerable surface (partial)**: when the model uses the structured `status="unanswerable"` path, the UI now shows a `unanswerable-banner` instead of green "Analysis Complete". **Known limitation**: for RL prompts the model often *prose-refuses* (`success=true`, `fallback_reason=None`, 0 charts) without the structured status, so that path is still shown as success. A deterministic RL guard (detect RL intent on the instruction + static-tabular data → structured refusal before the LLM call) is the robust fix — deferred.

Deferred to a follow-up (architectural, higher regression risk — sequenced in §7): compute guard + hard wall clock, deterministic RL refusal guard, reproducibility AST enforcement, and the latency-aware tier planner.

---

## 2. Architecture reality (corrects the "Intent Classifier should decide" framing)

The Intent Classifier (11-node `intent_workflow`) is a **query router** (RAG vs code-exec vs cost-estimation). It does **not** see dataset metadata and is **not** on the data-analysis path — the page calls `/api/v1/data/analyze/*` directly. Putting dataset-metadata decisioning there is an architectural mismatch.

The "do advanced analysis?" decision already exists, twice, both weak:

| Form | Location | State | Weakness |
|---|---|---|---|
| Deterministic metadata gate `decide_model_comparison()` | `backend/services/data_analysis/analysis_planner.py` | **Dormant** — only the fallback (non-agentic) path uses it | Not latency-aware; target column via keyword/last-column heuristic |
| LLM soft judgment (CRISP-DM) | `prompts/agentic_v1_system.md:4` ("Skip modeling if <2 numeric columns or no target column") | **Active** | Driven by the user's question text; non-deterministic; uncontrollable |

In the demo config (`USE_GLM5_AGENT=true`), `data_analysis_agent.py:157` makes the **agentic path own the response and return immediately**, so `decide_model_comparison` never runs. Net: advanced analysis is gated only by the user's wording + the LLM's soft judgment. Neither is latency-aware.

---

## 3. Empirical probe results (live backend, E2B, agentic)

11 ML instructions via `/api/v1/data/analyze/start` + SSE. Harness: `scripts/testing/run_data_analysis_ml_e2e.py`.

| Probe | Dataset | success | charts | final libs | wall | note |
|---|---|---|---|---|---|---|
| supervised multiclass (macro-F1, confusion) | penguins | ✅ | 1 | sklearn | 21s | |
| supervised imbalanced (PR-AUC, PR curve) | titanic | ✅ | 1 | sklearn | 16s | |
| regression mixed (one-hot, R²/RMSE) | mpg | ✅ | 1 | sklearn | 15s | |
| clustering + silhouette + choose k | penguins | ✅ | 1 | sklearn | 16s | |
| PCA + explained variance | penguins | ✅ | 1 | sklearn | 14s | |
| DBSCAN density clusters | penguins | ✅ | 1 | sklearn | 16s | |
| anomaly (IsolationForest) | synthetic | ✅ | 1 | sklearn | 15s | |
| time-series ARIMA forecast | airline | ✅ | 1 | statsmodels | 15s | bootstrap worked |
| **ADV xgboost (explicit)** | titanic | ✅ | 1 | **sklearn** | 27s | rounds=2, repair=True → xgboost failed at runtime, repaired to sklearn. **Silent substitution.** |
| **ADV GridSearchCV (large grid, 5-fold)** | titanic | **None / False** | 0 | — | **~120-129s** | Hits budget; outcome is non-deterministic across runs (`success=None` with no result event, or `success=False` with an empty payload). Either way: no usable result after ~2min. No compute guard. |
| **ADV reinforcement learning (Q-learning)** | construction | ✅ | 0 | — | 3.5s | LLM declined honestly ("static historical data … no state transitions"), but reported as `success=true`. |

---

## 4. Confirmed risks (Codex static review + empirical + validator probe)

Priority = Capstone-demo risk.

### P1 — Heavy analysis hangs 120s with no recoverable result
- Empirical: GridSearch → `success=None`, 120s, zero result.
- Codex: the "120s total budget" is **advisory, not a hard wall** — round-2 sandbox budget is derived from remaining time while the outer wait adds `BOOTSTRAP_BUDGET_S + 5` on top (`agentic_loop.py:537-546`, `904-919`). There's a graceful `time_budget_exhausted` envelope (`agentic_envelope.py:349-352`) **only if control returns**.
- No compute guard anywhere for `GridSearchCV` / large CV / param grids (only a `range > 1_000_000` warning, `validator.py:612-633`).
- **SSE disconnect is terminal**: `tracker.close()` deletes the tracker (`main.py:1783-1784`, `progress_tracker.py:153-159`); there is **no `job_id` result-fetch endpoint**, so a dropped stream loses the result permanently (`page.tsx:290-298`). (This compounds the SSE last-event-drop bug fixed separately in `main.py` stream flush.)

### P1 — xgboost/lightgbm: whitelisted but uninstalled → silent sklearn substitution
- Whitelisted (`validator.py:72-98`) but only `statsmodels` is bootstrapped (`agentic_loop.py:77-83`; `sandbox_runtime.py:36-37`). Runtime readiness never checks xgboost/lightgbm despite "keep prompt/validator/runtime aligned" comments.
- The repair prompt explicitly tells the model the sandbox only has sklearn/scipy/statsmodels (`agentic_v1_repair_template.md:29-35`), so a runtime `ModuleNotFoundError` naturally becomes an sklearn rewrite.
- `fallback_reason` is only set on *failure* (`agentic_envelope.py:369-376`) and the frontend ignores `repair_triggered` (`page.tsx:749-755`) → **the user asks for XGBoost feature importances and silently gets a sklearn model.**

### P1 — Validator is name-based and trivially bypassed (defense-in-depth gap)
Empirically verified (`tests/unit/test_data_analysis_ml_contracts.py::TestValidatorMlGadgets`):

| Snippet | Expected | Actual |
|---|---|---|
| `pd.read_csv('https://evil/x.csv')` | block | **PASS** (SSRF/exfil) |
| `pd.read_csv('/etc/hosts')` | block | **PASS** (local read) |
| `np.fromfile('/etc/passwd')` | block | **PASS** |
| `from numpy import load as L; L(...)` | block | **PASS** (aliasing bypasses `np.load` block) |
| `sklearn.datasets.fetch_openml(...)` | block | **PASS** (network) |
| `scipy.io.loadmat(...)` | block | **PASS** (deserialization) |
| `plt.savefig('/tmp/evil.png')` | workspace-only | **PASS** (arbitrary write) |
| `np.load(...)` direct / `import pickle` | block | BLOCK ✓ |

The E2B sandbox is the real boundary (operator's own datasets, ephemeral), so demo blast radius is low — but the validator docstring claims filesystem/network prevention (`validator.py:4-9`) it does not deliver.

### P2 — Honesty / silent downgrade (Capstone is graded on sound, honest technical decisions)
- Repaired runs don't disclose the downgrade; RL refusal is surfaced as `success=true` + "Analysis Complete" (`page.tsx:694-700`, `862-868`).
- Bonus: the UI hardcodes **"Docker Sandbox"** while the actual provider is E2B (`page.tsx:451-456`).

### P2 — Reproducibility is prompt-hope, not enforced
- Prompt mandates `np.random.seed(42)` / `random.seed(42)` / `random_state=42`, but nothing in `validator.py` enforces it. The backend added an LLM response cache *because output wasn't byte-stable even at temperature 0* (`agentic_loop.py:651-669`) → determinism depends on cache hits + prompt obedience. The deterministic `model_comparison` path *is* seeded correctly.

### P2 — RL guard depends on LLM judgment (non-deterministic)
- No explicit guard. The only mechanism is the prompt's `status="unanswerable"` option. A stronger prompt could make the model attempt manual numpy/sklearn Q-learning (not blocked). RL is a paradigm mismatch with static tabular data — worth a deterministic refusal, surfaced as refusal not success.

### P2 — Cold-sandbox timeout misclassification
- `run_sandbox()` times the full lifecycle (create/bootstrap/upload) against the *user-code* budget (`agentic_loop.py:551-552` vs `222-225`), so a cold sandbox can be marked timed-out even when user code stayed within 30s.

### P3 — Test coverage gap
- Only a smoke gate (`tests/integration/test_data_analysis_runtime_gate.py`); agentic tests are mocked; model tests mock executor output rather than real training.

---

## 5. Recommended design — latency-aware "analysis-tier planner" (decisions locked 2026-05-29)

**Locus:** activate + upgrade the dormant `decide_model_comparison()` into a deterministic **analysis-tier planner** that runs after metadata extraction and *before* the agentic call. Not the Intent Classifier; not the LLM.

**Posture:** EDA always runs (fast, ~15s). Advanced is decided from metadata, **auto only when cheap**:

```
tier = plan_advanced(metadata):
  estimate cost ≈ f(rows, n_cols, candidate_models, CV_folds)
  if no recognizable target OR <2 numeric cols     -> skip
  elif estimated_cost <= LIGHT_BUDGET              -> light   (single model, no CV)   [auto]
  elif user explicitly asked for heavy modeling    -> full    (model_comparison)       [+ hard compute guard]
  else                                             -> skip (offer "run full analysis" button)
```

The tier becomes a **hard constraint written into the agentic prompt** (it *overrides* the LLM's CRISP-DM free choice — one source of truth, reproducible).

**Seamless page integration:** EDA renders first (progressive enhancement). Advanced renders as one "Advanced Analysis" card with three honest states:
- ✅ `ran` — model + metrics + why-this-model
- ⏭️ `skipped` — **explicit reason** ("120k rows, exceeds live-training cap" / "no recognizable target") — this turns today's silent downgrade into honest disclosure (Capstone plus)
- ⚠️ `descoped` — ("large GridSearch requested; auto-simplified to single 5-fold for responsiveness")

This single design also closes the P1 compute-guard, the durable-result need, and the P2 disclosure gap.

### Adversarial review of *this* design (integration traps)
1. Cost estimation will be imprecise → use a conservative upper bound + a **true request-level hard wall clock** as backstop; on overrun return partial result (EDA + "advanced timed out"), never zero.
2. Keep it **one LLM call** with tier-conditioned prompt; do *not* split EDA/advanced into two SSE passes (doubles latency/complexity).
3. The deterministic tier must **override** the LLM soft-skip, or the two logics contradict and reproducibility breaks.
4. Default to **auto only when cheap** (light tier); full/heavy stays explicit-request + guarded.
5. The keyword/last-column target heuristic is fragile → low-confidence target ⇒ `skip`, not garbage modeling.

---

## 6. Targeted test cases (delivered)

**Live capability E2E** — `scripts/testing/run_data_analysis_ml_e2e.py` (11 scenarios above; proves supervised/unsupervised/anomaly/time-series; flags the 3 adversarial ones).

**Contract tests** — `tests/unit/test_data_analysis_ml_contracts.py`:
1. `TestValidatorMlGadgets` — aliased `numpy.load`, `np.fromfile`, URL/abs-path `read_csv`, `sklearn.datasets.fetch_*`, `scipy.io.loadmat`, arbitrary `savefig`. *(Currently xfail — documents the P1 gadget gap.)*
2. `test_xgboost_request_disclosed` — xgboost asked → either real xgboost or a **disclosed** sklearn downgrade, never silent. *(xfail — P1.)*
3. `test_gridsearch_guarded_within_sla` — large GridSearch → de-scoped or timeout payload within SLA, SSE always emits a terminal payload. *(xfail — P1.)*
4. `test_rl_refusal_not_success` — static dataset + RL prompt → refusal status, not `success=true`. *(xfail — P2.)*
5. `test_seed_contract` — KMeans/IsolationForest/train_test_split → seed lines + `random_state=42` present; two runs byte-identical. *(xfail — P2.)*
6. `test_result_recoverable_by_job_id` — drop the SSE mid-run, refetch by `job_id`. *(xfail — P1, endpoint doesn't exist yet.)*

xfail markers carry the gap reason so the suite stays green while the gaps are tracked, TDI-style. Remove the marker as each fix lands.

---

## 7. Fix order (when implementation is greenlit)
1. **P1** hard request-level wall clock + compute guard (GridSearch/large CV auto-descope) + durable result-by-`job_id`.
2. **P1** remove xgboost/lightgbm from the agentic whitelist (fail-fast) *or* preinstall in E2B + live tests; disclose any downgrade.
3. **P1** validator: workspace-only paths, no URL inputs, alias-resistant blocks, block `np.fromfile`/`fetch_*`/`loadmat`/arbitrary `savefig`.
4. **Design** activate the latency-aware tier planner + three-state Advanced card.
5. **P2** RL refusal guard; reproducibility AST checks; surface requested-vs-actual lib + repair/downgrade in UI; fix "Docker Sandbox" label.
