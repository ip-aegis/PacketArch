"""OPC UA packet building utilities.

OPC UA Binary Protocol runs over TCP port 4840.
Message structure:
- Message Header (8 bytes): Type(3) + Reserved(1) + Size(4)
- Secure Channel Header (variable)
- Sequence Header (8 bytes): SequenceNumber(4) + RequestId(4)
- Body (variable)
"""

import struct
from typing import Any

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether

from app.protocol_engines.types import DeviceContext

# OPC UA message types
MSG_TYPE_HELLO = b"HEL"
MSG_TYPE_ACKNOWLEDGE = b"ACK"
MSG_TYPE_ERROR = b"ERR"
MSG_TYPE_OPEN_SECURE_CHANNEL = b"OPN"
MSG_TYPE_CLOSE_SECURE_CHANNEL = b"CLO"
MSG_TYPE_MESSAGE = b"MSG"

# OPC UA service identifiers
SERVICE_CREATE_SESSION = 461
SERVICE_ACTIVATE_SESSION = 467
SERVICE_CLOSE_SESSION = 473
SERVICE_READ = 631
SERVICE_WRITE = 673
SERVICE_BROWSE = 527
SERVICE_CREATE_SUBSCRIPTION = 787
SERVICE_PUBLISH = 826

# Security policies
SECURITY_POLICY_NONE = "http://opcfoundation.org/UA/SecurityPolicy#None"

# Default port
OPC_UA_PORT = 4840


def build_tcp_header(src: DeviceContext, dst: DeviceContext) -> bytes:
    """Build Ethernet + IP + TCP header for OPC UA."""
    # Ethernet header (14 bytes)
    dst_mac = bytes.fromhex(dst.mac_address.replace(":", "").replace("-", ""))
    src_mac = bytes.fromhex(src.mac_address.replace(":", "").replace("-", ""))
    eth_type = b"\x08\x00"  # IPv4
    eth_header = dst_mac + src_mac + eth_type

    # IP header (20 bytes)
    src_ip_parts = [int(x) for x in src.ip_address.split(".")]
    dst_ip_parts = [int(x) for x in dst.ip_address.split(".")]

    ip_header = bytes([
        0x45,  # Version (4) + IHL (5)
        0x00,  # DSCP + ECN
        0x00, 0x00,  # Total length (placeholder)
        0x00, 0x01,  # Identification
        0x40, 0x00,  # Flags + Fragment offset (DF set)
        0x40,  # TTL (64)
        0x06,  # Protocol (TCP)
        0x00, 0x00,  # Header checksum (placeholder)
        src_ip_parts[0], src_ip_parts[1], src_ip_parts[2], src_ip_parts[3],
        dst_ip_parts[0], dst_ip_parts[1], dst_ip_parts[2], dst_ip_parts[3],
    ])

    # TCP header (20 bytes, no options)
    src_port = src.port if src.port else 50000
    dst_port = dst.port if dst.port else OPC_UA_PORT

    tcp_header = struct.pack(
        ">HHIIBBHHH",
        src_port,
        dst_port,
        0,  # Sequence number (placeholder)
        0,  # Acknowledgment number (placeholder)
        0x50,  # Data offset (5 * 4 = 20 bytes)
        0x18,  # Flags: PSH + ACK
        65535,  # Window size
        0,  # Checksum (placeholder)
        0,  # Urgent pointer
    )

    return eth_header + ip_header + tcp_header


def build_opc_ua_header(msg_type: bytes, size: int, is_final: bool = True) -> bytes:
    """Build OPC UA message header.

    Args:
        msg_type: 3-byte message type (HEL, ACK, OPN, MSG, CLO, ERR)
        size: Total message size including header
        is_final: Whether this is the final chunk

    Returns:
        8-byte message header
    """
    chunk_type = b"F" if is_final else b"C"
    return msg_type + chunk_type + struct.pack("<I", size)


