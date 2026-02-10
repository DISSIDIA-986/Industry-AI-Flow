from __future__ import annotations

import json

from pathlib import Path
import importlib.util


def _load_module(module_path: str):
    path = Path(module_path)
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_prompt_admin_api_client_request_mapping(monkeypatch):
    client_module = _load_module("tools/prompt-admin/api_client.py")
    PromptApiClient = client_module.PromptApiClient

    calls: list[dict] = []

    class _FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self.content = json.dumps(payload).encode("utf-8")

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def _fake_request(self, method, url, timeout=20, **kwargs):  # noqa: ARG001
        calls.append({"method": method, "url": url, "kwargs": kwargs})
        if url.endswith("/api/prompts/"):
            return _FakeResponse({"data": [], "pagination": {"total": 0}})
        if url.endswith("/api/prompts/metrics/summary"):
            return _FakeResponse({"totals": {"usage_logs": 1}})
        if url.endswith("/status"):
            return _FakeResponse({"success": True})
        return _FakeResponse({})

    monkeypatch.setattr(client_module.requests.Session, "request", _fake_request)

    client = PromptApiClient("http://localhost:8000", api_key="k")
    list_payload = client.list_prompts(page=2, size=10, category="rag")
    metrics_payload = client.get_metrics_summary(days=30, category="rag", top_limit=5)
    status_payload = client.update_experiment_status("exp-1", "paused")

    assert list_payload["pagination"]["total"] == 0
    assert metrics_payload["totals"]["usage_logs"] == 1
    assert status_payload["success"] is True

    assert calls[0]["method"] == "GET"
    assert calls[0]["url"] == "http://localhost:8000/api/prompts/"
    assert calls[0]["kwargs"]["params"]["page"] == 2
    assert calls[0]["kwargs"]["params"]["category"] == "rag"

    assert calls[1]["method"] == "GET"
    assert calls[1]["kwargs"]["params"]["days"] == 30
    assert calls[1]["kwargs"]["params"]["top_limit"] == 5

    assert calls[2]["method"] == "PATCH"
    assert calls[2]["url"].endswith("/api/prompts/experiments/exp-1/status")
    assert calls[2]["kwargs"]["json"]["status"] == "paused"
