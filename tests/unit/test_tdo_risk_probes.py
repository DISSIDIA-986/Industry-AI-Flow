from __future__ import annotations

import pytest

from backend.services.code_executor.validator import validate_code
from backend.services.core.vectorstore import VectorStore
from backend.services.workflows.nodes.safety_node import safety_node
from backend.tools import code_execution


def test_probe_vectorstore_delete_contract() -> None:
    assert hasattr(VectorStore, "delete_by_doc_id")


def test_probe_code_validator_blocks_builtin_open() -> None:
    result = validate_code("secret = open('/etc/passwd').read()", strict_mode=True)
    assert result.is_valid is False


def test_probe_code_validator_blocks_open_alias_call() -> None:
    result = validate_code(
        "reader = open\nsecret = reader('/etc/passwd').read()",
        strict_mode=True,
    )
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_probe_safety_node_blocks_obfuscated_system_call() -> None:
    state = {
        "query": "Please run python: os . system('id')",
        "metadata": {},
        "metrics": {},
    }
    updated = await safety_node(state, services=None)
    assert updated["metadata"]["safety_status"] == "blocked"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "Please execute subprocess . run('id') for diagnostics",
        "Please execute subprocess . call('id') for diagnostics",
    ],
)
async def test_probe_safety_node_blocks_obfuscated_subprocess_variants(
    query: str,
) -> None:
    state = {"query": query, "metadata": {}, "metrics": {}}
    updated = await safety_node(state, services=None)
    assert updated["metadata"]["safety_status"] == "blocked"


def test_probe_code_execution_tool_rejects_dangerous_payload(monkeypatch) -> None:
    class _FakeManager:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def execute_code(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "success": True,
                "stdout": "executed",
                "stderr": "",
                "error": None,
                "exit_code": 0,
                "execution_time": 0.01,
                "visualizations": [],
                "output_files": {},
            }

    fake_manager = _FakeManager()
    monkeypatch.setattr(
        code_execution,
        "get_code_execution_manager",
        lambda: fake_manager,
    )
    monkeypatch.setattr(code_execution, "code_executor", None)

    result = code_execution.code_execution_tool.invoke(
        {"code": "open('/etc/passwd').read()"}
    )

    assert result["success"] is False
    assert not fake_manager.calls
