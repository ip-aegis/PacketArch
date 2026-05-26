# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""User-related schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""

    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr | None = None


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    username: str | None = Field(None, min_length=3, max_length=255)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=100)
    is_active: bool | None = None
    is_admin: bool | None = None


class UserResponse(UserBase):
    """Schema for user response."""

    id: uuid.UUID
    is_active: bool
    is_admin: bool
    auth_source: str
    created_at: datetime
    last_login: datetime | None
    welcome_seen: bool

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str
    password: str


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Body schema for /auth/refresh — token rides in the JSON body, not
    a query string, so it doesn't end up in nginx access logs."""

    refresh_token: str


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""

    sub: str  # User ID
    exp: datetime
    type: str  # "access" or "refresh"
