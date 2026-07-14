# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""EMP (Edge Message Protocol) engine — Interoperable Train Control (ITC/PTC).

Models the office/wayside IP side of the AAR ITC messaging stack: EMP messages
carried over a TCP session (Class D modelled as session behaviour — see
``packets.py`` for the fidelity scope). The canonical flow is a wayside node
(WIU) that opens a TCP connection to the Back Office Server (BOS), registers,
then exchanges periodic status reports and control commands.

Flow role convention:
- ``flow.source``      = the initiating field node (default node type ``w``,
  wayside). It opens the TCP connection and sends WIU status reports.
- ``flow.destination`` = the Back Office Server (default node type ``b``). It
  answers with application ACKs and occasional wayside-device control commands.

Config keys (all optional):
- ``railroad``            railroad mnemonic for EMP addresses (default ``aar``)
- ``source_node_type``    EMP node-type letter for source (default ``w``)
- ``dest_node_type``      EMP node-type letter for destination (default ``b``)
- ``wiu_id``              numeric wayside id used in payloads (default 1)
- ``base_epoch``          base unix time for payload timestamps (keeps PCAPs
                          reproducible; default 1_700_000_000)
- ``control_every``       emit a WDC control command every N poll cycles instead
                          of a plain ACK (default 5; 0 disables)
