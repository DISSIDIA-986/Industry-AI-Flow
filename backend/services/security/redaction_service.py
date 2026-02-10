"""Sensitive-data redaction before cloud egress."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RedactionResult:
    text: str
    hit_count: int
    categories: List[str]
    replacements: Dict[str, int]


class RedactionService:
    # Keep patterns conservative to avoid over-redaction.
    PATTERNS = {
        "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "phone_cn": re.compile(r"\b(?:\+?86[- ]?)?1[3-9]\d{9}\b"),
        "phone_us": re.compile(
            r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        "id_like": re.compile(r"\b\d{15,18}[0-9Xx]?\b"),
        "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    }

    def redact(self, text: str) -> RedactionResult:
        if not text:
            return RedactionResult(text="", hit_count=0, categories=[], replacements={})

        out = text
        hit_count = 0
        categories: List[str] = []
        replacements: Dict[str, int] = {}

        for category, pattern in self.PATTERNS.items():
            token = f"<REDACTED_{category.upper()}>"
            updated, count = pattern.subn(token, out)
            if count > 0:
                out = updated
                hit_count += count
                categories.append(category)
                replacements[category] = count

        return RedactionResult(
            text=out,
            hit_count=hit_count,
            categories=categories,
            replacements=replacements,
        )
