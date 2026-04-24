# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Scenario manipulation tools for MCP."""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.scenario import Scenario


async def get_scenario(db: AsyncSession, scenario_id: str) -> str:
    """Get complete scenario data.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string of full scenario
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    return json.dumps({
        "scenario": {
            "id": str(scenario.id),
            "name": scenario.name,
            "description": scenario.description,
            "vertical": scenario.vertical,
            "total_duration_ms": scenario.total_duration_ms,
            "definition": scenario.definition,
            "addressing_config": scenario.addressing_config,
            "version": scenario.version,
        }
    })


async def get_scenario_summary(db: AsyncSession, scenario_id: str) -> str:
    """Get scenario summary with statistics.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string of scenario summary
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})
    zones = definition.get("zones", {})
    phases = definition.get("phases", [])

    # Count devices by type
    device_types: dict[str, int] = {}
    for device in devices.values():
        device_type = device.get("type", "unknown")
        device_types[device_type] = device_types.get(device_type, 0) + 1

    # Count flows by protocol
    flow_protocols: dict[str, int] = {}
    for flow in flows.values():
        protocol = flow.get("protocol", "unknown")
        flow_protocols[protocol] = flow_protocols.get(protocol, 0) + 1

    return json.dumps({
        "summary": {
            "name": scenario.name,
            "vertical": scenario.vertical,
            "total_duration_ms": scenario.total_duration_ms,
            "device_count": len(devices),
            "flow_count": len(flows),
            "zone_count": len(zones),
            "phase_count": len(phases),
            "device_types": device_types,
            "flow_protocols": flow_protocols,
        }
    })


async def add_zone(db: AsyncSession, scenario_id: str, zone_data: dict[str, Any]) -> str:
    """Add a zone to a scenario with proper subnet allocation.

    Automatically assigns a subnet_offset if not provided, ensuring each zone
    gets its own /24 subnet within the scenario's /16 range.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        zone_data: Zone configuration (may include subnet_offset, level, vlan)

    Returns:
        JSON string with zone ID and subnet info
    """
    from app.services.ip_management import get_ip_allocation

    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    # Generate zone ID if not provided
    zone_id = zone_data.get("id") or f"zone_{uuid.uuid4().hex[:8]}"

    # Get or initialize zones dict
    definition = scenario.definition.copy()
    zones = definition.get("zones", {})

    # Get scenario's IP allocation for subnet derivation
    ip_allocation = await get_ip_allocation(db, uuid.UUID(scenario_id))
    range_index = ip_allocation.range_index if ip_allocation else 1

    # Auto-assign subnet_offset if not provided
    subnet_offset = zone_data.get("subnet_offset")
    if subnet_offset is None:
        # Find next available offset by looking at existing zones
        used_offsets = set()
        for existing_zone in zones.values():
            offset = existing_zone.get("subnet_offset")
            if offset is not None:
                used_offsets.add(offset)
            # Also check nested network config
            network = existing_zone.get("network", {})
            offset = network.get("subnet_offset")
            if offset is not None:
                used_offsets.add(offset)
        # Find first unused offset
        subnet_offset = 0
        while subnet_offset in used_offsets:
            subnet_offset += 1

    # Build network config for the zone
    network_config = {
        "subnet": f"10.{range_index}.{subnet_offset}.0/24",
        "gateway": f"10.{range_index}.{subnet_offset}.1",
        "subnet_offset": subnet_offset,
    }

    # Build complete zone config
    zone_config = {
        "id": zone_id,
        "name": zone_data.get("name", zone_id.replace("_", " ").title()),
        "subnet_offset": subnet_offset,
        "level": zone_data.get("level"),
        "vlan": zone_data.get("vlan", 100 + subnet_offset * 10),
        "network": network_config,
        "deviceIds": zone_data.get("deviceIds", []),
        **{k: v for k, v in zone_data.items() if k not in ["id", "name", "subnet_offset", "level", "vlan", "network", "deviceIds"]},
    }

    # Add zone
    zones[zone_id] = zone_config
    definition["zones"] = zones

    # Update scenario - use flag_modified to ensure JSONB change is detected
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "zone_id": zone_id,
        "subnet_offset": subnet_offset,
        "subnet": network_config["subnet"],
        "gateway": network_config["gateway"],
        "range_index": range_index,
    })


