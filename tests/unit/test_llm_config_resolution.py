"""Tests for dispatch-related config resolution."""

from __future__ import annotations

from backend.config import Settings


def test_config_resolution_prefers_explicit_dispatch_fields(monkeypatch):
    monkeypatch.setenv("LOCAL_PRIMARY_BACKEND", "ollama")
    monkeypatch.setenv("LLM_BACKEND", "llama_cpp")
    monkeypatch.setenv("LLM_PROVIDER", "zhipu")
    monkeypatch.setenv("CLOUD_PROVIDER", "zhipu")
    monkeypatch.setenv("HYBRID_MODE", "hybrid_auto")
    monkeypatch.setenv("DEMO_MODE", "local_safe")

    s = Settings()
    assert s.resolved_hybrid_mode == "hybrid_auto"
    assert s.resolved_local_backend == "ollama"
    assert s.resolved_cloud_provider == "zhipu"
    assert s.resolved_demo_mode == "local_safe"


def test_config_resolution_falls_back_to_safe_defaults(monkeypatch):
    monkeypatch.setenv("LOCAL_PRIMARY_BACKEND", "unknown")
    monkeypatch.setenv("LLM_BACKEND", "unknown")
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    monkeypatch.setenv("CLOUD_PROVIDER", "unknown")
    monkeypatch.setenv("HYBRID_MODE", "unknown")
    monkeypatch.setenv("DEMO_MODE", "unknown")

    s = Settings()
    assert s.resolved_hybrid_mode == "local_only"
    assert s.resolved_local_backend == "ollama"
    assert s.resolved_cloud_provider == "zhipu"
    assert s.resolved_demo_mode == "live_hybrid"
