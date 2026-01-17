"""Protocol engine types and data structures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocol_engines.fingerprint_applicator import FingerprintApplicator


class ProtocolType(str, Enum):
    """Supported protocol types."""

    MODBUS_TCP = "modbus_tcp"
    ETHERNET_IP = "ethernet_ip"
    PROFINET = "profinet"
    S7COMM = "s7comm"
    OPC_UA = "opc_ua"
    DNP3 = "dnp3"
    IEC_104 = "iec_104"
    SNMP = "snmp"  # SNMP/NTCIP for transportation systems
    BACNET = "bacnet"  # BACnet/IP for building automation systems


@dataclass
class DeviceContext:
    """Context information for a device in a flow.

    Extended to include comprehensive fingerprint data for
    hyper-realistic device emulation.
    """

    device_id: str
    mac_address: str
    ip_address: str
    port: int
    unit_id: int | None = None

    # Legacy fingerprint dict (for backwards compatibility)
    vendor_fingerprint: dict[str, Any] = field(default_factory=dict)

    # CVE vulnerability override - contains protocol identity overrides
    # for emitting vulnerable firmware versions in identity responses
    vulnerability_override: dict[str, Any] | None = None

    # Extended fingerprint fields
    vendor: str | None = None
    vendor_family: str | None = None
    model: str | None = None
    firmware_version: str | None = None

    # Fingerprint applicator (lazy-loaded)
    _fingerprint_applicator: "FingerprintApplicator | None" = field(
        default=None, repr=False, compare=False
    )

    @property
    def fingerprint_applicator(self) -> "FingerprintApplicator":
        """Get or create fingerprint applicator for this device.

        Returns:
            FingerprintApplicator instance with vulnerability overrides applied
        """
        if self._fingerprint_applicator is None:
            from app.protocol_engines.fingerprint_applicator import (
                FingerprintApplicator,
                create_default_applicator,
            )

            if self.vendor_fingerprint:
                # Pass vulnerability_override to apply CVE-specific identity overrides
                self._fingerprint_applicator = FingerprintApplicator(
                    self.vendor_fingerprint,
                    vulnerability_override=self.vulnerability_override,
                )
            else:
                self._fingerprint_applicator = create_default_applicator()

        return self._fingerprint_applicator

    def get_tcp_ttl(self) -> int:
        """Get TCP TTL for this device."""
        return self.fingerprint_applicator.get_tcp_options().ttl

    def get_tcp_window_size(self) -> int:
        """Get TCP window size for this device."""
        return self.fingerprint_applicator.get_tcp_options().window_size

    def get_response_delay_ms(self) -> float:
        """Get a sampled response delay for this device.

        Returns:
            Delay in milliseconds
        """
        sample = self.fingerprint_applicator.get_response_delay()
        return sample.delay_ms if not sample.is_timeout else 0

    def should_inject_error(self) -> bool:
        """Check if an error should be injected."""
        return self.fingerprint_applicator.should_inject_error()

    def get_exception_code(self) -> int:
        """Get a random exception code for error injection."""
        return self.fingerprint_applicator.get_random_exception_code()


@dataclass
class FlowContext:
    """Context for a communication flow between devices."""

    flow_id: str
    source: DeviceContext
    destination: DeviceContext
    protocol: ProtocolType
    config: dict[str, Any]
    timing_model: dict[str, Any]
    payload_template: dict[str, Any] | None = None


@dataclass
class PacketEvent:
    """Represents a packet generation event."""

    timestamp_ms: float
    flow_id: str
    packet_bytes: bytes
    direction: str  # "request" or "response"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """State for a protocol conversation.

    DEPRECATED: Use protocol-specific state classes instead:
    - ModbusConversationState
    - EtherNetIPConversationState
    - ProfinetConversationState
    - S7ConversationState
    - SNMPConversationState
    - BACnetConversationState
    - DNP3ConversationState
    - IEC104ConversationState
    - OPCUAConversationState

    This class is kept for backwards compatibility.
    """

    flow_id: str
    state_name: str
    transaction_id: int = 0
    sequence_number: int = 0
    custom_data: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Protocol-Specific Conversation State Classes
# =============================================================================


@dataclass
class ConversationStateBase:
    """Base class for typed conversation states.

    All protocol-specific state classes inherit from this.
    Provides common fields used across all protocols.
    """

    flow_id: str
    state_name: str = "idle"
    transaction_id: int = 0
    sequence_number: int = 0
    error_count: int = 0
    last_activity_ms: float = 0.0

    def reset(self) -> None:
        """Reset state to initial values."""
        self.state_name = "idle"
        self.transaction_id = 0
        self.sequence_number = 0
        self.error_count = 0

    def increment_transaction(self) -> int:
        """Increment and return the transaction ID."""
        self.transaction_id += 1
        return self.transaction_id


@dataclass
class ModbusConversationState(ConversationStateBase):
    """Typed state for Modbus TCP conversations.

    Attributes:
        tcp_seq_client: Client-side TCP sequence number
        tcp_seq_server: Server-side TCP sequence number
        last_function_code: Last Modbus function code sent
        last_unit_id: Last unit ID addressed
        retry_count: Current retry attempt count
        pending_request: Whether a request is awaiting response
        expected_response_length: Expected bytes in response
    """

    tcp_seq_client: int = 0
    tcp_seq_server: int = 0
    last_function_code: int | None = None
    last_unit_id: int = 1
    retry_count: int = 0
    max_retries: int = 3
    pending_request: bool = False
    expected_response_length: int = 0

    def start_request(self, function_code: int, unit_id: int = 1) -> int:
        """Record start of a new request.

        Args:
            function_code: Modbus function code
            unit_id: Target unit ID

        Returns:
            Transaction ID for this request
        """
        self.last_function_code = function_code
        self.last_unit_id = unit_id
        self.pending_request = True
        self.retry_count = 0
        return self.increment_transaction()

    def complete_request(self) -> None:
        """Mark current request as completed."""
        self.pending_request = False
        self.retry_count = 0

    def should_retry(self) -> bool:
        """Check if a retry should be attempted."""
        return self.retry_count < self.max_retries


@dataclass
class EtherNetIPConversationState(ConversationStateBase):
    """Typed state for EtherNet/IP conversations.

    Attributes:
        session_handle: Current session handle from RegisterSession
        sender_context: Sender context bytes for request correlation
        connection_id: CIP connection ID (for I/O connections)
        connection_serial: CIP connection serial number
        is_registered: Whether session is registered
        is_connected: Whether CIP connection is established
        originator_serial: Originator serial number
        timeout_multiplier: Connection timeout multiplier
        tcp_seq_client: TCP sequence number for client
        tcp_seq_server: TCP sequence number for server
        tcp_ack_client: TCP ack number for client
        tcp_ack_server: TCP ack number for server
        io_sequence: I/O data sequence number
        consecutive_timeouts: Count of consecutive timeouts
        retry_count: Current retry count
    """

    session_handle: int = 0
    sender_context: bytes = field(default=b"\x00" * 8)
    connection_id: int | None = None
    connection_serial: int = 0
    is_registered: bool = False
    is_connected: bool = False
    originator_serial: int = 0
    timeout_multiplier: int = 32
    # TCP state
    tcp_seq_client: int = 0
    tcp_seq_server: int = 0
    tcp_ack_client: int = 0
    tcp_ack_server: int = 0
    # I/O state
    io_sequence: int = 0
    consecutive_timeouts: int = 0
    retry_count: int = 0

    def register_session(self, handle: int) -> None:
        """Record successful session registration.

        Args:
            handle: Session handle from device
        """
        self.session_handle = handle
        self.is_registered = True
        self.state_name = "registered"

    def unregister_session(self) -> None:
        """Record session unregistration."""
        self.session_handle = 0
        self.is_registered = False
        self.is_connected = False
        self.connection_id = None
        self.state_name = "idle"

    def establish_connection(self, conn_id: int, serial: int) -> None:
        """Record CIP connection establishment.

        Args:
            conn_id: Connection ID assigned
            serial: Connection serial number
        """
        self.connection_id = conn_id
        self.connection_serial = serial
        self.is_connected = True
        self.state_name = "connected"


@dataclass
class ProfinetConversationState(ConversationStateBase):
    """Typed state for PROFINET conversations.

    Attributes:
        station_name: PROFINET station name
        ar_uuid: Application Relationship UUID
        session_key: Session key for AR
        cycle_counter: Current IO cycle counter
        data_status: IO data status bits
        is_identified: Whether DCP identify completed
        is_ar_established: Whether AR is established
        io_active: Whether cyclic IO is running
    """

    station_name: str = ""
    ar_uuid: bytes | None = None
    session_key: int = 0
    cycle_counter: int = 0
    data_status: int = 0x35  # Normal status
    is_identified: bool = False
    is_ar_established: bool = False
    io_active: bool = False

    def complete_identify(self, station_name: str) -> None:
        """Record successful DCP identify.

        Args:
            station_name: Discovered station name
        """
        self.station_name = station_name
        self.is_identified = True
        self.state_name = "identified"

    def establish_ar(self, ar_uuid: bytes, session_key: int) -> None:
        """Record AR establishment.

        Args:
            ar_uuid: Application Relationship UUID
            session_key: Session key
        """
        self.ar_uuid = ar_uuid
        self.session_key = session_key
        self.is_ar_established = True
        self.state_name = "ar_established"

    def start_io(self) -> None:
        """Start cyclic IO data exchange."""
        self.io_active = True
        self.cycle_counter = 0
        self.state_name = "io_active"

    def increment_cycle(self) -> int:
        """Increment and return cycle counter."""
        self.cycle_counter = (self.cycle_counter + 1) & 0xFFFF
        return self.cycle_counter


@dataclass
class S7ConversationState(ConversationStateBase):
    """Typed state for S7comm conversations.

    Attributes:
        cotp_src_ref: COTP source reference
        cotp_dst_ref: COTP destination reference
        pdu_ref: S7 PDU reference number
        max_pdu_size: Negotiated max PDU size
        is_connected: Whether COTP connection established
        is_setup: Whether S7 communication setup completed
        plc_mode: Current PLC operating mode
    """

    cotp_src_ref: int = 0x0100
    cotp_dst_ref: int = 0x0000
    pdu_ref: int = 0
    max_pdu_size: int = 480
    is_connected: bool = False
    is_setup: bool = False
    plc_mode: str = "RUN"

    def connect_cotp(self, dst_ref: int) -> None:
        """Record COTP connection.

        Args:
            dst_ref: Destination reference from PLC
        """
        self.cotp_dst_ref = dst_ref
        self.is_connected = True
        self.state_name = "cotp_connected"

    def setup_communication(self, max_pdu: int) -> None:
        """Record S7 communication setup.

        Args:
            max_pdu: Negotiated maximum PDU size
        """
        self.max_pdu_size = max_pdu
        self.is_setup = True
        self.state_name = "s7_setup"

    def next_pdu_ref(self) -> int:
        """Get next PDU reference number."""
        self.pdu_ref = (self.pdu_ref + 1) & 0xFFFF
        return self.pdu_ref


@dataclass
class SNMPConversationState(ConversationStateBase):
    """Typed state for SNMP conversations.

    Attributes:
        request_id: Current SNMP request ID
        community: SNMP community string
        version: SNMP version (0=v1, 1=v2c, 3=v3)
        engine_id: SNMPv3 engine ID
        context_name: SNMPv3 context name
        last_oid: Last OID accessed
        walk_in_progress: Whether a walk operation is active
    """

    request_id: int = 0
    community: str = "public"
    version: int = 1  # v2c default
    engine_id: bytes | None = None
    context_name: str = ""
    last_oid: str = ""
    walk_in_progress: bool = False
    walk_start_oid: str = ""

    def start_request(self) -> int:
        """Start a new SNMP request.

        Returns:
            Request ID for this request
        """
        self.request_id += 1
        return self.request_id

    def start_walk(self, start_oid: str) -> None:
        """Start an SNMP walk operation.

        Args:
            start_oid: Starting OID for walk
        """
        self.walk_in_progress = True
        self.walk_start_oid = start_oid
        self.last_oid = start_oid
        self.state_name = "walking"

    def end_walk(self) -> None:
        """End SNMP walk operation."""
        self.walk_in_progress = False
        self.state_name = "idle"


@dataclass
class BACnetConversationState(ConversationStateBase):
    """Typed state for BACnet/IP conversations.

    Attributes:
        invoke_id: Current BACnet invoke ID
        device_instance: Target device instance
        max_apdu_length: Max APDU length accepted
        segmentation_supported: Segmentation capability
        pending_segmented: Whether segmented transfer active
        segments_received: List of received segment numbers
    """

    invoke_id: int = 0
    device_instance: int = 0
    max_apdu_length: int = 1476
    segmentation_supported: int = 3  # No segmentation
    pending_segmented: bool = False
    segments_received: list[int] = field(default_factory=list)

    def next_invoke_id(self) -> int:
        """Get next invoke ID (wraps at 255).

        Returns:
            Next invoke ID
        """
        self.invoke_id = (self.invoke_id + 1) & 0xFF
        return self.invoke_id

    def start_segmented_receive(self) -> None:
        """Start receiving a segmented message."""
        self.pending_segmented = True
        self.segments_received = []
        self.state_name = "segmented_receive"

    def receive_segment(self, segment_number: int) -> None:
        """Record receipt of a segment.

        Args:
            segment_number: Sequence number of segment
        """
        self.segments_received.append(segment_number)

    def complete_segmented(self) -> None:
        """Complete segmented transfer."""
        self.pending_segmented = False
        self.segments_received = []
        self.state_name = "idle"


@dataclass
class DNP3ConversationState(ConversationStateBase):
    """Typed state for DNP3 conversations.

    Attributes:
        master_address: DNP3 master address
        outstation_address: DNP3 outstation address
        sequence: Current application sequence number
        fir: First fragment flag
        fin: Final fragment flag
        con: Confirmation required flag
        uns: Unsolicited response flag
        iir: Internal indications register
    """

    master_address: int = 1
    outstation_address: int = 10
    sequence: int = 0
    fir: bool = True
    fin: bool = True
    con: bool = False
    uns: bool = False
    iir: int = 0x0000  # Internal indications

    def next_sequence(self) -> int:
        """Get next application sequence number.

        Returns:
            Next sequence number (0-15)
        """
        self.sequence = (self.sequence + 1) & 0x0F
        return self.sequence


@dataclass
class IEC104ConversationState(ConversationStateBase):
    """Typed state for IEC 60870-5-104 conversations.

    Attributes:
        send_sequence: Send sequence number V(S)
        recv_sequence: Receive sequence number V(R)
        is_started: Whether STARTDT confirmed
        last_asdu_type: Last ASDU type sent
        w_counter: I-format counter for S-format
        t1_active: Whether T1 timeout is active
    """

    send_sequence: int = 0
    recv_sequence: int = 0
    is_started: bool = False
    last_asdu_type: int = 0
    w_counter: int = 0
    t1_active: bool = False

    def next_send_sequence(self) -> int:
        """Get next send sequence number.

        Returns:
            Next V(S) value
        """
        seq = self.send_sequence
        self.send_sequence = (self.send_sequence + 1) & 0x7FFF
        return seq

    def update_recv_sequence(self, received: int) -> None:
        """Update receive sequence from received I-format.

        Args:
            received: V(S) from received frame
        """
        self.recv_sequence = (received + 1) & 0x7FFF
        self.w_counter += 1

    def start_dt(self) -> None:
        """Record STARTDT activation."""
        self.is_started = True
        self.state_name = "started"


@dataclass
class OPCUAConversationState(ConversationStateBase):
    """Typed state for OPC UA conversations.

    Attributes:
        secure_channel_id: Secure channel identifier
        token_id: Security token ID
        request_id: Current request ID
        sequence_number: Sequence number in channel
        request_handle: Client request handle
        session_id: Session node ID
        authentication_token: Session auth token
    """

    secure_channel_id: int = 0
    token_id: int = 0
    request_id: int = 0
    sequence_number: int = 1
    request_handle: int = 0
    session_id: bytes | None = None
    authentication_token: bytes | None = None
    is_channel_open: bool = False
    is_session_active: bool = False

    def open_channel(self, channel_id: int, token_id: int) -> None:
        """Record secure channel opening.

        Args:
            channel_id: Assigned channel ID
            token_id: Assigned token ID
        """
        self.secure_channel_id = channel_id
        self.token_id = token_id
        self.is_channel_open = True
        self.state_name = "channel_open"

    def activate_session(self, session_id: bytes, token: bytes) -> None:
        """Record session activation.

        Args:
            session_id: Session node ID
            token: Authentication token
        """
        self.session_id = session_id
        self.authentication_token = token
        self.is_session_active = True
        self.state_name = "session_active"

    def next_request_id(self) -> int:
        """Get next request ID.

        Returns:
            Next request ID
        """
        self.request_id += 1
        return self.request_id


# =============================================================================
# Factory Function
# =============================================================================


def create_conversation_state(
    protocol: ProtocolType,
    flow_id: str,
    **kwargs: Any,
) -> ConversationStateBase:
    """Create a typed conversation state for a protocol.

    Args:
        protocol: Protocol type
        flow_id: Flow identifier
        **kwargs: Additional state initialization arguments

    Returns:
        Protocol-specific ConversationStateBase subclass

    Raises:
        ValueError: If protocol is not supported
    """
    state_classes: dict[ProtocolType, type[ConversationStateBase]] = {
        ProtocolType.MODBUS_TCP: ModbusConversationState,
        ProtocolType.ETHERNET_IP: EtherNetIPConversationState,
        ProtocolType.PROFINET: ProfinetConversationState,
        ProtocolType.S7COMM: S7ConversationState,
        ProtocolType.SNMP: SNMPConversationState,
        ProtocolType.BACNET: BACnetConversationState,
        ProtocolType.DNP3: DNP3ConversationState,
        ProtocolType.IEC_104: IEC104ConversationState,
        ProtocolType.OPC_UA: OPCUAConversationState,
    }

    state_class = state_classes.get(protocol)
    if state_class is None:
        raise ValueError(f"No conversation state class for protocol: {protocol}")

    return state_class(flow_id=flow_id, **kwargs)
