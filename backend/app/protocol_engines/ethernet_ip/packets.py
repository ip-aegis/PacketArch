"""EtherNet/IP packet building utilities.

Includes ListIdentity support for hyper-realistic device emulation.
"""

import struct
from typing import TYPE_CHECKING, Any

from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

from app.protocol_engines.tcp_builder import extract_tcp_options
from app.protocol_engines.types import DeviceContext

if TYPE_CHECKING:
    from app.protocol_engines.fingerprint_applicator import FingerprintApplicator, TcpOptions

# EtherNet/IP Commands
ENIP_CMD_NOP = 0x0000
ENIP_CMD_LIST_SERVICES = 0x0004
ENIP_CMD_LIST_IDENTITY = 0x0063
ENIP_CMD_LIST_INTERFACES = 0x0064
ENIP_CMD_REGISTER_SESSION = 0x0065
ENIP_CMD_UNREGISTER_SESSION = 0x0066
ENIP_CMD_SEND_RR_DATA = 0x006F
ENIP_CMD_SEND_UNIT_DATA = 0x0070

# EtherNet/IP Status Codes
ENIP_STATUS_SUCCESS = 0x0000

# CPF Item Type IDs
CPF_TYPE_NULL = 0x0000
CPF_TYPE_CONNECTED_ADDRESS = 0x00A1
CPF_TYPE_CONNECTED_DATA = 0x00B1
CPF_TYPE_UNCONNECTED_DATA = 0x00B2
CPF_TYPE_LIST_SERVICES = 0x0100
CPF_TYPE_SOCKADDR_INFO_OT = 0x8000
CPF_TYPE_SOCKADDR_INFO_TO = 0x8001
CPF_TYPE_SEQUENCED_ADDRESS = 0x8002

# CIP Device Types
CIP_DEVICE_TYPE_PLC = 14  # Programmable Logic Controller
CIP_DEVICE_TYPE_HMI = 24  # Human-Machine Interface
CIP_DEVICE_TYPE_DRIVE = 2  # AC Drive
CIP_DEVICE_TYPE_COMM_ADAPTER = 12  # Communications Adapter


def build_list_identity_request() -> bytes:
    """Build ListIdentity request for device discovery.

    This is sent as a broadcast/multicast UDP packet to discover
    EtherNet/IP devices on the network.

    Returns:
        Complete ListIdentity request payload (encapsulation header only)
    """
    # ListIdentity has no data payload, just the header
    return build_encapsulation_header(
        command=ENIP_CMD_LIST_IDENTITY,
        length=0,
        session_handle=0,
    )


def build_list_identity_response(
    fingerprint_applicator: "FingerprintApplicator",
    socket_addr: tuple[str, int] | None = None,
    sender_context: bytes = b"\x00" * 8,
) -> bytes:
    """Build ListIdentity response using fingerprint data.

    This response identifies the device with vendor-specific information
    that vulnerability scanners use for device classification.

    Args:
        fingerprint_applicator: Applicator with vendor fingerprint data
        socket_addr: (IP, port) tuple for the responding device
        sender_context: 8-byte sender context from request

    Returns:
        Complete ListIdentity response payload
    """
    # Get identity data from fingerprint via identity builder
    response = fingerprint_applicator.get_identity_response(
        "ethernet_ip", socket_addr=socket_addr
    )
    identity_data = response.raw_bytes

    # Build CPF (Common Packet Format) structure
    # Item count: 1
    # Item 1: ListIdentity (0x000C)
    cpf_item_type = 0x000C
    cpf_item_length = len(identity_data)

    cpf_data = struct.pack("<HHH", 1, cpf_item_type, cpf_item_length) + identity_data

    # Build encapsulation header
    header = build_encapsulation_header(
        command=ENIP_CMD_LIST_IDENTITY,
        length=len(cpf_data),
        session_handle=0,
        sender_context=sender_context,
    )

    return header + cpf_data


