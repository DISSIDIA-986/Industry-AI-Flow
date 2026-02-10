"""Retrieval node for workflow pipeline."""

from __future__ import annotations

from typing import Any

from backend.services.workflows.state import WorkflowState


async def retrieval_node(state: WorkflowState, services: Any) -> WorkflowState:
    metadata = state.setdefault("metadata", {})
    metrics = state.setdefault("metrics", {})
    query = state.get("query", "")
    top_k = int(metadata.get("retrieval_top_k", 5))

    retriever = getattr(services, "retriever", None)
    contexts = state.get("retrieved_context") or []

    if retriever is not None:
        if hasattr(retriever, "retrieve"):
            result = retriever.retrieve(query=query, top_k=top_k, metadata=metadata)
            contexts = await result if hasattr(result, "__await__") else result
        elif hasattr(retriever, "search"):
            result = retriever.search(query=query, top_k=top_k)
            contexts = await result if hasattr(result, "__await__") else result

    if not isinstance(contexts, list):
        contexts = []

    state["retrieved_context"] = contexts
    metrics["retrieved_count"] = len(contexts)
    metadata["retrieval_status"] = "ok"
    return state
