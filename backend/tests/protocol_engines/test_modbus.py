# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for Modbus TCP protocol engine."""

import pytest

from app.protocol_engines import get_engine, list_supported_protocols
from app.protocol_engines.types import (
    DeviceContext,
    FlowContext,
    ProtocolType,
)
from app.protocol_engines.modbus.engine import ModbusTcpEngine
from app.protocol_engines.modbus.function_codes import (
    FUNCTION_CODE_HANDLERS,
    get_handler,
    FC03ReadHoldingRegisters,
    FC06WriteSingleRegister,
)
from app.protocol_engines.modbus.packets import (
    build_mbap_header,
    build_tcp_packet,
)


class TestModbusEngineRegistry:
    """Test Modbus engine registration."""

    def test_modbus_registered(self):
        """Test that Modbus TCP engine is registered."""
        protocols = list_supported_protocols()
        assert ProtocolType.MODBUS_TCP in protocols

    def test_get_modbus_engine(self):
        """Test getting Modbus engine instance."""
        engine = get_engine(ProtocolType.MODBUS_TCP)
        assert isinstance(engine, ModbusTcpEngine)
        assert engine.protocol_type == ProtocolType.MODBUS_TCP


class TestModbusFunctionCodes:
    """Test Modbus function code handlers."""

    def test_fc03_read_holding_registers_request(self):
        """Test FC03 request building."""
        handler = get_handler(0x03)
        assert isinstance(handler, FC03ReadHoldingRegisters)

        config = {
            "start_address": 100,
            "quantity": 10,
        }
        request = handler.build_request(config)

        # FC03 request: FC(1) + Start Address(2) + Quantity(2) = 5 bytes
        assert len(request) == 5
        assert request[0] == 0x03  # Function code
        assert request[1:3] == b'\x00\x64'  # Start address 100
        assert request[3:5] == b'\x00\x0A'  # Quantity 10

    def test_fc03_read_holding_registers_response(self):
        """Test FC03 response building."""
        handler = get_handler(0x03)

        config = {"quantity": 5}
        payload = {"values": [100, 200, 300, 400, 500]}
        response = handler.build_response(config, payload)

        # FC03 response: FC(1) + Byte Count(1) + Data(quantity*2)
        assert len(response) == 2 + 5 * 2
        assert response[0] == 0x03  # Function code
        assert response[1] == 10  # Byte count (5 registers * 2 bytes)

    def test_fc06_write_single_register_request(self):
        """Test FC06 request building."""
        handler = get_handler(0x06)
        assert isinstance(handler, FC06WriteSingleRegister)

        config = {
            "address": 50,
            "value": 0x1234,
        }
        request = handler.build_request(config)

        # FC06 request: FC(1) + Address(2) + Value(2) = 5 bytes
        assert len(request) == 5
        assert request[0] == 0x06  # Function code
        assert request[1:3] == b'\x00\x32'  # Address 50
        assert request[3:5] == b'\x12\x34'  # Value

    def test_all_function_codes_registered(self):
        """Test that all expected function codes are registered."""
        expected_codes = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x0F, 0x10]
        for code in expected_codes:
            assert code in FUNCTION_CODE_HANDLERS, f"FC {code:02X} not registered"


class TestModbusPackets:
    """Test Modbus packet building."""

    def test_mbap_header(self):
        """Test MBAP header building."""
        header = build_mbap_header(
            transaction_id=0x1234,
            unit_id=1,
            pdu_length=5,
        )

        # MBAP: Transaction ID(2) + Protocol ID(2) + Length(2) + Unit ID(1) = 7 bytes
        assert len(header) == 7
        assert header[0:2] == b'\x12\x34'  # Transaction ID
        assert header[2:4] == b'\x00\x00'  # Protocol ID (Modbus = 0)
        assert header[4:6] == b'\x00\x06'  # Length (PDU + Unit ID)
        assert header[6] == 0x01  # Unit ID

    def test_tcp_packet_structure(self):
        """Test TCP packet building."""
        src = DeviceContext(
            device_id="plc1",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=50000,
        )
        dst = DeviceContext(
            device_id="hmi1",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=502,
        )

        payload = b'\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00\x0A'
        packet = build_tcp_packet(src, dst, payload, seq=1000, ack=2000, flags="PA")

        # Packet should have Ethernet(14) + IP(20) + TCP(20) + payload
        assert len(packet) >= 54 + len(payload)