def build_list_identity_response_raw(
    vendor_id: int = 1,
    device_type: int = CIP_DEVICE_TYPE_PLC,
    product_code: int = 1,
    revision_major: int = 1,
    revision_minor: int = 0,
    serial_number: int = 0x12345678,
    product_name: str = "Unknown Device",
    state: int = 3,
    socket_addr: tuple[str, int] | None = None,
    sender_context: bytes = b"\x00" * 8,
) -> bytes:
    """Build ListIdentity response with explicit parameters.

    Use this when you don't have a fingerprint applicator but need
    to specify identity fields directly.

    Args:
        vendor_id: ODVA Vendor ID (1=Rockwell, 67=Schneider, etc.)
        device_type: CIP device type code
        product_code: Product code
        revision_major: Major revision
        revision_minor: Minor revision
        serial_number: Device serial number
        product_name: Product name string (max 32 chars)
        state: Device state (3=operational)
        socket_addr: (IP, port) tuple
        sender_context: 8-byte sender context

    Returns:
        Complete ListIdentity response payload
    """
    # Socket address
    if socket_addr:
        ip_str, port = socket_addr
        ip_parts = [int(x) for x in ip_str.split(".")]
    else:
        ip_parts = [192, 168, 1, 100]
        port = 44818

    # Encode product name
    product_name_bytes = product_name.encode("utf-8")[:32]
    product_name_len = len(product_name_bytes)

    # Build identity item data
    # Socket address info (16 bytes)
    sin_family = 2  # AF_INET
    sin_port = ((port >> 8) & 0xFF) | ((port & 0xFF) << 8)  # Big-endian port
    sin_addr = (ip_parts[0] << 24) | (ip_parts[1] << 16) | (ip_parts[2] << 8) | ip_parts[3]

    identity_data = struct.pack(
        "<HHIH8s",
        1,  # Encapsulation protocol version
        sin_family,
        sin_port,
        sin_addr,
        b"\x00" * 8,  # sin_zero
    )

    # Add vendor info
    identity_data += struct.pack(
        "<HHHHBBHI",
        vendor_id,
        device_type,
        product_code,
        (revision_major << 8) | revision_minor,  # Revision as 16-bit
        0x00,  # Status low byte
        0x30,  # Status high byte (Owned, Configured)
        serial_number,
        product_name_len,
    )
    identity_data += product_name_bytes
    identity_data += struct.pack("<B", state)

    # Build CPF structure
    cpf_item_type = 0x000C  # ListIdentity
    cpf_data = struct.pack("<HHH", 1, cpf_item_type, len(identity_data)) + identity_data

    # Build header
    header = build_encapsulation_header(
        command=ENIP_CMD_LIST_IDENTITY,
        length=len(cpf_data),
        session_handle=0,
        sender_context=sender_context,
    )

    return header + cpf_data


def build_encapsulation_header(
    command: int,
    length: int,
    session_handle: int = 0,
    status: int = ENIP_STATUS_SUCCESS,
    sender_context: bytes = b"\x00" * 8,
    options: int = 0,
) -> bytes:
    """Build EtherNet/IP encapsulation header.

    Args:
        command: EtherNet/IP command code
        length: Length of encapsulated data
        session_handle: Session handle (0 for RegisterSession request)
        status: Status code
        sender_context: 8-byte sender context
        options: Options flags

    Returns:
        24-byte encapsulation header
    """
    return struct.pack(
        "<HHIIQQ",
        command,
        length,
        session_handle,
        status,
        int.from_bytes(sender_context[:8], "little"),
        options,
    )


def build_register_session_request() -> bytes:
    """Build RegisterSession request.

    Returns:
        Complete RegisterSession request payload
    """
    # RegisterSession data
    protocol_version = 1
    options_flags = 0

    data = struct.pack("<HH", protocol_version, options_flags)

    # Build header
    header = build_encapsulation_header(
        command=ENIP_CMD_REGISTER_SESSION,
        length=len(data),
        session_handle=0,
    )

    return header + data


def build_register_session_response(session_handle: int) -> bytes:
    """Build RegisterSession response.

    Args:
        session_handle: Assigned session handle

    Returns:
        Complete RegisterSession response payload
    """
    # RegisterSession data
    protocol_version = 1
    options_flags = 0

    data = struct.pack("<HH", protocol_version, options_flags)

    # Build header
    header = build_encapsulation_header(
        command=ENIP_CMD_REGISTER_SESSION,
        length=len(data),
        session_handle=session_handle,
    )

    return header + data


def build_cip_forward_open_request(
    connection_path: bytes = b"\x20\x04\x24\x01",  # Default: Class 4, Instance 1
) -> bytes:
    """Build CIP ForwardOpen request.

    Args:
        connection_path: Connection path (default targets Message Router)

    Returns:
        CIP ForwardOpen request data
    """
    # ForwardOpen parameters (simplified)
    priority_tick_time = 0x0A  # Priority/tick time
    timeout_ticks = 0xF0  # Timeout ticks
    o_to_t_connection_id = 0x12345678  # O->T connection ID
    t_to_o_connection_id = 0x87654321  # T->O connection ID
    connection_serial_number = 0x0001  # Connection serial number
    vendor_id = 0x0001  # Vendor ID
    originator_serial_number = 0x12345678  # Originator serial number
    timeout_multiplier = 0x00  # Connection timeout multiplier
    o_to_t_rpi = 0x00200000  # O->T RPI (32ms)
    o_to_t_network_params = 0x4321  # O->T network connection parameters
    t_to_o_rpi = 0x00200000  # T->O RPI (32ms)
    t_to_o_network_params = 0x4321  # T->O network connection parameters
    transport_class_trigger = 0xA3  # Transport class/trigger

    # Build ForwardOpen data (simplified version)
    forward_open = struct.pack(
        "<BBIIHHIBIIHIHB",
        priority_tick_time,
        timeout_ticks,
        o_to_t_connection_id,
        t_to_o_connection_id,
        connection_serial_number,
        vendor_id,
        originator_serial_number,
        timeout_multiplier,
        0,  # Reserved
        o_to_t_rpi,
        o_to_t_network_params,
        t_to_o_rpi,
        t_to_o_network_params,
        transport_class_trigger,
    )

    # Add connection path
    connection_path_size = len(connection_path) // 2  # Size in words
    forward_open += struct.pack("B", connection_path_size) + connection_path

    return forward_open


