# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for PROFINET protocol engine."""

import pytest

from app.protocol_engines import get_engine, list_supported_protocols
from app.protocol_engines.types import (
    DeviceContext,
    FlowContext,
    ProtocolType,
)
from app.protocol_engines.profinet.engine import ProfinetEngine
from app.protocol_engines.profinet.packets import (
    build_ethernet_header,
    build_rt_frame,
    build_rt_packet,
    build_dcp_header,
    build_dcp_block,
    build_dcp_identify_request,
    build_dcp_identify_response,
    DataStatus,
    PROFINET_ETHERTYPE,
    DCP_SERVICE_IDENTIFY,
    DCP_SERVICE_TYPE_REQUEST,
)
from app.protocol_engines.profinet.states import (
    ProfinetDeviceStateMachine,
    ProfinetControllerStateMachine,
    RTCycleState,
)


class TestProfinetEngineRegistry:
    """Test PROFINET engine registration."""

    def test_profinet_registered(self):
        """Test that PROFINET engine is registered."""
        protocols = list_supported_protocols()
        assert ProtocolType.PROFINET in protocols

    def test_get_profinet_engine(self):
        """Test getting PROFINET engine instance."""
        engine = get_engine(ProtocolType.PROFINET)
        assert isinstance(engine, ProfinetEngine)
        assert engine.protocol_type == ProtocolType.PROFINET


class TestProfinetPackets:
    """Test PROFINET packet building."""

    def test_ethernet_header(self):
        """Test Ethernet header building."""
        src = DeviceContext(
            device_id="controller",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=0,
        )
        dst = DeviceContext(
            device_id="device",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=0,
        )

        header = build_ethernet_header(src, dst, PROFINET_ETHERTYPE)

        # Ethernet header: Dst MAC(6) + Src MAC(6) + EtherType(2) = 14 bytes
        assert len(header) == 14
        assert header[0:6] == bytes.fromhex("66778899AABB")  # Dst MAC
        assert header[12:14] == b'\x88\x92'  # PROFINET EtherType

    def test_rt_frame_structure(self):
        """Test RT frame building."""
        data = bytes([0x01, 0x02, 0x03, 0x04])  # 4 bytes I/O data
        frame = build_rt_frame(
            frame_id=0x8000,
            data=data,
            cycle_counter=100,
            data_status=DataStatus.VALID_RUN_PRIMARY,
        )

        # RT frame: Frame ID(2) + Data(4) + Cycle Counter(2) + Data Status(1) + Transfer Status(1)
        assert len(frame) == 2 + 4 + 2 + 1 + 1
        assert frame[0:2] == b'\x80\x00'  # Frame ID
        assert frame[2:6] == data  # I/O data
        assert frame[6:8] == b'\x00\x64'  # Cycle counter 100
        assert frame[8] == DataStatus.VALID_RUN_PRIMARY  # Data status

    def test_rt_packet_complete(self):
        """Test complete RT packet building."""
        src = DeviceContext(
            device_id="controller",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=0,
        )
        dst = DeviceContext(
            device_id="device",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=0,
        )

        packet = build_rt_packet(
            src=src,
            dst=dst,
            frame_id=0x8000,
            data=bytes(32),  # 32 bytes I/O
            cycle_counter=1,
        )

        # Ethernet(14) + Frame ID(2) + Data(32) + Cycle(2) + Status(2) = 52 bytes
        assert len(packet) == 14 + 2 + 32 + 2 + 2

    def test_dcp_header(self):
        """Test DCP header building."""
        header = build_dcp_header(
            service_id=DCP_SERVICE_IDENTIFY,
            service_type=DCP_SERVICE_TYPE_REQUEST,
            xid=0x12345678,
            response_delay=1,
            data_length=4,
        )

        # DCP header: Service ID(1) + Service Type(1) + XID(4) + Response Delay(2) + Data Length(2) = 10 bytes
        assert len(header) == 10
        assert header[0] == DCP_SERVICE_IDENTIFY
        assert header[1] == DCP_SERVICE_TYPE_REQUEST

    def test_dcp_block(self):
        """Test DCP block building."""
        block = build_dcp_block(
            option=0x02,  # Device
            suboption=0x02,  # Name of station
            data=b"my-device",
        )

        # Block: Option(1) + Suboption(1) + Length(2) + Data(9) + Padding(1) = 14 bytes
        assert len(block) == 14  # Padded to even length
        assert block[0] == 0x02
        assert block[1] == 0x02

    def test_dcp_identify_request(self):
        """Test DCP Identify request building."""
        request = build_dcp_identify_request(xid=0x00000001)

        # Should contain header + ALL block
        assert len(request) >= 10  # At least header

    def test_dcp_identify_response(self):
        """Test DCP Identify response building."""
        response = build_dcp_identify_response(
            xid=0x00000001,
            device_name="test-device",
            vendor_id=0x002A,
            device_id=0x0001,
            ip_address="192.168.1.100",
        )

        # Should contain header + multiple blocks
        assert len(response) > 20


