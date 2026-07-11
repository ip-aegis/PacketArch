# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Schemas for the multi-sensor topology ("Advanced Deployment") routes."""

from typing import Any

from pydantic import BaseModel, Field


class TopologyIssue(BaseModel):
    code: str
    message: str
    subject_id: str | None = None


class TopologySegment(BaseModel):
    span: str = Field(description="SPAN this frame appears on: 'zone:<zone_id>' or 'core'")
    src_mac: str
    dst_mac: str
    vlan: int | None = Field(default=None, description="802.1Q tag; None = untagged")
    ttl_delta: int = Field(description="IP TTL adjustment vs the generated packet (0 or -1)")


class TopologyFlowPlan(BaseModel):
    kind: str = Field(description="'intra' or 'cross'")
    source_zone: str
    target_zone: str
    segments_forward: list[TopologySegment]
    segments_reverse: list[TopologySegment]


class TopologyPreviewResponse(BaseModel):
    """Derived L1 topology + per-flow segment plans. Pure preview, no side effects."""

    valid: bool
    errors: list[TopologyIssue]
    warnings: list[TopologyIssue]
    switches: dict[str, dict[str, Any]] = Field(description="zone_id -> derived IE3500 switch")
    core: dict[str, Any] | None = Field(default=None, description="Derived IE9320 core with per-zone SVIs")
    links: list[dict[str, Any]] = Field(description="L1 links: device->switch (access), switch->core (trunk)")
    spans: list[dict[str, Any]] = Field(description="Capture SPANs: one per zone + core")
    flow_plans: dict[str, TopologyFlowPlan] = Field(description="flow_id -> segment plan")
