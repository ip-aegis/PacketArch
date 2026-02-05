"""WMI (Windows Management Instrumentation) packet building utilities.

WMI operates over DCOM/DCE-RPC:
- Port 135: RPC Endpoint Mapper (initial connection)
- Dynamic ports (49152-65535): Actual WMI communication

Protocol stack:
  WMI -> DCOM (ORPC) -> DCE/RPC -> TCP

Key interfaces:
- IRemoteSCMActivator: DCOM activation
- IWbemLevel1Login: WMI authentication
- IWbemServices: WMI queries
"""

import struct
import uuid
import os
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


# =============================================================================
# DCE/RPC Constants
# =============================================================================

# RPC Version
RPC_VERSION_MAJOR = 5
RPC_VERSION_MINOR = 0

# RPC Packet Types
class RPCPacketType(IntEnum):
    """DCE/RPC packet types."""
    REQUEST = 0
    PING = 1
    RESPONSE = 2
    FAULT = 3
    WORKING = 4
    NOCALL = 5
    REJECT = 6
    ACK = 7
    CL_CANCEL = 8
    FACK = 9
    CANCEL_ACK = 10
    BIND = 11
    BIND_ACK = 12
    BIND_NAK = 13
    ALTER_CONTEXT = 14
    ALTER_CONTEXT_RESP = 15
    AUTH3 = 16
    SHUTDOWN = 17
    CO_CANCEL = 18
    ORPHANED = 19


# RPC Packet Flags
class RPCPacketFlags(IntEnum):
    """DCE/RPC packet flags."""
    FIRST_FRAG = 0x01
    LAST_FRAG = 0x02
    PENDING_CANCEL = 0x04
    RESERVED_1 = 0x08
    CONC_MPX = 0x10
    DID_NOT_EXECUTE = 0x20
    MAYBE = 0x40
    OBJECT_UUID = 0x80


# NDR Data Representation (little-endian, ASCII, IEEE float)
NDR_LITTLE_ENDIAN = bytes([0x10, 0x00, 0x00, 0x00])

# Default fragment sizes
DEFAULT_MAX_XMIT_FRAG = 4280
DEFAULT_MAX_RECV_FRAG = 4280


# =============================================================================
# Interface UUIDs
# =============================================================================

# NDR Transfer Syntax UUID
NDR_UUID = uuid.UUID("8a885d04-1ceb-11c9-9fe8-08002b104860")
NDR_VERSION = (2, 0)

# IRemoteSCMActivator - DCOM activation service
IREMOTESCMACTIVATOR_UUID = uuid.UUID("000001a0-0000-0000-c000-000000000046")
IREMOTESCMACTIVATOR_VERSION = (0, 0)

# IWbemLevel1Login - WMI login interface
IWBEMLEVEL1LOGIN_UUID = uuid.UUID("f309ad18-d86a-11d0-a075-00c04fb68820")
IWBEMLEVEL1LOGIN_VERSION = (0, 0)

# IWbemServices - WMI query interface
IWBEMSERVICES_UUID = uuid.UUID("9556dc99-828c-11cf-a37e-00aa003240c7")
IWBEMSERVICES_VERSION = (0, 0)


# =============================================================================
# NTLMSSP Constants
# =============================================================================

NTLMSSP_SIGNATURE = b"NTLMSSP\x00"

class NTLMSSPMessageType(IntEnum):
    """NTLMSSP message types."""
    NEGOTIATE = 1
    CHALLENGE = 2
    AUTHENTICATE = 3


