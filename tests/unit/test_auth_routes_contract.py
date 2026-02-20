from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

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
async def test_auth_register_login_me_work_without_api_key() -> None:
    email = f"user-{uuid4().hex[:8]}@example.com"
    password = "secret123"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        register = await client.post(
            "/api/v1/auth/register",
            json={"name": "Contract User", "email": email, "password": password},
        )
        assert register.status_code == 200
        register_payload = register.json()
        assert register_payload["token"]

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200
        login_payload = login.json()
        assert login_payload["token"]

        me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login_payload['token']}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == email


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
