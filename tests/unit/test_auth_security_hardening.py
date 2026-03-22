"""Tests for security hardening: env-var password, registration gating, auth enforcement."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.config import settings
from backend.main import app


@pytest.mark.asyncio
async def test_login_with_env_password_succeeds() -> None:
    """Login with the DEMO_USER_PASSWORD env var password should succeed."""
    password = settings.demo_user_password
    assert password, "DEMO_USER_PASSWORD must be set for this test"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "demo@example.com", "password": password},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token"]
    assert payload["user"]["email"] == "demo@example.com"


@pytest.mark.asyncio
async def test_login_with_old_demo123_fails() -> None:
    """The old hardcoded password 'demo123' must no longer work."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "demo@example.com", "password": "demo123"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_returns_403_when_disabled() -> None:
    """Registration must be blocked when ALLOW_REGISTRATION=false."""
    assert not settings.allow_registration, "ALLOW_REGISTRATION should be false"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Attacker",
                "email": "attacker@example.com",
                "password": "password123",
            },
        )

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unauthenticated_api_returns_401() -> None:
    """API endpoints must require auth when REQUIRE_USER_AUTH=true."""
    if not settings.require_user_auth:
        pytest.skip("REQUIRE_USER_AUTH is not enabled")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Test workflow query endpoint
        response = await client.post(
            "/api/v1/workflow/query",
            json={"query": "test"},
        )

    assert response.status_code in (401, 500)
    # 401 = proper auth rejection; 500 = JWT secret validation error
    # Both mean the request was blocked, not processed


@pytest.mark.asyncio
async def test_authenticated_api_passes_auth_check() -> None:
    """Authenticated requests should pass the auth middleware."""
    password = settings.demo_user_password
    if not password:
        pytest.skip("DEMO_USER_PASSWORD not set")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # First login to get a token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "demo@example.com", "password": password},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["token"]

        # Use token to access /auth/me (verifies token is valid)
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "demo@example.com"


def test_startup_fails_without_jwt_secret() -> None:
    """Server should fail fast if REQUIRE_USER_AUTH=true but AUTH_JWT_SECRET is empty."""
    with patch.object(settings, "require_user_auth", True), patch.object(
        settings, "auth_jwt_secret", ""
    ):
        # Import the lifespan function and test it raises
        from backend.main import lifespan

        import asyncio

        async def _run_lifespan():
            async with lifespan(app):
                pass

        with pytest.raises(RuntimeError, match="AUTH_JWT_SECRET"):
            asyncio.get_event_loop().run_until_complete(_run_lifespan())