class NTLMSSPFlags(IntEnum):
    """NTLMSSP negotiation flags."""
    NEGOTIATE_UNICODE = 0x00000001
    NEGOTIATE_OEM = 0x00000002
    REQUEST_TARGET = 0x00000004
    NEGOTIATE_SIGN = 0x00000010
    NEGOTIATE_SEAL = 0x00000020
    NEGOTIATE_DATAGRAM = 0x00000040
    NEGOTIATE_LM_KEY = 0x00000080
    NEGOTIATE_NTLM = 0x00000200
    NEGOTIATE_ANONYMOUS = 0x00000800
    NEGOTIATE_OEM_DOMAIN_SUPPLIED = 0x00001000
    NEGOTIATE_OEM_WORKSTATION_SUPPLIED = 0x00002000
    NEGOTIATE_ALWAYS_SIGN = 0x00008000
    TARGET_TYPE_DOMAIN = 0x00010000
    TARGET_TYPE_SERVER = 0x00020000
    NEGOTIATE_EXTENDED_SESSIONSECURITY = 0x00080000
    NEGOTIATE_IDENTIFY = 0x00100000
    REQUEST_NON_NT_SESSION_KEY = 0x00400000
    NEGOTIATE_TARGET_INFO = 0x00800000
    NEGOTIATE_VERSION = 0x02000000
    NEGOTIATE_128 = 0x20000000
    NEGOTIATE_KEY_EXCH = 0x40000000
    NEGOTIATE_56 = 0x80000000


# =============================================================================
# WMI Query Classes
# =============================================================================

# Common WMI discovery queries
WMI_DISCOVERY_QUERIES = [
    "SELECT * FROM Win32_ComputerSystem",
    "SELECT * FROM Win32_OperatingSystem",
    "SELECT * FROM Win32_NetworkAdapterConfiguration WHERE IPEnabled = TRUE",
    "SELECT * FROM Win32_BIOS",
    "SELECT * FROM Win32_Processor",
    "SELECT * FROM Win32_LogicalDisk WHERE DriveType = 3",
]


# =============================================================================
# Helper Functions
# =============================================================================

def uuid_to_bytes_le(u: uuid.UUID) -> bytes:
    """Convert UUID to little-endian bytes (DCE/RPC format).

    DCE/RPC uses a mixed-endian format:
    - First 3 components: little-endian
    - Last 2 components: big-endian (network order)
    """
    # UUID fields: time_low (4), time_mid (2), time_hi_version (2),
    #              clock_seq_hi_variant (1), clock_seq_low (1), node (6)
    return (
        struct.pack("<I", u.time_low) +
        struct.pack("<H", u.time_mid) +
        struct.pack("<H", u.time_hi_version) +
        bytes([u.clock_seq_hi_variant, u.clock_seq_low]) +
        u.node.to_bytes(6, "big")
    )


def build_ndr_string(s: str) -> bytes:
    """Build NDR-encoded Unicode string.

    Format:
    - MaxCount (4 bytes): Maximum characters
    - Offset (4 bytes): Offset in array (0)
    - ActualCount (4 bytes): Actual characters
    - Data: UTF-16LE encoded string with null terminator
    """
    encoded = s.encode("utf-16-le") + b"\x00\x00"  # Null terminator
    char_count = len(s) + 1  # Include null
    return (
        struct.pack("<I", char_count) +  # MaxCount
        struct.pack("<I", 0) +           # Offset
        struct.pack("<I", char_count) +  # ActualCount
        encoded
    )


def pad_to_alignment(data: bytes, alignment: int = 4) -> bytes:
    """Pad data to specified alignment."""
    remainder = len(data) % alignment
    if remainder:
        data += b"\x00" * (alignment - remainder)
    return data


# =============================================================================
# DCE/RPC Packet Builders
# =============================================================================

def build_rpc_header(
    packet_type: RPCPacketType,
    flags: int,
    frag_length: int,
    auth_length: int = 0,
    call_id: int = 1,
) -> bytes:
    """Build DCE/RPC common header (16 bytes).

    Args:
        packet_type: RPC packet type
        flags: Packet flags
        frag_length: Total fragment length
        auth_length: Authentication data length
        call_id: Call identifier

    Returns:
        16-byte RPC header
    """
    return struct.pack(
        "<BBBBIHHI",
        RPC_VERSION_MAJOR,  # Version major
        RPC_VERSION_MINOR,  # Version minor
        packet_type,        # Packet type
        flags,              # Flags
        0x00000010,         # Data representation (little-endian)
        frag_length,        # Fragment length
        auth_length,        # Auth length
        call_id,            # Call ID
    )


