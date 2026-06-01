# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Beckwith Electric device templates.

Beckwith Electric (now part of Eaton) makes protection, monitoring,
and automatic-tap-change controls for power distribution. Common deployments:
transformer monitors, LTC controllers, and generator protection relays.
"""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    # ------------------------------------------------------------------
    # Beckwith M-7679 — Transformer monitor (DGA, temperature, LTC status).
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="beckwith/monitor/m-7679",
        vendor="Beckwith Electric",
        vendor_family="M-Series",
        model="M-7679",
        model_name="Beckwith M-7679 Transformer Monitor",
        device_type="meter",
        description="Power transformer monitor with thermal modeling and LTC condition assessment",

        oui_prefixes=[],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 15.0,
            "mean_ms": 3.5,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["modbus_tcp", "dnp3", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="BEM7679{6NUM}",
            station_name_pattern="xfmr-monitor-{seq}",
            vendor_short="BEC",
            model_short="M7679",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.2.0",
                release_date=date(2024, 2, 14),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.0.1",
                release_date=date(2022, 5, 9),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Beckwith Electric",
            "product_code": "M-7679",
            "product_name": "M-7679 Transformer Monitor",
        },

        snmp_identity={
            "sys_descr": "Beckwith Electric M-7679 Transformer Monitor V3.2.0",
            "sys_object_id": "1.3.6.1.4.1.2456.7679.11",
            "sys_name": "BEC-M7679-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "Beckwith Electric",
            "device_name": "M-7679 Transformer Monitor",
            "hardware_version": "M-7679",
        },
    ),

    # ------------------------------------------------------------------
    # Beckwith M-2001D — Digital Tap-Changer Control for transformer LTCs.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="beckwith/tap-changer/m-2001d",
        vendor="Beckwith Electric",
        vendor_family="M-Series",
        model="M-2001D",
        model_name="Beckwith M-2001D Digital Tap-Changer Control",
        device_type="tap_changer",
        description="Microprocessor-based load tap-changer control for voltage regulation",

        oui_prefixes=[],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 12.0,
            "mean_ms": 3.0,
            "std_dev_ms": 1.8,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["modbus_tcp", "dnp3"],

        instance_rules=InstanceGenerationRules(
            serial_format="BEM2001{6NUM}",
            station_name_pattern="ltc-ctrl-{seq}",
            vendor_short="BEC",
            model_short="M2001D",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.4.2",
                release_date=date(2024, 1, 22),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.2.0",
                release_date=date(2022, 4, 11),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Beckwith Electric",
            "product_code": "M-2001D",
            "product_name": "M-2001D Digital Tap-Changer Control",
        },

        snmp_identity={
            "sys_descr": "Beckwith Electric M-2001D Digital Tap-Changer Control V5.4.2",
            "sys_object_id": "1.3.6.1.4.1.2456.2001.4",
            "sys_name": "BEC-M2001D-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "Beckwith Electric",
            "device_name": "M-2001D Digital Tap-Changer Control",
            "hardware_version": "M-2001D",
        },
    ),

    # ------------------------------------------------------------------
    # Beckwith M-3425A — Generator protection relay (40/24/27/59/64/87G).
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="beckwith/relay/m-3425a",
        vendor="Beckwith Electric",
        vendor_family="M-Series",
        model="M-3425A",
        model_name="Beckwith M-3425A Generator Protection Relay",
        device_type="protection_relay",
        description="Integrated generator protection relay for synchronous machines",

        oui_prefixes=[],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 10.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.1,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="BEM3425{6NUM}",
            station_name_pattern="gen-prot-{seq}",
            vendor_short="BEC",
            model_short="M3425A",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.8.1",
                release_date=date(2024, 3, 18),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.6.0",
                release_date=date(2022, 7, 5),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Beckwith Electric",
            "product_code": "M-3425A",
            "product_name": "M-3425A Generator Protection Relay",
        },

        snmp_identity={
            "sys_descr": "Beckwith Electric M-3425A Generator Protection Relay V2.8.1",
            "sys_object_id": "1.3.6.1.4.1.2456.3425.7",
            "sys_name": "BEC-M3425A-001",
            "sys_location": "Power Plant",
        },

        dnp3_identity={
            "vendor_name": "Beckwith Electric",
            "device_name": "M-3425A Generator Protection Relay",
            "hardware_version": "M-3425A",
        },

        iec61850_identity={
            "ied_name": "BEC_M3425A_IED",
            "vendor": "Beckwith Electric",
            "software_version": "V2.8.1",
            "logical_devices": ["CTRL", "MEAS", "PROT"],
            "icd_filename": "BEC_M3425A.icd",
        },
    ),
]
