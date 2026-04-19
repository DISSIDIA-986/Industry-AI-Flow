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
- `.apply`, `.eval`, `.query`, `.agg`, `.map`, `.pipe`, `.transform` → **completely forbidden**. Use the inline replacements below, do NOT just rename the method.
- `import os`, `import sys`, `import subprocess`, `import pathlib` → **REMOVE these imports entirely**. The sandbox already mounts the CSV at `/workspace/{filename}`; you never need os.path, sys.path, or subprocess. If your previous code had `import os` for ANY reason (even unused), delete that line on round 2.
- Disallowed imports → stay within pandas, numpy, matplotlib, seaborn, sklearn, scipy, statsmodels.
- File I/O other than `pd.read_csv("/workspace/{filename}")` → remove it.
- NaN crashes → guard with .isna() before arithmetic, or use .dropna() before modeling.
- Forecasting by row index → use the datetime column (parse with pd.to_datetime if needed).
- Chart path → save to /workspace/analysis_chart.png if produces_chart=true.
- Module not found → the sandbox has pandas, numpy, matplotlib, seaborn, sklearn, scipy, statsmodels only.
- JSON wrapping → emit raw JSON object only, no markdown fences, no prose before or after.

## Inline Replacement Cookbook (use these exact forms on the repair round)

### `.transform(...)` → groupby + broadcast via dict map or merge
```python
# BAD:   df['tip_demeaned'] = df.groupby('size')['tip'].transform(lambda x: x - x.mean())
# GOOD A (dict broadcast, same-dtype key):
group_means = df.groupby('size')['tip'].mean().to_dict()
df['size_mean'] = df['size'].replace(group_means)
df['tip_demeaned'] = df['tip'] - df['size_mean']
# GOOD B (merge broadcast, works for any key dtype):
means = df.groupby('size')['tip'].mean().rename('size_mean').reset_index()
df = df.merge(means, on='size')
df['tip_demeaned'] = df['tip'] - df['size_mean']
```

### `.map({...})` → `.replace({...})` then `.astype(...)`
```python
# BAD:   df['Sex_num'] = df['Sex'].map({'male': 0, 'female': 1})
# GOOD:  df['Sex_num'] = df['Sex'].replace({'male': 0, 'female': 1}).astype(int)
# GOOD (multi-class via Categorical codes):
df['cls_id'] = pd.Categorical(df['species']).codes
```

### `.apply(lambda ...)` → vectorized ops or np.where
```python
# BAD:   df['big_tip'] = df['tip'].apply(lambda x: 1 if x > 5 else 0)
# GOOD:  df['big_tip'] = (df['tip'] > 5).astype(int)
# GOOD:  df['big_tip'] = np.where(df['tip'] > 5, 1, 0)
# For row-wise logic: explicit for-loop over df.iterrows(), NOT apply(axis=1).
```

### `.agg({...})` → per-column mean/std/etc. directly or dict comp
```python
# BAD:   df.groupby('class').agg({'Fare': 'mean', 'Age': 'median'})
# GOOD:  pd.DataFrame({
#            'Fare_mean':   df.groupby('class')['Fare'].mean(),
#            'Age_median':  df.groupby('class')['Age'].median(),
#        })
```

### `.query('...')` → boolean indexing with `&` / `|`
```python
# BAD:   df.query('Age > 30 and Sex == "female"')
# GOOD:  df[(df['Age'] > 30) & (df['Sex'] == 'female')]
```

Focus: minimum diff from your previous code. Keep the same overall approach unless the approach itself was the cause. If your round-1 code used a blocked method, **copy the exact GOOD form above** rather than inventing a new one.
