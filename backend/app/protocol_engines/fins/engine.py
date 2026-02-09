"""Omron FINS protocol engine implementation.

FINS (Factory Interface Network Service) is Omron's proprietary protocol
for PLC communication over Ethernet, Controller Link, and serial interfaces.

Supported transport modes:
- FINS/UDP (port 9600) - Most common, connectionless
- FINS/TCP (port 9600) - Connection-oriented with node address exchange

Supported PLCs:
- CJ/CS series (CJ1, CJ2, CS1)
- NJ/NX series (newer PLCs)
- CP series (compact PLCs)
- CV series (older series)

Features:
- Memory area read/write (CIO, WR, HR, AR, DM, EM)
- Controller data and status read
- Clock read/write
- Run/Stop mode control
- Error log access
"""

import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.fins.packets import (
    FINS_PORT,
    FINSCommand,
    FINSTcpCommand,
    MemoryArea,
    ResponseCode,
    build_clock_read_command,
    build_controller_data_read_command,
    build_controller_status_read_command,
    build_fins_header,
    build_fins_response,
    build_fins_response_header,
    build_fins_tcp_frame,
    build_fins_tcp_packet,
    build_fins_udp_packet,
    build_memory_read_command,
    build_memory_write_command,
    build_tcp_client_handshake,
    build_tcp_fin,
    build_tcp_handshake_ack,
    build_tcp_handshake_syn,
    build_tcp_handshake_syn_ack,
    build_tcp_server_handshake,
)
from app.protocol_engines.types import (
    FINSConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)


