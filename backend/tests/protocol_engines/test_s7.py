"""Unit tests for S7 Communication protocol engine."""

import pytest

from app.protocol_engines import get_engine, list_supported_protocols
from app.protocol_engines.types import (
    ConversationState,
    DeviceContext,
    FlowContext,
    PacketEvent,
    ProtocolType,
)
from app.protocol_engines.s7.engine import S7Engine
from app.protocol_engines.s7.config import (
    S7Area,
    S7ConnectionType,
    S7CPUProfile,
    S7DataReturnCode,
    S7FlowConfig,
    S7Function,
    S7ReadArea,
    S7TransportSize,
    S7WriteArea,
    S7_CPU_PROFILES,
    get_cpu_profile,
)
from app.protocol_engines.s7.packets import (
    TPKTPacket,
    COTPConnectionRequest,
    COTPConnectionConfirm,
    COTPData,
    COTPDisconnectRequest,
    S7Header,
    S7PDUType,
    S7SetupCommunicationRequest,
    S7SetupCommunicationResponse,
    S7ReadVarRequest,
    S7ReadVarResponse,
    S7WriteVarRequest,
    S7WriteVarResponse,
    S7UserdataRequest,
    S7UserdataResponse,
    build_cotp_cr_packet,
    build_cotp_cc_packet,
    build_cotp_dr_packet,
    build_s7_setup_request,
    build_s7_setup_response,
    build_s7_read_request,
    build_s7_read_response,
    build_s7_write_request,
    build_s7_write_response,
    build_s7_szl_request,
    build_s7_szl_response,
)


class TestS7EngineRegistry:
    """Test S7 engine registration."""

    def test_s7_registered(self):
        """Test that S7 engine is registered."""
        protocols = list_supported_protocols()
        assert ProtocolType.S7COMM in protocols

    def test_get_s7_engine(self):
        """Test getting S7 engine instance."""
        engine = get_engine(ProtocolType.S7COMM)
        assert isinstance(engine, S7Engine)
        assert engine.protocol_type == ProtocolType.S7COMM


class TestS7Config:
    """Test S7 configuration data structures."""

    def test_s7_area_values(self):
        """Test S7 area code values."""
        assert S7Area.DB == 0x84
        assert S7Area.INPUTS == 0x81
        assert S7Area.OUTPUTS == 0x82
        assert S7Area.MERKERS == 0x83

    def test_s7_connection_types(self):
        """Test S7 connection type values."""
        assert S7ConnectionType.PG == 0x01
        assert S7ConnectionType.OP == 0x02
        assert S7ConnectionType.S7_BASIC == 0x03

    def test_s7_read_area_defaults(self):
        """Test S7ReadArea default values."""
        area = S7ReadArea()
        assert area.area == S7Area.DB
        assert area.db_number == 1
        assert area.start == 0
        assert area.size == 10
        assert area.transport_size == S7TransportSize.BYTE

    def test_s7_read_area_start_byte(self):
        """Test S7ReadArea byte address calculation."""
        area = S7ReadArea(start=80)  # 80 bits = 10 bytes
        assert area.start_byte == 10
        assert area.start_bit == 0

    def test_s7_read_area_start_bit(self):
        """Test S7ReadArea bit offset calculation."""
        area = S7ReadArea(start=83)  # 83 bits = byte 10, bit 3
        assert area.start_byte == 10
        assert area.start_bit == 3

    def test_s7_write_area_defaults(self):
        """Test S7WriteArea default values."""
        area = S7WriteArea()
        assert area.area == S7Area.DB
        assert area.db_number == 1
        assert area.start == 0
        assert len(area.data) == 10

    def test_s7_flow_config_defaults(self):
        """Test S7FlowConfig default values."""
        config = S7FlowConfig()
        assert config.rack == 0
        assert config.slot == 1
        assert config.pdu_size == 480
        assert config.connection_type == S7ConnectionType.PG
        assert config.poll_read_only is True
        # Default read area should be auto-created
        assert len(config.read_areas) == 1
        assert config.read_areas[0].area == S7Area.DB
        assert config.read_areas[0].db_number == 1

    def test_cpu_profile_exact_match(self):
        """Test CPU profile lookup by exact name."""
        profile = get_cpu_profile("CPU 1214C")
        assert profile is not None
        assert profile.name == "CPU 1214C DC/DC/DC"
        assert profile.max_pdu_size == 240
        assert profile.slot == 1

    def test_cpu_profile_partial_match(self):
        """Test CPU profile lookup by partial name."""
        profile = get_cpu_profile("1516")
        assert profile is not None
        assert "1516" in profile.name

    def test_cpu_profile_not_found(self):
        """Test CPU profile returns None for unknown model."""
        profile = get_cpu_profile("CPU 99999")
        assert profile is None

    def test_cpu_profiles_have_required_fields(self):
        """Test all CPU profiles have required fields."""
        for name, profile in S7_CPU_PROFILES.items():
            assert profile.name, f"Profile {name} missing name"
            assert profile.max_pdu_size > 0, f"Profile {name} has invalid pdu_size"
            assert profile.slot >= 0, f"Profile {name} has invalid slot"
            assert len(profile.response_delay_ms) == 2, f"Profile {name} has invalid delay tuple"
            assert profile.response_delay_ms[0] < profile.response_delay_ms[1]