class TestModbusEngine:
    """Test Modbus TCP engine."""

    @pytest.fixture
    def engine(self) -> ModbusTcpEngine:
        """Create Modbus engine instance."""
        return ModbusTcpEngine()

    @pytest.fixture
    def flow_context(self) -> FlowContext:
        """Create test flow context."""
        src = DeviceContext(
            device_id="controller",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=50000,
            unit_id=1,
        )
        dst = DeviceContext(
            device_id="plc",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=502,
            unit_id=1,
        )
        return FlowContext(
            flow_id="test-flow-1",
            source=src,
            destination=dst,
            protocol=ProtocolType.MODBUS_TCP,
            config={
                "function_code": 3,
                "start_address": 0,
                "quantity": 10,
            },
            timing_model={
                "poll_interval_ms": 1000,
                "response_delay_ms": 5,
            },
        )

    def test_create_initial_state(self, engine: ModbusTcpEngine, flow_context: FlowContext):
        """Test initial state creation."""
        state = engine.create_initial_state(flow_context)

        assert state.flow_id == flow_context.flow_id
        assert state.state_name == "idle"
        assert 1 <= state.transaction_id <= 65535
        # TCP sequence numbers live on the typed ModbusConversationState
        # (not custom_data) and are seeded in the valid randint range.
        assert 100_000_000 <= state.tcp_seq_client <= 4_000_000_000
        assert 100_000_000 <= state.tcp_seq_server <= 4_000_000_000

    def test_generate_startup_sequence(self, engine: ModbusTcpEngine, flow_context: FlowContext):
        """Test TCP handshake + Modbus MEI device-ID discovery generation."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # SYN, SYN-ACK, ACK, then a Modbus Encapsulated Interface (FC43)
        # Read Device Identification request/response — the latter two are
        # what Cyber Vision uses to fingerprint the device at startup.
        assert len(events) == 5

        # Check event types
        assert events[0].metadata["type"] == "tcp_syn"
        assert events[1].metadata["type"] == "tcp_syn_ack"
        assert events[2].metadata["type"] == "tcp_ack"
        assert events[3].metadata["type"] == "modbus_mei_request"
        assert events[4].metadata["type"] == "modbus_mei_response"

        # Check timing order
        assert events[0].timestamp_ms < events[1].timestamp_ms
        assert events[1].timestamp_ms < events[2].timestamp_ms

    def test_generate_poll_cycle(self, engine: ModbusTcpEngine, flow_context: FlowContext):
        """Test Modbus request/response generation."""
        state = engine.create_initial_state(flow_context)
        # Initialize TCP state (simulating completed handshake)
        state.custom_data["tcp_seq_client"] = 1000
        state.custom_data["tcp_seq_server"] = 2000
        state.custom_data["tcp_ack_server"] = 1000
        state.custom_data["tcp_ack_client"] = 2000

        initial_transaction_id = state.transaction_id
        events = list(engine.generate_poll_cycle(flow_context, state, 100.0))

        # Should generate request and response
        assert len(events) == 2

        # Check request
        assert events[0].direction == "request"
        assert events[0].metadata["type"] == "modbus_request"
        assert events[0].metadata["function_code"] == 3
        assert events[0].metadata["transaction_id"] == initial_transaction_id

        # Check response
        assert events[1].direction == "response"
        assert events[1].metadata["type"] == "modbus_response"
        assert events[1].timestamp_ms > events[0].timestamp_ms

        # Transaction ID should be incremented
        assert state.transaction_id == (initial_transaction_id + 1) % 65536

    def test_generate_shutdown_sequence(self, engine: ModbusTcpEngine, flow_context: FlowContext):
        """Test TCP FIN handshake generation."""
        state = engine.create_initial_state(flow_context)
        state.custom_data["tcp_seq_client"] = 1000
        state.custom_data["tcp_seq_server"] = 2000

        events = list(engine.generate_shutdown_sequence(flow_context, state, 1000.0))

        # Should generate FIN, FIN-ACK, ACK
        assert len(events) == 3

        assert events[0].metadata["type"] == "tcp_fin"
        assert events[1].metadata["type"] == "tcp_fin_ack"
        assert events[2].metadata["type"] == "tcp_ack"

    def test_validate_config_valid(self, engine: ModbusTcpEngine):
        """Test config validation with valid config."""
        config = {
            "function_code": 3,
            "start_address": 0,
            "quantity": 10,
        }
        errors = engine.validate_config(config)
        assert len(errors) == 0

    def test_validate_config_missing_function_code(self, engine: ModbusTcpEngine):
        """Test config validation with missing function code."""
        config = {
            "start_address": 0,
            "quantity": 10,
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("function_code" in e for e in errors)

    def test_validate_config_invalid_quantity(self, engine: ModbusTcpEngine):
        """Test config validation with invalid quantity."""
        config = {
            "function_code": 3,
            "start_address": 0,
            "quantity": 200,  # Max is 125
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("quantity" in e for e in errors)

    def test_validate_config_unsupported_function_code(self, engine: ModbusTcpEngine):
        """Test config validation with unsupported function code."""
        config = {
            "function_code": 99,  # Invalid
            "start_address": 0,
            "quantity": 10,
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("Unsupported" in e for e in errors)