"""

from __future__ import annotations

import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.emp.packets import (
    EMP_MSG_ACK,
    EMP_MSG_NAMES,
    EMP_MSG_REGISTRATION,
    EMP_MSG_WDC_CONTROL,
    EMP_MSG_WIU_STATUS,
    build_ack_payload,
    build_emp_message,
    build_registration_payload,
    build_wdc_control_payload,
    build_wiu_status_payload,
    emp_address,
    emp_field_map,
)
from app.protocol_engines.tcp_builder import (
    build_tcp_ack,
    build_tcp_fin,
    build_tcp_fin_ack,
    build_tcp_packet,
    build_tcp_syn,
    build_tcp_syn_ack,
)
from app.protocol_engines.types import (
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)

DEFAULT_BASE_EPOCH = 1_700_000_000


@register_engine(ProtocolType.EMP)
class EmpEngine(ProtocolEngine):
    """Edge Message Protocol (ITC/PTC) engine."""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.EMP

    # -- helpers ----------------------------------------------------------

    def _addresses(self, flow: FlowContext) -> tuple[str, str]:
        """Return (source_emp_addr, dest_emp_addr) for this flow."""
        rr = flow.config.get("railroad", "aar")
        src_t = flow.config.get("source_node_type", "w")
        dst_t = flow.config.get("dest_node_type", "b")
        src_node = flow.source.device_name or flow.source.device_id
        dst_node = flow.destination.device_name or flow.destination.device_id
        return (
            emp_address(rr, src_t, src_node),
            emp_address(rr, dst_t, dst_node),
        )

    def _emp_event(
        self,
        flow: FlowContext,
        timestamp_ms: float,
        src,
        dst,
        seq: int,
        ack: int,
        msg_type: int,
        sender_addr: str,
        dest_addr: str,
        payload: bytes,
        payload_fields: list[dict],
        direction: str,
    ) -> PacketEvent:
        """Build one EMP-over-TCP PacketEvent with ground-truth label metadata."""
        frame = build_emp_message(msg_type, sender_addr, dest_addr, payload)
        packet = build_tcp_packet(
            src, dst, payload=frame, seq=seq, ack=ack, flags="PA",
            tcp_options=src.fingerprint_applicator.get_tcp_options(),
        )
        # EMP begins after Ethernet(14) + IP(20) + TCP(20) = 54 bytes. The
        # corpus exporter shifts EMP-relative offsets by this base.
        return PacketEvent(
            timestamp_ms=timestamp_ms,
            flow_id=flow.flow_id,
            packet_bytes=packet,
            direction=direction,
            metadata={
                "type": f"emp_{EMP_MSG_NAMES.get(msg_type, msg_type)}",
                "protocol": "emp",
                "emp_msg_type": msg_type,
                "emp_src": sender_addr,
                "emp_dst": dest_addr,
                "l7_offset": 54,
                "emp_fields": emp_field_map(
                    msg_type, sender_addr, dest_addr, payload, payload_fields
                ),
            },
        )

    # -- engine contract --------------------------------------------------

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        return ConversationState(
            flow_id=flow.flow_id,
            state_name="disconnected",
            transaction_id=0,
            sequence_number=0,
            custom_data={
                "tcp_seq_client": random.randint(1000, 900000),
                "tcp_seq_server": random.randint(1000, 900000),
                "app_seq": 0,
                "wiu_id": flow.config.get("wiu_id", 1),
                "signal_aspect": random.randint(0, 3),
                "cycle": 0,
            },
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """TCP handshake + EMP node registration + ACK."""
        t = start_time_ms
        cd = state.custom_data
        client_seq = cd["tcp_seq_client"]
        server_seq = cd["tcp_seq_server"]
        src_addr, dst_addr = self._addresses(flow)

        # TCP three-way handshake
        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_syn(
                flow.source, flow.destination, client_seq,
                tcp_options=flow.source.fingerprint_applicator.get_tcp_options(),
            ),
            direction="request",
            metadata={"type": "tcp_syn", "protocol": "emp"},
        )
        t += random.uniform(1.0, 5.0)
        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_syn_ack(
                flow.destination, flow.source, server_seq, client_seq + 1,
                tcp_options=flow.destination.fingerprint_applicator.get_tcp_options(),
            ),
            direction="response",
            metadata={"type": "tcp_syn_ack", "protocol": "emp"},
        )
        t += random.uniform(0.1, 0.5)
        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_ack(
                flow.source, flow.destination, client_seq + 1, server_seq + 1,
            ),
            direction="request",
            metadata={"type": "tcp_ack", "protocol": "emp"},
        )
        client_seq += 1
        server_seq += 1

        # EMP registration (WIU -> BOS)
        t += random.uniform(10.0, 40.0)
        reg_payload, reg_fields = build_registration_payload(
            node_id=cd["wiu_id"], role=1
        )
        yield self._emp_event(
            flow, t, flow.source, flow.destination, client_seq, server_seq,
            EMP_MSG_REGISTRATION, src_addr, dst_addr, reg_payload, reg_fields,
            "request",
        )
        client_seq += len(build_emp_message(
            EMP_MSG_REGISTRATION, src_addr, dst_addr, reg_payload
        ))

        # EMP registration ACK (BOS -> WIU)
        t += random.uniform(5.0, 20.0)
        ack_payload, ack_fields = build_ack_payload(ack_seq=cd["app_seq"])
        yield self._emp_event(
            flow, t, flow.destination, flow.source, server_seq, client_seq,
            EMP_MSG_ACK, dst_addr, src_addr, ack_payload, ack_fields,
            "response",
        )
        server_seq += len(build_emp_message(
            EMP_MSG_ACK, dst_addr, src_addr, ack_payload
        ))

        cd["tcp_seq_client"] = client_seq
        cd["tcp_seq_server"] = server_seq
        state.state_name = "registered"

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """WIU status report (WIU -> BOS) + BOS ACK or wayside control command."""
        cd = state.custom_data
        client_seq = cd["tcp_seq_client"]
        server_seq = cd["tcp_seq_server"]
        src_addr, dst_addr = self._addresses(flow)
        base_epoch = flow.config.get("base_epoch", DEFAULT_BASE_EPOCH)
        epoch_s = int(base_epoch + cycle_time_ms / 1000.0)

        # Evolve the signal aspect as a small random walk (plausible wayside state).
        aspect = cd["signal_aspect"]
        aspect = max(0, min(3, aspect + random.choice([-1, 0, 0, 1])))
        cd["signal_aspect"] = aspect

        status_payload, status_fields = build_wiu_status_payload(
            wiu_id=cd["wiu_id"],
            signal_aspect=aspect,
            switch_normal=random.random() > 0.15,
            track_occupancy=random.getrandbits(8),
            battery_dv=random.randint(1180, 1320),   # 118.0–132.0 V
            vital_ok=random.random() > 0.02,
            epoch_s=epoch_s,
        )
        yield self._emp_event(
            flow, cycle_time_ms, flow.source, flow.destination,
            client_seq, server_seq,
            EMP_MSG_WIU_STATUS, src_addr, dst_addr, status_payload, status_fields,
            "request",
        )
        client_seq += len(build_emp_message(
            EMP_MSG_WIU_STATUS, src_addr, dst_addr, status_payload
        ))

        # BOS response: usually an ACK, periodically a wayside-device control.
        cd["cycle"] += 1
        control_every = flow.config.get("control_every", 5)
        resp_time = cycle_time_ms + random.uniform(15.0, 80.0)
        if control_every and cd["cycle"] % control_every == 0:
            cd["app_seq"] += 1
            ctl_payload, ctl_fields = build_wdc_control_payload(
                wiu_id=cd["wiu_id"],
                command=random.choice([1, 2, 3]),   # e.g. set-aspect / throw-switch
                target=random.randint(1, 64),
                value=random.randint(0, 3),
                seq=cd["app_seq"] & 0xFFFF,
            )
            yield self._emp_event(
                flow, resp_time, flow.destination, flow.source,
                server_seq, client_seq,
                EMP_MSG_WDC_CONTROL, dst_addr, src_addr, ctl_payload, ctl_fields,
                "response",
            )
            server_seq += len(build_emp_message(
                EMP_MSG_WDC_CONTROL, dst_addr, src_addr, ctl_payload
            ))
        else:
            ack_payload, ack_fields = build_ack_payload(ack_seq=cd["app_seq"] & 0xFFFF)
            yield self._emp_event(
                flow, resp_time, flow.destination, flow.source,
                server_seq, client_seq,
                EMP_MSG_ACK, dst_addr, src_addr, ack_payload, ack_fields,
                "response",
            )
            server_seq += len(build_emp_message(
                EMP_MSG_ACK, dst_addr, src_addr, ack_payload
            ))

        cd["tcp_seq_client"] = client_seq
        cd["tcp_seq_server"] = server_seq
        state.sequence_number += 1

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """TCP FIN teardown."""
        t = start_time_ms
        cd = state.custom_data
        client_seq = cd["tcp_seq_client"]
        server_seq = cd["tcp_seq_server"]

        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_fin(
                flow.source, flow.destination, client_seq, server_seq
            ),
            direction="request",
            metadata={"type": "tcp_fin", "protocol": "emp"},
        )
        t += random.uniform(1.0, 5.0)
        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_fin_ack(
                flow.destination, flow.source, server_seq, client_seq + 1
            ),
            direction="response",
            metadata={"type": "tcp_fin_ack", "protocol": "emp"},
        )
        t += random.uniform(0.1, 0.5)
        yield PacketEvent(
            timestamp_ms=t,
            flow_id=flow.flow_id,
            packet_bytes=build_tcp_ack(
                flow.source, flow.destination, client_seq + 1, server_seq + 1
            ),
            direction="request",
            metadata={"type": "tcp_ack", "protocol": "emp"},
        )
        state.state_name = "disconnected"

    def validate_config(self, config: dict) -> list[str]:
        errors: list[str] = []

        wiu_id = config.get("wiu_id")
        if wiu_id is not None and (not isinstance(wiu_id, int) or not 0 <= wiu_id <= 0xFFFF):
            errors.append("wiu_id must be an integer 0-65535")

        control_every = config.get("control_every")
        if control_every is not None and (not isinstance(control_every, int) or control_every < 0):
            errors.append("control_every must be a non-negative integer")

        base_epoch = config.get("base_epoch")
        if base_epoch is not None and (not isinstance(base_epoch, int) or base_epoch < 0):
            errors.append("base_epoch must be a non-negative integer")

        for key in ("source_node_type", "dest_node_type"):
            val = config.get(key)
            if val is not None and (not isinstance(val, str) or len(val) != 1 or not val.isalpha()):
                errors.append(f"{key} must be a single letter (e.g. 'w', 'b', 'l')")

        return errors
