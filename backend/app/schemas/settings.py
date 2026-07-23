# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Settings-related schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SettingBase(BaseModel):
    """Base setting schema."""

    key: str
    value: str | None = None
    is_secret: bool = False
    category: str | None = None
    description: str | None = None


class SettingUpdate(BaseModel):
    """Schema for updating a setting."""

    value: str | None = None


class SettingResponse(SettingBase):
    """Schema for setting response."""

    id: uuid.UUID
    updated_at: datetime
    # Value is masked if is_secret is True
    value: str | None = None

    model_config = {"from_attributes": True}


class SettingsResponse(BaseModel):
    """Schema for grouped settings response."""

    api_tokens: list[SettingResponse] = []
    network: list[SettingResponse] = []
    system: list[SettingResponse] = []
    ai: list[SettingResponse] = []


class SettingsBulkUpdate(BaseModel):
    """Schema for bulk updating settings."""

    settings: dict[str, str | None] = Field(
        ...,
        description="Dictionary of setting keys to values",
    )
