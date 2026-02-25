"""Language policy helpers for request validation."""

from __future__ import annotations

import re

from fastapi import HTTPException

RAG_CHINESE_QUERY_UNSUPPORTED = "RAG_CHINESE_QUERY_UNSUPPORTED"

_HAN_REGEX = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")


def contains_han(text: str | None) -> bool:
    """Return True when text contains Han characters."""
    if not text:
        return False
    return _HAN_REGEX.search(text) is not None


def ensure_rag_english_query(query: str, *, field: str) -> None:
    """Block Chinese input for RAG query entrypoints."""
    if not contains_han(query):
        return

    raise HTTPException(
        status_code=400,
        detail={
            "code": RAG_CHINESE_QUERY_UNSUPPORTED,
            "message": (
                "Chinese input is not supported for RAG queries. "
                "Please submit your query in English."
            ),
            "field": field,
        },
    )