def build_hello_message(
    endpoint_url: str = "opc.tcp://localhost:4840",
    max_message_size: int = 65536,
    max_chunk_count: int = 0,
) -> bytes:
    """Build OPC UA Hello message.

    Args:
        endpoint_url: Server endpoint URL
        max_message_size: Maximum message size
        max_chunk_count: Maximum chunk count (0 = unlimited)

    Returns:
        Complete Hello message bytes
    """
    # Hello body
    endpoint_bytes = endpoint_url.encode("utf-8")
    body = struct.pack(
        "<IIII",
        0,  # Protocol version
        65536,  # Receive buffer size
        65536,  # Send buffer size
        max_message_size,
    ) + struct.pack("<I", max_chunk_count) + struct.pack("<I", len(endpoint_bytes)) + endpoint_bytes

    # Total size = header(8) + body
    total_size = 8 + len(body)
    header = build_opc_ua_header(MSG_TYPE_HELLO, total_size)

    return header + body


def build_acknowledge_message(
    max_message_size: int = 65536,
    max_chunk_count: int = 0,
) -> bytes:
    """Build OPC UA Acknowledge message.

    Args:
        max_message_size: Maximum message size
        max_chunk_count: Maximum chunk count

    Returns:
        Complete Acknowledge message bytes
    """
    body = struct.pack(
        "<IIIII",
        0,  # Protocol version
        65536,  # Receive buffer size
        65536,  # Send buffer size
        max_message_size,
        max_chunk_count,
    )

    total_size = 8 + len(body)
    header = build_opc_ua_header(MSG_TYPE_ACKNOWLEDGE, total_size)

    return header + body


def build_open_secure_channel_request(
    security_policy: str = SECURITY_POLICY_NONE,
    request_id: int = 1,
) -> bytes:
    """Build OpenSecureChannel request.

    Args:
        security_policy: Security policy URI
        request_id: Request identifier

    Returns:
        Complete OpenSecureChannel request bytes
    """
    # Security policy URI
    policy_bytes = security_policy.encode("utf-8")

    # SecureChannelId — per OPC UA Part 6 §7.1.2.2 the OPN body starts with a
    # 4-byte SecureChannelId immediately after the 8-byte MessageHeader, BEFORE
    # the asymmetric security header. For an open-channel REQUEST the channel
    # does not exist yet, so the client sends 0; the server assigns a real ID
    # in the response. Omitting this field made Wireshark dissect the next
    # 4 bytes (SecurityPolicyUri length) as the channel id, then read garbage
    # for the URI length, and flag the packet as malformed.
    secure_channel_id = struct.pack("<I", 0)

    # Asymmetric security header
    security_header = (
        struct.pack("<I", len(policy_bytes)) + policy_bytes +
        struct.pack("<I", 0xFFFFFFFF) +  # Sender certificate (null)
        struct.pack("<I", 0xFFFFFFFF)    # Receiver certificate thumbprint (null)
    )

    # Sequence header
    sequence_header = struct.pack("<II", 1, request_id)

    # Request body (simplified)
    # RequestHeader + SecurityTokenRequestType + MessageSecurityMode + RequestedLifetime
    request_body = bytes([
        # Null NodeId for authentication token
        0x00, 0x00,
        # Timestamp (8 bytes)
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        # RequestHandle
        0x01, 0x00, 0x00, 0x00,
        # ReturnDiagnostics
        0x00, 0x00, 0x00, 0x00,
        # AuditEntryId (null string)
        0xFF, 0xFF, 0xFF, 0xFF,
        # TimeoutHint
        0x00, 0x00, 0x00, 0x00,
        # AdditionalHeader (null)
        0x00, 0x00, 0x00,
        # ClientProtocolVersion
        0x00, 0x00, 0x00, 0x00,
        # SecurityTokenRequestType (Issue = 0)
        0x00, 0x00, 0x00, 0x00,
        # MessageSecurityMode (None = 1)
        0x01, 0x00, 0x00, 0x00,
        # ClientNonce (null)
        0xFF, 0xFF, 0xFF, 0xFF,
        # RequestedLifetime (3600000 ms = 1 hour)
        0x40, 0x77, 0x1B, 0x00,
    ])

    body = secure_channel_id + security_header + sequence_header + request_body

    # OpenSecureChannel message type
    total_size = 8 + len(body)
    header = build_opc_ua_header(MSG_TYPE_OPEN_SECURE_CHANNEL, total_size)

    return header + body


