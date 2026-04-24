# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Validation and realism scoring tools for MCP."""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scenario import Scenario


# Vertical-specific norms for realism scoring
VERTICAL_NORMS: dict[str, dict[str, Any]] = {
    "manufacturing": {
        "expected_protocols": ["profinet", "ethernet_ip", "modbus_tcp", "opc_ua"],
        "typical_poll_intervals_ms": [1, 4, 10, 100, 500, 1000],
        "device_ratios": {
            "plc": (0.15, 0.35),  # 15-35% of devices should be PLCs
            "hmi": (0.05, 0.15),
            "drive": (0.15, 0.30),
            "io_module": (0.20, 0.40),
            "engineering_station": (0.02, 0.10),
        },
        "min_devices": 5,
        "expected_zones": ["process", "field", "enterprise"],
    },
    "water_wastewater": {
        "expected_protocols": ["modbus_tcp", "dnp3", "opc_ua"],
        "typical_poll_intervals_ms": [500, 1000, 5000, 10000, 30000, 60000],
        "device_ratios": {
            "rtu": (0.20, 0.50),
            "plc": (0.10, 0.30),
            "scada_server": (0.02, 0.10),
            "sensor": (0.15, 0.40),
        },
        "min_devices": 3,
        "expected_zones": ["enterprise", "process", "remote"],
    },
    "energy_power": {
        "expected_protocols": ["iec104", "dnp3", "modbus_tcp", "opc_ua"],
        "typical_poll_intervals_ms": [1000, 5000, 10000, 30000, 60000],
        "device_ratios": {
            "protection_relay": (0.20, 0.50),
            "rtu": (0.10, 0.30),
            "meter": (0.10, 0.30),
            "plc": (0.05, 0.20),
        },
        "min_devices": 4,
        "expected_zones": ["process", "field", "wan"],
    },
    "oil_gas": {
        "expected_protocols": ["modbus_tcp", "opc_ua", "dnp3"],
        "typical_poll_intervals_ms": [100, 500, 1000, 5000, 30000, 60000],
        "device_ratios": {
            "plc": (0.15, 0.35),
            "rtu": (0.20, 0.50),
            "sensor": (0.15, 0.35),
            "scada_server": (0.02, 0.08),
        },
        "min_devices": 5,
        "expected_zones": ["enterprise", "process", "field", "remote"],
    },
}


async def validate_topology(db: AsyncSession, scenario_id: str) -> str:
    """Validate scenario topology for issues.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string with validation results
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})

    issues = []
    warnings = []

    # Check for orphaned devices (no flows)
    devices_with_flows = set()
    for flow in flows.values():
        devices_with_flows.add(flow.get("sourceDeviceId"))
        devices_with_flows.add(flow.get("targetDeviceId"))

    orphaned_devices = set(devices.keys()) - devices_with_flows
    if orphaned_devices:
        warnings.append({
            "type": "orphaned_devices",
            "message": f"Found {len(orphaned_devices)} devices with no flows",
            "devices": list(orphaned_devices),
        })

    # Check for flows with missing devices
    for flow_id, flow in flows.items():
        source_id = flow.get("sourceDeviceId")
        target_id = flow.get("targetDeviceId")

        if source_id not in devices:
            issues.append({
                "type": "missing_device",
                "message": f"Flow {flow_id} references missing source device {source_id}",
                "flow_id": flow_id,
            })

        if target_id not in devices:
            issues.append({
                "type": "missing_device",
                "message": f"Flow {flow_id} references missing target device {target_id}",
                "flow_id": flow_id,
            })

        # Check for self-loops
        if source_id == target_id:
            warnings.append({
                "type": "self_loop",
                "message": f"Flow {flow_id} has same source and target device",
                "flow_id": flow_id,
            })

    # Check for protocol compatibility
    for flow_id, flow in flows.items():
        source_id = flow.get("sourceDeviceId")
        target_id = flow.get("targetDeviceId")
        protocol = flow.get("protocol")

        if source_id in devices and target_id in devices:
            source_protocols = devices[source_id].get("protocols", [])
            target_protocols = devices[target_id].get("protocols", [])

            if protocol not in source_protocols:
                warnings.append({
                    "type": "protocol_mismatch",
                    "message": f"Source device {source_id} doesn't support protocol {protocol}",
                    "flow_id": flow_id,
                })

            if protocol not in target_protocols:
                warnings.append({
                    "type": "protocol_mismatch",
                    "message": f"Target device {target_id} doesn't support protocol {protocol}",
                    "flow_id": flow_id,
                })

    return json.dumps({
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "issue_count": len(issues),
        "warning_count": len(warnings),
    })


async def validate_addressing(db: AsyncSession, scenario_id: str) -> str:
    """Validate IP and MAC addressing for conflicts.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string with addressing validation
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition
    devices = definition.get("devices", {})

    issues = []
    warnings = []

    # Track IP and MAC addresses
    ip_addresses: dict[str, list[str]] = {}
    mac_addresses: dict[str, list[str]] = {}
    devices_without_ip = []
    devices_without_mac = []

    for device_id, device in devices.items():
        network = device.get("network", {})

        # Check IP address
        ip = network.get("ipAddress", "").strip()
        if ip:
            if ip not in ip_addresses:
                ip_addresses[ip] = []
            ip_addresses[ip].append(device_id)
        else:
            devices_without_ip.append(device_id)

        # Check MAC address
        mac = network.get("macAddress", "").strip()
        if mac:
            if mac not in mac_addresses:
                mac_addresses[mac] = []
            mac_addresses[mac].append(device_id)
        else:
            devices_without_mac.append(device_id)

    # Check for duplicate IPs
    for ip, device_ids in ip_addresses.items():
        if len(device_ids) > 1:
            issues.append({
                "type": "duplicate_ip",
                "message": f"IP address {ip} assigned to multiple devices",
                "ip": ip,
                "devices": device_ids,
            })

    # Check for duplicate MACs
    for mac, device_ids in mac_addresses.items():
        if len(device_ids) > 1:
            issues.append({
                "type": "duplicate_mac",
                "message": f"MAC address {mac} assigned to multiple devices",
                "mac": mac,
                "devices": device_ids,
            })

    # Warn about missing addresses
    if devices_without_ip:
        warnings.append({
            "type": "missing_ip",
            "message": f"{len(devices_without_ip)} devices without IP addresses",
            "devices": devices_without_ip,
        })

    if devices_without_mac:
        warnings.append({
            "type": "missing_mac",
            "message": f"{len(devices_without_mac)} devices without MAC addresses",
            "devices": devices_without_mac,
        })

    return json.dumps({
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "issue_count": len(issues),
        "warning_count": len(warnings),
    })


