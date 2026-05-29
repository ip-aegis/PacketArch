# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for typed conversation state classes."""


from app.protocol_engines.types import (
    BACnetConversationState,
    ConversationState,
    DNP3ConversationState,
    EtherNetIPConversationState,
    IEC104ConversationState,
    ModbusConversationState,
    OPCUAConversationState,
    ProfinetConversationState,
    ProtocolType,
    S7ConversationState,
    SNMPConversationState,
    create_conversation_state,
)


class TestConversationStateFactory:
    """Tests for create_conversation_state factory function."""

    def test_create_modbus_state(self):
        """Test creating Modbus state."""
        state = create_conversation_state(ProtocolType.MODBUS_TCP, "flow-001")
        assert isinstance(state, ModbusConversationState)
        assert state.flow_id == "flow-001"

    def test_create_ethernet_ip_state(self):
        """Test creating EtherNet/IP state."""
        state = create_conversation_state(ProtocolType.ETHERNET_IP, "flow-002")
        assert isinstance(state, EtherNetIPConversationState)

    def test_create_profinet_state(self):
        """Test creating PROFINET state."""
        state = create_conversation_state(ProtocolType.PROFINET, "flow-003")
        assert isinstance(state, ProfinetConversationState)

    def test_create_s7_state(self):
        """Test creating S7 state."""
        state = create_conversation_state(ProtocolType.S7COMM, "flow-004")
        assert isinstance(state, S7ConversationState)

    def test_create_snmp_state(self):
        """Test creating SNMP state."""
        state = create_conversation_state(ProtocolType.SNMP, "flow-005")
        assert isinstance(state, SNMPConversationState)

    def test_create_bacnet_state(self):
        """Test creating BACnet state."""
        state = create_conversation_state(ProtocolType.BACNET, "flow-006")
        assert isinstance(state, BACnetConversationState)

    def test_create_dnp3_state(self):
        """Test creating DNP3 state."""
        state = create_conversation_state(ProtocolType.DNP3, "flow-007")
        assert isinstance(state, DNP3ConversationState)

    def test_create_iec104_state(self):
        """Test creating IEC-104 state."""
        state = create_conversation_state(ProtocolType.IEC_104, "flow-008")
        assert isinstance(state, IEC104ConversationState)

    def test_create_opcua_state(self):
        """Test creating OPC UA state."""
        state = create_conversation_state(ProtocolType.OPC_UA, "flow-009")
        assert isinstance(state, OPCUAConversationState)

    def test_create_with_kwargs(self):
        """Test creating state with additional kwargs."""
        state = create_conversation_state(
            ProtocolType.MODBUS_TCP,
            "flow-001",
            max_retries=5,
        )
        assert state.max_retries == 5


class TestConversationStateBase:
    """Tests for ConversationStateBase."""

    def test_default_values(self):
        """Test default state values."""
        state = ModbusConversationState(flow_id="test")
        assert state.state_name == "idle"
        assert state.transaction_id == 0
        assert state.sequence_number == 0
        assert state.error_count == 0

    def test_reset(self):
        """Test state reset."""
        state = ModbusConversationState(flow_id="test")
        state.state_name = "active"
        state.transaction_id = 100
        state.error_count = 5

        state.reset()

        assert state.state_name == "idle"
        assert state.transaction_id == 0
        assert state.error_count == 0

    def test_increment_transaction(self):
        """Test transaction ID increment."""
        state = ModbusConversationState(flow_id="test")

        tid1 = state.increment_transaction()
        tid2 = state.increment_transaction()
        tid3 = state.increment_transaction()

        assert tid1 == 1
        assert tid2 == 2
        assert tid3 == 3


class TestModbusConversationState:
    """Tests for ModbusConversationState."""

    def test_start_request(self):
        """Test starting a request."""
        state = ModbusConversationState(flow_id="test")

        tid = state.start_request(function_code=3, unit_id=1)

        assert tid == 1
        assert state.last_function_code == 3
        assert state.last_unit_id == 1
        assert state.pending_request is True
        assert state.retry_count == 0

    def test_complete_request(self):
        """Test completing a request."""
        state = ModbusConversationState(flow_id="test")
        state.start_request(3, 1)
        state.retry_count = 2

        state.complete_request()

        assert state.pending_request is False
        assert state.retry_count == 0

    def test_should_retry(self):
        """Test retry decision."""
        state = ModbusConversationState(flow_id="test", max_retries=3)

        state.retry_count = 0
        assert state.should_retry() is True

        state.retry_count = 3
        assert state.should_retry() is False

        state.retry_count = 4
        assert state.should_retry() is False


