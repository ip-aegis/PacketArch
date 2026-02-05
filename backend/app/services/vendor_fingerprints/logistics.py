"""Logistics and Distribution vendor fingerprints.

Fingerprint data for logistics, warehouse, and distribution automation equipment.
These devices use EtherNet/IP, PROFINET, and Modbus TCP protocols and are found in:
- E-commerce fulfillment centers
- Distribution centers
- Cold chain/refrigerated warehouses
- Parcel sorting hubs

Vendors covered:
- KUKA (AGVs - KMP mobile platforms)
- MiR - Mobile Industrial Robots (AMRs)
- Cognex (vision systems, barcode readers)
- Impinj (RFID readers)
- Zebra Technologies (RFID readers, barcode scanners)
"""

from typing import Any

# MAC OUI Prefixes for logistics vendors (IEEE registrations)
# NOTE: The authoritative source for MAC generation is:
#   backend/app/protocol_engines/vendor_oui.py (VENDOR_OUIS dict)
KUKA_OUI_PREFIXES = [
    "00:1A:28",  # KUKA Roboter GmbH
    "00:1F:29",  # KUKA Roboter GmbH
    "00:10:DC",  # KUKA Roboter GmbH
]

MIR_OUI_PREFIXES = [
    "00:1E:06",  # Mobile Industrial Robots A/S
]

COGNEX_OUI_PREFIXES = [
    "00:04:3E",  # Cognex Corporation
    "00:0D:88",  # Cognex Corporation
]

IMPINJ_OUI_PREFIXES = [
    "00:16:25",  # Impinj Inc
]

ZEBRA_OUI_PREFIXES = [
    "00:A0:F8",  # Zebra Technologies (Symbol legacy)
    "00:23:68",  # Zebra Technologies
    "AC:3F:A4",  # Zebra Technologies
]

DEMATIC_OUI_PREFIXES = [
    "00:1C:34",  # Dematic (Kion Group)
]


