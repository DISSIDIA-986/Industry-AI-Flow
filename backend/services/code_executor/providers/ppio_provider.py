"""PPIO/cloud execution provider implementation with circuit breaker."""

from __future__ import annotations

import asyncio
import base64
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

from backend.config import settings
from backend.services.code_executor.providers.base import ExecutionResult


def _is_subpath(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _allowed_data_roots() -> list[Path]:
    roots = [
        Path.cwd().resolve(),
        Path(settings.temp_data_dir).resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ]
    env_tmp = os.getenv("TMPDIR")
    if env_tmp:
        roots.append(Path(env_tmp).resolve())
    seen: set[Path] = set()
    unique: list[Path] = []
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        unique.append(root)
    return unique


def _resolve_allowed_data_file(path_value: str) -> Path:
    candidate = Path(path_value).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    allowed = _allowed_data_roots()
    if not any(_is_subpath(candidate, root) or candidate == root for root in allowed):
        raise ValueError("data file path is outside allowed paths")
    if not candidate.exists() or not candidate.is_file():
        raise ValueError(f"data file not found: {candidate}")
    return candidate


class PPIOExecutionProvider:
    def __init__(
        self,
        enabled: bool = False,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        execute_path: str = "/v1/code/execute",
        health_path: str = "/health",
        model: Optional[str] = None,
        timeout_seconds: int = 60,
        failure_threshold: int = 3,
        cooldown_seconds: int = 30,
        verify_tls: bool = True,
    ):
        self.enabled = enabled
        self.base_url = (base_url or "").strip().rstrip("/")
        self.api_key = (api_key or "").strip()
        self.execute_path = execute_path
        self.health_path = health_path
        self.model = model
        self.timeout_seconds = max(int(timeout_seconds), 5)
        self.failure_threshold = max(int(failure_threshold), 1)
        self.cooldown_seconds = max(int(cooldown_seconds), 1)
        self.verify_tls = bool(verify_tls)

        self._failure_count = 0
        self._circuit_open_until = 0.0
        self._last_error: Optional[str] = None

    async def execute(
        self,
        code: str,
        files: Optional[Dict[str, bytes]] = None,
        timeout_s: int = 60,
    ) -> ExecutionResult:
        if not self.enabled:
            return self._provider_error(
                "PPIO provider is disabled", "provider_disabled"
            )

        if not self.base_url:
            return self._provider_error(
                "PPIO provider base URL is not configured",
                "provider_misconfigured",
            )

        if self._is_circuit_open():
            remaining = max(0, int(self._circuit_open_until - time.monotonic()))
            return self._provider_error(
                f"PPIO circuit_open retry_in={remaining}s",
                "circuit_open",
            )

        payload = self._build_execute_payload(
            code=code, files=files, timeout_s=timeout_s
        )
        timeout_value = max(int(timeout_s), self.timeout_seconds)
        url = self._resolve_url(self.execute_path)

        try:
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                headers=self._headers(),
                timeout=timeout_value,
                verify=self.verify_tls,
            )
            response.raise_for_status()
            data = self._safe_json(response)
            result = self._parse_execution_result(data)
            if result.success:
                self._record_success()
            else:
                self._record_failure(result.error or result.stderr or "remote_failure")
            return result
        except requests.RequestException as exc:
            self._record_failure(str(exc))
            return self._provider_error(f"PPIO request failed: {exc}", "request_failed")
        except Exception as exc:  # pragma: no cover - defensive guard
            self._record_failure(str(exc))
            return self._provider_error(
                f"PPIO execution failed: {exc}", "execution_failed"
            )

    async def health(self) -> dict:
        if not self.enabled:
            return {"provider": "ppio", "healthy": False, "status": "disabled"}
        if not self.base_url:
            return {"provider": "ppio", "healthy": False, "status": "misconfigured"}
        if self._is_circuit_open():
            return {
                "provider": "ppio",
                "healthy": False,
                "status": "circuit_open",
                "failure_count": self._failure_count,
                "last_error": self._last_error,
            }

        url = self._resolve_url(self.health_path)
        try:
            response = await asyncio.to_thread(
                requests.get,
                url,
                headers=self._headers(include_content_type=False),
                timeout=min(self.timeout_seconds, 15),
                verify=self.verify_tls,
            )
            healthy = 200 <= response.status_code < 300
            return {
                "provider": "ppio",
                "healthy": healthy,
                "status": "ok" if healthy else "unhealthy",
                "status_code": response.status_code,
                "failure_count": self._failure_count,
                "last_error": self._last_error,
            }
        except requests.RequestException as exc:
            return {
                "provider": "ppio",
                "healthy": False,
                "status": "unreachable",
                "error": str(exc),
                "failure_count": self._failure_count,
                "last_error": self._last_error,
            }

    def execute_code(
        self,
        code: str,
        data_files: Optional[list[str]] = None,
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

    def _headers(self, include_content_type: bool = True) -> dict:
        headers: dict[str, str] = {}
        if include_content_type:
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _resolve_url(self, path: str) -> str:
        cleaned = (path or "").strip()
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            return cleaned
        if not cleaned.startswith("/"):
            cleaned = f"/{cleaned}"
        return urljoin(f"{self.base_url}/", cleaned.lstrip("/"))

    def _build_execute_payload(
        self,
        *,
        code: str,
        files: Optional[Dict[str, bytes]],
        timeout_s: int,
    ) -> dict:
        payload = {
            "code": code,
            "language": "python",
            "timeout_s": int(timeout_s),
        }
        if self.model:
            payload["model"] = self.model
        if files:
            payload["files"] = {
                name: base64.b64encode(content).decode("utf-8")
                for name, content in files.items()
            }
        return payload

    def _parse_execution_result(self, payload: dict[str, Any]) -> ExecutionResult:
        success = bool(payload.get("success", False))
        stdout = str(payload.get("stdout") or "")
        stderr = str(payload.get("stderr") or "")
        error = payload.get("error")
        if error is not None:
            error = str(error)

        execution_time_s = 0.0
        for key in ("execution_time_s", "execution_time"):
            if key in payload and payload[key] is not None:
                execution_time_s = float(payload[key])
                break
        if execution_time_s == 0.0 and payload.get("latency_ms") is not None:
            execution_time_s = float(payload["latency_ms"]) / 1000.0

        output_files: dict[str, bytes] = {}
        raw_files = payload.get("output_files")
        if isinstance(raw_files, dict):
            for name, content in raw_files.items():
                if isinstance(content, bytes):
                    output_files[name] = content
                    continue
                if isinstance(content, str):
                    try:
                        output_files[name] = base64.b64decode(content, validate=True)
                    except Exception:
                        output_files[name] = content.encode("utf-8")

        return ExecutionResult(
            success=success,
            stdout=stdout,
            stderr=stderr,
            error=error,
            execution_time_s=execution_time_s,
            output_files=output_files,
        )

    @staticmethod
    def _safe_json(response: requests.Response) -> dict[str, Any]:
        try:
            data = response.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

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
    def _load_files(data_files: Optional[list[str]]) -> Dict[str, bytes]:
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
