import json
import logging
from typing import Any, Dict, Optional

import requests

from backend.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        default_temperature: float = 0.7,
        default_max_tokens: int = 2000,
        default_top_p: float = 0.9,
    ):
        self.base_url = base_url or settings.ollama_host
        self.model = model or settings.ollama_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.default_top_p = default_top_p

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stream: bool = False,
        **kwargs,
    ) -> str:
        """
        ENOllamaEN

        Args:
            prompt: EN
            temperature: EN,EN (0.0-1.0)
            max_tokens: ENtokenEN
            top_p: EN (0.0-1.0)
            stream: EN
            **kwargs: ENOllamaEN

        Returns:
            EN
        """
        # EN
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature
                if temperature is not None
                else self.default_temperature,
                "num_predict": max_tokens
                if max_tokens is not None
                else self.default_max_tokens,
                "top_p": top_p if top_p is not None else self.default_top_p,
            },
        }

        # EN
        if kwargs:
            payload["options"].update(kwargs)

        try:
            response = requests.post(
                f"{self.base_url}/api/generate", json=payload, timeout=60  # 60EN
            )
            response.raise_for_status()

            if stream:
                return self._handle_stream_response(response)
            else:
                return response.json()["response"]

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed: {e}")
            raise Exception(f"LLM generation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {e}")
            raise Exception(f"LLM generation error: {str(e)}")

    def _handle_stream_response(self, response) -> str:
        """EN"""
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode())
                    if "response" in data:
                        full_response += data["response"]
                    if data.get("done", False):
                        break
                except Exception as e:
                    logger.warning(f"Failed to parse stream response chunk: {e}")
                    continue
        return full_response

    def chat(
        self,
        messages: list,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> str:
        """
        EN

        Args:
            messages: EN,EN [{"role": "user", "content": "..."}]
            temperature: EN
            max_tokens: ENtokenEN
            top_p: EN

        Returns:
            EN
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
                if temperature is not None
                else self.default_temperature,
                "num_predict": max_tokens
                if max_tokens is not None
                else self.default_max_tokens,
                "top_p": top_p if top_p is not None else self.default_top_p,
            },
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat", json=payload, timeout=60
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama chat API request failed: {e}")
            raise Exception(f"LLM chat failed: {str(e)}")

    def get_model_info(self) -> Dict[str, Any]:
        """EN"""
        try:
            response = requests.post(
                f"{self.base_url}/api/show", json={"name": self.model}, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return {}

    def list_models(self) -> list:
        """EN"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=30)
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def update_config(self, **kwargs):
        """EN"""
        valid_params = ["default_temperature", "default_max_tokens", "default_top_p"]
        for param, value in kwargs.items():
            if param in valid_params:
                setattr(self, param, value)
                logger.info(f"Updated {param} to {value}")
            else:
                logger.warning(f"Invalid parameter: {param}")

    def get_current_config(self) -> Dict[str, Any]:
        """EN"""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "default_temperature": self.default_temperature,
            "default_max_tokens": self.default_max_tokens,
            "default_top_p": self.default_top_p,
        }