class TestS7Packets:
    """Test S7 packet building structures."""

    def test_tpkt_packet_build(self):
        """Test TPKT packet building."""
        payload = b"\x01\x02\x03"
        tpkt = TPKTPacket(payload=payload)
        result = tpkt.build()

        # TPKT header: version(1) + reserved(1) + length(2) = 4 bytes + payload
        assert len(result) == 4 + len(payload)
        assert result[0] == 0x03  # Version
        assert result[1] == 0x00  # Reserved
        # Length includes header
        expected_length = 4 + len(payload)
        assert result[2] == (expected_length >> 8) & 0xFF
        assert result[3] == expected_length & 0xFF
        assert result[4:] == payload

    def test_tpkt_parse_header(self):
        """Test TPKT header parsing."""
        data = b"\x03\x00\x00\x0A"  # Version 3, length 10
        version, length = TPKTPacket.parse_header(data)
        assert version == 3
        assert length == 10

    def test_tpkt_parse_header_too_short(self):
        """Test TPKT header parsing with insufficient data."""
        with pytest.raises(ValueError, match="too short"):
            TPKTPacket.parse_header(b"\x03\x00")

    def test_cotp_cr_build(self):
        """Test COTP Connection Request building."""
        cr = COTPConnectionRequest.for_s7(rack=0, slot=1, connection_type=S7ConnectionType.PG)
        result = cr.build()

        # CR PDU should start with length indicator, then CR type (0xE0)
        assert result[1] == 0xE0  # CR PDU type

    def test_cotp_cc_build(self):
        """Test COTP Connection Confirm building."""
        cc = COTPConnectionConfirm(dst_ref=0x0001, src_ref=0x0002)
        result = cc.build()

        assert result[1] == 0xD0  # CC PDU type

    def test_cotp_data_build(self):
        """Test COTP Data Transfer building."""
        payload = b"\x32\x01\x00\x00"  # Some S7 data
        dt = COTPData(payload=payload, last=True)
        result = dt.build()

        assert result[0] == 0x02  # Length indicator
        assert result[1] == 0xF0  # DT PDU type
        assert result[2] & 0x80 == 0x80  # EOT flag set (last=True)
        assert result[3:] == payload

    def test_cotp_dr_build(self):
        """Test COTP Disconnect Request building."""
        dr = COTPDisconnectRequest(dst_ref=0x0001, src_ref=0x0002, reason=0x00)
        result = dr.build()

        assert result[0] == 0x06  # Length indicator
        assert result[1] == 0x80  # DR PDU type

    def test_s7_header_job(self):
        """Test S7 header building for JOB PDU type."""
        header = S7Header(
            pdu_type=S7PDUType.JOB,
            pdu_ref=0x0001,
            param_length=8,
            data_length=0,
        )
        result = header.build()

        assert result[0] == 0x32  # Protocol ID
        assert result[1] == S7PDUType.JOB
        # No error fields for JOB type
        assert len(result) == 10  # 1+1+2+2+2+2

    def test_s7_header_ack_data(self):
        """Test S7 header building for ACK_DATA includes error fields."""
        header = S7Header(
            pdu_type=S7PDUType.ACK_DATA,
            pdu_ref=0x0001,
            param_length=2,
            data_length=10,
            error_class=0,
            error_code=0,
        )
        result = header.build()

        assert result[0] == 0x32
        assert result[1] == S7PDUType.ACK_DATA
        # ACK_DATA has 2 additional error bytes
        assert len(result) == 12  # 10 + 2

    def test_build_cotp_cr_packet(self):
        """Test complete COTP CR packet with TPKT wrapper."""
        packet = build_cotp_cr_packet(rack=0, slot=1)

        # Should be TPKT + COTP CR
        assert packet[0] == 0x03  # TPKT version
        assert len(packet) > 4  # At least TPKT header

    def test_build_cotp_cc_packet(self):
        """Test complete COTP CC packet with TPKT wrapper."""
        packet = build_cotp_cc_packet(dst_ref=1, src_ref=2)

        assert packet[0] == 0x03  # TPKT version

    def test_build_cotp_dr_packet(self):
        """Test complete COTP DR packet with TPKT wrapper."""
        packet = build_cotp_dr_packet(dst_ref=0, src_ref=1)

        assert packet[0] == 0x03  # TPKT version

    def test_build_s7_setup_request(self):
        """Test complete S7 Setup Communication request packet."""
        packet = build_s7_setup_request(pdu_ref=0, pdu_size=480)

        assert packet[0] == 0x03  # TPKT version
        # Should contain S7 protocol ID
        assert b"\x32" in packet

    def test_build_s7_setup_response(self):
        """Test complete S7 Setup Communication response packet."""
        packet = build_s7_setup_response(pdu_ref=0, pdu_size=240)

        assert packet[0] == 0x03  # TPKT version

    def test_build_s7_read_request(self):
        """Test S7 Read Variable request packet."""
        read_areas = [
            S7ReadArea(area=S7Area.DB, db_number=1, start=0, size=10),
        ]
        packet = build_s7_read_request(pdu_ref=1, read_areas=read_areas)

        assert packet[0] == 0x03  # TPKT
        assert len(packet) > 20  # Non-trivial packet

    def test_build_s7_read_response(self):
        """Test S7 Read Variable response packet."""
        items = [(S7DataReturnCode.SUCCESS, b"\x01\x02\x03\x04\x05")]
        packet = build_s7_read_response(pdu_ref=1, items=items)

        assert packet[0] == 0x03  # TPKT

    def test_build_s7_write_request(self):
        """Test S7 Write Variable request packet."""
        write_areas = [
            S7WriteArea(area=S7Area.DB, db_number=1, start=0, data=b"\x01\x02"),
        ]
        packet = build_s7_write_request(pdu_ref=2, write_areas=write_areas)

        assert packet[0] == 0x03

    def test_build_s7_write_response(self):
        """Test S7 Write Variable response packet."""
        return_codes = [S7DataReturnCode.SUCCESS]
        packet = build_s7_write_response(pdu_ref=2, return_codes=return_codes)

        assert packet[0] == 0x03

    def test_build_s7_szl_request(self):
        """Test S7 SZL read request packet."""
        packet = build_s7_szl_request(pdu_ref=3, szl_id=0x0011, szl_index=0x0000)

        assert packet[0] == 0x03
        assert len(packet) > 20

    def test_build_s7_szl_response(self):
        """Test S7 SZL read response packet."""
        szl_data = b"\x00" * 34  # Dummy SZL data
        packet = build_s7_szl_response(
            pdu_ref=3, szl_id=0x0011, szl_index=0x0000, szl_data=szl_data
        )

        assert packet[0] == 0x03
        assert len(packet) > 30


