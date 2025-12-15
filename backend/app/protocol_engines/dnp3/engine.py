"""DNP3 protocol engine implementation.

DNP3 (Distributed Network Protocol version 3) is used in SCADA systems
for electric utilities, water/wastewater, and oil/gas industries.

Key features:
- TCP port 20000 (or serial)
- Master/Outstation architecture
- Event-based and polled data
- Time synchronization
- Multiple object types (binary, analog, counter)
"""

import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.dnp3.packets import (
    DNP3_PORT,
    GROUP_ANALOG_INPUT,
    GROUP_BINARY_INPUT,
    GROUP_COUNTER,
    build_dnp3_packet,
    build_read_request,
    build_read_response,
    build_write_request,
    build_write_response,
)
from app.protocol_engines.modbus.packets import (
    build_tcp_fin,
    build_tcp_fin_ack,
    build_tcp_handshake_ack,
    build_tcp_handshake_syn,
    build_tcp_handshake_syn_ack,
)
from app.protocol_engines.timing import get_response_delay
from app.protocol_engines.types import (
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)


@register_engine(ProtocolType.DNP3)
class Dnp3Engine(ProtocolEngine):
    """DNP3 protocol engine."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.DNP3

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        """Create initial conversation state."""
        return ConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            transaction_id=0,
            sequence_number=0,
            custom_data={
                "tcp_seq_client": random.randint(1000, 9999),
                "tcp_seq_server": random.randint(1000, 9999),
                "master_address": flow.config.get("master_address", 1),
                "outstation_address": flow.config.get("outstation_address", 10),
                "app_sequence": 0,
            },
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate DNP3 connection establishment.

        For DNP3/TCP, this includes TCP handshake followed by
        optional integrity poll.
        """
        current_time = start_time_ms
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]

        # === TCP Three-Way Handshake ===

        # SYN
        syn_packet = build_tcp_handshake_syn(flow.source, flow.destination, client_seq)
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_packet,
            direction="request",
            metadata={"type": "tcp_syn"},
        )

        # SYN-ACK
        current_time += random.uniform(1.0, 5.0)
        syn_ack_packet = build_tcp_handshake_syn_ack(
            flow.destination, flow.source, server_seq, client_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=syn_ack_packet,
            direction="response",
            metadata={"type": "tcp_syn_ack"},
        )

        # ACK
        current_time += random.uniform(0.1, 0.5)
        ack_packet = build_tcp_handshake_ack(
            flow.source, flow.destination, client_seq + 1, server_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",
            metadata={"type": "tcp_ack"},
        )

        client_seq += 1
        server_seq += 1

        # === Integrity Poll (Class 1, 2, 3, 0 data) ===

        if flow.config.get("integrity_poll", True):
            current_time += random.uniform(50.0, 200.0)

            master_addr = state.custom_data["master_address"]
            outstation_addr = state.custom_data["outstation_address"]

            # Read all class data
            read_frame = build_read_request(
                destination=outstation_addr,
                source=master_addr,
                objects=[
                    (60, 2),  # Class 1
                    (60, 3),  # Class 2
                    (60, 4),  # Class 3
                    (60, 1),  # Class 0 (static data)
                ],
                sequence=0,
            )

            read_packet = build_dnp3_packet(
                flow.source, flow.destination, read_frame,
                seq=client_seq, ack=server_seq
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=read_packet,
                direction="request",
                metadata={
                    "type": "dnp3_integrity_poll",
                    "master_address": master_addr,
                    "outstation_address": outstation_addr,
                },
            )

            client_seq += len(read_frame)

            # Response with static data
            current_time += random.uniform(20.0, 100.0)

            # Generate some sample data
            binary_values = [random.choice([True, False]) for _ in range(4)]
            analog_values = [random.uniform(0, 100) for _ in range(4)]
            counter_values = [random.randint(0, 10000) for _ in range(2)]

            response_frame = build_read_response(
                destination=master_addr,
                source=outstation_addr,
                objects=[
                    (GROUP_BINARY_INPUT, 1, binary_values),
                    (GROUP_ANALOG_INPUT, 5, analog_values),
                    (GROUP_COUNTER, 1, counter_values),
                ],
                sequence=0,
            )

            response_packet = build_dnp3_packet(
                flow.destination, flow.source, response_frame,
                seq=server_seq, ack=client_seq
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=response_packet,
                direction="response",
                metadata={
                    "type": "dnp3_integrity_response",
                    "binary_count": len(binary_values),
                    "analog_count": len(analog_values),
                    "counter_count": len(counter_values),
                },
            )

            server_seq += len(response_frame)
            state.custom_data["app_sequence"] = 1

        # Update state
        state.custom_data["tcp_seq_client"] = client_seq
        state.custom_data["tcp_seq_server"] = server_seq
        state.state_name = "connected"

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate DNP3 poll cycle.

        Typically polls for event data (Class 1, 2, 3).
        """
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]
        master_addr = state.custom_data["master_address"]
        outstation_addr = state.custom_data["outstation_address"]
        app_seq = state.custom_data["app_sequence"]

        # === Event Poll ===

        # Get poll type from config
        poll_type = flow.config.get("poll_type", "event")

        if poll_type == "event":
            # Poll for event data (Class 1, 2, 3)
            objects_to_read = [(60, 2), (60, 3), (60, 4)]
        elif poll_type == "static":
            # Poll for static data (Class 0)
            objects_to_read = [(60, 1)]
        else:
            # Poll specific objects
            objects_to_read = flow.config.get("objects", [(GROUP_ANALOG_INPUT, 0)])

        read_frame = build_read_request(
            destination=outstation_addr,
            source=master_addr,
            objects=objects_to_read,
            sequence=app_seq,
        )

        read_packet = build_dnp3_packet(
            flow.source, flow.destination, read_frame,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=read_packet,
            direction="request",
            metadata={
                "type": "dnp3_poll_request",
                "poll_type": poll_type,
                "sequence": app_seq,
            },
        )

        client_seq += len(read_frame)

        # === Poll Response ===

        response_delay = get_response_delay(flow.timing_model)
        response_time = cycle_time_ms + response_delay

        # Generate response data based on config
        objects_response = []

        if poll_type == "event":
            # Random chance of having events
            if random.random() < 0.3:  # 30% chance of events
                # Some event data
                event_count = random.randint(1, 3)
                analog_events = [random.uniform(-10, 110) for _ in range(event_count)]
                objects_response.append((GROUP_ANALOG_INPUT, 5, analog_events))
        else:
            # Static data response
            point_count = flow.config.get("point_count", 4)
            analog_values = [random.uniform(0, 100) for _ in range(point_count)]
            objects_response.append((GROUP_ANALOG_INPUT, 5, analog_values))

        response_frame = build_read_response(
            destination=master_addr,
            source=outstation_addr,
            objects=objects_response,
            sequence=app_seq,
        )

        response_packet = build_dnp3_packet(
            flow.destination, flow.source, response_frame,
            seq=server_seq, ack=client_seq
        )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_packet,
            direction="response",
            metadata={
                "type": "dnp3_poll_response",
                "sequence": app_seq,
                "object_count": len(objects_response),
            },
        )

        server_seq += len(response_frame)

        # Update state
        state.custom_data["tcp_seq_client"] = client_seq
        state.custom_data["tcp_seq_server"] = server_seq
        state.custom_data["app_sequence"] = (app_seq + 1) % 16
        state.sequence_number += 1

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate DNP3 connection termination."""
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]
        current_time = start_time_ms

        # TCP FIN handshake
        fin_packet = build_tcp_fin(
            flow.source, flow.destination, client_seq, server_seq
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_packet,
            direction="request",
            metadata={"type": "tcp_fin"},
        )

        current_time += random.uniform(1.0, 5.0)
        fin_ack_packet = build_tcp_fin_ack(
            flow.destination, flow.source, server_seq, client_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=fin_ack_packet,
            direction="response",
            metadata={"type": "tcp_fin_ack"},
        )

        current_time += random.uniform(0.1, 0.5)
        final_ack = build_tcp_handshake_ack(
            flow.source, flow.destination, client_seq + 1, server_seq + 1
        )
        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=final_ack,
            direction="request",
            metadata={"type": "tcp_ack"},
        )

        state.state_name = "idle"

    def validate_config(self, config: dict) -> list[str]:
        """Validate DNP3 configuration."""
        errors = []

        # Validate addresses
        master_addr = config.get("master_address")
        if master_addr is not None:
            if not isinstance(master_addr, int) or master_addr < 0 or master_addr > 65519:
                errors.append("master_address must be 0-65519")

        outstation_addr = config.get("outstation_address")
        if outstation_addr is not None:
            if not isinstance(outstation_addr, int) or outstation_addr < 0 or outstation_addr > 65519:
                errors.append("outstation_address must be 0-65519")

        # Validate poll type
        poll_type = config.get("poll_type")
        if poll_type is not None:
            if poll_type not in ["event", "static", "custom"]:
                errors.append("poll_type must be 'event', 'static', or 'custom'")

        # Validate point count
        point_count = config.get("point_count")
        if point_count is not None:
            if not isinstance(point_count, int) or point_count < 1 or point_count > 65535:
                errors.append("point_count must be 1-65535")

        return errors
