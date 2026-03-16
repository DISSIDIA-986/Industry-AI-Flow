from __future__ import annotations

import base64

import pytest
import requests

from backend.services.code_executor.providers.ppio_provider import PPIOExecutionProvider


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_ppio_provider_disabled():
    provider = PPIOExecutionProvider(enabled=False)
    result = await provider.execute("print('x')")
    health = await provider.health()

    assert result.success is False
    assert "disabled" in (result.error or "")
    assert health["healthy"] is False
    assert health["status"] == "disabled"


@pytest.mark.asyncio
async def test_ppio_provider_execute_success(monkeypatch):
    sent = {}

    def _fake_post(url, json=None, headers=None, timeout=None, verify=None):
        sent["url"] = url
        sent["json"] = json or {}
        sent["headers"] = headers or {}
        sent["timeout"] = timeout
        sent["verify"] = verify
        payload = {
            "success": True,
            "stdout": "ok",
            "stderr": "",
            "execution_time_s": 0.2,
            "output_files": {
                "out.txt": base64.b64encode(b"hello").decode("utf-8"),
            },
        }
        return _FakeResponse(status_code=200, payload=payload)

    monkeypatch.setattr(requests, "post", _fake_post)

    provider = PPIOExecutionProvider(
        enabled=True,
        base_url="https://ppio.example",
        api_key="k",
        verify_tls=False,
    )
    result = await provider.execute(
        "print('x')", files={"input.txt": b"123"}, timeout_s=7
    )

    assert result.success is True
    assert result.stdout == "ok"
    assert result.output_files["out.txt"] == b"hello"
    assert sent["url"] == "https://ppio.example/v1/code/execute"
    assert sent["verify"] is False
    assert sent["json"]["files"]["input.txt"] == base64.b64encode(b"123").decode(
        "utf-8"
    )


@pytest.mark.asyncio
async def test_ppio_provider_circuit_breaker(monkeypatch):
    calls = {"count": 0}

    def _fake_post(*args, **kwargs):
        calls["count"] += 1
        raise requests.RequestException("network_down")

    monkeypatch.setattr(requests, "post", _fake_post)

    provider = PPIOExecutionProvider(
        enabled=True,
        base_url="https://ppio.example",
        failure_threshold=2,
        cooldown_seconds=60,
    )

    first = await provider.execute("print('x')")
    second = await provider.execute("print('x')")
    third = await provider.execute("print('x')")

    assert first.success is False
    assert second.success is False
    assert third.success is False
    assert "circuit_open" in (third.error or "")
    assert calls["count"] == 2
