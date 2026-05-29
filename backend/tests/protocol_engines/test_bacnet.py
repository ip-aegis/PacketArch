# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for BACnet/IP protocol engine."""

import pytest

from app.protocol_engines import get_engine, list_supported_protocols
from app.protocol_engines.types import (
    DeviceContext,
    FlowContext,
    ProtocolType,
)
from app.protocol_engines.bacnet.engine import BACnetEngine
from app.protocol_engines.vendor_oui import BACNET_VENDOR_IDS
from app.protocol_engines.bacnet.types import (
    BACNET_PORT,
    BACNET_BVLC_TYPE,
    BACnetFlowConfig,
    BACnetObjectIdentifier,
    BACnetObjectType,
    BACnetPDUType,
    BACnetPropertyIdentifier,
    BACnetSegmentation,
    BACnetState,
    BACnetUnconfirmedService,
    BVLCFunction,
)
from app.protocol_engines.bacnet.packets import (
    build_bvlc_header,
    build_npdu,
    build_who_is_apdu,
    build_i_am_apdu,
    build_who_is_packet,
    build_i_am_packet,
    build_read_property_request_apdu,
    build_read_property_response_apdu,
    build_read_property_request_packet,
    build_read_property_response_packet,
    encode_unsigned,
    encode_signed,
    encode_real,
    encode_enumerated,
    encode_character_string,
    encode_boolean,
    encode_null,
    encode_object_identifier,
    encode_length,
    encode_context_tag,
    encode_opening_tag,
    encode_closing_tag,
)


class TestBACnetEngineRegistry:
    """Test BACnet engine registration."""

    def test_bacnet_registered(self):
        """Test that BACnet engine is registered."""
        protocols = list_supported_protocols()
        assert ProtocolType.BACNET in protocols

    def test_get_bacnet_engine(self):
        """Test getting BACnet engine instance."""
        engine = get_engine(ProtocolType.BACNET)
        assert isinstance(engine, BACnetEngine)
        assert engine.protocol_type == ProtocolType.BACNET


class TestBACnetTypes:
    """Test BACnet type constants."""

    def test_bacnet_port(self):
        """Test BACnet port constant."""
        assert BACNET_PORT == 47808  # 0xBAC0

    def test_bacnet_bvlc_type(self):
        """Test BVLC type constant."""
        assert BACNET_BVLC_TYPE == 0x81

    def test_bacnet_object_types(self):
        """Test BACnet object type values."""
        assert BACnetObjectType.ANALOG_INPUT == 0
        assert BACnetObjectType.ANALOG_OUTPUT == 1
        assert BACnetObjectType.ANALOG_VALUE == 2
        assert BACnetObjectType.BINARY_INPUT == 3
        assert BACnetObjectType.DEVICE == 8

    def test_bacnet_segmentation(self):
        """Test segmentation enum values."""
        assert BACnetSegmentation.NO_SEGMENTATION == 3
        assert BACnetSegmentation.SEGMENTED_BOTH == 0

    def test_bacnet_vendor_ids(self):
        """Test vendor ID dictionary has expected entries."""
        assert 5 in BACNET_VENDOR_IDS  # Johnson Controls
        assert 17 in BACNET_VENDOR_IDS  # Honeywell
        assert 24 in BACNET_VENDOR_IDS  # Siemens

    def test_bacnet_object_identifier_valid(self):
        """Test BACnet Object Identifier encoding."""
        obj_id = BACnetObjectIdentifier(
            object_type=BACnetObjectType.DEVICE,
            instance=1001,
        )
        encoded = obj_id.encode()
        # Type 8 (10 bits) << 22 | instance 1001 (22 bits)
        expected = (8 << 22) | 1001
        assert encoded == expected

    def test_bacnet_object_identifier_decode(self):
        """Test BACnet Object Identifier decoding."""
        encoded_value = (8 << 22) | 1001
        obj_id = BACnetObjectIdentifier.decode(encoded_value)
        assert obj_id.object_type == BACnetObjectType.DEVICE
        assert obj_id.instance == 1001

    def test_bacnet_object_identifier_invalid_instance(self):
        """Test BACnet Object Identifier rejects invalid instance."""
        with pytest.raises(ValueError):
            BACnetObjectIdentifier(
                object_type=BACnetObjectType.DEVICE,
                instance=0x400000,  # > 4194303
            )

    def test_bacnet_flow_config_defaults(self):
        """Test BACnetFlowConfig default values."""
        config = BACnetFlowConfig()
        assert config.device_instance == 0
        assert config.vendor_id == 0
        assert config.max_apdu_length == 1476
        assert config.segmentation == BACnetSegmentation.NO_SEGMENTATION
        assert config.generate_who_is is True
        assert config.timeout_ms == 3000


