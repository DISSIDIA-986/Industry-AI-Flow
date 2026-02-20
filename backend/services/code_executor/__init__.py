"""Code executor package exports with graceful optional Docker support."""

from __future__ import annotations

import logging
from typing import Any, Optional

from backend.services.code_executor.manager import CodeExecutionManager
from backend.services.code_executor.providers.docker_provider import DockerExecutionProvider
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

# 创建全局执行器实例（延迟初始化）
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
    """获取全局代码执行器实例（单例模式）"""
    global _global_executor
    if _global_executor is None:
        if not _docker_requested():
            return None
        if DockerExecutor is None:
            return None
        try:
            _global_executor = DockerExecutor()
        except Exception as e:
            logger.error(f"无法初始化代码执行器: {e}")
            _global_executor = None
    return _global_executor


# 为向后兼容性提供code_executor别名
code_executor = get_code_executor()


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

    if docker_provider is None and not ppio_enabled:
        return None

    if docker_provider is None and ppio_enabled:
        _execution_manager = CodeExecutionManager(
            docker_provider=ppio_provider,
            ppio_provider=ppio_provider,
        )
        return _execution_manager

    _execution_manager = CodeExecutionManager(
        docker_provider=docker_provider,
        ppio_provider=ppio_provider if ppio_enabled else None,
    )
    return _execution_manager


# 自定义异常
class CodeExecutionError(Exception):
    """代码执行异常"""

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
    "CodeExecutionError",
]
