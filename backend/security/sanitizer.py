"""Lightweight input sanitization utilities."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import unquote

import bleach
from fastapi import HTTPException, status

SCRIPT_PATTERN = re.compile(r"<\s*script.*?>", re.IGNORECASE | re.DOTALL)
SQL_PATTERN = re.compile(
    r"("
    r"drop\s+table"
    r"|union\s+(all\s+)?select"
    r"|insert\s+into"
    r"|update\s+\S+\s+set"
    r"|delete\s+from"
    r"|alter\s+table"
    r"|create\s+table"
    r"|truncate\s+table"
    r"|\bexec(ute)?\b\s*\("
    r"|\bxp_"
    r"|--"
    r"|;"
    r")",
    re.IGNORECASE,
)
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_text(
    value: Optional[str], *, field_name: str, max_length: int = 2048
) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot be empty.",
        )
    if len(stripped) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} exceeds max length of {max_length} characters.",
        )
    # URL-decode iteratively so double/triple encoding is fully resolved.
    decoded = stripped
    for _ in range(5):
        next_decoded = unquote(decoded)
        if next_decoded == decoded:
            break
        decoded = next_decoded
    if SCRIPT_PATTERN.search(decoded) or CONTROL_CHAR_PATTERN.search(decoded):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} contains disallowed characters.",
        )
    if SQL_PATTERN.search(decoded):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} appears to contain a prohibited pattern.",
        )
    cleaned = bleach.clean(stripped, tags=[], attributes={}, strip=True)
    return cleaned


def sanitize_identifier(
    value: Optional[str], field_name: str, max_length: int = 255
) -> Optional[str]:
    if value is None:
        return None
    sanitized = value.strip()
    if not sanitized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot be blank.",
        )
    if len(sanitized) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} exceeds max length of {max_length}.",
        )
    if "/" in sanitized or "\\" in sanitized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} contains invalid path characters.",
        )
    if "\x00" in sanitized or "%00" in sanitized.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} contains invalid null byte.",
        )
    return sanitized
