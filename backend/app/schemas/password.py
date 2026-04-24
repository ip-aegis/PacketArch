# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Password management schemas."""

from pydantic import BaseModel, Field


class ChangePasswordRequest(BaseModel):
    """Request schema for changing own password."""

    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (minimum 8 characters)",
    )


class ResetPasswordRequest(BaseModel):
    """Request schema for admin password reset."""

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (minimum 8 characters)",
    )


class PasswordChangeResponse(BaseModel):
    """Response schema for password operations."""

    success: bool
    message: str
