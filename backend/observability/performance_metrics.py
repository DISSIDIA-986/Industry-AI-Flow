"""Custom application performance metrics."""

from __future__ import annotations

import logging

from prometheus_client import Histogram

logger = logging.getLogger(__name__)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Duration of database operations",
    labelnames=("query_type",),
)


def record_db_query_duration(query_type: str, duration_seconds: float) -> None:
    """Observe DB query duration and swallow Prometheus errors if any."""
    try:
        DB_QUERY_DURATION.labels(query_type=query_type).observe(duration_seconds)
    except Exception as exc:  # pragma: no cover - metrics shouldn't break app
        logger.debug("Unable to record DB metric: %s", exc)
