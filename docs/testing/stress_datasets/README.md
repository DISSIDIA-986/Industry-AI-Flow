# Data Analysis Stress Test Harness

Two scripts that exercise `/api/v1/data/analyze/start` (SSE) end-to-end
against the agentic path, classifying outcomes by inspecting the full
response envelope (code, charts, answer, error) rather than trusting
HTTP 200.

## Scripts

- **`run_data_analysis_stress_v1.py`** — 12 diverse public datasets,
  simple questions (distribution, correlation, predict, forecast, etc).
  Smoke-level: do common shapes work at all?
- **`run_data_analysis_stress_v2.py`** — 15 harder questions on the
  same datasets: multi-classifier ROC, 5-fold CV, PCA, multi-chart
  composite, time-series forecast, vague prompts, adversarial
  non-existent columns. Coverage-level: does the system generalize?

## Datasets (`docs/testing/stress_datasets/`)

| File | Why it's interesting |
|---|---|
| `single_column.csv` | Triggers CSV sniff regression (fixed in PR #39) |
| `semicolon_delimited.csv` | UCI-style European CSV |
| `categorical_only.csv` | No numeric columns — pure dtype edge case |
| `high_missing.csv` | NaN-heavy, tests dropna handling |
| `pii_looking.csv` | name/email/phone columns — tests PII redaction (PR #35) |
| `timeseries.csv` | Datetime column, tests forecast / rolling-mean |
| `iris.csv` | Classic ML baseline |
| `wine.csv` | Multi-feature classification |
| `heart_disease.csv` | Binary classification |
| `wide_dataset.csv` | Many columns — PCA / feature-selection stress |
| `breast_cancer.csv` | Classic ML, balanced classes |
| `diabetes.csv` | Regression target |

## Auth

Both scripts authenticate via `/api/v1/auth/login` using
`DEMO_USER_PASSWORD` from `.env`. The production-like server at
`http://127.0.0.1:8000` requires JWT — these scripts handle that.

## Running

```bash
# server must be running with USE_GLM5_AGENT=true (default)
# requires E2B_API_KEY and ZHIPU_API_KEY in .env

.venv/bin/python scripts/testing/stress/run_data_analysis_stress_v1.py
.venv/bin/python scripts/testing/stress/run_data_analysis_stress_v2.py
```

Outputs written to `/tmp/real-stress-results.json` and
`/tmp/stage2-stress-results.json`.

## Historical results (2026-05-28 baseline)

| Iteration | v1 PASS | v2 PASS |
|---|---|---|
| Initial (before PR #39 hotfixes) | 1/12 | n/a |
| After PR #39 | 12/12 | n/a |
| After PR #39 + Stage 2 design | 12/12 | 14/15 (15/15 incl. graceful "no such column") |

The 1 non-PASS in v2 is by design — system gracefully explains that
the requested column doesn't exist, rather than hallucinating broken
code. Classifier flags it as `WRONG_BUT_PLAUSIBLE` for safety but the
underlying behavior is correct.

## Adding new test cases

Each test is a `(csv_basename, question, expected_signal)` tuple.
`expected_signal` keys:
- `code_substr_any`: list of strings — at least one must appear in
  generated code for PASS. Empty list = no code-content requirement.
- `chart_required`: bool — must `visualizations[]` be non-empty?
- `allow_failure`: bool — if True, `success=False` is `GRACEFUL_FAIL`
  not `HARD_FAIL`. Use for adversarial / impossible prompts.

The classifier handles both agentic-path (LLM-generated) and
deterministic-planner outputs — same envelope structure for both.
