"""Safety guard node for workflow pipeline."""

from __future__ import annotations

from typing import Any

from backend.services.workflows.state import WorkflowState


_BLOCK_PATTERNS = (
    "rm -rf",
    "drop table",
    "shutdown -h",
    "os.system(",
    "subprocess.Popen",
)


async def safety_node(state: WorkflowState, services: Any) -> WorkflowState:
    del services

    metadata = state.setdefault("metadata", {})
    query = (state.get("query") or "").lower()

    matched = [pattern for pattern in _BLOCK_PATTERNS if pattern in query]
    if matched:
        state["error"] = "Request blocked by safety policy"
        metadata["safety_status"] = "blocked"
        metadata["safety_matches"] = matched
        return state

    metadata["safety_status"] = "ok"
    return state
