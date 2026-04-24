# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""EtherNet/IP conversation state machine."""

from statemachine import State, StateMachine


class EtherNetIPConnectionMachine(StateMachine):
    """State machine for EtherNet/IP connection lifecycle."""

    # States
    unconnected = State(initial=True)
    registering = State()
    registered = State()
    opening_connection = State()
    connected = State()
    io_active = State()
    closing = State()
    error_state = State()

    # Transitions
    register = unconnected.to(registering)
    registration_complete = registering.to(registered)
    open_connection = registered.to(opening_connection)
    connection_opened = opening_connection.to(connected)
    start_io = connected.to(io_active)
    stop_io = io_active.to(connected)
    close_connection = (
        connected.to(closing) | io_active.to(closing) | registered.to(closing)
    )
    disconnect = closing.to(unconnected)
    error_occurred = (
        registering.to(error_state)
        | registered.to(error_state)
        | opening_connection.to(error_state)
        | connected.to(error_state)
        | io_active.to(error_state)
    )
    recover = error_state.to(unconnected)

    def __init__(self, flow_id: str):
        """Initialize state machine.

        Args:
            flow_id: Flow identifier
        """
        self.flow_id = flow_id
        super().__init__()

    def on_enter_registered(self):
        """Handler for entering registered state."""
        pass

    def on_enter_connected(self):
        """Handler for entering connected state."""
        pass

    def on_enter_io_active(self):
        """Handler for entering io_active state."""
        pass

    def on_enter_error_state(self):
        """Handler for entering error_state."""
        pass
