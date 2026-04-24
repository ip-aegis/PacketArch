# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""User management API routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.api.helpers import get_or_404
from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.password import (
    ChangePasswordRequest,
    PasswordChangeResponse,
    ResetPasswordRequest,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/me/password", response_model=PasswordChangeResponse)
async def change_own_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> PasswordChangeResponse:
    """
    Change the current user's password.

    Requires the current password for verification. Not available to LDAP
    users — their password lives in the directory.
    """
    if current_user.auth_source != "local" or current_user.password_hash is None:
        raise ValidationError(
            "Password is managed by your directory (LDAP). Change it there."
        )

    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise ValidationError("Current password is incorrect")

    # Check new password is different
    if request.current_password == request.new_password:
        raise ValidationError("New password must be different from current password")

    # Update password
    current_user.password_hash = get_password_hash(request.new_password)
    await db.commit()

    return PasswordChangeResponse(
        success=True,
        message="Password changed successfully",
    )


@router.post("/{user_id}/reset-password", response_model=PasswordChangeResponse)
async def admin_reset_password(
    user_id: uuid.UUID,
    request: ResetPasswordRequest,
    admin: AdminUser,
    db: DBSession,
) -> PasswordChangeResponse:
    """
    Reset a user's password (admin only).

    Does not require the user's current password.
    """
    target_user = await get_or_404(db, User, user_id, "User")

    if target_user.auth_source != "local":
        raise ValidationError(
            f"User '{target_user.username}' authenticates via LDAP — password cannot be reset here."
        )

    # Update password
    target_user.password_hash = get_password_hash(request.new_password)
    await db.commit()

    return PasswordChangeResponse(
        success=True,
        message=f"Password reset successfully for user '{target_user.username}'",
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    admin: AdminUser,
    db: DBSession,
) -> list[User]:
    """
    List all users (admin only).
    """
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return list(users)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    admin: AdminUser,
    db: DBSession,
) -> User:
    """
    Get a specific user by ID (admin only).
    """
    return await get_or_404(db, User, user_id, "User")


@router.patch("/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_user_active(
    user_id: uuid.UUID,
    admin: AdminUser,
    db: DBSession,
) -> User:
    """
    Toggle a user's active status (admin only).

    Cannot deactivate yourself.
    """
    if user_id == admin.id:
        raise ValidationError("Cannot deactivate your own account")

    user = await get_or_404(db, User, user_id, "User")

    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)

    return user
