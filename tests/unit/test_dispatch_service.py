"""Unit tests for the unified LLM dispatch service."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.services.demo_mode_service import (
    DEMO_MODE_LIVE_HYBRID,
    DEMO_MODE_LOCAL_SAFE,
    get_demo_mode_service,
)
from backend.services.llm_integration.dispatch_service import DispatchService
from backend.services.llm_integration.types import (
    CostStats,
    DispatchRequest,
    UsageStats,
)


class _FakeLocalClient:
    def __init__(self, text: str) -> None:
        self.text = text
        self.model = "fake-local-model"

    def generate(self, prompt: str, **kwargs) -> str:
        return self.text


class _FakeCloudClient:
    def __init__(self, text: str) -> None:
        self.text = text
        self.model = "fake-cloud-model"
        self.last_prompt = None

    def generate(self, prompt: str, **kwargs) -> str:
        self.last_prompt = prompt
        return self.text


@dataclass
class _FakeTracker:
    allow_cloud: bool = True
    last_record_provider: str | None = None

    def estimate_usage(self, prompt: str, completion: str) -> UsageStats:
        return UsageStats(prompt_tokens=10, completion_tokens=20, total_tokens=30)

    def estimate_cost(self, provider: str, model: str, usage: UsageStats) -> CostStats:
        return CostStats(estimated_cost_usd=0.001)

    def record_usage(self, **kwargs):
        self.last_record_provider = kwargs.get("provider")

    def evaluate_budget(self, tenant_id: str, additional_cost_usd: float = 0.0):
        if self.allow_cloud:
            return {"allowed": True, "decision": "allow", "policy_mode": "none"}
        return {
            "allowed": False,
            "decision": "block_cloud",
            "policy_mode": "block",
        }


@pytest.fixture(autouse=True)
def _reset_demo_mode_state():
    service = get_demo_mode_service()
    service.reset_for_tests(mode=DEMO_MODE_LIVE_HYBRID, allow_cloud_override=False)
    yield
    service.reset_for_tests(mode=DEMO_MODE_LIVE_HYBRID, allow_cloud_override=False)


def test_local_only_uses_local_client():
    tracker = _FakeTracker()
    service = DispatchService(
        local_client=_FakeLocalClient("local answer"),
        cloud_client=_FakeCloudClient("cloud answer"),
        tracker=tracker,
    )
    req = DispatchRequest(
        prompt="what is concrete strength?",
        tenant_id="tenant-a",
        trace_id="trace-1",
        route_mode="local_only",
    )

    res = service.generate(req)
    assert res.success is True
    assert res.provider in {"llama_cpp", "ollama"}
    assert res.text == "local answer"


def test_hybrid_auto_falls_back_to_cloud_on_low_confidence():
    tracker = _FakeTracker(allow_cloud=True)
    cloud = _FakeCloudClient("cloud answer with details")
    service = DispatchService(
        local_client=_FakeLocalClient("I don't know."),
        cloud_client=cloud,
        tracker=tracker,
    )
    req = DispatchRequest(
        prompt="Contact me at test@example.com",
        tenant_id="tenant-a",
        trace_id="trace-2",
        route_mode="hybrid_auto",
        local_conf_threshold=0.7,
    )

    res = service.generate(req)
    assert res.success is True
    assert res.provider == "zhipu"
    assert res.text.startswith("cloud answer")
    assert "<REDACTED_EMAIL>" in (cloud.last_prompt or "")


def test_cloud_only_respects_budget_block_policy():
    tracker = _FakeTracker(allow_cloud=False)
    service = DispatchService(
        local_client=_FakeLocalClient("local answer"),
        cloud_client=_FakeCloudClient("cloud answer"),
        tracker=tracker,
    )
    req = DispatchRequest(
        prompt="hello",
        tenant_id="tenant-a",
        trace_id="trace-3",
        route_mode="cloud_only",
    )

    res = service.generate(req)
    assert res.success is False
    assert res.policy_decision == "block_cloud"


def test_cloud_only_request_is_forced_to_local_in_local_safe_mode():
    get_demo_mode_service().set_mode(DEMO_MODE_LOCAL_SAFE)

    tracker = _FakeTracker(allow_cloud=True)
    service = DispatchService(
        local_client=_FakeLocalClient("local answer"),
        cloud_client=_FakeCloudClient("cloud answer"),
        tracker=tracker,
    )
    req = DispatchRequest(
        prompt="hello",
        tenant_id="tenant-a",
        trace_id="trace-4",
        route_mode="cloud_only",
    )

    res = service.generate(req)
    assert res.success is True
    assert res.provider in {"llama_cpp", "ollama"}
    assert res.route_mode == "local_only"
