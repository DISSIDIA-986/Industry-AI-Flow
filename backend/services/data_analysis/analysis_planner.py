"""Heuristic model-comparison planner.

Decides whether a dataset is a plausible supervised-learning target and,
if so, names the target column and task type. Lives alongside
``chart_plan`` (deterministic EDA planner) and feeds
``chart_executor.execute_model_comparison``.

Design choice: no LLM on this path. The original design doc leaned
toward an LLM call to pick the target. Heuristic is:

1. Stable (no cloud latency / JSON schema failures on the demo path).
2. Predictable on the usual teaching datasets: iris (``species`` /
   ``class``), titanic (``survived``), wine-quality (``quality``),
   california housing (``median_house_value``), etc.
3. Debuggable: ``rationale`` always explains the choice.

Precedence for target column:
  - Name match against ``_TARGET_NAME_PATTERNS`` (case-insensitive,
    exact or last-token match).
  - Fallback to the last column (sklearn tutorial convention).

Task type:
  - ``classification`` if role is ``categorical`` OR unique values < 10.
  - ``regression`` if role is ``numeric`` AND unique values >= 10.

Guardrails (any one fails → enabled=False with rationale):
  - rows > 50_000 (row cap, would blow the 12s stage budget).
  - rows < 20 (can't split train/test meaningfully).
  - <= 1 non-target column (nothing to train on).
  - target has < 2 unique values (degenerate label).
  - classification target cardinality > 20 (too many classes for
    a quick demo; behaves like an ID column).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Row cap before model training becomes too slow for the 12s stage budget.
# Kept here (not imported from chart_plan) so this module stands alone.
_ROW_CAP = 50_000
_ROW_FLOOR = 20

# Common target column names, checked in order. Case-insensitive exact or
# suffix match against column name (e.g. ``y``, ``median_house_value``).
# Order matters: more specific names first so ``target`` doesn't swallow
# ``is_target_acquired``.
_TARGET_NAME_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"^(target|label|class|y|outcome|response)$", re.IGNORECASE),
    re.compile(r"^(survived|default|churn|fraud)$", re.IGNORECASE),
    re.compile(r"^(quality|price|value|score|rating)$", re.IGNORECASE),
    re.compile(r"(_target|_label|_class|_y|_outcome)$", re.IGNORECASE),
]

# Classification task cardinality cap. Anything above this is almost
# certainly an ID column or a regression target mis-classified, and
# training a classifier on 100-unique classes inside 12s fails anyway.
_CLASS_CARDINALITY_CAP = 20


def decide_model_comparison(
    dataset_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Return the ``model_comparison`` plan block.

    Shape matches what ``chart_plan.eda_plan_from_metadata`` currently
    emits so consumers (report_composer, frontend) see a single shape
    regardless of whether the stretch path is active.

    Returns:
        {
          "enabled": bool,
          "target_column": str | None,
          "task": "classification" | "regression" | None,
          "models": list[str],
          "reason": str,
        }
    """
    columns_info: List[Dict[str, Any]] = dataset_metadata.get("columns_info") or []
    rows: int = int(dataset_metadata.get("rows") or 0)

    if rows > _ROW_CAP:
        return _disabled(
            f"dataset has {rows} rows, exceeds {_ROW_CAP} row cap "
            "for live demo model training"
        )
    if rows < _ROW_FLOOR:
        return _disabled(
            f"dataset has only {rows} rows, need at least {_ROW_FLOOR} "
            "for a meaningful train/test split"
        )
    if len(columns_info) < 2:
        return _disabled(
            f"only {len(columns_info)} column(s) — no features left after "
            "picking a target"
        )

    target = _pick_target_column(columns_info)
    if target is None:
        return _disabled(
            "no column matched a recognizable target pattern "
            "(target/label/class/quality/...) and dataset has no usable "
            "last-column fallback"
        )

    unique = int(target.get("unique_values") or 0)
    if unique < 2:
        return _disabled(
            f"target column {target['name']!r} has {unique} unique value(s) — "
            "degenerate label"
        )

    task = _classify_task(target)

    if task == "classification" and unique > _CLASS_CARDINALITY_CAP:
        return _disabled(
            f"target column {target['name']!r} has {unique} unique classes — "
            f"exceeds {_CLASS_CARDINALITY_CAP} cap for quick demo training"
        )

    models = _models_for_task(task)

    return {
        "enabled": True,
        "target_column": target["name"],
        "task": task,
        "models": models,
        "reason": (
            f"target={target['name']!r}, task={task}, "
            f"unique_values={unique}, rows={rows}"
        ),
    }