async def score_realism(db: AsyncSession, scenario_id: str) -> str:
    """Score the realism of a scenario (0-100) with vertical-specific criteria.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string with realism score and factors
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})
    zones = definition.get("zones", {})
    vertical = scenario.vertical

    score = 100
    factors = []
    vertical_factors = []

    # Get vertical norms if available
    norms = VERTICAL_NORMS.get(vertical, {}) if vertical else {}

    # === Basic Checks (all verticals) ===

    # Check device diversity
    device_types = set(d.get("type") for d in devices.values())
    if len(device_types) < 2:
        score -= 20
        factors.append("Low device diversity (single type)")
    elif len(device_types) < 3:
        score -= 10
        factors.append("Limited device diversity")

    # Check flow count vs device count
    if devices:
        flow_ratio = len(flows) / len(devices)
        if flow_ratio < 0.5:
            score -= 15
            factors.append("Too few flows for device count")
        elif flow_ratio > 3:
            score -= 10
            factors.append("Unusually high flow count")

    # Check for zones
    if not zones:
        score -= 15
        factors.append("No network zones defined")

    # Check addressing completeness
    devices_with_ip = sum(
        1 for d in devices.values()
        if d.get("network", {}).get("ipAddress", "").strip()
    )
    if devices:
        ip_ratio = devices_with_ip / len(devices)
        if ip_ratio < 0.5:
            score -= 15
            factors.append("Many devices without IP addresses")
        elif ip_ratio < 1.0:
            score -= 5
            factors.append("Some devices without IP addresses")

    # Check protocol variety
    protocols_used = set(f.get("protocol") for f in flows.values())
    if len(protocols_used) < 2 and len(flows) > 3:
        score -= 10
        factors.append("Limited protocol variety")

    # Check timing realism (generic)
    unrealistic_timing = 0
    for flow in flows.values():
        timing = flow.get("timing", {})
        interval = timing.get("intervalMs", 0)
        if interval > 0 and (interval < 1 or interval > 300000):
            unrealistic_timing += 1

    if unrealistic_timing > 0:
        penalty = min(15, unrealistic_timing * 3)
        score -= penalty
        factors.append(f"{unrealistic_timing} flows with unrealistic timing intervals")

    # === Vertical-Specific Checks ===

    if norms:
        # Check expected protocols for vertical
        expected_protocols = set(norms.get("expected_protocols", []))
        if expected_protocols and protocols_used:
            missing_protocols = expected_protocols - protocols_used
            unexpected_protocols = protocols_used - expected_protocols

            if len(unexpected_protocols) > len(protocols_used) / 2:
                score -= 10
                vertical_factors.append(
                    f"Unusual protocols for {vertical}: {', '.join(unexpected_protocols)}"
                )

            # Bonus for using expected protocols
            if len(protocols_used & expected_protocols) >= 2:
                score += 5
                vertical_factors.append(f"Good protocol selection for {vertical}")

        # Check timing patterns for vertical
        typical_intervals = norms.get("typical_poll_intervals_ms", [])
        if typical_intervals and flows:
            interval_match_count = 0
            for flow in flows.values():
                timing = flow.get("timing", {})
                interval = timing.get("intervalMs", 0)
                if interval > 0:
                    # Check if interval is close to any typical value
                    for typical in typical_intervals:
                        if 0.5 * typical <= interval <= 2 * typical:
                            interval_match_count += 1
                            break

            if len(flows) > 0:
                match_ratio = interval_match_count / len(flows)
                if match_ratio < 0.3:
                    score -= 10
                    vertical_factors.append(
                        f"Timing intervals atypical for {vertical}"
                    )
                elif match_ratio > 0.7:
                    score += 5
                    vertical_factors.append(
                        f"Timing intervals match {vertical} patterns"
                    )

        # Check device ratios for vertical
        device_ratios = norms.get("device_ratios", {})
        if device_ratios and devices:
            device_type_counts = {}
            for d in devices.values():
                dtype = d.get("type", "unknown")
                device_type_counts[dtype] = device_type_counts.get(dtype, 0) + 1

            total_devices = len(devices)
            ratio_issues = []

            for dtype, (min_ratio, max_ratio) in device_ratios.items():
                actual_count = device_type_counts.get(dtype, 0)
                actual_ratio = actual_count / total_devices if total_devices > 0 else 0

                if actual_count > 0 and actual_ratio < min_ratio * 0.5:
                    ratio_issues.append(f"Low {dtype} count")
                elif actual_ratio > max_ratio * 1.5:
                    ratio_issues.append(f"High {dtype} count")

            if len(ratio_issues) > 2:
                score -= 10
                vertical_factors.append(
                    f"Device composition atypical for {vertical}: {', '.join(ratio_issues[:3])}"
                )

        # Check minimum device count for vertical
        min_devices = norms.get("min_devices", 3)
        if len(devices) < min_devices:
            score -= 10
            vertical_factors.append(
                f"Too few devices for realistic {vertical} scenario (min: {min_devices})"
            )

        # Check expected zones for vertical
        expected_zones = set(norms.get("expected_zones", []))
        if expected_zones and zones:
            zone_ids = set(zones.keys())
            matching_zones = zone_ids & expected_zones

            if len(matching_zones) < len(expected_zones) / 2:
                score -= 5
                vertical_factors.append(
                    f"Missing typical zones for {vertical}"
                )

    # Ensure score stays in bounds
    score = max(0, min(100, score))

    # Combine factors
    all_factors = factors + vertical_factors

    return json.dumps({
        "score": score,
        "grade": _get_grade(score),
        "factors": all_factors,
        "vertical": vertical,
        "vertical_specific": len(vertical_factors) > 0,
    })


async def suggest_improvements(db: AsyncSession, scenario_id: str) -> str:
    """AI suggests improvements to scenario realism.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string with improvement suggestions
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})
    zones = definition.get("zones", {})

    suggestions = []

    # Check for missing addresses
    devices_without_ip = [
        d_id for d_id, d in devices.items()
        if not d.get("network", {}).get("ipAddress", "").strip()
    ]
    if devices_without_ip:
        suggestions.append({
            "category": "addressing",
            "priority": "high",
            "message": "Assign IP addresses to all devices",
            "action": "auto_assign_addresses",
            "affected_devices": devices_without_ip,
        })

    # Check for orphaned devices
    devices_with_flows = set()
    for flow in flows.values():
        devices_with_flows.add(flow.get("sourceDeviceId"))
        devices_with_flows.add(flow.get("targetDeviceId"))

    orphaned_devices = set(devices.keys()) - devices_with_flows
    if orphaned_devices:
        suggestions.append({
            "category": "topology",
            "priority": "medium",
            "message": "Add flows for isolated devices",
            "affected_devices": list(orphaned_devices),
        })

    # Check for missing zones
    if not zones:
        suggestions.append({
            "category": "organization",
            "priority": "medium",
            "message": "Create network zones to organize devices",
            "action": "create_zones",
        })

    # Check device diversity
    device_types = set(d.get("type") for d in devices.values())
    if len(device_types) < 3 and scenario.vertical:
        suggestions.append({
            "category": "devices",
            "priority": "low",
            "message": f"Consider adding more device types for {scenario.vertical} vertical",
        })

    return json.dumps({
        "suggestions": suggestions,
        "count": len(suggestions),
    })


def _get_grade(score: int) -> str:
    """Convert score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"