@register_engine(ProtocolType.FINS)
class FINSEngine(ProtocolEngine):
    """Omron FINS protocol engine.

    Generates realistic FINS traffic patterns including:
    - UDP and TCP transport modes
    - Memory area read/write operations
    - Controller data and status queries
    - PLC mode control (Run/Stop)
    """

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.FINS

    def create_initial_state(self, flow: FlowContext) -> FINSConversationState:
        """Create initial conversation state for FINS."""
        transport_mode = flow.config.get("transport_mode", "udp")

        # Derive node addresses from IP if not specified
        src_ip = flow.source.ip_address
        dst_ip = flow.destination.ip_address

        src_node = flow.config.get("src_node") or int(src_ip.split(".")[-1])
        dst_node = flow.config.get("dst_node") or int(dst_ip.split(".")[-1])

        return FINSConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            sid=random.randint(0, 255),
            src_node=src_node & 0xFF,
            dst_node=dst_node & 0xFF,
            transport_mode=transport_mode,
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: FINSConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate FINS startup sequence.

        For UDP: No startup needed (connectionless)
        For TCP: TCP handshake + FINS node address exchange
        """
        if state.transport_mode == "udp":
            # UDP is connectionless - no startup needed
            return

        # TCP mode - perform handshake and node address exchange
        current_time = start_time_ms

        # Initialize TCP state
        state.custom_data["tcp_seq_client"] = random.randint(1000, 9999)
        state.custom_data["tcp_seq_server"] = random.randint(1000, 9999)

        # Phase 1: TCP three-way handshake
        yield from self._generate_tcp_handshake(flow, state, current_time)
        current_time += 3.0  # 3ms for handshake

        # Phase 2: FINS node address exchange
        yield from self._generate_fins_node_exchange(flow, state, current_time)

        state.is_connected = True
        state.state_name = "connected"

    def _generate_tcp_handshake(
        self,
        flow: FlowContext,
        state: FINSConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate TCP three-way handshake."""
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]

        # SYN
        syn_packet = build_tcp_handshake_syn(flow.source, flow.destination, client_seq)
        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=syn_packet,
            direction="request",
            metadata={"type": "tcp_syn", "protocol": "fins"},
        )

        # SYN-ACK
        syn_ack_time = time_ms + random.uniform(1.0, 2.0)
        server_tcp_opts = flow.destination.fingerprint_applicator.get_tcp_options()
        syn_ack_packet = build_tcp_handshake_syn_ack(
            flow.destination, flow.source, server_seq, client_seq + 1,
            tcp_options=server_tcp_opts,
        )
        yield PacketEvent(
            timestamp_ms=syn_ack_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack_packet,
            direction="response",
            metadata={"type": "tcp_syn_ack", "protocol": "fins"},
        )

        # ACK
        ack_time = syn_ack_time + random.uniform(0.1, 0.5)
        ack_packet = build_tcp_handshake_ack(
            flow.source, flow.destination, client_seq + 1, server_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=ack_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"type": "tcp_ack", "protocol": "fins"},
        )

        # Update sequence numbers
        state.custom_data["tcp_seq_client"] = client_seq + 1
        state.custom_data["tcp_seq_server"] = server_seq + 1
        state.custom_data["tcp_ack_client"] = server_seq + 1
        state.custom_data["tcp_ack_server"] = client_seq + 1

    def _generate_fins_node_exchange(
        self,
        flow: FlowContext,
        state: FINSConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate FINS/TCP node address exchange."""
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]

        # Client sends node address request (0 = auto-assign)
        client_request = build_tcp_client_handshake(0x00)
        request_packet = build_fins_tcp_packet(
            flow.source,
            flow.destination,
            client_request,
            seq=client_seq,
            ack=server_seq,
        )

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "fins_tcp_node_request",
                "tcp_command": "CLIENT_NODE_ADDR_SEND",
            },
        )

        # Server responds with assigned addresses
        assigned_client = state.src_node
        server_node = state.dst_node

        server_response = build_tcp_server_handshake(assigned_client, server_node)
        response_time = time_ms + random.uniform(1.0, 3.0)

        client_seq_after = client_seq + len(client_request)
        response_packet = build_fins_tcp_packet(
            flow.destination,
            flow.source,
            server_response,
            seq=server_seq,
            ack=client_seq_after,
        )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "fins_tcp_node_response",
                "tcp_command": "SERVER_NODE_ADDR_SEND",
                "client_node": assigned_client,
                "server_node": server_node,
            },
        )

        # Record handshake results
        state.record_tcp_handshake(assigned_client, server_node)

        # Update TCP sequence numbers
        state.custom_data["tcp_seq_client"] = client_seq_after
        state.custom_data["tcp_seq_server"] = server_seq + len(server_response)

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: FINSConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate FINS poll cycle (memory read or other command)."""
        # Determine command type from config
        command_type = flow.config.get("command_type", "memory_read")

        if command_type == "memory_read":
            yield from self._generate_memory_read(flow, state, cycle_time_ms)
        elif command_type == "memory_write":
            yield from self._generate_memory_write(flow, state, cycle_time_ms)
        elif command_type == "controller_data":
            yield from self._generate_controller_data_read(flow, state, cycle_time_ms)
        elif command_type == "controller_status":
            yield from self._generate_controller_status_read(flow, state, cycle_time_ms)
        elif command_type == "clock_read":
            yield from self._generate_clock_read(flow, state, cycle_time_ms)
        else:
            # Default to memory read
            yield from self._generate_memory_read(flow, state, cycle_time_ms)

    def _generate_memory_read(
        self,
        flow: FlowContext,
        state: FINSConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Memory Area Read request/response."""
        # Get memory area configuration
        area_code = flow.config.get("area_code", MemoryArea.DM_WORD)
        start_address = flow.config.get("start_address", 0)
        num_items = flow.config.get("num_items", 10)

        # Build FINS header
        sid = state.next_sid()
        fins_header = build_fins_header(
            dst_node=state.dst_node,
            src_node=state.src_node,
            sid=sid,
        )

        # Build command
        command_data = build_memory_read_command(area_code, start_address, num_items)
        fins_frame = fins_header + command_data

        state.last_command = FINSCommand.MEMORY_AREA_READ

        # Build and send request
        if state.transport_mode == "udp":
            request_packet = build_fins_udp_packet(
                flow.source, flow.destination, fins_frame
            )
        else:
            tcp_frame = build_fins_tcp_frame(fins_frame)
            client_seq = state.custom_data.get("tcp_seq_client", 1000)
            server_seq = state.custom_data.get("tcp_seq_server", 1000)
            request_packet = build_fins_tcp_packet(
                flow.source, flow.destination, tcp_frame,
                seq=client_seq, ack=server_seq
            )
            state.custom_data["tcp_seq_client"] = client_seq + len(tcp_frame)

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "fins_memory_read_request",
                "command": hex(FINSCommand.MEMORY_AREA_READ),
                "area_code": hex(area_code),
                "address": start_address,
                "num_items": num_items,
                "sid": sid,
            },
        )

        # Build response
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = time_ms + timing_sample.delay_ms

        # Generate simulated data
        response_data = self._generate_memory_data(num_items)

        response_header = build_fins_response_header(
            dst_node=state.src_node,
            src_node=state.dst_node,
            sid=sid,
        )
        response_body = build_fins_response(
            FINSCommand.MEMORY_AREA_READ,
            ResponseCode.NORMAL,
            response_data,
        )
        response_frame = response_header + response_body

        if state.transport_mode == "udp":
            response_packet = build_fins_udp_packet(
                flow.destination, flow.source, response_frame
            )
        else:
            tcp_frame = build_fins_tcp_frame(response_frame)
            server_seq = state.custom_data.get("tcp_seq_server", 1000)
            client_seq = state.custom_data.get("tcp_seq_client", 1000)
            response_packet = build_fins_tcp_packet(
                flow.destination, flow.source, tcp_frame,
                seq=server_seq, ack=client_seq
            )
            state.custom_data["tcp_seq_server"] = server_seq + len(tcp_frame)

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "fins_memory_read_response",
                "command": hex(FINSCommand.MEMORY_AREA_READ),
                "response_code": hex(ResponseCode.NORMAL),
                "data_length": len(response_data),
                "response_delay_ms": timing_sample.delay_ms,
            },
        )

    def _generate_memory_write(
        self,
        flow: FlowContext,
        state: FINSConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Memory Area Write request/response."""
        area_code = flow.config.get("area_code", MemoryArea.DM_WORD)
        start_address = flow.config.get("start_address", 0)
        write_data = flow.config.get("write_data") or self._generate_memory_data(5)

        sid = state.next_sid()
        fins_header = build_fins_header(
            dst_node=state.dst_node,
            src_node=state.src_node,
            sid=sid,
        )

        command_data = build_memory_write_command(area_code, start_address, write_data)
        fins_frame = fins_header + command_data

        state.last_command = FINSCommand.MEMORY_AREA_WRITE

        if state.transport_mode == "udp":
            request_packet = build_fins_udp_packet(
                flow.source, flow.destination, fins_frame
            )
        else:
            tcp_frame = build_fins_tcp_frame(fins_frame)
            client_seq = state.custom_data.get("tcp_seq_client", 1000)
            server_seq = state.custom_data.get("tcp_seq_server", 1000)
            request_packet = build_fins_tcp_packet(
                flow.source, flow.destination, tcp_frame,
                seq=client_seq, ack=server_seq
            )
            state.custom_data["tcp_seq_client"] = client_seq + len(tcp_frame)

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "fins_memory_write_request",
                "command": hex(FINSCommand.MEMORY_AREA_WRITE),
                "area_code": hex(area_code),
                "address": start_address,
                "data_length": len(write_data),
                "sid": sid,
            },
        )

        # Write response (no data, just status)
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = time_ms + timing_sample.delay_ms

        response_header = build_fins_response_header(
            dst_node=state.src_node,
            src_node=state.dst_node,
            sid=sid,
        )
        response_body = build_fins_response(
            FINSCommand.MEMORY_AREA_WRITE,
            ResponseCode.NORMAL,
        )
        response_frame = response_header + response_body

        if state.transport_mode == "udp":
            response_packet = build_fins_udp_packet(
                flow.destination, flow.source, response_frame
            )
        else:
            tcp_frame = build_fins_tcp_frame(response_frame)
            server_seq = state.custom_data.get("tcp_seq_server", 1000)
            client_seq = state.custom_data.get("tcp_seq_client", 1000)
            response_packet = build_fins_tcp_packet(
                flow.destination, flow.source, tcp_frame,
                seq=server_seq, ack=client_seq
            )
            state.custom_data["tcp_seq_server"] = server_seq + len(tcp_frame)

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "fins_memory_write_response",
                "command": hex(FINSCommand.MEMORY_AREA_WRITE),
                "response_code": hex(ResponseCode.NORMAL),
            },
        )

    def _generate_controller_data_read(
        self,
        flow: FlowContext,
        state: FINSConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Controller Data Read request/response."""
        sid = state.next_sid()
        fins_header = build_fins_header(
            dst_node=state.dst_node,
            src_node=state.src_node,
            sid=sid,
        )

        command_data = build_controller_data_read_command()
        fins_frame = fins_header + command_data

        state.last_command = FINSCommand.CONTROLLER_DATA_READ

        if state.transport_mode == "udp":
            request_packet = build_fins_udp_packet(
                flow.source, flow.destination, fins_frame
            )
        else:
            tcp_frame = build_fins_tcp_frame(fins_frame)
            client_seq = state.custom_data.get("tcp_seq_client", 1000)
            server_seq = state.custom_data.get("tcp_seq_server", 1000)
            request_packet = build_fins_tcp_packet(
                flow.source, flow.destination, tcp_frame,
                seq=client_seq, ack=server_seq
            )
            state.custom_data["tcp_seq_client"] = client_seq + len(tcp_frame)

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "fins_controller_data_request",
                "command": hex(FINSCommand.CONTROLLER_DATA_READ),
                "sid": sid,
            },
        )

        # Build controller data response
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = time_ms + timing_sample.delay_ms

        # Simulated controller data
        controller_data = self._build_controller_data(flow)

        response_header = build_fins_response_header(
            dst_node=state.src_node,
            src_node=state.dst_node,
            sid=sid,
        )
        response_body = build_fins_response(
            FINSCommand.CONTROLLER_DATA_READ,
            ResponseCode.NORMAL,
            controller_data,
        )
        response_frame = response_header + response_body

        if state.transport_mode == "udp":
            response_packet = build_fins_udp_packet(
                flow.destination, flow.source, response_frame
            )
        else:
            tcp_frame = build_fins_tcp_frame(response_frame)
            server_seq = state.custom_data.get("tcp_seq_server", 1000)
            client_seq = state.custom_data.get("tcp_seq_client", 1000)
            response_packet = build_fins_tcp_packet(
                flow.destination, flow.source, tcp_frame,
                seq=server_seq, ack=client_seq
            )
            state.custom_data["tcp_seq_server"] = server_seq + len(tcp_frame)

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "fins_controller_data_response",
                "command": hex(FINSCommand.CONTROLLER_DATA_READ),
                "response_code": hex(ResponseCode.NORMAL),
            },
        )

    def _generate_controller_status_read(
        self,
        flow: FlowContext,
        state: FINSConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Controller Status Read request/response."""
        sid = state.next_sid()
        fins_header = build_fins_header(
            dst_node=state.dst_node,
            src_node=state.src_node,
            sid=sid,
        )

        command_data = build_controller_status_read_command()
        fins_frame = fins_header + command_data

        state.last_command = FINSCommand.CONTROLLER_STATUS_READ

        if state.transport_mode == "udp":
            request_packet = build_fins_udp_packet(
                flow.source, flow.destination, fins_frame
            )
        else:
            tcp_frame = build_fins_tcp_frame(fins_frame)
            client_seq = state.custom_data.get("tcp_seq_client", 1000)
            server_seq = state.custom_data.get("tcp_seq_server", 1000)
            request_packet = build_fins_tcp_packet(
                flow.source, flow.destination, tcp_frame,
                seq=client_seq, ack=server_seq
            )
            state.custom_data["tcp_seq_client"] = client_seq + len(tcp_frame)

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "fins_controller_status_request",
                "command": hex(FINSCommand.CONTROLLER_STATUS_READ),
                "sid": sid,
            },
        )

        # Build status response
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = time_ms + timing_sample.delay_ms

        # Simulated status data: RUN mode, no errors
        status_data = bytes([
            0x01,  # Status: RUN mode
            0x00,  # Mode: Normal
            0x00, 0x00,  # Fatal error: None
            0x00, 0x00,  # Non-fatal error: None
            0x00, 0x00,  # Error message
        ])

        response_header = build_fins_response_header(
            dst_node=state.src_node,
            src_node=state.dst_node,
            sid=sid,
        )
        response_body = build_fins_response(
            FINSCommand.CONTROLLER_STATUS_READ,
            ResponseCode.NORMAL,
            status_data,
        )
        response_frame = response_header + response_body

        if state.transport_mode == "udp":
            response_packet = build_fins_udp_packet(
                flow.destination, flow.source, response_frame
            )
        else:
            tcp_frame = build_fins_tcp_frame(response_frame)
            server_seq = state.custom_data.get("tcp_seq_server", 1000)
            client_seq = state.custom_data.get("tcp_seq_client", 1000)
            response_packet = build_fins_tcp_packet(
                flow.destination, flow.source, tcp_frame,
                seq=server_seq, ack=client_seq
            )
            state.custom_data["tcp_seq_server"] = server_seq + len(tcp_frame)

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "fins_controller_status_response",
                "command": hex(FINSCommand.CONTROLLER_STATUS_READ),
                "response_code": hex(ResponseCode.NORMAL),
                "plc_mode": "RUN",
            },
        )

    def _generate_clock_read(
        self,
        flow: FlowContext,
        state: FINSConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Clock Read request/response."""
        sid = state.next_sid()
        fins_header = build_fins_header(
            dst_node=state.dst_node,
            src_node=state.src_node,
            sid=sid,
        )

        command_data = build_clock_read_command()
        fins_frame = fins_header + command_data

        state.last_command = FINSCommand.CLOCK_READ

        if state.transport_mode == "udp":
            request_packet = build_fins_udp_packet(
                flow.source, flow.destination, fins_frame
            )
        else:
            tcp_frame = build_fins_tcp_frame(fins_frame)
            client_seq = state.custom_data.get("tcp_seq_client", 1000)
            server_seq = state.custom_data.get("tcp_seq_server", 1000)
            request_packet = build_fins_tcp_packet(
                flow.source, flow.destination, tcp_frame,
                seq=client_seq, ack=server_seq
            )
            state.custom_data["tcp_seq_client"] = client_seq + len(tcp_frame)

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "fins_clock_read_request",
                "command": hex(FINSCommand.CLOCK_READ),
                "sid": sid,
            },
        )

        # Build clock response
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = time_ms + timing_sample.delay_ms

        # Simulated clock data (BCD format)
        # Year (2 bytes), Month, Day, Hour, Minute, Second, Day of week
        import datetime
        now = datetime.datetime.now()
        clock_data = bytes([
            (now.year // 100),  # Century
            (now.year % 100),   # Year
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second,
            now.weekday(),  # Day of week
        ])

        response_header = build_fins_response_header(
            dst_node=state.src_node,
            src_node=state.dst_node,
            sid=sid,
        )
        response_body = build_fins_response(
            FINSCommand.CLOCK_READ,
            ResponseCode.NORMAL,
            clock_data,
        )
        response_frame = response_header + response_body

        if state.transport_mode == "udp":
            response_packet = build_fins_udp_packet(
                flow.destination, flow.source, response_frame
            )
        else:
            tcp_frame = build_fins_tcp_frame(response_frame)
            server_seq = state.custom_data.get("tcp_seq_server", 1000)
            client_seq = state.custom_data.get("tcp_seq_client", 1000)
            response_packet = build_fins_tcp_packet(
                flow.destination, flow.source, tcp_frame,
                seq=server_seq, ack=client_seq
            )
            state.custom_data["tcp_seq_server"] = server_seq + len(tcp_frame)

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "fins_clock_read_response",
                "command": hex(FINSCommand.CLOCK_READ),
                "response_code": hex(ResponseCode.NORMAL),
            },
        )

    def _generate_memory_data(self, num_words: int) -> bytes:
        """Generate simulated memory data."""
        data = bytearray()
        for i in range(num_words):
            # Generate varying word values
            value = (i * 100 + random.randint(0, 99)) & 0xFFFF
            data.extend(value.to_bytes(2, "big"))  # FINS uses big-endian for data
        return bytes(data)

    def _build_controller_data(self, flow: FlowContext) -> bytes:
        """Build simulated controller data response."""
        # Model info from fingerprint or defaults
        model = flow.destination.model or "CJ2M-CPU31"
        version = flow.destination.firmware_version or "2.0"

        # Build controller data structure
        # This is a simplified version of the actual response
        data = bytearray()

        # Controller model (20 bytes, ASCII)
        model_bytes = model.encode("ascii")[:20].ljust(20, b"\x00")
        data.extend(model_bytes)

        # Controller version (20 bytes, ASCII)
        version_bytes = version.encode("ascii")[:20].ljust(20, b"\x00")
        data.extend(version_bytes)

        # System version (40 bytes)
        data.extend(b"\x00" * 40)

        # Area data (memory sizes)
        # DM size (2 bytes)
        data.extend((32768).to_bytes(2, "big"))
        # EM banks (1 byte)
        data.extend(bytes([3]))

        return bytes(data)

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: FINSConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate FINS shutdown sequence.

        For UDP: No shutdown needed
        For TCP: TCP FIN handshake
        """
        if state.transport_mode == "udp":
            return

        client_seq = state.custom_data.get("tcp_seq_client", 1000)
        server_seq = state.custom_data.get("tcp_seq_server", 1000)

        # FIN from client
        fin_packet = build_tcp_fin(
            flow.source, flow.destination, client_seq, server_seq
        )
        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=fin_packet,
            direction="request",
            metadata={"type": "tcp_fin", "protocol": "fins"},
        )

        # FIN-ACK from server
        fin_ack_time = start_time_ms + random.uniform(1.0, 2.0)
        fin_ack_packet = build_tcp_fin(
            flow.destination, flow.source, server_seq, client_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=fin_ack_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_ack_packet,
            direction="response",
            metadata={"type": "tcp_fin_ack", "protocol": "fins"},
        )

        # Final ACK
        ack_time = fin_ack_time + random.uniform(0.1, 0.5)
        ack_packet = build_tcp_handshake_ack(
            flow.source, flow.destination, client_seq + 1, server_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=ack_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"type": "tcp_ack", "protocol": "fins"},
        )

        state.is_connected = False
        state.state_name = "disconnected"

    def validate_config(self, config: dict) -> list[str]:
        """Validate FINS configuration."""
        errors = []

        # Validate transport mode
        transport_mode = config.get("transport_mode", "udp")
        if transport_mode not in ("udp", "tcp"):
            errors.append(f"Invalid transport_mode: {transport_mode}")

        # Validate node addresses
        src_node = config.get("src_node")
        if src_node is not None and (src_node < 1 or src_node > 254):
            errors.append("src_node must be between 1 and 254")

        dst_node = config.get("dst_node")
        if dst_node is not None and (dst_node < 1 or dst_node > 254):
            errors.append("dst_node must be between 1 and 254")

        # Validate memory area code
        area_code = config.get("area_code")
        valid_areas = [0xB0, 0xB1, 0xB2, 0xB3, 0x82, 0x98, 0xA0, 0x30, 0x31, 0x32, 0x33, 0x02]
        if area_code is not None and area_code not in valid_areas:
            errors.append(f"Invalid area_code: {hex(area_code)}")

        # Validate num_items
        num_items = config.get("num_items", 10)
        if num_items < 1 or num_items > 999:
            errors.append("num_items must be between 1 and 999")

        return errors
