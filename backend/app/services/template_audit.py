# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Template catalog audit: flag declarations that disagree with reality.

Two classes of issue surfaced:

1. **Off-vendor declarations** — a template's explicit supported_protocols
   includes a protocol the vendor doesn't natively serve. Example:
   Siemens S7 PLC with `ethernet_ip` in supported_protocols.

2. **Missing-identity declarations** — a protocol is declared but the
   corresponding identity block is None on the template. Example:
   `opc_ua` listed but `opc_ua_identity = None`.

This is purely a read-only audit. No source files are mutated. The output
helps a human curator decide whether to remove a declaration (it's wrong)
or populate the identity block (declaration is intentional but data is
incomplete).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.device_templates._protocol_defaults import (
    PROTOCOL_TO_TEMPLATE_IDENTITY,
    VENDOR_NATIVE_PROTOCOLS,
    vendor_brand,
)


@dataclass
class TemplateAuditFinding:
    """A single finding for one template."""

    template_id: str
    vendor: str
    model: str
    model_name: str
    device_type: str

    # Declared `supported_protocols` (None means template didn't set it)
    declared: list[str] = field(default_factory=list)

    # Vendor-native set the audit looked up
    vendor_natives: list[str] = field(default_factory=list)

    # Declared but not in vendor-natives — most likely wrong
    off_vendor: list[str] = field(default_factory=list)

    # Declared protocols whose identity block is None on the template
    missing_identity: list[str] = field(default_factory=list)

    # Identity blocks that ARE populated (helps spot "implicit" support)
    populated_identity_blocks: list[str] = field(default_factory=list)

    # True if vendor isn't in the whitelist — audit can't conclude anything
    unknown_vendor: bool = False


def _identity_block_populated(template: Any, ikey: str) -> bool:
    val = getattr(template, ikey, None)
    return bool(val)


def audit_templates(templates: list[Any] | None = None) -> list[TemplateAuditFinding]:
    """Run the audit across the template registry.

    If `templates` is None, uses the canonical DEVICE_TEMPLATES registry.
    """
    if templates is None:
        from app.services.device_templates._registry import DEVICE_TEMPLATES
        templates = list(DEVICE_TEMPLATES.values())

    findings: list[TemplateAuditFinding] = []

    for t in templates:
        declared = list(getattr(t, "supported_protocols", None) or [])
        vendor = getattr(t, "vendor", "") or ""
        brand = vendor_brand(vendor)
        natives = VENDOR_NATIVE_PROTOCOLS.get(brand)

        # Track which identity blocks the template populates
        populated_ikeys = sorted(
            {
                ikey
                for ikey in PROTOCOL_TO_TEMPLATE_IDENTITY.values()
                if _identity_block_populated(t, ikey)
            }
        )

        # Off-vendor list (declared protocols not in vendor-natives)
        off_vendor: list[str] = []
        if natives is not None and declared:
            off_vendor = sorted(
                p for p in declared if p.lower() not in natives
            )

        # Missing-identity list (declared but template lacks identity block)
        missing_identity: list[str] = []
        for p in declared:
            ikey = PROTOCOL_TO_TEMPLATE_IDENTITY.get(p.lower())
            if ikey is None:
                continue  # protocols without an identity requirement
            if not _identity_block_populated(t, ikey):
                # SNMP gets a free pass — noise generator synthesises identity
                # from vendor OUI. Other protocols genuinely need data.
                if p.lower() == "snmp":
                    continue
                missing_identity.append(p)

        # Only emit a finding if there's something to surface.
        if off_vendor or missing_identity:
            findings.append(
                TemplateAuditFinding(
                    template_id=getattr(t, "id", ""),
                    vendor=vendor,
                    model=getattr(t, "model", ""),
                    model_name=getattr(t, "model_name", ""),
                    device_type=getattr(t, "device_type", ""),
                    declared=declared,
                    vendor_natives=sorted(natives) if natives else [],
                    off_vendor=off_vendor,
                    missing_identity=missing_identity,
                    populated_identity_blocks=populated_ikeys,
                    unknown_vendor=natives is None,
                )
            )

    # Stable ordering for deterministic output / diffs
    findings.sort(key=lambda f: (f.vendor.lower(), f.model.lower(), f.template_id))
    return findings


def summarize(findings: list[TemplateAuditFinding]) -> dict[str, int]:
    """Bucket counts for the report header."""
    return {
        "total_findings": len(findings),
        "off_vendor_only": sum(
            1 for f in findings if f.off_vendor and not f.missing_identity
        ),
        "missing_identity_only": sum(
            1 for f in findings if f.missing_identity and not f.off_vendor
        ),
        "both_issues": sum(
            1 for f in findings if f.off_vendor and f.missing_identity
        ),
        "unknown_vendor": sum(1 for f in findings if f.unknown_vendor),
        "templates_with_off_vendor_protocols": sum(
            1 for f in findings if f.off_vendor
        ),
        "templates_with_missing_identity": sum(
            1 for f in findings if f.missing_identity
        ),
    }


def finding_to_dict(f: TemplateAuditFinding) -> dict[str, Any]:
    """Serialize a finding for JSON responses."""
    return {
        "template_id": f.template_id,
        "vendor": f.vendor,
        "model": f.model,
        "model_name": f.model_name,
        "device_type": f.device_type,
        "declared": f.declared,
        "vendor_natives": f.vendor_natives,
        "off_vendor": f.off_vendor,
        "missing_identity": f.missing_identity,
        "populated_identity_blocks": f.populated_identity_blocks,
        "unknown_vendor": f.unknown_vendor,
    }


# ----------------------------------------------------------------------
# Irrational flow detection
# ----------------------------------------------------------------------

# Protocols that are too generic to count as a real industrial-flow basis
# in the same way OT protocols are. A flow whose only shared protocol falls
# in this set is reviewed by device-type pairing — for jump-server-to-asset
# flows it's expected (admin remote access); for plc-to-plc it's wrong.
_GENERIC_ONLY_PROTOCOLS: frozenset[str] = frozenset({
    "snmp", "http", "telnet",
})

# Source device types where a generic-only protocol IS the correct shape
# (admins / jump servers / management stations / vertical-specific NMS).
# When source is one of these, generic-only flows are not flagged.
_GENERIC_OK_SOURCE_TYPES: frozenset[str] = frozenset({
    # IT-style admin / jump
    "jump_server", "remote_gateway", "engineering_workstation",
    "engineering_station", "workstation", "server", "scada_server",
    "historian",
    # Transportation: ATMS master stations, cabinet controllers, toll
    # controllers, and the traffic controller all legitimately speak
    # SNMP/NTCIP (NTCIP rides on SNMP — it's the operational protocol,
    # not just admin-style).
    "master_station", "traffic_controller", "atms_master",
    "toll_controller", "cabinet_controller",
    # Data-center infrastructure management — DCIM servers monitor PDUs,
    # UPSes, switches via SNMP as their primary protocol.
    "dcim_server",
    # Building automation supervisor / NMS variants
    "bms_supervisor", "bms_server", "ems_server",
    # Substation / energy NMS
    "rtu_master", "scada_master",
    # Robotics / AGV fleet managers — speak HTTPS/SNMP to their fleet
    "fleet_manager", "fleet_controller",
})

# Pairings of (source_device_type, target_device_type) that don't make
# operational sense regardless of shared protocol. Industrial-network
# topology rules: SCADA polls PLCs, PLCs poll field devices, network
# management polls everything. Things like "field device polls PLC" or
# "remote-access gateway polls cell-internal field device" usually
# indicate the scenario was authored incorrectly.
_IRRATIONAL_TYPE_PAIRS: tuple[tuple[str, str, str], ...] = (
    # source, target, reason
    ("jump_server", "plc", "jump server should not directly poll PLCs — go through SCADA/eng workstation"),
    ("jump_server", "drive", "jump server should not directly poll drives"),
    ("jump_server", "io_module", "jump server should not directly poll IO modules"),
    ("jump_server", "sensor", "jump server should not directly poll sensors"),
    ("ewon_gateway", "plc", "EWON gateway typically forwards to remote SCADA via cloud, not direct polling"),
    ("drive", "plc", "drives respond to PLC polls, not initiate them"),
    ("drive", "hmi", "drives don't poll HMIs"),
    ("io_module", "plc", "IO modules respond to PLC polls"),
    ("io_module", "hmi", "IO modules don't poll HMIs"),
    ("sensor", "plc", "sensors respond to PLC polls"),
    ("sensor", "hmi", "sensors don't poll HMIs"),
    ("switch", "plc", "switches don't poll PLCs over industrial protocols"),
    ("switch", "hmi", "switches don't poll HMIs"),
    # Network gear is polled by NMS/jump servers, not by control devices.
    ("plc", "switch", "PLCs don't poll switches; NMS or jump server does"),
    ("rtu", "switch", "RTUs don't poll switches; NMS does"),
    ("hmi", "switch", "HMIs don't poll switches; NMS or jump server does"),
    # HMIs poll PLCs, never field IO directly. PLC mediates field IO access.
    ("hmi", "io_module", "HMIs don't poll IO modules directly; PLC does"),
    ("hmi", "drive", "HMIs don't poll drives directly; PLC does"),
    ("hmi", "sensor", "HMIs don't poll sensors directly; PLC does"),
)


@dataclass
class IrrationalFlowFinding:
    """A flow whose protocol pairing or device-type pairing looks wrong."""

    flow_id: str
    flow_name: str | None
    protocol: str | None
    source_device_id: str
    source_device_name: str
    source_device_type: str
    source_vendor: str
    target_device_id: str
    target_device_name: str
    target_device_type: str
    target_vendor: str
    reason: str
    severity: str  # "warning" | "info"


def _normalize_devices_for_flow_audit(
    devices_in: Any,
) -> dict[str, dict[str, Any]]:
    if isinstance(devices_in, list):
        return {d.get("id", str(i)): d for i, d in enumerate(devices_in)}
    return dict(devices_in or {})


def _flow_eps(flow: dict[str, Any]) -> tuple[str | None, str | None]:
    src = (
        flow.get("sourceDeviceId")
        or flow.get("source_device_id")
        or flow.get("source")
    )
    tgt = (
        flow.get("targetDeviceId")
        or flow.get("destinationDeviceId")
        or flow.get("destination_device_id")
        or flow.get("target")
    )
    return src, tgt


def audit_irrational_flows(
    definition: dict[str, Any],
) -> list[IrrationalFlowFinding]:
    """Detect flows that look semantically wrong even when the protocol
    technically validates.

    Two checks per flow:
      1. **Generic-only protocol** — if the chosen protocol is SNMP, HTTPS,
         SSH or similar and that's the *only* protocol both endpoints share,
         the flow is probably a degraded snap from an irrational pairing.
      2. **Type-pair sanity** — some source/target device-type combinations
         don't exist in real industrial networks (jump server → PLC,
         drive → PLC, sensor → HMI, etc.). Surface those regardless of
         protocol so authors can rethink the scenario topology.

    Conservative: emits warnings, never auto-corrects. Cloud / coverage /
    skip-marked flows are exempt.
    """
    from app.protocol_engines.protocols import get_supported_protocols

    devices = _normalize_devices_for_flow_audit(definition.get("devices"))
    flows_raw = definition.get("flows") or {}
    if isinstance(flows_raw, list):
        flows = {f.get("id", str(i)): f for i, f in enumerate(flows_raw)}
    else:
        flows = dict(flows_raw)

    if not devices or not flows:
        return []

    findings: list[IrrationalFlowFinding] = []

    for fid, flow in flows.items():
        # Exempt the same set as repair_flow_protocols
        if (
            flow.get("coverage_flow")
            or flow.get("auto_repair_skip")
            or (flow.get("config") or {}).get("external")
        ):
            continue

        src_id, tgt_id = _flow_eps(flow)
        if not src_id or not tgt_id:
            continue
        src = devices.get(src_id)
        tgt = devices.get(tgt_id)
        if not src or not tgt:
            continue

        proto = (flow.get("protocol") or "").strip().lower() or None
        src_fp = (
            src.get("vendorFingerprint")
            or src.get("vendor_fingerprint")
            or src.get("fingerprint")
            or {}
        )
        tgt_fp = (
            tgt.get("vendorFingerprint")
            or tgt.get("vendor_fingerprint")
            or tgt.get("fingerprint")
            or {}
        )
        src_type = (src.get("type") or "").lower().strip()
        tgt_type = (tgt.get("type") or "").lower().strip()
        src_vendor = (src_fp.get("vendor") or "").strip()
        tgt_vendor = (tgt_fp.get("vendor") or "").strip()

        # Check 1: generic-only protocol (only-shared = SNMP/HTTP/Telnet)
        # Skip when the source is an admin/management device — those
        # legitimately use generic protocols to manage assets.
        if (
            proto
            and proto in _GENERIC_ONLY_PROTOCOLS
            and src_type not in _GENERIC_OK_SOURCE_TYPES
        ):
            src_supp = {p.lower() for p in get_supported_protocols(src_fp)}
            tgt_supp = {p.lower() for p in get_supported_protocols(tgt_fp)}
            shared = (src_supp & tgt_supp) - _GENERIC_ONLY_PROTOCOLS
            if not shared:
                findings.append(IrrationalFlowFinding(
                    flow_id=fid,
                    flow_name=flow.get("name"),
                    protocol=proto,
                    source_device_id=src_id,
                    source_device_name=src.get("name", src_id),
                    source_device_type=src_type,
                    source_vendor=src_vendor,
                    target_device_id=tgt_id,
                    target_device_name=tgt.get("name", tgt_id),
                    target_device_type=tgt_type,
                    target_vendor=tgt_vendor,
                    reason=(
                        f"only shared protocol is generic ({proto}); "
                        f"{src_type or 'source'} → {tgt_type or 'target'} "
                        "pairing likely doesn't reflect a real industrial flow"
                    ),
                    severity="warning",
                ))
                # Don't double-fire on type-pair check below.
                continue

        # Check 2: irrational type pair.
        # Carve-out: when the source is an admin/management device AND the
        # flow protocol is a generic management protocol (SNMP/HTTP/Telnet),
        # this is a legitimate reachability/monitoring pattern (e.g. a
        # jump server SNMP-pinging a PLC). Don't flag those.
        if (
            src_type in _GENERIC_OK_SOURCE_TYPES
            and proto
            and proto in _GENERIC_ONLY_PROTOCOLS
        ):
            continue
        type_pair_fired = False
        for bad_src, bad_tgt, reason in _IRRATIONAL_TYPE_PAIRS:
            if src_type == bad_src and tgt_type == bad_tgt:
                findings.append(IrrationalFlowFinding(
                    flow_id=fid,
                    flow_name=flow.get("name"),
                    protocol=proto,
                    source_device_id=src_id,
                    source_device_name=src.get("name", src_id),
                    source_device_type=src_type,
                    source_vendor=src_vendor,
                    target_device_id=tgt_id,
                    target_device_name=tgt.get("name", tgt_id),
                    target_device_type=tgt_type,
                    target_vendor=tgt_vendor,
                    reason=reason,
                    severity="warning",
                ))
                type_pair_fired = True
                break

        # Check 3: role-pair check via role catalog typical_partners.
        # Only fires when BOTH endpoints have an architectural_role set
        # (explicit or auto-stamped from device_type). Flags pairs where
        # neither role lists the other as a typical partner — surfaces
        # role mismatches the type-pair table misses (e.g. a vfd polling
        # an engineering_workstation).
        if not type_pair_fired:
            src_role = (
                src.get("architecturalRole")
                or src.get("architectural_role")
            )
            tgt_role = (
                tgt.get("architecturalRole")
                or tgt.get("architectural_role")
            )
            if src_role and tgt_role and src_role != tgt_role:
                src_partners = _typical_partners_for(src_role)
                tgt_partners = _typical_partners_for(tgt_role)
                if (
                    src_partners is not None
                    and tgt_partners is not None
                    and tgt_role not in src_partners
                    and src_role not in tgt_partners
                ):
                    findings.append(IrrationalFlowFinding(
                        flow_id=fid,
                        flow_name=flow.get("name"),
                        protocol=proto,
                        source_device_id=src_id,
                        source_device_name=src.get("name", src_id),
                        source_device_type=src_type,
                        source_vendor=src_vendor,
                        target_device_id=tgt_id,
                        target_device_name=tgt.get("name", tgt_id),
                        target_device_type=tgt_type,
                        target_vendor=tgt_vendor,
                        reason=(
                            f"role pair {src_role} → {tgt_role} not in "
                            f"either role's typical_partners — likely "
                            f"unrealistic traffic pattern"
                        ),
                        severity="info",
                    ))

    findings.sort(key=lambda f: (f.source_device_name, f.target_device_name))
    return findings


def _typical_partners_for(role_id: str) -> set[str] | None:
    """Look up typical_partners for a role. Returns None if unknown."""
    from app.services.architecture.role_catalog import get_role
    role = get_role(role_id)
    if role is None:
        return None
    return set(role.typical_partners)


def irrational_flow_to_dict(f: IrrationalFlowFinding) -> dict[str, Any]:
    return {
        "flow_id": f.flow_id,
        "flow_name": f.flow_name,
        "protocol": f.protocol,
        "source_device_id": f.source_device_id,
        "source_device_name": f.source_device_name,
        "source_device_type": f.source_device_type,
        "source_vendor": f.source_vendor,
        "target_device_id": f.target_device_id,
        "target_device_name": f.target_device_name,
        "target_device_type": f.target_device_type,
        "target_vendor": f.target_vendor,
        "reason": f.reason,
        "severity": f.severity,
    }
