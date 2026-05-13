# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Per-scenario site identity that drives device naming.

A SiteIdentity is generated once per scenario at create-time (LLM or
deterministic fallback) and persisted on scenario.definition.site_identity.
It drives every device name in the scenario via the deterministic
renamer in site_naming.py.

The point: two scenarios from the same template should look like two
DIFFERENT real plants, not two copies of the same plant. Real plants
each have their own naming convention, site code, operator, and
location. This module makes every scenario carry that identity.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SiteIdentity:
    """Identity that anchors every device name in a single scenario.

    Generated once per scenario; reused for every device. Format strings
    in `role_patterns` are Python format() templates with the following
    slots available:

      {site}       - the site_code, e.g. "RR"
      {zone}       - the zone short code from zone_codes
      {n}          - 1-based counter, scoped to (zone_id, role_id)
      {nn}         - n zero-padded to 2 digits
      {nnn}        - n zero-padded to 3 digits
      {vendor}     - short vendor token (e.g. "RKW", "SIE")
      {role_abbr}  - short role abbreviation (e.g. "PLC", "WSUS", "HMI")
    """

    site_code: str           # "RR", "FAB-A", "MTL", "U1"
    plant_name: str          # "Round Rock Production Plant"
    location: str            # "Round Rock, Texas, USA"
    operator: str            # "Pharmaco LLC"
    industry_context: str    # "GMP vaccine manufacturing"
    domain_suffix: str | None  # "rr.pharmaco.com" or None
    naming_style: str        # "code_only" | "site_role_idx" | "vendor_prefixed" | "hierarchical"
    role_patterns: dict[str, str]
    zone_codes: dict[str, str]
    source: str = "deterministic"  # "llm" | "deterministic"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteIdentity:
        return cls(
            site_code=data.get("site_code", "SITE"),
            plant_name=data.get("plant_name", "Unnamed Plant"),
            location=data.get("location", "Unknown"),
            operator=data.get("operator", "Unknown Operator"),
            industry_context=data.get("industry_context", ""),
            domain_suffix=data.get("domain_suffix"),
            naming_style=data.get("naming_style", "site_role_idx"),
            role_patterns=dict(data.get("role_patterns") or {}),
            zone_codes=dict(data.get("zone_codes") or {}),
            source=data.get("source", "deterministic"),
        )


