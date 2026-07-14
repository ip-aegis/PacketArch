# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Request/response schemas for the Mimic device-emulation API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MimicStatusResponse(BaseModel):
    enabled: bool
    host_agent_available: bool
    message: str


class PointInput(BaseModel):
    space: str  # holding | input | coil | discrete
    address: int
    source: str = "variable"  # variable | static | counter | actuator
    variable: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    static_value: int = 0
    writable: bool = False
    write_target: str | None = None
    write_true_value: float = 1.0
    write_false_value: float = 0.0


class ProtocolInput(BaseModel):
    protocol: str = "modbus"
    port: int = 502
    unit_id: int = 1
    points: list[PointInput] = Field(default_factory=list)


class ClientInput(BaseModel):
    protocol: str = "modbus"
    target_device: str | None = None  # peer device_id, resolved to an IP at deploy
    port: int = 502
    unit_id: int = 1
    interval_s: float = 3.0
    read_holding: int = 4
    read_coils: int = 1
    identity: bool = True


class PersonaInput(BaseModel):
    device_id: str
    scenario_id: str
    name: str
    template_id: str
    firmware_version: str | None = None
    process_model_id: str | None = None
    protocols: list[ProtocolInput] = Field(default_factory=list)
    clients: list[ClientInput] = Field(default_factory=list)
    step_interval_ms: float = 100.0


class DeployCellRequest(BaseModel):
    lab_slug: str = Field(..., description="Existing Local Lab whose SPAN to attach to")
    cell_name: str = "Mimic Cell"
    personas: list[PersonaInput] = Field(..., min_length=1)


class DeployCellResponse(BaseModel):
    cell_slug: str
    request_id: str
    containers: list[str]


class AuthorDeviceInput(BaseModel):
    key: str
    name: str
    template_id: str
    protocol: str | None = None  # server protocol; None = client-only device
    process_model_id: str | None = None


class AuthorRelationship(BaseModel):
    source: str  # device key that polls
    target: str  # device key being polled


class AuthorCellRequest(BaseModel):
    lab_slug: str = Field(..., description="Existing Local Lab whose SPAN to attach to")
    cell_name: str = "Mimic Cell"
    devices: list[AuthorDeviceInput] = Field(..., min_length=1)
    relationships: list[AuthorRelationship] = Field(default_factory=list)


class CellItem(BaseModel):
    cell_slug: str
    name: str
    lab_slug: str | None = None
    devices: list[str] = Field(default_factory=list)
    state: str = "unknown"
    message: str = ""


class CellListResponse(BaseModel):
    items: list[CellItem] = Field(default_factory=list)


class TeardownResponse(BaseModel):
    request_id: str


class CmlMimicStatusResponse(BaseModel):
    """Whether the off-box (CML) Mimic path is usable here."""
    cml_connected: bool
    cv_configured: bool
    message: str = ""


class CmlDeployRequest(BaseModel):
    cell_name: str = "Mimic Cell"
    devices: list[AuthorDeviceInput] = Field(..., min_length=1)
    relationships: list[AuthorRelationship] = Field(default_factory=list)
    with_sensor: bool = False  # add an IOSvL2 SPAN + auto-provisioned CV sensor node


class CmlPersonaResult(BaseModel):
    name: str
    data_ip: str | None = None
    node_id: str | None = None


class CmlDeployResponse(BaseModel):
    lab_id: str
    lab_title: str
    personas: list[CmlPersonaResult] = Field(default_factory=list)
    sensor_serial: str | None = None
    message: str = ""


class CmlLabItem(BaseModel):
    lab_id: str
    title: str
    state: str = "UNKNOWN"
    node_count: int = 0


class CmlLabListResponse(BaseModel):
    items: list[CmlLabItem] = Field(default_factory=list)


class CmlTeardownResponse(BaseModel):
    lab_id: str
    message: str = ""


class TemplateItem(BaseModel):
    id: str
    vendor: str
    model_name: str
    device_type: str
    protocols: list[str] = Field(default_factory=list)
    # Mimic certification (see app.mimic.certification):
    role_class: str = "responder"  # "responder" (server persona) | "client"
    client_capable: bool = False
    # deploy target -> the server protocols this device is certified to emulate there
    server_protocols: dict[str, list[str]] = Field(default_factory=dict)


class TemplateListResponse(BaseModel):
    items: list[TemplateItem] = Field(default_factory=list)


class ProcessModelListResponse(BaseModel):
    models: list[str] = Field(default_factory=list)


class PresetItem(BaseModel):
    key: str
    name: str
    description: str
    personas: list[PersonaInput] = Field(default_factory=list)


class PresetListResponse(BaseModel):
    items: list[PresetItem] = Field(default_factory=list)
