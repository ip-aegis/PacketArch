# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Protocol engine types and data structures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.protocol_engines.fingerprint_applicator import FingerprintApplicator


class ProtocolType(str, Enum):
    """Supported protocol types."""

    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"  # Modbus RTU (serial framing with CRC-16)
    ETHERNET_IP = "ethernet_ip"
    PROFINET = "profinet"
    S7COMM = "s7comm"
    OPC_UA = "opc_ua"
    DNP3 = "dnp3"
    IEC_104 = "iec_104"
    IEC61850 = "iec61850"  # IEC 61850 MMS/GOOSE/SV for power systems
    PCCC = "pccc"  # Allen-Bradley PCCC/DF1 for Rockwell PLCs
    CODESYS = "codesys"  # Codesys runtime for 500+ PLC vendors
    LLDP = "lldp"  # Link Layer Discovery Protocol (IEEE 802.1AB)
    SNMP = "snmp"  # SNMP/NTCIP for transportation systems
    BACNET = "bacnet"  # BACnet/IP for building automation systems
    ETHERCAT = "ethercat"  # EtherCAT for Beckhoff motion control
    FINS = "fins"  # Omron FINS protocol for Omron PLCs
    SLMP = "slmp"  # Mitsubishi SLMP/MC Protocol for MELSEC PLCs
    CDP = "cdp"  # Cisco Discovery Protocol for network discovery
    WMI = "wmi"  # Windows Management Instrumentation over DCOM/RPC
    FANUC = "fanuc"  # FANUC FOCAS CNC machine protocol
    DCS = "dcs"  # DCS protocols (DeltaV, Experion, Vnet/IP, Triconex)
    CLOUD_SERVICE = "cloud_service"  # Cloud service TLS heartbeats (Talk2M, TeamViewer, etc.)


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

    # Scenario ID for unique serial number generation
    # When provided, combined with device_id to generate deterministic unique serials
    scenario_id: str | None = None

    # Extended fingerprint fields
    vendor: str | None = None
    vendor_family: str | None = None
    model: str | None = None
    firmware_version: str | None = None

    # Device name for generating human-readable unique identifiers
    # Used for BACnet object_name, PROFINET station_name, SNMP sys_name
    device_name: str | None = None

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
                # Pass device_id, scenario_id, and device_name for unique identifier generation
                self._fingerprint_applicator = FingerprintApplicator(
                    self.vendor_fingerprint,
                    vulnerability_override=self.vulnerability_override,
                    device_id=self.device_id,
                    scenario_id=self.scenario_id,
                    device_name=self.device_name,
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
    payload_generator: Any | None = None  # PayloadGenerator instance
    startup_offset_ms: float = 0.0  # Per-flow delay before startup sequence begins


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
    custom_data: dict[str, Any] = field(default_factory=dict)

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
    tcp_ack_client: int = 0
    tcp_ack_server: int = 0
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
class ModbusRtuConversationState(ConversationStateBase):
    """Typed state for Modbus RTU conversations.

    Supports both pure RTU frames (serial) and RTU-over-TCP encapsulation.

    Attributes:
        current_unit_id: Current target unit ID (slave address)
        tcp_seq_client: Client-side TCP sequence number (RTU-over-TCP only)
        tcp_seq_server: Server-side TCP sequence number
        tcp_ack_client: Client-side TCP ack number
        tcp_ack_server: Server-side TCP ack number
        baud_rate: Serial baud rate for timing calculations
        inter_frame_gap_ms: Inter-frame gap in milliseconds (3.5 char times)
        transport_mode: "rtu_over_tcp" or "raw_rtu"
        retry_count: Current retry attempt count
        pending_request: Whether a request is awaiting response
    """

    current_unit_id: int = 1
    tcp_seq_client: int = 0
    tcp_seq_server: int = 0
    tcp_ack_client: int = 0
    tcp_ack_server: int = 0
    baud_rate: int = 9600
    inter_frame_gap_ms: float = 4.0
    transport_mode: str = "rtu_over_tcp"
    retry_count: int = 0
    max_retries: int = 3
    pending_request: bool = False

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


@dataclass
class IEC61850ConversationState(ConversationStateBase):
    """Typed state for IEC 61850 conversations.

    Supports MMS, GOOSE, and SV protocol modes.

    Attributes:
        invoke_id: MMS invoke ID
        cotp_src_ref: COTP source reference
        cotp_dst_ref: COTP destination reference
        is_connected: Whether COTP connection established
        is_associated: Whether MMS association established
        max_pdu_size: Negotiated max PDU size
        goose_state_num: GOOSE state number (increments on data change)
        goose_sq_num: GOOSE sequence number (increments each send)
        goose_time_allowed_to_live: GOOSE TTL in milliseconds
        sv_smp_cnt: SV sample count
        sv_smp_synch: SV synchronization status
    """

    # MMS state
    invoke_id: int = 0
    cotp_src_ref: int = 0x0100
    cotp_dst_ref: int = 0
    is_connected: bool = False
    is_associated: bool = False
    max_pdu_size: int = 65000

    # GOOSE state
    goose_state_num: int = 1
    goose_sq_num: int = 0
    goose_time_allowed_to_live: int = 4000

    # SV state
    sv_smp_cnt: int = 0
    sv_smp_synch: int = 0

    def next_invoke_id(self) -> int:
        """Get next MMS invoke ID.

        Returns:
            Next invoke ID
        """
        self.invoke_id = (self.invoke_id + 1) % 0xFFFFFFFF
        return self.invoke_id

    def increment_goose_sq(self) -> int:
        """Increment GOOSE sequence number.

        Returns:
            New sequence number
        """
        self.goose_sq_num = (self.goose_sq_num + 1) % 0xFFFFFFFF
        return self.goose_sq_num

    def increment_goose_state(self) -> int:
        """Increment GOOSE state number (on data change).

        Returns:
            New state number
        """
        self.goose_state_num = (self.goose_state_num + 1) % 0xFFFFFFFF
        self.goose_sq_num = 0  # Reset sequence on state change
        return self.goose_state_num

    def increment_sv_sample(self) -> int:
        """Increment SV sample count.

        Returns:
            New sample count
        """
        self.sv_smp_cnt = (self.sv_smp_cnt + 1) % 65536
        return self.sv_smp_cnt

    def connect_mms(self, dst_ref: int) -> None:
        """Record COTP/MMS connection.

        Args:
            dst_ref: Destination reference from server
        """
        self.cotp_dst_ref = dst_ref
        self.is_connected = True
        self.state_name = "cotp_connected"

    def associate_mms(self, max_pdu: int = 65000) -> None:
        """Record MMS association.

        Args:
            max_pdu: Negotiated max PDU size
        """
        self.max_pdu_size = max_pdu
        self.is_associated = True
        self.state_name = "mms_associated"


@dataclass
class PCCCConversationState(ConversationStateBase):
    """Typed state for PCCC/DF1 conversations.

    Supports Allen-Bradley/Rockwell PLCs including PLC-5, SLC-500,
    MicroLogix, and ControlLogix/CompactLogix.

    Attributes:
        tcp_seq_client: Client-side TCP sequence number
        tcp_seq_server: Server-side TCP sequence number
        tcp_ack_client: Client-side TCP ack number
        tcp_ack_server: Server-side TCP ack number
        session_handle: EtherNet/IP session handle (for EIP transport)
        sender_context: EtherNet/IP sender context
        is_registered: Whether EIP session is registered
        is_connected: Whether TCP connection is established
        last_command: Last PCCC command code sent
        last_function: Last PCCC function code sent
    """

    # TCP state
    tcp_seq_client: int = 0
    tcp_seq_server: int = 0
    tcp_ack_client: int = 0
    tcp_ack_server: int = 0

    # EtherNet/IP state (for EIP transport)
    session_handle: int = 0
    sender_context: bytes = field(default_factory=lambda: b"\x00" * 8)
    is_registered: bool = False

    # Connection state
    is_connected: bool = False
    last_command: int = 0
    last_function: int = 0

    def next_transaction_id(self) -> int:
        """Get next transaction ID (wraps at 65535).

        Returns:
            Next transaction ID (TNSW)
        """
        self.transaction_id = (self.transaction_id + 1) & 0xFFFF
        return self.transaction_id

    def register_session(self, handle: int) -> None:
        """Record EIP session registration.

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
        self.state_name = "connected" if self.is_connected else "idle"


@dataclass
class CodesysConversationState(ConversationStateBase):
    """Typed state for Codesys conversations.

    Supports Codesys V3 (port 11740) and V2 (port 1200) protocols
    used by 500+ PLC vendors including WAGO, Beckhoff, Festo, Schneider, ABB.

    Attributes:
        tcp_seq_client: Client-side TCP sequence number
        tcp_seq_server: Server-side TCP sequence number
        tcp_ack_client: Client-side TCP ack number
        tcp_ack_server: Server-side TCP ack number
        session_id: Codesys session identifier
        invoke_id: Current invoke ID for requests
        is_connected: Whether TCP connection is established
        is_authenticated: Whether authentication completed (V3.5+)
    """

    # TCP state
    tcp_seq_client: int = 0
    tcp_seq_server: int = 0
    tcp_ack_client: int = 0
    tcp_ack_server: int = 0

    # Codesys session state
    session_id: int = 0
    invoke_id: int = 0
    is_connected: bool = False
    is_authenticated: bool = False

    def next_invoke_id(self) -> int:
        """Get next invoke ID (wraps at 65535).

        Returns:
            Next invoke ID
        """
        self.invoke_id = (self.invoke_id + 1) & 0xFFFF
        return self.invoke_id


@dataclass
class LLDPConversationState(ConversationStateBase):
    """Typed state for LLDP conversations.

    LLDP (IEEE 802.1AB) is a one-way broadcast protocol - devices send
    advertisements periodically without expecting responses.

    Attributes:
        frame_count: Number of LLDP frames sent
        last_tx_time_ms: Timestamp of last transmission
        tx_interval: Transmission interval in seconds
    """

    frame_count: int = 0
    last_tx_time_ms: float = 0.0
    tx_interval: int = 30  # Default 30 seconds


@dataclass
class EtherCATConversationState(ConversationStateBase):
    """Typed state for EtherCAT conversations.

    EtherCAT is a Layer 2 real-time Ethernet protocol (EtherType 0x88A4)
    for high-speed motion control and I/O systems.

    Attributes:
        datagram_idx: Current datagram index (0-255, wraps)
        num_slaves: Number of discovered slaves
        slave_states: Dict of station_addr -> AL state
        cycle_counter: Cyclic data exchange counter
        dc_enabled: Whether Distributed Clocks are active
        dc_reference_time: DC reference timestamp
        al_state: Current Application Layer state (INIT/PREOP/SAFEOP/OP)
        logical_address: Base logical address for LRW operations
        station_addresses: List of configured station addresses
    """

    datagram_idx: int = 0
    num_slaves: int = 0
    slave_states: dict[int, int] = field(default_factory=dict)
    cycle_counter: int = 0
    dc_enabled: bool = False
    dc_reference_time: int = 0
    al_state: int = 0x01  # INIT state
    logical_address: int = 0
    station_addresses: list[int] = field(default_factory=list)

    # AL State constants
    AL_STATE_INIT = 0x01
    AL_STATE_PREOP = 0x02
    AL_STATE_BOOT = 0x03
    AL_STATE_SAFEOP = 0x04
    AL_STATE_OP = 0x08

    def next_idx(self) -> int:
        """Get next datagram index (wraps at 256).

        Returns:
            Next index value
        """
        idx = self.datagram_idx
        self.datagram_idx = (self.datagram_idx + 1) & 0xFF
        return idx

    def increment_cycle(self) -> int:
        """Increment and return cycle counter."""
        self.cycle_counter = (self.cycle_counter + 1) & 0xFFFFFFFF
        return self.cycle_counter

    def transition_state(self, new_state: int) -> None:
        """Record AL state transition.

        Args:
            new_state: New AL state value
        """
        self.al_state = new_state
        if new_state == self.AL_STATE_INIT:
            self.state_name = "init"
        elif new_state == self.AL_STATE_PREOP:
            self.state_name = "preop"
        elif new_state == self.AL_STATE_SAFEOP:
            self.state_name = "safeop"
        elif new_state == self.AL_STATE_OP:
            self.state_name = "op"


@dataclass
class FINSConversationState(ConversationStateBase):
    """Typed state for Omron FINS conversations.

    FINS (Factory Interface Network Service) is Omron's proprietary protocol
    for PLC communication over Ethernet (UDP/TCP port 9600).

    Attributes:
        sid: Service ID (transaction identifier, 0-255)
        src_node: Source node address (SA1)
        dst_node: Destination node address (DA1)
        src_network: Source network address (SNA)
        dst_network: Destination network address (DNA)
        transport_mode: "udp" or "tcp"
        tcp_client_node: Assigned TCP client node (from handshake)
        tcp_server_node: TCP server node (from handshake)
        is_connected: Whether TCP connection is established
        last_command: Last command code sent (MRC << 8 | SRC)
    """

    sid: int = 0
    src_node: int = 0x0A  # Default: node 10
    dst_node: int = 0x01  # Default: node 1
    src_network: int = 0x00  # Local network
    dst_network: int = 0x00  # Local network
    transport_mode: str = "udp"
    tcp_client_node: int = 0
    tcp_server_node: int = 0
    is_connected: bool = False
    last_command: int = 0

    def next_sid(self) -> int:
        """Get next service ID (wraps at 256).

        Returns:
            Next SID value
        """
        sid = self.sid
        self.sid = (self.sid + 1) & 0xFF
        return sid

    def record_tcp_handshake(self, client_node: int, server_node: int) -> None:
        """Record TCP node address handshake results.

        Args:
            client_node: Assigned client node address
            server_node: Server node address
        """
        self.tcp_client_node = client_node
        self.tcp_server_node = server_node
        self.src_node = client_node
        self.dst_node = server_node
        self.is_connected = True
        self.state_name = "connected"


@dataclass
class SLMPConversationState(ConversationStateBase):
    """Typed state for Mitsubishi SLMP/MC Protocol conversations.

    SLMP (Seamless Message Protocol) is Mitsubishi's standardized protocol
    for MELSEC PLCs (Q, iQ-R, iQ-F, L series) over TCP port 5000.

    Attributes:
        serial_number: 4E frame serial number for request/response matching
        network_number: Network number (0x00 = own station)
        pc_number: PC/Station number (0xFF = own station)
        dest_module_io: Destination module I/O number (0x03FF = CPU)
        dest_module_station: Destination module station number
        frame_type: "3e" or "4e"
        tcp_seq_client: Client TCP sequence number
        tcp_seq_server: Server TCP sequence number
        is_connected: Whether TCP connection is established
        last_command: Last command code sent
    """

    serial_number: int = 0
    network_number: int = 0x00  # Own station
    pc_number: int = 0xFF  # Own station
    dest_module_io: int = 0x03FF  # CPU module
    dest_module_station: int = 0x00
    frame_type: str = "3e"
    tcp_seq_client: int = 0
    tcp_seq_server: int = 0
    tcp_ack_client: int = 0
    tcp_ack_server: int = 0
    is_connected: bool = False
    last_command: int = 0

    def next_serial(self) -> int:
        """Get next serial number (wraps at 65536).

        Returns:
            Next serial number for 4E frames
        """
        serial = self.serial_number
        self.serial_number = (self.serial_number + 1) & 0xFFFF
        return serial


@dataclass
class CDPConversationState(ConversationStateBase):
    """Typed state for CDP (Cisco Discovery Protocol) conversations.

    CDP is a one-way broadcast protocol - devices send advertisements
    periodically without expecting responses.

    Attributes:
        frame_count: Number of CDP frames sent
        last_tx_time_ms: Timestamp of last transmission
        tx_interval: Transmission interval in seconds (default 60)
        ttl: Time to live in seconds (default 180)
    """

    frame_count: int = 0
    last_tx_time_ms: float = 0.0
    tx_interval: int = 60  # Default 60 seconds
    ttl: int = 180  # Default 180 seconds


@dataclass
class WMIConversationState(ConversationStateBase):
    """Typed state for WMI (Windows Management Instrumentation) conversations.

    WMI operates over DCOM/RPC with NTLMSSP authentication.

    Attributes:
        tcp_seq_client: Client TCP sequence number
        tcp_seq_server: Server TCP sequence number
        client_port: Client ephemeral port
        dynamic_port: WMI service dynamic port (from endpoint mapper)
        call_id: RPC call identifier
        is_connected: Whether TCP connection is established
        is_authenticated: Whether NTLM auth completed
        query_index: Current index in query list
    """

    tcp_seq_client: int = 0
    tcp_seq_server: int = 0
    client_port: int = 49152
    dynamic_port: int = 0
    call_id: int = 0
    is_connected: bool = False
    is_authenticated: bool = False
    query_index: int = 0


@dataclass
class FANUCConversationState(ConversationStateBase):
    """Typed state for FANUC FOCAS CNC conversations.

    FOCAS is FANUC's proprietary protocol for CNC communication.
    Default port: TCP 8193

    Attributes:
        tcp_seq_client: Client TCP sequence number
        tcp_seq_server: Server TCP sequence number
        client_port: Client ephemeral port
        handle: FOCAS connection handle
        sequence: FOCAS message sequence number
        is_connected: Whether connected to CNC
        cnc_model: Connected CNC model (e.g., "30i-B")
        poll_index: Current polling function index
    """

    tcp_seq_client: int = 0
    tcp_seq_server: int = 0
    client_port: int = 49152
    handle: int = 0
    sequence: int = 0
    is_connected: bool = False
    cnc_model: str = ""
    poll_index: int = 0


@dataclass
class DCSConversationState(ConversationStateBase):
    """Typed state for DCS (Distributed Control System) conversations.

    Supports multiple DCS vendors:
    - Emerson DeltaV (UDP 18507)
    - Honeywell Experion (TCP)
    - Yokogawa CENTUM VP (Vnet/IP UDP 230)
    - Schneider Triconex (UDP 1502)

    Attributes:
        tcp_seq_client: Client TCP sequence number (for TCP-based protocols)
        tcp_seq_server: Server TCP sequence number
        client_port: Client ephemeral port
        server_port: Server port (varies by vendor)
        sequence: Message sequence number
        session_id: Session identifier (for connection-based protocols)
        node_id: Controller node identifier
        vendor: DCS vendor enum value
        is_connected: Whether connection is established
        poll_index: Current poll cycle index
    """

    tcp_seq_client: int = 0
    tcp_seq_server: int = 0
    client_port: int = 49152
    server_port: int = 0
    sequence: int = 0
    session_id: int = 0
    node_id: int = 1
    vendor: Any = None  # DCSVendor enum
    is_connected: bool = False
    poll_index: int = 0


@dataclass
class CloudServiceConversationState(ConversationStateBase):
    """Typed state for cloud service TLS heartbeat conversations.

    Tracks TCP state for periodic TLS Client Hello heartbeats to
    cloud services (EWON Talk2M, TeamViewer, AWS IoT, etc.).

    Attributes:
        src_port: Source TCP port (ephemeral, rotated per heartbeat)
        seq_num: TCP sequence number
        hostname: Server hostname for TLS SNI extension
        tls_enabled: Whether to generate TLS Client Hello
    """

    src_port: int = 49152
    seq_num: int = 0
    hostname: str = ""
    tls_enabled: bool = True


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
        ProtocolType.MODBUS_RTU: ModbusRtuConversationState,
        ProtocolType.ETHERNET_IP: EtherNetIPConversationState,
        ProtocolType.PROFINET: ProfinetConversationState,
        ProtocolType.S7COMM: S7ConversationState,
        ProtocolType.SNMP: SNMPConversationState,
        ProtocolType.BACNET: BACnetConversationState,
        ProtocolType.DNP3: DNP3ConversationState,
        ProtocolType.IEC_104: IEC104ConversationState,
        ProtocolType.OPC_UA: OPCUAConversationState,
        ProtocolType.IEC61850: IEC61850ConversationState,
        ProtocolType.PCCC: PCCCConversationState,
        ProtocolType.CODESYS: CodesysConversationState,
        ProtocolType.LLDP: LLDPConversationState,
        ProtocolType.ETHERCAT: EtherCATConversationState,
        ProtocolType.FINS: FINSConversationState,
        ProtocolType.SLMP: SLMPConversationState,
        ProtocolType.CDP: CDPConversationState,
        ProtocolType.WMI: WMIConversationState,
        ProtocolType.FANUC: FANUCConversationState,
        ProtocolType.DCS: DCSConversationState,
        ProtocolType.CLOUD_SERVICE: CloudServiceConversationState,
    }

    state_class = state_classes.get(protocol)
    if state_class is None:
        raise ValueError(f"No conversation state class for protocol: {protocol}")

    return state_class(flow_id=flow_id, **kwargs)