# Per-vertical bank of realistic site codes, plant names, operators
# used by the deterministic fallback. LLM path can pick freely.
_VERTICAL_SITE_BANK: dict[str, list[dict[str, str]]] = {
    "manufacturing": [
        {"site_code": "AUS01", "plant_name": "Austin Assembly Plant",
         "location": "Austin, Texas, USA", "operator": "Lone Star Industrial",
         "domain": "aus01.lonestar-ind.com",
         "context": "discrete-cell automotive subassembly"},
        {"site_code": "MTY02", "plant_name": "Monterrey Production Plant",
         "location": "Monterrey, Nuevo León, Mexico", "operator": "NorthBound Manufactura",
         "domain": "mty02.northbound-mfg.com.mx",
         "context": "high-mix discrete manufacturing"},
        {"site_code": "RR-P1", "plant_name": "Round Rock Plant 1",
         "location": "Round Rock, Texas, USA", "operator": "Pharmaco LLC",
         "domain": "rr-p1.pharmaco.com",
         "context": "GMP vaccine bioreactor"},
        {"site_code": "DUB01", "plant_name": "Dublin Bioprocess Plant",
         "location": "Dublin, Ireland", "operator": "Cellura Biologics",
         "domain": "dub01.cellura-bio.ie",
         "context": "GMP cell-and-gene therapy"},
        {"site_code": "DRESDEN", "plant_name": "Dresden Wafer Fab",
         "location": "Dresden, Saxony, Germany", "operator": "Halbleiter Werke AG",
         "domain": "dresden.halbleiter-werke.de",
         "context": "300mm semiconductor fab"},
        {"site_code": "TSV01", "plant_name": "Tsing Yi Fab 1",
         "location": "Tsing Yi, Hong Kong", "operator": "Pacific Silicon",
         "domain": "tsv01.pac-silicon.hk",
         "context": "300mm semiconductor fab"},
        {"site_code": "NVDA-EV", "plant_name": "Nevada EV Battery Plant",
         "location": "Sparks, Nevada, USA", "operator": "Volterra Cell Systems",
         "domain": "nvda-ev.volterra-cells.com",
         "context": "EV battery cell manufacturing"},
        {"site_code": "JF-WUXI", "plant_name": "Wuxi Battery Cell Plant",
         "location": "Wuxi, Jiangsu, China", "operator": "Jufeng Energy",
         "domain": "jf-wuxi.jufeng-energy.cn",
         "context": "EV battery cell manufacturing"},
    ],
    "water_wastewater": [
        {"site_code": "EAST-WTP", "plant_name": "East Side Water Treatment",
         "location": "Eastlake, Ohio, USA", "operator": "Lake Erie Water Authority",
         "domain": "eastwtp.leawater.gov",
         "context": "municipal drinking-water treatment"},
        {"site_code": "VALLEY", "plant_name": "Valley Reclamation Facility",
         "location": "Phoenix, Arizona, USA", "operator": "Sonoran Water District",
         "domain": "valley.sonoran-water.gov",
         "context": "wastewater reclamation"},
        {"site_code": "ALB-MUNI", "plant_name": "Albany Municipal Water",
         "location": "Albany, New York, USA", "operator": "Capital Region Water",
         "domain": "albmuni.cap-water.gov",
         "context": "municipal water + SCADA"},
    ],
    "energy_power": [
        {"site_code": "PNW-SUB1", "plant_name": "Pacific Northwest Substation 1",
         "location": "Vancouver, Washington, USA", "operator": "Cascadia Power Cooperative",
         "domain": "pnwsub1.cascadia-power.coop",
         "context": "230kV/115kV distribution substation"},
        {"site_code": "OK-WIND-04", "plant_name": "Oklahoma Wind Farm 04",
         "location": "Woodward, Oklahoma, USA", "operator": "Plains Renewables",
         "domain": "okwind04.plains-renewables.com",
         "context": "wind generation + collector substation"},
        {"site_code": "MV-SOLAR1", "plant_name": "Mojave Solar Park 1",
         "location": "Daggett, California, USA", "operator": "Sunfield Power",
         "domain": "mvsolar1.sunfield-power.com",
         "context": "utility-scale solar PV + BESS"},
        {"site_code": "U1-NORTH", "plant_name": "North Plant Unit 1",
         "location": "Charlotte, North Carolina, USA", "operator": "Carolina Energy Authority",
         "domain": "u1north.carolina-energy.com",
         "context": "combined-cycle generation Unit 1"},
    ],
    "oil_gas": [
        {"site_code": "PB-CFR1", "plant_name": "Permian Basin Compressor 1",
         "location": "Midland, Texas, USA", "operator": "Permian Midstream",
         "domain": "pbcfr1.permian-mid.com",
         "context": "natural gas compression + metering"},
        {"site_code": "RFNRY-A", "plant_name": "Galveston Refinery — Unit A",
         "location": "Galveston, Texas, USA", "operator": "Gulf Coast Refining",
         "domain": "rfnry-a.gcrefining.com",
         "context": "crude distillation + FCC"},
    ],
    "transportation": [
        {"site_code": "I-35-NB", "plant_name": "I-35 Northbound TMC",
         "location": "Austin, Texas, USA", "operator": "Capital Area Transit Authority",
         "domain": "i35nb.cata-its.gov",
         "context": "active traffic management"},
        {"site_code": "TX130-TOLL", "plant_name": "TX-130 Toll Plaza",
         "location": "Pflugerville, Texas, USA", "operator": "Central Texas Tollway",
         "domain": "tx130toll.cttollway.gov",
         "context": "AET toll plaza"},
        {"site_code": "EB-TUN", "plant_name": "East Bay Tunnel",
         "location": "Oakland, California, USA", "operator": "Bay Area Tunnel Authority",
         "domain": "ebtun.bay-tunnel.gov",
         "context": "tunnel ventilation + jet fan SCADA"},
    ],
    "building_automation": [
        {"site_code": "HQ-CHI", "plant_name": "Chicago HQ Campus",
         "location": "Chicago, Illinois, USA", "operator": "Lakeside Properties",
         "domain": "hq-chi.lakeside-props.com",
         "context": "office HVAC + lighting + access"},
        {"site_code": "STNFRD-MED", "plant_name": "Stamford Medical Tower",
         "location": "Stamford, Connecticut, USA", "operator": "Pinnacle Health Real Estate",
         "domain": "stnfrd-med.pinnacle-re.com",
         "context": "hospital BAS + critical environment"},
    ],
    "distribution_logistics": [
        {"site_code": "MEM-DC1", "plant_name": "Memphis DC1",
         "location": "Memphis, Tennessee, USA", "operator": "Continental Logistics",
         "domain": "mem-dc1.continental-log.com",
         "context": "high-throughput sortation"},
        {"site_code": "CDG-FC", "plant_name": "CDG Fulfillment Center",
         "location": "Roissy, Île-de-France, France", "operator": "Eurocourier",
         "domain": "cdg-fc.eurocourier.eu",
         "context": "automated fulfillment + AGV"},
    ],
    "testing": [
        {"site_code": "LAB01", "plant_name": "PacketArch Test Lab 01",
         "location": "Internal", "operator": "PacketArch Engineering",
         "domain": "lab01.packetarch.internal",
         "context": "fingerprint validation"},
    ],
}


