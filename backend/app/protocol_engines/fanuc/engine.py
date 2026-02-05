"""FANUC FOCAS (FANUC Open CNC API Specification) protocol engine.

FOCAS is FANUC's proprietary protocol for CNC machine communication.
This engine generates realistic CNC monitoring traffic.

Default port: TCP 8193

Supported CNC models (simulated):
- Series 30i-B, 31i-B, 32i-B, 35i
- Series 0i-F, 0i-F Plus
- Power Motion i-A

Common operations:
- System info (cnc_sysinfo)
- Status monitoring (cnc_statinfo)
- Axis positions (cnc_rdposition)
- Spindle data (cnc_acts2)
- Program info (cnc_rdprognum)
- Feedrate (cnc_actf)
- Alarms (cnc_alarm)
"""

import logging
import random
import struct
from typing import Any

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.jitter import get_response_delay
from app.protocol_engines.fanuc.packets import (
    FOCAS_DEFAULT_PORT,
    FOCASFunction,
    CNCType,
    AxisPosition,
    SpindleData,
    CNCStatus,
    build_connect_request,
    build_connect_response,
    build_sysinfo_request,
    build_sysinfo_response,
    build_statinfo_request,
    build_statinfo_response,
    build_rdposition_request,
    build_rdposition_response,
    build_acts_request,
    build_acts_response,
    build_alarm_request,
    build_alarm_response,
    build_rdprognum_request,
    build_rdprognum_response,
    build_actf_request,
    build_actf_response,
    build_disconnect_request,
    build_disconnect_response,
)
from app.protocol_engines.types import (
    DeviceContext,
    FlowContext,
    PacketEvent,
    ProtocolType,
    FANUCConversationState,
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
    ttl: int = 128,
) -> bytes:
    """Build a TCP packet with IP and Ethernet headers."""
    def mac_to_bytes(mac: str) -> bytes:
        return bytes.fromhex(mac.replace(":", "").replace("-", ""))

    def ip_to_bytes(ip: str) -> bytes:
        return bytes([int(x) for x in ip.split(".")])

    # Ethernet header
    eth_header = mac_to_bytes(dst_mac) + mac_to_bytes(src_mac) + b"\x08\x00"

    # IP header
    ip_version_ihl = 0x45
    ip_dscp_ecn = 0x00
    ip_total_len = 20 + 20 + len(payload)
    ip_id = random.randint(0, 65535)
    ip_flags_frag = 0x4000
    ip_proto = 6

    ip_header_no_checksum = struct.pack(
        "!BBHHHBBH4s4s",
        ip_version_ihl, ip_dscp_ecn, ip_total_len,
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
        ip_version_ihl, ip_dscp_ecn, ip_total_len,
        ip_id, ip_flags_frag,
        ttl, ip_proto, ip_checksum,
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip)
    )

    # TCP header
    tcp_data_offset = 0x50
    tcp_urgent = 0

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


# Polling functions in order of typical monitoring
POLL_FUNCTIONS = [
    ("statinfo", build_statinfo_request, build_statinfo_response),
    ("rdposition", build_rdposition_request, build_rdposition_response),
    ("acts", build_acts_request, build_acts_response),
    ("actf", build_actf_request, build_actf_response),
    ("rdprognum", build_rdprognum_request, build_rdprognum_response),
    ("alarm", build_alarm_request, build_alarm_response),
]


@register_engine(ProtocolType.FANUC)
class FANUCEngine(ProtocolEngine):
    """Protocol engine for FANUC FOCAS (CNC communication).

    Generates realistic CNC monitoring traffic including:
    - Connection establishment
    - System information query
    - Periodic status polling
    - Axis position updates
    - Spindle data
    - Program information
    """

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: FANUCConversationState,
    ) -> list[PacketEvent]:
        """Generate FOCAS connection startup sequence.

        This includes:
        1. TCP handshake
        2. FOCAS connect (cnc_allclibhndl3)
        3. System info query (cnc_sysinfo)

        Args:
            flow: Flow context with device information
            state: FANUC conversation state

        Returns:
            List of PacketEvent for startup sequence
        """
        events = []
        current_time = 0.0

        src = flow.source
        dst = flow.destination
        config = flow.config

        # Get TCP parameters
        ttl = src.get_tcp_ttl()
        window = src.get_tcp_window_size()

        # Initialize sequence numbers
        state.tcp_seq_client = random.randint(1000000, 4000000000)
        state.tcp_seq_server = random.randint(1000000, 4000000000)

        focas_port = config.get("port", FOCAS_DEFAULT_PORT)

        # =====================================================================
        # TCP Handshake
        # =====================================================================

        # SYN
        syn_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=focas_port,
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
            metadata={"tcp_flags": "SYN"},
        ))
        state.tcp_seq_client += 1
        current_time += 1.0

        # SYN-ACK
        syn_ack_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=focas_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_SYN_ACK,
            ttl=64,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack_packet,
            direction="response",
            metadata={"tcp_flags": "SYN-ACK"},
        ))
        state.tcp_seq_server += 1
        current_time += 1.0

        # ACK
        ack_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=focas_port,
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
            metadata={"tcp_flags": "ACK"},
        ))
        current_time += 2.0

        # =====================================================================
        # FOCAS Connect
        # =====================================================================

        connect_req = build_connect_request(
            ip_address=dst.ip_address,
            port=focas_port,
        )

        connect_req_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=focas_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=connect_req,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=connect_req_packet,
            direction="request",
            metadata={"focas": "cnc_allclibhndl3"},
        ))
        state.tcp_seq_client += len(connect_req)
        current_time += get_response_delay(src.vendor_fingerprint)

        # Connect response
        state.handle = random.randint(1, 255)
        connect_resp = build_connect_response(handle=state.handle)

        connect_resp_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=focas_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=connect_resp,
            ttl=64,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=connect_resp_packet,
            direction="response",
            metadata={"focas": "cnc_allclibhndl3_response", "handle": state.handle},
        ))
        state.tcp_seq_server += len(connect_resp)
        current_time += 5.0

        # =====================================================================
        # System Info Query
        # =====================================================================

        state.sequence += 1
        sysinfo_req = build_sysinfo_request(state.sequence, state.handle)

        sysinfo_req_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=focas_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=sysinfo_req,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=sysinfo_req_packet,
            direction="request",
            metadata={"focas": "cnc_sysinfo"},
        ))
        state.tcp_seq_client += len(sysinfo_req)
        current_time += get_response_delay(src.vendor_fingerprint)

        # System info response
        cnc_model = config.get("cnc_model", "30i-B")
        cnc_type = config.get("cnc_type", CNCType.MACHINING_CENTER)
        num_axes = config.get("axes", 5)

        sysinfo_resp = build_sysinfo_response(
            sequence=state.sequence,
            handle=state.handle,
            model=cnc_model,
            cnc_type=cnc_type,
            axes=num_axes,
        )

        sysinfo_resp_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=focas_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=sysinfo_resp,
            ttl=64,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=sysinfo_resp_packet,
            direction="response",
            metadata={"focas": "cnc_sysinfo_response", "model": cnc_model},
        ))
        state.tcp_seq_server += len(sysinfo_resp)

        # Update state
        state.is_connected = True
        state.state_name = "connected"
        state.cnc_model = cnc_model

        logger.debug(
            f"FANUC startup complete: model={cnc_model}, "
            f"handle={state.handle}, axes={num_axes}"
        )

        return events

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: FANUCConversationState,
        current_time_ms: float,
    ) -> list[PacketEvent]:
        """Generate FOCAS polling cycle.

        Rotates through common CNC monitoring functions.

        Args:
            flow: Flow context
            state: FANUC conversation state
            current_time_ms: Current simulation time

        Returns:
            List of PacketEvent for poll request/response
        """
        events = []

        if not state.is_connected:
            logger.warning("FANUC poll cycle called but not connected")
            return events

        src = flow.source
        dst = flow.destination
        config = flow.config

        ttl = src.get_tcp_ttl()
        window = src.get_tcp_window_size()
        focas_port = config.get("port", FOCAS_DEFAULT_PORT)

        # Select next polling function
        poll_name, req_builder, resp_builder = POLL_FUNCTIONS[
            state.poll_index % len(POLL_FUNCTIONS)
        ]
        state.poll_index += 1
        state.sequence += 1

        # Build request
        if poll_name in ("rdposition", "acts"):
            # These have extra parameters
            if poll_name == "rdposition":
                request = req_builder(state.sequence, state.handle, 0, -1)
            else:
                request = req_builder(state.sequence, state.handle, 1)
        else:
            request = req_builder(state.sequence, state.handle)

        req_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=focas_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=request,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=req_packet,
            direction="request",
            metadata={"focas": f"cnc_{poll_name}"},
        ))
        state.tcp_seq_client += len(request)

        # Generate response
        response_delay = get_response_delay(src.vendor_fingerprint)
        response_time = current_time_ms + response_delay

        # Build response with simulated data
        if poll_name == "rdposition":
            # Generate varying positions
            positions = self._generate_axis_positions(state)
            response = resp_builder(state.sequence, state.handle, positions)
        elif poll_name == "acts":
            # Generate varying spindle data
            spindle = self._generate_spindle_data(state)
            response = resp_builder(state.sequence, state.handle, spindle)
        elif poll_name == "statinfo":
            status = self._generate_cnc_status(state)
            response = resp_builder(state.sequence, state.handle, status)
        else:
            response = resp_builder(state.sequence, state.handle)

        resp_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=focas_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=response,
            ttl=64,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=resp_packet,
            direction="response",
            metadata={"focas": f"cnc_{poll_name}_response"},
        ))
        state.tcp_seq_server += len(response)

        return events

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: FANUCConversationState,
    ) -> list[PacketEvent]:
        """Generate FOCAS disconnect sequence.

        Args:
            flow: Flow context
            state: FANUC conversation state

        Returns:
            List of PacketEvent for disconnect
        """
        events = []

        src = flow.source
        dst = flow.destination
        config = flow.config

        ttl = src.get_tcp_ttl()
        window = src.get_tcp_window_size()
        focas_port = config.get("port", FOCAS_DEFAULT_PORT)

        current_time = 0.0

        # FOCAS disconnect
        state.sequence += 1
        disconnect_req = build_disconnect_request(state.sequence, state.handle)

        disconnect_req_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=focas_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags=TCP_PSH_ACK,
            payload=disconnect_req,
            ttl=ttl,
            window=window,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=disconnect_req_packet,
            direction="request",
            metadata={"focas": "cnc_freelibhndl"},
        ))
        state.tcp_seq_client += len(disconnect_req)
        current_time += 5.0

        disconnect_resp = build_disconnect_response(state.sequence, state.handle)

        disconnect_resp_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=focas_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_PSH_ACK,
            payload=disconnect_resp,
            ttl=64,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=disconnect_resp_packet,
            direction="response",
            metadata={"focas": "cnc_freelibhndl_response"},
        ))
        state.tcp_seq_server += len(disconnect_resp)
        current_time += 2.0

        # TCP FIN
        fin_packet = build_tcp_packet(
            src_mac=src.mac_address,
            dst_mac=dst.mac_address,
            src_ip=src.ip_address,
            dst_ip=dst.ip_address,
            src_port=state.client_port,
            dst_port=focas_port,
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
        current_time += 1.0

        fin_ack_packet = build_tcp_packet(
            src_mac=dst.mac_address,
            dst_mac=src.mac_address,
            src_ip=dst.ip_address,
            dst_ip=src.ip_address,
            src_port=focas_port,
            dst_port=state.client_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags=TCP_FIN_ACK,
            ttl=64,
            window=65535,
        )
        events.append(PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_ack_packet,
            direction="response",
            metadata={"tcp_flags": "FIN-ACK"},
        ))

        state.is_connected = False
        state.state_name = "disconnected"

        return events

    def _generate_axis_positions(
        self,
        state: FANUCConversationState,
    ) -> list[AxisPosition]:
        """Generate simulated axis positions with slight variation."""
        # Add small random movement to simulate machining
        x_var = random.uniform(-0.5, 0.5)
        y_var = random.uniform(-0.5, 0.5)
        z_var = random.uniform(-0.1, 0.1)

        return [
            AxisPosition("X", 150.0 + x_var, 150.0 + x_var, 0.0, 0.0),
            AxisPosition("Y", 75.5 + y_var, 75.5 + y_var, 0.0, 0.0),
            AxisPosition("Z", -50.25 + z_var, 249.75 + z_var, 0.0, 0.0),
            AxisPosition("A", 45.0, 45.0, 0.0, 0.0),
            AxisPosition("B", 0.0, 0.0, 0.0, 0.0),
        ]

    def _generate_spindle_data(
        self,
        state: FANUCConversationState,
    ) -> SpindleData:
        """Generate simulated spindle data with variation."""
        base_speed = 8000
        speed_var = random.randint(-100, 100)
        load_var = random.randint(-5, 5)

        return SpindleData(
            spindle_num=1,
            actual_speed=base_speed + speed_var,
            commanded_speed=base_speed,
            load=35 + load_var,
            motor_temp=45 + random.randint(-2, 2),
        )

    def _generate_cnc_status(
        self,
        state: FANUCConversationState,
    ) -> CNCStatus:
        """Generate simulated CNC status."""
        return CNCStatus(
            run=1,      # Running
            motion=1,   # Moving
            aut=1,      # Auto mode
            alarm=0,    # No alarm
        )

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate FANUC configuration.

        Args:
            config: Configuration dictionary

        Returns:
            List of validation error messages
        """
        errors = []

        if "port" in config:
            port = config["port"]
            if not isinstance(port, int) or port < 1 or port > 65535:
                errors.append("port must be a valid TCP port (1-65535)")

        if "cnc_model" in config:
            from app.protocol_engines.fanuc.packets import FANUC_MODELS
            model = config["cnc_model"]
            if model not in FANUC_MODELS:
                errors.append(f"cnc_model must be one of: {list(FANUC_MODELS.keys())}")

        if "axes" in config:
            axes = config["axes"]
            if not isinstance(axes, int) or axes < 1 or axes > 32:
                errors.append("axes must be between 1 and 32")

        if "cnc_type" in config:
            cnc_type = config["cnc_type"]
            if cnc_type not in [t.value for t in CNCType]:
                errors.append(f"cnc_type must be a valid CNCType value (0-5)")

        return errors

    def create_state(
        self,
        flow_id: str,
        config: dict[str, Any],
    ) -> FANUCConversationState:
        """Create FANUC conversation state.

        Args:
            flow_id: Flow identifier
            config: Flow configuration

        Returns:
            Initialized FANUCConversationState
        """
        return FANUCConversationState(
            flow_id=flow_id,
            state_name="init",
            client_port=random.randint(49152, 65535),
        )
