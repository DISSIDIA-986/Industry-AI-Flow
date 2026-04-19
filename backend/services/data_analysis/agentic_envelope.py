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

    visualizations, chart_entry = _persist_chart(result, question)

    charts = [chart_entry] if chart_entry else []
    key_findings = _extract_key_findings(summary, plan)
    rationale = _build_rationale(plan, result)

    answer = _build_answer(result, plan, summary)

    fallback_reason = _fallback_reason(result)

    return {
        "success": result.success and bool(chart_entry) if _plan_produces_chart(plan) else result.success,
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
        },
        "dataset_info": dataset_metadata,
        "execution_time": round(result.total_elapsed_s, 2),
        "model_comparison": {"enabled": False, "reason": "agentic path"},
        "stdout": result.final_stdout or "",
        "stderr": _extract_stderr(result),
    }


def _plan_produces_chart(plan: Dict[str, Any]) -> bool:
    return bool(plan.get("produces_chart"))


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
    """Turn {ModelName: {mean_auc: X, std_auc: Y, ...}} into sorted bullets.

    Expected shapes (any one of):
      {"RF": {"mean_auc": 0.87, "std_auc": 0.02}, ...}
      {"RF": {"auc": 0.87}, ...}
      {"RF": 0.87, ...}
    """
    scored: List[tuple[str, float, str]] = []
    for name, payload in mc.items():
        if not isinstance(name, str):
            continue
        score: Optional[float] = None
        detail = ""
        if isinstance(payload, dict):
            for score_key in ("mean_auc", "auc", "roc_auc", "score", "accuracy"):
                if score_key in payload:
                    try:
                        score = float(payload[score_key])
                        std = payload.get("std_auc") or payload.get("std")
                        if std is not None:
                            try:
                                detail = f" ± {float(std):.3f}"
                            except (TypeError, ValueError):
                                pass
                        break
                    except (TypeError, ValueError):
                        continue
        else:
            try:
                score = float(payload)
            except (TypeError, ValueError):
                continue
        if score is not None:
            scored.append((name, score, detail))

    if not scored:
        return []

    scored.sort(key=lambda t: t[1], reverse=True)
    bullets = [f"{name}: AUC={score:.4f}{detail}" for name, score, detail in scored]
    leader = scored[0]
    bullets.insert(0, f"Best model: {leader[0]} (AUC={leader[1]:.4f}{leader[2]})")
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
