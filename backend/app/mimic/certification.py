# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Mimic certification — gatekeep what a persona can convincingly emulate.

Mimic exists to fool a skilled analyst / Cyber Vision, so "the device speaks a
protocol we have a server for" is necessary but NOT sufficient. A persona only
"looks real" when it also returns the correct DEVICE IDENTITY over that protocol
(FC43 / OPC-UA BuildInfo / BACnet device object — what CV classifies on), the
runtime can actually serve that protocol for the chosen deploy target, and the
device is the KIND of thing that responds as a server on the wire.

This module is the single source of truth for that gate. It is used to (a) tell the
Studio which (device, protocol, target) combos to offer, and (b) REJECT an
uncertified persona at deploy time.

Policy (operator-chosen): software / workstation roles (Historian, SCADA,
engineering station, HMI, …) are NOT certified as bound servers — a real one is a
client, not a responder — so they're offered only as CLIENT personas (they poll).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Backend protocol name -> the canonical Mimic server protocol we can emulate.
PROTO_MAP: dict[str, str] = {
    "modbus_tcp": "modbus",
    "opc_ua": "opcua",
    "bacnet": "bacnet",
    "bacnet_ip": "bacnet",
    "iec104": "iec104",
}

# Deploy targets each protocol has a working SERVER runtime for. iec104 (c104) has
# no musllinux wheel, so it can't run on the slim off-box Alpine node.
RUNTIME_SUPPORT: dict[str, frozenset[str]] = {
    "modbus": frozenset({"onbox", "offbox"}),
    "opcua": frozenset({"onbox", "offbox"}),
    "bacnet": frozenset({"onbox", "offbox"}),
    "iec104": frozenset({"onbox"}),
}

# Roles that are software / operator / workstation — a real instance is a CLIENT
# (polls field devices), not a bound device server. Everything else is a responder.
CLIENT_ONLY_ROLES: frozenset[str] = frozenset({
    "hmi", "scada", "scada_server", "operator_station", "engineering_station",
    "engineering_workstation", "workstation", "historian", "server", "fleet_manager",
})


def emulable_protocols(supported: list[str] | None) -> list[str]:
    """The template's protocols mapped to the Mimic server protocols, de-duped."""
    out: list[str] = []
    for p in supported or []:
        s = PROTO_MAP.get(p)
        if s and s not in out:
            out.append(s)
    return out


def is_client_role(device_type: str) -> bool:
    return device_type in CLIENT_ONLY_ROLES


def has_identity(fingerprint: dict, protocol: str) -> bool:
    """Whether the fingerprint carries the identity a persona needs to answer this
    protocol AS the real device (not a generic responder)."""
    fp = fingerprint or {}
    if protocol == "modbus":
        mi = fp.get("modbus_identity") or {}
        return bool(mi.get("product_code") or mi.get("product_name") or mi.get("model_name"))
    if protocol == "opcua":
        return bool(fp.get("vendor") and (fp.get("model") or fp.get("vendor_family")))
    if protocol == "bacnet":
        bi = fp.get("bacnet_identity") or {}
        return bool(bi.get("vendor_id") or bi.get("model_name"))
    if protocol == "iec104":
        return True  # telecontrol has no read-device-identity; realism is behavioral
    return False


def certify_server(fingerprint: dict, device_type: str, protocol: str, target: str) -> tuple[bool, str]:
    """Can this device convincingly bind a `protocol` server for `target`?
    Returns (certified, reason)."""
    if is_client_role(device_type):
        return False, f"'{device_type}' is a client/software role — use it as a client persona, not a server"
    if target not in RUNTIME_SUPPORT.get(protocol, frozenset()):
        return False, f"no {target} server runtime for {protocol}"
    if not has_identity(fingerprint, protocol):
        return False, f"no {protocol} identity data — would answer as a generic device"
    return True, "certified"


@dataclass
class TemplateCertification:
    role_class: str  # "responder" | "client"
    client_capable: bool
    server_protocols: dict[str, list[str]] = field(default_factory=dict)  # target -> certified protocols

    def to_dict(self) -> dict:
        return {
            "role_class": self.role_class,
            "client_capable": self.client_capable,
            "server_protocols": self.server_protocols,
        }


def check_devices(items: list[tuple[str, str, dict, str | None]], target: str) -> list[str]:
    """Validate authored personas against certification. ``items`` are
    (name, device_type, fingerprint, protocol|None); a None protocol is a
    client-only persona (always allowed). Returns a list of rejection reasons
    (empty = all certified)."""
    errors: list[str] = []
    for name, device_type, fingerprint, protocol in items:
        if protocol is None:
            continue  # client-only node — a valid persona for any device
        ok, reason = certify_server(fingerprint, device_type, protocol, target)
        if not ok:
            errors.append(f"{name}: {reason}")
    return errors


def certify_template(fingerprint: dict, device_type: str, supported: list[str] | None,
                     targets: tuple[str, ...] = ("onbox", "offbox")) -> TemplateCertification:
    """Full certification for a template across deploy targets."""
    protos = emulable_protocols(supported)
    client = is_client_role(device_type)
    server_protocols = {
        t: [p for p in protos if certify_server(fingerprint, device_type, p, t)[0]]
        for t in targets
    }
    return TemplateCertification(
        role_class="client" if client else "responder",
        client_capable=client,
        server_protocols=server_protocols,
    )
