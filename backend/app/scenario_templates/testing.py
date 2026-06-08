# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Testing and demo scenario templates.

These templates are designed for testing specific PacketArch features,
not for realistic industrial deployments.
"""

from typing import Any


TESTING_TEMPLATES: dict[str, dict[str, Any]] = {
    # ============================================================
    # TEMPLATE: DUPLICATE MAC DETECTION DEMO (10 devices)
    # Produces 4 duplicate MAC pairs triggering all severity levels
    # ============================================================
    "duplicate_mac_demo": {
        "name": "Duplicate MAC Detection Demo",
        "description": "Testing utility with 4 intentional duplicate MAC pairs that trigger "
                       "all severity levels: critical (different vendors), high (different IPs), "
                       "medium (different names), and low (identical devices). Deploy to an agent "
                       "and wait ~5 minutes for Cyber Vision discovery, then use the MAC Analysis tab "
                       "to verify detection across all severity tiers. 10 devices on a single flat network.",
        "vertical": "testing",
        # This template's authoring intent collides with the realism
        # rules — duplicate MACs and duplicate names are the FEATURE
        # under test. Tell the audit harness not to flag those.
        "audit_exempt_categories": [
            "readiness:Unique MAC addresses",
            "readiness:Unique device names",
        ],
        "devices": [
            # ============================================================
            # POLLING SOURCE — 1 device
            # HMI that polls all demo devices via Modbus TCP + SNMP
            # ============================================================
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "test_net",
             "name": "Test-SCADA-Server", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "HMISTM6",
             "firmware_version": "V3.3.0",
             "role": "SCADA Server"},

            # ============================================================
            # CRITICAL PAIR — Same MAC, different vendors
            # Triggers: "Same MAC shared across N different vendors"
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "test_net",
             "name": "CRIT-Siemens-PLC", "protocols": ["modbus_tcp", "s7comm", "snmp"],
             "fingerprint_model": "6ES7 516-3AN02-0AB0",
             "firmware_version": "V2.9.2",
             "role": "Demo PLC",
             "mac_address": "DE:AD:BE:EF:00:01"},
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "test_net",
             "name": "CRIT-Rockwell-PLC", "protocols": ["modbus_tcp", "ethernet_ip", "snmp"],
             "fingerprint_model": "1769-L33ER",
             "firmware_version": "V33.013",
             "role": "Demo PLC",
             "mac_address": "DE:AD:BE:EF:00:01"},

            # ============================================================
            # HIGH PAIR — Same MAC + vendor, different IPs (auto-assigned)
            # Triggers: "Same MAC with N different IP addresses"
            # ============================================================
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "test_net",
             "name": "HIGH-Schneider-A", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "BMEP586040",
             "role": "Demo PLC",
             "mac_address": "DE:AD:BE:EF:00:02"},
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "test_net",
             "name": "HIGH-Schneider-B", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "BMEP586040",
             "role": "Demo PLC",
             "mac_address": "DE:AD:BE:EF:00:02"},

            # ============================================================
            # MEDIUM PAIR — Same MAC + vendor + IP, different names
            # Triggers: "Same MAC and IP but different device names or models"
            # ============================================================
            {"type": "temperature_controller", "vendor": "honeywell", "count": 1, "zone": "test_net",
             "name": "MED-Honeywell-Primary", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "HC900 Controller",
             "role": "Demo Controller",
             "mac_address": "DE:AD:BE:EF:00:03",
             "ip_host_offset": 40},
            {"type": "temperature_controller", "vendor": "honeywell", "count": 1, "zone": "test_net",
             "name": "MED-Honeywell-Standby", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "HC900 Controller",
             "role": "Demo Controller",
             "mac_address": "DE:AD:BE:EF:00:03",
             "ip_host_offset": 40},

            # ============================================================
            # LOW PAIR — Identical devices (same MAC, IP, name, model)
            # Triggers: "Devices appear nearly identical"
            # NOTE: CV may merge these into a single entry; low severity is
            #       most commonly seen in multi-deployment environments.
            # ============================================================
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "test_net",
             "name": "LOW-IO-Module", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Demo IO",
             "mac_address": "DE:AD:BE:EF:00:04",
             "ip_host_offset": 50},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "test_net",
             "name": "LOW-IO-Module", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Demo IO",
             "mac_address": "DE:AD:BE:EF:00:04",
             "ip_host_offset": 50},
        ],
        "flows": [
            # Modbus TCP polling — SCADA to all demo devices (2s interval).
            # NOTE: This is an intentionally-flat test scenario for
            # duplicate-MAC detection; the realism rules (HMI→IO direct
            # polling) do not apply. auto_repair_skip prevents the audit
            # from flagging it.
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 2000,
             "source_types": ["hmi"],
             "target_types": ["plc", "temperature_controller", "io_module"],
             "source_zones": ["test_net"], "target_zones": ["test_net"],
             "jitter_ms": 200, "jitter_type": "gaussian",
             "auto_repair_skip": True},

            # SNMP monitoring — identity enrichment for CV (30s interval)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source_types": ["hmi"],
             "target_types": ["plc", "temperature_controller", "io_module"],
             "source_zones": ["test_net"], "target_zones": ["test_net"],
             "jitter_ms": 3000, "jitter_type": "uniform",
             "auto_repair_skip": True},
        ],
        "zones": [
            {"id": "test_net", "name": "Test Network", "level": 2,
             "subnet_offset": 0, "vlan": 100, "security_level": "standard"},
        ],
        "total_duration_ms": 600000,  # 10 minutes
    },
}
