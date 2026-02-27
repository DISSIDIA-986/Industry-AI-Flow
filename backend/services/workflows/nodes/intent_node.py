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
            "construction costs",
            "budget overrun",
            "cost risk",
            "project budget",
            "project cost",
            "cost forecast",
            "cost prediction",
            "how much does it cost",
            "how much will it cost",
            "price estimate",
            "price prediction",
            "analyze cost",
            "analyze costs",
        )
    ) or any(pattern.search(text) for pattern in _COST_PATTERNS):
        return "cost_estimation"
    if any(
        token in text
        for token in (
            "python",
            "script",
            "execute code",
            "run code",
            "code execution",
            "python program",
        )
    ):
        return "code_execution"
    if any(
        token in text
        for token in (
            "dataset",
            "csv",
            "dataframe",
            "data frame",
            "data analysis",
            "analyze data",
            "analyze the data",
            "analyze the dataset",
            "analyze this dataset",
            "statistical analysis",
        )
    ) or (
        any(w in text for w in ("analyze", "analysis"))
        and any(w in text for w in ("data", "dataset", "csv", "table", "spreadsheet", "chart", "plot", "graph", "statistics", "column", "row"))
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

    try:
        from backend.services.intent_classification.intent_classifier import QueryContext
        if isinstance(metadata, dict):
            valid_fields = set(QueryContext.__dataclass_fields__) if hasattr(QueryContext, '__dataclass_fields__') else set()
            context_obj = QueryContext(**{k: v for k, v in metadata.items() if k in valid_fields}) if valid_fields else metadata
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
