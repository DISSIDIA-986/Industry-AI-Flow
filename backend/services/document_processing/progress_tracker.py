"""
Document processing pipeline progress tracker.

Provides real-time progress updates via janus.Queue (sync→async bridge)
for SSE streaming to frontend clients.
"""

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import janus
except ImportError:
    janus = None
    logger.warning("janus not installed — SSE progress tracking disabled")


@dataclass
class StageEvent:
    """A single pipeline stage progress event."""
    stage: str          # "extract", "ocr", "chunk", "embed", "store"
    status: str         # "pending", "running", "completed", "failed", "skipped"
    progress: float     # 0.0 - 1.0
    detail: str         # "Extracting text: 47/150 pages"
    elapsed_ms: int     # Time spent in this stage so far

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "status": self.status,
            "progress": self.progress,
            "detail": self.detail,
            "elapsed_ms": self.elapsed_ms,
        }


class PipelineProgressTracker:
    """
    Tracks progress of the document processing pipeline.

    Used from sync code (ThreadPoolExecutor) via sync_q.put().
    Read from async code (SSE endpoint) via async_q.get().
    """

    # Class-level registry of active trackers (doc_id → tracker)
    _registry: dict[str, "PipelineProgressTracker"] = {}
    _registry_lock = threading.Lock()
    # TTL for cleanup (seconds)
    TTL_SECONDS = 300  # 5 minutes

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self.created_at = time.monotonic()
        self._stage_starts: dict[str, float] = {}
        self._queue: Optional[janus.Queue] = None
        self._completed = False

        if janus is not None:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're called from a sync context within an async loop
                    # Create queue in a thread-safe way
                    self._queue = janus.Queue()
                else:
                    self._queue = janus.Queue()
            except RuntimeError:
                self._queue = janus.Queue()

        # Register this tracker
        with self._registry_lock:
            self._registry[doc_id] = self
            # Cleanup stale trackers
            self._cleanup_stale()

    @classmethod
    def get(cls, doc_id: str) -> Optional["PipelineProgressTracker"]:
        """Get tracker by doc_id, or None if not found."""
        with cls._registry_lock:
            return cls._registry.get(doc_id)

    @classmethod
    def _cleanup_stale(cls):
        """Remove trackers older than TTL_SECONDS."""
        now = time.monotonic()
        stale = [
            k for k, v in cls._registry.items()
            if now - v.created_at > cls.TTL_SECONDS
        ]
        for k in stale:
            tracker = cls._registry.pop(k, None)
            if tracker and tracker._queue:
                tracker._queue.close()

    def _elapsed_ms(self, stage: str) -> int:
        """Get elapsed time for a stage in milliseconds."""
        start = self._stage_starts.get(stage)
        if start is None:
            return 0
        return int((time.monotonic() - start) * 1000)

    def update(self, stage: str, status: str, progress: float, detail: str):
        """Push a progress event (called from sync code)."""
        if status == "running" and stage not in self._stage_starts:
            self._stage_starts[stage] = time.monotonic()

        event = StageEvent(
            stage=stage,
            status=status,
            progress=progress,
            detail=detail,
            elapsed_ms=self._elapsed_ms(stage),
        )

        if self._queue is not None:
            try:
                self._queue.sync_q.put(event)
            except Exception:
                pass  # Queue closed or full — non-critical

    def complete(self):
        """Signal pipeline completion."""
        self._completed = True
        if self._queue is not None:
            try:
                self._queue.sync_q.put(None)  # Sentinel
            except Exception:
                pass

    def fail(self, stage: str, error: str):
        """Signal pipeline failure at a specific stage."""
        self.update(stage, "failed", 0.0, error)
        self._completed = True
        if self._queue is not None:
            try:
                self._queue.sync_q.put(None)  # Sentinel
            except Exception:
                pass

    @property
    def async_queue(self):
        """Get the async side of the queue for SSE streaming."""
        if self._queue is not None:
            return self._queue.async_q
        return None

    def close(self):
        """Clean up resources."""
        with self._registry_lock:
            self._registry.pop(self.doc_id, None)
        if self._queue is not None:
            try:
                self._queue.close()
            except Exception:
                pass
