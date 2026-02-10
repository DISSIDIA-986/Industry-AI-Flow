"""Response construction node for workflow pipeline."""

from __future__ import annotations

from typing import Any

from backend.services.workflows.state import WorkflowState


def _build_default_response(state: WorkflowState) -> str:
    if state.get("error"):
        return "Request could not be processed due to safety or execution constraints."

    provider = state.get("provider_used") or "local"
    intent = state.get("intent") or "unknown"
    prompt_name = ((state.get("prompt_meta") or {}).get("name")) or "default"
    query = state.get("query") or ""
    contexts = state.get("retrieved_context") or []
    context_hint = ""
    if isinstance(contexts, list) and contexts:
        first = contexts[0]
        if isinstance(first, dict):
            context_hint = str(first.get("content") or first.get("text") or "")[:120]
    code_exec = ((state.get("metadata") or {}).get("code_exec_result") or {}).get("stdout", "")

    parts = [f"[provider={provider}]", f"[intent={intent}]", f"[prompt={prompt_name}]"]
    if query:
        parts.append(f"Query: {query}")
    if context_hint:
        parts.append(f"Context: {context_hint}")
    if code_exec:
        parts.append(f"Code output: {code_exec}")
    return "\n".join(parts)


async def response_node(state: WorkflowState, services: Any) -> WorkflowState:
    if state.get("response"):
        return state

    builder = getattr(services, "response_builder", None)
    if builder is not None:
        result = builder(state=state)
        state["response"] = await result if hasattr(result, "__await__") else result
    else:
        state["response"] = _build_default_response(state)

    metrics = state.setdefault("metrics", {})
    metrics["response_length"] = len(state.get("response") or "")
    return state