def build_rpc_bind(
    interface_uuid: uuid.UUID,
    interface_version: tuple[int, int],
    call_id: int = 1,
    max_xmit_frag: int = DEFAULT_MAX_XMIT_FRAG,
    max_recv_frag: int = DEFAULT_MAX_RECV_FRAG,
    assoc_group: int = 0,
) -> bytes:
    """Build RPC BIND PDU.

    Args:
        interface_uuid: Target interface UUID
        interface_version: Interface version (major, minor)
        call_id: Call identifier
        max_xmit_frag: Max transmit fragment size
        max_recv_frag: Max receive fragment size
        assoc_group: Association group ID (0 for new)

    Returns:
        Complete RPC BIND PDU
    """
    # Build presentation context
    context_id = 0
    num_transfer_syntaxes = 1

    # Abstract syntax (interface)
    abstract_syntax = (
        uuid_to_bytes_le(interface_uuid) +
        struct.pack("<HH", interface_version[0], interface_version[1])
    )

    # Transfer syntax (NDR)
    transfer_syntax = (
        uuid_to_bytes_le(NDR_UUID) +
        struct.pack("<HH", NDR_VERSION[0], NDR_VERSION[1])
    )

    # Context list
    num_contexts = 1
    context_list = (
        struct.pack("<BBH", context_id, num_transfer_syntaxes, 0) +  # Context header + padding
        abstract_syntax +
        transfer_syntax
    )

    # BIND body
    bind_body = (
        struct.pack("<HH", max_xmit_frag, max_recv_frag) +
        struct.pack("<I", assoc_group) +
        struct.pack("<B", num_contexts) +
        b"\x00" * 3 +  # Padding
        context_list
    )

    # Calculate fragment length
    frag_length = 16 + len(bind_body)

    # Build header
    flags = RPCPacketFlags.FIRST_FRAG | RPCPacketFlags.LAST_FRAG
    header = build_rpc_header(RPCPacketType.BIND, flags, frag_length, 0, call_id)

    return header + bind_body


def build_rpc_bind_ack(
    call_id: int = 1,
    max_xmit_frag: int = DEFAULT_MAX_XMIT_FRAG,
    max_recv_frag: int = DEFAULT_MAX_RECV_FRAG,
    assoc_group: int = 0x12345678,
    secondary_addr: str = "",
    result: int = 0,  # 0 = acceptance
) -> bytes:
    """Build RPC BIND_ACK PDU.

    Args:
        call_id: Call identifier (echo from BIND)
        max_xmit_frag: Agreed max transmit fragment
        max_recv_frag: Agreed max receive fragment
        assoc_group: Association group ID
        secondary_addr: Secondary address (port as string)
        result: Context negotiation result

    Returns:
        Complete RPC BIND_ACK PDU
    """
    # Secondary address with length
    sec_addr_bytes = secondary_addr.encode("ascii") + b"\x00"
    sec_addr_len = len(sec_addr_bytes)

    # Pad to 4-byte alignment
    sec_addr_padded = pad_to_alignment(sec_addr_bytes, 4)

    # Result list (single context)
    # Result (2), Reason (2), Transfer syntax UUID (16), Version (4)
    result_entry = (
        struct.pack("<HH", result, 0) +
        uuid_to_bytes_le(NDR_UUID) +
        struct.pack("<HH", NDR_VERSION[0], NDR_VERSION[1])
    )

    num_results = 1
    result_list = struct.pack("<BBH", num_results, 0, 0) + result_entry

    # BIND_ACK body
    bind_ack_body = (
        struct.pack("<HH", max_xmit_frag, max_recv_frag) +
        struct.pack("<I", assoc_group) +
        struct.pack("<H", sec_addr_len) +
        sec_addr_padded +
        result_list
    )

    # Calculate fragment length
    frag_length = 16 + len(bind_ack_body)

    # Build header
    flags = RPCPacketFlags.FIRST_FRAG | RPCPacketFlags.LAST_FRAG
    header = build_rpc_header(RPCPacketType.BIND_ACK, flags, frag_length, 0, call_id)

    return header + bind_ack_body


