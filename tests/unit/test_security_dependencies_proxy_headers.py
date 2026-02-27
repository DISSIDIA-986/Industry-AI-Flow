from __future__ import annotations

from types import SimpleNamespace

from backend.security import dependencies


def _make_request(client_host: str, headers: dict[str, str]):
    return SimpleNamespace(
        client=SimpleNamespace(host=client_host),
        headers=headers,
    )


def _set_trusted_proxy_ips(raw_value: str) -> None:
    dependencies.settings.trusted_proxy_ips_raw = raw_value
    if hasattr(dependencies.settings, "_trusted_proxy_ip_cache"):
        delattr(dependencies.settings, "_trusted_proxy_ip_cache")


def test_resolve_client_host_ignores_forwarded_headers_when_proxy_trust_disabled(
    monkeypatch,
):
    monkeypatch.setattr(dependencies.settings, "trust_proxy_headers", False)
    _set_trusted_proxy_ips("10.0.0.1")
    request = _make_request(
        "10.0.0.1",
        {"X-Forwarded-For": "203.0.113.10"},
    )

    assert dependencies._resolve_client_host(request) == "10.0.0.1"


def test_resolve_client_host_uses_forwarded_for_from_trusted_proxy(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "trust_proxy_headers", True)
    _set_trusted_proxy_ips("10.0.0.1")
    request = _make_request(
        "10.0.0.1",
        {"X-Forwarded-For": "203.0.113.10, 10.0.0.1"},
    )

    assert dependencies._resolve_client_host(request) == "203.0.113.10"


def test_resolve_client_host_ignores_spoofed_forwarded_headers_from_untrusted_peer(
    monkeypatch,
):
    monkeypatch.setattr(dependencies.settings, "trust_proxy_headers", True)
    _set_trusted_proxy_ips("10.0.0.1")
    request = _make_request(
        "198.51.100.5",
        {"X-Forwarded-For": "203.0.113.10"},
    )

    assert dependencies._resolve_client_host(request) == "198.51.100.5"
