# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Honeywell device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="honeywell/controledge/lcnp4m",
        vendor="Honeywell",
        vendor_family="ControlEdge",
        model="900CP1",
        model_name="ControlEdge 900 Controller",
        device_type="plc",
        description="ControlEdge 900 platform process controller (Modbus TCP)",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

        tcp_stack={
            "ttl": 64,
            "window_size": 65535,
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
            serial_format="HW{10ALPHANUM}",
            station_name_pattern="{role}-cedge-{seq}",
            vendor_short="HON",
            model_short="CE900",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R161.1",
                release_date=date(2024, 2, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="R150.2",
                release_date=date(2022, 9, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="R140.1",
                release_date=date(2020, 6, 10),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "900CP1",
            "product_name": "ControlEdge 900 Controller",
        },

        snmp_identity={
            "sys_descr": "Honeywell ControlEdge 900 Controller R161.1",
            "sys_object_id": "1.3.6.1.4.1.2879.492.38",
            "sys_name": "CONTRO-PLC-001",
            "sys_location": "Production Floor",
        },
    ),
    DeviceTemplate(
        id="honeywell/experion-pks/c300",
        vendor="Honeywell",
        vendor_family="Experion PKS",
        model="C300",
        model_name="Experion PKS C300 Controller",
        device_type="dcs_controller",
        description="High-performance process controller for Experion PKS DCS",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 12.0,
            "mean_ms": 2.5,
            "std_dev_ms": 1.8,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="C300-{8HEX}",
            station_name_pattern="c300-{location}-{seq}",
            vendor_short="HON",
            model_short="C300",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R520.2",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=["CVE-2023-24480", "CVE-2023-25178", "CVE-2023-26597"],
            ),
            FirmwareVariant(
                version="R510.1",
                release_date=date(2022, 10, 20),
                cves=["CVE-2023-24480", "CVE-2023-25178", "CVE-2023-26597"],
            ),
            FirmwareVariant(
                version="R501.1",
                release_date=date(2021, 4, 10),
                cves=["CVE-2023-24480", "CVE-2023-25178", "CVE-2023-26597"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "C300",
            "vendor_url": "http://www.honeywell.com",
            "product_name": "Experion PKS C300 Controller",
            "model_name": "C300",
        },

        snmp_identity={
            "sys_descr": "Honeywell Experion PKS C300 Controller VR520.2",
            "sys_object_id": "1.3.6.1.4.1.2879.1.3.300",
        },
    ),
    DeviceTemplate(
        id="honeywell/experion-pks/c200",
        vendor="Honeywell",
        vendor_family="Experion PKS",
        model="C200",
        model_name="Experion PKS C200 Controller",
        device_type="dcs_controller",
        description="Mid-range process controller for Experion PKS DCS",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 0.8,
            "max_ms": 18.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.5,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="C200-{8HEX}",
            station_name_pattern="c200-{location}-{seq}",
            vendor_short="HON",
            model_short="C200",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R520.2",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=["CVE-2021-38395", "CVE-2021-38397", "CVE-2021-38399"],
            ),
            FirmwareVariant(
                version="R510.1",
                release_date=date(2022, 10, 20),
                cves=["CVE-2021-38395", "CVE-2021-38397", "CVE-2021-38399"],
            ),
            FirmwareVariant(
                version="R501.1",
                release_date=date(2021, 4, 10),
                cves=["CVE-2021-38395", "CVE-2021-38397", "CVE-2021-38399"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "C200",
            "vendor_url": "http://www.honeywell.com",
            "product_name": "Experion PKS C200 Controller",
            "model_name": "C200",
        },

        snmp_identity={
            "sys_descr": "Honeywell Experion PKS C200 Controller VR520.2",
            "sys_object_id": "1.3.6.1.4.1.2879.1.3.200",
        },
    ),
    DeviceTemplate(
        id="honeywell/experion-pks/server",
        vendor="Honeywell",
        vendor_family="Experion PKS",
        model="Experion Server",
        model_name="Experion PKS Server",
        device_type="scada_server",
        description="Experion PKS application server for DCS operation",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

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
            "min_ms": 1.0,
            "max_ms": 50.0,
            "mean_ms": 10.0,
            "std_dev_ms": 8.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp", "opc_ua", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="EXPSVR-{8HEX}",
            station_name_pattern="experion-svr-{seq}",
            vendor_short="HON",
            model_short="EXPSVR",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R520.2",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=["CVE-2023-24474", "CVE-2023-23585", "CVE-2023-25078"],
            ),
            FirmwareVariant(
                version="R510.1",
                release_date=date(2022, 10, 20),
                cves=["CVE-2023-24474", "CVE-2023-23585", "CVE-2023-25078"],
            ),
            FirmwareVariant(
                version="R501.1",
                release_date=date(2021, 4, 10),
                cves=["CVE-2023-24474", "CVE-2023-23585", "CVE-2023-25078"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "Experion-Server",
            "product_name": "Experion PKS Server",
        },

        snmp_identity={
            "sys_descr": "Honeywell Experion PKS Server VR520.2",
            "sys_object_id": "1.3.6.1.4.1.2879.60.74",
            "sys_name": "EXPERI-PKS-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="honeywell/experion-pks/safety-manager",
        vendor="Honeywell",
        vendor_family="Experion PKS",
        model="Safety Manager",
        model_name="Experion Safety Manager",
        device_type="safety_plc",
        description="SIL 3 safety controller for Experion PKS",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

        tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 8,
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

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="SM-{8HEX}",
            station_name_pattern="safety-{location}-{seq}",
            vendor_short="HON",
            model_short="SM",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V12.5",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=["CVE-2022-30315"],
            ),
            FirmwareVariant(
                version="V11.3",
                release_date=date(2022, 6, 15),
                cves=["CVE-2022-30315"],
            ),
            FirmwareVariant(
                version="V10.2",
                release_date=date(2020, 9, 10),
                cves=["CVE-2022-30315"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "Safety-Manager",
            "product_name": "Experion Safety Manager",
        },

        snmp_identity={
            "sys_descr": "Honeywell Experion Safety Manager V12.5",
            "sys_object_id": "1.3.6.1.4.1.2879.245.34",
            "sys_name": "EXPERI-SAFETY-001",
            "sys_location": "Safety Cabinet",
        },
    ),
    DeviceTemplate(
        id="honeywell/experion-pks/series-c-io",
        vendor="Honeywell",
        vendor_family="Experion PKS",
        model="Series C I/O",
        model_name="Experion Series C I/O",
        device_type="remote_io",
        description="Series C distributed I/O for Experion PKS",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 0.5,
            "max_ms": 10.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.2,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="SCIO-{8HEX}",
            station_name_pattern="io-seriesc-{seq}",
            vendor_short="HON",
            model_short="SCIO",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V5.3",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V5.0",
                release_date=date(2022, 5, 20),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "Series-C-IO",
            "product_name": "Experion Series C I/O",
        },

        snmp_identity={
            "sys_descr": "Honeywell Experion Series C I/O V5.3",
            "sys_object_id": "1.3.6.1.4.1.2879.507.16",
            "sys_name": "EXPERI-SERIES-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="honeywell/experion-pks/station",
        vendor="Honeywell",
        vendor_family="Experion PKS",
        model="Experion Station",
        model_name="Experion Operator Station",
        device_type="operator_station",
        description="Operator workstation for Experion PKS HMI",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

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
            "min_ms": 2.0,
            "max_ms": 100.0,
            "mean_ms": 20.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="EXPWS-{8HEX}",
            station_name_pattern="experion-ws-{seq}",
            vendor_short="HON",
            model_short="EXPWS",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="R520.2",
                release_date=date(2024, 2, 15),
                is_latest=True,
                is_default=True,
                cves=["CVE-2023-23585", "CVE-2023-25078"],
            ),
            FirmwareVariant(
                version="R510.1",
                release_date=date(2022, 10, 20),
                cves=["CVE-2023-23585", "CVE-2023-25078"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "Experion-Station",
            "product_name": "Experion Operator Station",
        },

        snmp_identity={
            "sys_descr": "Honeywell Experion Operator Station VR520.2",
            "sys_object_id": "1.3.6.1.4.1.2879.724.18",
            "sys_name": "EXPERI-OPERAT-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="honeywell/niagara/jace-8000",
        vendor="Honeywell",
        vendor_family="Niagara",
        model="JACE 8000",
        model_name="JACE 8000 Controller",
        device_type="bms_controller",
        description="Niagara Framework-based building automation controller",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 80.0,
            "mean_ms": 15.0,
            "std_dev_ms": 12.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp", "bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="JACE8K-{8HEX}",
            station_name_pattern="jace-{location}-{seq}",
            vendor_short="HON",
            model_short="JACE8",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="N4.13",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="N4.10",
                release_date=date(2022, 8, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="N4.8",
                release_date=date(2021, 3, 10),
                cves=["CVE-2019-8998", "CVE-2019-13528"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "JACE-8000",
            "product_name": "Niagara JACE 8000",
        },

        bacnet_identity={
            "vendor_id": 17,  # Honeywell (JACE/Tridium sold under Honeywell)
            "vendor_name": "Tridium, Inc.",
            "model_name": "JACE 8000",
        },

        snmp_identity={
            "sys_descr": "Honeywell JACE 8000 Controller VN4.13",
            "sys_object_id": "1.3.6.1.4.1.2879.507.41",
            "sys_name": "JACE-8000-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="honeywell/excel/xl-web",
        vendor="Honeywell",
        vendor_family="Excel",
        model="XL Web",
        model_name="Excel Web Boiler Controller",
        device_type="hvac_controller",
        description="Excel Web controller for boiler and HVAC applications",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
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

        supported_protocols=["modbus_tcp", "bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="XLWEB-{8NUM}",
            station_name_pattern="xlweb-{location}-{seq}",
            vendor_short="HON",
            model_short="XLWEB",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="XLWebExe-2-01-00",
                release_date=date(2016, 11, 30),
                is_latest=True,
                is_default=True,
                cves=["CVE-2017-5143", "CVE-2017-5141", "CVE-2017-5140", "CVE-2017-5139"],
            ),
            FirmwareVariant(
                version="XLWebExe-1-02-08",
                release_date=date(2015, 6, 15),
                cves=["CVE-2017-5143", "CVE-2017-5141", "CVE-2017-5140", "CVE-2017-5139"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "XL-Web",
            "product_name": "Excel Web Boiler Controller",
        },

        bacnet_identity={
            "vendor_id": 17,  # Honeywell
            "vendor_name": "Honeywell",
            "model_name": "Excel Web",
        },

        snmp_identity={
            "sys_descr": "Honeywell Excel Web Boiler Controller XLWebExe-2-01-00",
            "sys_object_id": "1.3.6.1.4.1.2879.154.4",
            "sys_name": "EXCEL-WEB-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="honeywell/enraf/optiflex-6000",
        vendor="Honeywell",
        vendor_family="Enraf",
        model="Optiflex 6000",
        model_name="Optiflex 6000 Level Gauge",
        device_type="level_gauge",
        description="Servo tank gauge for custody transfer applications",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

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
            serial_format="OPT6K-{8NUM}",
            station_name_pattern="gauge-{location}-{seq}",
            vendor_short="HON",
            model_short="OPT6K",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.3.1",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.1.0",
                release_date=date(2022, 5, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="V3.8.0",
                release_date=date(2020, 9, 10),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Honeywell Enraf",
            "product_code": "Optiflex-6000",
            "product_name": "Optiflex 6000 Level Gauge",
        },

        snmp_identity={
            "sys_descr": "Honeywell Optiflex 6000 Level Gauge V4.3.1",
            "sys_object_id": "1.3.6.1.4.1.2879.114.18",
            "sys_name": "OPTIFL-6000-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="honeywell/rtu/2020",
        vendor="Honeywell",
        vendor_family="Enraf",
        model="RTU2020",
        model_name="RTU2020 Remote Terminal Unit",
        device_type="rtu",
        description="Remote terminal unit for tank gauging and control",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 80.0,
            "mean_ms": 20.0,
            "std_dev_ms": 12.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="HW-RTU{8NUM}",
            station_name_pattern="rtu-{location}-{seq}",
            vendor_short="HON",
            model_short="R2020",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.6.0",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=["CVE-2020-10628"],
            ),
            FirmwareVariant(
                version="V3.4.0",
                release_date=date(2022, 7, 15),
                cves=["CVE-2020-10628"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "RTU2020",
            "product_name": "RTU2020 Remote Terminal Unit",
        },

        snmp_identity={
            "sys_descr": "Honeywell RTU2020 Remote Terminal Unit V3.6.0",
            "sys_object_id": "1.3.6.1.4.1.2879.202.67",
            "sys_name": "RTU202-REMOTE-001",
            "sys_location": "Remote Site",
        },
    ),
    DeviceTemplate(
        id="honeywell/spyder/vav",
        vendor="Honeywell",
        vendor_family="Spyder",
        model="PUB6438S",
        model_name="Spyder Unitary Controller",
        device_type="vav_controller",
        description="Programmable VAV controller with BACnet",

        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 80.0,
            "mean_ms": 20.0,
            "std_dev_ms": 12.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="SPY{10NUM}",
            station_name_pattern="vav-{location}-{seq}",
            vendor_short="HON",
            model_short="SPY",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.0.3",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.8.0",
                release_date=date(2022, 6, 10),
                cves=[],
            ),
        ],

        bacnet_identity={
            "vendor_id": 17,  # Honeywell
            "device_type": "VAV Controller",
            "model_name": "Spyder PUB6438S",
        },

        modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "PUB6438S",
            "product_name": "Spyder Unitary Controller",
        },

        snmp_identity={
            "sys_descr": "Honeywell Spyder Unitary Controller V4.0.3",
            "sys_object_id": "1.3.6.1.4.1.2879.843.87",
            "sys_name": "SPYDER-UNITAR-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="honeywell/hc900/hc900-controller",
        vendor="Honeywell",
        vendor_family="HC900",
        model="HC900 Controller",
        model_name="HC900 Controller",
        device_type="instrument",
        description="Honeywell HC900 Controller",
        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],
        tcp_stack={
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 5.0,
                "max_ms": 50.0,
                "mean_ms": 15.0,
                "std_dev_ms": 8.0,
                "distribution": "gaussian",
            },
        supported_protocols=['modbus_tcp'],
        firmware_variants=[FirmwareVariant(
            version="7.3",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Honeywell International Inc",
                "product_code": "900C52-0001",
                "major_minor_revision": "7.3",
                "product_name": "HC900 Hybrid Controller",
                "model_name": "HC900",
            },

        snmp_identity={
            "sys_descr": "Honeywell HC900 Controller V7.3",
            "sys_object_id": "1.3.6.1.4.1.2879.935.2",
            "sys_name": "HC900-CONTRO-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="honeywell/lds/pipeline-lds",
        vendor="Honeywell",
        vendor_family="LDS",
        model="Pipeline LDS",
        model_name="Pipeline LDS",
        device_type="leak_detection",
        description="Honeywell Pipeline LDS",
        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],
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
                "std_dev_ms": 15.0,
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
            version="3.2.0",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Honeywell International Inc.",
                "product_code": "LDS-3200",
                "major_minor_revision": "V3.2.0",
                "product_name": "Pipeline Leak Detection System",
                "model_name": "LDS Server",
            },

        snmp_identity={
            "sys_descr": "Honeywell Pipeline LDS V3.2.0",
            "sys_object_id": "1.3.6.1.4.1.2879.659.68",
            "sys_name": "PIPELI-LDS-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="honeywell/stt/stt850",
        vendor="Honeywell",
        vendor_family="STT",
        model="STT850",
        model_name="STT850",
        device_type="instrument",
        description="Honeywell STT850",
        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],
        tcp_stack={
                "ttl": 64,
                "window_size": 4096,
                "mss": 536,
            },
        response_timing={
                "min_ms": 20.0,
                "max_ms": 150.0,
                "mean_ms": 50.0,
                "std_dev_ms": 25.0,
                "distribution": "gaussian",
            },
        supported_protocols=['modbus_tcp'],
        firmware_variants=[FirmwareVariant(
            version="4.2",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Honeywell International Inc",
                "product_code": "STT850-E-0-AHS",
                "major_minor_revision": "4.2",
                "product_name": "STT850 SmartLine Temperature Transmitter",
                "model_name": "STT850",
            },

        snmp_identity={
            "sys_descr": "Honeywell STT850 V4.2",
            "sys_object_id": "1.3.6.1.4.1.2879.656.72",
            "sys_name": "STT850-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="honeywell/uda/uda2182",
        vendor="Honeywell",
        vendor_family="UDA",
        model="UDA2182",
        model_name="UDA2182",
        device_type="instrument",
        description="Honeywell UDA2182",
        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 10.0,
                "max_ms": 80.0,
                "mean_ms": 30.0,
                "std_dev_ms": 15.0,
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
            version="2.50",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Honeywell International Inc.",
                "product_code": "UDA2182",
                "major_minor_revision": "V2.50",
                "product_name": "UDA2182 Universal Dual Analyzer",
                "model_name": "Process Analyzer",
            },

        snmp_identity={
            "sys_descr": "Honeywell UDA2182 V2.50",
            "sys_object_id": "1.3.6.1.4.1.2879.200.39",
            "sys_name": "UDA2182-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="honeywell/udc/udc3500",
        vendor="Honeywell",
        vendor_family="UDC",
        model="UDC3500",
        model_name="UDC3500",
        device_type="instrument",
        description="Honeywell UDC3500",
        oui_prefixes=["00:06:4A", "00:0A:13", "00:11:12", "00:1E:1E"],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 10.0,
                "max_ms": 80.0,
                "mean_ms": 25.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
            },
        supported_protocols=['modbus_tcp'],
        firmware_variants=[FirmwareVariant(
            version="6.1",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Honeywell International Inc",
                "product_code": "DC3500-EE-0L00-200",
                "major_minor_revision": "6.1",
                "product_name": "UDC3500 Universal Digital Controller",
                "model_name": "UDC3500",
            },

        snmp_identity={
            "sys_descr": "Honeywell UDC3500 V6.1",
            "sys_object_id": "1.3.6.1.4.1.2879.380.92",
            "sys_name": "UDC3500-001",
            "sys_location": "Industrial Network",
        },
    ),
]