def build_rpc_request(
    opnum: int,
    stub_data: bytes,
    call_id: int = 1,
    context_id: int = 0,
    object_uuid: uuid.UUID | None = None,
) -> bytes:
    """Build RPC REQUEST PDU.

    Args:
        opnum: Operation number (method index)
        stub_data: Marshaled call arguments
        call_id: Call identifier
        context_id: Presentation context ID
        object_uuid: Object UUID (for ORPC)

    Returns:
        Complete RPC REQUEST PDU
    """
    flags = RPCPacketFlags.FIRST_FRAG | RPCPacketFlags.LAST_FRAG

    # Request-specific fields
    alloc_hint = len(stub_data)

    request_body = struct.pack("<IHH", alloc_hint, context_id, opnum)

    # Add object UUID if present
    if object_uuid:
        flags |= RPCPacketFlags.OBJECT_UUID
        request_body = uuid_to_bytes_le(object_uuid) + request_body

    request_body += stub_data

    # Calculate fragment length
    frag_length = 16 + len(request_body)

    # Build header
    header = build_rpc_header(RPCPacketType.REQUEST, flags, frag_length, 0, call_id)

    return header + request_body


def build_rpc_response(
    stub_data: bytes,
    call_id: int = 1,
    context_id: int = 0,
) -> bytes:
    """Build RPC RESPONSE PDU.

    Args:
        stub_data: Marshaled response data
        call_id: Call identifier
        context_id: Presentation context ID

    Returns:
        Complete RPC RESPONSE PDU
    """
    # Response-specific fields
    alloc_hint = len(stub_data)
    cancel_count = 0

    response_body = (
        struct.pack("<IHH", alloc_hint, context_id, cancel_count) +
        stub_data
    )

    # Calculate fragment length
    frag_length = 16 + len(response_body)

    # Build header
    flags = RPCPacketFlags.FIRST_FRAG | RPCPacketFlags.LAST_FRAG
    header = build_rpc_header(RPCPacketType.RESPONSE, flags, frag_length, 0, call_id)

    return header + response_body


# =============================================================================
# NTLMSSP Message Builders
# =============================================================================

def build_ntlmssp_negotiate(
    domain: str = "",
    workstation: str = "",
) -> bytes:
    """Build NTLMSSP Negotiate message (Type 1).

    Args:
        domain: Domain name (optional)
        workstation: Workstation name (optional)

    Returns:
        NTLMSSP Negotiate message
    """
    flags = (
        NTLMSSPFlags.NEGOTIATE_UNICODE |
        NTLMSSPFlags.NEGOTIATE_NTLM |
        NTLMSSPFlags.NEGOTIATE_SIGN |
        NTLMSSPFlags.NEGOTIATE_SEAL |
        NTLMSSPFlags.REQUEST_TARGET |
        NTLMSSPFlags.NEGOTIATE_EXTENDED_SESSIONSECURITY |
        NTLMSSPFlags.NEGOTIATE_VERSION |
        NTLMSSPFlags.NEGOTIATE_128 |
        NTLMSSPFlags.NEGOTIATE_56
    )

    # Encode domain and workstation
    domain_bytes = domain.encode("ascii")
    workstation_bytes = workstation.encode("ascii")

    # Calculate offsets (after fixed fields)
    offset = 32  # Fixed header size
    if flags & NTLMSSPFlags.NEGOTIATE_VERSION:
        offset += 8  # Version field

    domain_offset = offset
    workstation_offset = domain_offset + len(domain_bytes)

    # Build message
    message = (
        NTLMSSP_SIGNATURE +
        struct.pack("<I", NTLMSSPMessageType.NEGOTIATE) +
        struct.pack("<I", flags) +
        # Domain fields (len, max_len, offset)
        struct.pack("<HHI", len(domain_bytes), len(domain_bytes), domain_offset) +
        # Workstation fields (len, max_len, offset)
        struct.pack("<HHI", len(workstation_bytes), len(workstation_bytes), workstation_offset)
    )

    # Add version if negotiated
    if flags & NTLMSSPFlags.NEGOTIATE_VERSION:
        # Windows 10 version
        message += struct.pack("<BBHBBBB", 10, 0, 19041, 15, 0, 0, 0)

    # Add payload
    message += domain_bytes + workstation_bytes

    return message


