"""Response construction node for workflow pipeline."""

from __future__ import annotations

from typing import Any

from backend.services.workflows.state import WorkflowState


def _build_default_response(state: WorkflowState) -> str:
    if state.get("error"):
        return "Your request could not be processed. Please try rephrasing your question."

    # Return a safe generic acknowledgment without leaking internal debug
    # information (provider name, intent type, raw query, context snippets).
    intent = state.get("intent") or "unknown"
    code_exec_result = ((state.get("metadata") or {}).get("code_exec_result") or {}).get("stdout", "")

    if code_exec_result:
        return f"Code output: {code_exec_result}"

    intent_labels = {
        "knowledge_retrieval": "I found relevant information for your question.",
        "cost_estimation": "Cost estimation analysis is ready.",
        "data_analysis": "Data analysis has been completed.",
        "code_execution": "Code execution has finished.",
        "document_processing": "Document processing is complete.",
    }
    return intent_labels.get(intent, "Your request has been processed.")


async def response_node(state: WorkflowState, services: Any) -> WorkflowState:
    # On error, use default response without wasting an LLM call
    if state.get("error"):
        state["response"] = _build_default_response(state)
        metrics = state.setdefault("metrics", {})
        metrics["response_length"] = len(state.get("response") or "")
        return state

    if state.get("response"):
        return state

    builder = getattr(services, "response_builder", None)
    if builder is not None:
        result = builder(state=state)
        result = await result if hasattr(result, "__await__") else result
        state["response"] = result if result is not None else _build_default_response(state)
    else:
        state["response"] = _build_default_response(state)

    metrics = state.setdefault("metrics", {})
    metrics["response_length"] = len(state.get("response") or "")
    return state
