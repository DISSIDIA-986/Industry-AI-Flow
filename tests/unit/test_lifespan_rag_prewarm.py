"""Lifespan pre-warm wiring tests for the RAG pipeline.

Pins the cold-start fix so a silent no-op, wrong-route warm-up, or a warm-up
that escalates a non-fatal failure into a startup crash cannot slip through
review. Covers:
- Gate trips when rag_prewarm_on_startup is True and we are NOT under pytest.
- Gate is a no-op when rag_prewarm_on_startup is False.
- Warm-up runs ONE real query end-to-end through get_workflow_runner().
- route_mode is resolved via the demo-mode service (cloud_only never triggers
  a stray local model load).
- Embedder is warmed (off the event loop).
- A warm-up failure is non-fatal and flips status to "failed", never raises.

Note: backend.main's warm-up self-skips when PYTEST_CURRENT_TEST is set, so
every test here must monkeypatch.delenv it to exercise the real branch.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

import backend.main as main_module


def _drive_lifespan_with_prewarm(monkeypatch, *, prewarm_enabled: bool):
    """Drive backend.main.lifespan and let the background warm-up task settle.

    Returns the final main_module.rag_prewarm_status plus the mocks so callers
    can assert on interactions.
    """
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    main_module.rag_prewarm_status = "disabled"

    runner = MagicMock()
    runner.run_workflow = AsyncMock(return_value={"response": "ok"})

    demo_service = MagicMock()
    demo_service.resolve_route_mode.return_value = "cloud_only"

    embed_mock = MagicMock(return_value=[0.0, 0.1])

    app = FastAPI()

    async def _drive():
        with patch.object(
            main_module.settings, "rag_prewarm_on_startup", prewarm_enabled
        ), patch.object(
            main_module.settings, "use_glm5_agent", False
        ), patch.object(
            main_module.settings, "code_execution_provider", ""
        ), patch(
            "backend.services.core.embedder.embed_query_text", embed_mock
        ), patch(
            "backend.api.workflow_query_routes.get_workflow_runner",
            new=AsyncMock(return_value=runner),
        ), patch(
            "backend.services.demo_mode_service.get_demo_mode_service",
            return_value=demo_service,
        ):
            cm = main_module.lifespan(app)
            await cm.__aenter__()
            # Warm-up is a background create_task; give the loop room to run it.
            for _ in range(20):
                await asyncio.sleep(0.01)
            await cm.__aexit__(None, None, None)

    asyncio.run(_drive())
    return main_module.rag_prewarm_status, runner, demo_service, embed_mock


def test_prewarm_runs_full_query_when_enabled(monkeypatch):
    status, runner, demo_service, embed_mock = _drive_lifespan_with_prewarm(
        monkeypatch, prewarm_enabled=True
    )

    assert status == "warm", "successful warm-up must flip status to 'warm'"
    assert embed_mock.called, "embedder must be warmed"
    runner.run_workflow.assert_awaited_once()
    # route_mode must be the resolved demo route, not a hardcoded local_only.
    _, kwargs = runner.run_workflow.call_args
    assert kwargs["route_mode"] == "cloud_only"
    demo_service.resolve_route_mode.assert_called_once_with(None)


def test_prewarm_noop_when_disabled(monkeypatch):
    status, runner, _demo, embed_mock = _drive_lifespan_with_prewarm(
        monkeypatch, prewarm_enabled=False
    )

    assert status == "disabled", "disabled flag must leave status untouched"
    runner.run_workflow.assert_not_awaited()
    assert not embed_mock.called


def test_prewarm_self_skips_under_pytest(monkeypatch):
    """With PYTEST_CURRENT_TEST set (the real CI/dev condition), the warm-up
    must NOT load real models even if the flag is on."""
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "dummy::test")
    main_module.rag_prewarm_status = "disabled"

    runner = MagicMock()
    runner.run_workflow = AsyncMock()
    app = FastAPI()

    async def _drive():
        with patch.object(
            main_module.settings, "rag_prewarm_on_startup", True
        ), patch.object(
            main_module.settings, "use_glm5_agent", False
        ), patch.object(
            main_module.settings, "code_execution_provider", ""
        ), patch(
            "backend.api.workflow_query_routes.get_workflow_runner",
            new=AsyncMock(return_value=runner),
        ):
            cm = main_module.lifespan(app)
            await cm.__aenter__()
            for _ in range(5):
                await asyncio.sleep(0.01)
            await cm.__aexit__(None, None, None)

    asyncio.run(_drive())
    assert main_module.rag_prewarm_status == "disabled"
    runner.run_workflow.assert_not_awaited()


def test_prewarm_task_cancelled_on_shutdown(monkeypatch):
    """A warm-up still in flight at lifespan shutdown must be cancelled, not
    orphaned, and the cancellation must not propagate out of lifespan."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    main_module.rag_prewarm_status = "disabled"

    runner = MagicMock()

    async def _never_returns(**_kwargs):
        await asyncio.Event().wait()  # hang until cancelled

    runner.run_workflow = _never_returns

    demo_service = MagicMock()
    demo_service.resolve_route_mode.return_value = "cloud_only"
    app = FastAPI()

    async def _drive():
        with patch.object(
            main_module.settings, "rag_prewarm_on_startup", True
        ), patch.object(
            main_module.settings, "use_glm5_agent", False
        ), patch.object(
            main_module.settings, "code_execution_provider", ""
        ), patch(
            "backend.services.core.embedder.embed_query_text",
            MagicMock(return_value=[0.0]),
        ), patch(
            "backend.api.workflow_query_routes.get_workflow_runner",
            new=AsyncMock(return_value=runner),
        ), patch(
            "backend.services.demo_mode_service.get_demo_mode_service",
            return_value=demo_service,
        ):
            cm = main_module.lifespan(app)
            await cm.__aenter__()
            # Let the warm-up reach the hanging run_workflow.
            for _ in range(10):
                await asyncio.sleep(0.01)
            # __aexit__ must cancel the still-running task without raising.
            await cm.__aexit__(None, None, None)

    # Must complete without an unhandled CancelledError escaping.
    asyncio.run(_drive())


def test_prewarm_failure_is_non_fatal(monkeypatch, caplog):
    """An exception inside warm-up must flip status to 'failed' and never
    propagate out of lifespan."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    main_module.rag_prewarm_status = "disabled"

    app = FastAPI()

    async def _drive():
        with patch.object(
            main_module.settings, "rag_prewarm_on_startup", True
        ), patch.object(
            main_module.settings, "use_glm5_agent", False
        ), patch.object(
            main_module.settings, "code_execution_provider", ""
        ), patch(
            "backend.services.core.embedder.embed_query_text",
            side_effect=RuntimeError("boom"),
        ):
            cm = main_module.lifespan(app)
            # Must not raise.
            await cm.__aenter__()
            for _ in range(20):
                await asyncio.sleep(0.01)
            await cm.__aexit__(None, None, None)

    with caplog.at_level("WARNING"):
        asyncio.run(_drive())

    assert main_module.rag_prewarm_status == "failed"
    joined = " ".join(rec.message for rec in caplog.records)
    assert "RAG pre-warm failed" in joined
