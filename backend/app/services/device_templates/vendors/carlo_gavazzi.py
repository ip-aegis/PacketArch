# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Carlo Gavazzi device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="carlo_gavazzi/em24/ethernet",
        vendor="Carlo Gavazzi",
        vendor_family="EM24",
        model="EM24DINAV23XE1X",
        model_name="EM24-Ethernet Energy Meter",
        device_type="power_meter",
        description="DIN-rail three-phase energy meter with native Ethernet/Modbus TCP, "
                     "the standard per-tenant electrical sub-meter for EU commercial "
                     "real-estate billing retrofits",

        oui_prefixes=["00:19:EE", "00:50:A1", "68:49:B2"],

        tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },

        response_timing={
            "min_ms": 3.0,
            "max_ms": 60.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="EM24{6NUM}",
            station_name_pattern="meter-em24-{seq}",
            vendor_short="CGZ",
            model_short="EM24",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="2.5",
                release_date=date(2021, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Carlo Gavazzi",
            "product_code": "EM24DINAV23XE1X",
            "vendor_url": "https://www.gavazziautomation.com",
            "product_name": "EM24-Ethernet Energy Meter",
            "model_name": "EM24",
        },
    ),
    DeviceTemplate(
        id="carlo_gavazzi/vmu-c/em",
        vendor="Carlo Gavazzi",
        vendor_family="VMU-C",
        model="VMU-C EM",
        model_name="VMU-C EM Data Concentrator",
        device_type="meter_data_concentrator",
        description="Multi-meter data concentrator aggregating up to 32 RS-485 "
                     "sub-meters onto Modbus TCP/IP with a built-in web/FTP portal; "
                     "typically one per building riser or floor cluster",

        oui_prefixes=["00:19:EE", "00:50:A1", "68:49:B2"],

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
            "distribution": "gaussian",
            "outlier_probability": 0.003,
            "outlier_multiplier": 3.5,
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="VMUC{6NUM}",
            station_name_pattern="submeter-concentrator-{seq}",
            vendor_short="CGZ",
            model_short="VMUC",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="A11_U04",
                release_date=date(2015, 6, 1),
                cves=["CVE-2017-5144"],
                notes="Access-control flaw (ICSA-17-012-03) allows unauthenticated "
                      "access to most application functions",
            ),
            FirmwareVariant(
                version="A11_U05",
                release_date=date(2017, 3, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Carlo Gavazzi",
            "product_code": "VMU-C EM",
            "vendor_url": "https://www.gavazziautomation.com",
            "product_name": "VMU-C EM Data Concentrator",
            "model_name": "VMU-C EM",
        },
    ),
]
