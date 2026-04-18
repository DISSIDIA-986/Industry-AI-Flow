## Dataset Profile
Filename: {filename}
Rows: {n_rows}, Columns: {n_cols}

Columns (name | dtype | role | non_null_pct | n_unique | sample_3):
{column_profile_table}

## User Question
{question}

## Required Output (strict JSON)
{{
  "status": "ok" | "unanswerable",
  "business_goal": "<1 sentence, or null if unanswerable>",
  "analysis_plan": "<2-4 sentences, or null if unanswerable>",
  "assumptions": ["<assumption>", ...],
  "python_code": "<executable Python code as a single string, or null if unanswerable>",
  "produces_chart": true | false,
  "reason": "<why unanswerable, required if status=unanswerable>",
  "suggestion": "<what the user could do instead, required if status=unanswerable>"
}}

## Hard Constraints
- Libraries allowed: pandas, numpy, matplotlib, seaborn, sklearn, scipy, statsmodels. Nothing else.
- BLOCKED DataFrame methods (any use rejects the code): .apply, .agg, .map, .pipe, .query, .eval, .transform. Use groupby with named functions, value_counts, pivot_table, or for-loops instead.
- BLOCKED modules and builtins: os, subprocess, pathlib, sys, socket, urllib, requests, open, eval, exec, __import__.
- Load the dataset yourself with `df = pd.read_csv("/workspace/{filename}")` as the first step of your code. (pd.read_csv is allowed; only the BLOCKED list above is forbidden.)
- If produces_chart is true, save exactly one PNG to /workspace/analysis_chart.png. Overwrite any existing file. A blank file counts as failure.
- If the task is pure modeling or forecasting with no natural chart, set produces_chart to false and skip the save.
- Print exactly one line starting with `ANALYSIS_SUMMARY_JSON=` followed by a compact one-line JSON object of key findings (numeric results, test metrics, or notable observations).
- If the dataset cannot answer the question, set status="unanswerable", fill in reason and suggestion, and set python_code to null.

## Examples of valid groupby replacements for banned methods
- Mean tip by size: `df.groupby('size')['tip'].mean()` (no .agg, no .apply)
- Survival by Pclass: `df.groupby('Pclass')['Survived'].mean()`
- Custom summary: use a for-loop or a dict comprehension, not the banned .agg method.
