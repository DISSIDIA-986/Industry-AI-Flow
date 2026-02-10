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
        "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "phone_cn": re.compile(r"\b(?:\+?86[- ]?)?1[3-9]\d{9}\b"),
        "phone_us": re.compile(
            r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        "id_like": re.compile(r"\b\d{15,18}[0-9Xx]?\b"),
        "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    }

    def redact(self, text: str) -> RedactionResult:
        """
        脱敏处理，包含异常处理和降级策略
        
        Args:
            text: 需要脱敏的文本
            
        Returns:
            RedactionResult: 脱敏结果，异常时返回原始文本
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
            # 降级策略：脱敏失败时返回原始文本并记录警告
            logger.warning(f"Redaction failed: {e}, returning original text")
            return RedactionResult(
                text=text,
                hit_count=0,
                categories=[],
                replacements={}
            )
