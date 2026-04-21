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

    visualizations, chart_entry, chart_persist_error = _persist_chart(result, question)
    chart_persist_failed = bool(result.final_chart_bytes) and chart_entry is None

    charts = [chart_entry] if chart_entry else []
    key_findings = _extract_key_findings(summary, plan)
    rationale = _build_rationale(plan, result)

    answer = _build_answer(result, plan, summary)

    fallback_reason = _fallback_reason(result)

    # SUCCESS CONTRACT (plan-eng-review 2026-04-20):
    # The round-level success predicate (RoundRecord.is_successful /
    # PlanExecutionResult.success) is the single source of truth.
    # Artifact failures (chart persist, summary parse) are observability,
    # not gates. Under-producing the UI is handled per-field (empty charts
    # list, model_comparison.enabled=False), not by flipping the whole
    # envelope to failed.
    model_comparison_block = _normalize_model_comparison_block(summary)

    return {
        "success": result.success,
        "answer": answer,
        "charts": charts,
        "visualizations": visualizations,
        "code": result.final_code or "",
        "analysis_summary": {
            "key_findings": key_findings,
            "rationale": rationale,
        },
        "code_generation": {
            "mode": AGENTIC_MODE,
            "fallback_reason": fallback_reason,
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
            # Artifact observability: chart persist is a best-effort
            # write; a failure here does NOT fail the run.
            "chart_persist_failed": chart_persist_failed,
            "chart_persist_error": chart_persist_error,
        },
        "dataset_info": dataset_metadata,
        "execution_time": round(result.total_elapsed_s, 2),
        "model_comparison": model_comparison_block,
        "stdout": result.final_stdout or "",
        "stderr": _extract_stderr(result),
    }


def _plan_produces_chart(plan: Dict[str, Any]) -> bool:
    return bool(plan.get("produces_chart"))


def _persist_chart(
    result: PlanExecutionResult, question: str
) -> tuple[List[Dict[str, str]], Optional[Dict[str, Any]], Optional[str]]:
    """Write chart PNG (if present) to temp_data_dir and return the
    legacy ``{filename, path}`` visualization entry, the chart record,
    and an error string (None on success).

    No chart → empty visualizations, chart_entry=None, error=None.
    Persist error → empty visualizations, chart_entry=None, error=<str>.
    """
    if not result.final_chart_bytes:
        return [], None, None

    try:
        from backend.tools.visualization import _persist_visualization_artifacts
    except Exception as exc:  # pragma: no cover — import failure is fatal
        logger.error("visualization persister unavailable: %s", exc)
        return [], None, f"import_error: {type(exc).__name__}"

    try:
        persisted = _persist_visualization_artifacts(
            {"analysis_chart.png": result.final_chart_bytes}
        )
    except Exception as exc:
        logger.warning("agentic chart persist failed: %s", exc)
        return [], None, f"{type(exc).__name__}: {exc!s}"[:200]

    if not persisted:
        return [], None, "persister_returned_empty"

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
    return [{"filename": entry["filename"], "path": entry["path"]}], chart, None


def _normalize_model_comparison_block(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Shape the envelope ``model_comparison`` block for the frontend.

    The frontend types ``metrics`` as ``Record<str, Record<str, number>>``.
    LLM-emitted ``summary.model_comparison`` can be heterogeneous:
      - {"RF": {"auc": 0.87}, "best_model": "RF"}  # mixed dict + string
      - {"RF": 0.87, "LR": 0.72}                   # bare scalars
      - {"RF": {"auc": "high"}}                    # non-numeric metrics
      - {}                                         # empty

    This normalizer keeps only entries where the value is a dict with at
    least one finite numeric metric. Empty result → ``enabled=False`` so
    the frontend cleanly hides the metrics table (it still gets synthesized
    bullets via ``_bullets_from_model_comparison``).

    Plan-eng-review 2026-04-20: previously hardcoded ``enabled=False`` on
    the agentic path, burying real per-model metrics in bullets only.
    """
    mc = summary.get("model_comparison")
    if not isinstance(mc, dict) or not mc:
        return {"enabled": False, "reason": "no_model_comparison"}

    normalized: Dict[str, Dict[str, float]] = {}
    for name, payload in mc.items():
        if not isinstance(name, str) or not isinstance(payload, dict):
            continue
        metrics: Dict[str, float] = {}
        for metric_key, metric_val in payload.items():
            if isinstance(metric_val, bool):  # bool subclasses int
                continue
            if not isinstance(metric_val, (int, float)):
                continue
            if not math.isfinite(float(metric_val)):
                continue
            metrics[str(metric_key)] = float(metric_val)
        if metrics:
            normalized[name] = metrics

    if not normalized:
        return {"enabled": False, "reason": "no_numeric_metrics"}

    task = summary.get("task") if isinstance(summary.get("task"), str) else None
    target = (
        summary.get("target_column")
        if isinstance(summary.get("target_column"), str)
        else None
    )
    block: Dict[str, Any] = {"enabled": True, "metrics": normalized}
    if task:
        block["task"] = task
    if target:
        block["target_column"] = target
    return block


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
        if result.time_budget_exhausted:
            return "Analysis exceeded the time budget. Please retry with a simpler question."
        return (
            result.error_message
            or "The analysis could not complete. Please retry."
        )

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
    if result.time_budget_exhausted:
        return "time_budget_exhausted"
    if result.status == "unanswerable":
        return "model_declared_unanswerable"
    return result.error_message or "agentic_loop_failed"


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
