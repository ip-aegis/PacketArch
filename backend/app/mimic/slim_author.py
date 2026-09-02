# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Author an OFF-BOX (CML) Mimic cell from the Studio device graph.

The Studio canvas emits the same device graph the on-box path uses (devices +
poll relationships). This module turns it into fully-RESOLVED slim persona specs
for off-box deployment: it reuses ``scaffold`` to build the point maps + client
bindings, assigns each persona a static OT data-segment IP, bakes the per-protocol
identity at author time, and rewrites each poll edge to target the peer's data IP.

The result feeds ``slim_deploy.deploy_slim_cell`` / ``slim_sensor.deploy_cell_with_sensor``.
"""

from __future__ import annotations

import dataclasses

from .interfaces import ClientBinding, PersonaSpec
from .scaffold import _PORTS, scaffold_persona
from .slim_deploy import resolve_persona

# Isolated OT data segment for an off-box cell: PLC .10, next .20, ...
_DATA_NET = "10.99.0"


def _data_ip(index: int) -> str:
    return f"{_DATA_NET}.{10 + index * 10}"


def _to_slim_spec(persona: PersonaSpec, data_ip_by_key: dict[str, str]) -> dict:
    """Convert one on-box PersonaSpec into a resolved slim spec dict."""
    server = persona.protocols[0] if persona.protocols else None
    if server is not None:
        spec = resolve_persona(
            name=persona.name, template_id=persona.template_id,
            firmware_version=persona.firmware_version, process_model_id=persona.process_model_id,
            protocol=server.protocol, port=server.port, unit_id=server.unit_id,
            points=[dataclasses.asdict(pt) for pt in server.points],
        )
    else:  # client-only persona (an HMI) — no server to bind
        spec = {"name": persona.name, "bind_ip": "0.0.0.0", "firmware_version": "",
                "process_model_id": persona.process_model_id, "protocols": []}
    spec["data_ip"] = data_ip_by_key[persona.device_id]
    spec["clients"] = [
        {"protocol": c.protocol, "target_ip": data_ip_by_key[c.target_device],
         "port": c.port, "unit_id": c.unit_id, "interval_s": c.interval_s,
         "read_holding": c.read_holding, "read_coils": c.read_coils, "identity": c.identity}
        for c in persona.clients if c.target_device in data_ip_by_key
    ]
    return spec


def resolve_cml_cell(*, devices: list[dict], relationships: list[dict]) -> list[dict]:
    """Device graph → resolved slim specs for off-box CML deployment.

    ``devices``: [{key, name, template_id, protocol|None, process_model_id}];
    ``relationships``: [{source, target}] — source polls target.
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

    data_ip_by_key = {key: _data_ip(i) for i, key in enumerate(by_key)}

    for rel in relationships:
        src, dst = rel.get("source"), rel.get("target")
        if src not in by_key or dst not in by_key:
            continue
        target_proto = proto_by_key.get(dst) or "modbus"
        by_key[src].clients.append(ClientBinding(
            protocol=target_proto, target_device=dst, port=_PORTS.get(target_proto, 502)))

    return [_to_slim_spec(by_key[key], data_ip_by_key) for key in by_key]
