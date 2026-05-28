"""Health endpoint surfaces agentic runtime readiness.

Without this field, operators have to grep uvicorn logs to know which
data-analysis code path is live (agentic vs deterministic_planner).
That gap was hit in a 2026-05-28 stress-eval iteration where the
agentic probe was false and the symptom looked like 'reproducibility
broken' when it was actually 'agentic not even running'.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from tests.conftest import get_demo_auth_headers

_AUTH = get_demo_auth_headers()


@pytest.mark.asyncio
async def test_health_includes_agentic_runtime_field():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/v1/health", headers=_AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert "agentic_runtime" in body, (
        "/health envelope must include agentic_runtime so operators can "
        "tell pre-demo which data-analysis code path is live"
    )


@pytest.mark.asyncio
async def test_agentic_runtime_shape_is_explicit():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/v1/health", headers=_AUTH)
    ar = resp.json()["agentic_runtime"]
    # All three fields MUST be present so consumers can distinguish:
    #   feature_flag=False              → operator turned it off
    #   feature_flag=True, probe=False  → startup probe rejected (e.g. E2B unreachable)
    #   feature_flag=True, probe=True   → agentic path is live (active=True)
    assert set(ar.keys()) == {"feature_flag", "probe_ready", "active"}, (
        f"agentic_runtime shape changed unexpectedly: {sorted(ar.keys())}"
    )
    for k in ("feature_flag", "probe_ready", "active"):
        assert isinstance(ar[k], bool), f"{k} must be bool, got {type(ar[k]).__name__}"


@pytest.mark.asyncio
async def test_active_is_logical_and_of_flag_and_probe():
    """`active` field is the AND of the two — what analyze_query() actually checks."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/v1/health", headers=_AUTH)
    ar = resp.json()["agentic_runtime"]
    assert ar["active"] == (ar["feature_flag"] and ar["probe_ready"]), (
        "active must equal feature_flag AND probe_ready"
    )