async def update_zone(
    db: AsyncSession, scenario_id: str, zone_id: str, updates: dict[str, Any]
) -> str:
    """Update a zone in a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        zone_id: Zone ID
        updates: Updates to apply

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    zones = definition.get("zones", {})

    if zone_id not in zones:
        return json.dumps({"error": f"Zone {zone_id} not found"})

    # Merge updates
    zone = zones[zone_id].copy()
    zone.update(updates)
    zones[zone_id] = zone
    definition["zones"] = zones

    # Update scenario - use flag_modified to ensure JSONB change is detected
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({"success": True, "zone_id": zone_id})


async def add_phase(db: AsyncSession, scenario_id: str, phase_data: dict[str, Any]) -> str:
    """Add a phase to a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        phase_data: Phase configuration

    Returns:
        JSON string with phase ID
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    # Generate phase ID if not provided
    phase_id = phase_data.get("id") or f"phase_{uuid.uuid4().hex[:8]}"
    phase_data["id"] = phase_id

    # Get or initialize phases list
    definition = scenario.definition.copy()
    phases = definition.get("phases", [])

    # Add phase
    phases.append(phase_data)
    definition["phases"] = phases

    # Update scenario - use flag_modified to ensure JSONB change is detected
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({"success": True, "phase_id": phase_id})


