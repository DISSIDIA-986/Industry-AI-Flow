from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_demo_module():
    path = Path("scripts/testing/run_prompt_admin_demo.py")
    spec = importlib.util.spec_from_file_location("run_prompt_admin_demo", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.content = json.dumps(payload).encode("utf-8")

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_run_prompt_admin_demo_smoke_no_experiment(monkeypatch):
    demo = _load_demo_module()
    calls = []

    def _fake_request(self, method, url, timeout=20, **kwargs):  # noqa: ARG001
        calls.append((method, url, kwargs))
        if url.endswith("/api/prompts/categories/list"):
            return _FakeResponse(["rag"])
        if url.endswith("/api/prompts/"):
            return _FakeResponse({"data": []})
        if url.endswith("/api/prompts/metrics/summary"):
            return _FakeResponse({"totals": {"usage_logs": 0}})
        return _FakeResponse({})

    monkeypatch.setattr(demo.requests.Session, "request", _fake_request)

    result = demo.run_demo(
        base_url="http://localhost:8000",
        api_key=None,
        execute_experiment=False,
    )
    assert result["base_url"] == "http://localhost:8000"
    assert any(step["step"] == "list_prompts" for step in result["steps"])
    assert any(
        step["step"] == "experiment_flow" and step.get("skipped")
        for step in result["steps"]
    )
    assert len(calls) == 3


def test_run_prompt_admin_demo_executes_experiment_flow(monkeypatch):
    demo = _load_demo_module()
    calls = []
    prompt_a = {"id": "a-id", "name": "construction_rag_grounded_qa", "category": "rag"}
    prompt_b = {"id": "b-id", "name": "construction_rag_grounded_qa", "category": "rag"}

    def _fake_request(self, method, url, timeout=20, **kwargs):  # noqa: ARG001
        calls.append((method, url, kwargs))
        if url.endswith("/api/prompts/categories/list"):
            return _FakeResponse(["rag"])
        if url.endswith("/api/prompts/"):
            return _FakeResponse({"data": [prompt_a, prompt_b]})
        if url.endswith("/api/prompts/metrics/summary"):
            return _FakeResponse({"totals": {"usage_logs": 3}})
        if url.endswith("/api/prompts/experiments") and method == "POST":
            return _FakeResponse({"experiment": {"id": "exp-1"}})
        if url.endswith("/api/prompts/experiments/exp-1/traffic"):
            split = kwargs["json"]["traffic_split"]
            return _FakeResponse(
                {
                    "experiment": {
                        "id": "exp-1",
                        "status": "active",
                        "traffic_split": split,
                    }
                }
            )
        if url.endswith("/api/prompts/experiments/exp-1/status"):
            return _FakeResponse({"experiment": {"id": "exp-1", "status": "paused"}})
        return _FakeResponse({})

    monkeypatch.setattr(demo.requests.Session, "request", _fake_request)

    result = demo.run_demo(
        base_url="http://localhost:8000",
        api_key=None,
        execute_experiment=True,
    )

    steps = [item["step"] for item in result["steps"]]
    assert "create_experiment" in steps
    assert steps.count("ramp_traffic") == 2
    assert "pause_experiment" in steps
    assert any(
        url.endswith("/api/prompts/experiments/exp-1/traffic") for _, url, _ in calls
    )
