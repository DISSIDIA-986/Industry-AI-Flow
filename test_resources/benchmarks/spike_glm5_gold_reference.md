# Gold Reference Sheet — Spike GLM-5 Benchmark
Computed from actual datasets on 2026-04-18. All expected values come from pandas ground-truth computed in `scripts/spike_data_analysis_glm5.py` setup. Reviewers use these to judge the `silent_bad` rubric in the design doc (Appendix A.3).

## Tolerance Table (from Appendix B.5)

| Task family | Expected metric | Tolerance |
|---|---|---|
| descriptive | mean / median / grouped mean | ±10% relative |
| correlation | Pearson r | ±0.05 absolute |
| regression | R² | ±0.10 absolute |
| classification | accuracy / F1 | ±0.10 absolute |
| time-series | trend direction + seasonality period | direction match only |
| forecast | MAPE on holdout | ±20% relative |

---

## Dataset 1: tips.csv (244 rows)

### Q1 (descriptive): "How does mean tip vary with party size?"
**Task family:** descriptive
**Expected approach:** group by `size`, compute mean of `tip`, bar chart with error bars OR boxplot
**Expected numbers (mean tip by size, ±10% relative):**
- size=1 → 1.44
- size=2 → 2.58
- size=3 → 3.39
- size=4 → 4.14
- size=5 → 4.03
- size=6 → 5.23
**Expected chart:** bar or boxplot, x=size, y=tip, 6 groups visible
**Expected trend:** monotonic upward (with size=5 slight dip)

### Q2 (regression): "Predict tip from total_bill, size, and time of day."
**Task family:** regression
**Expected approach:** encode `time` (one-hot or label), fit linear regression, 80/20 split, report R² + RMSE
**Expected R² (±0.10 absolute):** ~0.45 to 0.55 (total_bill dominates)
**Expected chart:** optional (regression task, produces_chart may be false)
**Silent-bad flags to catch:** using tip in features (leakage); no train/test split

---

## Dataset 2: mpg.csv (398 rows)

### Q1 (correlation): "Which numeric features correlate most strongly with mpg?"
**Task family:** correlation
**Expected approach:** Pearson correlation of numeric-only columns vs mpg; sort by absolute value; heatmap
**Expected correlations with mpg (±0.05 absolute):**
- weight → -0.83
- displacement → -0.80
- horsepower → -0.78
- cylinders → -0.78
- acceleration → +0.42
- model_year → +0.58
**Expected chart:** correlation heatmap OR sorted bar chart of |corr|
**Silent-bad flags:** string columns (origin, name) sneaking in; ID-like columns treated as numeric

### Q2 (regression): "Predict mpg from weight, horsepower, model_year."
**Task family:** regression
**Expected approach:** linear regression or RandomForest; 80/20 split; report R² + RMSE
**Expected R² (±0.10 absolute):** ~0.80 to 0.85
**Expected chart:** optional
**Silent-bad flags:** using mpg in features; no train/test split; horsepower has NaNs (must be handled)

---

## Dataset 3: penguins.csv (344 rows)

### Q1 (descriptive): "What are the differences in body measurements between the three species?"
**Task family:** descriptive
**Expected approach:** group by `species`, compute means for bill_length_mm, bill_depth_mm, flipper_length_mm, body_mass_g; boxplots or grouped bar
**Expected means by species (±10% relative):**
- Adelie: bill_length ≈ 38.8 mm, body_mass ≈ 3701 g
- Chinstrap: bill_length ≈ 48.8 mm, body_mass ≈ 3733 g
- Gentoo: bill_length ≈ 47.5 mm, body_mass ≈ 5076 g
**Expected chart:** boxplots or grouped bars with 3 species × 4 metrics
**Species counts:** Adelie=152, Gentoo=124, Chinstrap=68

### Q2 (classification): "Classify penguin species using bill_length, bill_depth, flipper_length."
**Task family:** classification
**Expected approach:** LogisticRegression or RandomForestClassifier, 80/20 split, report accuracy + per-class F1
**Expected accuracy (±0.10 absolute):** ~0.90 to 0.98 (very separable dataset)
**Silent-bad flags:** using species in features; no split; NaN rows (2 rows have NaN — must drop or impute)

---

## Dataset 4: titanic.csv (891 rows)

### Q1 (descriptive + missing): "Which factors are associated with survival? Handle missing Age."
**Task family:** descriptive + missing-value handling
**Expected approach:** impute OR acknowledge 19.9% missing Age (177 of 891); survival rate by Pclass and Sex at minimum; chart
**Expected numbers (±10% relative):**
- Overall survival rate: 0.384
- By Pclass: {1: 0.63, 2: 0.47, 3: 0.24}
- By Sex: {female: 0.74, male: 0.19}
**Expected chart:** bar chart of survival rate by Pclass or Sex
**Silent-bad flags:** not addressing Age missingness; treating Survived as feature

### Q2 (classification + cleaning): "Classify survival from Pclass, Sex, Age, Fare."
**Task family:** classification
**Expected approach:** impute Age (median or similar), encode Sex, 80/20 split, LogisticRegression or RandomForest, accuracy + F1
**Expected accuracy (±0.10 absolute):** ~0.75 to 0.82
**Silent-bad flags:** Age NaN handling missing (crashes or silently drops); Survived in features; dropping most rows during cleaning (nrows_after should be ≥700)

---

## Dataset 5: airline-passengers.csv (144 rows, 1949-01 to 1960-12)

### Q1 (time-series): "Describe the trend and seasonality in monthly passenger counts."
**Task family:** time-series
**Expected approach:** parse Month as datetime, use statsmodels.tsa.seasonal.seasonal_decompose (period=12) OR STL; plot trend + seasonal components
**Expected observations (direction match only):**
- Trend: clearly upward (first-year mean 127, last-year mean 476)
- Seasonality: annual period (12 months), summer peaks
- Passengers mean ≈ 280.3, std ≈ 120.0
**Expected chart:** decomposition plot OR line chart with trend overlay
**Silent-bad flags:** using row index as time (row 0 = Jan 1949, not "0"); not identifying the 12-month seasonality; plotting flat line

### Q2 (forecast): "Forecast the next 12 months."
**Task family:** forecast
**Expected approach:** ARIMA, SARIMAX, or ExponentialSmoothing from statsmodels; 12-step ahead forecast; plot history + forecast
**Expected forecast range for 1961 monthly:** ~420 to 620 passengers (last observed value was 432 in Dec 1960, with upward trend and seasonality)
**Expected MAPE on train (±20% relative):** <15% for reasonable model
**Expected chart:** line chart with history + forecast, ideally CI bands
**Silent-bad flags:** forecasting with row index; using linear regression on row number (ignores seasonality); predicting monotonic decline

---

## Reviewer Notes
- "±10% relative" means absolute_difference / |expected| ≤ 0.10
- "direction match only" means the sign/trend matches, not specific magnitude
- When the generated code includes a different but valid approach (e.g., median instead of mean for tips Q1), mark checkbox if the ALTERNATIVE is justified in `assumptions` field and still answers the question
- When in doubt on tolerance, PASS the trial — this spike measures capability, not pixel-perfect accuracy
