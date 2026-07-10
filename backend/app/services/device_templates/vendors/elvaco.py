# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Elvaco device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="elvaco/cme/3100",
        vendor="Elvaco",
        vendor_family="CMe",
        model="CMe3100",
        model_name="CMe3100 M-Bus Metering Gateway",
        device_type="meter_data_concentrator",
        description="M-Bus/wireless M-Bus (EN 13757) to BACnet/IP and Modbus TCP "
                     "metering gateway for up to 512 wired meters; marketed "
                     "specifically for EU EED remote-reading compliance of heat, "
                     "hot-water, and cold-water sub-meters",

        oui_prefixes=["94:19:3A"],

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

        supported_protocols=["modbus_tcp", "bacnet"],

        instance_rules=InstanceGenerationRules(
            serial_format="CME3100-{8HEX}",
            station_name_pattern="meter-concentrator-{seq}",
            vendor_short="ELV",
            model_short="CME3100",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="1.12.0",
                release_date=date(2023, 6, 1),
                cves=["CVE-2024-49396", "CVE-2024-49397", "CVE-2024-49398", "CVE-2024-49399"],
                notes="ICSA-24-291-01: insufficiently protected credentials, "
                      "authentication bypass, unrestricted file upload (RCE), and "
                      "unauthorized remote access",
            ),
            FirmwareVariant(
                version="1.13.0",
                release_date=date(2024, 11, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Elvaco AB",
            "product_code": "CMe3100",
            "vendor_url": "https://www.elvaco.com",
            "product_name": "CMe3100 M-Bus Metering Gateway",
            "model_name": "CMe3100",
        },

        bacnet_identity={
            "vendor_id": 1473,
            "vendor_name": "Elvaco AB",
            "model_name": "CMe3100",
            "device_instance": 0,
        },
    ),
]
