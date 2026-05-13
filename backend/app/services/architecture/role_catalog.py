# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Typed role catalog for OT scenario authoring.

A "role" is the architectural function a device serves in the plant —
distinct from its physical type. A `plc` device_type can be a
`cell_controller`, `batch_controller`, `safety_controller`, or
`dcs_controller`, each with a different communication footprint.

Roles let templates, the AI wizard, and the scenario generator reason
about what belongs where, what talks to what, and which protocols are
appropriate, without hand-rolling the rationality at every call site.

Roles are arranged by Purdue level (L0 process .. L3.5 IDMZ) plus
network-infra and external classes that span layers. Each role declares:

  - purdue_level + category (Purdue layer + sub-class)
  - vertical_applicability (which verticals it appears in)
  - primary_device_types (maps to existing device.type field for
    back-compat with the current template format)
  - required_protocols / optional_protocols (must-serve / may-serve)
  - typical_partners (the role IDs it usually talks to — used by the
    comm matrix as a sanity check; the matrix itself is authoritative)
  - when_to_include (plain-English guidance for the AI wizard and
    `packetarch-scenario-authoring` skill)

This file is the source of truth. The comm matrix and archetype
catalog reference role IDs from here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


# ---------------------------------------------------------------------------
# Verticals
# ---------------------------------------------------------------------------

class Vertical(str, Enum):
    """Industrial verticals supported by PacketArch.

    Per-vertical archetypes and comm-matrix entries reference these.
    """

    MANUFACTURING_DISCRETE = "manufacturing_discrete"
    MANUFACTURING_PROCESS = "manufacturing_process"
    WATER_UTILITY = "water_utility"
    ENERGY_SUBSTATION = "energy_substation"
    ENERGY_GENERATION = "energy_generation"
    OIL_GAS = "oil_gas"
    BUILDING_AUTOMATION = "building_automation"
    TRANSPORTATION_ITS = "transportation_its"
    DISTRIBUTION_LOGISTICS = "distribution_logistics"
    DATA_CENTER_INFRA = "data_center_infra"


VERTICALS: frozenset[str] = frozenset(v.value for v in Vertical)

# Convenience: the four "process-like" verticals that share DCS-style
# architecture (continuous control, batch, regulated). These tend to
# share more comm-matrix entries than discrete-cell verticals.
PROCESS_VERTICALS: frozenset[str] = frozenset({
    Vertical.MANUFACTURING_PROCESS.value,
    Vertical.OIL_GAS.value,
    Vertical.ENERGY_GENERATION.value,
})

# SCADA-master / RTU-remote verticals. They omit L2 area-supervision
# and have strong WAN/serial backhaul characteristics.
MASTER_REMOTE_VERTICALS: frozenset[str] = frozenset({
    Vertical.WATER_UTILITY.value,
    Vertical.ENERGY_SUBSTATION.value,
    Vertical.OIL_GAS.value,  # pipelines/wellheads behave master-remote
})


# ---------------------------------------------------------------------------
# Categories (Purdue layer subclasses)
# ---------------------------------------------------------------------------

class RoleCategory(str, Enum):
    """High-level role classification.

    Maps to Purdue level groupings but allows finer subdivision than
    raw float levels (e.g. "network_infra" spans layers; "external"
    is the IT/cloud edge beyond L4).
    """

    IDMZ = "idmz"                    # L3.5
    OPERATIONS = "operations"        # L3
    AREA_SUPERVISION = "area"        # L2
    BASIC_CONTROL = "control"        # L1
    PROCESS = "process"              # L0
    NETWORK_INFRA = "network_infra"  # spans L0-L3.5
    EXTERNAL = "external"            # L4+ / cloud / partner


# ---------------------------------------------------------------------------
# Role definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Role:
    """An architectural role a device fulfills in an OT plant.

    Roles are vendor-agnostic — `cell_controller` is the role; whether
    the device is a Siemens S7-1500, Rockwell ControlLogix, or
    Schneider M580 is a separate vendor decision driven by the archetype.
    """

    id: str
    """Canonical role identifier (snake_case, stable). Referenced by
    archetypes, comm matrix, and scenario generator."""

    name: str
    """Human-readable name for UI / docs."""

    category: RoleCategory
    """High-level Purdue subclass."""

    purdue_level: float
    """Numeric Purdue level. 0=process, 1=basic control, 2=area
    supervision, 3=operations, 3.5=IDMZ, 4=enterprise."""

    description: str
    """One-line role description."""

    when_to_include: str
    """Plain-English guidance for AI wizard / authoring skill: when does
    a scenario need this role, when can it omit, and what scale tiers
    require it?"""

    primary_device_types: tuple[str, ...]
    """Device.type values that legitimately fulfill this role (back-compat
    with existing template format). First entry is the canonical type."""

    vertical_applicability: frozenset[str]
    """Verticals where this role appears. Empty frozenset means "all"."""

    required_protocols: tuple[str, ...] = ()
    """Protocols this role MUST serve to function (e.g. SCADA primary
    must serve SNMP for NMS; engineering workstation must serve the
    vendor programming protocol)."""

    optional_protocols: tuple[str, ...] = ()
    """Protocols this role COMMONLY serves but isn't required to (e.g.
    historian replicates over OPC UA but could use a vendor-proprietary
    historian protocol instead)."""

    typical_partners: tuple[str, ...] = ()
    """Role IDs this role typically initiates traffic to or receives
    traffic from. Sanity check; comm matrix is authoritative."""

    examples: tuple[str, ...] = ()
    """Known products fulfilling this role (helps catalog selection)."""

    @property
    def is_idmz(self) -> bool:
        return self.category == RoleCategory.IDMZ

    @property
    def is_field(self) -> bool:
        return self.category == RoleCategory.PROCESS

    def applies_to(self, vertical: str) -> bool:
        """True if this role appears in the given vertical."""
        if not self.vertical_applicability:
            return True
        return vertical in self.vertical_applicability


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

# Helpers for compact frozenset construction
def _verts(*names: str) -> frozenset[str]:
    return frozenset(names)


_ALL_VERTS: frozenset[str] = frozenset()  # empty == "all"


