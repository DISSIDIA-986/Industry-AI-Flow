"""Lightweight auth routes for frontend contract compatibility."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
import os
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


def _hash_password(password: str) -> str:
    # TODO: migrate to bcrypt/argon2id for production password hashing
    salt = os.urandom(16).hex()
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"


def _verify_password(password: str, stored: str) -> bool:
    if "$" not in stored:
        return False
    salt, h = stored.split("$", 1)
    return hmac.compare_digest(
        hashlib.sha256((salt + password).encode()).hexdigest(), h
    )


_users_lock = Lock()
_users: Dict[str, Dict[str, str | List[str]]] = {
    "demo@example.com": {
        "id": "user-demo",
        "name": "Demo User",
        "email": "demo@example.com",
        "password": _hash_password("demo123"),
        "roles": ["user"],
    }
}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


_EPHEMERAL_JWT_SECRET: str | None = None


def _jwt_secret() -> str:
    global _EPHEMERAL_JWT_SECRET
    secret = settings.auth_jwt_secret
    if secret:
        return secret
    if _EPHEMERAL_JWT_SECRET is None:
        import secrets as _secrets

        _EPHEMERAL_JWT_SECRET = _secrets.token_urlsafe(32)
        import logging

        logging.getLogger(__name__).warning(
            "AUTH_JWT_SECRET not configured — using ephemeral random secret."
        )
    return _EPHEMERAL_JWT_SECRET


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

    if not user or not _verify_password(payload.password, user.get("password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return AuthResponse(token=_create_access_token(user), user=_public_user(user))


@router.post("/register", response_model=AuthResponse)
async def register(payload: RegisterRequest) -> AuthResponse:
    key = payload.email.lower()
    with _users_lock:
        if len(_users) >= 1000:
            raise HTTPException(
                status_code=429, detail="Registration limit reached"
            )
        if key in _users:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user = {
            "id": f"user-{uuid4().hex[:8]}",
            "name": payload.name,
            "email": key,
            "password": _hash_password(payload.password),
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
            detail="Invalid token",
        ) from exc

    identity = build_identity(decoded)
    return {
        "id": identity.user_id,
        "name": str(decoded.get("name") or identity.user_id),
        "email": str(decoded.get("email") or ""),
        "roles": identity.roles,
    }