def build_open_secure_channel_response(
    security_token_id: int = 1,
    channel_id: int = 1,
    request_id: int = 1,
) -> bytes:
    """Build OpenSecureChannel response.

    Args:
        security_token_id: Security token ID
        channel_id: Secure channel ID
        request_id: Request ID being responded to

    Returns:
        Complete OpenSecureChannel response bytes
    """
    # Security policy (None)
    policy_bytes = SECURITY_POLICY_NONE.encode("utf-8")

    # SecureChannelId — for an OpenSecureChannel RESPONSE the server returns
    # the channel id it assigned to the new channel. Same wire-format slot
    # as in the request: immediately after the 8-byte message header.
    secure_channel_id = struct.pack("<I", channel_id)

    # Asymmetric security header
    security_header = (
        struct.pack("<I", len(policy_bytes)) + policy_bytes +
        struct.pack("<I", 0xFFFFFFFF) +  # Sender certificate (null)
        struct.pack("<I", 0xFFFFFFFF)    # Receiver certificate thumbprint (null)
    )

    # Sequence header
    sequence_header = struct.pack("<II", 1, request_id)

    # Response body (simplified)
    response_body = bytes([
        # ResponseHeader - ServiceResult (Good = 0)
        0x00, 0x00, 0x00, 0x00,
    ]) + struct.pack("<I", channel_id) + struct.pack("<I", security_token_id) + bytes([
        # Revised lifetime
        0x40, 0x77, 0x1B, 0x00,
        # Server nonce (null)
        0xFF, 0xFF, 0xFF, 0xFF,
    ])

    body = secure_channel_id + security_header + sequence_header + response_body

    total_size = 8 + len(body)
    header = build_opc_ua_header(MSG_TYPE_OPEN_SECURE_CHANNEL, total_size)

    return header + body


def build_create_session_request(
    session_name: str = "PacketArch-Session",
    request_id: int = 2,
    channel_id: int = 1,
) -> bytes:
    """Build CreateSession request.

    Args:
        session_name: Session name
        request_id: Request identifier
        channel_id: Secure channel ID

    Returns:
        Complete CreateSession request bytes
    """
    session_name_bytes = session_name.encode("utf-8")

    # Symmetric security header (after OpenSecureChannel)
    security_header = struct.pack("<II", channel_id, 1)  # ChannelId + TokenId

    # Sequence header
    sequence_header = struct.pack("<II", 2, request_id)

    # CreateSession request type ID
    type_id = struct.pack("<HH", 461, 0)  # NodeId for CreateSessionRequest

    # Request body (simplified)
    request_body = bytes([
        # RequestHeader (simplified)
        0x00, 0x00,  # Null authentication token
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Timestamp
        0x02, 0x00, 0x00, 0x00,  # RequestHandle
        0x00, 0x00, 0x00, 0x00,  # ReturnDiagnostics
        0xFF, 0xFF, 0xFF, 0xFF,  # AuditEntryId (null)
        0x00, 0x00, 0x00, 0x00,  # TimeoutHint
        0x00, 0x00, 0x00,  # AdditionalHeader (null)
    ]) + struct.pack("<I", len(session_name_bytes)) + session_name_bytes + bytes([
        # ClientNonce (null)
        0xFF, 0xFF, 0xFF, 0xFF,
        # ClientCertificate (null)
        0xFF, 0xFF, 0xFF, 0xFF,
        # RequestedSessionTimeout (1200000 ms = 20 min)
        0x00, 0x00, 0x80, 0x51, 0x01, 0x00, 0x00, 0x00,
        # MaxResponseMessageSize
        0x00, 0x00, 0x01, 0x00,
    ])

    body = security_header + sequence_header + type_id + request_body

    total_size = 8 + len(body)
    header = build_opc_ua_header(MSG_TYPE_MESSAGE, total_size)

    return header + body


