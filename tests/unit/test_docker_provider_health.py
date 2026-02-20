from __future__ import annotations

import pytest

from backend.services.code_executor.providers.docker_provider import DockerExecutionProvider


class _SmokeResult:
    def __init__(self, success: bool, error: str | None = None, stderr: str = "") -> None:
        self.success = success
        self.error = error
        self.stderr = stderr


class _FakeClient:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def ping(self) -> None:
        if self.should_fail:
            raise RuntimeError("docker ping failed")


class _FakeExecutor:
    def __init__(self, *, ping_fail: bool = False, smoke_success: bool = True) -> None:
        self.client = _FakeClient(should_fail=ping_fail)
        self._smoke_success = smoke_success

    def execute(self, code: str, input_files=None):  # noqa: ANN001
        del code, input_files
        if self._smoke_success:
            return _SmokeResult(success=True)
        return _SmokeResult(success=False, error="sandbox unavailable")

    def execute_code(self, code: str, data_files=None, timeout=None):  # noqa: ANN001
        del code, data_files, timeout
        return {"success": True}


@pytest.mark.asyncio
async def test_docker_provider_health_reports_ok_when_ping_and_probe_pass() -> None:
    provider = DockerExecutionProvider(executor=_FakeExecutor())
    health = await provider.health()
    assert health["healthy"] is True
    assert health["status"] == "ok"


@pytest.mark.asyncio
async def test_docker_provider_health_reports_unreachable_daemon() -> None:
    provider = DockerExecutionProvider(executor=_FakeExecutor(ping_fail=True))
    health = await provider.health()
    assert health["healthy"] is False
    assert health["status"] == "daemon_unreachable"


@pytest.mark.asyncio
async def test_docker_provider_health_reports_probe_failure() -> None:
    provider = DockerExecutionProvider(executor=_FakeExecutor(smoke_success=False))
    health = await provider.health()
    assert health["healthy"] is False
    assert health["status"] == "sandbox_probe_failed"