# --------------------------------------------------------------------------
# target selection
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Latency-aware analysis-tier planner (2026-05-29).
#
# EDA is always done (fast). ADVANCED analysis (model training) is the slow,
# supplementary part — decided here from dataset metadata, "auto only when
# cheap". The tier becomes a HARD constraint in the agentic prompt, overriding
# the LLM's soft CRISP-DM skip choice (one source of truth, reproducible). NOT
# the Intent Classifier — that's a query router with no dataset metadata.
#
#   skip  : EDA only, no model (infeasible, or not requested and not cheap)
#   light : at most ONE simple model, small CV, no hyperparameter search
#   full  : model comparison allowed (still bounded by the compute guard)
# --------------------------------------------------------------------------

# rows × features proxy below which a single model fit is "cheap" enough to run
# automatically even when the user didn't explicitly ask to model.
_LIGHT_COST_BUDGET = 2_000_000

# Signals the user explicitly wants advanced/modeling (not just EDA).
_MODEL_INTENT = re.compile(
    r"\b(predict|classif\w*|regress\w*|forecast\w*|cluster\w*|model\w*|train\w*|"
    r"svm|random[ _]?forest|xgboost|gradient[ _]?boost\w*|knn|logistic|"
    r"decision[ _]?tree|feature[ _]?importance\w*|hyper[ _]?parameter\w*|"
    r"cross[ -]?validat\w*|anomal\w*|outlier\w*|pca|dimensionality|"
    r"advanced analysis)\b",
    re.IGNORECASE,
)


def plan_analysis_tier(
    dataset_metadata: Dict[str, Any], question: str = ""
) -> Dict[str, Any]:
    """Decide how much ADVANCED analysis to attempt, from metadata + the question.

    Returns ``{tier, reason, model_requested, target_column, task, estimated_cost}``
    where ``tier`` is ``skip`` | ``light`` | ``full``. EDA always runs regardless.
    """
    columns_info: List[Dict[str, Any]] = dataset_metadata.get("columns_info") or []
    rows = int(dataset_metadata.get("rows") or 0)
    n_numeric = sum(
        1
        for c in columns_info
        if c.get("role") == "numeric"
        or str(c.get("type", "")).startswith(("int", "float"))
    )
    n_features = max(0, len(columns_info) - 1)
    cost = rows * max(1, n_features)
    asked = bool(_MODEL_INTENT.search(question or ""))
    # Name-match only (no last-column fallback): tiering is a hard latency gate,
    # so it must NOT auto-pick a target the user never named. A false-positive
    # target escalates an EDA-only request to model training and burns the time
    # budget. decide_model_comparison keeps the permissive _pick_target_column
    # fallback — that path is about feasibility, not auto-escalation policy.
    target = _match_by_name(columns_info)
    task = _classify_task(target) if target else None

    def _tier(t: str, reason: str) -> Dict[str, Any]:
        return {
            "tier": t,
            "reason": reason,
            "model_requested": asked,
            "target_column": target["name"] if target else None,
            "task": task,
            "estimated_cost": cost,
        }

    if rows > _ROW_CAP:
        return _tier(
            "skip", f"{rows} rows exceed the {_ROW_CAP} cap for live model training"
        )
    if n_numeric < 2 or rows < _ROW_FLOOR:
        return _tier("skip", "not enough numeric data to train a meaningful model")
    if target is None:
        if asked:
            return _tier(
                "light",
                "no obvious target column; attempting one bounded model per request",
            )
        return _tier("skip", "no recognizable target column; EDA only")
    if task == "classification":
        unique = int(target.get("unique_values") or 0)
        if unique > _CLASS_CARDINALITY_CAP:
            return _tier(
                "skip",
                f"target {target['name']!r} has {unique} classes — too many for quick training",
            )
    if asked:
        t = "full" if cost <= _LIGHT_COST_BUDGET else "light"
        return _tier(t, f"requested modeling; target={target['name']!r}, task={task}")
    if cost <= _LIGHT_COST_BUDGET:
        return _tier(
            "light",
            f"cheap dataset — auto single model (target={target['name']!r}, task={task})",
        )
    return _tier(
        "skip", "large dataset — advanced modeling skipped unless explicitly requested"
    )


