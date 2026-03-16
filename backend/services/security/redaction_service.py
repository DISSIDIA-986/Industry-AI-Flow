"""Sensitive-data redaction before cloud egress."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class RedactionResult:
    text: str
    hit_count: int
    categories: List[str]
    replacements: Dict[str, int]


class RedactionService:
    # Keep patterns conservative to avoid over-redaction.
    PATTERNS = {
        # Unicode-aware email matcher with delimiter guards.
        "email": re.compile(
            r"[^\s@<>()\[\]{}\"',.;:,:]+@[^\s@<>()\[\]{}\"',.;:,:]+\.[^\s@<>()\[\]{}\"',.;:,:]+"
        ),
        "phone_cn": re.compile(r"\b(?:\+?86[- ]?)?1[3-9]\d{9}\b"),
        # US number requires explicit separators/parentheses to avoid over-matching plain 10-digit ids.
        "phone_us": re.compile(
            r"(?<!\w)(?:\+1[-.\s]?)?(?:\(\d{3}\)[-.\s]?|\d{3}[-.\s])\d{3}[-.\s]\d{4}(?!\w)"
        ),
        "id_like": re.compile(r"\b\d{15,18}[0-9Xx]?\b"),
        "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    }

    def redact(self, text: str) -> RedactionResult:
        """
        EN,EN

        Args:
            text: EN

        Returns:
            RedactionResult: EN,EN
        """
        if not text:
            return RedactionResult(text="", hit_count=0, categories=[], replacements={})

        try:
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
        except Exception as e:
            # Fail-closed: return empty text to prevent PII leakage to cloud
            logger.warning(
                "Redaction failed: %s, blocking text to prevent PII leakage", e
            )
            return RedactionResult(
                text="",
                hit_count=0,
                categories=["redaction_error"],
                replacements={},
            )
