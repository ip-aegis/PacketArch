# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Danfoss device templates."""

from app.services.device_templates._types import DeviceTemplate, FirmwareVariant, InstanceGenerationRules

from datetime import date


TEMPLATES: list[DeviceTemplate] = [
    DeviceTemplate(
        id="danfoss/ecl-comfort/310",
        vendor="Danfoss",
        vendor_family="ECL Comfort",
        model="ECL Comfort 310",
        model_name="ECL Comfort 310 District Heating Controller",
        device_type="heat_substation_controller",
        description="Weather-compensated district heating/cooling substation "
                     "(\"energy center\") controller for up to 4 circuits; native "
                     "Ethernet/Modbus TCP to the BMS, local M-Bus port (not modeled "
                     "as a separate IP device) for its wired heat meter. No native "
                     "BACnet — BACnet requires a discontinued third-party gateway.",

        oui_prefixes=["00:07:68", "00:0B:2D", "00:19:09", "00:1B:08"],

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
            "distribution": "gaussian",
        },

        supported_protocols=["modbus_tcp"],

        instance_rules=InstanceGenerationRules(
            serial_format="ECL310-{8HEX}",
            station_name_pattern="heat-substation-{seq}",
            vendor_short="DAN",
            model_short="ECL310",
        ),

        firmware_variants=[
            FirmwareVariant(
                version="2.30",
                release_date=date(2022, 1, 1),
                is_latest=True,
                is_default=True,
                cves=[],
            ),
        ],

        modbus_identity={
            "vendor_name": "Danfoss A/S",
            "product_code": "ECL Comfort 310",
            "vendor_url": "https://www.danfoss.com",
            "product_name": "ECL Comfort 310 District Heating Controller",
            "model_name": "ECL Comfort 310",
        },
    ),
]
