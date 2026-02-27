"""Cost estimation node for workflow pipeline."""

from __future__ import annotations

from typing import Any, Dict

from backend.services.cost_estimation_service import (
    CostEstimationError,
    CostEstimationService,
    extract_cost_features_from_query,
)
from backend.services.workflows.state import WorkflowState


def _build_missing_features_response(parsed_features: Dict[str, Any]) -> str:
    observed = ", ".join(sorted(parsed_features.keys())) if parsed_features else "none"
    return (
        "To estimate construction cost, please provide at least:\n"
        "- estimated_cost_cad\n"
        "- one scope indicator such as sqft / planned_duration_weeks / floors\n"
        "- optional project_type and location for better accuracy\n"
        f"\nDetected fields: {observed}"
    )


def _render_cost_estimation_response(prediction: Dict[str, Any]) -> str:
    pred_actual = prediction["predicted_actual_cost_cad"]
    pred_overrun = prediction["predicted_cost_overrun_pct"]
    interval = prediction["prediction_interval_cad"]
    unknown = prediction.get("unknown_categories") or {}

    lines = [
        "Cost estimation result",
        f"- Predicted actual cost (CAD): {pred_actual:,.2f}",
        f"- Predicted overrun (%): {pred_overrun:.2f}",
        (
            f"- Prediction interval ({interval['confidence_quantile']:.2f}) "
            f"(CAD): {interval['lower']:,.2f} to {interval['upper']:,.2f}"
        ),
    ]
    if unknown:
        unknown_str = ", ".join(f"{k}={v}" for k, v in unknown.items())
        lines.append(f"- Unknown categories mapped with fallback: {unknown_str}")
        lines.append(
            "- WARNING: Reduced accuracy — the above categories were not seen "
            "during training. Prediction confidence is degraded."
        )
    return "\n".join(lines)


async def cost_estimation_node(state: WorkflowState, services: Any) -> WorkflowState:
    metadata = state.setdefault("metadata", {})
    metrics = state.setdefault("metrics", {})

    if state.get("intent") != "cost_estimation":
        metadata["cost_estimation_status"] = "skipped"
        return state

    provided_features = metadata.get("cost_estimation_features")
    if not isinstance(provided_features, dict):
        provided_features = {}

    parsed_features = extract_cost_features_from_query(state.get("query", ""))
    merged_features = {**parsed_features, **provided_features}
    metadata["cost_estimation_extracted_features"] = parsed_features
    metadata["cost_estimation_features"] = merged_features

    if "estimated_cost_cad" not in merged_features:
        metadata["cost_estimation_status"] = "need_features"
        state["response"] = _build_missing_features_response(merged_features)
        metadata["shortcut_response"] = True
        metrics["cost_estimation_executed"] = True
        return state

    service = getattr(services, "cost_estimation_service", None)
    if service is None:
        service = CostEstimationService()

    if not isinstance(service, CostEstimationService) and not hasattr(service, "predict_project"):
        metadata["cost_estimation_status"] = "unavailable"
        state["response"] = (
            "Cost estimation model service is unavailable. "
            "Train a model first via /api/v1/cost-estimation/train."
        )
        metadata["shortcut_response"] = True
        metrics["cost_estimation_executed"] = True
        return state

    try:
        confidence_quantile = float(metadata.get("cost_estimation_confidence_quantile", 0.90))
    except (TypeError, ValueError):
        confidence_quantile = 0.90

    try:
        prediction = service.predict_project(
            merged_features,
            confidence_quantile=confidence_quantile,
        )
    except CostEstimationError:
        metadata["cost_estimation_status"] = "unavailable"
        state["response"] = (
            "Cost estimation model is not loaded yet. "
            "Train and load a model via /api/v1/cost-estimation/train first."
        )
        metadata["shortcut_response"] = True
        metrics["cost_estimation_executed"] = True
        return state

    metadata["cost_estimation_status"] = "ok"
    metadata["cost_estimation_prediction"] = prediction
    state["response"] = _render_cost_estimation_response(prediction)
    state["provider_used"] = "cost_estimation_model"
    metadata["shortcut_response"] = True
    metrics["cost_estimation_executed"] = True
    return state
