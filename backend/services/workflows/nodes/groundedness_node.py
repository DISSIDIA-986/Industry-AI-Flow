"""Groundedness scoring node for workflow pipeline."""

from __future__ import annotations

from typing import Any

from backend.services.workflows.state import WorkflowState


async def groundedness_node(state: WorkflowState, services: Any) -> WorkflowState:
    del services

    metadata = state.setdefault("metadata", {})
    metrics = state.setdefault("metrics", {})
    contexts = state.get("retrieved_context") or []
    answer = state.get("response") or state.get("answer") or ""

    context_count = len(contexts) if isinstance(contexts, list) else 0
    threshold = float(metadata.get("groundedness_threshold", 0.4))

    if not answer or context_count == 0:
        score = 0.0
    else:
        answer_tokens = set(answer.lower().split())
        context_text = " ".join(
            c.get("content", c) if isinstance(c, dict) else str(c)
            for c in contexts
        )
        context_tokens = set(context_text.lower().split())
        overlap = answer_tokens & context_tokens
        score = len(overlap) / max(len(answer_tokens), 1)

    metrics["groundedness_score"] = score
    metadata["groundedness_score"] = score
    metadata["groundedness_passed"] = score >= threshold
    return state
