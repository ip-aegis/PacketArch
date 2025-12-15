"""Unit tests for EtherNet/IP protocol engine."""

import pytest

from app.protocol_engines import get_engine, list_supported_protocols
from app.protocol_engines.types import (
    DeviceContext,
    FlowContext,
    ProtocolType,
)
from app.protocol_engines.ethernet_ip.engine import EtherNetIPEngine
from app.protocol_engines.ethernet_ip.packets import (
    build_register_session_request,
    build_register_session_response,
    build_cip_forward_open_request,
    build_cip_forward_open_response,
    build_cip_io_data,
    build_enip_packet,
)


class TestEtherNetIPEngineRegistry:
    """Test EtherNet/IP engine registration."""

    def test_ethernet_ip_registered(self):
        """Test that EtherNet/IP engine is registered."""
        protocols = list_supported_protocols()
        assert ProtocolType.ETHERNET_IP in protocols

    def test_get_ethernet_ip_engine(self):
        """Test getting EtherNet/IP engine instance."""
        engine = get_engine(ProtocolType.ETHERNET_IP)
        assert isinstance(engine, EtherNetIPEngine)
        assert engine.protocol_type == ProtocolType.ETHERNET_IP


class TestEtherNetIPPackets:
    """Test EtherNet/IP packet building."""

    def test_register_session_request(self):
        """Test RegisterSession request building."""
        request = build_register_session_request()

        # EtherNet/IP encapsulation header (24 bytes) + command data
        assert len(request) >= 24

        # Command should be RegisterSession (0x0065)
        assert request[0:2] == b'\x65\x00'

    def test_register_session_response(self):
        """Test RegisterSession response building."""
        session_handle = 0x12345678
        response = build_register_session_response(session_handle)

        # Should contain session handle in the response
        assert len(response) >= 24

        # Command should be RegisterSession (0x0065)
        assert response[0:2] == b'\x65\x00'

    def test_forward_open_request(self):
        """Test ForwardOpen request building."""
        request = build_cip_forward_open_request()

        # Should be a valid CIP encapsulated request
        assert len(request) > 24

    def test_forward_open_response_success(self):
        """Test successful ForwardOpen response."""
        response = build_cip_forward_open_response(success=True)

        assert len(response) > 0

    def test_forward_open_response_failure(self):
        """Test failed ForwardOpen response."""
        response = build_cip_forward_open_response(success=False)

        assert len(response) > 0

    def test_cip_io_data(self):
        """Test CIP I/O data building."""
        test_data = bytes([0x01, 0x02, 0x03, 0x04])
        io_packet = build_cip_io_data(test_data)

        # Should contain the data
        assert len(io_packet) > len(test_data)

    def test_enip_packet_complete(self):
        """Test complete EtherNet/IP packet building."""
        src = DeviceContext(
            device_id="plc",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=50000,
        )
        dst = DeviceContext(
            device_id="scada",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=44818,
        )

        payload = build_register_session_request()
        packet = build_enip_packet(src, dst, payload, seq=1000, ack=2000, flags="PA")

        # Packet should have Ethernet(14) + IP(20) + TCP(20) + payload
        assert len(packet) >= 54 + len(payload)