def build_cip_forward_open_response(success: bool = True) -> bytes:
    """Build CIP ForwardOpen response.

    Args:
        success: Whether the ForwardOpen was successful

    Returns:
        CIP ForwardOpen response data
    """
    if success:
        # Success response
        o_to_t_connection_id = 0x12345678
        t_to_o_connection_id = 0x87654321
        connection_serial_number = 0x0001
        vendor_id = 0x0001
        originator_serial_number = 0x12345678
        o_to_t_api = 0x00200000  # Actual packet interval
        t_to_o_api = 0x00200000

        return struct.pack(
            "<IIHIII",
            o_to_t_connection_id,
            t_to_o_connection_id,
            connection_serial_number,
            vendor_id,
            originator_serial_number,
            o_to_t_api,
        )
    else:
        # Error response (simplified)
        return b"\x00\x00"


def build_cip_io_data(data: bytes) -> bytes:
    """Build CIP I/O data packet.

    Args:
        data: I/O data bytes

    Returns:
        Complete I/O data packet
    """
    # Sequence count (incremented for each packet)
    sequence_count = 0x0001

    return struct.pack("<H", sequence_count) + data


# ========== CIP Error Response Functions ==========


# CIP General Status Codes
CIP_STATUS_SUCCESS = 0x00
CIP_STATUS_CONNECTION_FAILURE = 0x01
CIP_STATUS_RESOURCE_UNAVAILABLE = 0x02
CIP_STATUS_INVALID_PARAMETER_VALUE = 0x03
CIP_STATUS_PATH_SEGMENT_ERROR = 0x04
CIP_STATUS_PATH_DESTINATION_UNKNOWN = 0x05
CIP_STATUS_PARTIAL_TRANSFER = 0x06
CIP_STATUS_CONNECTION_LOST = 0x07
CIP_STATUS_SERVICE_NOT_SUPPORTED = 0x08
CIP_STATUS_INVALID_ATTRIBUTE_VALUE = 0x09
CIP_STATUS_ATTRIBUTE_LIST_ERROR = 0x0A
CIP_STATUS_ALREADY_IN_STATE = 0x0B
CIP_STATUS_OBJECT_STATE_CONFLICT = 0x0C
CIP_STATUS_OBJECT_ALREADY_EXISTS = 0x0D
CIP_STATUS_ATTRIBUTE_NOT_SETTABLE = 0x0E
CIP_STATUS_PRIVILEGE_VIOLATION = 0x0F
CIP_STATUS_DEVICE_STATE_CONFLICT = 0x10
CIP_STATUS_REPLY_DATA_TOO_LARGE = 0x11
CIP_STATUS_FRAGMENTATION_OF_PRIMITIVE = 0x12
CIP_STATUS_NOT_ENOUGH_DATA = 0x13
CIP_STATUS_ATTRIBUTE_NOT_SUPPORTED = 0x14
CIP_STATUS_TOO_MUCH_DATA = 0x15
CIP_STATUS_OBJECT_DOES_NOT_EXIST = 0x16
CIP_STATUS_NO_STORED_ATTRIBUTE_DATA = 0x18
CIP_STATUS_STORE_OPERATION_FAILURE = 0x19
CIP_STATUS_INVALID_PARAMETER = 0x20
CIP_STATUS_VENDOR_SPECIFIC_ERROR = 0xFF

# Extended Status Codes for Connection Manager
CIP_EXT_STATUS_CONNECTION_IN_USE = 0x0100
CIP_EXT_STATUS_TRANSPORT_CLASS_TRIGGER = 0x0103
CIP_EXT_STATUS_OWNERSHIP_CONFLICT = 0x0106
CIP_EXT_STATUS_CONNECTION_NOT_FOUND = 0x0107
CIP_EXT_STATUS_INVALID_CONNECTION_TYPE = 0x0108
CIP_EXT_STATUS_INVALID_CONNECTION_SIZE = 0x0109
CIP_EXT_STATUS_RPI_NOT_SUPPORTED = 0x0110
CIP_EXT_STATUS_RPI_VALUE_NOT_ACCEPTABLE = 0x0111
CIP_EXT_STATUS_CONN_MANAGER_ERROR = 0x0113
CIP_EXT_STATUS_TIMEOUT_MULTIPLIER = 0x0114
CIP_EXT_STATUS_DUPLICATE_FORWARD_OPEN = 0x0115
CIP_EXT_STATUS_TARGET_CONNECTION_NOT_FOUND = 0x0116
CIP_EXT_STATUS_PARAMETER_ERROR = 0x0117


