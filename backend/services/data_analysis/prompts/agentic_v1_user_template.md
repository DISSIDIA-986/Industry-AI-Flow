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
- Libraries allowed: pandas, numpy, matplotlib, seaborn, sklearn, scipy, statsmodels, AND the Python stdlib modules `json` and `math`. xgboost and lightgbm are NOT installed — for gradient boosting use sklearn's `GradientBoostingClassifier`/`GradientBoostingRegressor` or `HistGradientBoostingClassifier`/`HistGradientBoostingRegressor`.
- **Adaptive model selection (when the Analysis Tier permits modeling and the task is supervised):** train **≥2 candidate models** and pick the best by the task-appropriate metric, then put the comparison in `summary["model_comparison"]` as `{ModelName: {metric: value, ...}}` with the SAME metric keys for every model. Metric guidance:
  - **Classification** → report `f1` (macro for multiclass), `roc_auc` (binary) or `accuracy`, plus `precision`/`recall` for imbalanced targets. Good candidates: `LogisticRegression`, `RandomForestClassifier`, `GradientBoostingClassifier`.
  - **Regression** → report `rmse`, `r2`, optionally `mae`. Good candidates: `Ridge`/`LinearRegression`, `RandomForestRegressor`, `GradientBoostingRegressor`.
  Evaluate each model ONCE on a single held-out train/test split (or <=5-fold CV) — never a tuned search (see compute budget). Name the winning model and its key metric in `key_findings`. If the tier is `light` (one model only) or `skip` (EDA only), respect that and do NOT train a multi-model comparison.
- **One-hot encoding (avoid the dummy-column trap):** after `pd.get_dummies(...)`, NEVER hardcode a dummy column name like `origin_europe` — a category may be absent in this dataset or dropped by `drop_first=True`, causing `KeyError: ['origin_europe'] not in index`. Build the feature matrix dynamically instead: encode the whole frame and select by dtype/prefix, e.g. `X = pd.get_dummies(df[feature_cols], drop_first=True); X = X.select_dtypes("number")` and feed ALL of `X` to the model. If you must reference specific dummies, derive them from `X.columns` at runtime, never from literals.
- **Compute budget (your code is killed after ~30s of execution — keep it FAST):** Your generated code runs in a sandbox with a hard ~30-second execution limit; anything slower returns NO result. Do NOT use `GridSearchCV`, `RandomizedSearchCV`, or `auto_arima`/`pmdarima`, and do NOT sweep many hyperparameters. Use sensible FIXED hyperparameters. Keep `n_estimators <= 200`, `cross_val` folds <= 5, and for ARIMA/SARIMA use a single explicit small order (e.g. `ARIMA(series, order=(1,1,1))`) — never an order grid search. For unsupervised tasks use ONE method with sane defaults (e.g. a single `KMeans`, `DBSCAN`, `PCA`, or `IsolationForest` fit); only sweep `k`/`eps`/`contamination` if the question explicitly asks you to choose the best value, and then over a SMALL range (<=8 values). If comparing supervised models, train each ONCE on a single train/test split (or <=5-fold CV), not a tuned search. A fast approximate answer that returns beats a perfectly-tuned one that times out.
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
- **Emit the summary by calling the pre-defined helper `emit_summary(summary)` exactly once.** It is ALREADY DEFINED in your runtime — do NOT define it yourself, do NOT `import json`, and do NOT print the `ANALYSIS_SUMMARY_JSON=` line manually. The helper serializes NumPy types safely (scipy/sklearn/pandas return `numpy.bool_` for `p < 0.05`, `numpy.float64` for `.mean()`, `numpy.int64` for `value_counts().iloc[0]`, and ndarrays — all of which crash a bare `json.dumps`). Calling the helper removes that entire crash class. The `summary` dict MUST include a top-level `"key_findings"` field: a list of 2-5 short human-readable strings (AUC numbers, strongest correlations, notable class imbalance, the winning model, etc.). For a model comparison, each finding should cite specific metric values. Example:
  ```python
  summary = {
      "key_findings": [
          "GradientBoosting leads with AUC=0.876 ± 0.020",
          "RandomForest close second at AUC=0.874",
          "LogisticRegression weakest at AUC=0.856",
      ],
      "model_comparison": {"GradientBoosting": {"auc": 0.876}, "RandomForest": {"auc": 0.874}},
      "chart_type": "bar",
      "analysis_type": "ml_comparison",
  }
  emit_summary(summary)   # NOT json.dumps, NOT print — the helper does both, NumPy-safe
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