def build_create_session_response(
    session_id: bytes,
    request_id: int = 2,
    channel_id: int = 1,
) -> bytes:
    """Build CreateSession response.

    Args:
        session_id: Session ID (16 bytes GUID)
        request_id: Request ID being responded to
        channel_id: Secure channel ID

    Returns:
        Complete CreateSession response bytes
    """
    # Symmetric security header
    security_header = struct.pack("<II", channel_id, 1)

    # Sequence header
    sequence_header = struct.pack("<II", 2, request_id)

    # CreateSession response type ID
    type_id = struct.pack("<HH", 464, 0)  # NodeId for CreateSessionResponse

    # Response body (simplified)
    response_body = bytes([
        # ResponseHeader - ServiceResult (Good = 0)
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Timestamp
        0x02, 0x00, 0x00, 0x00,  # RequestHandle
        0x00, 0x00, 0x00, 0x00,  # ServiceDiagnostics (null)
        0xFF, 0xFF, 0xFF, 0xFF,  # StringTable (null array)
        0x00, 0x00, 0x00,  # AdditionalHeader (null)
    ]) + bytes([0x04]) + session_id + bytes([  # SessionId (GUID)
        # AuthenticationToken
        0x04,
    ]) + session_id + bytes([
        # RevisedSessionTimeout
        0x00, 0x00, 0x80, 0x51, 0x01, 0x00, 0x00, 0x00,
        # ServerNonce (null)
        0xFF, 0xFF, 0xFF, 0xFF,
        # ServerCertificate (null)
        0xFF, 0xFF, 0xFF, 0xFF,
    ])

    body = security_header + sequence_header + type_id + response_body

    total_size = 8 + len(body)
    header = build_opc_ua_header(MSG_TYPE_MESSAGE, total_size)

    return header + body


def build_read_request(
    node_ids: list[str],
    request_id: int = 3,
    channel_id: int = 1,
    token_id: int = 1,
) -> bytes:
    """Build Read service request.

    Args:
        node_ids: List of node IDs to read (e.g., ["ns=2;i=1", "ns=2;s=Temperature"])
        request_id: Request identifier
        channel_id: Secure channel ID
        token_id: Security token ID

    Returns:
        Complete Read request bytes
    """
    # Symmetric security header
    security_header = struct.pack("<II", channel_id, token_id)

    # Sequence header
    sequence_header = struct.pack("<II", request_id, request_id)

    # Read request type ID
    type_id = struct.pack("<HH", SERVICE_READ, 0)

    # Request body (simplified - reads value attribute)
    node_count = len(node_ids)

    # Request header
    request_header = bytes([
        0x00, 0x00,  # AuthenticationToken (null for simplicity)
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Timestamp
    ]) + struct.pack("<I", request_id) + bytes([
        0x00, 0x00, 0x00, 0x00,  # ReturnDiagnostics
        0xFF, 0xFF, 0xFF, 0xFF,  # AuditEntryId
        0x00, 0x00, 0x00, 0x00,  # TimeoutHint
        0x00, 0x00, 0x00,  # AdditionalHeader
    ])

    # MaxAge (0 = from cache if available)
    max_age = struct.pack("<d", 0.0)

    # TimestampsToReturn (Both = 2)
    timestamps = struct.pack("<I", 2)

    # NodesToRead array
    nodes_to_read = struct.pack("<I", node_count)
    for node_id in node_ids:
        # Simple numeric node ID
        if node_id.startswith("ns="):
            parts = node_id.split(";")
            ns = int(parts[0].split("=")[1])
            if parts[1].startswith("i="):
                node_num = int(parts[1].split("=")[1])
                # Numeric NodeId encoding
                if ns == 0 and node_num < 256:
                    nodes_to_read += bytes([0x00, node_num])
                else:
                    nodes_to_read += bytes([0x01]) + struct.pack("<BH", ns, node_num)
            else:
                # String NodeId
                node_str = parts[1].split("=")[1].encode("utf-8")
                nodes_to_read += bytes([0x03]) + struct.pack("<B", ns) + struct.pack("<I", len(node_str)) + node_str
        else:
            # Default to numeric node ID 1
            nodes_to_read += bytes([0x00, 0x01])

        # AttributeId (Value = 13)
        nodes_to_read += struct.pack("<I", 13)
        # IndexRange (null)
        nodes_to_read += struct.pack("<I", 0xFFFFFFFF)
        # DataEncoding (null)
        nodes_to_read += bytes([0x00, 0x00])

    body = security_header + sequence_header + type_id + request_header + max_age + timestamps + nodes_to_read

    total_size = 8 + len(body)
    header = build_opc_ua_header(MSG_TYPE_MESSAGE, total_size)

    return header + body


