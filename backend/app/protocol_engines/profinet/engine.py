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
    RTClass,
    IRT_FRAME_ID_MIN,
    IRT_FRAME_ID_MAX,
    build_dcp_identify_request_packet,
    build_dcp_identify_response_packet,
    build_dcp_identify_response_packet_fingerprinted,
    build_rt_packet,
    build_irt_packet,
    build_rta_alarm_ack_packet,
    build_rta_alarm_packet,
    build_ptcp_sync_frame,
    build_ptcp_followup_frame,
    build_ptcp_delay_request,
    build_ptcp_delay_response,
    generate_io_data,
    allocate_irt_frame_id,
    IRTCycleState,
)
from app.protocol_engines.profinet.states import RTCycleState, IRTSyncState, IRTPhaseConfig
from app.protocol_engines.jitter import apply_jitter, get_response_delay
from app.protocol_engines.types import (
    ConversationState,
    ConversationStateBase,
    FlowContext,
    PacketEvent,
    ProfinetConversationState,
    ProtocolType,
)


# Default PROFINET RT cycle times (in milliseconds)
DEFAULT_CYCLE_TIME_MS = 1.0  # 1ms typical for RT Class 1
MIN_CYCLE_TIME_MS = 0.25     # 250µs minimum
MAX_CYCLE_TIME_MS = 512.0    # 512ms maximum

# Default IRT cycle times (in microseconds for precision)
DEFAULT_IRT_CYCLE_TIME_US = 250  # 250µs typical for IRT
MIN_IRT_CYCLE_TIME_US = 31.25    # 31.25µs minimum (PROFINET V2.3)
MAX_IRT_CYCLE_TIME_US = 4000     # 4ms maximum for IRT

# Default I/O data sizes
DEFAULT_OUTPUT_SIZE = 32  # bytes
DEFAULT_INPUT_SIZE = 32   # bytes

# Frame ID ranges
FRAME_ID_RT_START = 0x8000
FRAME_ID_RT_END = 0xBFFF

