"""PROFINET protocol engine implementation.

PROFINET (Process Field Network) is an Industrial Ethernet standard
for automation. This engine generates:
- DCP (Discovery and Configuration Protocol) frames
- RT (Real-Time) cyclic I/O data frames
- RTA (Real-Time Acyclic) alarm frames

Enhanced with:
- Fingerprint-based identity responses
- Alarm frame generation with configurable injection
- Timeout behavior simulation

PROFINET operates at Layer 2 (Ethernet) with EtherType 0x8892.
"""

import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.profinet.packets import (
    ALARM_TYPE_DIAGNOSTIC,
    ALARM_TYPE_PROCESS,
    ALARM_TYPE_STATUS,
    DataStatus,
    build_dcp_identify_request_packet,
    build_dcp_identify_response_packet,
    build_dcp_identify_response_packet_fingerprinted,
    build_rt_packet,
    build_rta_alarm_ack_packet,
    build_rta_alarm_packet,
    generate_io_data,
)
from app.protocol_engines.profinet.states import RTCycleState
from app.protocol_engines.timing import apply_jitter, get_response_delay
from app.protocol_engines.types import (
    ConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)


# Default PROFINET RT cycle times (in milliseconds)
DEFAULT_CYCLE_TIME_MS = 1.0  # 1ms typical for RT Class 1
MIN_CYCLE_TIME_MS = 0.25     # 250µs minimum
MAX_CYCLE_TIME_MS = 512.0    # 512ms maximum

# Default I/O data sizes
DEFAULT_OUTPUT_SIZE = 32  # bytes
DEFAULT_INPUT_SIZE = 32   # bytes

# Frame ID ranges
FRAME_ID_RT_START = 0x8000
FRAME_ID_RT_END = 0xBFFF


