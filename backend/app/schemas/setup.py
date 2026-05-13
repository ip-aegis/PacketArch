# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Schemas for the first-run setup wizard."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class SetupStatusResponse(BaseModel):
    """Public payload returned by GET /setup/status.

    The frontend's SetupGate consumes this once at app boot to decide between
    rendering the wizard or the normal app shell. Read by unauthenticated
    clients — must not leak anything sensitive.
    """

    setup_complete: bool
    build_variant: Literal["full", "pcap-only"]
    ai_supported: bool
    live_traffic_supported: bool


class AdminAccount(BaseModel):
    """Step 1 of the wizard: admin credentials."""

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    email: EmailStr | None = None


class SiteIdentity(BaseModel):
    """Step 2: site display + addressing metadata."""

    name: str = Field(min_length=1, max_length=128)
    fqdn: str = Field(min_length=1, max_length=255)
    timezone: str = Field(min_length=1, max_length=64)


class AICapability(BaseModel):
    """Step 3 partial: AI provider configuration."""

    enabled: bool = False
    # Optional API key. Encrypted at rest via app.core.encryption.encrypt_value.
    anthropic_api_key: str | None = None


class CyberVisionCapability(BaseModel):
    """Step 3 partial: optional Cyber Vision integration."""

    enabled: bool = False
    url: str | None = None
    api_token: str | None = None
    verify_ssl: bool = False


class SetupCompleteRequest(BaseModel):
    """Body for POST /setup/complete."""

    admin: AdminAccount
    site: SiteIdentity
    ai: AICapability = AICapability()
    cyber_vision: CyberVisionCapability = CyberVisionCapability()
    # Operator must check the GPL acknowledgment box on step 4.
    accept_acknowledgment: bool = False


class SetupCompleteResponse(BaseModel):
    """Returned on successful wizard completion. Includes auto-login tokens."""

    setup_complete: bool
    access_token: str
    refresh_token: str


class TestAIKeyRequest(BaseModel):
    """Body for POST /setup/test-ai-key."""

    anthropic_api_key: str = Field(min_length=1, max_length=512)


class TestAIKeyResponse(BaseModel):
    """Result of validating an Anthropic key against api.anthropic.com."""

    valid: bool
    error: str | None = None
