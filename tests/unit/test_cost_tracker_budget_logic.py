"""Unit tests for cost tracker budget decisions."""

from __future__ import annotations

from backend.services.llm_integration.cost_tracker import BudgetPolicy, CostTracker
from backend.services.llm_integration.types import CostStats, UsageStats


class _FakeTracker(CostTracker):
    def __init__(self, policy: BudgetPolicy | None, monthly_spend: float) -> None:
        super().__init__()
        self._policy = policy
        self._monthly_spend = monthly_spend

    def get_budget_policy(self, tenant_id: str):
        return self._policy

    def get_monthly_spend(self, tenant_id: str, when=None):
        return self._monthly_spend


def test_budget_allow_when_no_policy():
    tracker = _FakeTracker(policy=None, monthly_spend=0)
    result = tracker.evaluate_budget("tenant-a")
    assert result["allowed"] is True
    assert result["decision"] == "allow"


def test_budget_soft_limit_warn():
    policy = BudgetPolicy(
        tenant_id="tenant-a",
        monthly_budget_usd=100,
        soft_limit_ratio=0.8,
        hard_limit_ratio=1.0,
        policy_mode="local_only",
    )
    tracker = _FakeTracker(policy=policy, monthly_spend=85)
    result = tracker.evaluate_budget("tenant-a")
    assert result["allowed"] is True
    assert result["decision"] == "warn_soft_limit"


def test_budget_hard_limit_force_local():
    policy = BudgetPolicy(
        tenant_id="tenant-a",
        monthly_budget_usd=100,
        soft_limit_ratio=0.8,
        hard_limit_ratio=1.0,
        policy_mode="local_only",
    )
    tracker = _FakeTracker(policy=policy, monthly_spend=120)
    result = tracker.evaluate_budget("tenant-a")
    assert result["allowed"] is True
    assert result["decision"] == "force_local"


def test_budget_hard_limit_block_cloud():
    policy = BudgetPolicy(
        tenant_id="tenant-a",
        monthly_budget_usd=100,
        soft_limit_ratio=0.8,
        hard_limit_ratio=1.0,
        policy_mode="block",
    )
    tracker = _FakeTracker(policy=policy, monthly_spend=120)
    result = tracker.evaluate_budget("tenant-a")
    assert result["allowed"] is False
    assert result["decision"] == "block_cloud"


def test_record_usage_closes_db_handles_on_insert_failure(monkeypatch):
    state = {"conn_closed": False, "cursor_closed": False}

    class _FailingCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            state["cursor_closed"] = True
            return False

        def execute(self, *_args, **_kwargs):
            raise RuntimeError("insert failed")

    class _FailingConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            state["conn_closed"] = True
            return False

        def cursor(self):
            return _FailingCursor()

    tracker = CostTracker()
    monkeypatch.setattr(tracker, "_connect", lambda: _FailingConnection())

    tracker.record_usage(
        tenant_id="tenant-a",
        provider="zhipu",
        model="glm-4-plus",
        usage=UsageStats(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        cost=CostStats(estimated_cost_usd=0.01),
        latency_ms=12,
        status="error",
        trace_id="t1",
        route_mode="cloud_only",
    )

    assert state["cursor_closed"] is True
    assert state["conn_closed"] is True
