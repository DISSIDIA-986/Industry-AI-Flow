"""Compose a legacy-shaped response envelope from a PlanExecutionResult.

W4 (Plan Appendix E, v3.2 APPROVED): the agentic loop returns rich
telemetry via ``PlanExecutionResult``; the frontend and existing tests
speak the legacy envelope that ``compose_eda_response`` produces. This
module is the one-way adapter.

Kept separate from ``agentic_loop.py`` so the loop stays pure (no disk
I/O, no settings coupling) and can be replaced without touching the
envelope contract the UI depends on.
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional

from backend.services.data_analysis.agentic_loop import PlanExecutionResult

logger = logging.getLogger(__name__)

# Stable marker so the frontend and debug UIs can identify agentic runs.
# Matches the pattern of "deterministic_planner" in report_composer.
#
# NAMING HISTORY: Plan Appendix E originally codenamed this "GLM-5", but the
# actual model (Zhipu's `glm-4.7`) was unchanged throughout. The literal
# "glm5_agent" string is kept as the public envelope contract so existing
# frontend conditionals, env-var configurations, and downstream consumers
# don't break. User-visible display strings ("GLM-4.7 Agent") live at the
# UI layer and reflect the real model.
AGENTIC_MODE = "glm5_agent"


def compose_agentic_response(
    *,
    result: PlanExecutionResult,
    question: str,
    dataset_metadata: Dict[str, Any],
    data_file_path: str,
    analysis_tier: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Map a ``PlanExecutionResult`` onto the legacy analyze_query envelope.

    The shape must match ``report_composer.compose_eda_response`` so the
    frontend's ``data-analysis/page.tsx`` renders both paths uniformly:
    ``charts``, ``visualizations`` (list of ``{filename, path}``),
    ``analysis_summary.key_findings``, ``code_generation.mode``, etc.

    Failure modes produce an envelope with ``success=False`` and a
    human-readable ``answer`` — the UI already handles this.
    """
    plan = result.final_plan or {}
    summary = result.final_summary or {}

    visualizations, chart_entry = _persist_chart(result, question)

    charts = [chart_entry] if chart_entry else []
    key_findings = _extract_key_findings(summary, plan)
    rationale = _build_rationale(plan, result)

    answer = _build_answer(result, plan, summary)

    fallback_reason = _fallback_reason(result)

    # Success/chart logic. A chart the plan DECLARED but the code didn't actually
    # save must not fail an otherwise-valid analysis that produced findings — e.g.
    # pure statistical hypothesis tests legitimately yield p-values with no chart.
    # Show the findings (the UI has a chartless-result path) instead of a hard
    # "Analysis Error". Only a code failure, or an empty result with neither chart
    # nor findings, is a real failure.
    chart_ok = bool(chart_entry)
    if _plan_produces_chart(plan):
        success = result.success and (chart_ok or bool(key_findings))
    else:
        success = result.success
    chart_missing = bool(success and _plan_produces_chart(plan) and not chart_ok)

    return {
        "success": success,
        "answer": answer,
        "charts": charts,
        "visualizations": visualizations,
        "code": result.final_code or "",
        "analysis_summary": {
            "key_findings": key_findings,
            "rationale": rationale,
        },
        "analysis_tier": analysis_tier,
        "code_generation": {
            "mode": AGENTIC_MODE,
            "fallback_reason": fallback_reason,
            "chart_missing": chart_missing,
            # A2 (2026-06-04): honest degraded-success. True when a usable
            # chart was salvaged but the run wasn't fully clean (summary
            # emission failed after results were produced). The UI surfaces
            # this so a salvaged result is never presented as flawless.
            "degraded": bool(result.degraded),
            "degraded_reason": result.degraded_reason,
            "analysis_tier": (analysis_tier or {}).get("tier"),
            "repair_triggered": result.repair_triggered,
            "repair_trigger_type": result.repair_trigger_type,
            "repair_recovered": result.repair_recovered,
            "time_budget_exhausted": result.time_budget_exhausted,
            "rounds": len(result.rounds),
            "elapsed_s": round(result.total_elapsed_s, 2),
            # Cost observability — null when no round reported usage
            # (tests with stub callers, or pre-LLM error paths).
            "tokens_in": result.total_tokens_in,
            "tokens_out": result.total_tokens_out,
        },
        "dataset_info": dataset_metadata,
        "execution_time": round(result.total_elapsed_s, 2),
        # B2 (2026-06-04): surface a structured model leaderboard so the UI's
        # model-metrics-table renders (previously hardcoded disabled on the
        # agentic path, so the metrics only ever appeared as text bullets).
        "model_comparison": _structured_model_comparison(summary),
        "stdout": result.final_stdout or "",
        "stderr": _extract_stderr(result),
    }