def build_cip_error_response(
    service: int,
    status: int,
    extended_status: int | None = None,
    additional_data: bytes = b"",
) -> bytes:
    """Build a CIP error response.

    Args:
        service: CIP service code (with reply bit 0x80)
        status: CIP general status code
        extended_status: Optional extended status code
        additional_data: Additional error data

    Returns:
        CIP error response bytes
    """
    # Reply bit is 0x80 OR'd with original service
    reply_service = service | 0x80

    # Build error response
    if extended_status is not None:
        # Include extended status
        response = struct.pack(
            "<BBBB",
            reply_service,
            0x00,  # Reserved
            status,
            1,  # Extended status size (1 word)
        )
        response += struct.pack("<H", extended_status)
    else:
        # No extended status
        response = struct.pack(
            "<BBBB",
            reply_service,
            0x00,  # Reserved
            status,
            0,  # Extended status size (0)
        )

    response += additional_data
    return response


def build_forward_open_error_response(
    status: int = CIP_STATUS_CONNECTION_FAILURE,
    extended_status: int = CIP_EXT_STATUS_CONNECTION_NOT_FOUND,
) -> bytes:
    """Build ForwardOpen error response.

    Args:
        status: CIP general status code
        extended_status: Extended status code

    Returns:
        ForwardOpen error response bytes
    """
    # ForwardOpen service code is 0x54
    return build_cip_error_response(0x54, status, extended_status)


def build_forward_close_error_response(
    status: int = CIP_STATUS_CONNECTION_FAILURE,
    extended_status: int = CIP_EXT_STATUS_CONNECTION_NOT_FOUND,
) -> bytes:
    """Build ForwardClose error response.

    Args:
        status: CIP general status code
        extended_status: Extended status code

    Returns:
        ForwardClose error response bytes
    """
    # ForwardClose service code is 0x4E
    return build_cip_error_response(0x4E, status, extended_status)


def build_read_attribute_error_response(
    status: int = CIP_STATUS_ATTRIBUTE_NOT_SUPPORTED,
) -> bytes:
    """Build GetAttributeSingle error response.

    Args:
        status: CIP general status code

    Returns:
        Error response bytes
    """
    # GetAttributeSingle service code is 0x0E
    return build_cip_error_response(0x0E, status)


def build_send_rr_data_error_response(
    session_handle: int,
    sender_context: bytes = b"\x00" * 8,
    status: int = CIP_STATUS_SERVICE_NOT_SUPPORTED,
    extended_status: int | None = None,
) -> bytes:
    """Build SendRRData encapsulated error response.

    Args:
        session_handle: Session handle
        sender_context: Sender context from request
        status: CIP general status code
        extended_status: Optional extended status

    Returns:
        Complete SendRRData error response
    """
    # Build CIP error response
    cip_error = build_cip_error_response(0x00, status, extended_status)

    # Build CPF with error
    # Null address item + unconnected data item
    cpf_data = struct.pack(
        "<HHHH",
        2,  # Item count
        CPF_TYPE_NULL,  # Null address
        0,  # Null length
        CPF_TYPE_UNCONNECTED_DATA,  # Unconnected data
    )
    cpf_data += struct.pack("<H", len(cip_error))
    cpf_data += cip_error

    # Build encapsulation header
    header = build_encapsulation_header(
        command=ENIP_CMD_SEND_RR_DATA,
        length=len(cpf_data) + 6,  # CPF + interface handle + timeout
        session_handle=session_handle,
        sender_context=sender_context,
    )

    # Interface handle (0) + timeout (0)
    interface_timeout = struct.pack("<IH", 0, 0)

    return header + interface_timeout + cpf_data


def build_register_session_error_response(
    status: int = 0x0001,  # Invalid/unsupported protocol version
    sender_context: bytes = b"\x00" * 8,
) -> bytes:
    """Build RegisterSession error response.

    Args:
        status: Encapsulation status code
        sender_context: Sender context from request

    Returns:
        Complete RegisterSession error response
    """
    # RegisterSession response with error status
    protocol_version = 1
    options_flags = 0

    data = struct.pack("<HH", protocol_version, options_flags)

    # Build header with error status
    header = struct.pack(
        "<HHIIQQ",
        ENIP_CMD_REGISTER_SESSION,
        len(data),
        0,  # Session handle (0 for error)
        status,
        int.from_bytes(sender_context[:8], "little"),
        0,  # Options
    )

    return header + data


# EtherNet/IP encapsulation status codes
ENIP_STATUS_SUCCESS = 0x0000
ENIP_STATUS_INVALID_CMD = 0x0001
ENIP_STATUS_INSUFFICIENT_MEM = 0x0002
ENIP_STATUS_INCORRECT_DATA = 0x0003
ENIP_STATUS_INVALID_SESSION = 0x0064
ENIP_STATUS_INVALID_LENGTH = 0x0065
ENIP_STATUS_UNSUPPORTED_VERSION = 0x0069


