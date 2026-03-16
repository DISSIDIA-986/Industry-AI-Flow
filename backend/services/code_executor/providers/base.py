"""Execution provider protocol and result model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Protocol


@dataclass
class ExecutionResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    execution_time_s: float = 0.0
    output_files: Dict[str, bytes] = field(default_factory=dict)


class ExecutionProvider(Protocol):
    async def execute(
        self,
        code: str,
        files: Optional[Dict[str, bytes]] = None,
        timeout_s: int = 60,
    ) -> ExecutionResult:
        ...

    async def health(self) -> dict:
        ...
