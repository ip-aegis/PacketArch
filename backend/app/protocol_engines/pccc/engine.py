# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""PCCC/DF1 protocol engine implementation.

Supports Allen-Bradley/Rockwell PLCs:
- PLC-5 series (legacy)
- SLC-500 series
- MicroLogix series
- ControlLogix/CompactLogix (compatibility mode)

Transport modes:
- PCCC over TCP (port 2222) - Legacy direct TCP
- PCCC over EtherNet/IP (port 44818) - Modern encapsulated
"""

import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.pccc.packets import (
    PCCC_TCP_PORT,
    ETHERNET_IP_PORT,
    build_pccc_tcp_packet,
    build_diagnostic_status_request,
    build_diagnostic_status_response,
    build_protected_typed_read_request,
    build_protected_typed_read_response,
    build_protected_typed_write_request,
    build_protected_typed_write_response,
    build_eip_register_session_request,
    build_eip_register_session_response,
    build_eip_unregister_session_request,
    build_eip_send_rr_data,
    build_tcp_packet,
    build_tcp_syn,
    build_tcp_syn_ack,
    build_tcp_ack,
    build_tcp_fin,
)
from app.protocol_engines.pccc.types import (
    PCCCTransport,
    PCCCCommand,
    PCCCFunction,
    PCCCStatus,
    PCCCFileType,
    PCCCAddress,
    PCCCDeviceIdentity,
    ABDeviceType,
    ABProductCode,
    AB_PRODUCT_NAMES,
)
from app.protocol_engines.types import (
    FlowContext,
    PacketEvent,
    PCCCConversationState,
    ProtocolType,
)


@register_engine(ProtocolType.PCCC)
class PCCCEngine(ProtocolEngine):
    """PCCC/DF1 protocol engine for Allen-Bradley PLCs."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.PCCC

    def create_initial_state(self, flow: FlowContext) -> PCCCConversationState:
        """Create initial conversation state."""
        state = PCCCConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            transaction_id=random.randint(1, 65535),
            tcp_seq_client=random.randint(1000, 9999),
            tcp_seq_server=random.randint(1000, 9999),
        )

        # Initialize sender context for EIP
        state.sender_context = random.randbytes(8)

        return state

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: PCCCConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate startup sequence.

        TCP mode: TCP handshake only
        EIP mode: TCP handshake + EtherNet/IP session registration
        """
        transport = flow.config.get("transport", PCCCTransport.TCP)
        if isinstance(transport, str):
            transport = PCCCTransport(transport)

        # Determine port based on transport
        dst_port = PCCC_TCP_PORT if transport == PCCCTransport.TCP else ETHERNET_IP_PORT
        src_port = flow.source.port or random.randint(49152, 65535)

        # Store port in state
        state.custom_data["src_port"] = src_port
        state.custom_data["dst_port"] = dst_port
        state.custom_data["transport"] = transport.value

        # === TCP Three-way Handshake ===
        yield from self._generate_tcp_handshake(flow, state, start_time_ms, src_port, dst_port)

        if transport == PCCCTransport.ETHERNET_IP:
            # === EtherNet/IP Session Registration ===
            yield from self._generate_eip_registration(flow, state, start_time_ms + 10)

        state.is_connected = True
        state.state_name = "connected"

    def _generate_tcp_handshake(
        self,
        flow: FlowContext,
        state: PCCCConversationState,
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

    def _generate_eip_registration(
        self,
        flow: FlowContext,
        state: PCCCConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate EtherNet/IP session registration."""
        src_port = state.custom_data["src_port"]
        dst_port = state.custom_data["dst_port"]

        # Register Session Request
        reg_req = build_eip_register_session_request()
        reg_req_packet = build_tcp_packet(
            src_mac=flow.source.mac_address,
            dst_mac=flow.destination.mac_address,
            src_ip=flow.source.ip_address,
            dst_ip=flow.destination.ip_address,
            src_port=src_port,
            dst_port=dst_port,
            payload=reg_req,
            seq=state.tcp_seq_client,
            ack=state.tcp_seq_server,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=reg_req_packet,
            direction="request",
            metadata={"type": "eip_register_session_request"},
        )
        state.tcp_seq_client += len(reg_req)

        # Register Session Response
        response_time = start_time_ms + random.uniform(2.0, 10.0)
        session_handle = random.randint(1, 0xFFFFFFFF)
        reg_resp = build_eip_register_session_response(session_handle)
        reg_resp_packet = build_tcp_packet(
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
            src_ip=flow.destination.ip_address,
            dst_ip=flow.source.ip_address,
            src_port=dst_port,
            dst_port=src_port,
            payload=reg_resp,
            seq=state.tcp_seq_server,
            ack=state.tcp_seq_client,
            flags="PA",
        )
        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=reg_resp_packet,
            direction="response",
            metadata={"type": "eip_register_session_response", "session_handle": session_handle},
        )
        state.tcp_seq_server += len(reg_resp)

        # Update state
        state.register_session(session_handle)

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: PCCCConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate PCCC poll cycle (read or write operation)."""
        if not state.is_connected:
            return

        transport = PCCCTransport(state.custom_data.get("transport", "tcp"))

        # Determine operation type
        operation = flow.config.get("operation", "read")

        if operation == "read":
            yield from self._generate_read_cycle(flow, state, cycle_time_ms, transport)
        elif operation == "write":
            yield from self._generate_write_cycle(flow, state, cycle_time_ms, transport)
        elif operation == "diagnostic":
            yield from self._generate_diagnostic_cycle(flow, state, cycle_time_ms, transport)
        else:
            # Default to read
            yield from self._generate_read_cycle(flow, state, cycle_time_ms, transport)

    def _generate_read_cycle(
        self,
        flow: FlowContext,
        state: PCCCConversationState,
        cycle_time_ms: float,
        transport: PCCCTransport,
    ) -> Iterator[PacketEvent]:
        """Generate Protected Typed Logical Read cycle."""
        src_port = state.custom_data["src_port"]
        dst_port = state.custom_data["dst_port"]

        # Parse address from config or use default
        address_str = flow.config.get("address", "N7:0")
        try:
            address = PCCCAddress.parse(address_str)
        except ValueError:
            # Default address
            address = PCCCAddress(
                file_type=PCCCFileType.INTEGER,
                file_number=7,
                element=0,
            )

        num_elements = flow.config.get("num_elements", 1)
        transaction_id = state.next_transaction_id()

        # Build PCCC read request
        pccc_request = build_protected_typed_read_request(
            transaction_id=transaction_id,
            address=address,
            num_elements=num_elements,
        )

        # Wrap based on transport
        if transport == PCCCTransport.ETHERNET_IP:
            payload = build_eip_send_rr_data(
                session_handle=state.session_handle,
                pccc_data=pccc_request,
                sender_context=state.sender_context,
            )
        else:
            payload = build_pccc_tcp_packet(pccc_request)

        # Send request
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
                "type": "pccc_read_request",
                "address": address.to_string(),
                "transaction_id": transaction_id,
            },
        )
        state.tcp_seq_client += len(payload)

        # Generate response with random values
        response_delay = random.uniform(5.0, 30.0)
        response_time = cycle_time_ms + response_delay

        # Generate random values for response
        values = [random.randint(0, 65535) for _ in range(num_elements)]

        pccc_response = build_protected_typed_read_response(
            transaction_id=transaction_id,
            values=values,
        )

        if transport == PCCCTransport.ETHERNET_IP:
            resp_payload = build_eip_send_rr_data(
                session_handle=state.session_handle,
                pccc_data=pccc_response,
                sender_context=state.sender_context,
            )
        else:
            resp_payload = build_pccc_tcp_packet(pccc_response)

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
                "type": "pccc_read_response",
                "address": address.to_string(),
                "transaction_id": transaction_id,
                "values": values,
                "response_delay_ms": response_delay,
            },
        )
        state.tcp_seq_server += len(resp_payload)

    def _generate_write_cycle(
        self,
        flow: FlowContext,
        state: PCCCConversationState,
        cycle_time_ms: float,
        transport: PCCCTransport,
    ) -> Iterator[PacketEvent]:
        """Generate Protected Typed Logical Write cycle."""
        src_port = state.custom_data["src_port"]
        dst_port = state.custom_data["dst_port"]

        # Parse address
        address_str = flow.config.get("address", "N7:0")
        try:
            address = PCCCAddress.parse(address_str)
        except ValueError:
            address = PCCCAddress(
                file_type=PCCCFileType.INTEGER,
                file_number=7,
                element=0,
            )

        # Get values to write
        values = flow.config.get("values", [0])
        if not isinstance(values, list):
            values = [values]

        transaction_id = state.next_transaction_id()

        # Build PCCC write request
        pccc_request = build_protected_typed_write_request(
            transaction_id=transaction_id,
            address=address,
            values=values,
        )

        if transport == PCCCTransport.ETHERNET_IP:
            payload = build_eip_send_rr_data(
                session_handle=state.session_handle,
                pccc_data=pccc_request,
                sender_context=state.sender_context,
            )
        else:
            payload = build_pccc_tcp_packet(pccc_request)

        # Send request
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
                "type": "pccc_write_request",
                "address": address.to_string(),
                "transaction_id": transaction_id,
                "values": values,
            },
        )
        state.tcp_seq_client += len(payload)

        # Generate response
        response_delay = random.uniform(5.0, 30.0)
        response_time = cycle_time_ms + response_delay

        pccc_response = build_protected_typed_write_response(transaction_id=transaction_id)

        if transport == PCCCTransport.ETHERNET_IP:
            resp_payload = build_eip_send_rr_data(
                session_handle=state.session_handle,
                pccc_data=pccc_response,
                sender_context=state.sender_context,
            )
        else:
            resp_payload = build_pccc_tcp_packet(pccc_response)

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
                "type": "pccc_write_response",
                "transaction_id": transaction_id,
                "response_delay_ms": response_delay,
            },
        )
        state.tcp_seq_server += len(resp_payload)

    def _generate_diagnostic_cycle(
        self,
        flow: FlowContext,
        state: PCCCConversationState,
        cycle_time_ms: float,
        transport: PCCCTransport,
    ) -> Iterator[PacketEvent]:
        """Generate Diagnostic Status cycle."""
        src_port = state.custom_data["src_port"]
        dst_port = state.custom_data["dst_port"]

        transaction_id = state.next_transaction_id()

        # Build diagnostic request
        pccc_request = build_diagnostic_status_request(transaction_id)

        if transport == PCCCTransport.ETHERNET_IP:
            payload = build_eip_send_rr_data(
                session_handle=state.session_handle,
                pccc_data=pccc_request,
                sender_context=state.sender_context,
            )
        else:
            payload = build_pccc_tcp_packet(pccc_request)

        # Send request
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
                "type": "pccc_diagnostic_request",
                "transaction_id": transaction_id,
            },
        )
        state.tcp_seq_client += len(payload)

        # Build identity from fingerprint or config
        identity = self._get_device_identity(flow)

        response_delay = random.uniform(5.0, 20.0)
        response_time = cycle_time_ms + response_delay

        pccc_response = build_diagnostic_status_response(
            transaction_id=transaction_id,
            identity=identity,
        )

        if transport == PCCCTransport.ETHERNET_IP:
            resp_payload = build_eip_send_rr_data(
                session_handle=state.session_handle,
                pccc_data=pccc_response,
                sender_context=state.sender_context,
            )
        else:
            resp_payload = build_pccc_tcp_packet(pccc_response)

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
                "type": "pccc_diagnostic_response",
                "transaction_id": transaction_id,
                "product_name": identity.product_name,
                "revision": identity.get_revision_string(),
                "response_delay_ms": response_delay,
            },
        )
        state.tcp_seq_server += len(resp_payload)

    def _get_device_identity(self, flow: FlowContext) -> PCCCDeviceIdentity:
        """Get device identity from fingerprint or config."""
        # Check for fingerprint-based identity
        fingerprint = flow.destination.vendor_fingerprint
        if fingerprint:
            pccc_identity = fingerprint.get("pccc_identity", {})
            if pccc_identity:
                return PCCCDeviceIdentity(
                    product_code=pccc_identity.get("product_code", ABProductCode.SLC500_05),
                    revision_major=pccc_identity.get("revision_major", 5),
                    revision_minor=pccc_identity.get("revision_minor", 0),
                    serial_number=pccc_identity.get("serial_number", random.randint(0, 0xFFFFFFFF)),
                    product_name=pccc_identity.get("product_name", "1747-L553 SLC-5/05"),
                )

        # Check config
        config = flow.config
        product_code = config.get("product_code", ABProductCode.SLC500_05)
        product_name = AB_PRODUCT_NAMES.get(product_code, "Allen-Bradley PLC")

        return PCCCDeviceIdentity(
            product_code=product_code,
            revision_major=config.get("revision_major", 5),
            revision_minor=config.get("revision_minor", 0),
            serial_number=config.get("serial_number", random.randint(0, 0xFFFFFFFF)),
            product_name=product_name,
        )

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: PCCCConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate shutdown sequence."""
        if not state.is_connected:
            return

        src_port = state.custom_data.get("src_port", 49152)
        dst_port = state.custom_data.get("dst_port", PCCC_TCP_PORT)
        transport = PCCCTransport(state.custom_data.get("transport", "tcp"))

        # Unregister EIP session if applicable
        if transport == PCCCTransport.ETHERNET_IP and state.is_registered:
            unreg_req = build_eip_unregister_session_request(state.session_handle)
            unreg_packet = build_tcp_packet(
                src_mac=flow.source.mac_address,
                dst_mac=flow.destination.mac_address,
                src_ip=flow.source.ip_address,
                dst_ip=flow.destination.ip_address,
                src_port=src_port,
                dst_port=dst_port,
                payload=unreg_req,
                seq=state.tcp_seq_client,
                ack=state.tcp_seq_server,
                flags="PA",
            )
            yield PacketEvent(
                timestamp_ms=start_time_ms,
                flow_id=flow.flow_id,
                packet_bytes=unreg_packet,
                direction="request",
                metadata={"type": "eip_unregister_session"},
            )
            state.tcp_seq_client += len(unreg_req)
            start_time_ms += random.uniform(1.0, 3.0)

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
        state.is_registered = False
        state.state_name = "idle"

    def validate_config(self, config: dict) -> list[str]:
        """Validate PCCC configuration."""
        errors = []

        # Validate transport
        transport = config.get("transport", "tcp")
        if transport not in ["tcp", "eip"]:
            errors.append(f"Invalid transport: {transport}. Must be 'tcp' or 'eip'")

        # Validate operation
        operation = config.get("operation", "read")
        if operation not in ["read", "write", "diagnostic"]:
            errors.append(f"Invalid operation: {operation}. Must be 'read', 'write', or 'diagnostic'")

        # Validate address format if provided
        address = config.get("address")
        if address:
            try:
                PCCCAddress.parse(address)
            except ValueError as e:
                errors.append(f"Invalid address format: {e}")

        # Validate values for write operation
        if operation == "write":
            values = config.get("values")
            if values is None:
                errors.append("values is required for write operation")
            elif isinstance(values, list):
                for i, v in enumerate(values):
                    if not isinstance(v, int):
                        errors.append(f"values[{i}] must be an integer")
                    elif not (0 <= v <= 65535):
                        errors.append(f"values[{i}] must be 0-65535")

        # Validate num_elements for read
        num_elements = config.get("num_elements", 1)
        if not isinstance(num_elements, int) or num_elements < 1 or num_elements > 244:
            errors.append("num_elements must be 1-244")

        return errors
