# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Mitsubishi SLMP/MC Protocol engine implementation.

SLMP (Seamless Message Protocol) is Mitsubishi's standardized protocol
for MELSEC PLCs communication over Ethernet.

Supported PLCs:
- MELSEC Q series
- MELSEC iQ-R series
- MELSEC iQ-F series
- MELSEC L series

Frame types:
- 3E Frame: Standard format (most common)
- 4E Frame: Extended format with serial number for matching

Default port: TCP 5000

Features:
- Device batch read/write (D, M, X, Y, W, B, R, etc.)
- Remote Run/Stop control
- CPU model and status read
"""

import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.slmp.packets import (
    DeviceCode,
    ResponseCode,
    SLMPCommand,
    build_3e_response_header,
    build_4e_response_header,
    build_batch_read_command,
    build_batch_write_command,
    build_read_cpu_model_command,
    build_read_cpu_state_command,
    build_remote_run_command,
    build_remote_stop_command,
    build_slmp_3e_frame,
    build_slmp_4e_frame,
    build_slmp_tcp_packet,
    build_tcp_fin,
    build_tcp_handshake_ack,
    build_tcp_handshake_syn,
    build_tcp_handshake_syn_ack,
)
from app.protocol_engines.types import (
    FlowContext,
    PacketEvent,
    ProtocolType,
    SLMPConversationState,
)


@register_engine(ProtocolType.SLMP)
class SLMPEngine(ProtocolEngine):
    """Mitsubishi SLMP/MC Protocol engine.

    Generates realistic SLMP traffic patterns including:
    - TCP connection establishment
    - Device batch read/write operations
    - Remote PLC control (Run/Stop)
    - CPU information queries
    """

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.SLMP

    def create_initial_state(self, flow: FlowContext) -> SLMPConversationState:
        """Create initial conversation state for SLMP."""
        frame_type = flow.config.get("frame_type", "3e")

        return SLMPConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            serial_number=random.randint(0, 65535),
            network_number=flow.config.get("network_number", 0x00),
            pc_number=flow.config.get("pc_number", 0xFF),
            dest_module_io=flow.config.get("dest_module_io", 0x03FF),
            dest_module_station=flow.config.get("dest_module_station", 0x00),
            frame_type=frame_type,
            tcp_seq_client=random.randint(1000, 9999),
            tcp_seq_server=random.randint(1000, 9999),
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: SLMPConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate SLMP startup sequence (TCP handshake)."""
        current_time = start_time_ms

        # TCP three-way handshake
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # SYN
        syn_packet = build_tcp_handshake_syn(flow.source, flow.destination, client_seq)
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_packet,
            direction="request",
            metadata={"type": "tcp_syn", "protocol": "slmp"},
        )

        # SYN-ACK
        syn_ack_time = current_time + random.uniform(1.0, 2.0)
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
            metadata={"type": "tcp_syn_ack", "protocol": "slmp"},
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
            metadata={"type": "tcp_ack", "protocol": "slmp"},
        )

        # Update state
        state.tcp_seq_client = client_seq + 1
        state.tcp_seq_server = server_seq + 1
        state.tcp_ack_client = server_seq + 1
        state.tcp_ack_server = client_seq + 1
        state.is_connected = True
        state.state_name = "connected"

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: SLMPConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate SLMP poll cycle (device read or other command)."""
        command_type = flow.config.get("command_type", "batch_read")

        if command_type == "batch_read":
            yield from self._generate_batch_read(flow, state, cycle_time_ms)
        elif command_type == "batch_write":
            yield from self._generate_batch_write(flow, state, cycle_time_ms)
        elif command_type == "cpu_model":
            yield from self._generate_cpu_model_read(flow, state, cycle_time_ms)
        elif command_type == "cpu_state":
            yield from self._generate_cpu_state_read(flow, state, cycle_time_ms)
        elif command_type == "remote_run":
            yield from self._generate_remote_run(flow, state, cycle_time_ms)
        elif command_type == "remote_stop":
            yield from self._generate_remote_stop(flow, state, cycle_time_ms)
        else:
            yield from self._generate_batch_read(flow, state, cycle_time_ms)

    def _generate_batch_read(
        self,
        flow: FlowContext,
        state: SLMPConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Batch Read request/response."""
        # Get device configuration
        device_code = flow.config.get("device_code", DeviceCode.D)
        start_address = flow.config.get("start_address", 0)
        num_points = flow.config.get("num_points", 10)
        bit_access = flow.config.get("bit_access", False)

        # Build command
        command_data = build_batch_read_command(
            device_code, start_address, num_points, bit_access
        )

        # Build frame based on type
        if state.frame_type == "4e":
            serial = state.next_serial()
            slmp_frame = build_slmp_4e_frame(
                command_data,
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
                dest_module_io=state.dest_module_io,
                dest_module_station=state.dest_module_station,
            )
        else:
            serial = None
            slmp_frame = build_slmp_3e_frame(
                command_data,
                network_number=state.network_number,
                pc_number=state.pc_number,
                dest_module_io=state.dest_module_io,
                dest_module_station=state.dest_module_station,
            )

        state.last_command = SLMPCommand.BATCH_READ

        # Build and send request
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        request_packet = build_slmp_tcp_packet(
            flow.source, flow.destination, slmp_frame,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "slmp_batch_read_request",
                "frame_type": state.frame_type,
                "command": hex(SLMPCommand.BATCH_READ),
                "device_code": hex(device_code),
                "start_address": start_address,
                "num_points": num_points,
                "serial": serial,
            },
        )

        # Build response
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = time_ms + timing_sample.delay_ms

        # Generate simulated data
        if bit_access:
            response_data = bytes([random.randint(0, 1) for _ in range(num_points)])
        else:
            response_data = self._generate_word_data(num_points)

        # Build response frame
        if state.frame_type == "4e":
            response_header = build_4e_response_header(
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
                dest_module_io=state.dest_module_io,
                dest_module_station=state.dest_module_station,
                data_length=2 + len(response_data),  # end_code + data
                end_code=ResponseCode.NORMAL,
            )
        else:
            response_header = build_3e_response_header(
                network_number=state.network_number,
                pc_number=state.pc_number,
                dest_module_io=state.dest_module_io,
                dest_module_station=state.dest_module_station,
                data_length=2 + len(response_data),
                end_code=ResponseCode.NORMAL,
            )

        response_frame = response_header + response_data

        client_seq_after = client_seq + len(slmp_frame)
        response_packet = build_slmp_tcp_packet(
            flow.destination, flow.source, response_frame,
            seq=server_seq, ack=client_seq_after
        )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "slmp_batch_read_response",
                "frame_type": state.frame_type,
                "end_code": hex(ResponseCode.NORMAL),
                "data_length": len(response_data),
                "response_delay_ms": timing_sample.delay_ms,
            },
        )

        # Update TCP state
        state.tcp_seq_client = client_seq_after
        state.tcp_seq_server = server_seq + len(response_frame)

    def _generate_batch_write(
        self,
        flow: FlowContext,
        state: SLMPConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Batch Write request/response."""
        device_code = flow.config.get("device_code", DeviceCode.D)
        start_address = flow.config.get("start_address", 0)
        bit_access = flow.config.get("bit_access", False)

        # Get write data or generate
        write_data = flow.config.get("write_data")
        if write_data is None:
            num_points = flow.config.get("num_points", 5)
            if bit_access:
                write_data = bytes([random.randint(0, 1) for _ in range(num_points)])
            else:
                write_data = self._generate_word_data(num_points)

        command_data = build_batch_write_command(
            device_code, start_address, write_data, bit_access
        )

        if state.frame_type == "4e":
            serial = state.next_serial()
            slmp_frame = build_slmp_4e_frame(
                command_data,
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
            )
        else:
            serial = None
            slmp_frame = build_slmp_3e_frame(
                command_data,
                network_number=state.network_number,
                pc_number=state.pc_number,
            )

        state.last_command = SLMPCommand.BATCH_WRITE

        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        request_packet = build_slmp_tcp_packet(
            flow.source, flow.destination, slmp_frame,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "slmp_batch_write_request",
                "frame_type": state.frame_type,
                "command": hex(SLMPCommand.BATCH_WRITE),
                "device_code": hex(device_code),
                "start_address": start_address,
                "data_length": len(write_data),
            },
        )

        # Write response (no data, just status)
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = time_ms + timing_sample.delay_ms

        if state.frame_type == "4e":
            response_header = build_4e_response_header(
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
                data_length=2,  # Just end code
                end_code=ResponseCode.NORMAL,
            )
        else:
            response_header = build_3e_response_header(
                network_number=state.network_number,
                pc_number=state.pc_number,
                data_length=2,
                end_code=ResponseCode.NORMAL,
            )

        response_frame = response_header

        client_seq_after = client_seq + len(slmp_frame)
        response_packet = build_slmp_tcp_packet(
            flow.destination, flow.source, response_frame,
            seq=server_seq, ack=client_seq_after
        )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "slmp_batch_write_response",
                "frame_type": state.frame_type,
                "end_code": hex(ResponseCode.NORMAL),
            },
        )

        state.tcp_seq_client = client_seq_after
        state.tcp_seq_server = server_seq + len(response_frame)

    def _generate_cpu_model_read(
        self,
        flow: FlowContext,
        state: SLMPConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate CPU Model Read request/response."""
        command_data = build_read_cpu_model_command()

        if state.frame_type == "4e":
            serial = state.next_serial()
            slmp_frame = build_slmp_4e_frame(
                command_data,
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
            )
        else:
            serial = None
            slmp_frame = build_slmp_3e_frame(
                command_data,
                network_number=state.network_number,
                pc_number=state.pc_number,
            )

        state.last_command = SLMPCommand.READ_CPU_MODEL

        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        request_packet = build_slmp_tcp_packet(
            flow.source, flow.destination, slmp_frame,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "slmp_cpu_model_request",
                "frame_type": state.frame_type,
                "command": hex(SLMPCommand.READ_CPU_MODEL),
            },
        )

        # Build response with CPU model info
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = time_ms + timing_sample.delay_ms

        # CPU model name (16 characters)
        model = flow.destination.model or "Q06UDVCPU"
        model_bytes = model.encode("ascii")[:16].ljust(16, b" ")

        if state.frame_type == "4e":
            response_header = build_4e_response_header(
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
                data_length=2 + len(model_bytes),
                end_code=ResponseCode.NORMAL,
            )
        else:
            response_header = build_3e_response_header(
                network_number=state.network_number,
                pc_number=state.pc_number,
                data_length=2 + len(model_bytes),
                end_code=ResponseCode.NORMAL,
            )

        response_frame = response_header + model_bytes

        client_seq_after = client_seq + len(slmp_frame)
        response_packet = build_slmp_tcp_packet(
            flow.destination, flow.source, response_frame,
            seq=server_seq, ack=client_seq_after
        )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "slmp_cpu_model_response",
                "frame_type": state.frame_type,
                "cpu_model": model,
                "end_code": hex(ResponseCode.NORMAL),
            },
        )

        state.tcp_seq_client = client_seq_after
        state.tcp_seq_server = server_seq + len(response_frame)

    def _generate_cpu_state_read(
        self,
        flow: FlowContext,
        state: SLMPConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate CPU State Read request/response."""
        command_data = build_read_cpu_state_command()

        if state.frame_type == "4e":
            serial = state.next_serial()
            slmp_frame = build_slmp_4e_frame(
                command_data,
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
            )
        else:
            serial = None
            slmp_frame = build_slmp_3e_frame(
                command_data,
                network_number=state.network_number,
                pc_number=state.pc_number,
            )

        state.last_command = SLMPCommand.READ_CPU_STATE

        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        request_packet = build_slmp_tcp_packet(
            flow.source, flow.destination, slmp_frame,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "slmp_cpu_state_request",
                "frame_type": state.frame_type,
                "command": hex(SLMPCommand.READ_CPU_STATE),
            },
        )

        # Build response
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = time_ms + timing_sample.delay_ms

        # CPU state: RUN
        state_data = bytes([0x01])  # 0x01 = RUN, 0x00 = STOP

        if state.frame_type == "4e":
            response_header = build_4e_response_header(
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
                data_length=2 + len(state_data),
                end_code=ResponseCode.NORMAL,
            )
        else:
            response_header = build_3e_response_header(
                network_number=state.network_number,
                pc_number=state.pc_number,
                data_length=2 + len(state_data),
                end_code=ResponseCode.NORMAL,
            )

        response_frame = response_header + state_data

        client_seq_after = client_seq + len(slmp_frame)
        response_packet = build_slmp_tcp_packet(
            flow.destination, flow.source, response_frame,
            seq=server_seq, ack=client_seq_after
        )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "slmp_cpu_state_response",
                "frame_type": state.frame_type,
                "cpu_state": "RUN",
                "end_code": hex(ResponseCode.NORMAL),
            },
        )

        state.tcp_seq_client = client_seq_after
        state.tcp_seq_server = server_seq + len(response_frame)

    def _generate_remote_run(
        self,
        flow: FlowContext,
        state: SLMPConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Remote Run command."""
        forced = flow.config.get("forced_run", False)
        command_data = build_remote_run_command(forced=forced)

        if state.frame_type == "4e":
            serial = state.next_serial()
            slmp_frame = build_slmp_4e_frame(
                command_data,
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
            )
        else:
            serial = None
            slmp_frame = build_slmp_3e_frame(
                command_data,
                network_number=state.network_number,
                pc_number=state.pc_number,
            )

        state.last_command = SLMPCommand.REMOTE_RUN

        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        request_packet = build_slmp_tcp_packet(
            flow.source, flow.destination, slmp_frame,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "slmp_remote_run_request",
                "frame_type": state.frame_type,
                "command": hex(SLMPCommand.REMOTE_RUN),
                "forced": forced,
            },
        )

        # Response
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = time_ms + timing_sample.delay_ms

        if state.frame_type == "4e":
            response_header = build_4e_response_header(
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
                data_length=2,
                end_code=ResponseCode.NORMAL,
            )
        else:
            response_header = build_3e_response_header(
                network_number=state.network_number,
                pc_number=state.pc_number,
                data_length=2,
                end_code=ResponseCode.NORMAL,
            )

        response_frame = response_header

        client_seq_after = client_seq + len(slmp_frame)
        response_packet = build_slmp_tcp_packet(
            flow.destination, flow.source, response_frame,
            seq=server_seq, ack=client_seq_after
        )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "slmp_remote_run_response",
                "frame_type": state.frame_type,
                "end_code": hex(ResponseCode.NORMAL),
            },
        )

        state.tcp_seq_client = client_seq_after
        state.tcp_seq_server = server_seq + len(response_frame)

    def _generate_remote_stop(
        self,
        flow: FlowContext,
        state: SLMPConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Remote Stop command."""
        command_data = build_remote_stop_command()

        if state.frame_type == "4e":
            serial = state.next_serial()
            slmp_frame = build_slmp_4e_frame(
                command_data,
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
            )
        else:
            serial = None
            slmp_frame = build_slmp_3e_frame(
                command_data,
                network_number=state.network_number,
                pc_number=state.pc_number,
            )

        state.last_command = SLMPCommand.REMOTE_STOP

        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        request_packet = build_slmp_tcp_packet(
            flow.source, flow.destination, slmp_frame,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=request_packet,
            direction="request",
            metadata={
                "type": "slmp_remote_stop_request",
                "frame_type": state.frame_type,
                "command": hex(SLMPCommand.REMOTE_STOP),
            },
        )

        # Response
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = time_ms + timing_sample.delay_ms

        if state.frame_type == "4e":
            response_header = build_4e_response_header(
                serial_number=serial,
                network_number=state.network_number,
                pc_number=state.pc_number,
                data_length=2,
                end_code=ResponseCode.NORMAL,
            )
        else:
            response_header = build_3e_response_header(
                network_number=state.network_number,
                pc_number=state.pc_number,
                data_length=2,
                end_code=ResponseCode.NORMAL,
            )

        response_frame = response_header

        client_seq_after = client_seq + len(slmp_frame)
        response_packet = build_slmp_tcp_packet(
            flow.destination, flow.source, response_frame,
            seq=server_seq, ack=client_seq_after
        )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "slmp_remote_stop_response",
                "frame_type": state.frame_type,
                "end_code": hex(ResponseCode.NORMAL),
            },
        )

        state.tcp_seq_client = client_seq_after
        state.tcp_seq_server = server_seq + len(response_frame)

    def _generate_word_data(self, num_words: int) -> bytes:
        """Generate simulated word data."""
        data = bytearray()
        for i in range(num_words):
            value = (i * 100 + random.randint(0, 99)) & 0xFFFF
            data.extend(value.to_bytes(2, "little"))
        return bytes(data)

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: SLMPConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate SLMP shutdown sequence (TCP FIN handshake)."""
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # FIN from client
        fin_packet = build_tcp_fin(
            flow.source, flow.destination, client_seq, server_seq
        )
        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=fin_packet,
            direction="request",
            metadata={"type": "tcp_fin", "protocol": "slmp"},
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
            metadata={"type": "tcp_fin_ack", "protocol": "slmp"},
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
            metadata={"type": "tcp_ack", "protocol": "slmp"},
        )

        state.is_connected = False
        state.state_name = "disconnected"

    def validate_config(self, config: dict) -> list[str]:
        """Validate SLMP configuration."""
        errors = []

        # Validate frame type
        frame_type = config.get("frame_type", "3e")
        if frame_type not in ("3e", "4e"):
            errors.append(f"Invalid frame_type: {frame_type}")

        # Validate network number
        network_number = config.get("network_number", 0x00)
        if network_number < 0 or network_number > 0xEF:
            errors.append("network_number must be between 0x00 and 0xEF")

        # Validate PC number
        pc_number = config.get("pc_number", 0xFF)
        if pc_number != 0xFF and (pc_number < 0x01 or pc_number > 0x78):
            errors.append("pc_number must be 0xFF or between 0x01 and 0x78")

        # Validate device code
        device_code = config.get("device_code")
        valid_codes = [
            DeviceCode.D, DeviceCode.M, DeviceCode.X, DeviceCode.Y,
            DeviceCode.W, DeviceCode.B, DeviceCode.R, DeviceCode.SM,
            DeviceCode.SD, DeviceCode.L, DeviceCode.F, DeviceCode.V,
        ]
        if device_code is not None and device_code not in valid_codes:
            errors.append(f"Invalid device_code: {hex(device_code)}")

        # Validate num_points
        num_points = config.get("num_points", 10)
        if num_points < 1 or num_points > 960:
            errors.append("num_points must be between 1 and 960")

        return errors
