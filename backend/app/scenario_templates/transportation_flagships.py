# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Flagship roadway transportation demo scenarios.

Large, curated scenarios built by small factories (one cabinet, one corridor
hub) instead of hand-typed device lists, so a 150-device deployment stays
readable and every device is explicitly named, pinned and paired. Plan:
``tasks/transportation-flagships-plan.md``.

Conventions used by every flagship:

- ``naming: "curated"`` — authored asset names survive site naming (the
  scenario's site code is prefixed so two scenarios never share hostnames).
- ``honor_flow_config: True`` — flow specs may carry engine options.
- Flow ``pairing`` is explicit: ``fan_out`` for central systems that poll
  every field device, ``same_group`` for traffic that stays inside one
  cabinet or gantry.
- Explicit conduits and ``cell_isolation: conduit_gated``.
- Who polls a signal controller decides what NTCIP is on the wire: the ATMS
  reads 1202 status every second, the historian collects volume/occupancy,
  the engineering workstation reads configuration, and the NMS reads MIB-II.
"""

from __future__ import annotations

from typing import Any

from app.services.device_templates import DEVICE_TEMPLATES

# Fingerprint template ids used by the flagships.
FP = {
    # Central / TMC
    "atms_centracs": "econolite/centracs/atms-server",
    "historian": "aveva/pi-system/pi-server-2018",
    "ews": "microsoft/windows-workstation/ot-engineering-workstation",
    "nms": "paessler/network-monitor/prtg-24",
    "vms": "genetec/security-center/vms-server",
    "core_switch": "cisco/ie9320/24t4x",
    # IDMZ
    "jump": "microsoft/windows-server/jump-server-2019",
    "jump_vulnerable": "microsoft/windows-server/jump-server-2019-printnightmare",
    "remote_gateway": "hms/ewon/cosy-131",
    "reverse_proxy": "f5/big-ip/ltm-i2800",
    # Field
    "hub_switch": "cisco/ie3500/8t3s",
    "cabinet_switch": "siemens/ruggedcom/rs900",
    "atc_cobalt": "econolite/cobalt/atc",
    "atc_maxtime": "qfree/intelight-2070lx/maxtime",
    "atc_mccain": "mccain/atc-ex2/omni-ex",
    "atc_m60": "siemens-its/m60/atc",
    "radar_detector": "wavetronix/smartsensor/advance",
    "camera": "axis/camera/p1455-le",
    "ptz_camera": "bosch/ptz-camera/mic-ip-7100i",
    "cell_cradlepoint": "cradlepoint/ibr900/router",
    "cell_sierra": "sierra/airlink-rv55/router",
    # Tunnel plant (F2)
    "tunnel_scada": "siemens/wincc/professional",
    "tunnel_hmi": "siemens/wincc/unified",
    "vent_plc": "siemens/s7-1500/cpu-1516-3",
    "vent_safety_plc": "siemens/s7-1500/cpu-1516f-3",
    "jet_fan_drive": "siemens/sinamics/g120",
    "air_quality_io": "siemens/io/et200sp-im155-6",
    "plant_switch": "siemens/scalance/xm-400",
    "drainage_plc": "rockwell/controllogix/l83e",
    "pump_drive": "rockwell/powerflex/525",
    "bms_server": "siemens/desigo/cc",
    "lighting_controller": "siemens/desigo/dxr2",
    "substation_hvac": "siemens/climatix/c600",
    "fire_panel": "notifier/nfs2/3030",
    "ups": "schneider/galaxy/vm",
    "lane_signal": "daktronics/vanguard/vf-2020",
    "portal_dms": "daktronics/vanguard/vx-2420",
    "rwis": "vaisala/rws/200",
    "incident_radar": "wavetronix/smartsensor/hd",
    "thermal_detector": "flir/trafione/sensor",
    "bore_camera": "axis/camera/p1448-le",
    "jump_patched": "microsoft/windows-server/jump-server-2019",
    # Freeway (F3)
    "mainline_radar": "wavetronix/smartsensor/hd",
    "ramp_meter": "mccain/2070/atc",
    "travel_time_dms": "daktronics/vanguard/vx-2420",
    "freeway_core_switch": "cisco/ie9320/24p4x",
    # Tolling (F4)
    "toll_zone_controller": "kapsch/tzc/toll-zone-controller",
    "toll_reader": "kapsch/janus/mpr2.4",
    "alpr_camera": "genetec/autovu/sharpv",
    "classifier": "sick/tic502/master",
    "toll_host": "kapsch/facility-host/moms",
    "pricing_dms": "daktronics/vanguard/vx-2420",
}



def device(name: str, dtype: str, zone: str, fp_key: str, protocols: list[str], *,
           group: str | None = None, firmware: str | None = None, role: str | None = None) -> dict[str, Any]:
    """One explicitly named device spec.

    The vendor is read from the fingerprint record, so it always matches the
    OUI the MAC is drawn from; a firmware pin must name a real variant.
    """
    template = DEVICE_TEMPLATES[FP[fp_key]]
    if firmware and firmware not in {v.version for v in template.firmware_variants}:
        raise ValueError(f"{name}: {FP[fp_key]} has no firmware variant {firmware!r}")
    spec: dict[str, Any] = {
        "type": dtype,
        "count": 1,
        "zone": zone,
        "name": name,
        "vendor": template.vendor,
        "fingerprint_id": FP[fp_key],
        "protocols": protocols,
    }
    if group:
        spec["group"] = group
    if firmware:
        spec["firmware_version"] = firmware
    if role:
        spec["role"] = role
    return spec


def flow(protocol: str, sources: list[str], targets: list[str], interval_ms: int, *,
         source_zones: list[str] | None = None, target_zones: list[str] | None = None,
         pairing: str = "fan_out", jitter_ms: int | None = None,
         config: dict[str, Any] | None = None) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "protocol": protocol,
        "pattern": "poll",
        "source_types": sources,
        "target_types": targets,
        "interval_ms": interval_ms,
        "pairing": pairing,
        "jitter_ms": jitter_ms if jitter_ms is not None else max(20, interval_ms // 20),
        "jitter_type": "gaussian",
    }
    if source_zones:
        spec["source_zones"] = source_zones
    if target_zones:
        spec["target_zones"] = target_zones
    if config:
        spec["config"] = config
    return spec


def conduit(src: str, dst: str, protocols: list[str], description: str) -> dict[str, Any]:
    return {
        "id": f"{src}__{dst}",
        "name": f"{src} ↔ {dst}",
        "source_zone": src,
        "target_zone": dst,
        "direction": "bidirectional",
        "allowed_protocols": protocols,
        "security_level": "critical",
        "description": description,
    }


def _summary(devices: list[dict[str, Any]], zones: list[dict[str, Any]]) -> str:
    return f"{sum(d.get('count', 1) for d in devices)} devices across {len(zones)} zones."


# ===========================================================================
# F1 — Metro Arterial Signal System
# ===========================================================================

# (zone id, display name, subnet offset, corridor, cross streets, ATC model,
#  cellular router model)
_F1_HUBS = [
    ("hub_cbd", "Downtown / CBD Hub", 10, "Main_St",
     ["1st_Ave", "2nd_Ave", "3rd_Ave", "4th_Ave", "5th_Ave", "6th_Ave"],
     "atc_cobalt", "cell_cradlepoint"),
    ("hub_north", "North Corridor Hub", 11, "Broadway",
     ["Elm_St", "Oak_St", "Pine_St", "Cedar_St", "Maple_St", "Birch_St"],
     "atc_mccain", "cell_cradlepoint"),
    ("hub_south", "South Corridor Hub", 12, "Lincoln_Ave",
     ["10th_St", "11th_St", "12th_St", "13th_St", "14th_St", "15th_St"],
     "atc_m60", "cell_sierra"),
    ("hub_east", "East Corridor Hub", 13, "Airport_Blvd",
     ["Harbor_Dr", "Terminal_Rd", "Cargo_Way", "Freight_Ln", "Runway_Rd", "Hangar_Dr"],
     "atc_maxtime", "cell_cradlepoint"),
    ("hub_west", "West Corridor Hub", 14, "University_Ave",
     ["College_St", "Campus_Dr", "Stadium_Way", "Library_Ln", "Science_Dr", "Union_St"],
     "atc_cobalt", "cell_sierra"),
]

# Deliberately vulnerable firmware on a few downtown controllers
# (Econolite EOS < 3.2.23: CVE-2023-0451/0452, ICSA-23-026-02).
_F1_VULNERABLE_COBALT = {("hub_cbd", 1), ("hub_cbd", 4), ("hub_west", 2)}
_F1_VULNERABLE_CAMERAS = {("hub_cbd", 3), ("hub_east", 1)}
_ATC_PROTOCOLS = ["snmp"]


def _f1_cabinet(hub: str, corridor: str, cross: str, index: int, atc: str,
                cell: str) -> list[dict[str, Any]]:
    """One signalized intersection cabinet (all devices share its group).

    Not modelled yet, on purpose: the conflict monitor (EDI's MMU2-16LEip
    speaks EDI's ECcom protocol, not SNMP, and EDI holds no IEEE OUI) and
    video detection (Iteris / Autoscope publish RTSP/ONVIF, no SNMP). They
    land with the engines that can speak for them (plan, Wave 3).
    """
    group = f"{hub}_cab{index:02d}"
    short = f"{corridor.split('_')[0]}_{cross.split('_')[0]}"
    # Pin every Cobalt and camera so exactly the demo devices are vulnerable
    # (unpinned, the catalog's population mix would make ~40% of them so).
    firmware = None
    if atc == "atc_cobalt":
        firmware = "3.2.20" if (hub, index) in _F1_VULNERABLE_COBALT else "3.2.23"
    specs = [
        device(f"{short}_ATC", "traffic_controller", hub, atc, _ATC_PROTOCOLS, group=group, firmware=firmware),
        device(f"{short}_Radar", "radar_detector", hub, "radar_detector", ["snmp"], group=group),
        device(f"{short}_CabSW", "network_switch", hub, "cabinet_switch", ["snmp", "syslog"], group=group),
    ]
    if index % 2 == 1:
        # Two cameras still run AXIS OS 10.6.0 (CVE-2021-31986).
        cam_fw = "10.6.0" if (hub, index) in _F1_VULNERABLE_CAMERAS else "11.6.94"
        specs.append(device(f"{short}_CCTV", "camera", hub, "camera", ["snmp", "https"], group=group,
                            firmware=cam_fw))
    if index == 1:
        specs.append(device(f"{short}_PTZ", "ptz_camera", hub, "ptz_camera", ["snmp", "https"], group=group))
    if index == 6:
        # The far end of each corridor is not on fiber: cellular backhaul.
        specs.append(device(f"{short}_Cell", "cellular_router", hub, cell, ["snmp", "https", "syslog"], group=group))
    return specs


def _metro_arterial() -> dict[str, Any]:
    zones = [
        {"id": "idmz", "name": "Industrial DMZ", "level": 3.5, "subnet_offset": 0, "vlan": 100,
         "security_level": "critical"},
        {"id": "tmc", "name": "Traffic Management Center", "level": 3, "subnet_offset": 1, "vlan": 110,
         "security_level": "critical"},
        {"id": "backup_tmc", "name": "Backup TMC (Emergency Ops)", "level": 3, "subnet_offset": 2,
         "vlan": 120, "security_level": "critical"},
    ]
    devices: list[dict[str, Any]] = [
        device("TMC_ATMS_Primary", "atms_server", "tmc", "atms_centracs", ["snmp", "https"]),
        device("TMC_Historian", "historian", "tmc", "historian", ["snmp", "https"]),
        device("TMC_Signal_Eng_WS", "engineering_workstation", "tmc", "ews", ["snmp", "rdp", "https"]),
        device("TMC_NMS", "nms", "tmc", "nms", ["snmp", "https", "syslog"]),
        device("TMC_Video_Mgmt", "vms_server", "tmc", "vms", ["snmp", "https"]),
        device("TMC_Core_SW", "network_switch", "tmc", "core_switch", ["snmp", "syslog"]),
        device("EOC_ATMS_Standby", "atms_server", "backup_tmc", "atms_centracs", ["snmp", "https"]),
        device("EOC_Core_SW", "network_switch", "backup_tmc", "core_switch", ["snmp", "syslog"]),
        device("DMZ_Jump_Host", "jump_server", "idmz", "jump_vulnerable", ["snmp", "rdp", "https"]),
        device("DMZ_Vendor_Remote", "remote_gateway", "idmz", "remote_gateway", ["snmp"]),
        device("DMZ_Traveler_Info_Proxy", "reverse_proxy", "idmz", "reverse_proxy", ["snmp", "https"]),
    ]
    hub_ids = []
    for hub, display, offset, corridor, crosses, atc, cell in _F1_HUBS:
        hub_ids.append(hub)
        zones.append({"id": hub, "name": display, "level": 2, "subnet_offset": offset,
                      "vlan": 200 + 10 * (offset - 9), "security_level": "high"})
        devices.append(device(f"{corridor.split('_')[0]}_Hub_SW", "network_switch", hub, "hub_switch", ["snmp", "syslog"]))
        for i, cross in enumerate(crosses, start=1):
            devices.extend(_f1_cabinet(hub, corridor, cross, i, atc, cell))

    field_mgmt = ["network_switch", "radar_detector", "camera", "ptz_camera", "cellular_router"]
    flows = [
        # NTCIP 1202: live status every second from the ATMS; the EOC standby
        # keeps a slower watch; historian collects 60 s volume/occupancy;
        # the signal engineer's workstation pulls configuration.
        flow("snmp", ["atms_server"], ["traffic_controller"], 1000,
             source_zones=["tmc"], target_zones=hub_ids),
        flow("snmp", ["atms_server"], ["traffic_controller"], 30000,
             source_zones=["backup_tmc"], target_zones=hub_ids),
        flow("snmp", ["historian"], ["traffic_controller"], 60000, target_zones=hub_ids),
        flow("snmp", ["engineering_workstation"], ["traffic_controller"], 600000, target_zones=hub_ids),
        # Detection stations: the ATMS collects each 30 s NTCIP 1209 sample.
        flow("snmp", ["atms_server"], ["radar_detector"], 30000,
             source_zones=["tmc"], target_zones=hub_ids),
        # Network operations: MIB-II health of every field asset; switches
        # and cellular routers send syslog to the NMS.
        flow("snmp", ["nms"], field_mgmt, 60000),
        flow("syslog", ["network_switch", "cellular_router"], ["nms"], 120000),
        # Video management sessions to every camera.
        flow("https", ["vms_server"], ["camera", "ptz_camera"], 10000, target_zones=hub_ids),
        # Cellular routers report to the ATMS over the carrier link.
        flow("https", ["cellular_router"], ["atms_server"], 120000, target_zones=["tmc"]),
        # Center plumbing: EOC replication, traveler-info feed, admin access.
        flow("https", ["atms_server"], ["atms_server"], 60000,
             source_zones=["backup_tmc"], target_zones=["tmc"]),
        flow("https", ["reverse_proxy"], ["atms_server"], 30000, target_zones=["tmc"]),
        flow("rdp", ["jump_server"], ["engineering_workstation"], 300000),
        flow("https", ["jump_server"], ["atms_server"], 300000, target_zones=["tmc"]),
        flow("snmp", ["nms"], ["remote_gateway", "reverse_proxy", "jump_server"], 60000),
    ]

    conduits = [
        conduit("tmc", hub, ["snmp", "https", "syslog"], "ATMS NTCIP polling, VMS video sessions, NMS "
                "monitoring and syslog, cellular router check-in") for hub in hub_ids
    ] + [
        conduit("backup_tmc", hub, ["snmp"], "EOC standby ATMS NTCIP watch") for hub in hub_ids
    ] + [
        conduit("tmc", "backup_tmc", ["https", "snmp"], "ATMS database replication; NMS"),
        conduit("idmz", "tmc", ["rdp", "https", "snmp"], "Jump host RDP to the signal engineering "
                "workstation; traveler-info proxy feed; NMS"),
    ]

    return {
        "name": "Metro Arterial Signal System",
        "description": (
            "City traffic management center running 30 signalized intersections on five corridors "
            "(Downtown, Broadway, Lincoln Ave, Airport Blvd, University Ave). Mixed ATC fleet "
            "(Econolite Cobalt, McCain ATC eX2, Siemens M60, Q-Free Intelight MAXTIME) with radar "
            "detection, RUGGEDCOM cabinet switches, CCTV/PTZ and cellular backhaul at "
            "corridor ends; primary TMC plus an emergency-ops standby ATMS; IDMZ with jump host, "
            "vendor remote access and a traveler-information proxy. Real NTCIP 1201/1202 on the "
            "wire. " + _summary(devices, zones)
        ),
        "vertical": "transportation",
        "naming": "curated",
        "honor_flow_config": True,
        "phase_preset": "standard",
        "cell_isolation": {"mode": "conduit_gated"},
        "zones": zones,
        "conduits": conduits,
        "devices": devices,
        "flows": flows,
        "cloud_services": [
            {"provider": "talk2m", "region": "us-west", "device_types": ["remote_gateway"],
             "heartbeat_interval_ms": 30000},
        ],
        "recommended_attack_playbooks": [
            {"playbook_id": "its_signal_disruption", "relevance": "high",
             "rationale": "Thirty NTCIP controllers answer SNMP SETs; a pattern or flash change is visible on the wire"},
            {"playbook_id": "network_recon", "relevance": "high",
             "rationale": "Field hubs expose SNMP on every cabinet asset to the TMC"},
            {"playbook_id": "volt_typhoon_like", "relevance": "medium",
             "rationale": "Cellular routers at corridor ends are internet-reachable edge devices"},
        ],
        "total_duration_ms": 3600000,
    }


# ===========================================================================
# F2 — Twin-Bore Road Tunnel Control
# ===========================================================================

_BORES = [("nb", "Northbound"), ("sb", "Southbound")]


def _road_tunnel() -> dict[str, Any]:
    zones = [
        {"id": "idmz", "name": "Industrial DMZ", "level": 3.5, "subnet_offset": 0, "vlan": 100,
         "security_level": "critical"},
        {"id": "control_room", "name": "Tunnel Control Room", "level": 3, "subnet_offset": 1,
         "vlan": 110, "security_level": "critical"},
        {"id": "ventilation", "name": "Ventilation Plant", "level": 2, "subnet_offset": 10,
         "vlan": 210, "security_level": "critical"},
        {"id": "drainage", "name": "Drainage Pump Station", "level": 2, "subnet_offset": 11,
         "vlan": 220, "security_level": "high"},
        {"id": "power_lighting", "name": "Power, Lighting and Life Safety", "level": 2,
         "subnet_offset": 12, "vlan": 230, "security_level": "critical"},
        {"id": "traffic_control", "name": "Portal Traffic Control", "level": 2, "subnet_offset": 13,
         "vlan": 240, "security_level": "high"},
        {"id": "cctv", "name": "Bore CCTV Network", "level": 2, "subnet_offset": 14, "vlan": 250,
         "security_level": "medium"},
    ]
    devices: list[dict[str, Any]] = [
        device("DMZ_Jump_Host", "jump_server", "idmz", "jump_patched", ["snmp", "rdp", "https"]),
        device("DMZ_Vendor_Remote", "remote_gateway", "idmz", "remote_gateway", ["snmp"]),
        device("TCR_SCADA_A", "scada", "control_room", "tunnel_scada",
               ["s7comm", "opc_ua", "modbus_tcp"]),
        device("TCR_SCADA_B", "scada", "control_room", "tunnel_scada",
               ["s7comm", "opc_ua", "modbus_tcp"]),
        device("TCR_Operator_HMI_1", "hmi", "control_room", "tunnel_hmi", ["s7comm", "opc_ua"]),
        device("TCR_Operator_HMI_2", "hmi", "control_room", "tunnel_hmi", ["s7comm", "opc_ua"]),
        device("TCR_Traffic_ATMS", "atms_server", "control_room", "atms_centracs", ["snmp", "https"]),
        device("TCR_Historian", "historian", "control_room", "historian", ["opc_ua", "snmp", "https"]),
        device("TCR_Eng_WS", "engineering_workstation", "control_room", "ews",
               ["s7comm", "ethernet_ip", "rdp", "snmp"]),
        device("TCR_BMS_Server", "bms_server", "control_room", "bms_server", ["bacnet"]),
        device("TCR_NMS", "nms", "control_room", "nms", ["snmp", "https", "syslog"]),
        device("TCR_Video_Mgmt", "vms_server", "control_room", "vms", ["snmp", "https"]),
        device("TCR_Core_SW", "network_switch", "control_room", "core_switch", ["snmp", "syslog"]),
        device("Vent_Plant_SW", "network_switch", "ventilation", "plant_switch", ["snmp", "syslog"]),
        device("Vent_Fire_Mode_SPLC", "safety_plc", "ventilation", "vent_safety_plc",
               ["s7comm", "profinet"]),
        device("Drain_Plant_SW", "network_switch", "drainage", "hub_switch", ["snmp", "syslog"]),
        device("Drain_Sump_PLC", "plc", "drainage", "drainage_plc", ["ethernet_ip", "modbus_tcp"],
               group="sump"),
        device("Power_Plant_SW", "network_switch", "power_lighting", "plant_switch", ["snmp", "syslog"]),
        device("Portal_Traffic_SW", "network_switch", "traffic_control", "hub_switch", ["snmp", "syslog"]),
        device("CCTV_Agg_SW", "network_switch", "cctv", "hub_switch", ["snmp", "syslog"]),
    ]
    for i in range(1, 4):
        devices.append(device(f"Drain_Pump_{i:02d}_VFD", "drive", "drainage", "pump_drive",
                              ["ethernet_ip"], group="sump"))
    for i in range(1, 3):
        devices.append(device(f"Power_UPS_{i:02d}", "ups", "power_lighting", "ups", ["modbus_tcp", "snmp"]))
        devices.append(device(f"Substation_HVAC_{i:02d}", "building_controller", "power_lighting",
                              "substation_hvac", ["bacnet", "snmp"]))
    for bore, label in _BORES:
        b = bore.upper()
        group = f"vent_{bore}"
        devices.append(device(f"Vent_{b}_PLC", "plc", "ventilation", "vent_plc", ["s7comm", "profinet"],
                              group=group))
        for i in range(1, 7):
            devices.append(device(f"Vent_{b}_JetFan_{i:02d}_VFD", "drive", "ventilation", "jet_fan_drive",
                                  ["profinet"], group=group))
        for i in range(1, 4):
            devices.append(device(f"Vent_{b}_AirQuality_IO_{i:02d}", "io_module", "ventilation",
                                  "air_quality_io", ["profinet"], group=group))
        for i in range(1, 3):
            devices.append(device(f"Light_{b}_Zone_{i:02d}", "room_controller", "power_lighting",
                                  "lighting_controller", ["bacnet"]))
        devices.append(device(f"Fire_{b}_Panel", "fire_panel", "power_lighting", "fire_panel", ["bacnet"]))
        # Lane-use control signals over each lane at the portal and mid-bore.
        for i in range(1, 5):
            devices.append(device(f"Lane_{b}_LCS_{i:02d}", "dms", "traffic_control", "lane_signal", ["snmp"]))
        devices.append(device(f"Portal_{b}_DMS", "dms", "traffic_control", "portal_dms", ["snmp"]))
        devices.append(device(f"Portal_{b}_Closure_ATC", "traffic_controller", "traffic_control",
                              "atc_cobalt", ["snmp"]))
        devices.append(device(f"Portal_{b}_RWIS", "weather_station", "traffic_control", "rwis", ["snmp"]))
        for i in range(1, 3):
            devices.append(device(f"Bore_{b}_Incident_Radar_{i:02d}", "radar_detector", "traffic_control",
                                  "incident_radar", ["snmp"]))
        devices.append(device(f"Bore_{b}_Thermal_Det", "thermal_sensor", "traffic_control",
                              "thermal_detector", ["snmp"]))
        for i in range(1, 7):
            devices.append(device(f"Bore_{b}_CCTV_{i:02d}", "camera", "cctv", "bore_camera", ["snmp", "https"]))

    plant_switches = ["network_switch"]
    flows = [
        # SCADA and operator HMIs read the ventilation PLCs (CO, opacity, fan
        # speeds come from the road_tunnel process model).
        flow("s7comm", ["scada"], ["plc", "safety_plc"], 1000, target_zones=["ventilation"]),
        flow("s7comm", ["hmi"], ["plc"], 1000, target_zones=["ventilation"]),
        # Each bore's PLC runs its own jet fans and air-quality I/O.
        flow("profinet", ["plc"], ["drive", "io_module"], 32, source_zones=["ventilation"],
             target_zones=["ventilation"], pairing="same_group"),
        flow("profinet", ["safety_plc"], ["plc"], 100, source_zones=["ventilation"],
             target_zones=["ventilation"]),
        # Drainage: WinCC has no CIP driver, so SCADA reads the sump PLC over
        # Modbus TCP; the PLC commands its pumps over CIP.
        flow("modbus_tcp", ["scada"], ["plc"], 1000, target_zones=["drainage"]),
        flow("ethernet_ip", ["plc"], ["drive"], 100, source_zones=["drainage"],
             target_zones=["drainage"], pairing="same_group"),
        # Power: UPS status to SCADA.
        flow("modbus_tcp", ["scada"], ["ups"], 5000, target_zones=["power_lighting"]),
        # Building automation: lighting, substation HVAC, fire panels.
        flow("bacnet", ["bms_server"], ["room_controller", "building_controller", "fire_panel"], 10000),
        # Portal traffic control over NTCIP from the traffic ATMS (WinCC has
        # no NTCIP driver): lane signals, DMS, closure signals, RWIS, radar.
        flow("snmp", ["atms_server"], ["dms", "traffic_controller"], 1000, target_zones=["traffic_control"]),
        flow("snmp", ["atms_server"], ["weather_station", "radar_detector"], 30000,
             target_zones=["traffic_control"]),
        flow("snmp", ["historian"], ["traffic_controller", "weather_station"], 60000,
             target_zones=["traffic_control"]),
        # Historian collects from both SCADA servers.
        flow("opc_ua", ["historian"], ["scada"], 5000),
        # Video.
        flow("https", ["vms_server"], ["camera"], 10000, target_zones=["cctv"]),
        # Engineering and network operations.
        flow("s7comm", ["engineering_workstation"], ["plc", "safety_plc"], 600000, target_zones=["ventilation"]),
        flow("ethernet_ip", ["engineering_workstation"], ["plc"], 600000, target_zones=["drainage"]),
        flow("snmp", ["nms"], plant_switches + ["camera", "ups", "building_controller", "thermal_sensor"],
             60000),
        flow("snmp", ["nms"], ["remote_gateway", "jump_server"], 60000),
        flow("syslog", ["network_switch"], ["nms"], 120000),
        flow("rdp", ["jump_server"], ["engineering_workstation"], 300000),
    ]

    conduits = [
        conduit("control_room", "ventilation", ["s7comm", "snmp", "syslog"], "SCADA/HMI S7 reads, engineering, NMS"),
        conduit("control_room", "drainage", ["modbus_tcp", "ethernet_ip", "snmp", "syslog"],
                "SCADA Modbus reads, engineering CIP, NMS"),
        conduit("control_room", "power_lighting", ["modbus_tcp", "bacnet", "snmp", "syslog"],
                "UPS Modbus, BMS BACnet, NMS"),
        conduit("control_room", "traffic_control", ["snmp", "syslog"], "ATMS NTCIP sign/signal/RWIS control; NMS"),
        conduit("control_room", "cctv", ["https", "snmp", "syslog"], "Video management; NMS"),
        conduit("idmz", "control_room", ["rdp", "snmp"], "Jump host RDP to engineering; NMS"),
    ]

    return {
        "name": "Twin-Bore Road Tunnel Control",
        "description": (
            "Highway twin-bore road tunnel. Siemens S7-1500 ventilation PLCs run SINAMICS jet fans "
            "on CO and visibility from ET200SP air-quality I/O, with a fail-safe S7-1500F fire-mode "
            "controller; a ControlLogix sump PLC cycles PowerFlex drainage pumps; WinCC SCADA (duty/"
            "standby) and operator HMIs; a Centracs traffic ATMS; Desigo CC over BACnet for lighting, substation HVAC and "
            "Notifier fire panels; UPS over Modbus; NTCIP lane-use signals, portal DMS, closure "
            "signals and RWIS at both portals under the ATMS; radar and thermal incident detection; bore CCTV. "
            "Register values follow a tunnel process model (traffic drives CO, fans respond; the "
            "sump cycles its duty pump). " + _summary(devices, zones)
        ),
        "vertical": "transportation",
        "process_model": "road_tunnel",
        "naming": "curated",
        "honor_flow_config": True,
        "phase_preset": "standard",
        "cell_isolation": {"mode": "conduit_gated"},
        "zones": zones,
        "conduits": conduits,
        "devices": devices,
        "flows": flows,
        "cloud_services": [
            {"provider": "talk2m", "region": "us-west", "device_types": ["remote_gateway"],
             "heartbeat_interval_ms": 30000},
        ],
        "recommended_attack_playbooks": [
            {"playbook_id": "pipedream_like", "relevance": "high",
             "rationale": "Siemens S7-1500 and ControlLogix PLCs run ventilation and drainage"},
            {"playbook_id": "network_recon", "relevance": "high",
             "rationale": "Flat plant cells behind one control-room conduit each"},
            {"playbook_id": "insider_threat", "relevance": "medium",
             "rationale": "The engineering workstation holds S7 and CIP write access to every PLC"},
        ],
        "total_duration_ms": 3600000,
    }


# ===========================================================================
# F3 — Freeway Management Corridor
# ===========================================================================

# (zone id, display name, subnet offset, mileposts, has RWIS)
_F3_HUBS = [
    ("hub_mp00", "Hub MP 0-4", 10, (0, 4), True),
    ("hub_mp04", "Hub MP 4-8", 11, (4, 8), False),
    ("hub_mp08", "Hub MP 8-12", 12, (8, 12), True),
    ("hub_mp12", "Hub MP 12-16", 13, (12, 16), False),
    ("hub_mp16", "Hub MP 16-20", 14, (16, 20), True),
]
_F3_STATIONS_PER_HUB = 8
_F3_CELLULAR_HUB = "hub_mp16"        # past the end of the fiber plant
_F3_VULNERABLE_CAMERA_HUB = "hub_mp08"


def _f3_hub(hub: str, start_mp: int, end_mp: int, rwis: bool) -> list[dict[str, Any]]:
    specs = [device(f"MP{start_mp:02d}_Hub_SW", "network_switch", hub, "hub_switch", ["snmp", "syslog"])]
    span = (end_mp - start_mp) / _F3_STATIONS_PER_HUB
    for i in range(_F3_STATIONS_PER_HUB):
        mp = start_mp + span * (i + 0.5)
        tag = f"MP{mp:04.1f}".replace(".", "_")
        group = f"{hub}_ds{i + 1:02d}"
        specs += [
            device(f"{tag}_Detector", "radar_detector", hub, "mainline_radar", ["snmp"], group=group),
            device(f"{tag}_CabSW", "network_switch", hub, "cabinet_switch", ["snmp", "syslog"], group=group),
        ]
        if hub == _F3_CELLULAR_HUB and i >= _F3_STATIONS_PER_HUB - 2:
            specs.append(device(f"{tag}_Cell", "cellular_router", hub, "cell_sierra", ["snmp", "https", "syslog"],
                                group=group))
    for j, mp in enumerate((start_mp + 1, start_mp + 3), start=1):
        group = f"{hub}_rm{j}"
        specs += [
            device(f"MP{mp:02d}_Ramp_Meter", "ramp_meter", hub, "ramp_meter", ["snmp"], group=group),
            device(f"MP{mp:02d}_Ramp_CabSW", "network_switch", hub, "cabinet_switch", ["snmp", "syslog"], group=group),
        ]
    specs.append(device(f"MP{start_mp + 2:02d}_TravelTime_DMS", "dms", hub, "travel_time_dms", ["snmp"]))
    specs += [device(f"MP{start_mp + k:02d}_PTZ", "ptz_camera", hub, "ptz_camera", ["snmp", "https"])
              for k in (1, 3)]
    cam_fw = "10.6.0" if hub == _F3_VULNERABLE_CAMERA_HUB else "11.6.94"
    specs.append(device(f"MP{start_mp + 2:02d}_CCTV", "camera", hub, "camera", ["snmp", "https"],
                        firmware=cam_fw))
    if rwis:
        specs.append(device(f"MP{start_mp + 2:02d}_RWIS", "weather_station", hub, "rwis", ["snmp"]))
    return specs


def _freeway_corridor() -> dict[str, Any]:
    zones = [
        {"id": "idmz", "name": "Industrial DMZ", "level": 3.5, "subnet_offset": 0, "vlan": 100,
         "security_level": "critical"},
        {"id": "tmc", "name": "Freeway Traffic Management Center", "level": 3, "subnet_offset": 1,
         "vlan": 110, "security_level": "critical"},
    ]
    devices: list[dict[str, Any]] = [
        device("TMC_ATMS_Primary", "atms_server", "tmc", "atms_centracs", ["snmp", "https"]),
        device("TMC_ATMS_Standby", "atms_server", "tmc", "atms_centracs", ["snmp", "https"]),
        device("TMC_Historian", "historian", "tmc", "historian", ["snmp", "https"]),
        device("TMC_Ops_Eng_WS", "engineering_workstation", "tmc", "ews", ["snmp", "rdp", "https"]),
        device("TMC_NMS", "nms", "tmc", "nms", ["snmp", "https", "syslog"]),
        device("TMC_Video_Mgmt", "vms_server", "tmc", "vms", ["snmp", "https"]),
        # The core still runs IOS XE 17.9.3: web UI exposed (CVE-2023-20198).
        device("TMC_Core_SW", "network_switch", "tmc", "freeway_core_switch", ["snmp", "syslog"],
               firmware="17.9.3"),
        device("DMZ_Jump_Host", "jump_server", "idmz", "jump_patched", ["snmp", "rdp", "https"]),
        device("DMZ_Traveler_Info_Proxy", "reverse_proxy", "idmz", "reverse_proxy", ["snmp", "https"]),
        device("DMZ_Vendor_Remote", "remote_gateway", "idmz", "remote_gateway", ["snmp"]),
    ]
    hub_ids = []
    for hub, display, offset, (start_mp, end_mp), rwis in _F3_HUBS:
        hub_ids.append(hub)
        zones.append({"id": hub, "name": display, "level": 2, "subnet_offset": offset,
                      "vlan": 200 + 10 * (offset - 9), "security_level": "high"})
        devices.extend(_f3_hub(hub, start_mp, end_mp, rwis))

    field_infra = ["network_switch", "camera", "ptz_camera", "cellular_router"]
    flows = [
        # NTCIP 1209: the ATMS collects every 30 s sample; the standby and
        # the historian keep their own copies.
        flow("snmp", ["atms_server"], ["radar_detector"], 30000, target_zones=hub_ids),
        flow("snmp", ["historian"], ["radar_detector"], 60000, target_zones=hub_ids),
        # NTCIP 1203 travel-time signs, 1204 RWIS, ramp meters (MIB-II only
        # until NTCIP 1207 is modelled).
        flow("snmp", ["atms_server"], ["dms"], 30000, target_zones=hub_ids),
        flow("snmp", ["atms_server"], ["weather_station"], 300000, target_zones=hub_ids),
        flow("snmp", ["atms_server"], ["ramp_meter"], 30000, target_zones=hub_ids),
        flow("snmp", ["engineering_workstation"], ["ramp_meter", "dms"], 600000, target_zones=hub_ids),
        # Video, network operations, cellular check-in.
        flow("https", ["vms_server"], ["camera", "ptz_camera"], 10000, target_zones=hub_ids),
        flow("snmp", ["nms"], field_infra, 60000),
        flow("syslog", ["network_switch", "cellular_router"], ["nms"], 120000),
        flow("https", ["cellular_router"], ["atms_server"], 120000, target_zones=["tmc"]),
        # Center plumbing.
        flow("https", ["reverse_proxy"], ["atms_server"], 30000, target_zones=["tmc"]),
        flow("rdp", ["jump_server"], ["engineering_workstation"], 300000),
        flow("snmp", ["nms"], ["remote_gateway", "reverse_proxy", "jump_server"], 60000),
    ]
    conduits = [
        conduit("tmc", hub, ["snmp", "https", "syslog"], "ATMS NTCIP collection, video, NMS and syslog, "
                "cellular check-in")
        for hub in hub_ids
    ] + [
        conduit("idmz", "tmc", ["rdp", "https", "snmp"], "Jump host RDP; traveler-info feed; NMS"),
    ]

    return {
        "name": "Freeway Management Corridor",
        "description": (
            "Twenty-mile freeway corridor run from a freeway TMC over five fiber hubs. Every half "
            "mile a Wavetronix SmartSensor HD station reports NTCIP 1209 lane volume, occupancy "
            "and speed every 30 s; McCain 2070 ramp meters; Daktronics travel-time signs (NTCIP "
            "1203); Vaisala RWIS (NTCIP 1204); Bosch PTZ and Axis fixed CCTV; the last stations "
            "past the fiber plant backhaul over Sierra Wireless cellular. Centracs ATMS primary/"
            "standby, PI historian, Genetec VMS, PRTG; IDMZ with jump host, traveler-information "
            "proxy and vendor remote access. " + _summary(devices, zones)
        ),
        "vertical": "transportation",
        "naming": "curated",
        "honor_flow_config": True,
        "phase_preset": "standard",
        "cell_isolation": {"mode": "conduit_gated"},
        "zones": zones,
        "conduits": conduits,
        "devices": devices,
        "flows": flows,
        "cloud_services": [
            {"provider": "talk2m", "region": "us-west", "device_types": ["remote_gateway"],
             "heartbeat_interval_ms": 30000},
        ],
        "recommended_attack_playbooks": [
            {"playbook_id": "network_recon", "relevance": "high",
             "rationale": "Every hub exposes SNMP on detection, sign and ramp-meter cabinets"},
            {"playbook_id": "its_signal_disruption", "relevance": "high",
             "rationale": "Travel-time signs and ramp meters are managed over SNMP from the TMC"},
            {"playbook_id": "volt_typhoon_like", "relevance": "medium",
             "rationale": "Internet-facing core switch web UI and cellular edge routers"},
        ],
        "total_duration_ms": 3600000,
    }


# ===========================================================================
# F4 — All-Electronic Toll and Express Lanes
# ===========================================================================

# (zone id, display name, subnet offset, lanes, express)
_F4_GANTRIES = [
    ("gantry_ort_nb", "ORT Gantry NB (MP 12.4)", 10, 3, False),
    ("gantry_ort_sb", "ORT Gantry SB (MP 12.4)", 11, 3, False),
    ("gantry_el_nb", "Express Lanes Gantry NB (MP 18.1)", 12, 2, True),
    ("gantry_el_sb", "Express Lanes Gantry SB (MP 18.1)", 13, 2, True),
]


def _f4_gantry(zone: str, lanes: int, express: bool) -> list[dict[str, Any]]:
    """One tolling point: zone controller, reader, ALPR front/rear per lane,
    laser classifier, cabinet switch; express entries add pricing signs."""
    tag = zone.replace("gantry_", "").upper()
    specs = [
        device(f"{tag}_Toll_Zone_Ctrl", "toll_controller", zone, "toll_zone_controller", ["snmp"]),
        device(f"{tag}_Tag_Reader", "toll_rsu", zone, "toll_reader", ["snmp"]),
        device(f"{tag}_Classifier", "classification_sensor", zone, "classifier", ["https"]),
        device(f"{tag}_Gantry_SW", "network_switch", zone, "cabinet_switch", ["snmp", "syslog"]),
    ]
    for lane in range(1, lanes + 1):
        for side in ("Front", "Rear"):
            specs.append(device(f"{tag}_L{lane}_ALPR_{side}", "anpr_camera", zone, "alpr_camera", ["https"]))
    if express:
        specs += [device(f"{tag}_Pricing_DMS_{i}", "dms", zone, "pricing_dms", ["snmp"]) for i in (1, 2)]
    return specs


def _toll_express_lanes() -> dict[str, Any]:
    zones = [
        {"id": "idmz", "name": "Industrial DMZ (Back-Office Link)", "level": 3.5, "subnet_offset": 0,
         "vlan": 100, "security_level": "critical"},
        {"id": "toll_ops", "name": "Toll Operations Center", "level": 3, "subnet_offset": 1, "vlan": 110,
         "security_level": "critical"},
    ]
    devices: list[dict[str, Any]] = [
        device("TOC_Facility_Host_A", "toll_host", "toll_ops", "toll_host", ["snmp", "https"]),
        device("TOC_Facility_Host_B", "toll_host", "toll_ops", "toll_host", ["snmp", "https"]),
        device("TOC_NMS", "nms", "toll_ops", "nms", ["snmp", "https", "syslog"]),
        device("TOC_Eng_WS", "engineering_workstation", "toll_ops", "ews", ["snmp", "rdp", "https"]),
        device("TOC_Core_SW", "network_switch", "toll_ops", "core_switch", ["snmp", "syslog"]),
        device("DMZ_Jump_Host", "jump_server", "idmz", "jump_patched", ["snmp", "rdp", "https"]),
        device("DMZ_Back_Office_Proxy", "reverse_proxy", "idmz", "reverse_proxy", ["snmp", "https"]),
        device("DMZ_Vendor_Remote", "remote_gateway", "idmz", "remote_gateway", ["snmp"]),
    ]
    gantry_ids = []
    for zone, display, offset, lanes, express in _F4_GANTRIES:
        gantry_ids.append(zone)
        zones.append({"id": zone, "name": display, "level": 2, "subnet_offset": offset,
                      "vlan": 200 + 10 * (offset - 9), "security_level": "high"})
        devices.extend(_f4_gantry(zone, lanes, express))

    flows = [
        # MOMS: maintenance monitoring of zone controllers and readers over SNMP.
        flow("snmp", ["toll_host"], ["toll_controller", "toll_rsu"], 60000, target_zones=gantry_ids),
        # Plate images from the ALPR cameras; classifier status (TEMS web).
        flow("https", ["toll_host"], ["anpr_camera"], 5000, target_zones=gantry_ids),
        flow("https", ["toll_host"], ["classification_sensor"], 60000, target_zones=gantry_ids),
        # Dynamic pricing: the facility host drives the express-lane signs (NTCIP 1203).
        flow("snmp", ["toll_host"], ["dms"], 30000, target_zones=gantry_ids),
        # Network operations and engineering.
        flow("snmp", ["nms"], ["network_switch", "toll_controller", "toll_rsu"], 60000),
        flow("syslog", ["network_switch"], ["nms"], 120000),
        flow("snmp", ["nms"], ["remote_gateway", "reverse_proxy", "jump_server"], 60000),
        flow("https", ["engineering_workstation"], ["classification_sensor"], 600000, target_zones=gantry_ids),
        # Back-office link and admin access.
        flow("https", ["reverse_proxy"], ["toll_host"], 15000, target_zones=["toll_ops"]),
        flow("rdp", ["jump_server"], ["engineering_workstation"], 300000),
    ]
    conduits = [
        conduit("toll_ops", g, ["snmp", "https", "syslog"], "MOMS, ALPR images, classifier, pricing signs, "
                "NMS and syslog")
        for g in gantry_ids
    ] + [
        conduit("idmz", "toll_ops", ["https", "rdp", "snmp"], "Back-office transaction link; jump host; NMS"),
    ]

    return {
        "name": "All-Electronic Toll and Express Lanes",
        "description": (
            "Open-road tolling on a freeway with priced express lanes. Four gantries (two 3-lane "
            "general-purpose, two 2-lane express) each carry a Kapsch Toll Zone Controller, a "
            "Kapsch JANUS multi-protocol tag reader, front and rear Genetec AutoVu SharpV ALPR "
            "cameras per lane, a SICK TIC502 laser classifier and a RUGGEDCOM switch; Daktronics "
            "pricing signs ahead of the express entries. A Kapsch Facility Host pair runs MOMS "
            "(SNMP monitoring of the roadside), pulls plate images and drives the pricing signs; "
            "the back office is reached across the IDMZ. " + _summary(devices, zones)
        ),
        "vertical": "transportation",
        "naming": "curated",
        "honor_flow_config": True,
        "phase_preset": "standard",
        "cell_isolation": {"mode": "conduit_gated"},
        "zones": zones,
        "conduits": conduits,
        "devices": devices,
        "flows": flows,
        "cloud_services": [
            {"provider": "talk2m", "region": "us-west", "device_types": ["remote_gateway"],
             "heartbeat_interval_ms": 30000},
        ],
        "recommended_attack_playbooks": [
            {"playbook_id": "network_recon", "relevance": "high",
             "rationale": "Every gantry exposes SNMP-managed controllers and readers to the TOC"},
            {"playbook_id": "insider_threat", "relevance": "medium",
             "rationale": "Back-office link and vendor remote access reach the toll operations center"},
        ],
        "total_duration_ms": 3600000,
    }


FLAGSHIP_TEMPLATES: dict[str, dict[str, Any]] = {
    "metro_arterial_signal_system": _metro_arterial(),
    "twin_bore_road_tunnel": _road_tunnel(),
    "freeway_management_corridor": _freeway_corridor(),
    "toll_express_lanes": _toll_express_lanes(),
}
