"""Compatibility adapter for LangChain agent construction."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, Iterable
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from backend.config import settings

logger = logging.getLogger(__name__)

try:
    from langchain.agents import create_agent as _native_create_agent
except Exception:  # pragma: no cover - depends on installed langchain version
    _native_create_agent = None


class _FallbackAgent:
    """Minimal agent fallback when LangChain create_agent is unavailable."""

    def __init__(
        self,
        *,
        model: Any,
        tools: Iterable[Any],
        system_prompt: str = "",
        max_iterations: int | None = None,
    ) -> None:
        self.model = model
        self.tools = list(tools)
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

    def get_graph(self) -> Any:
        node_names = [getattr(tool, "name", str(tool)) for tool in self.tools]
        return SimpleNamespace(nodes=node_names)

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        messages = list(payload.get("messages") or [])
        question = self._resolve_question(payload, messages)
        answer = self._build_answer(question)
        messages.append(AIMessage(content=answer))
        return {"messages": messages, "intermediate_steps": []}

    def _resolve_question(self, payload: dict[str, Any], messages: list[Any]) -> str:
        question = str(payload.get("question") or "").strip()
        if question:
            return question
        for message in reversed(messages):
            content = getattr(message, "content", "")
            if content:
                return str(content).strip()
        return ""

    def _build_answer(self, question: str) -> str:
        if not question:
            return "No user question provided."

        if hasattr(self.model, "invoke"):
            try:
                response = self.model.invoke(
                    [
                        SystemMessage(content=self.system_prompt or ""),
                        HumanMessage(content=question),
                    ]
                )
                content = getattr(response, "content", None)
                if content:
                    return str(content)
            except Exception as exc:
                logger.warning("Fallback agent model invocation failed: %s", exc)

        return (
            "Agent fallback response. The environment is running in compatibility "
            f"mode. Query: {question}"
        )


class _LegacyLLMInvokeAdapter:
    """Adapter that exposes .invoke() over the project's LLMClientFactory client."""

    def __init__(self, llm_client: Any) -> None:
        self._llm_client = llm_client

    def invoke(self, messages: list[Any]) -> AIMessage:
        prompt_parts: list[str] = []
        for message in messages:
            role = type(message).__name__.replace("Message", "").lower()
            content = str(getattr(message, "content", "")).strip()
            if not content:
                continue
            prompt_parts.append(f"{role}: {content}")
        prompt = "\n".join(prompt_parts).strip()
        if not prompt:
            prompt = "user: "

        text = self._llm_client.generate(prompt)
        return AIMessage(content=str(text))


class _DispatchLLMInvokeAdapter:
    """Adapter that routes compatibility invocations through dispatch gateway."""

    def __init__(self, dispatch_service: Any, fallback_client: Any | None = None) -> None:
        self._dispatch_service = dispatch_service
        self._fallback_client = fallback_client

    @staticmethod
    def _build_prompt(messages: list[Any]) -> str:
        prompt_parts: list[str] = []
        for message in messages:
            role = type(message).__name__.replace("Message", "").lower()
            content = str(getattr(message, "content", "")).strip()
            if not content:
                continue
            prompt_parts.append(f"{role}: {content}")
        prompt = "\n".join(prompt_parts).strip()
        if not prompt:
            return "user: "
        return prompt

    def invoke(self, messages: list[Any]) -> AIMessage:
        from backend.services.llm_integration.types import DispatchRequest

        prompt = self._build_prompt(messages)
        route_mode = settings.resolved_hybrid_mode
        if route_mode not in {"local_only", "hybrid_auto", "cloud_only"}:
            route_mode = "local_only"
        request = DispatchRequest(
            prompt=prompt,
            tenant_id=settings.default_tenant_id,
            trace_id=str(uuid4()),
            route_mode=route_mode,  # type: ignore[arg-type]
        )

        response = self._dispatch_service.generate(request)
        if response.success and response.text:
            return AIMessage(content=str(response.text))

        if self._fallback_client is not None:
            try:
                text = self._fallback_client.generate(prompt)
                if text:
                    return AIMessage(content=str(text))
            except Exception as exc:
                logger.warning("Legacy fallback client generation failed: %s", exc)

        return AIMessage(
            content=f"Dispatch gateway unavailable: {response.error or 'unknown_error'}"
        )


def create_agent_compat(**kwargs: Any) -> Any:
    """Create agent using native create_agent when available, else fallback."""
    model = kwargs.get("model")
    if _native_create_agent is not None and model is not None:
        return _native_create_agent(**kwargs)
    logger.warning(
        "Using fallback agent wrapper (native create_agent unavailable or model missing)."
    )
    return _FallbackAgent(
        model=model,
        tools=kwargs.get("tools") or [],
        system_prompt=str(kwargs.get("system_prompt") or ""),
        max_iterations=kwargs.get("max_iterations"),
    )


def build_legacy_llm_invoke_adapter() -> Any:
    """Build invoke-capable model from backend LLM client for compatibility mode."""
    from backend.services.llm_integration.dispatch_service import get_dispatch_service
    from backend.services.llm_integration.llm_client import get_llm_client

    fallback_client = None
    try:
        fallback_client = get_llm_client()
    except Exception as exc:
        logger.warning("Fallback LLM client unavailable for compatibility adapter: %s", exc)

    try:
        dispatch_service = get_dispatch_service()
        return _DispatchLLMInvokeAdapter(dispatch_service, fallback_client=fallback_client)
    except Exception as exc:
        logger.warning("Dispatch gateway unavailable, using legacy adapter fallback: %s", exc)
        if fallback_client is None:
            raise
        return _LegacyLLMInvokeAdapter(fallback_client)
