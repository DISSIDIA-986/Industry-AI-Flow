"""Budget policy helpers for workflow pipeline."""

from __future__ import annotations

from typing import Any


def can_use_cloud(evaluation: Any) -> bool:
    if not isinstance(evaluation, dict):
        return False
    return bool(evaluation.get("allowed", False))


def evaluate_budget(
    *,
    monthly_spend_usd: float | int | None,
    monthly_budget_usd: float | int | None,
    soft_limit_ratio: float = 0.8,
    hard_limit_ratio: float = 1.0,
) -> dict:
    """
    Evaluate whether cloud routing is allowed under the current budget usage.
    """
    spend = float(monthly_spend_usd or 0.0)
    budget = float(monthly_budget_usd or 0.0)

    if budget <= 0:
        return {
            "allowed": False,
            "usage_ratio": None,
            "status": "no_budget",
            "reason": "monthly_budget_usd must be > 0",
        }

    usage_ratio = spend / budget
    if usage_ratio >= hard_limit_ratio:
        return {
            "allowed": False,
            "usage_ratio": usage_ratio,
            "status": "hard_limit",
            "reason": "hard limit reached",
        }
    if usage_ratio >= soft_limit_ratio:
        return {
            "allowed": True,
            "usage_ratio": usage_ratio,
            "status": "soft_limit",
            "reason": "within soft-limit zone",
        }
    return {
        "allowed": True,
        "usage_ratio": usage_ratio,
        "status": "normal",
        "reason": "within budget",
    }
