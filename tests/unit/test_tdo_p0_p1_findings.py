from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.workflow_query_routes import (
    get_workflow_runner,
    router as workflow_router,
)
from backend.services.code_executor.docker_executor import DockerExecutor, ExecutionResult
from backend.services.code_executor.providers.docker_provider import DockerExecutionProvider
from backend.services.code_executor.providers.ppio_provider import PPIOExecutionProvider


def test_p1_workflow_query_runner_exception_is_controlled() -> None:
    class _BoomRunner:
        async def run_workflow(
            self,
            query: str,
            session_id: str,
            user_id=None,
            thread_id=None,
            route_mode=None,
        ):
            del query, session_id, user_id, thread_id, route_mode
            raise RuntimeError("boom")

    app = FastAPI()
    app.include_router(workflow_router)

    async def _override_runner():
        return _BoomRunner()

    app.dependency_overrides[get_workflow_runner] = _override_runner
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/workflow/query",
        json={"query": "trigger failure", "session_id": "tdo-risk-session"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "workflow execution failed"
    assert payload["trace_id"]


def test_p0_docker_executor_rejects_out_of_workspace_data_files() -> None:
    # Build executor instance without Docker daemon initialization.
    executor = object.__new__(DockerExecutor)
    executor.timeout = 60

    def _fake_execute(code: str, input_files=None):
        del code, input_files
        return ExecutionResult(
            success=True,
            stdout="ok",
            stderr="",
            error=None,
            execution_time=0.01,
            output_files={},
        )

    executor.execute = _fake_execute

    result = executor.execute_code(
        code="print('ok')",
        data_files=["/etc/hosts"],
        timeout=30,
    )

    assert result["success"] is False
    assert "outside allowed paths" in (result["error"] or "")


def test_p1_docker_provider_execute_propagates_timeout() -> None:
    class _FakeExecutor:
        def __init__(self) -> None:
            self.timeout_seen = None

        def execute(self, code: str, input_files=None, timeout=None):
            del code, input_files
            self.timeout_seen = timeout
            return ExecutionResult(
                success=True,
                stdout="ok",
                stderr="",
                error=None,
                execution_time=0.02,
                output_files={},
            )

    fake_executor = _FakeExecutor()
    provider = DockerExecutionProvider(executor=fake_executor)

    result = asyncio.run(provider.execute(code="print('ok')", timeout_s=7))

    assert result.success is True
    assert fake_executor.timeout_seen == 7


def test_p0_ppio_provider_rejects_out_of_workspace_data_files() -> None:
    result = PPIOExecutionProvider(enabled=False).execute_code(
        code="print('ok')",
        data_files=["/etc/hosts"],
        timeout=5,
    )
    assert result["success"] is False
    assert "outside allowed paths" in (result["error"] or "")
