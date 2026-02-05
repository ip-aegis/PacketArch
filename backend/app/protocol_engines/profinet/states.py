"""PROFINET state machines using python-statemachine.

Models the PROFINET device lifecycle:
1. Power On -> DCP Discovery
2. DCP Set (optional) -> Connection Request
3. Application Relationship (AR) establishment
4. Parameter End -> Application Ready
5. Cyclic Data Exchange (RT)
6. Disconnect / Offline
"""

from statemachine import State, StateMachine


class ProfinetDeviceStateMachine(StateMachine):
    """State machine for PROFINET IO-Device.

    Models the device lifecycle from power-on through data exchange.

    States:
    - power_on: Initial state after power on
    - dcp_wait: Waiting for DCP Identify
    - dcp_identified: Responded to DCP Identify
    - connecting: AR (Application Relationship) being established
    - parameterizing: Receiving parameters from controller
    - application_ready: Ready for data exchange
    - data_exchange: Active cyclic RT data exchange
    - offline: Disconnected or stopped
    """

    # States
    power_on = State(initial=True)
    dcp_wait = State()
    dcp_identified = State()
    connecting = State()
    parameterizing = State()
    application_ready = State()
    data_exchange = State()
    offline = State()

    # Transitions
    start_discovery = power_on.to(dcp_wait)
    receive_identify = dcp_wait.to(dcp_identified)
    start_connection = dcp_identified.to(connecting)
    connection_established = connecting.to(parameterizing)
    parameters_complete = parameterizing.to(application_ready)
    start_io = application_ready.to(data_exchange)
    io_cycle = data_exchange.to(data_exchange, internal=True)
    disconnect = (
        data_exchange.to(offline) |
        application_ready.to(offline) |
        parameterizing.to(offline) |
        connecting.to(offline)
    )
    reconnect = offline.to(power_on)
    timeout = (
        dcp_wait.to(power_on) |
        connecting.to(dcp_identified)
    )

    def __init__(self, device_id: str):
        """Initialize state machine.

        Args:
            device_id: Unique device identifier
        """
        self.device_id = device_id
        self.ar_uuid: str | None = None
        self.session_key: int = 0
        self.cycle_counter: int = 0
        self.dcp_xid: int = 0
        super().__init__()

    def on_enter_dcp_wait(self) -> None:
        """Called when entering DCP wait state."""
        self.dcp_xid = 0

    def on_enter_dcp_identified(self) -> None:
        """Called when DCP Identify response sent."""
        pass

    def on_enter_connecting(self) -> None:
        """Called when starting AR establishment."""
        import uuid
        self.ar_uuid = str(uuid.uuid4())
        self.session_key = 1

    def on_enter_data_exchange(self) -> None:
        """Called when entering data exchange."""
        self.cycle_counter = 0

    def on_io_cycle(self) -> None:
        """Called on each IO cycle (internal transition)."""
        self.cycle_counter = (self.cycle_counter + 1) % 65536


class ProfinetControllerStateMachine(StateMachine):
    """State machine for PROFINET IO-Controller.

    Models the controller initiating connections to devices.

    States:
    - idle: No active connections
    - discovering: Sending DCP Identify requests
    - configuring: Sending DCP Set if needed
    - connecting: Establishing AR with device
    - parameterizing: Sending parameters to device
    - waiting_ready: Waiting for Application Ready
    - data_exchange: Active cyclic RT data exchange
    - stopping: Graceful shutdown
    """

    # States
    idle = State(initial=True)
    discovering = State()
    configuring = State()
    connecting = State()
    parameterizing = State()
    waiting_ready = State()
    data_exchange = State()
    stopping = State()

    # Transitions
    start_discovery = idle.to(discovering)
    device_found = discovering.to(configuring)
    skip_config = discovering.to(connecting)
    config_complete = configuring.to(connecting)
    ar_established = connecting.to(parameterizing)
    params_sent = parameterizing.to(waiting_ready)
    device_ready = waiting_ready.to(data_exchange)
    io_cycle = data_exchange.to(data_exchange, internal=True)
    initiate_stop = data_exchange.to(stopping)
    stop_complete = stopping.to(idle)
    error = (
        discovering.to(idle) |
        configuring.to(idle) |
        connecting.to(idle) |
        parameterizing.to(idle) |
        waiting_ready.to(idle) |
        data_exchange.to(idle)
    )

    def __init__(self, controller_id: str):
        """Initialize controller state machine.

        Args:
            controller_id: Unique controller identifier
        """
        self.controller_id = controller_id
        self.connected_devices: list[str] = []
        self.ar_uuid: str | None = None
        self.session_key: int = 0
        self.cycle_counter: int = 0
        super().__init__()

    def on_enter_discovering(self) -> None:
        """Called when starting discovery."""
        self.connected_devices = []

    def on_enter_connecting(self) -> None:
        """Called when establishing AR."""
        import uuid
        self.ar_uuid = str(uuid.uuid4())
        self.session_key = 1

    def on_enter_data_exchange(self) -> None:
        """Called when entering data exchange."""
        self.cycle_counter = 0

    def on_io_cycle(self) -> None:
        """Called on each IO cycle."""
        self.cycle_counter = (self.cycle_counter + 1) % 65536


