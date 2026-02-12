"""Compatibility helpers for psycopg v3 / psycopg2 and pgvector adapters."""

from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_driver = None
driver_name = "unknown"

for module_name, label in (("psycopg", "psycopg"), ("psycopg2", "psycopg2")):
    try:
        _driver = importlib.import_module(module_name)
        driver_name = label
        break
    except Exception:
        continue

if _driver is None:  # pragma: no cover - defensive import guard
    raise ImportError("Neither psycopg nor psycopg2 is available")


def connect(database_url: str):
    """Create a sync DB connection using whichever psycopg driver is installed."""
    return _driver.connect(database_url)


def register_pgvector(conn: Any) -> bool:
    """Register pgvector adapter for the active DB connection when available."""
    for module_path in ("pgvector.psycopg", "pgvector.psycopg2"):
        try:
            module = importlib.import_module(module_path)
            register_vector = getattr(module, "register_vector", None)
            if callable(register_vector):
                register_vector(conn)
                return True
        except Exception:
            continue
    logger.debug("pgvector adapter registration skipped")
    return False


def fetchall_dicts(cursor: Any) -> List[Dict[str, Any]]:
    """Return cursor rows as dictionaries using cursor metadata."""
    rows = cursor.fetchall()
    description = getattr(cursor, "description", None) or []
    columns = [item[0] for item in description]
    if not columns:
        return []
    return [dict(zip(columns, row)) for row in rows]


def fetchone_dict(cursor: Any) -> Optional[Dict[str, Any]]:
    """Return one cursor row as a dictionary."""
    row = cursor.fetchone()
    if row is None:
        return None
    description = getattr(cursor, "description", None) or []
    columns = [item[0] for item in description]
    if not columns:
        return None
    return dict(zip(columns, row))
