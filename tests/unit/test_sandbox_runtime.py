"""W1 unit tests for the startup sandbox-readiness probe.

Per Plan Appendix E W5, this module has exactly one test covering the
happy path + failure modes of verify_sandbox_packages. Integration-level
verification of the probe against a real E2B sandbox lives in the
env-gated `test_agentic_real_provider.py` (W5 Day 1-2 verification).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.services.code_executor.sandbox_runtime import (
    SandboxReadiness,
    set_agent_runtime_ready,
    is_agent_runtime_ready,
    verify_sandbox_packages,
)


@pytest.mark.asyncio
async def test_verify_packages_logs_and_fails_gracefully():
    """Single test covering 4 scenarios the probe must handle.

    Plan E.3 W5 budgeted 1 test for this module; inline the scenarios to
    keep the file lean while still exercising each branch.
    """
    # Scenario 1: no API key → ready=False, error set, no sandbox spun
    result = await verify_sandbox_packages(api_key="", packages=["statsmodels"])
    assert result.ready is False
    assert result.missing == ["statsmodels"]
    assert "E2B_API_KEY not configured" in (result.error or "")
    assert result.elapsed_s == 0.0

    # Scenario 2: sandbox reports all packages importable → ready=True
    fake_execution = MagicMock()
    fake_execution.logs.stdout = ['PROBE_RESULT=[]\n']
    fake_execution.text = ""
    fake_sbx = MagicMock()
    fake_sbx.run_code = MagicMock(return_value=fake_execution)
    fake_sbx.kill = MagicMock()

    with patch(
        "e2b_code_interpreter.Sandbox.create", return_value=fake_sbx
    ):
        result = await verify_sandbox_packages(
            api_key="test-key", packages=["statsmodels"]
        )
    assert result.ready is True
    assert result.missing == []
    assert result.error is None
    assert result.elapsed_s > 0

    # Scenario 3: sandbox reports statsmodels missing → ready=False
    fake_execution.logs.stdout = ['PROBE_RESULT=["statsmodels"]\n']
    with patch(
        "e2b_code_interpreter.Sandbox.create", return_value=fake_sbx
    ):
        result = await verify_sandbox_packages(
            api_key="test-key", packages=["statsmodels"]
        )
    assert result.ready is False
    assert result.missing == ["statsmodels"]

    # Scenario 4: sandbox creation raises → ready=False with error captured
    with patch(
        "e2b_code_interpreter.Sandbox.create",
        side_effect=RuntimeError("network unreachable"),
    ):
        result = await verify_sandbox_packages(
            api_key="test-key", packages=["statsmodels"]
        )
    assert result.ready is False
    assert result.missing == ["statsmodels"]
    assert "network unreachable" in (result.error or "")
    assert result.elapsed_s >= 0


def test_module_level_readiness_flag_starts_false_and_updates():
    """Sanity check the module-level flag that analyze_query() will read."""
    # Default state on module import is false
    assert is_agent_runtime_ready() is False

    set_agent_runtime_ready(True)
    assert is_agent_runtime_ready() is True

    set_agent_runtime_ready(False)
    assert is_agent_runtime_ready() is False
