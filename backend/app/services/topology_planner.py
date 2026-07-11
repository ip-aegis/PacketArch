# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Multi-sensor topology planner (pure functions, no I/O).

Derives an L1 topology from a scenario definition — one Cisco IE3500
aggregation switch per zone, one IE9320 core whose per-zone SVIs are the
zone gateways — and plans, for every flow, the ordered list of SPAN
segments it traverses with the exact per-segment L2 framing (src/dst MAC,
802.1Q tag, TTL delta).

Semantics (see tasks/multi-sensor-topology-design.md):
- Every zone boundary is an L3 boundary; the core routes between zones.
- Intra-zone flows appear on one zone SPAN with the devices' true MACs,
  untagged.
- Cross-zone flows appear on the source zone SPAN, the core SPAN (both
  framings), and the target zone SPAN; IPs are preserved end-to-end while
  MACs are rewritten per segment and TTL decrements across the core.
- L2-only protocols (PROFINET RT, GOOSE, SV) cannot cross an L3 boundary;
  a cross-zone L2-only flow is a planning error, not a silent drop.
"""

import hashlib
import ipaddress
from dataclasses import dataclass, field
from typing import Any

from app.protocol_engines.vendor_oui import VENDOR_OUI_PREFIXES

# Flow protocols that exist only at Layer 2 and cannot traverse a router.
L2_ONLY_PROTOCOLS = {"profinet", "goose", "sv"}

ZONE_SWITCH_TEMPLATE = "cisco/ie3500/8p3s"
CORE_SWITCH_TEMPLATE = "cisco/ie9320/26s2c"

CORE_SPAN = "core"

# Host conventions within a zone /24 (gateway .1, devices start at .10).
SWITCH_MGMT_HOST = 2


@dataclass
class PlanIssue:
    code: str
    message: str
    subject_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "subject_id": self.subject_id}


@dataclass
class TopologyPlan:
    errors: list[PlanIssue] = field(default_factory=list)
    warnings: list[PlanIssue] = field(default_factory=list)
    switches: dict[str, dict[str, Any]] = field(default_factory=dict)  # zone_id -> switch
    core: dict[str, Any] | None = None
    links: list[dict[str, Any]] = field(default_factory=list)
    spans: list[dict[str, Any]] = field(default_factory=list)
    flow_plans: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Endpoint → zone index for routing frames that carry no flow_id plan
    # (ambient ARP/LLDP, unplanned/attack packets). Keyed by lowercased IP/MAC.
    endpoint_index: dict[str, dict[str, str]] = field(
        default_factory=lambda: {"ip_to_zone": {}, "mac_to_zone": {}}
    )

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [e.as_dict() for e in self.errors],
            "warnings": [w.as_dict() for w in self.warnings],
            "switches": self.switches,
            "core": self.core,
            "links": self.links,
            "spans": self.spans,
            "flow_plans": self.flow_plans,
            "endpoint_index": self.endpoint_index,
        }


# ---------------------------------------------------------------------------
# Definition access helpers (defensive: camelCase with snake_case fallbacks,
# dict-keyed or list-shaped collections — mirrors conduit_compliance.py)
# ---------------------------------------------------------------------------


def _as_dict(collection: Any) -> dict[str, dict[str, Any]]:
    """Normalize a devices/zones/flows collection to a dict keyed by id."""
    if isinstance(collection, dict):
        return collection
    if isinstance(collection, list):
        return {item.get("id"): item for item in collection if isinstance(item, dict) and item.get("id")}
    return {}


def _device_zone(device_id: str, device: dict[str, Any], zones: dict[str, dict[str, Any]]) -> list[str]:
    """All zones claiming this device (device key first, then zone membership)."""
    claimed: list[str] = []
    own = device.get("zoneId") or device.get("zone_id") or device.get("zone")
    if own and own in zones:
        claimed.append(own)
    for zid, zone in zones.items():
        member_ids = zone.get("deviceIds", zone.get("device_ids", [])) or []
        if device_id in member_ids and zid not in claimed:
            claimed.append(zid)
    return claimed


def _zone_vlan(zone: dict[str, Any], fallback: int) -> int:
    net = zone.get("network") or {}
    for candidate in (net.get("vlan"), net.get("vlanId"), zone.get("vlan"), zone.get("vlanId")):
        if candidate is not None:
            try:
                return int(candidate)
            except (TypeError, ValueError):
                continue
    return fallback


def _zone_network(
    zone: dict[str, Any], zone_devices: list[dict[str, Any]]
) -> tuple[str, str] | None:
    """(subnet_cidr, gateway_ip) for a zone, or None if underivable.

    Prefers explicit zone.network; falls back to the IP-management
    convention (shared /24, gateway .1) when every zone device agrees.
    """
    net = zone.get("network") or {}
    subnet = net.get("subnet")
    gateway = net.get("gateway")
    if subnet and gateway:
        return subnet, gateway
    if subnet and not gateway:
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            return subnet, str(network.network_address + 1)
        except ValueError:
            return None

    subnets = set()
    for device in zone_devices:
        ip = (device.get("network") or {}).get("ipAddress")
        if not ip:
            continue
        try:
            subnets.add(ipaddress.ip_network(f"{ip}/24", strict=False))
        except ValueError:
            continue
    if len(subnets) == 1:
        network = subnets.pop()
        return str(network), str(network.network_address + 1)
    return None


def _deterministic_mac(seed: str, key: str) -> str:
    """Cisco-OUI MAC derived from (seed, key) — stable across runs."""
    ouis = VENDOR_OUI_PREFIXES.get("cisco") or ["00:00:0C"]
    digest = hashlib.sha256(f"{seed}:{key}".encode()).digest()
    oui = ouis[digest[0] % len(ouis)]
    return f"{oui}:{digest[1]:02X}:{digest[2]:02X}:{digest[3]:02X}".lower()


def _host_ip(subnet: str, host: int) -> str | None:
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        return str(network.network_address + host)
    except ValueError:
        return None


def _safe_name(raw: str) -> str:
    cleaned = "".join(c if c.isalnum() else "_" for c in raw).strip("_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned or "Zone"


# ---------------------------------------------------------------------------
# Topology derivation
# ---------------------------------------------------------------------------


def derive_topology(definition: dict[str, Any], seed: str = "") -> TopologyPlan:
    """Derive the L1 topology: per-zone IE3500 + IE9320 core with SVIs.

    Pure function; ``seed`` (normally the scenario id) makes every generated
    MAC deterministic. Validation problems land in plan.errors/warnings —
    preview-time feedback, never silent defaults.

    Editable overrides (persisted on the scenario as ``topology_overrides``):
      - ``zone_switch_template``   — default switch model for every zone
      - ``zone_switch_templates``  — {zone_id: template_id} per-zone override
      - ``core_template``          — core aggregation switch model
    Absent keys fall back to the IE3500 / IE9320 defaults.
    """
    plan = TopologyPlan()
    zones = _as_dict(definition.get("zones"))
    devices = _as_dict(definition.get("devices"))
    overrides = definition.get("topology_overrides") or {}
    default_sw_tpl = overrides.get("zone_switch_template") or ZONE_SWITCH_TEMPLATE
    per_zone_sw_tpl = overrides.get("zone_switch_templates") or {}
    core_tpl = overrides.get("core_template") or CORE_SWITCH_TEMPLATE

    if not zones:
        plan.errors.append(PlanIssue("NO_ZONES", "Scenario has no zones; topology mode needs at least one."))
        return plan

    # --- Device membership validation -------------------------------------
    # Synthetic topology infra (the switches/core THIS planner materializes on
    # a prior pass) is skipped here — it is not an endpoint that needs a switch,
    # and it must not self-link. It still flows through plan_segments +
    # endpoint_index so its own management traffic is routed.
    zone_members: dict[str, list[str]] = {zid: [] for zid in zones}
    for device_id, device in devices.items():
        if device.get("_topology_synthetic"):
            continue
        claimed = _device_zone(device_id, device, zones)
        name = device.get("name", device_id)
        if not claimed:
            plan.errors.append(
                PlanIssue("UNZONED_DEVICE", f"Device '{name}' is in no zone; every device needs exactly one.", device_id)
            )
        elif len(claimed) > 1:
            plan.errors.append(
                PlanIssue("MULTI_ZONE_DEVICE", f"Device '{name}' is claimed by zones {claimed}; only one allowed.", device_id)
            )
        else:
            zone_members[claimed[0]].append(device_id)

    # --- Zone networks, VLANs, switches ------------------------------------
    single_zone = len(zones) == 1
    ordered_zone_ids = sorted(zones)
    for index, zone_id in enumerate(ordered_zone_ids):
        zone = zones[zone_id]
        zone_name = zone.get("name", zone_id)
        members = [devices[d] for d in zone_members[zone_id]]
        network = _zone_network(zone, members)
        if network is None:
            plan.errors.append(
                PlanIssue(
                    "ZONE_NETWORK_UNDERIVABLE",
                    f"Zone '{zone_name}' has no subnet/gateway and its devices don't share one /24.",
                    zone_id,
                )
            )
            continue
        subnet, gateway = network
        vlan = _zone_vlan(zone, fallback=100 + index)
        switch_id = f"topo-sw-{zone_id}"
        sw_template = per_zone_sw_tpl.get(zone_id) or default_sw_tpl
        sw_short = sw_template.split("/")[1].upper() if "/" in sw_template else "SW"
        plan.switches[zone_id] = {
            "id": switch_id,
            "name": f"{_safe_name(zone_name)}_SW_{sw_short}",
            "template_id": sw_template,
            "zone_id": zone_id,
            "mgmt_ip": _host_ip(subnet, SWITCH_MGMT_HOST),
            "mac": _deterministic_mac(seed, f"switch:{zone_id}"),
            "vlan": vlan,
            "subnet": subnet,
            "gateway": gateway,
            "span": f"zone:{zone_id}",
        }
        plan.spans.append({"id": f"zone:{zone_id}", "zone_id": zone_id, "vlan": vlan})
        for device_id in zone_members[zone_id]:
            plan.links.append({"a": device_id, "b": switch_id, "kind": "access"})

    if plan.errors:
        return plan

    # --- Core (skipped for the degenerate single-zone case) ----------------
    if single_zone:
        plan.warnings.append(
            PlanIssue(
                "SINGLE_ZONE_DEGENERATE",
                "One zone: no core is created — this collapses to a single local sensor lab.",
            )
        )
        return plan

    svis = {}
    for zone_id in ordered_zone_ids:
        switch = plan.switches[zone_id]
        svis[zone_id] = {
            "ip": switch["gateway"],
            "mac": _deterministic_mac(seed, f"svi:{zone_id}"),
            "vlan": switch["vlan"],
        }
    # Core management rides the SVI of the highest-Purdue-level zone.
    def _level(zid: str) -> float:
        try:
            return float(zones[zid].get("level") or 0)
        except (TypeError, ValueError):
            return 0.0

    mgmt_zone = max(ordered_zone_ids, key=_level)
    core_short = core_tpl.split("/")[1].upper() if "/" in core_tpl else "SW"
    plan.core = {
        "id": "topo-core",
        "name": f"Core_SW_{core_short}",
        "template_id": core_tpl,
        "mgmt_ip": svis[mgmt_zone]["ip"],
        "mac": _deterministic_mac(seed, "core"),
        "svis": svis,
        "span": CORE_SPAN,
    }
    plan.spans.append({"id": CORE_SPAN, "zone_id": None, "vlan": None})
    for zone_id in ordered_zone_ids:
        plan.links.append({"a": plan.switches[zone_id]["id"], "b": "topo-core", "kind": "trunk"})
    return plan


# ---------------------------------------------------------------------------
# Per-flow segment planning
# ---------------------------------------------------------------------------


def _segment(span: str, src_mac: str, dst_mac: str, vlan: int | None, ttl_delta: int) -> dict[str, Any]:
    return {"span": span, "src_mac": src_mac, "dst_mac": dst_mac, "vlan": vlan, "ttl_delta": ttl_delta}


def plan_segments(definition: dict[str, Any], plan: TopologyPlan) -> TopologyPlan:
    """Attach per-flow segment plans (forward + reverse framing) to ``plan``.

    Requires a valid derive_topology() result. Flows whose endpoints lack
    network identity are skipped with a warning; cross-zone L2-only flows
    are errors (an L2 frame cannot cross the routed core).
    """
    if not plan.valid:
        return plan
    zones = _as_dict(definition.get("zones"))
    devices = _as_dict(definition.get("devices"))
    flows = _as_dict(definition.get("flows"))
    core_svis = (plan.core or {}).get("svis", {})

    device_zone: dict[str, str] = {}
    for device_id, device in devices.items():
        claimed = _device_zone(device_id, device, zones)
        if len(claimed) == 1:
            device_zone[device_id] = claimed[0]
            net = device.get("network") or {}
            ip = (net.get("ipAddress") or "").lower()
            mac = (net.get("macAddress") or "").lower()
            if ip:
                plan.endpoint_index["ip_to_zone"][ip] = claimed[0]
            if mac:
                plan.endpoint_index["mac_to_zone"][mac] = claimed[0]

    for flow_id, flow in flows.items():
        src_id = flow.get("sourceDeviceId") or flow.get("source_device_id")
        dst_id = flow.get("targetDeviceId") or flow.get("target_device_id")
        protocol = (flow.get("protocol") or "").lower()
        flow_name = flow.get("name", flow_id)

        src = devices.get(src_id)
        dst = devices.get(dst_id)
        if not src or not dst:
            plan.warnings.append(
                PlanIssue("UNKNOWN_FLOW_ENDPOINT", f"Flow '{flow_name}' references a missing device; skipped.", flow_id)
            )
            continue
        src_net, dst_net = src.get("network") or {}, dst.get("network") or {}
        src_mac = (src_net.get("macAddress") or "").lower()
        dst_mac = (dst_net.get("macAddress") or "").lower()
        src_ip = (src_net.get("ipAddress") or "").lower()
        dst_ip = (dst_net.get("ipAddress") or "").lower()
        if not src_mac or not dst_mac:
            plan.warnings.append(
                PlanIssue("DEVICE_MISSING_NET", f"Flow '{flow_name}' endpoint lacks a MAC; skipped.", flow_id)
            )
            continue
        src_zone = device_zone.get(src_id)
        dst_zone = device_zone.get(dst_id)
        if src_zone is None or dst_zone is None:
            continue  # membership errors already reported by derive_topology

        if src_zone == dst_zone:
            span = f"zone:{src_zone}"
            forward = [_segment(span, src_mac, dst_mac, None, 0)]
            reverse = [_segment(span, dst_mac, src_mac, None, 0)]
            plan.flow_plans[flow_id] = {
                "kind": "intra",
                "source_zone": src_zone,
                "target_zone": dst_zone,
                "source_ip": src_ip,
                "target_ip": dst_ip,
                "segments_forward": forward,
                "segments_reverse": reverse,
            }
            continue

        if protocol in L2_ONLY_PROTOCOLS:
            plan.errors.append(
                PlanIssue(
                    "L2_CROSS_ZONE",
                    f"Flow '{flow_name}' ({protocol}) is Layer-2-only and cannot cross the routed zone "
                    f"boundary — co-locate both endpoints in one zone.",
                    flow_id,
                )
            )
            continue

        svi_a, svi_b = core_svis[src_zone], core_svis[dst_zone]
        vlan_a, vlan_b = svi_a["vlan"], svi_b["vlan"]
        forward = [
            _segment(f"zone:{src_zone}", src_mac, svi_a["mac"], vlan_a, 0),
            _segment(CORE_SPAN, src_mac, svi_a["mac"], vlan_a, 0),
            _segment(CORE_SPAN, svi_b["mac"], dst_mac, vlan_b, -1),
            _segment(f"zone:{dst_zone}", svi_b["mac"], dst_mac, vlan_b, -1),
        ]
        reverse = [
            _segment(f"zone:{dst_zone}", dst_mac, svi_b["mac"], vlan_b, 0),
            _segment(CORE_SPAN, dst_mac, svi_b["mac"], vlan_b, 0),
            _segment(CORE_SPAN, svi_a["mac"], src_mac, vlan_a, -1),
            _segment(f"zone:{src_zone}", svi_a["mac"], src_mac, vlan_a, -1),
        ]
        plan.flow_plans[flow_id] = {
            "kind": "cross",
            "source_zone": src_zone,
            "target_zone": dst_zone,
            "source_ip": src_ip,
            "target_ip": dst_ip,
            "segments_forward": forward,
            "segments_reverse": reverse,
        }

    return plan


def preview(definition: dict[str, Any], seed: str = "") -> dict[str, Any]:
    """derive_topology + plan_segments in one call; JSON-ready dict."""
    plan = derive_topology(definition, seed=seed)
    plan = plan_segments(definition, plan)
    return plan.as_dict()
