"""IEC 60870-5-104 protocol engine implementation.

IEC 104 is the network adaptation of IEC 101, used for telecontrol
in power system automation and substation communication.

Key features:
- TCP port 2404
- Controlling station / Controlled station architecture
- Balanced and unbalanced modes
- General interrogation
- Spontaneous data transmission
- Time synchronization
"""

import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.iec104.packets import (
    COT_INTERROGATION,
    COT_SPONTANEOUS,
    IEC104_PORT,
    STARTDT_ACT,
    STARTDT_CON,
    STOPDT_ACT,
    STOPDT_CON,
    build_apci_s_format,
    build_apci_u_format,
    build_iec104_packet,
    build_interrogation_command,
    build_interrogation_end,
    build_interrogation_response,
    build_measured_value_float,
    build_measured_value_scaled,
    build_single_point_info,
)
from app.protocol_engines.modbus.packets import (
    build_tcp_fin,
    build_tcp_fin_ack,
    build_tcp_handshake_ack,
    build_tcp_handshake_syn,
    build_tcp_handshake_syn_ack,
)
from app.protocol_engines.jitter import get_response_delay
from app.protocol_engines.types import (
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)


@register_engine(ProtocolType.IEC_104)
class Iec104Engine(ProtocolEngine):
    """IEC 60870-5-104 protocol engine."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.IEC_104

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        """Create initial conversation state."""
        return ConversationState(
            flow_id=flow.flow_id,
            state_name="stopped",
            transaction_id=0,
            sequence_number=0,
            custom_data={
                "tcp_seq_client": random.randint(1000, 9999),
                "tcp_seq_server": random.randint(1000, 9999),
                "send_seq": 0,  # V(S) - send sequence
                "recv_seq": 0,  # V(R) - receive sequence
                "common_address": flow.config.get("common_address", 1),
            },
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate IEC 104 connection establishment.

        Sequence:
        1. TCP handshake
        2. STARTDT_ACT / STARTDT_CON
        3. General Interrogation (optional)
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

        # === STARTDT Activation ===

        current_time += random.uniform(10.0, 50.0)

        startdt_act = build_apci_u_format(STARTDT_ACT)
        startdt_packet = build_iec104_packet(
            flow.source, flow.destination, startdt_act,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=startdt_packet,
            direction="request",
            metadata={"type": "iec104_startdt_act"},
        )

        client_seq += len(startdt_act)

        # === STARTDT Confirmation ===

        current_time += random.uniform(5.0, 20.0)

        startdt_con = build_apci_u_format(STARTDT_CON)
        startdt_con_packet = build_iec104_packet(
            flow.destination, flow.source, startdt_con,
            seq=server_seq, ack=client_seq
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=startdt_con_packet,
            direction="response",
            metadata={"type": "iec104_startdt_con"},
        )

        server_seq += len(startdt_con)

        # === General Interrogation (optional) ===

        if flow.config.get("general_interrogation", True):
            current_time += random.uniform(50.0, 200.0)

            common_addr = state.custom_data["common_address"]
            send_seq = state.custom_data["send_seq"]
            recv_seq = state.custom_data["recv_seq"]

            # Interrogation command
            gi_command = build_interrogation_command(
                send_seq=send_seq,
                recv_seq=recv_seq,
                common_address=common_addr,
            )
            gi_packet = build_iec104_packet(
                flow.source, flow.destination, gi_command,
                seq=client_seq, ack=server_seq
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=gi_packet,
                direction="request",
                metadata={
                    "type": "iec104_gi_request",
                    "common_address": common_addr,
                },
            )

            client_seq += len(gi_command)
            send_seq += 1

            # Interrogation confirmation
            current_time += random.uniform(10.0, 30.0)

            gi_con = build_interrogation_response(
                send_seq=recv_seq,
                recv_seq=send_seq,
                common_address=common_addr,
            )
            gi_con_packet = build_iec104_packet(
                flow.destination, flow.source, gi_con,
                seq=server_seq, ack=client_seq
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=gi_con_packet,
                direction="response",
                metadata={"type": "iec104_gi_con"},
            )

            server_seq += len(gi_con)
            recv_seq += 1

            # Send some data in response to GI
            current_time += random.uniform(5.0, 15.0)

            # Single point info
            sp_values = [
                (1, random.choice([True, False])),
                (2, random.choice([True, False])),
                (3, random.choice([True, False])),
            ]
            sp_data = build_single_point_info(
                send_seq=recv_seq,
                recv_seq=send_seq,
                common_address=common_addr,
                values=sp_values,
                cot=COT_INTERROGATION,
            )
            sp_packet = build_iec104_packet(
                flow.destination, flow.source, sp_data,
                seq=server_seq, ack=client_seq
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=sp_packet,
                direction="response",
                metadata={
                    "type": "iec104_sp_data",
                    "point_count": len(sp_values),
                },
            )

            server_seq += len(sp_data)
            recv_seq += 1

            # Measured values
            current_time += random.uniform(2.0, 8.0)

            mv_values = [
                (101, random.uniform(0, 100)),
                (102, random.uniform(0, 100)),
                (103, random.uniform(0, 100)),
                (104, random.uniform(0, 100)),
            ]
            mv_data = build_measured_value_float(
                send_seq=recv_seq,
                recv_seq=send_seq,
                common_address=common_addr,
                values=mv_values,
                cot=COT_INTERROGATION,
            )
            mv_packet = build_iec104_packet(
                flow.destination, flow.source, mv_data,
                seq=server_seq, ack=client_seq
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=mv_packet,
                direction="response",
                metadata={
                    "type": "iec104_mv_data",
                    "point_count": len(mv_values),
                },
            )

            server_seq += len(mv_data)
            recv_seq += 1

            # Interrogation termination
            current_time += random.uniform(5.0, 15.0)

            gi_end = build_interrogation_end(
                send_seq=recv_seq,
                recv_seq=send_seq,
                common_address=common_addr,
            )
            gi_end_packet = build_iec104_packet(
                flow.destination, flow.source, gi_end,
                seq=server_seq, ack=client_seq
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=gi_end_packet,
                direction="response",
                metadata={"type": "iec104_gi_end"},
            )

            server_seq += len(gi_end)
            recv_seq += 1

            state.custom_data["send_seq"] = send_seq
            state.custom_data["recv_seq"] = recv_seq

        # Update state
        state.custom_data["tcp_seq_client"] = client_seq
        state.custom_data["tcp_seq_server"] = server_seq
        state.state_name = "started"

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate IEC 104 spontaneous data transmission.

        IEC 104 is typically event-driven, with spontaneous
        data transmission when values change.
        """
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]
        send_seq = state.custom_data["send_seq"]
        recv_seq = state.custom_data["recv_seq"]
        common_addr = state.custom_data["common_address"]

        # === Spontaneous Data ===

        data_type = flow.config.get("data_type", "measured_float")
        point_count = flow.config.get("point_count", 4)
        base_ioa = flow.config.get("base_ioa", 101)

        if data_type == "single_point":
            values = [(base_ioa + i, random.choice([True, False])) for i in range(point_count)]
            data_apdu = build_single_point_info(
                send_seq=recv_seq,
                recv_seq=send_seq,
                common_address=common_addr,
                values=values,
                cot=COT_SPONTANEOUS,
            )
            data_type_str = "iec104_sp_spontaneous"
        elif data_type == "measured_scaled":
            values = [(base_ioa + i, random.randint(-32768, 32767)) for i in range(point_count)]
            data_apdu = build_measured_value_scaled(
                send_seq=recv_seq,
                recv_seq=send_seq,
                common_address=common_addr,
                values=values,
                cot=COT_SPONTANEOUS,
            )
            data_type_str = "iec104_mv_scaled_spontaneous"
        else:  # measured_float
            values = [(base_ioa + i, random.uniform(-100, 100)) for i in range(point_count)]
            data_apdu = build_measured_value_float(
                send_seq=recv_seq,
                recv_seq=send_seq,
                common_address=common_addr,
                values=values,
                cot=COT_SPONTANEOUS,
            )
            data_type_str = "iec104_mv_float_spontaneous"

        data_packet = build_iec104_packet(
            flow.destination, flow.source, data_apdu,
            seq=server_seq, ack=client_seq
        )

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=data_packet,
            direction="response",
            metadata={
                "type": data_type_str,
                "point_count": point_count,
                "send_seq": recv_seq,
            },
        )

        server_seq += len(data_apdu)
        recv_seq += 1

        # === S-format Acknowledgment ===

        response_delay = get_response_delay(flow.timing_model)
        ack_time = cycle_time_ms + response_delay

        s_format = build_apci_s_format(recv_seq)
        s_packet = build_iec104_packet(
            flow.source, flow.destination, s_format,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=ack_time,
            flow_id=flow.flow_id,
            packet_bytes=s_packet,
            direction="request",
            metadata={
                "type": "iec104_s_format",
                "recv_seq": recv_seq,
            },
        )

        client_seq += len(s_format)

        # Update state
        state.custom_data["tcp_seq_client"] = client_seq
        state.custom_data["tcp_seq_server"] = server_seq
        state.custom_data["send_seq"] = send_seq
        state.custom_data["recv_seq"] = recv_seq
        state.sequence_number += 1

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate IEC 104 connection termination.

        Sequence:
        1. STOPDT_ACT / STOPDT_CON
        2. TCP FIN handshake
        """
        current_time = start_time_ms
        client_seq = state.custom_data["tcp_seq_client"]
        server_seq = state.custom_data["tcp_seq_server"]

        # === STOPDT Activation ===

        stopdt_act = build_apci_u_format(STOPDT_ACT)
        stopdt_packet = build_iec104_packet(
            flow.source, flow.destination, stopdt_act,
            seq=client_seq, ack=server_seq
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=stopdt_packet,
            direction="request",
            metadata={"type": "iec104_stopdt_act"},
        )

        client_seq += len(stopdt_act)

        # === STOPDT Confirmation ===

        current_time += random.uniform(5.0, 15.0)

        stopdt_con = build_apci_u_format(STOPDT_CON)
        stopdt_con_packet = build_iec104_packet(
            flow.destination, flow.source, stopdt_con,
            seq=server_seq, ack=client_seq
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=stopdt_con_packet,
            direction="response",
            metadata={"type": "iec104_stopdt_con"},
        )

        server_seq += len(stopdt_con)

        # === TCP FIN Handshake ===

        current_time += random.uniform(10.0, 30.0)

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

        state.state_name = "stopped"

    def validate_config(self, config: dict) -> list[str]:
        """Validate IEC 104 configuration."""
        errors = []

        # Validate common address
        common_addr = config.get("common_address")
        if common_addr is not None:
            if not isinstance(common_addr, int) or common_addr < 1 or common_addr > 65534:
                errors.append("common_address must be 1-65534")

        # Validate data type
        data_type = config.get("data_type")
        if data_type is not None:
            valid_types = ["single_point", "measured_float", "measured_scaled"]
            if data_type not in valid_types:
                errors.append(f"data_type must be one of: {valid_types}")

        # Validate point count
        point_count = config.get("point_count")
        if point_count is not None:
            if not isinstance(point_count, int) or point_count < 1 or point_count > 127:
                errors.append("point_count must be 1-127")

        # Validate base IOA
        base_ioa = config.get("base_ioa")
        if base_ioa is not None:
            if not isinstance(base_ioa, int) or base_ioa < 0 or base_ioa > 16777215:
                errors.append("base_ioa must be 0-16777215")

        return errors
