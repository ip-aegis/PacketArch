# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""WMI (Windows Management Instrumentation) protocol engine.

WMI is used for Windows device discovery and management over DCOM/RPC.

Connection flow:
1. TCP connect to port 135 (RPC Endpoint Mapper)
2. RPC BIND to IRemoteSCMActivator
3. DCOM activation to get dynamic port
4. TCP connect to dynamic port
5. RPC BIND to IWbemLevel1Login
6. NTLM authentication
7. RPC BIND to IWbemServices
8. Execute WMI queries (Win32_ComputerSystem, etc.)

Supported features:
- RPC BIND/BIND_ACK handshake
- NTLMSSP authentication simulation
- Common WMI discovery queries
- Realistic timing patterns
"""

import logging
import random
import struct
from typing import Any

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.jitter import get_response_delay
from app.protocol_engines.wmi.packets import (
    WMI_DISCOVERY_QUERIES,
    build_ntlmssp_authenticate,
    build_ntlmssp_challenge,
    build_ntlmssp_negotiate,
    build_rpc_bind,
    build_rpc_bind_ack,
    build_rpc_request,
    build_rpc_response,
    build_wmi_bind_to_endpoint_mapper,
    build_wmi_bind_ack_endpoint_mapper,
    build_wmi_bind_to_wbem_login,
    build_wmi_bind_to_services,
    build_wmi_exec_query,
    build_wmi_query_response,
    IWBEMSERVICES_UUID,
    IWBEMSERVICES_VERSION,
)
from app.protocol_engines.types import (
    DeviceContext,
    FlowContext,
    PacketEvent,
    ProtocolType,
    WMIConversationState,
)

logger = logging.getLogger(__name__)


# Default ports
RPC_ENDPOINT_MAPPER_PORT = 135
WMI_DYNAMIC_PORT_MIN = 49152
WMI_DYNAMIC_PORT_MAX = 65535

# Default timing (ms)
TCP_HANDSHAKE_DELAY = 1.0
RPC_RESPONSE_DELAY_MIN = 5.0
RPC_RESPONSE_DELAY_MAX = 50.0
WMI_QUERY_RESPONSE_DELAY_MIN = 20.0
WMI_QUERY_RESPONSE_DELAY_MAX = 200.0


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
    ttl: int = 128,
) -> bytes:
    """Build a TCP packet with IP and Ethernet headers.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_port: Source port
        dst_port: Destination port
        seq: TCP sequence number
        ack: TCP acknowledgment number
        flags: TCP flags
        payload: TCP payload
        window: TCP window size
        ttl: IP TTL

    Returns:
        Complete Ethernet frame bytes
    """
    def mac_to_bytes(mac: str) -> bytes:
        return bytes.fromhex(mac.replace(":", "").replace("-", ""))

    def ip_to_bytes(ip: str) -> bytes:
        return bytes([int(x) for x in ip.split(".")])

    # Ethernet header
    eth_header = mac_to_bytes(dst_mac) + mac_to_bytes(src_mac) + b"\x08\x00"

    # IP header (20 bytes, no options)
    ip_version_ihl = 0x45
    ip_dscp_ecn = 0x00
    ip_total_len = 20 + 20 + len(payload)
    ip_id = random.randint(0, 65535)
    ip_flags_frag = 0x4000  # Don't fragment
    ip_proto = 6  # TCP

    # Calculate IP checksum
    ip_header_no_checksum = struct.pack(
        "!BBHHHBBH4s4s",
        ip_version_ihl, ip_dscp_ecn, ip_total_len,
        ip_id, ip_flags_frag,
        ttl, ip_proto, 0,  # checksum placeholder
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip)
    )

    # IP checksum
    checksum = 0
    for i in range(0, len(ip_header_no_checksum), 2):
        checksum += int.from_bytes(ip_header_no_checksum[i:i+2], "big")
    while checksum > 0xFFFF:
        checksum = (checksum & 0xFFFF) + (checksum >> 16)
    ip_checksum = (~checksum) & 0xFFFF

    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        ip_version_ihl, ip_dscp_ecn, ip_total_len,
        ip_id, ip_flags_frag,
        ttl, ip_proto, ip_checksum,
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip)
    )

    # TCP header (20 bytes, no options)
    tcp_data_offset = 0x50  # 5 words (20 bytes)
    tcp_reserved = 0
    tcp_urgent = 0

    # Simple TCP checksum (pseudo-header + TCP)
    pseudo_header = (
        ip_to_bytes(src_ip) + ip_to_bytes(dst_ip) +
        struct.pack("!BBH", 0, 6, 20 + len(payload))
    )

    tcp_header_no_checksum = struct.pack(
        "!HHIIHHHH",
        src_port, dst_port,
        seq, ack,
        (tcp_data_offset << 8) | flags,
        window, 0, tcp_urgent
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
        window, tcp_checksum, tcp_urgent
    )

    return eth_header + ip_header + tcp_header + payload


# TCP Flags
TCP_SYN = 0x02
TCP_ACK = 0x10
TCP_PSH = 0x08
TCP_FIN = 0x01
TCP_SYN_ACK = TCP_SYN | TCP_ACK
TCP_PSH_ACK = TCP_PSH | TCP_ACK
TCP_FIN_ACK = TCP_FIN | TCP_ACK


@register_engine(ProtocolType.WMI)
class WMIEngine(ProtocolEngine):
    """Protocol engine for WMI (Windows Management Instrumentation).

    Generates realistic WMI discovery traffic over DCOM/RPC.
    """

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: WMIConversationState,
    ) -> list[PacketEvent]:
        """Generate WMI connection startup sequence.

        This includes:
        1. TCP handshake to port 135
        2. RPC BIND to IRemoteSCMActivator
        3. RPC BIND_ACK with dynamic port
        4. TCP handshake to dynamic port
        5. RPC BIND to IWbemLevel1Login
        6. NTLM authentication exchange
        7. RPC BIND to IWbemServices

        Args:
            flow: Flow context with device information
            state: WMI conversation state

        Returns:
            List of PacketEvent for startup sequence
        """
        events = []
        current_time = 0.0

        src = flow.source
        dst = flow.destination
        config = flow.config

        # Allocate dynamic port for WMI service
        state.dynamic_port = random.randint(WMI_DYNAMIC_PORT_MIN, WMI_DYNAMIC_PORT_MAX)

        # Get TCP parameters from fingerprint
        ttl = src.get_tcp_ttl()
        window = src.get_tcp_window_size()

        # Initialize sequence numbers
        state.tcp_seq_client = random.randint(1000000, 4000000000)
        state.tcp_seq_server = random.randint(1000000, 4000000000)

        # =====================================================================
        # Phase 1: TCP Handshake to Port 135
        # =====================================================================

        # SYN
        syn_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=RPC_ENDPOINT_MAPPER_PORT,
            seq=state.tcp_seq_client,
            ack=0,
            flags=TCP_SYN,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_packet,
            direction="request",
            metadata={"tcp_flags": "SYN", "port": 135},
        ))
        state.tcp_seq_client += 1
        current_time += TCP_HANDSHAKE_DELAY

        # SYN-ACK
        syn_ack_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=RPC_ENDPOINT_MAPPER_PORT,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_SYN_ACK,
            ttl=128,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack_packet,
            direction="response",
            metadata={"tcp_flags": "SYN-ACK", "port": 135},
        ))
        state.tcp_seq_server += 1
        current_time += TCP_HANDSHAKE_DELAY

        # ACK
        ack_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=RPC_ENDPOINT_MAPPER_PORT,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_ACK,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"tcp_flags": "ACK", "port": 135},
        ))
        current_time += 2.0

        # =====================================================================
        # Phase 2: RPC BIND to IRemoteSCMActivator
        # =====================================================================

        state.call_id = 1
        bind_pdu = build_wmi_bind_to_endpoint_mapper(state.call_id)

        bind_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=RPC_ENDPOINT_MAPPER_PORT,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=bind_pdu,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=bind_packet,
            direction="request",
            metadata={"rpc": "BIND", "interface": "IRemoteSCMActivator"},
        ))
        state.tcp_seq_client += len(bind_pdu)
        current_time += get_response_delay(src.vendor_fingerprint)

        # RPC BIND_ACK
        bind_ack_pdu = build_wmi_bind_ack_endpoint_mapper(
            call_id=state.call_id,
            dynamic_port=state.dynamic_port,
        )

        bind_ack_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=RPC_ENDPOINT_MAPPER_PORT,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=bind_ack_pdu,
            ttl=128,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=bind_ack_packet,
            direction="response",
            metadata={"rpc": "BIND_ACK", "dynamic_port": state.dynamic_port},
        ))
        state.tcp_seq_server += len(bind_ack_pdu)
        current_time += 5.0

        # =====================================================================
        # Phase 3: TCP Handshake to Dynamic Port
        # =====================================================================

        # Reset sequence numbers for new connection
        state.tcp_seq_client = random.randint(1000000, 4000000000)
        state.tcp_seq_server = random.randint(1000000, 4000000000)
        state.client_port = random.randint(49152, 65535)

        # SYN to dynamic port
        syn_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=state.dynamic_port,
            seq=state.tcp_seq_client,
            ack=0,
            flags=TCP_SYN,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_packet,
            direction="request",
            metadata={"tcp_flags": "SYN", "port": state.dynamic_port},
        ))
        state.tcp_seq_client += 1
        current_time += TCP_HANDSHAKE_DELAY

        # SYN-ACK
        syn_ack_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=state.dynamic_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_SYN_ACK,
            ttl=128,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack_packet,
            direction="response",
            metadata={"tcp_flags": "SYN-ACK", "port": state.dynamic_port},
        ))
        state.tcp_seq_server += 1
        current_time += TCP_HANDSHAKE_DELAY

        # ACK
        ack_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=state.dynamic_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_ACK,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"tcp_flags": "ACK", "port": state.dynamic_port},
        ))
        current_time += 2.0

        # =====================================================================
        # Phase 4: RPC BIND to IWbemLevel1Login + NTLM Auth
        # =====================================================================

        state.call_id = 1
        bind_login_pdu = build_wmi_bind_to_wbem_login(state.call_id)

        bind_login_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=state.dynamic_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=bind_login_pdu,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=bind_login_packet,
            direction="request",
            metadata={"rpc": "BIND", "interface": "IWbemLevel1Login"},
        ))
        state.tcp_seq_client += len(bind_login_pdu)
        current_time += get_response_delay(src.vendor_fingerprint)

        # BIND_ACK for login
        bind_ack_login_pdu = build_rpc_bind_ack(call_id=state.call_id)

        bind_ack_login_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=state.dynamic_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=bind_ack_login_pdu,
            ttl=128,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=bind_ack_login_packet,
            direction="response",
            metadata={"rpc": "BIND_ACK", "interface": "IWbemLevel1Login"},
        ))
        state.tcp_seq_server += len(bind_ack_login_pdu)
        current_time += 5.0

        # =====================================================================
        # Phase 5: NTLMSSP Authentication
        # =====================================================================

        # NTLM Negotiate
        ntlm_negotiate = build_ntlmssp_negotiate()
        state.call_id += 1

        negotiate_request = build_rpc_request(
            opnum=6,  # NTLMLogin
            stub_data=ntlm_negotiate,
            call_id=state.call_id,
        )

        negotiate_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=state.dynamic_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=negotiate_request,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=negotiate_packet,
            direction="request",
            metadata={"ntlmssp": "NEGOTIATE"},
        ))
        state.tcp_seq_client += len(negotiate_request)
        current_time += get_response_delay(src.vendor_fingerprint)

        # NTLM Challenge
        ntlm_challenge = build_ntlmssp_challenge(target_name=config.get("domain", "WORKGROUP"))

        challenge_response = build_rpc_response(
            stub_data=ntlm_challenge,
            call_id=state.call_id,
        )

        challenge_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=state.dynamic_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=challenge_response,
            ttl=128,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=challenge_packet,
            direction="response",
            metadata={"ntlmssp": "CHALLENGE"},
        ))
        state.tcp_seq_server += len(challenge_response)
        current_time += 5.0

        # NTLM Authenticate
        ntlm_auth = build_ntlmssp_authenticate(
            domain=config.get("domain", "WORKGROUP"),
            username=config.get("username", "Administrator"),
        )
        state.call_id += 1

        auth_request = build_rpc_request(
            opnum=6,
            stub_data=ntlm_auth,
            call_id=state.call_id,
        )

        auth_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=state.dynamic_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=auth_request,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=auth_packet,
            direction="request",
            metadata={"ntlmssp": "AUTHENTICATE"},
        ))
        state.tcp_seq_client += len(auth_request)
        current_time += get_response_delay(src.vendor_fingerprint)

        # Auth success response
        auth_success = build_rpc_response(
            stub_data=struct.pack("<I", 0),  # HRESULT success
            call_id=state.call_id,
        )

        auth_success_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=state.dynamic_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=auth_success,
            ttl=128,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=auth_success_packet,
            direction="response",
            metadata={"ntlmssp": "SUCCESS"},
        ))
        state.tcp_seq_server += len(auth_success)
        current_time += 5.0

        # =====================================================================
        # Phase 6: RPC BIND to IWbemServices
        # =====================================================================

        state.call_id = 1
        bind_services_pdu = build_wmi_bind_to_services(state.call_id)

        bind_services_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=state.dynamic_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=bind_services_pdu,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=bind_services_packet,
            direction="request",
            metadata={"rpc": "BIND", "interface": "IWbemServices"},
        ))
        state.tcp_seq_client += len(bind_services_pdu)
        current_time += get_response_delay(src.vendor_fingerprint)

        # BIND_ACK for services
        bind_ack_services_pdu = build_rpc_bind_ack(call_id=state.call_id)

        bind_ack_services_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=state.dynamic_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=bind_ack_services_pdu,
            ttl=128,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=bind_ack_services_packet,
            direction="response",
            metadata={"rpc": "BIND_ACK", "interface": "IWbemServices"},
        ))
        state.tcp_seq_server += len(bind_ack_services_pdu)

        # Update state
        state.is_connected = True
        state.is_authenticated = True
        state.state_name = "ready"

        logger.debug(
            f"WMI startup complete: dynamic_port={state.dynamic_port}, "
            f"packets={len(events)}"
        )

        return events

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: WMIConversationState,
        current_time_ms: float,
    ) -> list[PacketEvent]:
        """Generate WMI query poll cycle.

        Executes the next WMI query in the configured query list.

        Args:
            flow: Flow context
            state: WMI conversation state
            current_time_ms: Current simulation time

        Returns:
            List of PacketEvent for query/response
        """
        events = []

        if not state.is_connected or not state.is_authenticated:
            logger.warning("WMI poll cycle called but not connected/authenticated")
            return events

        src = flow.source
        dst = flow.destination
        config = flow.config

        # Get configured queries or use defaults
        queries = config.get("queries", WMI_DISCOVERY_QUERIES)

        # Select next query
        query = queries[state.query_index % len(queries)]
        state.query_index += 1

        ttl = src.get_tcp_ttl()
        window = src.get_tcp_window_size()

        # Build WMI ExecQuery request
        state.call_id += 1
        query_pdu = build_wmi_exec_query(query, state.call_id)

        query_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=state.dynamic_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=query_pdu,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=query_packet,
            direction="request",
            metadata={"wmi": "ExecQuery", "query": query},
        ))
        state.tcp_seq_client += len(query_pdu)

        # Generate response delay
        response_delay = random.uniform(
            WMI_QUERY_RESPONSE_DELAY_MIN,
            WMI_QUERY_RESPONSE_DELAY_MAX,
        )
        response_time = current_time_ms + response_delay

        # Build WMI response
        response_pdu = build_rpc_response(
            stub_data=build_wmi_query_response([{"result": "simulated"}]),
            call_id=state.call_id,
        )

        response_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=state.dynamic_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=response_pdu,
            ttl=128,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={"wmi": "ExecQuery_Response", "query": query},
        ))
        state.tcp_seq_server += len(response_pdu)

        return events

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: WMIConversationState,
    ) -> list[PacketEvent]:
        """Generate WMI shutdown sequence.

        Args:
            flow: Flow context
            state: WMI conversation state

        Returns:
            List of PacketEvent for TCP FIN handshake
        """
        events = []

        src = flow.source
        dst = flow.destination

        ttl = src.get_tcp_ttl()
        window = src.get_tcp_window_size()

        current_time = 0.0

        # FIN from client
        fin_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=state.dynamic_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_FIN_ACK,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_packet,
            direction="request",
            metadata={"tcp_flags": "FIN-ACK"},
        ))
        state.tcp_seq_client += 1
        current_time += TCP_HANDSHAKE_DELAY

        # FIN-ACK from server
        fin_ack_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=state.dynamic_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_FIN_ACK,
            ttl=128,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_ack_packet,
            direction="response",
            metadata={"tcp_flags": "FIN-ACK"},
        ))
        state.tcp_seq_server += 1
        current_time += TCP_HANDSHAKE_DELAY

        # Final ACK
        final_ack_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=state.dynamic_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_ACK,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=final_ack_packet,
            direction="request",
            metadata={"tcp_flags": "ACK"},
        ))

        state.is_connected = False
        state.state_name = "closed"

        return events

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate WMI configuration.

        Args:
            config: Configuration dictionary

        Returns:
            List of validation error messages
        """
        errors = []

        if "queries" in config:
            queries = config["queries"]
            if not isinstance(queries, list):
                errors.append("queries must be a list of WQL query strings")
            elif not queries:
                errors.append("queries list cannot be empty")
            else:
                for i, q in enumerate(queries):
                    if not isinstance(q, str):
                        errors.append(f"queries[{i}] must be a string")
                    elif not q.upper().startswith("SELECT"):
                        errors.append(f"queries[{i}] must be a valid SELECT query")

        if "poll_interval_ms" in config:
            interval = config["poll_interval_ms"]
            if not isinstance(interval, (int, float)) or interval < 1000:
                errors.append("poll_interval_ms must be at least 1000ms")

        return errors

    def create_state(self, flow_id: str, config: dict[str, Any]) -> WMIConversationState:
        """Create WMI conversation state.

        Args:
            flow_id: Flow identifier
            config: Flow configuration

        Returns:
            Initialized WMIConversationState
        """
        return WMIConversationState(
            flow_id=flow_id,
            state_name="init",
            client_port=random.randint(49152, 65535),
        )