@register_engine(ProtocolType.PROFINET)
class ProfinetEngine(ProtocolEngine):
    """PROFINET RT protocol engine.

    Generates realistic PROFINET traffic including:
    - DCP discovery phase (Identify request/response)
    - RT cyclic I/O data exchange

    Configuration options:
    - frame_id_output: Frame ID for output data (default: 0x8000)
    - frame_id_input: Frame ID for input data (default: 0x8001)
    - output_data_size: Output data size in bytes (default: 32)
    - input_data_size: Input data size in bytes (default: 32)
    - cycle_time_ms: RT cycle time in milliseconds (default: 1.0)
    - vlan_id: Optional VLAN ID for tagged frames
    - device_name: PROFINET station name
    - vendor_id: Vendor ID (default: 0x002A)
    - device_id: Device ID (default: 0x0001)
    - skip_dcp: Skip DCP discovery phase (default: False)
    """

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.PROFINET

    def create_initial_state(self, flow: FlowContext) -> ConversationState:
        """Create initial conversation state for PROFINET."""
        config = flow.config

        # Extract configuration
        frame_id_output = config.get("frame_id_output", FRAME_ID_RT_START)
        frame_id_input = config.get("frame_id_input", FRAME_ID_RT_START + 1)
        output_size = config.get("output_data_size", DEFAULT_OUTPUT_SIZE)
        input_size = config.get("input_data_size", DEFAULT_INPUT_SIZE)

        # Create RT cycle state tracker
        rt_state = RTCycleState(
            frame_id_output=frame_id_output,
            frame_id_input=frame_id_input,
            output_data_size=output_size,
            input_data_size=input_size,
        )

        return ConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            transaction_id=random.randint(1, 0xFFFFFFFF),
            sequence_number=0,
            custom_data={
                "rt_state": rt_state,
                "dcp_xid": random.randint(1, 0xFFFFFFFF),
                "device_name": config.get("device_name", f"device-{flow.destination.device_id[:8]}"),
                "vendor_id": config.get("vendor_id", 0x002A),
                "device_id": config.get("device_id", 0x0001),
                "vlan_id": config.get("vlan_id"),
                "cycle_time_ms": config.get("cycle_time_ms", DEFAULT_CYCLE_TIME_MS),
            },
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate PROFINET startup sequence.

        Includes DCP discovery (unless skipped) and connection establishment.
        """
        config = flow.config
        skip_dcp = config.get("skip_dcp", False)
        current_time = start_time_ms

        if not skip_dcp:
            # Phase 1: DCP Identify Request (Controller -> Multicast)
            dcp_request = build_dcp_identify_request_packet(
                src=flow.source,
                dst_mac="01:0E:CF:00:00:00",  # PROFINET DCP multicast
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=dcp_request,
                direction="request",
                metadata={
                    "type": "dcp_identify_request",
                    "xid": state.custom_data["dcp_xid"],
                },
            )

            # Phase 2: DCP Identify Response (Device -> Controller)
            # Use fingerprint for response delay if available
            applicator = flow.destination.fingerprint_applicator
            timing_sample = applicator.get_response_delay()
            response_delay = timing_sample.delay_ms if timing_sample.delay_ms > 5 else random.uniform(10.0, 50.0)
            current_time += response_delay

            # Use fingerprinted DCP response if fingerprint available
            if flow.destination.vendor_fingerprint:
                dcp_response = build_dcp_identify_response_packet_fingerprinted(
                    src=flow.destination,
                    dst=flow.source,
                    xid=state.custom_data["dcp_xid"],
                )
            else:
                dcp_response = build_dcp_identify_response_packet(
                    src=flow.destination,
                    dst=flow.source,
                    xid=state.custom_data["dcp_xid"],
                    device_name=state.custom_data["device_name"],
                    vendor_id=state.custom_data["vendor_id"],
                    device_id=state.custom_data["device_id"],
                )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=dcp_response,
                direction="response",
                metadata={
                    "type": "dcp_identify_response",
                    "xid": state.custom_data["dcp_xid"],
                    "device_name": state.custom_data["device_name"],
                    "is_fingerprinted": bool(flow.destination.vendor_fingerprint),
                },
            )

            # Small delay before connection establishment
            current_time += random.uniform(5.0, 20.0)

        # Note: Full PROFINET connection establishment (RPC-based AR setup)
        # is complex and involves multiple steps. For traffic simulation,
        # we skip directly to RT data exchange after DCP.
        # In a complete implementation, this would include:
        # - Connect Request/Response
        # - Write Request/Response (parameters)
        # - Control Command (Application Ready)

        state.state_name = "data_exchange"

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate PROFINET RT cyclic I/O data exchange.

        A single cycle includes:
        1. Output frame: Controller -> Device (process data to device)
        2. Input frame: Device -> Controller (process data from device)
        """
        rt_state: RTCycleState = state.custom_data["rt_state"]
        vlan_id = state.custom_data.get("vlan_id")
        timing_model = flow.timing_model

        # Increment cycle counter
        cycle_counter = rt_state.increment_cycle()

        # Generate output data (simulated process data)
        output_data = self._generate_process_data(
            rt_state.output_data_size,
            flow.payload_template,
            "output",
        )

        # Build Output frame (Controller -> Device)
        output_packet = build_rt_packet(
            src=flow.source,
            dst=flow.destination,
            frame_id=rt_state.frame_id_output,
            data=output_data,
            cycle_counter=cycle_counter,
            data_status=DataStatus.VALID_RUN_PRIMARY,
            vlan_id=vlan_id,
        )

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=output_packet,
            direction="request",
            metadata={
                "type": "rt_output",
                "frame_id": rt_state.frame_id_output,
                "cycle_counter": cycle_counter,
                "data_size": rt_state.output_data_size,
            },
        )

        # Calculate input frame timing
        # PROFINET RT typically has very low jitter within a cycle
        response_delay = get_response_delay(timing_model)
        if response_delay < 0.1:
            response_delay = random.uniform(0.05, 0.2)  # 50-200µs typical

        input_time = cycle_time_ms + response_delay

        # Generate input data (simulated sensor data)
        input_data = self._generate_process_data(
            rt_state.input_data_size,
            flow.payload_template,
            "input",
        )

        # Build Input frame (Device -> Controller)
        input_packet = build_rt_packet(
            src=flow.destination,
            dst=flow.source,
            frame_id=rt_state.frame_id_input,
            data=input_data,
            cycle_counter=cycle_counter,
            data_status=DataStatus.VALID_RUN_PRIMARY,
            vlan_id=vlan_id,
        )

        yield PacketEvent(
            timestamp_ms=input_time,
            flow_id=flow.flow_id,
            packet_bytes=input_packet,
            direction="response",
            metadata={
                "type": "rt_input",
                "frame_id": rt_state.frame_id_input,
                "cycle_counter": cycle_counter,
                "data_size": rt_state.input_data_size,
            },
        )

        # Update state
        state.sequence_number = cycle_counter

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate PROFINET shutdown sequence.

        In PROFINET, shutdown involves:
        1. Sending final RT frames with "Stop" status
        2. Release Request/Response (RPC-based)

        For simplicity, we send final frames with modified status.
        """
        rt_state: RTCycleState = state.custom_data["rt_state"]
        vlan_id = state.custom_data.get("vlan_id")

        # Increment cycle for shutdown
        cycle_counter = rt_state.increment_cycle()

        # Final output frame with STOP status
        output_data = bytes(rt_state.output_data_size)  # Zero data
        output_packet = build_rt_packet(
            src=flow.source,
            dst=flow.destination,
            frame_id=rt_state.frame_id_output,
            data=output_data,
            cycle_counter=cycle_counter,
            data_status=DataStatus.VALID_STOP_PRIMARY,  # Stop status
            vlan_id=vlan_id,
        )

        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=output_packet,
            direction="request",
            metadata={
                "type": "rt_output_stop",
                "frame_id": rt_state.frame_id_output,
                "cycle_counter": cycle_counter,
            },
        )

        # Final input frame with STOP status
        response_time = start_time_ms + random.uniform(0.05, 0.2)
        input_data = bytes(rt_state.input_data_size)

        input_packet = build_rt_packet(
            src=flow.destination,
            dst=flow.source,
            frame_id=rt_state.frame_id_input,
            data=input_data,
            cycle_counter=cycle_counter,
            data_status=DataStatus.VALID_STOP_PRIMARY,
            vlan_id=vlan_id,
        )

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=input_packet,
            direction="response",
            metadata={
                "type": "rt_input_stop",
                "frame_id": rt_state.frame_id_input,
                "cycle_counter": cycle_counter,
            },
        )

        state.state_name = "offline"

    def validate_config(self, config: dict) -> list[str]:
        """Validate PROFINET configuration."""
        errors = []

        # Validate frame IDs
        frame_id_output = config.get("frame_id_output", FRAME_ID_RT_START)
        frame_id_input = config.get("frame_id_input", FRAME_ID_RT_START + 1)

        if not (FRAME_ID_RT_START <= frame_id_output <= FRAME_ID_RT_END):
            errors.append(
                f"frame_id_output must be between {FRAME_ID_RT_START:#x} and {FRAME_ID_RT_END:#x}"
            )

        if not (FRAME_ID_RT_START <= frame_id_input <= FRAME_ID_RT_END):
            errors.append(
                f"frame_id_input must be between {FRAME_ID_RT_START:#x} and {FRAME_ID_RT_END:#x}"
            )

        if frame_id_output == frame_id_input:
            errors.append("frame_id_output and frame_id_input must be different")

        # Validate data sizes
        output_size = config.get("output_data_size", DEFAULT_OUTPUT_SIZE)
        input_size = config.get("input_data_size", DEFAULT_INPUT_SIZE)

        if output_size < 1 or output_size > 1440:
            errors.append("output_data_size must be between 1 and 1440 bytes")

        if input_size < 1 or input_size > 1440:
            errors.append("input_data_size must be between 1 and 1440 bytes")

        # Validate cycle time
        cycle_time = config.get("cycle_time_ms", DEFAULT_CYCLE_TIME_MS)
        if cycle_time < MIN_CYCLE_TIME_MS or cycle_time > MAX_CYCLE_TIME_MS:
            errors.append(
                f"cycle_time_ms must be between {MIN_CYCLE_TIME_MS} and {MAX_CYCLE_TIME_MS}"
            )

        # Validate VLAN ID if present
        vlan_id = config.get("vlan_id")
        if vlan_id is not None:
            if not isinstance(vlan_id, int) or vlan_id < 1 or vlan_id > 4094:
                errors.append("vlan_id must be between 1 and 4094")

        # Validate device name
        device_name = config.get("device_name", "")
        if device_name:
            if len(device_name) > 240:
                errors.append("device_name must be 240 characters or less")
            # PROFINET device names must be DNS-compatible
            import re
            if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$|^[a-z0-9]$', device_name.lower()):
                errors.append(
                    "device_name must be DNS-compatible (lowercase alphanumeric and hyphens)"
                )

        return errors

    def _generate_process_data(
        self,
        size: int,
        payload_template: dict | None,
        direction: str,
    ) -> bytes:
        """Generate simulated process data.

        Args:
            size: Data size in bytes
            payload_template: Optional template with data patterns
            direction: "input" or "output"

        Returns:
            Generated process data bytes
        """
        if payload_template:
            pattern = payload_template.get(f"{direction}_pattern", "random")
            if pattern == "zeros":
                return bytes(size)
            elif pattern == "ones":
                return bytes([0xFF] * size)
            elif pattern == "counter":
                return bytes([i % 256 for i in range(size)])
            elif isinstance(pattern, list):
                # Use provided byte values, cycling if needed
                return bytes([pattern[i % len(pattern)] for i in range(size)])

        # Default: random but realistic-looking data
        # Mix of status bytes and analog values
        data = bytearray(size)
        for i in range(size):
            if i < 2:
                # First bytes often status/control
                data[i] = random.choice([0x00, 0x01, 0x03, 0x07, 0x0F])
            elif i % 2 == 0:
                # Even bytes: high byte of analog values
                data[i] = random.randint(0, 127)  # Positive analog range
            else:
                # Odd bytes: low byte of analog values
                data[i] = random.randint(0, 255)

        return bytes(data)

    def generate_alarm_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
        alarm_type: int = ALARM_TYPE_DIAGNOSTIC,
        slot_number: int = 1,
        subslot_number: int = 1,
    ) -> Iterator[PacketEvent]:
        """Generate PROFINET RTA alarm sequence.

        A complete alarm sequence includes:
        1. Alarm notification from device
        2. Alarm acknowledgment from controller

        Args:
            flow: Flow context
            state: Conversation state
            start_time_ms: Start timestamp
            alarm_type: Type of alarm (diagnostic, process, status)
            slot_number: Slot number where alarm occurred
            subslot_number: Subslot number where alarm occurred

        Yields:
            PacketEvent for alarm sequence
        """
        vlan_id = state.custom_data.get("vlan_id")

        # Get alarm sequence number
        alarm_seq = state.custom_data.get("alarm_seq", 1)
        state.custom_data["alarm_seq"] = (alarm_seq + 1) % 256

        # Alarm notification from device to controller
        alarm_packet = build_rta_alarm_packet(
            src=flow.destination,  # Device sends alarm
            dst=flow.source,  # Controller receives
            alarm_type=alarm_type,
            slot_number=slot_number,
            subslot_number=subslot_number,
            send_seq_num=alarm_seq,
            ack_seq_num=0,
            vlan_id=vlan_id,
        )

        yield PacketEvent(
            timestamp_ms=start_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=alarm_packet,
            direction="response",  # Device initiated
            metadata={
                "type": "rta_alarm",
                "alarm_type": alarm_type,
                "slot": slot_number,
                "subslot": subslot_number,
                "sequence": alarm_seq,
            },
        )

        # Alarm acknowledgment from controller
        # Response delay from fingerprint or default
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        ack_delay = timing_sample.delay_ms if timing_sample.delay_ms > 0.5 else random.uniform(1.0, 5.0)
        ack_time = start_time_ms + ack_delay

        ack_packet = build_rta_alarm_ack_packet(
            src=flow.source,  # Controller sends ACK
            dst=flow.destination,  # Device receives
            send_seq_num=0,
            ack_seq_num=alarm_seq,  # Acknowledge received alarm
            vlan_id=vlan_id,
        )

        yield PacketEvent(
            timestamp_ms=ack_time,
            flow_id=flow.flow_id,
            packet_bytes=ack_packet,
            direction="request",  # Controller initiated
            metadata={
                "type": "rta_alarm_ack",
                "acked_sequence": alarm_seq,
            },
        )

    def generate_diagnostic_alarm(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
        slot_number: int = 1,
    ) -> Iterator[PacketEvent]:
        """Generate a diagnostic alarm (hardware/software issue).

        Args:
            flow: Flow context
            state: Conversation state
            start_time_ms: Start timestamp
            slot_number: Slot number with diagnostic issue

        Yields:
            PacketEvent for diagnostic alarm
        """
        yield from self.generate_alarm_sequence(
            flow, state, start_time_ms,
            alarm_type=ALARM_TYPE_DIAGNOSTIC,
            slot_number=slot_number,
            subslot_number=1,
        )

    def generate_process_alarm(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
        slot_number: int = 1,
    ) -> Iterator[PacketEvent]:
        """Generate a process alarm (application-level event).

        Args:
            flow: Flow context
            state: Conversation state
            start_time_ms: Start timestamp
            slot_number: Slot number with process alarm

        Yields:
            PacketEvent for process alarm
        """
        yield from self.generate_alarm_sequence(
            flow, state, start_time_ms,
            alarm_type=ALARM_TYPE_PROCESS,
            slot_number=slot_number,
            subslot_number=1,
        )

    def inject_random_alarm(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Inject a random alarm based on fingerprint error probability.

        Uses the device fingerprint to determine if an alarm should be
        injected and what type.

        Args:
            flow: Flow context
            state: Conversation state
            start_time_ms: Start timestamp

        Yields:
            PacketEvent for alarm if injected
        """
        applicator = flow.destination.fingerprint_applicator

        # Check if we should inject an error/alarm
        if not applicator.should_inject_error():
            return

        # Choose random alarm type
        alarm_types = [ALARM_TYPE_DIAGNOSTIC, ALARM_TYPE_PROCESS, ALARM_TYPE_STATUS]
        alarm_type = random.choice(alarm_types)

        # Choose random slot (1-4 typical)
        slot_number = random.randint(1, 4)

        yield from self.generate_alarm_sequence(
            flow, state, start_time_ms,
            alarm_type=alarm_type,
            slot_number=slot_number,
            subslot_number=1,
        )

    def generate_dcp_discovery_sequence(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate PROFINET DCP discovery sequence for device fingerprinting.

        This generates DCP Identify request/response that contains device identity
        information used by scanners like Cisco Cyber Vision:
        - Station name
        - Vendor ID / Device ID
        - Device role
        - OEM Device ID (includes firmware version - key for CVE detection)

        This is called by the orchestrator before main traffic to ensure
        device identity is visible to network scanners.

        Args:
            flow: Flow context
            state: Conversation state
            start_time_ms: Start timestamp

        Yields:
            PacketEvent for DCP discovery sequence
        """
        current_time = start_time_ms

        # DCP Identify Request (Controller -> Multicast)
        # This simulates a controller/scanner querying for devices
        dcp_request = build_dcp_identify_request_packet(
            src=flow.source,
            dst_mac="01:0E:CF:00:00:00",  # PROFINET DCP multicast
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=dcp_request,
            direction="request",
            metadata={
                "type": "dcp_identify_request",
                "xid": state.custom_data.get("dcp_xid", 1),
                "discovery_phase": True,
            },
        )

        # DCP Identify Response (Device -> Controller)
        # Response delay based on device fingerprint timing
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_delay = max(timing_sample.delay_ms, random.uniform(10.0, 50.0))
        current_time += response_delay

        # Use fingerprinted DCP response for realistic identity
        if flow.destination.vendor_fingerprint:
            dcp_response = build_dcp_identify_response_packet_fingerprinted(
                src=flow.destination,
                dst=flow.source,
                xid=state.custom_data.get("dcp_xid", 1),
            )
        else:
            dcp_response = build_dcp_identify_response_packet(
                src=flow.destination,
                dst=flow.source,
                xid=state.custom_data.get("dcp_xid", 1),
                device_name=state.custom_data.get("device_name", "device"),
                vendor_id=state.custom_data.get("vendor_id", 0x002A),
                device_id=state.custom_data.get("device_id", 0x0001),
            )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=dcp_response,
            direction="response",
            metadata={
                "type": "dcp_identify_response",
                "xid": state.custom_data.get("dcp_xid", 1),
                "device_name": state.custom_data.get("device_name", "device"),
                "is_fingerprinted": bool(flow.destination.vendor_fingerprint),
                "discovery_phase": True,
            },
        )
