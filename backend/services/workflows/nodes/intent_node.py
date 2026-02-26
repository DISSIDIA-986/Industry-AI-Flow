"""Intent classification node for workflow pipeline."""

from __future__ import annotations

import re
from typing import Any, Optional

from backend.services.workflows.state import WorkflowState


_COST_PATTERNS = (
    re.compile(
        r"(estimate|estimating|predict|forecast|project).{0,32}"
        r"(cost|budget|overrun|expense|price)"
    ),
    re.compile(
        r"(cost|budget|overrun|expense|price).{0,32}"
        r"(estimate|estimation|predict|forecast|projection)"
    ),
)


def _heuristic_intent(query: str) -> str:
    text = (query or "").strip().lower()
    # Cost estimation checked FIRST — higher business priority and avoids
    # mis-routing "predict cost using python" to code_execution.
    if any(
        token in text
        for token in (
            "cost estimate",
            "cost estimation",
            "estimate cost",
            "budget estimate",
            "cost overrun",
            "construction cost",
            "budget overrun",
            "cost risk",
            "project budget",
            "project cost",
            "cost forecast",
            "cost prediction",
            "how much",
            "price",
        )
    ) or any(pattern.search(text) for pattern in _COST_PATTERNS):
        return "cost_estimation"
    if any(
        token in text
        for token in (
            "python",
            "script",
            "execute",
            "run code",
            "code execution",
            "program",
        )
    ):
        return "code_execution"
    if any(
        token in text
        for token in (
            "analyze",
            "analysis",
            "dataset",
            "csv",
            "dataframe",
            "data frame",
        )
    ):
        return "data_analysis"
    if any(
        token in text
        for token in (
            "document",
            "pdf",
            "ocr",
            "extract text",
            "file upload",
            "scan",
        )
    ):
        return "document_processing"
    return "knowledge_retrieval"


def _extract_intent_value(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    if hasattr(raw, "value"):
        return str(getattr(raw, "value"))
    return str(raw)


async def _call_classifier(classifier: Any, query: str, metadata: dict) -> Any:
    import inspect

    if hasattr(classifier, "classify_intent"):
        sig = inspect.signature(classifier.classify_intent)
        params = set(sig.parameters.keys()) - {"self"}
        if {"query", "context"} <= params:
            result = classifier.classify_intent(query=query, context=metadata)
        elif {"query", "metadata"} <= params:
            result = classifier.classify_intent(query=query, metadata=metadata)
        elif "query" in params:
            result = classifier.classify_intent(query=query)
        else:
            result = None
        if result is not None:
            return await result if hasattr(result, "__await__") else result

    if hasattr(classifier, "classify"):
        result = classifier.classify(query=query, metadata=metadata)
        return await result if hasattr(result, "__await__") else result

    return None


async def intent_node(state: WorkflowState, services: Any) -> WorkflowState:
    metadata = state.setdefault("metadata", {})
    query = state.get("query", "")

    classifier = getattr(services, "intent_classifier", None)
    if classifier is None:
        state["intent"] = _heuristic_intent(query)
        metadata["intent_source"] = "heuristic"
        metadata["intent_confidence"] = 0.85
        return state

    result = await _call_classifier(classifier, query, metadata)
    if result is not None:
        if isinstance(result, dict):
            extracted = _extract_intent_value(result.get("intent"))
            state["intent"] = extracted or _heuristic_intent(query)
            if "confidence" in result:
                metadata["intent_confidence"] = result.get("confidence")
        elif hasattr(result, "intent"):
            extracted = _extract_intent_value(getattr(result, "intent"))
            state["intent"] = extracted or _heuristic_intent(query)
            if hasattr(result, "confidence"):
                metadata["intent_confidence"] = getattr(result, "confidence")
        else:
            state["intent"] = _extract_intent_value(result) or _heuristic_intent(query)
        metadata["intent_source"] = "classifier"
        return state

    state["intent"] = _heuristic_intent(query)
    metadata["intent_source"] = "heuristic"
    metadata["intent_confidence"] = 0.85
    return state