def tier_directive(plan: Dict[str, Any]) -> str:
    """Render the tier decision as a hard prompt constraint for the agentic round."""
    t = plan.get("tier", "skip")
    reason = plan.get("reason", "")
    if t == "skip":
        return (
            f"ANALYSIS TIER = skip (reason: {reason}). Do EDA only. Do NOT train any "
            "ML model. If the user explicitly asked for modeling that this tier "
            "cannot support, explain why in the answer and set produces_chart per the EDA."
        )
    if t == "light":
        return (
            f"ANALYSIS TIER = light (reason: {reason}). You MAY train at most ONE "
            "simple model (e.g. a single RandomForest / LinearRegression / KMeans) "
            "with at most 5-fold CV. Do NOT use GridSearchCV, RandomizedSearchCV, or "
            "any hyperparameter search, and keep n_estimators <= 300."
        )
    return (
        f"ANALYSIS TIER = full (reason: {reason}). Model comparison is allowed. Keep "
        "any hyperparameter search small (well under 100 fits) and n_estimators <= 300 "
        "so the analysis finishes within the time budget."
    )


# --------------------------------------------------------------------------
# Advanced-analysis method planner (2026-07-12).
#
# The tier planner above governs *how much modeling* to attempt. It does NOT
# decide *which analytical method* the question actually calls for. Before this,
# inferential statistics (hypothesis tests, correlation significance, effect
# sizes), time-series forecasting, and model explainability were left entirely
# to the LLM's soft judgment via the prompt — so the same "does X differ between
# groups?" question would sometimes get a bar chart with no p-value.
#
# This planner ports the pattern every serious OSS data agent converges on
# (a stat-test registry keyed by variable-type-pair, plus a time-series router)
# into a DETERMINISTIC directive, rendered exactly like `tier_directive`. The
# LLM still generates the code (current architecture, unchanged) but is now told
# precisely which scipy/statsmodels/sklearn call to make and which quantities to
# report. Detection requires BOTH a matching data shape AND explicit question
# intent; when neither fires, `method_directive` returns "" and behaviour is
# byte-identical to before (default-off, purely additive — never overrides EDA).
# --------------------------------------------------------------------------

# Grouping-variable cardinality window: a categorical/boolean column with 2..N
# distinct values is a plausible group factor for a between-groups comparison.
# Above this it behaves like an ID and the test is meaningless.
_GROUP_CARD_CAP = 10

# Minimum points for a credible forecast backtest (Codex: below ~24 do a trend
# summary only, never a seasonal model).
_TS_MIN_POINTS = 24

# At most this many method cards per request, so two stat fits + EDA still land
# inside the ~30s sandbox budget. Priority order is applied before truncation.
_MAX_METHOD_CARDS = 2

