"""Unit tests for OPC UA protocol engine."""

import pytest

from app.protocol_engines import get_engine, list_supported_protocols
from app.protocol_engines.types import (
    DeviceContext,
    FlowContext,
    ProtocolType,
)
from app.protocol_engines.opc_ua.engine import OpcUaEngine
from app.protocol_engines.opc_ua.packets import (
    OPC_UA_PORT,
    build_hello_message,
    build_acknowledge_message,
    build_open_secure_channel_request,
    build_open_secure_channel_response,
    build_create_session_request,
    build_read_request,
    build_read_response,
    build_opc_ua_header,
    MSG_TYPE_HELLO,
    MSG_TYPE_MESSAGE,
)


class TestOpcUaEngineRegistry:
    """Test OPC UA engine registration."""

    def test_opc_ua_registered(self):
        """Test that OPC UA engine is registered."""
        protocols = list_supported_protocols()
        assert ProtocolType.OPC_UA in protocols

    def test_get_opc_ua_engine(self):
        """Test getting OPC UA engine instance."""
        engine = get_engine(ProtocolType.OPC_UA)
        assert isinstance(engine, OpcUaEngine)
        assert engine.protocol_type == ProtocolType.OPC_UA


class TestOpcUaPackets:
    """Test OPC UA packet building."""

    def test_opc_ua_header(self):
        """Test OPC UA message header building."""
        header = build_opc_ua_header(MSG_TYPE_HELLO, 100)

        assert len(header) == 8
        assert header[0:3] == MSG_TYPE_HELLO
        assert header[3:4] == b"F"  # Final chunk

    def test_hello_message(self):
        """Test Hello message building."""
        hello = build_hello_message(endpoint_url="opc.tcp://localhost:4840")

        # Should start with HEL header
        assert len(hello) >= 8
        assert hello[0:3] == MSG_TYPE_HELLO

    def test_acknowledge_message(self):
        """Test Acknowledge message building."""
        ack = build_acknowledge_message()

        assert len(ack) >= 8
        assert ack[0:3] == b"ACK"

    def test_open_secure_channel_request(self):
        """Test OpenSecureChannel request building."""
        request = build_open_secure_channel_request(request_id=1)

        assert len(request) > 8
        assert request[0:3] == b"OPN"

    def test_open_secure_channel_response(self):
        """Test OpenSecureChannel response building."""
        response = build_open_secure_channel_response(
            security_token_id=1,
            channel_id=1,
            request_id=1,
        )

        assert len(response) > 8
        assert response[0:3] == b"OPN"

    def test_create_session_request(self):
        """Test CreateSession request building."""
        request = build_create_session_request(
            session_name="TestSession",
            request_id=2,
            channel_id=1,
        )

        assert len(request) > 8
        assert request[0:3] == MSG_TYPE_MESSAGE

    def test_read_request(self):
        """Test Read service request building."""
        request = build_read_request(
            node_ids=["ns=2;i=1", "ns=2;s=Temperature"],
            request_id=3,
            channel_id=1,
        )

        assert len(request) > 8

    def test_read_response(self):
        """Test Read service response building."""
        values = [
            (6, 42),      # Int32
            (11, 23.5),   # Double
            (1, True),    # Boolean
        ]
        response = build_read_response(
            values=values,
            request_id=3,
            channel_id=1,
        )

        assert len(response) > 8


class TestOpcUaEngine:
    """Test OPC UA engine."""

    @pytest.fixture
    def engine(self) -> OpcUaEngine:
        """Create OPC UA engine instance."""
        return OpcUaEngine()

    @pytest.fixture
    def flow_context(self) -> FlowContext:
        """Create test flow context."""
        src = DeviceContext(
            device_id="client",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=50000,
        )
        dst = DeviceContext(
            device_id="server",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=OPC_UA_PORT,
        )
        return FlowContext(
            flow_id="opc-ua-flow-1",
            source=src,
            destination=dst,
            protocol=ProtocolType.OPC_UA,
            config={
                "endpoint_url": "opc.tcp://192.168.1.20:4840",
                "session_name": "TestSession",
                "node_ids": ["ns=2;i=1", "ns=2;i=2"],
            },
            timing_model={
                "response_delay_ms": 10,
            },
        )

    def test_create_initial_state(self, engine: OpcUaEngine, flow_context: FlowContext):
        """Test initial state creation."""
        state = engine.create_initial_state(flow_context)

        assert state.flow_id == flow_context.flow_id
        assert state.state_name == "disconnected"
        assert "tcp_seq_client" in state.custom_data
        assert "channel_id" in state.custom_data
        assert state.custom_data["channel_id"] == 0

    def test_generate_startup_sequence(self, engine: OpcUaEngine, flow_context: FlowContext):
        """Test startup sequence with Hello/Ack + SecureChannel + Session."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Should have: TCP(3) + Hello + Ack + OpenSecureChannel(2) + CreateSession(2) = 9
        assert len(events) >= 9

        # Check TCP handshake
        assert events[0].metadata["type"] == "tcp_syn"
        assert events[1].metadata["type"] == "tcp_syn_ack"
        assert events[2].metadata["type"] == "tcp_ack"

        # Check OPC UA Hello/Ack
        assert events[3].metadata["type"] == "opc_ua_hello"
        assert events[4].metadata["type"] == "opc_ua_acknowledge"

        # Check secure channel
        assert events[5].metadata["type"] == "opc_ua_open_secure_channel_request"
        assert events[6].metadata["type"] == "opc_ua_open_secure_channel_response"

        # State should be updated
        assert state.state_name == "session_active"
        assert state.custom_data["channel_id"] != 0

    def test_generate_poll_cycle(self, engine: OpcUaEngine, flow_context: FlowContext):
        """Test Read request/response cycle."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "session_active"
        state.custom_data["channel_id"] = 1
        state.custom_data["token_id"] = 1
        state.custom_data["request_id"] = 2

        events = list(engine.generate_poll_cycle(flow_context, state, 100.0))

        # Should generate Read request and response
        assert len(events) == 2

        assert events[0].direction == "request"
        assert events[0].metadata["type"] == "opc_ua_read_request"
        assert "node_ids" in events[0].metadata

        assert events[1].direction == "response"
        assert events[1].metadata["type"] == "opc_ua_read_response"

    def test_generate_shutdown_sequence(self, engine: OpcUaEngine, flow_context: FlowContext):
        """Test shutdown sequence."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "session_active"

        events = list(engine.generate_shutdown_sequence(flow_context, state, 1000.0))

        # Should generate TCP FIN handshake
        assert len(events) == 3
        assert events[0].metadata["type"] == "tcp_fin"
        assert events[1].metadata["type"] == "tcp_fin_ack"
        assert events[2].metadata["type"] == "tcp_ack"

        assert state.state_name == "disconnected"

    def test_validate_config_valid(self, engine: OpcUaEngine):
        """Test config validation with valid config."""
        config = {
            "endpoint_url": "opc.tcp://localhost:4840",
            "session_name": "TestSession",
            "node_ids": ["ns=2;i=1"],
        }
        errors = engine.validate_config(config)
        assert len(errors) == 0

    def test_validate_config_invalid_endpoint(self, engine: OpcUaEngine):
        """Test config validation with invalid endpoint URL."""
        config = {
            "endpoint_url": "http://localhost:4840",  # Wrong protocol
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("endpoint_url" in e for e in errors)

    def test_validate_config_invalid_node_id(self, engine: OpcUaEngine):
        """Test config validation with invalid node ID."""
        config = {
            "node_ids": ["invalid-node-id"],
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
