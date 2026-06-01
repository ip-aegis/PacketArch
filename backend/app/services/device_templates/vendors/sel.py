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
                cves=["CVE-2024-2103"],
            ),
            FirmwareVariant(
                version="R150-V0",
                release_date=date(2020, 10, 10),
                cves=["CVE-2024-2103"],
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
                cves=["CVE-2023-31148", "CVE-2023-31150", "CVE-2023-2310"],
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
                cves=["CVE-2023-31176"],
            ),
            FirmwareVariant(
                version="R157-V0",
                release_date=date(2020, 11, 10),
                cves=["CVE-2023-31176"],
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
                cves=[],
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
                cves=[],
            ),
            FirmwareVariant(
                version="R108-V0",
                release_date=date(2020, 8, 10),
                cves=[],
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
                cves=[],
            ),
            FirmwareVariant(
                version="R156-V0",
                release_date=date(2020, 9, 15),
                cves=[],
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

    # ------------------------------------------------------------------
    # SEL-411L — Line Current Differential System with integrated PMU.
    # High-end transmission line protection (87L/21/67 + C37.118 streaming).
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="sel/relay/sel-411l",
        vendor="SEL",
        vendor_family="SEL-400 Series",
        model="SEL-411L",
        model_name="SEL-411L Line Current Differential System",
        device_type="protection_relay",
        description="Line current differential and distance protection with integrated synchrophasor PMU",

        oui_prefixes=["00:30:A7", "00:1C:73"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 8.0,
            "mean_ms": 1.8,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850", "c37118"],

        instance_rules=InstanceGenerationRules(
            serial_format="SEL{10NUM}",
            station_name_pattern="relay-411l-{seq}",
            vendor_short="SEL",
            model_short="411L",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R125-V3",
                release_date=date(2024, 3, 5),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R123-V2",
                release_date=date(2022, 9, 12),
                cves=["CVE-2023-2265"],
            ),
            FirmwareVariant(
                version="R120-V0",
                release_date=date(2020, 5, 18),
                cves=["CVE-2023-2265"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "product_code": "SEL-411L",
            "product_name": "SEL-411L Line Current Differential System",
        },

        snmp_identity={
            "sys_descr": "Schweitzer Engineering Laboratories SEL-411L Line Current Differential System VR125-V3",
            "sys_object_id": "1.3.6.1.4.1.1027.411.51",
            "sys_name": "SEL-41-LINEDIFF-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-411L Line Current Differential System",
            "hardware_version": "411L",
        },

        iec61850_identity={
            "ied_name": "SEL_411L_IED",
            "vendor": "SEL",
            "software_version": "R125-V3",
            "logical_devices": ["CTRL", "MEAS", "PROT"],
            "icd_filename": "SEL_411L.icd",
        },

        c37118_identity={
            "station_name": "SEL_411L_PMU_01 ",
            "idcode": 4111,
            "data_rate": 60,
            "fnom": 60,
            "num_phasors": 6,
            "num_analog": 2,
            "num_digital": 1,
            "channel_names": ["VA", "VB", "VC", "IA", "IB", "IC"],
            "config_count": 1,
        },
    ),

    # ------------------------------------------------------------------
    # SEL-787 — Transformer Protection Relay (87T differential + 50/51).
    # Often deployed as PMU on transformer high/low sides for WAMS.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="sel/relay/sel-787",
        vendor="SEL",
        vendor_family="SEL-700 Series",
        model="SEL-787",
        model_name="SEL-787 Transformer Protection Relay",
        device_type="protection_relay",
        description="Two-winding transformer differential protection with synchrophasor PMU",

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

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850", "c37118"],

        instance_rules=InstanceGenerationRules(
            serial_format="SEL{10NUM}",
            station_name_pattern="relay-787-{seq}",
            vendor_short="SEL",
            model_short="787",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R208-V4",
                release_date=date(2024, 2, 28),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R206-V2",
                release_date=date(2022, 6, 8),
                cves=["CVE-2024-2103"],
            ),
            FirmwareVariant(
                version="R203-V0",
                release_date=date(2020, 4, 22),
                cves=["CVE-2024-2103"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "product_code": "SEL-787",
            "product_name": "SEL-787 Transformer Protection Relay",
        },

        snmp_identity={
            "sys_descr": "Schweitzer Engineering Laboratories SEL-787 Transformer Protection Relay VR208-V4",
            "sys_object_id": "1.3.6.1.4.1.1027.787.34",
            "sys_name": "SEL-78-XFMR-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-787 Transformer Protection Relay",
            "hardware_version": "787",
        },

        iec61850_identity={
            "ied_name": "SEL_787_IED",
            "vendor": "SEL",
            "software_version": "R208-V4",
            "logical_devices": ["CTRL", "MEAS", "PROT"],
            "icd_filename": "SEL_787.icd",
        },

        c37118_identity={
            "station_name": "SEL_787_PMU_01  ",
            "idcode": 7870,
            "data_rate": 30,
            "fnom": 60,
            "num_phasors": 6,
            "num_analog": 1,
            "num_digital": 1,
            "channel_names": ["VA", "VB", "VC", "IA", "IB", "IC"],
            "config_count": 1,
        },
    ),

    # ------------------------------------------------------------------
    # SEL-3555 — Next-gen Real-Time Automation Controller (Linux-based).
    # Larger I/O, more protocols, IEC 104 master, web HMI.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="sel/rtac/sel-3555",
        vendor="SEL",
        vendor_family="SEL-3500 Series",
        model="SEL-3555",
        model_name="SEL-3555 RTAC",
        device_type="rtu",
        description="Next-generation Real-Time Automation Controller with expanded protocol support",

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
            "mean_ms": 1.4,
            "std_dev_ms": 0.9,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["modbus_tcp", "dnp3", "iec61850", "iec104", "snmp", "c37118"],

        instance_rules=InstanceGenerationRules(
            serial_format="RTAC{10NUM}",
            station_name_pattern="rtac-3555-{seq}",
            vendor_short="SEL",
            model_short="3555",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R152-V3",
                release_date=date(2024, 4, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R150-V1",
                release_date=date(2022, 11, 18),
                cves=["CVE-2023-31148", "CVE-2023-31149", "CVE-2023-2310"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "product_code": "SEL-3555",
            "product_name": "SEL-3555 Real-Time Automation Controller",
        },

        snmp_identity={
            "sys_descr": "Schweitzer Engineering Laboratories SEL-3555 RTAC VR152-V3",
            "sys_object_id": "1.3.6.1.4.1.1027.3555.12",
            "sys_name": "SEL-35-RTAC-555",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-3555 Real-Time Automation Controller",
            "hardware_version": "3555",
        },

        iec104_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-3555 Real-Time Automation Controller",
            "hardware_version": "3555",
        },

        iec61850_identity={
            "ied_name": "SEL_3555_RTAC",
            "vendor": "SEL",
            "software_version": "R152-V3",
            "logical_devices": ["CTRL", "MEAS"],
            "icd_filename": "SEL_3555.icd",
        },
    ),

    # ------------------------------------------------------------------
    # SEL-735 — Power Quality and Revenue Meter (Class 0.2 accuracy).
    # ANSI C12.20 revenue, IEEE 1159 PQ, DNP3 metering points.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="sel/meter/sel-735",
        vendor="SEL",
        vendor_family="SEL-700 Series",
        model="SEL-735",
        model_name="SEL-735 Power Quality and Revenue Meter",
        device_type="meter",
        description="Class 0.2 revenue meter with IEEE 1159 power-quality recording",

        oui_prefixes=["00:30:A7", "00:1C:73"],

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
            serial_format="SEL{10NUM}",
            station_name_pattern="meter-735-{seq}",
            vendor_short="SEL",
            model_short="735",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R110-V2",
                release_date=date(2024, 1, 30),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R108-V1",
                release_date=date(2022, 3, 14),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "product_code": "SEL-735",
            "product_name": "SEL-735 Power Quality and Revenue Meter",
        },

        snmp_identity={
            "sys_descr": "Schweitzer Engineering Laboratories SEL-735 Power Quality and Revenue Meter VR110-V2",
            "sys_object_id": "1.3.6.1.4.1.1027.735.22",
            "sys_name": "SEL-73-METER-001",
            "sys_location": "Substation Switchyard",
        },

        dnp3_identity={
            "vendor_name": "Schweitzer Engineering Laboratories",
            "device_name": "SEL-735 Power Quality and Revenue Meter",
            "hardware_version": "735",
        },
    ),
]