def build_enip_packet(
    src: DeviceContext,
    dst: DeviceContext,
    payload: bytes,
    seq: int = 1000,
    ack: int = 1000,
    flags: str = "PA",
    tcp_options: "TcpOptions | None" = None,
) -> bytes:
    """Build complete EtherNet/IP packet with Ethernet/IP/TCP headers.

    Args:
        src: Source device context
        dst: Destination device context
        payload: EtherNet/IP payload
        seq: TCP sequence number
        ack: TCP acknowledgment number
        flags: TCP flags
        tcp_options: Optional TCP options from fingerprint

    Returns:
        Complete packet bytes
    """
    ttl, window, options, df = extract_tcp_options(tcp_options, flags)

    ip_layer = IP(src=src.ip_address, dst=dst.ip_address, ttl=ttl)
    if df:
        ip_layer.flags = "DF"

    tcp_layer = TCP(
        sport=src.port,
        dport=dst.port,
        seq=seq,
        ack=ack,
        flags=flags,
        window=window,
    )
    if options:
        tcp_layer.options = options

    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / ip_layer
        / tcp_layer
        / Raw(load=payload)
    )

    return bytes(packet)


def build_enip_packet_fingerprinted(
    src: DeviceContext,
    dst: DeviceContext,
    payload: bytes,
    seq: int = 1000,
    ack: int = 1000,
    flags: str = "PA",
) -> bytes:
    """Build EtherNet/IP TCP packet using device fingerprint for TCP options.

    This is a convenience function that extracts TCP options from the
    source device's fingerprint applicator.

    Args:
        src: Source device context (provides fingerprint)
        dst: Destination device context
        payload: EtherNet/IP payload bytes
        seq: TCP sequence number
        ack: TCP acknowledgment number
        flags: TCP flags

    Returns:
        Complete packet bytes with fingerprinted TCP stack
    """
    tcp_options = src.fingerprint_applicator.get_tcp_options()
    return build_enip_packet(src, dst, payload, seq, ack, flags, tcp_options)


def build_enip_udp_packet(
    src: DeviceContext,
    dst: DeviceContext,
    payload: bytes,
    ttl: int = 64,
) -> bytes:
    """Build EtherNet/IP UDP packet for discovery/implicit messaging.

    Args:
        src: Source device context
        dst: Destination device context
        payload: EtherNet/IP payload
        ttl: IP TTL value

    Returns:
        Complete UDP packet bytes
    """
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address, ttl=ttl)
        / UDP(sport=src.port, dport=dst.port)
        / Raw(load=payload)
    )

    return bytes(packet)


def build_list_identity_request_packet(
    src: DeviceContext,
    dst: DeviceContext,
) -> bytes:
    """Build complete ListIdentity request packet (UDP).

    ListIdentity is typically sent as UDP broadcast/multicast on port 44818.

    Args:
        src: Source device context
        dst: Destination device context (often broadcast)

    Returns:
        Complete UDP packet bytes
    """
    payload = build_list_identity_request()
    return build_enip_udp_packet(src, dst, payload)


def build_list_identity_response_packet(
    src: DeviceContext,
    dst: DeviceContext,
    sender_context: bytes = b"\x00" * 8,
) -> bytes:
    """Build complete ListIdentity response packet (UDP) using fingerprint.

    Args:
        src: Source device context (provides fingerprint for identity)
        dst: Destination device context
        sender_context: Sender context from request

    Returns:
        Complete UDP packet bytes with fingerprinted identity
    """
    tcp_options = src.fingerprint_applicator.get_tcp_options()
    payload = build_list_identity_response(
        src.fingerprint_applicator,
        socket_addr=(src.ip_address, src.port),
        sender_context=sender_context,
    )
    return build_enip_udp_packet(src, dst, payload, ttl=tcp_options.ttl)


# =============================================================================
# CIP Service Constants for Deep Fingerprinting
# =============================================================================

# CIP Service Codes
CIP_SERVICE_GET_ATTRIBUTE_ALL = 0x01
CIP_SERVICE_GET_ATTRIBUTE_SINGLE = 0x0E
CIP_SERVICE_SET_ATTRIBUTE_SINGLE = 0x10
CIP_SERVICE_FORWARD_OPEN = 0x54
CIP_SERVICE_FORWARD_CLOSE = 0x4E

# CIP Service Response Codes (reply service = service | 0x80)
CIP_SERVICE_RESPONSE_MASK = 0x80

# CIP Status Codes
CIP_STATUS_SUCCESS = 0x00
CIP_STATUS_PATH_SEGMENT_ERROR = 0x04
CIP_STATUS_PATH_DESTINATION_UNKNOWN = 0x05
CIP_STATUS_SERVICE_NOT_SUPPORTED = 0x08
CIP_STATUS_ATTRIBUTE_NOT_SUPPORTED = 0x14
CIP_STATUS_OBJECT_DOES_NOT_EXIST = 0x16

# CIP Object Classes
CIP_CLASS_IDENTITY = 0x01
CIP_CLASS_MESSAGE_ROUTER = 0x02
CIP_CLASS_ASSEMBLY = 0x04
CIP_CLASS_CONNECTION_MANAGER = 0x06
CIP_CLASS_PARAMETER = 0x0F
CIP_CLASS_TCP_IP_INTERFACE = 0xF5
CIP_CLASS_ETHERNET_LINK = 0xF6


