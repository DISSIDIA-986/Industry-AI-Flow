"""Optional code execution node for workflow pipeline."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.services.workflows.state import WorkflowState


async def code_exec_node(state: WorkflowState, services: Any) -> WorkflowState:
    metadata = state.setdefault("metadata", {})

    requires_code_exec = bool(
        metadata.get("requires_code_execution", False)
        or state.get("intent") == "code_execution"
    )
    if not requires_code_exec:
        metadata["code_exec_status"] = "skipped"
        return state

    manager = getattr(services, "code_execution_manager", None)
    if manager is None:
        metadata["code_exec_status"] = "unavailable"
        return state

    code = metadata.get("code_to_execute") or "print('code execution requested')"
    mode = metadata.get("code_execution_mode", "auto")
    timeout = metadata.get("code_execution_timeout")

    # Validate code before execution to prevent dangerous code bypass
    # when using non-Docker execution managers.
    from backend.services.code_executor.validator import validate_code

    validation = validate_code(code, strict_mode=True)
    if not validation.is_valid:
        metadata["code_exec_status"] = "failed"
        metadata["code_exec_error"] = f"validation_failed: {validation.error}"
        metadata["code_exec_result"] = {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": f"Code validation failed: {validation.error}",
        }
        return state

    # Run synchronous execute_code in thread pool to avoid blocking event loop
    result = await asyncio.to_thread(
        manager.execute_code,
        code=code,
        data_files=metadata.get("code_execution_files"),
        timeout=timeout,
        mode=mode,
    )
    if not isinstance(result, dict):
        metadata["code_exec_status"] = "failed"
        metadata["code_exec_error"] = "invalid_result"
        return state

    metadata["code_exec_status"] = "ok" if result.get("success") else "failed"
    metadata["code_exec_result"] = {
        "success": bool(result.get("success")),
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "error": result.get("error"),
    }
    return state
