"""Prompt rendering facade used by workflow nodes."""

from __future__ import annotations

from typing import Any, Dict, Tuple


class PromptRenderService:
    """Thin adapter around PromptManager.get_prompt."""

    def __init__(self, prompt_manager: Any):
        self.prompt_manager = prompt_manager

    async def render(
        self,
        *,
        name: str,
        category: str,
        context: Dict[str, Any] | None,
        variables: Dict[str, Any] | None,
        enable_experiments: bool,
    ) -> Tuple[Any, str]:
        return await self.prompt_manager.get_prompt(
            name=name,
            category=category,
            context=context,
            variables=variables,
            enable_experiments=enable_experiments,
        )