class TestBACnetEncoding:
    """Test BACnet ASN.1/BER encoding utilities."""

    def test_encode_length_short(self):
        """Test short form length encoding."""
        assert encode_length(10) == bytes([10])
        assert encode_length(127) == bytes([127])

    def test_encode_length_one_byte(self):
        """Test one-byte extended length encoding."""
        assert encode_length(128) == bytes([0x81, 128])
        assert encode_length(255) == bytes([0x81, 255])

    def test_encode_length_two_bytes(self):
        """Test two-byte extended length encoding."""
        result = encode_length(256)
        assert result[0] == 0x82
        assert result[1:] == b"\x01\x00"

    def test_encode_unsigned_zero(self):
        """Test unsigned integer encoding for zero."""
        result = encode_unsigned(0)
        # Tag byte (2 << 4 | length) + value
        assert len(result) >= 2

    def test_encode_unsigned_small(self):
        """Test unsigned integer encoding for small value."""
        result = encode_unsigned(42)
        # Should be application tag 2 with 1-byte value
        tag = result[0]
        assert (tag >> 4) == 2  # Unsigned int tag

    def test_encode_unsigned_large(self):
        """Test unsigned integer encoding for large value."""
        result = encode_unsigned(100000)
        tag = result[0]
        assert (tag >> 4) == 2

    def test_encode_signed_positive(self):
        """Test signed integer encoding."""
        result = encode_signed(42)
        tag = result[0]
        assert (tag >> 4) == 3  # Signed int tag

    def test_encode_signed_negative(self):
        """Test signed integer encoding for negative."""
        result = encode_signed(-42)
        tag = result[0]
        assert (tag >> 4) == 3

    def test_encode_real(self):
        """Test real (float) encoding."""
        result = encode_real(72.5)
        tag = result[0]
        assert (tag >> 4) == 4  # Real tag
        assert (tag & 0x0F) == 4  # 4 bytes for float

    def test_encode_enumerated(self):
        """Test enumerated value encoding."""
        result = encode_enumerated(3)
        tag = result[0]
        assert (tag >> 4) == 9  # Enumerated tag

    def test_encode_character_string(self):
        """Test character string encoding."""
        result = encode_character_string("Hello")
        tag = result[0]
        assert (tag >> 4) == 7  # Character string tag

    def test_encode_boolean_true(self):
        """Test boolean encoding for True."""
        result = encode_boolean(True)
        assert result == bytes([0x11])  # Tag 1, value 1

    def test_encode_boolean_false(self):
        """Test boolean encoding for False."""
        result = encode_boolean(False)
        assert result == bytes([0x10])  # Tag 1, value 0

    def test_encode_null(self):
        """Test null value encoding."""
        result = encode_null()
        assert result == bytes([0x00])

    def test_encode_object_identifier(self):
        """Test Object Identifier encoding."""
        result = encode_object_identifier(BACnetObjectType.DEVICE, 1001)
        tag = result[0]
        assert (tag >> 4) == 12  # Object identifier tag
        assert (tag & 0x0F) == 4  # 4 bytes

    def test_encode_context_tag(self):
        """Test context-specific tag encoding."""
        data = bytes([0x01, 0x02])
        result = encode_context_tag(0, data)
        tag = result[0]
        assert tag & 0x08 == 0x08  # Context-specific bit set

    def test_encode_opening_tag(self):
        """Test opening tag encoding."""
        result = encode_opening_tag(3)
        assert result == bytes([(3 << 4) | 0x0E])

    def test_encode_closing_tag(self):
        """Test closing tag encoding."""
        result = encode_closing_tag(3)
        assert result == bytes([(3 << 4) | 0x0F])


