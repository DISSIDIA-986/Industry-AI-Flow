"""Retrieval node for workflow pipeline."""

from __future__ import annotations

import asyncio
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
            if hasattr(result, "__await__"):
                contexts = await result
            else:
                # Synchronous retriever — offload to thread pool
                contexts = await asyncio.to_thread(
                    retriever.retrieve, query=query, top_k=top_k, metadata=metadata
                )
        elif hasattr(retriever, "search"):
            result = retriever.search(query=query, top_k=top_k)
            if hasattr(result, "__await__"):
                contexts = await result
            else:
                contexts = await asyncio.to_thread(
                    retriever.search, query=query, top_k=top_k
                )

    if not isinstance(contexts, list):
        contexts = []

    state["retrieved_context"] = contexts
    metrics["retrieved_count"] = len(contexts)
    metadata["retrieval_status"] = "ok"
    return state
