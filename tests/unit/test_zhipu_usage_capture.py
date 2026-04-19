"""Zhipu client must surface token usage via ``last_usage``.

Codex review (2026-04-18) flagged that the Anthropic-compatible endpoint
returns a ``usage`` block on every response, but ``ZhipuClient.generate()``
discarded it. Cost-per-request observability needs the tokens threaded
into telemetry. These tests lock in the non-breaking attribute pattern:
callers who don't care ignore ``last_usage``; the agentic loop reads it
to populate ``RoundRecord.llm_tokens_in/out``.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.services.llm_integration.zhipu_client import ZhipuClient


def _make_client() -> ZhipuClient:
    """Build a client without hitting env-var validation."""
    c = ZhipuClient.__new__(ZhipuClient)
    c.backend = "zhipu"
    c.api_key = "test-key"
    c.base_url = "https://example.invalid/v1"
    c.model = "glm-test"
    c.timeout_seconds = 10
    c.last_usage = {}
    return c


def test_last_usage_starts_empty():
    c = _make_client()
    assert c.last_usage == {}


def test_last_usage_populated_on_success():
    """Happy path: endpoint returns usage block; client captures it."""
    c = _make_client()
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json = MagicMock(
        return_value={
            "content": [{"type": "text", "text": "hello"}],
            "usage": {"input_tokens": 1234, "output_tokens": 56},
        }
    )

    with patch(
        "backend.services.llm_integration.zhipu_client.requests.post",
        return_value=fake_resp,
    ):
        text = c.generate("ping")

    assert text == "hello"
    assert c.last_usage == {"input_tokens": 1234, "output_tokens": 56}


def test_last_usage_empty_when_endpoint_omits_it():
    """Some deployments might omit the usage block; client must tolerate."""
    c = _make_client()
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json = MagicMock(
        return_value={"content": [{"type": "text", "text": "hello"}]}
    )

    with patch(
        "backend.services.llm_integration.zhipu_client.requests.post",
        return_value=fake_resp,
    ):
        text = c.generate("ping")

    assert text == "hello"
    assert c.last_usage == {}


def test_last_usage_cleared_when_prior_call_had_usage():
    """Second call overwrites stale usage — no cross-call leakage."""
    c = _make_client()

    resp_with = MagicMock()
    resp_with.raise_for_status = MagicMock()
    resp_with.json = MagicMock(
        return_value={
            "content": [{"type": "text", "text": "a"}],
            "usage": {"input_tokens": 9, "output_tokens": 1},
        }
    )
    resp_without = MagicMock()
    resp_without.raise_for_status = MagicMock()
    resp_without.json = MagicMock(
        return_value={"content": [{"type": "text", "text": "b"}]}
    )

    with patch(
        "backend.services.llm_integration.zhipu_client.requests.post",
        side_effect=[resp_with, resp_without],
    ):
        c.generate("first")
        assert c.last_usage == {"input_tokens": 9, "output_tokens": 1}
        c.generate("second")
        assert c.last_usage == {}, "second call's missing usage must clear stale tokens"