async def generate_scenario(
    db: AsyncSession,
    user_id: str,
    vertical: str,
    device_count: int,
    duration_ms: int,
) -> str:
    """Generate a complete scenario with fingerprinted devices and realistic flows.

    Args:
        db: Database session
        user_id: User ID
        vertical: Industry vertical
        device_count: Number of devices to generate
        duration_ms: Scenario duration in milliseconds

    Returns:
        JSON string with generated scenario ID
    """
    import random
    from app.protocol_engines.identity import generate_mac
    from app.protocol_engines.protocols import PROTOCOL_TO_IDENTITY_KEY
    from app.services.device_identity_enricher import (
        enrich_device_serial_numbers,
        enrich_device_unique_identifiers,
    )
    from app.services.device_templates import get_fingerprints_by_vendor
    from app.traffic_generator.flow_generator import generate_flows_for_scenario

    # Vertical-specific device templates with vendors and fingerprint hints
    device_templates: dict[str, list[dict[str, Any]]] = {
        "manufacturing": [
            {"type": "plc", "vendor": "siemens", "protocols": ["profinet", "s7comm"], "zone": "control"},
            {"type": "plc", "vendor": "rockwell", "protocols": ["ethernet_ip"], "zone": "control"},
            {"type": "hmi", "vendor": "siemens", "protocols": ["profinet"], "zone": "control"},
            {"type": "drive", "vendor": "siemens", "protocols": ["profinet"], "zone": "field"},
            {"type": "io_module", "vendor": "siemens", "protocols": ["profinet"], "zone": "field"},
            {"type": "switch", "vendor": "cisco", "protocols": ["snmp"], "zone": "control"},
        ],
        "water_wastewater": [
            {"type": "plc", "vendor": "schneider", "protocols": ["modbus_tcp"], "zone": "control"},
            {"type": "rtu", "vendor": "schneider", "protocols": ["modbus_tcp"], "zone": "field"},
            {"type": "hmi", "vendor": "schneider", "protocols": ["modbus_tcp"], "zone": "control"},
            {"type": "sensor", "vendor": "schneider", "protocols": ["modbus_tcp"], "zone": "field"},
            {"type": "switch", "vendor": "cisco", "protocols": ["snmp"], "zone": "control"},
        ],
        "energy_power": [
            {"type": "relay", "vendor": "sel", "protocols": ["modbus_tcp"], "zone": "control"},
            {"type": "rtu", "vendor": "schneider", "protocols": ["modbus_tcp"], "zone": "control"},
            {"type": "hmi", "vendor": "schneider", "protocols": ["modbus_tcp"], "zone": "enterprise"},
            {"type": "meter", "vendor": "schneider", "protocols": ["modbus_tcp"], "zone": "field"},
        ],
        "building_automation": [
            {"type": "plc", "vendor": "honeywell", "protocols": ["bacnet"], "zone": "control"},
            {"type": "vav_controller", "vendor": "honeywell", "protocols": ["bacnet"], "zone": "field"},
            {"type": "hmi", "vendor": "honeywell", "protocols": ["bacnet"], "zone": "control"},
            {"type": "sensor", "vendor": "honeywell", "protocols": ["bacnet"], "zone": "field"},
        ],
        "oil_gas": [
            {"type": "plc", "vendor": "emerson", "protocols": ["modbus_tcp"], "zone": "control"},
            {"type": "rtu", "vendor": "emerson", "protocols": ["modbus_tcp"], "zone": "field"},
            {"type": "hmi", "vendor": "emerson", "protocols": ["modbus_tcp"], "zone": "control"},
            {"type": "sensor", "vendor": "emerson", "protocols": ["modbus_tcp"], "zone": "field"},
        ],
    }

    templates = device_templates.get(vertical, device_templates["manufacturing"])

    # Generate devices with fingerprint lookup and vendor-correct MACs
    devices: dict[str, dict[str, Any]] = {}
    for i in range(device_count):
        template = templates[i % len(templates)]
        device_id = f"device_{i:03d}"
        vendor = template.get("vendor", "")
        device_type = template["type"]
        protocols = list(template["protocols"])

        # Look up vendor fingerprint for realistic identity
        fingerprint_data = None
        vendor_fps = get_fingerprints_by_vendor(vendor) if vendor else []
        if vendor_fps:
            # Pick a fingerprint appropriate for the device type
            for fp in vendor_fps:
                fp_type = (fp.get("device_type") or "").lower()
                if fp_type == device_type or not fp_type:
                    fingerprint_data = fp
                    break
            if not fingerprint_data:
                fingerprint_data = random.choice(vendor_fps)

        # Filter protocols to those with identity support in fingerprint
        if fingerprint_data:
            validated = []
            for proto in protocols:
                ik = PROTOCOL_TO_IDENTITY_KEY.get(proto)
                if ik and fingerprint_data.get(ik):
                    validated.append(proto)
                elif not ik:
                    validated.append(proto)
            protocols = validated or protocols[:1]

        # Generate MAC from fingerprint OUIs when available
        fp_ouis = fingerprint_data.get("oui_prefixes") if fingerprint_data else None
        mac = generate_mac(
            vendor=vendor, device_type=device_type,
            oui_patterns=fp_ouis if fp_ouis else None,
        )

        device_def: dict[str, Any] = {
            "id": device_id,
            "name": f"{device_type.upper()}_{i+1:02d}",
            "type": device_type,
            "vendor": vendor,
            "protocols": protocols,
            "position": {"x": 100 + (i % 5) * 150, "y": 100 + (i // 5) * 100},
            "zoneId": template["zone"],
            "network": {
                "macAddress": mac,
                "ipAddress": "",
                "subnetMask": "255.255.255.0",
            },
        }
        if fingerprint_data:
            device_def["vendorFingerprint"] = fingerprint_data
            device_def["fingerprint_model"] = fingerprint_data.get("model")

        devices[device_id] = device_def

    # Generate zones
    zone_ids = sorted(set(d["zoneId"] for d in devices.values()))
    zones: dict[str, dict[str, Any]] = {}
    for idx, zid in enumerate(zone_ids):
        zones[zid] = {
            "id": zid,
            "name": zid.replace("_", " ").title(),
            "type": "network",
            "position": {"x": 50, "y": 50 + idx * 450},
            "dimensions": {"width": 800, "height": 400},
            "deviceIds": [did for did, d in devices.items() if d["zoneId"] == zid],
        }

    # Use SmartFlowGenerator for realistic role-based flows
    device_list = list(devices.values())
    raw_flows = generate_flows_for_scenario(device_list, pattern="realistic")

    # Remap from GeneratedFlow.to_dict() keys to scenario definition format
    flows: dict[str, dict[str, Any]] = {}
    for f in raw_flows:
        fid = f["flow_id"]
        flows[fid] = {
            "id": fid,
            "name": f"{f['protocol']} poll",
            "sourceDeviceId": f["source_id"],
            "targetDeviceId": f["destination_id"],
            "protocol": f["protocol"],
            "timing": {"intervalMs": f.get("poll_rate", 1000), "jitterMs": 50},
            "protocolConfig": {},
        }

    # Create scenario
    scenario = Scenario(
        user_id=uuid.UUID(user_id),
        name=f"Generated {vertical.replace('_', ' ').title()} Scenario",
        description=f"AI-generated {vertical.replace('_', ' ')} scenario with {device_count} devices",
        vertical=vertical,
        total_duration_ms=duration_ms,
        definition={
            "devices": devices,
            "flows": flows,
            "zones": zones,
            "phases": [],
            "events": [],
        },
        version=1,
    )

    db.add(scenario)
    await db.flush()

    # Enrich devices with unique serial numbers and protocol identity names
    for dev_id, dev in devices.items():
        enrich_device_serial_numbers(dev, dev_id, str(scenario.id))
        enrich_device_unique_identifiers(dev, dev_id, str(scenario.id))

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "scenario_id": str(scenario.id),
        "device_count": len(devices),
        "flow_count": len(flows),
    })