class TestS7Engine:
    """Test S7 engine."""

    @pytest.fixture
    def engine(self) -> S7Engine:
        """Create S7 engine instance."""
        return S7Engine()

    @pytest.fixture
    def flow_context(self) -> FlowContext:
        """Create test flow context."""
        src = DeviceContext(
            device_id="hmi",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=50000,
        )
        dst = DeviceContext(
            device_id="plc",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=102,
        )
        return FlowContext(
            flow_id="s7-flow-1",
            source=src,
            destination=dst,
            protocol=ProtocolType.S7COMM,
            config={
                "rack": 0,
                "slot": 1,
                "pdu_size": 480,
                "read_areas": [
                    {"area": S7Area.DB, "db_number": 1, "start": 0, "size": 10}
                ],
            },
            timing_model={
                "response_delay_ms": 5,
            },
        )

    def test_create_initial_state(self, engine: S7Engine, flow_context: FlowContext):
        """Test initial state creation."""
        state = engine.create_initial_state(flow_context)

        assert state.flow_id == flow_context.flow_id
        assert state.state_name == "idle"
        assert state.transaction_id == 0
        assert "tcp_seq_client" in state.custom_data
        assert "tcp_seq_server" in state.custom_data
        assert "cotp_src_ref" in state.custom_data
        assert "pdu_ref" in state.custom_data
        assert state.custom_data["pdu_ref"] == 0
        assert state.custom_data["negotiated_pdu_size"] == 480
        # Check TCP sequence numbers are in valid range
        assert 100_000_000 <= state.custom_data["tcp_seq_client"] <= 4_000_000_000
        assert 100_000_000 <= state.custom_data["tcp_seq_server"] <= 4_000_000_000

    def test_generate_startup_sequence(self, engine: S7Engine, flow_context: FlowContext):
        """Test startup sequence: TCP handshake + COTP CR/CC + S7 setup."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Expect: 3 TCP + 2 COTP + 2 S7 Setup = 7 events
        assert len(events) == 7

        # Check TCP handshake
        assert events[0].metadata["type"] == "tcp_syn"
        assert events[0].metadata["phase"] == "tcp_handshake"
        assert events[1].metadata["type"] == "tcp_syn_ack"
        assert events[2].metadata["type"] == "tcp_ack"

        # Check COTP connection
        assert events[3].metadata["type"] == "cotp_cr"
        assert events[3].metadata["phase"] == "cotp_connect"
        assert events[4].metadata["type"] == "cotp_cc"

        # Check S7 setup
        assert events[5].metadata["type"] == "s7_setup_req"
        assert events[5].metadata["phase"] == "s7_setup"
        assert events[6].metadata["type"] == "s7_setup_resp"
        assert "pdu_size" in events[6].metadata

        # Verify timing order
        for i in range(1, len(events)):
            assert events[i].timestamp_ms >= events[i - 1].timestamp_ms

        # State should be updated
        assert state.state_name == "connected"
        assert state.custom_data["pdu_ref"] == 1

    def test_generate_poll_cycle_read(self, engine: S7Engine, flow_context: FlowContext):
        """Test read poll cycle generation."""
        state = engine.create_initial_state(flow_context)
        # Simulate completed startup
        state.state_name = "connected"
        state.custom_data["tcp_seq_client"] = 5000
        state.custom_data["tcp_seq_server"] = 6000
        state.custom_data["pdu_ref"] = 1

        events = list(engine.generate_poll_cycle(flow_context, state, 100.0))

        # Should generate read request and response
        assert len(events) == 2

        # Check read request
        assert events[0].direction == "request"
        assert events[0].metadata["type"] == "s7_read_req"
        assert events[0].metadata["pdu_ref"] == 1

        # Check read response
        assert events[1].direction == "response"
        assert events[1].metadata["type"] == "s7_read_resp"
        assert events[1].timestamp_ms > events[0].timestamp_ms

        # PDU ref should be incremented
        assert state.custom_data["pdu_ref"] == 2

    def test_generate_poll_cycle_with_write(self, engine: S7Engine, flow_context: FlowContext):
        """Test poll cycle with both read and write operations."""
        flow_context.config["poll_read_only"] = False
        flow_context.config["write_areas"] = [
            {"area": S7Area.DB, "db_number": 1, "start": 0, "data": [0, 1, 2, 3]}
        ]
        state = engine.create_initial_state(flow_context)
        state.state_name = "connected"
        state.custom_data["tcp_seq_client"] = 5000
        state.custom_data["tcp_seq_server"] = 6000
        state.custom_data["pdu_ref"] = 1

        events = list(engine.generate_poll_cycle(flow_context, state, 100.0))

        # Should generate: read req + read resp + write req + write resp = 4
        assert len(events) == 4

        assert events[0].metadata["type"] == "s7_read_req"
        assert events[1].metadata["type"] == "s7_read_resp"
        assert events[2].metadata["type"] == "s7_write_req"
        assert events[3].metadata["type"] == "s7_write_resp"

        # PDU ref incremented twice (once for read, once for write)
        assert state.custom_data["pdu_ref"] == 3

    def test_generate_shutdown_sequence(self, engine: S7Engine, flow_context: FlowContext):
        """Test shutdown sequence: COTP DR + TCP FIN."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "connected"
        state.custom_data["tcp_seq_client"] = 5000
        state.custom_data["tcp_seq_server"] = 6000
        state.custom_data["cotp_dst_ref"] = 10
        state.custom_data["cotp_src_ref"] = 5

        events = list(engine.generate_shutdown_sequence(flow_context, state, 1000.0))

        # Should generate: COTP DR + TCP FIN + TCP FIN-ACK + TCP ACK = 4
        assert len(events) == 4

        assert events[0].metadata["type"] == "cotp_dr"
        assert events[0].metadata["phase"] == "disconnect"
        assert events[1].metadata["type"] == "tcp_fin"
        assert events[2].metadata["type"] == "tcp_fin_ack"
        assert events[3].metadata["type"] == "tcp_ack"

        assert state.state_name == "disconnected"

    def test_validate_config_valid(self, engine: S7Engine):
        """Test config validation with valid config."""
        config = {
            "rack": 0,
            "slot": 1,
            "pdu_size": 480,
            "connection_type": S7ConnectionType.PG,
        }
        errors = engine.validate_config(config)
        assert len(errors) == 0

    def test_validate_config_invalid_rack(self, engine: S7Engine):
        """Test config validation with invalid rack number."""
        config = {"rack": 10}  # Max is 7
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("rack" in e.lower() for e in errors)

    def test_validate_config_invalid_slot(self, engine: S7Engine):
        """Test config validation with invalid slot number."""
        config = {"slot": 50}  # Max is 31
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("slot" in e.lower() for e in errors)

    def test_validate_config_invalid_pdu_size(self, engine: S7Engine):
        """Test config validation with invalid PDU size."""
        config = {"pdu_size": 100}  # Min is 240
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("pdu" in e.lower() for e in errors)

    def test_validate_config_pdu_size_too_large(self, engine: S7Engine):
        """Test config validation with PDU size too large."""
        config = {"pdu_size": 2000}  # Max is 960
        errors = engine.validate_config(config)
        assert len(errors) > 0

    def test_validate_config_invalid_connection_type(self, engine: S7Engine):
        """Test config validation with invalid connection type."""
        config = {"connection_type": 99}
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("connection type" in e.lower() for e in errors)

    def test_validate_config_invalid_area_code(self, engine: S7Engine):
        """Test config validation with invalid area code in read areas."""
        config = {
            "read_areas": [
                {"area": 0xFF}  # Invalid
            ]
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("area code" in e.lower() for e in errors)

    def test_packet_bytes_non_empty(self, engine: S7Engine, flow_context: FlowContext):
        """Test that all generated packet events have non-empty packet bytes."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        for event in events:
            assert len(event.packet_bytes) > 0, (
                f"Event {event.metadata.get('type')} has empty packet bytes"
            )
