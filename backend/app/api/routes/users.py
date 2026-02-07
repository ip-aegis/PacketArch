"""User management API routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, CurrentUser, DBSession
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

    Requires the current password for verification.
    """
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
    # Get the target user
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if target_user is None:
        raise NotFoundError("User")

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
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise NotFoundError("User")

    return user


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

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise NotFoundError("User")

    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)

    return user
