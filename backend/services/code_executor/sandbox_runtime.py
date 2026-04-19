"""Startup-time sandbox readiness probe.

Per Plan Appendix E W1 (v3.2 APPROVED), expanded in W6 remediation:
- Purpose: verify the agentic runtime can produce a working sandbox at
  request time — that means running the same bootstrap pip install the
  loop runs per-request, then import-checking every package the validator
  whitelists. If the bootstrap step fails (pypi down, network blocked,
  E2B image regression) or a package still won't import after install,
  the probe returns ready=False.
- Probe runs once at FastAPI lifespan start, only when use_glm5_agent=true.
- On failure: log ERROR, set ready=False. The agentic route then falls
  back silently to the deterministic path. No 503, no broken request.

Three library boundaries must stay in sync (spike finding, Appendix D):
    1. Prompt: what the LLM is told it may use
    2. Validator: CodeValidator.WHITELISTED_IMPORTS
    3. Sandbox runtime: actually importable at runtime (after bootstrap)

This module governs boundary (3). `agentic_loop.BOOTSTRAP_PACKAGES`
handles boundary (3) at request time; this probe verifies that
mechanism itself works before any real request arrives.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# Packages the spike proved must be in the sandbox runtime in addition to
# E2B's defaults (pandas, numpy, matplotlib, seaborn, sklearn). Keep lean.
# Add new entries only when the validator whitelists a package that proves
# to be absent from E2B's default code-interpreter image.
EXTRA_SANDBOX_PACKAGES: List[str] = ["statsmodels"]

# Probe timeout guard. The probe spins a real E2B sandbox; network + cold
# start + bootstrap pip install + import check must complete within this
# window. Bumped 30s→90s in W6 remediation to absorb the pip-install step.
PROBE_TIMEOUT_S: int = 90


@dataclass
class SandboxReadiness:
    """Result of verify_sandbox_packages().

    ready: True iff every package in EXTRA_SANDBOX_PACKAGES imported cleanly.
    missing: packages that failed to import (or empty list when ready).
    elapsed_s: wall-clock of the probe.
    error: short message when the probe itself could not run (no E2B key,
        sandbox creation failed, import threw unexpected exception).
    """

    ready: bool
    missing: List[str] = field(default_factory=list)
    elapsed_s: float = 0.0
    error: Optional[str] = None


async def verify_sandbox_packages(
    api_key: str,
    packages: Optional[List[str]] = None,
    timeout_s: int = PROBE_TIMEOUT_S,
) -> SandboxReadiness:
    """Probe the E2B default image for the given packages.

    Pure verification. This function NEVER runs pip install — if a package
    is missing, the caller's job is to fix the image or disable the flag.

    Args:
        api_key: E2B API key. Empty string disables the probe cleanly.
        packages: override the default list (mainly for tests).
        timeout_s: hard cap on probe duration.
    """
    target = packages if packages is not None else EXTRA_SANDBOX_PACKAGES
    start = time.monotonic()

    if not api_key:
        return SandboxReadiness(
            ready=False,
            missing=list(target),
            elapsed_s=0.0,
            error="E2B_API_KEY not configured; cannot probe sandbox runtime.",
        )

    try:
        from e2b_code_interpreter import Sandbox
    except ImportError as exc:
        return SandboxReadiness(
            ready=False,
            missing=list(target),
            elapsed_s=time.monotonic() - start,
            error=f"e2b-code-interpreter not installed: {exc!s}",
        )

    sbx = None
    try:
        sbx = Sandbox.create(api_key=api_key)

        # Step 1 (W6 remediation): run the same bootstrap pip install the
        # agentic loop runs per-request. This validates BOTH the network
        # path AND the E2B runtime's ability to install our deps, not
        # just the image defaults. Packages already present make `-q` a
        # no-op, so this is cheap when the image already has them.
        bootstrap_lines = [
            "import subprocess, sys",
            (
                "r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', "
                + ", ".join(repr(p) for p in target)
                + "], capture_output=True, text=True, timeout=60)"
            ),
            "print('BOOTSTRAP_RC=' + str(r.returncode))",
            "if r.returncode != 0:",
            "    print('BOOTSTRAP_STDERR=' + r.stderr[-300:])",
        ]
        bootstrap_code = "\n".join(bootstrap_lines)
        try:
            sbx.run_code(bootstrap_code, timeout=float(min(timeout_s, 90)))
        except Exception as exc:  # noqa: BLE001 — fall through to import check
            logger.warning("probe bootstrap step raised: %s", exc)

        # Step 2: import-check each package. If bootstrap succeeded the
        # imports pass; if bootstrap failed silently an import here is
        # the guaranteed detector.
        lines = ["import json", "missing = []"]
        for pkg in target:
            lines.append(f"try:\n    import {pkg}\nexcept ImportError:\n    missing.append('{pkg}')")
        lines.append("print('PROBE_RESULT=' + json.dumps(missing))")
        probe_code = "\n".join(lines)

        execution = sbx.run_code(probe_code, timeout=float(timeout_s))
        stdout_parts = []
        if hasattr(execution, "logs") and execution.logs and hasattr(execution.logs, "stdout"):
            stdout_parts = execution.logs.stdout or []
        stdout = "".join(stdout_parts) if stdout_parts else (execution.text or "")

        import json as _json
        missing: List[str] = []
        for line in stdout.splitlines():
            if line.startswith("PROBE_RESULT="):
                try:
                    missing = _json.loads(line[len("PROBE_RESULT=") :]) or []
                except _json.JSONDecodeError:
                    missing = list(target)
                break
        else:
            # Probe ran but our marker didn't appear — treat as failure for safety
            missing = list(target)

        elapsed = time.monotonic() - start
        return SandboxReadiness(
            ready=(len(missing) == 0),
            missing=missing,
            elapsed_s=elapsed,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 — probe must never crash startup
        return SandboxReadiness(
            ready=False,
            missing=list(target),
            elapsed_s=time.monotonic() - start,
            error=f"sandbox probe failed: {type(exc).__name__}: {exc!s}",
        )
    finally:
        if sbx is not None:
            try:
                sbx.kill()
            except Exception:  # noqa: BLE001 — cleanup is best-effort
                pass


# Module-level flag consulted by analyze_query() to decide whether the
# agentic path is actually serviceable, independent of USE_GLM5_AGENT.
# Written once by main.py::lifespan startup; read by data_analysis_agent.
agent_runtime_ready: bool = False


def set_agent_runtime_ready(ready: bool) -> None:
    """Called from lifespan after the probe returns."""
    global agent_runtime_ready
    agent_runtime_ready = ready


def is_agent_runtime_ready() -> bool:
    return agent_runtime_ready
