"""FastAPI dependency helpers for security and multi-tenancy."""

from __future__ import annotations

import ipaddress
import logging
import re
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
logger = logging.getLogger(__name__)
_missing_api_key_config_logged = False

_PUBLIC_PATH_PREFIXES = (
    "/health",
    "/api/v1/health",
    "/api/v1/auth/",
    "/api/v1/data/analyze/stream/",  # SSE — EventSource can't send headers; UUID4 job_id is auth
)


def _is_public_path(path: str) -> bool:
    """Endpoints that are intentionally reachable without API key."""
    if path in {"/api/v1/auth", "/api/v1/auth/"}:
        return True
    return path.startswith(_PUBLIC_PATH_PREFIXES)


def _normalize_forwarded_ip(value: str) -> Optional[str]:
    token = (value or "").strip().strip('"')
    if not token or token.lower() == "unknown":
        return None

    # RFC 7239 can encode IPv6 as for="[2001:db8::1]:1234"
    if token.startswith("["):
        end = token.find("]")
        if end > 1:
            token = token[1:end]
    # Common X-Forwarded-For form for IPv4: "203.0.113.1:53210"
    elif ":" in token and "." in token:
        maybe_ip, maybe_port = token.rsplit(":", 1)
        if maybe_port.isdigit():
            token = maybe_ip

    try:
        return str(ipaddress.ip_address(token))
    except ValueError:
        return None


def _resolve_proxy_forwarded_ip(request: Request) -> Optional[str]:
    x_forwarded_for = request.headers.get("X-Forwarded-For", "")
    if x_forwarded_for:
        for part in x_forwarded_for.split(","):
            ip = _normalize_forwarded_ip(part)
            if ip:
                return ip

    x_real_ip = _normalize_forwarded_ip(request.headers.get("X-Real-IP", ""))
    if x_real_ip:
        return x_real_ip

    forwarded = request.headers.get("Forwarded", "")
    if forwarded:
        match = re.search(r"for=(?:\"?)([^;,\"\\s]+)", forwarded, re.IGNORECASE)
        if match:
            ip = _normalize_forwarded_ip(match.group(1))
            if ip:
                return ip

    return None


def _resolve_client_host(request: Request) -> str:
    direct_host = request.client.host if request.client else "unknown"
    if not settings.trust_proxy_headers:
        return direct_host
    if direct_host not in settings.trusted_proxy_ip_set:
        return direct_host
    forwarded_ip = _resolve_proxy_forwarded_ip(request)
    return forwarded_ip or direct_host


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

    client_host = _resolve_client_host(request)
    user_identity: Optional[UserIdentity] = None
    path = request.url.path
    is_public = _is_public_path(path)

    # 1. API key validation
    configured_api_keys = bool(settings.api_key_set or settings.api_key_hashes)
    enforce_api_key = settings.require_api_key and configured_api_keys
    global _missing_api_key_config_logged
    if settings.require_api_key and not configured_api_keys and not is_public:
        if not _missing_api_key_config_logged:
            logger.warning(
                "REQUIRE_API_KEY is enabled but no API keys are configured; "
                "temporarily allowing requests without API key."
            )
            _missing_api_key_config_logged = True

    if enforce_api_key and not is_public:
        if not api_key or not settings.is_api_key_allowed(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )
    elif api_key and configured_api_keys and not settings.is_api_key_allowed(api_key):
        # If API keys are provided but not required, still block unknown keys
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provided API key is not recognized",
        )

    # 2. User authentication (Bearer token)
    if (authorization or settings.require_user_auth) and not is_public:
        if not settings.auth_jwt_secret:
            # Optional bearer auth should not break non-auth-required deployments.
            if settings.require_user_auth:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="User authentication required but AUTH_JWT_SECRET not configured.",
                )
        else:
            user_identity = authenticate_user(authorization)

    # 3. Tenant resolution
    tenant_id = (
        request.headers.get(settings.tenant_header) or settings.default_tenant_id
    )
    import re as _re

    if tenant_id and tenant_id != settings.default_tenant_id:
        if not _re.match(r"^[a-zA-Z0-9_-]{1,64}$", tenant_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant identifier format",
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