# Question-intent signals. Each method needs its intent AND a matching data
# shape; a shape alone never triggers a test (keeps EDA-only requests EDA-only).
_COMPARE_INTENT = re.compile(
    r"\b(differ\w*|compare\w*|versus|vs\.?|higher|lower|greater|less|more than|"
    r"effect of|impact of|influence of|between|across|by (group|category)|"
    r"affect\w*|significantly)\b",
    re.IGNORECASE,
)
# Correlation intent is deliberately correlation-SPECIFIC: `associat*`/`related`/
# `depend*` were removed (Codex P1 #3) because they overlap with categorical
# association and made a chi-square question also spawn a spurious numeric
# correlation. Those words now live only in _CAT_ASSOC_INTENT below.
_RELATION_INTENT = re.compile(
    r"\b(correlat\w*|relationship|correlated with|driver\w*|drives|predict\w*|"
    r"influenc\w*|linked|trade[- ]?off|scatter\w*|linear relationship|"
    r"vary with|move together)\b",
    re.IGNORECASE,
)
_CAT_ASSOC_INTENT = re.compile(
    r"\b(associat\w*|independen\w*|contingency|cross[- ]?tab\w*|chi[- ]?squ\w*)\b",
    re.IGNORECASE,
)
# Forecast intent is EXPLICIT-forecast only (Codex P1 #1): bare `trend`/`over
# time`/`season` were dropped so "show the cost trend over time" stays a simple
# line-chart EDA rather than forcing a full ARIMA/ETS backtest + intervals.
_FORECAST_INTENT = re.compile(
    r"\b(forecast\w*|future|upcoming|next \d+|next (month|quarter|year|week|day|"
    r"period)s?|projection|extrapolat\w*|going forward|predict\w* (the )?"
    r"(next|future))\b",
    re.IGNORECASE,
)
# Importance intent requires explicit driver/predictive wording (Codex P1 #2):
# bare `why`/`important` were dropped so "why is the price distribution skewed?"
# does NOT train a model. Still needs a named target column downstream.
_IMPORTANCE_INTENT = re.compile(
    r"\b(driver\w*|what drives|key factor\w*|main factor\w*|top factor\w*|"
    r"most predictive|feature importance|which (features?|factors?|variables?)|"
    r"most important (feature|factor|variable|predictor))\b",
    re.IGNORECASE,
)

# Object/unparsed columns whose NAME reads as a time axis, so a date stored as
# text still routes to the time-series card. role==datetime is the primary
# signal; this catches the common "date parsed as object" case.
_DATE_NAME = re.compile(
    r"^(date|time|timestamp|datetime|day|month|year|period|week|quarter|ds)$"
    r"|_(date|time|month|year|day)$|(date|time|month|year)$",
    re.IGNORECASE,
)