_ROLES: tuple[Role, ...] = (
    # =====================================================================
    # IDMZ (L3.5) — the IT/OT boundary. Always present in scale >= medium
    # for any vertical with cross-IT traffic. Small utilities may collapse
    # IDMZ into operations.
    # =====================================================================

    Role(
        id="jump_server",
        name="Jump Server",
        category=RoleCategory.IDMZ,
        purdue_level=3.5,
        description=(
            "Hardened admin pivot host. Operators and vendors RDP/SSH "
            "in from IT/external, then reach OT assets through it."
        ),
        when_to_include=(
            "Include in any scenario with vendor remote access, "
            "operator remote work, or IT admin reach into OT. Effectively "
            "every scale >= small that has external connectivity."
        ),
        primary_device_types=("jump_server", "server"),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp", "rdp", "ssh"),
        optional_protocols=("https", "telnet"),
        typical_partners=(
            "scada_primary", "engineering_workstation", "cell_controller",
            "field_rtu", "core_switch", "cell_switch",
        ),
        examples=("Microsoft Jump Server 2016/2019", "Linux bastion"),
    ),

    Role(
        id="reverse_proxy",
        name="Reverse Proxy / Web Gateway",
        category=RoleCategory.IDMZ,
        purdue_level=3.5,
        description=(
            "HTTPS / RDP gateway that brokers IT-initiated sessions to "
            "OT services without exposing those services directly."
        ),
        when_to_include=(
            "Include when IT users access OT historian/HMI web UIs or "
            "when external partners reach OT via a published URL. "
            "Optional at small scale."
        ),
        primary_device_types=("server", "reverse_proxy"),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("https",),
        optional_protocols=("rdp", "snmp"),
        typical_partners=("scada_primary", "process_historian", "area_hmi"),
        examples=("Citrix StoreFront", "Apache reverse proxy", "F5 BIG-IP"),
    ),

    Role(
        id="patch_staging_server",
        name="Patch / Update Staging Server",
        category=RoleCategory.IDMZ,
        purdue_level=3.5,
        description=(
            "WSUS-equivalent: pulls vendor / OS updates from internet, "
            "stages them for OT-side approval and distribution."
        ),
        when_to_include=(
            "Include at scale >= medium when scenario models patch "
            "management traffic. Optional otherwise."
        ),
        primary_device_types=("server",),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("https", "snmp"),
        optional_protocols=("smb",),
        typical_partners=("engineering_workstation", "scada_primary"),
        examples=("WSUS", "Rockwell Patch Server", "vendor depot"),
    ),

    Role(
        id="av_management_server",
        name="AV / EDR Management Server",
        category=RoleCategory.IDMZ,
        purdue_level=3.5,
        description=(
            "Central console for endpoint protection across the OT "
            "network. Pulls definitions from vendor cloud, pushes to "
            "OT endpoints."
        ),
        when_to_include=(
            "Include in regulated environments (NERC CIP, IEC 62443 SL3+) "
            "or when modeling endpoint security telemetry. Optional at "
            "small scale."
        ),
        primary_device_types=("server",),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("https", "snmp"),
        typical_partners=(
            "engineering_workstation", "scada_primary", "process_historian",
        ),
        examples=("CrowdStrike Falcon manager", "Symantec EPM"),
    ),

    Role(
        id="historian_replica",
        name="Historian Replica (IDMZ)",
        category=RoleCategory.IDMZ,
        purdue_level=3.5,
        description=(
            "Read-only mirror of the process historian, exposed to IT "
            "consumers (BI, MES upstream, dashboards) without giving "
            "them direct access to operations."
        ),
        when_to_include=(
            "Include when IT/business consumers need process data. "
            "Common in manufacturing/oil_gas at scale >= medium."
        ),
        primary_device_types=("historian", "server"),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.OIL_GAS.value,
            Vertical.ENERGY_GENERATION.value,
        ),
        required_protocols=("opc_ua", "snmp"),
        optional_protocols=("https",),
        typical_partners=("process_historian", "reverse_proxy"),
        examples=("AVEVA PI to AF replica", "Honeywell Uniformance"),
    ),

    Role(
        id="opc_ua_aggregator",
        name="OPC UA Aggregator",
        category=RoleCategory.IDMZ,
        purdue_level=3.5,
        description=(
            "Multi-vendor OPC UA broker. Aggregates tags from PLCs of "
            "different vendors and publishes a unified namespace. "
            "Common in multi-vendor plants."
        ),
        when_to_include=(
            "Include in multi-vendor enterprise scenarios where IT-side "
            "consumers want a single OPC UA endpoint instead of N "
            "vendor-native endpoints."
        ),
        primary_device_types=("server", "gateway"),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.OIL_GAS.value,
            Vertical.ENERGY_GENERATION.value,
            Vertical.DISTRIBUTION_LOGISTICS.value,
        ),
        required_protocols=("opc_ua", "snmp"),
        typical_partners=(
            "cell_controller", "dcs_controller", "scada_primary",
            "process_historian",
        ),
        examples=("Kepware KEPServerEX", "Matrikon UA Gateway"),
    ),

    Role(
        id="remote_access_gateway",
        name="Remote Access Gateway",
        category=RoleCategory.IDMZ,
        purdue_level=3.5,
        description=(
            "Vendor cloud-bridge gateway. Maintains an outbound TLS "
            "tunnel to the vendor's cloud (Talk2M, SiteManager) so "
            "external service techs can reach the plant without inbound "
            "rules."
        ),
        when_to_include=(
            "Include when scenario models vendor remote service access. "
            "Common in small/medium utilities, manufacturing cells with "
            "OEM service contracts."
        ),
        primary_device_types=("remote_gateway",),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("https", "snmp"),
        optional_protocols=("modbus_tcp", "ethernet_ip"),
        typical_partners=(
            "cell_controller", "field_rtu", "scada_primary",
        ),
        examples=("HMS eWON Flexy 205", "Secomea SiteManager"),
    ),

    Role(
        id="dns_ntp_relay",
        name="DNS / NTP Relay",
        category=RoleCategory.IDMZ,
        purdue_level=3.5,
        description=(
            "Local recursive DNS + stratum-2 NTP for OT. Pulls upstream "
            "from IT, serves OT to keep external resolution off the "
            "plant floor."
        ),
        when_to_include=(
            "Include at scale >= medium. Small sites typically use the "
            "remote-access gateway or operations server for time/DNS."
        ),
        primary_device_types=("server",),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("dns", "ntp", "snmp"),
        typical_partners=("scada_primary", "engineering_workstation"),
        examples=("BIND", "ntpd", "Windows DNS"),
    ),

    Role(
        id="email_relay",
        name="Email / Alarm Relay",
        category=RoleCategory.IDMZ,
        purdue_level=3.5,
        description=(
            "Outbound SMTP from OT for alarm dispatch (page-out to "
            "operator phones, SOC ticket creation)."
        ),
        when_to_include=(
            "Include when scenario models alarm escalation traffic. "
            "Optional at small scale."
        ),
        primary_device_types=("server",),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("smtp", "snmp"),
        typical_partners=("scada_primary", "alarm_event_server"),
        examples=("Postfix relay", "MS SMTP forwarder"),
    ),

    # =====================================================================
    # OPERATIONS (L3) — the plant control center.
    # =====================================================================

    Role(
        id="scada_primary",
        name="SCADA / HMI Server (Primary)",
        category=RoleCategory.OPERATIONS,
        purdue_level=3.0,
        description=(
            "Master SCADA / HMI server. Aggregates data from all field "
            "controllers, drives operator displays, raises alarms."
        ),
        when_to_include=(
            "Include in every scenario except pure substation/edge "
            "deployments where a separate aggregator_rtu fills the role. "
            "Required for scale >= small in manufacturing/water/oil&gas."
        ),
        primary_device_types=("scada_server", "server"),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp",),
        optional_protocols=("opc_ua", "modbus_tcp", "ethernet_ip", "https"),
        typical_partners=(
            "cell_controller", "dcs_controller", "field_rtu", "area_hmi",
            "process_historian", "engineering_workstation",
        ),
        examples=("AVEVA System Platform", "Wonderware InTouch", "Ignition"),
    ),

    Role(
        id="scada_standby",
        name="SCADA / HMI Server (Standby)",
        category=RoleCategory.OPERATIONS,
        purdue_level=3.0,
        description=(
            "Hot/warm standby SCADA. Continuously synchronizes from "
            "primary; takes over on failover. Same partners as primary "
            "but most flows are mirror traffic."
        ),
        when_to_include=(
            "Include at scale >= medium for any vertical where uptime "
            "matters (manufacturing, water, energy). Optional at small."
        ),
        primary_device_types=("scada_server", "server"),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp",),
        optional_protocols=("opc_ua", "modbus_tcp", "ethernet_ip"),
        typical_partners=("scada_primary", "process_historian"),
    ),

    Role(
        id="process_historian",
        name="Process Historian",
        category=RoleCategory.OPERATIONS,
        purdue_level=3.0,
        description=(
            "Long-term time-series store for process data. Subscribes "
            "to PLCs/DCS/RTUs, persists tags at high resolution, serves "
            "trends/reports."
        ),
        when_to_include=(
            "Include in any scenario larger than tiny demo. Required for "
            "scale >= small in process-like verticals."
        ),
        primary_device_types=("historian", "server"),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp",),
        optional_protocols=(
            "opc_ua", "modbus_tcp", "ethernet_ip", "s7comm", "https",
        ),
        typical_partners=(
            "cell_controller", "dcs_controller", "field_rtu",
            "scada_primary", "historian_replica", "mes_server",
        ),
        examples=("AVEVA PI", "GE Proficy Historian", "Honeywell Uniformance"),
    ),

    Role(
        id="engineering_workstation",
        name="Engineering Workstation",
        category=RoleCategory.OPERATIONS,
        purdue_level=3.0,
        description=(
            "Vendor-specific engineering host. Hosts programming software "
            "(Studio 5000, TIA Portal, Unity Pro, EcoStruxure Control "
            "Expert). Used for downloads, online edits, diagnostics."
        ),
        when_to_include=(
            "Include in every scenario with PLCs/DCS. Vendor-pinned: a "
            "Siemens shop has TIA Portal hosts; a Rockwell shop has "
            "Studio 5000 hosts. Multi-vendor sites have one per vendor."
        ),
        primary_device_types=("workstation", "engineering_workstation"),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp",),
        optional_protocols=(
            "s7comm", "ethernet_ip", "modbus_tcp", "opc_ua", "https",
        ),
        typical_partners=(
            "cell_controller", "safety_controller", "dcs_controller",
            "field_rtu", "patch_staging_server",
        ),
    ),

    Role(
        id="asset_management_server",
        name="Asset Management Server",
        category=RoleCategory.OPERATIONS,
        purdue_level=3.0,
        description=(
            "Tracks firmware versions, PLC programs, configuration "
            "baselines across the plant. Periodic asset polls."
        ),
        when_to_include=(
            "Include at scale >= medium for regulated verticals "
            "(manufacturing, oil_gas, energy)."
        ),
        primary_device_types=("server",),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.OIL_GAS.value,
            Vertical.ENERGY_GENERATION.value,
            Vertical.ENERGY_SUBSTATION.value,
        ),
        required_protocols=("snmp", "https"),
        optional_protocols=("ethernet_ip", "s7comm", "modbus_tcp"),
        typical_partners=(
            "cell_controller", "dcs_controller", "engineering_workstation",
        ),
        examples=("Rockwell FactoryTalk AssetCentre", "PAS Cyber Integrity"),
    ),

    Role(
        id="nms_server",
        name="Network Management Server",
        category=RoleCategory.OPERATIONS,
        purdue_level=3.0,
        description=(
            "Polls every switch and routable OT asset over SNMP. "
            "Surfaces link-up/down, CPU/memory, port stats."
        ),
        when_to_include=(
            "Include in every scenario at scale >= small. The NMS is "
            "the canonical SNMP source — without it, switches end up "
            "orphaned for Cyber Vision discovery."
        ),
        primary_device_types=("server", "nms"),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp",),
        optional_protocols=("https", "ssh"),
        typical_partners=(
            "core_switch", "cell_switch", "bay_switch",
            "scada_primary", "cell_controller", "field_rtu",
        ),
        examples=("SolarWinds Orion", "PRTG", "LibreNMS"),
    ),

    Role(
        id="alarm_event_server",
        name="Alarm / Event Server",
        category=RoleCategory.OPERATIONS,
        purdue_level=3.0,
        description=(
            "Dedicated alarm management. Often co-resident with SCADA "
            "but called out separately for regulated environments."
        ),
        when_to_include=(
            "Optional everywhere. Include for ISA-18.2 alarm-management "
            "scenarios (oil_gas, energy_generation)."
        ),
        primary_device_types=("server",),
        vertical_applicability=_verts(
            Vertical.OIL_GAS.value,
            Vertical.ENERGY_GENERATION.value,
            Vertical.MANUFACTURING_PROCESS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("https", "smtp"),
        typical_partners=("scada_primary", "email_relay", "process_historian"),
    ),

    Role(
        id="batch_server",
        name="Batch Control Server",
        category=RoleCategory.OPERATIONS,
        purdue_level=3.0,
        description=(
            "ISA-88 batch execution. Coordinates recipe-driven control "
            "across multiple batch_controllers."
        ),
        when_to_include=(
            "Include in pharma / specialty chemicals / food&beverage "
            "process_manufacturing scenarios."
        ),
        primary_device_types=("server",),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.OIL_GAS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("opc_ua",),
        typical_partners=("batch_controller", "process_historian"),
        examples=("Rockwell PlantPAx Batch", "Emerson DeltaV Batch"),
    ),

    Role(
        id="mes_server",
        name="MES / MOM Server",
        category=RoleCategory.OPERATIONS,
        purdue_level=3.0,
        description=(
            "Manufacturing execution layer. Bridges enterprise (L4) "
            "production orders down to plant control. Pulls from "
            "historian, pushes work orders to HMIs/PLCs."
        ),
        when_to_include=(
            "Include in manufacturing scenarios at scale >= medium "
            "where enterprise integration is in scope."
        ),
        primary_device_types=("server",),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.DISTRIBUTION_LOGISTICS.value,
        ),
        required_protocols=("https", "snmp"),
        optional_protocols=("opc_ua",),
        typical_partners=(
            "process_historian", "scada_primary", "historian_replica",
        ),
        examples=("Rockwell FactoryTalk Production", "Siemens Opcenter"),
    ),

    Role(
        id="ot_domain_controller",
        name="OT Domain Controller",
        category=RoleCategory.OPERATIONS,
        purdue_level=3.0,
        description=(
            "AD/LDAP for OT-only authentication. Replicates carefully "
            "from IT or stands alone for air-gapped sites."
        ),
        when_to_include=(
            "Optional. Include at scale >= medium for centralized auth "
            "across SCADA/HMI/engineering hosts."
        ),
        primary_device_types=("server",),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp",),
        optional_protocols=("dns", "ldaps", "kerberos", "ntp"),
        typical_partners=(
            "scada_primary", "engineering_workstation", "process_historian",
        ),
    ),

    # =====================================================================
    # AREA SUPERVISION (L2) — operator-facing per area / cell.
    # =====================================================================

    Role(
        id="area_hmi",
        name="Area / Cell HMI",
        category=RoleCategory.AREA_SUPERVISION,
        purdue_level=2.0,
        description=(
            "Operator HMI panel inside a cell. Polls the cell's "
            "controllers over the vendor-native protocol; provides "
            "local operator interaction."
        ),
        when_to_include=(
            "Include one per cell/area in discrete-cell manufacturing, "
            "BAS supervisor zones, oil/gas process areas. Skip in pure "
            "master-remote SCADA topologies (water/energy substation)."
        ),
        primary_device_types=("hmi",),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.OIL_GAS.value,
            Vertical.ENERGY_GENERATION.value,
            Vertical.BUILDING_AUTOMATION.value,
            Vertical.DISTRIBUTION_LOGISTICS.value,
            Vertical.WATER_UTILITY.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=(
            "ethernet_ip", "modbus_tcp", "s7comm", "profinet", "bacnet",
        ),
        typical_partners=("cell_controller", "scada_primary"),
    ),

    Role(
        id="area_supervisor_plc",
        name="Area Supervisor PLC",
        category=RoleCategory.AREA_SUPERVISION,
        purdue_level=2.0,
        description=(
            "Higher-level coordinating PLC in a cell — orchestrates "
            "multiple cell_controllers and routes data to L3 SCADA. "
            "Common in large discrete plants."
        ),
        when_to_include=(
            "Optional. Include only at enterprise-scale discrete "
            "manufacturing where cells need a coordinator."
        ),
        primary_device_types=("plc",),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
            Vertical.DISTRIBUTION_LOGISTICS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=(
            "ethernet_ip", "modbus_tcp", "s7comm", "profinet", "opc_ua",
        ),
        typical_partners=(
            "cell_controller", "scada_primary", "process_historian",
        ),
    ),

    Role(
        id="local_historian",
        name="Local / Edge Historian",
        category=RoleCategory.AREA_SUPERVISION,
        purdue_level=2.0,
        description=(
            "Edge-buffering historian inside a cell. Captures locally, "
            "forwards to L3 historian. Used when WAN to L3 is unreliable."
        ),
        when_to_include=(
            "Optional. Include in distributed scenarios (multi-site, "
            "remote oil&gas, distributed water)."
        ),
        primary_device_types=("historian",),
        vertical_applicability=_verts(
            Vertical.OIL_GAS.value,
            Vertical.WATER_UTILITY.value,
            Vertical.ENERGY_SUBSTATION.value,
            Vertical.MANUFACTURING_PROCESS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("opc_ua", "modbus_tcp"),
        typical_partners=("cell_controller", "process_historian"),
    ),

    # =====================================================================
    # BASIC CONTROL (L1) — the controllers that actually run the plant.
    # =====================================================================

    Role(
        id="cell_controller",
        name="Cell PLC",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "General-purpose PLC running cell automation. Polls field "
            "I/O cyclically, exchanges with peer PLCs, surfaces tags "
            "to area HMI and L3 SCADA."
        ),
        when_to_include=(
            "Required in every discrete/cell-based scenario. One or "
            "more per cell."
        ),
        primary_device_types=("plc",),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.WATER_UTILITY.value,
            Vertical.OIL_GAS.value,
            Vertical.BUILDING_AUTOMATION.value,
            Vertical.DISTRIBUTION_LOGISTICS.value,
            Vertical.DATA_CENTER_INFRA.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=(
            "ethernet_ip", "modbus_tcp", "s7comm", "profinet", "opc_ua",
        ),
        typical_partners=(
            "distributed_io", "vfd", "servo", "field_instrument",
            "area_hmi", "scada_primary", "process_historian",
        ),
    ),

    Role(
        id="batch_controller",
        name="Batch PLC",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Recipe-aware PLC executing ISA-88 phase logic. Coordinates "
            "with batch_server above and skid-level control below."
        ),
        when_to_include=(
            "Include in pharma / specialty chemicals / food&beverage "
            "manufacturing_process scenarios."
        ),
        primary_device_types=("plc",),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_PROCESS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("modbus_tcp", "ethernet_ip", "opc_ua"),
        typical_partners=("batch_server", "vfd", "valve_actuator"),
    ),

    Role(
        id="safety_controller",
        name="Safety PLC (SIL2/3)",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Dedicated safety controller. Runs SIL2/3 logic over "
            "fail-safe protocols (PROFIsafe, CIP Safety, openSafety). "
            "Distinct from regular PLC; cannot share network in some "
            "regulated configs."
        ),
        when_to_include=(
            "Include in scenarios with explicit safety functions: "
            "robot cells, chemical reactors, gas detection, burner "
            "management, emergency shutdown."
        ),
        primary_device_types=("safety_plc",),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.OIL_GAS.value,
            Vertical.ENERGY_GENERATION.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=(
            "profisafe", "cip_safety", "ethernet_ip", "profinet", "s7comm",
        ),
        typical_partners=(
            "cell_controller", "vfd", "distributed_io", "valve_actuator",
        ),
    ),

    Role(
        id="dcs_controller",
        name="DCS Controller",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Distributed Control System controller. Vendor-specific "
            "(Yokogawa Centum, Honeywell Experion, Emerson DeltaV, "
            "ABB 800xA). Continuous regulatory control loops at high "
            "deterministic rates."
        ),
        when_to_include=(
            "Include in continuous-process scenarios: refineries, "
            "petrochem, power generation, pharma. Replaces cell_controller "
            "in those verticals."
        ),
        primary_device_types=("plc", "dcs_controller"),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.OIL_GAS.value,
            Vertical.ENERGY_GENERATION.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=(
            "modbus_tcp", "opc_ua", "ethernet_ip", "vendor_dcs",
        ),
        typical_partners=(
            "field_instrument", "valve_actuator", "vfd",
            "scada_primary", "process_historian", "batch_controller",
        ),
        examples=("Yokogawa Centum VP", "Honeywell Experion", "Emerson DeltaV"),
    ),

    Role(
        id="field_rtu",
        name="Field RTU",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Remote site controller at a substation, lift station, "
            "wellhead, pump station. Owns local I/O, reports to a "
            "central aggregator over WAN/serial."
        ),
        when_to_include=(
            "Include in master-remote SCADA scenarios: water utility "
            "(per pump station), energy substation (per bay), oil_gas "
            "(per wellhead/compressor)."
        ),
        primary_device_types=("rtu",),
        vertical_applicability=_verts(
            Vertical.WATER_UTILITY.value,
            Vertical.ENERGY_SUBSTATION.value,
            Vertical.OIL_GAS.value,
            Vertical.TRANSPORTATION_ITS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=(
            "modbus_tcp", "dnp3", "iec104", "iec61850",
        ),
        typical_partners=(
            "aggregator_rtu", "scada_primary", "field_instrument",
            "valve_actuator",
        ),
    ),

    Role(
        id="aggregator_rtu",
        name="Aggregator / Master RTU (RTAC)",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.5,  # operationally between L1 RTUs and L2/L3 SCADA
        description=(
            "Concentrator / RTAC. Aggregates data from many field_rtus, "
            "performs site-wide protection logic, presents a single "
            "point to L3 SCADA."
        ),
        when_to_include=(
            "Include one per site in master-remote SCADA scenarios. "
            "In substations, this is the SEL-3530 / SEL-3555 RTAC."
        ),
        primary_device_types=("rtu", "gateway"),
        vertical_applicability=_verts(
            Vertical.WATER_UTILITY.value,
            Vertical.ENERGY_SUBSTATION.value,
            Vertical.OIL_GAS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=(
            "modbus_tcp", "dnp3", "iec104", "iec61850", "https",
        ),
        typical_partners=(
            "field_rtu", "protection_relay", "scada_primary", "core_switch",
        ),
        examples=("SEL-3530 RTAC", "GE D400", "Schneider SCADAPack"),
    ),

    Role(
        id="protection_relay",
        name="Protection Relay (IEC 61850 IED)",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Substation IED. Runs feeder/transformer/bus protection "
            "logic, exchanges GOOSE multicast at the bay, reports MMS "
            "to the aggregator_rtu / station bus."
        ),
        when_to_include=(
            "Required in energy_substation. Multiple per bay."
        ),
        primary_device_types=("protection_relay", "ied"),
        vertical_applicability=_verts(
            Vertical.ENERGY_SUBSTATION.value,
        ),
        required_protocols=("iec61850", "snmp"),
        optional_protocols=("modbus_tcp", "dnp3"),
        typical_partners=(
            "aggregator_rtu", "protection_relay", "bay_switch",
        ),
        examples=("SEL-411L", "Schweitzer SEL-751", "ABB REL670"),
    ),

    Role(
        id="bms_field_controller",
        name="BAS Field Controller",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "BACnet/IP field controller. Runs zone HVAC sequences, "
            "lighting schedules, energy meter polling. Reports to "
            "BAS supervisor (the building's scada_primary equivalent)."
        ),
        when_to_include=(
            "Required in building_automation. One per zone or AHU."
        ),
        primary_device_types=("plc", "controller"),
        vertical_applicability=_verts(
            Vertical.BUILDING_AUTOMATION.value,
        ),
        required_protocols=("bacnet", "snmp"),
        optional_protocols=("modbus_tcp", "https"),
        typical_partners=(
            "scada_primary", "field_instrument", "valve_actuator", "vfd",
        ),
        examples=("Tridium JACE", "Distech ECY", "Reliable Controls MACH"),
    ),

    Role(
        id="traffic_controller",
        name="Traffic Cabinet Controller",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "ATC/2070 traffic signal controller in a roadside cabinet. "
            "Runs phase timing, communicates NTCIP over SNMP to ATMS."
        ),
        when_to_include=(
            "Required in transportation_its. One per intersection / "
            "ramp meter / DMS."
        ),
        primary_device_types=("traffic_controller", "controller"),
        vertical_applicability=_verts(
            Vertical.TRANSPORTATION_ITS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("ntcip", "https"),
        typical_partners=("scada_primary", "cabinet_controller"),
        examples=("Econolite Cobalt", "McCain ATC eX", "Siemens M60"),
    ),

    Role(
        id="cabinet_controller",
        name="ITS Cabinet Auxiliary Controller",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Auxiliary controller in roadside cabinet — generic stand-in "
            "for cabinet-level auxiliaries that aren't specifically "
            "modeled (use cctv_camera / dms_sign / rwis_station for "
            "specific device classes)."
        ),
        when_to_include=(
            "Optional. Use only when no specific role fits — prefer "
            "cctv_camera, anpr_camera, ptz_camera, dms_sign, rwis_station."
        ),
        primary_device_types=("controller",),
        vertical_applicability=_verts(
            Vertical.TRANSPORTATION_ITS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("rtsp", "https", "ntcip"),
        typical_partners=("scada_primary", "traffic_controller"),
    ),

    # =====================================================================
    # ITS field equipment (cameras, DMS, RSU, RWIS, toll) — all polled by
    # the ATMS master at L3. Modeled as L1 field/roadside roles, same
    # architectural class as traffic_controller.
    # =====================================================================

    Role(
        id="cctv_camera",
        name="CCTV Camera (Fixed)",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Fixed surveillance camera at roadside / tunnel / toll plaza. "
            "Streams RTSP video; SNMP-monitored for health by ATMS / NMS."
        ),
        when_to_include=(
            "Include in transportation scenarios with surveillance: "
            "tunnels, toll plazas, highway corridors, urban-grid CCTV."
        ),
        primary_device_types=("camera", "ip_camera"),
        vertical_applicability=_verts(
            Vertical.TRANSPORTATION_ITS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("rtsp", "https"),
        typical_partners=("scada_primary", "cabinet_controller"),
        examples=("Axis P1455-LE", "Pelco Spectra Enhanced", "Bosch MIC IP"),
    ),

    Role(
        id="ptz_camera",
        name="PTZ Surveillance Camera",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Pan-tilt-zoom surveillance camera. Operator-controllable; "
            "RTSP stream + SNMP health + control commands."
        ),
        when_to_include=(
            "Include for active surveillance scenarios — toll plaza "
            "approach monitoring, tunnel watchtower, urban corridor PTZ."
        ),
        primary_device_types=("ptz_camera", "camera"),
        vertical_applicability=_verts(
            Vertical.TRANSPORTATION_ITS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("rtsp", "https", "onvif"),
        typical_partners=("scada_primary",),
        examples=("Pelco SD436-PG-E1", "Bosch MIC IP 7100i"),
    ),

    Role(
        id="anpr_camera",
        name="ANPR / ALPR Camera",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Automatic Number Plate / License Plate Recognition camera. "
            "Captures plate images, runs OCR, reports matches over HTTPS / "
            "RTSP. Toll plaza enforcement, tunnel entry, urban tolling."
        ),
        when_to_include=(
            "Required in toll plaza scenarios. Common in tunnel entry "
            "and urban tolling deployments."
        ),
        primary_device_types=("anpr_camera", "camera"),
        vertical_applicability=_verts(
            Vertical.TRANSPORTATION_ITS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("rtsp", "https"),
        typical_partners=("scada_primary", "toll_lane_controller"),
        examples=("Hikvision DS-2CD7A26G0/P",),
    ),

    Role(
        id="dms_sign",
        name="Dynamic Message Sign (DMS)",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Variable / dynamic message sign — overhead matrix display "
            "showing traveler info. NTCIP-over-SNMP control from ATMS."
        ),
        when_to_include=(
            "Include in highway corridors, tunnels, toll-plaza approaches, "
            "and urban-grid traveler-info deployments."
        ),
        primary_device_types=("dms",),
        vertical_applicability=_verts(
            Vertical.TRANSPORTATION_ITS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("ntcip", "https"),
        typical_partners=("scada_primary",),
        examples=("Daktronics Venus 1500", "Daktronics Venus 7000"),
    ),

    Role(
        id="toll_rsu",
        name="Toll Roadside Unit (DSRC)",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "DSRC roadside unit for electronic toll collection — reads "
            "transponders / OBUs as vehicles pass. Reports transactions "
            "to the toll plaza host."
        ),
        when_to_include=(
            "Required in toll plaza scenarios with electronic toll "
            "collection (ETC) or open-road tolling."
        ),
        primary_device_types=("toll_rsu",),
        vertical_applicability=_verts(
            Vertical.TRANSPORTATION_ITS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("https",),
        typical_partners=("toll_lane_controller", "scada_primary"),
        examples=("Q-Free RSU 5000",),
    ),

    Role(
        id="toll_lane_controller",
        name="Toll Lane Controller (ETC)",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Toll-lane host: aggregates RSU transactions, drives ANPR "
            "enforcement, controls lane gates. ETC system controller."
        ),
        when_to_include=(
            "Required in toll plaza scenarios. One per lane (ETC + ANPR + "
            "gate aggregator)."
        ),
        primary_device_types=("toll_controller",),
        vertical_applicability=_verts(
            Vertical.TRANSPORTATION_ITS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("https",),
        typical_partners=("toll_rsu", "anpr_camera", "scada_primary"),
        examples=("Kapsch TCS 2000",),
    ),

    # =====================================================================
    # BAS terminal-unit roles (Phase 9 audit) — vav, ahu, chiller, etc.
    # were collapsed into bms_field_controller in the refactor; restore
    # them as distinct roles for proper Cyber Vision classification.
    # =====================================================================

    Role(
        id="vav_controller",
        name="VAV Terminal Controller",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Variable Air Volume terminal unit controller. Modulates "
            "supply air to a zone based on temperature setpoint. Part "
            "of every modern commercial HVAC deployment."
        ),
        when_to_include=(
            "Include in commercial-office and university BAS scenarios "
            "with per-zone HVAC. Multiple per zone."
        ),
        primary_device_types=("vav_controller",),
        vertical_applicability=_verts(Vertical.BUILDING_AUTOMATION.value),
        required_protocols=("bacnet", "snmp"),
        optional_protocols=("modbus_tcp",),
        typical_partners=("scada_primary", "bms_field_controller"),
        examples=("Honeywell PUB6438S", "Distech ECY-VAV", "EC-BOS-8"),
    ),

    Role(
        id="ahu_controller",
        name="AHU Controller",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Air Handling Unit controller — dampers, fans, mixing-box, "
            "supply temperature. Coordinates with VAVs downstream."
        ),
        when_to_include=(
            "Include in BAS scenarios with central air handling. One "
            "or more per building zone."
        ),
        primary_device_types=("ahu_controller",),
        vertical_applicability=_verts(Vertical.BUILDING_AUTOMATION.value),
        required_protocols=("bacnet", "snmp"),
        optional_protocols=("modbus_tcp",),
        typical_partners=("scada_primary", "vav_controller", "vfd"),
        examples=("Delta Controls enteliBUS Manager",),
    ),

    Role(
        id="chiller_controller",
        name="Chiller Plant Controller",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Centralized chilled-water plant controller. Stages chillers, "
            "manages pump VFDs, coordinates condenser water and tower fans."
        ),
        when_to_include=(
            "Include in BAS / DCIM scenarios with central cooling plant."
        ),
        primary_device_types=("chiller_controller",),
        vertical_applicability=_verts(
            Vertical.BUILDING_AUTOMATION.value,
            Vertical.DATA_CENTER_INFRA.value,
        ),
        required_protocols=("bacnet", "snmp"),
        optional_protocols=("modbus_tcp",),
        typical_partners=("scada_primary", "vfd", "valve_actuator"),
        examples=("Carel pCO5+", "Honeywell XL Web"),
    ),

    Role(
        id="room_controller",
        name="Room / Zone Controller",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Room-level field controller — combines temperature, "
            "occupancy, lighting, and shading control into one box."
        ),
        when_to_include=(
            "Include in commercial / university BAS scenarios with "
            "fine-grained room control."
        ),
        primary_device_types=("room_controller",),
        vertical_applicability=_verts(Vertical.BUILDING_AUTOMATION.value),
        required_protocols=("bacnet", "snmp"),
        typical_partners=("scada_primary", "bms_field_controller"),
        examples=("Siemens DXR2.E12",),
    ),

    # =====================================================================
    # DCIM power / cooling field equipment.
    # =====================================================================

    Role(
        id="pdu",
        name="Power Distribution Unit",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Rack PDU — branch-circuit metering and outlet-level switching. "
            "SNMP polled by DCIM for per-rack power telemetry."
        ),
        when_to_include=(
            "Required in DCIM scenarios. Multiple per rack row."
        ),
        primary_device_types=("pdu",),
        vertical_applicability=_verts(Vertical.DATA_CENTER_INFRA.value),
        required_protocols=("snmp",),
        optional_protocols=("https",),
        typical_partners=("scada_primary",),
        examples=("Schneider Rack PDU",),
    ),

    Role(
        id="ups_unit",
        name="UPS",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Uninterruptible Power Supply — battery-backed power for "
            "critical IT loads. Reports load, runtime, battery state via "
            "SNMP."
        ),
        when_to_include=(
            "Required in DCIM scenarios. Several per data hall."
        ),
        primary_device_types=("ups",),
        vertical_applicability=_verts(Vertical.DATA_CENTER_INFRA.value),
        required_protocols=("snmp",),
        optional_protocols=("modbus_tcp", "https"),
        typical_partners=("scada_primary", "cell_controller"),
        examples=("Schneider Galaxy VM",),
    ),

    Role(
        id="crac_unit",
        name="CRAC / CRAH Unit",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Computer Room Air Conditioner / Handler. Cools data-hall "
            "racks; reports supply/return temperatures, fan speed, "
            "compressor state."
        ),
        when_to_include=(
            "Required in DCIM scenarios. One or more per cooling zone."
        ),
        primary_device_types=("crac_unit",),
        vertical_applicability=_verts(Vertical.DATA_CENTER_INFRA.value),
        required_protocols=("snmp",),
        optional_protocols=("modbus_tcp", "bacnet"),
        typical_partners=("scada_primary", "chiller_controller"),
        examples=("Schneider InRow DX",),
    ),

    # =====================================================================
    # Distribution / logistics — robotics, identification, vision.
    # =====================================================================

    Role(
        id="agv",
        name="AGV / AMR (Mobile Robot)",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Autonomous Guided / Mobile Robot — moves goods through the "
            "warehouse. Reports position, battery, task state to a fleet "
            "manager. Modern fulfillment floors have many."
        ),
        when_to_include=(
            "Include in distribution scenarios with autonomous material "
            "handling (modern fulfillment, sortation, ASRS retrieval)."
        ),
        primary_device_types=("agv",),
        vertical_applicability=_verts(Vertical.DISTRIBUTION_LOGISTICS.value),
        required_protocols=("https", "snmp"),
        optional_protocols=("mqtt", "rest"),
        typical_partners=("fleet_manager", "scada_primary"),
        examples=("MiR250", "MiR500", "KUKA KMP 600"),
    ),

    Role(
        id="fleet_manager",
        name="Robot Fleet Manager",
        category=RoleCategory.OPERATIONS,
        purdue_level=3.0,
        description=(
            "Centralized AGV / AMR fleet supervisor. Dispatches tasks, "
            "manages traffic / collision avoidance, monitors fleet health."
        ),
        when_to_include=(
            "Required when AGV / AMR are in the scenario. One per site."
        ),
        primary_device_types=("fleet_manager",),
        vertical_applicability=_verts(Vertical.DISTRIBUTION_LOGISTICS.value),
        required_protocols=("https", "snmp"),
        optional_protocols=("mqtt",),
        typical_partners=("agv", "scada_primary"),
        examples=("MiR Fleet", "KUKA.FleetManager"),
    ),

    Role(
        id="barcode_scanner",
        name="Barcode Scanner",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Fixed industrial barcode reader — typically over a conveyor "
            "or at a pick station. Reports reads via Ethernet / TCP."
        ),
        when_to_include=(
            "Include in fulfillment / distribution / parcel-sorting "
            "scenarios — many per zone."
        ),
        primary_device_types=("barcode_scanner",),
        vertical_applicability=_verts(Vertical.DISTRIBUTION_LOGISTICS.value),
        required_protocols=("snmp",),
        optional_protocols=("https", "modbus_tcp"),
        typical_partners=("conveyor_controller", "wcs_controller"),
        examples=("Cognex DataMan 280", "SICK CLV650-0120"),
    ),

    Role(
        id="rfid_reader",
        name="RFID Reader",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Fixed UHF RFID reader — captures tagged carton / pallet IDs "
            "as items pass. Reports reads to WMS via HTTPS / TCP."
        ),
        when_to_include=(
            "Include in distribution-center scenarios (incoming dock, "
            "outbound staging, returns processing)."
        ),
        primary_device_types=("rfid_reader",),
        vertical_applicability=_verts(Vertical.DISTRIBUTION_LOGISTICS.value),
        required_protocols=("snmp",),
        optional_protocols=("https",),
        typical_partners=("wcs_controller",),
        examples=("Impinj Speedway R420", "Zebra FX9600"),
    ),

    # =====================================================================
    # Manufacturing-specific motion / robotics (Phase 9 audit) —
    # robot_controller and cnc_controller are real distinct device
    # classes that the original archetype refactor missed.
    # =====================================================================

    Role(
        id="robot_controller",
        name="Industrial Robot Controller",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Industrial robot controller — articulated 6-axis robots for "
            "welding, assembly, painting, palletizing. Uses vendor-native "
            "fieldbus (PROFINET/Fanuc-FOCAS/EtherNet-IP) plus safety."
        ),
        when_to_include=(
            "Include in cells with robotic automation: weld cells, "
            "robotic assembly, paint booths, palletizing, pick-and-place. "
            "Common in automotive, electronics, packaging."
        ),
        primary_device_types=("robot_controller",),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.DISTRIBUTION_LOGISTICS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=(
            "ethernet_ip", "profinet", "modbus_tcp", "fanuc",
        ),
        typical_partners=("cell_controller", "safety_controller", "vfd"),
        examples=("Fanuc R-30iB Plus", "KUKA KR C4", "ABB IRC5"),
    ),

    Role(
        id="cnc_controller",
        name="CNC Machine Controller",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Computer Numerical Control machine tool controller — milling, "
            "lathe, grinding, EDM. Vendor-native (Fanuc / Siemens / "
            "Heidenhain) over Ethernet, with optional MTConnect feed."
        ),
        when_to_include=(
            "Include in machining cells (CNC mill / lathe / grind), "
            "fab shops, automotive machining lines."
        ),
        primary_device_types=("cnc_controller",),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("ethernet_ip", "profinet", "modbus_tcp"),
        typical_partners=("cell_controller", "servo"),
        examples=("Fanuc 0i-TF Plus",),
    ),

    Role(
        id="vision_system",
        name="Machine Vision System",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Industrial machine-vision camera — inspects part placement, "
            "barcode quality, dimensional checks. Reports pass/fail + "
            "metrology over Ethernet."
        ),
        when_to_include=(
            "Include in fulfillment / sortation / quality-station "
            "scenarios."
        ),
        primary_device_types=("vision_system",),
        vertical_applicability=_verts(
            Vertical.DISTRIBUTION_LOGISTICS.value,
            Vertical.MANUFACTURING_DISCRETE.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("https", "modbus_tcp", "ethernet_ip"),
        typical_partners=("conveyor_controller", "cell_controller"),
        examples=("Cognex In-Sight 7802", "SICK Inspector P631"),
    ),

    # =====================================================================
    # Process analyzers + custody-transfer meters (oil_gas / process mfg).
    # =====================================================================

    Role(
        id="analyzer",
        name="Process Analyzer",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Continuous gas / liquid analyzer — chromatograph, laser "
            "spectrometer, pH/conductivity, etc. Reports compositional "
            "data over Modbus / HART-IP."
        ),
        when_to_include=(
            "Include in oil&gas refinery, LNG terminal, water treatment "
            "(Cl2, fluoride), and pharma scenarios."
        ),
        primary_device_types=("analyzer",),
        vertical_applicability=_verts(
            Vertical.OIL_GAS.value,
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.WATER_UTILITY.value,
            Vertical.ENERGY_GENERATION.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("modbus_tcp", "hart_ip"),
        typical_partners=("dcs_controller", "field_rtu"),
        examples=("Yokogawa GC8000", "Yokogawa TDLS8000",
                  "Endress+Hauser CM442"),
    ),

    Role(
        id="flow_meter",
        name="Custody-Transfer Flow Meter",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Coriolis / mag / ultrasonic flow meter, often used for "
            "custody transfer (oil&gas, distribution). High-accuracy "
            "totalization + supplemental temperature / density."
        ),
        when_to_include=(
            "Include in oil&gas pipeline, refinery, water-distribution "
            "metering scenarios."
        ),
        primary_device_types=("flow_meter",),
        vertical_applicability=_verts(
            Vertical.OIL_GAS.value,
            Vertical.WATER_UTILITY.value,
            Vertical.MANUFACTURING_PROCESS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("modbus_tcp", "hart_ip"),
        typical_partners=("dcs_controller", "field_rtu"),
        examples=("Emerson 5700", "Endress+Hauser Promag 400"),
    ),

    # =====================================================================
    # Power meter (substation / grid revenue metering).
    # =====================================================================

    Role(
        id="power_meter",
        name="Revenue Power Meter",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Revenue-grade electrical power meter — current/voltage/"
            "active/reactive power, harmonics. Polled by SCADA / EMS for "
            "billing-quality data."
        ),
        when_to_include=(
            "Include in substation, grid control center, power-generation, "
            "and large industrial scenarios."
        ),
        primary_device_types=("power_meter",),
        vertical_applicability=_verts(
            Vertical.ENERGY_SUBSTATION.value,
            Vertical.ENERGY_GENERATION.value,
            Vertical.OIL_GAS.value,
            Vertical.MANUFACTURING_PROCESS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("modbus_tcp", "iec61850"),
        typical_partners=("scada_primary", "aggregator_rtu"),
        examples=("Schneider PM8000", "Schneider ION8650"),
    ),

    Role(
        id="rwis_station",
        name="Road Weather Information Station",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "Roadside weather station — wind, temperature, precipitation, "
            "road-surface state. NTCIP-over-SNMP polled by ATMS for "
            "dispatch / DMS messaging."
        ),
        when_to_include=(
            "Include in highway corridors and tunnels with weather-aware "
            "operations."
        ),
        primary_device_types=("weather_station",),
        vertical_applicability=_verts(
            Vertical.TRANSPORTATION_ITS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("ntcip", "https"),
        typical_partners=("scada_primary",),
        examples=("Vaisala RWIS500",),
    ),

    Role(
        id="wcs_controller",
        name="Warehouse Control System PLC",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "PLC running warehouse control system logic — sortation, "
            "ASRS, AGV traffic, conveyor coordination."
        ),
        when_to_include=(
            "Required in distribution_logistics scenarios."
        ),
        primary_device_types=("plc",),
        vertical_applicability=_verts(
            Vertical.DISTRIBUTION_LOGISTICS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("ethernet_ip", "modbus_tcp", "profinet"),
        typical_partners=(
            "conveyor_controller", "vfd", "distributed_io", "scada_primary",
        ),
    ),

    Role(
        id="conveyor_controller",
        name="Conveyor / Sortation PLC",
        category=RoleCategory.BASIC_CONTROL,
        purdue_level=1.0,
        description=(
            "PLC running conveyor or sortation lane. Tight timing "
            "for divert / merge / weigh stations."
        ),
        when_to_include=(
            "Required in distribution_logistics for fulfillment / "
            "parcel-sorting scenarios."
        ),
        primary_device_types=("plc",),
        vertical_applicability=_verts(
            Vertical.DISTRIBUTION_LOGISTICS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("ethernet_ip", "modbus_tcp", "profinet"),
        typical_partners=(
            "wcs_controller", "vfd", "distributed_io", "discrete_sensor",
        ),
    ),

    # =====================================================================
    # PROCESS (L0) — the field. Sensors, drives, valves, IO.
    # =====================================================================

    Role(
        id="distributed_io",
        name="Distributed I/O",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Remote I/O block. Slave to the cell_controller's cyclic "
            "fieldbus (PROFINET IO, EtherNet/IP implicit)."
        ),
        when_to_include=(
            "Include in any cell with field-mounted sensors/actuators "
            "that aren't directly wired to the controller chassis."
        ),
        primary_device_types=("io_module", "distributed_io"),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp",),
        optional_protocols=("profinet", "ethernet_ip", "modbus_tcp"),
        typical_partners=("cell_controller", "safety_controller"),
    ),

    Role(
        id="vfd",
        name="Variable Frequency Drive",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Drive controlling a motor (pump, fan, conveyor, mixer). "
            "Receives speed/torque commands from controller, returns "
            "current/voltage/temperature."
        ),
        when_to_include=(
            "Include in any scenario with motors. Common in "
            "manufacturing, water (pumps), oil_gas (compressors), "
            "BAS (fans)."
        ),
        primary_device_types=("drive", "vfd"),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp",),
        optional_protocols=(
            "profinet", "ethernet_ip", "modbus_tcp",
        ),
        typical_partners=(
            "cell_controller", "safety_controller", "dcs_controller",
            "conveyor_controller", "bms_field_controller",
        ),
    ),

    Role(
        id="servo",
        name="Servo Drive",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "High-precision motion controller for robots, CNC, "
            "pick-and-place. Tight cyclic communication with motion-"
            "capable cell_controller."
        ),
        when_to_include=(
            "Include in discrete manufacturing motion applications: "
            "CNC, robotic cells, packaging."
        ),
        primary_device_types=("servo", "drive"),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
            Vertical.DISTRIBUTION_LOGISTICS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("profinet", "ethernet_ip"),
        typical_partners=("cell_controller", "safety_controller"),
    ),

    Role(
        id="field_instrument",
        name="Field Instrument (Smart Sensor)",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Smart transmitter — temperature, pressure, level, flow. "
            "Often HART-over-Ethernet or Modbus-mapped via gateway."
        ),
        when_to_include=(
            "Include in process verticals (manufacturing_process, oil_gas, "
            "water, energy_generation) and BAS."
        ),
        primary_device_types=(
            "instrument", "sensor", "transmitter", "temperature_controller",
        ),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.OIL_GAS.value,
            Vertical.WATER_UTILITY.value,
            Vertical.ENERGY_GENERATION.value,
            Vertical.BUILDING_AUTOMATION.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("modbus_tcp", "hart_ip", "bacnet"),
        typical_partners=("dcs_controller", "cell_controller", "field_rtu"),
    ),

    Role(
        id="discrete_sensor",
        name="Discrete Sensor",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Limit switch, photoelectric, proximity sensor. Wired to "
            "distributed_io rather than spoken to directly."
        ),
        when_to_include=(
            "Optional; usually represented at the I/O block level "
            "rather than as standalone devices."
        ),
        primary_device_types=("sensor",),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_DISCRETE.value,
            Vertical.DISTRIBUTION_LOGISTICS.value,
        ),
        required_protocols=(),
        optional_protocols=("snmp",),
        typical_partners=("distributed_io", "cell_controller"),
    ),

    Role(
        id="valve_actuator",
        name="Valve Actuator",
        category=RoleCategory.PROCESS,
        purdue_level=0.0,
        description=(
            "Actuated valve — motorized (water/oil), pneumatic "
            "(process), solenoid (small bore). Receives open/close "
            "or modulating setpoint from controller."
        ),
        when_to_include=(
            "Include in process verticals and water/wastewater. "
            "Modeled per major valve when specifically interesting."
        ),
        primary_device_types=("actuator", "valve"),
        vertical_applicability=_verts(
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.OIL_GAS.value,
            Vertical.WATER_UTILITY.value,
            Vertical.ENERGY_GENERATION.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("modbus_tcp", "hart_ip", "profibus_pa"),
        typical_partners=("dcs_controller", "cell_controller", "field_rtu"),
    ),

    # =====================================================================
    # NETWORK INFRASTRUCTURE — spans Purdue layers.
    # =====================================================================

    Role(
        id="core_switch",
        name="Core / Distribution Switch",
        category=RoleCategory.NETWORK_INFRA,
        purdue_level=3.0,
        description=(
            "Plant-core or operations-zone switch. SNMP polled by NMS."
        ),
        when_to_include=(
            "Required: every scenario has at least one. The L3 spine."
        ),
        primary_device_types=("switch",),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp",),
        optional_protocols=("https", "ssh"),
        typical_partners=("nms_server", "jump_server"),
    ),

    Role(
        id="cell_switch",
        name="Cell / Area Switch",
        category=RoleCategory.NETWORK_INFRA,
        purdue_level=2.0,
        description=(
            "Per-cell or per-area access switch. Often industrial-"
            "hardened (Stratix, Scalance, Hirschmann)."
        ),
        when_to_include=(
            "Include one per cell in cell-based topologies."
        ),
        primary_device_types=("switch",),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp",),
        optional_protocols=("https", "ssh"),
        typical_partners=("nms_server", "core_switch"),
    ),

    Role(
        id="bay_switch",
        name="Bay-Level Switch",
        category=RoleCategory.NETWORK_INFRA,
        purdue_level=1.0,
        description=(
            "Substation bay / process-skid switch. Hardened. Often "
            "supports PRP/HSR for protection-grade redundancy."
        ),
        when_to_include=(
            "Include in energy_substation (per bay) and large "
            "manufacturing_process scenarios (per skid)."
        ),
        primary_device_types=("switch",),
        vertical_applicability=_verts(
            Vertical.ENERGY_SUBSTATION.value,
            Vertical.MANUFACTURING_PROCESS.value,
            Vertical.OIL_GAS.value,
        ),
        required_protocols=("snmp",),
        optional_protocols=("https", "ssh"),
        typical_partners=(
            "nms_server", "core_switch", "protection_relay",
            "aggregator_rtu",
        ),
    ),

    Role(
        id="wan_edge_router",
        name="WAN Edge Router",
        category=RoleCategory.NETWORK_INFRA,
        purdue_level=3.5,
        description=(
            "Site WAN edge — typically MPLS / cellular / satellite "
            "uplink. Egress for IDMZ traffic, ingress for vendor "
            "remote access."
        ),
        when_to_include=(
            "Include in any scenario with WAN connectivity (most). "
            "Optional for fully air-gapped demo scenarios."
        ),
        primary_device_types=("router", "switch"),
        vertical_applicability=_ALL_VERTS,
        required_protocols=("snmp",),
        optional_protocols=("https", "ssh"),
        typical_partners=("nms_server", "remote_access_gateway"),
    ),
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_ROLES_BY_ID: dict[str, Role] = {r.id: r for r in _ROLES}

# Sanity check: no duplicates at import time.
if len(_ROLES_BY_ID) != len(_ROLES):
    seen: set[str] = set()
    dupes: list[str] = []
    for r in _ROLES:
        if r.id in seen:
            dupes.append(r.id)
        seen.add(r.id)
    raise RuntimeError(
        f"Duplicate role IDs in role catalog: {dupes}"
    )


def get_role(role_id: str) -> Role | None:
    """Look up a role by ID."""
    return _ROLES_BY_ID.get(role_id)


def list_roles() -> tuple[Role, ...]:
    """All roles in catalog order (IDMZ → operations → area → control →
    process → network infra)."""
    return _ROLES


def list_roles_for_vertical(vertical: str) -> tuple[Role, ...]:
    """Roles applicable to the given vertical (in catalog order)."""
    return tuple(r for r in _ROLES if r.applies_to(vertical))


def list_roles_at_purdue_level(level: float) -> tuple[Role, ...]:
    """Roles at a specific Purdue level (e.g. 3.5 for IDMZ, 1.0 for L1)."""
    return tuple(r for r in _ROLES if r.purdue_level == level)


def list_roles_by_category(category: RoleCategory) -> tuple[Role, ...]:
    """Roles in a category (IDMZ, OPERATIONS, ...)."""
    return tuple(r for r in _ROLES if r.category == category)


def role_ids_for_device_type(
    device_type: str,
    vertical: str | None = None,
) -> tuple[str, ...]:
    """Roles that legitimately fulfill a given device.type. When `vertical`
    is provided, filter to roles applicable in that vertical.

    Used when a template author has only declared `device.type` (no
    explicit role) — the validator can warn if the implied role set is
    ambiguous, or pick a default.
    """
    out: list[str] = []
    for r in _ROLES:
        if device_type in r.primary_device_types:
            if vertical is None or r.applies_to(vertical):
                out.append(r.id)
    return tuple(out)


def required_protocols_for(
    role_ids: Iterable[str],
) -> frozenset[str]:
    """Union of required protocols across the given roles."""
    out: set[str] = set()
    for rid in role_ids:
        r = _ROLES_BY_ID.get(rid)
        if r:
            out.update(r.required_protocols)
    return frozenset(out)


# Default architectural role per device_type. Used by legacy scenario
# templates (pre-role-catalog) so role-aware readiness / audit checks
# work without forcing every template author to hand-stamp roles.
#
# Conservative mapping: prefer the most common interpretation. A `plc`
# without other context becomes a `cell_controller`, not an
# `area_supervisor_plc`. Ambiguous types (server, appliance) return None.
_DEFAULT_ROLE_BY_TYPE: dict[str, str] = {
    # Controllers
    "plc": "cell_controller",
    "safety_plc": "safety_controller",
    "dcs_controller": "dcs_controller",
    "rtu": "field_rtu",
    "robot_controller": "robot_controller",
    "cnc_controller": "cnc_controller",
    "batch_controller": "batch_controller",
    "agv_controller": "agv",
    "fleet_manager": "fleet_manager",
    "wellhead_controller": "field_rtu",
    "compressor_controller": "dcs_controller",
    "pump_controller": "field_rtu",
    "leak_detection": "field_rtu",
    "flow_computer": "field_rtu",
    "wcs_controller": "wcs_controller",
    "conveyor_controller": "conveyor_controller",
    "sortation_controller": "conveyor_controller",
    "protection_relay": "protection_relay",
    # Supervisory
    "hmi": "area_hmi",
    "scada": "scada_primary",
    "scada_server": "scada_primary",
    "engineering_station": "engineering_workstation",
    "engineering_workstation": "engineering_workstation",
    "operator_station": "scada_primary",
    "workstation": "engineering_workstation",
    "master_station": "scada_primary",
    "alarm_event_server": "alarm_event_server",
    "batch_server": "batch_server",
    "mes_server": "mes_server",
    # Operations / IDMZ
    "historian": "process_historian",
    "jump_server": "jump_server",
    "domain_controller": "ot_domain_controller",
    "patch_server": "patch_staging_server",
    "asset_management": "asset_management_server",
    "nms": "nms_server",
    "av_server": "av_management_server",
    "edr_server": "av_management_server",
    "reverse_proxy": "reverse_proxy",
    "remote_access_gateway": "remote_access_gateway",
    # Field instruments
    "io_module": "distributed_io",
    "safety_io": "distributed_io",
    "sensor": "discrete_sensor",
    "discrete_sensor": "discrete_sensor",
    "actuator": "valve_actuator",
    "valve_positioner": "valve_actuator",
    "pressure_transmitter": "field_instrument",
    "flow_transmitter": "flow_meter",
    "flow_meter": "flow_meter",
    "level_transmitter": "field_instrument",
    "temperature_transmitter": "field_instrument",
    "temperature_controller": "field_instrument",
    "field_instrument": "field_instrument",
    "process_analyzer": "analyzer",
    "gas_chromatograph": "analyzer",
    "analyzer": "analyzer",
    "custody_meter": "flow_meter",
    "power_meter": "power_meter",
    "energy_meter": "power_meter",
    "meter": "power_meter",
    "relay": "protection_relay",
    "weigh_scale": "field_instrument",
    "drive": "vfd",
    "servo": "servo",
    # Vision / scanning / robotics
    "vision_system": "vision_system",
    "barcode_scanner": "barcode_scanner",
    "rfid_reader": "rfid_reader",
    "rfid_gateway": "rfid_reader",
    "agv": "agv",
    "amr": "agv",
    "pick_to_light": "discrete_sensor",
    "label_applicator": "discrete_sensor",
    # Building automation
    "ahu_controller": "ahu_controller",
    "ahu_unit": "ahu_controller",
    "rooftop_unit": "ahu_controller",
    "boiler_controller": "ahu_controller",
    "vav_controller": "vav_controller",
    "chiller_controller": "chiller_controller",
    "chiller": "chiller_controller",
    "room_controller": "room_controller",
    "zone_controller": "room_controller",
    "thermostat": "room_controller",
    "bms_controller": "bms_field_controller",
    "building_controller": "bms_field_controller",
    "bms_server": "scada_primary",
    "niagara_jace": "bms_field_controller",
    "webctrl": "scada_primary",
    "metasys": "scada_primary",
    "tracer": "bms_field_controller",
    "access_panel": "cabinet_controller",
    "access_controller": "cabinet_controller",
    "crac_unit": "crac_unit",
    "cold_storage_controller": "room_controller",
    # ITS / transportation
    "traffic_controller": "traffic_controller",
    "tunnel_controller": "cabinet_controller",
    "lighting_controller": "cabinet_controller",
    "ventilation_controller": "cabinet_controller",
    "fire_panel": "cabinet_controller",
    "barrier_controller": "cabinet_controller",
    "detector_rack": "cabinet_controller",
    "dms": "dms_sign",
    "dynamic_message_sign": "dms_sign",
    "radar_sensor": "discrete_sensor",
    "thermal_sensor": "discrete_sensor",
    "seismic_sensor": "discrete_sensor",
    "chem_sensor": "discrete_sensor",
    "classification_sensor": "discrete_sensor",
    "weather_station": "rwis_station",
    "toll_system": "toll_lane_controller",
    "toll_controller": "toll_lane_controller",
    "toll_host": "toll_lane_controller",
    "lane_controller": "toll_lane_controller",
    "rsu": "toll_rsu",
    "roadside_unit": "toll_rsu",
    "its_camera": "cctv_camera",
    "camera": "cctv_camera",
    "ptz_camera": "ptz_camera",
    "anpr_camera": "anpr_camera",
    "video_detector": "cctv_camera",
    # Network infra
    "switch": "cell_switch",
    "core_switch": "core_switch",
    "cell_switch": "cell_switch",
    "bay_switch": "bay_switch",
    "gateway": "wan_edge_router",
    "firewall": "wan_edge_router",
    "router": "wan_edge_router",
    "ups": "ups_unit",
    "pdu": "pdu",
    # Ambiguous — caller must supply role explicitly
    "server": None,
    "appliance": None,
}


def default_role_for_device_type(device_type: str | None) -> str | None:
    """Return a default architectural role for a device_type.

    Returns None if the device_type is unknown or maps to an ambiguous
    bucket (e.g. "server"). Callers should treat None as "leave role
    unset rather than guess wrong."
    """
    if not device_type:
        return None
    return _DEFAULT_ROLE_BY_TYPE.get(device_type.lower())
