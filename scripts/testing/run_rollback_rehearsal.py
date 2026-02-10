#!/usr/bin/env python3
"""Run rollback rehearsal checks for workflow release readiness."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings


@dataclass(frozen=True)
class RehearsalCheck:
    name: str
    passed: bool
    expected: str
    actual: str
    message: str


@dataclass
class RehearsalResult:
    passed: bool
    checks: List[RehearsalCheck] = field(default_factory=list)

    @property
    def failed_checks(self) -> List[RehearsalCheck]:
        return [item for item in self.checks if not item.passed]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "failed_count": len(self.failed_checks),
            "checks": [asdict(item) for item in self.checks],
        }


async def _probe_workflow_fallback() -> tuple[bool, str]:
    from types import SimpleNamespace

    from backend.services.workflows.orchestrator import (
        DefaultWorkflowRunner,
        WorkflowOrchestrator,
    )

    runner = DefaultWorkflowRunner(
        orchestrator=WorkflowOrchestrator(services=SimpleNamespace())
    )
    response = await runner.run_workflow(
        query="rollback rehearsal smoke query",
        session_id="rollback-rehearsal",
    )
    metadata = response.get("metadata") or {}
    if not response.get("success"):
        return False, "fallback runner returned success=False"
    if metadata.get("workflow_runner") != "fallback_orchestrator":
        return False, "unexpected workflow_runner marker"
    if not response.get("agent_response"):
        return False, "fallback runner produced empty response"
    return True, "fallback runner responded successfully"


async def evaluate_rehearsal(
    *,
    skip_prompt_check: bool,
    skip_provider_check: bool,
    skip_fallback_check: bool,
) -> RehearsalResult:
    checks: List[RehearsalCheck] = []

    if not skip_prompt_check:
        prompt_enabled = bool(getattr(settings, "prompt_experiments_enabled", False))
        checks.append(
            RehearsalCheck(
                name="prompt_experiments_disabled",
                passed=not prompt_enabled,
                expected="PROMPT_EXPERIMENTS_ENABLED=false",
                actual=str(prompt_enabled).lower(),
                message="Prompt experiments must be disabled for rollback rehearsal.",
            )
        )

    if not skip_provider_check:
        provider = str(getattr(settings, "code_execution_provider", "") or "")
        checks.append(
            RehearsalCheck(
                name="code_execution_provider_docker",
                passed=provider == "docker",
                expected="docker",
                actual=provider or "<empty>",
                message="Rollback mode should force docker execution provider.",
            )
        )

    if not skip_fallback_check:
        ok, reason = await _probe_workflow_fallback()
        checks.append(
            RehearsalCheck(
                name="workflow_fallback_runner",
                passed=ok,
                expected="fallback runner can return successful response",
                actual=reason,
                message="Workflow must keep serving requests in fallback mode.",
            )
        )

    return RehearsalResult(
        passed=all(item.passed for item in checks) if checks else True,
        checks=checks,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run workflow rollback rehearsal checks")
    parser.add_argument(
        "--skip-prompt-check",
        action="store_true",
        help="Skip PROMPT_EXPERIMENTS_ENABLED rollback check",
    )
    parser.add_argument(
        "--skip-provider-check",
        action="store_true",
        help="Skip CODE_EXECUTION_PROVIDER rollback check",
    )
    parser.add_argument(
        "--skip-fallback-check",
        action="store_true",
        help="Skip fallback workflow smoke check",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = asyncio.run(
        evaluate_rehearsal(
            skip_prompt_check=args.skip_prompt_check,
            skip_provider_check=args.skip_provider_check,
            skip_fallback_check=args.skip_fallback_check,
        )
    )
    if args.pretty:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