def build_ntlmssp_challenge(
    target_name: str = "WORKGROUP",
    challenge: bytes | None = None,
    target_info: bytes | None = None,
) -> bytes:
    """Build NTLMSSP Challenge message (Type 2).

    Args:
        target_name: Target name/domain
        challenge: 8-byte server challenge (random if not provided)
        target_info: Target info AV pairs

    Returns:
        NTLMSSP Challenge message
    """
    if challenge is None:
        challenge = os.urandom(8)

    flags = (
        NTLMSSPFlags.NEGOTIATE_UNICODE |
        NTLMSSPFlags.NEGOTIATE_NTLM |
        NTLMSSPFlags.NEGOTIATE_SIGN |
        NTLMSSPFlags.NEGOTIATE_SEAL |
        NTLMSSPFlags.TARGET_TYPE_DOMAIN |
        NTLMSSPFlags.NEGOTIATE_TARGET_INFO |
        NTLMSSPFlags.NEGOTIATE_EXTENDED_SESSIONSECURITY |
        NTLMSSPFlags.NEGOTIATE_VERSION |
        NTLMSSPFlags.NEGOTIATE_128 |
        NTLMSSPFlags.NEGOTIATE_56
    )

    # Encode target name as UTF-16LE
    target_name_bytes = target_name.encode("utf-16-le")

    # Build target info if not provided
    if target_info is None:
        target_info = build_target_info(target_name)

    # Calculate offsets
    offset = 56  # Fixed header size with version
    target_name_offset = offset
    target_info_offset = target_name_offset + len(target_name_bytes)

    # Build message
    message = (
        NTLMSSP_SIGNATURE +
        struct.pack("<I", NTLMSSPMessageType.CHALLENGE) +
        # Target name fields
        struct.pack("<HHI", len(target_name_bytes), len(target_name_bytes), target_name_offset) +
        struct.pack("<I", flags) +
        challenge +
        b"\x00" * 8 +  # Reserved
        # Target info fields
        struct.pack("<HHI", len(target_info), len(target_info), target_info_offset) +
        # Version (Windows 10)
        struct.pack("<BBHBBBB", 10, 0, 19041, 15, 0, 0, 0) +
        target_name_bytes +
        target_info
    )

    return message


def build_target_info(domain: str = "WORKGROUP") -> bytes:
    """Build NTLMSSP target info AV pairs.

    Args:
        domain: Domain/workgroup name

    Returns:
        Target info structure
    """
    # AV_PAIR types
    MsvAvNbDomainName = 2
    MsvAvNbComputerName = 1
    MsvAvDnsDomainName = 4
    MsvAvDnsComputerName = 3
    MsvAvEOL = 0

    def av_pair(av_id: int, value: bytes) -> bytes:
        return struct.pack("<HH", av_id, len(value)) + value

    domain_utf16 = domain.encode("utf-16-le")
    computer_utf16 = "WIN-SERVER".encode("utf-16-le")

    info = (
        av_pair(MsvAvNbDomainName, domain_utf16) +
        av_pair(MsvAvNbComputerName, computer_utf16) +
        av_pair(MsvAvDnsDomainName, domain_utf16) +
        av_pair(MsvAvDnsComputerName, computer_utf16) +
        av_pair(MsvAvEOL, b"")
    )

    return info


