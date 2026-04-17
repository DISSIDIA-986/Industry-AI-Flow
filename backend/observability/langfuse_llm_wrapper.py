"""Transparent Langfuse tracing wrapper for BaseLLMClient implementations.

Wraps any client exposing ``generate(prompt, **kwargs) -> str`` and emits a
``generation``-type observation per call with model, input, output, latency.
If Langfuse is disabled, this is a pass-through and adds ~microseconds.

Two contracts this wrapper must honor:

1. **Observability is best-effort.** A Langfuse outage, SDK bug, or OTel
   context error must NOT surface as an LLM outage. Any failure from the
   tracing SDK falls through to an untraced inner ``generate()`` call.

2. **Local-only backends keep prompts local by default.** When the backend
   is local (e.g. Ollama) and the operator has not explicitly opted in with
   ``LANGFUSE_TRACE_LOCAL_PROMPTS=true``, the span records only the length
   and model metadata — never the prompt or completion text. This preserves
   the ``DEMO_MODE=local_safe`` / ``HYBRID_MODE=local_only`` privacy posture
   that ``DispatchService`` already enforces on the cloud routing side.

Usage (at factory level)::

    client = OllamaClient()
    return wrap(client)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

from backend.observability.langfuse_client import get_langfuse, is_enabled

logger = logging.getLogger(__name__)


class LangfuseLLMWrapper:
    """Proxy wrapping a BaseLLMClient to emit langfuse generation spans.

    Non-generate() attributes forward via ``__getattr__``, so this is a
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

    # Backends where prompts are considered local/sensitive by default. Prompts
    # and outputs for these backends are redacted unless the operator opts in
    # with LANGFUSE_TRACE_LOCAL_PROMPTS=true.
    _LOCAL_BACKENDS = frozenset({"ollama"})

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._backend = self._BACKEND_BY_CLASS.get(
            type(inner).__name__, "unknown"
        )
        self._model = getattr(inner, "model", "unknown")
        self._trace_local_prompts = (
            os.getenv("LANGFUSE_TRACE_LOCAL_PROMPTS", "false").lower() == "true"
        )

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
        if lf is None:
            # is_enabled() returned True but client went away; stay up.
            return self._inner.generate(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                **kwargs,
            )

        model_params = {
            k: v
            for k, v in {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
            }.items()
            if v is not None
        }

        redact = (
            self._backend in self._LOCAL_BACKENDS
            and not self._trace_local_prompts
        )
        span_input: Any = (
            {"redacted": True, "prompt_chars": len(prompt or "")}
            if redact
            else prompt
        )

        # Defensive open: if the SDK fails starting the span, fall through to
        # an untraced call. Observability must never break the request path.
        span_ctx = None
        gen = None
        try:
            span_ctx = lf.start_as_current_observation(
                name=f"llm.{self._backend}",
                as_type="generation",
                model=self._model,
                input=span_input,
                model_parameters=model_params,
                metadata={"backend": self._backend, "redacted": redact},
            )
            gen = span_ctx.__enter__()
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("Langfuse span open failed (%s) — untraced fallback", exc)
            return self._inner.generate(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                **kwargs,
            )

        start = time.perf_counter()
        try:
            output = self._inner.generate(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                **kwargs,
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            if gen is not None:
                try:
                    gen.update(
                        output=(
                            {"redacted": True, "output_chars": len(output or "")}
                            if redact
                            else output
                        ),
                        metadata={
                            "backend": self._backend,
                            "latency_ms": latency_ms,
                            "prompt_chars": len(prompt or ""),
                            "output_chars": len(output or ""),
                            "redacted": redact,
                        },
                    )
                except Exception:  # pylint: disable=broad-except
                    pass
            return output
        finally:
            if span_ctx is not None:
                try:
                    span_ctx.__exit__(None, None, None)
                except Exception:  # pylint: disable=broad-except
                    pass

    def __getattr__(self, name: str) -> Any:
        # Forward everything else (get_model_info, is_loaded, list_models, ...)
        return getattr(self._inner, name)


def wrap(client: Any) -> Any:
    """Return a traced wrapper iff langfuse is enabled, else the original client."""
    if not is_enabled():
        return client
    return LangfuseLLMWrapper(client)
