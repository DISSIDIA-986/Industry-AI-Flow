from __future__ import annotations

from backend.services.workflows.policies.budget_policy import (
    can_use_cloud,
    evaluate_budget,
)
from backend.services.workflows.policies.routing_policy import (
    resolve_route_mode,
    select_provider,
)


def test_budget_evaluation_hard_limit_blocks_cloud():
    evaluation = evaluate_budget(monthly_spend_usd=120, monthly_budget_usd=100)
    assert evaluation["status"] == "hard_limit"
    assert can_use_cloud(evaluation) is False


def test_budget_evaluation_soft_limit_allows_cloud():
    evaluation = evaluate_budget(monthly_spend_usd=85, monthly_budget_usd=100)
    assert evaluation["status"] == "soft_limit"
    assert can_use_cloud(evaluation) is True


def test_routing_policy_provider_selection():
    assert resolve_route_mode("hybrid_auto") == "hybrid_auto"
    assert resolve_route_mode("unknown") == "local_only"
    assert select_provider("local_only", cloud_allowed=True) == "local"
    assert select_provider("hybrid_auto", cloud_allowed=True) == "cloud"
    assert select_provider("cloud_only", cloud_allowed=False) == "local_fallback"
