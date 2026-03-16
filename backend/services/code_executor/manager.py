"""Provider-aware code execution manager with fallback strategy."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from typing import Dict, Optional

from backend.services.code_executor.providers.base import (
    ExecutionProvider,
    ExecutionResult,
)


@dataclass
class CodeExecutionManager:
    docker_provider: ExecutionProvider
    ppio_provider: Optional[ExecutionProvider] = None

    async def execute(
        self,
        code: str,
        files: Optional[Dict[str, bytes]] = None,
        timeout_s: int = 60,
        mode: str = "docker",
    ) -> ExecutionResult:
        requested_mode = (mode or "docker").strip().lower()

        if requested_mode == "ppio":
            if self.ppio_provider is None:
                return ExecutionResult(success=False, error="PPIO provider unavailable")
            ppio_health = await self._provider_health(self.ppio_provider)
            if ppio_health is not None and not ppio_health.get("healthy", False):
                return ExecutionResult(
                    success=False,
                    error=f"PPIO provider unhealthy: {ppio_health.get('status', 'unknown')}",
                )
            return await self.ppio_provider.execute(code, files, timeout_s)

        if requested_mode == "auto" and self.ppio_provider is not None:
            docker_result = await self.docker_provider.execute(code, files, timeout_s)
            if docker_result.success:
                return docker_result
            ppio_health = await self._provider_health(self.ppio_provider)
            if ppio_health is not None and not ppio_health.get("healthy", False):
                combined_error = (
                    f"docker_error={docker_result.error or docker_result.stderr}; "
                    f"ppio_unhealthy={ppio_health.get('status', 'unknown')}"
                )
                return ExecutionResult(success=False, error=combined_error)
            ppio_result = await self.ppio_provider.execute(code, files, timeout_s)
            if ppio_result.success:
                return ppio_result
            combined_error = (
                f"docker_error={docker_result.error or docker_result.stderr}; "
                f"ppio_error={ppio_result.error or ppio_result.stderr}"
            )
            return ExecutionResult(success=False, error=combined_error)

        return await self.docker_provider.execute(code, files, timeout_s)

    def execute_code(
        self,
        code: str,
        data_files: Optional[list[str]] = None,
        timeout: Optional[int] = None,
        mode: str = "docker",
    ) -> dict:
        requested_mode = (mode or "docker").strip().lower()

        if requested_mode == "ppio":
            if self.ppio_provider is None:
                return self._error_result("PPIO provider unavailable")
            ppio_health = self._provider_health_sync(self.ppio_provider)
            if ppio_health is not None and not ppio_health.get("healthy", False):
                return self._error_result(
                    f"PPIO provider unhealthy: {ppio_health.get('status', 'unknown')}"
                )
            return self._execute_provider_sync(
                self.ppio_provider, code, data_files, timeout
            )

        if requested_mode == "auto":
            docker_result = self._execute_provider_sync(
                self.docker_provider, code, data_files, timeout
            )
            if docker_result.get("success"):
                return docker_result
            if self.ppio_provider is None:
                return docker_result
            ppio_health = self._provider_health_sync(self.ppio_provider)
            if ppio_health is not None and not ppio_health.get("healthy", False):
                docker_error = docker_result.get("error") or docker_result.get("stderr")
                return self._error_result(
                    f"docker_error={docker_error}; "
                    f"ppio_unhealthy={ppio_health.get('status', 'unknown')}",
                    docker_result,
                )
            ppio_result = self._execute_provider_sync(
                self.ppio_provider, code, data_files, timeout
            )
            if ppio_result.get("success"):
                return ppio_result
            docker_error = docker_result.get("error") or docker_result.get("stderr")
            ppio_error = ppio_result.get("error") or ppio_result.get("stderr")
            return self._error_result(
                f"docker_error={docker_error}; ppio_error={ppio_error}",
                docker_result,
            )

        return self._execute_provider_sync(
            self.docker_provider, code, data_files, timeout
        )

    def _execute_provider_sync(
        self,
        provider: ExecutionProvider,
        code: str,
        data_files: Optional[list[str]],
        timeout: Optional[int],
    ) -> dict:
        if hasattr(provider, "execute_code"):
            return provider.execute_code(
                code=code, data_files=data_files, timeout=timeout
            )

        timeout_s = int(timeout) if timeout else 60
        result = self._run_coro_sync(provider.execute(code, None, timeout_s))
        return self._to_legacy_result(result)

    @staticmethod
    def _run_coro_sync(coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        box: dict[str, object] = {}
        error: dict[str, BaseException] = {}

        def _runner():
            try:
                box["result"] = asyncio.run(coro)
            except BaseException as exc:  # pragma: no cover
                error["exc"] = exc

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()
        if error:
            raise error["exc"]
        return box.get("result")

    async def _provider_health(self, provider: ExecutionProvider) -> Optional[dict]:
        if not hasattr(provider, "health"):
            return None
        try:
            return await provider.health()
        except Exception:
            return {"healthy": False, "status": "health_error"}

    def _provider_health_sync(self, provider: ExecutionProvider) -> Optional[dict]:
        if not hasattr(provider, "health"):
            return None
        try:
            return self._run_coro_sync(provider.health())
        except Exception:
            return {"healthy": False, "status": "health_error"}

    def health_snapshot(self, mode: str = "docker") -> dict:
        requested_mode = (mode or "docker").strip().lower()
        docker_health = self._provider_health_sync(self.docker_provider) or {
            "provider": "docker",
            "healthy": True,
            "status": "unknown",
        }
        ppio_health = None
        if self.ppio_provider is not None:
            ppio_health = self._provider_health_sync(self.ppio_provider) or {
                "provider": "ppio",
                "healthy": True,
                "status": "unknown",
            }

        if requested_mode == "ppio":
            selected_provider = "ppio"
            selected_healthy = bool(ppio_health and ppio_health.get("healthy", False))
        elif requested_mode == "auto":
            if docker_health.get("healthy", False):
                selected_provider = "docker"
                selected_healthy = True
            elif ppio_health is not None and ppio_health.get("healthy", False):
                selected_provider = "ppio"
                selected_healthy = True
            else:
                selected_provider = "docker"
                selected_healthy = False
        else:
            selected_provider = "docker"
            selected_healthy = bool(docker_health.get("healthy", False))

        return {
            "healthy": selected_healthy,
            "mode": requested_mode,
            "selected_provider": selected_provider,
            "providers": {
                "docker": docker_health,
                "ppio": ppio_health,
            },
        }

    @staticmethod
    def _to_legacy_result(result: ExecutionResult) -> dict:
        visualizations = [
            name
            for name in (result.output_files or {}).keys()
            if name.endswith((".png", ".jpg", ".jpeg", ".svg", ".pdf", ".html"))
        ]
        return {
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": result.error,
            "exit_code": 0 if result.success else 1,
            "execution_time": result.execution_time_s,
            "visualizations": visualizations,
            "output_files": result.output_files or {},
        }

    @staticmethod
    def _error_result(error: str, base: Optional[dict] = None) -> dict:
        payload = {
            "success": False,
            "error": error,
            "stdout": "",
            "stderr": error,
            "exit_code": -1,
            "execution_time": 0.0,
            "visualizations": [],
            "output_files": {},
        }
        if base:
            payload.update(base)
            payload["success"] = False
            payload["error"] = error
        return payload
