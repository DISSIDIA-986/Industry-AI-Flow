"""Prometheus metrics integration."""

from __future__ import annotations

from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    excluded_handlers={"/metrics"},
)


def setup_metrics(app):
    instrumentator.instrument(app).expose(app, include_in_schema=False)