def get_logistics_fingerprints() -> list[dict[str, Any]]:
    """Get all logistics vendor fingerprints."""
    return [
        # ============================================================
        # KUKA - Mobile Platforms (AGVs)
        # ============================================================
        # KUKA KMP 1500 - Heavy-duty AGV platform
        {
            "vendor": "KUKA",
            "vendor_family": "KMP Mobile Platform",
            "model": "KMP 1500",
            "firmware_version": "8.6.0",
            "oui_prefixes": KUKA_OUI_PREFIXES,
            "supported_protocols": ["profinet", "ethernet_ip"],
            "profinet_identity": {
                "vendor_id": 0x0170,  # KUKA PROFINET vendor ID
                "device_id": 0x1500,
                "station_name": "kmp1500",
                "device_type": "KMP 1500 Mobile Platform",
                "device_role": 1,  # IO-Device
                "sw_release": "V8.6.0",
                "im0_manufacturer": "KUKA Roboter GmbH",
                "im0_order_id": "KMP 1500",
                "im0_hw_revision": 3,
                "im0_sw_revision": "V8.6.0",
            },
            "ethernet_ip_identity": {
                "vendor_id": 368,  # KUKA ODVA vendor ID
                "device_type": 43,  # Generic Device
                "product_code": 1500,
                "revision_major": 8,
                "revision_minor": 6,
                "serial_number": 0x4B4D5031,  # KMP1
                "product_name": "KMP 1500 Mobile Platform",
                "state": 3,  # Running
            },
            "tcp_stack": {
                "ttl": 64,  # Linux-based controller
                "window_size": 29200,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
            },
            "error_behavior": {
                "timeout_probability": 0.0005,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # KUKA KMP 600 - Compact AGV platform
        {
            "vendor": "KUKA",
            "vendor_family": "KMP Mobile Platform",
            "model": "KMP 600",
            "firmware_version": "8.5.2",
            "oui_prefixes": KUKA_OUI_PREFIXES,
            "supported_protocols": ["profinet", "ethernet_ip"],
            "profinet_identity": {
                "vendor_id": 0x0170,
                "device_id": 0x0600,
                "station_name": "kmp600",
                "device_type": "KMP 600 Mobile Platform",
                "device_role": 1,
                "sw_release": "V8.5.2",
                "im0_manufacturer": "KUKA Roboter GmbH",
                "im0_order_id": "KMP 600",
            },
            "ethernet_ip_identity": {
                "vendor_id": 368,
                "device_type": 43,
                "product_code": 600,
                "revision_major": 8,
                "revision_minor": 5,
                "product_name": "KMP 600 Mobile Platform",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # KUKA Fleet Manager - Central AGV coordination
        {
            "vendor": "KUKA",
            "vendor_family": "Fleet Management",
            "model": "KUKA.FleetManager",
            "firmware_version": "3.2.1",
            "oui_prefixes": KUKA_OUI_PREFIXES,
            "supported_protocols": ["profinet", "ethernet_ip", "modbus_tcp"],
            "profinet_identity": {
                "vendor_id": 0x0170,  # KUKA PROFINET vendor ID
                "device_id": 0x9001,
                "station_name": "kuka-fleetmgr",
                "device_type": "KUKA Fleet Manager",
                "device_role": 2,  # IO-Controller
                "sw_release": "V3.2.1",
                "im0_manufacturer": "KUKA Roboter GmbH",
                "im0_order_id": "FleetManager",
                "im0_hw_revision": 2,
                "im0_sw_revision": "V3.2.1",
            },
            "ethernet_ip_identity": {
                "vendor_id": 368,
                "device_type": 12,  # Communications Adapter
                "product_code": 9001,
                "revision_major": 3,
                "revision_minor": 2,
                "product_name": "KUKA.FleetManager",
                "state": 3,
            },
            "modbus_identity": {
                "vendor_name": "KUKA Roboter GmbH",
                "product_code": "FleetManager",
                "major_minor_revision": "3.2.1",
                "product_name": "KUKA Fleet Management System",
                "model_name": "FleetManager",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 15.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # MiR - Mobile Industrial Robots (AMRs)
        # ============================================================
        # MiR100 - Entry-level AMR (100kg payload)
        {
            "vendor": "MiR",
            "vendor_family": "MiR Mobile Robots",
            "model": "MiR100",
            "firmware_version": "3.12.0",
            "oui_prefixes": MIR_OUI_PREFIXES,
            "supported_protocols": ["modbus_tcp", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Mobile Industrial Robots A/S",
                "product_code": "MiR100",
                "major_minor_revision": "3.12.0",
                "vendor_url": "https://www.mobile-industrial-robots.com",
                "product_name": "MiR100 Autonomous Mobile Robot",
                "model_name": "MiR100",
            },
            "ethernet_ip_identity": {
                "vendor_id": 0,  # Generic EtherNet/IP adapter
                "device_type": 12,  # Communications Adapter
                "product_code": 100,
                "revision_major": 3,
                "revision_minor": 12,
                "product_name": "MiR100",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,  # Linux-based
                "window_size": 29200,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.02,
            },
            "error_behavior": {
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
            "is_builtin": True,
        },
        # MiR250 - Mid-range AMR (250kg payload)
        {
            "vendor": "MiR",
            "vendor_family": "MiR Mobile Robots",
            "model": "MiR250",
            "firmware_version": "3.12.0",
            "oui_prefixes": MIR_OUI_PREFIXES,
            "supported_protocols": ["modbus_tcp", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Mobile Industrial Robots A/S",
                "product_code": "MiR250",
                "major_minor_revision": "3.12.0",
                "vendor_url": "https://www.mobile-industrial-robots.com",
                "product_name": "MiR250 Autonomous Mobile Robot",
                "model_name": "MiR250",
            },
            "ethernet_ip_identity": {
                "vendor_id": 0,
                "device_type": 12,
                "product_code": 250,
                "revision_major": 3,
                "revision_minor": 12,
                "product_name": "MiR250",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # MiR500 - Heavy-duty AMR (500kg payload, cold-rated available)
        {
            "vendor": "MiR",
            "vendor_family": "MiR Mobile Robots",
            "model": "MiR500",
            "firmware_version": "3.12.0",
            "oui_prefixes": MIR_OUI_PREFIXES,
            "supported_protocols": ["modbus_tcp", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Mobile Industrial Robots A/S",
                "product_code": "MiR500",
                "major_minor_revision": "3.12.0",
                "vendor_url": "https://www.mobile-industrial-robots.com",
                "product_name": "MiR500 Autonomous Mobile Robot",
                "model_name": "MiR500",
            },
            "ethernet_ip_identity": {
                "vendor_id": 0,
                "device_type": 12,
                "product_code": 500,
                "revision_major": 3,
                "revision_minor": 12,
                "product_name": "MiR500",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 60.0,
                "mean_ms": 18.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # MiR Fleet Controller
        {
            "vendor": "MiR",
            "vendor_family": "MiR Fleet",
            "model": "MiR Fleet",
            "firmware_version": "3.8.0",
            "oui_prefixes": MIR_OUI_PREFIXES,
            "supported_protocols": ["modbus_tcp"],
            "modbus_identity": {
                "vendor_name": "Mobile Industrial Robots A/S",
                "product_code": "MiR Fleet",
                "major_minor_revision": "3.8.0",
                "product_name": "MiR Fleet Management System",
                "model_name": "MiR Fleet",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 20.0,
                "mean_ms": 6.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # COGNEX - Vision Systems and Barcode Readers
        # ============================================================
        # Cognex In-Sight 7000 - Industrial vision camera
        {
            "vendor": "Cognex",
            "vendor_family": "In-Sight",
            "model": "In-Sight 7802",
            "firmware_version": "6.3.2",
            "oui_prefixes": COGNEX_OUI_PREFIXES,
            "supported_protocols": ["ethernet_ip"],
            "ethernet_ip_identity": {
                "vendor_id": 112,  # Cognex ODVA vendor ID
                "device_type": 43,  # Generic Device
                "product_code": 7802,
                "revision_major": 6,
                "revision_minor": 3,
                "serial_number": 0x49533738,  # IS78
                "product_name": "In-Sight 7802 Vision System",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 100.0,
                "mean_ms": 35.0,
                "std_dev_ms": 20.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # Cognex DataMan 370 - Fixed-mount barcode reader
        {
            "vendor": "Cognex",
            "vendor_family": "DataMan",
            "model": "DataMan 370",
            "firmware_version": "6.2.0",
            "oui_prefixes": COGNEX_OUI_PREFIXES,
            "supported_protocols": ["ethernet_ip", "modbus_tcp"],
            "ethernet_ip_identity": {
                "vendor_id": 112,
                "device_type": 43,
                "product_code": 370,
                "revision_major": 6,
                "revision_minor": 2,
                "product_name": "DataMan 370 Barcode Reader",
                "state": 3,
            },
            "modbus_identity": {
                "vendor_name": "Cognex Corporation",
                "product_code": "DataMan 370",
                "major_minor_revision": "6.2.0",
                "product_name": "DataMan 370 Fixed-Mount Barcode Reader",
                "model_name": "DataMan 370",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # Cognex DataMan 280 - Compact barcode reader
        {
            "vendor": "Cognex",
            "vendor_family": "DataMan",
            "model": "DataMan 280",
            "firmware_version": "6.1.5",
            "oui_prefixes": COGNEX_OUI_PREFIXES,
            "supported_protocols": ["ethernet_ip"],
            "ethernet_ip_identity": {
                "vendor_id": 112,
                "device_type": 43,
                "product_code": 280,
                "revision_major": 6,
                "revision_minor": 1,
                "product_name": "DataMan 280 Barcode Reader",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 40.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # IMPINJ - RFID Readers
        # ============================================================
        # Impinj Speedway R700 - Enterprise RFID reader
        {
            "vendor": "Impinj",
            "vendor_family": "Speedway",
            "model": "Speedway R700",
            "firmware_version": "8.2.0",
            "oui_prefixes": IMPINJ_OUI_PREFIXES,
            "supported_protocols": ["modbus_tcp", "snmp"],
            "modbus_identity": {
                "vendor_name": "Impinj Inc",
                "product_code": "Speedway R700",
                "major_minor_revision": "8.2.0",
                "vendor_url": "https://www.impinj.com",
                "product_name": "Impinj Speedway R700 RAIN RFID Reader",
                "model_name": "R700",
            },
            "snmp_identity": {
                "sys_descr": "Impinj Speedway R700 RAIN RFID Reader V8.2.0",
                "sys_object_id": "1.3.6.1.4.1.25882.1.1",
                "sys_name": "SPEEDWAY-R700-001",
                "sys_location": "Dock Door",
                "sys_contact": "rfid@warehouse.local",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 3.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # Impinj Speedway R420 - Mid-range RFID reader
        {
            "vendor": "Impinj",
            "vendor_family": "Speedway",
            "model": "Speedway R420",
            "firmware_version": "7.5.0",
            "oui_prefixes": IMPINJ_OUI_PREFIXES,
            "supported_protocols": ["modbus_tcp", "snmp"],
            "modbus_identity": {
                "vendor_name": "Impinj Inc",
                "product_code": "Speedway R420",
                "major_minor_revision": "7.5.0",
                "product_name": "Impinj Speedway R420 RAIN RFID Reader",
                "model_name": "R420",
            },
            "snmp_identity": {
                "sys_descr": "Impinj Speedway R420 RAIN RFID Reader V7.5.0",
                "sys_object_id": "1.3.6.1.4.1.25882.1.2",
                "sys_name": "SPEEDWAY-R420-001",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 40.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # ZEBRA TECHNOLOGIES - RFID Readers and Scanners
        # ============================================================
        # Zebra FX9600 - Fixed RFID reader
        {
            "vendor": "Zebra",
            "vendor_family": "Fixed RFID",
            "model": "FX9600",
            "firmware_version": "3.29.15",
            "oui_prefixes": ZEBRA_OUI_PREFIXES,
            "supported_protocols": ["snmp", "modbus_tcp"],
            "snmp_identity": {
                "sys_descr": "Zebra FX9600 Fixed RFID Reader V3.29.15",
                "sys_object_id": "1.3.6.1.4.1.10642.1.1",
                "sys_name": "FX9600-001",
                "sys_location": "Portal",
                "sys_contact": "rfid@warehouse.local",
            },
            "modbus_identity": {
                "vendor_name": "Zebra Technologies Corporation",
                "product_code": "FX9600",
                "major_minor_revision": "3.29.15",
                "product_name": "Zebra FX9600 8-Port RFID Reader",
                "model_name": "FX9600",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 18.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # Zebra FX7500 - Compact fixed RFID reader
        {
            "vendor": "Zebra",
            "vendor_family": "Fixed RFID",
            "model": "FX7500",
            "firmware_version": "3.28.10",
            "oui_prefixes": ZEBRA_OUI_PREFIXES,
            "supported_protocols": ["snmp", "modbus_tcp"],
            "snmp_identity": {
                "sys_descr": "Zebra FX7500 Fixed RFID Reader V3.28.10",
                "sys_object_id": "1.3.6.1.4.1.10642.1.2",
                "sys_name": "FX7500-001",
            },
            "modbus_identity": {
                "vendor_name": "Zebra Technologies Corporation",
                "product_code": "FX7500",
                "major_minor_revision": "3.28.10",
                "product_name": "Zebra FX7500 4-Port RFID Reader",
                "model_name": "FX7500",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 45.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # DEMATIC - Warehouse Automation Controllers
        # ============================================================
        # Dematic iQ Software Platform - WCS Controller
        {
            "vendor": "Dematic",
            "vendor_family": "iQ Platform",
            "model": "iQ WCS Controller",
            "firmware_version": "5.4.0",
            "oui_prefixes": DEMATIC_OUI_PREFIXES,
            "supported_protocols": ["modbus_tcp", "ethernet_ip"],
            "modbus_identity": {
                "vendor_name": "Dematic Corporation",
                "product_code": "iQ-WCS",
                "major_minor_revision": "5.4.0",
                "product_name": "Dematic iQ Warehouse Control System",
                "model_name": "iQ WCS",
            },
            "ethernet_ip_identity": {
                "vendor_id": 0,  # Generic
                "device_type": 12,
                "product_code": 5400,
                "revision_major": 5,
                "revision_minor": 4,
                "product_name": "Dematic iQ WCS",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 128,  # Windows-based server
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # CISCO - Industrial Network Switches (SNMP)
        # ============================================================
        {
            "vendor": "Cisco",
            "vendor_family": "IE Industrial Ethernet",
            "model": "IE-3300-8T2S",
            "firmware_version": "17.6.3",
            "oui_prefixes": ["00:1B:0D", "00:1E:BD", "00:22:55"],
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Cisco IOS Software, IE3300 Software (IE3300-UNIVERSALK9-M), Version 17.6.3",
                "sys_object_id": "1.3.6.1.4.1.9.1.2815",
                "sys_name": "IE-Switch-001",
                "sys_location": "Control Room",
                "sys_contact": "network@facility.local",
            },
            "tcp_stack": {
                "ttl": 255,  # Cisco default
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 15.0,
                "mean_ms": 3.0,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # Cisco Stratix (Rockwell branded)
        {
            "vendor": "Cisco",
            "vendor_family": "Stratix",
            "model": "Stratix 5700",
            "firmware_version": "15.2(7)E3",
            "oui_prefixes": ["00:1B:0D", "00:1E:BD"],
            "supported_protocols": ["snmp"],
            "snmp_identity": {
                "sys_descr": "Cisco IOS Software, Stratix 5700 Software, Version 15.2(7)E3",
                "sys_object_id": "1.3.6.1.4.1.9.1.1858",
                "sys_name": "Stratix-5700-001",
                "sys_location": "Plant Floor",
                "sys_contact": "ot-network@facility.local",
            },
            "tcp_stack": {
                "ttl": 255,
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 10.0,
                "mean_ms": 2.5,
                "std_dev_ms": 1.5,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # ROCKWELL - I/O Modules (EtherNet/IP)
        # ============================================================
        # 1756-EN2T EtherNet/IP Communication Module
        {
            "vendor": "Rockwell",
            "vendor_family": "ControlLogix",
            "model": "1756-EN2T",
            "firmware_version": "11.003",
            "oui_prefixes": ["00:00:BC", "00:1D:9C"],
            "supported_protocols": ["ethernet_ip"],
            "ethernet_ip_identity": {
                "vendor_id": 1,  # Rockwell Automation
                "device_type": 12,  # Communications Adapter
                "product_code": 166,
                "revision_major": 11,
                "revision_minor": 3,
                "product_name": "1756-EN2T/D",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 8.0,
                "mean_ms": 2.0,
                "std_dev_ms": 1.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # Generic Point I/O (pick-to-light, sensors)
        {
            "vendor": "Rockwell",
            "vendor_family": "Point I/O",
            "model": "1734-AENT",
            "firmware_version": "6.011",
            "oui_prefixes": ["00:00:BC", "00:1D:9C"],
            "supported_protocols": ["ethernet_ip"],
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 7,  # Generic I/O
                "product_code": 92,
                "revision_major": 6,
                "revision_minor": 11,
                "product_name": "1734-AENT Point I/O",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 4096,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 0.5,
                "max_ms": 5.0,
                "mean_ms": 1.5,
                "std_dev_ms": 0.8,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # PowerFlex 755 High-Performance Drive
        {
            "vendor": "Rockwell",
            "vendor_family": "PowerFlex",
            "model": "PowerFlex 755",
            "firmware_version": "20.013",
            "oui_prefixes": ["00:00:BC", "00:1D:9C"],
            "supported_protocols": ["ethernet_ip"],
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 2,  # AC Drive
                "product_code": 56,
                "revision_major": 20,
                "revision_minor": 13,
                "product_name": "PowerFlex 755",
                "state": 3,
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 15.0,
                "mean_ms": 4.0,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # SICK - Barcode Scanners (Explicit CLV650 match)
        # ============================================================
        {
            "vendor": "SICK",
            "vendor_family": "CLV",
            "model": "SICK CLV650",
            "firmware_version": "5.60",
            "oui_prefixes": ["00:06:6F", "00:10:BE"],
            "supported_protocols": ["ethernet_ip", "modbus_tcp"],
            "ethernet_ip_identity": {
                "vendor_id": 218,  # SICK AG ODVA vendor ID
                "device_type": 12,
                "product_code": 650,
                "revision_major": 5,
                "revision_minor": 60,
                "product_name": "CLV650 Barcode Scanner",
                "state": 3,
            },
            "modbus_identity": {
                "vendor_name": "SICK AG",
                "product_code": "1041807",
                "major_minor_revision": "V5.60",
                "product_name": "CLV650 Fixed Mount Barcode Scanner",
                "model_name": "CLV650",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 8.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # HONEYWELL - Temperature Controllers (Modbus)
        # ============================================================
        {
            "vendor": "Honeywell",
            "vendor_family": "HC900",
            "model": "HC900 Controller",
            "firmware_version": "7.3",
            "oui_prefixes": ["00:40:84", "00:22:6A"],
            "supported_protocols": ["modbus_tcp"],
            "modbus_identity": {
                "vendor_name": "Honeywell International Inc",
                "product_code": "900C52-0001",
                "major_minor_revision": "7.3",
                "product_name": "HC900 Hybrid Controller",
                "model_name": "HC900",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # Honeywell UDC Temperature Controller
        {
            "vendor": "Honeywell",
            "vendor_family": "UDC",
            "model": "UDC3500",
            "firmware_version": "6.1",
            "oui_prefixes": ["00:40:84", "00:22:6A"],
            "supported_protocols": ["modbus_tcp"],
            "modbus_identity": {
                "vendor_name": "Honeywell International Inc",
                "product_code": "DC3500-EE-0L00-200",
                "major_minor_revision": "6.1",
                "product_name": "UDC3500 Universal Digital Controller",
                "model_name": "UDC3500",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 10.0,
                "max_ms": 80.0,
                "mean_ms": 25.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
        # Honeywell Temperature Transmitter
        {
            "vendor": "Honeywell",
            "vendor_family": "STT",
            "model": "STT850",
            "firmware_version": "4.2",
            "oui_prefixes": ["00:40:84", "00:22:6A"],
            "supported_protocols": ["modbus_tcp"],
            "modbus_identity": {
                "vendor_name": "Honeywell International Inc",
                "product_code": "STT850-E-0-AHS",
                "major_minor_revision": "4.2",
                "product_name": "STT850 SmartLine Temperature Transmitter",
                "model_name": "STT850",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 4096,
                "mss": 536,  # Smaller MSS for transmitter
            },
            "response_timing": {
                "min_ms": 20.0,
                "max_ms": 150.0,
                "mean_ms": 50.0,
                "std_dev_ms": 25.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # GE - Historian / HMI/SCADA
        # ============================================================
        {
            "vendor": "GE",
            "vendor_family": "Proficy",
            "model": "Proficy Historian",
            "firmware_version": "8.0",
            "oui_prefixes": ["00:04:A3", "00:60:B0"],
            "supported_protocols": ["ethernet_ip", "modbus_tcp"],
            "ethernet_ip_identity": {
                "vendor_id": 82,  # GE
                "device_type": 12,
                "product_code": 8000,
                "revision_major": 8,
                "revision_minor": 0,
                "product_name": "Proficy Historian",
                "state": 3,
            },
            "modbus_identity": {
                "vendor_name": "GE Digital",
                "product_code": "Historian",
                "major_minor_revision": "8.0",
                "product_name": "Proficy Historian OPC-UA Server",
                "model_name": "Historian",
            },
            "tcp_stack": {
                "ttl": 128,  # Windows-based
                "window_size": 65535,
                "mss": 1460,
                "sack_permitted": True,
            },
            "response_timing": {
                "min_ms": 1.0,
                "max_ms": 25.0,
                "mean_ms": 5.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # SCHNEIDER - HMI (Modbus)
        # ============================================================
        {
            "vendor": "Schneider",
            "vendor_family": "Magelis",
            "model": "HMIGTO5310",
            "firmware_version": "5.1",
            "oui_prefixes": ["00:80:F4", "00:60:E5"],
            "supported_protocols": ["modbus_tcp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "HMIGTO5310",
                "major_minor_revision": "5.1",
                "product_name": "Magelis GTO Advanced HMI",
                "model_name": "HMIGTO5310",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 40.0,
                "mean_ms": 12.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # SCHNEIDER - Safety PLC (Modbus)
        # ============================================================
        {
            "vendor": "Schneider",
            "vendor_family": "Modicon",
            "model": "TM5CSLC100FS",
            "firmware_version": "2.11",
            "oui_prefixes": ["00:80:F4", "00:60:E5"],
            "supported_protocols": ["modbus_tcp"],
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "TM5CSLC100FS",
                "major_minor_revision": "2.11",
                "product_name": "TM5 Safety Logic Controller",
                "model_name": "TM5CSLC100FS",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
            "response_timing": {
                "min_ms": 2.0,
                "max_ms": 20.0,
                "mean_ms": 6.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },

        # ============================================================
        # HMS - Remote Gateway (eWON Flexy)
        # ============================================================
        {
            "vendor": "HMS",
            "vendor_family": "eWON Flexy",
            "model": "Flexy 205",
            "firmware_version": "14.5",
            "oui_prefixes": ["00:06:71"],
            "supported_protocols": ["modbus_tcp", "snmp"],
            "modbus_identity": {
                "vendor_name": "HMS Industrial Networks",
                "product_code": "Flexy205",
                "major_minor_revision": "14.5",
                "product_name": "eWON Flexy 205 Industrial Router",
                "model_name": "Flexy205",
            },
            "snmp_identity": {
                "sys_descr": "eWON Flexy 205 - Firmware 14.5s0",
                "sys_object_id": "1.3.6.1.4.1.8284.2.1",
                "sys_name": "FLEXY-205-001",
                "sys_location": "Remote Site",
                "sys_contact": "remote@facility.local",
            },
            "tcp_stack": {
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
                "sack_permitted": True,
            },
            "response_timing": {
                "min_ms": 5.0,
                "max_ms": 100.0,
                "mean_ms": 25.0,
                "std_dev_ms": 20.0,
                "distribution": "gaussian",
            },
            "is_builtin": True,
        },
    ]
