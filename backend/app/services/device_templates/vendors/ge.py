# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""GE / General Electric device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="ge/pacsystems/rx3i-cpe400",
        vendor="GE",
        vendor_family="PACSystems",
        model="IC695CPE400",
        model_name="PACSystems RX3i CPE400",
        device_type="plc",
        description="High-performance PACSystems controller",

        oui_prefixes=["00:14:49", "00:60:B0", "1C:39:47"],

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
            "mean_ms": 3.5,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="GE{10NUM}",
            station_name_pattern="{role}-rx3i-{seq}",
            vendor_short="GE",
            model_short="CPE4",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V10.10",
                release_date=date(2024, 2, 5),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V9.70",
                release_date=date(2022, 8, 20),
                cves=["CVE-2022-2893"],
            ),
            FirmwareVariant(
                version="V9.50",
                release_date=date(2021, 3, 15),
                cves=["CVE-2022-2893", "CVE-2021-27478"],
            ),
        ],

        modbus_identity={
            "vendor_name": "GE Automation",
            "product_code": "IC695CPE400",
            "vendor_url": "http://www.geautomation.com",
            "product_name": "PACSystems RX3i CPE400",
        },

        ethernet_ip_identity={
            "vendor_id": 82,
            "device_type": 14,
            "product_code": 400,
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "GE PACSystems RX3i CPE400 V10.10",
            "sys_object_id": "1.3.6.1.4.1.3861.897.0",
            "sys_name": "PACSYS-RX3I-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="ge/mark-vie/is420ucsbh1a",
        vendor="GE",
        vendor_family="Mark VIe",
        model="IS420UCSBH1A",
        model_name="Mark VIe Controller",
        device_type="dcs_controller",
        description="Turbine control system controller with redundancy support",

        oui_prefixes=["00:14:49", "00:60:B0", "1C:39:47", "00:C0:4F"],

        tcp_stack={
            "ttl": 128,  # Windows-based
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.8,
            "max_ms": 20.0,
            "mean_ms": 4.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
            "outlier_multiplier": 4.0,
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 5],
            "exception_probability": 0.0002,
            "timeout_probability": 0.0001,
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="IS42{8ALPHANUM}",
            station_name_pattern="{role}-markvie-{seq}",
            vendor_short="GE",
            model_short="UCSB",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="06.03.09",
                release_date=date(2024, 2, 28),
                is_latest=True,
                is_default=True,
                cves=[],
                notes="Latest firmware with security updates",
            ),
            FirmwareVariant(
                version="06.02.00",
                release_date=date(2022, 11, 15),
                cves=["CVE-2022-37953"],
                notes="Vulnerable to denial of service",
            ),
            FirmwareVariant(
                version="06.00.02",
                release_date=date(2021, 7, 20),
                cves=["CVE-2022-37953", "CVE-2021-44477"],
                notes="Multiple vulnerabilities - upgrade recommended",
            ),
            FirmwareVariant(
                version="05.04.00",
                release_date=date(2019, 9, 10),
                cves=["CVE-2022-37953", "CVE-2021-44477", "CVE-2019-13559"],
                notes="Legacy firmware with critical vulnerabilities",
            ),
        ],

        modbus_identity={
            "vendor_name": "GE Vernova",
            "product_code": "IS420UCSBH1A",
            "vendor_url": "http://www.gevernova.com",
            "product_name": "Mark VIe Controller",
            "model_name": "IS420UCSBH1A",
        },

        protocol_quirks={
            "modbus_max_registers": 125,
            "redundancy_support": True,
        },

        snmp_identity={
            "sys_descr": "GE Mark VIe Controller V06.03.09",
            "sys_object_id": "1.3.6.1.4.1.3861.43.57",
            "sys_name": "MARK-VIE-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="ge/proficy/historian",
        vendor="GE",
        vendor_family="Proficy",
        model="Proficy Historian",
        model_name="Proficy Historian",
        device_type="historian",
        description="Industrial data historian for process and manufacturing data",

        oui_prefixes=["00:50:C2", "00:12:A9"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 150.0,
            "mean_ms": 35.0,
            "std_dev_ms": 20.0,
            "distribution": "gaussian",
        },

        supported_protocols=["opc_ua", "modbus_tcp"],

        modbus_identity={
            "vendor_name": "GE Digital",
            "product_code": "Proficy Historian",
            "major_minor_revision": "8.0",
            "vendor_url": "http://www.ge.com/digital",
            "product_name": "Proficy Historian Server",
            "model_name": "Proficy Historian 8.0",
        },

        opc_ua_identity={
            "application_name": "GE Proficy Historian",
            "application_uri": "urn:GE:Proficy:Historian",
            "product_uri": "http://www.ge.com/digital/proficy-historian",
            "manufacturer_name": "GE Digital",
            "product_name": "Proficy Historian",
            "software_version": "8.0.1",
            "build_number": "1234",
            "build_date": "2024-01-15T12:00:00Z",
        },

        instance_rules=InstanceGenerationRules(
            serial_format="HIST{8HEX}",
            station_name_pattern="historian-{location}-{seq}",
            vendor_short="GE",
            model_short="HIST",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="8.0",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="7.1",
                release_date=date(2022, 6, 10),
                cves=["CVE-2022-23127"],
            ),
        ],

        snmp_identity={
            "sys_descr": "GE Proficy Historian V8.0",
            "sys_object_id": "1.3.6.1.4.1.3861.820.39",
            "sys_name": "PROFIC-HISTOR-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="ge/multilin/850",
        vendor="GE",
        vendor_family="Multilin",
        model="850",
        model_name="Multilin 850 Feeder Protection System",
        device_type="protection_relay",
        description="Advanced feeder protection and bay control relay",

        oui_prefixes=["00:14:49", "00:60:B0"],

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

        supported_protocols=["modbus_tcp", "iec61850", "dnp3"],

        instance_rules=InstanceGenerationRules(
            serial_format="GE850{8NUM}",
            station_name_pattern="relay-850-{seq}",
            vendor_short="GE",
            model_short="M850",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V8.00",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V7.90",
                release_date=date(2022, 9, 15),
                cves=["CVE-2022-21805"],
            ),
            FirmwareVariant(
                version="V7.60",
                release_date=date(2020, 6, 20),
                cves=["CVE-2022-21805", "CVE-2020-12009"],
            ),
        ],

        modbus_identity={
            "vendor_name": "GE Grid Solutions",
            "product_code": "850",
            "product_name": "Multilin 850 Feeder Protection",
        },

        snmp_identity={
            "sys_descr": "GE Multilin 850 Feeder Protection System V8.00",
            "sys_object_id": "1.3.6.1.4.1.3861.156.0",
            "sys_name": "MULTIL-850-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "GE Grid Solutions",
            "device_name": "Multilin 850 Feeder Protection System",
            "hardware_version": "850",
        },
    ),
    DeviceTemplate(
        id="ge/multilin/f650",
        vendor="GE",
        vendor_family="Multilin",
        model="F650",
        model_name="Multilin F650 Digital Bay Controller",
        device_type="protection_relay",
        description="Digital bay controller with comprehensive protection",

        oui_prefixes=["00:14:49", "00:60:B0"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 12.0,
            "mean_ms": 2.5,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "dnp3"],

        instance_rules=InstanceGenerationRules(
            serial_format="GEF65{8NUM}",
            station_name_pattern="relay-f650-{seq}",
            vendor_short="GE",
            model_short="F650",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V6.40",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V6.20",
                release_date=date(2022, 5, 10),
                cves=["CVE-2022-21805"],
            ),
        ],

        modbus_identity={
            "vendor_name": "GE Grid Solutions",
            "product_code": "F650",
            "product_name": "Multilin F650 Bay Controller",
        },

        snmp_identity={
            "sys_descr": "GE Multilin F650 Digital Bay Controller V6.40",
            "sys_object_id": "1.3.6.1.4.1.3861.367.15",
            "sys_name": "MULTIL-F650-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "GE Grid Solutions",
            "device_name": "Multilin F650 Digital Bay Controller",
            "hardware_version": "F650",
        },
    ),
    DeviceTemplate(
        id="ge/multilin/t60",
        vendor="GE",
        vendor_family="Multilin",
        model="T60",
        model_name="Multilin T60 Transformer Protection",
        device_type="protection_relay",
        description="Transformer protection relay with comprehensive protection functions",

        oui_prefixes=["00:14:49", "00:60:B0", "1C:39:47"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 7.0,
            "mean_ms": 1.5,
            "std_dev_ms": 0.9,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="GET60{8NUM}",
            station_name_pattern="relay-t60-{seq}",
            vendor_short="GE",
            model_short="T60",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V8.2",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V8.0",
                release_date=date(2022, 6, 15),
                cves=["CVE-2022-21805"],
            ),
            FirmwareVariant(
                version="V7.6",
                release_date=date(2020, 11, 10),
                cves=["CVE-2022-21805", "CVE-2020-6949"],
            ),
        ],

        modbus_identity={
            "vendor_name": "GE Grid Solutions",
            "product_code": "T60",
            "product_name": "Multilin T60 Transformer Protection",
        },

        snmp_identity={
            "sys_descr": "GE Multilin T60 Transformer Protection V8.2",
            "sys_object_id": "1.3.6.1.4.1.3861.998.60",
            "sys_name": "MULTIL-T60-001",
            "sys_location": "Substation",
        },

        dnp3_identity={
            "vendor_name": "GE Grid Solutions",
            "device_name": "Multilin T60 Transformer Protection",
            "hardware_version": "T60",
        },
    ),
    DeviceTemplate(
        id="ge/versamax/ic200udd104",
        vendor="GE",
        vendor_family="VersaMax",
        model="IC200UDD104",
        model_name="IC200UDD104",
        device_type="plc",
        description="GE IC200UDD104",
        oui_prefixes=['00:09:45', '00:30:C1', '00:50:99', '00:22:52'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 5.0,
                "max_ms": 80.0,
                "mean_ms": 20.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.002,
            },
        supported_protocols=['modbus_tcp'],
        firmware_variants=[FirmwareVariant(
            version="4.21",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "GE Fanuc",
                "product_code": "IC200UDD104",
                "major_minor_revision": "4.21",
                "vendor_url": "http://www.gefanuc.com",
                "product_name": "VersaMax Micro PLC",
                "model_name": "VersaMax Micro",
            },

        snmp_identity={
            "sys_descr": "GE IC200UDD104 V4.21",
            "sys_object_id": "1.3.6.1.4.1.3861.867.40",
            "sys_name": "IC200UDD104-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="ge/pacsystems/ic695cpe310",
        vendor="GE",
        vendor_family="PACSystems",
        model="IC695CPE310",
        model_name="IC695CPE310",
        device_type="plc",
        description="GE IC695CPE310",
        oui_prefixes=['00:09:45', '00:30:C1', '00:50:99', '00:22:52'],
        tcp_stack={
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 1.5,
                "max_ms": 40.0,
                "mean_ms": 10.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0008,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="10.80",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "GE Automation",
                "product_code": "IC695CPE310",
                "major_minor_revision": "10.80",
                "vendor_url": "http://www.geautomation.com",
                "product_name": "PACSystems RX3i CPE310",
                "model_name": "PACSystems RX3i",
            },
        ethernet_ip_identity={
                "vendor_id": 82,
                "device_type": 14,
                "product_code": 310,
                "revision_major": 10,
                "revision_minor": 80,
                "serial_number": 3156467269,
                "product_name": "PACSystems RX3i CPE310",
                "state": 3,
            },

        snmp_identity={
            "sys_descr": "GE IC695CPE310 V10.80",
            "sys_object_id": "1.3.6.1.4.1.3861.325.76",
            "sys_name": "IC695CPE310-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="ge/proficy/proficy-historian-7-2",
        vendor="GE",
        vendor_family="Proficy",
        model="Proficy Historian 7.2",
        model_name="Proficy Historian 7.2",
        device_type="server",
        description="GE Proficy Historian 7.2",
        oui_prefixes=['00:09:45', '00:30:C1', '00:50:99', '00:22:52'],
        tcp_stack={
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
                "window_scaling": 7,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 8.0,
                "max_ms": 250.0,
                "mean_ms": 65.0,
                "std_dev_ms": 40.0,
                "distribution": "lognormal",
                "outlier_probability": 0.01,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0015,
                "timeout_probability": 0.0008,
            },
        supported_protocols=['modbus_tcp', 'opc_ua'],
        protocol_quirks={
                "max_concurrent_connections": 300,
                "query_timeout_ms": 30000,
                "data_compression_enabled": True,
                "historian_api_version": "7.2",
            },
        firmware_variants=[FirmwareVariant(
            version="7.2",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "GE Digital",
                "product_code": "Proficy Historian",
                "major_minor_revision": "7.2",
                "vendor_url": "http://www.ge.com/digital",
                "product_name": "Proficy Historian Server",
                "model_name": "Proficy Historian 7.2",
            },
        opc_ua_identity={
                "application_name": "GE Proficy Historian",
                "application_uri": "urn:GE:Proficy:Historian",
                "product_uri": "http://www.ge.com/digital/proficy-historian",
                "manufacturer_name": "GE Digital",
                "product_name": "Proficy Historian",
                "software_version": "7.2.0",
                "build_number": "5678",
                "build_date": "2020-06-10T12:00:00Z",
            },

        snmp_identity={
            "sys_descr": "GE Proficy Historian 7.2 V7.2",
            "sys_object_id": "1.3.6.1.4.1.3861.128.27",
            "sys_name": "PROFIC-HISTOR-001",
            "sys_location": "Industrial Network",
        },
    ),
]
