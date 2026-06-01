# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Rockwell Automation device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="rockwell/controllogix/l83e",
        vendor="Rockwell",
        vendor_family="ControlLogix",
        model="1756-L83E",
        model_name="ControlLogix 5580",
        device_type="plc",
        description="High-performance ControlLogix controller for complex applications",

        oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16", "E4:90:69"],

        tcp_stack={
            "ttl": 128,  # Windows-based
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "nop_padding": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 3.5,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
            "outlier_probability": 0.005,
            "outlier_multiplier": 4.0,
        },

        error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 6],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0002,
            "retry_behavior": True,
            "max_retries": 3,
        },

        supported_protocols=["ethernet_ip", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{8HEX}",
            station_name_pattern="{model_short}_{role}_{seq}",
            vendor_short="ROC",
            model_short="L83E",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V34.011",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V33.013",
                release_date=date(2023, 8, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="V32.011",
                release_date=date(2022, 11, 20),
                cves=["CVE-2022-3157"],
                notes="Vulnerable to DoS via malformed CIP packets",
            ),
            FirmwareVariant(
                version="V31.011",
                release_date=date(2021, 9, 10),
                cves=["CVE-2022-3157", "CVE-2022-1161"],
                notes="Multiple CIP vulnerabilities",
            ),
            FirmwareVariant(
                version="V28.015",
                release_date=date(2019, 6, 5),
                cves=["CVE-2022-3157", "CVE-2022-1161", "CVE-2020-6998", "CVE-2019-10955"],
                notes="Legacy firmware with critical vulnerabilities",
            ),
        ],

        modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1756-L83E/B",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1756-L83E Logix5580 Controller",
            "model_name": "ControlLogix 5580",
        },

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,  # Programmable Logic Controller
            "product_code": 55,
            "product_name": "1756-L83E/B LOGIX5580",
            "state": 3,  # Operational
            # revision_major, revision_minor, serial_number merged from firmware/instance
        },

        protocol_quirks={
            "enip_encap_timeout_ms": 10000,
            "cip_connection_timeout_multiplier": 32,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation ControlLogix 5580 V34.011",
            "sys_object_id": "1.3.6.1.4.1.53148.583.86",
            "sys_name": "CONTRO-5580-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/compactlogix/l33er",
        vendor="Rockwell",
        vendor_family="CompactLogix",
        model="1769-L33ER",
        model_name="CompactLogix 5370",
        device_type="plc",
        description="Mid-range CompactLogix controller with embedded EtherNet/IP",

        oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16"],

        tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.8,
            "max_ms": 20.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{8HEX}",
            station_name_pattern="{model_short}_{role}_{seq}",
            vendor_short="ROC",
            model_short="L33ER",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V34.014",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V33.013",
                release_date=date(2023, 6, 10),
                cves=[],
            ),
            FirmwareVariant(
                version="V30.014",
                release_date=date(2021, 4, 15),
                cves=["CVE-2022-1161"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1769-L33ER",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1769-L33ER CompactLogix Controller",
            "model_name": "CompactLogix 5370",
        },

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 89,
            "product_name": "1769-L33ER COMPACTLOGIX",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation CompactLogix 5370 V34.014",
            "sys_object_id": "1.3.6.1.4.1.53148.591.21",
            "sys_name": "COMPAC-5370-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/panelview/plus7-15",
        vendor="Rockwell",
        vendor_family="PanelView",
        model="2711P-T15C22D9P",
        model_name="PanelView Plus 7 - 15 inch",
        device_type="hmi",
        description="15-inch graphic terminal with touchscreen",

        oui_prefixes=["00:00:BC", "00:1D:9C"],

        tcp_stack={
            "ttl": 64,  # VxWorks/Linux based
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "lognormal",
        },

        supported_protocols=["ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="{10ALPHANUM}",
            station_name_pattern="hmi-{location}-{seq2}",
            vendor_short="ROC",
            model_short="PV7",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V14.00",
                release_date=date(2024, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V12.00",
                release_date=date(2022, 5, 15),
                cves=["CVE-2022-2848"],
            ),
            FirmwareVariant(
                version="V10.00",
                release_date=date(2020, 8, 10),
                cves=["CVE-2022-2848", "CVE-2020-14480"],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 24,  # Human-Machine Interface
            "product_code": 773,
            "product_name": "2711P-T15C22D9P PANELVIEW PLUS 7",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation PanelView Plus 7 - 15 inch V14.00",
            "sys_object_id": "1.3.6.1.4.1.53148.192.56",
            "sys_name": "PANELV-PLUS-001",
            "sys_location": "Control Room",
        },
    ),
    DeviceTemplate(
        id="rockwell/controllogix/l85e",
        vendor="Rockwell",
        vendor_family="ControlLogix",
        model="1756-L85E",
        model_name="ControlLogix 5580",
        device_type="plc",
        description="High-end ControlLogix controller with 80MB memory",

        oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16", "E4:90:69"],

        tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.4,
            "max_ms": 12.0,
            "mean_ms": 2.8,
            "std_dev_ms": 1.8,
            "distribution": "gaussian",
        },

        # ControlLogix 5580 supports OPC UA Server via Logix Designer
        # Studio 5000 v32+ (built-in OPC UA Server profile).
        supported_protocols=["ethernet_ip", "modbus_tcp", "opc_ua", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{8HEX}",
            station_name_pattern="{model_short}_{role}_{seq}",
            vendor_short="ROC",
            model_short="L85E",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V35.011",
                release_date=date(2024, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V34.011",
                release_date=date(2023, 8, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="V33.013",
                release_date=date(2022, 11, 20),
                cves=["CVE-2022-3157"],
            ),
            FirmwareVariant(
                version="V32.011",
                release_date=date(2021, 9, 10),
                cves=["CVE-2022-3157", "CVE-2022-1161"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1756-L85E/B",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1756-L85E Logix5580 Controller",
            "model_name": "ControlLogix 5580",
        },

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 166,
            "product_name": "1756-L85E/B LOGIX5580",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1756-L85E/B ControlLogix 5580 V35.011",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10",
        },

        opc_ua_identity={
            "application_name": "Rockwell Automation Logix5580 OPC UA Server",
            "application_uri": "urn:RockwellAutomation:Logix5580:1756-L85E",
            "product_uri": "http://www.rockwellautomation.com/products/logix5580",
            "manufacturer_name": "Rockwell Automation",
            "product_name": "ControlLogix 5580 OPC UA Server",
            "software_version": "35.011",
            "build_number": "V35.011",
            "build_date": "2024-03-01T00:00:00Z",
        },
    ),
    DeviceTemplate(
        id="rockwell/guardlogix/l83es",
        vendor="Rockwell",
        vendor_family="GuardLogix",
        model="1756-L83ES",
        model_name="GuardLogix 5580 Safety",
        device_type="safety_plc",
        description="Safety controller with integrated SIL 3/PLe safety",

        oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16"],

        tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 10.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.2,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip", "cip_safety"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{8HEX}",
            station_name_pattern="safety_{model_short}_{seq}",
            vendor_short="ROC",
            model_short="L83ES",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V35.011",
                release_date=date(2024, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V34.011",
                release_date=date(2023, 8, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="V33.013",
                release_date=date(2022, 11, 20),
                cves=["CVE-2022-3157"],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 167,
            "product_name": "1756-L83ES/B GUARDLOGIX",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation GuardLogix 5580 Safety V35.011",
            "sys_object_id": "1.3.6.1.4.1.53148.956.43",
            "sys_name": "GUARDL-5580-001",
            "sys_location": "Safety Cabinet",
        },
    ),
    DeviceTemplate(
        id="rockwell/pointio/1734-aent",
        vendor="Rockwell",
        vendor_family="Point I/O",
        model="1734-AENT",
        model_name="Point I/O EtherNet/IP Adapter",
        device_type="remote_io",
        description="EtherNet/IP adapter for Point I/O modules",

        oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 12.0,
            "mean_ms": 2.5,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{8HEX}",
            station_name_pattern="io-point-{seq}",
            vendor_short="ROC",
            model_short="AENT",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V7.013",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V6.013",
                release_date=date(2022, 9, 10),
                cves=["CVE-2022-3156"],
            ),
            FirmwareVariant(
                version="V5.019",
                release_date=date(2020, 7, 20),
                cves=["CVE-2022-3156", "CVE-2020-6084"],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 12,  # Communications Adapter
            "product_code": 164,
            "product_name": "1734-AENT POINT I/O",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation Point I/O EtherNet/IP Adapter V7.013",
            "sys_object_id": "1.3.6.1.4.1.53148.291.16",
            "sys_name": "POINT-I-O-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="rockwell/flex5000/5094-aen2tr",
        vendor="Rockwell",
        vendor_family="FLEX 5000",
        model="5094-AEN2TR",
        model_name="FLEX 5000 EtherNet/IP Adapter",
        device_type="remote_io",
        description="Dual-port EtherNet/IP adapter for FLEX 5000 I/O",

        oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16", "E4:90:69"],

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

        supported_protocols=["ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{8HEX}",
            station_name_pattern="io-flex5k-{seq}",
            vendor_short="ROC",
            model_short="FLEX5",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.011",
                release_date=date(2024, 2, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.011",
                release_date=date(2022, 10, 15),
                cves=["CVE-2022-3156"],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 12,
            "product_code": 196,
            "product_name": "5094-AEN2TR FLEX 5000",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation FLEX 5000 EtherNet/IP Adapter V3.011",
            "sys_object_id": "1.3.6.1.4.1.53148.324.85",
            "sys_name": "FLEX-5000-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="rockwell/powerflex/753",
        vendor="Rockwell",
        vendor_family="PowerFlex",
        model="PowerFlex 753",
        model_name="PowerFlex 753 AC Drive",
        device_type="drive",
        description="High-performance AC drive for industrial applications",

        oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 30.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="PF753-{8HEX}",
            station_name_pattern="drive-pf753-{seq}",
            vendor_short="ROC",
            model_short="PF753",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V16.002",
                release_date=date(2022, 6, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V14.001",
                release_date=date(2021, 5, 15),
                cves=["CVE-2022-3158"],
            ),
            FirmwareVariant(
                version="V12.001",
                release_date=date(2019, 3, 10),
                cves=["CVE-2022-3158", "CVE-2021-22682"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "PowerFlex 753",
            "product_name": "PowerFlex 753 AC Drive",
        },

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 2,  # AC Drive
            "product_code": 753,
            "product_name": "PowerFlex 753 AC DRIVE",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation PowerFlex 753 AC Drive V20.007",
            "sys_object_id": "1.3.6.1.4.1.53148.386.2",
            "sys_name": "POWERF-753-001",
            "sys_location": "Motor Control Center",
        },
    ),
    DeviceTemplate(
        id="rockwell/panelview/800",
        vendor="Rockwell",
        vendor_family="PanelView",
        model="2711R-T7T",
        model_name="PanelView 800 - 7 inch",
        device_type="hmi",
        description="Compact 7-inch graphic terminal",

        oui_prefixes=["00:00:BC", "00:1D:9C"],

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
            "mean_ms": 18.0,
            "std_dev_ms": 10.0,
            "distribution": "lognormal",
        },

        supported_protocols=["ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="{10ALPHANUM}",
            station_name_pattern="hmi-pv800-{seq2}",
            vendor_short="ROC",
            model_short="PV800",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V10.00",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V8.00",
                release_date=date(2022, 6, 20),
                cves=["CVE-2022-2848"],
            ),
            FirmwareVariant(
                version="V6.00",
                release_date=date(2020, 9, 10),
                cves=["CVE-2022-2848", "CVE-2020-14480"],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 24,
            "product_code": 800,
            "product_name": "2711R-T7T PANELVIEW 800",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation PanelView 800 - 7 inch V10.00",
            "sys_object_id": "1.3.6.1.4.1.53148.3.2",
            "sys_name": "PANELV-800-001",
            "sys_location": "Control Room",
        },
    ),
    DeviceTemplate(
        id="rockwell/controllogix/l73",
        vendor="Rockwell",
        vendor_family="ControlLogix",
        model="1756-L73",
        model_name="ControlLogix 5570",
        device_type="plc",
        description="Mid-range ControlLogix controller for complex applications",

        oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16", "E4:90:69"],

        tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.8,
            "max_ms": 20.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },

        # ControlLogix 5570 supports OPC UA Server via Studio 5000 v32+.
        supported_protocols=["ethernet_ip", "modbus_tcp", "opc_ua", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{8HEX}",
            station_name_pattern="{model_short}_{role}_{seq}",
            vendor_short="ROC",
            model_short="L73",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V33.011",
                release_date=date(2023, 10, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V32.011",
                release_date=date(2022, 11, 20),
                cves=["CVE-2022-3157"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1756-L73",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1756-L73 ControlLogix Controller",
            "model_name": "ControlLogix 5570",
        },

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 73,
            "product_name": "1756-L73 LOGIX5570",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1756-L73 ControlLogix 5570 V33.011",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10",
        },

        opc_ua_identity={
            "application_name": "Rockwell Automation Logix5570 OPC UA Server",
            "application_uri": "urn:RockwellAutomation:Logix5570:1756-L73",
            "product_uri": "http://www.rockwellautomation.com/products/logix5570",
            "manufacturer_name": "Rockwell Automation",
            "product_name": "ControlLogix 5570 OPC UA Server",
            "software_version": "33.011",
            "build_number": "V33.011",
            "build_date": "2023-10-01T00:00:00Z",
        },
    ),
    DeviceTemplate(
        id="rockwell/compactlogix/l33erms",
        vendor="Rockwell",
        vendor_family="CompactLogix",
        model="1769-L33ERMS",
        model_name="CompactGuardLogix 5370",
        device_type="safety_plc",
        description="Safety-rated CompactLogix controller for SIL2/PLd applications",

        oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16"],

        tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 3.5,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip", "cip_safety", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{8HEX}",
            station_name_pattern="{model_short}_{role}_{seq}",
            vendor_short="ROC",
            model_short="L33ERMS",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V33.013",
                release_date=date(2023, 8, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1769-L33ERMS",
            "product_name": "1769-L33ERMS CompactGuardLogix Controller",
            "model_name": "CompactGuardLogix 5370",
        },

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 133,
            "product_name": "1769-L33ERMS COMPACTGUARDLOGIX",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation CompactGuardLogix 5370 V33.013",
            "sys_object_id": "1.3.6.1.4.1.53148.991.45",
            "sys_name": "COMPAC-5370-001",
            "sys_location": "Safety Cabinet",
        },
    ),
    DeviceTemplate(
        id="rockwell/panelview/plus7-10",
        vendor="Rockwell",
        vendor_family="PanelView",
        model="2711P-T10C22D9P",
        model_name="PanelView Plus 7 - 10 inch",
        device_type="hmi",
        description="10-inch color touchscreen operator interface",

        oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 80.0,
            "mean_ms": 20.0,
            "std_dev_ms": 12.0,
            "distribution": "lognormal",
        },

        supported_protocols=["ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="PV{8HEX}",
            station_name_pattern="hmi-pv7-{seq}",
            vendor_short="ROC",
            model_short="PV7-10",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V13.0",
                release_date=date(2023, 9, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 24,
            "product_code": 2711,
            "product_name": "2711P-T10C22D9P PANELVIEW PLUS 7",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation PanelView Plus 7 - 10 inch V13.0",
            "sys_object_id": "1.3.6.1.4.1.53148.330.51",
            "sys_name": "PANELV-PLUS-001",
            "sys_location": "Control Room",
        },
    ),
    DeviceTemplate(
        id="rockwell/panelview/800",
        vendor="Rockwell",
        vendor_family="PanelView",
        model="2711R-T7T",
        model_name="PanelView 800",
        device_type="hmi",
        description="7-inch color touchscreen HMI for Micro800 systems",

        oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="PV8{8HEX}",
            station_name_pattern="hmi-pv800-{seq}",
            vendor_short="ROC",
            model_short="PV800",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V8.0",
                release_date=date(2023, 6, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 24,
            "product_code": 800,
            "product_name": "2711R-T7T PANELVIEW 800",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation PanelView 800 V8.0",
            "sys_object_id": "1.3.6.1.4.1.53148.3.2",
            "sys_name": "PANELV-800-001",
            "sys_location": "Control Room",
        },
    ),
    DeviceTemplate(
        id="rockwell/drives/powerflex-525",
        vendor="Rockwell",
        vendor_family="PowerFlex",
        model="25B-D030N104",
        model_name="PowerFlex 525",
        device_type="drive",
        description="Compact AC drive for simple stand-alone applications",

        oui_prefixes=["00:00:BC", "00:1D:9C"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="PF5{8HEX}",
            station_name_pattern="drive-pf525-{seq}",
            vendor_short="ROC",
            model_short="PF525",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V6.003",
                release_date=date(2023, 4, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "25B-D030N104",
            "product_name": "PowerFlex 525 AC Drive",
            "model_name": "PowerFlex 525",
        },

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 2,
            "product_code": 525,
            "product_name": "25B-D030N104 POWERFLEX 525",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation PowerFlex 525 V6.003",
            "sys_object_id": "1.3.6.1.4.1.53148.927.37",
            "sys_name": "POWERF-525-001",
            "sys_location": "Motor Control Center",
        },
    ),
    DeviceTemplate(
        id="rockwell/drives/powerflex-753",
        vendor="Rockwell",
        vendor_family="PowerFlex",
        model="20F-D052N103",
        model_name="PowerFlex 753",
        device_type="drive",
        description="High-performance AC drive for demanding applications",

        oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
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

        supported_protocols=["ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="PF7{8HEX}",
            station_name_pattern="drive-pf753-{seq}",
            vendor_short="ROC",
            model_short="PF753",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V16.002",
                release_date=date(2022, 6, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 2,
            "product_code": 753,
            "product_name": "20F-D052N103 POWERFLEX 753",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation PowerFlex 753 V20.003",
            "sys_object_id": "1.3.6.1.4.1.53148.193.65",
            "sys_name": "POWERF-753-001",
            "sys_location": "Motor Control Center",
        },
    ),
    DeviceTemplate(
        id="rockwell/servo/kinetix-5500",
        vendor="Rockwell",
        vendor_family="Kinetix",
        model="2198-D012-ERS3",
        model_name="Kinetix 5500",
        device_type="servo",
        description="Integrated servo drive for motion control applications",

        oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95"],

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

        supported_protocols=["ethernet_ip", "cip_motion"],

        instance_rules=InstanceGenerationRules(
            serial_format="K55{8HEX}",
            station_name_pattern="servo-k5500-{seq}",
            vendor_short="ROC",
            model_short="K5500",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V12.001",
                release_date=date(2023, 5, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 3,
            "product_code": 5500,
            "product_name": "2198-D012-ERS3 KINETIX 5500",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation Kinetix 5500 V12.001",
            "sys_object_id": "1.3.6.1.4.1.53148.662.62",
            "sys_name": "KINETI-5500-001",
            "sys_location": "Machine",
        },
    ),
    DeviceTemplate(
        id="rockwell/io/flex5000-aen2tr",
        vendor="Rockwell",
        vendor_family="FLEX 5000",
        model="5094-AEN2TR",
        model_name="FLEX 5000 EtherNet/IP",
        device_type="io_module",
        description="Dual-port EtherNet/IP adapter for FLEX 5000 I/O",

        oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
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

        supported_protocols=["ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="FX5{8HEX}",
            station_name_pattern="rio-flex5000-{seq}",
            vendor_short="ROC",
            model_short="FX5000",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.011",
                release_date=date(2023, 8, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 7,
            "product_code": 5094,
            "product_name": "5094-AEN2TR FLEX 5000",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation FLEX 5000 EtherNet/IP V3.011",
            "sys_object_id": "1.3.6.1.4.1.53148.143.71",
            "sys_name": "FLEX-5000-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="rockwell/io/1734-aent",
        vendor="Rockwell",
        vendor_family="POINT I/O",
        model="1734-AENT",
        model_name="POINT I/O EtherNet/IP",
        device_type="io_module",
        description="EtherNet/IP adapter for POINT I/O distributed I/O",

        oui_prefixes=["00:00:BC", "00:1D:9C"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 10.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip"],

        instance_rules=InstanceGenerationRules(
            serial_format="PI{8HEX}",
            station_name_pattern="rio-point-{seq}",
            vendor_short="ROC",
            model_short="1734",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V7.003",
                release_date=date(2023, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 7,
            "product_code": 1734,
            "product_name": "1734-AENT POINT I/O",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation POINT I/O EtherNet/IP V7.003",
            "sys_object_id": "1.3.6.1.4.1.53148.544.31",
            "sys_name": "POINT-I-O-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="rockwell/controllogix/l85e",
        vendor="Rockwell",
        vendor_family="ControlLogix",
        model="1756-L85E",
        model_name="ControlLogix 5580",
        device_type="plc",
        description="High-performance ControlLogix controller with 80MB memory",

        oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16", "E4:90:69"],

        tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 12.0,
            "mean_ms": 2.5,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        # ControlLogix 5580 supports OPC UA Server via Studio 5000 v32+.
        supported_protocols=["ethernet_ip", "modbus_tcp", "opc_ua", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{8HEX}",
            station_name_pattern="{model_short}_{role}_{seq}",
            vendor_short="ROC",
            model_short="L85E",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V35.011",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V34.011",
                release_date=date(2023, 6, 1),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1756-L85E",
            "product_name": "1756-L85E LOGIX5585E",
            "model_name": "ControlLogix 5580",
        },

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 85,
            "product_name": "1756-L85E LOGIX5580",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1756-L85E ControlLogix 5580 V35.011",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10",
        },

        opc_ua_identity={
            "application_name": "Rockwell Automation Logix5580 OPC UA Server",
            "application_uri": "urn:RockwellAutomation:Logix5580:1756-L85E",
            "product_uri": "http://www.rockwellautomation.com/products/logix5580",
            "manufacturer_name": "Rockwell Automation",
            "product_name": "ControlLogix 5580 OPC UA Server",
            "software_version": "35.011",
            "build_number": "V35.011",
            "build_date": "2024-01-15T00:00:00Z",
        },
    ),
    DeviceTemplate(
        id="rockwell/guardlogix/l83es",
        vendor="Rockwell",
        vendor_family="GuardLogix",
        model="1756-L83ES",
        model_name="GuardLogix 5580S",
        device_type="safety_plc",
        description="Safety-rated ControlLogix controller for SIL3/PLe applications",

        oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16"],

        tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 0.3,
            "max_ms": 12.0,
            "mean_ms": 2.5,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip", "cip_safety"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{8HEX}",
            station_name_pattern="{model_short}_{role}_{seq}",
            vendor_short="ROC",
            model_short="L83ES",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V35.011",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 183,
            "product_name": "1756-L83ES/B GUARDLOGIX",
            "state": 3,
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation GuardLogix 5580S V35.011",
            "sys_object_id": "1.3.6.1.4.1.53148.956.43",
            "sys_name": "GUARDL-5580S-001",
            "sys_location": "Safety Cabinet",
        },
    ),
    DeviceTemplate(
        id="rockwell/micrologix/1766-l32bwa",
        vendor="Rockwell",
        vendor_family="MicroLogix",
        model="1766-L32BWA",
        model_name="MicroLogix 1400",
        device_type="plc",
        description="Legacy MicroLogix 1400 PLC with built-in Ethernet",

        oui_prefixes=["00:00:BC", "00:1D:9C"],

        tcp_stack={
            "ttl": 128,
            "window_size": 8192,
            "mss": 1460,
            "timestamps_enabled": False,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 10.0,
            "max_ms": 150.0,
            "mean_ms": 45.0,
            "std_dev_ms": 25.0,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{6HEX}",
            station_name_pattern="ml1400_{role}_{seq}",
            vendor_short="ROC",
            model_short="ML1400",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="21.003",
                release_date=date(2020, 8, 1),
                is_latest=True,
                is_default=True,
                cves=["CVE-2020-6088"],
                notes="Legacy product with limited updates",
            ),
            FirmwareVariant(
                version="16.002",
                release_date=date(2016, 3, 15),
                cves=["CVE-2020-6088", "CVE-2017-7924"],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 155,
            "product_name": "1766-L32BWA MICROLOGIX 1400",
            "state": 3,
        },

        modbus_identity={
            "vendor_name": "Rockwell Automation",
            "product_code": "1766-L32BWA",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "MicroLogix 1400",
            "model_name": "MicroLogix",
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation MicroLogix 1400 V21.003",
            "sys_object_id": "1.3.6.1.4.1.53148.369.86",
            "sys_name": "MICROL-1400-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/compactlogix/1769-l24er-qb1b",
        vendor="Rockwell",
        vendor_family="CompactLogix",
        model="1769-L24ER-QB1B",
        model_name="CompactLogix 5370 L24ER",
        device_type="plc",
        description="Compact controller for small to medium applications",

        oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95"],

        tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 25.0,
            "mean_ms": 6.0,
            "std_dev_ms": 3.5,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="0x{8HEX}",
            station_name_pattern="{model_short}_{role}_{seq}",
            vendor_short="ROC",
            model_short="L24ER",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V33.011",
                release_date=date(2023, 9, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V32.011",
                release_date=date(2022, 6, 15),
                cves=["CVE-2022-3166"],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 89,
            "product_name": "1769-L24ER-QB1B COMPACTLOGIX",
            "state": 3,
        },

        modbus_identity={
            "vendor_name": "Rockwell Automation",
            "product_code": "1769-L24ER-QB1B",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "CompactLogix 5370 L24ER",
            "model_name": "CompactLogix",
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation CompactLogix 5370 L24ER V33.011",
            "sys_object_id": "1.3.6.1.4.1.53148.99.69",
            "sys_name": "COMPAC-5370-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/powerflex/525",
        vendor="Rockwell",
        vendor_family="PowerFlex",
        model="25B-D030N104",
        model_name="PowerFlex 525 AC Drive",
        device_type="drive",
        description="Compact AC drive with embedded Ethernet/IP",

        oui_prefixes=["00:00:BC", "00:1D:9C"],

        tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 35.0,
            "mean_ms": 7.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        # PowerFlex 525 supports both EtherNet/IP (native) and a Modbus
        # TCP option card (25-COMM-M). Declaring both lets cross-vendor
        # DCS scenarios (Emerson modbus, Yokogawa modbus) use this drive.
        supported_protocols=["ethernet_ip", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="PF525{8NUM}",
            station_name_pattern="vfd-pf525-{seq}",
            vendor_short="ROC",
            model_short="PF525",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V7.001",
                release_date=date(2024, 1, 25),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V6.003",
                release_date=date(2022, 7, 10),
                cves=["CVE-2022-3166"],
            ),
        ],

        ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 2,  # AC Drive
            "product_code": 525,
            "product_name": "25B-D030N104 POWERFLEX 525",
            "state": 3,
        },

        modbus_identity={
            "vendor_name": "Rockwell Automation",
            "product_code": "25B-D030N104",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "PowerFlex 525 AC Drive (25-COMM-M option)",
            "model_name": "PowerFlex 525",
        },

        snmp_identity={
            "sys_descr": "Rockwell Automation PowerFlex 525 AC Drive V7.001",
            "sys_object_id": "1.3.6.1.4.1.53148.112.96",
            "sys_name": "POWERF-525-001",
            "sys_location": "Motor Control Center",
        },
    ),
    DeviceTemplate(
        id="rockwell/controllogix/1756-en2t",
        vendor="Rockwell",
        vendor_family="ControlLogix",
        model="1756-EN2T",
        model_name="1756-EN2T",
        device_type="communication_module",
        description="Rockwell 1756-EN2T",
        oui_prefixes=['00:00:BC', '00:1D:9C'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 0.5,
                "max_ms": 8.0,
                "mean_ms": 2.0,
                "std_dev_ms": 1.0,
                "distribution": "gaussian",
            },
        supported_protocols=['ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="11.003",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 12,
                "product_code": 166,
                "revision_major": 11,
                "revision_minor": 3,
                "product_name": "1756-EN2T/D",
                "state": 3,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1756-EN2T V11.003",
            "sys_object_id": "1.3.6.1.4.1.53148.60.29",
            "sys_name": "1756-EN2T-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="rockwell/guardlogix/1756-l73s",
        vendor="Rockwell",
        vendor_family="GuardLogix",
        model="1756-L73S",
        model_name="1756-L73S",
        device_type="plc",
        description="Rockwell 1756-L73S",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 128,
                "window_size": 64240,
                "mss": 1460,
                "window_scaling": 8,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 0.5,
                "max_ms": 15.0,
                "mean_ms": 3.5,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
                "outlier_probability": 0.002,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0003,
                "timeout_probability": 0.0001,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        protocol_quirks={
                "enip_encap_timeout_ms": 10000,
                "cip_safety_enabled": True,
            },
        firmware_variants=[FirmwareVariant(
            version="32.012",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L73S/B",
                "major_minor_revision": "32.012",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L73S GuardLogix5573S Safety Controller",
                "model_name": "GuardLogix 5573S",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 167,
                "revision_major": 32,
                "revision_minor": 12,
                "serial_number": 1870302108,
                "product_name": "1756-L73S/B GUARDLOGIX5573S",
                "state": 3,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1756-L73S V32.012",
            "sys_object_id": "1.3.6.1.4.1.53148.409.23",
            "sys_name": "1756-L73S-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/controllogix/1756-l81e",
        vendor="Rockwell",
        vendor_family="ControlLogix",
        model="1756-L81E",
        model_name="1756-L81E",
        device_type="plc",
        description="Rockwell 1756-L81E",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 128,
                "window_size": 64240,
                "mss": 1460,
                "window_scaling": 8,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 0.6,
                "max_ms": 18.0,
                "mean_ms": 4.0,
                "std_dev_ms": 2.5,
                "distribution": "gaussian",
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0006,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="32.011",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L81E/B",
                "major_minor_revision": "32.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L81E Logix5581E Controller",
                "model_name": "ControlLogix 5581E",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 81,
                "revision_major": 32,
                "revision_minor": 11,
                "serial_number": 3285509622,
                "product_name": "1756-L81E/B LOGIX5581E",
                "state": 3,
                "status": 0,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1756-L81E V32.011",
            "sys_object_id": "1.3.6.1.4.1.53148.480.74",
            "sys_name": "1756-L81E-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/controllogix/1756-l82e",
        vendor="Rockwell",
        vendor_family="ControlLogix",
        model="1756-L82E",
        model_name="1756-L82E",
        device_type="plc",
        description="Rockwell 1756-L82E",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 128,
                "window_size": 64240,
                "mss": 1460,
                "window_scaling": 8,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 0.5,
                "max_ms": 15.0,
                "mean_ms": 3.2,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0005,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="32.011",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L82E/B",
                "major_minor_revision": "32.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L82E Logix5582E Controller",
                "model_name": "ControlLogix 5582E",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 82,
                "revision_major": 32,
                "revision_minor": 11,
                "serial_number": 3571840519,
                "product_name": "1756-L82E/B LOGIX5582E",
                "state": 3,
                "status": 0,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1756-L82E V32.011",
            "sys_object_id": "1.3.6.1.4.1.53148.368.68",
            "sys_name": "1756-L82E-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/controllogix/1756-l84e",
        vendor="Rockwell",
        vendor_family="ControlLogix",
        model="1756-L84E",
        model_name="1756-L84E",
        device_type="plc",
        description="Rockwell 1756-L84E",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 128,
                "window_size": 64240,
                "mss": 1460,
                "window_scaling": 8,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 0.35,
                "max_ms": 12.0,
                "mean_ms": 2.6,
                "std_dev_ms": 1.7,
                "distribution": "gaussian",
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4, 6],
                "exception_probability": 0.0004,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="32.011",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L84E/B",
                "major_minor_revision": "32.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1756-L84E Logix5584E Controller",
                "model_name": "ControlLogix 5584E",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 84,
                "revision_major": 32,
                "revision_minor": 11,
                "serial_number": 3858106136,
                "product_name": "1756-L84E/B LOGIX5584E",
                "state": 3,
                "status": 0,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1756-L84E V32.011",
            "sys_object_id": "1.3.6.1.4.1.53148.303.55",
            "sys_name": "1756-L84E-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/micrologix/1763-l16bwa",
        vendor="Rockwell",
        vendor_family="MicroLogix",
        model="1763-L16BWA",
        model_name="1763-L16BWA",
        device_type="plc",
        description="Rockwell 1763-L16BWA",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 3.0,
                "max_ms": 60.0,
                "mean_ms": 15.0,
                "std_dev_ms": 10.0,
                "distribution": "gaussian",
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.003,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="14.000",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1763-L16BWA",
                "major_minor_revision": "14.000",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1763-L16BWA MicroLogix 1100",
                "model_name": "MicroLogix 1100",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 22,
                "revision_major": 14,
                "revision_minor": 0,
                "serial_number": 2999178469,
                "product_name": "1763-L16BWA MICROLOGIX1100",
                "state": 3,
                "status": 0,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1763-L16BWA V14.000",
            "sys_object_id": "1.3.6.1.4.1.53148.908.83",
            "sys_name": "1763-L16BWA-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/micrologix/1766-l32awaa",
        vendor="Rockwell",
        vendor_family="MicroLogix",
        model="1766-L32AWAA",
        model_name="1766-L32AWAA",
        device_type="plc",
        description="Rockwell 1766-L32AWAA",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.002,
                "timeout_probability": 0.001,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="21.007",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1766-L32AWAA",
                "major_minor_revision": "21.007",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1766-L32AWAA MicroLogix 1400",
                "model_name": "MicroLogix 1400",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 25,
                "revision_major": 21,
                "revision_minor": 7,
                "serial_number": 3302352631,
                "product_name": "1766-L32AWAA MICROLOGIX1400",
                "state": 3,
                "status": 0,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1766-L32AWAA V21.007",
            "sys_object_id": "1.3.6.1.4.1.53148.11.75",
            "sys_name": "1766-L32AWAA-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/micrologix/1766-l32bwaa",
        vendor="Rockwell",
        vendor_family="MicroLogix",
        model="1766-L32BWAA",
        model_name="1766-L32BWAA",
        device_type="plc",
        description="Rockwell 1766-L32BWAA",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.002,
                "timeout_probability": 0.001,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="21.007",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1766-L32BWAA",
                "major_minor_revision": "21.007",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1766-L32BWAA MicroLogix 1400",
                "model_name": "MicroLogix 1400",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 25,
                "revision_major": 21,
                "revision_minor": 7,
                "serial_number": 2729690325,
                "product_name": "1766-L32BWAA MICROLOGIX1400",
                "state": 3,
                "status": 0,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1766-L32BWAA V21.007",
            "sys_object_id": "1.3.6.1.4.1.53148.486.11",
            "sys_name": "1766-L32BWAA-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/micrologix/1766-l32bxb",
        vendor="Rockwell",
        vendor_family="MicroLogix",
        model="1766-L32BXB",
        model_name="1766-L32BXB",
        device_type="plc",
        description="Rockwell 1766-L32BXB",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.002,
                "timeout_probability": 0.001,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="21.007",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1766-L32BXB",
                "major_minor_revision": "21.007",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1766-L32BXB MicroLogix 1400",
                "model_name": "MicroLogix 1400",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 25,
                "revision_major": 21,
                "revision_minor": 7,
                "serial_number": 3016021478,
                "product_name": "1766-L32BXB MICROLOGIX1400",
                "state": 3,
                "status": 0,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1766-L32BXB V21.007",
            "sys_object_id": "1.3.6.1.4.1.53148.818.76",
            "sys_name": "1766-L32BXB-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/micrologix/1766-l32bxba",
        vendor="Rockwell",
        vendor_family="MicroLogix",
        model="1766-L32BXBA",
        model_name="1766-L32BXBA",
        device_type="plc",
        description="Rockwell 1766-L32BXBA",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": False,
                "timestamps_enabled": False,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 50.0,
                "mean_ms": 12.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
                "outlier_probability": 0.01,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.002,
                "timeout_probability": 0.001,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="21.007",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1766-L32BXBA",
                "major_minor_revision": "21.007",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1766-L32BXBA MicroLogix 1400",
                "model_name": "MicroLogix 1400",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 25,
                "revision_major": 21,
                "revision_minor": 7,
                "serial_number": 3588683528,
                "product_name": "1766-L32BXBA MICROLOGIX1400",
                "state": 3,
                "status": 0,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1766-L32BXBA V21.007",
            "sys_object_id": "1.3.6.1.4.1.53148.774.34",
            "sys_name": "1766-L32BXBA-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/compactlogix/1769-l30erm",
        vendor="Rockwell",
        vendor_family="CompactLogix",
        model="1769-L30ERM",
        model_name="1769-L30ERM",
        device_type="plc",
        description="Rockwell 1769-L30ERM",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 128,
                "window_size": 64240,
                "mss": 1460,
                "window_scaling": 8,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 0.9,
                "max_ms": 22.0,
                "mean_ms": 5.5,
                "std_dev_ms": 3.5,
                "distribution": "gaussian",
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0009,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="33.011",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1769-L30ERM",
                "major_minor_revision": "33.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1769-L30ERM CompactLogix Controller",
                "model_name": "CompactLogix 5370",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 88,
                "revision_major": 33,
                "revision_minor": 11,
                "serial_number": 4127660073,
                "product_name": "1769-L30ERM/B LOGIX5370",
                "state": 3,
                "status": 0,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1769-L30ERM V33.011",
            "sys_object_id": "1.3.6.1.4.1.53148.670.54",
            "sys_name": "1769-L30ERM-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/compact-guardlogix/1769-l31es",
        vendor="Rockwell",
        vendor_family="Compact GuardLogix",
        model="1769-L31ES",
        model_name="1769-L31ES",
        device_type="plc",
        description="Rockwell 1769-L31ES",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 128,
                "window_size": 64240,
                "mss": 1460,
                "window_scaling": 8,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 0.8,
                "max_ms": 20.0,
                "mean_ms": 5.0,
                "std_dev_ms": 3.0,
                "distribution": "gaussian",
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0004,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        protocol_quirks={
                "cip_safety_enabled": True,
            },
        firmware_variants=[FirmwareVariant(
            version="33.011",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1769-L31ES",
                "major_minor_revision": "33.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1769-L31ES Compact GuardLogix Safety Controller",
                "model_name": "Compact GuardLogix 5370S",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 169,
                "revision_major": 33,
                "revision_minor": 11,
                "serial_number": 119023930,
                "product_name": "1769-L31ES COMPACTGUARDLOGIX",
                "state": 3,
                "status": 0,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1769-L31ES V33.011",
            "sys_object_id": "1.3.6.1.4.1.53148.912.53",
            "sys_name": "1769-L31ES-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/compact-guardlogix/1769-l32es",
        vendor="Rockwell",
        vendor_family="Compact GuardLogix",
        model="1769-L32ES",
        model_name="1769-L32ES",
        device_type="plc",
        description="Rockwell 1769-L32ES",
        oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
        tcp_stack={
                "ttl": 128,
                "window_size": 64240,
                "mss": 1460,
                "window_scaling": 8,
                "sack_permitted": True,
                "timestamps_enabled": True,
                "df_flag": True,
            },
        response_timing={
                "min_ms": 0.7,
                "max_ms": 18.0,
                "mean_ms": 4.5,
                "std_dev_ms": 2.8,
                "distribution": "gaussian",
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0004,
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        protocol_quirks={
                "cip_safety_enabled": True,
            },
        firmware_variants=[FirmwareVariant(
            version="33.011",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1769-L32ES",
                "major_minor_revision": "33.011",
                "vendor_url": "http://www.rockwellautomation.com",
                "product_name": "1769-L32ES Compact GuardLogix Safety Controller",
                "model_name": "Compact GuardLogix 5370S",
            },
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 170,
                "revision_major": 33,
                "revision_minor": 11,
                "serial_number": 405355083,
                "product_name": "1769-L32ES COMPACTGUARDLOGIX",
                "state": 3,
                "status": 0,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation 1769-L32ES V33.011",
            "sys_object_id": "1.3.6.1.4.1.53148.693.7",
            "sys_name": "1769-L32ES-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="rockwell/powerflex/powerflex-755",
        vendor="Rockwell",
        vendor_family="PowerFlex",
        model="PowerFlex 755",
        model_name="PowerFlex 755",
        device_type="drive",
        description="Rockwell PowerFlex 755",
        oui_prefixes=['00:00:BC', '00:1D:9C'],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 1.0,
                "max_ms": 15.0,
                "mean_ms": 4.0,
                "std_dev_ms": 2.0,
                "distribution": "gaussian",
            },
        supported_protocols=['ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="16.002",
            release_date=date(2022, 6, 1),
            is_default=True,
            is_latest=True,
        )],
        ethernet_ip_identity={
                "vendor_id": 1,
                "device_type": 2,
                "product_code": 56,
                "revision_major": 16,
                "revision_minor": 2,
                "product_name": "PowerFlex 755",
                "state": 3,
            },

        snmp_identity={
            "sys_descr": "Rockwell Automation PowerFlex 755 V16.002",
            "sys_object_id": "1.3.6.1.4.1.53148.556.48",
            "sys_name": "POWERF-755-001",
            "sys_location": "Motor Control Center",
        },
    ),
]
