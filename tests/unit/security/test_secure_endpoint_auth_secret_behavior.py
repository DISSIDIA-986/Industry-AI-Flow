from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.config import settings
from backend.security import dependencies
from backend.security.dependencies import secure_endpoint


def _build_request(path: str = "/api/v1/cost-estimation/predict") -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 54321),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_secure_endpoint_allows_optional_bearer_when_secret_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "require_api_key", False)
    monkeypatch.setattr(settings, "require_user_auth", False)
    monkeypatch.setattr(settings, "auth_jwt_secret", "")
    monkeypatch.setattr(settings, "default_tenant_id", "public")
    monkeypatch.setattr(
        dependencies,
        "authenticate_user",
        lambda _authorization: (_ for _ in ()).throw(
            AssertionError("authenticate_user should not be called")
        ),
    )
    monkeypatch.setattr(dependencies._rate_limiter, "hit", lambda _key: None)

    context = await secure_endpoint(
        request=_build_request(),
        api_key=None,
        authorization="Bearer dummy-token",
    )

    assert context.tenant_id == "public"
    assert context.user_id is None


@pytest.mark.asyncio
async def test_secure_endpoint_requires_secret_when_user_auth_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "require_api_key", False)
    monkeypatch.setattr(settings, "require_user_auth", True)
    monkeypatch.setattr(settings, "auth_jwt_secret", "")
    monkeypatch.setattr(dependencies._rate_limiter, "hit", lambda _key: None)

    with pytest.raises(HTTPException) as exc:
        await secure_endpoint(
            request=_build_request(),
            api_key=None,
            authorization="Bearer dummy-token",
        )

    assert exc.value.status_code == 500
    assert "AUTH_JWT_SECRET not configured" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_secure_endpoint_skips_api_key_enforcement_when_no_keys_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "require_api_key", True)
    monkeypatch.setattr(settings, "_api_key_cache", set(), raising=False)
    monkeypatch.setattr(settings, "_api_key_hash_cache", set(), raising=False)
    monkeypatch.setattr(settings, "require_user_auth", False)
    monkeypatch.setattr(settings, "default_tenant_id", "public")
    monkeypatch.setattr(dependencies, "_missing_api_key_config_logged", False)
    monkeypatch.setattr(dependencies._rate_limiter, "hit", lambda _key: None)

    context = await secure_endpoint(
        request=_build_request(),
        api_key=None,
        authorization=None,
    )

    assert context.tenant_id == "public"
