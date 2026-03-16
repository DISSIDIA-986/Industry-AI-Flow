from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.langchain_compat import build_legacy_llm_invoke_adapter
from backend.config import settings


class _FakeDispatchService:
    def __init__(
        self, response_text: str, success: bool = True, error: str | None = None
    ):
        self.response_text = response_text
        self.success = success
        self.error = error
        self.last_request = None

    def generate(self, request):
        self.last_request = request
        return SimpleNamespace(
            success=self.success,
            text=self.response_text,
            error=self.error,
        )


class _FakeFallbackClient:
    def __init__(self, text: str):
        self.text = text
        self.calls: list[str] = []

    def generate(self, prompt: str, **kwargs) -> str:
        del kwargs
        self.calls.append(prompt)
        return self.text


def test_legacy_adapter_uses_dispatch_gateway(monkeypatch):
    fake_dispatch = _FakeDispatchService("gateway answer")
    fake_fallback = _FakeFallbackClient("fallback answer")

    monkeypatch.setattr(settings, "hybrid_mode", "hybrid_auto", raising=False)
    monkeypatch.setattr(
        "backend.services.llm_integration.dispatch_service.get_dispatch_service",
        lambda: fake_dispatch,
    )
    monkeypatch.setattr(
        "backend.services.llm_integration.llm_client.get_llm_client",
        lambda: fake_fallback,
    )

    adapter = build_legacy_llm_invoke_adapter()
    message = adapter.invoke(
        [
            SystemMessage(content="you are a helpful assistant"),
            HumanMessage(content="summarize this"),
        ]
    )

    assert str(message.content) == "gateway answer"
    assert fake_dispatch.last_request is not None
    assert fake_dispatch.last_request.route_mode == "hybrid_auto"
    assert fake_dispatch.last_request.tenant_id == settings.default_tenant_id
    assert not fake_fallback.calls


def test_legacy_adapter_falls_back_to_local_client_when_dispatch_fails(monkeypatch):
    fake_dispatch = _FakeDispatchService(
        response_text="",
        success=False,
        error="dispatch unavailable",
    )
    fake_fallback = _FakeFallbackClient("local fallback answer")

    monkeypatch.setattr(
        "backend.services.llm_integration.dispatch_service.get_dispatch_service",
        lambda: fake_dispatch,
    )
    monkeypatch.setattr(
        "backend.services.llm_integration.llm_client.get_llm_client",
        lambda: fake_fallback,
    )

    adapter = build_legacy_llm_invoke_adapter()
    message = adapter.invoke([HumanMessage(content="analyze this dataframe")])

    assert str(message.content) == "local fallback answer"
    assert fake_fallback.calls
