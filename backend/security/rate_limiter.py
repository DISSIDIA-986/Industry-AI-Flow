"""Lightweight in-memory rate limiting utilities."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict


class RateLimitExceeded(Exception):
    """Raised when a caller exceeds the configured rate."""

    def __init__(self, retry_after: float):
        super().__init__("Too Many Requests")
        self.retry_after = retry_after


@dataclass
class RateLimitResult:
    """Holds basic telemetry data for rate-limited requests."""

    remaining: int
    reset_in: float


class SlidingWindowRateLimiter:
    """Simple thread-safe sliding window limiter."""

    def __init__(self, limit: int, interval_seconds: int = 60, burst: int = 0):
        self.limit = limit
        self.interval_seconds = interval_seconds
        self.burst = burst
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _evict_expired(self, key: str, now: float) -> None:
        window = self._hits[key]
        while window and now - window[0] > self.interval_seconds:
            window.popleft()

    def hit(self, key: str) -> RateLimitResult:
        """Record a hit for `key`, raising on limit."""
        now = time.monotonic()
        with self._lock:
            self._evict_expired(key, now)
            window = self._hits[key]
            allowed = self.limit + self.burst
            if len(window) >= allowed:
                retry_after = self.interval_seconds - (now - window[0])
                raise RateLimitExceeded(max(retry_after, 0))
            window.append(now)
            remaining = max(allowed - len(window), 0)
            reset_in = self.interval_seconds - (now - window[0]) if window else 0.0
            return RateLimitResult(remaining=remaining, reset_in=max(reset_in, 0.0))