def plan_analysis_methods(
    dataset_metadata: Dict[str, Any], question: str = ""
) -> Dict[str, Any]:
    """Pick the inferential/temporal/explainability methods the question warrants.

    Returns ``{"methods": [card, ...], "reason": str}`` where each card is
    ``{"kind", "columns", "detail"}``. An empty ``methods`` list means "nothing
    beyond EDA is warranted" and renders to an empty directive (no-op).
    """
    columns_info: List[Dict[str, Any]] = dataset_metadata.get("columns_info") or []
    rows = int(dataset_metadata.get("rows") or 0)
    q = question or ""

    numeric = _numeric_cols(columns_info)
    groups = _group_cols(columns_info)
    datetimes = _datetime_cols(columns_info)

    cards: List[Dict[str, Any]] = []

    # 1. Time-series forecasting (highest priority — most visibly "advanced").
    if datetimes and numeric and rows >= _TS_MIN_POINTS and _FORECAST_INTENT.search(q):
        time_col = _pick_by_mention(datetimes, q) or datetimes[0]
        value_col = _pick_value_col(numeric, q, avoid=time_col["name"])
        if value_col is not None:
            cards.append(
                {
                    "kind": "timeseries",
                    "columns": [time_col["name"], value_col["name"]],
                    "detail": (
                        f"time={time_col['name']!r}, value={value_col['name']!r}, "
                        f"points={rows}"
                    ),
                }
            )

    # 2. Between-groups comparison (t-test / ANOVA + non-parametric + effect size).
    if _COMPARE_INTENT.search(q) and groups and numeric:
        # Prefer a group named in the question; else a group whose VALUES are
        # named (e.g. "Lunch and Dinner" → the `time` column), else the first.
        group_col = (
            _pick_by_mention(groups, q)
            or _pick_by_value_mention(groups, q)
            or groups[0]
        )
        value_col = _pick_value_col(numeric, q, avoid=group_col["name"])
        # _group_unique returns 2 for booleans (whose unique_values the metadata
        # extractor leaves unset), so a boolean factor isn't a false negative.
        n_groups = _group_unique(group_col)
        if value_col is not None and n_groups >= 2:
            cards.append(
                {
                    "kind": "group_comparison",
                    "columns": [group_col["name"], value_col["name"]],
                    "detail": f"group={group_col['name']!r} ({n_groups} levels), "
                    f"value={value_col['name']!r}",
                    "n_groups": n_groups,
                }
            )

    # 3. Correlation significance (Pearson + Spearman + CI).
    if _RELATION_INTENT.search(q) and len(numeric) >= 2:
        pair = _pick_corr_pair(dataset_metadata, numeric, q)
        if pair is not None:
            cards.append(
                {
                    "kind": "correlation",
                    "columns": list(pair),
                    "detail": f"pair={pair[0]!r} vs {pair[1]!r}",
                }
            )

    # 4. Categorical association (chi-square + Cramér's V).
    if _CAT_ASSOC_INTENT.search(q) and len(groups) >= 2:
        a, b = groups[0], groups[1]
        b = _pick_by_mention([c for c in groups if c["name"] != a["name"]], q) or b
        cards.append(
            {
                "kind": "cat_association",
                "columns": [a["name"], b["name"]],
                "detail": f"{a['name']!r} × {b['name']!r}",
            }
        )

    # 5. Feature importance + baseline (rides on modeling; anti-fake-confidence).
    #    Gated on the SAME cost budget the tier planner uses for a single model
    #    (Codex P1 #4): permutation_importance on top of training is the slowest
    #    card, so a large rows×features dataset must not route it — it would blow
    #    the 30s sandbox budget. The directive further caps repeats + samples.
    if _IMPORTANCE_INTENT.search(q):
        target = _match_by_name(columns_info)
        n_features = max(0, len(columns_info) - 1)
        cost = rows * max(1, n_features)
        if (
            target is not None
            and n_features >= 2
            and rows >= _ROW_FLOOR
            and cost <= _LIGHT_COST_BUDGET
        ):
            cards.append(
                {
                    "kind": "feature_importance",
                    "columns": [target["name"]],
                    "detail": f"target={target['name']!r}, features={n_features}",
                    "task": _classify_task(target),
                }
            )

    # Correlation-vs-categorical disambiguation (Codex P1 #3): when the question
    # is really a categorical-association question, do NOT ALSO run a numeric
    # correlation on unrelated columns the user never named. Drop correlation if
    # a cat_association card exists and neither correlation column was named.
    if any(c["kind"] == "cat_association" for c in cards):
        ql = q.lower()
        cards = [
            c
            for c in cards
            if c["kind"] != "correlation"
            or all(str(col).lower() in ql for col in c["columns"])
        ]

    # Priority order then truncate to the sandbox budget.
    priority = {
        "timeseries": 0,
        "group_comparison": 1,
        "feature_importance": 2,
        "correlation": 3,
        "cat_association": 4,
    }
    cards.sort(key=lambda c: priority.get(c["kind"], 9))
    selected = cards[:_MAX_METHOD_CARDS]

    if not selected:
        return {
            "methods": [],
            "reason": "no inferential/temporal intent detected — EDA only",
        }
    return {
        "methods": selected,
        "reason": "; ".join(f"{c['kind']}({c['detail']})" for c in selected),
    }


