"""Lifespan pre-warm wiring tests for E2B sandbox.

Pins down the expected behavior so a silent no-op or wrong-provider warmup
cannot slip through review. Covers:
- Gate trips only when `CODE_EXECUTION_PROVIDER == "e2b"`.
- Gate does NOT trip for docker/ppio/auto.
- `get_code_execution_manager` is retrieved via the existing singleton path.
- `cloud_provider.health()` is awaited.
- Unhealthy response logs a warning instead of raising.
- Timeout wraps the health call so a stalled Sandbox.create() cannot hang startup.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

import backend.main as main_module


class _StubCloudProvider:
    def __init__(self, health_result=None, health_side_effect=None):
        self.health_calls = 0
        self._health_result = health_result or {"healthy": True, "status": "ok"}
        self._health_side_effect = health_side_effect

    async def health(self):
        self.health_calls += 1
        if self._health_side_effect is not None:
            raise self._health_side_effect
        return self._health_result


def _run_lifespan(manager_obj, provider_setting: str, *, enable_e2b: bool = False):
    """Drive backend.main.lifespan to completion with the given manager + setting.

    Returns None on clean completion; raises on unexpected error.
    """
    app = FastAPI()

    async def _drive():
        with patch.object(
            main_module.settings, "code_execution_provider", provider_setting
        ), patch.object(
            main_module.settings, "enable_e2b_code_execution", enable_e2b, create=True
        ), patch(
            "backend.services.code_executor.get_code_execution_manager",
            return_value=manager_obj,
        ):
            cm = main_module.lifespan(app)
            # __aenter__ runs everything before yield (including pre-warm)
            await cm.__aenter__()
            await cm.__aexit__(None, None, None)

    asyncio.run(_drive())


def _make_manager(cloud_provider):
    mgr = MagicMock()
    mgr.cloud_provider = cloud_provider
    return mgr


def test_prewarm_fires_only_when_provider_is_e2b(caplog):
    cloud = _StubCloudProvider()
    mgr = _make_manager(cloud)

    _run_lifespan(mgr, provider_setting="e2b")

    assert cloud.health_calls == 1, "e2b mode must trigger health()"


@pytest.mark.parametrize("provider_setting", ["docker", "ppio", "auto", ""])
def test_prewarm_skipped_for_non_e2b_providers(provider_setting):
    """When E2B is not wired at all, pre-warm must not fire."""
    cloud = _StubCloudProvider()
    mgr = _make_manager(cloud)

    _run_lifespan(mgr, provider_setting=provider_setting, enable_e2b=False)

    assert cloud.health_calls == 0, (
        f"mode {provider_setting!r} with enable_e2b=False must NOT trigger pre-warm"
    )


def test_prewarm_fires_in_auto_mode_when_e2b_enabled():
    """Auto mode with E2B wired as cloud fallback must pre-warm too.

    Codex pass-7 flagged that auto+E2B is a legitimate deployment shape and
    the first docker-fail fallback would hit a cold E2B sandbox without
    pre-warm.
    """
    cloud = _StubCloudProvider()
    mgr = _make_manager(cloud)

    _run_lifespan(mgr, provider_setting="auto", enable_e2b=True)

    assert cloud.health_calls == 1, (
        "auto mode with enable_e2b_code_execution=True must trigger pre-warm "
        "so the first docker-fail→E2B fallback lands on a warm sandbox"
    )


def test_prewarm_tolerates_no_manager():
    # get_code_execution_manager() can return None when cloud is disabled.
    _run_lifespan(None, provider_setting="e2b")
    # No crash; nothing to assert beyond clean exit.


def test_prewarm_tolerates_no_cloud_provider():
    mgr = _make_manager(None)
    _run_lifespan(mgr, provider_setting="e2b")
    # No crash.


def test_prewarm_logs_warning_on_unhealthy(caplog):
    cloud = _StubCloudProvider(
        health_result={"healthy": False, "status": "circuit_open"}
    )
    mgr = _make_manager(cloud)

    with caplog.at_level("WARNING"):
        _run_lifespan(mgr, provider_setting="e2b")

    joined = " ".join(rec.message for rec in caplog.records)
    assert "unhealthy" in joined.lower() or "circuit_open" in joined


def test_prewarm_non_fatal_on_exception(caplog):
    cloud = _StubCloudProvider(health_side_effect=RuntimeError("boom"))
    mgr = _make_manager(cloud)

    with caplog.at_level("WARNING"):
        # Must not raise — pre-warm failure is non-fatal
        _run_lifespan(mgr, provider_setting="e2b")

    joined = " ".join(rec.message for rec in caplog.records)
    assert "E2B pre-warm failed" in joined


def test_provider_health_structurally_offloads_to_thread():
    """[P1 regression, pass-6] E2BExecutionProvider.health() must offload the
    sync Sandbox.create() to a worker thread.

    Codex pass-6 pointed out that patching this in lifespan only protects ONE
    caller. The auto-mode Docker-fail → E2B-fallback path (manager.py:54 in
    _provider_health) still blocks the event loop if health() itself is
    inline-sync. Fix at the source: provider.health() owns the offload, every
    caller is protected automatically.
    """
    import inspect

    from backend.services.code_executor.providers.e2b_provider import (
        E2BExecutionProvider,
    )

    source = inspect.getsource(E2BExecutionProvider.health)
    assert "to_thread" in source, (
        "E2BExecutionProvider.health() must offload Sandbox.create() via "
        "asyncio.to_thread — otherwise every async caller (lifespan, auto "
        "mode fallback) blocks the event loop on cold starts"
    )


def test_provider_health_does_not_block_event_loop():
    """Verify the offload actually works: while health() runs, the event
    loop stays free to do other work.

    With the offload in the provider, we can write a real timing test
    because we are not inside asyncio.run's executor-shutdown wait. We
    mock out the e2b_code_interpreter import so Sandbox.create() becomes a
    controllable sync sleep that we can time against loop responsiveness.
    """
    import sys
    import time
    import types

    from backend.services.code_executor.providers.e2b_provider import (
        E2BExecutionProvider,
    )

    # Fake e2b_code_interpreter module whose Sandbox.create sleeps 0.5s
    # synchronously and whose kill is a no-op.
    fake_mod = types.ModuleType("e2b_code_interpreter")

    class _FakeSandbox:
        def __init__(self):
            pass

        @staticmethod
        def create(api_key=None):
            time.sleep(0.5)
            return _FakeSandbox()

        def kill(self):
            pass

    fake_mod.Sandbox = _FakeSandbox
    # Save the original entry (if any) so we can restore it. Popping
    # unconditionally on cleanup would evict a legitimately cached module
    # and break unrelated tests that imported e2b_code_interpreter earlier.
    _MISSING = object()
    _original = sys.modules.get("e2b_code_interpreter", _MISSING)
    sys.modules["e2b_code_interpreter"] = fake_mod

    try:
        provider = E2BExecutionProvider(enabled=True, api_key="test-key")

        async def _race():
            # Kick off health() and a simple async tick in parallel. If
            # health() blocks the loop, the tick won't run until after
            # Sandbox.create's sleep. With proper offload, the tick runs
            # immediately.
            tick_done = asyncio.Event()

            async def _tick():
                tick_done.set()

            health_task = asyncio.create_task(provider.health())
            tick_task = asyncio.create_task(_tick())
            # Give the event loop a chance to schedule _tick.
            await asyncio.sleep(0.05)
            tick_ran = tick_done.is_set()
            result = await health_task
            await tick_task
            return tick_ran, result

        tick_ran, result = asyncio.run(_race())
    finally:
        if _original is _MISSING:
            sys.modules.pop("e2b_code_interpreter", None)
        else:
            sys.modules["e2b_code_interpreter"] = _original

    assert tick_ran, (
        "event loop was blocked during provider.health() — "
        "Sandbox.create() is not offloaded to a thread"
    )
    assert result.get("healthy") is True


def test_prewarm_timeout_branch_logs_non_fatal(caplog):
    """TimeoutError from wait_for logs a warning and does not propagate."""
    # A provider whose health() never resolves so wait_for will fire.
    class _NeverResolving:
        async def health(self):
            await asyncio.Event().wait()  # never set

    mgr = _make_manager(_NeverResolving())

    # Patch wait_for to raise TimeoutError immediately so we exercise the
    # except branch deterministically without waiting 15 real seconds.
    async def _instant_timeout(coro, timeout):
        # Cancel the awaitable to avoid pending-task warnings.
        if hasattr(coro, "close"):
            coro.close()
        raise TimeoutError()

    with caplog.at_level("WARNING"):
        with patch("asyncio.wait_for", new=_instant_timeout):
            _run_lifespan(mgr, provider_setting="e2b")

    joined = " ".join(rec.message for rec in caplog.records)
    assert "timed out" in joined.lower() or "timeout" in joined.lower()
