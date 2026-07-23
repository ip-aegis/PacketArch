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
    """Schema for grouped settings response.

    One field per `SystemSetting.category`. ``get_all_settings`` groups by
    matching a setting's category against these field NAMES, so adding a
    category is a one-line change here and needs no route edit — and, more to
    the point, a category with no field is reported rather than dropped on the
    floor. The route previously grouped with a hardcoded if/elif chain and
    returned 4 of the 37 settings the app ships.
    """

    # Categories in DEFAULT_SETTINGS.
    ai: list[SettingResponse] = []
    cml: list[SettingResponse] = []
    cyber_vision: list[SettingResponse] = []
    ldap: list[SettingResponse] = []
    setup: list[SettingResponse] = []
    system: list[SettingResponse] = []

    # No longer in DEFAULT_SETTINGS, kept so existing clients keep their keys.
    api_tokens: list[SettingResponse] = []
    network: list[SettingResponse] = []


class SettingsBulkUpdate(BaseModel):
    """Schema for bulk updating settings."""

    settings: dict[str, str | None] = Field(
        ...,
        description="Dictionary of setting keys to values",
    )
