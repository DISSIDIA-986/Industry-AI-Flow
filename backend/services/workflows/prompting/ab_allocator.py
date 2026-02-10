"""Deterministic A/B allocator for prompt experiments."""

from __future__ import annotations

import hashlib


class ABAllocator:
    """Allocate experiment bucket deterministically by key."""

    def allocate(self, key: str, split: float = 0.5) -> str:
        if split <= 0 or split >= 1:
            return "A"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        value = int(digest[:8], 16) / 0xFFFFFFFF
        return "A" if value < split else "B"
