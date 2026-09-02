# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Building automation device templates (Johnson Controls, Trane, Carrier, Delta Controls, Automated Logic, Distech Controls, Carel, Notifier, Lutron)."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="johnson-controls/metasys/nae55",
        vendor="Johnson Controls",
        vendor_family="Metasys",
        model="NAE55",
        model_name="NAE55 Network Automation Engine",
        device_type="bac",
        description="Building automation network controller",

        oui_prefixes=["00:10:8D"],

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
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="NAE{10NUM}",
            station_name_pattern="bms-{location}-{seq}",
            vendor_short="JCI",
            model_short="NAE55",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V12.0.3",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V11.0.6",
                release_date=date(2022, 10, 20),
                cves=[],
            ),
            FirmwareVariant(
                version="V10.1.0",
                release_date=date(2021, 3, 10),
                cves=[],
            ),
        ],

        bacnet_identity={
            "vendor_id": 5,  # Johnson Controls
            "device_type": "Network Automation Engine",
            "model_name": "NAE55",
        },

        snmp_identity={
            "sys_descr": "Johnson Controls Metasys NAE55 Network Automation Engine V12.0.3",
            "sys_object_id": "1.3.6.1.4.1.4399.2.1.10",
        },
    ),
    DeviceTemplate(
        id="johnson-controls/facility-explorer/fec26",
        vendor="Johnson Controls",
        vendor_family="Facility Explorer",
        model="FEC26",
        model_name="FEC26 Field Equipment Controller",
        device_type="field_controller",
        description="BACnet field controller for HVAC equipment",

        oui_prefixes=["00:10:8D"],

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

        supported_protocols=["bacnet", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="FEC26{8NUM}",
            station_name_pattern="fec-{location}-{seq}",
            vendor_short="JCI",
            model_short="FEC26",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.5.1",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.3.0",
                release_date=date(2022, 6, 15),
                cves=[],
            ),
            FirmwareVariant(
                version="V3.0.0",
                release_date=date(2020, 10, 10),
                cves=[],
            ),
        ],

        bacnet_identity={
            "vendor_id": 5,
            "device_type": "Field Controller",
            "model_name": "FEC26",
        },

        modbus_identity={
            "vendor_name": "Johnson Controls",
            "product_code": "FEC26",
            "product_name": "Facility Explorer FEC26",
        },

        snmp_identity={
            "sys_descr": "Johnson Controls FEC26 Field Equipment Controller V3.5.1",
            "sys_object_id": "1.3.6.1.4.1.21239.857.19",
            "sys_name": "FEC26-FIELD-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="johnson_controls/metasys/nae55",
        vendor="Johnson Controls",
        vendor_family="Metasys",
        model="NAE55",
        model_name="NAE55 Network Automation Engine",
        device_type="bms_controller",
        description="Building automation network engine for Metasys",

        oui_prefixes=["00:10:8D"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 10.0,
            "max_ms": 150.0,
            "mean_ms": 50.0,
            "std_dev_ms": 25.0,
            "distribution": "gaussian",
        },

        supported_protocols=["bacnet", "snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="JCI{8ALPHANUM}",
            station_name_pattern="nae-{location}-{seq}",
            vendor_short="JCI",
            model_short="NAE55",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="12.0",
                release_date=date(2023, 9, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="11.0",
                release_date=date(2021, 6, 15),
                cves=[],
            ),
        ],

        bacnet_identity={
            "vendor_id": 5,
            "model_name": "NAE55",
            "device_instance": 0,
        },

        snmp_identity={
            "sys_descr": "Johnson Controls Metasys NAE55 Network Automation Engine V12.0",
            "sys_object_id": "1.3.6.1.4.1.4399.2.1.10",
        },
    ),
    DeviceTemplate(
        id="johnson_controls/metasys/fec26",
        vendor="Johnson Controls",
        vendor_family="Metasys",
        model="FEC26",
        model_name="FEC26 Field Equipment Controller",
        device_type="lighting_controller",
        description="Field equipment controller for lighting and HVAC",

        oui_prefixes=["00:10:8D"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 10.0,
            "max_ms": 100.0,
            "mean_ms": 35.0,
            "std_dev_ms": 18.0,
            "distribution": "gaussian",
        },

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="JCI{6ALPHANUM}",
            station_name_pattern="fec-{location}-{seq}",
            vendor_short="JCI",
            model_short="FEC26",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V7.0",
                release_date=date(2023, 4, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        bacnet_identity={
            "vendor_id": 5,
            "model_name": "FEC26",
            "device_instance": 0,
        },

        snmp_identity={
            "sys_descr": "Johnson Controls FEC26 Field Equipment Controller V7.0",
            "sys_object_id": "1.3.6.1.4.1.21239.459.75",
            "sys_name": "FEC26-FIELD-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="automated_logic/webctrl/server",
        vendor="Automated Logic",
        vendor_family="WebCTRL",
        model="Server",
        model_name="WebCTRL Server",
        device_type="bms_server",
        description="WebCTRL building automation server",

        oui_prefixes=["00:E0:C9"],

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
            "mean_ms": 60.0,
            "std_dev_ms": 30.0,
            "distribution": "gaussian",
        },

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="ALC{8ALPHANUM}",
            station_name_pattern="webctrl-{location}-{seq}",
            vendor_short="ALC",
            model_short="WCTRL",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="8.0",
                release_date=date(2023, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="7.0",
                release_date=date(2021, 9, 15),
                cves=["CVE-2021-44228", "CVE-2017-9650", "CVE-2016-5795"],
                notes="Log4j vulnerability",
            ),
        ],

        bacnet_identity={
            "vendor_id": 24,
            "model_name": "WebCTRL Server",
            "device_instance": 0,
        },

        snmp_identity={
            "sys_descr": "Automated Logic WebCTRL Server V8.0",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10.189.91",
            "sys_name": "WEBCTR-SERVER-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="delta_controls/entelibus/manager",
        vendor="Delta Controls",
        vendor_family="enteliBUS",
        model="enteliBUS Manager",
        model_name="enteliBUS Manager",
        device_type="ahu_controller",
        description="Building automation controller for HVAC applications",

        oui_prefixes=["00:40:AE"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 10.0,
            "max_ms": 120.0,
            "mean_ms": 40.0,
            "std_dev_ms": 20.0,
            "distribution": "gaussian",
        },

        # Delta Controls enteliBUS supports BACnet/IP, BACnet MS/TP,
        # and Modbus TCP — declaring both so AHU↔VFD flows have a
        # shared modbus-tcp option for non-BACnet drives.
        supported_protocols=["bacnet", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="DCL{8ALPHANUM}",
            station_name_pattern="ahu-{location}-{seq}",
            vendor_short="DCL",
            model_short="EBUS",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.2",
                release_date=date(2023, 6, 1),
                is_latest=True,
                is_default=True,
                cves=["CVE-2019-9569"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 8,
            "model_name": "enteliBUS Manager",
            "device_instance": 0,
        },

        modbus_identity={
            "vendor_name": "Delta Controls",
            "product_code": "enteliBUS Manager",
            "vendor_url": "http://www.deltacontrols.com",
            "product_name": "enteliBUS Manager (Modbus TCP gateway)",
            "model_name": "enteliBUS",
        },

        snmp_identity={
            "sys_descr": "Delta Controls enteliBUS Manager V4.2",
            "sys_object_id": "1.3.6.1.4.1.12412.270.52",
            "sys_name": "ENTELI-MANAGE-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="trane/tracer/sc-plus",
        vendor="Trane",
        vendor_family="Tracer",
        model="SC+",
        model_name="Tracer SC+ System Controller",
        device_type="bms_controller",
        description="Building automation system controller",

        oui_prefixes=["00:12:EA", "FC:71:FA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
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
            serial_format="TSC{10NUM}",
            station_name_pattern="bms-{location}-{seq}",
            vendor_short="TRA",
            model_short="SC+",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V6.20",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V6.10",
                release_date=date(2022, 7, 20),
                cves=["CVE-2021-38450", "CVE-2021-42534"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 2,  # Trane
            "device_type": "Building Controller",
            "model_name": "Tracer SC+",
        },

        modbus_identity={
            "vendor_name": "Trane Technologies",
            "product_code": "Tracer SC+",
            "product_name": "Tracer SC+ System Controller",
        },

        snmp_identity={
            "sys_descr": "Trane Tracer SC+ System Controller V6.20",
            "sys_object_id": "1.3.6.1.4.1.11108.263.80",
            "sys_name": "TRACER-SC+-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="trane/thermostat/xl950",
        vendor="Trane",
        vendor_family="XL",
        model="XL950",
        model_name="XL950 ComfortLink II Thermostat",
        device_type="thermostat",
        description="Wi-Fi enabled smart thermostat with touchscreen",

        oui_prefixes=["00:12:EA", "FC:71:FA"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 150.0,
            "mean_ms": 40.0,
            "std_dev_ms": 25.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="XL95{8NUM}",
            station_name_pattern="tstat-{location}-{seq}",
            vendor_short="TRA",
            model_short="XL95",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.1.0",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.8.0",
                release_date=date(2022, 5, 15),
                cves=["CVE-2015-2867", "CVE-2015-2868"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 2,
            "device_type": "Thermostat",
            "model_name": "XL950",
        },

        snmp_identity={
            "sys_descr": "Trane XL950 ComfortLink II Thermostat V3.1.0",
            "sys_object_id": "1.3.6.1.4.1.11108.836.55",
            "sys_name": "XL950-COMFOR-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="carrier/i-vu/pro",
        vendor="Carrier",
        vendor_family="i-Vu",
        model="i-Vu Pro",
        model_name="i-Vu Pro Building Automation Server",
        device_type="bms_server",
        description="Web-based building automation system",

        oui_prefixes=["00:02:52", "34:6D:9C", "9C:F6:1A"],

        tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 60.0,
            "mean_ms": 15.0,
            "std_dev_ms": 10.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="IVU-{10NUM}",
            station_name_pattern="bas-{location}-{seq}",
            vendor_short="CAR",
            model_short="IVU",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V8.0.0.1",
                release_date=date(2024, 1, 20),
                is_latest=True,
                is_default=True,
                cves=["CVE-2024-8527"],
            ),
            FirmwareVariant(
                version="V7.0.0.15",
                release_date=date(2022, 8, 10),
                cves=["CVE-2021-44228", "CVE-2024-8527"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 16,  # Carrier
            "device_type": "Automation Server",
            "model_name": "i-Vu Pro",
        },

        snmp_identity={
            "sys_descr": "Carrier i-Vu Pro Building Automation Server V8.0.0.1",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10.342.16",
            "sys_name": "I-VU-PRO-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="carrier/thermostat/33cs2pp",
        vendor="Carrier",
        vendor_family="Performance",
        model="33CS2PP",
        model_name="33CS2PP Programmable Thermostat",
        device_type="thermostat",
        description="Commercial programmable thermostat with BACnet",

        oui_prefixes=["00:02:52", "34:6D:9C", "9C:F6:1A"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 120.0,
            "mean_ms": 30.0,
            "std_dev_ms": 20.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="CS2P{8NUM}",
            station_name_pattern="tstat-{location}-{seq}",
            vendor_short="CAR",
            model_short="CS2P",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.15",
                release_date=date(2024, 2, 5),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.10",
                release_date=date(2022, 6, 15),
                cves=[],
            ),
        ],

        bacnet_identity={
            "vendor_id": 16,
            "device_type": "Thermostat",
            "model_name": "33CS2PP",
        },

        snmp_identity={
            "sys_descr": "Carrier 33CS2PP Programmable Thermostat V2.15",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10.279.0",
            "sys_name": "33CS2P-PROGRA-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="distech/eclypse/bos-8",
        vendor="Distech Controls",
        vendor_family="ECLYPSE",
        model="EC-BOS-8",
        model_name="ECLYPSE Connected BACnet/IP Controller",
        device_type="vav_controller",
        description="Connected controller for VAV box and equipment control",

        oui_prefixes=["00:0D:2C", "00:0F:2C", "00:80:A3", "00:C0:F2"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="ECB8{10NUM}",
            station_name_pattern="vav-{location}-{seq}",
            vendor_short="DIS",
            model_short="ECB8",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V1.6.0",
                release_date=date(2024, 1, 25),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V1.4.5",
                release_date=date(2022, 7, 10),
                cves=["CVE-2025-3936", "CVE-2025-3937", "CVE-2025-3944", "CVE-2025-3945"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 332,  # Distech Controls
            "device_type": "VAV Controller",
            "model_name": "EC-BOS-8",
        },

        snmp_identity={
            "sys_descr": "Distech Controls ECLYPSE Connected BACnet/IP Controller V1.6.0",
            "sys_object_id": "1.3.6.1.4.1.37567.258.70",
            "sys_name": "ECLYPS-CONNEC-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="delta-controls/entelibus/vav",
        vendor="Delta Controls",
        vendor_family="enteliBUS",
        model="enteliBUS",
        model_name="enteliBUS Building Controller",
        device_type="bms_controller",
        description="Modular building automation controller",

        oui_prefixes=["00:40:AE"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 60.0,
            "mean_ms": 15.0,
            "std_dev_ms": 10.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="DCTL{10NUM}",
            station_name_pattern="bms-{location}-{seq}",
            vendor_short="DEL",
            model_short="EBUS",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.6.0",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.4.0",
                release_date=date(2022, 9, 15),
                cves=["CVE-2019-9569"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 8,  # Delta Controls
            "device_type": "Building Controller",
            "model_name": "enteliBUS",
        },

        snmp_identity={
            "sys_descr": "Delta Controls enteliBUS Building Controller V4.6.0",
            "sys_object_id": "1.3.6.1.4.1.12412.552.78",
            "sys_name": "ENTELI-BUILDI-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="automated-logic/webctrl/server",
        vendor="Automated Logic",
        vendor_family="WebCTRL",
        model="WebCTRL",
        model_name="WebCTRL Building Automation System",
        device_type="bms_server",
        description="Enterprise building automation software platform",

        oui_prefixes=["00:E0:C9"],

        tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="WCTL{10NUM}",
            station_name_pattern="bas-{location}-{seq}",
            vendor_short="ALC",
            model_short="WCTL",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V8.0",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=["CVE-2024-8527"],
            ),
            FirmwareVariant(
                version="V7.0",
                release_date=date(2022, 5, 20),
                cves=["CVE-2021-44228", "CVE-2017-9650", "CVE-2016-5795", "CVE-2024-8527"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 24,  # Automated Logic
            "device_type": "Automation Server",
            "model_name": "WebCTRL",
        },

        snmp_identity={
            "sys_descr": "Automated Logic WebCTRL Building Automation System V8.0",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10.610.39",
            "sys_name": "WEBCTR-BUILDI-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="carel/pco5/plus",
        vendor="Carel",
        vendor_family="pCO",
        model="pCO5+",
        model_name="pCO5+ HVAC Controller",
        device_type="hvac_controller",
        description="Programmable controller for HVAC applications",

        oui_prefixes=["00:0A:5C"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 60.0,
            "mean_ms": 15.0,
            "std_dev_ms": 10.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp", "bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="PCO5{10NUM}",
            station_name_pattern="hvac-{location}-{seq}",
            vendor_short="CAR",
            model_short="PCO5",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V3.5.0",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V3.2.0",
                release_date=date(2022, 7, 15),
                cves=["CVE-2019-13553"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Carel Industries",
            "product_code": "pCO5+",
            "product_name": "pCO5+ HVAC Controller",
        },

        bacnet_identity={
            "vendor_id": 77,
            "device_type": "HVAC Controller",
            "model_name": "pCO5+",
            "firmware_revision": "V3.5.0",
        },

        snmp_identity={
            "sys_descr": "Carel pCO5+ HVAC Controller V3.5.0",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10.737.55",
            "sys_name": "PCO5+-HVAC-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="notifier/nfs2/3030",
        vendor="Notifier",
        vendor_family="NFS2",
        model="NFS2-3030",
        model_name="NFS2-3030 Fire Alarm Control Panel",
        device_type="fire_panel",
        description="Intelligent fire alarm control panel",

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

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="NFS{10NUM}",
            station_name_pattern="facp-{location}-{seq}",
            vendor_short="NOT",
            model_short="NFS3",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V4.2.0",
                release_date=date(2024, 1, 25),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V4.0.0",
                release_date=date(2022, 6, 20),
                cves=["CVE-2020-6974", "CVE-2020-6972"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 188,  # Notifier
            "device_type": "Fire Alarm Panel",
            "model_name": "NFS2-3030",
        },

        snmp_identity={
            "sys_descr": "Notifier NFS2-3030 Fire Alarm Control Panel V4.2.0",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10.260.78",
            "sys_name": "NFS2-3-FIRE-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="lutron/quantum/hub",
        vendor="Lutron",
        vendor_family="Quantum",
        model="QSN-4T16-S",
        model_name="Quantum Total Light Management",
        device_type="lighting_controller",
        description="Enterprise lighting control processor",

        oui_prefixes=["00:0F:E7"],

        tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="LUT{10NUM}",
            station_name_pattern="ltg-{location}-{seq}",
            vendor_short="LUT",
            model_short="QTM",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V15.0",
                release_date=date(2024, 2, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V14.2",
                release_date=date(2022, 8, 10),
                cves=[],
            ),
        ],

        bacnet_identity={
            "vendor_id": 115,  # Lutron
            "device_type": "Lighting Controller",
            "model_name": "Quantum",
        },

        snmp_identity={
            "sys_descr": "Lutron Quantum Total Light Management V15.0",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10.610.20",
            "sys_name": "QUANTU-TOTAL-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="automated-logic/webctrl/me812u",
        vendor="Automated Logic",
        vendor_family="WebCTRL",
        model="ME812U",
        model_name="ME812U",
        device_type="building_controller",
        description="Automated Logic ME812U",
        oui_prefixes=["00:E0:C9"],
        tcp_stack={},
        response_timing={
                "min_ms": 8.0,
                "max_ms": 100.0,
                "mean_ms": 30.0,
                "std_dev_ms": 18.0,
                "distribution": "lognormal",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['bacnet'],
        firmware_variants=[FirmwareVariant(
            version="6.2.0",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        bacnet_identity={
                "vendor_id": 24,
                "vendor_name": "Automated Logic",
                "model_name": "ME812U Field Controller",
                "firmware_revision": "6.2.0",
                "application_software_version": "6.2",
                "protocol_version": 1,
                "protocol_revision": 14,
                "max_apdu_length": 480,
                "segmentation_supported": 3,
                "device_instance": 11002,
                "object_name": "ME812U-001",
            },

        snmp_identity={
            "sys_descr": "Automated Logic ME812U V6.2.0",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10.835.48",
            "sys_name": "ME812U-001",
            "sys_location": "Mechanical Room",
        },
    ),
    DeviceTemplate(
        id="carrier/i-vu/pro-open",
        vendor="Carrier",
        vendor_family="i-Vu",
        model="Pro Open",
        model_name="Pro Open",
        device_type="bms_server",
        description="Carrier Pro Open",
        oui_prefixes=["00:02:52", "34:6D:9C", "9C:F6:1A"],
        tcp_stack={
                "ttl": 64,
                "window_size": 65535,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 5.0,
                "max_ms": 70.0,
                "mean_ms": 22.0,
                "std_dev_ms": 12.0,
                "distribution": "gaussian",
                "outlier_probability": 0.003,
                "outlier_multiplier": 4.0,
            },
        error_behavior={
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['bacnet'],
        firmware_variants=[FirmwareVariant(
            version="7.0.2",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        bacnet_identity={
                "vendor_id": 16,
                "vendor_name": "Carrier",
                "model_name": "i-Vu Pro Open Server",
                "firmware_revision": "7.0.2",
                "application_software_version": "7.0",
                "protocol_version": 1,
                "protocol_revision": 19,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 5001,
                "object_name": "IVU-SERVER-001",
            },

        snmp_identity={
            "sys_descr": "Carrier Pro Open V7.0.2",
            "sys_object_id": "1.3.6.1.4.1.8072.3.2.10.392.20",
            "sys_name": "PRO-OPEN-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="delta-controls/entelibus/manager",
        vendor="Delta Controls",
        vendor_family="enteliBUS",
        model="Manager",
        model_name="Manager",
        device_type="building_controller",
        description="Delta Controls Manager",
        oui_prefixes=["00:40:AE"],
        tcp_stack={
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 5.0,
                "max_ms": 80.0,
                "mean_ms": 22.0,
                "std_dev_ms": 13.0,
                "distribution": "gaussian",
                "outlier_probability": 0.004,
                "outlier_multiplier": 4.0,
            },
        error_behavior={
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['bacnet'],
        firmware_variants=[FirmwareVariant(
            version="4.8.0",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        bacnet_identity={
                "vendor_id": 8,
                "vendor_name": "Delta Controls",
                "model_name": "enteliBUS Manager",
                "firmware_revision": "4.8.0",
                "application_software_version": "4.8",
                "protocol_version": 1,
                "protocol_revision": 19,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 8001,
                "object_name": "ENTBUS-MGR-001",
                "description": "enteliBUS Building Controller",
            },

        snmp_identity={
            "sys_descr": "Delta Controls Manager V4.8.0",
            "sys_object_id": "1.3.6.1.4.1.12412.692.50",
            "sys_name": "MANAGER-001",
            "sys_location": "Mechanical Room",
        },
    ),
    DeviceTemplate(
        id="delta-controls/entelibus/ebcon",
        vendor="Delta Controls",
        vendor_family="enteliBUS",
        model="eBCON",
        model_name="eBCON",
        device_type="zone_controller",
        description="Delta Controls eBCON",
        oui_prefixes=["00:40:AE"],
        tcp_stack={},
        response_timing={
                "min_ms": 10.0,
                "max_ms": 120.0,
                "mean_ms": 35.0,
                "std_dev_ms": 20.0,
                "distribution": "lognormal",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['bacnet'],
        firmware_variants=[FirmwareVariant(
            version="3.5.0",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        bacnet_identity={
                "vendor_id": 8,
                "vendor_name": "Delta Controls",
                "model_name": "eBCON Controller",
                "firmware_revision": "3.5.0",
                "application_software_version": "3.5",
                "protocol_version": 1,
                "protocol_revision": 14,
                "max_apdu_length": 480,
                "segmentation_supported": 3,
                "device_instance": 8002,
                "object_name": "EBCON-001",
            },

        snmp_identity={
            "sys_descr": "Delta Controls eBCON V3.5.0",
            "sys_object_id": "1.3.6.1.4.1.12412.245.83",
            "sys_name": "EBCON-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="distech-controls/ecy/ecy-vav",
        vendor="Distech Controls",
        vendor_family="ECY",
        model="ECY-VAV",
        model_name="ECY-VAV",
        device_type="vav_controller",
        description="Distech Controls ECY-VAV",
        oui_prefixes=["00:0D:2C", "00:0F:2C", "00:80:A3", "00:C0:F2"],
        tcp_stack={},
        response_timing={
                "min_ms": 8.0,
                "max_ms": 100.0,
                "mean_ms": 28.0,
                "std_dev_ms": 15.0,
                "distribution": "lognormal",
                "outlier_probability": 0.004,
                "outlier_multiplier": 3.5,
            },
        error_behavior={
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['bacnet'],
        firmware_variants=[FirmwareVariant(
            version="2.5.0",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        bacnet_identity={
                "vendor_id": 332,
                "vendor_name": "Distech Controls",
                "model_name": "ECY-VAV Variable Air Volume Controller",
                "firmware_revision": "2.5.0",
                "application_software_version": "2.5",
                "protocol_version": 1,
                "protocol_revision": 14,
                "max_apdu_length": 480,
                "segmentation_supported": 3,
                "device_instance": 9002,
                "object_name": "ECY-VAV-001",
            },

        snmp_identity={
            "sys_descr": "Distech Controls ECY-VAV V2.5.0",
            "sys_object_id": "1.3.6.1.4.1.37567.293.8",
            "sys_name": "ECY-VAV-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="johnson-controls/metasys/snc",
        vendor="Johnson Controls",
        vendor_family="Metasys",
        model="SNC",
        model_name="SNC",
        device_type="building_controller",
        description="Johnson Controls SNC",
        oui_prefixes=["00:10:8D"],
        tcp_stack={
                "ttl": 64,
                "window_size": 32768,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 8.0,
                "max_ms": 120.0,
                "mean_ms": 35.0,
                "std_dev_ms": 20.0,
                "distribution": "lognormal",
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.5,
            },
        error_behavior={
                "timeout_probability": 0.001,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['bacnet'],
        firmware_variants=[FirmwareVariant(
            version="11.0.2",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        bacnet_identity={
                "vendor_id": 5,
                "vendor_name": "Johnson Controls",
                "model_name": "SNC Supervisory Network Controller",
                "firmware_revision": "11.0.2",
                "application_software_version": "11.0",
                "protocol_version": 1,
                "protocol_revision": 17,
                "max_apdu_length": 1476,
                "segmentation_supported": 0,
                "device_instance": 1002,
                "object_name": "SNC-001",
                "description": "Metasys Supervisory Controller",
            },

        snmp_identity={
            "sys_descr": "Johnson Controls SNC V11.0.2",
            "sys_object_id": "1.3.6.1.4.1.21239.439.98",
            "sys_name": "SNC-001",
            "sys_location": "Mechanical Room",
        },
    ),
    DeviceTemplate(
        id="trane/tracer/uc600",
        vendor="Trane",
        vendor_family="Tracer",
        model="UC600",
        model_name="UC600",
        device_type="building_controller",
        description="Trane UC600",
        oui_prefixes=["00:12:EA", "FC:71:FA"],
        tcp_stack={},
        response_timing={
                "min_ms": 12.0,
                "max_ms": 120.0,
                "mean_ms": 35.0,
                "std_dev_ms": 20.0,
                "distribution": "lognormal",
                "outlier_probability": 0.005,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "timeout_probability": 0.002,
                "retry_behavior": True,
                "max_retries": 3,
            },
        supported_protocols=['bacnet'],
        firmware_variants=[FirmwareVariant(
            version="3.5.2",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        bacnet_identity={
                "vendor_id": 2,
                "vendor_name": "Trane",
                "model_name": "UC600 Unit Controller",
                "firmware_revision": "3.5.2",
                "application_software_version": "3.5",
                "protocol_version": 1,
                "protocol_revision": 14,
                "max_apdu_length": 480,
                "segmentation_supported": 3,
                "device_instance": 4002,
                "object_name": "UC600-AHU-001",
            },

        snmp_identity={
            "sys_descr": "Trane UC600 V3.5.2",
            "sys_object_id": "1.3.6.1.4.1.11108.595.83",
            "sys_name": "UC600-001",
            "sys_location": "Mechanical Room",
        },
    ),
    # ------------------------------------------------------------------
    # Belimo Energy Valve — pressure-independent control valve with an
    # integrated thermal energy meter and a native IP stack.
    #
    # Added to break up bas_tridium emitting up to 12 fingerprint-identical
    # valve actuators and 27 identical field instruments off single catalog
    # entries; Cyber Vision merges identically-fingerprinted devices. Belimo is
    # the natural choice here — it is a building-automation valve vendor, not a
    # process-industry one, so this is a better fit for a BAS scenario than the
    # Fisher/Rotork actuators used on the DCS and water profiles.
    #
    # Sources, all authoritative:
    #   OUI 6C:65:67    IEEE MA-L, registrant "BELIMO Automation AG",
    #                   Brunnenbachstrasse 1, Hinwil CH.
    #   BACnet vid 423  bacnet.org assigned-vendor-ids list, registered as
    #                   "BELIMO Automation AG" at the SAME Hinwil address as
    #                   the IEEE entry — cross-confirming it is one company.
    #                   Belimo holds two IDs (284 and 423); 423 is used here.
    #   model EV065F+BAC  belimo.com datasheets — the Energy Valve range is
    #                   EV<size><body>+BAC, the "+BAC" suffix denoting BACnet.
    #   protocols       belimo.com: BACnet/IP, BACnet MS/TP, Modbus TCP,
    #                   Modbus RTU and MP-Bus, over Ethernet 10/100 with an
    #                   integrated web server and PoE.
    #
    # firmware_variants is EMPTY: Belimo does not publish a firmware version
    # for this range in any citable form, and an invented value would be a
    # confidently-incorrect fingerprint. cves is empty and correct — no
    # published CVEs for this product.
    DeviceTemplate(
        id="belimo/energy-valve/ev065f",
        vendor="Belimo",
        vendor_family="Energy Valve",
        model="EV065F+BAC",
        model_name="Belimo Energy Valve EV065F+BAC",
        device_type="valve_positioner",
        description=(
            "Pressure-independent characterised control valve with integrated "
            "thermal energy meter, native BACnet/IP and Modbus TCP"
        ),

        oui_prefixes=["6C:65:67"],

        tcp_stack={
            "ttl": 64,
            "window_size": 5840,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 10.0,
            "max_ms": 150.0,
            "mean_ms": 40.0,
            "std_dev_ms": 22.0,
            "distribution": "lognormal",
        },

        supported_protocols=["bacnet", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="BEL{10NUM}",
            station_name_pattern="ev-{location}-{seq}",
            vendor_short="BLM",
            model_short="EV065",
        ),

        firmware_variants=[],

        bacnet_identity={
            "vendor_id": 423,
            "device_type": "Energy Valve",
            "model_name": "EV065F+BAC",
        },

        modbus_identity={
            "vendor_name": "BELIMO Automation AG",
            "product_code": "EV065F+BAC",
            "product_name": "Belimo Energy Valve",
        },
    ),
    # ------------------------------------------------------------------
    # Data-centre rack PDUs. dcim_cisco scenarios emit up to 16 PDUs, and the
    # catalog held exactly one (Schneider Rack PDU), so every rack in a
    # generated data centre had an identical PDU fingerprint — and Cyber Vision
    # merges identically-fingerprinted devices.
    #
    # Raritan PX3. Sources: OUI 00:0D:5D is IEEE MA-L "Raritan Computer, Inc"
    # (confirmed against the live registry and reproduced by regenerating from
    # the bundled CSV). PX3-5660 is a real model from raritan.com's own product
    # selector, and raritan.com lists the PX3 management protocols as
    # HTTP(S), SSH, Telnet, SNMP v2/v3 and MODBUS-TCP.
    # firmware/cves empty — no citable firmware version, no published CVEs.
    DeviceTemplate(
        id="raritan/px3/px3-5660",
        vendor="Raritan",
        vendor_family="PX3",
        model="PX3-5660",
        model_name="Raritan PX3-5660 Intelligent Rack PDU",
        device_type="pdu",
        description="Intelligent switched rack power distribution unit with per-outlet metering",

        oui_prefixes=["00:0D:5D"],

        tcp_stack={"ttl": 64, "window_size": 14600, "mss": 1460, "sack_permitted": True},

        response_timing={
            "min_ms": 6.0, "max_ms": 90.0, "mean_ms": 25.0,
            "std_dev_ms": 15.0, "distribution": "lognormal",
        },

        supported_protocols=["snmp", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="RAR{10NUM}",
            station_name_pattern="pdu-{location}-{seq}",
            vendor_short="RAR",
            model_short="PX3",
        ),

        firmware_variants=[],

        snmp_identity={
            "sys_descr": "Raritan PX3-5660 Intelligent Rack PDU",
            "sys_object_id": "1.3.6.1.4.1.13742",  # Raritan enterprise OID
            "sys_name": "PX3-5660-PDU-001",
            "sys_location": "Data Center",
        },

        modbus_identity={
            "vendor_name": "Raritan Computer, Inc",
            "product_code": "PX3-5660",
            "product_name": "PX3 Intelligent Rack PDU",
        },
    ),

    # Eaton ePDU G3. Sources: OUI 00:05:4B and siblings are IEEE MA-L Eaton
    # registrations (regenerated from the bundled IEEE CSV, not hand-entered).
    # EVMAGU23X-3 is a real Eaton order code, appearing as the subject of
    # Eaton's own G3 Universal Input Rack PDU brochure and installation manual.
    # eaton.com states the ePDU G3 supports SNMP v1, v2 and v3 with traps and
    # per-outlet get/set; no Modbus is claimed, so none is declared here.
    #
    # OUI note: IEEE also registers 00:22:D5 to "Eaton Corp. Electrical Group
    # Data Center Solutions", which would be the closest match of all — but the
    # OUI generator caps each vendor at six prefixes and that one sorts past the
    # cut, so it is not in VENDOR_OUIS and the OUI integrity guard rejects it.
    # 00:20:85 is "Eaton Corporation" in the same registry and is the correct
    # registrant for the product either way.
    DeviceTemplate(
        id="eaton/epdu-g3/evmagu23x-3",
        vendor="Eaton",
        vendor_family="ePDU G3",
        model="EVMAGU23X-3",
        model_name="Eaton ePDU G3 Universal Input Rack PDU",
        device_type="pdu",
        description="Managed universal-input rack PDU with outlet switching and metering",

        oui_prefixes=["00:20:85"],

        tcp_stack={"ttl": 64, "window_size": 8192, "mss": 1460, "sack_permitted": True},

        response_timing={
            "min_ms": 8.0, "max_ms": 110.0, "mean_ms": 32.0,
            "std_dev_ms": 18.0, "distribution": "lognormal",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="ETN{10NUM}",
            station_name_pattern="pdu-{location}-{seq}",
            vendor_short="ETN",
            model_short="G3",
        ),

        firmware_variants=[],

        snmp_identity={
            "sys_descr": "Eaton ePDU G3 Universal Input Rack PDU EVMAGU23X-3",
            "sys_object_id": "1.3.6.1.4.1.534",  # Eaton/Powerware enterprise OID
            "sys_name": "EPDU-G3-PDU-001",
            "sys_location": "Data Center",
        },
    ),
    # ------------------------------------------------------------------
    # KMC Controls BAC-A1616BC — BACnet Building Controller for plant/AHU duty.
    #
    # Closes bas_tridium/ahu_controller, which emitted up to 8 identical
    # controllers off the catalog's single Delta Controls entry.
    #
    # Sources: OUI 00:D0:6F is IEEE MA-L "KMC CONTROLS" (already in
    # VENDOR_OUIS, and it matches the live registry). BAC-A1616BC is the real
    # model designation, sold as -000 and -001 variants; kmccontrols.com's own
    # datasheet describes a native BACnet B-BC with an integrated router, web
    # server and 16x16 expandable I/O.
    #
    # IP-capable, which matters: the controller routes between two MS/TP ports,
    # a PTP port, FOUR logical BACnet IP ports and one BACnet Ethernet port on
    # the physical Ethernet interface, and supports BBMD and foreign-device
    # registration. Reliable Controls' MACH-ProZone and MACH-ProAir were
    # considered first and REJECTED for this role: both are MS/TP only, so they
    # have no IP endpoint and cannot be an addressed device in a scenario.
    #
    # firmware/cves empty — no citable firmware version, no published CVEs.
    DeviceTemplate(
        id="kmc/bac-a1616bc/building-controller",
        vendor="KMC Controls",
        vendor_family="BAC-A1616BC",
        model="BAC-A1616BC",
        model_name="KMC Controls BAC-A1616BC BACnet Building Controller",
        device_type="ahu_controller",
        description=(
            "Native BACnet building controller with integrated router and web "
            "server, 16x16 expandable I/O, for air-handling and plant duty"
        ),

        oui_prefixes=["00:D0:6F"],

        tcp_stack={"ttl": 64, "window_size": 4096, "mss": 1460, "sack_permitted": False},

        response_timing={
            "min_ms": 15.0, "max_ms": 220.0, "mean_ms": 55.0,
            "std_dev_ms": 30.0, "distribution": "lognormal",
        },

        supported_protocols=["bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="KMC{10NUM}",
            station_name_pattern="ahu-{location}-{seq}",
            vendor_short="KMC",
            model_short="A1616",
        ),

        firmware_variants=[],

        bacnet_identity={
            "vendor_id": 28,  # KMC Controls, already in BACNET_VENDOR_IDS
            "device_type": "BACnet Building Controller",
            "model_name": "BAC-A1616BC",
        },
    ),
    # ------------------------------------------------------------------
    # Belimo 22RTH-5U00A room sensor — humidity + temperature.
    #
    # Closes bas_tridium/field_instrument, the largest gap the ratchet tracked:
    # up to 27 devices, all previously pinned to a Honeywell JACE 8000, which
    # is a BACnet SUPERVISORY CONTROLLER and was labelled "stand-in for BACnet
    # sensors" in the pinning table. The catalog had no BAS sensor at all.
    #
    # Sources: OUI 6C:65:67 is IEEE MA-L "BELIMO Automation AG". 22RTH-5U00A is
    # a real part number from Belimo's own US shop catalog, listed as a room
    # sensor with active humidity/temperature, NFC, Modbus and BACnet; Belimo
    # publishes Modbus register maps for the 22RTH / 22UTH / 22ADP families.
    #
    # Honest note on the role: a room sensor is a field-bus device, not an
    # IP-addressed one. The field_instrument role explicitly covers this —
    # "often HART-over-Ethernet or Modbus-mapped via gateway" — so it is
    # surfaced the way the role documents rather than by pretending the sensor
    # has its own IP stack. This is also why Reliable Controls' MACH-ProZone
    # and MACH-ProAir were rejected for the controller roles: MS/TP only, with
    # no such gateway story.
    DeviceTemplate(
        id="belimo/22rth/5u00a",
        vendor="Belimo",
        vendor_family="22RTH",
        model="22RTH-5U00A",
        model_name="Belimo 22RTH-5U00A Room Sensor",
        device_type="room_sensor",
        description=(
            "Room air sensor measuring temperature and relative humidity, "
            "with Modbus and BACnet output"
        ),

        oui_prefixes=["6C:65:67"],

        tcp_stack={"ttl": 64, "window_size": 2920, "mss": 1460, "sack_permitted": False},

        response_timing={
            "min_ms": 20.0, "max_ms": 300.0, "mean_ms": 70.0,
            "std_dev_ms": 45.0, "distribution": "lognormal",
        },

        supported_protocols=["bacnet", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="BEL{10NUM}",
            station_name_pattern="rm-sensor-{location}-{seq}",
            vendor_short="BLM",
            model_short="22RTH",
        ),

        firmware_variants=[],

        bacnet_identity={
            "vendor_id": 423,
            "device_type": "Room Sensor",
            "model_name": "22RTH-5U00A",
        },

        modbus_identity={
            "vendor_name": "BELIMO Automation AG",
            "product_code": "22RTH-5U00A",
            "product_name": "Belimo Room Sensor",
        },
    ),
]
