# Spike GLM-5 — Stage 2 Decision Memo
Date: 2026-04-18
Source: `test_resources/benchmarks/spike_glm5_20260418.jsonl`
Design doc: `~/.gstack/projects/DISSIDIA-986-Industry-AI-Flow/niuyp-main-design-20260418-093902.md`

## Result
**7/10 passed (70%). Verdict: PARTIAL.**

| Case | Task family | Status | Chart | Fail reason |
|---|---|---|---|---|
| tips-Q1 | descriptive | ok | ✓ | — |
| tips-Q2 | regression | ok | ✓ | — |
| mpg-Q1 | correlation | ok | — | — |
| mpg-Q2 | regression | ok | ✓ | — |
| penguins-Q1 | descriptive | **fail** | — | validator: `.agg()` |
| penguins-Q2 | classification | ok | ✓ | — |
| titanic-Q1 | descriptive | ok | ✓ | — |
| titanic-Q2 | classification | **fail** | — | validator: `.transform()` |
| airline-Q1 | time-series | ok | ✓ | — |
| airline-Q2 | forecast | **fail** | — | sandbox: `ModuleNotFoundError: statsmodels` |

### By task_family

| Family | Pass | Note |
|---|---|---|
| descriptive | 2/3 | penguins-Q1 tripped on `.agg()` |
| correlation | 1/1 | ✓ |
| regression | 2/2 | ✓ |
| classification | 1/2 | titanic-Q2 tripped on `.transform()` |
| time-series | 1/1 | ✓ |
| forecast | 0/1 | **infra gap**: statsmodels not in E2B sandbox |

## Analysis

**Core capability signal: STRONG.** GLM-5 produced executable, validator-passing, sandbox-succeeding code for 7 of 10 CRISP-DM style questions on first shot, across 5 of 6 task families. Every task family except forecast has ≥1 pass, confirming P3 is not falsified.

**Two failure buckets, different remediation:**

1. **Prompt compliance (2 cases: penguins-Q1, titanic-Q2).** GLM-5 ignored the "BLOCKED methods" list and used `.agg()` / `.transform()`. This is addressable without changing architecture:
   - (a) Tighter prompt with per-method replacements inline (current prompt has examples only for `.agg`)
   - (b) V2 repair loop (the one we cut from the spike) — likely pushes these 2 to PASS on round 2
   - Prior in spike_v1 smoke, tips-Q2 failed similarly (`.map()`), passed on second run with identical prompt. Sampling variance at temp=0.2 is real but small.

2. **Infra gap (1 case: airline-Q2).** E2B's default `code-interpreter` image ships pandas/numpy/matplotlib/seaborn/sklearn but **NOT statsmodels**. Adding statsmodels to the validator whitelist (B.2) lets the code pass validation, but the sandbox then fails at import. This is not a capability issue — it's an environment setup miss.

## Decision

**PROCEED to Plan with caveats.** The spike verdict "PARTIAL" by raw rules, but the failure modes are not evidence against P3 — they are addressable without questioning the core premise:

### Mandatory Plan-stage work
1. **Install statsmodels in E2B sandbox runtime** — either pre-install via custom image, or inject `!pip install statsmodels` before forecast-family code runs. Without this, forecast tasks cannot ship.
2. **V2 repair loop** — the 2 `.agg()` / `.transform()` failures are textbook repair candidates. Plan should budget for the bounded 2-pass loop; do not skip.
3. **Prompt refinement** — expand the "Examples of valid groupby replacements" section with concrete substitutes for `.agg()`, `.transform()`, `.apply()`. The current template has `.agg` example but not `.transform`.

### Counterfactual (why not STOP?)
- Pure STOP would be warranted if failures were across families or showed GLM-5 lacked conceptual understanding (e.g., wrong analysis approach, hallucinated column names). None of that appeared.
- Pure PROCEED-without-caveats would be warranted if ≥8/10 pass with no infra gaps. We are one prompt refinement + one pip install away from that.

### Counterfactual (why not run a V2 round right now on the failures?)
- Tempting, but would bias the decision. The spike was sized as "first-pass only." Spending budget on a bolt-on V2 run would turn the spike into the thing it was meant to inform.

## Action items for the Plan phase

- [ ] Custom E2B image or runtime injection for statsmodels (1 hour infra)
- [ ] Design V2 repair loop with bounded-at-1 retries (mirror Codex's original A.2, revive the deleted repair prompt template)
- [ ] Expand prompt with full pandas-without-banned-methods cookbook (2 hours prompt work)
- [ ] Re-run spike post-prompt-refinement + E2B fix as a Plan confirmation gate

## Cost & Time

Cost: negligible (10 × ~1200 tokens in, ~500 out ≈ $0.04 total on Zhipu pricing).
Time: 1m30s wall clock (setup dominated; actual LLM + sandbox ≈ 90s).