class TestProfinetStateMachines:
    """Test PROFINET state machines."""

    def test_device_state_machine_initial(self):
        """Test device state machine initial state."""
        sm = ProfinetDeviceStateMachine("device-1")
        assert sm.current_state == sm.power_on

    def test_device_state_machine_discovery(self):
        """Test device state machine discovery flow."""
        sm = ProfinetDeviceStateMachine("device-1")

        sm.start_discovery()
        assert sm.current_state == sm.dcp_wait

        sm.receive_identify()
        assert sm.current_state == sm.dcp_identified

    def test_device_state_machine_full_cycle(self):
        """Test device state machine full connection cycle."""
        sm = ProfinetDeviceStateMachine("device-1")

        # Discovery
        sm.start_discovery()
        sm.receive_identify()

        # Connection
        sm.start_connection()
        assert sm.current_state == sm.connecting
        assert sm.ar_uuid is not None

        sm.connection_established()
        assert sm.current_state == sm.parameterizing

        sm.parameters_complete()
        assert sm.current_state == sm.application_ready

        sm.start_io()
        assert sm.current_state == sm.data_exchange

        # I/O cycles (internal)
        sm.io_cycle()
        assert sm.cycle_counter == 1
        sm.io_cycle()
        assert sm.cycle_counter == 2

        # Disconnect
        sm.disconnect()
        assert sm.current_state == sm.offline

    def test_controller_state_machine(self):
        """Test controller state machine."""
        sm = ProfinetControllerStateMachine("controller-1")
        assert sm.current_state == sm.idle

        sm.start_discovery()
        assert sm.current_state == sm.discovering

        sm.skip_config()  # Skip DCP Set
        assert sm.current_state == sm.connecting

    def test_rt_cycle_state(self):
        """Test RT cycle state tracker."""
        rt_state = RTCycleState(
            frame_id_output=0x8000,
            frame_id_input=0x8001,
            output_data_size=32,
            input_data_size=32,
        )

        assert rt_state.cycle_counter == 0

        # Increment cycles
        c1 = rt_state.increment_cycle()
        assert c1 == 1
        assert rt_state.cycle_counter == 1

        c2 = rt_state.increment_cycle()
        assert c2 == 2

        # Update data
        rt_state.update_output_data(bytes(32))
        assert len(rt_state.output_data) == 32


