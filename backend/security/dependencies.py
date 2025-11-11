"""FastAPI dependency helpers for security and multi-tenancy."""

from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException, Request, status

from backend.config import settings
from backend.security.auth import UserIdentity, authenticate_user
from backend.security.context import TenantContext, set_tenant_context
from backend.security.rate_limiter import RateLimitExceeded, SlidingWindowRateLimiter

_rate_limiter = SlidingWindowRateLimiter(
    limit=settings.api_rate_limit_per_minute,
    interval_seconds=60,
    burst=settings.api_rate_limit_burst,
)


async def secure_endpoint(
    request: Request,
    api_key: Optional[str] = Header(
        default=None, alias=settings.api_key_header, convert_underscores=False
    ),
    authorization: Optional[str] = Header(
        default=None, alias="Authorization", convert_underscores=False
    ),
) -> TenantContext:
    """
    Shared dependency that enforces:
    - Optional API key authentication
    - Tenant resolution
    - Lightweight rate limiting per tenant/IP
    """

    client_host = request.client.host if request.client else "unknown"
    user_identity: Optional[UserIdentity] = None

    # 1. API key validation
    if settings.require_api_key:
        if not api_key or not settings.is_api_key_allowed(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )
    elif api_key and not settings.is_api_key_allowed(api_key):
        # If API keys are provided but not required, still block unknown keys
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provided API key is not recognized",
        )

    # 2. User authentication (Bearer token)
    if authorization or settings.require_user_auth:
        if not settings.auth_jwt_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User authentication required but AUTH_JWT_SECRET not configured.",
            )
        user_identity = authenticate_user(authorization)

    # 3. Tenant resolution
    tenant_id = (
        request.headers.get(settings.tenant_header) or settings.default_tenant_id
    )
    if (
        not tenant_id
        and settings.multi_tenant_mode
        and not settings.allow_anonymous_tenants
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant header is required",
        )
    tenant_id = tenant_id or settings.default_tenant_id

    # 4. Rate limiting (per tenant + IP)
    limiter_key = f"{tenant_id}:{client_host}"
    try:
        _rate_limiter.hit(limiter_key)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, slow down.",
            headers={"Retry-After": f"{int(exc.retry_after) + 1}"},
        ) from exc

    context = TenantContext(
        tenant_id=tenant_id,
        api_key=api_key,
        headers=dict(request.headers),
        ip_address=client_host,
    )
    if user_identity:
        context.user_id = user_identity.user_id
        context.roles = user_identity.roles
        context.permissions = user_identity.permissions
    set_tenant_context(context)
    request.state.tenant_context = context
    return context


async def get_current_tenant(request: Request) -> TenantContext:
    """Helper dependency to fetch the tenant context after `secure_endpoint`."""
    context: Optional[TenantContext] = getattr(request.state, "tenant_context", None)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant context not initialized; ensure `secure_endpoint` is used.",
        )
    return context
