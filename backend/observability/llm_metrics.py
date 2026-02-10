"""LLM dispatch/cost Prometheus metrics."""

from __future__ import annotations

import logging

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Count of LLM dispatch requests",
    labelnames=("provider", "route_mode", "status"),
)

LLM_FALLBACK_TOTAL = Counter(
    "llm_fallback_total",
    "Count of local-to-cloud fallback events",
    labelnames=("reason",),
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total prompt/completion tokens",
    labelnames=("provider", "token_type"),
)

LLM_COST_USD_TOTAL = Counter(
    "llm_cost_usd_total",
    "Estimated LLM cost in USD",
    labelnames=("provider",),
)

LLM_LATENCY_SECONDS = Histogram(
    "llm_latency_seconds",
    "LLM request latency seconds",
    labelnames=("provider", "route_mode"),
)


def _safe_record(record_fn) -> None:
    try:
        record_fn()
    except Exception as exc:  # pragma: no cover - never break main flow
        logger.debug("Unable to record LLM metric: %s", exc)


def record_llm_request(
    *, provider: str, route_mode: str, status: str, latency_seconds: float
) -> None:
    _safe_record(
        lambda: LLM_REQUESTS_TOTAL.labels(
            provider=provider, route_mode=route_mode, status=status
        ).inc()
    )
    _safe_record(
        lambda: LLM_LATENCY_SECONDS.labels(
            provider=provider, route_mode=route_mode
        ).observe(max(0.0, latency_seconds))
    )


def record_llm_fallback(reason: str) -> None:
    _safe_record(lambda: LLM_FALLBACK_TOTAL.labels(reason=reason).inc())


def record_llm_tokens(
    *, provider: str, prompt_tokens: int, completion_tokens: int
) -> None:
    _safe_record(
        lambda: LLM_TOKENS_TOTAL.labels(provider=provider, token_type="prompt").inc(
            max(0, prompt_tokens)
        )
    )
    _safe_record(
        lambda: LLM_TOKENS_TOTAL.labels(provider=provider, token_type="completion").inc(
            max(0, completion_tokens)
        )
    )


def record_llm_cost(*, provider: str, estimated_cost_usd: float) -> None:
    _safe_record(
        lambda: LLM_COST_USD_TOTAL.labels(provider=provider).inc(
            max(0.0, float(estimated_cost_usd))
        )
    )
