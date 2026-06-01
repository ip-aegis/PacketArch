# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Fieldbus and networking device templates (Moxa, Hirschmann, Advantech, Kepware, Phoenix Contact, WAGO, Beckhoff, B&R)."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="beckhoff/cx/cx5130",
        vendor="Beckhoff",
        vendor_family="CX Series",
        model="CX5130",
        model_name="CX5130 Embedded PC",
        device_type="plc",
        description="Fanless Intel Atom-based embedded PC controller",

        oui_prefixes=["00:01:05"],

        tcp_stack={
            "ttl": 128,  # Windows CE/TwinCAT
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.2,
            "max_ms": 8.0,
            "mean_ms": 1.5,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },

        supported_protocols=["ethercat"],

        instance_rules=InstanceGenerationRules(
            serial_format="CX51-{8HEX}",
            station_name_pattern="{role}-cx5130-{seq}",
            vendor_short="BEC",
            model_short="CX51",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.1.4024.35",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
                notes="TwinCAT 3.1 Build 4024.35",
            ),
            FirmwareVariant(
                version="V3.1.4024.22",
                release_date=date(2022, 9, 10),
                cves=["CVE-2024-41173", "CVE-2024-41175"],
            ),
            FirmwareVariant(
                version="V3.1.4022.30",
                release_date=date(2021, 3, 20),
                cves=["CVE-2024-41173", "CVE-2024-41175"],
            ),
        ],

        snmp_identity={
            "sys_descr": "Beckhoff CX5130 Embedded PC V3.1.4024.35",
            "sys_object_id": "1.3.6.1.4.1.2510.953.39",
            "sys_name": "CX5130-EMBEDD-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="phoenix-contact/plcnext/axc-f-2152",
        vendor="Phoenix Contact",
        vendor_family="PLCnext",
        model="AXC F 2152",
        model_name="PLCnext Control AXC F 2152",
        device_type="plc",
        description="Linux-based open automation controller",

        oui_prefixes=["00:A0:45", "00:16:9D", "A8:74:1D"],

        tcp_stack={
            "ttl": 64,  # Linux
            "window_size": 29200,
            "mss": 1460,
            "window_scaling": 7,
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

        supported_protocols=["profinet"],

        instance_rules=InstanceGenerationRules(
            serial_format="AXC{10NUM}",
            station_name_pattern="{role}-plcnext-{seq}",
            vendor_short="PHX",
            model_short="AXC",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2024.0.0",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2022.0.5",
                release_date=date(2022, 11, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="V2021.0.3",
                release_date=date(2021, 6, 20),
                cves=["CVE-2019-10997", "CVE-2019-10998"],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x00B8,
            "device_id": 0x0152,
            "device_role": 2,
            "im0_manufacturer": "Phoenix Contact",
            "im0_order_id": "AXC F 2152",
        },

        snmp_identity={
            "sys_descr": "Phoenix Contact PLCnext Control AXC F 2152 V2024.0.0",
            "sys_object_id": "1.3.6.1.4.1.4346.700.42",
            "sys_name": "PLCNEX-CONTRO-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="wago/pfc200/750-8212",
        vendor="WAGO",
        vendor_family="PFC200",
        model="750-8212",
        model_name="PFC200 Controller",
        device_type="plc",
        description="Compact Linux-based controller with CODESYS runtime",

        oui_prefixes=["00:30:DE", "00:03:C6"],

        tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.8,
            "max_ms": 20.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "codesys"],

        instance_rules=InstanceGenerationRules(
            serial_format="750{10NUM}",
            station_name_pattern="{role}-pfc200-{seq}",
            vendor_short="WAG",
            model_short="PFC2",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="FW24",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="FW22",
                release_date=date(2022, 7, 10),
                cves=[],
            ),
            FirmwareVariant(
                version="FW18",
                release_date=date(2020, 4, 15),
                cves=["CVE-2021-34569"],
                notes="Multiple critical vulnerabilities",
            ),
        ],

        modbus_identity={
            "vendor_name": "WAGO Kontakttechnik GmbH",
            "product_code": "750-8212",
            "product_name": "PFC200 G2 2ETH RS",
            "model_name": "750-8212",
        },

        snmp_identity={
            "sys_descr": "WAGO PFC200 Controller VFW24",
            "sys_object_id": "1.3.6.1.4.1.13576.65.83",
            "sys_name": "PFC200-CONTRO-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="moxa/iologik/e1210",
        vendor="Moxa",
        vendor_family="ioLogik E1200",
        model="ioLogik E1210",
        model_name="ioLogik E1210 Remote I/O",
        device_type="remote_io",
        description="16-channel digital input remote I/O with Modbus/TCP",

        oui_prefixes=["00:90:E8"],

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
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="TAIB{8NUM}",
            station_name_pattern="rio-{location}-{seq}",
            vendor_short="MOX",
            model_short="E1210",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.3",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.1",
                release_date=date(2022, 5, 20),
                cves=["CVE-2016-8359", "CVE-2016-8372"],
            ),
            FirmwareVariant(
                version="V2.5",
                release_date=date(2020, 8, 10),
                cves=["CVE-2016-8359", "CVE-2016-8372"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Moxa Inc.",
            "product_code": "ioLogik E1210",
            "product_name": "ioLogik E1210 Remote I/O",
        },

        snmp_identity={
            "sys_descr": "Moxa ioLogik E1210 Remote I/O V3.3",
            "sys_object_id": "1.3.6.1.4.1.8691.907.72",
            "sys_name": "IOLOGI-E1210-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="br-automation/x20/cp1586",
        vendor="B&R",
        vendor_family="X20",
        model="X20CP1586",
        model_name="X20 Compact PLC",
        device_type="plc",
        description="High-performance compact PLC with integrated I/O",

        oui_prefixes=["00:60:65"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 12.0,
            "mean_ms": 2.5,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "powerlink"],

        instance_rules=InstanceGenerationRules(
            serial_format="BR{2ALPHA}{10NUM}",
            station_name_pattern="{role}-x20-{seq}",
            vendor_short="BR",
            model_short="X20",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.20",
                release_date=date(2024, 2, 5),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.10",
                release_date=date(2022, 10, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="V4.91",
                release_date=date(2021, 5, 20),
                cves=["CVE-2021-22275"],
            ),
        ],

        modbus_identity={
            "vendor_name": "B&R Industrial Automation",
            "product_code": "X20CP1586",
            "product_name": "X20 Compact PLC",
        },

        snmp_identity={
            "sys_descr": "B&R X20 Compact PLC V5.20",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10.504.32",
            "sys_name": "X20-COMPAC-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="advantech/adam/6052",
        vendor="Advantech",
        vendor_family="ADAM-6000",
        model="ADAM-6052",
        model_name="ADAM-6052 Digital I/O Module",
        device_type="remote_io",
        description="16-channel digital I/O module with Modbus/TCP",

        oui_prefixes=["00:D0:C9"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 40.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="ADAM{8NUM}",
            station_name_pattern="rio-{location}-{seq}",
            vendor_short="ADV",
            model_short="A6052",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.05",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.02",
                release_date=date(2022, 4, 20),
                cves=["CVE-2008-5848"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Advantech Co., Ltd.",
            "product_code": "ADAM-6052",
            "product_name": "Digital I/O Module",
        },

        snmp_identity={
            "sys_descr": "Advantech ADAM-6052 Digital I/O Module V2.05",
            "sys_object_id": "1.3.6.1.4.1.10297.475.34",
            "sys_name": "ADAM-6-DIGITA-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="kepware/kepserverex/gateway",
        vendor="Kepware",
        vendor_family="KEPServerEX",
        model="KEPServerEX",
        model_name="KEPServerEX OPC UA Gateway",
        device_type="gateway",
        description="OPC UA gateway for multi-protocol industrial connectivity",

        oui_prefixes=[],  # Software runs on standard PCs

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 50.0,
            "mean_ms": 10.0,
            "std_dev_ms": 8.0,
            "distribution": "lognormal",
        },

        supported_protocols=["opc_ua", "modbus_tcp", "ethernet_ip", "s7comm"],

        opc_ua_identity={
            "application_name": "Kepware KEPServerEX",
            "application_uri": "urn:localhost:KEPServerEX",
            "product_uri": "http://www.kepware.com/kepserverex",
            "manufacturer_name": "Kepware Technologies",
            "product_name": "KEPServerEX",
            "software_version": "6.14.263.0",
            "build_number": "263",
            "build_date": "2023-09-15T12:00:00Z",
        },

        modbus_identity={
            "vendor_name": "Kepware Technologies",
            "product_code": "KEPServerEX",
            "major_minor_revision": "6.14",
            "vendor_url": "http://www.kepware.com",
            "product_name": "KEPServerEX OPC Server",
            "model_name": "OPC UA Gateway",
        },

        ethernet_ip_identity={
            "vendor_id": 1,  # Generic
            "device_type": 12,  # Communications Adapter
            "product_code": 614,
            "revision_major": 6,
            "revision_minor": 14,
            "serial_number": 0x4B455001,
            "product_name": "KEPServerEX EtherNet/IP Driver",
            "state": 3,
        },

        s7_identity={
            "order_code": "KEPServerEX-S7",
            "module_type": "Siemens S7 Driver",
            "firmware_version": "6.14",
            "hardware_version": "N/A",
        },

        instance_rules=InstanceGenerationRules(
            serial_format="KEP-{8HEX}",
            station_name_pattern="gw-opc-{seq}",
            vendor_short="KEP",
            model_short="KEPE",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="6.14",
                release_date=date(2023, 9, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Kepware KEPServerEX OPC UA Gateway V6.14",
            "sys_object_id": "1.3.6.1.4.1.49374.502.34",
            "sys_name": "KEPSER-OPC-001",
            "sys_location": "Network Cabinet",
        },
    ),
]