class RTCycleState:
    """Tracks RT cycle state for a single connection.

    Used by the engine to manage cyclic data exchange without
    full state machine overhead.
    """

    def __init__(
        self,
        frame_id_output: int,
        frame_id_input: int,
        output_data_size: int,
        input_data_size: int,
        rt_class: int = 1,  # RT Class 1, 2, or 3 (IRT)
    ):
        """Initialize RT cycle state.

        Args:
            frame_id_output: Frame ID for output (controller -> device)
            frame_id_input: Frame ID for input (device -> controller)
            output_data_size: Size of output data in bytes
            input_data_size: Size of input data in bytes
            rt_class: PROFINET RT class (1=unsync, 2=sync, 3=IRT)
        """
        self.frame_id_output = frame_id_output
        self.frame_id_input = frame_id_input
        self.output_data_size = output_data_size
        self.input_data_size = input_data_size
        self.rt_class = rt_class
        self.cycle_counter = 0
        self.output_data: bytes = bytes(output_data_size)
        self.input_data: bytes = bytes(input_data_size)
        self.data_status = 0x35  # Valid, Run, Primary

    def increment_cycle(self) -> int:
        """Increment cycle counter and return new value."""
        self.cycle_counter = (self.cycle_counter + 1) % 65536
        return self.cycle_counter

    def update_output_data(self, data: bytes) -> None:
        """Update output data buffer."""
        if len(data) == self.output_data_size:
            self.output_data = data
        else:
            # Pad or truncate to correct size
            self.output_data = (data + bytes(self.output_data_size))[:self.output_data_size]

    def update_input_data(self, data: bytes) -> None:
        """Update input data buffer."""
        if len(data) == self.input_data_size:
            self.input_data = data
        else:
            self.input_data = (data + bytes(self.input_data_size))[:self.input_data_size]

    def is_irt(self) -> bool:
        """Check if this is an IRT (RT Class 3) connection."""
        return self.rt_class == 3


