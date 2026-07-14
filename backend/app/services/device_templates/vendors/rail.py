# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Rail / train-control device templates for the transportation vertical.

Two families:

- **PTC / Interoperable Train Control (EMP)** — Wabtec I-ETMS and GE
  Transportation ITCS: Back Office Server, Wayside Interface Unit, and the
  locomotive Train Management Computer. These speak EMP (the ITC message
  envelope). Meteorcomm operates the ITCnet radio network but is not the device
  hardware vendor, so these ground to the Wabtec / GE Transportation OUIs.
- **Legacy ATCS codeline (ATCS)** — the signal-supplier heritage lines
  (Alstom, Siemens Mobility, Hitachi Rail) that built ATCS wayside MCPs and base
  communications packages.

OUIs are IEEE-grounded and rewritten by scripts/generate_vendor_ouis.py.
"""

from datetime import date

from app.services.device_templates._types import (
    DeviceTemplate,
    FirmwareVariant,
    InstanceGenerationRules,
)

# Slower comms than plant-floor OT: PTC messaging rides an office/backhaul
# network; ATCS codeline is radio-derived. Timings reflect that.
_EMP_TIMING = {"min_ms": 20.0, "max_ms": 400.0, "mean_ms": 120.0, "std_dev_ms": 80.0, "distribution": "lognormal"}
_LOCO_TIMING = {"min_ms": 100.0, "max_ms": 2000.0, "mean_ms": 500.0, "std_dev_ms": 350.0, "distribution": "lognormal"}
_ATCS_TIMING = {"min_ms": 200.0, "max_ms": 3000.0, "mean_ms": 800.0, "std_dev_ms": 500.0, "distribution": "lognormal"}

_TCP = {"ttl": 64, "window_size": 32768, "mss": 1460, "sack_permitted": True}


TEMPLATES: list[DeviceTemplate] = [
    # ─── Wabtec I-ETMS (PTC / EMP) ──────────────────────────────────────
    DeviceTemplate(
        id="wabtec/i-etms/bos",
        vendor="Wabtec",
        vendor_family="I-ETMS",
        model="I-ETMS Back Office Server",
        model_name="Wabtec I-ETMS Back Office Server",
        device_type="back_office_server",
        description="I-ETMS Positive Train Control back-office server; exchanges EMP messages with wayside units and locomotives",
        oui_prefixes=["00:22:E2"],
        tcp_stack=_TCP,
        response_timing=_EMP_TIMING,
        supported_protocols=["emp"],
        instance_rules=InstanceGenerationRules(
            serial_format="WAB{10NUM}",
            station_name_pattern="ptc-bos-{location}-{seq}",
            vendor_short="WAB",
            model_short="BOS",
        ),
        firmware_variants=[
            FirmwareVariant(version="I-ETMS 5.2", release_date=date(2024, 3, 1), is_latest=True, is_default=True, cves=[]),
            FirmwareVariant(version="I-ETMS 5.0", release_date=date(2022, 5, 15), cves=[]),
        ],
        emp_identity={
            "itc_role": "back_office_server",
            "emp_address": "aar.b.bos",
            "i_etms_version": "5.x",
            "message_version": 4,
        },
        vertical_hints=["transportation", "rail", "ptc"],
    ),
    DeviceTemplate(
        id="wabtec/i-etms/wiu",
        vendor="Wabtec",
        vendor_family="I-ETMS",
        model="I-ETMS Wayside Interface Unit",
        model_name="Wabtec I-ETMS Wayside Interface Unit",
        device_type="wayside_interface_unit",
        description="I-ETMS wayside interface unit; broadcasts signal/switch status as EMP messages to approaching locomotives",
        oui_prefixes=["00:22:E2"],
        tcp_stack=_TCP,
        response_timing=_EMP_TIMING,
        supported_protocols=["emp"],
        instance_rules=InstanceGenerationRules(
            serial_format="WAB{10NUM}",
            station_name_pattern="ptc-wiu-{location}-{seq}",
            vendor_short="WAB",
            model_short="WIU",
        ),
        firmware_variants=[
            FirmwareVariant(version="I-ETMS 5.2", release_date=date(2024, 3, 1), is_latest=True, is_default=True, cves=[]),
        ],
        emp_identity={
            "itc_role": "wayside_interface_unit",
            "emp_address": "aar.w.wiu",
            "i_etms_version": "5.x",
            "message_version": 4,
        },
        vertical_hints=["transportation", "rail", "ptc"],
    ),
    DeviceTemplate(
        id="wabtec/i-etms/tmc",
        vendor="Wabtec",
        vendor_family="I-ETMS",
        model="I-ETMS Train Management Computer",
        model_name="Wabtec I-ETMS Locomotive Train Management Computer",
        device_type="locomotive_computer",
        description="I-ETMS onboard train management computer; enforces movement authorities from EMP messages",
        oui_prefixes=["00:22:E2"],
        tcp_stack=_TCP,
        response_timing=_LOCO_TIMING,
        supported_protocols=["emp"],
        instance_rules=InstanceGenerationRules(
            serial_format="WAB{10NUM}",
            station_name_pattern="ptc-loco-{seq}",
            vendor_short="WAB",
            model_short="TMC",
        ),
        firmware_variants=[
            FirmwareVariant(version="I-ETMS 5.2", release_date=date(2024, 3, 1), is_latest=True, is_default=True, cves=[]),
            FirmwareVariant(version="I-ETMS 4.8", release_date=date(2021, 9, 1), cves=[]),
        ],
        emp_identity={
            "itc_role": "locomotive",
            "emp_address": "aar.l.loco",
            "i_etms_version": "5.x",
            "message_version": 4,
        },
        vertical_hints=["transportation", "rail", "ptc"],
    ),
    # ─── GE Transportation ITCS (PTC / EMP) ─────────────────────────────
    DeviceTemplate(
        id="ge_transportation/itcs/wayside",
        vendor="GE Transportation",
        vendor_family="ITCS",
        model="ITCS Wayside Controller",
        model_name="GE Transportation ITCS Wayside Controller",
        device_type="wayside_interface_unit",
        description="Incremental Train Control System wayside controller; EMP messaging to onboard equipment",
        oui_prefixes=["00:1F:44"],
        tcp_stack=_TCP,
        response_timing=_EMP_TIMING,
        supported_protocols=["emp"],
        instance_rules=InstanceGenerationRules(
            serial_format="GET{10NUM}",
            station_name_pattern="itcs-wayside-{location}-{seq}",
            vendor_short="GET",
            model_short="ITCS",
        ),
        firmware_variants=[
            FirmwareVariant(version="ITCS 3.4", release_date=date(2023, 6, 1), is_latest=True, is_default=True, cves=[]),
        ],
        emp_identity={
            "itc_role": "wayside_interface_unit",
            "emp_address": "aar.w.itcs",
            "system": "ITCS",
            "message_version": 4,
        },
        vertical_hints=["transportation", "rail", "ptc"],
    ),
    # ─── Legacy ATCS codeline (ATCS) ────────────────────────────────────
    DeviceTemplate(
        id="alstom/atcs/mcp",
        vendor="Alstom",
        vendor_family="ATCS",
        model="ATCS Wayside MCP",
        model_name="Alstom ATCS Wayside Message/Control Point",
        device_type="wayside_mcp",
        description="ATCS (AAR Spec 200) wayside message/control point; radio codeline indications and controls",
        oui_prefixes=["00:16:9B"],
        tcp_stack=_TCP,
        response_timing=_ATCS_TIMING,
        supported_protocols=["atcs"],
        instance_rules=InstanceGenerationRules(
            serial_format="ALS{10NUM}",
            station_name_pattern="atcs-mcp-{location}-{seq}",
            vendor_short="ALS",
            model_short="MCP",
        ),
        firmware_variants=[
            FirmwareVariant(version="GEO 6.1", release_date=date(2019, 4, 1), is_latest=True, is_default=True, cves=[]),
        ],
        atcs_identity={
            "atcs_role": "wayside_mcp",
            "atcs_type": 7,
            "mcp_model": "GEO",
            "spec": "AAR Spec 200",
        },
        vertical_hints=["transportation", "rail", "atcs"],
    ),
    DeviceTemplate(
        id="siemens_mobility/atcs/bcp",
        vendor="Siemens Mobility",
        vendor_family="ATCS",
        model="ATCS Base Communications Package",
        model_name="Siemens Mobility ATCS Base Communications Package",
        device_type="atcs_base_station",
        description="ATCS base communications package (BCP); relays codeline between office and wayside MCPs",
        oui_prefixes=["70:38:11"],
        tcp_stack=_TCP,
        response_timing=_ATCS_TIMING,
        supported_protocols=["atcs"],
        instance_rules=InstanceGenerationRules(
            serial_format="SMO{10NUM}",
            station_name_pattern="atcs-bcp-{location}-{seq}",
            vendor_short="SMO",
            model_short="BCP",
        ),
        firmware_variants=[
            FirmwareVariant(version="Safetran 4.2", release_date=date(2018, 8, 1), is_latest=True, is_default=True, cves=[]),
        ],
        atcs_identity={
            "atcs_role": "base_station",
            "atcs_type": 3,
            "mcp_model": "Safetran BCP",
            "spec": "AAR Spec 200",
        },
        vertical_hints=["transportation", "rail", "atcs"],
    ),
    DeviceTemplate(
        id="hitachi_rail/atcs/wayside",
        vendor="Hitachi Rail",
        vendor_family="ATCS",
        model="Wayside Signal Controller",
        model_name="Hitachi Rail Wayside Signal Controller",
        device_type="wayside_signal_controller",
        description="Wayside signal/interlocking controller with ATCS codeline reporting (US&S heritage)",
        oui_prefixes=["4C:30:89"],
        tcp_stack=_TCP,
        response_timing=_ATCS_TIMING,
        supported_protocols=["atcs"],
        instance_rules=InstanceGenerationRules(
            serial_format="HIT{10NUM}",
            station_name_pattern="atcs-wsc-{location}-{seq}",
            vendor_short="HIT",
            model_short="WSC",
        ),
        firmware_variants=[
            FirmwareVariant(version="MicroLok II 6.0", release_date=date(2020, 2, 1), is_latest=True, is_default=True, cves=[]),
        ],
        atcs_identity={
            "atcs_role": "wayside_mcp",
            "atcs_type": 7,
            "mcp_model": "MicroLok II",
            "spec": "AAR Spec 200",
        },
        vertical_hints=["transportation", "rail", "atcs"],
    ),
]
