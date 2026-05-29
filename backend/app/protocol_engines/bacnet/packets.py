# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""BACnet/IP packet building utilities.

Builds complete BACnet/IP packets including:
- BVLC (BACnet Virtual Link Control) header
- NPDU (Network Protocol Data Unit) header
- APDU (Application Protocol Data Unit) with services

Uses Scapy for Ethernet/IP/UDP layers and manual BACnet encoding.
"""

import struct
from typing import Any

from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

from app.protocol_engines.bacnet.types import (
    BACNET_PORT,
    BACNET_BVLC_TYPE,
    BACnetApplicationTag,
    BACnetConfirmedService,
    BACnetObjectType,
    BACnetPDUType,
    BACnetPropertyIdentifier,
    BACnetSegmentation,
    BACnetUnconfirmedService,
    BVLCFunction,
)
from app.protocol_engines.types import DeviceContext


# ============================================================================
# ASN.1/BER Encoding Utilities
# ============================================================================

def encode_length(length: int) -> bytes:
    """Encode ASN.1 BER length field.

    Args:
        length: Length to encode

    Returns:
        Encoded length bytes
    """
    if length < 128:
        return bytes([length])
    elif length < 256:
        return bytes([0x81, length])
    elif length < 65536:
        return bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])
    elif length < 16777216:
        return bytes([0x83, (length >> 16) & 0xFF, (length >> 8) & 0xFF, length & 0xFF])
    else:
        return bytes([0x84, (length >> 24) & 0xFF, (length >> 16) & 0xFF,
                      (length >> 8) & 0xFF, length & 0xFF])


def encode_unsigned(value: int) -> bytes:
    """Encode an unsigned integer as BACnet application-tagged data.

    Args:
        value: Unsigned integer value

    Returns:
        Encoded bytes with application tag
    """
    if value == 0:
        data = bytes([0])
    elif value < 0x100:
        data = bytes([value])
    elif value < 0x10000:
        data = struct.pack(">H", value)
    elif value < 0x1000000:
        data = struct.pack(">I", value)[1:]  # 3 bytes
    else:
        data = struct.pack(">I", value)

    # Application tag 2 (unsigned integer)
    tag = BACnetApplicationTag.UNSIGNED_INT << 4
    if len(data) < 5:
        tag |= len(data)
        return bytes([tag]) + data
    else:
        tag |= 5  # Extended length
        return bytes([tag]) + encode_length(len(data)) + data


def encode_signed(value: int) -> bytes:
    """Encode a signed integer as BACnet application-tagged data."""
    if -128 <= value <= 127:
        data = struct.pack(">b", value)
    elif -32768 <= value <= 32767:
        data = struct.pack(">h", value)
    else:
        data = struct.pack(">i", value)

    tag = BACnetApplicationTag.SIGNED_INT << 4
    if len(data) < 5:
        tag |= len(data)
        return bytes([tag]) + data
    else:
        tag |= 5
        return bytes([tag]) + encode_length(len(data)) + data


def encode_real(value: float) -> bytes:
    """Encode a floating point number as BACnet application-tagged data."""
    data = struct.pack(">f", value)
    tag = (BACnetApplicationTag.REAL << 4) | 4
    return bytes([tag]) + data


def encode_enumerated(value: int) -> bytes:
    """Encode an enumeration as BACnet application-tagged data."""
    if value < 0x100:
        data = bytes([value])
    elif value < 0x10000:
        data = struct.pack(">H", value)
    else:
        data = struct.pack(">I", value)

    tag = BACnetApplicationTag.ENUMERATED << 4
    if len(data) < 5:
        tag |= len(data)
        return bytes([tag]) + data
    else:
        tag |= 5
        return bytes([tag]) + encode_length(len(data)) + data


def encode_character_string(value: str, encoding: int = 0) -> bytes:
    """Encode a character string as BACnet application-tagged data.

    Args:
        value: String to encode
        encoding: Character encoding (0 = ANSI X3.4 / UTF-8)

    Returns:
        Encoded bytes with application tag
    """
    encoded = bytes([encoding]) + value.encode("utf-8")
    tag = BACnetApplicationTag.CHARACTER_STRING << 4
    if len(encoded) < 5:
        tag |= len(encoded)
        return bytes([tag]) + encoded
    else:
        tag |= 5
        return bytes([tag]) + encode_length(len(encoded)) + encoded


def encode_boolean(value: bool) -> bytes:
    """Encode a boolean as BACnet application-tagged data."""
    return bytes([0x10 | (1 if value else 0)])


def encode_null() -> bytes:
    """Encode a NULL value."""
    return bytes([0x00])


def encode_object_identifier(object_type: int, instance: int) -> bytes:
    """Encode a BACnet Object Identifier as application-tagged data.

    Object Identifier: 10 bits type + 22 bits instance = 32 bits total

    Args:
        object_type: Object type (0-1023)
        instance: Object instance (0-4194303)

    Returns:
        Encoded bytes with application tag
    """
    value = ((object_type & 0x3FF) << 22) | (instance & 0x3FFFFF)
    data = struct.pack(">I", value)
    tag = (BACnetApplicationTag.BACNET_OBJECT_IDENTIFIER << 4) | 4
    return bytes([tag]) + data


def encode_context_tag(tag_number: int, data: bytes) -> bytes:
    """Encode data with a context-specific tag.

    Args:
        tag_number: Context tag number (0-14, or 15 for extended)
        data: Data to wrap with context tag

    Returns:
        Context-tagged data
    """
    if tag_number < 15:
        class_bit = 0x08  # Context-specific
        constructed = 0x00  # Primitive
        tag = (tag_number << 4) | class_bit | constructed
    else:
        # Extended tag
        tag = 0x0F
        tag |= 0x08  # Context-specific

    if len(data) < 5:
        tag |= len(data)
        return bytes([tag]) + data
    elif len(data) < 254:
        tag |= 5  # Extended length marker
        return bytes([tag, len(data)]) + data
    elif len(data) < 65536:
        tag |= 5
        return bytes([tag, 254]) + struct.pack(">H", len(data)) + data
    else:
        tag |= 5
        return bytes([tag, 255]) + struct.pack(">I", len(data)) + data


def encode_opening_tag(tag_number: int) -> bytes:
    """Encode a context-specific opening tag."""
    if tag_number < 15:
        return bytes([(tag_number << 4) | 0x0E])
    else:
        return bytes([0xFE, tag_number])


def encode_closing_tag(tag_number: int) -> bytes:
    """Encode a context-specific closing tag."""
    if tag_number < 15:
        return bytes([(tag_number << 4) | 0x0F])
    else:
        return bytes([0xFF, tag_number])


# ============================================================================
# BVLC Header Building
# ============================================================================

def build_bvlc_header(function: BVLCFunction, npdu_length: int) -> bytes:
    """Build BVLC (BACnet Virtual Link Control) header.

    BVLC Header Format (4 bytes):
    - Type: 0x81 (BACnet/IP)
    - Function: BVLC function code
    - Length: Total length (BVLC header + NPDU)

    Args:
        function: BVLC function code
        npdu_length: Length of NPDU (including APDU)

    Returns:
        BVLC header bytes (4 bytes)
    """
    total_length = 4 + npdu_length  # BVLC header is 4 bytes
    return struct.pack(">BBH", BACNET_BVLC_TYPE, function, total_length)


# ============================================================================
# NPDU Header Building
# ============================================================================

def build_npdu(
    expecting_reply: bool = False,
    priority: int = 0,
    destination_net: int | None = None,
    destination_addr: bytes | None = None,
    source_net: int | None = None,
    source_addr: bytes | None = None,
    hop_count: int = 255,
) -> bytes:
    """Build NPDU (Network Protocol Data Unit) header.

    NPDU Header Format:
    - Version: 0x01 (BACnet/IP)
    - Control: Bit field for routing flags
    - Optional: DNET, DLEN, DADR, SNET, SLEN, SADR, Hop Count

    Args:
        expecting_reply: True if expecting a reply
        priority: Network priority (0-3)
        destination_net: Destination network number (optional)
        destination_addr: Destination MAC address (optional)
        source_net: Source network number (optional)
        source_addr: Source MAC address (optional)
        hop_count: Hop count for routed messages

    Returns:
        NPDU header bytes
    """
    version = 0x01
    control = 0x00

    # Bit 2: Expecting reply
    if expecting_reply:
        control |= 0x04

    # Bits 0-1: Network priority
    control |= (priority & 0x03)

    npdu = bytes([version, control])

    # Destination specifier (bit 5)
    if destination_net is not None:
        control |= 0x20
        npdu = bytes([version, control])
        npdu += struct.pack(">H", destination_net)
        if destination_addr:
            npdu += bytes([len(destination_addr)]) + destination_addr
        else:
            npdu += bytes([0])  # Broadcast (DLEN = 0)

    # Source specifier (bit 3)
    if source_net is not None:
        control |= 0x08
        # Rebuild with updated control
        npdu = bytes([version, control]) + npdu[2:]
        npdu += struct.pack(">H", source_net)
        if source_addr:
            npdu += bytes([len(source_addr)]) + source_addr
        else:
            npdu += bytes([0])

    # Hop count (only if destination specifier is set)
    if destination_net is not None:
        npdu += bytes([hop_count])

    return npdu


# ============================================================================
# APDU Building - Unconfirmed Services
# ============================================================================

def build_who_is_apdu(
    low_limit: int | None = None,
    high_limit: int | None = None,
) -> bytes:
    """Build Who-Is unconfirmed request APDU.

    Who-Is is used for device discovery. Optional limits specify
    device instance range to query.

    Args:
        low_limit: Lower device instance limit (optional)
        high_limit: Upper device instance limit (optional)

    Returns:
        Who-Is APDU bytes
    """
    # PDU type (unconfirmed request) and service choice
    apdu = bytes([
        (BACnetPDUType.UNCONFIRMED_REQUEST << 4),
        BACnetUnconfirmedService.WHO_IS
    ])

    # Add device instance range if specified
    if low_limit is not None:
        apdu += encode_context_tag(0, encode_unsigned_raw(low_limit))
    if high_limit is not None:
        apdu += encode_context_tag(1, encode_unsigned_raw(high_limit))

    return apdu


def encode_unsigned_raw(value: int) -> bytes:
    """Encode unsigned integer without application tag (for context tags)."""
    if value == 0:
        return bytes([0])
    elif value < 0x100:
        return bytes([value])
    elif value < 0x10000:
        return struct.pack(">H", value)
    elif value < 0x1000000:
        return struct.pack(">I", value)[1:]
    else:
        return struct.pack(">I", value)


def build_i_am_apdu(
    device_instance: int,
    max_apdu_length: int,
    segmentation: int,
    vendor_id: int,
) -> bytes:
    """Build I-Am unconfirmed response APDU.

    I-Am is the discovery response containing device identity.
    This is CRITICAL for Cyber Vision device detection.

    Args:
        device_instance: Device object instance number
        max_apdu_length: Maximum APDU length accepted
        segmentation: Segmentation supported enumeration
        vendor_id: BACnet registered vendor ID

    Returns:
        I-Am APDU bytes
    """
    # PDU type and service choice
    apdu = bytes([
        (BACnetPDUType.UNCONFIRMED_REQUEST << 4),
        BACnetUnconfirmedService.I_AM
    ])

    # Object Identifier (Device object)
    apdu += encode_object_identifier(BACnetObjectType.DEVICE, device_instance)

    # Max APDU Length Accepted (unsigned)
    apdu += encode_unsigned(max_apdu_length)

    # Segmentation Supported (enumerated)
    apdu += encode_enumerated(segmentation)

    # Vendor ID (unsigned)
    apdu += encode_unsigned(vendor_id)

    return apdu


def build_i_have_apdu(
    device_instance: int,
    object_type: int,
    object_instance: int,
    object_name: str,
) -> bytes:
    """Build I-Have unconfirmed response APDU.

    I-Have is sent in response to Who-Has requests.

    Args:
        device_instance: Device object instance
        object_type: Type of object that was found
        object_instance: Instance of object that was found
        object_name: Name of the object

    Returns:
        I-Have APDU bytes
    """
    apdu = bytes([
        (BACnetPDUType.UNCONFIRMED_REQUEST << 4),
        BACnetUnconfirmedService.I_HAVE
    ])

    # Device Identifier
    apdu += encode_object_identifier(BACnetObjectType.DEVICE, device_instance)

    # Object Identifier
    apdu += encode_object_identifier(object_type, object_instance)

    # Object Name
    apdu += encode_character_string(object_name)

    return apdu


# ============================================================================
# APDU Building - Confirmed Services
# ============================================================================

def build_read_property_request_apdu(
    invoke_id: int,
    object_type: int,
    object_instance: int,
    property_id: int,
    array_index: int | None = None,
) -> bytes:
    """Build ReadProperty confirmed request APDU.

    Args:
        invoke_id: Invoke ID for matching responses
        object_type: Target object type
        object_instance: Target object instance
        property_id: Property to read
        array_index: Array index (optional)

    Returns:
        ReadProperty request APDU bytes
    """
    # APDU header for confirmed request
    # PDU type (bits 4-7), segmented/more flags (bits 2-3), SA bit (bit 1)
    apdu = bytes([
        (BACnetPDUType.CONFIRMED_REQUEST << 4),
        0x05,  # Max segments = 0, max response = 1476
        invoke_id,
        BACnetConfirmedService.READ_PROPERTY
    ])

    # Object Identifier [0]
    obj_id_data = struct.pack(">I", ((object_type & 0x3FF) << 22) | (object_instance & 0x3FFFFF))
    apdu += encode_context_tag(0, obj_id_data)

    # Property Identifier [1]
    apdu += encode_context_tag(1, encode_unsigned_raw(property_id))

    # Property Array Index [2] (optional)
    if array_index is not None:
        apdu += encode_context_tag(2, encode_unsigned_raw(array_index))

    return apdu


def build_read_property_response_apdu(
    invoke_id: int,
    object_type: int,
    object_instance: int,
    property_id: int,
    property_value: Any,
    property_type: str = "unsigned",
    array_index: int | None = None,
) -> bytes:
    """Build ReadProperty complex-ack response APDU.

    Args:
        invoke_id: Invoke ID (must match request)
        object_type: Object type
        object_instance: Object instance
        property_id: Property identifier
        property_value: Property value
        property_type: Type hint for encoding
        array_index: Array index (optional)

    Returns:
        ReadProperty response APDU bytes
    """
    # APDU header for complex-ack
    apdu = bytes([
        (BACnetPDUType.COMPLEX_ACK << 4),
        invoke_id,
        BACnetConfirmedService.READ_PROPERTY
    ])

    # Object Identifier [0]
    obj_id_data = struct.pack(">I", ((object_type & 0x3FF) << 22) | (object_instance & 0x3FFFFF))
    apdu += encode_context_tag(0, obj_id_data)

    # Property Identifier [1]
    apdu += encode_context_tag(1, encode_unsigned_raw(property_id))

    # Property Array Index [2] (optional)
    if array_index is not None:
        apdu += encode_context_tag(2, encode_unsigned_raw(array_index))

    # Property Value [3] - opening tag
    apdu += encode_opening_tag(3)

    # Encode value based on type
    if property_type == "unsigned":
        apdu += encode_unsigned(property_value)
    elif property_type == "signed":
        apdu += encode_signed(property_value)
    elif property_type == "real":
        apdu += encode_real(property_value)
    elif property_type == "string":
        apdu += encode_character_string(str(property_value))
    elif property_type == "enumerated":
        apdu += encode_enumerated(property_value)
    elif property_type == "boolean":
        apdu += encode_boolean(property_value)
    elif property_type == "object_identifier":
        if isinstance(property_value, tuple):
            apdu += encode_object_identifier(property_value[0], property_value[1])
        else:
            apdu += encode_object_identifier(BACnetObjectType.DEVICE, property_value)
    elif property_type == "bitstring":
        # Encode as octet string for simplicity
        apdu += bytes([0x82, 0x02, 0x04, property_value & 0xFF])
    else:
        # Default to unsigned
        apdu += encode_unsigned(property_value if isinstance(property_value, int) else 0)

    # Property Value [3] - closing tag
    apdu += encode_closing_tag(3)

    return apdu


def build_read_property_multiple_request_apdu(
    invoke_id: int,
    read_access_specs: list[dict],
) -> bytes:
    """Build ReadPropertyMultiple confirmed request APDU.

    Args:
        invoke_id: Invoke ID
        read_access_specs: List of {object_type, object_instance, properties: [prop_ids]}

    Returns:
        ReadPropertyMultiple request APDU bytes
    """
    apdu = bytes([
        (BACnetPDUType.CONFIRMED_REQUEST << 4),
        0x05,
        invoke_id,
        BACnetConfirmedService.READ_PROPERTY_MULTIPLE
    ])

    for spec in read_access_specs:
        obj_type = spec["object_type"]
        obj_instance = spec["object_instance"]
        properties = spec.get("properties", [BACnetPropertyIdentifier.PRESENT_VALUE])

        # Object Identifier [0]
        obj_id_data = struct.pack(">I", ((obj_type & 0x3FF) << 22) | (obj_instance & 0x3FFFFF))
        apdu += encode_context_tag(0, obj_id_data)

        # List of Property References [1]
        apdu += encode_opening_tag(1)
        for prop_id in properties:
            # Property Identifier [0]
            apdu += encode_context_tag(0, encode_unsigned_raw(prop_id))
        apdu += encode_closing_tag(1)

    return apdu


def build_write_property_request_apdu(
    invoke_id: int,
    object_type: int,
    object_instance: int,
    property_id: int,
    property_value: Any,
    property_type: str = "unsigned",
    priority: int | None = None,
) -> bytes:
    """Build WriteProperty confirmed request APDU.

    Args:
        invoke_id: Invoke ID
        object_type: Target object type
        object_instance: Target object instance
        property_id: Property to write
        property_value: Value to write
        property_type: Type hint for encoding
        priority: Write priority (1-16, optional)

    Returns:
        WriteProperty request APDU bytes
    """
    apdu = bytes([
        (BACnetPDUType.CONFIRMED_REQUEST << 4),
        0x05,
        invoke_id,
        BACnetConfirmedService.WRITE_PROPERTY
    ])

    # Object Identifier [0]
    obj_id_data = struct.pack(">I", ((object_type & 0x3FF) << 22) | (object_instance & 0x3FFFFF))
    apdu += encode_context_tag(0, obj_id_data)

    # Property Identifier [1]
    apdu += encode_context_tag(1, encode_unsigned_raw(property_id))

    # Property Value [3]
    apdu += encode_opening_tag(3)
    if property_type == "unsigned":
        apdu += encode_unsigned(property_value)
    elif property_type == "real":
        apdu += encode_real(property_value)
    elif property_type == "string":
        apdu += encode_character_string(str(property_value))
    elif property_type == "enumerated":
        apdu += encode_enumerated(property_value)
    elif property_type == "boolean":
        apdu += encode_boolean(property_value)
    else:
        apdu += encode_unsigned(property_value)
    apdu += encode_closing_tag(3)

    # Priority [4] (optional)
    if priority is not None:
        apdu += encode_context_tag(4, encode_unsigned_raw(priority))

    return apdu


def build_simple_ack_apdu(invoke_id: int, service: int) -> bytes:
    """Build Simple-ACK response APDU.

    Args:
        invoke_id: Invoke ID (must match request)
        service: Service being acknowledged

    Returns:
        Simple-ACK APDU bytes
    """
    return bytes([
        (BACnetPDUType.SIMPLE_ACK << 4),
        invoke_id,
        service
    ])


def build_error_apdu(
    invoke_id: int,
    service: int,
    error_class: int,
    error_code: int,
) -> bytes:
    """Build Error response APDU.

    Args:
        invoke_id: Invoke ID (must match request)
        service: Service that generated the error
        error_class: BACnet error class
        error_code: BACnet error code

    Returns:
        Error APDU bytes
    """
    apdu = bytes([
        (BACnetPDUType.ERROR << 4),
        invoke_id,
        service
    ])
    apdu += encode_enumerated(error_class)
    apdu += encode_enumerated(error_code)
    return apdu


def build_reject_apdu(invoke_id: int, reject_reason: int) -> bytes:
    """Build Reject response APDU.

    Args:
        invoke_id: Invoke ID (must match request)
        reject_reason: Reject reason code

    Returns:
        Reject APDU bytes
    """
    return bytes([
        (BACnetPDUType.REJECT << 4),
        invoke_id,
        reject_reason
    ])


def build_abort_apdu(invoke_id: int, abort_reason: int, server: bool = True) -> bytes:
    """Build Abort response APDU.

    Args:
        invoke_id: Invoke ID
        abort_reason: Abort reason code
        server: True if server initiated abort

    Returns:
        Abort APDU bytes
    """
    return bytes([
        (BACnetPDUType.ABORT << 4) | (0x01 if server else 0x00),
        invoke_id,
        abort_reason
    ])


# ============================================================================
# Complete Packet Building
# ============================================================================

def build_bacnet_packet(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    bvlc_function: BVLCFunction,
    apdu: bytes,
    expecting_reply: bool = False,
    ttl: int = 64,
) -> bytes:
    """Build complete BACnet/IP packet with all layers.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_port: Source UDP port
        dst_port: Destination UDP port
        bvlc_function: BVLC function type
        apdu: APDU payload
        expecting_reply: Whether expecting a reply
        ttl: IP TTL value

    Returns:
        Complete packet bytes
    """
    # Build NPDU
    npdu = build_npdu(expecting_reply=expecting_reply)

    # Build BVLC header
    bvlc = build_bvlc_header(bvlc_function, len(npdu) + len(apdu))

    # BACnet payload
    bacnet_payload = bvlc + npdu + apdu

    # Build complete packet with Scapy
    packet = (
        Ether(src=src_mac, dst=dst_mac)
        / IP(src=src_ip, dst=dst_ip, ttl=ttl)
        / UDP(sport=src_port, dport=dst_port)
        / Raw(load=bacnet_payload)
    )

    return bytes(packet)


def build_who_is_packet(
    src: DeviceContext,
    low_limit: int | None = None,
    high_limit: int | None = None,
) -> bytes:
    """Build complete Who-Is broadcast packet.

    Args:
        src: Source device (manager)
        low_limit: Lower device instance limit (optional)
        high_limit: Upper device instance limit (optional)

    Returns:
        Complete Who-Is packet bytes
    """
    apdu = build_who_is_apdu(low_limit, high_limit)

    # Get TTL from fingerprint
    ttl = 64
    if src.vendor_fingerprint:
        tcp_stack = src.vendor_fingerprint.get("tcp_stack", {})
        ttl = tcp_stack.get("ttl", 64)

    return build_bacnet_packet(
        src_mac=src.mac_address,
        dst_mac="ff:ff:ff:ff:ff:ff",  # Broadcast
        src_ip=src.ip_address,
        dst_ip="255.255.255.255",
        src_port=BACNET_PORT,
        dst_port=BACNET_PORT,
        bvlc_function=BVLCFunction.ORIGINAL_BROADCAST_NPDU,
        apdu=apdu,
        expecting_reply=False,
        ttl=ttl,
    )


def build_i_am_packet(
    src: DeviceContext,
    device_instance: int,
    max_apdu_length: int = 1476,
    segmentation: int = BACnetSegmentation.NO_SEGMENTATION,
    vendor_id: int = 0,
) -> bytes:
    """Build complete I-Am broadcast response packet.

    This is the CRITICAL packet for Cyber Vision device detection.

    Args:
        src: Source device (responding device)
        device_instance: Device object instance
        max_apdu_length: Maximum APDU length supported
        segmentation: Segmentation support
        vendor_id: BACnet registered vendor ID

    Returns:
        Complete I-Am packet bytes
    """
    apdu = build_i_am_apdu(device_instance, max_apdu_length, segmentation, vendor_id)

    # Get TTL from fingerprint
    ttl = 64
    if src.vendor_fingerprint:
        tcp_stack = src.vendor_fingerprint.get("tcp_stack", {})
        ttl = tcp_stack.get("ttl", 64)

    return build_bacnet_packet(
        src_mac=src.mac_address,
        dst_mac="ff:ff:ff:ff:ff:ff",  # Broadcast response
        src_ip=src.ip_address,
        dst_ip="255.255.255.255",
        src_port=BACNET_PORT,
        dst_port=BACNET_PORT,
        bvlc_function=BVLCFunction.ORIGINAL_BROADCAST_NPDU,
        apdu=apdu,
        expecting_reply=False,
        ttl=ttl,
    )


def build_read_property_request_packet(
    src: DeviceContext,
    dst: DeviceContext,
    invoke_id: int,
    object_type: int,
    object_instance: int,
    property_id: int,
    array_index: int | None = None,
) -> bytes:
    """Build complete ReadProperty request packet.

    Args:
        src: Source device (requesting)
        dst: Destination device (target)
        invoke_id: Invoke ID for response matching
        object_type: Target object type
        object_instance: Target object instance
        property_id: Property to read
        array_index: Array index (optional)

    Returns:
        Complete ReadProperty request packet bytes
    """
    apdu = build_read_property_request_apdu(
        invoke_id, object_type, object_instance, property_id, array_index
    )

    ttl = 64
    if src.vendor_fingerprint:
        tcp_stack = src.vendor_fingerprint.get("tcp_stack", {})
        ttl = tcp_stack.get("ttl", 64)

    return build_bacnet_packet(
        src_mac=src.mac_address,
        dst_mac=dst.mac_address,
        src_ip=src.ip_address,
        dst_ip=dst.ip_address,
        src_port=BACNET_PORT,
        dst_port=BACNET_PORT,
        bvlc_function=BVLCFunction.ORIGINAL_UNICAST_NPDU,
        apdu=apdu,
        expecting_reply=True,
        ttl=ttl,
    )


def build_read_property_response_packet(
    src: DeviceContext,
    dst: DeviceContext,
    invoke_id: int,
    object_type: int,
    object_instance: int,
    property_id: int,
    property_value: Any,
    property_type: str = "unsigned",
) -> bytes:
    """Build complete ReadProperty response packet.

    Args:
        src: Source device (responding)
        dst: Destination device (requester)
        invoke_id: Invoke ID (must match request)
        object_type: Object type
        object_instance: Object instance
        property_id: Property identifier
        property_value: Property value
        property_type: Type hint for encoding

    Returns:
        Complete ReadProperty response packet bytes
    """
    apdu = build_read_property_response_apdu(
        invoke_id, object_type, object_instance, property_id,
        property_value, property_type
    )

    ttl = 64
    if src.vendor_fingerprint:
        tcp_stack = src.vendor_fingerprint.get("tcp_stack", {})
        ttl = tcp_stack.get("ttl", 64)

    return build_bacnet_packet(
        src_mac=src.mac_address,
        dst_mac=dst.mac_address,
        src_ip=src.ip_address,
        dst_ip=dst.ip_address,
        src_port=BACNET_PORT,
        dst_port=BACNET_PORT,
        bvlc_function=BVLCFunction.ORIGINAL_UNICAST_NPDU,
        apdu=apdu,
        expecting_reply=False,
        ttl=ttl,
    )