def build_list_services_response(
    fingerprint_applicator: "FingerprintApplicator",
    sender_context: bytes = b"\x00" * 8,
) -> bytes:
    """Build EtherNet/IP ListServices response using fingerprint data.

    ListServices advertises what communication services the device supports.
    Cisco Cyber Vision queries this to determine device capabilities.

    Args:
        fingerprint_applicator: Applicator with vendor fingerprint data
        sender_context: 8-byte sender context from request

    Returns:
        Complete ListServices response payload
    """
    # Get services from fingerprint
    services = fingerprint_applicator.get_list_services()

    if not services:
        # Default communications service if none defined
        services = [{
            "type_code": 0x0100,
            "name": "Communications",
            "capability_flags": 0x0120,  # TCP + UDP
        }]

    # Build service items
    service_items = b""
    for service in services:
        # Service name (max 16 chars, null-padded)
        name = service.get("name", "Communications")[:16]
        name_bytes = name.encode("utf-8").ljust(16, b"\x00")

        # Build service item
        service_item = struct.pack(
            "<HH",
            service.get("type_code", 0x0100),
            service.get("capability_flags", 0x0120),
        )
        service_item += name_bytes

        service_items += struct.pack("<HH", CPF_TYPE_LIST_SERVICES, len(service_item))
        service_items += service_item

    # Build CPF header (item count)
    cpf_data = struct.pack("<H", len(services)) + service_items

    # Build encapsulation header
    header = build_encapsulation_header(
        command=ENIP_CMD_LIST_SERVICES,
        length=len(cpf_data),
        session_handle=0,
        sender_context=sender_context,
    )

    return header + cpf_data


def build_cip_error_response(
    service: int,
    status: int = CIP_STATUS_SERVICE_NOT_SUPPORTED,
    additional_status: bytes = b"",
) -> bytes:
    """Build CIP error response.

    Args:
        service: Original service code (will be ORed with 0x80)
        status: CIP error status code
        additional_status: Additional status bytes

    Returns:
        CIP error response bytes
    """
    additional_status_size = len(additional_status) // 2  # Size in words
    return struct.pack(
        "<BBB",
        service | CIP_SERVICE_RESPONSE_MASK,  # Reply service
        0x00,  # Reserved
        status,
    ) + struct.pack("<B", additional_status_size) + additional_status


def build_cip_get_attribute_all_response(
    fingerprint_applicator: "FingerprintApplicator",
    class_id: int,
    instance_id: int,
) -> bytes:
    """Build CIP GetAttributeAll response for Identity Object.

    This is the primary response Cisco Cyber Vision uses for deep fingerprinting.
    It returns all attributes of the Identity Object in a single response.

    Args:
        fingerprint_applicator: Applicator with vendor fingerprint data
        class_id: CIP class ID (0x01 for Identity)
        instance_id: Instance ID (typically 1)

    Returns:
        Complete CIP GetAttributeAll response bytes
    """
    if class_id != CIP_CLASS_IDENTITY or instance_id != 1:
        return build_cip_error_response(
            CIP_SERVICE_GET_ATTRIBUTE_ALL,
            CIP_STATUS_OBJECT_DOES_NOT_EXIST,
        )

    # Get identity data from fingerprint
    identity = fingerprint_applicator.get_cip_identity_object()

    # Build Identity Object attributes in CIP order
    # Attr 1: Vendor ID (UINT)
    # Attr 2: Device Type (UINT)
    # Attr 3: Product Code (UINT)
    # Attr 4: Revision (STRUCT: Major USINT + Minor USINT)
    # Attr 5: Status (WORD)
    # Attr 6: Serial Number (UDINT)
    # Attr 7: Product Name (SHORT_STRING)
    # Attr 8: State (USINT)
    # Extended attributes may follow

    vendor_id = identity.get("vendor_id", 1)
    device_type = identity.get("device_type", 14)
    product_code = identity.get("product_code", 1)
    revision = identity.get("revision", {"major": 1, "minor": 0})
    status = identity.get("status", 0x0030)
    serial_number = identity.get("serial_number", 0x12345678)
    product_name = identity.get("product_name", "Unknown Device")[:32]
    state = identity.get("state", 3)

    # Build attribute data
    attr_data = struct.pack(
        "<HHH",
        vendor_id,
        device_type,
        product_code,
    )

    # Revision (Major + Minor as separate bytes)
    if isinstance(revision, dict):
        attr_data += struct.pack("<BB", revision.get("major", 1), revision.get("minor", 0))
    else:
        attr_data += struct.pack("<BB", 1, 0)

    # Status
    attr_data += struct.pack("<H", status)

    # Serial Number
    attr_data += struct.pack("<I", serial_number)

    # Product Name (SHORT_STRING: length byte + string)
    name_bytes = product_name.encode("utf-8")
    attr_data += struct.pack("<B", len(name_bytes)) + name_bytes

    # State
    attr_data += struct.pack("<B", state)

    # Build response header
    response = struct.pack(
        "<BBB",
        CIP_SERVICE_GET_ATTRIBUTE_ALL | CIP_SERVICE_RESPONSE_MASK,  # Reply service
        0x00,  # Reserved
        CIP_STATUS_SUCCESS,
    ) + struct.pack("<B", 0)  # Additional status size (0)

    return response + attr_data


