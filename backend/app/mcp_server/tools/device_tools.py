"""Device manipulation tools for MCP."""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.scenario import Scenario


async def list_devices(db: AsyncSession, scenario_id: str) -> str:
    """List all devices in a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string of devices
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    devices = scenario.definition.get("devices", {})
    return json.dumps({"devices": devices, "count": len(devices)})


async def get_device(db: AsyncSession, scenario_id: str, device_id: str) -> str:
    """Get details of a specific device.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID

    Returns:
        JSON string of device details
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    devices = scenario.definition.get("devices", {})
    device = devices.get(device_id)

    if not device:
        return json.dumps({"error": f"Device {device_id} not found"})

    return json.dumps({"device": device})


async def add_device(
    db: AsyncSession, scenario_id: str, device_data: dict[str, Any]
) -> str:
    """Add a device to a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_data: Device configuration

    Returns:
        JSON string with device ID
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    # Generate device ID if not provided
    device_id = device_data.get("id") or f"device_{uuid.uuid4().hex[:8]}"

    # Get or initialize devices dict
    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    # Add device
    devices[device_id] = device_data
    definition["devices"] = devices

    # Update scenario - use flag_modified to ensure JSONB change is detected
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({"success": True, "device_id": device_id})


async def update_device(
    db: AsyncSession, scenario_id: str, device_id: str, updates: dict[str, Any]
) -> str:
    """Update a device in a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        updates: Updates to apply

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    # Merge updates
    device = devices[device_id].copy()
    device.update(updates)
    devices[device_id] = device
    definition["devices"] = devices

    # Update scenario - use flag_modified to ensure JSONB change is detected
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({"success": True, "device_id": device_id})


async def remove_device(db: AsyncSession, scenario_id: str, device_id: str) -> str:
    """Remove a device from a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    # Remove device
    del devices[device_id]
    definition["devices"] = devices

    # Also remove flows involving this device
    flows = definition.get("flows", {})
    flows_to_remove = [
        flow_id
        for flow_id, flow in flows.items()
        if flow.get("sourceDeviceId") == device_id or flow.get("targetDeviceId") == device_id
    ]

    for flow_id in flows_to_remove:
        del flows[flow_id]

    definition["flows"] = flows

    # Update scenario - use flag_modified to ensure JSONB change is detected
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps(
        {"success": True, "device_id": device_id, "removed_flows": flows_to_remove}
    )


async def suggest_device(
    db: AsyncSession, scenario_id: str, vertical: str, zone: str
) -> str:
    """AI suggests a device configuration for a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        vertical: Industry vertical
        zone: Zone name

    Returns:
        JSON string with suggested device
    """
    # This is a simplified suggestion - in production, this would use more sophisticated logic
    # or query device profiles

    device_suggestions = {
        "manufacturing": {
            "plant_floor": {
                "type": "plc",
                "name": "PLC Controller",
                "protocols": ["modbus_tcp", "ethernet_ip"],
                "role": "Controller",
            },
            "dmz": {
                "type": "historian",
                "name": "Data Historian",
                "protocols": ["opc_ua"],
                "role": "Data Collection",
            },
        },
        "water_wastewater": {
            "plant_floor": {
                "type": "rtu",
                "name": "Remote Terminal Unit",
                "protocols": ["dnp3", "modbus_tcp"],
                "role": "SCADA RTU",
            },
        },
        "energy_power": {
            "plant_floor": {
                "type": "relay",
                "name": "Protection Relay",
                "protocols": ["iec104", "dnp3"],
                "role": "Protection",
            },
        },
    }

    suggestion = (
        device_suggestions.get(vertical, {})
        .get(zone, {})
    )

    if not suggestion:
        suggestion = {
            "type": "plc",
            "name": "Generic PLC",
            "protocols": ["modbus_tcp"],
            "role": "Controller",
        }

    # Add default network configuration
    suggestion["network"] = {
        "macAddress": "",
        "ipAddress": "",
        "subnetMask": "255.255.255.0",
    }

    suggestion["position"] = {"x": 100, "y": 100}
    suggestion["zoneId"] = zone

    return json.dumps({"suggested_device": suggestion})
