# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for IEC 60870-5-104 protocol engine."""

import pytest

from app.protocol_engines import get_engine, list_supported_protocols
from app.protocol_engines.types import (
    DeviceContext,
    FlowContext,
    ProtocolType,
)
from app.protocol_engines.iec104.engine import Iec104Engine
from app.protocol_engines.iec104.packets import (
    IEC104_PORT,
    IEC104_START_BYTE,
    STARTDT_ACT,
    STARTDT_CON,
    COT_SPONTANEOUS,
    build_apci_u_format,
    build_apci_s_format,
    build_apci_i_format,
    build_interrogation_command,
    build_interrogation_response,
    build_single_point_info,
    build_measured_value_float,
    build_measured_value_scaled,
    build_single_command,
)


class TestIec104EngineRegistry:
    """Test IEC 104 engine registration."""

    def test_iec104_registered(self):
        """Test that IEC 104 engine is registered."""
        protocols = list_supported_protocols()
        assert ProtocolType.IEC_104 in protocols

    def test_get_iec104_engine(self):
        """Test getting IEC 104 engine instance."""
        engine = get_engine(ProtocolType.IEC_104)
        assert isinstance(engine, Iec104Engine)
        assert engine.protocol_type == ProtocolType.IEC_104


class TestIec104Packets:
    """Test IEC 104 packet building."""

    def test_apci_u_format(self):
        """Test U-format APCI building."""
        apci = build_apci_u_format(STARTDT_ACT)

        assert len(apci) == 6
        assert apci[0] == IEC104_START_BYTE
        assert apci[1] == 4  # APDU length
        assert apci[2] == STARTDT_ACT

    def test_apci_s_format(self):
        """Test S-format APCI building."""
        apci = build_apci_s_format(recv_seq=10)

        assert len(apci) == 6
        assert apci[0] == IEC104_START_BYTE
        # Bit 0-1 of control should be 01 for S-format
        assert (apci[2] & 0x03) == 0x01

    def test_apci_i_format(self):
        """Test I-format APCI building."""
        apci = build_apci_i_format(send_seq=5, recv_seq=3, asdu_length=10)

        assert len(apci) == 6
        assert apci[0] == IEC104_START_BYTE
        assert apci[1] == 4 + 10  # Control fields + ASDU
        # Bit 0 of control should be 0 for I-format
        assert (apci[2] & 0x01) == 0x00

    def test_interrogation_command(self):
        """Test Interrogation command building."""
        apdu = build_interrogation_command(
            send_seq=0,
            recv_seq=0,
            common_address=1,
        )

        assert apdu[0] == IEC104_START_BYTE
        # Type ID should be C_IC_NA_1 (100)
        assert apdu[6] == 100

    def test_interrogation_response(self):
        """Test Interrogation response building."""
        apdu = build_interrogation_response(
            send_seq=0,
            recv_seq=1,
            common_address=1,
        )

        assert apdu[0] == IEC104_START_BYTE

    def test_single_point_info(self):
        """Test Single-point information building."""
        values = [(1, True), (2, False), (3, True)]
        apdu = build_single_point_info(
            send_seq=1,
            recv_seq=1,
            common_address=1,
            values=values,
            cot=COT_SPONTANEOUS,
        )

        assert apdu[0] == IEC104_START_BYTE
        # Type ID should be M_SP_NA_1 (1)
        assert apdu[6] == 1
        # Number of objects should be 3
        assert (apdu[7] & 0x7F) == 3

    def test_measured_value_float(self):
        """Test Measured value float building."""
        values = [(101, 23.5), (102, 45.7)]
        apdu = build_measured_value_float(
            send_seq=2,
            recv_seq=2,
            common_address=1,
            values=values,
        )

        assert apdu[0] == IEC104_START_BYTE
        # Type ID should be M_ME_NC_1 (13)
        assert apdu[6] == 13

    def test_measured_value_scaled(self):
        """Test Measured value scaled building."""
        values = [(201, 1000), (202, -500)]
        apdu = build_measured_value_scaled(
            send_seq=3,
            recv_seq=3,
            common_address=1,
            values=values,
        )

        assert apdu[0] == IEC104_START_BYTE
        # Type ID should be M_ME_NB_1 (11)
        assert apdu[6] == 11

    def test_single_command(self):
        """Test Single command building."""
        apdu = build_single_command(
            send_seq=4,
            recv_seq=4,
            common_address=1,
            ioa=1001,
            value=True,
            select=False,
        )

        assert apdu[0] == IEC104_START_BYTE
        # Type ID should be C_SC_NA_1 (45)
        assert apdu[6] == 45