class TestEtherNetIPConversationState:
    """Tests for EtherNetIPConversationState."""

    def test_register_session(self):
        """Test session registration."""
        state = EtherNetIPConversationState(flow_id="test")

        state.register_session(0x12345678)

        assert state.session_handle == 0x12345678
        assert state.is_registered is True
        assert state.state_name == "registered"

    def test_unregister_session(self):
        """Test session unregistration."""
        state = EtherNetIPConversationState(flow_id="test")
        state.register_session(0x12345678)
        state.establish_connection(0x1234, 0x5678)

        state.unregister_session()

        assert state.session_handle == 0
        assert state.is_registered is False
        assert state.is_connected is False
        assert state.connection_id is None
        assert state.state_name == "idle"

    def test_establish_connection(self):
        """Test CIP connection establishment."""
        state = EtherNetIPConversationState(flow_id="test")
        state.register_session(0x12345678)

        state.establish_connection(conn_id=0x1234, serial=0x5678)

        assert state.connection_id == 0x1234
        assert state.connection_serial == 0x5678
        assert state.is_connected is True
        assert state.state_name == "connected"


class TestProfinetConversationState:
    """Tests for ProfinetConversationState."""

    def test_complete_identify(self):
        """Test DCP identify completion."""
        state = ProfinetConversationState(flow_id="test")

        state.complete_identify("plc-siemens-001")

        assert state.station_name == "plc-siemens-001"
        assert state.is_identified is True
        assert state.state_name == "identified"

    def test_establish_ar(self):
        """Test AR establishment."""
        state = ProfinetConversationState(flow_id="test")
        ar_uuid = b"\x01\x02\x03\x04" * 4

        state.establish_ar(ar_uuid, session_key=12345)

        assert state.ar_uuid == ar_uuid
        assert state.session_key == 12345
        assert state.is_ar_established is True
        assert state.state_name == "ar_established"

    def test_start_io(self):
        """Test starting cyclic IO."""
        state = ProfinetConversationState(flow_id="test")

        state.start_io()

        assert state.io_active is True
        assert state.cycle_counter == 0
        assert state.state_name == "io_active"

    def test_increment_cycle(self):
        """Test cycle counter increment and wrap."""
        state = ProfinetConversationState(flow_id="test")
        state.start_io()

        # Normal increment
        assert state.increment_cycle() == 1
        assert state.increment_cycle() == 2

        # Test wrap at 0xFFFF
        state.cycle_counter = 0xFFFE
        assert state.increment_cycle() == 0xFFFF
        assert state.increment_cycle() == 0  # Wrap


class TestS7ConversationState:
    """Tests for S7ConversationState."""

    def test_connect_cotp(self):
        """Test COTP connection."""
        state = S7ConversationState(flow_id="test")

        state.connect_cotp(dst_ref=0x1234)

        assert state.cotp_dst_ref == 0x1234
        assert state.is_connected is True
        assert state.state_name == "cotp_connected"

    def test_setup_communication(self):
        """Test S7 communication setup."""
        state = S7ConversationState(flow_id="test")

        state.setup_communication(max_pdu=960)

        assert state.max_pdu_size == 960
        assert state.is_setup is True
        assert state.state_name == "s7_setup"

    def test_next_pdu_ref(self):
        """Test PDU reference increment and wrap."""
        state = S7ConversationState(flow_id="test")

        assert state.next_pdu_ref() == 1
        assert state.next_pdu_ref() == 2

        # Test wrap
        state.pdu_ref = 0xFFFE
        assert state.next_pdu_ref() == 0xFFFF
        assert state.next_pdu_ref() == 0


