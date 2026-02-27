"""Groundedness scoring node for workflow pipeline."""

from __future__ import annotations

import re
from typing import Any

from backend.services.workflows.state import WorkflowState

_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*")


def _tokenize(text: str) -> set[str]:
    """Tokenize text using regex that strips punctuation (consistent with GroundednessChecker)."""
    return set(_TOKEN_RE.findall(text.lower()))


def _extract_context_text(ctx: Any) -> str:
    """Safely extract text content from a context item."""
    if isinstance(ctx, dict):
        return str(ctx.get("content", ctx.get("text", "")))
    return str(ctx)


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
        answer_tokens = _tokenize(answer)
        context_text = " ".join(_extract_context_text(c) for c in contexts)
        context_tokens = _tokenize(context_text)
        overlap = answer_tokens & context_tokens
        score = len(overlap) / max(len(answer_tokens), 1)

    metrics["groundedness_score"] = score
    metadata["groundedness_score"] = score
    metadata["groundedness_passed"] = score >= threshold
    return state
