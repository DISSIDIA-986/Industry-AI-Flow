"""Pin the Ollama keep_alive payload contract.

keep_alive keeps the model resident in VRAM between requests, eliminating the
per-query reload cold start on the local fallback path. It MUST be a top-level
payload field (Ollama ignores it inside `options`) and configurable via
settings / per-call override.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from backend.services.llm_integration.ollama_client import OllamaClient


def _capture_payload(generate_kwargs=None):
    client = OllamaClient()
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json = MagicMock(return_value={"response": "hi"})

    with patch.object(client._session, "post", return_value=fake_resp) as post:
        client.generate("hello", **(generate_kwargs or {}))

    _, kwargs = post.call_args
    return kwargs["json"]


def test_keep_alive_is_top_level_not_in_options():
    payload = _capture_payload()
    assert "keep_alive" in payload, "keep_alive must be a top-level field"
    assert "keep_alive" not in payload["options"], (
        "keep_alive inside options is silently ignored by Ollama"
    )


def test_keep_alive_defaults_from_settings():
    from backend.config import settings

    payload = _capture_payload()
    assert payload["keep_alive"] == settings.ollama_keep_alive


def test_keep_alive_per_call_override():
    payload = _capture_payload({"keep_alive": "-1"})
    assert payload["keep_alive"] == "-1"


def test_chat_payload_includes_keep_alive():
    client = OllamaClient()
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json = MagicMock(return_value={"message": {"content": "hi"}})
    with patch.object(client._session, "post", return_value=fake_resp) as post:
        client.chat([{"role": "user", "content": "hello"}])
    _, kwargs = post.call_args
    assert "keep_alive" in kwargs["json"]
    assert "keep_alive" not in kwargs["json"]["options"]
