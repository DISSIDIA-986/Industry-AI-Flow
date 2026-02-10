"""Groundedness scoring node for workflow pipeline."""

from __future__ import annotations

from typing import Any

from backend.services.workflows.state import WorkflowState


async def groundedness_node(state: WorkflowState, services: Any) -> WorkflowState:
    del services

    metadata = state.setdefault("metadata", {})
    metrics = state.setdefault("metrics", {})
    contexts = state.get("retrieved_context") or []

    context_count = len(contexts) if isinstance(contexts, list) else 0
    score = min(1.0, context_count * 0.2)
    threshold = float(metadata.get("groundedness_threshold", 0.4))

    metrics["groundedness_score"] = score
    metadata["groundedness_score"] = score
    metadata["groundedness_passed"] = score >= threshold
    return state
