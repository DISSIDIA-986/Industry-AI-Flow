from __future__ import annotations

import pytest

from backend.services.code_executor.manager import CodeExecutionManager
from backend.services.code_executor.providers.base import ExecutionResult


class _FakeProvider:
    def __init__(self, result: ExecutionResult):
        self.result = result
        self.calls = 0

    async def execute(self, code, files=None, timeout_s=60):
        self.calls += 1
        return self.result

    async def health(self):
        return {"healthy": True}


class _UnhealthyProvider(_FakeProvider):
    async def health(self):
        return {"healthy": False, "status": "circuit_open"}


@pytest.mark.asyncio
async def test_auto_mode_fallback_to_ppio_on_docker_failure():
    docker = _FakeProvider(ExecutionResult(success=False, error="docker failed"))
    ppio = _FakeProvider(ExecutionResult(success=True, stdout="cloud ok"))
    manager = CodeExecutionManager(docker_provider=docker, ppio_provider=ppio)

    result = await manager.execute("print('x')", mode="auto")

    assert result.success is True
    assert result.stdout == "cloud ok"
    assert docker.calls == 1
    assert ppio.calls == 1


@pytest.mark.asyncio
async def test_auto_mode_returns_combined_error_when_both_fail():
    docker = _FakeProvider(ExecutionResult(success=False, error="docker failed"))
    ppio = _FakeProvider(ExecutionResult(success=False, error="ppio failed"))
    manager = CodeExecutionManager(docker_provider=docker, ppio_provider=ppio)

    result = await manager.execute("print('x')", mode="auto")

    assert result.success is False
    assert "docker_error=docker failed" in (result.error or "")
    assert "ppio_error=ppio failed" in (result.error or "")


@pytest.mark.asyncio
async def test_ppio_mode_requires_provider():
    docker = _FakeProvider(ExecutionResult(success=True, stdout="local ok"))
    manager = CodeExecutionManager(docker_provider=docker, ppio_provider=None)

    result = await manager.execute("print('x')", mode="ppio")

    assert result.success is False
    assert result.error == "PPIO provider unavailable"


@pytest.mark.asyncio
async def test_auto_mode_skips_ppio_when_unhealthy():
    docker = _FakeProvider(ExecutionResult(success=False, error="docker failed"))
    ppio = _UnhealthyProvider(ExecutionResult(success=True, stdout="cloud ok"))
    manager = CodeExecutionManager(docker_provider=docker, ppio_provider=ppio)

    result = await manager.execute("print('x')", mode="auto")

    assert result.success is False
    assert "docker_error=docker failed" in (result.error or "")
    assert "ppio_unhealthy=circuit_open" in (result.error or "")
    assert ppio.calls == 0
