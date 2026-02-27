"""Retrieval node for workflow pipeline."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

from backend.services.workflows.state import WorkflowState


async def retrieval_node(state: WorkflowState, services: Any) -> WorkflowState:
    metadata = state.setdefault("metadata", {})
    metrics = state.setdefault("metrics", {})
    query = state.get("query", "")
    top_k = int(metadata.get("retrieval_top_k", 5))

    retriever = getattr(services, "retriever", None)
    contexts = state.get("retrieved_context") or []

    # Skip retrieval only for intents that have dedicated structured pipelines.
    # code_execution may still need retrieved context for grounded explanations.
    intent = state.get("intent", "")
    if intent == "cost_estimation":
        metadata["retrieval_status"] = "skipped"
        state["retrieved_context"] = contexts
        metrics["retrieved_count"] = len(contexts)
        return state

    if retriever is not None:
        if hasattr(retriever, "retrieve"):
            if inspect.iscoroutinefunction(retriever.retrieve):
                contexts = await retriever.retrieve(query=query, top_k=top_k, metadata=metadata)
            else:
                contexts = await asyncio.to_thread(
                    retriever.retrieve, query=query, top_k=top_k, metadata=metadata
                )
        elif hasattr(retriever, "search"):
            if inspect.iscoroutinefunction(retriever.search):
                contexts = await retriever.search(query=query, top_k=top_k)
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
