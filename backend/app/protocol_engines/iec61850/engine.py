# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""IEC 61850 protocol engine implementation.

Supports:
- MMS (Manufacturing Message Specification) over TCP/IP
- GOOSE (Generic Object Oriented Substation Event) over Layer 2
- SV (Sampled Values) over Layer 2

IEC 61850 is the communication standard for substations and
intelligent electronic devices (IEDs) in power systems.
"""

import random
import time
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.iec61850.packets import (
    build_cotp_cr,
    build_cotp_cc,
    build_cotp_dt,
    build_mms_initiate_request,
    build_mms_initiate_response,
    build_mms_read_request,
    build_mms_read_response,
    build_tpkt_header,
    build_goose_packet,
    build_sv_packet,
    generate_3phase_samples,
    build_ethernet_header,
)
from app.protocol_engines.iec61850.types import (
    MMS_PORT,
    GOOSEConfig,
    SVConfig,
    GOOSEDataType,
)
from app.protocol_engines.types import (
    FlowContext,
    IEC61850ConversationState,
    PacketEvent,
    ProtocolType,
)


def _build_tcp_packet(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    payload: bytes,
    seq: int,
    ack: int,
    flags: str = "PA",
    ttl: int = 64,
    window: int = 65535,
) -> bytes:
    """Build a TCP/IP packet with Ethernet header.

    Simplified packet building for MMS traffic.
    """
    import struct
    import socket

    # Ethernet header
    eth_header = build_ethernet_header(src_mac, dst_mac, 0x0800)

    # IP header
    version_ihl = 0x45
    dscp_ecn = 0x00
    total_length = 20 + 20 + len(payload)  # IP + TCP + payload
    identification = random.randint(1, 65535)
    flags_fragment = 0x4000  # Don't fragment
    protocol = 6  # TCP
    checksum = 0  # Will be calculated

    src_ip_bytes = socket.inet_aton(src_ip)
    dst_ip_bytes = socket.inet_aton(dst_ip)

    ip_header = struct.pack(
        ">BBHHHBBH4s4s",
        version_ihl,
        dscp_ecn,
        total_length,
        identification,
        flags_fragment,
        ttl,
        protocol,
        checksum,
        src_ip_bytes,
        dst_ip_bytes,
    )

    # TCP header
    data_offset_flags = (5 << 12)  # 5 * 4 = 20 bytes header
    if "S" in flags:
        data_offset_flags |= 0x02
    if "A" in flags:
        data_offset_flags |= 0x10
    if "P" in flags:
        data_offset_flags |= 0x08
    if "F" in flags:
        data_offset_flags |= 0x01
    if "R" in flags:
        data_offset_flags |= 0x04

    tcp_header = struct.pack(
        ">HHIIHHHH",
        src_port,
        dst_port,
        seq,
        ack,
        data_offset_flags,
        window,
        0,  # Checksum placeholder
        0,  # Urgent pointer
    )

    return eth_header + ip_header + tcp_header + payload


@register_engine(ProtocolType.IEC61850)
class IEC61850Engine(ProtocolEngine):
    """IEC 61850 protocol engine supporting MMS, GOOSE, and SV."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.IEC61850

    def create_initial_state(self, flow: FlowContext) -> IEC61850ConversationState:
        """Create initial conversation state.

        Determines protocol mode from config and initializes accordingly.
        """
        mode = flow.config.get("mode", "mms")

        state = IEC61850ConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            cotp_src_ref=random.randint(0x0100, 0x0FFF),
        )

        if mode == "goose":
            # Initialize GOOSE state
            state.goose_state_num = 1
            state.goose_sq_num = 0
            state.goose_time_allowed_to_live = flow.config.get(
                "time_allowed_to_live", 4000
            )

        elif mode == "sv":
            # Initialize SV state
            state.sv_smp_cnt = 0
            state.sv_smp_synch = flow.config.get("smp_synch", 2)  # Global sync

        return state

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: IEC61850ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate startup sequence based on protocol mode.

        MMS: TCP handshake + COTP connection + MMS initiate
        GOOSE: No startup needed (Layer 2 multicast)
        SV: No startup needed (Layer 2 multicast)
        """
        mode = flow.config.get("mode", "mms")

        if mode == "mms":
            yield from self._generate_mms_startup(flow, state, start_time_ms)
        elif mode == "goose":
            # GOOSE is connectionless, but we emit an initial GOOSE
            # to establish presence
            state.state_name = "goose_publishing"
            # No explicit startup packets, first poll cycle will emit GOOSE
        elif mode == "sv":
            # SV is connectionless
            state.state_name = "sv_streaming"
            # No explicit startup packets

    def _generate_mms_startup(
        self,
        flow: FlowContext,
        state: IEC61850ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate MMS connection establishment sequence.

        1. TCP three-way handshake
        2. COTP Connection Request/Confirm
        3. MMS Initiate Request/Response
        """
        # Initialize TCP sequence numbers
        tcp_seq_client = random.randint(1000, 9999)
        tcp_seq_server = random.randint(1000, 9999)

        # === TCP Three-way Handshake ===

        # SYN
        syn_packet = _build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=flow.source.port or random.randint(49152, 65535),
            dst_port=MMS_PORT,
            payload=b"",
            seq=tcp_seq_client,
            ack=0,
            flags="S",
        )
        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=syn_packet,
            direction="request",
            metadata={"type": "tcp_syn"},
        )

        # SYN-ACK
        syn_ack_time = start_time_ms + random.uniform(1.0, 3.0)
        syn_ack_packet = _build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=MMS_PORT,
            dst_port=flow.source.port or random.randint(49152, 65535),
            payload=b"",
            seq=tcp_seq_server,
            ack=tcp_seq_client + 1,
            flags="SA",
        )
        yield PacketEvent(
            timestamp_ms=syn_ack_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack_packet,
            direction="response",
            metadata={"type": "tcp_syn_ack"},
        )

        # ACK
        ack_time = syn_ack_time + random.uniform(0.1, 0.5)
        ack_packet = _build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=flow.source.port or random.randint(49152, 65535),
            dst_port=MMS_PORT,
            payload=b"",
            seq=tcp_seq_client + 1,
            ack=tcp_seq_server + 1,
            flags="A",
        )
        yield PacketEvent(
            timestamp_ms=ack_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"type": "tcp_ack"},
        )

        tcp_seq_client += 1
        tcp_seq_server += 1

        # === COTP Connection Request ===
        cotp_cr_time = ack_time + random.uniform(1.0, 5.0)
        cotp_cr = build_cotp_cr(state.cotp_src_ref, 0)
        tpkt_cr = build_tpkt_header(len(cotp_cr)) + cotp_cr

        cr_packet = _build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=flow.source.port or random.randint(49152, 65535),
            dst_port=MMS_PORT,
            payload=tpkt_cr,
            seq=tcp_seq_client,
            ack=tcp_seq_server,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=cotp_cr_time,
            flow_id=flow.flow_id,
            packet_bytes=cr_packet,
            direction="request",
            metadata={"type": "cotp_cr"},
        )
        tcp_seq_client += len(tpkt_cr)

        # === COTP Connection Confirm ===
        cotp_cc_time = cotp_cr_time + random.uniform(2.0, 10.0)
        state.cotp_dst_ref = random.randint(0x0100, 0x0FFF)
        cotp_cc = build_cotp_cc(state.cotp_dst_ref, state.cotp_src_ref)
        tpkt_cc = build_tpkt_header(len(cotp_cc)) + cotp_cc

        cc_packet = _build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=MMS_PORT,
            dst_port=flow.source.port or random.randint(49152, 65535),
            payload=tpkt_cc,
            seq=tcp_seq_server,
            ack=tcp_seq_client,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=cotp_cc_time,
            flow_id=flow.flow_id,
            packet_bytes=cc_packet,
            direction="response",
            metadata={"type": "cotp_cc"},
        )
        tcp_seq_server += len(tpkt_cc)

        state.is_connected = True

        # === MMS Initiate Request ===
        mms_init_time = cotp_cc_time + random.uniform(1.0, 5.0)
        mms_init_req = build_mms_initiate_request()
        cotp_dt_req = build_cotp_dt(mms_init_req)
        tpkt_init_req = build_tpkt_header(len(cotp_dt_req)) + cotp_dt_req

        init_req_packet = _build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=flow.source.port or random.randint(49152, 65535),
            dst_port=MMS_PORT,
            payload=tpkt_init_req,
            seq=tcp_seq_client,
            ack=tcp_seq_server,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=mms_init_time,
            flow_id=flow.flow_id,
            packet_bytes=init_req_packet,
            direction="request",
            metadata={"type": "mms_initiate_request"},
        )
        tcp_seq_client += len(tpkt_init_req)

        # === MMS Initiate Response ===
        mms_resp_time = mms_init_time + random.uniform(5.0, 20.0)
        mms_init_resp = build_mms_initiate_response()
        cotp_dt_resp = build_cotp_dt(mms_init_resp)
        tpkt_init_resp = build_tpkt_header(len(cotp_dt_resp)) + cotp_dt_resp

        init_resp_packet = _build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=MMS_PORT,
            dst_port=flow.source.port or random.randint(49152, 65535),
            payload=tpkt_init_resp,
            seq=tcp_seq_server,
            ack=tcp_seq_client,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=mms_resp_time,
            flow_id=flow.flow_id,
            packet_bytes=init_resp_packet,
            direction="response",
            metadata={"type": "mms_initiate_response"},
        )
        tcp_seq_server += len(tpkt_init_resp)

        state.is_associated = True
        state.state_name = "mms_associated"

        # Store TCP state for poll cycles
        state.custom_data["tcp_seq_client"] = tcp_seq_client
        state.custom_data["tcp_seq_server"] = tcp_seq_server
        state.custom_data["client_port"] = flow.source.port or random.randint(
            49152, 65535
        )

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: IEC61850ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate a poll cycle based on protocol mode.

        MMS: Read request/response
        GOOSE: Publish GOOSE message
        SV: Publish sampled values
        """
        mode = flow.config.get("mode", "mms")

        if mode == "mms":
            yield from self._generate_mms_poll_cycle(flow, state, cycle_time_ms)
        elif mode == "goose":
            yield from self._generate_goose_poll_cycle(flow, state, cycle_time_ms)
        elif mode == "sv":
            yield from self._generate_sv_poll_cycle(flow, state, cycle_time_ms)

    def _generate_mms_poll_cycle(
        self,
        flow: FlowContext,
        state: IEC61850ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate MMS read request/response."""
        if not state.is_associated:
            return

        # Get TCP state
        tcp_seq_client = state.custom_data.get("tcp_seq_client", 1000)
        tcp_seq_server = state.custom_data.get("tcp_seq_server", 1000)
        client_port = state.custom_data.get("client_port", 49152)

        # Get variable to read
        variable_spec = flow.config.get(
            "variable", "XCBR1$ST$Pos$stVal"
        )
        domain_id = flow.config.get("domain_id", "LD0")

        invoke_id = state.next_invoke_id()

        # Build MMS Read Request
        mms_read_req = build_mms_read_request(invoke_id, variable_spec, domain_id)
        cotp_dt_req = build_cotp_dt(mms_read_req)
        tpkt_req = build_tpkt_header(len(cotp_dt_req)) + cotp_dt_req

        req_packet = _build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=client_port,
            dst_port=MMS_PORT,
            payload=tpkt_req,
            seq=tcp_seq_client,
            ack=tcp_seq_server,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=req_packet,
            direction="request",
            metadata={
                "type": "mms_read_request",
                "invoke_id": invoke_id,
                "variable": variable_spec,
            },
        )
        tcp_seq_client += len(tpkt_req)

        # Response delay
        response_delay = random.uniform(5.0, 30.0)
        response_time = cycle_time_ms + response_delay

        # Build MMS Read Response
        # Generate response values based on config
        values = flow.config.get("values", [(True, "boolean")])
        mms_read_resp = build_mms_read_response(invoke_id, values)
        cotp_dt_resp = build_cotp_dt(mms_read_resp)
        tpkt_resp = build_tpkt_header(len(cotp_dt_resp)) + cotp_dt_resp

        resp_packet = _build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=MMS_PORT,
            dst_port=client_port,
            payload=tpkt_resp,
            seq=tcp_seq_server,
            ack=tcp_seq_client,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=resp_packet,
            direction="response",
            metadata={
                "type": "mms_read_response",
                "invoke_id": invoke_id,
                "response_delay_ms": response_delay,
            },
        )
        tcp_seq_server += len(tpkt_resp)

        # Update state
        state.custom_data["tcp_seq_client"] = tcp_seq_client
        state.custom_data["tcp_seq_server"] = tcp_seq_server

    def _generate_goose_poll_cycle(
        self,
        flow: FlowContext,
        state: IEC61850ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate GOOSE publish message.

        GOOSE messages are multicast Layer 2 frames containing
        status changes (e.g., breaker positions, interlocks).
        """
        # Build GOOSE config from flow config
        goose_config = GOOSEConfig(
            gocb_ref=flow.config.get(
                "gocb_ref", f"{flow.source.device_id}LD0/LLN0$GO$gcb01"
            ),
            dat_set=flow.config.get(
                "dat_set", f"{flow.source.device_id}LD0/LLN0$GOOSE1"
            ),
            go_id=flow.config.get("go_id", flow.source.device_id),
            app_id=flow.config.get("app_id", random.randint(0x0000, 0x3FFF)),
            conf_rev=flow.config.get("conf_rev", 1),
            needs_comm=flow.config.get("needs_comm", False),
            vlan_id=flow.config.get("vlan_id"),
            vlan_priority=flow.config.get("vlan_priority", 4),
        )

        # Get data values
        # Default: simulate a breaker position (boolean) and quality
        data_values = flow.config.get(
            "data_values",
            [
                (True, GOOSEDataType.BOOLEAN),  # Breaker position
                (0, GOOSEDataType.BIT_STRING),  # Quality flags
            ],
        )

        # Check if data changed (would increment stNum)
        data_changed = flow.config.get("data_changed", False)
        if data_changed:
            state.increment_goose_state()
        else:
            state.increment_goose_sq()

        # Build GOOSE packet
        goose_packet = build_goose_packet(
            src=flow.source,
            config=goose_config,
            st_num=state.goose_state_num,
            sq_num=state.goose_sq_num,
            all_data=data_values,
            timestamp=cycle_time_ms / 1000.0 + time.time(),  # Approximate real time
        )

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=goose_packet,
            direction="request",  # GOOSE is publish, not request/response
            metadata={
                "type": "goose_publish",
                "st_num": state.goose_state_num,
                "sq_num": state.goose_sq_num,
                "app_id": goose_config.app_id,
                "data_changed": data_changed,
            },
        )

    def _generate_sv_poll_cycle(
        self,
        flow: FlowContext,
        state: IEC61850ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Sampled Values publish message.

        SV messages are multicast Layer 2 frames containing
        analog measurements (voltage, current) at high sample rates.
        """
        # Build SV config from flow config
        sv_config = SVConfig(
            sv_id=flow.config.get("sv_id", f"{flow.source.device_id}_MU01"),
            dat_set=flow.config.get(
                "dat_set", f"{flow.source.device_id}MU01/LLN0$SV01"
            ),
            app_id=flow.config.get("app_id", random.randint(0x4000, 0x7FFF)),
            conf_rev=flow.config.get("conf_rev", 1),
            smp_rate=flow.config.get("smp_rate", 80),  # 80 samples per cycle
            vlan_id=flow.config.get("vlan_id"),
            vlan_priority=flow.config.get("vlan_priority", 4),
        )

        # Generate sample data
        magnitude = flow.config.get("magnitude", 1.0)
        frequency = flow.config.get("frequency", 50.0)

        sample_data = generate_3phase_samples(
            smp_cnt=state.sv_smp_cnt,
            magnitude=magnitude,
            frequency=frequency,
            samples_per_cycle=sv_config.smp_rate,
            include_neutral=flow.config.get("include_neutral", True),
        )

        # Build SV packet
        sv_packet = build_sv_packet(
            src=flow.source,
            config=sv_config,
            smp_cnt=state.sv_smp_cnt,
            sample_data=sample_data,
            smp_synch=state.sv_smp_synch,
        )

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=sv_packet,
            direction="request",  # SV is publish
            metadata={
                "type": "sv_publish",
                "smp_cnt": state.sv_smp_cnt,
                "app_id": sv_config.app_id,
                "smp_synch": state.sv_smp_synch,
            },
        )

        # Increment sample count
        state.increment_sv_sample()

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: IEC61850ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate shutdown sequence.

        MMS: TCP FIN handshake
        GOOSE/SV: No explicit shutdown needed
        """
        mode = flow.config.get("mode", "mms")

        if mode == "mms" and state.is_connected:
            yield from self._generate_mms_shutdown(flow, state, start_time_ms)

        # GOOSE and SV are connectionless - no shutdown needed
        state.state_name = "idle"
        state.is_connected = False
        state.is_associated = False

    def _generate_mms_shutdown(
        self,
        flow: FlowContext,
        state: IEC61850ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate MMS/TCP connection shutdown."""
        tcp_seq_client = state.custom_data.get("tcp_seq_client", 1000)
        tcp_seq_server = state.custom_data.get("tcp_seq_server", 1000)
        client_port = state.custom_data.get("client_port", 49152)

        # FIN from client
        fin_packet = _build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=client_port,
            dst_port=MMS_PORT,
            payload=b"",
            seq=tcp_seq_client,
            ack=tcp_seq_server,
            flags="FA",
        )
        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=fin_packet,
            direction="request",
            metadata={"type": "tcp_fin"},
        )

        # FIN-ACK from server
        fin_ack_time = start_time_ms + random.uniform(1.0, 3.0)
        fin_ack_packet = _build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=MMS_PORT,
            dst_port=client_port,
            payload=b"",
            seq=tcp_seq_server,
            ack=tcp_seq_client + 1,
            flags="FA",
        )
        yield PacketEvent(
            timestamp_ms=fin_ack_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_ack_packet,
            direction="response",
            metadata={"type": "tcp_fin_ack"},
        )

        # Final ACK from client
        ack_time = fin_ack_time + random.uniform(0.1, 0.5)
        ack_packet = _build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=client_port,
            dst_port=MMS_PORT,
            payload=b"",
            seq=tcp_seq_client + 1,
            ack=tcp_seq_server + 1,
            flags="A",
        )
        yield PacketEvent(
            timestamp_ms=ack_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"type": "tcp_ack"},
        )

    def validate_config(self, config: dict) -> list[str]:
        """Validate IEC 61850 configuration."""
        errors = []

        mode = config.get("mode", "mms")
        if mode not in ["mms", "goose", "sv"]:
            errors.append(f"Invalid mode: {mode}. Must be 'mms', 'goose', or 'sv'")

        if mode == "mms":
            # MMS validation
            if "variable" in config and not isinstance(config["variable"], str):
                errors.append("variable must be a string")

        elif mode == "goose":
            # GOOSE validation
            app_id = config.get("app_id")
            if app_id is not None:
                if not isinstance(app_id, int) or not (0x0000 <= app_id <= 0x3FFF):
                    errors.append("GOOSE app_id must be integer 0x0000-0x3FFF")

            if "gocb_ref" in config and not isinstance(config["gocb_ref"], str):
                errors.append("gocb_ref must be a string")

        elif mode == "sv":
            # SV validation
            app_id = config.get("app_id")
            if app_id is not None:
                if not isinstance(app_id, int) or not (0x4000 <= app_id <= 0x7FFF):
                    errors.append("SV app_id must be integer 0x4000-0x7FFF")

            smp_rate = config.get("smp_rate")
            if smp_rate is not None:
                if not isinstance(smp_rate, int) or smp_rate not in [80, 256, 4000]:
                    errors.append("smp_rate must be 80, 256, or 4000")

            frequency = config.get("frequency")
            if frequency is not None:
                if not isinstance(frequency, (int, float)) or frequency not in [50, 60]:
                    errors.append("frequency must be 50 or 60 Hz")

        return errors
