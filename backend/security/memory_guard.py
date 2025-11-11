"""Simple process-level memory monitoring utilities."""

from __future__ import annotations

import logging
import os

import psutil

from backend.config import settings

logger = logging.getLogger(__name__)


class MemoryGuardExceeded(RuntimeError):
    """Raised when the process memory usage exceeds the configured limit."""

    def __init__(self, usage_mb: float, limit_mb: float, label: str | None = None):
        self.usage_mb = usage_mb
        self.limit_mb = limit_mb
        self.label = label or "unknown"
        super().__init__(
            f"Memory usage {usage_mb:.2f}MB exceeded limit {limit_mb:.2f}MB for {self.label}"
        )


class MemoryGuard:
    def __init__(self, hard_limit_mb: int, soft_limit_mb: int | None = None):
        self.hard_limit_mb = hard_limit_mb
        self.soft_limit_mb = soft_limit_mb or int(hard_limit_mb * 0.8)
        self.process = psutil.Process(os.getpid())

    def current_usage_mb(self) -> float:
        return round(self.process.memory_info().rss / 1024 / 1024, 2)

    def ensure_within_limit(self, label: str) -> float:
        usage = self.current_usage_mb()
        if usage >= self.hard_limit_mb:
            logger.error(
                "Memory guard triggered", extra={"usage_mb": usage, "label": label}
            )
            raise MemoryGuardExceeded(usage, self.hard_limit_mb, label)
        if usage >= self.soft_limit_mb:
            logger.warning(
                "Memory usage near limit",
                extra={
                    "usage_mb": usage,
                    "label": label,
                    "soft_limit_mb": self.soft_limit_mb,
                },
            )
        return usage


memory_guard = MemoryGuard(
    hard_limit_mb=settings.memory_guard_limit_mb,
    soft_limit_mb=settings.memory_guard_soft_limit_mb,
)
