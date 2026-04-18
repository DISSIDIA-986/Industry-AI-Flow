## Previous Attempt Failed
repair_trigger_type: {repair_trigger_type}
failure_detail:
{failure_detail}

## User Question (unchanged)
{question}

## Your Previous Plan and Code
{previous_json}

## Dataset Profile (unchanged)
Filename: {filename}
Rows: {n_rows}, Columns: {n_cols}

Columns (name | dtype | role | non_null_pct | n_unique | sample_3):
{column_profile_table}

## Instructions
Minimal fix. Preserve the intent and structure of your previous plan. Change only what caused the failure. Output the same strict JSON schema as round 1. No prose outside the JSON.

## Common failures and their fixes
- `.apply`, `.eval`, `.query`, `.agg`, `.map`, `.pipe`, `.transform` → use the Substitution Cookbook from the original system prompt. Do NOT use these methods at all.
- Disallowed imports → stay within pandas, numpy, matplotlib, seaborn, sklearn, scipy, statsmodels.
- File I/O other than `pd.read_csv("/workspace/{filename}")` → remove it.
- NaN crashes → guard with .isna() before arithmetic, or use .dropna() before modeling.
- Forecasting by row index → use the datetime column (parse with pd.to_datetime if needed).
- Chart path → save to /workspace/analysis_chart.png if produces_chart=true.
- Module not found → the sandbox has pandas, numpy, matplotlib, seaborn, sklearn, scipy, statsmodels only.
- JSON wrapping → emit raw JSON object only, no markdown fences, no prose before or after.

Focus: minimum diff from your previous code. Keep the same overall approach unless the approach itself was the cause.
