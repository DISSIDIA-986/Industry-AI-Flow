"""Routing policy helpers for workflow pipeline."""

from __future__ import annotations


def resolve_route_mode(requested: str | None, default_mode: str = "local_only") -> str:
    value = (requested or "").strip().lower()
    if value in {"local_only", "hybrid_auto", "cloud_only"}:
        return value
    return default_mode


def select_provider(route_mode: str, cloud_allowed: bool) -> str:
    """
    Resolve target provider from route mode and budget/safety allowance.
    """
    mode = resolve_route_mode(route_mode)
    if mode == "cloud_only":
        return "cloud" if cloud_allowed else "local_fallback"
    if mode == "hybrid_auto":
        return "cloud" if cloud_allowed else "local"
    return "local"
