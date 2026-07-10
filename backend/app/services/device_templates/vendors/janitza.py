# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Janitza electronics device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="janitza/umg/604-pro",
        vendor="Janitza",
        vendor_family="UMG",
        model="UMG 604-PRO",
        model_name="UMG 604-PRO Power Quality Analyzer",
        device_type="power_meter",
        description="Main-incomer power quality analyzer and energy management hub; "
                     "natively speaks Modbus TCP, BACnet/IP, and SNMP over Ethernet",

        oui_prefixes=["00:0E:6B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 60.0,
            "mean_ms": 14.0,
            "std_dev_ms": 9.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "bacnet", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="UMG604{6NUM}",
            station_name_pattern="meter-umg604-{seq}",
            vendor_short="JAN",
            model_short="UMG604",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="3.4",
                release_date=date(2014, 6, 1),
                cves=["CVE-2015-3968", "CVE-2015-3971", "CVE-2015-3972", "CVE-2015-3973"],
                notes="ICSA-15-265-03: default FTP password, unauthenticated debug "
                      "port (TCP 1239, code execution), unprotected web UI, weak "
                      "session tokens",
            ),
            FirmwareVariant(
                version="4.0",
                release_date=date(2016, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Janitza electronics GmbH",
            "product_code": "UMG604-PRO",
            "vendor_url": "https://www.janitza.com",
            "product_name": "UMG 604-PRO Power Quality Analyzer",
            "model_name": "UMG 604-PRO",
        },

        bacnet_identity={
            "vendor_id": 316,
            "vendor_name": "Janitza Electronics GmbH",
            "model_name": "UMG 604-PRO",
            "device_instance": 0,
        },

        snmp_identity={
            # No IANA-registered Janitza enterprise PEN found; the device's
            # embedded Linux stack ships Net-SNMP's agent unmodified, so it
            # reports the generic Net-SNMP sysObjectID branch (as seen on
            # other small OT vendors' Linux-based appliances in this catalog).
            "sys_descr": "Janitza UMG 604-PRO Power Quality Analyzer V4.0",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10",
            "sys_name": "UMG604-PRO-001",
            "sys_location": "Main Distribution Board",
        },
    ),
]
