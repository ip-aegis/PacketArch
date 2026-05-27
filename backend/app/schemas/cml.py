# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cisco Modeling Labs (CML) schemas for API validation.

Mirrors the Cyber Vision schema style: settings (secret masked), test/status,
and the deploy/undeploy workflow used to auto-provision a remote traffic agent
node inside a CML lab.
"""

from pydantic import BaseModel, Field


# --- Settings ---------------------------------------------------------------

class CMLSettingsUpdate(BaseModel):
    """Schema for updating CML settings."""

    cml_url: str | None = Field(default=None, description="CML base URL (e.g., https://10.10.20.230)")
    cml_username: str | None = Field(default=None, description="CML username")
    cml_password: str | None = Field(default=None, description="CML password (leave blank to keep existing)")
    cml_verify_ssl: bool | None = Field(default=None, description="Verify SSL certificates")
    cml_packetarch_server_url: str | None = Field(
        default=None,
        description="URL the deployed agent phones home to (reachable from inside the lab). Blank = use site FQDN.",
    )


class CMLSettingsResponse(BaseModel):
    """Schema for CML settings response (password masked)."""

    cml_url: str
    cml_username: str
    cml_password_set: bool
    cml_verify_ssl: bool
    cml_packetarch_server_url: str


# --- Connection test / status ----------------------------------------------

class CMLTestConnectionRequest(BaseModel):
    """Schema for testing a CML connection with provided credentials."""

    url: str = Field(..., description="CML URL")
    username: str = Field(..., description="CML username")
    password: str = Field(..., description="CML password")
    verify_ssl: bool = Field(default=False, description="Verify SSL certificates")


class CMLTestConnectionResponse(BaseModel):
    """Schema for CML connection test result."""

    success: bool
    message: str
    version: str | None = None


class CMLConnectionStatusResponse(BaseModel):
    """Schema for CML connection status."""

    connected: bool
    message: str
    version: str | None = None


# --- Labs / nodes (pickers) -------------------------------------------------

class CMLLabResponse(BaseModel):
    """A CML lab summary."""

    id: str
    title: str
    state: str
    node_count: int
    owner: str | None = None


class CMLLabListResponse(BaseModel):
    """List of CML labs."""

    items: list[CMLLabResponse]


class CMLInterfaceResponse(BaseModel):
    """An interface on a CML node (for the port picker)."""

    id: str
    label: str
    slot: int | None = None
    is_connected: bool = False


class CMLNodeResponse(BaseModel):
    """A node inside a CML lab (for the element picker)."""

    id: str
    label: str
    node_definition: str
    state: str
    is_infrastructure: bool = Field(
        default=False,
        description="True for external_connector / unmanaged_switch (not valid data-attach targets)",
    )
    interfaces: list[CMLInterfaceResponse] = Field(default_factory=list)


class CMLNodeListResponse(BaseModel):
    """List of nodes in a lab."""

    items: list[CMLNodeResponse]


# --- Deploy / undeploy ------------------------------------------------------

class CMLDataAttachment(BaseModel):
    """Where to wire the agent's data interface (ens3) inside the lab."""

    target_node_id: str = Field(..., description="ID of the lab node to attach to")
    slot: int = Field(..., ge=0, description="Interface slot on the target node")


class CMLDeployRequest(BaseModel):
    """Schema for deploying an agent into a CML lab."""

    lab_id: str = Field(..., description="Target CML lab ID")
    agent_name: str = Field(..., min_length=1, max_length=255, description="Name for the new PacketArch agent")
    data_attachment: CMLDataAttachment | None = Field(
        default=None,
        description=(
            "Where to wire the data interface. None = just drop the node into the lab with NO "
            "links at all (wire management + data manually in CML)."
        ),
    )
    start_node: bool = Field(
        default=False,
        description="Start (boot) the node after deploy. Default false — the node is created stopped.",
    )
    cpus: int = Field(default=2, ge=1, le=8, description="vCPUs for the agent node")
    ram_mb: int = Field(default=3072, ge=1024, le=16384, description="RAM (MB) for the agent node")


class CMLDeployResponse(BaseModel):
    """Result of a deploy operation."""

    success: bool
    message: str
    agent_id: str | None = None
    agent_token: str | None = Field(default=None, description="Agent token (shown only once)")
    lab_id: str
    node_id: str | None = None
    node_label: str | None = None
    data_wired: bool = False
    mgmt_wired: bool = False
    started: bool = False
    warnings: list[str] = Field(default_factory=list)


class CMLUndeployRequest(BaseModel):
    """Schema for tearing down a CML-deployed agent."""

    agent_id: str = Field(..., description="PacketArch agent ID to undeploy")
    remove_cml_node: bool = Field(default=True, description="Stop and delete the CML node")
    deactivate_agent: bool = Field(default=True, description="Deactivate the PacketArch agent record")


class CMLUndeployResponse(BaseModel):
    """Result of an undeploy operation."""

    success: bool
    message: str
    cml_node_removed: bool = False
    agent_deactivated: bool = False


class CMLLabBuildRequest(BaseModel):
    """Schema for building a self-contained agent + CV-sensor lab."""

    lab_name: str = Field(..., min_length=1, max_length=128, description="Name for the new lab")
    agent_name: str = Field(..., min_length=1, max_length=255, description="Name for the PacketArch agent")
    sensor_compose: str = Field(
        ...,
        description="The full docker-compose YAML CV generates for a docker sensor (contains image, SERIAL_NUMBER, PROVISIONING_TOKEN)",
    )
    sensor_serial: str | None = Field(default=None, description="Sensor serial; default parsed from the compose")
    start_lab: bool = Field(default=False, description="Start the lab after building (default false)")
    agent_cpus: int = Field(default=2, ge=1, le=8)
    agent_ram_mb: int = Field(default=3072, ge=1024, le=16384)
    sensor_cpus: int = Field(default=2, ge=1, le=8)
    sensor_ram_mb: int = Field(default=4096, ge=1024, le=16384)


class CMLLabBuildResponse(BaseModel):
    """Result of a build-lab operation."""

    success: bool
    message: str
    lab_id: str | None = None
    agent_id: str | None = None
    agent_token: str | None = Field(default=None, description="Agent token (shown only once)")
    agent_node_id: str | None = None
    switch_node_id: str | None = None
    sensor_node_id: str | None = None
    sensor_serial: str | None = None
    started: bool = False
    warnings: list[str] = Field(default_factory=list)


class CMLTeardownLabRequest(BaseModel):
    """Schema for tearing down a PacketArch-built lab."""

    lab_id: str = Field(..., description="CML lab to stop, wipe, and delete")
    agent_id: str | None = Field(default=None, description="Associated agent to deactivate/remove, if any")


class CMLTeardownLabResponse(BaseModel):
    """Result of a teardown-lab operation."""

    success: bool
    message: str


class CMLDeploymentItem(BaseModel):
    """A PacketArch agent that was deployed into CML."""

    agent_id: str
    agent_name: str
    status: str
    is_active: bool
    cml_lab_id: str | None = None
    cml_node_id: str | None = None
    cml_node_label: str | None = None


class CMLDeploymentListResponse(BaseModel):
    """List of CML-backed deployments."""

    items: list[CMLDeploymentItem]
