# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Scenario review schemas for AI-powered scenario critique and remediation."""

from typing import Any

from pydantic import BaseModel, Field


class RemediationAction(BaseModel):
    """Machine-readable fix action that can be executed deterministically."""

    action_type: str = Field(
        ...,
        description=(
            "Action type: assign_fingerprint, repair_protocols, "
            "update_flow_timing, add_flow, assign_ips, "
            "regenerate_macs, apply_cve, remove_device, rename_device"
        ),
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters",
    )


class ReviewFinding(BaseModel):
    """A single review finding with actionable suggestion and optional auto-fix."""

    category: str = Field(
        ...,
        description="Finding category: topology, protocols, timing, realism, or security",
    )
    severity: str = Field(
        ...,
        description="Finding severity: critical, warning, suggestion, or info",
    )
    title: str = Field(..., description="Short finding title")
    description: str = Field(..., description="Detailed explanation of the issue")
    suggestion: str = Field(..., description="Actionable fix suggestion")
    affected_device_ids: list[str] = Field(
        default_factory=list,
        description="IDs of devices related to this finding",
    )
    affected_flow_ids: list[str] = Field(
        default_factory=list,
        description="IDs of flows related to this finding",
    )
    remediation: RemediationAction | None = Field(
        default=None,
        description="Machine-readable fix action. Null if manual intervention required.",
    )


class ScenarioReviewResponse(BaseModel):
    """Structured scenario review response."""

    scenario_id: str
    summary: str = Field(..., description="Narrative assessment paragraph")
    overall_score: int = Field(
        ..., ge=0, le=100, description="Quality score 0-100"
    )
    findings: list[ReviewFinding] = Field(default_factory=list)
    category_counts: dict[str, int] = Field(default_factory=dict)
    severity_counts: dict[str, int] = Field(default_factory=dict)


class RemediateRequest(BaseModel):
    """Request to execute one or more remediation actions."""

    actions: list[RemediationAction] = Field(
        ..., min_length=1, description="Remediation actions to apply"
    )


class RemediationResult(BaseModel):
    """Result of a single remediation action."""

    action_type: str
    success: bool
    message: str


class RemediateResponse(BaseModel):
    """Response from the remediate endpoint."""

    scenario_id: str
    applied: int
    failed: int
    results: list[RemediationResult]
