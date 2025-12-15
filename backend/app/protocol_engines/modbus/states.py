"""Modbus conversation state machine."""

from statemachine import State, StateMachine


class ModbusConversationMachine(StateMachine):
    """State machine for Modbus TCP conversation flow."""

    # States
    idle = State(initial=True)
    request_sent = State()
    awaiting_response = State()
    response_received = State()
    exception_state = State()

    # Transitions
    send_request = idle.to(request_sent)
    wait_response = request_sent.to(awaiting_response)
    receive_response = awaiting_response.to(response_received)
    complete_cycle = response_received.to(idle)
    error_occurred = (
        request_sent.to(exception_state)
        | awaiting_response.to(exception_state)
        | response_received.to(exception_state)
    )
    recover = exception_state.to(idle)

    def __init__(self, flow_id: str):
        """Initialize state machine.

        Args:
            flow_id: Flow identifier
        """
        self.flow_id = flow_id
        super().__init__()

    def on_enter_request_sent(self):
        """Handler for entering request_sent state."""
        pass

    def on_enter_awaiting_response(self):
        """Handler for entering awaiting_response state."""
        pass

    def on_enter_response_received(self):
        """Handler for entering response_received state."""
        pass

    def on_enter_exception_state(self):
        """Handler for entering exception_state."""
        pass
