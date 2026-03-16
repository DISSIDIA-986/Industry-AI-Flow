"""Route decision node for workflow pipeline."""

from __future__ import annotations

from typing import Any

from backend.services.workflows.policies.budget_policy import (
    can_use_cloud,
    evaluate_budget,
)
from backend.services.workflows.policies.routing_policy import (
    resolve_route_mode,
    select_provider,
)
from backend.services.workflows.state import WorkflowState


async def route_node(state: WorkflowState, services: Any) -> WorkflowState:
    del services

    metadata = state.setdefault("metadata", {})
    requested_mode = metadata.get("requested_route_mode") or state.get("route_mode")
    route_mode = resolve_route_mode(requested_mode, default_mode="local_only")

    budget_eval = metadata.get("budget_evaluation")
    if not isinstance(budget_eval, dict):
        spend = metadata.get("monthly_spend_usd")
        budget = metadata.get("monthly_budget_usd")
        if spend is not None or budget is not None:
            budget_eval = evaluate_budget(
                monthly_spend_usd=spend,
                monthly_budget_usd=budget,
                soft_limit_ratio=float(metadata.get("soft_limit_ratio", 0.8)),
                hard_limit_ratio=float(metadata.get("hard_limit_ratio", 1.0)),
            )
            metadata["budget_evaluation"] = budget_eval

    cloud_allowed = (
        can_use_cloud(budget_eval) if isinstance(budget_eval, dict) else False
    )
    provider = select_provider(route_mode, cloud_allowed=cloud_allowed)

    state["route_mode"] = route_mode
    state["provider_used"] = provider
    metadata["route_mode"] = route_mode
    metadata["provider_used"] = provider
    if provider == "local_fallback":
        metadata["budget_blocked"] = True
    return state
