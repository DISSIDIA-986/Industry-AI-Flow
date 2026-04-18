"""E2B cloud sandbox execution provider."""

from __future__ import annotations

import asyncio
import logging
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.services.code_executor.providers.base import ExecutionResult
from backend.services.code_executor.providers.ppio_provider import (
    _resolve_allowed_data_file,
)

logger = logging.getLogger(__name__)


class E2BExecutionProvider:
    """Cloud code execution via E2B Code Interpreter SDK.

    Uses ``e2b-code-interpreter`` package which provides a managed
    sandbox environment with pre-installed data-science packages
    (pandas, numpy, matplotlib, etc.).
    """

    def __init__(
        self,
        enabled: bool = False,
        *,
        api_key: Optional[str] = None,
        timeout_seconds: int = 60,
        failure_threshold: int = 5,
        cooldown_seconds: int = 30,
    ):
        self.enabled = enabled
        self.api_key = (api_key or "").strip()
        self.timeout_seconds = max(int(timeout_seconds), 5)
        self.failure_threshold = max(int(failure_threshold), 1)
        self.cooldown_seconds = max(int(cooldown_seconds), 1)

        self._failure_count = 0
        self._circuit_open_until = 0.0
        self._last_error: Optional[str] = None

    # ------------------------------------------------------------------
    # ExecutionProvider protocol
    # ------------------------------------------------------------------

    async def execute(
        self,
        code: str,
        files: Optional[Dict[str, bytes]] = None,
        timeout_s: int = 60,
    ) -> ExecutionResult:
        if not self.enabled:
            return self._provider_error("E2B provider is disabled", "provider_disabled")

        if not self.api_key:
            return self._provider_error(
                "E2B_API_KEY is not configured", "provider_misconfigured"
            )

        if self._is_circuit_open():
            remaining = max(0, int(self._circuit_open_until - time.monotonic()))
            return self._provider_error(
                f"E2B circuit_open retry_in={remaining}s", "circuit_open"
            )

        try:
            from e2b_code_interpreter import Sandbox
        except ImportError:
            return self._provider_error(
                "e2b-code-interpreter package not installed", "import_error"
            )

        start = time.monotonic()
        sbx = None
        try:
            sbx = Sandbox.create(api_key=self.api_key)

            # Upload data files into sandbox via filesystem API.
            # Write to /workspace/ to match the path convention used in
            # generated analysis code (data_analysis_agent prompts use
            # /workspace/{filename}).
            if files:
                for name, content in files.items():
                    sbx.files.write(f"/home/user/{name}", content)
                    sbx.files.write(f"/workspace/{name}", content)

            # Run the code
            execution = sbx.run_code(
                code,
                timeout=float(min(timeout_s, self.timeout_seconds)),
            )

            elapsed = time.monotonic() - start

            # E2B returns output in logs.stdout/stderr (lists of strings)
            stdout_parts = []
            stderr_parts = []
            if hasattr(execution, "logs") and execution.logs:
                if hasattr(execution.logs, "stdout") and execution.logs.stdout:
                    stdout_parts = execution.logs.stdout
                if hasattr(execution.logs, "stderr") and execution.logs.stderr:
                    stderr_parts = execution.logs.stderr

            stdout = "".join(stdout_parts) if stdout_parts else (execution.text or "")
            stderr = "".join(stderr_parts)
            error_msg = None
            output_files: Dict[str, bytes] = {}

            # Download generated files (charts, visualizations) from sandbox
            _VIZ_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".html", ".pdf"}
            try:
                for search_dir in ["/workspace"]:
                    try:
                        entries = sbx.files.list(search_dir)
                    except Exception:
                        continue
                    for entry in entries:
                        if not hasattr(entry, "name"):
                            continue
                        suffix = "." + entry.name.rsplit(".", 1)[-1].lower() if "." in entry.name else ""
                        if suffix in _VIZ_EXTENSIONS:
                            try:
                                content = sbx.files.read(f"{search_dir}/{entry.name}", format="bytes")
                                if content:
                                    output_files[entry.name] = content
                            except Exception:
                                pass
            except Exception:
                pass

            if execution.error:
                error_obj = execution.error
                # ExecutionError has name, value, traceback attributes
                if hasattr(error_obj, "traceback"):
                    error_msg = str(error_obj.traceback)
                else:
                    error_msg = str(error_obj)
                if not stderr:
                    stderr = error_msg

            self._record_success()
            return ExecutionResult(
                success=error_msg is None,
                stdout=stdout,
                stderr=stderr,
                error=error_msg,
                execution_time_s=elapsed,
                output_files=output_files,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            self._record_failure(str(exc))
            return self._provider_error(
                f"E2B execution failed: {exc}", "execution_failed"
            )
        finally:
            if sbx is not None:
                try:
                    sbx.kill()
                except Exception:
                    pass

    async def health(self) -> dict:
        if not self.enabled:
            return {"provider": "e2b", "healthy": False, "status": "disabled"}
        if not self.api_key:
            return {"provider": "e2b", "healthy": False, "status": "misconfigured"}
        if self._is_circuit_open():
            return {
                "provider": "e2b",
                "healthy": False,
                "status": "circuit_open",
                "failure_count": self._failure_count,
                "last_error": self._last_error,
            }
        # Quick connectivity check: create and immediately kill a sandbox.
        #
        # IMPORTANT: Sandbox.create() is a sync network call that can block
        # for 5-15s cold (or hang entirely on bad network). If we call it
        # inline inside this async function, we block the event loop —
        # lifespan warmup AND auto/cloud fallback paths would both freeze
        # the server while waiting. Off-load to a worker thread so asyncio
        # callers can use asyncio.wait_for to bound the wait and the loop
        # stays responsive.
        try:
            return await asyncio.to_thread(self._health_sync)
        except Exception as exc:  # pragma: no cover — defensive; _health_sync
            # already swallows its own exceptions and returns a dict.
            return {
                "provider": "e2b",
                "healthy": False,
                "status": "unreachable",
                "error": str(exc),
            }

    def _health_sync(self) -> dict:
        """Sync body of health(). Blocking — call via to_thread from async."""
        try:
            from e2b_code_interpreter import Sandbox

            sbx = Sandbox.create(api_key=self.api_key)
            sbx.kill()
            return {"provider": "e2b", "healthy": True, "status": "ok"}
        except Exception as exc:
            return {
                "provider": "e2b",
                "healthy": False,
                "status": "unreachable",
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Sync compatibility (same interface as PPIOExecutionProvider)
    # ------------------------------------------------------------------

    def execute_code(
        self,
        code: str,
        data_files: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ) -> dict:
        try:
            files = self._load_files(data_files)
        except Exception as exc:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(exc),
                "error": f"unable to load data files: {exc}",
                "exit_code": -1,
                "execution_time": 0.0,
                "visualizations": [],
                "output_files": {},
            }
        timeout_s = int(timeout) if timeout else self.timeout_seconds
        result = self._run_coro_sync(
            self.execute(code=code, files=files, timeout_s=timeout_s)
        )
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _provider_error(message: str, code: str) -> ExecutionResult:
        return ExecutionResult(success=False, error=message, stderr=code)

    def _is_circuit_open(self) -> bool:
        return time.monotonic() < self._circuit_open_until

    def _record_success(self) -> None:
        self._failure_count = 0
        self._circuit_open_until = 0.0
        self._last_error = None

    def _record_failure(self, error: str) -> None:
        self._failure_count += 1
        self._last_error = error
        if self._failure_count >= self.failure_threshold:
            self._circuit_open_until = time.monotonic() + self.cooldown_seconds

    @staticmethod
    def _load_files(data_files: Optional[List[str]]) -> Dict[str, bytes]:
        payload: Dict[str, bytes] = {}
        if not data_files:
            return payload
        for path in data_files:
            if not path:
                continue
            safe_path = _resolve_allowed_data_file(path)
            name = safe_path.name
            with safe_path.open("rb") as handle:
                payload[name] = handle.read()
        return payload

    @staticmethod
    def _run_coro_sync(coro):
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        box: dict[str, object] = {}
        error: dict[str, BaseException] = {}

        def _runner():
            try:
                box["result"] = asyncio.run(coro)
            except BaseException as exc:
                error["exc"] = exc

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()
        if error:
            raise error["exc"]
        return box.get("result")
