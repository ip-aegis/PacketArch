# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""S7 Communication protocol engine for Siemens PLCs.

Implements the S7comm protocol (ISO-on-TCP) for simulating
traffic to/from Siemens S7-300/400/1200/1500 PLCs.
"""

from __future__ import annotations

import os
import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.s7.config import (
    S7Area,
    S7ConnectionType,
    S7DataReturnCode,
    S7FlowConfig,
    S7ReadArea,
    S7WriteArea,
    S7_CPU_PROFILES,
    get_cpu_profile,
)
from app.protocol_engines.s7.packets import (
    build_cotp_cc_packet,
    build_cotp_cr_packet,
    build_cotp_dr_packet,
    build_s7_read_request,
    build_s7_read_response,
    build_s7_setup_request,
    build_s7_setup_response,
    build_s7_szl_request,
    build_s7_szl_response,
    build_s7_write_request,
    build_s7_write_response,
)
from app.protocol_engines.tcp_builder import (
    build_tcp_ack as _build_tcp_ack,
    build_tcp_fin as _build_tcp_fin,
    build_tcp_packet as _build_tcp_packet,
    build_tcp_syn as _build_tcp_syn,
    build_tcp_syn_ack as _build_tcp_syn_ack,
)
from app.protocol_engines.types import (
    ConversationState,
    DeviceContext,
    FlowContext,
    PacketEvent,
    ProtocolType,
)
from app.traffic_generator.flow_coordinator import (
    sample_address_range,
)


# S7 default port (ISO-TSAP)
S7_PORT = 102


def _parse_s7_config(flow_config: dict) -> S7FlowConfig:
    """Parse flow config dict into S7FlowConfig dataclass."""
    read_areas = []
    for area_dict in flow_config.get("read_areas", []):
        read_areas.append(
            S7ReadArea(
                area=area_dict.get("area", S7Area.DB),
                db_number=area_dict.get("db_number", 1),
                start=area_dict.get("start", 0),
                size=area_dict.get("size", 10),
                transport_size=area_dict.get("transport_size", 2),
            )
        )

    write_areas = []
    for area_dict in flow_config.get("write_areas", []):
        write_areas.append(
            S7WriteArea(
                area=area_dict.get("area", S7Area.DB),
                db_number=area_dict.get("db_number", 1),
                start=area_dict.get("start", 0),
                data=bytes(area_dict.get("data", [0] * 10)),
                transport_size=area_dict.get("transport_size", 2),
            )
        )

    return S7FlowConfig(
        rack=flow_config.get("rack", 0),
        slot=flow_config.get("slot", 1),
        pdu_size=flow_config.get("pdu_size", 480),
        connection_type=flow_config.get("connection_type", S7ConnectionType.PG),
        read_areas=read_areas if read_areas else None,
        write_areas=write_areas,
        poll_read_only=flow_config.get("poll_read_only", True),
        use_optimized_read=flow_config.get("use_optimized_read", False),
    )


@register_engine(ProtocolType.S7COMM)
class S7Engine(ProtocolEngine):
    """S7 Communication protocol engine for Siemens PLCs."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.S7COMM

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        """Create initial conversation state for S7 communication."""
        return ConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            transaction_id=0,  # S7 PDU reference
            sequence_number=0,
            custom_data={
                "tcp_seq_client": random.randint(100_000_000, 4_000_000_000),
                "tcp_seq_server": random.randint(100_000_000, 4_000_000_000),
                "tcp_ack_client": 0,
                "tcp_ack_server": 0,
                "cotp_src_ref": random.randint(1, 255),
                "cotp_dst_ref": 0,  # Assigned by server
                "pdu_ref": 0,  # S7 PDU reference counter
                "negotiated_pdu_size": 480,
            },
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate S7 startup sequence: TCP handshake + COTP CR/CC + S7 setup.

        The S7 connection establishment consists of:
        1. TCP 3-way handshake
        2. COTP Connection Request / Connection Confirm
        3. S7 Setup Communication request / response
        """
        config = _parse_s7_config(flow.config)
        current_time = start_time_ms

        # Get sequence numbers
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]

        # Get fingerprinted TCP options for client and server
        client_tcp_opts = flow.source.fingerprint_applicator.get_tcp_options()
        server_tcp_opts = flow.destination.fingerprint_applicator.get_tcp_options()

        # Get response timing from CPU profile
        cpu_model = flow.config.get("cpu_model", "CPU 1214C")
        profile = get_cpu_profile(cpu_model)
        if profile:
            base_delay = random.uniform(*profile.response_delay_ms)
        else:
            base_delay = random.uniform(5.0, 20.0)

        # ============================================================
        # Phase 1: TCP Three-Way Handshake
        # ============================================================

        # SYN from client
        syn_packet = _build_tcp_syn(
            flow.source, flow.destination, client_seq, tcp_options=client_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_packet,
            direction="request",
            metadata={"type": "tcp_syn", "phase": "tcp_handshake"},
        )
        current_time += random.uniform(0.5, 2.0)

        # SYN-ACK from server
        syn_ack_packet = _build_tcp_syn_ack(
            flow.destination, flow.source, server_seq, client_seq + 1,
            tcp_options=server_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack_packet,
            direction="response",
            metadata={"type": "tcp_syn_ack", "phase": "tcp_handshake"},
        )
        current_time += random.uniform(0.1, 0.5)

        # ACK from client
        ack_packet = _build_tcp_ack(
            flow.source, flow.destination, client_seq + 1, server_seq + 1,
            tcp_options=client_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"type": "tcp_ack", "phase": "tcp_handshake"},
        )

        # Update TCP state
        client_seq += 1
        server_seq += 1
        state.custom_data["tcp_seq_client"] = client_seq
        state.custom_data["tcp_seq_server"] = server_seq
        state.custom_data["tcp_ack_client"] = server_seq
        state.custom_data["tcp_ack_server"] = client_seq

        current_time += random.uniform(0.5, 2.0)

        # ============================================================
        # Phase 2: COTP Connection Request / Connection Confirm
        # ============================================================

        # COTP CR (Connection Request) from client
        cotp_cr_payload = build_cotp_cr_packet(
            rack=config.rack,
            slot=config.slot,
            connection_type=config.connection_type,
        )
        cotp_cr_packet = _build_tcp_packet(
            flow.source, flow.destination, cotp_cr_payload, client_seq, server_seq, "PA",
            tcp_options=client_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=cotp_cr_packet,
            direction="request",
            metadata={"type": "cotp_cr", "phase": "cotp_connect"},
        )
        client_seq += len(cotp_cr_payload)
        state.custom_data["tcp_seq_client"] = client_seq
        current_time += base_delay

        # COTP CC (Connection Confirm) from server
        cotp_dst_ref = random.randint(1, 255)
        state.custom_data["cotp_dst_ref"] = cotp_dst_ref
        cotp_cc_payload = build_cotp_cc_packet(
            dst_ref=state.custom_data["cotp_src_ref"],
            src_ref=cotp_dst_ref,
        )
        cotp_cc_packet = _build_tcp_packet(
            flow.destination, flow.source, cotp_cc_payload, server_seq, client_seq, "PA",
            tcp_options=server_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=cotp_cc_packet,
            direction="response",
            metadata={"type": "cotp_cc", "phase": "cotp_connect"},
        )
        server_seq += len(cotp_cc_payload)
        state.custom_data["tcp_seq_server"] = server_seq

        current_time += random.uniform(0.5, 2.0)

        # ============================================================
        # Phase 3: S7 Setup Communication
        # ============================================================

        # S7 Setup Communication Request from client
        pdu_ref = state.custom_data["pdu_ref"]
        s7_setup_req_payload = build_s7_setup_request(
            pdu_ref=pdu_ref,
            pdu_size=config.pdu_size,
        )
        s7_setup_req_packet = _build_tcp_packet(
            flow.source,
            flow.destination,
            s7_setup_req_payload,
            client_seq,
            server_seq,
            "PA",
            tcp_options=client_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=s7_setup_req_packet,
            direction="request",
            metadata={"type": "s7_setup_req", "phase": "s7_setup"},
        )
        client_seq += len(s7_setup_req_payload)
        state.custom_data["tcp_seq_client"] = client_seq
        current_time += base_delay

        # S7 Setup Communication Response from server
        # Server may negotiate a different PDU size
        negotiated_pdu_size = min(config.pdu_size, 480)
        if profile:
            negotiated_pdu_size = min(config.pdu_size, profile.max_pdu_size)
        state.custom_data["negotiated_pdu_size"] = negotiated_pdu_size

        s7_setup_resp_payload = build_s7_setup_response(
            pdu_ref=pdu_ref,
            pdu_size=negotiated_pdu_size,
        )
        s7_setup_resp_packet = _build_tcp_packet(
            flow.destination,
            flow.source,
            s7_setup_resp_payload,
            server_seq,
            client_seq,
            "PA",
            tcp_options=server_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=s7_setup_resp_packet,
            direction="response",
            metadata={
                "type": "s7_setup_resp",
                "phase": "s7_setup",
                "pdu_size": negotiated_pdu_size,
            },
        )
        server_seq += len(s7_setup_resp_payload)
        state.custom_data["tcp_seq_server"] = server_seq

        # Update state
        state.custom_data["pdu_ref"] = pdu_ref + 1
        state.state_name = "connected"

        # ============================================================
        # Phase 4: SZL Query (Module Identification)
        # ============================================================
        # Emit SZL 0x0011 (module identification) right after setup.
        # Cisco Cyber Vision uses this to fingerprint Siemens devices
        # (order code, serial number, firmware version).
        current_time += random.uniform(10.0, 50.0)
        yield from self.generate_szl_query_sequence(
            flow, state, start_time_ms=current_time,
        )

    def generate_szl_query_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
        szl_id: int = 0x0011,
    ) -> Iterator[PacketEvent]:
        """Generate S7 SZL (System Status List) query sequence.

        SZL queries are used by scanners like Cisco Cyber Vision to identify
        devices and detect vulnerable firmware versions.

        Key SZL IDs:
            - 0x0011: Module Identification (order code, serial, firmware version)
            - 0x001C: Component Identification
            - 0x0111: Module Identification for all modules

        The response uses the FingerprintApplicator which applies vulnerability
        overrides to include vulnerable firmware version strings.

        Args:
            flow: Flow context with source/destination devices
            state: Conversation state
            start_time_ms: Start timestamp
            szl_id: SZL ID to query (default 0x0011 for module identification)

        Yields:
            PacketEvent for SZL request and response
        """
        current_time = start_time_ms

        # Get sequence numbers
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]
        pdu_ref = state.custom_data["pdu_ref"]

        # Get fingerprinted TCP options
        client_tcp_opts = flow.source.fingerprint_applicator.get_tcp_options()
        server_tcp_opts = flow.destination.fingerprint_applicator.get_tcp_options()

        # Get response timing from CPU profile
        cpu_model = flow.config.get("cpu_model", "CPU 1214C")
        profile = get_cpu_profile(cpu_model)
        if profile:
            base_delay = random.uniform(*profile.response_delay_ms)
        else:
            base_delay = random.uniform(5.0, 20.0)

        # ============================================================
        # SZL Read Request (Module Identification)
        # ============================================================

        szl_request_payload = build_s7_szl_request(
            pdu_ref=pdu_ref,
            szl_id=szl_id,
            szl_index=0x0000,
        )

        szl_request_packet = _build_tcp_packet(
            flow.source,
            flow.destination,
            szl_request_payload,
            client_seq,
            server_seq,
            "PA",
            tcp_options=client_tcp_opts,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=szl_request_packet,
            direction="request",
            metadata={
                "type": "s7_szl_request",
                "szl_id": szl_id,
                "pdu_ref": pdu_ref,
            },
        )

        client_seq += len(szl_request_payload)
        state.custom_data["tcp_seq_client"] = client_seq
        current_time += base_delay

        # ============================================================
        # SZL Read Response (with vulnerable firmware from fingerprint)
        # ============================================================

        # Get the fingerprint applicator from the destination device
        # This includes vulnerability overrides if set
        applicator = flow.destination.fingerprint_applicator

        # Build SZL data using the identity builder system
        # This will include vulnerable firmware versions from CVE overrides
        response = applicator.get_identity_response("s7", szl_id=szl_id)
        szl_data = response.raw_bytes

        szl_response_payload = build_s7_szl_response(
            pdu_ref=pdu_ref,
            szl_id=szl_id,
            szl_index=0x0000,
            szl_data=szl_data,
        )

        szl_response_packet = _build_tcp_packet(
            flow.destination,
            flow.source,
            szl_response_payload,
            server_seq,
            client_seq,
            "PA",
            tcp_options=server_tcp_opts,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=szl_response_packet,
            direction="response",
            metadata={
                "type": "s7_szl_response",
                "szl_id": szl_id,
                "pdu_ref": pdu_ref,
                "has_vulnerability_override": applicator._vulnerability_override is not None,
                "firmware_version": applicator.s7_identity.get("firmware_version", ""),
                "order_code": applicator.s7_identity.get("order_code", ""),
            },
        )

        server_seq += len(szl_response_payload)
        state.custom_data["tcp_seq_server"] = server_seq
        state.custom_data["pdu_ref"] = pdu_ref + 1

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate S7 read/write poll cycle.

        A typical poll cycle consists of:
        - Read Variable Request / Response (for reading PLC data)
        - Optionally: Write Variable Request / Response (for writing data)

        Enhanced with learned patterns:
        - Response timing from PCAP analysis
        - Address patterns from real traffic
        """
        config = _parse_s7_config(flow.config)
        current_time = cycle_time_ms

        # Check for learned timing patterns
        learned_timing = flow.config.get("learned_timing")
        if learned_timing and "responseTimeMs" in learned_timing:
            # Use learned response time with some jitter
            base_delay = float(learned_timing["responseTimeMs"])
            jitter = learned_timing.get("jitterMs", 5.0)
            response_delay = base_delay + random.uniform(-jitter/2, jitter/2)
        else:
            # Get timing from CPU profile
            cpu_model = flow.config.get("cpu_model", "CPU 1214C")
            profile = get_cpu_profile(cpu_model)
            if profile:
                response_delay = random.uniform(*profile.response_delay_ms)
            else:
                response_delay = random.uniform(5.0, 20.0)

        # Check for learned address patterns
        address_patterns = flow.config.get("address_patterns")
        if address_patterns and isinstance(address_patterns, list) and config.read_areas:
            # Sample from learned patterns to vary read areas
            start_addr, size = sample_address_range(address_patterns)
            # Update first read area with sampled values
            if config.read_areas:
                config.read_areas[0].start = start_addr
                config.read_areas[0].size = min(size, 200)  # S7 typical limit

        # Get TCP state
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]
        pdu_ref = state.custom_data["pdu_ref"]

        # Get fingerprinted TCP options
        client_tcp_opts = flow.source.fingerprint_applicator.get_tcp_options()
        server_tcp_opts = flow.destination.fingerprint_applicator.get_tcp_options()

        # ============================================================
        # Read Variable Request / Response
        # ============================================================

        if config.read_areas:
            # Build read request
            s7_read_req_payload = build_s7_read_request(
                pdu_ref=pdu_ref,
                read_areas=config.read_areas,
            )
            s7_read_req_packet = _build_tcp_packet(
                flow.source,
                flow.destination,
                s7_read_req_payload,
                client_seq,
                server_seq,
                "PA",
                tcp_options=client_tcp_opts,
            )
            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=s7_read_req_packet,
                direction="request",
                metadata={"type": "s7_read_req", "pdu_ref": pdu_ref},
            )
            client_seq += len(s7_read_req_payload)
            state.custom_data["tcp_seq_client"] = client_seq
            current_time += response_delay

            # Build read response with simulated data
            response_items = []
            for read_area in config.read_areas:
                # Generate realistic data based on area type
                if flow.payload_generator:
                    # Use PayloadGenerator for correlated, trending values
                    data = bytearray()
                    num_floats = read_area.size // 4
                    remainder = read_area.size % 4
                    for j in range(num_floats):
                        try:
                            data.extend(
                                flow.payload_generator.get_value(
                                    f"s7_val_{j}", current_time
                                )
                            )
                        except KeyError:
                            data.extend(os.urandom(4))
                    if remainder:
                        data.extend(os.urandom(remainder))
                    data = bytes(data[: read_area.size])
                elif read_area.area == S7Area.DB:
                    # Data block - could be sensor values, setpoints, etc.
                    data = os.urandom(read_area.size)
                elif read_area.area == S7Area.INPUTS:
                    # Digital/analog inputs - typically changing values
                    data = os.urandom(read_area.size)
                elif read_area.area == S7Area.OUTPUTS:
                    # Output states
                    data = os.urandom(read_area.size)
                elif read_area.area == S7Area.MERKERS:
                    # Internal markers/flags
                    data = os.urandom(read_area.size)
                else:
                    data = os.urandom(read_area.size)

                response_items.append((S7DataReturnCode.SUCCESS, data))

            s7_read_resp_payload = build_s7_read_response(
                pdu_ref=pdu_ref,
                items=response_items,
            )
            s7_read_resp_packet = _build_tcp_packet(
                flow.destination,
                flow.source,
                s7_read_resp_payload,
                server_seq,
                client_seq,
                "PA",
                tcp_options=server_tcp_opts,
            )
            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=s7_read_resp_packet,
                direction="response",
                metadata={"type": "s7_read_resp", "pdu_ref": pdu_ref},
            )
            server_seq += len(s7_read_resp_payload)
            state.custom_data["tcp_seq_server"] = server_seq
            pdu_ref += 1
            current_time += random.uniform(1.0, 5.0)

        # ============================================================
        # Write Variable Request / Response (if not poll_read_only)
        # ============================================================

        if not config.poll_read_only and config.write_areas:
            # Build write request
            s7_write_req_payload = build_s7_write_request(
                pdu_ref=pdu_ref,
                write_areas=config.write_areas,
            )
            s7_write_req_packet = _build_tcp_packet(
                flow.source,
                flow.destination,
                s7_write_req_payload,
                client_seq,
                server_seq,
                "PA",
                tcp_options=client_tcp_opts,
            )
            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=s7_write_req_packet,
                direction="request",
                metadata={"type": "s7_write_req", "pdu_ref": pdu_ref},
            )
            client_seq += len(s7_write_req_payload)
            state.custom_data["tcp_seq_client"] = client_seq
            current_time += response_delay

            # Build write response
            return_codes = [S7DataReturnCode.SUCCESS] * len(config.write_areas)
            s7_write_resp_payload = build_s7_write_response(
                pdu_ref=pdu_ref,
                return_codes=return_codes,
            )
            s7_write_resp_packet = _build_tcp_packet(
                flow.destination,
                flow.source,
                s7_write_resp_payload,
                server_seq,
                client_seq,
                "PA",
                tcp_options=server_tcp_opts,
            )
            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=s7_write_resp_packet,
                direction="response",
                metadata={"type": "s7_write_resp", "pdu_ref": pdu_ref},
            )
            server_seq += len(s7_write_resp_payload)
            state.custom_data["tcp_seq_server"] = server_seq
            pdu_ref += 1

        # Update PDU reference
        state.custom_data["pdu_ref"] = pdu_ref

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate S7 shutdown sequence: COTP DR + TCP FIN.

        Clean disconnection sequence:
        1. COTP Disconnect Request (optional, often just TCP FIN)
        2. TCP FIN from client
        3. TCP FIN-ACK from server
        4. TCP ACK from client
        """
        current_time = start_time_ms

        # Get TCP state
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]

        # Get fingerprinted TCP options
        client_tcp_opts = flow.source.fingerprint_applicator.get_tcp_options()
        server_tcp_opts = flow.destination.fingerprint_applicator.get_tcp_options()

        # ============================================================
        # Option 1: Clean COTP Disconnect (some implementations)
        # ============================================================

        # COTP DR (Disconnect Request) - optional
        cotp_dr_payload = build_cotp_dr_packet(
            dst_ref=state.custom_data.get("cotp_dst_ref", 0),
            src_ref=state.custom_data.get("cotp_src_ref", 1),
        )
        cotp_dr_packet = _build_tcp_packet(
            flow.source,
            flow.destination,
            cotp_dr_payload,
            client_seq,
            server_seq,
            "PA",
            tcp_options=client_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=cotp_dr_packet,
            direction="request",
            metadata={"type": "cotp_dr", "phase": "disconnect"},
        )
        client_seq += len(cotp_dr_payload)
        current_time += random.uniform(1.0, 5.0)

        # ============================================================
        # TCP FIN sequence
        # ============================================================

        # FIN from client
        fin_packet = _build_tcp_fin(
            flow.source, flow.destination, client_seq, server_seq,
            tcp_options=client_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_packet,
            direction="request",
            metadata={"type": "tcp_fin", "phase": "disconnect"},
        )
        current_time += random.uniform(0.5, 2.0)

        # FIN-ACK from server
        fin_ack_packet = _build_tcp_fin(
            flow.destination, flow.source, server_seq, client_seq + 1,
            tcp_options=server_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_ack_packet,
            direction="response",
            metadata={"type": "tcp_fin_ack", "phase": "disconnect"},
        )
        current_time += random.uniform(0.1, 0.5)

        # Final ACK from client
        final_ack_packet = _build_tcp_ack(
            flow.source, flow.destination, client_seq + 1, server_seq + 1,
            tcp_options=client_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=final_ack_packet,
            direction="request",
            metadata={"type": "tcp_ack", "phase": "disconnect"},
        )

        # Update state
        state.state_name = "disconnected"

    def validate_config(self, config: dict) -> list[str]:
        """Validate S7-specific configuration.

        Args:
            config: Configuration dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate rack (0-7 for S7)
        rack = config.get("rack", 0)
        if not isinstance(rack, int) or rack < 0 or rack > 7:
            errors.append(f"Invalid rack number: {rack}. Must be 0-7.")

        # Validate slot (0-31)
        slot = config.get("slot", 1)
        if not isinstance(slot, int) or slot < 0 or slot > 31:
            errors.append(f"Invalid slot number: {slot}. Must be 0-31.")

        # Validate PDU size (240-960)
        pdu_size = config.get("pdu_size", 480)
        if not isinstance(pdu_size, int) or pdu_size < 240 or pdu_size > 960:
            errors.append(f"Invalid PDU size: {pdu_size}. Must be 240-960.")

        # Validate connection type
        conn_type = config.get("connection_type", S7ConnectionType.PG)
        if conn_type not in [1, 2, 3]:
            errors.append(
                f"Invalid connection type: {conn_type}. Must be 1 (PG), 2 (OP), or 3 (S7 Basic)."
            )

        # Validate read areas
        for i, area in enumerate(config.get("read_areas", [])):
            if not isinstance(area, dict):
                errors.append(f"Read area {i} must be a dictionary.")
                continue
            area_code = area.get("area", 0x84)
            if area_code not in [0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87]:
                errors.append(f"Invalid area code in read area {i}: {area_code}")

        return errors
