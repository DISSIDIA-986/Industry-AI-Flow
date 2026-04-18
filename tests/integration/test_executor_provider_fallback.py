from __future__ import annotations

import pytest

from backend.services.code_executor.manager import CodeExecutionManager
from backend.services.code_executor.providers.base import ExecutionResult


class _FakeProvider:
    def __init__(self, result: ExecutionResult):
        self.result = result
        self.calls = 0
        self.health_calls = 0

    async def execute(self, code, files=None, timeout_s=60):
        self.calls += 1
        return self.result

    async def health(self):
        self.health_calls += 1
        return {"healthy": True}


class _UnhealthyProvider(_FakeProvider):
    async def health(self):
        self.health_calls += 1
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
    assert "cloud_error=ppio failed" in (result.error or "")


@pytest.mark.asyncio
async def test_ppio_mode_requires_provider():
    docker = _FakeProvider(ExecutionResult(success=True, stdout="local ok"))
    manager = CodeExecutionManager(docker_provider=docker, ppio_provider=None)

    result = await manager.execute("print('x')", mode="ppio")

    assert result.success is False
    assert result.error == "ppio provider unavailable"


@pytest.mark.asyncio
async def test_auto_mode_skips_ppio_when_unhealthy():
    docker = _FakeProvider(ExecutionResult(success=False, error="docker failed"))
    ppio = _UnhealthyProvider(ExecutionResult(success=True, stdout="cloud ok"))
    manager = CodeExecutionManager(docker_provider=docker, ppio_provider=ppio)

    result = await manager.execute("print('x')", mode="auto")

    assert result.success is False
    assert "docker_error=docker failed" in (result.error or "")
    assert "cloud_unhealthy=circuit_open" in (result.error or "")
    assert ppio.calls == 0


@pytest.mark.asyncio
async def test_e2b_mode_requires_provider():
    docker = _FakeProvider(ExecutionResult(success=True, stdout="local ok"))
    manager = CodeExecutionManager(docker_provider=docker, cloud_provider=None)

    result = await manager.execute("print('x')", mode="e2b")

    assert result.success is False
    assert "provider unavailable" in (result.error or "")


@pytest.mark.asyncio
async def test_auto_mode_with_e2b_cloud_provider_still_runs_health_and_execute():
    """Auto mode with E2B as the cloud provider: health() + execute() both run.

    Documents current behavior: the e2b-mode health bypass does NOT extend to
    auto mode. When docker fails and auto falls back to cloud, the manager
    still calls health() (which, for E2B in reality, spins a Sandbox.create).
    This is intentional for auto mode — health gates the cloud fallback
    decision. If this invariant ever needs to change, a separate design
    conversation is warranted.
    """
    docker = _FakeProvider(ExecutionResult(success=False, error="docker failed"))
    cloud = _FakeProvider(ExecutionResult(success=True, stdout="e2b ok"))
    # Simulate E2B-as-cloud-provider by naming (actual type doesn't matter;
    # manager routes by requested_mode, not provider class).
    manager = CodeExecutionManager(docker_provider=docker, cloud_provider=cloud)

    result = await manager.execute("print('x')", mode="auto")

    assert result.success is True
    assert result.stdout == "e2b ok"
    assert docker.calls == 1
    assert cloud.calls == 1
    # Critical: auto mode STILL runs health() on the cloud provider. This is
    # the 2x-spin path the e2b explicit-mode bypass does NOT cover. Pinning
    # this assertion so a regression that silently changes auto-mode health
    # behavior is caught here.
    assert cloud.health_calls == 1, (
        "auto mode must still gate cloud fallback on health() — the "
        "explicit-e2b-mode bypass does not extend to auto mode by design"
    )


@pytest.mark.asyncio
async def test_e2b_mode_bypasses_unhealthy_gate():
    """E2B bypass: even an 'unhealthy' health() must not block execution,
    because manager.execute should not even call health() in e2b mode.

    This is the integration-level counterpart to the unit tests in
    tests/unit/test_code_execution_manager_e2b_bypass.py.
    """
    docker = _FakeProvider(ExecutionResult(success=True, stdout="local ok"))
    cloud = _UnhealthyProvider(ExecutionResult(success=True, stdout="e2b ok"))
    manager = CodeExecutionManager(docker_provider=docker, cloud_provider=cloud)

    result = await manager.execute("print('x')", mode="e2b")

    assert result.success is True
    assert result.stdout == "e2b ok"
    assert cloud.calls == 1
