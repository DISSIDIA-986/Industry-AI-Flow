"""User authentication helpers (JWT-based)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import jwt
from fastapi import HTTPException, status

from backend.config import settings


@dataclass
class UserIdentity:
    user_id: str
    roles: List[str]
    permissions: List[str]
    issuer: Optional[str] = None
    audience: Optional[str] = None
    token_id: Optional[str] = None


def _parse_authorization_header(header: str) -> str:
    if not header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be Bearer token",
        )
    return parts[1]


def _decode_jwt(token: str) -> Dict[str, Any]:
    try:
        options = {"verify_aud": bool(settings.auth_jwt_audience)}
        decoded = jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=[settings.auth_jwt_algorithm],
            issuer=settings.auth_jwt_issuer or None,
            audience=settings.auth_jwt_audience or None,
            options=options,
        )
        return decoded
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc


def build_identity(payload: Dict[str, Any]) -> UserIdentity:
    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )
    roles = payload.get("roles") or settings.default_roles_list
    if isinstance(roles, str):
        roles = [roles]
    permissions = payload.get("permissions") or []
    if isinstance(permissions, str):
        permissions = [permissions]

    return UserIdentity(
        user_id=str(user_id),
        roles=[str(role) for role in roles],
        permissions=[str(p) for p in permissions],
        issuer=payload.get("iss"),
        audience=payload.get("aud"),
        token_id=payload.get("jti"),
    )


def authenticate_user(authorization_header: Optional[str]) -> Optional[UserIdentity]:
    """Validate bearer token and return user identity or None."""
    if not authorization_header:
        if settings.require_user_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization token required",
            )
        return None

    token = _parse_authorization_header(authorization_header)
    payload = _decode_jwt(token)
    return build_identity(payload)