class TestBACnetPackets:
    """Test BACnet packet building."""

    def test_bvlc_header(self):
        """Test BVLC header building."""
        header = build_bvlc_header(BVLCFunction.ORIGINAL_UNICAST_NPDU, 100)

        assert len(header) == 4
        assert header[0] == BACNET_BVLC_TYPE  # 0x81
        assert header[1] == BVLCFunction.ORIGINAL_UNICAST_NPDU
        # Total length = 4 + 100 = 104
        expected_length = 104
        assert (header[2] << 8) | header[3] == expected_length

    def test_npdu_basic(self):
        """Test basic NPDU header (no routing)."""
        npdu = build_npdu(expecting_reply=False)

        assert len(npdu) == 2
        assert npdu[0] == 0x01  # Version
        assert npdu[1] & 0x04 == 0  # No expecting reply

    def test_npdu_expecting_reply(self):
        """Test NPDU with expecting_reply flag."""
        npdu = build_npdu(expecting_reply=True)

        assert npdu[1] & 0x04 == 0x04

    def test_who_is_apdu(self):
        """Test Who-Is APDU building."""
        apdu = build_who_is_apdu()

        # PDU type: unconfirmed request (1 << 4 = 0x10)
        assert apdu[0] == (BACnetPDUType.UNCONFIRMED_REQUEST << 4)
        # Service: Who-Is
        assert apdu[1] == BACnetUnconfirmedService.WHO_IS

    def test_i_am_apdu(self):
        """Test I-Am APDU building."""
        apdu = build_i_am_apdu(
            device_instance=1001,
            max_apdu_length=1476,
            segmentation=BACnetSegmentation.NO_SEGMENTATION,
            vendor_id=5,
        )

        assert apdu[0] == (BACnetPDUType.UNCONFIRMED_REQUEST << 4)
        assert apdu[1] == BACnetUnconfirmedService.I_AM
        assert len(apdu) > 10  # Non-trivial packet

    def test_read_property_request_apdu(self):
        """Test ReadProperty request APDU building."""
        apdu = build_read_property_request_apdu(
            invoke_id=1,
            object_type=BACnetObjectType.DEVICE,
            object_instance=1001,
            property_id=BACnetPropertyIdentifier.VENDOR_NAME,
        )

        assert apdu[0] == (BACnetPDUType.CONFIRMED_REQUEST << 4)
        assert apdu[2] == 1  # Invoke ID
        assert apdu[3] == 12  # ReadProperty service choice

    def test_read_property_response_apdu_string(self):
        """Test ReadProperty response APDU with string value."""
        apdu = build_read_property_response_apdu(
            invoke_id=1,
            object_type=BACnetObjectType.DEVICE,
            object_instance=1001,
            property_id=BACnetPropertyIdentifier.VENDOR_NAME,
            property_value="Johnson Controls",
            property_type="string",
        )

        assert apdu[0] == (BACnetPDUType.COMPLEX_ACK << 4)
        assert apdu[1] == 1  # Invoke ID

    def test_read_property_response_apdu_real(self):
        """Test ReadProperty response APDU with real (float) value."""
        apdu = build_read_property_response_apdu(
            invoke_id=2,
            object_type=BACnetObjectType.ANALOG_INPUT,
            object_instance=1,
            property_id=BACnetPropertyIdentifier.PRESENT_VALUE,
            property_value=72.5,
            property_type="real",
        )

        assert apdu[0] == (BACnetPDUType.COMPLEX_ACK << 4)

    def test_who_is_packet_complete(self):
        """Test complete Who-Is broadcast packet."""
        src = DeviceContext(
            device_id="bms-manager",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=BACNET_PORT,
        )

        packet = build_who_is_packet(src)

        # Should have Ethernet(14) + IP(20) + UDP(8) + BACnet payload (BVLC + NPDU + APDU)
        assert len(packet) >= 42 + 4 + 2  # Min headers + BVLC + NPDU

    def test_i_am_packet_complete(self):
        """Test complete I-Am broadcast response packet."""
        src = DeviceContext(
            device_id="controller",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=BACNET_PORT,
        )

        packet = build_i_am_packet(
            src=src,
            device_instance=1001,
            max_apdu_length=1476,
            segmentation=BACnetSegmentation.NO_SEGMENTATION,
            vendor_id=5,
        )

        assert len(packet) > 50

    def test_read_property_request_packet_complete(self):
        """Test complete ReadProperty request packet."""
        src = DeviceContext(
            device_id="manager",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=BACNET_PORT,
        )
        dst = DeviceContext(
            device_id="controller",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=BACNET_PORT,
        )

        packet = build_read_property_request_packet(
            src=src,
            dst=dst,
            invoke_id=1,
            object_type=BACnetObjectType.DEVICE,
            object_instance=1001,
            property_id=BACnetPropertyIdentifier.VENDOR_NAME,
        )

        assert len(packet) > 50

    def test_read_property_response_packet_complete(self):
        """Test complete ReadProperty response packet."""
        src = DeviceContext(
            device_id="controller",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=BACNET_PORT,
        )
        dst = DeviceContext(
            device_id="manager",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=BACNET_PORT,
        )

        packet = build_read_property_response_packet(
            src=src,
            dst=dst,
            invoke_id=1,
            object_type=BACnetObjectType.DEVICE,
            object_instance=1001,
            property_id=BACnetPropertyIdentifier.VENDOR_NAME,
            property_value="Johnson Controls",
            property_type="string",
        )

        assert len(packet) > 50


