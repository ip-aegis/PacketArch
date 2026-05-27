# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""User management API routes."""

import uuid

from fastapi import APIRouter, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.api.helpers import get_or_404
from app.core.exceptions import ConflictError, ValidationError
from app.core.security import get_password_hash, verify_password
from app.models.scenario import Scenario
from app.models.settings import SystemSetting
from app.models.traffic_agent import TrafficAgent
from app.models.user import User
from app.models.user_audit import UserAuditLog
from app.schemas.password import (
    ChangePasswordRequest,
    PasswordChangeResponse,
    ResetPasswordRequest,
)
from app.schemas.user import AdminUserCreate, UserAuditEntry, UserResponse, UserUpdate
from app.services.user_audit import record_user_audit

router = APIRouter(prefix="/users", tags=["users"])


async def _active_admin_count(db: AsyncSession, exclude_id: uuid.UUID | None = None) -> int:
    """Number of active admins, optionally excluding one user (the one being
    changed). Used to refuse the last-admin lockout."""
    stmt = select(func.count()).select_from(User).where(
        User.is_admin.is_(True), User.is_active.is_(True)
    )
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return (await db.execute(stmt)).scalar_one()


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
    record_user_audit(db, actor=current_user, action="change_password", target=current_user)
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
    record_user_audit(db, actor=admin, action="reset_password", target=target_user)
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


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    admin: AdminUser,
    db: DBSession,
) -> User:
    """Create a local user (admin only)."""
    if (
        await db.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none():
        raise ConflictError(f"Username '{payload.username}' is already taken")
    if payload.email and (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none():
        raise ConflictError(f"Email '{payload.email}' is already in use")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        is_admin=payload.is_admin,
        is_active=payload.is_active,
        auth_source="local",
    )
    db.add(user)
    await db.flush()  # assign user.id for the audit row
    record_user_audit(
        db,
        actor=admin,
        action="create",
        target=user,
        detail=f"role={'admin' if user.is_admin else 'user'}, active={user.is_active}",
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/audit", response_model=list[UserAuditEntry])
async def list_user_audit(
    admin: AdminUser,
    db: DBSession,
    limit: int = 100,
) -> list[UserAuditLog]:
    """Recent admin user-management actions, newest first (admin only)."""
    limit = max(1, min(limit, 500))
    result = await db.execute(
        select(UserAuditLog).order_by(UserAuditLog.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


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

    # Refuse to deactivate the last active admin (lockout guard).
    if user.is_active and user.is_admin and await _active_admin_count(db, exclude_id=user.id) == 0:
        raise ValidationError("Cannot deactivate the last active admin")

    user.is_active = not user.is_active
    record_user_audit(
        db, actor=admin, action=("activate" if user.is_active else "deactivate"), target=user
    )
    await db.commit()
    await db.refresh(user)

    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    admin: AdminUser,
    db: DBSession,
) -> User:
    """Edit a user's username/email/role/active status (admin only).

    Password is NOT changed here — use the reset-password endpoint. Username and
    email are editable for local users only (LDAP identities are directory-owned).
    """
    user = await get_or_404(db, User, user_id, "User")
    fields = payload.model_fields_set
    changes: list[str] = []

    # Lockout guards.
    demoting = "is_admin" in fields and payload.is_admin is False and user.is_admin
    deactivating = "is_active" in fields and payload.is_active is False and user.is_active
    if user.is_admin and (demoting or deactivating) and await _active_admin_count(db, exclude_id=user.id) == 0:
        raise ValidationError("Cannot remove admin/active from the last active admin")
    if user_id == admin.id and deactivating:
        raise ValidationError("Cannot deactivate your own account")
    if user_id == admin.id and demoting:
        raise ValidationError("Cannot remove your own admin rights")

    # Username / email (local users only).
    if "username" in fields and payload.username != user.username:
        if user.auth_source != "local":
            raise ValidationError("Username is managed by the directory (LDAP)")
        if (
            await db.execute(
                select(User).where(User.username == payload.username, User.id != user_id)
            )
        ).scalar_one_or_none():
            raise ConflictError(f"Username '{payload.username}' is already taken")
        user.username = payload.username
        changes.append("username")
    if "email" in fields and payload.email != user.email:
        if payload.email and (
            await db.execute(
                select(User).where(User.email == payload.email, User.id != user_id)
            )
        ).scalar_one_or_none():
            raise ConflictError(f"Email '{payload.email}' is already in use")
        user.email = payload.email
        changes.append("email")

    # Role / active status.
    action = "update"
    if "is_admin" in fields and payload.is_admin != user.is_admin:
        user.is_admin = payload.is_admin
        action = "promote" if payload.is_admin else "demote"
        changes.append(action)
    if "is_active" in fields and payload.is_active != user.is_active:
        user.is_active = payload.is_active
        sub = "activate" if payload.is_active else "deactivate"
        changes.append(sub)
        if action == "update":
            action = sub

    if changes:
        record_user_audit(db, actor=admin, action=action, target=user, detail=", ".join(changes))
        await db.commit()
        await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    admin: AdminUser,
    db: DBSession,
) -> Response:
    """Delete a user (admin only). Their scenarios/agents/settings are orphaned
    (owner set to NULL), not deleted. Refuses self-deletion and last-admin."""
    if user_id == admin.id:
        raise ValidationError("Cannot delete your own account")

    user = await get_or_404(db, User, user_id, "User")
    if user.is_admin and user.is_active and await _active_admin_count(db, exclude_id=user.id) == 0:
        raise ValidationError("Cannot delete the last active admin")

    target_name = user.username  # capture before deletion for the audit row

    # Release RESTRICT foreign keys so the delete doesn't error (other refs are
    # ON DELETE SET NULL / CASCADE and clear themselves).
    await db.execute(update(Scenario).where(Scenario.user_id == user_id).values(user_id=None))
    await db.execute(
        update(TrafficAgent).where(TrafficAgent.created_by_id == user_id).values(created_by_id=None)
    )
    await db.execute(
        update(SystemSetting).where(SystemSetting.updated_by_id == user_id).values(updated_by_id=None)
    )

    record_user_audit(db, actor=admin, action="delete", target=target_name, detail=f"deleted user '{target_name}'")
    await db.delete(user)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
