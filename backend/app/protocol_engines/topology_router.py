# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Topology segment router — the "render-many" half of generate-once/render-many.

Consumes the canonical packet stream (built once by the engines) plus a
topology plan (from ``services.topology_planner``) and, per packet, returns the
per-SPAN reframed copies: the same L3/L4 payload with only the L2 headers
rewritten (src/dst MAC, 802.1Q tag) and the IP TTL adjusted per segment.

Pure transform, no I/O — the same instance drives both the PCAP path
(``output.SpanPcapOutput``) and the live conductor (agent, Phase 3). It lives
in ``protocol_engines`` so the agent build stages it in; changes here MUST bump
``docker/packetarch-agent/app/version.py``.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TopologyRouter:
    """Map one canonical frame to its per-SPAN reframed copies.

    ``plan`` is the dict produced by ``TopologyPlan.as_dict()`` /
    ``topology_planner.preview()``.
    """

    def __init__(self, plan: dict[str, Any]) -> None:
        self._flow_plans: dict[str, dict[str, Any]] = plan.get("flow_plans", {}) or {}
        index = plan.get("endpoint_index") or {}
        self._ip_to_zone: dict[str, str] = index.get("ip_to_zone", {}) or {}
        self._mac_to_zone: dict[str, str] = index.get("mac_to_zone", {}) or {}
        # Every span id the plan knows about (for fan-out sinks to pre-create).
        self.span_ids: list[str] = [s["id"] for s in (plan.get("spans") or []) if s.get("id")]
        self._unplanned_logged: set[str] = set()

    # -- public API --------------------------------------------------------

    def route(self, packet_bytes: bytes, flow_id: str | None) -> list[tuple[str, bytes]]:
        """Return ``[(span_id, reframed_bytes), ...]`` for one canonical frame.

        A planned flow is reframed onto each segment of its path (direction
        chosen from the packet's own IPs). Frames with no plan (ambient
        ARP/LLDP, attack, unplanned) fall back to the L2-scope rule: emit
        untouched onto the SPAN(s) of the zone(s) their endpoints belong to.
        """
        plan = self._flow_plans.get(flow_id) if flow_id else None
        if plan is not None:
            return self._route_planned(packet_bytes, plan)
        return self._route_unplanned(packet_bytes, flow_id)

    # -- planned flows -----------------------------------------------------

    def _route_planned(self, packet_bytes: bytes, plan: dict[str, Any]) -> list[tuple[str, bytes]]:
        from scapy.layers.inet import IP

        src_ip = plan.get("source_ip") or ""
        forward = True
        try:
            pkt = IP(self._strip_l2(packet_bytes))
            if hasattr(pkt, "src") and src_ip and pkt.src.lower() != src_ip:
                forward = False
        except Exception:
            forward = True  # non-IP planned flow shouldn't happen; default fwd
        segments = plan["segments_forward"] if forward else plan["segments_reverse"]
        out = []
        for seg in segments:
            reframed = _reframe(packet_bytes, seg)
            if reframed is not None:
                out.append((seg["span"], reframed))
        return out

    # -- unplanned / ambient / attack -------------------------------------

    def _route_unplanned(self, packet_bytes: bytes, flow_id: str | None) -> list[tuple[str, bytes]]:
        from scapy.layers.inet import IP
        from scapy.layers.l2 import ARP, Ether

        zones: set[str] = set()
        try:
            eth = Ether(packet_bytes)
            if eth.haslayer(ARP):
                arp = eth[ARP]
                for ip in (getattr(arp, "psrc", None), getattr(arp, "pdst", None)):
                    z = self._ip_to_zone.get((ip or "").lower())
                    if z:
                        zones.add(z)
            elif eth.haslayer(IP):
                ip = eth[IP]
                for addr in (ip.src, ip.dst):
                    z = self._ip_to_zone.get((addr or "").lower())
                    if z:
                        zones.add(z)
            # L2-only (no IP/ARP): fall back to MAC index
            if not zones:
                for mac in (getattr(eth, "src", None), getattr(eth, "dst", None)):
                    z = self._mac_to_zone.get((mac or "").lower())
                    if z:
                        zones.add(z)
        except Exception:
            pass

        if not zones:
            key = (flow_id or "?").split("_")[0]
            if key not in self._unplanned_logged:
                logger.debug("TopologyRouter: no zone for unplanned frame (flow=%s)", flow_id)
                self._unplanned_logged.add(key)
            return []
        # Emit untouched (true MACs) on each involved zone SPAN.
        return [(f"zone:{z}", packet_bytes) for z in sorted(zones)]

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _strip_l2(packet_bytes: bytes) -> bytes:
        """Return the L3 payload bytes (past Ether + any Dot1Q)."""
        from scapy.layers.l2 import Dot1Q, Ether

        eth = Ether(packet_bytes)
        l3 = eth.payload
        while isinstance(l3, Dot1Q):
            l3 = l3.payload
        return bytes(l3)


def _reframe(packet_bytes: bytes, seg: dict[str, Any]) -> bytes | None:
    """Rewrite L2 (MAC + optional 802.1Q) and adjust IP TTL for one segment."""
    from scapy.layers.inet import IP
    from scapy.layers.l2 import Dot1Q, Ether

    try:
        eth = Ether(packet_bytes)
    except Exception:
        return None

    # Descend to the real L3 payload, dropping any pre-existing VLAN tag.
    l3 = eth.payload
    while isinstance(l3, Dot1Q):
        l3 = l3.payload

    if l3.haslayer(IP):
        ip = l3[IP]
        delta = int(seg.get("ttl_delta") or 0)
        if delta:
            ip.ttl = max(1, int(ip.ttl) + delta)
        # Force checksum recompute (TTL changed) on serialize.
        if hasattr(ip, "chksum"):
            del ip.chksum

    new_eth = Ether(src=seg["src_mac"], dst=seg["dst_mac"])
    vlan = seg.get("vlan")
    frame = new_eth / Dot1Q(vlan=int(vlan)) / l3 if vlan is not None else new_eth / l3
    return bytes(frame)
