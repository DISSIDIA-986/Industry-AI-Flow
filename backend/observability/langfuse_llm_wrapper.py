"""Transparent Langfuse tracing wrapper for BaseLLMClient implementations.

Wraps any client exposing `generate(prompt, **kwargs) -> str` and emits a
`generation`-type observation per call with model, input, output, latency.
If Langfuse is disabled, this is a pass-through and adds ~microseconds.

Usage (at factory level):
    client = OllamaClient()
    return wrap(client)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from backend.observability.langfuse_client import get_langfuse, is_enabled

logger = logging.getLogger(__name__)


class LangfuseLLMWrapper:
    """Proxy wrapping a BaseLLMClient to emit langfuse generation spans.

    All non-generate() attributes are forwarded via __getattr__, so this is a
    drop-in replacement — the rest of the codebase sees the same interface.
    """

    # Map concrete client class names to the backend label used in span names.
    # Kept local so we never touch the network just to learn what we're wrapping
    # (OllamaClient.get_model_info() makes an HTTP POST, which would regress
    # startup time on the local demo path).
    _BACKEND_BY_CLASS = {
        "OllamaClient": "ollama",
        "ZhipuClient": "zhipu",
        "GroqClient": "groq",
    }

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._backend = self._BACKEND_BY_CLASS.get(
            type(inner).__name__, "unknown"
        )
        self._model = getattr(inner, "model", "unknown")

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        if not is_enabled():
            return self._inner.generate(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                **kwargs,
            )

        lf = get_langfuse()
        assert lf is not None  # narrowed by is_enabled()

        model_params = {
            k: v
            for k, v in {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
            }.items()
            if v is not None
        }

        start = time.perf_counter()
        try:
            with lf.start_as_current_observation(
                name=f"llm.{self._backend}",
                as_type="generation",
                model=self._model,
                input=prompt,
                model_parameters=model_params,
                metadata={"backend": self._backend},
            ) as gen:
                output = self._inner.generate(
                    prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    **kwargs,
                )
                latency_ms = int((time.perf_counter() - start) * 1000)
                try:
                    gen.update(
                        output=output,
                        metadata={
                            "backend": self._backend,
                            "latency_ms": latency_ms,
                            "prompt_chars": len(prompt or ""),
                            "output_chars": len(output or ""),
                        },
                    )
                except Exception:  # pylint: disable=broad-except
                    pass
                return output
        except Exception:
            # Re-raise to preserve original behavior. The context manager above
            # automatically records the exception status on the span.
            raise

    def __getattr__(self, name: str) -> Any:
        # Forward everything else (get_model_info, is_loaded, list_models, ...)
        return getattr(self._inner, name)


def wrap(client: Any) -> Any:
    """Return a traced wrapper iff langfuse is enabled, else the original client."""
    if not is_enabled():
        return client
    return LangfuseLLMWrapper(client)