class TestProfinetEngine:
    """Test PROFINET engine."""

    @pytest.fixture
    def engine(self) -> ProfinetEngine:
        """Create PROFINET engine instance."""
        return ProfinetEngine()

    @pytest.fixture
    def flow_context(self) -> FlowContext:
        """Create test flow context."""
        src = DeviceContext(
            device_id="controller",
            mac_address="00:11:22:33:44:55",
            ip_address="192.168.1.10",
            port=0,
        )
        dst = DeviceContext(
            device_id="io-device",
            mac_address="66:77:88:99:AA:BB",
            ip_address="192.168.1.20",
            port=0,
        )
        return FlowContext(
            flow_id="pn-flow-1",
            source=src,
            destination=dst,
            protocol=ProtocolType.PROFINET,
            config={
                "frame_id_output": 0x8000,
                "frame_id_input": 0x8001,
                "output_data_size": 32,
                "input_data_size": 32,
                "cycle_time_ms": 1.0,
                "device_name": "test-device",
            },
            timing_model={
                "response_delay_ms": 0.1,
            },
        )

    def test_create_initial_state(self, engine: ProfinetEngine, flow_context: FlowContext):
        """Test initial state creation."""
        state = engine.create_initial_state(flow_context)

        assert state.flow_id == flow_context.flow_id
        assert state.state_name == "idle"
        assert "rt_state" in state.custom_data
        assert "device_name" in state.custom_data
        assert state.custom_data["device_name"] == "test-device"

        rt_state = state.custom_data["rt_state"]
        assert rt_state.frame_id_output == 0x8000
        assert rt_state.frame_id_input == 0x8001

    def test_generate_startup_sequence_with_dcp(self, engine: ProfinetEngine, flow_context: FlowContext):
        """Test startup with DCP discovery + AR establishment."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # Should generate DCP Identify Request + Response + 6 RPC AR packets
        assert len(events) == 8

        assert events[0].metadata["type"] == "dcp_identify_request"
        assert events[0].direction == "request"

        assert events[1].metadata["type"] == "dcp_identify_response"
        assert events[1].direction == "response"

        # RPC AR setup: Connect, Write, Control (request + response each)
        assert events[2].metadata["type"] == "rpc_connect_request"
        assert events[3].metadata["type"] == "rpc_connect_response"
        assert events[4].metadata["type"] == "rpc_write_request"
        assert events[5].metadata["type"] == "rpc_write_response"
        assert events[6].metadata["type"] == "rpc_control_request"
        assert events[7].metadata["type"] == "rpc_control_response"

        # State should be updated
        assert state.state_name == "data_exchange"
        assert state.custom_data.get("is_ar_established") is True

    def test_generate_startup_sequence_skip_dcp(self, engine: ProfinetEngine, flow_context: FlowContext):
        """Test startup skipping DCP but still doing AR establishment."""
        flow_context.config["skip_dcp"] = True
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_startup_sequence(flow_context, state, 0.0))

        # No DCP packets when skipped, but still 6 RPC AR packets
        assert len(events) == 6
        assert events[0].metadata["type"] == "rpc_connect_request"
        assert state.state_name == "data_exchange"

    def test_generate_poll_cycle(self, engine: ProfinetEngine, flow_context: FlowContext):
        """Test RT cyclic I/O generation."""
        state = engine.create_initial_state(flow_context)
        state.state_name = "data_exchange"

        events = list(engine.generate_poll_cycle(flow_context, state, 100.0))

        # Should generate output + input frames
        assert len(events) == 2

        # Output frame (controller -> device)
        assert events[0].direction == "request"
        assert events[0].metadata["type"] == "rt_output"
        assert events[0].metadata["frame_id"] == 0x8000
        assert events[0].metadata["cycle_counter"] == 1

        # Input frame (device -> controller)
        assert events[1].direction == "response"
        assert events[1].metadata["type"] == "rt_input"
        assert events[1].metadata["frame_id"] == 0x8001
        assert events[1].metadata["cycle_counter"] == 1

        # Timing
        assert events[1].timestamp_ms > events[0].timestamp_ms

    def test_generate_poll_cycle_increments_counter(self, engine: ProfinetEngine, flow_context: FlowContext):
        """Test that cycle counter increments."""
        state = engine.create_initial_state(flow_context)

        # First cycle
        events1 = list(engine.generate_poll_cycle(flow_context, state, 100.0))
        assert events1[0].metadata["cycle_counter"] == 1

        # Second cycle
        events2 = list(engine.generate_poll_cycle(flow_context, state, 101.0))
        assert events2[0].metadata["cycle_counter"] == 2

        # Sequence number should match
        assert state.sequence_number == 2

    def test_generate_shutdown_sequence(self, engine: ProfinetEngine, flow_context: FlowContext):
        """Test shutdown sequence generation."""
        state = engine.create_initial_state(flow_context)
        events = list(engine.generate_shutdown_sequence(flow_context, state, 1000.0))

        # Should generate stop frames
        assert len(events) == 2

        assert events[0].metadata["type"] == "rt_output_stop"
        assert events[1].metadata["type"] == "rt_input_stop"

        assert state.state_name == "offline"

    def test_validate_config_valid(self, engine: ProfinetEngine):
        """Test config validation with valid config."""
        config = {
            "frame_id_output": 0x8000,
            "frame_id_input": 0x8001,
            "output_data_size": 32,
            "input_data_size": 32,
            "cycle_time_ms": 1.0,
            "device_name": "my-device",
        }
        errors = engine.validate_config(config)
        assert len(errors) == 0

    def test_validate_config_invalid_frame_id(self, engine: ProfinetEngine):
        """Test config validation with invalid frame ID."""
        config = {
            "frame_id_output": 0x1000,  # Out of RT range
            "frame_id_input": 0x8001,
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("frame_id_output" in e for e in errors)

    def test_validate_config_same_frame_ids(self, engine: ProfinetEngine):
        """Test config validation with same frame IDs."""
        config = {
            "frame_id_output": 0x8000,
            "frame_id_input": 0x8000,  # Same as output
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("must be different" in e for e in errors)

    def test_validate_config_invalid_data_size(self, engine: ProfinetEngine):
        """Test config validation with invalid data size."""
        config = {
            "output_data_size": 2000,  # Too large
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("output_data_size" in e for e in errors)

    def test_validate_config_invalid_cycle_time(self, engine: ProfinetEngine):
        """Test config validation with invalid cycle time."""
        config = {
            "cycle_time_ms": 0.1,  # Too fast (min is 0.25)
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("cycle_time_ms" in e for e in errors)

    def test_validate_config_invalid_device_name(self, engine: ProfinetEngine):
        """Test config validation with invalid device name."""
        config = {
            "device_name": "Invalid Name!",  # Contains invalid chars
        }
        errors = engine.validate_config(config)
        assert len(errors) > 0
        assert any("device_name" in e for e in errors)