def build_read_response(
    values: list[tuple[int, Any]],
    request_id: int = 3,
    channel_id: int = 1,
    token_id: int = 1,
) -> bytes:
    """Build Read service response.

    Args:
        values: List of (type_id, value) tuples
        request_id: Request ID being responded to
        channel_id: Secure channel ID
        token_id: Security token ID

    Returns:
        Complete Read response bytes
    """
    # Symmetric security header
    security_header = struct.pack("<II", channel_id, token_id)

    # Sequence header
    sequence_header = struct.pack("<II", request_id, request_id)

    # Read response type ID
    type_id = struct.pack("<HH", SERVICE_READ + 3, 0)  # 634 = ReadResponse

    # Response header
    response_header = bytes([
        0x00, 0x00, 0x00, 0x00,  # ServiceResult (Good)
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Timestamp
    ]) + struct.pack("<I", request_id) + bytes([
        0x00, 0x00, 0x00, 0x00,  # ServiceDiagnostics
        0xFF, 0xFF, 0xFF, 0xFF,  # StringTable
        0x00, 0x00, 0x00,  # AdditionalHeader
    ])

    # Results array
    results = struct.pack("<I", len(values))
    for value_type, value in values:
        # Status code (Good)
        results += struct.pack("<I", 0)
        # Source timestamp
        results += struct.pack("<Q", 0)
        # Server timestamp
        results += struct.pack("<Q", 0)

        # Value encoding
        if value_type == 1:  # Boolean
            results += bytes([0x01, 0x01 if value else 0x00])
        elif value_type == 6:  # Int32
            results += bytes([0x06]) + struct.pack("<i", value)
        elif value_type == 10:  # Float
            results += bytes([0x0A]) + struct.pack("<f", value)
        elif value_type == 11:  # Double
            results += bytes([0x0B]) + struct.pack("<d", value)
        elif value_type == 12:  # String
            str_bytes = str(value).encode("utf-8")
            results += bytes([0x0C]) + struct.pack("<I", len(str_bytes)) + str_bytes
        else:
            # Default to Int32
            results += bytes([0x06]) + struct.pack("<i", int(value))

    # DiagnosticInfos (null array)
    diagnostic_infos = struct.pack("<I", 0xFFFFFFFF)

    body = security_header + sequence_header + type_id + response_header + results + diagnostic_infos

    total_size = 8 + len(body)
    header = build_opc_ua_header(MSG_TYPE_MESSAGE, total_size)

    return header + body


def build_opc_ua_packet(
    src: DeviceContext,
    dst: DeviceContext,
    opc_ua_message: bytes,
    seq: int = 0,
    ack: int = 0,
) -> bytes:
    """Build complete OPC UA packet with TCP/IP headers.

    Args:
        src: Source device context
        dst: Destination device context
        opc_ua_message: OPC UA message bytes
        seq: TCP sequence number
        ack: TCP acknowledgment number

    Returns:
        Complete packet bytes with valid IP and TCP checksums.
    """
    # Build TCP/IP header
    header = build_tcp_header(src, dst)

    # Update TCP sequence/ack in header
    tcp_offset = 34  # Ethernet(14) + IP(20)
    header_list = list(header)

    # Sequence number (bytes 4-7 of TCP header)
    seq_bytes = struct.pack(">I", seq)
    header_list[tcp_offset + 4:tcp_offset + 8] = seq_bytes

    # Ack number (bytes 8-11 of TCP header)
    ack_bytes = struct.pack(">I", ack)
    header_list[tcp_offset + 8:tcp_offset + 12] = ack_bytes

    # Update IP total length
    total_length = 20 + 20 + len(opc_ua_message)  # IP + TCP + payload
    header_list[16:18] = struct.pack(">H", total_length)

    raw_packet = bytes(header_list) + opc_ua_message

    # CRITICAL: build_tcp_header() leaves both the IP header checksum AND
    # the TCP checksum at zero. CV's DPI engine (and most stack-aware
    # parsers) treat IP.chksum==0 as an invalid header per RFC 791 and
    # silently drop the packet before any L7 dissection happens, so
    # fingerprinting never starts.
    #
    # Round-trip the assembled bytes through scapy: clearing chksum on the
    # IP and TCP layers and re-serializing forces scapy to compute both
    # checksums correctly using the pseudo-header.
    parsed = Ether(raw_packet)
    if parsed.haslayer(IP):
        del parsed[IP].chksum
        if parsed.haslayer(TCP):
            del parsed[TCP].chksum
    return bytes(parsed)
