# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for DNP3 protocol engine."""

import pytest

from app.protocol_engines import get_engine, list_supported_protocols
from app.protocol_engines.types import (
    DeviceContext,
    FlowContext,
    ProtocolType,
)
from app.protocol_engines.dnp3.engine import Dnp3Engine
from app.protocol_engines.dnp3.packets import (
    DNP3_PORT,
    DNP3_START_BYTES,
    GROUP_ANALOG_INPUT,
    GROUP_BINARY_INPUT,
    GROUP_COUNTER,
    build_data_link_frame,
    build_read_request,
    build_read_response,
    build_write_request,
    build_write_response,
    calculate_crc,
)


class TestDnp3EngineRegistry:
    """Test DNP3 engine registration."""

    def test_dnp3_registered(self):
        """Test that DNP3 engine is registered."""
        protocols = list_supported_protocols()
        assert ProtocolType.DNP3 in protocols

    def test_get_dnp3_engine(self):
        """Test getting DNP3 engine instance."""
        engine = get_engine(ProtocolType.DNP3)
        assert isinstance(engine, Dnp3Engine)
        assert engine.protocol_type == ProtocolType.DNP3


class TestDnp3Packets:
    """Test DNP3 packet building."""

    def test_crc_calculation(self):
        """Test DNP3 CRC calculation."""
        # Known test vector
        data = bytes([0x05, 0xC0, 0x01, 0x00, 0x00, 0x00])
        crc = calculate_crc(data)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_data_link_frame(self):
        """Test data link frame building."""
        frame = build_data_link_frame(
            destination=10,
            source=1,
            control=0xC4,
            payload=bytes([0x01, 0x02, 0x03, 0x04]),
        )

        # Should start with start bytes
        assert frame[0:2] == DNP3_START_BYTES
        # Length field
        assert frame[2] == 5 + 4  # control + dest + src + payload

    def test_read_request(self):
        """Test Read request building."""
        request = build_read_request(
            destination=10,
            source=1,
            objects=[(GROUP_ANALOG_INPUT, 0), (GROUP_BINARY_INPUT, 0)],
            sequence=0,
        )

        assert request[0:2] == DNP3_START_BYTES

    def test_read_response(self):
        """Test Read response building."""
        response = build_read_response(
            destination=1,
            source=10,
            objects=[
                (GROUP_BINARY_INPUT, 1, [True, False, True]),
                (GROUP_ANALOG_INPUT, 5, [10.5, 20.3, 30.1]),
            ],
            sequence=0,
        )

        assert response[0:2] == DNP3_START_BYTES

    def test_write_request(self):
        """Test Write request building."""
        request = build_write_request(
            destination=10,
            source=1,
            group=40,  # Analog output
            variation=1,
            values=[100, 200],
            sequence=1,
        )

        assert request[0:2] == DNP3_START_BYTES

    def test_write_response(self):
        """Test Write response building."""
        response = build_write_response(
            destination=1,
            source=10,
            success=True,
            sequence=1,
        )

        assert response[0:2] == DNP3_START_BYTES


class TestDnp3Engine:
    """Test DNP3 engine."""

    @pytest.fixture
    def engine(self) -> Dnp3Engine:
        """Create DNP3 engine instance."""
        return Dnp3Engine()

    @pytest.fixture
    def flow_context(self) -> FlowContext:
        """Create test flow context."""
        src = DeviceContext(
            device_id="master",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=50000,
        )
        dst = DeviceContext(
            device_id="outstation",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=DNP3_PORT,
        )
        return FlowContext(
            flow_id="dnp3-flow-1",
            source=src,
            destination=dst,
            protocol=ProtocolType.DNP3,
            config={
                "master_address": 1,
                "outstation_address": 10,
                "poll_type": "event",
                "integrity_poll": True,
            },
            timing_model={
                "response_delay_ms": 50,
            },
        )

    def test_create_initial_state(self, engine: Dnp3Engine, flow_context: FlowContext):
        """Test initial state creation."""
        state = engine.create_initial_state(flow_context)

        assert state.flow_id == flow_context.flow_id
        assert state.state_name == "idle"
        assert state.custom_data["master_address"] == 1
        assert state.custom_data["outstation_address"] == 10
        assert state.custom_data["app_sequence"] == 0

    def test_generate_startup_sequence(self, engine: Dnp3Engine, flow_context: FlowContext):
        """Test startup sequence with TCP handshake + integrity poll."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Should have: TCP(3) + Integrity poll request/response = 5
        assert len(events) >= 5

        # Check TCP handshake
        assert events[0].metadata["type"] == "tcp_syn"
        assert events[1].metadata["type"] == "tcp_syn_ack"
        assert events[2].metadata["type"] == "tcp_ack"

        # Check integrity poll
        assert events[3].metadata["type"] == "dnp3_integrity_poll"
        assert events[4].metadata["type"] == "dnp3_integrity_response"

        assert state.state_name == "connected"

    def test_generate_startup_skip_integrity(self, engine: Dnp3Engine, flow_context: FlowContext):
        """Test startup without integrity poll."""
        flow_context.config["integrity_poll"] = False
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Should have only TCP handshake
        assert len(events) == 3
        assert events[0].metadata["type"] == "tcp_syn"

    def test_generate_poll_cycle(self, engine: Dnp3Engine, flow_context: FlowContext):
        """Test poll cycle."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "connected"

        events = list(engine.generate_poll_cycle(flow_context, state, 100.0))

        # Should generate poll request and response
        assert len(events) == 2

        assert events[0].direction == "request"
        assert events[0].metadata["type"] == "dnp3_poll_request"
        assert events[0].metadata["poll_type"] == "event"

        assert events[1].direction == "response"
        assert events[1].metadata["type"] == "dnp3_poll_response"

    def test_generate_poll_cycle_static(self, engine: Dnp3Engine, flow_context: FlowContext):
        """Test static poll cycle."""
        flow_context.config["poll_type"] = "static"
        state = engine.create_initial_state(flow_context)
        state.state_name = "connected"

        events = list(engine.generate_poll_cycle(flow_context, state, 100.0))

        assert events[0].metadata["poll_type"] == "static"

    def test_generate_shutdown_sequence(self, engine: Dnp3Engine, flow_context: FlowContext):
        """Test shutdown sequence."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "connected"

        events = list(engine.generate_shutdown_sequence(flow_context, state, 1000.0))

        # Should generate TCP FIN handshake
        assert len(events) == 3
        assert events[0].metadata["type"] == "tcp_fin"
        assert events[1].metadata["type"] == "tcp_fin_ack"
        assert events[2].metadata["type"] == "tcp_ack"

        assert state.state_name == "idle"

    def test_validate_config_valid(self, engine: Dnp3Engine):
        """Test config validation with valid config."""
        config = {
            "master_address": 1,
            "outstation_address": 10,
            "poll_type": "event",
            "point_count": 10,
        }
        errors = engine.validate_config(config)
        assert len(errors) == 0

    def test_validate_config_invalid_address(self, engine: Dnp3Engine):
        """Test config validation with invalid address."""
        config = {
            "master_address": 70000,  # Max is 65519
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("master_address" in e for e in errors)

    def test_validate_config_invalid_poll_type(self, engine: Dnp3Engine):
        """Test config validation with invalid poll type."""
        config = {
            "poll_type": "invalid",
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("poll_type" in e for e in errors)
