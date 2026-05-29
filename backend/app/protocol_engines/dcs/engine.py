# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""DCS (Distributed Control System) protocol engine.

Supports multiple DCS vendors:
- Emerson DeltaV (UDP 18507)
- Honeywell Experion (CDA protocol)
- Yokogawa CENTUM VP (Vnet/IP UDP 230)
- Schneider Triconex (TriStation)

Note: ABB 800xA uses MMS (see IEC 61850 engine)
      Siemens PCS7 uses S7comm (see S7 engine)
"""

import logging
import random
import struct
import time
from typing import Any

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.jitter import get_response_delay
from app.protocol_engines.dcs.packets import (
    DCSVendor,
    DCS_VENDOR_CONFIG,
    DCSTag,
    DCSController,
    # DeltaV
    DELTAV_UDP_PORT,
    build_deltav_heartbeat,
    build_deltav_status_request,
    build_deltav_status_response,
    build_deltav_data_request,
    build_deltav_data_response,
    # Honeywell Experion
    build_experion_connect,
    build_experion_connect_ack,
    build_experion_status_request,
    build_experion_status_response,
    build_experion_keepalive,
    build_experion_keepalive_ack,
    # Yokogawa Vnet/IP
    VNETIP_UDP_PORT,
    VnetIPBus,
    build_vnetip_cyclic_data,
    build_vnetip_time_sync,
    # Triconex
    TRICONEX_UDP_PORT,
    build_triconex_connect,
    build_triconex_status_request,
    build_triconex_status_response,
    # Common
    build_udp_packet,
)
from app.protocol_engines.types import (
    FlowContext,
    PacketEvent,
    ProtocolType,
    DCSConversationState,
)

logger = logging.getLogger(__name__)


# TCP flags
TCP_SYN = 0x02
TCP_ACK = 0x10
TCP_PSH = 0x08
TCP_FIN = 0x01
TCP_SYN_ACK = TCP_SYN | TCP_ACK
TCP_PSH_ACK = TCP_PSH | TCP_ACK
TCP_FIN_ACK = TCP_FIN | TCP_ACK


def build_tcp_packet(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq: int,
    ack: int,
    flags: int,
    payload: bytes = b"",
    window: int = 65535,
    ttl: int = 64,
) -> bytes:
    """Build TCP packet with headers."""
    def mac_to_bytes(mac: str) -> bytes:
        return bytes.fromhex(mac.replace(":", "").replace("-", ""))

    def ip_to_bytes(ip: str) -> bytes:
        return bytes([int(x) for x in ip.split(".")])

    eth_header = mac_to_bytes(dst_mac) + mac_to_bytes(src_mac) + b"\x08\x00"

    ip_version_ihl = 0x45
    ip_total_len = 20 + 20 + len(payload)
    ip_id = random.randint(0, 65535)
    ip_flags_frag = 0x4000
    ip_proto = 6

    ip_header_no_checksum = struct.pack(
        "!BBHHHBBH4s4s",
        ip_version_ihl, 0, ip_total_len,
        ip_id, ip_flags_frag,
        ttl, ip_proto, 0,
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip)
    )

    checksum = 0
    for i in range(0, len(ip_header_no_checksum), 2):
        checksum += int.from_bytes(ip_header_no_checksum[i:i+2], "big")
    while checksum > 0xFFFF:
        checksum = (checksum & 0xFFFF) + (checksum >> 16)
    ip_checksum = (~checksum) & 0xFFFF

    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        ip_version_ihl, 0, ip_total_len,
        ip_id, ip_flags_frag,
        ttl, ip_proto, ip_checksum,
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip)
    )

    tcp_data_offset = 0x50
    pseudo_header = (
        ip_to_bytes(src_ip) + ip_to_bytes(dst_ip) +
        struct.pack("!BBH", 0, 6, 20 + len(payload))
    )

    tcp_header_no_checksum = struct.pack(
        "!HHIIHHHH",
        src_port, dst_port,
        seq, ack,
        (tcp_data_offset << 8) | flags,
        window, 0, 0
    )

    checksum_data = pseudo_header + tcp_header_no_checksum + payload
    if len(checksum_data) % 2:
        checksum_data += b"\x00"

    checksum = 0
    for i in range(0, len(checksum_data), 2):
        checksum += int.from_bytes(checksum_data[i:i+2], "big")
    while checksum > 0xFFFF:
        checksum = (checksum & 0xFFFF) + (checksum >> 16)
    tcp_checksum = (~checksum) & 0xFFFF

    tcp_header = struct.pack(
        "!HHIIHHHH",
        src_port, dst_port,
        seq, ack,
        (tcp_data_offset << 8) | flags,
        window, tcp_checksum, 0
    )

    return eth_header + ip_header + tcp_header + payload


# Sample process tags for simulation
SAMPLE_TAGS = [
    ("FIC-101", "Flow Controller", "gpm"),
    ("TIC-201", "Temperature Controller", "degF"),
    ("PIC-301", "Pressure Controller", "psig"),
    ("LIC-401", "Level Controller", "%"),
    ("AIC-501", "Analyzer", "ppm"),
    ("FT-102", "Flow Transmitter", "gpm"),
    ("TT-202", "Temperature Transmitter", "degF"),
    ("PT-302", "Pressure Transmitter", "psig"),
]


@register_engine(ProtocolType.DCS)
class DCSEngine(ProtocolEngine):
    """Protocol engine for DCS (Distributed Control Systems).

    Supports multiple DCS vendors through configuration:
    - Emerson DeltaV
    - Honeywell Experion
    - Yokogawa CENTUM VP
    - Schneider Triconex
    """

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: DCSConversationState,
    ) -> list[PacketEvent]:
        """Generate DCS connection startup sequence.

        Args:
            flow: Flow context
            state: DCS conversation state

        Returns:
            List of startup events
        """
        events = []
        current_time = 0.0

        src = flow.source
        config = flow.config

        # Determine vendor
        vendor_name = config.get("vendor", "deltav").lower()
        vendor = self._get_vendor_enum(vendor_name)
        state.vendor = vendor

        vendor_config = DCS_VENDOR_CONFIG.get(vendor, DCS_VENDOR_CONFIG[DCSVendor.EMERSON_DELTAV])
        port = config.get("port", vendor_config["port"])
        protocol = vendor_config["protocol"]

        state.server_port = port

        src.get_tcp_ttl()
        src.get_tcp_window_size()

        if protocol == "tcp":
            # TCP handshake for Experion
            events.extend(self._generate_tcp_handshake(
                flow, state, current_time, port
            ))
            current_time += 10.0

        # Vendor-specific startup
        if vendor == DCSVendor.EMERSON_DELTAV:
            events.extend(self._deltav_startup(flow, state, current_time))
        elif vendor == DCSVendor.HONEYWELL_EXPERION:
            events.extend(self._experion_startup(flow, state, current_time))
        elif vendor == DCSVendor.YOKOGAWA_CENTUM:
            events.extend(self._vnetip_startup(flow, state, current_time))
        elif vendor == DCSVendor.SCHNEIDER_TRICONEX:
            events.extend(self._triconex_startup(flow, state, current_time))

        state.is_connected = True
        state.state_name = "connected"

        return events

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: DCSConversationState,
        current_time_ms: float,
    ) -> list[PacketEvent]:
        """Generate DCS polling cycle.

        Args:
            flow: Flow context
            state: DCS conversation state
            current_time_ms: Current time

        Returns:
            List of poll events
        """
        events = []

        if not state.is_connected:
            return events

        vendor = state.vendor

        if vendor == DCSVendor.EMERSON_DELTAV:
            events.extend(self._deltav_poll(flow, state, current_time_ms))
        elif vendor == DCSVendor.HONEYWELL_EXPERION:
            events.extend(self._experion_poll(flow, state, current_time_ms))
        elif vendor == DCSVendor.YOKOGAWA_CENTUM:
            events.extend(self._vnetip_poll(flow, state, current_time_ms))
        elif vendor == DCSVendor.SCHNEIDER_TRICONEX:
            events.extend(self._triconex_poll(flow, state, current_time_ms))

        return events

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: DCSConversationState,
    ) -> list[PacketEvent]:
        """Generate DCS shutdown sequence."""
        events = []

        state.is_connected = False
        state.state_name = "disconnected"

        return events

    # =========================================================================
    # Vendor-Specific Implementations
    # =========================================================================

    def _deltav_startup(
        self,
        flow: FlowContext,
        state: DCSConversationState,
        start_time: float,
    ) -> list[PacketEvent]:
        """Generate DeltaV startup sequence."""
        events = []
        current_time = start_time

        src = flow.source
        dst = flow.destination

        # Initial heartbeat
        state.sequence += 1
        heartbeat = build_deltav_heartbeat(state.sequence, state.node_id)

        packet = build_udp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=DELTAV_UDP_PORT,
            payload=heartbeat,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="request",
            metadata={"dcs": "deltav", "message": "heartbeat"},
        ))
        current_time += 5.0

        # Status request
        state.sequence += 1
        status_req = build_deltav_status_request(state.sequence, state.node_id)

        packet = build_udp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=DELTAV_UDP_PORT,
            payload=status_req,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="request",
            metadata={"dcs": "deltav", "message": "status_request"},
        ))
        current_time += get_response_delay(src.vendor_fingerprint)

        # Status response
        controller = self._create_controller(state.node_id, "CTRL-01")
        status_resp = build_deltav_status_response(state.sequence, state.node_id, controller)

        packet = build_udp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=DELTAV_UDP_PORT,
            dst_port=state.client_port,
            payload=status_resp,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="response",
            metadata={"dcs": "deltav", "message": "status_response"},
        ))

        return events

    def _experion_startup(
        self,
        flow: FlowContext,
        state: DCSConversationState,
        start_time: float,
    ) -> list[PacketEvent]:
        """Generate Honeywell Experion startup sequence."""
        events = []
        current_time = start_time

        src = flow.source
        dst = flow.destination

        # Connect request
        state.sequence += 1
        connect_req = build_experion_connect(state.sequence, "HMI-01")

        packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=state.server_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=connect_req,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="request",
            metadata={"dcs": "experion", "message": "connect"},
        ))
        state.tcp_seq_client += len(connect_req)
        current_time += get_response_delay(src.vendor_fingerprint)

        # Connect ACK
        state.session_id = random.randint(1, 65535)
        connect_ack = build_experion_connect_ack(state.sequence, state.session_id)

        packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=state.server_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=connect_ack,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="response",
            metadata={"dcs": "experion", "message": "connect_ack", "session": state.session_id},
        ))
        state.tcp_seq_server += len(connect_ack)

        return events

    def _vnetip_startup(
        self,
        flow: FlowContext,
        state: DCSConversationState,
        start_time: float,
    ) -> list[PacketEvent]:
        """Generate Yokogawa Vnet/IP startup sequence."""
        events = []
        current_time = start_time

        src = flow.source
        dst = flow.destination

        # Time sync from engineering station
        state.sequence += 1
        time_sync = build_vnetip_time_sync(state.sequence, state.node_id, time.time())

        packet = build_udp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=VNETIP_UDP_PORT,
            payload=time_sync,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="request",
            metadata={"dcs": "vnetip", "message": "time_sync"},
        ))
        current_time += 5.0

        # Initial cyclic data
        tags = self._generate_sample_tags()
        state.sequence += 1
        cyclic_data = build_vnetip_cyclic_data(state.sequence, state.node_id, tags)

        packet = build_udp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=VNETIP_UDP_PORT,
            dst_port=state.client_port,
            payload=cyclic_data,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="response",
            metadata={"dcs": "vnetip", "message": "cyclic_data"},
        ))

        return events

    def _triconex_startup(
        self,
        flow: FlowContext,
        state: DCSConversationState,
        start_time: float,
    ) -> list[PacketEvent]:
        """Generate Triconex startup sequence."""
        events = []
        current_time = start_time

        src = flow.source
        dst = flow.destination

        # Connect
        state.sequence += 1
        connect_req = build_triconex_connect(state.sequence, state.node_id)

        packet = build_udp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=TRICONEX_UDP_PORT,
            payload=connect_req,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="request",
            metadata={"dcs": "triconex", "message": "connect"},
        ))
        current_time += get_response_delay(src.vendor_fingerprint)

        # Status request
        state.sequence += 1
        status_req = build_triconex_status_request(state.sequence, state.node_id)

        packet = build_udp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=TRICONEX_UDP_PORT,
            payload=status_req,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="request",
            metadata={"dcs": "triconex", "message": "status_request"},
        ))
        current_time += get_response_delay(src.vendor_fingerprint)

        # Status response
        status_resp = build_triconex_status_response(state.sequence, state.node_id)

        packet = build_udp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=TRICONEX_UDP_PORT,
            dst_port=state.client_port,
            payload=status_resp,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="response",
            metadata={"dcs": "triconex", "message": "status_response"},
        ))

        return events

    # =========================================================================
    # Polling Implementations
    # =========================================================================

    def _deltav_poll(
        self,
        flow: FlowContext,
        state: DCSConversationState,
        current_time_ms: float,
    ) -> list[PacketEvent]:
        """Generate DeltaV poll cycle."""
        events = []

        src = flow.source
        dst = flow.destination

        # Alternate between heartbeat and data request
        state.poll_index += 1

        if state.poll_index % 5 == 0:
            # Heartbeat every 5th poll
            state.sequence += 1
            message = build_deltav_heartbeat(state.sequence, state.node_id)
            msg_type = "heartbeat"
        else:
            # Data request
            state.sequence += 1
            tag_names = [t[0] for t in SAMPLE_TAGS[:4]]
            message = build_deltav_data_request(state.sequence, state.node_id, tag_names)
            msg_type = "data_request"

        packet = build_udp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=DELTAV_UDP_PORT,
            payload=message,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="request",
            metadata={"dcs": "deltav", "message": msg_type},
        ))

        if msg_type == "data_request":
            # Data response
            response_time = current_time_ms + get_response_delay(src.vendor_fingerprint)
            tags = self._generate_sample_tags()[:4]
            response = build_deltav_data_response(state.sequence, state.node_id, tags)

            packet = build_udp_packet(
                src_mac=dst.mac_address,
                dst_mac=src.mac_address,
                src_ip=dst.ip_address,
                dst_ip=src.ip_address,
                src_port=DELTAV_UDP_PORT,
                dst_port=state.client_port,
                payload=response,
            )
            events.append(PacketEvent(
                timestamp_ms=response_time,
                flow_id=flow.flow_id,
                packet_bytes=packet,
                direction="response",
                metadata={"dcs": "deltav", "message": "data_response"},
            ))

        return events

    def _experion_poll(
        self,
        flow: FlowContext,
        state: DCSConversationState,
        current_time_ms: float,
    ) -> list[PacketEvent]:
        """Generate Honeywell Experion poll cycle."""
        events = []

        src = flow.source
        dst = flow.destination

        state.poll_index += 1

        if state.poll_index % 10 == 0:
            # Keepalive every 10th poll
            state.sequence += 1
            message = build_experion_keepalive(state.sequence, state.session_id)
            msg_type = "keepalive"
        else:
            # Status request
            state.sequence += 1
            message = build_experion_status_request(state.sequence, state.session_id)
            msg_type = "status_request"

        packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=state.server_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=message,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="request",
            metadata={"dcs": "experion", "message": msg_type},
        ))
        state.tcp_seq_client += len(message)

        # Response
        response_time = current_time_ms + get_response_delay(src.vendor_fingerprint)

        if msg_type == "keepalive":
            response = build_experion_keepalive_ack(state.sequence, state.session_id)
            resp_type = "keepalive_ack"
        else:
            controller = self._create_controller(state.node_id, "C300-01")
            response = build_experion_status_response(state.sequence, state.session_id, controller)
            resp_type = "status_response"

        packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=state.server_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=response,
        )
        events.append(PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="response",
            metadata={"dcs": "experion", "message": resp_type},
        ))
        state.tcp_seq_server += len(response)

        return events

    def _vnetip_poll(
        self,
        flow: FlowContext,
        state: DCSConversationState,
        current_time_ms: float,
    ) -> list[PacketEvent]:
        """Generate Yokogawa Vnet/IP poll cycle."""
        events = []

        src = flow.source
        dst = flow.destination

        # Vnet/IP uses deterministic cyclic data exchange
        state.sequence += 1
        tags = self._generate_sample_tags()

        # Cyclic data from controller
        cyclic_data = build_vnetip_cyclic_data(
            state.sequence,
            state.node_id,
            tags,
            bus=VnetIPBus.BUS_1 if state.poll_index % 2 == 0 else VnetIPBus.BUS_2,
        )

        packet = build_udp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=VNETIP_UDP_PORT,
            dst_port=state.client_port,
            payload=cyclic_data,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="response",
            metadata={"dcs": "vnetip", "message": "cyclic_data", "bus": state.poll_index % 2 + 1},
        ))

        state.poll_index += 1

        return events

    def _triconex_poll(
        self,
        flow: FlowContext,
        state: DCSConversationState,
        current_time_ms: float,
    ) -> list[PacketEvent]:
        """Generate Triconex poll cycle."""
        events = []

        src = flow.source
        dst = flow.destination

        # Status request
        state.sequence += 1
        status_req = build_triconex_status_request(state.sequence, state.node_id)

        packet = build_udp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=TRICONEX_UDP_PORT,
            payload=status_req,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="request",
            metadata={"dcs": "triconex", "message": "status_request"},
        ))

        # Response
        response_time = current_time_ms + get_response_delay(src.vendor_fingerprint)
        status_resp = build_triconex_status_response(state.sequence, state.node_id)

        packet = build_udp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=TRICONEX_UDP_PORT,
            dst_port=state.client_port,
            payload=status_resp,
        )
        events.append(PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction="response",
            metadata={"dcs": "triconex", "message": "status_response"},
        ))

        state.poll_index += 1

        return events

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _generate_tcp_handshake(
        self,
        flow: FlowContext,
        state: DCSConversationState,
        start_time: float,
        port: int,
    ) -> list[PacketEvent]:
        """Generate TCP handshake for TCP-based DCS protocols."""
        events = []
        current_time = start_time

        src = flow.source
        dst = flow.destination

        state.tcp_seq_client = random.randint(1000000, 4000000000)
        state.tcp_seq_server = random.randint(1000000, 4000000000)

        # SYN
        syn = build_tcp_packet(
            src.mac_address, dst.mac_address,
            src.ip_address, dst.ip_address,
            state.client_port, port,
            state.tcp_seq_client, 0, TCP_SYN,
        )
        events.append(PacketEvent(current_time, flow.flow_id, syn, "request", {"tcp": "SYN"}))
        state.tcp_seq_client += 1
        current_time += 1.0

        # SYN-ACK
        syn_ack = build_tcp_packet(
            dst.mac_address, src.mac_address,
            dst.ip_address, src.ip_address,
            port, state.client_port,
            state.tcp_seq_server, state.tcp_seq_client, TCP_SYN_ACK,
        )
        events.append(PacketEvent(current_time, flow.flow_id, syn_ack, "response", {"tcp": "SYN-ACK"}))
        state.tcp_seq_server += 1
        current_time += 1.0

        # ACK
        ack = build_tcp_packet(
            src.mac_address, dst.mac_address,
            src.ip_address, dst.ip_address,
            state.client_port, port,
            state.tcp_seq_client, state.tcp_seq_server, TCP_ACK,
        )
        events.append(PacketEvent(current_time, flow.flow_id, ack, "request", {"tcp": "ACK"}))

        return events

    def _get_vendor_enum(self, vendor_name: str) -> DCSVendor:
        """Convert vendor name to enum."""
        mapping = {
            "deltav": DCSVendor.EMERSON_DELTAV,
            "emerson": DCSVendor.EMERSON_DELTAV,
            "experion": DCSVendor.HONEYWELL_EXPERION,
            "honeywell": DCSVendor.HONEYWELL_EXPERION,
            "centum": DCSVendor.YOKOGAWA_CENTUM,
            "yokogawa": DCSVendor.YOKOGAWA_CENTUM,
            "vnetip": DCSVendor.YOKOGAWA_CENTUM,
            "triconex": DCSVendor.SCHNEIDER_TRICONEX,
            "schneider": DCSVendor.SCHNEIDER_TRICONEX,
        }
        return mapping.get(vendor_name, DCSVendor.EMERSON_DELTAV)

    def _create_controller(self, node_id: int, name: str) -> DCSController:
        """Create simulated controller status."""
        return DCSController(
            node_id=node_id,
            name=name,
            state=1,  # Running
            cpu_load=random.randint(15, 45),
            memory_used=random.randint(30, 60),
            redundancy_state=1,  # Primary
            io_scan_time_ms=random.uniform(50, 150),
            last_sync_time=time.time(),
        )

    def _generate_sample_tags(self) -> list[DCSTag]:
        """Generate sample process tags with realistic values."""
        tags = []
        for name, desc, unit in SAMPLE_TAGS:
            value = random.uniform(0, 100)
            tags.append(DCSTag(
                name=name,
                value=value,
                quality=192,  # Good
                timestamp=time.time(),
                unit=unit,
                alarm_state=0,
            ))
        return tags

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate DCS configuration."""
        errors = []

        if "vendor" in config:
            valid_vendors = ["deltav", "emerson", "experion", "honeywell",
                          "centum", "yokogawa", "vnetip", "triconex", "schneider"]
            if config["vendor"].lower() not in valid_vendors:
                errors.append(f"vendor must be one of: {valid_vendors}")

        return errors

    def create_state(self, flow_id: str, config: dict[str, Any]) -> DCSConversationState:
        """Create DCS conversation state."""
        return DCSConversationState(
            flow_id=flow_id,
            state_name="init",
            client_port=random.randint(49152, 65535),
            node_id=config.get("node_id", 1),
        )
