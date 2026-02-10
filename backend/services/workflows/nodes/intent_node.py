"""Intent classification node for workflow pipeline."""

from __future__ import annotations

from typing import Any

from backend.services.workflows.state import WorkflowState


def _heuristic_intent(query: str) -> str:
    text = (query or "").strip().lower()
    if any(token in text for token in ("python", "script", "execute", "run code")):
        return "code_execution"
    if any(token in text for token in ("analyze", "analysis", "dataset", "csv")):
        return "data_analysis"
    if any(token in text for token in ("document", "pdf", "ocr", "extract text")):
        return "document_processing"
    return "knowledge_retrieval"


async def intent_node(state: WorkflowState, services: Any) -> WorkflowState:
    metadata = state.setdefault("metadata", {})
    query = state.get("query", "")

    classifier = getattr(services, "intent_classifier", None)
    if classifier is None:
        state["intent"] = _heuristic_intent(query)
        metadata["intent_source"] = "heuristic"
        return state

    if hasattr(classifier, "classify"):
        result = classifier.classify(query=query, metadata=metadata)
        if hasattr(result, "__await__"):
            result = await result
        if isinstance(result, dict):
            state["intent"] = str(result.get("intent") or _heuristic_intent(query))
        else:
            state["intent"] = str(result or _heuristic_intent(query))
        metadata["intent_source"] = "classifier"
        return state

    state["intent"] = _heuristic_intent(query)
    metadata["intent_source"] = "heuristic"
    return state
