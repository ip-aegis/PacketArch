# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Conduit compliance validation service.

Checks all flows in a scenario definition against conduit rules
and produces compliance findings.
"""

from typing import Any

from app.schemas.conduit import (
    ComplianceFinding,
    ComplianceFindingReason,
    ComplianceSeverity,
    ConduitComplianceResponse,
)

# Protocol alias mapping: variant → parent protocol
# Flows may use variant names; conduits specify parent protocols.
PROTOCOL_ALIASES: dict[str, str] = {
    "profisafe": "profinet",
    "s7comm_plus": "s7comm",
    "cip_safety": "ethernet_ip",
    "modbus": "modbus_tcp",
    "enip": "ethernet_ip",
    "bacnet_ip": "bacnet",
}


def _resolve_protocol(protocol: str) -> str:
    """Resolve a protocol alias to its parent protocol."""
    return PROTOCOL_ALIASES.get(protocol, protocol)


def _get_device_zone(
    device_id: str,
    devices: dict[str, Any],
    zones: dict[str, Any],
) -> str | None:
    """Get the zone ID for a device.

    Checks device.zoneId first, then falls back to scanning zone.deviceIds.
    """
    device = devices.get(device_id, {})

    # Direct zone reference on device
    zone_id = device.get("zoneId") or device.get("zone_id") or device.get("zone")
    if zone_id:
        return zone_id

    # Fallback: search zones for device membership
    for zid, zone in zones.items():
        device_ids = zone.get("deviceIds", zone.get("device_ids", []))
        if device_id in device_ids:
            return zid

    return None


def _find_matching_conduit(
    source_zone_id: str,
    target_zone_id: str,
    protocol: str,
    conduits: dict[str, Any],
) -> tuple[str | None, ComplianceFindingReason | None]:
    """Find a conduit that covers a cross-zone flow.

    Returns:
        (conduit_id, reason) — conduit_id is set if a matching conduit exists.
        reason is set only when the flow is non-compliant.
    """
    resolved = _resolve_protocol(protocol)

    for cid, conduit in conduits.items():
        src = conduit.get("sourceZoneId", conduit.get("source_zone_id", ""))
        tgt = conduit.get("targetZoneId", conduit.get("target_zone_id", ""))
        direction = conduit.get("direction", "bidirectional")
        allowed = conduit.get("allowedProtocols", conduit.get("allowed_protocols", []))

        # Check if this conduit connects the two zones
        forward_match = src == source_zone_id and tgt == target_zone_id
        reverse_match = src == target_zone_id and tgt == source_zone_id

        if not forward_match and not reverse_match:
            continue

        # Direction check
        if direction == "a_to_b" and not forward_match:
            return cid, ComplianceFindingReason.WRONG_DIRECTION
        if direction == "b_to_a" and not reverse_match:
            return cid, ComplianceFindingReason.WRONG_DIRECTION

        # Protocol check — resolve aliases in the allowed list too
        resolved_allowed = {_resolve_protocol(p) for p in allowed}
        if resolved not in resolved_allowed:
            return cid, ComplianceFindingReason.PROTOCOL_NOT_ALLOWED

        # Fully compliant
        return cid, None

    # No conduit found
    return None, ComplianceFindingReason.NO_CONDUIT


def validate_conduit_compliance(
    definition: dict[str, Any],
) -> ConduitComplianceResponse:
    """Check all flows against conduit definitions.

    Rules:
        1. Same-zone flows: always compliant (no conduit needed)
        2. Cross-zone flows: look for a conduit connecting those zones
           a. No conduit found → warning "no_conduit"
           b. Conduit found but protocol not allowed → warning "protocol_not_allowed"
           c. Conduit found but direction wrong → warning "wrong_direction"
           d. Conduit found and matches → compliant (no finding)
        3. Flows with no zone info: silently compliant (backward compat)
    """
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})
    zones = definition.get("zones", {})
    conduits = definition.get("conduits", {})

    findings: list[ComplianceFinding] = []
    total_flows = 0
    compliant_flows = 0

    for flow_id, flow in flows.items():
        total_flows += 1

        source_id = flow.get("sourceDeviceId", flow.get("source_device_id", ""))
        target_id = flow.get("targetDeviceId", flow.get("target_device_id", ""))
        protocol = flow.get("protocol", "")
        flow_name = flow.get("name", f"{source_id} → {target_id}")

        source_zone = _get_device_zone(source_id, devices, zones)
        target_zone = _get_device_zone(target_id, devices, zones)

        # Missing zone info → emit a warning instead of silently passing.
        # This catches devices that were never assigned to a zone, which
        # means conduit rules cannot be enforced for their flows.
        if not source_zone or not target_zone:
            missing_side = "source" if not source_zone else "target"
            findings.append(ComplianceFinding(
                flow_id=flow_id,
                flow_name=flow_name,
                source_zone_id=source_zone or "(none)",
                target_zone_id=target_zone or "(none)",
                protocol=protocol,
                severity=ComplianceSeverity.WARNING,
                reason=ComplianceFindingReason.NO_CONDUIT,
                conduit_id=None,
            ))
            continue

        # Same zone → always compliant
        if source_zone == target_zone:
            compliant_flows += 1
            continue

        # No conduits defined at all → every cross-zone flow is non-compliant
        if not conduits:
            findings.append(ComplianceFinding(
                flow_id=flow_id,
                flow_name=flow_name,
                source_zone_id=source_zone,
                target_zone_id=target_zone,
                protocol=protocol,
                severity=ComplianceSeverity.WARNING,
                reason=ComplianceFindingReason.NO_CONDUIT,
            ))
            continue

        conduit_id, reason = _find_matching_conduit(
            source_zone, target_zone, protocol, conduits,
        )

        if reason is None:
            # Compliant
            compliant_flows += 1
        else:
            findings.append(ComplianceFinding(
                flow_id=flow_id,
                flow_name=flow_name,
                source_zone_id=source_zone,
                target_zone_id=target_zone,
                protocol=protocol,
                severity=ComplianceSeverity.WARNING,
                reason=reason,
                conduit_id=conduit_id,
            ))

    return ConduitComplianceResponse(
        findings=findings,
        total_flows=total_flows,
        compliant_flows=compliant_flows,
        non_compliant_flows=len(findings),
    )