class TestIec104Engine:
    """Test IEC 104 engine."""

    @pytest.fixture
    def engine(self) -> Iec104Engine:
        """Create IEC 104 engine instance."""
        return Iec104Engine()

    @pytest.fixture
    def flow_context(self) -> FlowContext:
        """Create test flow context."""
        src = DeviceContext(
            device_id="controlling",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=50000,
        )
        dst = DeviceContext(
            device_id="controlled",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=IEC104_PORT,
        )
        return FlowContext(
            flow_id="iec104-flow-1",
            source=src,
            destination=dst,
            protocol=ProtocolType.IEC_104,
            config={
                "common_address": 1,
                "general_interrogation": True,
                "data_type": "measured_float",
                "point_count": 4,
                "base_ioa": 101,
            },
            timing_model={
                "response_delay_ms": 20,
            },
        )

    def test_create_initial_state(self, engine: Iec104Engine, flow_context: FlowContext):
        """Test initial state creation."""
        state = engine.create_initial_state(flow_context)

        assert state.flow_id == flow_context.flow_id
        assert state.state_name == "stopped"
        assert state.custom_data["send_seq"] == 0
        assert state.custom_data["recv_seq"] == 0
        assert state.custom_data["common_address"] == 1

    def test_generate_startup_sequence(self, engine: Iec104Engine, flow_context: FlowContext):
        """Test startup sequence with STARTDT + GI."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Should have: TCP(3) + STARTDT(2) + GI request/con + data + end
        assert len(events) >= 7

        # Check TCP handshake
        assert events[0].metadata["type"] == "tcp_syn"
        assert events[1].metadata["type"] == "tcp_syn_ack"
        assert events[2].metadata["type"] == "tcp_ack"

        # Check STARTDT
        assert events[3].metadata["type"] == "iec104_startdt_act"
        assert events[4].metadata["type"] == "iec104_startdt_con"

        # Check GI
        assert events[5].metadata["type"] == "iec104_gi_request"

        assert state.state_name == "started"

    def test_generate_startup_skip_gi(self, engine: Iec104Engine, flow_context: FlowContext):
        """Test startup without general interrogation."""
        flow_context.config["general_interrogation"] = False
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Should have only TCP(3) + STARTDT(2)
        assert len(events) == 5
        event_types = [e.metadata["type"] for e in events]
        assert "iec104_gi_request" not in event_types

    def test_generate_poll_cycle(self, engine: Iec104Engine, flow_context: FlowContext):
        """Test spontaneous data transmission cycle."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "started"

        events = list(engine.generate_poll_cycle(flow_context, state, 100.0))

        # Should generate data + S-format ack
        assert len(events) == 2

        assert events[0].direction == "response"
        assert "spontaneous" in events[0].metadata["type"]
        assert events[0].metadata["point_count"] == 4

        assert events[1].direction == "request"
        assert events[1].metadata["type"] == "iec104_s_format"

    def test_generate_poll_cycle_different_types(self, engine: Iec104Engine, flow_context: FlowContext):
        """Test different data types in poll cycle."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "started"

        # Test single point
        flow_context.config["data_type"] = "single_point"
        events_sp = list(engine.generate_poll_cycle(flow_context, state, 100.0))
        assert "sp" in events_sp[0].metadata["type"]

        # Test measured scaled
        flow_context.config["data_type"] = "measured_scaled"
        events_scaled = list(engine.generate_poll_cycle(flow_context, state, 200.0))
        assert "scaled" in events_scaled[0].metadata["type"]

    def test_generate_shutdown_sequence(self, engine: Iec104Engine, flow_context: FlowContext):
        """Test shutdown sequence with STOPDT + TCP FIN."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "started"

        events = list(engine.generate_shutdown_sequence(flow_context, state, 1000.0))

        # Should generate STOPDT(2) + TCP FIN(3)
        assert len(events) == 5

        assert events[0].metadata["type"] == "iec104_stopdt_act"
        assert events[1].metadata["type"] == "iec104_stopdt_con"
        assert events[2].metadata["type"] == "tcp_fin"
        assert events[3].metadata["type"] == "tcp_fin_ack"
        assert events[4].metadata["type"] == "tcp_ack"

        assert state.state_name == "stopped"

    def test_validate_config_valid(self, engine: Iec104Engine):
        """Test config validation with valid config."""
        config = {
            "common_address": 1,
            "data_type": "measured_float",
            "point_count": 10,
            "base_ioa": 101,
        }
        errors = engine.validate_config(config)
        assert len(errors) == 0

    def test_validate_config_invalid_common_address(self, engine: Iec104Engine):
        """Test config validation with invalid common address."""
        config = {
            "common_address": 70000,  # Max is 65534
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("common_address" in e for e in errors)

    def test_validate_config_invalid_data_type(self, engine: Iec104Engine):
        """Test config validation with invalid data type."""
        config = {
            "data_type": "invalid_type",
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("data_type" in e for e in errors)

    def test_validate_config_invalid_point_count(self, engine: Iec104Engine):
        """Test config validation with invalid point count."""
        config = {
            "point_count": 200,  # Max is 127
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("point_count" in e for e in errors)

    def test_validate_config_invalid_base_ioa(self, engine: Iec104Engine):
        """Test config validation with invalid base IOA."""
        config = {
            "base_ioa": 20000000,  # Max is 16777215
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("base_ioa" in e for e in errors)