def method_directive(plan: Dict[str, Any]) -> str:
    """Render the method plan as a hard prompt constraint. Empty when no methods."""
    methods = plan.get("methods") or []
    if not methods:
        return ""

    lines: List[str] = [
        "## Required Statistical Methods (hard constraint — in addition to EDA)",
        "The question calls for the specific inferential/temporal analysis below. "
        "You MUST run exactly these (scipy/statsmodels/sklearn are available) and "
        "report the named quantities. Seed everything (already required). Record "
        "each result in the summary under a top-level "
        '`"statistical_tests"` list of '
        "`{test, statistic, p_value, effect_size, significant, interpretation}` "
        "objects, and cite the p-value/effect size in `key_findings`. Frame all "
        "findings as EXPLORATORY ASSOCIATION, never causal. If an assumption "
        "fails (tiny n, non-normal, empty group), say so and prefer the "
        "non-parametric option rather than skipping the test.",
    ]

    for i, card in enumerate(methods, 1):
        kind = card["kind"]
        cols = card.get("columns", [])
        if kind == "timeseries":
            t, v = cols[0], cols[1]
            lines.append(
                f"{i}. TIME-SERIES FORECAST of {v!r} over {t!r}: parse {t!r} with "
                "pd.to_datetime, sort, set as index, and coerce to a regular "
                "frequency (resample + interpolate if irregular). Hold out the last "
                "~20% as a backtest. Fit ONE statsmodels model. If you need a "
                "prediction interval, prefer `ARIMA(order=(1,1,1))` — its "
                "`get_forecast(...).conf_int()` gives native intervals; use "
                "`ExponentialSmoothing` (ETS) only when a clear seasonal period is "
                "plausible, and for ETS derive an interval from the residual std "
                "(mean ± 1.96·resid_std) since it has no native conf_int. NEVER "
                "auto_arima or an order grid. Also compute a naive last-value "
                "baseline. Report MAE and RMSE for BOTH on the holdout, forecast "
                "the next horizon, and state 'forecast NOT reliable' in "
                "key_findings if the model does not beat the naive baseline. Plot "
                "history + fitted + forecast (+ interval band if available) in the "
                "PNG. If statsmodels import or fit fails, fall back to a moving-"
                "average trend line and say so — never crash the analysis."
            )
        elif kind == "group_comparison":
            g, v = cols[0], cols[1]
            n_groups = int(card.get("n_groups") or 2)
            if n_groups == 2:
                lines.append(
                    f"{i}. TWO-GROUP COMPARISON of {v!r} by {g!r}: run Welch's t-test "
                    "`scipy.stats.ttest_ind(a, b, equal_var=False)` AND the "
                    "non-parametric `scipy.stats.mannwhitneyu(a, b)`. Compute Cohen's "
                    "d as the effect size. Report both p-values, the effect size, and "
                    "significance at α=0.05. Visualize with a boxplot or violin of "
                    f"{v!r} split by {g!r}."
                )
            else:
                lines.append(
                    f"{i}. MULTI-GROUP COMPARISON of {v!r} across the {n_groups} "
                    f"levels of {g!r}: run one-way ANOVA `scipy.stats.f_oneway(*groups)` "
                    "AND the non-parametric `scipy.stats.kruskal(*groups)`. Compute "
                    "eta-squared as the effect size (SS_between / SS_total). Report the "
                    "F statistic, both p-values, effect size, and significance at "
                    f"α=0.05. Visualize with a boxplot of {v!r} by {g!r}."
                )
        elif kind == "correlation":
            a, b = cols[0], cols[1]
            lines.append(
                f"{i}. CORRELATION SIGNIFICANCE between {a!r} and {b!r}: run "
                "`scipy.stats.pearsonr` AND `scipy.stats.spearmanr` on the pairwise "
                "non-null rows. Report r/rho, both p-values, the sample size n, and a "
                "95% confidence interval for Pearson r (Fisher z-transform). State "
                "whether the association is significant at α=0.05. Visualize with a "
                "scatter plot + fitted line."
            )
        elif kind == "cat_association":
            a, b = cols[0], cols[1]
            lines.append(
                f"{i}. CATEGORICAL ASSOCIATION between {a!r} and {b!r}: build a "
                "`pd.crosstab`, run `scipy.stats.chi2_contingency`, and compute "
                "Cramér's V as the effect size. Report the chi-square statistic, "
                "p-value, degrees of freedom, and Cramér's V. State significance at "
                "α=0.05. Visualize the contingency table as a heatmap."
            )
        elif kind == "feature_importance":
            target = cols[0]
            task = card.get("task", "classification")
            lines.append(
                f"{i}. FEATURE IMPORTANCE for predicting {target!r} (a {task} task): "
                "after training ONE model on a train/test split, ALSO fit a "
                f"`Dummy{'Classifier' if task == 'classification' else 'Regressor'}` "
                "baseline. Compute `sklearn.inspection.permutation_importance` on the "
                "HELD-OUT test set (n_repeats=3, random_state=42, and if the test "
                "set exceeds 2000 rows subsample it to 2000 with random_state=42 to "
                "stay within the time budget) — NOT impurity importances — and "
                "report the top-5 features by mean importance in `key_findings` and "
                'under a `"feature_importance"` summary key. Only claim the model is '
                "useful if it beats the dummy baseline; otherwise say so explicitly."
            )

    lines.append(
        "If the ANALYSIS TIER above is `skip` and a method here needs modeling "
        "(feature importance), do the statistical tests that don't require model "
        "training and note the tier constraint for the rest."
    )
    return "\n".join(lines)


