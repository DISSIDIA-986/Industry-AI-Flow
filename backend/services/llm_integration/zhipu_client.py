"""Zhipu GLM client via Anthropic-compatible API."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from backend.config import settings

logger = logging.getLogger(__name__)


class ZhipuClient:
    """Cloud LLM client for Zhipu's Anthropic-compatible endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.zhipu_api_key
        self.base_url = (base_url or settings.zhipu_base_url).rstrip("/")
        self.model = model or settings.zhipu_model
        self.timeout_seconds = max(int(settings.api_timeout_ms / 1000), 10)

        if not self.api_key:
            raise RuntimeError("ZHIPU_API_KEY is not configured")

    def _messages_endpoint(self) -> str:
        if self.base_url.endswith("/v1/messages"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/messages"
        return f"{self.base_url}/v1/messages"

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ) -> str:
        payload = {
            "model": self.model,
            "max_tokens": max_tokens if max_tokens is not None else 1024,
            "temperature": temperature if temperature is not None else 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }
        if top_p is not None:
            payload["top_p"] = top_p
        payload.update(kwargs or {})

        headers = {
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        try:
            response = requests.post(
                self._messages_endpoint(),
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("content", [])
            if isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict):
                    text = first.get("text")
                    if text:
                        return text
            if isinstance(content, str):
                return content
            raise RuntimeError(f"Unexpected Zhipu response format: {data}")
        except requests.RequestException as exc:
            logger.error("Zhipu request failed: %s", exc)
            raise RuntimeError(f"Cloud generation failed: {exc}") from exc

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "backend": "zhipu",
            "model": self.model,
            "base_url": self.base_url,
        }

    def list_models(self) -> list:
        # Zhipu Anthropic-compatible endpoint generally does not expose model list here.
        return [{"name": self.model}]

    def get_current_config(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }
