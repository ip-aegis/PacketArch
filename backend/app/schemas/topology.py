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
    endpoint_index: dict[str, Any] = Field(default_factory=dict, description="ip/mac -> zone routing index")


class TopologyPreflightResponse(BaseModel):
    """Non-destructive pre-deploy summary for the Advanced Deployment wizard."""

    scenario_id: str
    sensor_count: int = Field(description="Labs that would be provisioned (N zones + core)")
    ram_estimate_gb: float = Field(description="Estimated sensor ring-buffer RAM (N+1 x 1.26 GB)")
    spans: list[str]
    switches: int
    has_core: bool
    flow_plans: int


class TopologyMember(BaseModel):
    span_id: str
    role: str = Field(description="'zone' or 'core'")
    lab_id: str
    slug: str | None = None
    agent_id: str | None = None
    agent_token: str | None = Field(default=None, description="Shown once, at provisioning")
    gen_if: str | None = Field(default=None, description="pa-gen veth — the SPAN's injection interface")
    sensor_serial: str | None = None


class TopologyProvisionResponse(BaseModel):
    """Result of provisioning N+1 sensor labs for a scenario."""

    scenario_id: str
    sensor_count: int
    ram_estimate_gb: float
    members: list[TopologyMember]
    span_interface_map: dict[str, str] = Field(description="span_id -> injection interface")


class TopologyDeploymentResponse(BaseModel):
    """Live status of a topology deployment's member labs."""

    scenario_id: str
    sensor_count: int
    members: list[dict[str, Any]]
    torn_down: list[dict[str, Any]] | None = None