# Default role-name patterns. The LLM can override per scenario; the
# deterministic fallback uses these directly. Naming style matches what
# CV operators expect to see (short uppercase tokens, hyphenated).
DEFAULT_ROLE_PATTERNS: dict[str, str] = {
    # IDMZ / shared services
    "jump_server":              "{site}-JMP-{nn}",
    "remote_access_gateway":    "{site}-RAGW-{nn}",
    "patch_staging_server":     "{site}-WSUS-{nn}",
    "av_management_server":     "{site}-EPP-{nn}",
    "asset_management_server":  "{site}-ITAM-{nn}",
    "alarm_event_server":       "{site}-ALM-{nn}",
    "batch_server":             "{site}-BATCH-{nn}",
    "mes_server":               "{site}-MES-{nn}",
    "nms_server":               "{site}-NMS-{nn}",
    "dns_ntp_relay":            "{site}-DNS-{nn}",
    "email_relay":              "{site}-SMTP-{nn}",
    "reverse_proxy":            "{site}-LB-{nn}",
    "historian_replica":        "{site}-HIST-RPL-{nn}",
    "process_historian":        "{site}-HIST-{nn}",
    "local_historian":          "{site}-HIST-LCL-{nn}",
    "opc_ua_aggregator":        "{site}-OPCUA-{nn}",
    # SCADA / engineering
    "scada_primary":            "{site}-SCADA-PRI-{nn}",
    "scada_standby":            "{site}-SCADA-SBY-{nn}",
    "engineering_workstation":  "{site}-EWS-{nn}",
    "area_hmi":                 "{site}-{zone}-HMI-{nn}",
    # PLCs / controllers
    "cell_controller":          "{site}-{zone}-PLC-{nn}",
    "dcs_controller":           "{site}-{zone}-DCS-{nn}",
    "batch_controller":         "{site}-{zone}-BATCH-CTRL-{nn}",
    "safety_controller":        "{site}-{zone}-SIS-{nn}",
    "conveyor_controller":      "{site}-{zone}-CONV-{nn}",
    "wcs_controller":           "{site}-{zone}-WCS-{nn}",
    "robot_controller":         "{site}-{zone}-ROB-{nn}",
    "cnc_controller":           "{site}-{zone}-CNC-{nn}",
    "fleet_manager":            "{site}-{zone}-FLEET-{nn}",
    # Field devices
    "field_instrument":         "{site}-{zone}-XMTR-{nnn}",
    "valve_actuator":           "{site}-{zone}-FCV-{nnn}",
    "vfd":                      "{site}-{zone}-VFD-{nnn}",
    "servo":                    "{site}-{zone}-SRV-{nnn}",
    "distributed_io":           "{site}-{zone}-IO-{nnn}",
    "analyzer":                 "{site}-{zone}-AIT-{nnn}",
    "flow_meter":               "{site}-{zone}-FT-{nnn}",
    "power_meter":              "{site}-{zone}-PM-{nnn}",
    "vision_system":            "{site}-{zone}-VIS-{nnn}",
    "barcode_scanner":          "{site}-{zone}-BCR-{nnn}",
    "agv":                      "{site}-{zone}-AGV-{nnn}",
    # Network
    "core_switch":              "{site}-SW-CORE-{nn}",
    "cell_switch":              "{site}-{zone}-SW-{nn}",
    "bay_switch":               "{site}-{zone}-SW-{nn}",
    "wan_edge_router":          "{site}-RTR-WAN-{nn}",
    # Utility / RTU
    "field_rtu":                "{site}-{zone}-RTU-{nnn}",
    "aggregator_rtu":           "{site}-{zone}-RTAC-{nn}",
    "protection_relay":         "{site}-{zone}-87L-{nn}",
    # BAS
    "bms_field_controller":     "{site}-{zone}-VAV-{nnn}",
    # Transportation
    "traffic_controller":       "{site}-{zone}-ATC-{nnn}",
    "cabinet_controller":       "{site}-{zone}-CAB-{nnn}",
    "cctv_camera":              "{site}-{zone}-CAM-{nnn}",
    "ptz_camera":               "{site}-{zone}-PTZ-{nnn}",
    "anpr_camera":              "{site}-{zone}-LPR-{nnn}",
    "dms_sign":                 "{site}-{zone}-DMS-{nnn}",
    "toll_rsu":                 "{site}-{zone}-RSU-{nnn}",
    "toll_lane_controller":     "{site}-{zone}-LANE-{nnn}",
    "rwis_station":             "{site}-{zone}-RWIS-{nnn}",
}


