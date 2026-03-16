"""Intent classification node for workflow pipeline."""

from __future__ import annotations

import re
from typing import Any, Optional

from backend.services.intent_classification.capability_registry import (
    get_capability_registry,
)
from backend.services.workflows.state import WorkflowState


def _heuristic_intent(query: str) -> str:
    """Classify query using the Capability Registry's heuristic matching."""
    registry = get_capability_registry()
    intent, _confidence, _reasoning = registry.classify_heuristic(query)
    return intent


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

    try:
        from backend.services.intent_classification.intent_classifier import (
            QueryContext,
        )

        if isinstance(metadata, dict):
            valid_fields = (
                set(QueryContext.__dataclass_fields__)
                if hasattr(QueryContext, "__dataclass_fields__")
                else set()
            )
            context_obj = (
                QueryContext(**{k: v for k, v in metadata.items() if k in valid_fields})
                if valid_fields
                else metadata
            )
        else:
            context_obj = metadata
    except (ImportError, TypeError):
        context_obj = metadata

    if hasattr(classifier, "classify_intent"):
        sig = inspect.signature(classifier.classify_intent)
        params = set(sig.parameters.keys()) - {"self"}
        if {"query", "context"} <= params:
            result = classifier.classify_intent(query=query, context=context_obj)
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


def _extract_code_from_query(query: str) -> Optional[str]:
    """Extract code blocks from user query for code_execution intent."""
    # Try fenced code blocks first
    match = re.search(r"```(?:python)?\s*\n(.+?)```", query, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try inline code
    match = re.search(r"`(.+?)`", query, re.DOTALL)
    if match and "\n" in match.group(1):
        return match.group(1).strip()
    return None


async def intent_node(state: WorkflowState, services: Any) -> WorkflowState:
    metadata = state.setdefault("metadata", {})
    query = state.get("query", "")

    classifier = getattr(services, "intent_classifier", None)
    if classifier is None:
        state["intent"] = _heuristic_intent(query)
        metadata["intent_source"] = "heuristic"
        metadata["intent_confidence"] = 0.85
    elif (result := await _call_classifier(classifier, query, metadata)) is not None:
        if isinstance(result, dict):
            extracted = _extract_intent_value(result.get("intent"))
            state["intent"] = extracted or _heuristic_intent(query)
            metadata["intent_confidence"] = result.get("confidence", 0.85)
        elif hasattr(result, "intent"):
            extracted = _extract_intent_value(getattr(result, "intent"))
            state["intent"] = extracted or _heuristic_intent(query)
            metadata["intent_confidence"] = getattr(result, "confidence", 0.85)
        else:
            state["intent"] = _extract_intent_value(result) or _heuristic_intent(query)
            metadata["intent_confidence"] = 0.85
        metadata["intent_source"] = "classifier"
    else:
        state["intent"] = _heuristic_intent(query)
        metadata["intent_source"] = "heuristic"
        metadata["intent_confidence"] = 0.85

    # Extract code from query when intent is code_execution
    if state.get("intent") == "code_execution" and not metadata.get("code_to_execute"):
        code = _extract_code_from_query(query)
        if code:
            metadata["code_to_execute"] = code

    return state