# Phase presets
PHASE_PRESETS = {
    "startup_shutdown": {
        "name": "Startup & Shutdown",
        "description": "Basic startup and shutdown phases",
        "phases": [
            {
                "name": "Startup",
                "start_ms": 0,
                "duration_ms": 10000,
                "intensity": 0.3,
                "ramp_up_ms": 5000,
                "ramp_down_ms": 0,
                "flow_filter": {"startup": True},
            },
            {
                "name": "Steady State",
                "start_ms": 10000,
                "duration_ms": None,  # Until end
                "intensity": 1.0,
                "ramp_up_ms": 0,
                "ramp_down_ms": 0,
                "flow_filter": {"steadyState": True},
            },
            {
                "name": "Shutdown",
                "start_ms": -10000,  # Relative to end
                "duration_ms": 10000,
                "intensity": 0.3,
                "ramp_up_ms": 0,
                "ramp_down_ms": 5000,
                "flow_filter": {"shutdown": True},
            },
        ],
    },
    "maintenance_window": {
        "name": "Maintenance Window",
        "description": "Includes maintenance phase with reduced traffic",
        "phases": [
            {
                "name": "Normal Operation",
                "start_ms": 0,
                "duration_ms": 30000,
                "intensity": 1.0,
            },
            {
                "name": "Maintenance Prep",
                "start_ms": 30000,
                "duration_ms": 5000,
                "intensity": 0.5,
                "ramp_down_ms": 3000,
            },
            {
                "name": "Maintenance",
                "start_ms": 35000,
                "duration_ms": 20000,
                "intensity": 0.2,
                "flow_filter": {"maintenance": True},
            },
            {
                "name": "Recovery",
                "start_ms": 55000,
                "duration_ms": 5000,
                "intensity": 0.7,
                "ramp_up_ms": 3000,
            },
        ],
    },
    "shift_change": {
        "name": "Shift Change",
        "description": "Traffic patterns for shift changes",
        "phases": [
            {
                "name": "End of Shift",
                "start_ms": 0,
                "duration_ms": 10000,
                "intensity": 0.8,
                "ramp_down_ms": 5000,
            },
            {
                "name": "Handover",
                "start_ms": 10000,
                "duration_ms": 5000,
                "intensity": 0.4,
            },
            {
                "name": "New Shift Startup",
                "start_ms": 15000,
                "duration_ms": 10000,
                "intensity": 0.9,
                "ramp_up_ms": 7000,
            },
        ],
    },
    "incident_response": {
        "name": "Incident Response",
        "description": "Simulates an incident and response",
        "phases": [
            {
                "name": "Normal",
                "start_ms": 0,
                "duration_ms": 20000,
                "intensity": 1.0,
            },
            {
                "name": "Incident",
                "start_ms": 20000,
                "duration_ms": 10000,
                "intensity": 1.5,  # Spike in traffic
            },
            {
                "name": "Isolation",
                "start_ms": 30000,
                "duration_ms": 5000,
                "intensity": 0.3,
            },
            {
                "name": "Recovery",
                "start_ms": 35000,
                "duration_ms": 15000,
                "intensity": 0.7,
                "ramp_up_ms": 10000,
            },
        ],
    },
}