class TestSNMPConversationState:
    """Tests for SNMPConversationState."""

    def test_start_request(self):
        """Test SNMP request start."""
        state = SNMPConversationState(flow_id="test")

        rid1 = state.start_request()
        rid2 = state.start_request()

        assert rid1 == 1
        assert rid2 == 2

    def test_start_walk(self):
        """Test SNMP walk start."""
        state = SNMPConversationState(flow_id="test")

        state.start_walk("1.3.6.1.2.1.1")

        assert state.walk_in_progress is True
        assert state.walk_start_oid == "1.3.6.1.2.1.1"
        assert state.last_oid == "1.3.6.1.2.1.1"
        assert state.state_name == "walking"

    def test_end_walk(self):
        """Test SNMP walk end."""
        state = SNMPConversationState(flow_id="test")
        state.start_walk("1.3.6.1.2.1.1")

        state.end_walk()

        assert state.walk_in_progress is False
        assert state.state_name == "idle"


class TestBACnetConversationState:
    """Tests for BACnetConversationState."""

    def test_next_invoke_id(self):
        """Test invoke ID increment and wrap."""
        state = BACnetConversationState(flow_id="test")

        assert state.next_invoke_id() == 1
        assert state.next_invoke_id() == 2

        # Test wrap at 255
        state.invoke_id = 254
        assert state.next_invoke_id() == 255
        assert state.next_invoke_id() == 0

    def test_segmented_receive(self):
        """Test segmented message handling."""
        state = BACnetConversationState(flow_id="test")

        state.start_segmented_receive()
        assert state.pending_segmented is True
        assert state.segments_received == []

        state.receive_segment(0)
        state.receive_segment(1)
        state.receive_segment(2)
        assert state.segments_received == [0, 1, 2]

        state.complete_segmented()
        assert state.pending_segmented is False
        assert state.segments_received == []


class TestDNP3ConversationState:
    """Tests for DNP3ConversationState."""

    def test_next_sequence(self):
        """Test sequence number increment and wrap."""
        state = DNP3ConversationState(flow_id="test")

        assert state.next_sequence() == 1
        assert state.next_sequence() == 2

        # Test wrap at 15
        state.sequence = 14
        assert state.next_sequence() == 15
        assert state.next_sequence() == 0


class TestIEC104ConversationState:
    """Tests for IEC104ConversationState."""

    def test_next_send_sequence(self):
        """Test send sequence increment."""
        state = IEC104ConversationState(flow_id="test")

        assert state.next_send_sequence() == 0
        assert state.next_send_sequence() == 1
        assert state.next_send_sequence() == 2

    def test_update_recv_sequence(self):
        """Test receive sequence update."""
        state = IEC104ConversationState(flow_id="test")

        state.update_recv_sequence(5)
        assert state.recv_sequence == 6
        assert state.w_counter == 1

        state.update_recv_sequence(6)
        assert state.recv_sequence == 7
        assert state.w_counter == 2

    def test_start_dt(self):
        """Test STARTDT activation."""
        state = IEC104ConversationState(flow_id="test")

        state.start_dt()

        assert state.is_started is True
        assert state.state_name == "started"


class TestOPCUAConversationState:
    """Tests for OPCUAConversationState."""

    def test_open_channel(self):
        """Test secure channel opening."""
        state = OPCUAConversationState(flow_id="test")

        state.open_channel(channel_id=12345, token_id=67890)

        assert state.secure_channel_id == 12345
        assert state.token_id == 67890
        assert state.is_channel_open is True
        assert state.state_name == "channel_open"

    def test_activate_session(self):
        """Test session activation."""
        state = OPCUAConversationState(flow_id="test")
        session_id = b"\x01\x02\x03\x04"
        token = b"\x05\x06\x07\x08"

        state.activate_session(session_id, token)

        assert state.session_id == session_id
        assert state.authentication_token == token
        assert state.is_session_active is True
        assert state.state_name == "session_active"

    def test_next_request_id(self):
        """Test request ID increment."""
        state = OPCUAConversationState(flow_id="test")

        assert state.next_request_id() == 1
        assert state.next_request_id() == 2
        assert state.next_request_id() == 3


class TestLegacyConversationState:
    """Tests for legacy ConversationState (backward compatibility)."""

    def test_legacy_state_still_works(self):
        """Test that legacy state class still works."""
        state = ConversationState(
            flow_id="test",
            state_name="active",
            transaction_id=10,
            sequence_number=5,
            custom_data={"foo": "bar"},
        )

        assert state.flow_id == "test"
        assert state.state_name == "active"
        assert state.transaction_id == 10
        assert state.sequence_number == 5
        assert state.custom_data == {"foo": "bar"}
