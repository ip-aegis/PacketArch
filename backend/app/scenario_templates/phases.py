"""Phase templates for scenario timeline patterns."""

from typing import Any


# Standard phase templates
PHASE_TEMPLATES: dict[str, dict[str, Any]] = {
    "startup": {
        "id": "startup",
        "name": "System Startup",
        "description": "Initial system boot, connection establishment, and configuration download",
        "duration_pct": 5,  # 5% of total duration
        "traffic_multiplier": 0.1,  # 10% of normal traffic rate
        "color": "#52c41a",  # Green
        "behaviors": [
            "connection_establishment",
            "configuration_download",
            "initial_poll",
            "device_discovery",
            "time_sync",
        ],
        "protocol_patterns": {
            "profinet": "dcp_identify",
            "ethernet_ip": "register_session",
            "modbus_tcp": "initial_read",
            "opc_ua": "create_session",
            "dnp3": "cold_restart",
            "iec104": "startdt",
        },
    },
    "steady_state": {
        "id": "steady_state",
        "name": "Normal Operations",
        "description": "Standard cyclic I/O, periodic polling, and normal operational traffic",
        "duration_pct": 80,  # 80% of total duration
        "traffic_multiplier": 1.0,  # 100% normal rate
        "color": "#1890ff",  # Blue
        "behaviors": [
            "cyclic_io",
            "periodic_poll",
            "spontaneous_events",
            "heartbeat",
            "keepalive",
        ],
        "protocol_patterns": {
            "profinet": "cyclic_rt",
            "ethernet_ip": "implicit_io",
            "modbus_tcp": "read_holding_registers",
            "opc_ua": "publish",
            "dnp3": "integrity_poll",
            "iec104": "spontaneous",
        },
    },
    "maintenance": {
        "id": "maintenance",
        "name": "Maintenance Window",
        "description": "Configuration changes, firmware updates, and diagnostic activities",
        "duration_pct": 5,  # 5% of total duration
        "traffic_multiplier": 0.3,  # 30% normal rate (reduced operations)
        "color": "#faad14",  # Orange/Yellow
        "behaviors": [
            "firmware_update",
            "parameter_change",
            "diagnostics",
            "backup",
            "calibration",
        ],
        "protocol_patterns": {
            "profinet": "acyclic_write",
            "ethernet_ip": "explicit_msg",
            "modbus_tcp": "write_multiple_registers",
            "opc_ua": "write",
            "dnp3": "write",
            "iec104": "command",
        },
    },
    "shutdown": {
        "id": "shutdown",
        "name": "Graceful Shutdown",
        "description": "Orderly shutdown with state save, connection teardown, and final reporting",
        "duration_pct": 10,  # 10% of total duration
        "traffic_multiplier": 0.2,  # 20% of normal rate
        "color": "#ff4d4f",  # Red
        "behaviors": [
            "state_save",
            "connection_teardown",
            "final_poll",
            "alarm_clear",
            "logout",
        ],
        "protocol_patterns": {
            "profinet": "release_ar",
            "ethernet_ip": "forward_close",
            "modbus_tcp": "final_read",
            "opc_ua": "close_session",
            "dnp3": "warm_restart",
            "iec104": "stopdt",
        },
    },
}

# Vertical-specific phase variations
VERTICAL_PHASE_VARIATIONS: dict[str, dict[str, dict[str, Any]]] = {
    "manufacturing": {
        "startup": {
            "duration_pct": 3,
            "behaviors": [
                "connection_establishment",
                "plc_boot",
                "io_initialization",
                "safety_check",
            ],
        },
        "steady_state": {
            "duration_pct": 90,
            "behaviors": [
                "cyclic_io",
                "motion_control",
                "quality_check",
            ],
        },
        "maintenance": {
            "duration_pct": 2,
        },
        "shutdown": {
            "duration_pct": 5,
            "behaviors": [
                "machine_stop",
                "position_save",
                "io_safe_state",
            ],
        },
    },
    "water_wastewater": {
        "startup": {
            "duration_pct": 8,
            "behaviors": [
                "connection_establishment",
                "remote_site_scan",
                "integrity_check",
            ],
        },
        "steady_state": {
            "duration_pct": 80,
            "behaviors": [
                "periodic_poll",
                "unsolicited_events",
                "alarm_reporting",
            ],
        },
        "maintenance": {
            "duration_pct": 7,
            "behaviors": [
                "setpoint_change",
                "calibration",
                "firmware_update",
            ],
        },
        "shutdown": {
            "duration_pct": 5,
        },
    },
    "energy_power": {
        "startup": {
            "duration_pct": 10,
            "behaviors": [
                "connection_establishment",
                "general_interrogation",
                "time_sync",
                "protection_check",
            ],
        },
        "steady_state": {
            "duration_pct": 75,
            "behaviors": [
                "spontaneous_reporting",
                "integrity_poll",
                "event_burst",
            ],
        },
        "maintenance": {
            "duration_pct": 10,
            "behaviors": [
                "relay_testing",
                "settings_change",
                "firmware_update",
            ],
        },
        "shutdown": {
            "duration_pct": 5,
        },
    },
    "oil_gas": {
        "startup": {
            "duration_pct": 5,
            "behaviors": [
                "connection_establishment",
                "site_scan",
                "flow_computer_init",
            ],
        },
        "steady_state": {
            "duration_pct": 85,
            "behaviors": [
                "periodic_poll",
                "leak_detection",
                "flow_measurement",
            ],
        },
        "maintenance": {
            "duration_pct": 5,
            "behaviors": [
                "valve_testing",
                "calibration",
                "pig_tracking",
            ],
        },
        "shutdown": {
            "duration_pct": 5,
        },
    },
    "distribution_logistics": {
        "startup": {
            "duration_pct": 5,
            "behaviors": [
                "connection_establishment",
                "agv_fleet_init",
                "conveyor_startup_sequence",
                "scanner_calibration",
                "rfid_reader_init",
            ],
        },
        "steady_state": {
            "duration_pct": 85,
            "behaviors": [
                "agv_mission_dispatch",
                "conveyor_transport",
                "barcode_scanning",
                "rfid_tracking",
                "sortation_decisions",
                "pick_to_light_operations",
            ],
        },
        "maintenance": {
            "duration_pct": 5,
            "behaviors": [
                "agv_charging",
                "belt_calibration",
                "scanner_cleaning_cycle",
                "rfid_calibration",
            ],
        },
        "shutdown": {
            "duration_pct": 5,
            "behaviors": [
                "agv_return_to_home",
                "conveyor_clear_sequence",
                "system_park",
                "inventory_checkpoint",
            ],
        },
    },
}