async def apply_phase_preset(
    db: AsyncSession,
    scenario_id: str,
    preset_name: str,
) -> str:
    """Apply a predefined phase configuration preset.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        preset_name: Preset name (startup_shutdown, maintenance_window, shift_change, incident_response)

    Returns:
        JSON string with result
    """
    if preset_name not in PHASE_PRESETS:
        return json.dumps({
            "error": f"Unknown preset '{preset_name}'. Available presets: {list(PHASE_PRESETS.keys())}"
        })

    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    preset = PHASE_PRESETS[preset_name]
    definition = scenario.definition.copy()

    # Generate phases from preset
    phases = []
    for i, phase_template in enumerate(preset["phases"]):
        phase_id = f"phase_{uuid.uuid4().hex[:8]}"
        phase = {
            "id": phase_id,
            "name": phase_template["name"],
            "start_ms": phase_template["start_ms"],
            "duration_ms": phase_template.get("duration_ms"),
            "intensity": phase_template.get("intensity", 1.0),
            "ramp_up_ms": phase_template.get("ramp_up_ms", 0),
            "ramp_down_ms": phase_template.get("ramp_down_ms", 0),
            "flow_filter": phase_template.get("flow_filter"),
            "order": i,
        }
        phases.append(phase)

    definition["phases"] = phases
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "preset_name": preset_name,
        "preset_description": preset["description"],
        "phases_created": len(phases),
        "phase_names": [p["name"] for p in phases],
    })


async def update_phase_timing(
    db: AsyncSession,
    scenario_id: str,
    phase_id: str,
    start_ms: int | None = None,
    duration_ms: int | None = None,
    intensity: float | None = None,
    ramp_up_ms: int | None = None,
    ramp_down_ms: int | None = None,
) -> str:
    """Modify phase timing parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        phase_id: Phase ID
        start_ms: New start time in milliseconds
        duration_ms: New duration in milliseconds
        intensity: Traffic intensity multiplier (0.0-2.0)
        ramp_up_ms: Ramp up duration in milliseconds
        ramp_down_ms: Ramp down duration in milliseconds

    Returns:
        JSON string with result
    """
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    phases = definition.get("phases", [])

    # Find and update the phase
    phase_found = False
    for i, phase in enumerate(phases):
        if phase.get("id") == phase_id:
            phase_found = True
            updated_phase = phase.copy()

            if start_ms is not None:
                updated_phase["start_ms"] = start_ms
            if duration_ms is not None:
                updated_phase["duration_ms"] = duration_ms
            if intensity is not None:
                updated_phase["intensity"] = intensity
            if ramp_up_ms is not None:
                updated_phase["ramp_up_ms"] = ramp_up_ms
            if ramp_down_ms is not None:
                updated_phase["ramp_down_ms"] = ramp_down_ms

            phases[i] = updated_phase
            break

    if not phase_found:
        return json.dumps({"error": f"Phase {phase_id} not found"})

    definition["phases"] = phases
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "phase_id": phase_id,
        "updated_fields": {
            k: v for k, v in {
                "start_ms": start_ms,
                "duration_ms": duration_ms,
                "intensity": intensity,
                "ramp_up_ms": ramp_up_ms,
                "ramp_down_ms": ramp_down_ms,
            }.items() if v is not None
        },
    })


async def reorder_phases(
    db: AsyncSession,
    scenario_id: str,
    phase_ids_in_order: list[str],
) -> str:
    """Change phase execution order.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        phase_ids_in_order: List of phase IDs in desired order

    Returns:
        JSON string with result
    """
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    phases = definition.get("phases", [])

    # Build phase lookup
    phase_map = {p.get("id"): p for p in phases}

    # Validate all phase IDs exist
    missing = [pid for pid in phase_ids_in_order if pid not in phase_map]
    if missing:
        return json.dumps({"error": f"Phase IDs not found: {missing}"})

    # Reorder phases
    reordered_phases = []
    for i, phase_id in enumerate(phase_ids_in_order):
        phase = phase_map[phase_id].copy()
        phase["order"] = i
        reordered_phases.append(phase)

    # Add any phases not in the reorder list at the end
    for phase_id, phase in phase_map.items():
        if phase_id not in phase_ids_in_order:
            phase_copy = phase.copy()
            phase_copy["order"] = len(reordered_phases)
            reordered_phases.append(phase_copy)

    definition["phases"] = reordered_phases
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "phase_count": len(reordered_phases),
        "new_order": [p.get("id") for p in reordered_phases],
    })


async def list_phase_presets() -> str:
    """List available phase presets.

    Returns:
        JSON string with available presets
    """
    presets = []
    for name, preset in PHASE_PRESETS.items():
        presets.append({
            "name": name,
            "display_name": preset["name"],
            "description": preset["description"],
            "phase_count": len(preset["phases"]),
            "phase_names": [p["name"] for p in preset["phases"]],
        })

    return json.dumps({
        "presets": presets,
        "count": len(presets),
    })
