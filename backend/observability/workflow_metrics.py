"""Workflow pipeline metrics."""

from __future__ import annotations

import logging

try:
    from prometheus_client import Counter, Histogram
except Exception:  # pragma: no cover - optional dependency
    class _NoopMetric:
        def labels(self, **kwargs):
            del kwargs
            return self

        def inc(self, value=1):
            del value
            return None

        def observe(self, value):
            del value
            return None

    def Counter(*args, **kwargs):  # type: ignore[misc]
        del args, kwargs
        return _NoopMetric()

    def Histogram(*args, **kwargs):  # type: ignore[misc]
        del args, kwargs
        return _NoopMetric()

logger = logging.getLogger(__name__)

WORKFLOW_REQUESTS_TOTAL = Counter(
    "workflow_requests_total",
    "Count of workflow query requests",
    labelnames=("route_mode", "provider", "status"),
)

WORKFLOW_LATENCY_SECONDS = Histogram(
    "workflow_latency_seconds",
    "Workflow query end-to-end latency seconds",
    labelnames=("route_mode", "provider"),
)

WORKFLOW_NODE_LATENCY_SECONDS = Histogram(
    "workflow_node_latency_seconds",
    "Workflow node latency seconds",
    labelnames=("node",),
)


def _safe_record(record_fn) -> None:
    try:
        record_fn()
    except Exception as exc:  # pragma: no cover
        logger.debug("Unable to record workflow metric: %s", exc)


def record_workflow_request(
    *,
    route_mode: str,
    provider: str,
    status: str,
    latency_seconds: float,
) -> None:
    _safe_record(
        lambda: WORKFLOW_REQUESTS_TOTAL.labels(
            route_mode=route_mode,
            provider=provider,
            status=status,
        ).inc()
    )
    _safe_record(
        lambda: WORKFLOW_LATENCY_SECONDS.labels(
            route_mode=route_mode,
            provider=provider,
        ).observe(max(0.0, latency_seconds))
    )


def record_workflow_node_latency(node: str, latency_seconds: float) -> None:
    _safe_record(
        lambda: WORKFLOW_NODE_LATENCY_SECONDS.labels(node=node).observe(
            max(0.0, latency_seconds)
        )
    )
