# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Codesys protocol engine implementation.

Supports Codesys runtime used by 500+ PLC vendors including:
- WAGO (750/760 series)
- Beckhoff (TwinCAT compatible)
- Festo (CECC series)
- Schneider Electric (SoMachine, M241/M251)
- ABB (AC500 series)
- IFM, EPEC, Kontron, Eaton, and many more

Protocol versions:
- V3 (modern): TCP port 11740, block driver framing
- V2 (legacy): TCP port 1200, simplified protocol
"""

import random
import struct
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.codesys.packets import (
    build_device_info_request,
    build_device_info_response,
    build_device_status_request,
    build_device_status_response,
    build_variable_read_request,
    build_variable_read_response,
    build_variable_write_request,
    build_variable_write_response,
    build_variable_read_multiple_request,
    build_variable_read_multiple_response,
    build_app_info_request,
    build_app_info_response,
    build_v2_get_info_request,
    build_v2_get_info_response,
    build_tcp_packet,
    build_tcp_syn,
    build_tcp_syn_ack,
    build_tcp_ack,
    build_tcp_fin,
)
from app.protocol_engines.codesys.types import (
    CODESYS_V3_PORT,
    CODESYS_V2_PORT,
    CodesysVersion,
    CodesysDataType,
    CodesysDeviceIdentity,
    CodesysVendor,
    CODESYS_VENDOR_NAMES,
    CODESYS_DEVICE_MODELS,
    PLCState,
)
from app.protocol_engines.types import (
    FlowContext,
    PacketEvent,
    CodesysConversationState,
    ProtocolType,
)


@register_engine(ProtocolType.CODESYS)
class CodesysEngine(ProtocolEngine):
    """Codesys protocol engine."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.CODESYS

    def create_initial_state(self, flow: FlowContext) -> CodesysConversationState:
        """Create initial conversation state."""
        state = CodesysConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            tcp_seq_client=random.randint(1000, 9999),
            tcp_seq_server=random.randint(1000, 9999),
            session_id=random.randint(1, 0xFFFFFFFF),
            invoke_id=random.randint(1, 65535),
        )
        return state

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: CodesysConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate startup sequence.

        Includes:
        - TCP three-way handshake
        - Device info query (optional)
        """
        version = flow.config.get("version", CodesysVersion.V3)
        if isinstance(version, str):
            version = CodesysVersion(version)

        # Determine port
        dst_port = CODESYS_V3_PORT if version == CodesysVersion.V3 else CODESYS_V2_PORT
        src_port = flow.source.port or random.randint(49152, 65535)

        # Store in state
        state.custom_data["src_port"] = src_port
        state.custom_data["dst_port"] = dst_port
        state.custom_data["version"] = version.value

        # TCP handshake
        yield from self._generate_tcp_handshake(flow, state, start_time_ms, src_port, dst_port)

        state.is_connected = True
        state.state_name = "connected"

        # Optional: Device info query during startup
        if flow.config.get("query_device_info", True):
            info_time = start_time_ms + 10
            yield from self._generate_device_info_cycle(flow, state, info_time, version)

    def _generate_tcp_handshake(
        self,
        flow: FlowContext,
        state: CodesysConversationState,
        start_time_ms: float,
        src_port: int,
        dst_port: int,
    ) -> Iterator[PacketEvent]:
        """Generate TCP three-way handshake."""
        client_seq = state.tcp_seq_client
        server_seq = state.tcp_seq_server

        # SYN
        syn_packet = build_tcp_syn(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=dst_port,
            seq=client_seq,
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
        syn_ack_packet = build_tcp_syn_ack(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=dst_port,
            dst_port=src_port,
            seq=server_seq,
            ack=client_seq + 1,
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
        ack_packet = build_tcp_ack(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=dst_port,
            seq=client_seq + 1,
            ack=server_seq + 1,
        )
        yield PacketEvent(
            timestamp_ms=ack_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"type": "tcp_ack"},
        )

        # Update state
        state.tcp_seq_client = client_seq + 1
        state.tcp_seq_server = server_seq + 1
        state.tcp_ack_client = server_seq + 1
        state.tcp_ack_server = client_seq + 1

    def _generate_device_info_cycle(
        self,
        flow: FlowContext,
        state: CodesysConversationState,
        cycle_time_ms: float,
        version: CodesysVersion,
    ) -> Iterator[PacketEvent]:
        """Generate device info query."""
        src_port = state.custom_data["src_port"]
        dst_port = state.custom_data["dst_port"]

        invoke_id = state.next_invoke_id()

        if version == CodesysVersion.V3:
            # V3 device info request
            payload = build_device_info_request(state.session_id, invoke_id)
        else:
            # V2 get info request
            payload = build_v2_get_info_request()

        req_packet = build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=dst_port,
            payload=payload,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=req_packet,
            direction="request",
            metadata={"type": "codesys_device_info_request", "invoke_id": invoke_id},
        )
        state.tcp_seq_client += len(payload)

        # Response
        response_delay = random.uniform(5.0, 25.0)
        response_time = cycle_time_ms + response_delay

        identity = self._get_device_identity(flow)

        if version == CodesysVersion.V3:
            resp_payload = build_device_info_response(
                state.session_id, invoke_id, identity
            )
        else:
            resp_payload = build_v2_get_info_response(identity)

        resp_packet = build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=dst_port,
            dst_port=src_port,
            payload=resp_payload,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=resp_packet,
            direction="response",
            metadata={
                "type": "codesys_device_info_response",
                "invoke_id": invoke_id,
                "device_name": identity.device_name,
                "firmware": identity.firmware_version,
                "response_delay_ms": response_delay,
            },
        )
        state.tcp_seq_server += len(resp_payload)

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: CodesysConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate poll cycle (variable read/write)."""
        if not state.is_connected:
            return

        version = CodesysVersion(state.custom_data.get("version", "v3"))
        operation = flow.config.get("operation", "read")

        if operation == "read":
            yield from self._generate_variable_read_cycle(flow, state, cycle_time_ms, version)
        elif operation == "write":
            yield from self._generate_variable_write_cycle(flow, state, cycle_time_ms, version)
        elif operation == "read_multiple":
            yield from self._generate_variable_read_multiple_cycle(flow, state, cycle_time_ms)
        elif operation == "status":
            yield from self._generate_device_status_cycle(flow, state, cycle_time_ms)
        elif operation == "app_info":
            yield from self._generate_app_info_cycle(flow, state, cycle_time_ms)
        else:
            # Default to read
            yield from self._generate_variable_read_cycle(flow, state, cycle_time_ms, version)

    def _generate_variable_read_cycle(
        self,
        flow: FlowContext,
        state: CodesysConversationState,
        cycle_time_ms: float,
        version: CodesysVersion,
    ) -> Iterator[PacketEvent]:
        """Generate variable read cycle."""
        src_port = state.custom_data["src_port"]
        dst_port = state.custom_data["dst_port"]

        # Get address from config
        address = flow.config.get("address", 0x1000)
        size = flow.config.get("size", 4)
        data_type = flow.config.get("data_type", CodesysDataType.DINT)
        if isinstance(data_type, int):
            data_type = CodesysDataType(data_type)

        invoke_id = state.next_invoke_id()

        # Build request
        payload = build_variable_read_request(
            session_id=state.session_id,
            invoke_id=invoke_id,
            address=address,
            size=size,
            data_type=data_type,
        )

        req_packet = build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=dst_port,
            payload=payload,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=req_packet,
            direction="request",
            metadata={
                "type": "codesys_var_read_request",
                "invoke_id": invoke_id,
                "address": f"0x{address:08X}",
                "size": size,
            },
        )
        state.tcp_seq_client += len(payload)

        # Generate response with random data
        response_delay = random.uniform(2.0, 15.0)
        response_time = cycle_time_ms + response_delay

        # Generate random value based on type
        if data_type in (CodesysDataType.BOOL, CodesysDataType.BYTE, CodesysDataType.SINT, CodesysDataType.USINT):
            value_data = bytes([random.randint(0, 255)])
        elif data_type in (CodesysDataType.WORD, CodesysDataType.INT, CodesysDataType.UINT):
            value_data = struct.pack("<H", random.randint(0, 65535))
        elif data_type in (CodesysDataType.REAL,):
            value_data = struct.pack("<f", random.uniform(-1000.0, 1000.0))
        elif data_type in (CodesysDataType.LREAL,):
            value_data = struct.pack("<d", random.uniform(-1000.0, 1000.0))
        else:
            value_data = struct.pack("<I", random.randint(0, 0xFFFFFFFF))

        # Pad or extend to requested size
        if len(value_data) < size:
            value_data = value_data + bytes(size - len(value_data))
        elif len(value_data) > size:
            value_data = value_data[:size]

        resp_payload = build_variable_read_response(
            session_id=state.session_id,
            invoke_id=invoke_id,
            data=value_data,
        )

        resp_packet = build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=dst_port,
            dst_port=src_port,
            payload=resp_payload,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=resp_packet,
            direction="response",
            metadata={
                "type": "codesys_var_read_response",
                "invoke_id": invoke_id,
                "data_hex": value_data.hex(),
                "response_delay_ms": response_delay,
            },
        )
        state.tcp_seq_server += len(resp_payload)

    def _generate_variable_write_cycle(
        self,
        flow: FlowContext,
        state: CodesysConversationState,
        cycle_time_ms: float,
        version: CodesysVersion,
    ) -> Iterator[PacketEvent]:
        """Generate variable write cycle."""
        src_port = state.custom_data["src_port"]
        dst_port = state.custom_data["dst_port"]

        address = flow.config.get("address", 0x1000)
        value = flow.config.get("value", 0)
        data_type = flow.config.get("data_type", CodesysDataType.DINT)
        if isinstance(data_type, int):
            data_type = CodesysDataType(data_type)

        # Encode value
        if data_type in (CodesysDataType.BOOL, CodesysDataType.BYTE, CodesysDataType.SINT, CodesysDataType.USINT):
            value_data = bytes([value & 0xFF])
        elif data_type in (CodesysDataType.WORD, CodesysDataType.INT, CodesysDataType.UINT):
            value_data = struct.pack("<H", value & 0xFFFF)
        elif data_type in (CodesysDataType.REAL,):
            value_data = struct.pack("<f", float(value))
        elif data_type in (CodesysDataType.LREAL,):
            value_data = struct.pack("<d", float(value))
        else:
            value_data = struct.pack("<I", value & 0xFFFFFFFF)

        invoke_id = state.next_invoke_id()

        payload = build_variable_write_request(
            session_id=state.session_id,
            invoke_id=invoke_id,
            address=address,
            data=value_data,
            data_type=data_type,
        )

        req_packet = build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=dst_port,
            payload=payload,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=req_packet,
            direction="request",
            metadata={
                "type": "codesys_var_write_request",
                "invoke_id": invoke_id,
                "address": f"0x{address:08X}",
                "value": value,
            },
        )
        state.tcp_seq_client += len(payload)

        # Response
        response_delay = random.uniform(2.0, 15.0)
        response_time = cycle_time_ms + response_delay

        resp_payload = build_variable_write_response(
            session_id=state.session_id,
            invoke_id=invoke_id,
        )

        resp_packet = build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=dst_port,
            dst_port=src_port,
            payload=resp_payload,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=resp_packet,
            direction="response",
            metadata={
                "type": "codesys_var_write_response",
                "invoke_id": invoke_id,
                "response_delay_ms": response_delay,
            },
        )
        state.tcp_seq_server += len(resp_payload)

    def _generate_variable_read_multiple_cycle(
        self,
        flow: FlowContext,
        state: CodesysConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate multiple variable read cycle."""
        src_port = state.custom_data["src_port"]
        dst_port = state.custom_data["dst_port"]

        # Get variables from config
        variables = flow.config.get("variables", [
            (0x1000, 4, CodesysDataType.DINT),
            (0x1004, 4, CodesysDataType.REAL),
            (0x1008, 2, CodesysDataType.INT),
        ])

        invoke_id = state.next_invoke_id()

        payload = build_variable_read_multiple_request(
            session_id=state.session_id,
            invoke_id=invoke_id,
            variables=variables,
        )

        req_packet = build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=dst_port,
            payload=payload,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=req_packet,
            direction="request",
            metadata={
                "type": "codesys_var_read_multiple_request",
                "invoke_id": invoke_id,
                "variable_count": len(variables),
            },
        )
        state.tcp_seq_client += len(payload)

        # Generate response values
        response_delay = random.uniform(5.0, 25.0)
        response_time = cycle_time_ms + response_delay

        values = []
        for addr, size, dtype in variables:
            values.append(random.randbytes(size))

        resp_payload = build_variable_read_multiple_response(
            session_id=state.session_id,
            invoke_id=invoke_id,
            values=values,
        )

        resp_packet = build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=dst_port,
            dst_port=src_port,
            payload=resp_payload,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=resp_packet,
            direction="response",
            metadata={
                "type": "codesys_var_read_multiple_response",
                "invoke_id": invoke_id,
                "response_delay_ms": response_delay,
            },
        )
        state.tcp_seq_server += len(resp_payload)

    def _generate_device_status_cycle(
        self,
        flow: FlowContext,
        state: CodesysConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate device status query."""
        src_port = state.custom_data["src_port"]
        dst_port = state.custom_data["dst_port"]

        invoke_id = state.next_invoke_id()

        payload = build_device_status_request(state.session_id, invoke_id)

        req_packet = build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=dst_port,
            payload=payload,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=req_packet,
            direction="request",
            metadata={"type": "codesys_status_request", "invoke_id": invoke_id},
        )
        state.tcp_seq_client += len(payload)

        response_delay = random.uniform(2.0, 10.0)
        response_time = cycle_time_ms + response_delay

        plc_state = flow.config.get("plc_state", PLCState.RUNNING)

        resp_payload = build_device_status_response(
            session_id=state.session_id,
            invoke_id=invoke_id,
            plc_state=plc_state,
        )

        resp_packet = build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=dst_port,
            dst_port=src_port,
            payload=resp_payload,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=resp_packet,
            direction="response",
            metadata={
                "type": "codesys_status_response",
                "invoke_id": invoke_id,
                "plc_state": PLCState(plc_state).name,
                "response_delay_ms": response_delay,
            },
        )
        state.tcp_seq_server += len(resp_payload)

    def _generate_app_info_cycle(
        self,
        flow: FlowContext,
        state: CodesysConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate application info query."""
        src_port = state.custom_data["src_port"]
        dst_port = state.custom_data["dst_port"]

        invoke_id = state.next_invoke_id()

        payload = build_app_info_request(state.session_id, invoke_id)

        req_packet = build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=dst_port,
            payload=payload,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=req_packet,
            direction="request",
            metadata={"type": "codesys_app_info_request", "invoke_id": invoke_id},
        )
        state.tcp_seq_client += len(payload)

        response_delay = random.uniform(5.0, 20.0)
        response_time = cycle_time_ms + response_delay

        app_name = flow.config.get("app_name", "Application")
        app_version = flow.config.get("app_version", "1.0.0.0")

        resp_payload = build_app_info_response(
            session_id=state.session_id,
            invoke_id=invoke_id,
            app_name=app_name,
            app_version=app_version,
        )

        resp_packet = build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=dst_port,
            dst_port=src_port,
            payload=resp_payload,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=resp_packet,
            direction="response",
            metadata={
                "type": "codesys_app_info_response",
                "invoke_id": invoke_id,
                "app_name": app_name,
                "response_delay_ms": response_delay,
            },
        )
        state.tcp_seq_server += len(resp_payload)

    def _get_device_identity(self, flow: FlowContext) -> CodesysDeviceIdentity:
        """Get device identity from fingerprint or config."""
        fingerprint = flow.destination.vendor_fingerprint
        if fingerprint:
            codesys_identity = fingerprint.get("codesys_identity", {})
            if codesys_identity:
                return CodesysDeviceIdentity(
                    vendor_id=codesys_identity.get("vendor_id", CodesysVendor.WAGO),
                    vendor_name=codesys_identity.get("vendor_name", "WAGO Kontakttechnik"),
                    device_name=codesys_identity.get("device_name", "WAGO 750-880"),
                    device_type=codesys_identity.get("device_type", "PFC100"),
                    serial_number=codesys_identity.get("serial_number", "00000000"),
                    firmware_version=codesys_identity.get("firmware_version", "3.5.19.0"),
                )

        # Check for device model in config
        model_key = flow.config.get("device_model", "WAGO_750_880")
        if model_key in CODESYS_DEVICE_MODELS:
            model = CODESYS_DEVICE_MODELS[model_key]
            vendor_id = model["vendor"]
            return CodesysDeviceIdentity(
                vendor_id=vendor_id,
                vendor_name=CODESYS_VENDOR_NAMES.get(vendor_id, "Unknown"),
                device_name=model["name"],
                device_type=model["type"],
                serial_number=flow.config.get("serial_number", f"{random.randint(0, 99999999):08d}"),
                firmware_version=flow.config.get("firmware_version", "3.5.19.0"),
            )

        # Default
        return CodesysDeviceIdentity()

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: CodesysConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate shutdown sequence."""
        if not state.is_connected:
            return

        src_port = state.custom_data.get("src_port", 49152)
        dst_port = state.custom_data.get("dst_port", CODESYS_V3_PORT)

        # TCP FIN
        fin_packet = build_tcp_fin(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=dst_port,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
        )
        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=fin_packet,
            direction="request",
            metadata={"type": "tcp_fin"},
        )

        # FIN-ACK
        fin_ack_time = start_time_ms + random.uniform(1.0, 3.0)
        fin_ack_packet = build_tcp_fin(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=dst_port,
            dst_port=src_port,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client + 1,
        )
        yield PacketEvent(
            timestamp_ms=fin_ack_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_ack_packet,
            direction="response",
            metadata={"type": "tcp_fin_ack"},
        )

        # Final ACK
        ack_time = fin_ack_time + random.uniform(0.1, 0.5)
        ack_packet = build_tcp_ack(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=dst_port,
            seq=state.tcp_seq_client + 1,
            ack=state.tcp_seq_server + 1,
        )
        yield PacketEvent(
            timestamp_ms=ack_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"type": "tcp_ack"},
        )

        state.is_connected = False
        state.state_name = "idle"

    def validate_config(self, config: dict) -> list[str]:
        """Validate Codesys configuration."""
        errors = []

        # Validate version
        version = config.get("version", "v3")
        if version not in ["v2", "v3"]:
            errors.append(f"Invalid version: {version}. Must be 'v2' or 'v3'")

        # Validate operation
        operation = config.get("operation", "read")
        valid_ops = ["read", "write", "read_multiple", "status", "app_info", "device_info"]
        if operation not in valid_ops:
            errors.append(f"Invalid operation: {operation}. Must be one of {valid_ops}")

        # Validate address
        address = config.get("address")
        if address is not None:
            if not isinstance(address, int) or address < 0:
                errors.append("address must be a non-negative integer")

        # Validate size
        size = config.get("size")
        if size is not None:
            if not isinstance(size, int) or size < 1 or size > 512:
                errors.append("size must be 1-512 bytes")

        # Validate data type
        data_type = config.get("data_type")
        if data_type is not None:
            try:
                if isinstance(data_type, int):
                    CodesysDataType(data_type)
            except ValueError:
                errors.append(f"Invalid data_type: {data_type}")

        return errors
