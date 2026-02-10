"""Prompt policy helpers for workflow pipeline."""

from __future__ import annotations


def experiments_enabled(flags: dict | None) -> bool:
    if not flags:
        return False
    return bool(flags.get("prompt_experiments_enabled", False))