class TestEtherNetIPEngine:
    """Test EtherNet/IP engine."""

    @pytest.fixture
    def engine(self) -> EtherNetIPEngine:
        """Create EtherNet/IP engine instance."""
        return EtherNetIPEngine()

    @pytest.fixture
    def flow_context(self) -> FlowContext:
        """Create test flow context."""
        src = DeviceContext(
            device_id="scanner",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=50000,
        )
        dst = DeviceContext(
            device_id="adapter",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=44818,
        )
        return FlowContext(
            flow_id="enip-flow-1",
            source=src,
            destination=dst,
            protocol=ProtocolType.ETHERNET_IP,
            config={
                "io_data_size": 8,
                "use_forward_open": True,
            },
            timing_model={
                "response_delay_ms": 5,
            },
        )

    def test_create_initial_state(self, engine: EtherNetIPEngine, flow_context: FlowContext):
        """Test initial state creation."""
        state = engine.create_initial_state(flow_context)

        assert state.flow_id == flow_context.flow_id
        assert state.state_name == "unconnected"
        assert "tcp_seq_client" in state.custom_data
        assert "tcp_seq_server" in state.custom_data
        assert "session_handle" in state.custom_data
        assert state.custom_data["session_handle"] == 0

    def test_generate_startup_sequence(self, engine: EtherNetIPEngine, flow_context: FlowContext):
        """Test startup sequence with TCP + RegisterSession + ForwardOpen."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Should have: SYN, SYN-ACK, ACK, RegisterSession req/resp, ForwardOpen req/resp
        assert len(events) >= 5  # At minimum: 3 TCP + 2 RegisterSession

        # Check TCP handshake
        assert events[0].metadata["type"] == "tcp_syn"
        assert events[1].metadata["type"] == "tcp_syn_ack"
        assert events[2].metadata["type"] == "tcp_ack"

        # Check RegisterSession
        assert events[3].metadata["type"] == "enip_register_session_request"
        assert events[4].metadata["type"] == "enip_register_session_response"

        # State should be updated
        assert state.state_name == "io_active"
        assert state.custom_data["session_handle"] != 0

    def test_generate_startup_skip_forward_open(self, engine: EtherNetIPEngine, flow_context: FlowContext):
        """Test startup skipping ForwardOpen."""
        flow_context.config["use_forward_open"] = False
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Should have: SYN, SYN-ACK, ACK, RegisterSession req/resp (no ForwardOpen)
        assert len(events) == 5

        # No ForwardOpen events
        event_types = [e.metadata["type"] for e in events]
        assert "enip_forward_open_request" not in event_types

    def test_generate_poll_cycle(self, engine: EtherNetIPEngine, flow_context: FlowContext):
        """Test I/O data exchange."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "io_active"

        events = list(engine.generate_poll_cycle(flow_context, state, 100.0))

        # Should generate I/O request and response
        assert len(events) == 2

        # Check I/O data
        assert events[0].direction == "request"
        assert events[0].metadata["type"] == "enip_io_data"
        assert events[0].metadata["io_sequence"] == 1

        assert events[1].direction == "response"
        assert events[1].metadata["type"] == "enip_io_data_response"

    def test_generate_poll_cycle_increments_sequence(self, engine: EtherNetIPEngine, flow_context: FlowContext):
        """Test that I/O sequence increments."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "io_active"

        # First cycle
        events1 = list(engine.generate_poll_cycle(flow_context, state, 100.0))
        assert events1[0].metadata["io_sequence"] == 1

        # Second cycle
        events2 = list(engine.generate_poll_cycle(flow_context, state, 200.0))
        assert events2[0].metadata["io_sequence"] == 2

    def test_generate_shutdown_sequence(self, engine: EtherNetIPEngine, flow_context: FlowContext):
        """Test shutdown sequence."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "io_active"
        state.custom_data["tcp_seq_client"] = 5000
        state.custom_data["tcp_seq_server"] = 6000

        events = list(engine.generate_shutdown_sequence(flow_context, state, 1000.0))

        # Should generate FIN, FIN-ACK, ACK
        assert len(events) == 3

        assert events[0].metadata["type"] == "tcp_fin"
        assert events[1].metadata["type"] == "tcp_fin_ack"
        assert events[2].metadata["type"] == "tcp_ack"

        assert state.state_name == "unconnected"

    def test_validate_config_valid(self, engine: EtherNetIPEngine):
        """Test config validation with valid config."""
        config = {
            "io_data_size": 8,
            "use_forward_open": True,
        }
        errors = engine.validate_config(config)
        assert len(errors) == 0

    def test_validate_config_invalid_io_size(self, engine: EtherNetIPEngine):
        """Test config validation with invalid I/O data size."""
        config = {
            "io_data_size": 1000,  # Too large
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("io_data_size" in e for e in errors)

    def test_validate_config_invalid_forward_open(self, engine: EtherNetIPEngine):
        """Test config validation with invalid use_forward_open."""
        config = {
            "use_forward_open": "yes",  # Should be bool
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("use_forward_open" in e for e in errors)
