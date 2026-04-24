# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""AI scenario generation business logic.

Template helpers, preview generation, and scenario creation from templates/previews.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.scenario_templates import get_template, list_templates, list_verticals

logger = logging.getLogger(__name__)


def list_templates_filtered(vertical: str | None = None) -> list[dict]:
    """List templates with optional vertical filter."""
    templates = list_templates()
    if vertical:
        templates = [t for t in templates if t["vertical"] == vertical]
    return templates


def get_template_preview(vertical: str, template_name: str) -> dict:
    """Get detailed template preview."""
    template = get_template(vertical, template_name)
    if not template:
        return {"error": f"Template '{template_name}' not found for vertical '{vertical}'"}

    return {
        "name": template.get("name", template_name),
        "description": template.get("description", ""),
        "vertical": vertical,
        "devices": template.get("devices", []),
        "flows": template.get("flows", []),
        "zones": template.get("zones", []),
        "total_duration_ms": template.get("total_duration_ms", 300000),
        "device_count": sum(d.get("count", 1) for d in template.get("devices", [])),
        "flow_count": len(template.get("flows", [])),
        "zone_count": len(template.get("zones", [])),
    }


async def create_from_template(
    db: AsyncSession,
    user_id: str | None,
    vertical: str,
    template_name: str,
    scenario_name: str,
    description: str,
    total_duration_ms: int,
) -> dict:
    """Create scenario from template.

    Args:
        db: Database session
        user_id: Current user ID
        vertical: Industry vertical
        template_name: Template name
        scenario_name: Name for the new scenario
        description: Optional description
        total_duration_ms: Scenario duration

    Returns:
        Dict with scenario info
    """
    import uuid as uuid_module
    from app.models.scenario import Scenario
    from app.services.ip_management import IPManagementService
    from app.protocol_engines.vendor_oui import generate_mac_address
    from app.scenario_templates.phases import get_default_phases

    template = get_template(vertical, template_name)
    if not template:
        return {"error": f"Template '{template_name}' not found for vertical '{vertical}'"}

    # Create scenario
    scenario_id = uuid_module.uuid4()

    # Build zones
    zones = {}
    for i, zone_spec in enumerate(template.get("zones", [])):
        zone_id = zone_spec.get("id", f"zone_{i}")
        zones[zone_id] = {
            "id": zone_id,
            "name": zone_spec.get("name", zone_id),
            "level": zone_spec.get("level", 1),
            "network": {
                "subnet": zone_spec.get("subnet", f"10.1.{i}.0/24"),
                "vlan": zone_spec.get("vlan"),
            },
        }

    # Build devices
    devices = {}
    device_index = 0
    devices_by_type: dict[str, list[str]] = {}

    for device_spec in template.get("devices", []):
        count = device_spec.get("count", 1)
        for _ in range(count):
            device_index += 1
            device_id = f"device_{device_index:03d}"

            name_pattern = device_spec.get("name_pattern", "{type}-{n:03d}")
            try:
                name = name_pattern.format(n=device_index, **device_spec)
            except KeyError:
                name = f"{device_spec.get('type', 'device')}-{device_index:03d}"

            device = {
                "id": device_id,
                "name": name,
                "type": device_spec.get("type", "plc"),
                "protocols": device_spec.get("protocols", []),
                "zoneId": device_spec.get("zone"),
                "vendor": device_spec.get("vendor"),
                "fingerprintModel": device_spec.get("fingerprint_model"),
                "network": {
                    "macAddress": generate_mac_address(
                        vendor=device_spec.get("vendor"),
                        device_type=device_spec.get("type"),
                    ),
                },
            }

            if device_spec.get("role"):
                device["role"] = device_spec.get("role")

            devices[device_id] = device

            # Track by type for flow generation
            dtype = device_spec.get("type", "unknown")
            if dtype not in devices_by_type:
                devices_by_type[dtype] = []
            devices_by_type[dtype].append(device_id)

    # Build flows
    flows = {}
    flow_index = 0
    for flow_spec in template.get("flows", []):
        source_types = flow_spec.get("source_types", [])
        target_types = flow_spec.get("target_types", [])
        protocol = flow_spec.get("protocol")

        for source_type in source_types:
            for target_type in target_types:
                source_devices = devices_by_type.get(source_type, [])
                target_devices = devices_by_type.get(target_type, [])

                if not source_devices or not target_devices:
                    continue

                n_flows = max(len(source_devices), len(target_devices))
                for i in range(n_flows):
                    source_id = source_devices[i % len(source_devices)]
                    target_id = target_devices[i % len(target_devices)]

                    if source_id != target_id:
                        flow_index += 1
                        flow_id = f"flow_{flow_index:03d}"
                        flows[flow_id] = {
                            "id": flow_id,
                            "sourceDeviceId": source_id,
                            "targetDeviceId": target_id,
                            "protocol": protocol,
                            "timing": {"intervalMs": flow_spec.get("interval_ms", 1000)},
                        }

    # Generate phases
    phases = get_default_phases(total_duration_ms=total_duration_ms, preset="standard", vertical=vertical)

    # Allocate IP range and assign addresses
    try:
        allocation = await IPManagementService.allocate_range(db, scenario_id)
        range_idx = allocation.range_index

        # Update zone subnets
        for i, zone_id in enumerate(zones):
            zones[zone_id]["network"]["subnet"] = f"10.{range_idx}.{i}.0/24"

        # Assign IPs to devices
        devices_by_zone: dict[str, list[str]] = {}
        for device_id, device in devices.items():
            zone_id = device.get("zoneId", "default")
            if zone_id not in devices_by_zone:
                devices_by_zone[zone_id] = []
            devices_by_zone[zone_id].append(device_id)

        for zone_id, device_ids in devices_by_zone.items():
            zone = zones.get(zone_id, {})
            subnet = zone.get("network", {}).get("subnet", f"10.{range_idx}.0.0/24")
            base = ".".join(subnet.split("/")[0].split(".")[:3])

            for j, device_id in enumerate(device_ids, start=10):
                devices[device_id]["network"]["ipAddress"] = f"{base}.{j}"
                devices[device_id]["network"]["subnetMask"] = "255.255.255.0"
                devices[device_id]["network"]["gateway"] = f"{base}.1"

        addressing_config = {
            "ip_range": allocation.cidr_range,
            "range_index": range_idx,
            "auto_assign_enabled": True,
        }
    except Exception:
        addressing_config = None

    # Create scenario model
    scenario = Scenario(
        id=scenario_id,
        name=scenario_name,
        description=description or template.get("description", ""),
        vertical=vertical,
        total_duration_ms=total_duration_ms,
        definition={"devices": devices, "flows": flows, "zones": zones, "phases": phases},
        user_id=uuid_module.UUID(user_id) if user_id else None,
        version=1,
    )

    if addressing_config:
        scenario.addressing_config = addressing_config

    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)

    return {
        "scenario_id": str(scenario.id),
        "name": scenario.name,
        "device_count": len(devices),
        "flow_count": len(flows),
        "zone_count": len(zones),
        "phase_count": len(phases),
        "vertical": vertical,
        "template": template_name,
    }