# Preset phase sequences
PHASE_PRESETS: dict[str, list[dict[str, Any]]] = {
    "standard": [
        {"phase": "startup", "order": 1},
        {"phase": "steady_state", "order": 2},
        {"phase": "shutdown", "order": 3},
    ],
    "with_maintenance": [
        {"phase": "startup", "order": 1},
        {"phase": "steady_state", "order": 2},
        {"phase": "maintenance", "order": 3},
        {"phase": "steady_state", "order": 4},
        {"phase": "shutdown", "order": 5},
    ],
    "continuous": [
        {"phase": "steady_state", "order": 1},
    ],
    "startup_only": [
        {"phase": "startup", "order": 1},
    ],
    "full_lifecycle": [
        {"phase": "startup", "order": 1},
        {"phase": "steady_state", "order": 2},
        {"phase": "maintenance", "order": 3},
        {"phase": "steady_state", "order": 4},
        {"phase": "maintenance", "order": 5},
        {"phase": "steady_state", "order": 6},
        {"phase": "shutdown", "order": 7},
    ],
}


def get_phase_template(phase_id: str) -> dict[str, Any] | None:
    """Get a phase template by ID.

    Args:
        phase_id: Phase identifier

    Returns:
        Phase template or None if not found
    """
    return PHASE_TEMPLATES.get(phase_id)


def get_default_phases(
    total_duration_ms: int,
    preset: str = "standard",
    vertical: str | None = None,
) -> list[dict[str, Any]]:
    """Generate default phase list for a scenario.

    Args:
        total_duration_ms: Total scenario duration in milliseconds
        preset: Phase preset name
        vertical: Optional vertical for customization

    Returns:
        List of phase configurations
    """
    preset_sequence = PHASE_PRESETS.get(preset, PHASE_PRESETS["standard"])
    phases = []

    # Calculate cumulative percentages
    total_pct = 0
    for phase_config in preset_sequence:
        phase_id = phase_config["phase"]
        template = PHASE_TEMPLATES.get(phase_id, {})

        # Apply vertical-specific variations
        if vertical and vertical in VERTICAL_PHASE_VARIATIONS:
            vertical_variations = VERTICAL_PHASE_VARIATIONS[vertical].get(phase_id, {})
            template = {**template, **vertical_variations}

        duration_pct = template.get("duration_pct", 25)

        # Calculate actual times
        start_pct = total_pct
        end_pct = total_pct + duration_pct
        total_pct = end_pct

        start_ms = int(total_duration_ms * start_pct / 100)
        end_ms = int(total_duration_ms * end_pct / 100)

        phases.append({
            "id": f"{phase_id}_{phase_config['order']}",
            "phase_type": phase_id,
            "name": template.get("name", phase_id.title()),
            "description": template.get("description", ""),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": end_ms - start_ms,
            "traffic_multiplier": template.get("traffic_multiplier", 1.0),
            "color": template.get("color", "#1890ff"),
            "behaviors": template.get("behaviors", []),
            "protocol_patterns": template.get("protocol_patterns", {}),
        })

    # Normalize to ensure we hit exactly total_duration_ms
    if phases:
        phases[-1]["end_ms"] = total_duration_ms
        phases[-1]["duration_ms"] = phases[-1]["end_ms"] - phases[-1]["start_ms"]

    return phases


def list_phase_presets() -> list[dict[str, Any]]:
    """List available phase presets.

    Returns:
        List of preset summaries
    """
    presets = []
    for preset_name, sequence in PHASE_PRESETS.items():
        presets.append({
            "name": preset_name,
            "display_name": preset_name.replace("_", " ").title(),
            "phase_count": len(sequence),
            "phases": [p["phase"] for p in sequence],
        })
    return presets
