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
    ):
        """Initialize RT cycle state.

        Args:
            frame_id_output: Frame ID for output (controller -> device)
            frame_id_input: Frame ID for input (device -> controller)
            output_data_size: Size of output data in bytes
            input_data_size: Size of input data in bytes
        """
        self.frame_id_output = frame_id_output
        self.frame_id_input = frame_id_input
        self.output_data_size = output_data_size
        self.input_data_size = input_data_size
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