class IRTSyncState:
    """Tracks IRT synchronization state.

    Used by IRT sync masters and slaves to maintain time synchronization.
    """

    def __init__(
        self,
        subdomain_uuid: bytes,
        is_sync_master: bool = False,
        cycle_time_us: int = 250,
    ):
        """Initialize IRT sync state.

        Args:
            subdomain_uuid: PTCP subdomain UUID (16 bytes)
            is_sync_master: True if this device is the sync master
            cycle_time_us: Cycle time in microseconds
        """
        self.subdomain_uuid = subdomain_uuid[:16].ljust(16, b'\x00')
        self.is_sync_master = is_sync_master
        self.cycle_time_us = cycle_time_us

        # Sync state tracking
        self.sync_sequence_id = 0
        self.local_time_ns = 0
        self.master_time_ns = 0
        self.line_delay_ns = 0
        self.is_synchronized = False
        self.sync_lost_count = 0

        # PTCP timing
        self.last_sync_send_time_ns = 0
        self.last_sync_recv_time_ns = 0
        self.pending_delay_request_id: int | None = None

    def increment_sync_sequence(self) -> int:
        """Increment and return sync sequence ID."""
        self.sync_sequence_id = (self.sync_sequence_id + 1) % 65536
        return self.sync_sequence_id

    def process_sync(self, sync_time_ns: int, sequence_id: int) -> None:
        """Process received Sync frame.

        Args:
            sync_time_ns: Timestamp in Sync frame
            sequence_id: Sync sequence ID
        """
        self.last_sync_recv_time_ns = sync_time_ns
        self.sync_sequence_id = sequence_id
        self.is_synchronized = True
        self.sync_lost_count = 0

    def process_followup(self, precise_time_ns: int, sequence_id: int) -> None:
        """Process received FollowUp frame.

        Args:
            precise_time_ns: Precise send time of corresponding Sync
            sequence_id: Must match Sync sequence ID
        """
        if sequence_id == self.sync_sequence_id:
            # Calculate offset from master
            self.master_time_ns = precise_time_ns
            self.local_time_ns = self.last_sync_recv_time_ns

    def process_delay_response(
        self,
        sequence_id: int,
        request_receipt_ns: int,
        response_origin_ns: int,
    ) -> None:
        """Process received Delay Response.

        Args:
            sequence_id: Must match Delay Request
            request_receipt_ns: When master received request
            response_origin_ns: When master sent response
        """
        if self.pending_delay_request_id == sequence_id:
            # Calculate line delay using two-way measurement
            # delay = ((t4 - t1) - (t3 - t2)) / 2
            # where t1=request_send, t2=request_receipt, t3=response_origin, t4=response_receipt
            # Simplified: use (request_receipt + response_origin) / 2 as midpoint
            self.line_delay_ns = (request_receipt_ns + response_origin_ns) // 2
            self.pending_delay_request_id = None

    def sync_lost(self) -> None:
        """Called when sync is lost."""
        self.sync_lost_count += 1
        if self.sync_lost_count > 3:
            self.is_synchronized = False

    def get_corrected_time_ns(self, local_time_ns: int) -> int:
        """Get master-corrected time from local time.

        Args:
            local_time_ns: Local clock time

        Returns:
            Corrected time accounting for offset and delay
        """
        if not self.is_synchronized:
            return local_time_ns

        offset = self.master_time_ns - self.local_time_ns
        return local_time_ns + offset + self.line_delay_ns


class IRTPhaseConfig:
    """Configuration for IRT phase timing.

    PROFINET IRT divides each cycle into phases:
    - Red phase: Deterministic IRT data (highest priority)
    - Orange phase: Transition
    - Green phase: RT Class 1/2 and best-effort traffic
    """

    def __init__(
        self,
        cycle_time_us: int = 250,
        red_phase_duration_us: int = 50,
        orange_phase_duration_us: int = 25,
    ):
        """Initialize phase configuration.

        Args:
            cycle_time_us: Total cycle time in microseconds
            red_phase_duration_us: Duration of red phase
            orange_phase_duration_us: Duration of orange phase
        """
        self.cycle_time_us = cycle_time_us
        self.red_phase_duration_us = red_phase_duration_us
        self.orange_phase_duration_us = orange_phase_duration_us

        # Calculate green phase as remainder
        self.green_phase_duration_us = (
            cycle_time_us - red_phase_duration_us - 2 * orange_phase_duration_us
        )

    def get_phase_start_us(self, phase: str) -> int:
        """Get start time of phase within cycle.

        Args:
            phase: "red", "orange1", "green", "orange2"

        Returns:
            Start time in microseconds from cycle start
        """
        if phase == "red":
            return 0
        elif phase == "orange1":
            return self.red_phase_duration_us
        elif phase == "green":
            return self.red_phase_duration_us + self.orange_phase_duration_us
        elif phase == "orange2":
            return (
                self.red_phase_duration_us +
                self.orange_phase_duration_us +
                self.green_phase_duration_us
            )
        else:
            raise ValueError(f"Unknown phase: {phase}")

    def is_in_red_phase(self, time_in_cycle_us: int) -> bool:
        """Check if time is within red phase.

        Args:
            time_in_cycle_us: Time within cycle in microseconds

        Returns:
            True if in red phase
        """
        return time_in_cycle_us < self.red_phase_duration_us

    def get_slot_time_us(self, slot_index: int, total_slots: int) -> int:
        """Get send time for a specific slot within red phase.

        Args:
            slot_index: 0-based slot index
            total_slots: Total number of slots in red phase

        Returns:
            Send time in microseconds from cycle start
        """
        if total_slots <= 0:
            return 0
        slot_duration = self.red_phase_duration_us // total_slots
        return slot_index * slot_duration
