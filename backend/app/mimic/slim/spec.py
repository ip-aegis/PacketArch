# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Resolved persona spec for the slim runtime.

Unlike the on-box ``PersonaSpec`` (which resolves identity from the substrate at
start), the slim spec is fully RESOLVED by the backend at deploy time — the
protocol identity dicts (e.g. ``modbus_identity``) are baked in, so the node needs
no device_templates / fingerprint_applicator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PointBinding:
    space: str = "holding"
    address: int = 0
    source: str = "variable"
    variable: str | None = None
    name: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    static_value: int = 0
    writable: bool = False
    write_target: str | None = None
    write_true_value: float = 1.0
    write_false_value: float = 0.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PointBinding":
        return cls(**{k: d[k] for k in d if k in cls.__dataclass_fields__})


@dataclass
class ProtocolBinding:
    protocol: str = "modbus"
    port: int = 502
    unit_id: int = 1
    identity: dict[str, Any] = field(default_factory=dict)  # resolved protocol identity
    points: list[PointBinding] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProtocolBinding":
        return cls(
            protocol=d.get("protocol", "modbus"),
            port=int(d.get("port", 502)),
            unit_id=int(d.get("unit_id", 1)),
            identity=d.get("identity", {}) or {},
            points=[PointBinding.from_dict(p) for p in d.get("points", [])],
        )


@dataclass
class ClientBinding:
    """One peer this persona actively polls (the HMI / active-master side). The
    target_ip is resolved (baked) at deploy time from the cell's device directory."""

    protocol: str = "modbus"
    target_ip: str = ""
    port: int = 502
    unit_id: int = 1
    interval_s: float = 3.0
    read_holding: int = 4
    read_coils: int = 1
    identity: bool = True

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ClientBinding":
        return cls(**{k: d[k] for k in d if k in cls.__dataclass_fields__})


@dataclass
class ResolvedPersonaSpec:
    name: str
    bind_ip: str = "0.0.0.0"
    firmware_version: str = ""
    process_model_id: str | None = None
    protocols: list[ProtocolBinding] = field(default_factory=list)
    clients: list[ClientBinding] = field(default_factory=list)
    step_interval_ms: float = 100.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ResolvedPersonaSpec":
        return cls(
            name=d["name"],
            bind_ip=d.get("bind_ip", "0.0.0.0"),
            firmware_version=d.get("firmware_version", "") or "",
            process_model_id=d.get("process_model_id"),
            protocols=[ProtocolBinding.from_dict(p) for p in d.get("protocols", [])],
            clients=[ClientBinding.from_dict(c) for c in d.get("clients", [])],
            step_interval_ms=float(d.get("step_interval_ms", 100.0)),
        )
