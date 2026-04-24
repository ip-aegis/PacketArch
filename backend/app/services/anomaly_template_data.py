# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Anomaly template seed data for common OT traffic anomalies.

This module contains predefined anomaly templates covering:
- Timing anomalies (delays, timeouts, jitter)
- Protocol anomalies (errors, malformed packets)
- Sequence anomalies (duplicates, missing, out-of-order)
- Payload anomalies (value spikes, corruption)
- Network anomalies (packet loss, fragmentation)
- Security anomalies (scan signatures, exploit patterns)
"""

from typing import Any

# Timing anomalies - response delays and timeouts
TIMING_ANOMALIES: list[dict[str, Any]] = [
    {
        "name": "Response Timeout",
        "description": "Device fails to respond to request, simulating communication loss",
        "category": "timing",
        "severity": "high",
        "anomaly_type": "timeout",
        "parameters": {
            "timeout_ms": 5000,
            "partial_response": False,
        },
        "injection_probability": 0.005,
        "duration_cycles": 1,
        "tags": ["timeout", "communication-loss"],
    },
    {
        "name": "Slow Response",
        "description": "Device responds but with significant delay (10x normal)",
        "category": "timing",
        "severity": "medium",
        "anomaly_type": "delayed",
        "parameters": {
            "delay_factor": 10.0,
            "jitter_ms": 50,
        },
        "injection_probability": 0.01,
        "duration_cycles": 3,
        "tags": ["delay", "performance"],
    },
    {
        "name": "Intermittent Response",
        "description": "Device responds sporadically with high jitter",
        "category": "timing",
        "severity": "medium",
        "anomaly_type": "jitter_spike",
        "parameters": {
            "jitter_multiplier": 5.0,
            "jitter_distribution": "exponential",
        },
        "injection_probability": 0.02,
        "duration_cycles": 5,
        "tags": ["jitter", "unstable"],
    },
    {
        "name": "Watchdog Timeout",
        "description": "Simulates PLC watchdog timeout on communication loss",
        "category": "timing",
        "severity": "critical",
        "anomaly_type": "watchdog_timeout",
        "parameters": {
            "timeout_ms": 2000,
            "recovery_time_ms": 5000,
        },
        "target_protocols": ["profinet", "ethernet_ip"],
        "injection_probability": 0.001,
        "duration_cycles": 10,
        "tags": ["watchdog", "plc", "safety"],
    },
]

# Protocol anomalies - errors and violations
PROTOCOL_ANOMALIES: list[dict[str, Any]] = [
    {
        "name": "Modbus Exception - Illegal Function",
        "description": "Device responds with exception code 01 (Illegal Function)",
        "category": "protocol",
        "severity": "medium",
        "anomaly_type": "modbus_exception",
        "parameters": {
            "exception_code": 1,
            "exception_name": "ILLEGAL_FUNCTION",
        },
        "target_protocols": ["modbus_tcp"],
        "injection_probability": 0.01,
        "duration_cycles": 1,
        "tags": ["modbus", "exception"],
    },
    {
        "name": "Modbus Exception - Illegal Address",
        "description": "Device responds with exception code 02 (Illegal Data Address)",
        "category": "protocol",
        "severity": "medium",
        "anomaly_type": "modbus_exception",
        "parameters": {
            "exception_code": 2,
            "exception_name": "ILLEGAL_DATA_ADDRESS",
        },
        "target_protocols": ["modbus_tcp"],
        "injection_probability": 0.008,
        "duration_cycles": 1,
        "tags": ["modbus", "exception"],
    },
    {
        "name": "Modbus Exception - Device Busy",
        "description": "Device responds with exception code 06 (Slave Device Busy)",
        "category": "protocol",
        "severity": "low",
        "anomaly_type": "modbus_exception",
        "parameters": {
            "exception_code": 6,
            "exception_name": "SLAVE_DEVICE_BUSY",
        },
        "target_protocols": ["modbus_tcp"],
        "injection_probability": 0.02,
        "duration_cycles": 3,
        "tags": ["modbus", "exception", "busy"],
    },
    {
        "name": "CIP Error - Connection Failure",
        "description": "EtherNet/IP CIP connection failure response",
        "category": "protocol",
        "severity": "high",
        "anomaly_type": "cip_error",
        "parameters": {
            "status_code": 1,
            "extended_status": [0x0311],  # Connection failure
        },
        "target_protocols": ["ethernet_ip"],
        "injection_probability": 0.005,
        "duration_cycles": 1,
        "tags": ["ethernet_ip", "cip", "connection"],
    },
    {
        "name": "CIP Error - Resource Unavailable",
        "description": "EtherNet/IP resource unavailable error",
        "category": "protocol",
        "severity": "medium",
        "anomaly_type": "cip_error",
        "parameters": {
            "status_code": 2,
            "extended_status": [0x0107],  # Resource unavailable
        },
        "target_protocols": ["ethernet_ip"],
        "injection_probability": 0.008,
        "duration_cycles": 2,
        "tags": ["ethernet_ip", "cip", "resource"],
    },
    {
        "name": "PROFINET Alarm - Process Alarm",
        "description": "PROFINET RTA process alarm frame",
        "category": "protocol",
        "severity": "medium",
        "anomaly_type": "profinet_alarm",
        "parameters": {
            "alarm_type": 1,  # Process alarm
            "alarm_specifier": 0x0001,
            "user_structure": "0800",
        },
        "target_protocols": ["profinet"],
        "injection_probability": 0.01,
        "duration_cycles": 1,
        "tags": ["profinet", "alarm"],
    },
]

# Sequence anomalies - packet ordering issues
SEQUENCE_ANOMALIES: list[dict[str, Any]] = [
    {
        "name": "Duplicate Response",
        "description": "Device sends duplicate response packets",
        "category": "sequence",
        "severity": "low",
        "anomaly_type": "duplicate",
        "parameters": {
            "duplicate_count": 2,
            "interval_ms": 10,
        },
        "injection_probability": 0.01,
        "duration_cycles": 1,
        "tags": ["duplicate", "retransmission"],
    },
    {
        "name": "Missing Response",
        "description": "Response packet is dropped/missing",
        "category": "sequence",
        "severity": "medium",
        "anomaly_type": "drop",
        "parameters": {
            "drop_probability": 1.0,
        },
        "injection_probability": 0.005,
        "duration_cycles": 1,
        "tags": ["packet-loss", "missing"],
    },
    {
        "name": "Out-of-Order Packets",
        "description": "Response arrives before request is logged (timing skew)",
        "category": "sequence",
        "severity": "low",
        "anomaly_type": "reorder",
        "parameters": {
            "swap_with_previous": True,
        },
        "injection_probability": 0.005,
        "duration_cycles": 2,
        "tags": ["reorder", "sequence"],
    },
    {
        "name": "Transaction ID Mismatch",
        "description": "Response has mismatched transaction ID",
        "category": "sequence",
        "severity": "medium",
        "anomaly_type": "tid_mismatch",
        "parameters": {
            "offset": 1,
        },
        "target_protocols": ["modbus_tcp"],
        "injection_probability": 0.002,
        "duration_cycles": 1,
        "tags": ["modbus", "transaction"],
    },
]

# Payload anomalies - value and data issues
PAYLOAD_ANOMALIES: list[dict[str, Any]] = [
    {
        "name": "Value Spike",
        "description": "Register value suddenly spikes to extreme value",
        "category": "payload",
        "severity": "high",
        "anomaly_type": "value_spike",
        "parameters": {
            "spike_type": "max",  # "max", "min", "factor"
            "spike_factor": 100.0,
        },
        "target_protocols": ["modbus_tcp"],
        "injection_probability": 0.005,
        "duration_cycles": 3,
        "tags": ["value", "spike", "process"],
    },
    {
        "name": "Value Flatline",
        "description": "Register value stuck at constant (frozen sensor)",
        "category": "payload",
        "severity": "medium",
        "anomaly_type": "value_freeze",
        "parameters": {
            "freeze_value": "current",
            "duration_cycles": 20,
        },
        "injection_probability": 0.003,
        "duration_cycles": 20,
        "tags": ["value", "freeze", "sensor"],
    },
    {
        "name": "Value Drift",
        "description": "Register value slowly drifts from expected range",
        "category": "payload",
        "severity": "medium",
        "anomaly_type": "value_drift",
        "parameters": {
            "drift_rate": 0.5,  # % per cycle
            "drift_direction": "up",
        },
        "injection_probability": 0.002,
        "duration_cycles": 50,
        "tags": ["value", "drift", "calibration"],
    },
    {
        "name": "Invalid Data Type",
        "description": "Payload contains invalid/unexpected data format",
        "category": "payload",
        "severity": "medium",
        "anomaly_type": "invalid_format",
        "parameters": {
            "corruption_type": "byte_swap",
        },
        "injection_probability": 0.001,
        "duration_cycles": 1,
        "tags": ["format", "corruption"],
    },
]

# Network anomalies - infrastructure issues
NETWORK_ANOMALIES: list[dict[str, Any]] = [
    {
        "name": "Packet Loss Burst",
        "description": "Burst of consecutive packet losses",
        "category": "network",
        "severity": "high",
        "anomaly_type": "loss_burst",
        "parameters": {
            "burst_length": 5,
            "loss_probability": 0.8,
        },
        "injection_probability": 0.002,
        "duration_cycles": 5,
        "tags": ["packet-loss", "burst", "network"],
    },
    {
        "name": "High Jitter Period",
        "description": "Period of extreme network jitter",
        "category": "network",
        "severity": "medium",
        "anomaly_type": "jitter_period",
        "parameters": {
            "jitter_min_ms": 50,
            "jitter_max_ms": 500,
        },
        "injection_probability": 0.005,
        "duration_cycles": 20,
        "tags": ["jitter", "network", "qos"],
    },
    {
        "name": "Bandwidth Saturation",
        "description": "Simulates network congestion with delayed responses",
        "category": "network",
        "severity": "medium",
        "anomaly_type": "congestion",
        "parameters": {
            "queue_delay_ms": 100,
            "delay_variance": 0.3,
        },
        "injection_probability": 0.003,
        "duration_cycles": 30,
        "tags": ["congestion", "bandwidth", "qos"],
    },
]

# External communication anomalies - C2, exfil, exploits
EXTERNAL_COMMUNICATION_ANOMALIES: list[dict[str, Any]] = [
    {
        "name": "C2 Beacon - Fixed Interval",
        "description": "HTTP GET beacon every 60 seconds (easily detectable pattern)",
        "category": "external_communication",
        "severity": "critical",
        "anomaly_type": "c2_beacon",
        "parameters": {
            "pattern": "fixed_60s",
            "protocol": "http",
            "method": "GET",
            "path": "/api/check",
        },
        "external_target_type": "c2_server",
        "external_protocol": "http",
        "external_port": 80,
        "external_ip_pool": "test_net_1",
        "ids_trigger_patterns": [
            "alert tcp any any -> any 80 (content:\"GET\"; content:\"/api/check\";)",
        ],
        "injection_mode": "scheduled",
        "injection_schedule": {"interval_ms": 60000},
        "mitre_technique": "T0885",
        "tags": ["c2", "beacon", "http", "fixed-interval"],
    },
    {
        "name": "C2 Beacon - Jittered",
        "description": "HTTP POST beacon every 5 minutes with 15% jitter (harder to detect)",
        "category": "external_communication",
        "severity": "critical",
        "anomaly_type": "c2_beacon",
        "parameters": {
            "pattern": "jittered_5m",
            "protocol": "http",
            "method": "POST",
            "path": "/update",
            "jitter_pct": 0.15,
        },
        "external_target_type": "c2_server",
        "external_protocol": "http",
        "external_port": 80,
        "external_ip_pool": "test_net_1",
        "injection_mode": "scheduled",
        "injection_schedule": {"interval_ms": 300000, "jitter_pct": 0.15},
        "mitre_technique": "T0885",
        "tags": ["c2", "beacon", "http", "jittered"],
    },
    {
        "name": "C2 Beacon - Cobalt Strike Style",
        "description": "Beacon pattern mimicking Cobalt Strike default (37% jitter)",
        "category": "external_communication",
        "severity": "critical",
        "anomaly_type": "c2_beacon",
        "parameters": {
            "pattern": "cobalt_strike",
            "protocol": "http",
            "method": "GET",
            "jitter_pct": 0.37,
            "user_agent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)",
        },
        "external_target_type": "c2_server",
        "external_protocol": "https",
        "external_port": 443,
        "external_ip_pool": "test_net_1",
        "ids_trigger_patterns": [
            "alert tcp any any -> any 443 (content:\"MSIE 6.0\";)",
        ],
        "injection_mode": "scheduled",
        "mitre_technique": "T0885",
        "tags": ["c2", "beacon", "cobalt-strike", "apt"],
    },
    {
        "name": "DNS Tunnel - Data Exfiltration",
        "description": "Base32-encoded data in DNS TXT queries to external domain",
        "category": "external_communication",
        "severity": "critical",
        "anomaly_type": "dns_tunnel",
        "parameters": {
            "encoding": "base32",
            "query_type": "TXT",
            "base_domain": "tunnel.example.com",
            "chunk_size": 100,
        },
        "external_target_type": "exfil_destination",
        "external_protocol": "dns",
        "external_port": 53,
        "external_ip_pool": "test_net_1",
        "ids_trigger_patterns": [
            "alert udp any any -> any 53 (content:\"|00 10|\"; dns.query;)",
        ],
        "injection_mode": "scheduled",
        "mitre_technique": "T0884",
        "tags": ["dns", "tunnel", "exfil", "covert-channel"],
    },
    {
        "name": "DNS Beacon",
        "description": "Periodic DNS TXT queries for C2 check-in",
        "category": "external_communication",
        "severity": "high",
        "anomaly_type": "dns_beacon",
        "parameters": {
            "query_type": "TXT",
            "interval_ms": 60000,
            "domain_pattern": "{uid}.beacon.c2.example.com",
        },
        "external_target_type": "c2_server",
        "external_protocol": "dns",
        "external_port": 53,
        "external_ip_pool": "test_net_1",
        "injection_mode": "scheduled",
        "mitre_technique": "T0884",
        "tags": ["dns", "beacon", "c2"],
    },
    {
        "name": "HTTP Data Exfiltration",
        "description": "Chunked base64 HTTP POST uploads to external server",
        "category": "external_communication",
        "severity": "critical",
        "anomaly_type": "http_exfil",
        "parameters": {
            "encoding": "base64",
            "chunk_size": 4096,
            "path": "/upload",
            "content_type": "application/octet-stream",
        },
        "external_target_type": "exfil_destination",
        "external_protocol": "http",
        "external_port": 80,
        "external_ip_pool": "test_net_2",
        "ids_trigger_patterns": [
            "alert tcp any any -> any 80 (content:\"POST\"; content:\"base64\";)",
        ],
        "injection_mode": "triggered",
        "mitre_technique": "T0882",
        "tags": ["exfil", "http", "upload", "data-theft"],
    },
    {
        "name": "External Port Scan - OT Ports",
        "description": "TCP SYN scan of OT ports from external attacker",
        "category": "external_communication",
        "severity": "high",
        "anomaly_type": "external_scan",
        "parameters": {
            "scan_type": "syn",
            "ports": [102, 502, 2222, 4840, 20000, 44818, 47808],
            "scan_rate_pps": 5,
        },
        "external_target_type": "attacker_source",
        "external_protocol": "tcp_raw",
        "external_ip_pool": "test_net_3",
        "ids_trigger_patterns": [
            "alert tcp any any -> any [102,502,44818] (flags:S;)",
        ],
        "injection_mode": "scheduled",
        "injection_schedule": {"duration_ms": 30000},
        "mitre_technique": "T0846",
        "tags": ["scan", "reconnaissance", "external", "ot-ports"],
    },
    {
        "name": "Modbus Exploit - Buffer Overflow",
        "description": "NOP sled pattern in Modbus packet payload",
        "category": "external_communication",
        "severity": "critical",
        "anomaly_type": "exploit_attempt",
        "parameters": {
            "exploit": "buffer_overflow_generic",
            "target_protocol": "modbus",
            "nop_sled_size": 100,
        },
        "external_target_type": "attacker_source",
        "external_protocol": "tcp_raw",
        "external_port": 502,
        "external_ip_pool": "test_net_3",
        "ids_trigger_patterns": [
            "alert tcp any any -> any 502 (content:\"|90 90 90 90|\";)",
        ],
        "injection_mode": "triggered",
        "mitre_technique": "T0869",
        "tags": ["exploit", "buffer-overflow", "modbus", "attack"],
    },
    {
        "name": "S7 Stop CPU Attack",
        "description": "S7comm CPU stop command from external source",
        "category": "external_communication",
        "severity": "critical",
        "anomaly_type": "exploit_attempt",
        "parameters": {
            "exploit": "s7_stop_cpu",
            "target_protocol": "s7",
        },
        "external_target_type": "attacker_source",
        "external_protocol": "tcp_raw",
        "external_port": 102,
        "external_ip_pool": "test_net_3",
        "ids_trigger_patterns": [
            "alert tcp any any -> any 102 (content:\"|32 01|\"; content:\"|29|\";)",
        ],
        "injection_mode": "triggered",
        "mitre_technique": "T0816",
        "tags": ["exploit", "s7", "stop-cpu", "siemens", "attack"],
    },
    {
        "name": "Modbus Force Listen Only",
        "description": "Modbus diagnostic command to force listen-only mode",
        "category": "external_communication",
        "severity": "critical",
        "anomaly_type": "exploit_attempt",
        "parameters": {
            "exploit": "modbus_force_listen",
            "function_code": 8,
            "sub_function": 4,
        },
        "external_target_type": "attacker_source",
        "external_protocol": "tcp_raw",
        "external_port": 502,
        "external_ip_pool": "test_net_3",
        "ids_trigger_patterns": [
            "alert tcp any any -> any 502 (content:\"|00 08 00 04|\";)",
        ],
        "injection_mode": "triggered",
        "mitre_technique": "T0814",
        "tags": ["exploit", "modbus", "diagnostic", "dos", "attack"],
    },
]

# Security anomalies - attack signatures
SECURITY_ANOMALIES: list[dict[str, Any]] = [
    {
        "name": "Port Scan Pattern",
        "description": "Generates traffic resembling port scanning",
        "category": "security",
        "severity": "high",
        "anomaly_type": "scan_pattern",
        "parameters": {
            "scan_type": "sequential",
            "port_range": [1, 1024],
            "scan_rate_pps": 10,
        },
        "injection_mode": "scheduled",
        "injection_schedule": {"duration_ms": 60000},
        "mitre_technique": "T0846",
        "tags": ["scan", "reconnaissance", "attack"],
    },
    {
        "name": "Modbus Write Coil Flood",
        "description": "Rapid write coil commands (potential DoS)",
        "category": "security",
        "severity": "critical",
        "anomaly_type": "command_flood",
        "parameters": {
            "function_code": 5,
            "rate_multiplier": 50,
        },
        "target_protocols": ["modbus_tcp"],
        "injection_probability": 0.0005,
        "duration_cycles": 100,
        "mitre_technique": "T0814",
        "tags": ["flood", "dos", "write"],
    },
    {
        "name": "Unauthorized Function Code",
        "description": "Use of restricted/diagnostic function codes",
        "category": "security",
        "severity": "high",
        "anomaly_type": "unauthorized_fc",
        "parameters": {
            "function_codes": [8, 17, 43],  # Diagnostics, Report Slave ID, MEI
        },
        "target_protocols": ["modbus_tcp"],
        "injection_probability": 0.001,
        "duration_cycles": 1,
        "mitre_technique": "T0855",
        "tags": ["unauthorized", "diagnostic", "enumeration"],
    },
    {
        "name": "CIP Enumeration",
        "description": "CIP service enumeration pattern",
        "category": "security",
        "severity": "high",
        "anomaly_type": "cip_enumeration",
        "parameters": {
            "services": ["list_services", "list_identity", "list_interfaces"],
        },
        "target_protocols": ["ethernet_ip"],
        "injection_mode": "scheduled",
        "mitre_technique": "T0846",
        "tags": ["enumeration", "reconnaissance", "cip"],
    },
    {
        "name": "PLC Stop Command",
        "description": "Attempt to send PLC stop command",
        "category": "security",
        "severity": "critical",
        "anomaly_type": "plc_control",
        "parameters": {
            "command": "stop",
            "include_auth_bypass": False,
        },
        "target_device_types": ["plc"],
        "injection_probability": 0.0001,
        "duration_cycles": 1,
        "mitre_technique": "T0816",
        "tags": ["control", "stop", "critical"],
    },
]

# All anomaly templates combined
ALL_ANOMALY_TEMPLATES = (
    TIMING_ANOMALIES +
    PROTOCOL_ANOMALIES +
    SEQUENCE_ANOMALIES +
    PAYLOAD_ANOMALIES +
    NETWORK_ANOMALIES +
    SECURITY_ANOMALIES +
    EXTERNAL_COMMUNICATION_ANOMALIES
)


async def seed_anomaly_templates(db_session) -> int:
    """Seed the database with anomaly templates.

    Args:
        db_session: Database session

    Returns:
        Number of templates seeded
    """
    from sqlalchemy import select
    from app.models.anomaly_template import (
        AnomalyTemplate,
        AnomalyCategory,
        AnomalySeverity,
    )

    count = 0

    for template_data in ALL_ANOMALY_TEMPLATES:
        # Check if template already exists
        existing = await db_session.execute(
            select(AnomalyTemplate).where(AnomalyTemplate.name == template_data["name"])
        )
        if existing.scalar_one_or_none():
            continue

        template = AnomalyTemplate(
            name=template_data["name"],
            description=template_data.get("description"),
            category=AnomalyCategory(template_data["category"]),
            severity=AnomalySeverity(template_data.get("severity", "medium")),
            target_protocols=template_data.get("target_protocols"),
            target_device_types=template_data.get("target_device_types"),
            anomaly_type=template_data["anomaly_type"],
            parameters=template_data.get("parameters"),
            injection_mode=template_data.get("injection_mode", "random"),
            injection_probability=template_data.get("injection_probability", 0.01),
            injection_schedule=template_data.get("injection_schedule"),
            duration_cycles=template_data.get("duration_cycles"),
            affects_flow_count=template_data.get("affects_flow_count", 1),
            is_builtin=True,
            is_active=True,
            tags=template_data.get("tags"),
            mitre_technique=template_data.get("mitre_technique"),
            cve_reference=template_data.get("cve_reference"),
            detection_signature=template_data.get("detection_signature"),
            # External communication fields
            external_target_type=template_data.get("external_target_type"),
            external_protocol=template_data.get("external_protocol"),
            external_port=template_data.get("external_port"),
            ids_trigger_patterns=template_data.get("ids_trigger_patterns"),
            external_ip_pool=template_data.get("external_ip_pool"),
        )

        db_session.add(template)
        count += 1

    await db_session.commit()
    return count