# IRT default subdomain UUID (can be overridden in config)
DEFAULT_IRT_SUBDOMAIN_UUID = bytes([
    0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
    0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10
])


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

        # Determine RT class (1, 2, or 3/IRT)
        rt_class = config.get("rt_class", RTClass.RT_CLASS_1)

        # Extract configuration
        output_size = config.get("output_data_size", DEFAULT_OUTPUT_SIZE)
        input_size = config.get("input_data_size", DEFAULT_INPUT_SIZE)

        # Handle IRT (RT Class 3) separately
        if rt_class == RTClass.RT_CLASS_3:
            # IRT uses frame IDs in range 0x0100-0x7FFF
            slot = config.get("slot", 1)
            subslot = config.get("subslot", 1)
            frame_id_output = config.get(
                "frame_id_output",
                allocate_irt_frame_id(slot, subslot, "output")
            )
            frame_id_input = config.get(
                "frame_id_input",
                allocate_irt_frame_id(slot, subslot, "input")
            )

            # Create IRT cycle state tracker with timing info
            cycle_time_us = config.get("cycle_time_us", DEFAULT_IRT_CYCLE_TIME_US)
            rt_state = IRTCycleState(
                frame_id_output=frame_id_output,
                frame_id_input=frame_id_input,
                output_data_size=output_size,
                input_data_size=input_size,
                cycle_time_us=cycle_time_us,
                send_clock_factor=config.get("send_clock_factor", 32),
                reduction_ratio=config.get("reduction_ratio", 1),
                phase=config.get("phase", 0),
            )

            # Create IRT sync state if this is a sync master
            is_sync_master = config.get("is_sync_master", False)
            subdomain_uuid = config.get("subdomain_uuid", DEFAULT_IRT_SUBDOMAIN_UUID)
            if isinstance(subdomain_uuid, str):
                subdomain_uuid = bytes.fromhex(subdomain_uuid.replace("-", ""))
            irt_sync_state = IRTSyncState(
                subdomain_uuid=subdomain_uuid,
                is_sync_master=is_sync_master,
                cycle_time_us=cycle_time_us,
            )

            # Create IRT phase configuration
            irt_phase_config = IRTPhaseConfig(
                cycle_time_us=cycle_time_us,
                red_phase_duration_us=config.get("red_phase_duration_us", cycle_time_us // 4),
                orange_phase_duration_us=config.get("orange_phase_duration_us", cycle_time_us // 16),
            )

            custom_data = {
                "rt_state": rt_state,
                "irt_sync_state": irt_sync_state,
                "irt_phase_config": irt_phase_config,
                "rt_class": rt_class,
                "dcp_xid": random.randint(1, 0xFFFFFFFF),
                "device_name": config.get("device_name", f"device-{flow.destination.device_id[:8]}"),
                "vendor_id": config.get("vendor_id", 0x002A),
                "device_id": config.get("device_id", 0x0001),
                "vlan_id": config.get("vlan_id", 0),  # VLAN required for IRT
                "cycle_time_ms": cycle_time_us / 1000.0,  # Convert to ms for compatibility
                "cycle_time_us": cycle_time_us,
                "is_sync_master": is_sync_master,
            }
        else:
            # Standard RT Class 1 or 2
            frame_id_output = config.get("frame_id_output", FRAME_ID_RT_START)
            frame_id_input = config.get("frame_id_input", FRAME_ID_RT_START + 1)

            # Create RT cycle state tracker
            rt_state = RTCycleState(
                frame_id_output=frame_id_output,
                frame_id_input=frame_id_input,
                output_data_size=output_size,
                input_data_size=input_size,
                rt_class=rt_class,
            )

            custom_data = {
                "rt_state": rt_state,
                "rt_class": rt_class,
                "dcp_xid": random.randint(1, 0xFFFFFFFF),
                "device_name": config.get("device_name", f"device-{flow.destination.device_id[:8]}"),
                "vendor_id": config.get("vendor_id", 0x002A),
                "device_id": config.get("device_id", 0x0001),
                "vlan_id": config.get("vlan_id"),
                "cycle_time_ms": config.get("cycle_time_ms", DEFAULT_CYCLE_TIME_MS),
            }

        return ConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            transaction_id=random.randint(1, 0xFFFFFFFF),
            sequence_number=0,
            custom_data=custom_data,
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

        # For IRT (RT Class 3), perform PTCP synchronization startup
        rt_class = state.custom_data.get("rt_class", RTClass.RT_CLASS_1)
        if rt_class == RTClass.RT_CLASS_3:
            yield from self._generate_irt_sync_startup(flow, state, current_time)
            # Update time after IRT sync startup
            current_time = state.custom_data.get("last_sync_time_ms", current_time) + 10

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

        For IRT (RT Class 3), this also includes PTCP sync frames.
        """
        rt_class = state.custom_data.get("rt_class", RTClass.RT_CLASS_1)
        vlan_id = state.custom_data.get("vlan_id")
        timing_model = flow.timing_model

        # Dispatch to IRT-specific handler if RT Class 3
        if rt_class == RTClass.RT_CLASS_3:
            yield from self._generate_irt_poll_cycle(flow, state, cycle_time_ms)
            return

        # Standard RT Class 1/2 handling
        rt_state: RTCycleState = state.custom_data["rt_state"]

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
                "rt_class": rt_class,
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
                "rt_class": rt_class,
            },
        )

        # Update state
        state.sequence_number = cycle_counter

    def _generate_irt_poll_cycle(
        self,
        flow: FlowContext,
        state: ConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate PROFINET IRT (RT Class 3) cyclic data exchange.

        IRT adds:
        - PTCP sync frames (if sync master)
        - Precise timing within red phase
        - VLAN-tagged frames with priority 6
        - Periodic delay re-measurement for drift compensation
        """
        irt_state: IRTCycleState = state.custom_data["rt_state"]
        irt_sync_state: IRTSyncState = state.custom_data.get("irt_sync_state")
        irt_phase_config: IRTPhaseConfig = state.custom_data.get("irt_phase_config")
        vlan_id = state.custom_data.get("vlan_id", 0)
        is_sync_master = state.custom_data.get("is_sync_master", False)
        line_delay_ns = state.custom_data.get("line_delay_ns", 0)

        # Increment cycle counter
        cycle_counter = irt_state.increment_cycle()

        # Current time in nanoseconds within cycle
        current_time_us = 0
        current_time_offset_ms = 0.0

        # Phase 1: PTCP Sync (if sync master, every 8 cycles)
        if is_sync_master and irt_sync_state and (cycle_counter % 8 == 0):
            sync_seq = irt_sync_state.increment_sync_sequence()

            # Build PTCP Sync frame with measured line delay
            sync_packet = build_ptcp_sync_frame(
                src=flow.source,
                dst=flow.destination,
                sequence_id=sync_seq,
                delay_ns=line_delay_ns,  # Include measured delay
                subdomain_uuid=irt_sync_state.subdomain_uuid,
                vlan_id=vlan_id,
            )

            yield PacketEvent(
                timestamp_ms=cycle_time_ms,
                flow_id=flow.flow_id,
                packet_bytes=sync_packet,
                direction="request",
                metadata={
                    "type": "ptcp_sync",
                    "sequence_id": sync_seq,
                    "cycle_counter": cycle_counter,
                    "line_delay_ns": line_delay_ns,
                },
            )

            # PTCP FollowUp follows immediately
            # Calculate precise timestamp (simulated)
            precise_ns = int(cycle_time_ms * 1_000_000)

            followup_packet = build_ptcp_followup_frame(
                src=flow.source,
                dst=flow.destination,
                sequence_id=sync_seq,
                precise_timestamp_ns=precise_ns,
                subdomain_uuid=irt_sync_state.subdomain_uuid,
                vlan_id=vlan_id,
            )

            yield PacketEvent(
                timestamp_ms=cycle_time_ms + 0.001,  # 1µs later
                flow_id=flow.flow_id,
                packet_bytes=followup_packet,
                direction="request",
                metadata={
                    "type": "ptcp_followup",
                    "sequence_id": sync_seq,
                    "precise_timestamp_ns": precise_ns,
                },
            )

            current_time_us = 5  # Sync takes ~5µs
            current_time_offset_ms = 0.006  # 6µs total for sync+followup

        # Phase 1b: Periodic delay re-measurement (every 1000 cycles to compensate for drift)
        # This is important for maintaining sub-microsecond accuracy over time
        delay_remeasure_interval = state.custom_data.get("delay_remeasure_interval", 1000)
        if cycle_counter > 0 and (cycle_counter % delay_remeasure_interval == 0):
            yield from self._generate_delay_remeasurement(
                flow, state, cycle_time_ms + current_time_offset_ms, vlan_id
            )
            current_time_offset_ms += 0.3  # ~300µs for delay measurement

        # Phase 2: IRT data exchange in red phase
        # Calculate send time offset based on phase configuration
        if irt_phase_config:
            send_offset_us = irt_state.get_send_time_offset_ns() / 1000
        else:
            send_offset_us = 10  # Default 10µs offset

        # Account for any time consumed by sync/delay operations
        output_time_ms = cycle_time_ms + current_time_offset_ms + (current_time_us + send_offset_us) / 1000

        # Generate output data
        output_data = self._generate_process_data(
            irt_state.output_data_size,
            flow.payload_template,
            "output",
        )

        # Build IRT Output frame (Controller -> Device)
        output_packet = build_irt_packet(
            src=flow.source,
            dst=flow.destination,
            frame_id=irt_state.frame_id_output,
            data=output_data,
            cycle_counter=cycle_counter,
            data_status=DataStatus.VALID_RUN_PRIMARY,
            vlan_id=vlan_id,
            priority=6,
        )

        yield PacketEvent(
            timestamp_ms=output_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=output_packet,
            direction="request",
            metadata={
                "type": "irt_output",
                "frame_id": irt_state.frame_id_output,
                "cycle_counter": cycle_counter,
                "data_size": irt_state.output_data_size,
                "rt_class": 3,
                "cycle_time_us": irt_state.cycle_time_us,
                "phase": irt_state.phase,
                "send_offset_us": send_offset_us,
                "line_delay_ns": line_delay_ns,
                "is_synchronized": state.custom_data.get("irt_synchronized", False),
            },
        )

        # IRT response timing is very precise (sub-microsecond jitter)
        # Typical IRT response within same cycle, a few µs after output
        response_offset_us = random.uniform(5, 20)  # 5-20µs typical for IRT
        input_time_ms = output_time_ms + response_offset_us / 1000

        # Generate input data
        input_data = self._generate_process_data(
            irt_state.input_data_size,
            flow.payload_template,
            "input",
        )

        # Build IRT Input frame (Device -> Controller)
        input_packet = build_irt_packet(
            src=flow.destination,
            dst=flow.source,
            frame_id=irt_state.frame_id_input,
            data=input_data,
            cycle_counter=cycle_counter,
            data_status=DataStatus.VALID_RUN_PRIMARY,
            vlan_id=vlan_id,
            priority=6,
        )

        yield PacketEvent(
            timestamp_ms=input_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=input_packet,
            direction="response",
            metadata={
                "type": "irt_input",
                "frame_id": irt_state.frame_id_input,
                "cycle_counter": cycle_counter,
                "data_size": irt_state.input_data_size,
                "rt_class": 3,
                "response_time_us": response_offset_us,
                "phase": irt_state.phase,
                "line_delay_ns": line_delay_ns,
            },
        )

        # Update state
        state.sequence_number = cycle_counter

    def _generate_irt_sync_startup(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate IRT-specific synchronization startup sequence.

        Before IRT data exchange can begin, devices must:
        1. Receive PTCP Sync frames (if sync slave) or send them (if sync master)
        2. Perform delay measurement to calculate line delays
        3. Establish synchronized timing across the IRT domain

        This generates the initial synchronization handshake required
        for deterministic IRT operation.

        Args:
            flow: Flow context
            state: Conversation state
            start_time_ms: Start timestamp

        Yields:
            PacketEvent for IRT synchronization sequence
        """
        irt_sync_state: IRTSyncState = state.custom_data.get("irt_sync_state")
        vlan_id = state.custom_data.get("vlan_id", 0)
        is_sync_master = state.custom_data.get("is_sync_master", False)
        current_time = start_time_ms

        if not irt_sync_state:
            return

        # Phase 1: Initial PTCP Sync/FollowUp (sync master sends, slave receives)
        if is_sync_master:
            # Sync master sends initial sync frames to establish timing
            sync_seq = irt_sync_state.increment_sync_sequence()

            # Build initial PTCP Sync frame
            sync_packet = build_ptcp_sync_frame(
                src=flow.source,
                dst=flow.destination,
                sequence_id=sync_seq,
                delay_ns=0,  # Initial delay unknown
                subdomain_uuid=irt_sync_state.subdomain_uuid,
                vlan_id=vlan_id,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=sync_packet,
                direction="request",
                metadata={
                    "type": "ptcp_sync_initial",
                    "sequence_id": sync_seq,
                    "phase": "irt_startup",
                },
            )

            # FollowUp with precise timestamp
            precise_ns = int(current_time * 1_000_000)
            followup_packet = build_ptcp_followup_frame(
                src=flow.source,
                dst=flow.destination,
                sequence_id=sync_seq,
                precise_timestamp_ns=precise_ns,
                subdomain_uuid=irt_sync_state.subdomain_uuid,
                vlan_id=vlan_id,
            )

            current_time += 0.001  # 1µs for followup

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=followup_packet,
                direction="request",
                metadata={
                    "type": "ptcp_followup_initial",
                    "sequence_id": sync_seq,
                    "precise_timestamp_ns": precise_ns,
                    "phase": "irt_startup",
                },
            )

            current_time += 0.5  # 500µs before delay measurement

        # Phase 2: PTCP Delay Measurement
        # Device sends Delay Request to measure line delay to sync master
        delay_seq = random.randint(1, 65535)
        delay_request_time_ms = current_time

        delay_request_packet = build_ptcp_delay_request(
            src=flow.destination,  # Device sends request
            dst=flow.source,  # To sync master/controller
            sequence_id=delay_seq,
            vlan_id=vlan_id,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=delay_request_packet,
            direction="response",  # From device perspective
            metadata={
                "type": "ptcp_delay_request",
                "sequence_id": delay_seq,
                "phase": "irt_startup",
            },
        )

        # Phase 3: Delay Response from sync master
        # Simulate realistic processing delay for delay response
        processing_delay_us = random.uniform(50, 200)  # 50-200µs typical
        current_time += processing_delay_us / 1000

        # Calculate timestamps for delay calculation
        # t1 = delay request send time (at device)
        # t2 = delay request receive time (at master)
        # t3 = delay response send time (at master)
        # t4 = delay response receive time (at device)
        # Line delay = ((t2 - t1) + (t4 - t3)) / 2

        request_receipt_ns = int(delay_request_time_ms * 1_000_000) + random.randint(500, 2000)
        response_origin_ns = int(current_time * 1_000_000)

        delay_response_packet = build_ptcp_delay_response(
            src=flow.source,  # Sync master responds
            dst=flow.destination,  # To requesting device
            sequence_id=delay_seq,
            request_receipt_timestamp_ns=request_receipt_ns,
            response_origin_timestamp_ns=response_origin_ns,
            vlan_id=vlan_id,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=delay_response_packet,
            direction="request",
            metadata={
                "type": "ptcp_delay_response",
                "sequence_id": delay_seq,
                "request_receipt_ns": request_receipt_ns,
                "response_origin_ns": response_origin_ns,
                "phase": "irt_startup",
            },
        )

        # Calculate simulated line delay
        line_delay_ns = random.randint(200, 1500)  # 200ns-1.5µs typical for Ethernet
        state.custom_data["line_delay_ns"] = line_delay_ns
        state.custom_data["irt_synchronized"] = True

        current_time += 0.5  # 500µs settling time

        # Phase 4: Second Sync/FollowUp with delay compensation (if sync master)
        if is_sync_master:
            sync_seq = irt_sync_state.increment_sync_sequence()

            sync_packet = build_ptcp_sync_frame(
                src=flow.source,
                dst=flow.destination,
                sequence_id=sync_seq,
                delay_ns=line_delay_ns,  # Include measured delay
                subdomain_uuid=irt_sync_state.subdomain_uuid,
                vlan_id=vlan_id,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=sync_packet,
                direction="request",
                metadata={
                    "type": "ptcp_sync_compensated",
                    "sequence_id": sync_seq,
                    "delay_ns": line_delay_ns,
                    "phase": "irt_startup",
                },
            )

            precise_ns = int(current_time * 1_000_000)
            followup_packet = build_ptcp_followup_frame(
                src=flow.source,
                dst=flow.destination,
                sequence_id=sync_seq,
                precise_timestamp_ns=precise_ns,
                subdomain_uuid=irt_sync_state.subdomain_uuid,
                vlan_id=vlan_id,
            )

            current_time += 0.001

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=followup_packet,
                direction="request",
                metadata={
                    "type": "ptcp_followup_compensated",
                    "sequence_id": sync_seq,
                    "precise_timestamp_ns": precise_ns,
                    "phase": "irt_startup",
                },
            )

        # Store final sync time for caller
        state.custom_data["last_sync_time_ms"] = current_time

    def _generate_delay_remeasurement(
        self,
        flow: FlowContext,
        state: ConversationState,
        start_time_ms: float,
        vlan_id: int,
    ) -> Iterator[PacketEvent]:
        """Generate periodic delay re-measurement sequence.

        IRT networks periodically re-measure line delays to compensate
        for drift due to temperature changes, cable aging, etc.
        This maintains sub-microsecond accuracy over time.

        Args:
            flow: Flow context
            state: Conversation state
            start_time_ms: Start timestamp
            vlan_id: VLAN ID for frames

        Yields:
            PacketEvent for delay re-measurement sequence
        """
        current_time = start_time_ms

        # Delay Request from device
        delay_seq = random.randint(1, 65535)
        delay_request_time_ms = current_time

        delay_request_packet = build_ptcp_delay_request(
            src=flow.destination,  # Device sends request
            dst=flow.source,  # To sync master/controller
            sequence_id=delay_seq,
            vlan_id=vlan_id,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=delay_request_packet,
            direction="response",
            metadata={
                "type": "ptcp_delay_request",
                "sequence_id": delay_seq,
                "phase": "delay_remeasure",
            },
        )

        # Delay Response from sync master
        # Simulate realistic turnaround time
        turnaround_us = random.uniform(30, 100)  # 30-100µs typical
        current_time += turnaround_us / 1000

        # Timestamps for delay calculation
        request_receipt_ns = int(delay_request_time_ms * 1_000_000) + random.randint(200, 800)
        response_origin_ns = int(current_time * 1_000_000)

        delay_response_packet = build_ptcp_delay_response(
            src=flow.source,
            dst=flow.destination,
            sequence_id=delay_seq,
            request_receipt_timestamp_ns=request_receipt_ns,
            response_origin_timestamp_ns=response_origin_ns,
            vlan_id=vlan_id,
        )

        yield PacketEvent(
            timestamp_ms=current_time,
            flow_id=flow.flow_id,
            packet_bytes=delay_response_packet,
            direction="request",
            metadata={
                "type": "ptcp_delay_response",
                "sequence_id": delay_seq,
                "request_receipt_ns": request_receipt_ns,
                "response_origin_ns": response_origin_ns,
                "phase": "delay_remeasure",
            },
        )

        # Update line delay with slight drift simulation
        old_delay_ns = state.custom_data.get("line_delay_ns", 500)
        # Simulate small drift (+/- 50ns typical)
        drift_ns = random.randint(-50, 50)
        new_delay_ns = max(100, min(2000, old_delay_ns + drift_ns))
        state.custom_data["line_delay_ns"] = new_delay_ns
        state.custom_data["delay_remeasure_count"] = (
            state.custom_data.get("delay_remeasure_count", 0) + 1
        )

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

        # Get RT class to determine validation rules
        rt_class = config.get("rt_class", RTClass.RT_CLASS_1)

        # Validate frame IDs based on RT class
        if rt_class == RTClass.RT_CLASS_3:
            # IRT mode validation
            frame_id_output = config.get("frame_id_output")
            frame_id_input = config.get("frame_id_input")

            if frame_id_output is not None:
                if not (IRT_FRAME_ID_MIN <= frame_id_output <= IRT_FRAME_ID_MAX):
                    errors.append(
                        f"IRT frame_id_output must be between {IRT_FRAME_ID_MIN:#x} and {IRT_FRAME_ID_MAX:#x}"
                    )

            if frame_id_input is not None:
                if not (IRT_FRAME_ID_MIN <= frame_id_input <= IRT_FRAME_ID_MAX):
                    errors.append(
                        f"IRT frame_id_input must be between {IRT_FRAME_ID_MIN:#x} and {IRT_FRAME_ID_MAX:#x}"
                    )

            if frame_id_output is not None and frame_id_input is not None:
                if frame_id_output == frame_id_input:
                    errors.append("frame_id_output and frame_id_input must be different")

            # IRT cycle time validation (in microseconds)
            cycle_time_us = config.get("cycle_time_us", DEFAULT_IRT_CYCLE_TIME_US)
            if cycle_time_us < MIN_IRT_CYCLE_TIME_US or cycle_time_us > MAX_IRT_CYCLE_TIME_US:
                errors.append(
                    f"IRT cycle_time_us must be between {MIN_IRT_CYCLE_TIME_US} and {MAX_IRT_CYCLE_TIME_US}"
                )

            # VLAN is required for IRT
            vlan_id = config.get("vlan_id")
            if vlan_id is None:
                errors.append("vlan_id is required for IRT (RT Class 3)")

            # Validate phase configuration
            red_phase_us = config.get("red_phase_duration_us")
            if red_phase_us is not None:
                if red_phase_us < 10 or red_phase_us > cycle_time_us * 0.5:
                    errors.append("red_phase_duration_us must be between 10µs and 50% of cycle time")

            # Validate send clock factor
            send_clock_factor = config.get("send_clock_factor", 32)
            valid_factors = [1, 2, 4, 8, 16, 32, 64, 128]
            if send_clock_factor not in valid_factors:
                errors.append(f"send_clock_factor must be one of {valid_factors}")

        else:
            # Standard RT Class 1/2 validation
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

            # Standard cycle time validation (in milliseconds)
            cycle_time = config.get("cycle_time_ms", DEFAULT_CYCLE_TIME_MS)
            if cycle_time < MIN_CYCLE_TIME_MS or cycle_time > MAX_CYCLE_TIME_MS:
                errors.append(
                    f"cycle_time_ms must be between {MIN_CYCLE_TIME_MS} and {MAX_CYCLE_TIME_MS}"
                )

        # Validate data sizes (common to all RT classes)
        output_size = config.get("output_data_size", DEFAULT_OUTPUT_SIZE)
        input_size = config.get("input_data_size", DEFAULT_INPUT_SIZE)

        if output_size < 1 or output_size > 1440:
            errors.append("output_data_size must be between 1 and 1440 bytes")

        if input_size < 1 or input_size > 1440:
            errors.append("input_data_size must be between 1 and 1440 bytes")

        # Validate VLAN ID if present (common validation)
        vlan_id = config.get("vlan_id")
        if vlan_id is not None:
            if not isinstance(vlan_id, int) or vlan_id < 0 or vlan_id > 4094:
                errors.append("vlan_id must be between 0 and 4094")

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
