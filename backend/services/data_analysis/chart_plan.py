"""Deterministic chart planner for EDA.

Produces a JSON plan describing which charts to render from dataset metadata,
using pure heuristics (no LLM). This replaces analysis_planner.py for the
must-ship EDA path — the LLM planner is deferred to stretch work around
model comparison, where it has a real decision to make (is this dataset
labeled? which task type?).

Design rationale (from niuyp-main-design-20260417-183703.md):
- Must-ship EDA needs zero LLM in the critical path — one less cloud round
  trip to fail, no JSON schema retries, no prompt engineering surface.
- Heuristics are richer than the existing `_pick_relevant_column` so charts
  are actually informative, not just "numeric column 0 vs numeric column 1".
- Output shape matches what chart_executor.py consumes, so when/if the LLM
  planner returns for model comparison, the executor doesn't care about
  the plan's origin.

Input contract: `dataset_metadata["columns_info"]` is a list of per-column
dicts produced by `DataAnalysisAgent._extract_dataset_info`. Each entry has:
  - `name`: raw column name from the dataset
  - `role`: one of "numeric" / "categorical" / "boolean" / "datetime" /
    "unknown" — **semantic role** we filter by, not raw pandas dtype
  - `unique_values`: distinct value count (present for numeric + categorical)
  - `is_id_like`: True when unique/non_null ratio ≥ 0.9 — excludes IDs,
    timestamps-as-ints, ZIP codes, and other near-unique sequences from
    heuristic picks (they produce useless charts)
  - `std`: present for numeric role, used to rank by variance

Heuristic selection (target: 3-5 charts on a typical mixed dataset):
  - Histograms: top 3 numeric columns by std (skip zero-variance and ID-like).
  - Scatter:    validated `top_corr_pair` from metadata, falling back to the
                two highest-std numerics.
  - Heatmap:    correlation matrix of all usable numeric columns when >= 3.
  - Bar:        lowest-cardinality categorical (2-20 unique, not ID-like).
  - Boxplot:    top numeric × low-cardinality categorical when both exist.

Output chart schema (normalized):
  {
    "id": "chart_01_histogram",
    "type": "histogram",
    "params": {...type-specific kwargs...},
    "source_columns": ["column_a", "column_b"]
  }

`source_columns` is the authoritative list of column names the chart
depends on. The executor MUST sanitize these before interpolating into
generated Python code — column names can contain quotes/backslashes and
the sanitization responsibility lives in chart_executor.py (see
_sanitize_column_name there). The planner does NOT attempt to sanitize;
it emits raw names so the executor can assert-then-sanitize consistently
for every chart. Any chart whose source_columns fail sanitization is
dropped by the executor with a CHART_FAILED_JSON marker.

All logic is pure functions on a metadata dict, making unit tests trivial
(no sandbox, no network, no pandas required at test time beyond what the
fixture needs to construct).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

# Cardinality range that makes a categorical column worth a bar/boxplot.
# Below 2 = no variation. Above 20 = unreadable chart.
_CATEGORICAL_MIN_UNIQUE = 2
_CATEGORICAL_MAX_UNIQUE = 20

# Row-count threshold above which model comparison is automatically disabled
# (training RandomForest etc. in the 10s-timeout sandbox is unreliable on
# large data). Planner emits the flag; executor enforces.
_MODEL_COMPARISON_ROW_LIMIT = 50_000

# Cap on histograms so the grid doesn't explode on wide datasets.
_MAX_HISTOGRAMS = 3


def eda_plan_from_metadata(
    dataset_metadata: Dict[str, Any],
    user_question: str = "",
) -> Dict[str, Any]:
    """Produce a deterministic EDA plan from dataset metadata + user question.

    Args:
        dataset_metadata: Output shape from
            ``DataAnalysisAgent._extract_dataset_info``. Expected keys:
            ``rows``, ``columns``, ``columns_info`` (list of per-column
            dicts with ``role``, ``is_id_like``, ``unique_values``,
            ``std``, etc.), optional ``top_corr_pair``.
        user_question: Free-form question. Classified into one of 7
            intent buckets via ``_classify_intent``; the intent drives
            which subset of chart pickers fires. Empty / unrecognized
            questions fall back to ``generic_eda`` (the historical
            all-5-types behavior, preserved for backward compat).

    Returns:
        Plan dict with ``schema_version``, ``eda.charts`` (ordered list
        of chart specs in normalized schema), ``model_comparison``
        (intent-gated), and ``rationale``. JSON-serializable.
        Includes ``intent`` field for observability — operators can grep
        logs / inspect responses to see how their question was classified.
    """
    columns_info: List[Dict[str, Any]] = dataset_metadata.get("columns_info") or []
    rows = int(dataset_metadata.get("rows") or 0)

    numeric = _numeric_columns(columns_info)
    categorical = _categorical_columns(columns_info)

    intent = _classify_intent(user_question, numeric, categorical)
    logger.info(
        "chart_plan: intent=%s (q=%r, numeric=%d, categorical=%d)",
        intent, (user_question or "")[:80], len(numeric), len(categorical),
    )

    raw_charts: List[tuple[str, Dict[str, Any], List[str]]] = []
    rationale_parts: List[str] = [f"Intent: {intent}."]

    # Which pickers fire is intent-driven. The mapping is intentionally
    # explicit (no clever lookup table) so a code reader can see at a
    # glance which charts each intent gets. `generic_eda` reproduces the
    # historical behavior — all 5 pickers in the original order.
    want_hist = intent in {"distribution_univariate", "generic_eda"}
    want_scatter = intent in {
        "relationship_bivariate", "supervised_regression", "generic_eda",
    }
    want_heatmap = intent in {"correlation_matrix", "generic_eda"}
    want_bar = intent in {"categorical_distribution", "generic_eda"}
    want_box = intent in {"categorical_vs_numeric", "generic_eda"}

    if want_hist:
        hist_items, hist_note = _pick_histograms(numeric)
        raw_charts.extend(hist_items)
        if hist_note:
            rationale_parts.append(hist_note)

    if want_scatter:
        scatter_item, scatter_note = _pick_scatter(
            numeric, dataset_metadata.get("top_corr_pair")
        )
        if scatter_item:
            raw_charts.append(scatter_item)
        if scatter_note:
            rationale_parts.append(scatter_note)

    if want_heatmap:
        heatmap_item, heatmap_note = _pick_heatmap(numeric)
        if heatmap_item:
            raw_charts.append(heatmap_item)
        if heatmap_note:
            rationale_parts.append(heatmap_note)

    if want_bar:
        bar_item, bar_note = _pick_bar(categorical)
        if bar_item:
            raw_charts.append(bar_item)
        if bar_note:
            rationale_parts.append(bar_note)

    if want_box:
        boxplot_item, box_note = _pick_boxplot(numeric, categorical)
        if boxplot_item:
            raw_charts.append(boxplot_item)
        if box_note:
            rationale_parts.append(box_note)

    # Normalize into the final chart schema. Stable IDs let the executor
    # correlate partial-failure markers back to the plan, and the explicit
    # source_columns list makes the sanitization contract unambiguous.
    charts: List[Dict[str, Any]] = []
    for idx, (chart_type, params, source_cols) in enumerate(raw_charts):
        charts.append(
            {
                "id": f"chart_{idx:02d}_{chart_type}",
                "type": chart_type,
                "params": params,
                "source_columns": source_cols,
            }
        )

    if not charts:
        rationale_parts.append(
            "No charts selected: metadata contains no usable numeric or "
            "low-cardinality categorical columns (after excluding ID-like)."
        )

    # Model-comparison decision (stretch goal). Lives in a sibling module
    # so the EDA planner stays metadata-only. Planner returns a dict with
    # exactly the shape this plan embeds, so we can splice it in directly.
    from backend.services.data_analysis.analysis_planner import (
        decide_model_comparison,
    )

    try:
        model_comparison = decide_model_comparison(dataset_metadata)
    except Exception as exc:
        # Never let the planner kill EDA. Log and fall back to disabled.
        logger.warning(
            "model-comparison planner failed, falling back to disabled: %s",
            exc,
        )
        model_comparison = {
            "enabled": False,
            "target_column": None,
            "task": None,
            "models": [],
            "reason": f"planner raised {type(exc).__name__}",
        }

    # Intent gating for model comparison.
    #
    # Three regimes:
    #  - generic_eda: preserve historical behavior — let decide_model_comparison's
    #    own logic stand (auto-detect target, fire training if usable).
    #  - supervised_*: also let it stand (intent agrees with the auto-detect).
    #  - any other EDA-only intent (distribution_univariate, correlation_matrix,
    #    categorical_*, relationship_bivariate): suppress training. User asked
    #    for a specific chart; don't burn sandbox time on RandomForests they
    #    didn't request.
    _EDA_ONLY_INTENTS = {
        "distribution_univariate",
        "correlation_matrix",
        "categorical_distribution",
        "categorical_vs_numeric",
        "relationship_bivariate",
    }
    if intent in _EDA_ONLY_INTENTS and model_comparison.get("enabled"):
        model_comparison = {
            **model_comparison,
            "enabled": False,
            "reason": (
                f"intent={intent} does not request modeling; "
                f"original gate would have enabled "
                f"(target={model_comparison.get('target_column')!r})"
            ),
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "eda": {"charts": charts},
        "model_comparison": model_comparison,
        "rationale": " ".join(rationale_parts).strip()
        or "Deterministic plan from dataset metadata.",
        "user_question": user_question[:500] if user_question else "",
        "intent": intent,
    }


# --- intent classification ----------------------------------------------
#
# Heuristic, regex-keyword based — chosen over LLM for three reasons:
#  1. Latency: planner is synchronous and must stay < 50ms. No cloud call.
#  2. Determinism: agentic_loop.py's response cache keys on the rendered
#     prompt; if the planner output drifts run-to-run the cache misses.
#     Same question → same intent guaranteed.
#  3. Maintainability: keyword list edited by a person, no model versioning
#     concerns 6 months out.
#
# Priority order is INTENTIONAL — earlier intents shadow later ones. This
# resolves ambiguity (e.g. "correlation heatmap" matches both
# correlation_matrix and relationship_bivariate; we want heatmap).

_INTENT_PATTERNS: List[tuple[str, re.Pattern]] = [
    # Supervised regression FIRST so a query like "predict mpg using linear
    # regression" matches regression on the word "regression" rather than
    # falling into supervised_classification on "predict". Both gate
    # model_comparison the same way so behavior is similar; the difference
    # matters for the intent label / future task-type-specific chart picks.
    (
        "supervised_regression",
        re.compile(
            r"\b(regress(ion)?|forecast|estimate\s+the|r\s*[-_]?squared|rmse|"
            r"linear\s+model)",
            re.IGNORECASE,
        ),
    ),
    (
        "supervised_classification",
        re.compile(
            r"\b(predict|classif(y|ier|ication)|train\s+a?\s*(model|classifier)|"
            r"confusion\s+matrix|roc\b|auc\b)",
            re.IGNORECASE,
        ),
    ),
    # Correlation matrix BEFORE bivariate so "correlation heatmap" → heatmap,
    # not scatter.
    (
        "correlation_matrix",
        re.compile(
            r"\b(correlation\s+(matrix|heatmap)|heatmap|all\s+numeric|"
            r"pairwise\s+correlation)",
            re.IGNORECASE,
        ),
    ),
    # "X by Y" pattern → boxplot of X grouped by Y. Checked BEFORE
    # categorical_distribution so "price by region" doesn't get classified
    # as just "show region counts".
    (
        "categorical_vs_numeric",
        re.compile(
            r"\b(\w+\s+by\s+\w+|compare\s+\w+\s+(across|by|between)|"
            r"distribution\s+of\s+\w+\s+by\s+\w+|boxplot|box\s+plot)",
            re.IGNORECASE,
        ),
    ),
    (
        "distribution_univariate",
        re.compile(
            r"\b(distribution|histogram|density|spread|frequenc(y|ies))",
            re.IGNORECASE,
        ),
    ),
    # Bivariate scatter — "X vs Y", "relate", "scatter". Avoid matching
    # the word "correlation" alone (that goes to correlation_matrix above).
    (
        "relationship_bivariate",
        re.compile(
            r"\b(scatter|\w+\s+vs\.?\s+\w+|\w+\s+versus\s+\w+|"
            r"relationship\s+between|relate(d|s)?\s+to)",
            re.IGNORECASE,
        ),
    ),
    (
        "categorical_distribution",
        re.compile(
            r"\b(count\s+of|how\s+many|breakdown|value\s+counts|"
            r"bar\s+chart\s+of|frequenc(y|ies)\s+of\s+\w+)",
            re.IGNORECASE,
        ),
    ),
]


def _classify_intent(
    question: str,
    numeric: List[Dict[str, Any]],
    categorical: List[Dict[str, Any]],
) -> str:
    """Classify a user question into one of 8 intent buckets.

    Returns the FIRST matching intent (priority-ordered), or
    ``generic_eda`` when nothing matches. ``generic_eda`` is the safe
    default — it preserves the historical 5-chart behavior, so any
    dataset that previously rendered will continue to render.

    Note: ``numeric`` / ``categorical`` are passed in to support future
    column-name extraction (PR #2). The current implementation only uses
    them implicitly via the fallback chain.
    """
    if not question or len(question.strip()) < 3:
        return "generic_eda"

    for intent_name, pattern in _INTENT_PATTERNS:
        if pattern.search(question):
            return intent_name

    return "generic_eda"


# --- column classification helpers --------------------------------------


def _numeric_columns(columns_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return plot-worthy numeric columns sorted by descending std.

    Filters out:
    - non-numeric roles (boolean, datetime, categorical, unknown)
    - zero-std columns (constants — useless histogram, cannot correlate)
    - ID-like columns (near-unique sequences — IDs, timestamps-as-int,
      ZIP codes — would dominate variance ranking and produce garbage)
    """
    numeric: List[Dict[str, Any]] = []
    for col in columns_info:
        if col.get("role") != "numeric":
            continue
        if col.get("is_id_like"):
            continue
        if "std" not in col:
            continue
        std = float(col.get("std") or 0.0)
        if std <= 0.0:
            continue
        numeric.append(col)
    numeric.sort(key=lambda c: float(c.get("std") or 0.0), reverse=True)
    return numeric


def _categorical_columns(
    columns_info: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return low-cardinality categorical columns (2-20 unique, not ID-like)."""
    cats: List[Dict[str, Any]] = []
    for col in columns_info:
        if col.get("role") != "categorical":
            continue
        if col.get("is_id_like"):
            continue
        unique = int(col.get("unique_values") or 0)
        if _CATEGORICAL_MIN_UNIQUE <= unique <= _CATEGORICAL_MAX_UNIQUE:
            cats.append(col)
    cats.sort(key=lambda c: int(c.get("unique_values") or 0))
    return cats


# --- chart pickers ------------------------------------------------------
#
# Each picker returns `(chart_type, params, source_columns)` plus an optional
# human-readable rationale note. Returning the components flat makes the
# normalize-to-schema step in `eda_plan_from_metadata` trivial, and keeps the
# pickers free of the id/source_columns boilerplate.


def _pick_histograms(
    numeric: List[Dict[str, Any]],
) -> tuple[List[tuple[str, Dict[str, Any], List[str]]], Optional[str]]:
    if not numeric:
        return [], None
    picked = numeric[:_MAX_HISTOGRAMS]
    items = [
        ("histogram", {"column": col["name"]}, [col["name"]]) for col in picked
    ]
    if len(picked) == 1:
        note = f"Histogram of '{picked[0]['name']}' (only variable numeric)."
    else:
        names = ", ".join(f"'{c['name']}'" for c in picked)
        note = f"Histograms of {names} (top {len(picked)} numeric by variance)."
    return items, note


def _pick_scatter(
    numeric: List[Dict[str, Any]],
    top_corr_pair: Optional[Dict[str, Any]],
) -> tuple[
    Optional[tuple[str, Dict[str, Any], List[str]]], Optional[str]
]:
    if len(numeric) < 2:
        return None, None

    numeric_names = {c["name"] for c in numeric}

    # Validate top_corr_pair BEFORE trusting it. Stale metadata, renamed
    # columns, or a pair that no longer passes numeric filtering would all
    # produce an invalid scatter spec. When invalid, fall back to the
    # variance-ranked default.
    if top_corr_pair and "col_a" in top_corr_pair and "col_b" in top_corr_pair:
        a = top_corr_pair["col_a"]
        b = top_corr_pair["col_b"]
        if a in numeric_names and b in numeric_names and a != b:
            rho = top_corr_pair.get("abs_rho")
            rho_str = (
                f"|ρ|={float(rho):.2f}" if rho is not None else "strongest pair"
            )
            return (
                ("scatter", {"x": a, "y": b}, [a, b]),
                f"Scatter of '{a}' vs '{b}' ({rho_str}).",
            )
        # top_corr_pair referenced columns that dropped out (e.g., marked
        # id_like after extraction) — silently fall through to the default.

    a = numeric[0]["name"]
    b = numeric[1]["name"]
    return (
        ("scatter", {"x": a, "y": b}, [a, b]),
        f"Scatter of '{a}' vs '{b}' (top-2 numeric by variance).",
    )


def _pick_heatmap(
    numeric: List[Dict[str, Any]],
) -> tuple[
    Optional[tuple[str, Dict[str, Any], List[str]]], Optional[str]
]:
    if len(numeric) < 3:
        return None, None
    cols = [c["name"] for c in numeric]
    return (
        ("heatmap", {"columns": cols}, list(cols)),
        f"Correlation heatmap of {len(cols)} numeric columns.",
    )


def _pick_bar(
    categorical: List[Dict[str, Any]],
) -> tuple[
    Optional[tuple[str, Dict[str, Any], List[str]]], Optional[str]
]:
    if not categorical:
        return None, None
    col = categorical[0]
    return (
        (
            "bar",
            {"column": col["name"], "metric": "count"},
            [col["name"]],
        ),
        f"Bar chart of '{col['name']}' ({col['unique_values']} categories).",
    )


def _pick_boxplot(
    numeric: List[Dict[str, Any]],
    categorical: List[Dict[str, Any]],
) -> tuple[
    Optional[tuple[str, Dict[str, Any], List[str]]], Optional[str]
]:
    if not numeric or not categorical:
        return None, None
    num = numeric[0]["name"]
    cat = categorical[0]["name"]
    return (
        ("boxplot", {"column": num, "by": cat}, [num, cat]),
        f"Boxplot of '{num}' by '{cat}'.",
    )


# --- model comparison gating --------------------------------------------


def _model_comparison_reason(
    rows: int, columns_info: List[Dict[str, Any]]
) -> str:
    if rows > _MODEL_COMPARISON_ROW_LIMIT:
        return (
            f"dataset has {rows} rows, exceeds "
            f"{_MODEL_COMPARISON_ROW_LIMIT} row cap for live demo training"
        )
    if not columns_info:
        return "no columns detected"
    return "model comparison is a stretch goal; disabled for must-ship release"
