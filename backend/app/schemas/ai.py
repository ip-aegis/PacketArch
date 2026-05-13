# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Pydantic schemas for AI assistant API endpoints."""

from typing import Any

from pydantic import BaseModel, Field


# ========== Session Schemas ==========


class AISessionCreateRequest(BaseModel):
    """Request to create or resume an AI session for a scenario."""

    scenario_id: str = Field(..., description="Scenario UUID to associate with the session")


class AISessionResponse(BaseModel):
    """AI session response."""

    session_id: str
    created_at: str
    scenario_id: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)


# ========== Chat Schemas ==========


class AIChatRequest(BaseModel):
    """AI chat request."""

    session_id: str
    scenario_id: str
    message: str


class AIChatResponse(BaseModel):
    """AI chat response."""

    response: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    pending_actions: list[str] = Field(default_factory=list)


class AIToolDefinition(BaseModel):
    """AI tool definition."""

    name: str
    description: str
    category: str


# ========== Scenario Generation Schemas ==========


class AIScenarioGenerateRequest(BaseModel):
    """Request for AI scenario generation preview."""

    name: str = Field(..., description="Scenario name")
    vertical: str = Field(..., description="Industry vertical")
    description: str = Field(..., description="Natural language description")
    vendors: list[str] | None = Field(None, description="Preferred vendors (None = let AI decide)")
    protocols: list[str] | None = Field(None, description="Preferred protocols (None = let AI decide)")
    duration_ms: int = Field(300000, description="Scenario duration in milliseconds")
    # Device count options
    total_device_count: int | None = Field(
        None,
        description="Target total device count (AI decides the mix). Range: 5-100.",
        ge=5,
        le=100,
    )
    device_counts: dict[str, int] | None = Field(
        None,
        description="Specific counts per device type (e.g., {'plc': 5, 'hmi': 2})",
    )
    # CVE vulnerability option
    include_vulnerable_devices: bool = Field(
        False,
        description="Include CVE-vulnerable devices for security testing",
    )
    # Purdue cell-isolation default mode for the generated scenario
    cell_isolation_mode: str = Field(
        "off",
        description=(
            "Default cell isolation mode for the generated scenario: "
            "'off' (permissive), 'conduit_gated' (cells need explicit "
            "conduit), or 'strict_northbound' (no east/west cell traffic; "
            "cells only talk to L3+). Steers AI flow/conduit authoring."
        ),
    )


class AIScenarioPreviewDevice(BaseModel):
    """Device in a scenario preview."""

    device_id: str
    name: str
    device_type: str
    vendor: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    zone: str | None = None
    protocols: list[str] = Field(default_factory=list)
    # Fingerprint data for proper protocol identity lookup
    fingerprint_model: str | None = None
    # CVE vulnerability info
    cve_ids: list[str] = Field(default_factory=list)
    is_vulnerable: bool = False


class AIScenarioPreviewFlow(BaseModel):
    """Flow in a scenario preview."""

    flow_id: str
    source_device_id: str
    destination_device_id: str
    protocol: str
    description: str


class AIScenarioPreviewResponse(BaseModel):
    """Response with generated scenario preview."""

    preview_id: str
    name: str
    vertical: str
    description: str
    devices: list[AIScenarioPreviewDevice]
    flows: list[AIScenarioPreviewFlow]
    device_count: int
    flow_count: int
    protocols_used: list[str]
    vendors_used: list[str]
    zones: list[dict[str, Any]] = Field(default_factory=list)
    # AI enhancement metadata
    ai_enhanced: bool = False
    ai_features: list[str] = Field(default_factory=list)
    design_rationale: str | None = None
    # CVE vulnerability stats
    vulnerable_device_count: int = 0
    cve_ids_used: list[str] = Field(default_factory=list)


class AIScenarioCreateFromPreviewRequest(BaseModel):
    """Request to create scenario from preview."""

    preview_id: str = Field(..., description="Preview ID from generate-preview")


class AIScenarioCreateFromPreviewResponse(BaseModel):
    """Response after creating scenario from preview."""

    success: bool
    scenario_id: str
    name: str
    device_count: int
    flow_count: int


class GenerateDescriptionRequest(BaseModel):
    """Request to generate an AI description for a scenario."""

    scenario_id: str = Field(..., description="Scenario UUID")


class GenerateDescriptionResponse(BaseModel):
    """Response with generated description."""

    description: str
    scenario_name: str
    device_count: int
    flow_count: int
    protocols: list[str]
