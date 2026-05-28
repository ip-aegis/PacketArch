# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Authentication routes."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.core.exceptions import ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.user import RefreshRequest, Token, UserCreate, UserLogin, UserResponse
from app.services import ldap_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _authenticate_via_ldap(db, credentials: UserLogin) -> User | None:
    """Try LDAP first. Returns a User on success, or None to fall through to local."""
    config = await ldap_service.load_config(db)
    if not ldap_service.is_enabled(config):
        return None

    result = ldap_service.authenticate(config, credentials.username, credentials.password)
    if not result.success:
        # Reason "not_found" / "disabled" falls back to local; anything else
        # is treated the same to avoid leaking which path accepted the creds.
        return None

    info = result.user
    assert info is not None

    # JIT provisioning: look up by (auth_source, ldap_dn) first, then username
    # as a migration-friendly fallback (e.g. if the DN was rewritten upstream).
    user = (
        await db.execute(
            select(User).where(User.auth_source == "ldap", User.ldap_dn == info.dn)
        )
    ).scalar_one_or_none()

    if user is None:
        user = (
            await db.execute(
                select(User).where(User.username == credentials.username)
            )
        ).scalar_one_or_none()
        if user is not None and user.auth_source == "local":
            # Don't let an LDAP login hijack an existing local account with
            # the same username.
            logger.warning(
                "LDAP login for '%s' collides with existing local account; rejecting",
                credentials.username,
            )
            return None

    if user is None:
        user = User(
            username=credentials.username,
            email=info.email,
            auth_source="ldap",
            ldap_dn=info.dn,
            password_hash=None,
            is_active=True,
            is_admin=False,
        )
        db.add(user)
    else:
        user.ldap_dn = info.dn
        if info.email:
            user.email = info.email
    return user


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: DBSession,
) -> Token:
    """Authenticate user and return JWT tokens.

    Tries LDAP first (if enabled and configured), then falls back to the local
    bcrypt flow. Any failure — LDAP unreachable, wrong LDAP password, unknown
    user — silently falls through so a local admin can still log in.
    """
    user = await _authenticate_via_ldap(db, credentials)

    if user is None:
        # Local bcrypt fallback. Covers: LDAP disabled, user not found in LDAP,
        # LDAP unreachable, or an existing local account.
        result = await db.execute(
            select(User).where(User.username == credentials.username)
        )
        user = result.scalar_one_or_none()

        if user is None or user.password_hash is None or not verify_password(
            credentials.password, user.password_hash
        ):
            raise INVALID_CREDENTIALS

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    # Create tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    body: RefreshRequest,
    db: DBSession,
) -> Token:
    """Refresh access token using refresh token.

    Non-sliding session: the new refresh token preserves the ORIGINAL
    `exp` of the inbound token instead of resetting the clock by
    `refresh_token_expire_days`. So the absolute session length is bounded
    by the original login, even if the user keeps the tab open and the
    frontend keeps silently refreshing. Pre-1.4 behavior was unbounded
    sliding refresh — see auth audit in tasks/todo.md.
    """
    payload = verify_token(body.refresh_token, token_type="refresh")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Preserve the original `exp` so the absolute session window doesn't
    # slide. `verify_token` already enforced that this `exp` is in the
    # future (jose checks `exp` on decode).
    original_exp = payload.get("exp")

    token_data = {"sub": str(user.id)}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data, original_exp=original_exp)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)


@router.post("/me/welcome-seen", response_model=UserResponse)
async def mark_welcome_seen(
    current_user: CurrentUser,
    db: DBSession,
) -> UserResponse:
    """Mark the Welcome Tour as dismissed for the current user."""
    if not current_user.welcome_seen:
        current_user.welcome_seen = True
        await db.commit()
        await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: DBSession,
    _admin: AdminUser,
) -> UserResponse:
    """Register a new user. Admin-only.

    Historically this was anonymous self-signup with "first user becomes
    admin" semantics. That role is now owned by the setup wizard, which runs
    while `setup.completed=false` and creates the bootstrap admin. After
    setup completes, this route is admin-only — same surface admins already
    have at `POST /api/v1/users`. Kept here for backwards compatibility with
    any tooling that hits `/auth/register`.
    """
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise ConflictError("Username already registered", resource="User")

    # Check if email already exists
    if user_data.email:
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise ConflictError("Email already registered", resource="User")

    # Created by an admin; non-admin by default. Admins promote via
    # PATCH /api/v1/users/{id} if needed.
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        is_admin=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)