# --- method-planner column helpers --------------------------------------

# Numeric columns whose NAME reads as an identifier/index (Codex P1 #9). The
# metadata extractor's `is_id_like` only fires on a narrow name set AND ~unique
# values; a monotonic `project_number` (1..N) slips through and would win the
# highest-variance value pick. Excluding these from correlation/value selection
# is safe — a genuine measurement (`rework_cost`) never matches these tokens.
_IDISH_NUMERIC_NAME = re.compile(
    r"(^|_)(id|no|num|number|idx|index|code|seq|sequence|key|rank|row)s?$"
    r"|^(id|no|num|number|idx|index|code|seq|key|rank|row)$",
    re.IGNORECASE,
)


def _is_idish_name(name: str) -> bool:
    return bool(_IDISH_NUMERIC_NAME.search(str(name or "")))


def _group_unique(col: Dict[str, Any]) -> int:
    """Level count for a group factor. Booleans have no ``unique_values`` in the
    real extractor metadata, so treat them as 2 (Codex P2 #8)."""
    unique = int(col.get("unique_values") or 0)
    if col.get("role") == "boolean":
        return unique or 2
    return unique


def _numeric_cols(columns_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        c
        for c in columns_info
        if c.get("role") == "numeric"
        and not c.get("is_id_like")
        and not _is_idish_name(c.get("name", ""))
    ]


