"""Unit tests for E2B health-check bypass in CodeExecutionManager.

Root cause these tests protect against: the manager used to call
`provider.health()` before every execute, and E2B's health() does a full
Sandbox.create()+kill(). Combined with the real execute's own Sandbox.create(),
that meant 2x sandbox spins per request. These tests assert that when
`requested_mode == "e2b"`, manager-level health is never invoked; when
`requested_mode == "ppio"`, it still is.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.services.code_executor.manager import CodeExecutionManager
from backend.services.code_executor.providers.base import ExecutionResult


class _TrackingProvider:
    """Provider that counts how many times health() is called."""

    def __init__(self, result: ExecutionResult, *, healthy: bool = True):
        self.result = result
        self.execute_calls = 0
        self.health_calls = 0
        self._healthy = healthy

    async def execute(self, code, files=None, timeout_s=60):
        self.execute_calls += 1
        return self.result

    async def health(self):
        self.health_calls += 1
        return {"healthy": self._healthy, "status": "ok" if self._healthy else "bad"}

    def execute_code(self, code, data_files=None, timeout=None):
        self.execute_calls += 1
        return {
            "success": self.result.success,
            "stdout": self.result.stdout,
            "stderr": self.result.stderr,
            "error": self.result.error,
            "exit_code": 0 if self.result.success else 1,
            "execution_time": 0.0,
            "visualizations": [],
            "output_files": {},
        }


@pytest.mark.asyncio
async def test_async_e2b_mode_skips_health_check():
    """mode=e2b must NOT invoke provider.health() on the async path."""
    docker = MagicMock()
    cloud = _TrackingProvider(ExecutionResult(success=True, stdout="ok"))
    manager = CodeExecutionManager(docker_provider=docker, cloud_provider=cloud)

    result = await manager.execute("print('x')", mode="e2b")

    assert result.success is True
    assert cloud.execute_calls == 1
    assert cloud.health_calls == 0, (
        "manager must NOT call health() in e2b mode — that would duplicate "
        "the sandbox spin done by the real execute()"
    )


@pytest.mark.asyncio
async def test_async_ppio_mode_still_runs_health_check():
    """mode=ppio must keep the health gate (auto/cloud fallback depends on it)."""
    docker = MagicMock()
    cloud = _TrackingProvider(ExecutionResult(success=True, stdout="ok"))
    manager = CodeExecutionManager(docker_provider=docker, cloud_provider=cloud)

    result = await manager.execute("print('x')", mode="ppio")

    assert result.success is True
    assert cloud.execute_calls == 1
    assert cloud.health_calls == 1


@pytest.mark.asyncio
async def test_async_e2b_mode_skips_health_even_when_provider_would_be_unhealthy():
    """E2B mode bypasses health entirely, so an unhealthy report is irrelevant."""
    docker = MagicMock()
    cloud = _TrackingProvider(
        ExecutionResult(success=True, stdout="ok"), healthy=False
    )
    manager = CodeExecutionManager(docker_provider=docker, cloud_provider=cloud)

    result = await manager.execute("print('x')", mode="e2b")

    assert result.success is True
    assert cloud.health_calls == 0


def test_sync_e2b_mode_skips_health_check():
    """mode=e2b must NOT invoke health() on the sync execute_code path."""
    docker = MagicMock()
    cloud = _TrackingProvider(ExecutionResult(success=True, stdout="ok"))
    manager = CodeExecutionManager(docker_provider=docker, cloud_provider=cloud)

    result = manager.execute_code("print('x')", data_files=None, timeout=10, mode="e2b")

    assert result["success"] is True
    assert cloud.execute_calls == 1
    assert cloud.health_calls == 0


def test_sync_ppio_mode_still_runs_health_check():
    """mode=ppio keeps the sync health gate."""
    docker = MagicMock()
    cloud = _TrackingProvider(ExecutionResult(success=True, stdout="ok"))
    manager = CodeExecutionManager(docker_provider=docker, cloud_provider=cloud)

    result = manager.execute_code("print('x')", data_files=None, timeout=10, mode="ppio")

    assert result["success"] is True
    assert cloud.execute_calls == 1
    assert cloud.health_calls == 1
