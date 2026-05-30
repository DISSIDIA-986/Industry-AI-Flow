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
    columns_info: List[Dict[str, Any]] = (
        dataset_metadata.get("columns_info") or []
    )
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
        return _tier("skip", f"{rows} rows exceed the {_ROW_CAP} cap for live model training")
    if n_numeric < 2 or rows < _ROW_FLOOR:
        return _tier("skip", "not enough numeric data to train a meaningful model")
    if target is None:
        if asked:
            return _tier("light", "no obvious target column; attempting one bounded model per request")
        return _tier("skip", "no recognizable target column; EDA only")
    if task == "classification":
        unique = int(target.get("unique_values") or 0)
        if unique > _CLASS_CARDINALITY_CAP:
            return _tier("skip", f"target {target['name']!r} has {unique} classes — too many for quick training")
    if asked:
        t = "full" if cost <= _LIGHT_COST_BUDGET else "light"
        return _tier(t, f"requested modeling; target={target['name']!r}, task={task}")
    if cost <= _LIGHT_COST_BUDGET:
        return _tier("light", f"cheap dataset — auto single model (target={target['name']!r}, task={task})")
    return _tier("skip", "large dataset — advanced modeling skipped unless explicitly requested")


def tier_directive(plan: Dict[str, Any]) -> str:
    """Render the tier decision as a hard prompt constraint for the agentic round."""
    t = plan.get("tier", "skip")
    reason = plan.get("reason", "")
    if t == "skip":
        return (
            f"ANALYSIS TIER = skip (reason: {reason}). Do EDA only. Do NOT train any "
            "ML model. If the user explicitly asked for modeling that this tier "
            'cannot support, explain why in the answer and set produces_chart per the EDA.'
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