class TestBACnetEngine:
    """Test BACnet engine."""

    @pytest.fixture
    def engine(self) -> BACnetEngine:
        """Create BACnet engine instance."""
        return BACnetEngine()

    @pytest.fixture
    def flow_context(self) -> FlowContext:
        """Create test flow context for BACnet."""
        src = DeviceContext(
            device_id="bms-manager",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=BACNET_PORT,
            vendor_fingerprint={},
        )
        dst = DeviceContext(
            device_id="hvac-controller",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=BACNET_PORT,
            vendor_fingerprint={
                "bacnet_identity": {
                    "vendor_id": 5,
                    "vendor_name": "Johnson Controls",
                    "model_name": "NAE55",
                    "firmware_revision": "12.0.3",
                    "device_instance": 1001,
                    "max_apdu_length": 1476,
                    "segmentation_supported": 3,
                    "protocol_version": 1,
                    "protocol_revision": 19,
                    "application_software_version": "3.0",
                    "system_status": 0,
                    "object_name": "AHU-1-Controller",
                    "description": "Air Handling Unit Controller",
                },
                "response_timing": {
                    "mean_ms": 25.0,
                    "std_dev_ms": 10.0,
                    "min_ms": 5.0,
                    "max_ms": 200.0,
                },
            },
        )
        return FlowContext(
            flow_id="bacnet-flow-1",
            source=src,
            destination=dst,
            protocol=ProtocolType.BACNET,
            config={
                "generate_who_is": True,
            },
            timing_model={
                "response_delay_ms": 25,
            },
        )

    def test_create_initial_state(self, engine: BACnetEngine, flow_context: FlowContext):
        """Test initial state creation."""
        state = engine.create_initial_state(flow_context)

        assert state.flow_id == flow_context.flow_id
        assert state.state_name == BACnetState.IDLE.value
        assert "invoke_id" in state.custom_data
        assert 1 <= state.custom_data["invoke_id"] <= 255
        # device_instance is injected per-instance-unique by the
        # FingerprintApplicator (UniqueIdentifierGenerator), deliberately
        # overriding the shared template value to stop Cyber Vision from
        # collapsing identically-fingerprinted devices. So it's a valid
        # BACnet instance, not necessarily the template's 1001.
        assert "device_instance" in state.custom_data
        assert 1 <= state.custom_data["device_instance"] <= 4194302
        assert state.custom_data["discovered"] is False

    def test_generate_startup_with_who_is(self, engine: BACnetEngine, flow_context: FlowContext):
        """Test startup sequence generates Who-Is and I-Am."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Should generate Who-Is + I-Am
        assert len(events) == 2

        # Who-Is
        assert events[0].metadata["type"] == "who_is"
        assert events[0].direction == "request"
        assert events[0].metadata["protocol"] == "bacnet"

        # I-Am
        assert events[1].metadata["type"] == "i_am"
        assert events[1].direction == "response"
        assert events[1].metadata["vendor_id"] == 5
        assert events[1].metadata["vendor_name"] == "Johnson Controls"
        # I-Am advertises the same applicator-assigned (unique) instance
        # that create_initial_state recorded — internal consistency, not
        # the raw template's 1001 (see test_create_initial_state).
        assert events[1].metadata["device_instance"] == state.custom_data["device_instance"]

        # Timing
        assert events[1].timestamp_ms > events[0].timestamp_ms

        # State updated
        assert state.custom_data["discovered"] is True
        assert state.state_name == BACnetState.POLLING.value

    def test_generate_startup_skip_who_is(self, engine: BACnetEngine, flow_context: FlowContext):
        """Test startup skipping Who-Is when disabled."""
        flow_context.config["generate_who_is"] = False
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Should only generate I-Am (no Who-Is)
        assert len(events) == 1
        assert events[0].metadata["type"] == "i_am"
        assert state.state_name == BACnetState.POLLING.value

    def test_generate_poll_cycle(self, engine: BACnetEngine, flow_context: FlowContext):
        """Test poll cycle generates ReadProperty request/response."""
        state = engine.create_initial_state(flow_context)
        state.state_name = BACnetState.POLLING.value
        state.custom_data["discovered"] = True

        events = list(engine.generate_poll_cycle(flow_context, state, 100.0))

        # Should generate request and response
        assert len(events) == 2

        # Request
        assert events[0].direction == "request"
        assert events[0].metadata["type"] == "read_property_request"
        assert "invoke_id" in events[0].metadata
        assert "object" in events[0].metadata
        assert "property" in events[0].metadata

        # Response
        assert events[1].direction == "response"
        assert events[1].metadata["type"] == "read_property_response"
        assert "value" in events[1].metadata
        assert events[1].timestamp_ms > events[0].timestamp_ms

        # State updated
        assert state.sequence_number == 1
        assert state.state_name == BACnetState.POLLING.value

    def test_poll_cycle_increments_state(self, engine: BACnetEngine, flow_context: FlowContext):
        """Test that multiple poll cycles advance through objects/properties."""
        state = engine.create_initial_state(flow_context)
        state.state_name = BACnetState.POLLING.value

        # Run several poll cycles
        for i in range(5):
            events = list(engine.generate_poll_cycle(flow_context, state, i * 1000.0))
            assert len(events) == 2
            assert state.sequence_number == i + 1

    def test_generate_shutdown_sequence(self, engine: BACnetEngine, flow_context: FlowContext):
        """Test shutdown sequence (BACnet is UDP - no teardown)."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_shutdown_sequence(flow_context, state, 1000.0))

        # BACnet is UDP-based, no connection teardown
        assert len(events) == 0

    def test_validate_config_valid(self, engine: BACnetEngine):
        """Test config validation with valid config."""
        config = {
            "device_instance": 1001,
            "vendor_id": 5,
            "timeout_ms": 3000,
        }
        errors = engine.validate_config(config)
        assert len(errors) == 0

    def test_validate_config_invalid_device_instance(self, engine: BACnetEngine):
        """Test config validation with invalid device instance."""
        config = {"device_instance": 5000000}  # Max is 4194302
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("device_instance" in e for e in errors)

    def test_validate_config_negative_vendor_id(self, engine: BACnetEngine):
        """Test config validation with negative vendor ID."""
        config = {"vendor_id": -1}
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("vendor_id" in e for e in errors)

    def test_validate_config_invalid_timeout(self, engine: BACnetEngine):
        """Test config validation with invalid timeout."""
        config = {"timeout_ms": 50}  # Min is 100
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("timeout_ms" in e for e in errors)

    def test_validate_config_invalid_poll_objects(self, engine: BACnetEngine):
        """Test config validation with invalid poll objects."""
        config = {"poll_objects": "not-a-list"}
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("poll_objects" in e for e in errors)

    def test_validate_config_invalid_poll_object_entry(self, engine: BACnetEngine):
        """Test config validation with invalid poll object entry."""
        config = {"poll_objects": [(0, 1), "bad-entry"]}
        errors = engine.validate_config(config)
        assert len(errors) > 0

    def test_packet_bytes_non_empty(self, engine: BACnetEngine, flow_context: FlowContext):
        """Test that all generated events have non-empty packet bytes."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))
        for event in events:
            assert len(event.packet_bytes) > 0
