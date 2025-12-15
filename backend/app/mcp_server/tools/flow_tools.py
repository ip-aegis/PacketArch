"""Flow manipulation tools for MCP."""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.scenario import Scenario


async def list_flows(db: AsyncSession, scenario_id: str) -> str:
    """List all flows in a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string of flows
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    flows = scenario.definition.get("flows", {})
    return json.dumps({"flows": flows, "count": len(flows)})


async def get_flow(db: AsyncSession, scenario_id: str, flow_id: str) -> str:
    """Get details of a specific flow.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID

    Returns:
        JSON string of flow details
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    flows = scenario.definition.get("flows", {})
    flow = flows.get(flow_id)

    if not flow:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    return json.dumps({"flow": flow})


async def add_flow(db: AsyncSession, scenario_id: str, flow_data: dict[str, Any]) -> str:
    """Add a flow to a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_data: Flow configuration

    Returns:
        JSON string with flow ID
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    # Validate that source and target devices exist
    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    source_id = flow_data.get("sourceDeviceId")
    target_id = flow_data.get("targetDeviceId")

    if source_id not in devices:
        return json.dumps({"error": f"Source device {source_id} not found"})

    if target_id not in devices:
        return json.dumps({"error": f"Target device {target_id} not found"})

    # Generate flow ID if not provided
    flow_id = flow_data.get("id") or f"flow_{uuid.uuid4().hex[:8]}"

    # Get or initialize flows dict
    flows = definition.get("flows", {})

    # Add flow
    flows[flow_id] = flow_data
    definition["flows"] = flows

    # Update scenario - use flag_modified to ensure JSONB change is detected
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({"success": True, "flow_id": flow_id})


async def update_flow(
    db: AsyncSession, scenario_id: str, flow_id: str, updates: dict[str, Any]
) -> str:
    """Update a flow in a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        updates: Updates to apply

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    # Merge updates
    flow = flows[flow_id].copy()
    flow.update(updates)
    flows[flow_id] = flow
    definition["flows"] = flows

    # Update scenario - use flag_modified to ensure JSONB change is detected
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({"success": True, "flow_id": flow_id})


async def remove_flow(db: AsyncSession, scenario_id: str, flow_id: str) -> str:
    """Remove a flow from a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    # Remove flow
    del flows[flow_id]
    definition["flows"] = flows

    # Update scenario - use flag_modified to ensure JSONB change is detected
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({"success": True, "flow_id": flow_id})


async def suggest_flows(db: AsyncSession, scenario_id: str, source_device_id: str) -> str:
    """AI suggests flows for a device based on its type and role.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        source_device_id: Source device ID

    Returns:
        JSON string with suggested flows
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition
    devices = definition.get("devices", {})

    source_device = devices.get(source_device_id)
    if not source_device:
        return json.dumps({"error": f"Source device {source_device_id} not found"})

    source_type = source_device.get("type")
    source_protocols = source_device.get("protocols", [])

    suggested_flows = []

    # Find compatible target devices
    for device_id, device in devices.items():
        if device_id == source_device_id:
            continue

        device_type = device.get("type")
        device_protocols = device.get("protocols", [])

        # Find common protocols
        common_protocols = set(source_protocols) & set(device_protocols)

        if not common_protocols:
            continue

        # Suggest flows based on device types
        if source_type == "plc" and device_type == "hmi":
            for protocol in common_protocols:
                suggested_flows.append({
                    "name": f"PLC to HMI - {protocol.upper()}",
                    "sourceDeviceId": source_device_id,
                    "targetDeviceId": device_id,
                    "protocol": protocol,
                    "timing": {"intervalMs": 1000, "jitterMs": 50},
                    "protocolConfig": {},
                })

        elif source_type == "sensor" and device_type in ["plc", "rtu"]:
            for protocol in common_protocols:
                suggested_flows.append({
                    "name": f"Sensor to {device_type.upper()} - {protocol.upper()}",
                    "sourceDeviceId": source_device_id,
                    "targetDeviceId": device_id,
                    "protocol": protocol,
                    "timing": {"intervalMs": 5000, "jitterMs": 100},
                    "protocolConfig": {},
                })

        elif device_type == "historian":
            for protocol in common_protocols:
                suggested_flows.append({
                    "name": f"{source_type.upper()} to Historian - {protocol.upper()}",
                    "sourceDeviceId": source_device_id,
                    "targetDeviceId": device_id,
                    "protocol": protocol,
                    "timing": {"intervalMs": 60000, "jitterMs": 1000},
                    "protocolConfig": {},
                })

    return json.dumps({
        "suggested_flows": suggested_flows,
        "count": len(suggested_flows),
    })