def build_ntlmssp_authenticate(
    domain: str = "WORKGROUP",
    username: str = "Administrator",
    workstation: str = "CLIENT",
    lm_response: bytes | None = None,
    nt_response: bytes | None = None,
) -> bytes:
    """Build NTLMSSP Authenticate message (Type 3).

    Args:
        domain: Domain name
        username: User name
        workstation: Workstation name
        lm_response: LM challenge response (simulated)
        nt_response: NT challenge response (simulated)

    Returns:
        NTLMSSP Authenticate message
    """
    flags = (
        NTLMSSPFlags.NEGOTIATE_UNICODE |
        NTLMSSPFlags.NEGOTIATE_NTLM |
        NTLMSSPFlags.NEGOTIATE_SIGN |
        NTLMSSPFlags.NEGOTIATE_SEAL |
        NTLMSSPFlags.NEGOTIATE_EXTENDED_SESSIONSECURITY |
        NTLMSSPFlags.NEGOTIATE_VERSION |
        NTLMSSPFlags.NEGOTIATE_128 |
        NTLMSSPFlags.NEGOTIATE_56 |
        NTLMSSPFlags.NEGOTIATE_KEY_EXCH
    )

    # Generate simulated responses if not provided
    if lm_response is None:
        lm_response = b"\x00" * 24
    if nt_response is None:
        # Simulated NTLMv2 response (16-byte HMAC + variable client blob)
        nt_response = os.urandom(16) + os.urandom(84)  # 100 bytes typical

    # Encode strings as UTF-16LE
    domain_bytes = domain.encode("utf-16-le")
    username_bytes = username.encode("utf-16-le")
    workstation_bytes = workstation.encode("utf-16-le")

    # Encrypted random session key (simulated)
    session_key = os.urandom(16)

    # Calculate offsets (after fixed header of 88 bytes)
    offset = 88
    lm_offset = offset
    nt_offset = lm_offset + len(lm_response)
    domain_offset = nt_offset + len(nt_response)
    username_offset = domain_offset + len(domain_bytes)
    workstation_offset = username_offset + len(username_bytes)
    session_key_offset = workstation_offset + len(workstation_bytes)

    # Build message
    message = (
        NTLMSSP_SIGNATURE +
        struct.pack("<I", NTLMSSPMessageType.AUTHENTICATE) +
        # LM response
        struct.pack("<HHI", len(lm_response), len(lm_response), lm_offset) +
        # NT response
        struct.pack("<HHI", len(nt_response), len(nt_response), nt_offset) +
        # Domain
        struct.pack("<HHI", len(domain_bytes), len(domain_bytes), domain_offset) +
        # Username
        struct.pack("<HHI", len(username_bytes), len(username_bytes), username_offset) +
        # Workstation
        struct.pack("<HHI", len(workstation_bytes), len(workstation_bytes), workstation_offset) +
        # Session key
        struct.pack("<HHI", len(session_key), len(session_key), session_key_offset) +
        struct.pack("<I", flags) +
        # Version
        struct.pack("<BBHBBBB", 10, 0, 19041, 15, 0, 0, 0) +
        # MIC placeholder (16 bytes)
        b"\x00" * 16 +
        # Payload
        lm_response +
        nt_response +
        domain_bytes +
        username_bytes +
        workstation_bytes +
        session_key
    )

    return message


# =============================================================================
# DCOM/ORPC Structures
# =============================================================================

def build_orpcthis() -> bytes:
    """Build ORPCTHIS header for DCOM calls.

    Returns:
        ORPCTHIS structure
    """
    # Version (5.7)
    version = struct.pack("<HH", 5, 7)
    flags = struct.pack("<I", 0)
    reserved = struct.pack("<I", 0)

    # Causality ID (random GUID)
    causality_id = os.urandom(16)

    # Extensions (none)
    extensions = struct.pack("<I", 0)

    return version + flags + reserved + causality_id + extensions


