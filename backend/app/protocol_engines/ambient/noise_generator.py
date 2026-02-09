"""Background noise generator for realistic ambient network traffic.

Generates gratuitous ARP, NTP queries, LLDP advertisements, STP BPDUs,
DHCP boot sequences, BACnet discovery, PROFINET DCP multicasts,
SNMP traps, CDP frames, and IGMP reports that real OT networks always have.

Registered with UnifiedOrchestrator as a composition peer alongside
AdaptiveController and AttackOrchestrator.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

from app.protocol_engines.ambient.arp import build_gratuitous_arp
from app.protocol_engines.ambient.ntp import build_ntp_query, build_ntp_response
from app.protocol_engines.types import PacketEvent

logger = logging.getLogger(__name__)


# ======================================================================
# Data classes
# ======================================================================


@dataclass
class AmbientDevice:
    """A device that participates in background noise.

    All new fields have defaults so existing code that constructs
    ``AmbientDevice(device_id, mac_address, ip_address, gateway_ip)``
    continues to work without modification.
    """

    device_id: str
    mac_address: str
    ip_address: str
    gateway_ip: str | None = None

    # Protocol / role metadata for filtering broadcast types
    protocols: list[str] = field(default_factory=list)
    device_type: str = ""          # "plc", "switch", "hmi", "sensor", etc.
    vendor: str = ""               # "Siemens", "Cisco", etc.
    device_name: str = ""          # human-readable name for LLDP/CDP

    # Zone context
    zone_id: str | None = None
    vlan_id: int | None = None
    purdue_level: int | None = None

    # Optional fingerprint for protocol-specific builders
    vendor_fingerprint: dict[str, Any] = field(default_factory=dict)


@dataclass
class AmbientConfig:
    """Configuration for background noise generation."""

    enabled: bool = True

    # -- Existing --
    arp_gratuitous_interval_s: float = 300.0  # 5 minutes
    ntp_interval_s: float = 64.0
    ntp_server_ip: str | None = None
    ntp_server_mac: str = "02:00:00:00:00:01"

    # -- Broadcast types --
    lldp_enabled: bool = True
    lldp_interval_s: float = 30.0
    stp_enabled: bool = True
    stp_hello_s: float = 2.0
    dhcp_enabled: bool = True          # one-shot at boot
    bacnet_whois_enabled: bool = True
    bacnet_whois_interval_s: float = 600.0  # 10 minutes
    profinet_dcp_enabled: bool = True
    profinet_dcp_interval_s: float = 120.0  # 2 minutes
    snmp_trap_enabled: bool = True     # coldStart one-shot at boot
    igmp_enabled: bool = True
    igmp_interval_s: float = 125.0
    cdp_enabled: bool = True
    cdp_interval_s: float = 60.0


# ======================================================================
# Main generator
# ======================================================================


class BackgroundNoiseGenerator:
    """Generates ambient network traffic.

    Follows the composition pattern used by AdaptiveController and
    AttackOrchestrator — schedules events on the shared event heap
    and handles them when dispatched by the orchestrator.
    """

    def __init__(
        self,
        devices: list[AmbientDevice],
        config: AmbientConfig | None = None,
    ) -> None:
        self.devices = devices
        self.config = config or AmbientConfig()
        self._device_map: dict[str, AmbientDevice] = {
            d.device_id: d for d in devices
        }
        # Zone lookup for broadcast responses
        self._zone_devices: dict[str | None, list[AmbientDevice]] = {}
        for d in devices:
            self._zone_devices.setdefault(d.zone_id, []).append(d)

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def schedule_initial_events(self, scheduler: Any, warmup_ms: float = 500.0) -> None:
        """Schedule initial ambient events after startup sequences."""
        if not self.config.enabled:
            return

        t = warmup_ms

        # Phase 1: Boot one-shots (DHCP, SNMP coldStart) — early
        for device in self.devices:
            if self._should_dhcp(device):
                scheduler.schedule(t, {
                    "type": "ambient_dhcp_boot",
                    "device_id": device.device_id,
                })
                t += random.uniform(50.0, 200.0)

        for device in self.devices:
            if self._should_snmp_trap(device):
                scheduler.schedule(t, {
                    "type": "ambient_snmp_coldstart",
                    "device_id": device.device_id,
                })
                t += random.uniform(10.0, 50.0)

        # Phase 2: Gratuitous ARP from all devices at boot (existing)
        for device in self.devices:
            scheduler.schedule(t, {
                "type": "ambient_gratuitous_arp",
                "device_id": device.device_id,
            })
            t += random.uniform(10.0, 100.0)

        # Phase 3: NTP queries (existing)
        ntp_server = self._resolve_ntp_server()
        if ntp_server:
            for device in self.devices:
                ntp_start = warmup_ms + random.uniform(1000.0, 5000.0)
                scheduler.schedule(ntp_start, {
                    "type": "ambient_ntp_query",
                    "device_id": device.device_id,
                })

        # Phase 4: Periodic broadcast types (staggered per device)
        for device in self.devices:
            base_t = warmup_ms

            if self._should_stp(device):
                scheduler.schedule(base_t + random.uniform(100.0, 2000.0), {
                    "type": "ambient_stp_bpdu",
                    "device_id": device.device_id,
                })

            if self._should_lldp(device):
                scheduler.schedule(base_t + random.uniform(500.0, 5000.0), {
                    "type": "ambient_lldp",
                    "device_id": device.device_id,
                })

            if self._should_cdp(device):
                scheduler.schedule(base_t + random.uniform(1000.0, 5000.0), {
                    "type": "ambient_cdp",
                    "device_id": device.device_id,
                })

            if self._should_bacnet_whois(device):
                scheduler.schedule(base_t + random.uniform(2000.0, 10000.0), {
                    "type": "ambient_bacnet_whois",
                    "device_id": device.device_id,
                })

            if self._should_profinet_dcp(device):
                scheduler.schedule(base_t + random.uniform(2000.0, 10000.0), {
                    "type": "ambient_profinet_dcp",
                    "device_id": device.device_id,
                })

            if self._should_igmp(device):
                scheduler.schedule(base_t + random.uniform(3000.0, 15000.0), {
                    "type": "ambient_igmp_join",
                    "device_id": device.device_id,
                })

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    _HANDLER_MAP: dict[str, str] = {
        "ambient_gratuitous_arp": "_handle_gratuitous_arp",
        "ambient_ntp_query": "_handle_ntp_query",
        "ambient_lldp": "_handle_lldp",
        "ambient_stp_bpdu": "_handle_stp_bpdu",
        "ambient_cdp": "_handle_cdp",
        "ambient_bacnet_whois": "_handle_bacnet_whois",
        "ambient_profinet_dcp": "_handle_profinet_dcp",
        "ambient_snmp_coldstart": "_handle_snmp_coldstart",
        "ambient_dhcp_boot": "_handle_dhcp_boot",
        "ambient_igmp_join": "_handle_igmp_join",
    }

    def handle_event(
        self,
        event: dict[str, Any],
        current_time_ms: float,
        scheduler: Any,
    ) -> list[PacketEvent]:
        """Handle an ambient event, returning packets and scheduling next."""
        event_type = event.get("type", "")
        device_id = event.get("device_id")
        device = self._device_map.get(device_id) if device_id else None
        if not device:
            return []

        handler_name = self._HANDLER_MAP.get(event_type)
        if handler_name:
            handler = getattr(self, handler_name)
            return handler(device, current_time_ms, scheduler, event)

        return []

    # ------------------------------------------------------------------
    # Device filtering helpers
    # ------------------------------------------------------------------

    def _should_lldp(self, device: AmbientDevice) -> bool:
        """All managed devices with metadata send LLDP."""
        return self.config.lldp_enabled and bool(device.device_type)

    def _should_stp(self, device: AmbientDevice) -> bool:
        """Only switches send STP BPDUs."""
        return self.config.stp_enabled and device.device_type == "switch"

    def _should_dhcp(self, device: AmbientDevice) -> bool:
        """HMIs and workstations use DHCP; PLCs/switches use static IP."""
        return (self.config.dhcp_enabled
                and device.device_type in ("hmi", "workstation", "server"))

    def _should_bacnet_whois(self, device: AmbientDevice) -> bool:
        """Only BACnet-capable devices send Who-Is."""
        return (self.config.bacnet_whois_enabled
                and "bacnet" in device.protocols)

    def _should_profinet_dcp(self, device: AmbientDevice) -> bool:
        """PROFINET controllers/PLCs send DCP identify."""
        return (self.config.profinet_dcp_enabled
                and "profinet" in device.protocols
                and device.device_type in ("plc", "controller", "hmi", "scada"))

    def _should_snmp_trap(self, device: AmbientDevice) -> bool:
        """Managed devices send SNMP coldStart on boot."""
        return (self.config.snmp_trap_enabled
                and device.device_type in ("switch", "plc", "rtu", "controller"))

    def _should_igmp(self, device: AmbientDevice) -> bool:
        """Devices using multicast protocols send IGMP joins."""
        return (self.config.igmp_enabled
                and any(p in device.protocols for p in ("bacnet", "profinet")))

    def _should_cdp(self, device: AmbientDevice) -> bool:
        """Only Cisco devices send CDP."""
        return (self.config.cdp_enabled
                and device.vendor.lower().startswith("cisco"))

    # ------------------------------------------------------------------
    # Handlers: existing (ARP, NTP)
    # ------------------------------------------------------------------

    def _handle_gratuitous_arp(
        self,
        device: AmbientDevice,
        current_time_ms: float,
        scheduler: Any,
        event: dict[str, Any],
    ) -> list[PacketEvent]:
        """Emit gratuitous ARP and reschedule."""
        pkt_bytes = build_gratuitous_arp(device.mac_address, device.ip_address)
        packets = [
            PacketEvent(
                timestamp_ms=current_time_ms,
                flow_id=f"ambient_arp_{device.device_id}",
                packet_bytes=pkt_bytes,
                direction="broadcast",
                metadata={"type": "gratuitous_arp", "device_id": device.device_id},
            )
        ]
        self._reschedule(scheduler, current_time_ms, self.config.arp_gratuitous_interval_s, event)
        return packets

    def _handle_ntp_query(
        self,
        device: AmbientDevice,
        current_time_ms: float,
        scheduler: Any,
        event: dict[str, Any],
    ) -> list[PacketEvent]:
        """Emit NTP query + response pair and reschedule."""
        ntp_server_ip = self._resolve_ntp_server(device)
        if not ntp_server_ip:
            return []

        src_port = random.randint(49152, 65535)
        query_bytes = build_ntp_query(
            src_mac=device.mac_address,
            src_ip=device.ip_address,
            dst_ip=ntp_server_ip,
            dst_mac=self.config.ntp_server_mac,
            src_port=src_port,
        )

        response_delay_ms = random.uniform(1.0, 15.0)
        response_bytes = build_ntp_response(
            src_mac=self.config.ntp_server_mac,
            src_ip=ntp_server_ip,
            dst_mac=device.mac_address,
            dst_ip=device.ip_address,
            dst_port=src_port,
        )

        flow_id = f"ambient_ntp_{device.device_id}"
        packets = [
            PacketEvent(
                timestamp_ms=current_time_ms,
                flow_id=flow_id,
                packet_bytes=query_bytes,
                direction="request",
                metadata={"type": "ntp_query", "device_id": device.device_id},
            ),
            PacketEvent(
                timestamp_ms=current_time_ms + response_delay_ms,
                flow_id=flow_id,
                packet_bytes=response_bytes,
                direction="response",
                metadata={"type": "ntp_response", "device_id": device.device_id},
            ),
        ]
        self._reschedule(scheduler, current_time_ms, self.config.ntp_interval_s, event)
        return packets

    # ------------------------------------------------------------------
    # Handlers: LLDP
    # ------------------------------------------------------------------

    def _handle_lldp(
        self,
        device: AmbientDevice,
        current_time_ms: float,
        scheduler: Any,
        event: dict[str, Any],
    ) -> list[PacketEvent]:
        """Emit LLDP advertisement and reschedule."""
        try:
            from app.protocol_engines.lldp.packets import build_lldpdu
            from app.protocol_engines.lldp.types import (
                LLDPIdentity,
                SystemCapability,
            )
        except ImportError:
            logger.debug("LLDP engine not available, skipping")
            return []

        caps = self._infer_lldp_capabilities(device)
        identity = LLDPIdentity(
            chassis_id=device.mac_address,
            port_id="eth0",
            system_name=device.device_name or device.device_id,
            system_description=f"{device.vendor} {device.device_type}".strip(),
            management_address=device.ip_address,
            capabilities=caps,
            enabled_capabilities=caps,
            vlan_id=device.vlan_id,
        )

        pkt_bytes = build_lldpdu(
            src_mac=device.mac_address,
            identity=identity,
            include_profinet="profinet" in device.protocols,
        )

        packets = [
            PacketEvent(
                timestamp_ms=current_time_ms,
                flow_id=f"ambient_lldp_{device.device_id}",
                packet_bytes=pkt_bytes,
                direction="broadcast",
                metadata={"type": "lldp", "device_id": device.device_id},
            )
        ]
        self._reschedule(scheduler, current_time_ms, self.config.lldp_interval_s, event)
        return packets

    @staticmethod
    def _infer_lldp_capabilities(device: AmbientDevice) -> int:
        """Infer LLDP system capabilities from device type."""
        from app.protocol_engines.lldp.types import SystemCapability

        dtype = device.device_type.lower()
        if dtype == "switch":
            return SystemCapability.BRIDGE
        if dtype == "router":
            return SystemCapability.BRIDGE | SystemCapability.ROUTER
        return SystemCapability.STATION_ONLY

    # ------------------------------------------------------------------
    # Handlers: STP/RSTP
    # ------------------------------------------------------------------

    def _handle_stp_bpdu(
        self,
        device: AmbientDevice,
        current_time_ms: float,
        scheduler: Any,
        event: dict[str, Any],
    ) -> list[PacketEvent]:
        """Emit RSTP BPDU and reschedule."""
        from app.protocol_engines.ambient.stp import build_rstp_bpdu

        pkt_bytes = build_rstp_bpdu(
            src_mac=device.mac_address,
            bridge_priority=32768,
        )
        packets = [
            PacketEvent(
                timestamp_ms=current_time_ms,
                flow_id=f"ambient_stp_{device.device_id}",
                packet_bytes=pkt_bytes,
                direction="broadcast",
                metadata={"type": "stp_bpdu", "device_id": device.device_id},
            )
        ]
        self._reschedule(scheduler, current_time_ms, self.config.stp_hello_s, event)
        return packets

    # ------------------------------------------------------------------
    # Handlers: CDP
    # ------------------------------------------------------------------

    def _handle_cdp(
        self,
        device: AmbientDevice,
        current_time_ms: float,
        scheduler: Any,
        event: dict[str, Any],
    ) -> list[PacketEvent]:
        """Emit CDP advertisement and reschedule."""
        from app.protocol_engines.ambient.cdp import build_cdp_frame

        fp = device.vendor_fingerprint
        platform = fp.get("model", "cisco IE-4010-16S12P")
        sw_version = fp.get("firmware_version", "Cisco IOS Software, Version 15.2(7)E")

        pkt_bytes = build_cdp_frame(
            src_mac=device.mac_address,
            device_id=device.device_name or device.device_id,
            ip_address=device.ip_address,
            platform=platform,
            software_version=sw_version,
            vlan_id=device.vlan_id,
        )
        packets = [
            PacketEvent(
                timestamp_ms=current_time_ms,
                flow_id=f"ambient_cdp_{device.device_id}",
                packet_bytes=pkt_bytes,
                direction="broadcast",
                metadata={"type": "cdp", "device_id": device.device_id},
            )
        ]
        self._reschedule(scheduler, current_time_ms, self.config.cdp_interval_s, event)
        return packets

    # ------------------------------------------------------------------
    # Handlers: BACnet Who-Is / I-Am
    # ------------------------------------------------------------------

    def _handle_bacnet_whois(
        self,
        device: AmbientDevice,
        current_time_ms: float,
        scheduler: Any,
        event: dict[str, Any],
    ) -> list[PacketEvent]:
        """Emit BACnet Who-Is and collect I-Am responses from zone peers."""
        try:
            from app.protocol_engines.bacnet.packets import (
                build_i_am_packet,
                build_who_is_packet,
            )
            from app.protocol_engines.types import DeviceContext
        except ImportError:
            logger.debug("BACnet engine not available, skipping")
            return []

        # Build Who-Is from this device
        src_ctx = self._device_context(device, port=47808)
        whois_bytes = build_who_is_packet(src_ctx)

        packets = [
            PacketEvent(
                timestamp_ms=current_time_ms,
                flow_id=f"ambient_bacnet_{device.device_id}",
                packet_bytes=whois_bytes,
                direction="broadcast",
                metadata={"type": "bacnet_whois", "device_id": device.device_id},
            )
        ]

        # Collect I-Am responses from BACnet peers in the same zone
        zone_peers = self._zone_devices.get(device.zone_id, [])
        delay = random.uniform(50.0, 200.0)
        for peer in zone_peers:
            if peer.device_id == device.device_id:
                continue
            if "bacnet" not in peer.protocols:
                continue
            peer_ctx = self._device_context(peer, port=47808)
            fp = peer.vendor_fingerprint
            bacnet_id = fp.get("protocol_identities", {}).get("bacnet", {})
            device_instance = bacnet_id.get("device_instance", random.randint(100, 4194303))
            vendor_id = bacnet_id.get("vendor_id", 0)

            iam_bytes = build_i_am_packet(
                peer_ctx,
                device_instance=device_instance,
                vendor_id=vendor_id,
            )
            packets.append(PacketEvent(
                timestamp_ms=current_time_ms + delay,
                flow_id=f"ambient_bacnet_{peer.device_id}",
                packet_bytes=iam_bytes,
                direction="broadcast",
                metadata={"type": "bacnet_iam", "device_id": peer.device_id},
            ))
            delay += random.uniform(10.0, 50.0)

        self._reschedule(scheduler, current_time_ms, self.config.bacnet_whois_interval_s, event)
        return packets

    # ------------------------------------------------------------------
    # Handlers: PROFINET DCP
    # ------------------------------------------------------------------

    def _handle_profinet_dcp(
        self,
        device: AmbientDevice,
        current_time_ms: float,
        scheduler: Any,
        event: dict[str, Any],
    ) -> list[PacketEvent]:
        """Emit PROFINET DCP identify multicast and responses."""
        try:
            from app.protocol_engines.profinet.packets import (
                build_dcp_identify_request_packet,
                build_dcp_identify_response_packet_fingerprinted,
            )
            from app.protocol_engines.types import DeviceContext
        except ImportError:
            logger.debug("PROFINET engine not available, skipping")
            return []

        src_ctx = self._device_context(device)
        req_bytes = build_dcp_identify_request_packet(src_ctx)

        packets = [
            PacketEvent(
                timestamp_ms=current_time_ms,
                flow_id=f"ambient_pndcp_{device.device_id}",
                packet_bytes=req_bytes,
                direction="broadcast",
                metadata={"type": "profinet_dcp_req", "device_id": device.device_id},
            )
        ]

        # DCP responses from PROFINET peers in same zone
        zone_peers = self._zone_devices.get(device.zone_id, [])
        delay = random.uniform(5.0, 50.0)
        for peer in zone_peers:
            if peer.device_id == device.device_id:
                continue
            if "profinet" not in peer.protocols:
                continue
            peer_ctx = self._device_context(peer)
            try:
                resp_bytes = build_dcp_identify_response_packet_fingerprinted(
                    src=peer_ctx,
                    dst_mac=device.mac_address,
                    vendor_fingerprint=peer.vendor_fingerprint,
                )
            except Exception:
                continue

            packets.append(PacketEvent(
                timestamp_ms=current_time_ms + delay,
                flow_id=f"ambient_pndcp_{peer.device_id}",
                packet_bytes=resp_bytes,
                direction="response",
                metadata={"type": "profinet_dcp_resp", "device_id": peer.device_id},
            ))
            delay += random.uniform(5.0, 20.0)

        self._reschedule(scheduler, current_time_ms, self.config.profinet_dcp_interval_s, event)
        return packets

    # ------------------------------------------------------------------
    # Handlers: SNMP coldStart (one-shot)
    # ------------------------------------------------------------------

    def _handle_snmp_coldstart(
        self,
        device: AmbientDevice,
        current_time_ms: float,
        scheduler: Any,
        event: dict[str, Any],
    ) -> list[PacketEvent]:
        """Emit SNMP coldStart trap (one-shot, no reschedule)."""
        try:
            from app.protocol_engines.snmp.packets import build_snmp_trap_packet
        except ImportError:
            logger.debug("SNMP engine not available, skipping")
            return []

        dst_ip = device.gateway_ip or "10.0.0.1"
        # Use locally-administered MAC for trap sink
        dst_mac = self.config.ntp_server_mac

        fp = device.vendor_fingerprint
        enterprise_oid = fp.get("protocol_identities", {}).get(
            "snmp", {}
        ).get("sysObjectID", "1.3.6.1.4.1.9.1.1")

        pkt_bytes = build_snmp_trap_packet(
            src_mac=device.mac_address,
            dst_mac=dst_mac,
            src_ip=device.ip_address,
            dst_ip=dst_ip,
            community="public",
            trap_type="coldStart",
            enterprise_oid=enterprise_oid,
            uptime_ticks=0,
        )
        return [
            PacketEvent(
                timestamp_ms=current_time_ms,
                flow_id=f"ambient_snmp_{device.device_id}",
                packet_bytes=pkt_bytes,
                direction="request",
                metadata={"type": "snmp_coldstart", "device_id": device.device_id},
            )
        ]

    # ------------------------------------------------------------------
    # Handlers: DHCP boot (one-shot)
    # ------------------------------------------------------------------

    def _handle_dhcp_boot(
        self,
        device: AmbientDevice,
        current_time_ms: float,
        scheduler: Any,
        event: dict[str, Any],
    ) -> list[PacketEvent]:
        """Emit DHCP DORA sequence (one-shot, no reschedule)."""
        from app.protocol_engines.ambient.dhcp import (
            build_dhcp_ack,
            build_dhcp_discover,
            build_dhcp_offer,
            build_dhcp_request,
        )

        xid = random.randint(1, 0xFFFFFFFF)
        server_ip = device.gateway_ip or device.ip_address.rsplit(".", 1)[0] + ".1"
        server_mac = self.config.ntp_server_mac  # reuse for DHCP server

        packets = []
        t = current_time_ms

        # Discover
        packets.append(PacketEvent(
            timestamp_ms=t,
            flow_id=f"ambient_dhcp_{device.device_id}",
            packet_bytes=build_dhcp_discover(
                client_mac=device.mac_address,
                xid=xid,
                hostname=device.device_name or "",
            ),
            direction="broadcast",
            metadata={"type": "dhcp_discover", "device_id": device.device_id},
        ))

        # Offer (from server, after 50-200ms)
        t += random.uniform(50.0, 200.0)
        packets.append(PacketEvent(
            timestamp_ms=t,
            flow_id=f"ambient_dhcp_{device.device_id}",
            packet_bytes=build_dhcp_offer(
                server_mac=server_mac,
                server_ip=server_ip,
                client_mac=device.mac_address,
                offered_ip=device.ip_address,
                xid=xid,
                gateway=server_ip,
            ),
            direction="broadcast",
            metadata={"type": "dhcp_offer", "device_id": device.device_id},
        ))

        # Request (from client, after 10-50ms)
        t += random.uniform(10.0, 50.0)
        packets.append(PacketEvent(
            timestamp_ms=t,
            flow_id=f"ambient_dhcp_{device.device_id}",
            packet_bytes=build_dhcp_request(
                client_mac=device.mac_address,
                xid=xid,
                requested_ip=device.ip_address,
                server_ip=server_ip,
            ),
            direction="broadcast",
            metadata={"type": "dhcp_request", "device_id": device.device_id},
        ))

        # ACK (from server, after 10-50ms)
        t += random.uniform(10.0, 50.0)
        packets.append(PacketEvent(
            timestamp_ms=t,
            flow_id=f"ambient_dhcp_{device.device_id}",
            packet_bytes=build_dhcp_ack(
                server_mac=server_mac,
                server_ip=server_ip,
                client_mac=device.mac_address,
                assigned_ip=device.ip_address,
                xid=xid,
                gateway=server_ip,
            ),
            direction="broadcast",
            metadata={"type": "dhcp_ack", "device_id": device.device_id},
        ))

        return packets

    # ------------------------------------------------------------------
    # Handlers: IGMP
    # ------------------------------------------------------------------

    def _handle_igmp_join(
        self,
        device: AmbientDevice,
        current_time_ms: float,
        scheduler: Any,
        event: dict[str, Any],
    ) -> list[PacketEvent]:
        """Emit IGMP membership report and reschedule."""
        from app.protocol_engines.ambient.igmp import build_igmpv2_report

        # Pick appropriate multicast group based on protocol
        if "profinet" in device.protocols:
            group_ip = "224.0.0.2"  # All-routers (PROFINET uses L2, but IGMP for infra)
        else:
            group_ip = "224.0.0.1"  # All-hosts

        pkt_bytes = build_igmpv2_report(
            src_mac=device.mac_address,
            src_ip=device.ip_address,
            group_ip=group_ip,
        )
        packets = [
            PacketEvent(
                timestamp_ms=current_time_ms,
                flow_id=f"ambient_igmp_{device.device_id}",
                packet_bytes=pkt_bytes,
                direction="broadcast",
                metadata={"type": "igmp_report", "device_id": device.device_id},
            )
        ]
        self._reschedule(scheduler, current_time_ms, self.config.igmp_interval_s, event)
        return packets

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _reschedule(
        scheduler: Any,
        current_time_ms: float,
        interval_s: float,
        event: dict[str, Any],
        jitter_pct: float = 0.1,
    ) -> None:
        """Reschedule an event with jitter."""
        interval_ms = interval_s * 1000.0
        jitter = random.uniform(-interval_ms * jitter_pct, interval_ms * jitter_pct)
        scheduler.schedule(current_time_ms + interval_ms + jitter, event)

    def _resolve_ntp_server(self, device: AmbientDevice | None = None) -> str | None:
        """Resolve the NTP server IP address."""
        if self.config.ntp_server_ip:
            return self.config.ntp_server_ip
        if device and device.gateway_ip:
            return device.gateway_ip
        for d in self.devices:
            if d.gateway_ip:
                return d.gateway_ip
        return None

    @staticmethod
    def _device_context(device: AmbientDevice, port: int = 0) -> Any:
        """Build a minimal DeviceContext from an AmbientDevice."""
        from app.protocol_engines.types import DeviceContext

        return DeviceContext(
            device_id=device.device_id,
            mac_address=device.mac_address,
            ip_address=device.ip_address,
            port=port,
            vendor_fingerprint=device.vendor_fingerprint,
        )
