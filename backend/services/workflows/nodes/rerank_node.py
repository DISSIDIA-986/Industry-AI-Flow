"""Rerank node for workflow pipeline."""

from __future__ import annotations

from typing import Any

from backend.services.workflows.state import WorkflowState


def _default_rerank(contexts: list[dict], limit: int) -> list[dict]:
    ranked = sorted(
        contexts,
        key=lambda item: float(item.get("score", 0.0))
        if isinstance(item, dict)
        else 0.0,
        reverse=True,
    )
    return ranked[:limit]


async def rerank_node(state: WorkflowState, services: Any) -> WorkflowState:
    metadata = state.setdefault("metadata", {})
    metrics = state.setdefault("metrics", {})
    contexts = state.get("retrieved_context") or []
    if not isinstance(contexts, list):
        contexts = []

    top_k = int(metadata.get("rerank_top_k", 5))
    reranker = getattr(services, "reranker", None)

    if reranker is not None and hasattr(reranker, "rerank"):
        result = reranker.rerank(
            query=state.get("query", ""),
            documents=contexts,
            top_k=top_k,
        )
        ranked = await result if hasattr(result, "__await__") else result
        if isinstance(ranked, list):
            contexts = ranked
    else:
        contexts = _default_rerank(contexts, top_k)

    state["retrieved_context"] = contexts
    metrics["reranked_count"] = len(contexts)
    metadata["rerank_status"] = "ok"
    return state
