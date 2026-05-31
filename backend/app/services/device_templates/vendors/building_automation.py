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

        oui_prefixes=["00:1A:17", "00:16:C7", "00:23:BE"],

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
                cves=["CVE-2021-36205"],
            ),
            FirmwareVariant(
                version="V10.1.0",
                release_date=date(2021, 3, 10),
                cves=["CVE-2021-36205", "CVE-2021-27654"],
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

        oui_prefixes=["00:1A:17", "00:16:C7", "00:23:BE"],

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
                cves=["CVE-2021-36205"],
            ),
            FirmwareVariant(
                version="V3.0.0",
                release_date=date(2020, 10, 10),
                cves=["CVE-2021-36205", "CVE-2020-9049"],
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

        oui_prefixes=["00:04:5A", "00:A0:AF"],

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
                cves=["CVE-2021-27660"],
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

        oui_prefixes=["00:04:5A", "00:A0:AF"],

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

        oui_prefixes=["00:50:C2", "00:17:61"],

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
                cves=["CVE-2021-44228"],
                notes="Log4j vulnerability",
            ),
        ],

        bacnet_identity={
            "vendor_id": 71,
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

        oui_prefixes=["00:60:35", "00:50:C2"],

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
                cves=[],
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

        oui_prefixes=["00:10:91", "00:1E:C0"],

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
                cves=["CVE-2022-21661"],
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

        oui_prefixes=["00:10:91", "00:1E:C0"],

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
                cves=[],
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

        oui_prefixes=["00:E0:C9", "00:25:B0"],

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
                cves=[],
            ),
            FirmwareVariant(
                version="V7.0.0.15",
                release_date=date(2022, 8, 10),
                cves=[],
            ),
        ],

        bacnet_identity={
            "vendor_id": 56,  # Carrier
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

        oui_prefixes=["00:E0:C9", "00:25:B0"],

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
            "vendor_id": 56,
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

        oui_prefixes=["00:0F:A3"],

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
                cves=["CVE-2022-40619"],
            ),
        ],

        bacnet_identity={
            "vendor_id": 285,  # Distech Controls
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

        oui_prefixes=["00:08:B6"],

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
                cves=["CVE-2022-44028"],
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

        oui_prefixes=["00:E0:C9", "00:0E:70"],

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
                cves=[],
            ),
            FirmwareVariant(
                version="V7.0",
                release_date=date(2022, 5, 20),
                cves=[],
            ),
        ],

        bacnet_identity={
            "vendor_id": 108,  # Automated Logic
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

        oui_prefixes=["00:1C:7E"],

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
                cves=["CVE-2022-37953"],
            ),
        ],

        modbus_identity={
            "vendor_name": "Carel Industries",
            "product_code": "pCO5+",
            "product_name": "pCO5+ HVAC Controller",
        },

        bacnet_identity={
            "vendor_id": 198,
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

        oui_prefixes=["00:60:35", "00:D0:36"],

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
                cves=["CVE-2022-39144"],
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

        oui_prefixes=["00:09:23", "00:15:B2"],

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
                cves=["CVE-2022-41666"],
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
        oui_prefixes=['00:14:C1', '00:1C:12'],
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
                "vendor_id": 86,
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
        oui_prefixes=['00:0D:AD', '00:1E:8E'],
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
                "vendor_id": 301,
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
        oui_prefixes=['00:0B:AB', '00:0D:9F'],
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
                "vendor_id": 122,
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
        oui_prefixes=['00:0B:AB', '00:0D:9F'],
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
                "vendor_id": 122,
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
        oui_prefixes=['00:1E:C0', 'D0:77:14'],
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
                "vendor_id": 165,
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
        oui_prefixes=['00:1A:17', '00:23:BE'],
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
        oui_prefixes=['00:0D:AD', '00:1C:C0'],
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
                "vendor_id": 97,
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
]
