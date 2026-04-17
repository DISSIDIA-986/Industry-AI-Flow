"""Langfuse cloud observability — lazy singleton with no-op fallback.

The client is intentionally defensive: any failure (missing keys, auth error,
SDK import error, network issue) must NEVER break the main request path.
Observability is best-effort.

Usage:
    from backend.observability.langfuse_client import get_langfuse, is_enabled

    if is_enabled():
        with get_langfuse().start_as_current_observation(
            name="rag-query", input={"query": q}
        ) as span:
            ...
            span.update(output=result)

For a more ergonomic API, prefer the `@observe()` decorator from langfuse
directly — it is a no-op when the client is disabled.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_client: Optional[Any] = None
_enabled: Optional[bool] = None  # tri-state: None=uninit, True=ready, False=disabled


def _read_config() -> dict[str, Any]:
    return {
        "enabled": os.getenv("LANGFUSE_ENABLED", "false").lower() == "true",
        "public_key": os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        "secret_key": os.getenv("LANGFUSE_SECRET_KEY", ""),
        "host": os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com"),
        "environment": os.getenv("LANGFUSE_ENVIRONMENT", "dev"),
        "sample_rate": float(os.getenv("LANGFUSE_SAMPLE_RATE", "1.0")),
    }


def _init_client() -> None:
    """Lazy init. Called from get_langfuse()/is_enabled() on first access."""
    global _client, _enabled

    cfg = _read_config()
    if not cfg["enabled"]:
        _enabled = False
        return

    if not cfg["public_key"] or not cfg["secret_key"]:
        logger.warning("Langfuse enabled but keys missing — disabling.")
        _enabled = False
        return

    try:
        from langfuse import Langfuse  # type: ignore
    except ImportError:
        logger.warning("langfuse package not installed — observability disabled.")
        _enabled = False
        return

    try:
        client = Langfuse(
            public_key=cfg["public_key"],
            secret_key=cfg["secret_key"],
            host=cfg["host"],
            environment=cfg["environment"],
            sample_rate=cfg["sample_rate"],
        )
        # auth_check is cheap (one GET) and catches bad keys early.
        if not client.auth_check():
            logger.warning("Langfuse auth_check failed — disabling.")
            _enabled = False
            return

        _client = client
        _enabled = True
        logger.info(
            "Langfuse observability enabled: host=%s environment=%s sample_rate=%s",
            cfg["host"],
            cfg["environment"],
            cfg["sample_rate"],
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Langfuse init failed: %s — disabling.", exc)
        _enabled = False


def is_enabled() -> bool:
    """True iff langfuse is configured and auth_check passed."""
    if _enabled is None:
        with _lock:
            if _enabled is None:
                _init_client()
    return bool(_enabled)


def get_langfuse() -> Optional[Any]:
    """Return the Langfuse client, or None if disabled.

    Callers should guard with `is_enabled()` or handle None.
    """
    if not is_enabled():
        return None
    return _client


def flush() -> None:
    """Flush pending traces. Safe to call when disabled."""
    if _client is None:
        return
    try:
        _client.flush()
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("Langfuse flush failed: %s", exc)


def shutdown() -> None:
    """Flush + shutdown. Call from FastAPI lifespan on app exit."""
    global _client, _enabled
    if _client is None:
        return
    try:
        _client.flush()
        _client.shutdown()
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("Langfuse shutdown failed: %s", exc)
    finally:
        _client = None
        _enabled = False
