"""Intent-aware prompt template selector."""

from __future__ import annotations

from typing import Tuple

from backend.services.workflows.prompting.template_registry import (
    DEFAULT_TEMPLATE,
    INTENT_TO_TEMPLATE,
)
from backend.services.workflows.state import WorkflowState


class TemplateSelector:
    """Select template name/category from workflow state."""

    def select(self, state: WorkflowState) -> Tuple[str, str]:
        intent = (state.get("intent") or "").strip().lower()
        spec = INTENT_TO_TEMPLATE.get(intent, DEFAULT_TEMPLATE)
        return spec.name, spec.category
