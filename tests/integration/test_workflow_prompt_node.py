from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.services.workflows.nodes.prompt_node import prompt_node


@dataclass
class _PromptInfo:
    id: str
    name: str
    category: str
    version: str


class _FakePromptManager:
    async def get_prompt(self, **kwargs):
        info = _PromptInfo(
            id=str(uuid4()),
            name=kwargs["name"],
            category=kwargs["category"],
            version="1.0.0",
        )
        rendered = f"SYSTEM: {kwargs['variables']['query']}"
        return info, rendered


@pytest.mark.asyncio
async def test_prompt_node_sets_system_prompt_and_meta():
    state = {
        "query": "What is CSA A23.1?",
        "intent": "knowledge_retrieval",
        "retrieved_context": [{"content": "ctx"}],
        "metadata": {"prompt_experiments_enabled": True},
    }
    services = SimpleNamespace(prompt_manager=_FakePromptManager())

    updated = await prompt_node(state, services)

    assert updated["system_prompt"].startswith("SYSTEM:")
    assert updated["prompt_meta"]["name"] == "construction_rag_grounded_qa"
    assert updated["prompt_meta"]["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_prompt_node_noops_without_prompt_manager():
    state = {"query": "q", "metadata": {}}
    services = SimpleNamespace()

    updated = await prompt_node(state, services)

    assert updated is state
    assert "error" not in updated
    assert "system_prompt" not in updated
    assert "prompt_meta" not in updated
