# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Yokogawa device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="yokogawa/centum-vp/fcu",
        vendor="Yokogawa",
        vendor_family="CENTUM VP",
        model="AFV10D",
        model_name="CENTUM VP Field Control Unit",
        device_type="dcs_controller",
        description="Field control unit for CENTUM VP distributed control system",

        oui_prefixes=["00:A0:64", "00:1E:62", "00:20:4A"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 3.0,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="YOK{2ALPHA}{8NUM}",
            station_name_pattern="dcs-fcu-{seq}",
            vendor_short="YOK",
            model_short="FCU",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R6.06",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R6.03",
                release_date=date(2022, 8, 20),
                cves=["CVE-2022-30997"],
            ),
            FirmwareVariant(
                version="R6.01",
                release_date=date(2021, 3, 10),
                cves=["CVE-2022-30997", "CVE-2021-27510"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Yokogawa Electric Corporation",
            "product_code": "AFV10D",
            "vendor_url": "http://www.yokogawa.com",
            "product_name": "CENTUM VP Field Control Unit",
        },

        snmp_identity={
            "sys_descr": "Yokogawa CENTUM VP Field Control Unit VR6.06",
            "sys_object_id": "1.3.6.1.4.1.2745.633.62",
            "sys_name": "CENTUM-VP-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="yokogawa/prosafe-rs/ssu",
        vendor="Yokogawa",
        vendor_family="ProSafe-RS",
        model="SSC60D",
        model_name="ProSafe-RS Safety Controller",
        device_type="safety_plc",
        description="Safety instrumented system controller for SIL3 applications",

        oui_prefixes=["00:A0:64", "00:1E:62"],

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
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="PSR{10NUM}",
            station_name_pattern="sis-{location}-{seq}",
            vendor_short="YOK",
            model_short="PSR",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R4.06",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R4.03",
                release_date=date(2022, 6, 15),
                cves=["CVE-2022-30997"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Yokogawa Electric Corporation",
            "product_code": "SSC60D",
            "product_name": "ProSafe-RS Safety Controller",
        },

        snmp_identity={
            "sys_descr": "Yokogawa ProSafe-RS Safety Controller VR4.06",
            "sys_object_id": "1.3.6.1.4.1.2745.531.95",
            "sys_name": "PROSAF-SAFETY-001",
            "sys_location": "Safety Cabinet",
        },
    ),
    DeviceTemplate(
        id="yokogawa/analyzer/gc8000",
        vendor="Yokogawa",
        vendor_family="GC8000",
        model="GC8000",
        model_name="GC8000 Gas Chromatograph",
        device_type="analyzer",
        description="Process gas chromatograph for natural gas and refinery applications",

        oui_prefixes=["00:A0:64", "00:1E:62", "00:20:4A"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="GC8K{10NUM}",
            station_name_pattern="gc-{location}-{seq}",
            vendor_short="YOK",
            model_short="GC8K",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.5",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.2",
                release_date=date(2022, 6, 15),
                cves=["CVE-2022-30997"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Yokogawa Electric Corporation",
            "product_code": "GC8000",
            "product_name": "GC8000 Gas Chromatograph",
        },

        snmp_identity={
            "sys_descr": "Yokogawa GC8000 Gas Chromatograph V4.5",
            "sys_object_id": "1.3.6.1.4.1.2745.986.19",
            "sys_name": "GC8000-GAS-001",
            "sys_location": "Process Area",
        },
    ),
    DeviceTemplate(
        id="yokogawa/analyzer/tdls8000",
        vendor="Yokogawa",
        vendor_family="TDLS8000",
        model="TDLS8000",
        model_name="TDLS8000 Laser Analyzer",
        device_type="analyzer",
        description="Tunable diode laser spectrometer for gas analysis",

        oui_prefixes=["00:A0:64", "00:1E:62"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 60.0,
            "mean_ms": 15.0,
            "std_dev_ms": 10.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="TDLS{10NUM}",
            station_name_pattern="tdls-{location}-{seq}",
            vendor_short="YOK",
            model_short="TDLS",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.2",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.0",
                release_date=date(2022, 7, 20),
                cves=["CVE-2022-30997"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Yokogawa Electric Corporation",
            "product_code": "TDLS8000",
            "product_name": "TDLS8000 Laser Analyzer",
        },

        snmp_identity={
            "sys_descr": "Yokogawa TDLS8000 Laser Analyzer V3.2",
            "sys_object_id": "1.3.6.1.4.1.2745.587.19",
            "sys_name": "TDLS80-LASER-001",
            "sys_location": "Process Area",
        },
    ),
    DeviceTemplate(
        id="yokogawa/transmitter/eja530a",
        vendor="Yokogawa",
        vendor_family="EJA-A Series",
        model="EJA530A",
        model_name="EJA530A Pressure Transmitter",
        device_type="transmitter",
        description="Digital differential pressure transmitter for process measurement",

        oui_prefixes=["00:A0:64", "00:1E:62"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 40.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="EJA{10NUM}",
            station_name_pattern="pt-{location}-{seq}",
            vendor_short="YOK",
            model_short="EJA",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V6.0",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.5",
                release_date=date(2022, 5, 10),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Yokogawa Electric Corporation",
            "product_code": "EJA530A",
            "product_name": "EJA530A Pressure Transmitter",
        },

        snmp_identity={
            "sys_descr": "Yokogawa EJA530A Pressure Transmitter V6.0",
            "sys_object_id": "1.3.6.1.4.1.2745.495.57",
            "sys_name": "EJA530-PRESSU-001",
            "sys_location": "Field",
        },
    ),
    DeviceTemplate(
        id="yokogawa/analyzer/flxa402",
        vendor="Yokogawa",
        vendor_family="FLEXA Series",
        model="FLXA402",
        model_name="FLXA402 Multi-Parameter Analyzer",
        device_type="analyzer",
        description="Four-wire pH/ORP analyzer for water quality monitoring",

        oui_prefixes=["00:A0:64", "00:1E:62"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="FLXA{10NUM}",
            station_name_pattern="ph-{location}-{seq}",
            vendor_short="YOK",
            model_short="FLXA",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.5",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.2",
                release_date=date(2022, 4, 15),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Yokogawa Electric Corporation",
            "product_code": "FLXA402",
            "product_name": "FLXA402 Multi-Parameter Analyzer",
        },

        snmp_identity={
            "sys_descr": "Yokogawa FLXA402 Multi-Parameter Analyzer V2.5",
            "sys_object_id": "1.3.6.1.4.1.2745.640.21",
            "sys_name": "FLXA40-MULTI--001",
            "sys_location": "Process Area",
        },
    ),
    DeviceTemplate(
        id="yokogawa/centum-vp/his",
        vendor="Yokogawa",
        vendor_family="CENTUM VP",
        model="HIS",
        model_name="CENTUM VP Human Interface Station",
        device_type="hmi",
        description="Operator interface station for CENTUM VP DCS",

        oui_prefixes=["00:A0:64", "00:1E:62", "00:20:4A"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 12.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="YOK{2ALPHA}{8NUM}",
            station_name_pattern="his-{seq}",
            vendor_short="YOK",
            model_short="HIS",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R6.05",
                release_date=date(2023, 9, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Yokogawa CENTUM VP Human Interface Station VR6.05",
            "sys_object_id": "1.3.6.1.4.1.2745.30.15",
            "sys_name": "CENTUM-VP-001",
            "sys_location": "Control Room",
        },

        modbus_identity={
            "vendor_name": "Yokogawa",
            "product_code": "HIS",
            "product_name": "CENTUM VP Human Interface Station",
        },
    ),
    DeviceTemplate(
        id="yokogawa/centum-vp/ews",
        vendor="Yokogawa",
        vendor_family="CENTUM VP",
        model="EWS",
        model_name="CENTUM VP Engineering Workstation",
        device_type="engineering_station",
        description="Engineering workstation for CENTUM VP configuration",

        oui_prefixes=["00:A0:64", "00:1E:62", "00:20:4A"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 150.0,
            "mean_ms": 40.0,
            "std_dev_ms": 20.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="YOK{2ALPHA}{8NUM}",
            station_name_pattern="ews-{seq}",
            vendor_short="YOK",
            model_short="EWS",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R6.05",
                release_date=date(2023, 9, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Yokogawa CENTUM VP Engineering Workstation VR6.05",
            "sys_object_id": "1.3.6.1.4.1.2745.799.51",
            "sys_name": "CENTUM-VP-001",
            "sys_location": "Engineering Office",
        },

        modbus_identity={
            "vendor_name": "Yokogawa",
            "product_code": "EWS",
            "product_name": "CENTUM VP Engineering Workstation",
        },
    ),
    DeviceTemplate(
        id="yokogawa/exaopc/server",
        vendor="Yokogawa",
        vendor_family="Exaopc",
        model="Exaopc",
        model_name="Exaopc OPC Server",
        device_type="historian",
        description="OPC server and historian for CENTUM VP and ProSafe-RS",

        oui_prefixes=["00:A0:64", "00:1E:62", "00:20:4A"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 200.0,
            "mean_ms": 50.0,
            "std_dev_ms": 25.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="YOK{2ALPHA}{8NUM}",
            station_name_pattern="exaopc-{seq}",
            vendor_short="YOK",
            model_short="EXAOPC",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R3.80",
                release_date=date(2023, 6, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Yokogawa Exaopc OPC Server VR3.80",
            "sys_object_id": "1.3.6.1.4.1.2745.815.60",
            "sys_name": "EXAOPC-OPC-001",
            "sys_location": "Industrial Network",
        },

        modbus_identity={
            "vendor_name": "Yokogawa",
            "product_code": "Exaopc",
            "product_name": "Exaopc OPC Server",
        },
    ),
    DeviceTemplate(
        id="yokogawa/centum-vp/centum-vp",
        vendor="Yokogawa",
        vendor_family="CENTUM VP",
        model="CENTUM VP",
        model_name="CENTUM VP",
        device_type="dcs_controller",
        description="Yokogawa CENTUM VP",
        oui_prefixes=['00:00:C1', '00:02:E0'],
        tcp_stack={
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
        response_timing={
                "min_ms": 3.0,
                "max_ms": 35.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.001,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        supported_protocols=['modbus_tcp'],
        firmware_variants=[FirmwareVariant(
            version="R6.08.00",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "CENTUM-VP",
                "major_minor_revision": "R6.08.00",
                "vendor_url": "http://www.yokogawa.com",
                "product_name": "CENTUM VP Field Control Station",
                "model_name": "CENTUM VP",
            },

        snmp_identity={
            "sys_descr": "Yokogawa CENTUM VP VR6.08.00",
            "sys_object_id": "1.3.6.1.4.1.2745.964.66",
            "sys_name": "CENTUM-VP-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="yokogawa/prosafe-rs/prosafe-rs",
        vendor="Yokogawa",
        vendor_family="ProSafe-RS",
        model="ProSafe-RS",
        model_name="ProSafe-RS",
        device_type="dcs_controller",
        description="Yokogawa ProSafe-RS",
        oui_prefixes=['00:00:C1', '00:02:E0'],
        tcp_stack={
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.0005,
                "outlier_multiplier": 2.5,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0001,
                "timeout_probability": 0.0001,
            },
        supported_protocols=['modbus_tcp'],
        firmware_variants=[FirmwareVariant(
            version="R4.05.00",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "ProSafe-RS",
                "major_minor_revision": "R4.05.00",
                "vendor_url": "http://www.yokogawa.com",
                "product_name": "ProSafe-RS Safety Instrumented System",
                "model_name": "ProSafe-RS",
            },

        snmp_identity={
            "sys_descr": "Yokogawa ProSafe-RS VR4.05.00",
            "sys_object_id": "1.3.6.1.4.1.2745.681.54",
            "sys_name": "PROSAFE-RS-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="yokogawa/rc400g/rc400g",
        vendor="Yokogawa",
        vendor_family="RC400G",
        model="RC400G",
        model_name="RC400G",
        device_type="rtu",
        description="Yokogawa RC400G",
        oui_prefixes=['00:00:C1', '00:02:E0'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 8.0,
                "max_ms": 65.0,
                "mean_ms": 22.0,
                "std_dev_ms": 11.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
        supported_protocols=['modbus_tcp'],
        firmware_variants=[FirmwareVariant(
            version="1.05",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "RC400G",
                "major_minor_revision": "V1.05",
                "vendor_url": "http://www.yokogawa.com",
                "product_name": "RC400G Residual Chlorine Analyzer",
                "model_name": "Chlorine Analyzer",
            },

        snmp_identity={
            "sys_descr": "Yokogawa RC400G V1.05",
            "sys_object_id": "1.3.6.1.4.1.2745.405.66",
            "sys_name": "RC400G-001",
            "sys_location": "Remote Site",
        },
    ),
    DeviceTemplate(
        id="yokogawa/sc450g/sc450g",
        vendor="Yokogawa",
        vendor_family="SC450G",
        model="SC450G",
        model_name="SC450G",
        device_type="rtu",
        description="Yokogawa SC450G",
        oui_prefixes=['00:00:C1', '00:02:E0'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 8.0,
                "max_ms": 60.0,
                "mean_ms": 20.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 3.5,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
        supported_protocols=['modbus_tcp'],
        firmware_variants=[FirmwareVariant(
            version="1.04",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Yokogawa Electric Corporation",
                "product_code": "SC450G",
                "major_minor_revision": "V1.04",
                "vendor_url": "http://www.yokogawa.com",
                "product_name": "SC450G Turbidity Analyzer",
                "model_name": "Turbidity Analyzer",
            },

        snmp_identity={
            "sys_descr": "Yokogawa SC450G V1.04",
            "sys_object_id": "1.3.6.1.4.1.2745.155.2",
            "sys_name": "SC450G-001",
            "sys_location": "Remote Site",
        },
    ),
]
