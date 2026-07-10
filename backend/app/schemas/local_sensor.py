# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Local sensor lab schemas.

Mirrors the CML build-lab schema style (schemas/cml.py) but for an on-box,
app-managed (agent + CV sensor + virtual SPAN) lab provisioned by the
privileged host-agent.
"""

from pydantic import BaseModel, Field


# --- host capability status -------------------------------------------------

class LocalHostStatusResponse(BaseModel):
    """Whether the host-agent capability is present and reachable."""

    available: bool = Field(..., description="Shared state volume mounted (host-agent wired)")
    host_agent_seen: bool = Field(..., description="Host-agent has initialized its state dirs")
    message: str


# --- build ------------------------------------------------------------------

class LocalLabBuildRequest(BaseModel):
    """Schema for building a local agent + CV-sensor lab on the host.

    The CV sensor is auto-provisioned via the Cyber Vision API (Settings >
    Cyber Vision must be configured) — no compose paste required.
    """

    name: str = Field(..., min_length=1, max_length=128, description="Name for the new local lab")
    agent_name: str | None = Field(
        default=None,
        max_length=255,
        description="Name for the PacketArch agent; default derived from the lab slug",
    )


class LocalLabBuildResponse(BaseModel):
    """Result of a build request (token shown once, like CML)."""

    success: bool
    message: str
    lab_id: str | None = None
    slug: str | None = None
    agent_id: str | None = None
    agent_token: str | None = Field(default=None, description="Agent token (shown only once)")
    sensor_serial: str | None = None
    state: str = "pending"
    warnings: list[str] = Field(default_factory=list)


# --- listing / detail -------------------------------------------------------

class LocalLabItem(BaseModel):
    """A local sensor lab with its live status."""

    lab_id: str
    name: str
    slug: str
    state: str
    status_detail: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    agent_status: str | None = None
    sensor_serial: str | None = None
    gen_if: str
    mon_if: str
    # Live fields merged from the host-agent status file (best-effort).
    stage: str | None = None
    percent: int | None = None
    resources: dict | None = None


class LocalLabListResponse(BaseModel):
    items: list[LocalLabItem]


class LocalLabTeardownResponse(BaseModel):
    success: bool
    message: str
