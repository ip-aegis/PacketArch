# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Security utilities for authentication and password hashing."""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# Algorithm whitelist. Hardcoded rather than read from settings so an
# operator who misconfigures `ALGORITHM=none` in `.env` cannot disable JWT
# signature checks — `python-jose` will happily accept unsigned tokens if
# `algorithms=["none"]` is passed. The trade-off: switching to RS256/ES256
# now requires a code change, not an env flip. That's the right default for
# an internet-facing app.
_JWT_ALGORITHMS = ["HS256"]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Hash a password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=_JWT_ALGORITHMS[0])
    return encoded_jwt


def create_refresh_token(
    data: dict[str, Any],
    original_exp: int | float | None = None,
) -> str:
    """Create a JWT refresh token.

    If `original_exp` is provided (a unix timestamp), the new token inherits
    that absolute expiration instead of resetting to `now + refresh_token_expire_days`.
    Used by `/auth/refresh` so the absolute session length is bounded by the
    original login — preventing the historical "sliding 7-day session that
    resets to 7 days every API call" bypass.
    """
    to_encode = data.copy()
    if original_exp is not None:
        # Carry the inbound exp through; jose accepts int / float / datetime here.
        to_encode.update({"exp": original_exp, "type": "refresh"})
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=_JWT_ALGORITHMS[0])
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=_JWT_ALGORITHMS)
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> dict[str, Any] | None:
    """Verify a token and check its type."""
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.get("type") != token_type:
        return None
    return payload
