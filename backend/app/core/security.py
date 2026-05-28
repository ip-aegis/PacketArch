# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Security utilities for authentication and password hashing."""

import logging
import secrets
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

# Per-process boot ID. Generated fresh every time this module loads, which
# is every time the backend container starts (host reboot, `docker compose
# restart backend`, `up -d --build backend`, etc.). Every JWT we mint
# carries this in the `bid` claim; `decode_token` rejects any token whose
# `bid` doesn't match. Net effect: EVERY backend restart invalidates EVERY
# outstanding session.
#
# This is the deliberate trade-off for an internet-exposed deployment: a
# stolen token (XSS, browser extension exfil, shoulder-surfed laptop) is
# bounded by the time until the next backend restart, not by the JWT's
# `exp` alone. The operator pays for it in having to re-login after every
# deploy — fine for a single-admin security tool, would be unacceptable
# for a multi-tenant SaaS.
#
# NOT persisted anywhere on purpose. If a future change wants
# "force-logout-all" without a backend restart, layer a per-user
# `tokens_invalid_before` timestamp on top — don't make BOOT_ID writable.
_BOOT_ID = secrets.token_hex(16)
logging.getLogger(__name__).info("JWT BOOT_ID generated for this process; all prior sessions invalidated")


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
    to_encode.update({"exp": expire, "type": "access", "bid": _BOOT_ID})
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
        to_encode.update({"exp": original_exp, "type": "refresh", "bid": _BOOT_ID})
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh", "bid": _BOOT_ID})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=_JWT_ALGORITHMS[0])
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token.

    Beyond the standard cryptographic + `exp` check, we also require the
    `bid` claim to match this process's `_BOOT_ID`. Tokens minted by a
    previous backend process (pre-restart) are rejected, which is how
    "restart the backend = log everyone out" gets enforced.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=_JWT_ALGORITHMS)
    except JWTError:
        return None
    if payload.get("bid") != _BOOT_ID:
        # Token was minted by a prior backend boot (or by an attacker who
        # forged the signature but didn't know the current bid — though if
        # they have the signing key, bid won't save us). Either way, drop.
        return None
    return payload


def verify_token(token: str, token_type: str = "access") -> dict[str, Any] | None:
    """Verify a token and check its type."""
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.get("type") != token_type:
        return None
    return payload