def _group_cols(columns_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for c in columns_info:
        if c.get("is_id_like"):
            continue
        if c.get("role") not in {"categorical", "boolean"}:
            continue
        unique = int(c.get("unique_values") or 0)
        # boolean has no unique_values populated; treat as 2 levels.
        if c.get("role") == "boolean":
            unique = unique or 2
        if 2 <= unique <= _GROUP_CARD_CAP:
            out.append(c)
    return out


def _datetime_cols(columns_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = [c for c in columns_info if c.get("role") == "datetime"]
    if out:
        return out
    # Fallback: a text/unknown column whose name reads as a time axis (dates
    # frequently arrive unparsed as object dtype).
    for c in columns_info:
        if c.get("role") in {"categorical", "unknown"} and _DATE_NAME.search(
            str(c.get("name") or "")
        ):
            out.append(c)
    return out


def _pick_by_mention(
    cols: List[Dict[str, Any]], question: str
) -> Optional[Dict[str, Any]]:
    """First column whose name appears (case-insensitive) in the question."""
    q = (question or "").lower()
    for c in cols:
        name = str(c.get("name") or "").lower()
        if name and name in q:
            return c
    return None


def _pick_by_value_mention(
    cols: List[Dict[str, Any]], question: str
) -> Optional[Dict[str, Any]]:
    """First categorical column whose sampled VALUES appear in the question.

    Handles "does tip differ between Lunch and Dinner?" where the user names the
    category levels (Lunch/Dinner) rather than the column (`time`). Uses the
    ``top_values`` the extractor records for low-cardinality categoricals.
    """
    q = (question or "").lower()
    for c in cols:
        top = c.get("top_values")
        if not isinstance(top, dict):
            continue
        for val in top:
            sval = str(val).strip().lower()
            # Guard against 1-char or numeric-looking levels matching noise.
            if len(sval) >= 3 and sval in q:
                return c
    return None


def _pick_value_col(
    numeric: List[Dict[str, Any]], question: str, *, avoid: str = ""
) -> Optional[Dict[str, Any]]:
    """Numeric column to analyze: mentioned in the question, else highest-variance."""
    candidates = [c for c in numeric if c["name"] != avoid]
    if not candidates:
        return None
    mentioned = _pick_by_mention(candidates, question)
    if mentioned is not None:
        return mentioned
    # Most variance → most interesting to compare. std may be absent (0.0 default).
    return max(candidates, key=lambda c: abs(float(c.get("std") or 0.0)))


def _pick_corr_pair(
    dataset_metadata: Dict[str, Any],
    numeric: List[Dict[str, Any]],
    question: str,
) -> Optional[Tuple[str, str]]:
    """Pick the numeric pair to correlate.

    Priority: two numeric columns explicitly named in the question > the
    precomputed strongest-correlation pair from metadata > the first two
    numeric columns.
    """
    names = [c["name"] for c in numeric]
    q = (question or "").lower()
    mentioned = [n for n in names if n.lower() in q]
    if len(mentioned) >= 2:
        return (mentioned[0], mentioned[1])
    top = dataset_metadata.get("top_corr_pair") or {}
    a, b = top.get("col_a"), top.get("col_b")
    if a in names and b in names:
        return (str(a), str(b))
    if len(names) >= 2:
        return (str(names[0]), str(names[1]))
    return None


def _pick_target_column(
    columns_info: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Return the target column dict, or None if nothing works.

    Priority: name pattern match > last column fallback.
    """
    matched = _match_by_name(columns_info)
    if matched is not None:
        return matched

    # Fallback: last column. Many sklearn teaching datasets follow the
    # "features on the left, target on the right" convention.
    last = columns_info[-1] if columns_info else None
    if last is None:
        return None
    if last.get("is_id_like"):
        # ID in the last column is the usual export shape with an
        # index, not a target. Refuse.
        return None
    if last.get("role") not in {"numeric", "categorical", "boolean"}:
        return None
    return last


def _match_by_name(
    columns_info: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    for pattern in _TARGET_NAME_PATTERNS:
        for col in columns_info:
            name = str(col.get("name") or "")
            if not name:
                continue
            if pattern.match(name) or pattern.search(name):
                if col.get("is_id_like"):
                    continue
                if col.get("role") not in {
                    "numeric",
                    "categorical",
                    "boolean",
                }:
                    continue
                return col
    return None


# --------------------------------------------------------------------------
# task classification
# --------------------------------------------------------------------------


def _classify_task(target: Dict[str, Any]) -> str:
    role = target.get("role")
    unique = int(target.get("unique_values") or 0)

    if role == "boolean":
        return "classification"
    if role == "categorical":
        return "classification"
    if role == "numeric":
        # Small unique count on a numeric column almost always means
        # labels stored as ints (0/1, 1-5 rating, 3-8 quality). Treat
        # those as classification so the confusion matrix is meaningful.
        if unique < 10:
            return "classification"
        return "regression"
    # Unknown role — default to classification, the cheaper of the two.
    return "classification"


def _models_for_task(task: str) -> List[str]:
    if task == "classification":
        return ["RandomForestClassifier", "LogisticRegression"]
    return ["RandomForestRegressor", "Ridge"]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _disabled(reason: str) -> Dict[str, Any]:
    return {
        "enabled": False,
        "target_column": None,
        "task": None,
        "models": [],
        "reason": reason,
    }
