# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Pydantic schemas for EULA / license acknowledgment."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AcknowledgmentStatus(BaseModel):
    """Whether the current user has accepted the current document version."""

    document: str
    current_version: str
    accepted: bool
    accepted_version: str | None = None
    accepted_at: datetime | None = None


class AcknowledgmentAccept(BaseModel):
    """Client payload when user clicks 'I acknowledge'.

    The version is echoed back from the client so we can detect a stale tab
    acknowledging an old version; if it mismatches the server's current, we
    still record it but the user will be re-prompted on next login.
    """

    document: str
    version: str


class AcknowledgmentRecord(BaseModel):
    """Persisted acknowledgment row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    document: str
    version: str
    accepted_at: datetime
    ip_address: str | None = None