def build_cip_get_attribute_single_response(
    fingerprint_applicator: "FingerprintApplicator",
    class_id: int,
    instance_id: int,
    attribute_id: int,
) -> bytes:
    """Build CIP GetAttributeSingle response using fingerprint data.

    This allows Cyber Vision to query individual attributes of the Identity Object.
    Extended attributes (9-20) are used for deeper fingerprinting.

    Args:
        fingerprint_applicator: Applicator with vendor fingerprint data
        class_id: CIP class ID (0x01 for Identity)
        instance_id: Instance ID (typically 1)
        attribute_id: Attribute number to return (1-20)

    Returns:
        Complete CIP GetAttributeSingle response bytes
    """
    if class_id != CIP_CLASS_IDENTITY or instance_id != 1:
        return build_cip_error_response(
            CIP_SERVICE_GET_ATTRIBUTE_SINGLE,
            CIP_STATUS_OBJECT_DOES_NOT_EXIST,
        )

    # Get identity data from fingerprint
    identity = fingerprint_applicator.get_cip_identity_object()

    # Build response header
    response_header = struct.pack(
        "<BBB",
        CIP_SERVICE_GET_ATTRIBUTE_SINGLE | CIP_SERVICE_RESPONSE_MASK,
        0x00,  # Reserved
        CIP_STATUS_SUCCESS,
    ) + struct.pack("<B", 0)  # Additional status size

    # Map attribute IDs to values
    attr_data = _build_identity_attribute_value(identity, attribute_id)

    if attr_data is None:
        return build_cip_error_response(
            CIP_SERVICE_GET_ATTRIBUTE_SINGLE,
            CIP_STATUS_ATTRIBUTE_NOT_SUPPORTED,
        )

    return response_header + attr_data


def _build_identity_attribute_value(identity: dict[str, Any], attribute_id: int) -> bytes | None:
    """Build the value bytes for a specific Identity Object attribute.

    Args:
        identity: CIP Identity Object dictionary
        attribute_id: Attribute number (1-20)

    Returns:
        Attribute value bytes, or None if attribute not supported
    """
    if attribute_id == 1:
        # Vendor ID (UINT)
        return struct.pack("<H", identity.get("vendor_id", 1))

    elif attribute_id == 2:
        # Device Type (UINT)
        return struct.pack("<H", identity.get("device_type", 14))

    elif attribute_id == 3:
        # Product Code (UINT)
        return struct.pack("<H", identity.get("product_code", 1))

    elif attribute_id == 4:
        # Revision (STRUCT: Major USINT + Minor USINT)
        revision = identity.get("revision", {"major": 1, "minor": 0})
        if isinstance(revision, dict):
            return struct.pack("<BB", revision.get("major", 1), revision.get("minor", 0))
        return struct.pack("<BB", 1, 0)

    elif attribute_id == 5:
        # Status (WORD)
        return struct.pack("<H", identity.get("status", 0x0030))

    elif attribute_id == 6:
        # Serial Number (UDINT)
        return struct.pack("<I", identity.get("serial_number", 0x12345678))

    elif attribute_id == 7:
        # Product Name (SHORT_STRING)
        name = identity.get("product_name", "Unknown")[:32]
        name_bytes = name.encode("utf-8")
        return struct.pack("<B", len(name_bytes)) + name_bytes

    elif attribute_id == 8:
        # State (USINT)
        return struct.pack("<B", identity.get("state", 3))

    elif attribute_id == 9:
        # Configuration Consistency Value (UDINT) - Extended attribute
        return struct.pack("<I", identity.get("configuration_consistency_value", 0))

    elif attribute_id == 10:
        # Heartbeat Interval (USINT) - Extended attribute
        return struct.pack("<B", min(identity.get("heartbeat_interval", 250), 255))

    elif attribute_id == 11:
        # Active Language (STRUCT with 3 language strings)
        lang = identity.get("active_language", "English")
        if isinstance(lang, dict):
            lang = lang.get("lang1", "English")
        # Return as SHORT_STRING
        lang_bytes = lang[:32].encode("utf-8")
        return struct.pack("<B", len(lang_bytes)) + lang_bytes

    elif attribute_id == 12:
        # Supported Language List (ARRAY of SHORT_STRING)
        languages = identity.get("supported_languages", ["English"])
        result = struct.pack("<H", len(languages))  # Array length
        for lang in languages[:16]:  # Max 16 languages
            lang_bytes = lang[:32].encode("utf-8")
            result += struct.pack("<B", len(lang_bytes)) + lang_bytes
        return result

    elif attribute_id == 19:
        # Protection Mode (USINT) - Rockwell-specific
        return struct.pack("<B", identity.get("protection_mode", 0))

    elif attribute_id == 20:
        # Maximum CIP Connections (UINT) - Extended attribute
        return struct.pack("<H", identity.get("maximum_cip_connections", 32))

    else:
        # Attribute not supported
        return None


