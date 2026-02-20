"""Safety guard node for workflow pipeline."""

from __future__ import annotations

import re
from typing import Any

from backend.services.workflows.state import WorkflowState


_BLOCK_RULES = (
    ("rm -rf", re.compile(r"\brm\s+-rf\b", re.IGNORECASE)),
    ("drop table", re.compile(r"\bdrop\s+table\b", re.IGNORECASE)),
    ("shutdown -h", re.compile(r"\bshutdown\s+-h\b", re.IGNORECASE)),
    ("os.system(", re.compile(r"\bos\s*\.\s*system\s*\(", re.IGNORECASE)),
    (
        "subprocess.popen",
        re.compile(r"\bsubprocess\s*\.\s*popen\s*\(", re.IGNORECASE),
    ),
    (
        "subprocess.run",
        re.compile(r"\bsubprocess\s*\.\s*run\s*\(", re.IGNORECASE),
    ),
    (
        "subprocess.call",
        re.compile(r"\bsubprocess\s*\.\s*call\s*\(", re.IGNORECASE),
    ),
)


def _normalize_query(query: str) -> str:
    compact = re.sub(r"\s+", " ", query.strip())
    return compact.lower()


def _find_block_matches(query: str) -> list[str]:
    normalized = _normalize_query(query)
    matches: list[str] = []
    for label, pattern in _BLOCK_RULES:
        if pattern.search(normalized):
            matches.append(label)
    return matches


async def safety_node(state: WorkflowState, services: Any) -> WorkflowState:
    del services

    metadata = state.setdefault("metadata", {})
    query = state.get("query") or ""
    matched = _find_block_matches(query)
    if matched:
        state["error"] = "Request blocked by safety policy"
        metadata["safety_status"] = "blocked"
        metadata["safety_matches"] = matched
        return state

    metadata["safety_status"] = "ok"
    return state
