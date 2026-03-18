"""Groq cloud LLM client via OpenAI-compatible API."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from backend.config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    """Cloud LLM client for Groq's OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.backend = "groq"
        self.api_key = api_key or settings.groq_api_key
        self.base_url = (base_url or settings.groq_base_url).rstrip("/")
        self.model = model or settings.groq_model
        self.timeout_seconds = max(int(settings.api_timeout_ms / 1000), 10)

        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")

    def _chat_endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens if max_tokens is not None else 1024,
            "temperature": temperature if temperature is not None else 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }
        if top_p is not None:
            payload["top_p"] = top_p

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            response = requests.post(
                self._chat_endpoint(),
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()

            # OpenAI-compatible response format
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content")
                if content is not None:
                    return content

            raise RuntimeError(f"Unexpected Groq response format: {data}")
        except requests.RequestException as exc:
            logger.error("Groq request failed: %s", exc)
            raise RuntimeError(f"Groq cloud generation failed: {exc}") from exc

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "backend": "groq",
            "model": self.model,
            "base_url": self.base_url,
        }

    def list_models(self) -> list:
        return [{"name": self.model}]

    def get_current_config(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }
