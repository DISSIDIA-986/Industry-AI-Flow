"""Docker-backed execution provider adapter."""

from __future__ import annotations

import asyncio
from typing import Dict, Optional

from backend.services.code_executor.providers.base import ExecutionResult


class DockerExecutionProvider:
    def __init__(self, executor=None):
        if executor is None:
            from backend.services.code_executor.docker_executor import DockerExecutor

            executor = DockerExecutor()
        self.executor = executor

    async def execute(
        self,
        code: str,
        files: Optional[Dict[str, bytes]] = None,
        timeout_s: int = 60,
    ) -> ExecutionResult:
        try:
            result = self.executor.execute(code, input_files=files, timeout=timeout_s)
        except TypeError:
            # Backward compatibility for custom executors without timeout parameter.
            result = self.executor.execute(code, input_files=files)
        return ExecutionResult(
            success=result.success,
            stdout=result.stdout,
            stderr=result.stderr,
            error=result.error,
            execution_time_s=result.execution_time,
            output_files=result.output_files,
        )

    def execute_code(
        self,
        code: str,
        data_files: Optional[list[str]] = None,
        timeout: Optional[int] = None,
    ) -> dict:
        return self.executor.execute_code(
            code=code, data_files=data_files, timeout=timeout
        )

    async def health(self) -> dict:
        def _probe() -> dict:
            client = getattr(self.executor, "client", None)
            if client is None:
                return {
                    "provider": "docker",
                    "healthy": False,
                    "status": "client_unavailable",
                }
            try:
                client.ping()
            except Exception as exc:
                return {
                    "provider": "docker",
                    "healthy": False,
                    "status": "daemon_unreachable",
                    "error": str(exc),
                }

            try:
                smoke = self.executor.execute("print('docker_health_ok')")
            except Exception as exc:
                return {
                    "provider": "docker",
                    "healthy": False,
                    "status": "sandbox_probe_failed",
                    "error": str(exc),
                }

            if not smoke.success:
                return {
                    "provider": "docker",
                    "healthy": False,
                    "status": "sandbox_probe_failed",
                    "error": smoke.error or smoke.stderr or "unknown_error",
                }

            return {
                "provider": "docker",
                "healthy": True,
                "status": "ok",
            }

        return await asyncio.to_thread(_probe)
