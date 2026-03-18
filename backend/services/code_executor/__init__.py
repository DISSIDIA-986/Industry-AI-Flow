"""Code executor package exports with graceful optional Docker support."""

from __future__ import annotations

import logging
from typing import Any, Optional

from backend.services.code_executor.manager import CodeExecutionManager
from backend.services.code_executor.providers.docker_provider import (
    DockerExecutionProvider,
)
from backend.services.code_executor.providers.e2b_provider import E2BExecutionProvider
from backend.services.code_executor.providers.ppio_provider import PPIOExecutionProvider
from backend.services.code_executor.validator import (
    CodeValidator,
    ValidationResult,
    validate_code,
)

logger = logging.getLogger(__name__)

try:
    from backend.services.code_executor.docker_executor import (
        DockerExecutor,
        ExecutionResult,
        execute_python_code,
    )
except Exception as exc:  # pragma: no cover - fallback for dependency-constrained envs
    logger.warning("Docker executor import failed: %s", exc)
    DockerExecutor = None  # type: ignore[assignment]
    ExecutionResult = Any  # type: ignore[assignment]

    def execute_python_code(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Docker executor is unavailable in current environment")


# Lazy-initialized global executor (created on first use)
_global_executor: Optional[Any] = None
_execution_manager: Optional[CodeExecutionManager] = None


def _docker_requested() -> bool:
    """Return whether Docker execution should be initialized."""
    from backend.config import settings

    provider = (settings.code_execution_provider or "docker").strip().lower()
    if not settings.enable_docker_sandbox:
        return False
    return provider in {"docker", "auto"}


def get_code_executor() -> Optional[Any]:
    """Get or create the global Docker code executor (lazy singleton)."""
    global _global_executor
    if _global_executor is None:
        if not _docker_requested():
            return None
        if DockerExecutor is None:
            return None
        try:
            _global_executor = DockerExecutor()
        except Exception as e:
            logger.error(f"Failed to initialize Docker code executor: {e}")
            _global_executor = None
    return _global_executor


# Lazy proxy: code_executor is resolved on first access, not at import time.
# Callers that import `code_executor` directly get None initially;
# prefer calling get_code_executor() for the up-to-date reference.
code_executor: Optional[Any] = None


def _init_code_executor() -> Optional[Any]:
    """Initialize code_executor on first real use."""
    global code_executor
    if code_executor is None:
        code_executor = get_code_executor()
    return code_executor


def get_code_execution_manager() -> Optional[CodeExecutionManager]:
    """Build provider-aware execution manager with graceful fallback."""
    global _execution_manager
    if _execution_manager is not None:
        return _execution_manager

    from backend.config import settings

    provider = (settings.code_execution_provider or "docker").strip().lower()
    docker_enabled = _docker_requested()
    ppio_enabled = settings.enable_ppio_code_execution or provider == "ppio"

    docker_provider = None
    if docker_enabled:
        try:
            docker_provider = DockerExecutionProvider()
        except Exception as exc:
            logger.warning("Docker provider unavailable: %s", exc)

    ppio_provider = None
    if ppio_enabled:
        ppio_provider = PPIOExecutionProvider(
            enabled=ppio_enabled,
            base_url=settings.ppio_base_url,
            api_key=settings.ppio_api_key or None,
            execute_path=settings.ppio_execute_path,
            health_path=settings.ppio_health_path,
            model=settings.ppio_model or None,
            timeout_seconds=settings.ppio_timeout_seconds,
            failure_threshold=settings.ppio_failure_threshold,
            cooldown_seconds=settings.ppio_cooldown_seconds,
            verify_tls=settings.ppio_verify_tls,
        )

    e2b_enabled = settings.enable_e2b_code_execution or provider == "e2b"
    e2b_provider = None
    if e2b_enabled:
        e2b_provider = E2BExecutionProvider(
            enabled=e2b_enabled,
            api_key=settings.e2b_api_key or None,
            timeout_seconds=settings.e2b_timeout_seconds,
            failure_threshold=settings.e2b_failure_threshold,
            cooldown_seconds=settings.e2b_cooldown_seconds,
        )

    # Determine the cloud provider to use (prefer E2B over PPIO if both enabled)
    active_cloud_provider = e2b_provider or ppio_provider
    cloud_enabled = e2b_enabled or ppio_enabled

    if docker_provider is None and not cloud_enabled:
        return None

    if docker_provider is None and cloud_enabled:
        # No Docker — cloud provider serves as both primary and cloud slot.
        _execution_manager = CodeExecutionManager(
            docker_provider=active_cloud_provider,
            cloud_provider=active_cloud_provider,
        )
        return _execution_manager

    _execution_manager = CodeExecutionManager(
        docker_provider=docker_provider,
        cloud_provider=active_cloud_provider if cloud_enabled else None,
    )
    return _execution_manager


# Package-level error class for code execution failures
class CodeExecutionError(Exception):
    """Raised when code execution fails in any provider."""

    pass


__all__ = [
    "DockerExecutor",
    "ExecutionResult",
    "CodeValidator",
    "ValidationResult",
    "execute_python_code",
    "validate_code",
    "get_code_executor",
    "get_code_execution_manager",
    "code_executor",
    "_init_code_executor",
    "CodeExecutionError",
]