def build_cip_unconnected_send_request(
    service: int,
    class_id: int,
    instance_id: int,
    attribute_id: int | None = None,
    session_handle: int = 0,
    sender_context: bytes = b"\x00" * 8,
) -> bytes:
    """Build CIP Unconnected Send request for attribute queries.

    This wraps CIP services in an UCMM (Unconnected Message Manager) request.
    Used for GetAttributeAll/GetAttributeSingle queries.

    Args:
        service: CIP service code (e.g., 0x01 for GetAttributeAll)
        class_id: CIP class ID (e.g., 0x01 for Identity)
        instance_id: Instance ID (typically 1)
        attribute_id: Attribute ID for GetAttributeSingle (None for GetAttributeAll)
        session_handle: Session handle from RegisterSession
        sender_context: 8-byte sender context

    Returns:
        Complete Unconnected Send request bytes
    """
    # Build CIP path: Class/Instance[/Attribute]
    # Path format: segment_type(1 byte) + value(variable)
    # Class segment: 0x20 + class_id (1 byte for small class)
    # Instance segment: 0x24 + instance_id (1 byte for small instance)
    # Attribute segment: 0x30 + attribute_id (1 byte for small attribute)

    if class_id <= 0xFF:
        path = struct.pack("<BB", 0x20, class_id)  # 8-bit class
    else:
        path = struct.pack("<BxH", 0x21, class_id)  # 16-bit class

    if instance_id <= 0xFF:
        path += struct.pack("<BB", 0x24, instance_id)  # 8-bit instance
    else:
        path += struct.pack("<BxH", 0x25, instance_id)  # 16-bit instance

    if attribute_id is not None:
        if attribute_id <= 0xFF:
            path += struct.pack("<BB", 0x30, attribute_id)  # 8-bit attribute
        else:
            path += struct.pack("<BxH", 0x31, attribute_id)  # 16-bit attribute

    # Build CIP Message Router Request
    path_size = len(path) // 2  # Path size in words
    cip_request = struct.pack("<BB", service, path_size) + path

    # Build Unconnected Send message (UCMM)
    # Route path to Message Router (backplane, slot 0)
    route_path = struct.pack("<BB", 0x01, 0x00)  # Port 1, slot 0
    route_path_size = len(route_path) // 2

    ucmm_data = struct.pack(
        "<BBHBB",
        0x52,  # Unconnected Send service
        0x02,  # Path size for Connection Manager
        0x0006,  # Connection Manager class
        0x01,  # Instance
        route_path_size,
    ) + route_path + struct.pack("<H", len(cip_request)) + cip_request

    # Build CPF (Common Packet Format)
    # Item 0: Null Address Item
    # Item 1: Unconnected Data Item
    cpf_data = struct.pack("<HHH", 2, CPF_TYPE_NULL, 0)  # 2 items, null address
    cpf_data += struct.pack("<HH", CPF_TYPE_UNCONNECTED_DATA, len(ucmm_data))
    cpf_data += ucmm_data

    # Build SendRRData header
    header = build_encapsulation_header(
        command=ENIP_CMD_SEND_RR_DATA,
        length=len(cpf_data) + 6,  # +6 for interface handle and timeout
        session_handle=session_handle,
        sender_context=sender_context,
    )

    # Interface handle (0) and timeout (0)
    return header + struct.pack("<IH", 0, 0) + cpf_data


def build_cip_unconnected_send_response(
    cip_response: bytes,
    session_handle: int = 0,
    sender_context: bytes = b"\x00" * 8,
) -> bytes:
    """Build CIP Unconnected Send response wrapper.

    Wraps CIP service responses in UCMM response format.

    Args:
        cip_response: The CIP service response bytes
        session_handle: Session handle from RegisterSession
        sender_context: 8-byte sender context

    Returns:
        Complete Unconnected Send response bytes
    """
    # Build CPF (Common Packet Format)
    # Item 0: Null Address Item
    # Item 1: Unconnected Data Item with CIP response
    cpf_data = struct.pack("<HHH", 2, CPF_TYPE_NULL, 0)  # 2 items, null address
    cpf_data += struct.pack("<HH", CPF_TYPE_UNCONNECTED_DATA, len(cip_response))
    cpf_data += cip_response

    # Build SendRRData header
    header = build_encapsulation_header(
        command=ENIP_CMD_SEND_RR_DATA,
        length=len(cpf_data) + 6,  # +6 for interface handle and timeout
        session_handle=session_handle,
        sender_context=sender_context,
    )

    # Interface handle (0) and timeout (0)
    return header + struct.pack("<IH", 0, 0) + cpf_data
