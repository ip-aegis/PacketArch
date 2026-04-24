# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""External communication tools for MCP.

This module provides tools for:
- Adding external communications (C2 beacons, DNS tunnels, HTTP exfil, exploits, scans)
- Listing external communications in a scenario
- Removing external communications
"""

import json
import uuid as uuid_module
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.scenario import Scenario


# MITRE ATT&CK for ICS technique mapping
MITRE_TECHNIQUE_MAP = {
    "c2_beacon": {"id": "T0885", "name": "Commonly Used Port"},
    "dns_tunnel": {"id": "T0884", "name": "Connection Proxy"},
    "http_exfil": {"id": "T0882", "name": "Theft of Operational Information"},
    "exploit": {"id": "T0869", "name": "Exploitation of Remote Services"},
    "port_scan": {"id": "T0846", "name": "Remote System Discovery"},
}

# Valid external communication types
VALID_COMM_TYPES = ["c2_beacon", "dns_tunnel", "http_exfil", "exploit", "port_scan"]

# Available C2 patterns
C2_PATTERNS = [
    "jittered_1m",
    "jittered_5m",
    "jittered_10m",
    "exponential_backoff",
    "regular_1m",
    "working_hours",
]

# Available exploit patterns
EXPLOIT_PATTERNS = [
    "buffer_overflow_generic",
    "command_injection",
    "sql_injection",
    "path_traversal",
    "modbus_force_listen_only",
    "modbus_restart_comms",
    "enip_firmware_upload",
]


async def add_external_communication(
    db: AsyncSession,
    scenario_id: str,
    comm_type: str,
    source_device_id: str,
    destination_ip: str | None = None,
    start_time_ms: float = 0,
    duration_ms: float = 300000,
    c2_pattern: str | None = None,
    c2_protocol: str = "http",
    beacon_count: int = 10,
    exfil_data_size: int = 1024,
    exploit_pattern: str | None = None,
    scan_ot_ports: bool = True,
    mitre_technique: str | None = None,
) -> str:
    """Add external communication to a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        comm_type: Type of communication (c2_beacon, dns_tunnel, http_exfil, exploit, port_scan)
        source_device_id: Device ID that initiates the communication
        destination_ip: External destination IP (auto-generated if not specified)
        start_time_ms: Start time in scenario timeline
        duration_ms: Duration of the communication
        c2_pattern: C2 beaconing pattern (for c2_beacon type)
        c2_protocol: Protocol for C2 (http, https, dns)
        beacon_count: Number of beacons (for c2_beacon type)
        exfil_data_size: Size of exfiltrated data in bytes (for exfil types)
        exploit_pattern: Exploit pattern name (for exploit type)
        scan_ot_ports: Scan OT-specific ports (for port_scan type)
        mitre_technique: Override MITRE ATT&CK technique ID

    Returns:
        JSON string with result
    """
    if comm_type not in VALID_COMM_TYPES:
        return json.dumps({
            "error": f"Invalid comm_type '{comm_type}'. Valid types: {VALID_COMM_TYPES}"
        })

    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid_module.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if source_device_id not in devices:
        return json.dumps({"error": f"Device {source_device_id} not found"})

    # Initialize external_communications if not present
    if "external_communications" not in definition:
        definition["external_communications"] = {}

    # Generate communication ID
    comm_id = f"ext_{str(uuid_module.uuid4())[:8]}"

    # Get source device IP for internal device reference
    source_device = devices[source_device_id]
    source_ip = source_device.get("network", {}).get("ipAddress", "10.0.0.10")

    # Get MITRE technique
    technique = MITRE_TECHNIQUE_MAP.get(comm_type, {})
    if mitre_technique:
        technique = {"id": mitre_technique, "name": "Custom"}

    # Build communication configuration
    comm_config: dict[str, Any] = {
        "id": comm_id,
        "type": comm_type,
        "source_device_id": source_device_id,
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "start_time_ms": start_time_ms,
        "duration_ms": duration_ms,
        "mitre_technique": technique,
    }

    # Type-specific configuration
    if comm_type == "c2_beacon":
        comm_config["c2_pattern"] = c2_pattern or "jittered_1m"
        comm_config["c2_protocol"] = c2_protocol
        comm_config["beacon_count"] = beacon_count

    elif comm_type in ("dns_tunnel", "http_exfil"):
        comm_config["exfil_protocol"] = "dns" if comm_type == "dns_tunnel" else "http"
        comm_config["exfil_data_size"] = exfil_data_size

    elif comm_type == "exploit":
        comm_config["exploit_pattern"] = exploit_pattern or "buffer_overflow_generic"

    elif comm_type == "port_scan":
        comm_config["scan_type"] = "syn"
        comm_config["scan_ot_ports"] = scan_ot_ports

    definition["external_communications"][comm_id] = comm_config

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "external_comm_id": comm_id,
        "type": comm_type,
        "source_device_id": source_device_id,
        "mitre_technique": technique,
    })


async def list_external_communications(
    db: AsyncSession,
    scenario_id: str,
    type_filter: str | None = None,
) -> str:
    """List external communications in a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        type_filter: Optional filter by communication type

    Returns:
        JSON string with external communications list
    """
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid_module.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition or {}
    external_comms = definition.get("external_communications", {})

    comm_list = []
    for comm_id, comm in external_comms.items():
        if type_filter and comm.get("type") != type_filter:
            continue

        comm_list.append({
            "id": comm_id,
            "type": comm.get("type"),
            "source_device_id": comm.get("source_device_id"),
            "source_ip": comm.get("source_ip"),
            "destination_ip": comm.get("destination_ip"),
            "start_time_ms": comm.get("start_time_ms"),
            "duration_ms": comm.get("duration_ms"),
            "mitre_technique": comm.get("mitre_technique"),
        })

    # Also list available patterns for reference
    return json.dumps({
        "external_communications": comm_list,
        "count": len(comm_list),
        "available_types": VALID_COMM_TYPES,
        "available_c2_patterns": C2_PATTERNS,
        "available_exploit_patterns": EXPLOIT_PATTERNS,
    })


async def remove_external_communication(
    db: AsyncSession,
    scenario_id: str,
    external_comm_id: str,
) -> str:
    """Remove an external communication from a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        external_comm_id: External communication ID

    Returns:
        JSON string with result
    """
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid_module.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    external_comms = definition.get("external_communications", {})

    if external_comm_id not in external_comms:
        return json.dumps({"error": f"External communication {external_comm_id} not found"})

    removed_comm = external_comms.pop(external_comm_id)
    definition["external_communications"] = external_comms

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "removed_comm_id": external_comm_id,
        "removed_type": removed_comm.get("type"),
    })


async def get_external_comm_patterns() -> str:
    """Get available external communication patterns.

    Returns:
        JSON string with available patterns
    """
    return json.dumps({
        "communication_types": [
            {
                "type": "c2_beacon",
                "description": "Command & Control beaconing to external server",
                "mitre": MITRE_TECHNIQUE_MAP["c2_beacon"],
            },
            {
                "type": "dns_tunnel",
                "description": "Data exfiltration via DNS tunneling",
                "mitre": MITRE_TECHNIQUE_MAP["dns_tunnel"],
            },
            {
                "type": "http_exfil",
                "description": "Data exfiltration via HTTP POST requests",
                "mitre": MITRE_TECHNIQUE_MAP["http_exfil"],
            },
            {
                "type": "exploit",
                "description": "Exploit attempt against OT device",
                "mitre": MITRE_TECHNIQUE_MAP["exploit"],
            },
            {
                "type": "port_scan",
                "description": "Reconnaissance port scanning",
                "mitre": MITRE_TECHNIQUE_MAP["port_scan"],
            },
        ],
        "c2_patterns": [
            {"name": "jittered_1m", "description": "~1 minute intervals with jitter"},
            {"name": "jittered_5m", "description": "~5 minute intervals with jitter"},
            {"name": "jittered_10m", "description": "~10 minute intervals with jitter"},
            {"name": "exponential_backoff", "description": "Increasing intervals"},
            {"name": "regular_1m", "description": "Fixed 1 minute intervals"},
            {"name": "working_hours", "description": "Only during business hours"},
        ],
        "exploit_patterns": [
            {"name": "buffer_overflow_generic", "description": "Generic buffer overflow attempt"},
            {"name": "command_injection", "description": "Command injection attack"},
            {"name": "sql_injection", "description": "SQL injection attack"},
            {"name": "path_traversal", "description": "Path traversal attack"},
            {"name": "modbus_force_listen_only", "description": "Modbus Force Listen Only Mode"},
            {"name": "modbus_restart_comms", "description": "Modbus Restart Communications"},
            {"name": "enip_firmware_upload", "description": "EtherNet/IP firmware upload attack"},
        ],
    })
