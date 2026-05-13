# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Apply a SiteIdentity to every device in a scenario definition.

Deterministic, no LLM. Walks the device list once, assigns a name
to each device based on its role + zone using the SiteIdentity's
role_patterns + zone_codes. Per-(zone, role) counters keep numbering
local and predictable.

Also re-populates SNMP sys_name to the new device name so CV-side
identity matches PacketArch-side naming.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from app.services.architecture.site_identity import (
    DEFAULT_ROLE_PATTERNS,
    SiteIdentity,
)


logger = logging.getLogger(__name__)


_VENDOR_ABBR: dict[str, str] = {
    "siemens": "SIE",
    "rockwell": "RKW",
    "schneider": "SCH",
    "abb": "ABB",
    "honeywell": "HWL",
    "emerson": "EMR",
    "ge": "GE",
    "yokogawa": "YOK",
    "sel": "SEL",
    "cisco": "CSC",
    "microsoft": "MS",
    "broadcom": "BRC",
    "kepware": "KEP",
    "paessler": "PSL",
    "aveva": "AVV",
    "lansweeper": "LSW",
    "f5 networks": "F5",
    "fanuc": "FAN",
    "kuka": "KKA",
    "cognex": "COG",
    "sick": "SCK",
    "axis": "AXS",
    "pelco": "PEL",
    "bosch": "BSH",
    "hikvision": "HIK",
    "daktronics": "DAK",
    "q-free": "QFR",
    "kapsch": "KAP",
    "vaisala": "VSL",
    "econolite": "ECN",
    "mir": "MIR",
    "hms": "HMS",
    "distech controls": "DST",
    "tridium": "TRD",
}


_ROLE_ABBR: dict[str, str] = {
    "patch_staging_server": "WSUS",
    "av_management_server": "EPP",
    "jump_server": "JMP",
    "remote_access_gateway": "RAGW",
    "asset_management_server": "ITAM",
    "alarm_event_server": "ALM",
    "batch_server": "BATCH",
    "mes_server": "MES",
    "nms_server": "NMS",
    "dns_ntp_relay": "DNS",
    "email_relay": "SMTP",
    "reverse_proxy": "LB",
    "process_historian": "HIST",
    "local_historian": "HIST-LCL",
    "historian_replica": "HIST-RPL",
    "opc_ua_aggregator": "OPCUA",
    "scada_primary": "SCADA-PRI",
    "scada_standby": "SCADA-SBY",
    "engineering_workstation": "EWS",
    "area_hmi": "HMI",
    "cell_controller": "PLC",
    "dcs_controller": "DCS",
    "batch_controller": "BATCH-CTRL",
    "safety_controller": "SIS",
    "conveyor_controller": "CONV",
    "wcs_controller": "WCS",
    "robot_controller": "ROB",
    "cnc_controller": "CNC",
    "fleet_manager": "FLEET",
    "field_instrument": "XMTR",
    "valve_actuator": "FCV",
    "vfd": "VFD",
    "servo": "SRV",
    "distributed_io": "IO",
    "analyzer": "AIT",
    "flow_meter": "FT",
    "power_meter": "PM",
    "vision_system": "VIS",
    "barcode_scanner": "BCR",
    "agv": "AGV",
    "core_switch": "SW-CORE",
    "cell_switch": "SW",
    "bay_switch": "SW",
    "wan_edge_router": "RTR-WAN",
    "field_rtu": "RTU",
    "aggregator_rtu": "RTAC",
    "protection_relay": "87L",
    "bms_field_controller": "VAV",
    "traffic_controller": "ATC",
    "cabinet_controller": "CAB",
    "cctv_camera": "CAM",
    "ptz_camera": "PTZ",
    "anpr_camera": "LPR",
    "dms_sign": "DMS",
    "toll_rsu": "RSU",
    "toll_lane_controller": "LANE",
    "rwis_station": "RWIS",
}


def _vendor_abbr(vendor: str | None) -> str:
    if not vendor:
        return "DEV"
    return _VENDOR_ABBR.get(vendor.strip().lower(), vendor[:3].upper())


def _role_abbr(role: str | None) -> str:
    if not role:
        return "DEV"
    return _ROLE_ABBR.get(role, role.upper().replace("_", "-")[:6])


