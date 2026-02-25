"""Lightweight auth routes for frontend contract compatibility."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import re
from threading import Lock
from typing import Dict, List
from uuid import uuid4

import jwt
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from backend.config import settings
from backend.security.auth import build_identity

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_users_lock = Lock()
_users: Dict[str, Dict[str, str | List[str]]] = {
    "demo@example.com": {
        "id": "user-demo",
        "name": "Demo User",
        "email": "demo@example.com",
        "password": "demo123",
        "roles": ["user"],
    }
}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _jwt_secret() -> str:
    return settings.auth_jwt_secret or "industry-ai-flow-dev-secret"


def _create_access_token(user: Dict[str, str | List[str]]) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user["id"]),
        "email": str(user["email"]),
        "name": str(user["name"]),
        "roles": list(user.get("roles") or []),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=24)).timestamp()),
        "jti": str(uuid4()),
    }
    if settings.auth_jwt_issuer:
        payload["iss"] = settings.auth_jwt_issuer
    if settings.auth_jwt_audience:
        payload["aud"] = settings.auth_jwt_audience
    return jwt.encode(payload, _jwt_secret(), algorithm=settings.auth_jwt_algorithm)


def _public_user(user: Dict[str, str | List[str]]) -> Dict[str, str | List[str]]:
    return {
        "id": str(user["id"]),
        "name": str(user["name"]),
        "email": str(user["email"]),
        "roles": list(user.get("roles") or []),
    }


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=256)
    password: str = Field(..., min_length=1, max_length=256)

    @field_validator("email", mode="before")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if not _EMAIL_RE.match(normalized):
            raise ValueError("Invalid email format")
        return normalized


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., min_length=3, max_length=256)
    password: str = Field(..., min_length=6, max_length=256)

    @field_validator("email", mode="before")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if not _EMAIL_RE.match(normalized):
            raise ValueError("Invalid email format")
        return normalized


class AuthResponse(BaseModel):
    token: str
    user: Dict[str, str | List[str]]


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    with _users_lock:
        user = _users.get(payload.email.lower())

    if not user or user.get("password") != payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return AuthResponse(token=_create_access_token(user), user=_public_user(user))


@router.post("/register", response_model=AuthResponse)
async def register(payload: RegisterRequest) -> AuthResponse:
    key = payload.email.lower()
    with _users_lock:
        if key in _users:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user = {
            "id": f"user-{uuid4().hex[:8]}",
            "name": payload.name,
            "email": key,
            "password": payload.password,
            "roles": ["user"],
        }
        _users[key] = user

    return AuthResponse(token=_create_access_token(user), user=_public_user(user))


@router.post("/logout")
async def logout() -> Dict[str, bool]:
    # Stateless JWT for now; frontend clears local token.
    return {"success": True}


@router.get("/me")
async def me(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Dict[str, str | List[str]]:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be Bearer token",
        )

    try:
        decoded = jwt.decode(
            parts[1],
            _jwt_secret(),
            algorithms=[settings.auth_jwt_algorithm],
            options={"verify_aud": bool(settings.auth_jwt_audience)},
            issuer=settings.auth_jwt_issuer or None,
            audience=settings.auth_jwt_audience or None,
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc

    identity = build_identity(decoded)
    return {
        "id": identity.user_id,
        "name": str(decoded.get("name") or identity.user_id),
        "email": str(decoded.get("email") or ""),
        "roles": identity.roles,
    }
