from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.config import settings
from backend.main import app


@pytest.mark.asyncio
async def test_health_route_is_public_without_api_key() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json().get("status") == "ok"


@pytest.mark.asyncio
async def test_auth_login_me_work_without_api_key() -> None:
    """Login + /me flow works with the demo user (registration disabled)."""
    password = settings.demo_user_password
    if not password:
        pytest.skip("DEMO_USER_PASSWORD not set")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "demo@example.com", "password": password},
        )
        assert login.status_code == 200
        login_payload = login.json()
        assert login_payload["token"]

        me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login_payload['token']}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == "demo@example.com"


@pytest.mark.asyncio
async def test_auth_login_rejects_invalid_credentials() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "bad"},
        )

    assert response.status_code == 401