def _pattern_for_role(identity: SiteIdentity, role: str | None) -> str:
    if not role:
        return "{site}-DEV-{nnn}"
    if role in identity.role_patterns:
        return identity.role_patterns[role]
    if role in DEFAULT_ROLE_PATTERNS:
        return DEFAULT_ROLE_PATTERNS[role]
    return "{site}-" + _role_abbr(role) + "-{nnn}"


def _zone_code(identity: SiteIdentity, zone_id: str | None) -> str:
    if not zone_id:
        return "GEN"
    code = identity.zone_codes.get(zone_id)
    if code:
        return code
    # last-ditch derivation
    from app.services.architecture.site_identity import _derive_zone_code
    return _derive_zone_code(zone_id)


def _device_role(device: dict[str, Any]) -> str | None:
    # The archetype scenario_generator stores the canonical role_id on
    # `architectural_role`; `role` carries the human-readable role
    # display name (e.g. "Jump Server" vs id "jump_server"). Prefer the
    # canonical id so DEFAULT_ROLE_PATTERNS lookups match.
    return (
        device.get("architectural_role")
        or device.get("role_id")
        or device.get("_role")
        or device.get("role")
    )


def _device_zone(device: dict[str, Any]) -> str | None:
    return device.get("zoneId") or device.get("zone_id") or device.get("zone")


def apply_site_identity(
    *,
    definition: dict[str, Any],
    identity: SiteIdentity,
) -> dict[str, Any]:
    """Rename every device in `definition.devices` using the SiteIdentity.

    Modifies the definition in place AND returns it.

    Side effects per device:
      - device["name"] replaced with the new site-coherent name
      - device["_archetype_name"] preserves the pre-rename name
      - device["vendorFingerprint"]["snmp_identity"]["sys_name"] set
        to match the new name (template placeholders are honored)
    """
    devs = definition.get("devices") or {}
    if isinstance(devs, list):
        devs_iter = list(devs)
    else:
        devs_iter = list(devs.values())

    # Per-(zone, role) counters. Sort by id first so the same scenario
    # always assigns the same counter to the same device.
    devs_iter.sort(key=lambda d: str(d.get("id", "")))

    counters: dict[tuple[str | None, str | None], int] = defaultdict(int)
    used_names: set[str] = set()

    for device in devs_iter:
        role = _device_role(device)
        zone_id = _device_zone(device)
        pattern = _pattern_for_role(identity, role)

        counters[(zone_id, role)] += 1
        n = counters[(zone_id, role)]

        slots = {
            "site": identity.site_code,
            "zone": _zone_code(identity, zone_id),
            "n": n,
            "nn": f"{n:02d}",
            "nnn": f"{n:03d}",
            "vendor": _vendor_abbr(device.get("vendor")),
            "role_abbr": _role_abbr(role),
        }
        try:
            new_name = pattern.format(**slots)
        except (KeyError, IndexError) as e:
            logger.warning(
                "Pattern format failed for role=%s pattern=%r (%s); "
                "falling back to default",
                role, pattern, e,
            )
            new_name = f"{slots['site']}-{slots['role_abbr']}-{slots['nnn']}"

        # If the LLM gave us a colliding pattern, force uniqueness with
        # a numeric suffix bump.
        candidate = new_name
        bump = 1
        while candidate in used_names:
            bump += 1
            candidate = f"{new_name}-{bump}"
        new_name = candidate
        used_names.add(new_name)

        old = device.get("name", "")
        if old and old != new_name:
            device.setdefault("_archetype_name", old)
        device["name"] = new_name

        fp = device.get("vendorFingerprint") or device.get("vendor_fingerprint") or {}
        snmp = fp.get("snmp_identity") if isinstance(fp, dict) else None
        if isinstance(snmp, dict):
            # Honor the {device_name} placeholder convention; otherwise
            # set sys_name directly to the new device name.
            current = snmp.get("sys_name")
            if not current or current == "{device_name}" or current == old:
                snmp["sys_name"] = new_name

    # Persist the identity on the definition so the UI can render it
    # and so admin operations can re-rename idempotently.
    definition["site_identity"] = identity.to_dict()
    return definition
