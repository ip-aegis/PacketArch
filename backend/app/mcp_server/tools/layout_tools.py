# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Canvas layout tools for MCP.

This module provides tools for:
- Setting device positions on the canvas
- Setting zone bounds and dimensions
- Auto-layouting scenarios
- Moving devices into zones
"""

import json
import math
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.scenario import Scenario


async def set_device_position(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    x: float,
    y: float,
) -> str:
    """Set exact X/Y coordinates for a device on the canvas.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        x: X coordinate
        y: Y coordinate

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
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()
    device["position"] = {"x": x, "y": y}
    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "position": {"x": x, "y": y},
    })


async def set_zone_bounds(
    db: AsyncSession,
    scenario_id: str,
    zone_id: str,
    x: float,
    y: float,
    width: float,
    height: float,
) -> str:
    """Set zone position and dimensions.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        zone_id: Zone ID
        x: X coordinate of top-left corner
        y: Y coordinate of top-left corner
        width: Zone width
        height: Zone height

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
    zones = definition.get("zones", {})

    if zone_id not in zones:
        return json.dumps({"error": f"Zone {zone_id} not found"})

    zone = zones[zone_id].copy()
    zone["position"] = {"x": x, "y": y}
    zone["dimensions"] = {"width": width, "height": height}
    zones[zone_id] = zone
    definition["zones"] = zones

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "zone_id": zone_id,
        "position": {"x": x, "y": y},
        "dimensions": {"width": width, "height": height},
    })


async def auto_layout_scenario(
    db: AsyncSession,
    scenario_id: str,
    layout_type: str = "hierarchical",
    spacing: float = 150,
) -> str:
    """Automatically arrange all devices using layout algorithms.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        layout_type: Layout algorithm - 'hierarchical', 'grid', 'circular', 'zone_grouped'
        spacing: Spacing between devices in pixels

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
    devices = definition.get("devices", {})
    zones = definition.get("zones", {})
    flows = definition.get("flows", {})

    if not devices:
        return json.dumps({"error": "No devices to layout"})

    device_ids = list(devices.keys())
    positions = {}

    if layout_type == "grid":
        # Simple grid layout
        cols = max(1, int(math.ceil(math.sqrt(len(device_ids)))))
        for i, device_id in enumerate(device_ids):
            row = i // cols
            col = i % cols
            positions[device_id] = {
                "x": 100 + col * spacing,
                "y": 100 + row * spacing,
            }

    elif layout_type == "circular":
        # Circular layout
        center_x = 400
        center_y = 400
        radius = max(200, len(device_ids) * spacing / (2 * math.pi))
        for i, device_id in enumerate(device_ids):
            angle = (2 * math.pi * i) / len(device_ids)
            positions[device_id] = {
                "x": center_x + radius * math.cos(angle),
                "y": center_y + radius * math.sin(angle),
            }

    elif layout_type == "zone_grouped":
        # Group devices by zone
        zone_devices: dict[str, list[str]] = {}
        unzoned_devices: list[str] = []

        for device_id, device in devices.items():
            zone_id = device.get("zone")
            if zone_id and zone_id in zones:
                if zone_id not in zone_devices:
                    zone_devices[zone_id] = []
                zone_devices[zone_id].append(device_id)
            else:
                unzoned_devices.append(device_id)

        # Position zones and devices within them
        zone_x = 100
        zone_y = 100
        zone_spacing = 400

        for zone_id, zone_device_ids in zone_devices.items():
            zone = zones[zone_id].copy()
            zone_width = max(300, len(zone_device_ids) * 100)
            zone_height = 300

            zone["position"] = {"x": zone_x, "y": zone_y}
            zone["dimensions"] = {"width": zone_width, "height": zone_height}
            zones[zone_id] = zone

            # Position devices within zone
            for i, device_id in enumerate(zone_device_ids):
                positions[device_id] = {
                    "x": zone_x + 50 + (i * 100),
                    "y": zone_y + 100,
                }

            zone_y += zone_spacing

        # Position unzoned devices
        for i, device_id in enumerate(unzoned_devices):
            positions[device_id] = {
                "x": zone_x + zone_spacing + (i % 4) * spacing,
                "y": 100 + (i // 4) * spacing,
            }

        definition["zones"] = zones

    else:  # hierarchical
        # Build device hierarchy based on flows
        # Find devices with no incoming flows (sources)
        incoming: dict[str, list[str]] = {d: [] for d in device_ids}
        outgoing: dict[str, list[str]] = {d: [] for d in device_ids}

        for flow in flows.values():
            source = flow.get("source")
            target = flow.get("target")
            if source in device_ids and target in device_ids:
                outgoing[source].append(target)
                incoming[target].append(source)

        # Find root devices (no incoming connections)
        roots = [d for d in device_ids if not incoming[d]]
        if not roots:
            roots = device_ids[:1]  # Fallback to first device

        # BFS to assign levels
        levels: dict[str, int] = {}
        visited = set()
        queue = [(r, 0) for r in roots]

        while queue:
            device_id, level = queue.pop(0)
            if device_id in visited:
                continue
            visited.add(device_id)
            levels[device_id] = level
            for target in outgoing.get(device_id, []):
                if target not in visited:
                    queue.append((target, level + 1))

        # Assign unvisited devices to level 0
        for device_id in device_ids:
            if device_id not in levels:
                levels[device_id] = 0

        # Group by level
        level_devices: dict[int, list[str]] = {}
        for device_id, level in levels.items():
            if level not in level_devices:
                level_devices[level] = []
            level_devices[level].append(device_id)

        # Position devices
        for level, level_device_ids in level_devices.items():
            for i, device_id in enumerate(level_device_ids):
                positions[device_id] = {
                    "x": 100 + level * spacing * 1.5,
                    "y": 100 + i * spacing,
                }

    # Apply positions to devices
    for device_id, pos in positions.items():
        device = devices[device_id].copy()
        device["position"] = pos
        devices[device_id] = device

    definition["devices"] = devices
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "layout_type": layout_type,
        "devices_positioned": len(positions),
        "positions": positions,
    })


async def move_devices_to_zone(
    db: AsyncSession,
    scenario_id: str,
    device_ids: list[str],
    zone_id: str,
    auto_position: bool = True,
) -> str:
    """Move multiple devices into a zone with optional auto-positioning.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_ids: List of device IDs to move
        zone_id: Target zone ID
        auto_position: Whether to auto-position devices within zone

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
    devices = definition.get("devices", {})
    zones = definition.get("zones", {})

    if zone_id not in zones:
        return json.dumps({"error": f"Zone {zone_id} not found"})

    zone = zones[zone_id]
    zone_pos = zone.get("position", {"x": 100, "y": 100})
    zone_dims = zone.get("dimensions", {"width": 400, "height": 300})

    moved_devices = []
    not_found = []

    for i, device_id in enumerate(device_ids):
        if device_id not in devices:
            not_found.append(device_id)
            continue

        device = devices[device_id].copy()
        device["zone"] = zone_id

        if auto_position:
            # Position devices in a grid within the zone
            cols = max(1, int(zone_dims["width"] / 120))
            row = i // cols
            col = i % cols
            device["position"] = {
                "x": zone_pos["x"] + 50 + col * 100,
                "y": zone_pos["y"] + 60 + row * 80,
            }

        devices[device_id] = device
        moved_devices.append(device_id)

    definition["devices"] = devices
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    result_data = {
        "success": True,
        "zone_id": zone_id,
        "moved_devices": moved_devices,
        "count": len(moved_devices),
    }

    if not_found:
        result_data["not_found"] = not_found

    return json.dumps(result_data)
