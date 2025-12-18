"""Device manipulation tools for MCP."""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scenario import Scenario
from app.mcp_server.tools.scenario_lock import safe_update_scenario

# Maximum number of devices allowed per scenario to prevent AI runaway
MAX_DEVICES_PER_SCENARIO = 100


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
    # Generate device ID upfront so we can reference it in the closure
    device_id = device_data.get("id") or f"device_{uuid.uuid4().hex[:8]}"

    def do_add_device(definition: dict) -> dict:
        """Inner function that modifies definition and returns result."""
        devices = definition.setdefault("devices", {})

        # Check device limit - return warning instead of error for better AI guidance
        if len(devices) >= MAX_DEVICES_PER_SCENARIO:
            return {
                "warning": f"Device limit reached ({MAX_DEVICES_PER_SCENARIO}). STOP adding devices.",
                "action": "Proceed to add flows or complete the scenario.",
                "current_count": len(devices),
                "max_allowed": MAX_DEVICES_PER_SCENARIO
            }

        # Ensure required fields are present for frontend/React Flow compatibility
        device_to_add = device_data.copy()
        device_to_add["id"] = device_id

        # Set default position if not provided (stagger based on device count)
        if "position" not in device_to_add:
            device_count = len(devices)
            device_to_add["position"] = {
                "x": 100 + (device_count % 5) * 200,
                "y": 100 + (device_count // 5) * 150
            }

        # Ensure network config exists
        if "network" not in device_to_add:
            device_to_add["network"] = {
                "macAddress": "",
                "ipAddress": "",
                "subnetMask": "255.255.255.0"
            }

        # Add device
        devices[device_id] = device_to_add
        return {"success": True, "device_id": device_id, "current_count": len(devices)}

    scenario, result = await safe_update_scenario(db, scenario_id, do_add_device)

    if scenario is None:
        return json.dumps({"error": "Scenario not found"})

    return json.dumps(result)


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
    def do_update_device(definition: dict) -> dict:
        """Inner function that modifies definition and returns result."""
        devices = definition.get("devices", {})

        if device_id not in devices:
            return {"error": f"Device {device_id} not found"}

        # Merge updates
        device = devices[device_id].copy()
        device.update(updates)
        devices[device_id] = device
        return {"success": True, "device_id": device_id}

    scenario, result = await safe_update_scenario(db, scenario_id, do_update_device)

    if scenario is None:
        return json.dumps({"error": "Scenario not found"})

    return json.dumps(result)


async def remove_device(db: AsyncSession, scenario_id: str, device_id: str) -> str:
    """Remove a device from a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID

    Returns:
        JSON string with result
    """
    removed_flows: list[str] = []

    def do_remove_device(definition: dict) -> dict:
        """Inner function that modifies definition and returns result."""
        nonlocal removed_flows
        devices = definition.get("devices", {})

        if device_id not in devices:
            return {"error": f"Device {device_id} not found"}

        # Remove device
        del devices[device_id]

        # Also remove flows involving this device
        flows = definition.get("flows", {})
        removed_flows = [
            flow_id
            for flow_id, flow in flows.items()
            if flow.get("sourceDeviceId") == device_id or flow.get("targetDeviceId") == device_id
        ]

        for flow_id in removed_flows:
            del flows[flow_id]

        return {"success": True, "device_id": device_id, "removed_flows": removed_flows}

    scenario, result = await safe_update_scenario(db, scenario_id, do_remove_device)

    if scenario is None:
        return json.dumps({"error": "Scenario not found"})

    return json.dumps(result)


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
