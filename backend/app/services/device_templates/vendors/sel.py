# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Schweitzer Engineering Laboratories (SEL) device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="sel/relay/sel-751",
        vendor="SEL",
        vendor_family="SEL-700 Series",
        model="SEL-751",
        model_name="SEL-751 Feeder Protection Relay",
        device_type="protection_relay",
        description="Feeder protection relay with comprehensive protection functions",

        oui_prefixes=["00:30:A7", "00:1C:73"],

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
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="SEL{10NUM}",
            station_name_pattern="relay-751-{seq}",
            vendor_short="SEL",
            model_short="751",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R151-V4",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R151-V2",
                release_date=date(2022, 5, 20),
                cves=["CVE-2023-31170"],
            ),
            FirmwareVariant(
                version="R150-V0",
                release_date=date(2020, 10, 10),
                cves=["CVE-2023-31170", "CVE-2021-31553"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "product_code": "SEL-751",
            "product_name": "SEL-751 Feeder Protection Relay",
        },

        snmp_identity={
            "sys_descr": "Schweitzer Engineering Laboratories SEL-751 Feeder Protection Relay VR151-V4",
            "sys_object_id": "1.3.6.1.4.1.1027.139.51",
            "sys_name": "SEL-75-FEEDER-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-751 Feeder Protection Relay",
            "hardware_version": "751",
        },
    ),
    DeviceTemplate(
        id="sel/rtac/sel-3530",
        vendor="SEL",
        vendor_family="SEL-3500 Series",
        model="SEL-3530",
        model_name="SEL-3530 RTAC",
        device_type="rtu",
        description="Real-Time Automation Controller for substation automation",

        oui_prefixes=["00:30:A7", "00:1C:73"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 8.0,
            "mean_ms": 1.5,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850", "iec104"],

        instance_rules=InstanceGenerationRules(
            serial_format="RTAC{10NUM}",
            station_name_pattern="rtac-{location}-{seq}",
            vendor_short="SEL",
            model_short="3530",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R150-V5",
                release_date=date(2024, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R148-V2",
                release_date=date(2022, 8, 15),
                cves=["CVE-2023-31170"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "product_code": "SEL-3530",
            "product_name": "SEL-3530 Real-Time Automation Controller",
        },

        snmp_identity={
            "sys_descr": "Schweitzer Engineering Laboratories SEL-3530 RTAC VR150-V5",
            "sys_object_id": "1.3.6.1.4.1.1027.124.87",
            "sys_name": "SEL-35-RTAC-001",
            "sys_location": "Remote Site",
        },

        dnp3_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-3530 Real-Time Automation Controller",
            "hardware_version": "3530",
        },

        iec104_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-3530 Real-Time Automation Controller",
            "hardware_version": "3530",
        },
    ),
    DeviceTemplate(
        id="sel/relay/sel-451",
        vendor="SEL",
        vendor_family="SEL-400 Series",
        model="SEL-451",
        model_name="SEL-451 Bay Controller",
        device_type="protection_relay",
        description="Bay controller with protection and control functions",

        oui_prefixes=["00:30:A7", "00:1C:73"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.4,
            "max_ms": 8.0,
            "mean_ms": 1.8,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="SEL{10NUM}",
            station_name_pattern="relay-451-{seq}",
            vendor_short="SEL",
            model_short="451",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R160-V5",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R159-V2",
                release_date=date(2022, 6, 20),
                cves=["CVE-2023-31170"],
            ),
            FirmwareVariant(
                version="R157-V0",
                release_date=date(2020, 11, 10),
                cves=["CVE-2023-31170", "CVE-2021-31553"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "product_code": "SEL-451",
            "product_name": "SEL-451 Bay Controller",
        },

        snmp_identity={
            "sys_descr": "Schweitzer Engineering Laboratories SEL-451 Bay Controller VR160-V5",
            "sys_object_id": "1.3.6.1.4.1.1027.672.79",
            "sys_name": "SEL-45-BAY-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-451 Bay Controller",
            "hardware_version": "451",
        },
    ),
    DeviceTemplate(
        id="sel/controller/sel-2411",
        vendor="SEL",
        vendor_family="SEL-2400 Series",
        model="SEL-2411",
        model_name="SEL-2411 Programmable Automation Controller",
        device_type="substation_controller",
        description="Programmable logic controller for substation automation",

        oui_prefixes=["00:30:A7", "00:1C:73"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 10.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.2,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="SEL{10NUM}",
            station_name_pattern="pac-2411-{seq}",
            vendor_short="SEL",
            model_short="2411",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R133-V4",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R131-V2",
                release_date=date(2022, 7, 15),
                cves=["CVE-2023-31170"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "product_code": "SEL-2411",
            "product_name": "SEL-2411 Programmable Automation Controller",
        },

        snmp_identity={
            "sys_descr": "Schweitzer Engineering Laboratories SEL-2411 Programmable Automation Controller VR133-V4",
            "sys_object_id": "1.3.6.1.4.1.1027.134.57",
            "sys_name": "SEL-24-PROGRA-001",
            "sys_location": "Industrial Network",
        },

        dnp3_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-2411 Programmable Automation Controller",
            "hardware_version": "2411",
        },
    ),
    DeviceTemplate(
        id="sel/relay/sel-311c",
        vendor="SEL",
        vendor_family="SEL-300 Series",
        model="SEL-311C",
        model_name="SEL-311C Line Protection Relay",
        device_type="protection_relay",
        description="Distance relay for transmission line protection",

        oui_prefixes=["00:30:A7", "00:1C:73"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 6.0,
            "mean_ms": 1.5,
            "std_dev_ms": 0.8,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="SEL{10NUM}",
            station_name_pattern="relay-311c-{seq}",
            vendor_short="SEL",
            model_short="311C",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R111-V6",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R110-V3",
                release_date=date(2022, 4, 15),
                cves=["CVE-2023-31170"],
            ),
            FirmwareVariant(
                version="R108-V0",
                release_date=date(2020, 8, 10),
                cves=["CVE-2023-31170", "CVE-2021-31553"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "product_code": "SEL-311C",
            "product_name": "SEL-311C Line Protection Relay",
        },

        snmp_identity={
            "sys_descr": "Schweitzer Engineering Laboratories SEL-311C Line Protection Relay VR111-V6",
            "sys_object_id": "1.3.6.1.4.1.1027.93.27",
            "sys_name": "SEL-31-LINE-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-311C Line Protection Relay",
            "hardware_version": "311C",
        },
    ),
    DeviceTemplate(
        id="sel/relay/sel-487e",
        vendor="SEL",
        vendor_family="SEL-400 Series",
        model="SEL-487E",
        model_name="SEL-487E Transformer Protection Relay",
        device_type="protection_relay",
        description="Transformer differential protection relay",

        oui_prefixes=["00:30:A7", "00:1C:73"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 7.0,
            "mean_ms": 1.6,
            "std_dev_ms": 0.9,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="SEL{10NUM}",
            station_name_pattern="relay-487e-{seq}",
            vendor_short="SEL",
            model_short="487E",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R160-V4",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R158-V2",
                release_date=date(2022, 5, 20),
                cves=["CVE-2023-31170"],
            ),
            FirmwareVariant(
                version="R156-V0",
                release_date=date(2020, 9, 15),
                cves=["CVE-2023-31170", "CVE-2021-31553"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "product_code": "SEL-487E",
            "product_name": "SEL-487E Transformer Protection Relay",
        },

        snmp_identity={
            "sys_descr": "Schweitzer Engineering Laboratories SEL-487E Transformer Protection Relay VR160-V4",
            "sys_object_id": "1.3.6.1.4.1.1027.351.42",
            "sys_name": "SEL-48-TRANSF-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-487E Transformer Protection Relay",
            "hardware_version": "487E",
        },
    ),

    # ------------------------------------------------------------------
    # SEL-5030 acSELerator Quickset — SEL's engineering/SCADA software.
    # Runs on hardened Windows workstations; used as engineering_workstation
    # and scada_primary in SEL_PROTECTION substation scenarios.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="sel/acselerator/quickset-5030",
        vendor="SEL",
        vendor_family="acSELerator",
        model="SEL-5030 acSELerator",
        model_name="SEL-5030 acSELerator Quickset",
        device_type="workstation",
        description=(
            "SEL acSELerator Quickset — relay engineering software "
            "running on a hardened Windows workstation. Operators and "
            "protection engineers use it as the substation HMI and "
            "engineering pivot."
        ),

        oui_prefixes=["00:15:5D", "00:50:56", "00:0C:29"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 40.0,
            "mean_ms": 12.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "dnp3", "modbus_tcp", "iec61850", "https"],

        instance_rules=InstanceGenerationRules(
            serial_format="ACS{8HEX}",
            station_name_pattern="acs-{location}-{seq}",
            vendor_short="SEL",
            model_short="ACS5030",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="9.0.0.0",
                release_date=date(2024, 4, 1),
                is_latest=True,
                is_default=True,
                cves=[],
                notes="acSELerator Quickset 9.0 — latest GA release",
            ),
            FirmwareVariant(
                version="8.3.0.0",
                release_date=date(2023, 6, 15),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "product_code": "SEL-5030 acSELerator",
            "product_name": "acSELerator Quickset (Modbus client)",
            "model_name": "SEL-5030",
        },

        snmp_identity={
            "sys_descr": (
                "Schweitzer Engineering Laboratories SEL-5030 "
                "acSELerator Quickset 9.0.0.0 (Windows workstation)"
            ),
            "sys_object_id": "1.3.6.1.4.1.1027.5030.1",
            "sys_name": "ACS-WORKSTATION-001",
            "sys_contact": "protection-eng@example.com",
            "sys_location": "Substation Control Building",
            "sys_services": 76,
        },

        dnp3_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-5030 acSELerator DNP3 Client",
            "hardware_version": "5030",
            "software_version": "9.0.0.0",
        },
    ),
]