def _plan_produces_chart(plan: Dict[str, Any]) -> bool:
    return bool(plan.get("produces_chart"))


# Metric directionality for picking the winner. Lower-is-better for error
# metrics; everything else higher-is-better.
_LOWER_IS_BETTER = {"mae", "rmse", "mse", "logloss", "log_loss", "error"}

# Substrings that mark a key as a METRIC name (not a model name). Used to
# detect and correct a transposed model_comparison (metric-keyed outer).
_METRIC_NAME_TOKENS = (
    "f1", "accuracy", "auc", "roc", "precision", "recall",
    "rmse", "mse", "r2", "rsquared", "mae", "silhouette", "logloss", "score",
)


def _looks_like_metric(key: str) -> bool:
    k = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return any(tok in k for tok in _METRIC_NAME_TOKENS)


def _normalize_mc_orientation(mc: Dict[str, Any]) -> Dict[str, Any]:
    """GLM-4.7 emits model_comparison in EITHER orientation:
    ``{Model: {metric: v}}`` (what we ask for) or the transposed
    ``{metric: {Model: v}}``. The frontend table and our winner logic assume
    model-outer; a transposed dict renders metrics as rows and mislabels the
    "BEST" badge (caught in browser QA 2026-06-04). Detect the metric-keyed
    orientation (outer keys look like metric names, inner keys do not) and
    transpose back to model-outer."""
    if not mc:
        return mc
    outer = list(mc.keys())
    inner = [k for v in mc.values() if isinstance(v, dict) for k in v.keys()]
    if not inner:
        return mc
    outer_metric = sum(_looks_like_metric(k) for k in outer)
    inner_metric = sum(_looks_like_metric(k) for k in inner)
    # Transpose only when the outer axis is clearly the metric axis and the
    # inner axis clearly is not (avoids flipping a genuine model-outer dict).
    if outer_metric >= max(1, (len(outer) + 1) // 2) and inner_metric == 0:
        transposed: Dict[str, Dict[str, Any]] = {}
        for metric, model_dict in mc.items():
            if isinstance(model_dict, dict):
                for model, val in model_dict.items():
                    transposed.setdefault(str(model), {})[str(metric)] = val
        if len(transposed) >= 2:
            return transposed
    return mc


def _structured_model_comparison(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Transform ``summary.model_comparison`` into the envelope shape the
    frontend ``model-metrics-table`` expects (B2).

    Frontend contract (page.tsx): renders only when ``enabled is True``;
    infers columns from the FIRST model's metric keys, then renders each row
    via ``Object.values(scores)``. So every model row MUST carry the SAME
    ordered metric keys or columns misalign. We collect the first-seen union
    of numeric metric keys and normalize every model to that key order
    (missing → omitted only if absent from all; present-everywhere stays
    aligned). Requires >= 2 models — a single model is carried by the text
    key_findings bullets, not a one-row "comparison" table.

    Shape: ``{enabled, task, winner, metrics: {Model: {metric: number}}}``.
    """
    mc = summary.get("model_comparison")
    if not isinstance(mc, dict) or not mc:
        return {"enabled": False, "reason": "no model comparison"}
    # Correct a transposed (metric-keyed) dict to model-outer BEFORE the
    # >=2-models check, so a single-metric × 2-model comparison isn't dropped.
    mc = _normalize_mc_orientation(mc)
    if len(mc) < 2:
        return {"enabled": False, "reason": "no multi-model comparison"}

    metric_order: List[str] = []
    per_model: Dict[str, Dict[str, float]] = {}
    for name, payload in mc.items():
        if not isinstance(name, str):
            continue
        row: Dict[str, float] = {}
        if isinstance(payload, dict):
            for k, v in payload.items():
                if isinstance(v, bool):  # bool is an int subclass — skip flags
                    continue
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    row[str(k)] = float(v)
                    if str(k) not in metric_order:
                        metric_order.append(str(k))
        elif isinstance(payload, (int, float)) and not isinstance(payload, bool):
            if math.isfinite(float(payload)):
                row["score"] = float(payload)
                if "score" not in metric_order:
                    metric_order.append("score")
        if row:
            per_model[name] = row

    if len(per_model) < 2 or not metric_order:
        return {"enabled": False, "reason": "no numeric metrics for >=2 models"}

    # Column alignment (Codex final review 2026-06-04): the frontend infers
    # table columns from the FIRST row's keys and renders every other row via
    # ``Object.values(scores)`` positionally. If rows had different keys, a
    # value would land under the wrong column. Keep only metrics present in
    # EVERY model (intersection, preserving first-seen order) so every row is
    # complete and positionally aligned. With the B1 prompt mandating the same
    # metric keys per model, the intersection is normally the full set.
    shared = [k for k in metric_order if all(k in row for row in per_model.values())]
    if not shared:
        return {"enabled": False, "reason": "models report no common metric"}
    metrics: Dict[str, Dict[str, float]] = {}
    for name, row in per_model.items():
        metrics[name] = {k: row[k] for k in shared}

    # Winner by the first (primary) shared metric; direction depends on it.
    primary = shared[0]
    ranked = [(n, r[primary]) for n, r in metrics.items() if primary in r]
    winner: Optional[str] = None
    if ranked:
        reverse = primary.lower() not in _LOWER_IS_BETTER
        ranked.sort(key=lambda t: t[1], reverse=reverse)
        winner = ranked[0][0]

    task = summary.get("analysis_type")
    return {
        "enabled": True,
        "task": task if isinstance(task, str) else None,
        "winner": winner,
        "primary_metric": primary,
        "metrics": metrics,
    }


def _persist_chart(
    result: PlanExecutionResult, question: str
) -> tuple[List[Dict[str, str]], Optional[Dict[str, Any]]]:
    """Write chart PNG (if present) to temp_data_dir and return the
    legacy ``{filename, path}`` visualization entry plus a chart record.

    No chart → empty visualizations, chart_entry=None.
    """
    if not result.final_chart_bytes:
        return [], None

    try:
        from backend.tools.visualization import _persist_visualization_artifacts
    except Exception as exc:  # pragma: no cover — import failure is fatal
        logger.error("visualization persister unavailable: %s", exc)
        return [], None

    try:
        persisted = _persist_visualization_artifacts(
            {"analysis_chart.png": result.final_chart_bytes}
        )
    except Exception as exc:
        logger.warning("agentic chart persist failed: %s", exc)
        return [], None

    if not persisted:
        return [], None

    entry = persisted[0]
    chart = {
        "id": "agentic_chart",
        "type": "agentic",
        "status": "ok",
        "image_filename": entry["filename"],
        "summary": question,
        "error": None,
        "params": {},
    }
    return [{"filename": entry["filename"], "path": entry["path"]}], chart


def _extract_key_findings(
    summary: Dict[str, Any], plan: Dict[str, Any]
) -> List[str]:
    """Pull key_findings from ANALYSIS_SUMMARY_JSON; synthesize when missing.

    Priority order:
      1. Explicit `key_findings` list from the summary (what the prompt asks for).
      2. Synthesize from structured fields the model commonly emits when
         it forgets key_findings — especially `model_comparison` (AUC-
         style metric dicts). This avoids showing the user a blank
         "Key Findings" panel while the real numbers sit in the raw JSON.
      3. Fall back to plan business_goal / analysis_plan prose.
    """
    findings = summary.get("key_findings")
    if isinstance(findings, list) and findings:
        return [str(f) for f in findings if f]

    # Synthesis from model_comparison — common when the query asks for
    # "AUC comparison", "ML comparison", etc. and GLM-4.7 puts results
    # under that key without a human-readable bullet list.
    mc = summary.get("model_comparison")
    if isinstance(mc, dict) and mc:
        bullets = _bullets_from_model_comparison(mc)
        if bullets:
            return bullets

    # Generic fallback: flatten any top-level numeric-or-short fields
    # into single-line bullets. Keeps the UI useful for
    # free-form summaries (correlations, counts, percentages).
    for key, value in summary.items():
        if key in ("key_findings", "chart_type", "analysis_type"):
            continue
        bullet = _format_summary_field(key, value)
        if bullet:
            return [bullet]  # one-shot synthesis; good enough for display.

    business_goal = plan.get("business_goal")
    analysis_plan = plan.get("analysis_plan")
    bullets: List[str] = []
    if business_goal:
        bullets.append(f"Goal: {business_goal}")
    if analysis_plan:
        bullets.append(f"Approach: {analysis_plan}")
    return bullets


def _bullets_from_model_comparison(mc: Dict[str, Any]) -> List[str]:
    """Turn {ModelName: {<metric>: X, <std>: Y, ...}} into sorted bullets.

    Expected shapes (any one of):
      {"RF": {"mean_auc": 0.87, "std_auc": 0.02}, ...}
      {"RF": {"auc": 0.87}, ...}
      {"RF": {"accuracy": 0.92}, ...}
      {"RF": 0.87, ...}    (bare float — metric label defaults to "score")

    Uses the actual metric name detected per-entry so accuracy/R²/etc.
    don't get mislabeled as AUC (Codex review finding, 2026-04-19).
    The first-detected metric across the dict wins for the header
    bullet — heterogeneous dicts (mixing auc + accuracy) are rare and
    degrade gracefully to the first valid entry.
    """
    # Score-key → display label. Order matters: first match wins per entry.
    _METRIC_LABELS: tuple[tuple[str, str], ...] = (
        ("mean_auc", "AUC"),
        ("auc", "AUC"),
        ("roc_auc", "AUC"),
        ("accuracy", "accuracy"),
        ("f1", "F1"),
        ("f1_score", "F1"),
        ("r2", "R²"),
        ("r_squared", "R²"),
        ("mae", "MAE"),
        ("rmse", "RMSE"),
        ("score", "score"),
    )

    scored: List[tuple[str, float, str, str]] = []  # (name, score, std_detail, metric_label)
    for name, payload in mc.items():
        if not isinstance(name, str):
            continue
        score: Optional[float] = None
        detail = ""
        label = "score"
        if isinstance(payload, dict):
            for score_key, display in _METRIC_LABELS:
                if score_key in payload:
                    raw = payload[score_key]
                    # Reject bools (bool is a subclass of int — float(True)==1.0)
                    if isinstance(raw, bool):
                        continue
                    try:
                        score = float(raw)
                        if not math.isfinite(score):
                            score = None
                            continue
                        label = display
                        # Try known std aliases in priority order. Live
                        # GLM-4.7 emissions use "std_auc" for any auc-
                        # family metric; some reports use plain "std".
                        std = (
                            payload.get("std_auc")
                            or payload.get("std")
                            or payload.get(f"std_{score_key}")
                        )
                        if std is not None:
                            try:
                                detail = f" ± {float(std):.3f}"
                            except (TypeError, ValueError):
                                pass
                        break
                    except (TypeError, ValueError):
                        continue
        elif isinstance(payload, bool):
            continue
        else:
            try:
                score = float(payload)
                if not math.isfinite(score):
                    continue
                label = "score"
            except (TypeError, ValueError):
                continue
        if score is not None:
            scored.append((name, score, detail, label))

    if not scored:
        return []

    # Heterogeneous metric guard (Codex M1): if entries report
    # different metric families (AUC vs accuracy vs MAE), ranking them
    # together is meaningless. Keep only the dominant metric and note
    # the drop in a trailing bullet so the user knows entries were
    # excluded.
    labels = {s[3] for s in scored}
    excluded = 0
    if len(labels) > 1:
        from collections import Counter
        dominant = Counter(s[3] for s in scored).most_common(1)[0][0]
        filtered = [s for s in scored if s[3] == dominant]
        excluded = len(scored) - len(filtered)
        scored = filtered

    # Higher-is-better for most metrics; MAE/RMSE are exceptions. When
    # the detected metric is an error metric, rank ascending so the
    # "best model" is the one with the lowest error.
    header_label = scored[0][3]  # metric of the first entry drives sort direction
    reverse = header_label not in ("MAE", "RMSE")
    scored.sort(key=lambda t: t[1], reverse=reverse)

    # M3: cap bullet count at 10 models (plus leader header = 11 total).
    MAX_MODELS = 10
    truncated = max(0, len(scored) - MAX_MODELS)
    shown = scored[:MAX_MODELS]

    bullets = [
        f"{name}: {label}={score:.4f}{detail}"
        for name, score, detail, label in shown
    ]
    leader = scored[0]
    bullets.insert(
        0,
        f"Best model: {leader[0]} ({leader[3]}={leader[1]:.4f}{leader[2]})",
    )
    if truncated:
        bullets.append(f"...and {truncated} more model(s) not shown")
    if excluded:
        bullets.append(
            f"Note: {excluded} entry(ies) with different metric excluded for fair ranking"
        )
    return bullets


def _format_summary_field(key: str, value: Any) -> Optional[str]:
    """Render a single top-level summary field as a bullet. None if unusable."""
    if isinstance(value, (int, float)):
        return f"{key}: {value}"
    if isinstance(value, str) and value and len(value) <= 200:
        return f"{key}: {value}"
    if isinstance(value, list) and value and all(isinstance(v, str) for v in value):
        return f"{key}: {', '.join(value[:5])}"
    return None


def _build_rationale(plan: Dict[str, Any], result: PlanExecutionResult) -> str:
    parts: List[str] = []
    goal = plan.get("business_goal")
    if goal:
        parts.append(str(goal))
    if result.repair_triggered:
        parts.append(
            f"(repaired: {result.repair_trigger_type}, "
            f"{'recovered' if result.repair_recovered else 'failed'})"
        )
    return " ".join(parts)


def _build_answer(
    result: PlanExecutionResult,
    plan: Dict[str, Any],
    summary: Dict[str, Any],
) -> str:
    if result.status == "unanswerable":
        reason = result.error_message or "The question cannot be answered from this dataset."
        suggestion = plan.get("suggestion")
        if suggestion:
            return f"{reason} {suggestion}"
        return reason

    if not result.success:
        em = (result.error_message or "").lower()
        if result.time_budget_exhausted or "timeout" in em:
            return (
                "Analysis exceeded the time budget — this often happens with heavy "
                "model tuning (large hyperparameter grids or many estimators). Try a "
                "simpler model, a smaller grid, or a more specific question."
            )
        # NEVER surface the raw sandbox traceback to the user (CLAUDE.md: no stack
        # traces leaked, messages must be user-friendly). result.error_message is the
        # sandbox stderr — a full multi-line Python traceback for runtime errors.
        # Distill it to a single safe summary line; keep the full trace in `stderr`.
        cause = _distill_error(result.error_message)
        base = (
            "The analysis couldn't complete on this dataset. This can happen with "
            "very small, degenerate, or unusual data — try a simpler or more specific "
            "question."
        )
        return f"{base} (Reason: {cause})" if cause else base

    # Success path: prefer summary's stated findings if present.
    findings = summary.get("key_findings")
    if isinstance(findings, list) and findings:
        lead = str(findings[0])
        return lead if len(lead) < 400 else lead[:400] + "..."

    goal = plan.get("business_goal")
    if goal:
        return f"Analysis complete: {goal}"
    return "Analysis complete."


def _fallback_reason(result: PlanExecutionResult) -> Optional[str]:
    if result.success:
        return None
    em = (result.error_message or "").lower()
    if result.time_budget_exhausted or "timeout" in em:
        return "time_budget_exhausted"
    if result.status == "unanswerable":
        return "model_declared_unanswerable"
    # Surface the cause for observability, but NEVER the raw multi-line traceback
    # (it would otherwise leak into the structured field the UI/analytics read).
    # Distill to a single safe line; the clean enum lives in repair_trigger_type.
    return _distill_error(result.error_message) or "agentic_loop_failed"


def _distill_error(message: Optional[str]) -> str:
    """Reduce a raw sandbox traceback to a single user-safe summary line.

    Never returns a multi-line traceback. Prefers the final ``SomeError: detail``
    line (the actual cause); otherwise the last non-empty line. Capped in length.
    """
    if not message:
        return ""
    text = str(message)
    # Prefer a real exception line (`SomeError:` / `SomeException:`) over a trailing
    # warning — a DeprecationWarning appended after the traceback is not the cause.
    err_lines = re.findall(r"^[A-Za-z_][\w.]*(?:Error|Exception):.*$", text, re.MULTILINE)
    if not err_lines:
        err_lines = re.findall(r"^[A-Za-z_][\w.]*Warning:.*$", text, re.MULTILINE)
    if err_lines:
        line = err_lines[-1].strip()
    else:
        non_empty = [ln.strip() for ln in text.splitlines() if ln.strip()]
        line = non_empty[-1] if non_empty else ""
    line = " ".join(line.split())  # collapse whitespace/newlines
    return (line[:197] + "...") if len(line) > 200 else line


def _extract_stderr(result: PlanExecutionResult) -> str:
    """Pull the most useful stderr snippet from the terminal round, if any."""
    if not result.rounds:
        return ""
    terminal = result.rounds[-1]
    return (
        terminal.sandbox_stderr
        or terminal.sandbox_exception_type
        or terminal.validator_fail_reason
        or ""
    )
