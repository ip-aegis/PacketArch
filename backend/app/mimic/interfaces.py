# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Frozen seams for the Mimic persona runtime.

These interfaces are the contract that lets P0 stay one thin vertical while the
later phases (more protocols, the userland TCP stack, off-box deployment, the
Mimic Studio canvas) slot in without re-architecting:

- ``PersonaSpec`` / ``ProtocolBinding`` / ``PointBinding`` — the JSON deploy
  contract the future canvas emits and the agent consumes.
- ``Transport`` — the persona's network context (bind address; in the userland
  variant, the stack itself).
- ``Projection`` — maps a protocol's addressable data items onto the single
  source-of-truth process model; reads are live, writes feed back (closed loop).
- ``ProtocolServer`` — a bound, listening protocol responder.
- ``PersonaRuntime`` — the composition root (implemented in ``persona.py``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------- #
# Deploy contract: PersonaSpec (authored by hand in P0; by Mimic Studio later)
# --------------------------------------------------------------------------- #


@dataclass
class PointBinding:
    """One addressable protocol data item ↔ the process model.

    ``space``/``address`` are protocol-shaped (Modbus in P0: ``holding`` |
    ``input`` | ``coil`` | ``discrete``, 0-based address). A read resolves the
    bound value live; a write (when ``writable``) feeds back into the model,
    which is what makes the emulated device controllable.
    """

    space: str
    address: int
    source: str = "variable"  # "variable" | "static" | "counter"
    variable: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    static_value: int = 0
    # Write-back: a client write to this point drives a model variable.
    writable: bool = False
    write_target: str | None = None  # defaults to ``variable`` when None
    write_true_value: float = 1.0  # bit-space write of 1 → this target value
    write_false_value: float = 0.0  # bit-space write of 0 → this target value

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PointBinding":
        return cls(**{k: d[k] for k in d if k in cls.__dataclass_fields__})


@dataclass
class ProtocolBinding:
    """One protocol server this persona exposes."""

    protocol: str  # "modbus" in P0
    port: int
    unit_id: int = 1
    points: list[PointBinding] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProtocolBinding":
        return cls(
            protocol=d["protocol"],
            port=int(d["port"]),
            unit_id=int(d.get("unit_id", 1)),
            points=[PointBinding.from_dict(p) for p in d.get("points", [])],
        )


@dataclass
class PersonaSpec:
    """Everything needed to bring one device persona to life.

    Identity is derived from the shared substrate at runtime from ``template_id``
    (+ optional ``firmware_version``); ``device_id`` / ``scenario_id`` seed the
    deterministic unique serial. ``bind_ip`` is where the servers listen — a
    real per-persona IP inside a netns on-box, ``127.0.0.1`` for dev.
    """

    device_id: str
    scenario_id: str
    name: str
    template_id: str
    firmware_version: str | None = None
    bind_ip: str = "127.0.0.1"
    process_model_id: str | None = None
    protocols: list[ProtocolBinding] = field(default_factory=list)
    step_interval_ms: float = 100.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PersonaSpec":
        return cls(
            device_id=d["device_id"],
            scenario_id=d["scenario_id"],
            name=d["name"],
            template_id=d["template_id"],
            firmware_version=d.get("firmware_version"),
            bind_ip=d.get("bind_ip", "127.0.0.1"),
            process_model_id=d.get("process_model_id"),
            protocols=[ProtocolBinding.from_dict(p) for p in d.get("protocols", [])],
            step_interval_ms=float(d.get("step_interval_ms", 100.0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "scenario_id": self.scenario_id,
            "name": self.name,
            "template_id": self.template_id,
            "firmware_version": self.firmware_version,
            "bind_ip": self.bind_ip,
            "process_model_id": self.process_model_id,
            "step_interval_ms": self.step_interval_ms,
            "protocols": [
                {
                    "protocol": pb.protocol,
                    "port": pb.port,
                    "unit_id": pb.unit_id,
                    "points": [vars(p) for p in pb.points],
                }
                for pb in self.protocols
            ],
        }


# --------------------------------------------------------------------------- #
# Runtime seams
# --------------------------------------------------------------------------- #


class Transport(ABC):
    """The persona's network context.

    P0 ships ``LocalhostTransport`` (dev) and ``NamespaceKernelStack`` (on-box:
    the host-agent creates a netns with the persona's IP + vendor-tuned TTL/window
    sysctls; the server binds an ordinary kernel socket inside it). A future
    ``UserlandStack`` transport will additionally own the listening socket so
    flagship device families can defeat OS fingerprinting — which is why servers
    take their bind context from here instead of hard-coding an address.
    """

    @property
    @abstractmethod
    def bind_ip(self) -> str:
        """The address protocol servers should listen on."""

    def describe(self) -> dict[str, Any]:
        return {"kind": type(self).__name__, "bind_ip": self.bind_ip}


class Projection(ABC):
    """Maps a protocol's addressable data items onto the single-source ProcessModel.

    The model is the source of truth; a projection is a live read/write *view*.
    Two protocols projecting the same variable therefore cannot disagree — that
    cross-protocol consistency is structural, not enforced.
    """

    protocol: str = ""


class ProtocolServer(ABC):
    """A bound, listening protocol responder for one persona."""

    protocol: str = ""

    @abstractmethod
    async def start(self) -> None:
        """Bind and begin serving. Returns once listening."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop serving and release the socket."""
