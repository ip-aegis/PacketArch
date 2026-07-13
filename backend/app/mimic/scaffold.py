# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Author a Mimic cell from a simple device graph (the Studio canvas contract).

The Mimic Studio canvas authors a *cell*: device nodes (template + protocol +
process model) and poll-relationship edges. This module turns that graph into full
``PersonaSpec``s — scaffolding a sensible default data model (point map) for each
device from its process model, and resolving each edge into a client poll binding —
so the point-level detail lives server-side (one source of truth), not in the UI.

Scaffolding rules (v1): a server device exposes its process model's public
variables as read points, plus a writable *setpoint* point where the protocol
supports numeric write-back (Modbus / IEC-104). A poll edge adds a Modbus client
loop from the source device to the target's server.
"""

from __future__ import annotations

from .deploy import deploy_cell
from .interfaces import ClientBinding, PersonaSpec, PointBinding, ProtocolBinding
from .process_library import build_process_model

# Default server port per protocol.
_PORTS = {"modbus": 502, "opcua": 4840, "bacnet": 47808, "iec104": 2404}
_NUMERIC_WRITE = {"modbus", "iec104"}  # protocols whose write-back handles a numeric setpoint


def _public_vars(process_model_id: str | None) -> tuple[list[str], bool]:
    """Return (read-variable names, has_setpoint) for a process model."""
    if not process_model_id:
        return [], False
    model = build_process_model(process_model_id)
    names = [n for n in model.variables if not n.startswith("_") and n != "clock"]
    has_setpoint = "setpoint" in names
    reads = [n for n in names if n != "setpoint"]
    return reads, has_setpoint


def _scaffold_points(protocol: str, process_model_id: str | None) -> list[PointBinding]:
    reads, has_setpoint = _public_vars(process_model_id)
    points: list[PointBinding] = []
    if protocol == "modbus":
        for i, var in enumerate(reads):
            points.append(PointBinding(space="holding", address=i, source="variable", variable=var, scale=100.0))
        if has_setpoint:
            points.append(PointBinding(space="holding", address=len(reads), source="variable",
                                       variable="setpoint", scale=100.0, writable=True, write_target="setpoint"))
    elif protocol in ("opcua", "bacnet"):
        for var in reads:
            points.append(PointBinding(space="", address=0, source="variable", variable=var, name=var.title()))
        if has_setpoint:  # numeric write-back unsupported on these servers yet — read-only
            points.append(PointBinding(space="", address=0, source="variable", variable="setpoint", name="Setpoint"))
    elif protocol == "iec104":
        for i, var in enumerate(reads):
            points.append(PointBinding(space="", address=11 + i, source="variable", variable=var))
        if has_setpoint:
            points.append(PointBinding(space="", address=21, source="variable", variable="setpoint",
                                       writable=True, write_target="setpoint"))
    return points


def scaffold_persona(*, key: str, name: str, template_id: str, protocol: str | None,
                     process_model_id: str | None) -> PersonaSpec:
    """Scaffold one device persona. ``protocol`` None → a client-only device (an HMI);
    poll bindings are added later from the graph edges."""
    spec = PersonaSpec(
        device_id=key, scenario_id="mimic", name=name,
        template_id=template_id, process_model_id=process_model_id,
    )
    if protocol:
        spec.protocols = [ProtocolBinding(
            protocol=protocol, port=_PORTS.get(protocol, 502),
            points=_scaffold_points(protocol, process_model_id),
        )]
    return spec


def author_cell(*, lab_slug: str, gen_if: str, cell_name: str,
                devices: list[dict], relationships: list[dict],
                persona_image: str | None = None) -> dict:
    """Build personas from an authored device graph and deploy the cell.

    ``devices``: [{key, name, template_id, protocol|None, process_model_id}].
    ``relationships``: [{source, target}] — source polls target over its protocol.
    """
    by_key: dict[str, PersonaSpec] = {}
    proto_by_key: dict[str, str | None] = {}
    for d in devices:
        proto = d.get("protocol")
        by_key[d["key"]] = scaffold_persona(
            key=d["key"], name=d.get("name", d["key"]), template_id=d["template_id"],
            protocol=proto, process_model_id=d.get("process_model_id"),
        )
        proto_by_key[d["key"]] = proto

    for rel in relationships:
        src, dst = rel.get("source"), rel.get("target")
        if src not in by_key or dst not in by_key:
            continue
        target_proto = proto_by_key.get(dst) or "modbus"
        by_key[src].clients.append(ClientBinding(
            protocol=target_proto, target_device=dst, port=_PORTS.get(target_proto, 502),
        ))

    return deploy_cell(
        lab_slug=lab_slug, gen_if=gen_if, cell_name=cell_name,
        personas=list(by_key.values()), persona_image=persona_image,
    )