_ZONE_CODE_OVERRIDES: dict[str, str] = {
    # Cross-archetype canonical zone short codes. Anything not in this
    # map is auto-derived from the zone_id by _derive_zone_code().
    "idmz": "DMZ",
    "operations": "OPS",
    "plant_operations": "OPS",
    "control_room": "CTL",
    "amhs": "AMHS",
    "cleanroom_env": "CLEAN",
    "lithography": "LITH",
    "etch": "ETCH",
    "deposition": "DEPO",
    "cmp": "CMP",
    "metrology": "METR",
    "diffusion": "DIFF",
    "coating": "COAT",
    "calendaring": "CAL",
    "formation": "FORM",
    "quality": "QC",
    "pack_assembly": "ASM",
    "bioreactor_train_a": "BRX-A",
    "bioreactor_train_b": "BRX-B",
    "bioreactor_train_c": "BRX-C",
    "purification": "PURIF",
    "fill_finish": "FF",
    "clean_utilities": "UTIL",
    "safety": "SFTY",
    "purdue_l1": "L1",
    "purdue_l2": "L2",
    "purdue_l3": "L3",
}


def _hash_index(scenario_id: str, modulo: int) -> int:
    h = hashlib.sha256(scenario_id.encode()).hexdigest()
    return int(h[:8], 16) % max(1, modulo)


def _derive_zone_code(zone_id: str) -> str:
    if zone_id in _ZONE_CODE_OVERRIDES:
        return _ZONE_CODE_OVERRIDES[zone_id]
    # Strip common prefixes, uppercase, hyphenate
    s = zone_id.upper().replace("_", "-")
    if len(s) <= 8:
        return s
    # Take first letter of each segment
    parts = s.split("-")
    if len(parts) > 1:
        return "-".join(p[:4] for p in parts if p)[:12]
    return s[:8]


def filter_bank_for_template(
    vertical: str,
    template_name: str | None,
) -> list[dict[str, str]]:
    """Return the sub-bank of site entries appropriate for the
    template context (e.g. only pharma cities for a pharma template).

    Falls back to the full vertical bank when no sub-filter matches.
    """
    bank = list(_VERTICAL_SITE_BANK.get(vertical) or _VERTICAL_SITE_BANK["testing"])
    if not template_name:
        return bank
    if vertical != "manufacturing":
        return bank
    tn = template_name.lower()
    sub: list[dict[str, str]] = []
    if "pharma" in tn or "biorea" in tn or "vaccine" in tn:
        sub = [b for b in bank if "GMP" in b["context"] or "biolog" in b["context"]]
    elif "semi" in tn or "wafer" in tn or "fab" in tn:
        sub = [b for b in bank if "semiconductor" in b["context"]]
    elif "battery" in tn or "ev_battery" in tn or "cell_plant" in tn:
        sub = [b for b in bank if "battery" in b["context"]]
    else:
        sub = [b for b in bank if "discrete" in b["context"] or "high-mix" in b["context"]]
    return sub or bank


def deterministic_site_identity(
    *,
    scenario_id: str,
    vertical: str,
    zone_ids: list[str],
    role_ids: list[str],
    template_name: str | None = None,
) -> SiteIdentity:
    """Build a SiteIdentity deterministically from scenario_id.

    Used as the audit-harness path and as a fallback when AI is
    disabled or fails. The same scenario_id always produces the same
    identity, so renaming is reproducible. When a `template_name` hint
    is provided, the bank is sub-filtered so a pharma template doesn't
    pick a semiconductor city.
    """
    bank = filter_bank_for_template(vertical, template_name)
    pick = bank[_hash_index(scenario_id, len(bank))]

    zone_codes = {z: _derive_zone_code(z) for z in zone_ids}
    role_patterns = {
        r: DEFAULT_ROLE_PATTERNS[r]
        for r in role_ids
        if r in DEFAULT_ROLE_PATTERNS
    }

    return SiteIdentity(
        site_code=pick["site_code"],
        plant_name=pick["plant_name"],
        location=pick["location"],
        operator=pick["operator"],
        industry_context=pick["context"],
        domain_suffix=pick.get("domain"),
        naming_style="site_role_idx",
        role_patterns=role_patterns,
        zone_codes=zone_codes,
        source="deterministic",
    )


def list_default_role_patterns() -> dict[str, str]:
    """Public read of the default patterns — used by the LLM call as
    a starting point so the LLM only needs to override what's worth
    overriding for the picked site."""
    return dict(DEFAULT_ROLE_PATTERNS)
