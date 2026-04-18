# Agentic GLM-5 — W6 Spike Gate Rerun Decision Memo
Date: 2026-04-18
Source: `test_resources/benchmarks/agentic_glm5_20260418.jsonl`
Runner: `scripts/spike_agentic_glm5.py` (W6)
Loop: `backend/services/data_analysis/agentic_loop.py` (W2 bounded 2-pass)
Compares against: `spike_glm5_20260418_decision.md` (V1 single-shot, PARTIAL 7/10)

## Result
**7/10 passed (70%). Verdict: HOLD.**

Gate rule ≥9/10 not met → `USE_GLM5_AGENT` stays **false** for demo.

| Case | Family | Status | Rounds | Repair | Recovered | Elapsed | Fail |
|---|---|---|---|---|---|---|---|
| tips-Q1 | descriptive | ok | 1 | — | — | 5.6s | — |
| tips-Q2 | regression | ok | 1 | — | — | 8.3s | — |
| mpg-Q1 | correlation | ok | 1 | — | — | 13.4s | — |
| mpg-Q2 | regression | ok | 1 | — | — | 10.8s | — |
| penguins-Q1 | descriptive | ok | 1 | — | — | 9.2s | — |
| penguins-Q2 | classification | ok | 1 | — | — | 7.7s | — |
| titanic-Q1 | descriptive | ok | 1 | — | — | 8.7s | — |
| titanic-Q2 | classification | **fail** | 2 | ✓ | ✗ | 13.9s | validator: `.transform()` |
| airline-Q1 | time-series | **error** | 0 | — | — | 0.0s | `{peak_month}` render_prompt leftover |
| airline-Q2 | forecast | **fail** | 2 | ✓ | ✗ | 12.2s | `ModuleNotFoundError: statsmodels` |

### By task_family

| Family | Agentic 2-pass | V1 single-shot | Δ |
|---|---|---|---|
| descriptive | 3/3 | 2/3 | **+1** (penguins-Q1 recovered on round 1 via prompt refinement) |
| correlation | 1/1 | 1/1 | 0 |
| regression | 2/2 | 2/2 | 0 |
| classification | 1/2 | 1/2 | 0 (titanic-Q2 `.transform()` unrecovered) |
| time-series | 0/1 | 1/1 | **-1** (new render_prompt bug, not a model issue) |
| forecast | 0/1 | 0/1 | 0 (statsmodels infra gap, known) |

## Analysis

**Core capability signal: STABLE.** Same 7/10 rate as V1, but with a shifted distribution: penguins-Q1 (W3 Substitution Cookbook paid off) recovered, airline-Q1 regressed on an implementation bug, not a model bug.

**Three failure buckets, each with clean remediation:**

1. **Repair-loop insufficient (1 case: titanic-Q2).** GLM-5 uses `.transform()` on round 1, repair prompt instructs avoidance, round 2 uses `.transform()` again. Repair prompt has the rule but no worked example specifically for the repair context. Cookbook lives in the **user** template; repair template only references it. Low-cost fix: inline the top-3 cookbook entries directly into the repair template.

2. **Our bug (1 case: airline-Q1, time-series).** `run_agentic_analysis` raised `ValueError: Prompt rendered with leftover placeholders: ['{peak_month}']`. Root cause: `_build_repair_prompt` feeds `previous_json` (the model's round-1 output, often containing Python f-strings like `f"Peak month: {peak_month}"`) through `render_prompt`, which calls `str.format_map` and then scans the *rendered* output for leftover `{word}` patterns. F-strings in captured code trip the check. **This is our defect, not a model failure** — in V1 the same question passed because V1 has no repair loop. Fix: use direct `.replace()` substitution for the repair template, bypassing format_map's brace-handling entirely, or escape braces in slot values that carry arbitrary captured output.

3. **Infra gap (1 case: airline-Q2, forecast).** E2B default image lacks `statsmodels`. The W1 sandbox-readiness probe already reports this correctly; in production `analyze_query()` would route to deterministic when `agent_runtime_ready=False`. The W6 gate bypasses that gate (it calls `run_agentic_analysis` directly), so this failure is **expected and correctly surfaced**. Remediation is still the same as V1: custom E2B image, runtime inject, or drop forecast from agentic scope.

## Decision

**HOLD — `USE_GLM5_AGENT` stays false for the demo.** The gate rule was ≥9/10; we are 2 cases short. All 3 failures are addressable, but fixing them post-HOLD is a judgment call the user/team should make explicitly:

### Counterfactual (why not PROCEED at 9/10 equivalent?)
- Even if we treat airline-Q2 as "gated at runtime-probe → deterministic fallback" and thus not a loop failure, we are still 8/10. airline-Q1 is a genuine loop defect. titanic-Q2 is a genuine model failure the repair loop should have caught. Neither can be rounded up.

### Counterfactual (why not REGRESSION?)
- 7/10 matches V1. Task-family coverage improved (+1 descriptive via prompt, -1 time-series via our bug). The repair loop landed cleanly (triggered on 2/2 failing cases, no time-budget blowouts, no exceptions to the happy path). Infrastructure is sound; content is the gap.

## Mandatory remediation before a re-run

- [ ] **Fix `_build_repair_prompt` brace escaping.** Switch to `.replace("{slot}", value)` or pre-escape `previous_json` / `failure_detail`. Expected recovery: airline-Q1 passes → 8/10.
- [ ] **Expand repair template with inline cookbook entries for `.transform`, `.map`, `.apply`.** Current template references the cookbook by name only. Expected recovery: titanic-Q2 passes → 9/10.
- [ ] **Statsmodels in E2B runtime** (pre-install or drop forecast family from agentic scope). Required to ship forecast cases at all; doesn't block 9/10 gate if we accept airline-Q2 as probe-gated. Expected recovery: airline-Q2 passes → 10/10.

## Next step

User decides whether to:
- **(a) Merge the three remediations then re-run W6** (estimate: 1-2 hours of prompt/infra work + 5 min gate rerun + $0.05 Zhipu). Gate result then determines demo flag.
- **(b) Accept HOLD.** Demo ships on the deterministic path (production default). Agentic loop remains behind `USE_GLM5_AGENT` for post-demo iteration.

The current commit chain (W1-W5) is safe to ship either way: agentic path is gated and inert, deterministic path is unchanged, rollback is `git reset --hard 95efa2d1` (pre-W1 baseline) if needed.

## Cost & Time

- Cost: ~$0.04 Zhipu + ~$0.01 E2B (10 sandboxes × ~7s each).
- Wall clock: ~3 min total (vs. ~1.5 min for V1 single-shot; overhead is the 3s inter-case sleep + extra repair round on 2 cases).
