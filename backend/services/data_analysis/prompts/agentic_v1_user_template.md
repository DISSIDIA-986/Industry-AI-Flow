## Dataset Profile
Filename: {filename}
Rows: {n_rows}, Columns: {n_cols}

Columns (name | dtype | role | non_null_pct | n_unique | sample_3):
{column_profile_table}

## User Question
{question}

## Analysis Tier (hard constraint — overrides your own judgment)
{tier_directive}
EDA is always expected. The tier above governs ONLY the advanced/modeling part: respect it exactly, even if you would otherwise choose differently.

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
- **Use ONLY the columns listed in the Dataset Profile above.** Do NOT infer columns from the filename (e.g. `assignment_4_dataset.csv` is NOT automatically the wine quality dataset — do not assume a `quality` column exists). If you need a target column for classification, pick one where `n_unique == 2` from the profile; for regression, pick a numeric column the user question names. KeyErrors from hallucinated columns are the most common failure mode.
- Libraries allowed: pandas, numpy, matplotlib, seaborn, sklearn, scipy, statsmodels, AND the Python stdlib modules `json` and `math` (needed for the summary serialization below).
- **One-hot encoding (avoid the dummy-column trap):** after `pd.get_dummies(...)`, NEVER hardcode a dummy column name like `origin_europe` — a category may be absent in this dataset or dropped by `drop_first=True`, causing `KeyError: ['origin_europe'] not in index`. Build the feature matrix dynamically instead: encode the whole frame and select by dtype/prefix, e.g. `X = pd.get_dummies(df[feature_cols], drop_first=True); X = X.select_dtypes("number")` and feed ALL of `X` to the model. If you must reference specific dummies, derive them from `X.columns` at runtime, never from literals.
- BLOCKED DataFrame methods (any use rejects the code): .apply, .agg, .map, .pipe, .query, .eval.
- `.transform()` is ALLOWED only when NOT passed a lambda/callable — e.g. `.transform("mean")`, `.transform(np.sqrt)`, `scaler.transform(X)`, `pipeline.transform(X)`. Passing a lambda (e.g. `df.groupby(...).transform(lambda x: x - x.mean())`) is REJECTED — use the merge-based broadcast shown in the cookbook instead.
- BLOCKED modules and builtins: os, subprocess, pathlib, sys, socket, urllib, requests, open, eval, exec, __import__.
- Load the dataset with pandas-only delimiter detection, NOT `sep=None, engine="python"`. Use exactly this pattern:
  ```python
  _path = "/workspace/{filename}"
  _df = None
  for _try_sep in (",", ";", "\t", "|"):
      try:
          _hdr = pd.read_csv(_path, sep=_try_sep, nrows=0)
          if len(_hdr.columns) > 1:
              _df = pd.read_csv(_path, sep=_try_sep)
              break
      except Exception:
          continue
  df = _df if _df is not None else pd.read_csv(_path)
  ```
  Why this pattern instead of `sep=None, engine="python"`: the python sniffer treats digits/punctuation in numeric data as delimiters and corrupts SINGLE-COLUMN CSVs — e.g. `value\n0.24\n1.35` becomes `['Unnamed: 0', 'alue']` with the second column 100% null. The profile above was built with the same header-sniff detector, so column names will match. `open()` is BLOCKED — use only pandas as shown.
- If produces_chart=true, save exactly one PNG to /workspace/analysis_chart.png, overwriting any existing file. A blank file counts as failure.
- **Multi-aspect queries** (e.g. "do EDA AND model comparison", "plot distribution AND train classifiers") must pack every aspect into the ONE saved PNG via `plt.subplots(nrows, ncols, figsize=(W, H))`. Use a 2×2 or 2×3 grid with each subplot titled (e.g. "Survival by Sex", "Age distribution", "Model AUC comparison", "ROC curves"). Do NOT sacrifice EDA visuals just to show model results — if the user asked for both, both must be visible in the saved figure.
- If the task is pure modeling or forecasting with no natural chart, set produces_chart=false and skip the save.
- Print exactly one line: `ANALYSIS_SUMMARY_JSON=<strict-json>` where `<strict-json>` is produced by `json.dumps(...)` (NOT `str(dict)` or `print(dict)` — those produce Python repr with single quotes that can't be parsed as JSON on the server). The line MUST include a top-level `"key_findings"` field that is a list of 2-5 short human-readable strings summarizing the result for the UI (AUC numbers, strongest correlations, notable class imbalance, etc.). If the task is a model comparison, each key finding should cite specific metric values.
- **NumPy-safe serialization (mandatory):** scipy/sklearn/pandas return NumPy scalars, not Python natives — e.g. `p < 0.05` is a `numpy.bool_`, `df['x'].mean()` is a `numpy.float64`, `value_counts().iloc[0]` is a `numpy.int64`. Bare `json.dumps` raises `TypeError: Object of type bool/int64/float64 is not JSON serializable` and crashes the whole analysis. You MUST always pass a converter: `json.dumps(summary, default=lambda o: o.item() if hasattr(o, "item") else str(o))`. NEVER call bare `json.dumps(summary)` when the summary contains any computed statistic. Example:
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
  print("ANALYSIS_SUMMARY_JSON=" + json.dumps(summary, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
  ```
- If the dataset cannot answer the question, set status="unanswerable", fill reason/suggestion, python_code=null.
- **Reproducibility (mandatory):** Every source of randomness MUST be seeded so that running your code twice on the same dataset yields byte-identical results. This is non-negotiable — the system runs the same prompt + dataset multiple times and asserts deterministic output.
  - As the SECOND line of your code (right after `import` statements), call `import numpy as np; np.random.seed(42); import random; random.seed(42)`.
  - Every sklearn estimator that takes `random_state` MUST receive `random_state=42` (RandomForestClassifier, RandomForestRegressor, DecisionTreeClassifier, DecisionTreeRegressor, GradientBoostingClassifier, GradientBoostingRegressor, LogisticRegression with solver='liblinear'/'saga', KMeans, MiniBatchKMeans, TSNE, PCA with svd_solver='randomized', train_test_split, KFold, StratifiedKFold, cross_val_score).
  - Any pandas sampling (`.sample(...)`) MUST pass `random_state=42`.
  - Do NOT call `np.random.default_rng()` without a seed, and do NOT use `time.time()` or `os.urandom()` as a seed source.

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
