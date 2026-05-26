# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Pydantic models for the portable scenario format.

These models mirror `schemas/packetarch-scenario.v1.json` at the repo root
and provide server-side validation. The JSON Schema is the public contract
shared with external authors / AI tools; these Pydantic classes enforce it
on import.

If you change one, change the other.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PORTABLE_FORMAT_VERSION = "1.0"


# Legal protocol identifiers for both Device.protocols and Flow.protocol.
# Mirrors the `Protocol` enum in schemas/packetarch-scenario.v1.json.
# Keep this enum strict: PacketArch's traffic engines only emit these.
# IT protocols (https, rdp, ssh, wmi, icmp, lldp, cdp) belong in
# `description`, not here — a strict enum surfaces them to the author at
# schema-validation time with a precise field path instead of silently
# being stripped by `auto_repair_protocols` after import.
PortableProtocol = Literal[
    # Canonical
    "modbus_tcp",
    "ethernet_ip",
    "profinet",
    "s7comm",
    "bacnet",
    "snmp",
    "opc_ua",
    "dnp3",
    "iec104",
    # Aliases — resolved server-side by `resolve_protocol()`
    "modbus",
    "enip",
    "bacnet_ip",
    "s7comm_plus",
    "profisafe",
    "cip_safety",
]


class PortableErrorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exception_rate: float = Field(0.001, ge=0, le=1)
    timeout_rate: float = Field(0.0005, ge=0, le=1)
    retry_behavior: bool = True
    max_retries: int = Field(3, ge=0)


class PortableZone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=r"^[a-z0-9_]+$")
    name: str = Field(..., min_length=1)
    purdue_level: float = Field(..., ge=0, le=5)
    vlan: int | None = Field(None, ge=1, le=4094)
    security_level: Literal["minimal", "standard", "high", "critical"] = "standard"
    subnet: str | None = Field(None, pattern=r"^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$")


class PortableDevice(BaseModel):
    """Device spec. `vendor` and `fingerprint_model` are both optional.

    The importer resolves missing fields from the local catalog using
    `type` + `protocols` + scenario `preferences`. See SCENARIO_SPEC.md
    for the three authoring modes (capability / vendor-pinned / fully
    specified).
    """

    model_config = ConfigDict(extra="forbid")

    type: str
    vendor: str | None = None
    fingerprint_model: str | None = None
    count: int = Field(1, ge=1)
    zone: str
    name_pattern: str | None = None
    protocols: list[PortableProtocol] = Field(..., min_length=1)
    role: str | None = None
    architectural_role: str | None = None
    cve_ids: list[str] | None = None
    error_config: PortableErrorConfig | None = None


class PortableFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol: PortableProtocol
    pattern: Literal["poll", "cyclic_io", "subscription", "safety", "event"]
    # Floor is 1 ms so EtherNet/IP / PROFINET cyclic_io down to the
    # protocol's native RPI minimum is accepted. The spec documents the
    # realistic ranges per protocol — see SCENARIO_SPEC.md Rule 8.
    interval_ms: int = Field(..., ge=1)
    source_types: list[str] = Field(..., min_length=1)
    target_types: list[str] = Field(..., min_length=1)
    source_zones: list[str] | None = None
    target_zones: list[str] | None = None
    jitter_ms: int = Field(0, ge=0)
    jitter_type: Literal["uniform", "gaussian", "exponential"] = "uniform"


class PortableConduit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=r"^[a-z0-9_]+$")
    name: str | None = None
    source_zone: str
    target_zone: str
    direction: Literal["bidirectional", "a_to_b", "b_to_a"] = "bidirectional"
    allowed_protocols: list[PortableProtocol] = Field(default_factory=list)
    security_level: Literal["minimal", "standard", "high", "critical"] = "standard"
    description: str | None = None


class PortableAnomalies(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timing: list[str] = Field(default_factory=list)
    protocol: list[str] = Field(default_factory=list)
    sequence: list[str] = Field(default_factory=list)
    payload: list[str] = Field(default_factory=list)
    network: list[str] = Field(default_factory=list)
    security: list[str] = Field(default_factory=list)


class PortableExternalComms(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enable_c2: bool = False
    c2_protocol: Literal["http", "https", "dns"] = "http"
    c2_pattern: str = "jittered_1m"
    enable_exfil: bool = False
    exfil_protocol: Literal["http", "dns"] = "http"
    exfil_data_size: int = Field(1024, ge=1)
    enable_exploits: bool = False
    exploit_patterns: list[str] = Field(default_factory=list)
    enable_recon: bool = False
    scan_ot_ports: bool = True
    target_device_types: list[str] = Field(default_factory=lambda: ["hmi", "plc"])


class PortablePhase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    start_time_ms: int = Field(..., ge=0)
    duration_ms: int = Field(..., ge=1)


class PortableModes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clean_demo_mode: bool = False
    broadcast_traffic_enabled: bool = True
    cell_isolation_mode: Literal["off", "soft", "hard"] = "off"


class PortablePreferences(BaseModel):
    """Resolver preferences for capability / vendor-pinned devices."""

    model_config = ConfigDict(extra="forbid")

    vendor_strategy: Literal["preferred", "diverse", "any"] = "preferred"
    preferred_vendors: list[str] = Field(default_factory=list)
    exclude_vendors: list[str] = Field(default_factory=list)
    deterministic_seed: str | None = None


VERTICAL_VALUES = (
    "manufacturing",
    "water_wastewater",
    "energy_power",
    "oil_gas",
    "transportation",
    "building_automation",
    "distribution_logistics",
    "testing",
)


class PortableScenario(BaseModel):
    """A portable scenario document.

    Authors produce this; the importer translates it into the internal
    scenario `definition` shape and persists it.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    format_version: Literal["1.0"] = PORTABLE_FORMAT_VERSION
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    vertical: str | None = None
    total_duration_ms: int = Field(60000, ge=1000, le=86400000)

    zones: list[PortableZone] = Field(..., min_length=1)
    devices: list[PortableDevice] = Field(..., min_length=1)
    flows: list[PortableFlow] = Field(..., min_length=1)
    conduits: list[PortableConduit] = Field(default_factory=list)

    anomalies: PortableAnomalies | None = None
    external_comms: PortableExternalComms | None = None
    phases: list[PortablePhase] = Field(default_factory=list)
    modes: PortableModes | None = None
    preferences: PortablePreferences | None = None

    # Allow $schema metadata key without forbid-extra rejection.
    schema_ref: str | None = Field(None, alias="$schema")


class PortableValidateResponse(BaseModel):
    """Response from POST /scenarios/validate/portable."""

    valid: bool
    schema_errors: list[dict] = Field(default_factory=list)
    readiness: dict | None = None
    expanded_summary: dict | None = None
