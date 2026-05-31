# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Siemens device templates (includes Siemens ITS)."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="siemens/s7-1500/cpu-1516-3",
        vendor="Siemens",
        vendor_family="S7-1500",
        model="6ES7 516-3AN02-0AB0",
        model_name="CPU 1516-3 PN/DP",
        device_type="plc",
        description="High-performance S7-1500 CPU with PROFINET and PROFIBUS interfaces",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
            "ecn_support": False,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 10.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
            "outlier_probability": 0.003,
            "outlier_multiplier": 5.0,
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 5, 6],
            "exception_probability": 0.0003,
            "timeout_probability": 0.0001,
        },

        supported_protocols=["profinet", "s7comm", "modbus_tcp", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="S C-{8HEX}",
            station_name_pattern="{role}-s71500-{seq}",
            vendor_short="SIE",
            model_short="1516",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.0.3",
                release_date=date(2023, 11, 15),
                is_latest=True,
                is_default=True,
                cves=[],
                notes="Latest version with security patches",
            ),
            FirmwareVariant(
                version="V2.9.7",
                release_date=date(2023, 6, 20),
                cves=[],
                notes="Previous stable release",
            ),
            FirmwareVariant(
                version="V2.9.4",
                release_date=date(2022, 11, 10),
                cves=["CVE-2022-38465"],
                notes="Vulnerable to authentication bypass",
                identity_overrides={
                    "modbus_identity": {"major_minor_revision": "V2.9.4"},
                    "profinet_identity": {"im0_sw_revision": "V2.9.4"},
                },
            ),
            FirmwareVariant(
                version="V2.8.1",
                release_date=date(2021, 8, 15),
                cves=["CVE-2022-38465", "CVE-2021-37205"],
                notes="Multiple vulnerabilities - memory corruption and auth bypass",
                identity_overrides={
                    "modbus_identity": {"major_minor_revision": "V2.8.1"},
                    "profinet_identity": {"im0_sw_revision": "V2.8.1"},
                },
            ),
            FirmwareVariant(
                version="V2.5.0",
                release_date=date(2020, 3, 10),
                cves=["CVE-2022-38465", "CVE-2021-37205", "CVE-2020-15782", "CVE-2019-13945"],
                notes="Legacy firmware with critical vulnerabilities",
                identity_overrides={
                    "modbus_identity": {"major_minor_revision": "V2.5.0"},
                    "profinet_identity": {"im0_sw_revision": "V2.5.0"},
                },
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6ES7 516-3AN02-0AB0",
            "vendor_url": "http://www.siemens.com",
            "product_name": "CPU 1516-3 PN/DP",
            "model_name": "S7-1500",
            # major_minor_revision merged from firmware
        },

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0301,
            "device_role": 2,  # Controller
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 516-3AN02-0AB0",
            "im0_hw_revision": 2,
            # station_name and im0_sw_revision merged from instance/firmware
        },

        s7_identity={
            "module_type": "CPU 1516-3 PN/DP",
            "order_code": "6ES7 516-3AN02-0AB0",
            "copyright": "Original Siemens Equipment",
            "module_name": "PLC_1",
            "hardware_version": "V2",
            # serial_number and plant_id merged from instance
        },

        opc_ua_identity={
            "application_name": "Siemens SIMATIC CPU 1516-3 OPC UA Server",
            "application_uri": "urn:Siemens:SIMATIC:S7-1500:CPU1516-3",
            "product_uri": "http://www.siemens.com/simatic-s7-1500",
            "manufacturer_name": "Siemens AG",
            "product_name": "SIMATIC S7-1500 OPC UA Server",
            "software_version": "3.0.3",
            "build_number": "V3.0.3",
        },

        protocol_quirks={
            "profinet_cycle_time_us": 1000,
            "s7_max_pdu_size": 960,
            "s7_connection_type": 0x01,  # PG connection
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC CPU 1516-3 PN/DP V3.0.3",
            "sys_object_id": "1.3.6.1.4.1.4329.66.23",
            "sys_name": "CPU-1516-3-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-1200/cpu-1214c",
        vendor="Siemens",
        vendor_family="S7-1200",
        model="6ES7 214-1AG40-0XB0",
        model_name="CPU 1214C DC/DC/DC",
        device_type="plc",
        description="Compact S7-1200 CPU for small to medium automation tasks",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "window_scaling": 5,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 25.0,
            "mean_ms": 6.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet", "s7comm", "modbus_tcp", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="S C-{8HEX}",
            station_name_pattern="{role}-s71200-{seq}",
            vendor_short="SIE",
            model_short="1214",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.6.0",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.5.2",
                release_date=date(2023, 5, 20),
                cves=[],
            ),
            FirmwareVariant(
                version="V4.4.0",
                release_date=date(2022, 8, 10),
                cves=["CVE-2022-38465"],
            ),
            FirmwareVariant(
                version="V4.2.1",
                release_date=date(2021, 3, 15),
                cves=["CVE-2022-38465", "CVE-2021-37185"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6ES7 214-1AG40-0XB0",
            "product_name": "CPU 1214C DC/DC/DC",
            "model_name": "S7-1200",
        },

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x010D,
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 214-1AG40-0XB0",
        },

        s7_identity={
            "module_type": "CPU 1214C DC/DC/DC",
            "order_code": "6ES7 214-1AG40-0XB0",
            "copyright": "Original Siemens Equipment",
            "module_name": "PLC_1",
            "hardware_version": "V4",
        },

        opc_ua_identity={
            "application_name": "Siemens SIMATIC CPU 1214C OPC UA Server",
            "application_uri": "urn:Siemens:SIMATIC:S7-1200:CPU1214C",
            "product_uri": "http://www.siemens.com/simatic-s7-1200",
            "manufacturer_name": "Siemens AG",
            "product_name": "SIMATIC S7-1200 OPC UA Server",
            "software_version": "4.6.0",
            "build_number": "V4.6.0",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC CPU 1214C DC/DC/DC V4.6.0",
            "sys_object_id": "1.3.6.1.4.1.4329.523.66",
            "sys_name": "CPU-1214C-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="siemens/hmi/ktp700",
        vendor="Siemens",
        vendor_family="SIMATIC HMI",
        model="6AV2 123-2GB03-0AX0",
        model_name="KTP700 Basic",
        device_type="hmi",
        description="7-inch Basic Panel with touch and key operation",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["profinet", "s7comm"],

        instance_rules=InstanceGenerationRules(
            serial_format="S V-{8HEX}",
            station_name_pattern="hmi-{location}-{seq}",
            vendor_short="SIE",
            model_short="ktp700",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V18.0.0.0",
                release_date=date(2023, 10, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V17.0.0.0",
                release_date=date(2022, 9, 15),
                cves=["CVE-2022-40227"],
            ),
            FirmwareVariant(
                version="V16.0.0.0",
                release_date=date(2021, 6, 20),
                cves=["CVE-2022-40227", "CVE-2021-27383"],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0403,
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6AV2 123-2GB03-0AX0",
        },

        s7_identity={
            "module_type": "SIMATIC HMI KTP700 Basic",
            "order_code": "6AV2 123-2GB03-0AX0",
            "copyright": "Original Siemens Equipment",
            "module_name": "HMI_1",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC HMI KTP700 Basic V18.0.0.0",
            "sys_object_id": "1.3.6.1.4.1.4329.613.68",
            "sys_name": "KTP700-BASIC-001",
            "sys_location": "Control Room",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-1500/cpu-1517-3",
        vendor="Siemens",
        vendor_family="S7-1500",
        model="6ES7 517-3AP00-0AB0",
        model_name="CPU 1517-3 PN/DP",
        device_type="plc",
        description="High-performance S7-1500 CPU with PROFINET and PROFIBUS interfaces",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
            "ecn_support": False,
        },

        response_timing={
            "min_ms": 0.2,
            "max_ms": 8.0,
            "mean_ms": 1.5,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
            "outlier_multiplier": 5.0,
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 5, 6],
            "exception_probability": 0.0003,
            "timeout_probability": 0.0001,
        },

        supported_protocols=["profinet", "s7comm", "modbus_tcp", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="S C-{8HEX}",
            station_name_pattern="{role}-s71517-{seq}",
            vendor_short="SIE",
            model_short="1517",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.0.3",
                release_date=date(2023, 11, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.9.4",
                release_date=date(2022, 11, 10),
                cves=["CVE-2022-38465"],
                notes="Vulnerable to authentication bypass",
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6ES7 517-3AP00-0AB0",
            "vendor_url": "http://www.siemens.com",
            "product_name": "CPU 1517-3 PN/DP",
            "model_name": "S7-1500",
        },

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0302,
            "device_role": 2,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 517-3AP00-0AB0",
            "im0_hw_revision": 2,
        },

        s7_identity={
            "module_type": "CPU 1517-3 PN/DP",
            "order_code": "6ES7 517-3AP00-0AB0",
            "copyright": "Original Siemens Equipment",
            "module_name": "PLC_1",
            "hardware_version": "V2",
        },

        opc_ua_identity={
            "application_name": "Siemens SIMATIC CPU 1517-3 OPC UA Server",
            "application_uri": "urn:Siemens:SIMATIC:S7-1500:CPU1517-3",
            "product_uri": "http://www.siemens.com/simatic-s7-1500",
            "manufacturer_name": "Siemens AG",
            "product_name": "SIMATIC S7-1500 OPC UA Server",
            "software_version": "3.0.3",
            "build_number": "V3.0.3",
        },

        ethernet_ip_identity={
            "vendor_id": 285,
            "device_type": 14,
            "product_code": 1517,
            "revision_major": 3,
            "revision_minor": 0,
            "product_name": "CPU 1517-3 PN/DP",
            "state": 3,
        },

        protocol_quirks={
            "profinet_cycle_time_us": 500,
            "s7_max_pdu_size": 960,
            "s7_connection_type": 0x01,
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC CPU 1517-3 PN/DP V3.0.3",
            "sys_object_id": "1.3.6.1.4.1.4329.737.50",
            "sys_name": "CPU-1517-3-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-1500/cpu-1516-3-v1",
        vendor="Siemens",
        vendor_family="S7-1500",
        model="6ES7 516-3AN01-0AB0",
        model_name="CPU 1516-3 PN/DP",
        device_type="plc",
        description="S7-1500 CPU with PROFINET and PROFIBUS interfaces (earlier version)",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 10.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet", "s7comm", "modbus_tcp", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="S C-{8HEX}",
            station_name_pattern="{role}-s71516-{seq}",
            vendor_short="SIE",
            model_short="1516",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.9.7",
                release_date=date(2023, 6, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.8.1",
                release_date=date(2021, 8, 15),
                cves=["CVE-2021-37205"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6ES7 516-3AN01-0AB0",
            "product_name": "CPU 1516-3 PN/DP",
            "model_name": "S7-1500",
        },

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0301,
            "device_role": 2,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 516-3AN01-0AB0",
        },

        s7_identity={
            "module_type": "CPU 1516-3 PN/DP",
            "order_code": "6ES7 516-3AN01-0AB0",
            "copyright": "Original Siemens Equipment",
            "module_name": "PLC_1",
            "hardware_version": "V1",
        },

        opc_ua_identity={
            "application_name": "Siemens SIMATIC CPU 1516-3 OPC UA Server",
            "application_uri": "urn:Siemens:SIMATIC:S7-1500:CPU1516-3",
            "product_uri": "http://www.siemens.com/simatic-s7-1500",
            "manufacturer_name": "Siemens AG",
            "product_name": "SIMATIC S7-1500 OPC UA Server",
            "software_version": "2.9.7",
            "build_number": "V2.9.7",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC CPU 1516-3 PN/DP V2.9.7",
            "sys_object_id": "1.3.6.1.4.1.4329.244.74",
            "sys_name": "CPU-1516-3-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-1500/cpu-1511-1",
        vendor="Siemens",
        vendor_family="S7-1500",
        model="6ES7 511-1AK02-0AB0",
        model_name="CPU 1511-1 PN",
        device_type="plc",
        description="Compact S7-1500 CPU for small automation tasks",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "window_scaling": 5,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.5,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet", "s7comm", "modbus_tcp", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="S C-{8HEX}",
            station_name_pattern="{role}-s71511-{seq}",
            vendor_short="SIE",
            model_short="1511",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.0.1",
                release_date=date(2023, 9, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6ES7 511-1AK02-0AB0",
            "product_name": "CPU 1511-1 PN",
            "model_name": "S7-1500",
        },

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0101,
            "device_role": 2,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 511-1AK02-0AB0",
        },

        s7_identity={
            "module_type": "CPU 1511-1 PN",
            "order_code": "6ES7 511-1AK02-0AB0",
            "copyright": "Original Siemens Equipment",
            "module_name": "PLC_1",
            "hardware_version": "V2",
        },

        opc_ua_identity={
            "application_name": "Siemens SIMATIC CPU 1511-1 OPC UA Server",
            "application_uri": "urn:Siemens:SIMATIC:S7-1500:CPU1511-1",
            "product_uri": "http://www.siemens.com/simatic-s7-1500",
            "manufacturer_name": "Siemens AG",
            "product_name": "SIMATIC S7-1500 OPC UA Server",
            "software_version": "3.0.1",
            "build_number": "V3.0.1",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC CPU 1511-1 PN V3.0.1",
            "sys_object_id": "1.3.6.1.4.1.4329.884.86",
            "sys_name": "CPU-1511-1-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-1500/cpu-1516f-3",
        vendor="Siemens",
        vendor_family="S7-1500F",
        model="6ES7 516-3FN01-0AB0",
        model_name="CPU 1516F-3 PN/DP",
        device_type="safety_plc",
        description="Failsafe S7-1500 CPU for safety applications up to SIL3/PLe",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 10.0,
            "mean_ms": 2.5,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet", "profisafe", "s7comm", "modbus_tcp", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="S C-{8HEX}",
            station_name_pattern="{role}-s71516f-{seq}",
            vendor_short="SIE",
            model_short="1516F",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.0.3",
                release_date=date(2023, 11, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.9.4",
                release_date=date(2022, 11, 10),
                cves=["CVE-2022-38465"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6ES7 516-3FN01-0AB0",
            "product_name": "CPU 1516F-3 PN/DP",
            "model_name": "S7-1500F",
        },

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0311,
            "device_role": 2,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 516-3FN01-0AB0",
        },

        s7_identity={
            "module_type": "CPU 1516F-3 PN/DP",
            "order_code": "6ES7 516-3FN01-0AB0",
            "copyright": "Original Siemens Equipment",
            "module_name": "FPLC_1",
            "hardware_version": "V2",
        },

        opc_ua_identity={
            "application_name": "Siemens SIMATIC CPU 1516F-3 OPC UA Server",
            "application_uri": "urn:Siemens:SIMATIC:S7-1500F:CPU1516F-3",
            "product_uri": "http://www.siemens.com/simatic-s7-1500f",
            "manufacturer_name": "Siemens AG",
            "product_name": "SIMATIC S7-1500F OPC UA Server",
            "software_version": "3.0.3",
            "build_number": "V3.0.3",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC CPU 1516F-3 PN/DP V3.0.3",
            "sys_object_id": "1.3.6.1.4.1.4329.747.88",
            "sys_name": "CPU-1516F--001",
            "sys_location": "Safety Cabinet",
        },
    ),
    DeviceTemplate(
        id="siemens/hmi/tp1200-comfort",
        vendor="Siemens",
        vendor_family="SIMATIC HMI",
        model="6AV2 124-0MC01-0AX0",
        model_name="TP1200 Comfort",
        device_type="hmi",
        description="12-inch Comfort Panel with touch operation",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 20.0,
            "std_dev_ms": 12.0,
            "distribution": "lognormal",
        },

        supported_protocols=["profinet", "s7comm", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="S V-{8HEX}",
            station_name_pattern="hmi-{location}-{seq}",
            vendor_short="SIE",
            model_short="tp1200",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V18.0.0.0",
                release_date=date(2023, 10, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V17.0.0.0",
                release_date=date(2022, 9, 15),
                cves=["CVE-2022-40227"],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0424,
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6AV2 124-0MC01-0AX0",
        },

        s7_identity={
            "module_type": "SIMATIC HMI TP1200 Comfort",
            "order_code": "6AV2 124-0MC01-0AX0",
            "copyright": "Original Siemens Equipment",
            "module_name": "HMI_1",
        },

        opc_ua_identity={
            "application_name": "Siemens SIMATIC HMI Comfort OPC UA Client",
            "application_uri": "urn:Siemens:SIMATIC:HMI:Comfort:TP1200",
            "product_uri": "http://www.siemens.com/simatic-hmi-comfort",
            "manufacturer_name": "Siemens AG",
            "product_name": "SIMATIC HMI TP1200 Comfort",
            "software_version": "18.0.0",
            "build_number": "V18.0.0.0",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC HMI TP1200 Comfort V18.0.0.0",
            "sys_object_id": "1.3.6.1.4.1.4329.519.27",
            "sys_name": "TP1200-COMFOR-001",
            "sys_location": "Control Room",
        },
    ),
    DeviceTemplate(
        id="siemens/hmi/ktp900-basic",
        vendor="Siemens",
        vendor_family="SIMATIC HMI",
        model="6AV2 123-2JB03-0AX0",
        model_name="KTP900 Basic",
        device_type="hmi",
        description="9-inch Basic Panel with touch and key operation",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["profinet", "s7comm"],

        instance_rules=InstanceGenerationRules(
            serial_format="S V-{8HEX}",
            station_name_pattern="hmi-{location}-{seq}",
            vendor_short="SIE",
            model_short="ktp900",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V18.0.0.0",
                release_date=date(2023, 10, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0409,
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6AV2 123-2JB03-0AX0",
        },

        s7_identity={
            "module_type": "SIMATIC HMI KTP900 Basic",
            "order_code": "6AV2 123-2JB03-0AX0",
            "copyright": "Original Siemens Equipment",
            "module_name": "HMI_1",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC HMI KTP900 Basic V18.0.0.0",
            "sys_object_id": "1.3.6.1.4.1.4329.998.50",
            "sys_name": "KTP900-BASIC-001",
            "sys_location": "Control Room",
        },
    ),
    DeviceTemplate(
        id="siemens/drives/g120c",
        vendor="Siemens",
        vendor_family="SINAMICS",
        model="6SL3210-1PE21-1UL0",
        model_name="SINAMICS G120C",
        device_type="drive",
        description="Compact frequency converter for simple drive tasks",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 30.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="T-{10ALPHANUM}",
            station_name_pattern="drive-g120c-{seq}",
            vendor_short="SIE",
            model_short="G120C",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.8",
                release_date=date(2023, 6, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6SL3210-1PE21-1UL0",
            "product_name": "SINAMICS G120C",
            "model_name": "SINAMICS",
        },

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0A01,
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6SL3210-1PE21-1UL0",
        },

        snmp_identity={
            "sys_descr": "Siemens SINAMICS G120C V4.8",
            "sys_object_id": "1.3.6.1.4.1.4329.733.62",
            "sys_name": "SINAMI-G120C-001",
            "sys_location": "Motor Control Center",
        },
    ),
    DeviceTemplate(
        id="siemens/drives/s120",
        vendor="Siemens",
        vendor_family="SINAMICS",
        model="6SL3310-1TE32-6AA3",
        model_name="SINAMICS S120",
        device_type="servo",
        description="High-performance servo drive system for motion control",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.25,
            "max_ms": 5.0,
            "mean_ms": 1.0,
            "std_dev_ms": 0.5,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet"],

        instance_rules=InstanceGenerationRules(
            serial_format="T-{10ALPHANUM}",
            station_name_pattern="servo-s120-{seq}",
            vendor_short="SIE",
            model_short="S120",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.2",
                release_date=date(2023, 8, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0A20,
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6SL3310-1TE32-6AA3",
        },

        snmp_identity={
            "sys_descr": "Siemens SINAMICS S120 V5.2",
            "sys_object_id": "1.3.6.1.4.1.4329.431.69",
            "sys_name": "SINAMI-S120-001",
            "sys_location": "Machine",
        },
    ),
    DeviceTemplate(
        id="siemens/drives/g115d",
        vendor="Siemens",
        vendor_family="SINAMICS",
        model="6SL3525-0PE21-5AA1",
        model_name="SINAMICS G115D",
        device_type="drive",
        description="Distributed frequency converter for conveyor applications",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 25.0,
            "mean_ms": 6.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet"],

        instance_rules=InstanceGenerationRules(
            serial_format="T-{10ALPHANUM}",
            station_name_pattern="drive-g115d-{seq}",
            vendor_short="SIE",
            model_short="G115D",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V1.1",
                release_date=date(2023, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0A15,
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6SL3525-0PE21-5AA1",
        },

        snmp_identity={
            "sys_descr": "Siemens SINAMICS G115D V1.1",
            "sys_object_id": "1.3.6.1.4.1.4329.224.64",
            "sys_name": "SINAMI-G115D-001",
            "sys_location": "Motor Control Center",
        },
    ),
    DeviceTemplate(
        id="siemens/io/et200sp-im155-6",
        vendor="Siemens",
        vendor_family="ET 200SP",
        model="6ES7155-6AU01-0BN0",
        model_name="ET 200SP IM155-6 PN",
        device_type="io_module",
        description="PROFINET interface module for ET 200SP distributed I/O",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.25,
            "max_ms": 5.0,
            "mean_ms": 1.0,
            "std_dev_ms": 0.5,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet"],

        instance_rules=InstanceGenerationRules(
            serial_format="S C-{8HEX}",
            station_name_pattern="et200sp-{seq}",
            vendor_short="SIE",
            model_short="ET200SP",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.2.0",
                release_date=date(2023, 5, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0B01,
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7155-6AU01-0BN0",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC ET 200SP IM155-6 PN V4.2.0",
            "sys_object_id": "1.3.6.1.4.1.4329.285.77",
            "sys_name": "ET-200SP-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="siemens/traffic/cp-8000",
        vendor="Siemens",
        vendor_family="SITRAFFIC",
        model="6NH3112-3BA00-0XX0",
        model_name="CP-8000",
        device_type="traffic_controller",
        description="Central traffic management controller for ITS applications",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 50.0,
            "mean_ms": 10.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="CP8-{8HEX}",
            station_name_pattern="tmc-cp8000-{seq}",
            vendor_short="SIE",
            model_short="CP8000",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V1.3.0",
                release_date=date(2023, 5, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V1.2.0",
                release_date=date(2022, 3, 15),
                cves=["CVE-2023-28489"],
                notes="Vulnerable to command injection",
            ),
        ],

        snmp_identity={
            "sys_descr": "Siemens SITRAFFIC CP-8000 Traffic Controller V1.3.0",
            "sys_object_id": "1.3.6.1.4.1.4329.10.8000",
        },
    ),
    DeviceTemplate(
        id="siemens/traffic/c600",
        vendor="Siemens",
        vendor_family="SITRAFFIC",
        model="C600",
        model_name="Siemens C600 Controller",
        device_type="traffic_controller",
        description="Field traffic signal controller with NTCIP support",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 100.0,
            "mean_ms": 20.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["snmp", "bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="C6-{8HEX}",
            station_name_pattern="signal-c600-{seq}",
            vendor_short="SIE",
            model_short="C600",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.5",
                release_date=date(2023, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Siemens SITRAFFIC C600 Signal Controller V2.5",
            "sys_object_id": "1.3.6.1.4.1.4329.10.600",
        },

        bacnet_identity={
            "vendor_id": 7,
            "device_type": "Traffic Controller",
            "model_name": "SITRAFFIC C600",
            "firmware_revision": "V2.5",
        },
    ),
    DeviceTemplate(
        id="siemens/traffic/m60",
        vendor="Siemens",
        vendor_family="SITRAFFIC",
        model="M60",
        model_name="Siemens M60 Master",
        device_type="master_station",
        description="Master traffic signal controller for intersection coordination",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 40.0,
            "mean_ms": 8.0,
            "std_dev_ms": 6.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="M60-{8HEX}",
            station_name_pattern="master-m60-{seq}",
            vendor_short="SIE",
            model_short="M60",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.1",
                release_date=date(2023, 4, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.8",
                release_date=date(2021, 9, 15),
                cves=["CVE-2020-25230"],
                notes="Vulnerable to denial of service",
            ),
        ],

        snmp_identity={
            "sys_descr": "Siemens SITRAFFIC M60 Master Controller V3.1",
            "sys_object_id": "1.3.6.1.4.1.4329.10.60",
        },
    ),
    DeviceTemplate(
        id="siemens/bms/desigo-cc",
        vendor="Siemens",
        vendor_family="Desigo",
        model="5WG1255-1AB02",
        model_name="Desigo CC",
        device_type="bms_controller",
        description="Building management system for HVAC, lighting, and access control",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 200.0,
            "mean_ms": 50.0,
            "std_dev_ms": 30.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="DCC-{8ALPHANUM}",
            station_name_pattern="desigo-cc-{seq}",
            vendor_short="SIE",
            model_short="DCC",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.0",
                release_date=date(2023, 6, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.2",
                release_date=date(2022, 1, 15),
                cves=["CVE-2022-31465"],
                notes="Privilege escalation vulnerability",
            ),
        ],

        bacnet_identity={
            "vendor_id": 42,
            "model_name": "Desigo CC",
            "device_instance": 0,
        },

        snmp_identity={
            "sys_descr": "Siemens Desigo CC Building Management System V5.0",
            "sys_object_id": "1.3.6.1.4.1.4329.20.255",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-300/cpu-315-2-pn-dp",
        vendor="Siemens",
        vendor_family="S7-300",
        model="CPU 315-2 PN/DP",
        model_name="CPU 315-2 PN/DP",
        device_type="plc",
        description="S7-300 CPU with integrated PROFINET and PROFIBUS interfaces (legacy)",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": False,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 80.0,
            "mean_ms": 25.0,
            "std_dev_ms": 12.0,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet", "s7comm"],

        instance_rules=InstanceGenerationRules(
            serial_format="S V-{6HEX}",
            station_name_pattern="s7300-{location}-{seq}",
            vendor_short="SIE",
            model_short="315",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.2.16",
                release_date=date(2019, 6, 1),
                is_latest=True,
                is_default=True,
                cves=["CVE-2019-10929"],
                notes="Legacy product - limited security updates",
            ),
            FirmwareVariant(
                version="V3.2.12",
                release_date=date(2017, 3, 15),
                cves=["CVE-2019-10929", "CVE-2017-2681"],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0102,
            "device_role": 2,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 315-2EH14-0AB0",
        },

        s7_identity={
            "module_type": "CPU 315-2 PN/DP",
            "order_code": "6ES7 315-2EH14-0AB0",
            "copyright": "Original Siemens Equipment",
            "module_name": "PLC_1",
            "hardware_version": "V3",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC CPU 315-2 PN/DP V3.2.16",
            "sys_object_id": "1.3.6.1.4.1.4329.489.26",
            "sys_name": "CPU-315-2-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-400/cpu-416-3-pn-dp",
        vendor="Siemens",
        vendor_family="S7-400",
        model="CPU 416-3 PN/DP",
        model_name="CPU 416-3 PN/DP",
        device_type="plc",
        description="High-end S7-400 CPU for complex automation tasks (legacy)",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "timestamps_enabled": False,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 50.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet", "s7comm"],

        instance_rules=InstanceGenerationRules(
            serial_format="S V-{8HEX}",
            station_name_pattern="s7400-{location}-{seq}",
            vendor_short="SIE",
            model_short="416",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V7.0.9",
                release_date=date(2020, 2, 1),
                is_latest=True,
                is_default=True,
                cves=["CVE-2019-10929"],
                notes="Legacy product - limited security updates",
            ),
            FirmwareVariant(
                version="V6.0.8",
                release_date=date(2018, 5, 10),
                cves=["CVE-2019-10929", "CVE-2017-2681"],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0401,
            "device_role": 2,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 416-3XS07-0AB0",
        },

        s7_identity={
            "module_type": "CPU 416-3 PN/DP",
            "order_code": "6ES7 416-3XS07-0AB0",
            "copyright": "Original Siemens Equipment",
            "module_name": "PLC_1",
            "hardware_version": "V7",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC CPU 416-3 PN/DP V7.0.9",
            "sys_object_id": "1.3.6.1.4.1.4329.809.6",
            "sys_name": "CPU-416-3-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="siemens/et200mp/im155-5-pn",
        vendor="Siemens",
        vendor_family="ET 200MP",
        model="ET 200MP IM155-5 PN",
        model_name="ET 200MP IM155-5 PN",
        device_type="io_module",
        description="ET 200MP distributed I/O interface module for PROFINET",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 15.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet"],

        instance_rules=InstanceGenerationRules(
            serial_format="S E-{6HEX}",
            station_name_pattern="et200mp-{location}-{seq}",
            vendor_short="SIE",
            model_short="ET200MP",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.2.3",
                release_date=date(2023, 9, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0B01,
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 155-5AA01-0AB0",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC ET 200MP IM155-5 PN V4.2.3",
            "sys_object_id": "1.3.6.1.4.1.4329.303.87",
            "sys_name": "ET-200MP-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-1200/cpu-1214fc",
        vendor="Siemens",
        vendor_family="S7-1200",
        model="CPU 1214FC DC/DC/DC",
        model_name="CPU 1214FC DC/DC/DC",
        device_type="safety_plc",
        description="S7-1200 Fail-safe CPU with integrated safety I/O",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 20.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet", "profisafe", "s7comm", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="S C-{6HEX}",
            station_name_pattern="s71200f-{location}-{seq}",
            vendor_short="SIE",
            model_short="1214FC",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.6.0",
                release_date=date(2023, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.5.0",
                release_date=date(2022, 8, 15),
                cves=["CVE-2022-38465"],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x010F,
            "device_role": 2,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 214-1HF40-0XB0",
        },

        s7_identity={
            "module_type": "CPU 1214FC DC/DC/DC",
            "order_code": "6ES7 214-1HF40-0XB0",
            "copyright": "Original Siemens Equipment",
            "module_name": "FPLC_1",
            "hardware_version": "V4",
        },

        opc_ua_identity={
            "application_name": "Siemens SIMATIC CPU 1214FC OPC UA Server",
            "application_uri": "urn:Siemens:SIMATIC:S7-1200F:CPU1214FC",
            "product_uri": "http://www.siemens.com/simatic-s7-1200f",
            "manufacturer_name": "Siemens AG",
            "product_name": "SIMATIC S7-1200F OPC UA Server",
            "software_version": "4.6.0",
            "build_number": "V4.6.0",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC CPU 1214FC DC/DC/DC V4.6.0",
            "sys_object_id": "1.3.6.1.4.1.4329.119.94",
            "sys_name": "CPU-1214FC-001",
            "sys_location": "Safety Cabinet",
        },
    ),
    DeviceTemplate(
        id="siemens/wincc/professional",
        vendor="Siemens",
        vendor_family="WinCC",
        model="WinCC Professional",
        model_name="WinCC Professional",
        device_type="scada",
        description="SCADA system for visualization and process control",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 15.0,
            "distribution": "gaussian",
        },

        supported_protocols=["s7comm", "opc_ua", "modbus_tcp"],

        s7_identity={
            "order_code": "6AV2105-0DA07-0AA0",
            "module_type": "WinCC Professional V18",
            "firmware_version": "V18.0",
            "hardware_version": "N/A",
        },

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "WinCC Professional",
            "major_minor_revision": "V18.0",
            "vendor_url": "http://www.siemens.com",
            "product_name": "SIMATIC WinCC Professional",
            "model_name": "SCADA/HMI Runtime",
        },

        opc_ua_identity={
            "application_name": "Siemens SIMATIC WinCC",
            "application_uri": "urn:Siemens:SIMATIC:WinCC",
            "product_uri": "http://www.siemens.com/simatic-wincc",
            "manufacturer_name": "Siemens AG",
            "product_name": "SIMATIC WinCC Professional",
            "software_version": "18.0.0",
            "build_number": "V18.0",
            "build_date": "2023-06-01T12:00:00Z",
        },

        instance_rules=InstanceGenerationRules(
            serial_format="WINCC-{6HEX}",
            station_name_pattern="wincc-{location}-{seq}",
            vendor_short="SIE",
            model_short="WinCC",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V18.0",
                release_date=date(2023, 10, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V17.0",
                release_date=date(2022, 4, 15),
                cves=["CVE-2022-32260"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Siemens SIMATIC WinCC Professional V18.0",
            "sys_object_id": "1.3.6.1.4.1.4329.369.26",
            "sys_name": "WINCC-PROFES-001",
            "sys_location": "Control Room",
        },
    ),
    DeviceTemplate(
        id="siemens/siprotec/7sj85",
        vendor="Siemens",
        vendor_family="SIPROTEC 5",
        model="7SJ85",
        model_name="SIPROTEC 7SJ85 Overcurrent Protection",
        device_type="protection_relay",
        description="Overcurrent and motor protection relay",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 8.0,
            "mean_ms": 1.5,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="SIE7SJ{8NUM}",
            station_name_pattern="relay-7sj85-{seq}",
            vendor_short="SIE",
            model_short="7SJ85",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V9.40",
                release_date=date(2024, 2, 5),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V9.20",
                release_date=date(2022, 7, 15),
                cves=["CVE-2022-32528"],
            ),
            FirmwareVariant(
                version="V8.30",
                release_date=date(2020, 12, 10),
                cves=["CVE-2022-32528", "CVE-2020-15795"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "7SJ85",
            "product_name": "SIPROTEC 7SJ85 Overcurrent Protection",
        },

        snmp_identity={
            "sys_descr": "Siemens SIPROTEC 7SJ85 Overcurrent Protection V9.40",
            "sys_object_id": "1.3.6.1.4.1.4329.577.53",
            "sys_name": "SIPROT-7SJ85-001",
            "sys_location": "Substation",
        },
    ),
    DeviceTemplate(
        id="siemens/siprotec/7sd87",
        vendor="Siemens",
        vendor_family="SIPROTEC 5",
        model="7SD87",
        model_name="SIPROTEC 7SD87 Differential Protection",
        device_type="protection_relay",
        description="Line differential protection relay",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.2,
            "max_ms": 6.0,
            "mean_ms": 1.2,
            "std_dev_ms": 0.8,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="SIE7SD{8NUM}",
            station_name_pattern="relay-7sd87-{seq}",
            vendor_short="SIE",
            model_short="7SD87",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V9.40",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V9.10",
                release_date=date(2022, 5, 20),
                cves=["CVE-2022-32528"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "7SD87",
            "product_name": "SIPROTEC 7SD87 Differential Protection",
        },

        snmp_identity={
            "sys_descr": "Siemens SIPROTEC 7SD87 Differential Protection V9.40",
            "sys_object_id": "1.3.6.1.4.1.4329.579.75",
            "sys_name": "SIPROT-7SD87-001",
            "sys_location": "Substation",
        },
    ),
    DeviceTemplate(
        id="siemens/siprotec/7sl87",
        vendor="Siemens",
        vendor_family="SIPROTEC 5",
        model="7SL87",
        model_name="SIPROTEC 7SL87 Line Differential",
        device_type="protection_relay",
        description="Line differential protection relay for transmission lines",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.2,
            "max_ms": 5.0,
            "mean_ms": 1.0,
            "std_dev_ms": 0.6,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="SIE7SL{8NUM}",
            station_name_pattern="relay-7sl87-{seq}",
            vendor_short="SIE",
            model_short="7SL87",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V9.40",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V9.20",
                release_date=date(2022, 8, 15),
                cves=["CVE-2022-32528"],
            ),
            FirmwareVariant(
                version="V8.30",
                release_date=date(2021, 1, 10),
                cves=["CVE-2022-32528", "CVE-2020-15795"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "7SL87",
            "product_name": "SIPROTEC 7SL87 Line Differential",
        },

        snmp_identity={
            "sys_descr": "Siemens SIPROTEC 7SL87 Line Differential V9.40",
            "sys_object_id": "1.3.6.1.4.1.4329.75.97",
            "sys_name": "SIPROT-7SL87-001",
            "sys_location": "Substation",
        },
    ),
    DeviceTemplate(
        id="siemens/siprotec/7ut87",
        vendor="Siemens",
        vendor_family="SIPROTEC 5",
        model="7UT87",
        model_name="SIPROTEC 7UT87 Transformer Differential",
        device_type="protection_relay",
        description="Transformer differential protection relay",

        oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.2,
            "max_ms": 5.0,
            "mean_ms": 1.0,
            "std_dev_ms": 0.6,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "iec61850"],

        instance_rules=InstanceGenerationRules(
            serial_format="SIE7UT{8NUM}",
            station_name_pattern="relay-7ut87-{seq}",
            vendor_short="SIE",
            model_short="7UT87",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V9.40",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V9.20",
                release_date=date(2022, 8, 15),
                cves=["CVE-2022-32528"],
            ),
            FirmwareVariant(
                version="V8.30",
                release_date=date(2021, 1, 10),
                cves=["CVE-2022-32528", "CVE-2020-15795"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "7UT87",
            "product_name": "SIPROTEC 7UT87 Transformer Differential",
        },

        snmp_identity={
            "sys_descr": "Siemens SIPROTEC 7UT87 Transformer Differential V9.40",
            "sys_object_id": "1.3.6.1.4.1.4329.277.26",
            "sys_name": "SIPROT-7UT87-001",
            "sys_location": "Substation",
        },
    ),
    DeviceTemplate(
        id="siemens/sinamics/g120",
        vendor="Siemens",
        vendor_family="SINAMICS",
        model="G120",
        model_name="SINAMICS G120 Drive",
        device_type="drive",
        description="Modular drive system for a wide range of applications",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.5,
            "max_ms": 40.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["profinet", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="G120-{8HEX}",
            station_name_pattern="vfd-{model_short}-{seq}",
            vendor_short="SIE",
            model_short="G120",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.8 SP7",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.7 SP11",
                release_date=date(2022, 9, 20),
                cves=["CVE-2022-45092"],
            ),
            FirmwareVariant(
                version="V4.7 SP5",
                release_date=date(2021, 4, 15),
                cves=["CVE-2022-45092", "CVE-2021-31337"],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0120,
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "SINAMICS G120",
        },

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "SINAMICS G120",
            "product_name": "SINAMICS G120 Drive",
        },

        snmp_identity={
            "sys_descr": "Siemens SINAMICS G120 Drive V4.8 SP7",
            "sys_object_id": "1.3.6.1.4.1.4329.325.24",
            "sys_name": "SINAMI-G120-001",
            "sys_location": "Motor Control Center",
        },
    ),
    DeviceTemplate(
        id="siemens/hmi/tp1500-comfort",
        vendor="Siemens",
        vendor_family="SIMATIC HMI",
        model="6AV2 124-0QC02-0AX1",
        model_name="TP1500 Comfort Panel",
        device_type="hmi",
        description="15-inch Comfort Panel with widescreen display",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 120.0,
            "mean_ms": 30.0,
            "std_dev_ms": 20.0,
            "distribution": "lognormal",
        },

        supported_protocols=["profinet", "s7comm", "opc_ua"],

        instance_rules=InstanceGenerationRules(
            serial_format="S V-{8HEX}",
            station_name_pattern="hmi-{location}-{seq}",
            vendor_short="SIE",
            model_short="TP15",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V19.0.0.0",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V18.0.0.0",
                release_date=date(2022, 10, 20),
                cves=["CVE-2022-40227"],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x040F,
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6AV2 124-0QC02-0AX1",
        },

        s7_identity={
            "module_type": "SIMATIC HMI TP1500 Comfort Panel",
            "order_code": "6AV2 124-0QC02-0AX1",
            "copyright": "Original Siemens Equipment",
            "module_name": "HMI_1",
        },

        opc_ua_identity={
            "application_name": "Siemens SIMATIC HMI Comfort OPC UA Client",
            "application_uri": "urn:Siemens:SIMATIC:HMI:Comfort:TP1500",
            "product_uri": "http://www.siemens.com/simatic-hmi-comfort",
            "manufacturer_name": "Siemens AG",
            "product_name": "SIMATIC HMI TP1500 Comfort Panel",
            "software_version": "19.0.0",
            "build_number": "V19.0.0.0",
        },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC HMI TP1500 Comfort Panel V19.0.0.0",
            "sys_object_id": "1.3.6.1.4.1.4329.879.27",
            "sys_name": "TP1500-COMFOR-001",
            "sys_location": "Control Room",
        },
    ),
    DeviceTemplate(
        id="siemens/desigo/cc",
        vendor="Siemens",
        vendor_family="Desigo",
        model="Desigo CC",
        model_name="Desigo CC Management Platform",
        device_type="bms_server",
        description="Integrated building management platform",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 128,  # Windows based
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 40.0,
            "mean_ms": 10.0,
            "std_dev_ms": 6.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="DCC{10NUM}",
            station_name_pattern="bas-{location}-{seq}",
            vendor_short="SIE",
            model_short="DCC",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V6.0",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.0 SP1",
                release_date=date(2022, 8, 15),
                cves=["CVE-2022-39158"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 10,  # Siemens Building Technologies
            "device_type": "Management Platform",
            "model_name": "Desigo CC",
        },

        snmp_identity={
            "sys_descr": "Siemens Desigo CC Management Platform V6.0",
            "sys_object_id": "1.3.6.1.4.1.4329.424.24",
            "sys_name": "DESIGO-CC-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="siemens/desigo/dxr2",
        vendor="Siemens",
        vendor_family="Desigo",
        model="DXR2.E12",
        model_name="Desigo DXR2 Room Controller",
        device_type="room_controller",
        description="Compact room automation controller for HVAC",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="DXR{10NUM}",
            station_name_pattern="room-{location}-{seq}",
            vendor_short="SIE",
            model_short="DXR2",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.3",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.0",
                release_date=date(2022, 6, 20),
                cves=["CVE-2022-39158"],
            ),
            FirmwareVariant(
                version="V3.5",
                release_date=date(2020, 10, 10),
                cves=["CVE-2022-39158", "CVE-2020-15796"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 10,
            "device_type": "Room Controller",
            "model_name": "DXR2.E12",
        },

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "DXR2.E12",
            "product_name": "Desigo DXR2 Room Controller",
        },

        snmp_identity={
            "sys_descr": "Siemens Desigo DXR2 Room Controller V4.3",
            "sys_object_id": "1.3.6.1.4.1.4329.241.20",
            "sys_name": "DESIGO-DXR2-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="siemens-its/m60/atc",
        vendor="Siemens ITS",
        vendor_family="M-Series",
        model="M60",
        model_name="M60 ATC Traffic Controller",
        device_type="traffic_controller",
        description="Advanced Transportation Controller with NTCIP support",

        oui_prefixes=["00:0E:8C", "00:30:5C"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 40.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "lognormal",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="M60{10NUM}",
            station_name_pattern="tsc-{location}-{seq}",
            vendor_short="SIE",
            model_short="M60",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V10.3.0",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V10.1.0",
                release_date=date(2022, 6, 15),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Siemens M60 ATC Traffic Signal Controller V10.3.0",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",
        },
    ),
    DeviceTemplate(
        id="siemens-its/cp-8000/central",
        vendor="Siemens ITS",
        vendor_family="CP-8000",
        model="CP-8000",
        model_name="CP-8000 Central Controller",
        device_type="traffic_controller",
        description="Central traffic management controller for arterial coordination",

        oui_prefixes=["00:0E:8C", "00:30:5C", "00:1B:1B"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 30.0,
            "mean_ms": 6.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
        },

        supported_protocols=["snmp", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="CP8K{10NUM}",
            station_name_pattern="central-{location}-{seq}",
            vendor_short="SIE",
            model_short="CP8K",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V12.5.0",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V12.2.0",
                release_date=date(2022, 7, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="V11.0.0",
                release_date=date(2020, 11, 10),
                cves=["CVE-2020-10055"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Siemens CP-8000 Central Traffic Controller V12.5.0",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.5",
        },

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "CP-8000",
            "product_name": "CP-8000 Central Controller",
        },
    ),
    DeviceTemplate(
        id="siemens/tia/portal",
        vendor="Siemens",
        vendor_family="SIMATIC",
        model="TIA Portal",
        model_name="TIA Portal Engineering Station",
        device_type="engineering_station",
        description="Engineering and programming station for Siemens PLCs",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 10.0,
            "max_ms": 200.0,
            "mean_ms": 50.0,
            "std_dev_ms": 30.0,
            "distribution": "lognormal",
        },

        supported_protocols=["s7comm", "profinet"],

        s7_identity={
            "order_code": "6ES7822-1AA08-0YA5",
            "module_type": "STEP 7 Professional",
            "firmware_version": "V18.0",
            "hardware_version": "N/A",
        },

        profinet_identity={
            "vendor_id": 0x002A,
            "device_id": 0x0800,
            "device_type": "Engineering Station",
            "station_name": "eng-tia",
            "device_role": 0,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "TIA Portal V18",
            "im0_hw_revision": 1,
            "im0_sw_revision": "V18.0",
        },

        instance_rules=InstanceGenerationRules(
            serial_format="TIA-{6HEX}",
            station_name_pattern="eng-tia-{seq}",
            vendor_short="SIE",
            model_short="TIA",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V18.0",
                release_date=date(2023, 10, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Siemens SIMATIC TIA Portal Engineering Station V18.0",
            "sys_object_id": "1.3.6.1.4.1.4329.180.43",
            "sys_name": "TIA-PORTAL-001",
            "sys_location": "Engineering Office",
        },
    ),
    DeviceTemplate(
        id="siemens/wincc/unified",
        vendor="Siemens",
        vendor_family="WinCC",
        model="WinCC Unified",
        model_name="WinCC Unified Comfort Panel",
        device_type="hmi",
        description="New generation HMI with OPC UA support",

        oui_prefixes=["00:0E:8C", "00:1B:1B"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["s7comm", "opc_ua"],

        s7_identity={
            "order_code": "6AV2128-3GB06-0AX1",
            "module_type": "WinCC Unified Comfort Panel",
            "firmware_version": "V18.0",
            "hardware_version": "V1",
        },

        opc_ua_identity={
            "application_name": "Siemens SIMATIC WinCC Unified",
            "application_uri": "urn:Siemens:SIMATIC:WinCC:Unified",
            "product_uri": "http://www.siemens.com/simatic-wincc-unified",
            "manufacturer_name": "Siemens AG",
            "product_name": "SIMATIC WinCC Unified",
            "software_version": "18.0.0",
            "build_number": "V18.0",
            "build_date": "2023-06-01T12:00:00Z",
        },

        instance_rules=InstanceGenerationRules(
            serial_format="WU-{6HEX}",
            station_name_pattern="hmi-wu-{seq}",
            vendor_short="SIE",
            model_short="WCCU",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V18.0",
                release_date=date(2023, 10, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Siemens SIMATIC HMI WinCC Unified Comfort Panel V18.0",
            "sys_object_id": "1.3.6.1.4.1.4329.954.5",
            "sys_name": "WINCC-UNIFIE-001",
            "sys_location": "Control Room",
        },
    ),
    DeviceTemplate(
        id="siemens/et-200mp/6es7-155-5aa01-0ab0",
        vendor="Siemens",
        vendor_family="ET 200MP",
        model="6ES7 155-5AA01-0AB0",
        model_name="6ES7 155-5AA01-0AB0",
        device_type="io_module",
        description="Siemens 6ES7 155-5AA01-0AB0",
        oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
        tcp_stack={
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
        response_timing={
                "min_ms": 0.5,
                "max_ms": 10.0,
                "mean_ms": 2.5,
                "std_dev_ms": 1.5,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 4.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        supported_protocols=['profinet'],
        firmware_variants=[FirmwareVariant(
            version="V4.1.3",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        profinet_identity={
                "vendor_id": 42,
                "device_id": 1538,
                "device_type": "ET 200MP IM155-5 PN",
                "station_name": "et200mp-im155",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 155-5AA01-0AB0",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V4.1.3",
            },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC 6ES7 155-5AA01-0AB0 V4.1.3",
            "sys_object_id": "1.3.6.1.4.1.4329.311.38",
            "sys_name": "6ES7-155-5A-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="siemens/et-200sp/6es7-155-6au01-0bn0",
        vendor="Siemens",
        vendor_family="ET 200SP",
        model="6ES7 155-6AU01-0BN0",
        model_name="6ES7 155-6AU01-0BN0",
        device_type="io_module",
        description="Siemens 6ES7 155-6AU01-0BN0",
        oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 0.3,
                "max_ms": 8.0,
                "mean_ms": 2.0,
                "std_dev_ms": 1.2,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 4.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        supported_protocols=['profinet'],
        protocol_quirks={
                "profinet_cycle_time_us": 250,
            },
        firmware_variants=[FirmwareVariant(
            version="V4.2.5",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        profinet_identity={
                "vendor_id": 42,
                "device_id": 1537,
                "device_type": "ET 200SP IM155-6 PN",
                "station_name": "et200sp-im155",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 155-6AU01-0BN0",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V4.2.5",
            },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC 6ES7 155-6AU01-0BN0 V4.2.5",
            "sys_object_id": "1.3.6.1.4.1.4329.568.54",
            "sys_name": "6ES7-155-6A-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-1200f/6es7-214-1hf40-0xb0",
        vendor="Siemens",
        vendor_family="S7-1200F",
        model="6ES7 214-1HF40-0XB0",
        model_name="6ES7 214-1HF40-0XB0",
        device_type="plc",
        description="Siemens 6ES7 214-1HF40-0XB0",
        oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
        tcp_stack={
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "window_scaling": 5,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
        response_timing={
                "min_ms": 1.0,
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
                "outlier_multiplier": 4.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        supported_protocols=['modbus_tcp', 'profinet', 's7comm', 'opc_ua'],
        protocol_quirks={
                "profisafe_enabled": True,
            },
        firmware_variants=[FirmwareVariant(
            version="V4.5.2",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 214-1HF40-0XB0",
                "major_minor_revision": "V4.5.2",
                "product_name": "CPU 1214FC DC/DC/DC",
                "model_name": "S7-1200F",
            },
        profinet_identity={
                "vendor_id": 42,
                "device_id": 271,
                "device_type": "CPU 1214FC DC/DC/DC",
                "station_name": "plc-s71200f",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 214-1HF40-0XB0",
                "im0_hw_revision": 4,
                "im0_sw_revision": "V4.5.2",
            },
        s7_identity={
                "order_code": "6ES7 214-1HF40-0XB0",
                "module_type": "CPU 1214FC DC/DC/DC",
                "firmware_version": "V4.5.2",
                "hardware_version": "4",
            },

        opc_ua_identity={
                "application_name": "Siemens SIMATIC CPU 1214FC OPC UA Server",
                "application_uri": "urn:Siemens:SIMATIC:S7-1200F:CPU1214FC",
                "product_uri": "http://www.siemens.com/simatic-s7-1200f",
                "manufacturer_name": "Siemens AG",
                "product_name": "SIMATIC S7-1200F OPC UA Server",
                "software_version": "4.5.2",
                "build_number": "V4.5.2",
            },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC 6ES7 214-1HF40-0XB0 V4.5.2",
            "sys_object_id": "1.3.6.1.4.1.4329.759.44",
            "sys_name": "6ES7-214-1H-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-300/6es7-315-2eh14-0ab0",
        vendor="Siemens",
        vendor_family="S7-300",
        model="6ES7 315-2EH14-0AB0",
        model_name="6ES7 315-2EH14-0AB0",
        device_type="plc",
        description="Siemens 6ES7 315-2EH14-0AB0",
        oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.008,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0008,
                "timeout_probability": 0.0004,
            },
        supported_protocols=['modbus_tcp', 'profinet', 's7comm'],
        protocol_quirks={
                "s7_max_pdu_size": 240,
            },
        firmware_variants=[FirmwareVariant(
            version="V3.2.17",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 315-2EH14-0AB0",
                "major_minor_revision": "V3.2.17",
                "product_name": "CPU 315-2 PN/DP",
                "model_name": "S7-300",
            },
        profinet_identity={
                "vendor_id": 42,
                "device_id": 514,
                "device_type": "CPU 315-2 PN/DP",
                "station_name": "plc-s7300",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 315-2EH14-0AB0",
                "im0_hw_revision": 14,
                "im0_sw_revision": "V3.2.17",
            },
        s7_identity={
                "order_code": "6ES7 315-2EH14-0AB0",
                "module_type": "CPU 315-2 PN/DP",
                "firmware_version": "V3.2.17",
                "hardware_version": "14",
            },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC 6ES7 315-2EH14-0AB0 V3.2.17",
            "sys_object_id": "1.3.6.1.4.1.4329.614.56",
            "sys_name": "6ES7-315-2E-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-400/6es7-416-3es07-0ab0",
        vendor="Siemens",
        vendor_family="S7-400",
        model="6ES7 416-3ES07-0AB0",
        model_name="6ES7 416-3ES07-0AB0",
        device_type="plc",
        description="Siemens 6ES7 416-3ES07-0AB0",
        oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
        tcp_stack={
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": True,
            },
        response_timing={
                "min_ms": 0.5,
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0003,
                "timeout_probability": 0.00015,
            },
        supported_protocols=['modbus_tcp', 'profinet', 's7comm'],
        protocol_quirks={
                "s7_max_pdu_size": 960,
            },
        firmware_variants=[FirmwareVariant(
            version="V6.0.9",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 416-3ES07-0AB0",
                "major_minor_revision": "V6.0.9",
                "product_name": "CPU 416-3 PN/DP",
                "model_name": "S7-400",
            },
        profinet_identity={
                "vendor_id": 42,
                "device_id": 515,
                "device_type": "CPU 416-3 PN/DP",
                "station_name": "plc-s7400",
                "device_role": 2,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 416-3ES07-0AB0",
                "im0_hw_revision": 7,
                "im0_sw_revision": "V6.0.9",
            },
        s7_identity={
                "order_code": "6ES7 416-3ES07-0AB0",
                "module_type": "CPU 416-3 PN/DP",
                "firmware_version": "V6.0.9",
                "hardware_version": "7",
            },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC 6ES7 416-3ES07-0AB0 V6.0.9",
            "sys_object_id": "1.3.6.1.4.1.4329.226.6",
            "sys_name": "6ES7-416-3E-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="siemens/s7-1500f/6es7-516-3fn02-0ab0",
        vendor="Siemens",
        vendor_family="S7-1500F",
        model="6ES7 516-3FN02-0AB0",
        model_name="6ES7 516-3FN02-0AB0",
        device_type="plc",
        description="Siemens 6ES7 516-3FN02-0AB0",
        oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
        tcp_stack={
                "ttl": 64,
                "window_size": 29200,
                "mss": 1460,
                "window_scaling": 7,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 0.25,
                "max_ms": 8.0,
                "mean_ms": 1.8,
                "std_dev_ms": 1.2,
                "distribution": "gaussian",
                "outlier_probability": 0.001,
                "outlier_multiplier": 4.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4, 5, 6],
                "exception_probability": 0.0002,
                "timeout_probability": 5e-05,
            },
        supported_protocols=['modbus_tcp', 'profinet', 's7comm', 'opc_ua'],
        protocol_quirks={
                "profinet_cycle_time_us": 500,
                "s7_max_pdu_size": 960,
                "profisafe_enabled": True,
                "f_host_mode": "standard",
            },
        firmware_variants=[FirmwareVariant(
            version="V3.0.3",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 516-3FN02-0AB0",
                "major_minor_revision": "V3.0.3",
                "vendor_url": "http://www.siemens.com",
                "product_name": "CPU 1516F-3 PN/DP",
                "model_name": "S7-1500F",
            },
        profinet_identity={
                "vendor_id": 42,
                "device_id": 783,
                "device_type": "CPU 1516F-3 PN/DP",
                "station_name": "plc-s71500f",
                "device_role": 2,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6ES7 516-3FN02-0AB0",
                "im0_hw_revision": 2,
                "im0_sw_revision": "V3.0.3",
            },
        s7_identity={
                "order_code": "6ES7 516-3FN02-0AB0",
                "module_type": "CPU 1516F-3 PN/DP",
                "firmware_version": "V3.0.3",
                "hardware_version": "2",
            },

        opc_ua_identity={
                "application_name": "Siemens SIMATIC CPU 1516F-3 OPC UA Server",
                "application_uri": "urn:Siemens:SIMATIC:S7-1500F:CPU1516F-3",
                "product_uri": "http://www.siemens.com/simatic-s7-1500f",
                "manufacturer_name": "Siemens AG",
                "product_name": "SIMATIC S7-1500F OPC UA Server",
                "software_version": "3.0.3",
                "build_number": "V3.0.3",
            },

        snmp_identity={
            "sys_descr": "Siemens SIMATIC 6ES7 516-3FN02-0AB0 V3.0.3",
            "sys_object_id": "1.3.6.1.4.1.4329.156.12",
            "sys_name": "6ES7-516-3F-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="siemens/sinamics/6sl3130-7te25-5aa3",
        vendor="Siemens",
        vendor_family="SINAMICS",
        model="6SL3130-7TE25-5AA3",
        model_name="6SL3130-7TE25-5AA3",
        device_type="drive",
        description="Siemens 6SL3130-7TE25-5AA3",
        oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
        tcp_stack={
                "ttl": 64,
                "window_size": 16384,
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
                "outlier_probability": 0.002,
                "outlier_multiplier": 4.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0002,
                "timeout_probability": 0.0001,
            },
        supported_protocols=['modbus_tcp', 'profinet'],
        firmware_variants=[FirmwareVariant(
            version="V5.2",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Siemens AG",
                "product_code": "6SL3130-7TE25-5AA3",
                "major_minor_revision": "V5.2",
                "product_name": "SINAMICS S120",
                "model_name": "Servo Drive",
            },
        profinet_identity={
                "vendor_id": 42,
                "device_id": 1281,
                "device_type": "SINAMICS S120",
                "station_name": "drive-s120",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6SL3130-7TE25-5AA3",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V5.2",
            },

        snmp_identity={
            "sys_descr": "Siemens SINAMICS 6SL3130-7TE25-5AA3 V5.2",
            "sys_object_id": "1.3.6.1.4.1.4329.739.25",
            "sys_name": "6SL3130-7TE2-001",
            "sys_location": "Motor Control Center",
        },
    ),
    DeviceTemplate(
        id="siemens/sinamics/6sl3210-1ke21-7uf1",
        vendor="Siemens",
        vendor_family="SINAMICS",
        model="6SL3210-1KE21-7UF1",
        model_name="6SL3210-1KE21-7UF1",
        device_type="drive",
        description="Siemens 6SL3210-1KE21-7UF1",
        oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 40.0,
                "mean_ms": 10.0,
                "std_dev_ms": 6.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.5,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0005,
                "timeout_probability": 0.0003,
            },
        supported_protocols=['modbus_tcp', 'profinet'],
        firmware_variants=[FirmwareVariant(
            version="V4.8",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Siemens AG",
                "product_code": "6SL3210-1KE21-7UF1",
                "major_minor_revision": "V4.8",
                "product_name": "SINAMICS G120C",
                "model_name": "Variable Speed Drive",
            },
        profinet_identity={
                "vendor_id": 42,
                "device_id": 1280,
                "device_type": "SINAMICS G120C",
                "station_name": "drive-g120c",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6SL3210-1KE21-7UF1",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V4.8",
            },

        snmp_identity={
            "sys_descr": "Siemens SINAMICS 6SL3210-1KE21-7UF1 V4.8",
            "sys_object_id": "1.3.6.1.4.1.4329.320.41",
            "sys_name": "6SL3210-1KE2-001",
            "sys_location": "Motor Control Center",
        },
    ),
    DeviceTemplate(
        id="siemens/sinamics/6sl3544-0fb21-1fa0",
        vendor="Siemens",
        vendor_family="SINAMICS",
        model="6SL3544-0FB21-1FA0",
        model_name="6SL3544-0FB21-1FA0",
        device_type="drive",
        description="Siemens 6SL3544-0FB21-1FA0",
        oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 3.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.006,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0006,
                "timeout_probability": 0.0003,
            },
        supported_protocols=['profinet'],
        firmware_variants=[FirmwareVariant(
            version="V1.2",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        profinet_identity={
                "vendor_id": 42,
                "device_id": 1282,
                "device_type": "SINAMICS G115D",
                "station_name": "drive-g115d",
                "device_role": 1,
                "im0_manufacturer": "Siemens AG",
                "im0_order_id": "6SL3544-0FB21-1FA0",
                "im0_hw_revision": 1,
                "im0_sw_revision": "V1.2",
            },

        snmp_identity={
            "sys_descr": "Siemens SINAMICS 6SL3544-0FB21-1FA0 V1.2",
            "sys_object_id": "1.3.6.1.4.1.4329.407.31",
            "sys_name": "6SL3544-0FB2-001",
            "sys_location": "Motor Control Center",
        },
    ),
    DeviceTemplate(
        id="siemens/traffic-management/cp-8000",
        vendor="Siemens",
        vendor_family="Traffic Management",
        model="CP-8000",
        model_name="CP-8000",
        device_type="traffic_controller",
        description="Siemens CP-8000",
        oui_prefixes=['00:1F:F8', '00:0E:8C', '64:00:6A'],
        tcp_stack={
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.005,
                "outlier_multiplier": 4.0,
            },
        error_behavior={
                "timeout_probability": 0.0003,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['snmp'],
        firmware_variants=[FirmwareVariant(
            version="V5.30",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        snmp_identity={
                "sys_descr": "Siemens SICAM CP-8000 Master Station V5.30",
                "sys_object_id": "1.3.6.1.4.1.4329.6.1.2",
                "sys_name": "CP8000-TMC-001",
                "sys_location": "Traffic Management Center",
                "ntcip_device_type": "master",
            },
    ),
    DeviceTemplate(
        id="siemens/tunnel-system/tcs-light",
        vendor="Siemens",
        vendor_family="Tunnel System",
        model="TCS-LIGHT",
        model_name="TCS-LIGHT",
        device_type="tunnel_controller",
        description="Siemens TCS-LIGHT",
        oui_prefixes=['00:1F:F8', '00:0E:8C', '64:00:6A'],
        tcp_stack={
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 25.0,
                "mean_ms": 8.0,
                "std_dev_ms": 4.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['snmp'],
        firmware_variants=[FirmwareVariant(
            version="V2.0.5",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        snmp_identity={
                "sys_descr": "Siemens TCS Tunnel Lighting Controller V2.0.5",
                "sys_object_id": "1.3.6.1.4.1.4329.6.2.2",
                "sys_name": "LIGHT-001",
                "sys_location": "Tunnel Zone 1",
                "ntcip_device_type": "tunnel",
            },
    ),
    DeviceTemplate(
        id="siemens/tunnel-system/tcs-vent",
        vendor="Siemens",
        vendor_family="Tunnel System",
        model="TCS-VENT",
        model_name="TCS-VENT",
        device_type="tunnel_controller",
        description="Siemens TCS-VENT",
        oui_prefixes=['00:1F:F8', '00:0E:8C', '64:00:6A'],
        tcp_stack={
                "ttl": 128,
                "window_size": 65535,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 3.0,
                "max_ms": 30.0,
                "mean_ms": 10.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['snmp'],
        firmware_variants=[FirmwareVariant(
            version="V2.1.0",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        snmp_identity={
                "sys_descr": "Siemens TCS Tunnel Ventilation Controller V2.1.0",
                "sys_object_id": "1.3.6.1.4.1.4329.6.2.1",
                "sys_name": "VENT-001",
                "sys_location": "Tunnel Section A",
                "ntcip_device_type": "tunnel",
            },
    ),
    DeviceTemplate(
        id="siemens/scalance/xm-400",
        vendor="Siemens",
        vendor_family="SCALANCE",
        model="XM-400",
        model_name="XM-400",
        device_type="traffic_controller",
        description="Siemens XM-400",
        oui_prefixes=['00:1F:F8', '00:0E:8C', '64:00:6A'],
        tcp_stack={
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 0.5,
                "max_ms": 10.0,
                "mean_ms": 3.0,
                "std_dev_ms": 1.5,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
        error_behavior={
                "timeout_probability": 0.0002,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['snmp'],
        firmware_variants=[FirmwareVariant(
            version="V6.3.0",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        snmp_identity={
                "sys_descr": "Siemens SCALANCE XM-400 Industrial Ethernet Switch V6.3.0",
                "sys_object_id": "1.3.6.1.4.1.4329.3.2.1",
                "sys_name": "CORE-SW-001",
                "sys_location": "ITS Equipment Room",
                "sys_services": 78,
            },
    ),

    # ------------------------------------------------------------------
    # SIPROTEC 7UM85 — Generator protection relay (40/24/27/59/64G/87G).
    # Speaks IEC 61850 natively, S7comm for engineering via DIGSI 5.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="siemens/siprotec/7um85",
        vendor="Siemens",
        vendor_family="SIPROTEC 5",
        model="7UM85",
        model_name="SIPROTEC 7UM85 Generator Protection",
        device_type="protection_relay",
        description="Generator protection relay with comprehensive machine protection functions",

        oui_prefixes=["00:0E:8C", "00:1C:06", "74:DA:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 8.0,
            "mean_ms": 1.5,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["s7comm", "iec61850", "modbus_tcp", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="SIE7UM{8NUM}",
            station_name_pattern="relay-7um85-{seq}",
            vendor_short="SIE",
            model_short="7UM85",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V9.40",
                release_date=date(2024, 2, 28),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V9.20",
                release_date=date(2022, 8, 18),
                cves=[],
            ),
            FirmwareVariant(
                version="V8.40",
                release_date=date(2020, 11, 5),
                cves=["CVE-2023-30899"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "7UM85",
            "product_name": "SIPROTEC 7UM85 Generator Protection",
        },

        snmp_identity={
            "sys_descr": "Siemens SIPROTEC 7UM85 Generator Protection V9.40",
            "sys_object_id": "1.3.6.1.4.1.4329.585.41",
            "sys_name": "SIPROT-7UM85-001",
            "sys_location": "Power Plant",
        },

        s7_identity={
            "module_type_name": "SIPROTEC 7UM85",
            "module_name": "7UM85 Generator Protection",
            "plant_id": "GEN-PROT",
            "serial_number": "SIE7UM00000000",
            "firmware_version": "V9.40",
        },

        iec61850_identity={
            "ied_name": "SIE_7UM85_IED",
            "vendor": "Siemens",
            "software_version": "V9.40",
            "logical_devices": ["CTRL", "MEAS", "PROT"],
            "icd_filename": "SIE_7UM85.icd",
        },
    ),

    # ------------------------------------------------------------------
    # SIPROTEC 7SS85 — Busbar differential protection relay (87B distributed).
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="siemens/siprotec/7ss85",
        vendor="Siemens",
        vendor_family="SIPROTEC 5",
        model="7SS85",
        model_name="SIPROTEC 7SS85 Busbar Differential",
        device_type="protection_relay",
        description="Distributed busbar differential protection relay",

        oui_prefixes=["00:0E:8C", "00:1C:06", "74:DA:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 7.0,
            "mean_ms": 1.4,
            "std_dev_ms": 0.9,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["s7comm", "iec61850", "modbus_tcp", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="SIE7SS{8NUM}",
            station_name_pattern="relay-7ss85-{seq}",
            vendor_short="SIE",
            model_short="7SS85",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V9.40",
                release_date=date(2024, 3, 5),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V9.20",
                release_date=date(2022, 9, 2),
                cves=["CVE-2024-31486"],
            ),
            FirmwareVariant(
                version="V8.40",
                release_date=date(2020, 10, 18),
                cves=["CVE-2024-31486", "CVE-2015-5374"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "7SS85",
            "product_name": "SIPROTEC 7SS85 Busbar Differential",
        },

        snmp_identity={
            "sys_descr": "Siemens SIPROTEC 7SS85 Busbar Differential V9.40",
            "sys_object_id": "1.3.6.1.4.1.4329.585.42",
            "sys_name": "SIPROT-7SS85-001",
            "sys_location": "Substation",
        },

        s7_identity={
            "module_type_name": "SIPROTEC 7SS85",
            "module_name": "7SS85 Busbar Differential",
            "plant_id": "BUS-PROT",
            "serial_number": "SIE7SS00000000",
            "firmware_version": "V9.40",
        },

        iec61850_identity={
            "ied_name": "SIE_7SS85_IED",
            "vendor": "Siemens",
            "software_version": "V9.40",
            "logical_devices": ["CTRL", "MEAS", "PROT"],
            "icd_filename": "SIE_7SS85.icd",
        },
    ),

    # ------------------------------------------------------------------
    # SIPROTEC 7VK87 — Autoreclose / synchrocheck (79/25) line bay relay.
    # ------------------------------------------------------------------
    DeviceTemplate(
        id="siemens/siprotec/7vk87",
        vendor="Siemens",
        vendor_family="SIPROTEC 5",
        model="7VK87",
        model_name="SIPROTEC 7VK87 Autoreclose / Synchrocheck",
        device_type="protection_relay",
        description="Autoreclose and synchrocheck relay for line bay applications",

        oui_prefixes=["00:0E:8C", "00:1C:06", "74:DA:EA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 8.0,
            "mean_ms": 1.5,
            "std_dev_ms": 0.9,
            "distribution": "gaussian",
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },

        supported_protocols=["s7comm", "iec61850", "modbus_tcp", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="SIE7VK{8NUM}",
            station_name_pattern="relay-7vk87-{seq}",
            vendor_short="SIE",
            model_short="7VK87",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V9.40",
                release_date=date(2024, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V9.20",
                release_date=date(2022, 7, 28),
                cves=["CVE-2023-30899"],
            ),
            FirmwareVariant(
                version="V8.40",
                release_date=date(2020, 10, 22),
                cves=["CVE-2023-30899", "CVE-2015-5374"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "7VK87",
            "product_name": "SIPROTEC 7VK87 Autoreclose / Synchrocheck",
        },

        snmp_identity={
            "sys_descr": "Siemens SIPROTEC 7VK87 Autoreclose / Synchrocheck V9.40",
            "sys_object_id": "1.3.6.1.4.1.4329.585.43",
            "sys_name": "SIPROT-7VK87-001",
            "sys_location": "Substation",
        },

        s7_identity={
            "module_type_name": "SIPROTEC 7VK87",
            "module_name": "7VK87 Autoreclose / Synchrocheck",
            "plant_id": "BAY-AR",
            "serial_number": "SIE7VK00000000",
            "firmware_version": "V9.40",
        },

        iec61850_identity={
            "ied_name": "SIE_7VK87_IED",
            "vendor": "Siemens",
            "software_version": "V9.40",
            "logical_devices": ["CTRL", "MEAS", "PROT"],
            "icd_filename": "SIE_7VK87.icd",
        },
    ),
]
