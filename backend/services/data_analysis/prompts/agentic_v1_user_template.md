## Dataset Profile
Filename: {filename}
Rows: {n_rows}, Columns: {n_cols}

Columns (name | dtype | role | non_null_pct | n_unique | sample_3):
{column_profile_table}

## User Question
{question}

## Required Output (strict JSON)
{
  "status": "ok" | "unanswerable",
  "business_goal": "<1 sentence, or null if unanswerable>",
  "analysis_plan": "<2-4 sentences, or null if unanswerable>",
  "assumptions": ["<assumption>", ...],
  "python_code": "<executable Python code as a single string, or null if unanswerable>",
  "produces_chart": true | false,
  "reason": "<why unanswerable, required if status=unanswerable>",
  "suggestion": "<what the user could do instead, required if status=unanswerable>"
}

## Hard Constraints
- Libraries allowed: pandas, numpy, matplotlib, seaborn, sklearn, scipy, statsmodels. Nothing else.
- BLOCKED DataFrame methods (any use rejects the code): .apply, .agg, .map, .pipe, .query, .eval, .transform.
- BLOCKED modules and builtins: os, subprocess, pathlib, sys, socket, urllib, requests, open, eval, exec, __import__.
- Load the dataset yourself with `df = pd.read_csv("/workspace/{filename}")` as the first step. (pd.read_csv is allowed; only the BLOCKED list above is forbidden.)
- If produces_chart=true, save exactly one PNG to /workspace/analysis_chart.png, overwriting any existing file. A blank file counts as failure.
- If the task is pure modeling or forecasting with no natural chart, set produces_chart=false and skip the save.
- Print exactly one line: `ANALYSIS_SUMMARY_JSON=<strict-json>` where `<strict-json>` is produced by `json.dumps(...)` (NOT `str(dict)` or `print(dict)` — those produce Python repr with single quotes that can't be parsed as JSON on the server). The line MUST include a top-level `"key_findings"` field that is a list of 2-5 short human-readable strings summarizing the result for the UI (AUC numbers, strongest correlations, notable class imbalance, etc.). If the task is a model comparison, each key finding should cite specific metric values. Example:
  ```python
  import json
  summary = {
      "key_findings": [
          "GradientBoosting leads with AUC=0.876 ± 0.020",
          "RandomForest close second at AUC=0.874",
          "SVM weakest at AUC=0.856, likely needs better scaling",
      ],
      "model_comparison": {"GradientBoosting": {"auc": 0.876}, ...},
      "chart_type": "bar",
      "analysis_type": "ml_comparison",
  }
  print("ANALYSIS_SUMMARY_JSON=" + json.dumps(summary))
  ```
- If the dataset cannot answer the question, set status="unanswerable", fill reason/suggestion, python_code=null.

## Substitution Cookbook (replacements for BLOCKED methods)

### Instead of .agg (use direct pandas methods or loops)
```python
# BAD:   df.groupby('size').agg({'tip': 'mean'})
# GOOD:  df.groupby('size')['tip'].mean()
# GOOD:  {col: df[col].mean() for col in ['tip', 'total_bill']}
# GOOD:  multi-stat: concat individual calls
out = pd.DataFrame({
    'mean': df.groupby('size')['tip'].mean(),
    'std':  df.groupby('size')['tip'].std(),
})
```

### Instead of .transform (broadcast via merge or explicit loop)
```python
# BAD:   df['tip_demeaned'] = df.groupby('size')['tip'].transform(lambda x: x - x.mean())
# GOOD:  group_means = df.groupby('size')['tip'].mean()
#        df['tip_demeaned'] = df['tip'] - df['size'].replace(group_means.to_dict())
# GOOD:  merge-based broadcast
means = df.groupby('size')['tip'].mean().rename('size_mean').reset_index()
df = df.merge(means, on='size')
df['tip_demeaned'] = df['tip'] - df['size_mean']
```

### Instead of .map (use .replace for dicts, np.select for conditions, Categorical for encoding)
```python
# BAD:   df['time_num'] = df['time'].map({'Lunch': 0, 'Dinner': 1})
# GOOD:  df['time_num'] = df['time'].replace({'Lunch': 0, 'Dinner': 1}).astype(int)
# GOOD:  df['time_num'] = np.where(df['time'] == 'Dinner', 1, 0)
# GOOD (for multi-class): df['time_num'] = pd.Categorical(df['time']).codes
```

### Instead of .apply (use vectorized ops, np.where, or explicit loop)
```python
# BAD:   df['big_tip'] = df['tip'].apply(lambda x: 1 if x > 5 else 0)
# GOOD:  df['big_tip'] = (df['tip'] > 5).astype(int)
# GOOD:  df['big_tip'] = np.where(df['tip'] > 5, 1, 0)
# For row-wise ops, use a for-loop over df.iterrows() and assign back, NOT .apply(axis=1)
```

### Instead of .query (use boolean indexing)
```python
# BAD:   df.query('tip > 5 and size == 2')
# GOOD:  df[(df['tip'] > 5) & (df['size'] == 2)]
```
