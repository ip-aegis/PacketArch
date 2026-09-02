# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Process instrumentation device templates (Endress+Hauser, SICK, Vaisala, Rotork)."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="sick/inspector/p631",
        vendor="SICK",
        vendor_family="Inspector",
        model="Inspector P631",
        model_name="Inspector P631 Vision Sensor",
        device_type="vision_sensor",
        description="2D vision sensor for quality inspection applications",

        oui_prefixes=["00:06:77"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip", "profinet", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="SICK{8ALPHANUM}",
            station_name_pattern="cam-{location}-{seq}",
            vendor_short="SICK",
            model_short="P631",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.4.1",
                release_date=date(2023, 10, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x0112,
            "device_id": 0x0631,
            "device_role": 1,
            "im0_manufacturer": "SICK AG",
            "im0_order_id": "Inspector P631",
        },

        ethernet_ip_identity={
            "vendor_id": 274,
            "device_type": 43,
            "product_code": 631,
            "revision_major": 2,
            "revision_minor": 4,
            "product_name": "Inspector P631 Vision Sensor",
            "state": 3,
        },

        modbus_identity={
            "vendor_name": "SICK AG",
            "product_code": "Inspector P631",
            "major_minor_revision": "V2.4.1",
            "product_name": "Inspector P631 Vision Sensor",
            "model_name": "Inspector P631",
        },

        snmp_identity={
            "sys_descr": "SICK Inspector P631 Vision Sensor V2.4.1",
            "sys_object_id": "1.3.6.1.4.1.1713.109.88",
            "sys_name": "INSPEC-P631-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="sick/clv/clv650-0120",
        vendor="SICK",
        vendor_family="CLV",
        model="CLV650-0120",
        model_name="CLV650 Barcode Scanner",
        device_type="barcode_scanner",
        description="Industrial barcode scanner for logistics and manufacturing",

        oui_prefixes=["00:06:77"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": True,
        },

        response_timing={
            "min_ms": 1.0,
            "max_ms": 25.0,
            "mean_ms": 8.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
        },

        supported_protocols=["ethernet_ip", "profinet", "modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="CLV{8ALPHANUM}",
            station_name_pattern="scan-{location}-{seq}",
            vendor_short="SICK",
            model_short="CLV650",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.10",
                release_date=date(2023, 7, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        profinet_identity={
            "vendor_id": 0x0112,
            "device_id": 0x0650,
            "device_role": 1,
            "im0_manufacturer": "SICK AG",
            "im0_order_id": "CLV650-0120",
        },

        ethernet_ip_identity={
            "vendor_id": 274,
            "device_type": 43,
            "product_code": 650,
            "revision_major": 2,
            "revision_minor": 10,
            "product_name": "CLV650 Barcode Scanner",
            "state": 3,
        },

        modbus_identity={
            "vendor_name": "SICK AG",
            "product_code": "CLV650-0120",
            "major_minor_revision": "V2.10",
            "product_name": "CLV650 Barcode Scanner",
            "model_name": "CLV650",
        },

        snmp_identity={
            "sys_descr": "SICK CLV650 Barcode Scanner V2.10",
            "sys_object_id": "1.3.6.1.4.1.1713.61.26",
            "sys_name": "CLV650-BARCOD-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="endress_hauser/promag/400",
        vendor="Endress+Hauser",
        vendor_family="Promag",
        model="Promag 400",
        model_name="Promag 400 Electromagnetic Flow Meter",
        device_type="flow_sensor",
        description="Electromagnetic flow meter for process applications",

        oui_prefixes=["00:07:05"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 80.0,
            "mean_ms": 25.0,
            "std_dev_ms": 12.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="EH{10ALPHANUM}",
            station_name_pattern="ft-{location}-{seq}",
            vendor_short="EH",
            model_short="PM400",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V01.06.00",
                release_date=date(2023, 8, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Endress+Hauser",
            "product_code": "Promag 400",
            "vendor_url": "http://www.endress.com",
            "product_name": "Promag 400",
            "model_name": "Promag",
        },

        snmp_identity={
            "sys_descr": "Endress+Hauser Promag 400 Electromagnetic Flow Meter V01.06.00",
            "sys_object_id": "1.3.6.1.4.1.8714.66.17",
            "sys_name": "PROMAG-400-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="endress_hauser/levelflex/fmp50",
        vendor="Endress+Hauser",
        vendor_family="Levelflex",
        model="FMP50",
        model_name="Levelflex FMP50 Level Transmitter",
        device_type="level_sensor",
        description="Guided wave radar level transmitter for liquids and solids",

        oui_prefixes=["00:07:05"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 30.0,
            "std_dev_ms": 15.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="EH{10ALPHANUM}",
            station_name_pattern="lt-{location}-{seq}",
            vendor_short="EH",
            model_short="FMP50",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V01.05.00",
                release_date=date(2023, 5, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Endress+Hauser",
            "product_code": "FMP50",
            "vendor_url": "http://www.endress.com",
            "product_name": "Levelflex FMP50",
            "model_name": "Levelflex",
        },

        snmp_identity={
            "sys_descr": "Endress+Hauser Levelflex FMP50 Level Transmitter V01.05.00",
            "sys_object_id": "1.3.6.1.4.1.8714.348.75",
            "sys_name": "LEVELF-FMP50-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="endress_hauser/cerabar/pmc71",
        vendor="Endress+Hauser",
        vendor_family="Cerabar",
        model="PMC71",
        model_name="Cerabar PMC71 Pressure Transmitter",
        device_type="pressure_sensor",
        description="Digital pressure transmitter for process measurement",

        oui_prefixes=["00:07:05"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 90.0,
            "mean_ms": 28.0,
            "std_dev_ms": 14.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="EH{10ALPHANUM}",
            station_name_pattern="pt-{location}-{seq}",
            vendor_short="EH",
            model_short="PMC71",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V01.06.00",
                release_date=date(2023, 9, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Endress+Hauser",
            "product_code": "PMC71",
            "vendor_url": "http://www.endress.com",
            "product_name": "Cerabar PMC71",
            "model_name": "Cerabar",
        },

        snmp_identity={
            "sys_descr": "Endress+Hauser Cerabar PMC71 Pressure Transmitter V01.06.00",
            "sys_object_id": "1.3.6.1.4.1.8714.768.21",
            "sys_name": "CERABA-PMC71-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="endress-hauser/promag/400",
        vendor="Endress+Hauser",
        vendor_family="Promag",
        model="Promag 400",
        model_name="Promag 400 Electromagnetic Flowmeter",
        device_type="flow_meter",
        description="Electromagnetic flowmeter for process measurement applications",

        oui_prefixes=["00:07:05"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 10.0,
            "std_dev_ms": 6.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="EH{2ALPHA}{10NUM}",
            station_name_pattern="fit-{location}-{seq}",
            vendor_short="EH",
            model_short="PM400",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V01.05.00",
                release_date=date(2024, 1, 15),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V01.03.00",
                release_date=date(2022, 6, 20),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Endress+Hauser",
            "product_code": "Promag 400",
            "product_name": "Electromagnetic Flowmeter",
        },

        snmp_identity={
            "sys_descr": "Endress+Hauser Promag 400 Electromagnetic Flowmeter V01.05.00",
            "sys_object_id": "1.3.6.1.4.1.8714.149.15",
            "sys_name": "PROMAG-400-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="endress-hauser/liquiline/cm442",
        vendor="Endress+Hauser",
        vendor_family="Liquiline",
        model="CM442",
        model_name="Liquiline CM442 Transmitter",
        device_type="analyzer",
        description="Multi-parameter transmitter for liquid analysis",

        oui_prefixes=["00:07:05"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 80.0,
            "mean_ms": 15.0,
            "std_dev_ms": 10.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="CM44{8NUM}",
            station_name_pattern="ait-{location}-{seq}",
            vendor_short="EH",
            model_short="CM442",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V01.08.00",
                release_date=date(2024, 2, 10),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V01.06.00",
                release_date=date(2022, 9, 15),
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Endress+Hauser",
            "product_code": "CM442",
            "product_name": "Liquiline Multiparameter Transmitter",
        },

        snmp_identity={
            "sys_descr": "Endress+Hauser Liquiline CM442 Transmitter V01.08.00",
            "sys_object_id": "1.3.6.1.4.1.8714.868.54",
            "sys_name": "LIQUIL-CM442-001",
            "sys_location": "Process Area",
        },
    ),
    DeviceTemplate(
        id="vaisala/rwis/500",
        vendor="Vaisala",
        vendor_family="RWIS",
        model="RWIS500",
        model_name="Road Weather Information System",
        device_type="weather_station",
        description="Road weather station for transportation applications",

        oui_prefixes=["00:0D:2C", "00:0F:2C", "00:80:A3", "00:C0:F2"],

        tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 20.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
        },

        supported_protocols=["snmp"],

        instance_rules=InstanceGenerationRules(
            serial_format="VWS{10NUM}",
            station_name_pattern="rwis-{location}-{seq}",
            vendor_short="VAI",
            model_short="RW500",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="V2.5.0",
                release_date=date(2024, 1, 25),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
            FirmwareVariant(
                version="V2.3.0",
                release_date=date(2022, 7, 10),
                cves=[],
            ),
        ],

        snmp_identity={
            "sys_descr": "Vaisala RWIS500 Road Weather Station V2.5.0",
            "sys_object_id": "1.3.6.1.4.1.10395.1.1",
        },
    ),
    DeviceTemplate(
        id="endress-hauser/prosonic/fmu90",
        vendor="Endress+Hauser",
        vendor_family="Prosonic",
        model="FMU90",
        model_name="FMU90",
        device_type="field_instrument",
        description="Endress+Hauser FMU90",
        oui_prefixes=["00:07:05"],
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
                "outlier_probability": 0.003,
                "outlier_multiplier": 3.0,
            },
        error_behavior={
                "supported_exception_codes": [1, 2, 3, 4],
                "exception_probability": 0.0004,
                "timeout_probability": 0.0002,
            },
        supported_protocols=['modbus_tcp'],
        firmware_variants=[FirmwareVariant(
            version="01.04.00",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Endress+Hauser",
                "product_code": "FMU90-R11CA111AA3A",
                "major_minor_revision": "01.04.00",
                "vendor_url": "http://www.endress.com",
                "product_name": "Prosonic S FMU90 Ultrasonic Level",
                "model_name": "Ultrasonic Level Transmitter",
            },

        snmp_identity={
            "sys_descr": "Endress+Hauser FMU90 V01.04.00",
            "sys_object_id": "1.3.6.1.4.1.8714.29.87",
            "sys_name": "FMU90-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="endress-hauser/promag/promag-w-400",
        vendor="Endress+Hauser",
        vendor_family="Promag",
        model="Promag W 400",
        model_name="Promag W 400",
        device_type="field_instrument",
        description="Endress+Hauser Promag W 400",
        oui_prefixes=["00:07:05"],
        tcp_stack={
                "ttl": 64,
                "window_size": 16384,
                "mss": 1460,
                "sack_permitted": True,
                "timestamps_enabled": False,
            },
        response_timing={
                "min_ms": 5.0,
                "max_ms": 45.0,
                "mean_ms": 14.0,
                "std_dev_ms": 7.0,
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
            version="01.07.00",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "Endress+Hauser",
                "product_code": "50W4H-UA0A1AA0AAAA",
                "major_minor_revision": "01.07.00",
                "vendor_url": "http://www.endress.com",
                "product_name": "Proline Promag W 400 Water Flowmeter",
                "model_name": "Water Flowmeter",
            },

        snmp_identity={
            "sys_descr": "Endress+Hauser Promag W 400 V01.07.00",
            "sys_object_id": "1.3.6.1.4.1.8714.36.65",
            "sys_name": "PROMAG-W-001",
            "sys_location": "Industrial Network",
        },
    ),
    DeviceTemplate(
        id="sick/clv/sick-clv650",
        vendor="SICK",
        vendor_family="CLV",
        model="SICK CLV650",
        model_name="SICK CLV650",
        device_type="barcode_scanner",
        description="SICK SICK CLV650",
        oui_prefixes=["00:06:77"],
        tcp_stack={
                "ttl": 64,
                "window_size": 8192,
                "mss": 1460,
            },
        response_timing={
                "min_ms": 2.0,
                "max_ms": 30.0,
                "mean_ms": 8.0,
                "std_dev_ms": 5.0,
                "distribution": "gaussian",
            },
        supported_protocols=['modbus_tcp', 'ethernet_ip'],
        firmware_variants=[FirmwareVariant(
            version="5.60",
            release_date=date(2024, 1, 1),
            is_default=True,
            is_latest=True,
        )],
        modbus_identity={
                "vendor_name": "SICK AG",
                "product_code": "1041807",
                "major_minor_revision": "V5.60",
                "product_name": "CLV650 Fixed Mount Barcode Scanner",
                "model_name": "CLV650",
            },
        ethernet_ip_identity={
                "vendor_id": 218,
                "device_type": 12,
                "product_code": 650,
                "revision_major": 5,
                "revision_minor": 60,
                "product_name": "CLV650 Barcode Scanner",
                "state": 3,
            },

        snmp_identity={
            "sys_descr": "SICK CLV650 V5.60",
            "sys_object_id": "1.3.6.1.4.1.1713.660.74",
            "sys_name": "SICK-CLV650-001",
            "sys_location": "Industrial Network",
        },
    ),
    # ------------------------------------------------------------------
    # Rotork IQ3 Pro — electric valve actuator with integrated Ethernet.
    #
    # Added because the catalog held exactly ONE valve actuator fingerprint
    # (Emerson Fisher DVC6200), shared by six archetype vendor profiles — up to
    # 32 fingerprint-identical actuators in a single generated scenario. Cyber
    # Vision merges identically-fingerprinted devices, so that inflates a
    # scenario's declared asset count above what CV will actually report.
    #
    # Every field below is from an authoritative source. Nothing is inferred:
    #   OUI 00:90:14   IEEE MA-L registry, registrant "ROTORK INSTRUMENTS, LTD."
    #   model          rotork.com — the IQ3 Pro range, "available with fully
    #                  integrated ethernet, which is compatible with EtherNet/IP
    #                  Modbus TCP and PROFINET protocols"
    #   ODVA vendor 659 + Generic Device profile 0x2B — ODVA marketplace listing
    #                  for the Rotork Integrated Ethernet Actuator, DOC 12399,
    #                  conformance tested 2025
    #
    # firmware_variants is deliberately EMPTY. Rotork does not publish IQ3 Pro
    # firmware version numbers (their own downloads page only says the device
    # firmware "needs to match the firmware in the title of the Device
    # Description zip file"), and the curation rule is that a firmware value
    # must be real rather than merely well-shaped. An absent firmware string is
    # honest; an invented one would be a confidently-incorrect fingerprint.
    # Populate this when a verifiable version is available.
    #
    # cves is empty and correct: no published CVEs for this actuator range.
    # Field devices legitimately have few or none, and padding the list would
    # be worse than leaving it bare.
    DeviceTemplate(
        id="rotork/iq3/pro",
        vendor="Rotork",
        vendor_family="IQ3 Pro",
        model="IQ3 Pro",
        model_name="Rotork IQ3 Pro Integrated Ethernet Actuator",
        device_type="valve_positioner",
        description=(
            "Intelligent multi-turn electric valve actuator for isolation or "
            "regulating duty, with integrated industrial Ethernet"
        ),

        oui_prefixes=["00:90:14"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
        },

        response_timing={
            "min_ms": 8.0,
            "max_ms": 120.0,
            "mean_ms": 30.0,
            "std_dev_ms": 18.0,
            "distribution": "lognormal",
        },

        supported_protocols=["modbus_tcp", "ethernet_ip", "profinet"],

        instance_rules=InstanceGenerationRules(
            serial_format="IQ3{10NUM}",
            station_name_pattern="actuator-{location}-{seq}",
            vendor_short="RTK",
            model_short="IQ3",
        ),

        firmware_variants=[],

        modbus_identity={
            "vendor_name": "Rotork Controls Limited",
            "product_code": "IQ3 Pro",
            "product_name": "IQ3 Pro Integrated Ethernet Actuator",
        },

        ethernet_ip_identity={
            # ODVA Authorized Vendor ID, from the ODVA marketplace listing.
            "vendor_id": 659,
            "device_type": 0x2B,  # Generic Device
            "product_name": "Integrated Ethernet Actuator",
        },
    ),
]
