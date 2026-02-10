"""Prompt node for workflow pipeline."""

from __future__ import annotations

from typing import Any

from backend.services.workflows.prompting.template_selector import TemplateSelector
from backend.services.workflows.state import WorkflowState


async def prompt_node(state: WorkflowState, services: Any) -> WorkflowState:
    """Select and render prompt template, then attach prompt metadata to state."""
    selector = getattr(services, "template_selector", None) or TemplateSelector()
    prompt_manager = getattr(services, "prompt_manager", None)
    if prompt_manager is None:
        state["error"] = "prompt_manager service is required"
        return state

    template_name, template_category = selector.select(state)
    metadata = state.get("metadata") or {}

    prompt_info, rendered = await prompt_manager.get_prompt(
        name=template_name,
        category=template_category,
        context=metadata,
        variables={
            "query": state.get("query", ""),
            "context": state.get("retrieved_context", []),
            "intent": state.get("intent"),
        },
        enable_experiments=bool(metadata.get("prompt_experiments_enabled", False)),
    )

    state["system_prompt"] = rendered
    state["prompt_meta"] = {
        "prompt_id": str(prompt_info.id),
        "name": prompt_info.name,
        "version": prompt_info.version,
        "category": prompt_info.category,
    }
    return state