def build_orpcthat() -> bytes:
    """Build ORPCTHAT header for DCOM responses.

    Returns:
        ORPCTHAT structure
    """
    flags = struct.pack("<I", 0)
    extensions = struct.pack("<I", 0)

    return flags + extensions


# =============================================================================
# WMI Query Builders
# =============================================================================

def build_wmi_query_request(
    query: str,
    namespace: str = "root\\cimv2",
) -> bytes:
    """Build WMI ExecQuery request stub data.

    Args:
        query: WQL query string
        namespace: WMI namespace

    Returns:
        Marshaled request data
    """
    # ORPCTHIS header
    orpcthis = build_orpcthis()

    # Query language ("WQL")
    query_lang = build_ndr_string("WQL")

    # Query string
    query_str = build_ndr_string(query)

    # Flags (0 = default)
    flags = struct.pack("<I", 0)

    # Context pointer (NULL)
    context_ptr = struct.pack("<I", 0)

    return orpcthis + query_lang + query_str + flags + context_ptr


def build_wmi_query_response(
    results: list[dict[str, Any]],
) -> bytes:
    """Build WMI ExecQuery response stub data.

    Args:
        results: List of result objects (simplified)

    Returns:
        Marshaled response data
    """
    # ORPCTHAT header
    orpcthat = build_orpcthat()

    # Return code (success = 0)
    hresult = struct.pack("<I", 0)

    # Enumerator pointer (simulated OBJREF)
    # For simulation, we just include minimal response
    objref_flags = struct.pack("<I", 1)  # OBJREF_STANDARD

    # Simplified: just indicate success with object count
    result_count = struct.pack("<I", len(results))

    return orpcthat + hresult + objref_flags + result_count


# =============================================================================
# Complete WMI Session Builders
# =============================================================================

def build_wmi_bind_to_endpoint_mapper(call_id: int = 1) -> bytes:
    """Build RPC BIND to endpoint mapper (port 135).

    Args:
        call_id: Call identifier

    Returns:
        RPC BIND PDU for IRemoteSCMActivator
    """
    return build_rpc_bind(
        interface_uuid=IREMOTESCMACTIVATOR_UUID,
        interface_version=IREMOTESCMACTIVATOR_VERSION,
        call_id=call_id,
    )


def build_wmi_bind_ack_endpoint_mapper(
    call_id: int = 1,
    dynamic_port: int = 49152,
) -> bytes:
    """Build RPC BIND_ACK from endpoint mapper.

    Args:
        call_id: Call identifier
        dynamic_port: Dynamic port for WMI service

    Returns:
        RPC BIND_ACK PDU
    """
    return build_rpc_bind_ack(
        call_id=call_id,
        secondary_addr=str(dynamic_port),
    )


def build_wmi_bind_to_wbem_login(call_id: int = 1) -> bytes:
    """Build RPC BIND to IWbemLevel1Login.

    Args:
        call_id: Call identifier

    Returns:
        RPC BIND PDU
    """
    return build_rpc_bind(
        interface_uuid=IWBEMLEVEL1LOGIN_UUID,
        interface_version=IWBEMLEVEL1LOGIN_VERSION,
        call_id=call_id,
    )


def build_wmi_bind_to_services(call_id: int = 1) -> bytes:
    """Build RPC BIND to IWbemServices.

    Args:
        call_id: Call identifier

    Returns:
        RPC BIND PDU
    """
    return build_rpc_bind(
        interface_uuid=IWBEMSERVICES_UUID,
        interface_version=IWBEMSERVICES_VERSION,
        call_id=call_id,
    )


def build_wmi_exec_query(
    query: str,
    call_id: int = 1,
) -> bytes:
    """Build WMI ExecQuery RPC REQUEST.

    Args:
        query: WQL query string
        call_id: Call identifier

    Returns:
        RPC REQUEST PDU with WMI query
    """
    stub_data = build_wmi_query_request(query)

    return build_rpc_request(
        opnum=20,  # ExecQuery opnum
        stub_data=stub_data,
        call_id=call_id,
    )
