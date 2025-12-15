"""DNP3 packet building utilities.

DNP3 (Distributed Network Protocol) is used in SCADA systems,
particularly in water/wastewater, electric utilities, and oil/gas.

Protocol structure:
- Transport over TCP (port 20000) or serial
- Data Link Layer frame with start bytes 0x0564
- Transport Layer for fragmentation
- Application Layer for data objects

Frame structure:
- Start bytes: 0x05 0x64
- Length: 1 byte (5-255, excludes start bytes and CRC)
- Control: 1 byte
- Destination: 2 bytes (little-endian)
- Source: 2 bytes (little-endian)
- CRC: 2 bytes
- Data blocks with CRC every 16 bytes
"""

import struct
from typing import Any

from app.protocol_engines.types import DeviceContext

# DNP3 constants
DNP3_START_BYTES = b"\x05\x64"
DNP3_PORT = 20000

# Function codes
FC_CONFIRM = 0x00
FC_READ = 0x01
FC_WRITE = 0x02
FC_SELECT = 0x03
FC_OPERATE = 0x04
FC_DIRECT_OPERATE = 0x05
FC_DIRECT_OPERATE_NR = 0x06
FC_FREEZE = 0x07
FC_FREEZE_CLEAR = 0x08
FC_FREEZE_AT_TIME = 0x09
FC_FREEZE_AT_TIME_NR = 0x0A
FC_COLD_RESTART = 0x0D
FC_WARM_RESTART = 0x0E
FC_INITIALIZE_DATA = 0x0F
FC_INITIALIZE_APP = 0x10
FC_START_APP = 0x11
FC_STOP_APP = 0x12
FC_ENABLE_UNSOLICITED = 0x14
FC_DISABLE_UNSOLICITED = 0x15
FC_ASSIGN_CLASS = 0x16
FC_DELAY_MEASURE = 0x17
FC_RECORD_CURRENT_TIME = 0x18
FC_RESPONSE = 0x81
FC_UNSOLICITED_RESPONSE = 0x82

# Object groups
GROUP_BINARY_INPUT = 1
GROUP_BINARY_INPUT_EVENT = 2
GROUP_BINARY_OUTPUT = 10
GROUP_BINARY_OUTPUT_EVENT = 11
GROUP_COUNTER = 20
GROUP_COUNTER_EVENT = 22
GROUP_ANALOG_INPUT = 30
GROUP_ANALOG_INPUT_EVENT = 32
GROUP_ANALOG_OUTPUT = 40
GROUP_ANALOG_OUTPUT_EVENT = 42
GROUP_TIME = 50
GROUP_CLASS = 60
GROUP_INTERNAL_INDICATIONS = 80

# Qualifier codes
QC_RANGE_START_STOP = 0x00
QC_RANGE_STOP = 0x01
QC_ALL_OBJECTS = 0x06
QC_SINGLE_VALUE = 0x07
QC_RANGE_16BIT = 0x08


def calculate_crc(data: bytes) -> int:
    """Calculate DNP3 CRC-16.

    Uses polynomial 0x3D65 with initial value 0x0000.
    """
    crc_table = [
        0x0000, 0x365E, 0x6CBC, 0x5AE2, 0xD978, 0xEF26, 0xB5C4, 0x839A,
        0xFF89, 0xC9D7, 0x9335, 0xA56B, 0x26F1, 0x10AF, 0x4A4D, 0x7C13,
        0xB26B, 0x8435, 0xDED7, 0xE889, 0x6B13, 0x5D4D, 0x07AF, 0x31F1,
        0x4DE2, 0x7BBC, 0x215E, 0x1700, 0x949A, 0xA2C4, 0xF826, 0xCE78,
        0x29AF, 0x1FF1, 0x4513, 0x734D, 0xF0D7, 0xC689, 0x9C6B, 0xAA35,
        0xD626, 0xE078, 0xBA9A, 0x8CC4, 0x0F5E, 0x3900, 0x63E2, 0x55BC,
        0x9BC4, 0xAD9A, 0xF778, 0xC126, 0x42BC, 0x74E2, 0x2E00, 0x185E,
        0x644D, 0x5213, 0x08F1, 0x3EAF, 0xBD35, 0x8B6B, 0xD189, 0xE7D7,
        0x535E, 0x6500, 0x3FE2, 0x09BC, 0x8A26, 0xBC78, 0xE69A, 0xD0C4,
        0xACD7, 0x9A89, 0xC06B, 0xF635, 0x75AF, 0x43F1, 0x1913, 0x2F4D,
        0xE135, 0xD76B, 0x8D89, 0xBBD7, 0x384D, 0x0E13, 0x54F1, 0x62AF,
        0x1EBC, 0x28E2, 0x7200, 0x445E, 0xC7C4, 0xF19A, 0xAB78, 0x9D26,
        0x7AF1, 0x4CAF, 0x164D, 0x2013, 0xA389, 0x95D7, 0xCF35, 0xF96B,
        0x8578, 0xB326, 0xE9C4, 0xDF9A, 0x5C00, 0x6A5E, 0x30BC, 0x06E2,
        0xC89A, 0xFEC4, 0xA426, 0x9278, 0x11E2, 0x27BC, 0x7D5E, 0x4B00,
        0x3713, 0x014D, 0x5BAF, 0x6DF1, 0xEE6B, 0xD835, 0x82D7, 0xB489,
        0xA6BC, 0x90E2, 0xCA00, 0xFC5E, 0x7FC4, 0x499A, 0x1378, 0x2526,
        0x5935, 0x6F6B, 0x3589, 0x03D7, 0x804D, 0xB613, 0xECF1, 0xDAAF,
        0x14D7, 0x2289, 0x786B, 0x4E35, 0xCDAF, 0xFBF1, 0xA113, 0x974D,
        0xEB5E, 0xDD00, 0x87E2, 0xB1BC, 0x3226, 0x0478, 0x5E9A, 0x68C4,
        0x8F13, 0xB94D, 0xE3AF, 0xD5F1, 0x566B, 0x6035, 0x3AD7, 0x0C89,
        0x709A, 0x46C4, 0x1C26, 0x2A78, 0xA9E2, 0x9FBC, 0xC55E, 0xF300,
        0x3D78, 0x0B26, 0x51C4, 0x679A, 0xE400, 0xD25E, 0x88BC, 0xBEE2,
        0xC2F1, 0xF4AF, 0xAE4D, 0x9813, 0x1B89, 0x2DD7, 0x7735, 0x416B,
        0xF5E2, 0xC3BC, 0x995E, 0xAF00, 0x2C9A, 0x1AC4, 0x4026, 0x7678,
        0x0A6B, 0x3C35, 0x66D7, 0x5089, 0xD313, 0xE54D, 0xBFAF, 0x89F1,
        0x4789, 0x71D7, 0x2B35, 0x1D6B, 0x9EF1, 0xA8AF, 0xF24D, 0xC413,
        0xB800, 0x8E5E, 0xD4BC, 0xE2E2, 0x6178, 0x5726, 0x0DC4, 0x3B9A,
        0xDC4D, 0xEA13, 0xB0F1, 0x86AF, 0x0535, 0x336B, 0x6989, 0x5FD7,
        0x23C4, 0x159A, 0x4F78, 0x7926, 0xFABC, 0xCCE2, 0x9600, 0xA05E,
        0x6E26, 0x5878, 0x029A, 0x34C4, 0xB75E, 0x8100, 0xDBE2, 0xEDBC,
        0x91AF, 0xA7F1, 0xFD13, 0xCB4D, 0x48D7, 0x7E89, 0x246B, 0x1235,
    ]

    crc = 0x0000
    for byte in data:
        crc = (crc >> 8) ^ crc_table[(crc ^ byte) & 0xFF]

    return (~crc) & 0xFFFF


def build_data_link_frame(
    destination: int,
    source: int,
    control: int,
    payload: bytes,
) -> bytes:
    """Build DNP3 data link layer frame.

    Args:
        destination: Destination address (0-65519)
        source: Source address (0-65519)
        control: Control byte
        payload: Transport + Application layer data

    Returns:
        Complete data link frame with CRCs
    """
    # Header: Start(2) + Length(1) + Control(1) + Dest(2) + Src(2)
    length = 5 + len(payload)  # 5 = control(1) + dest(2) + src(2)

    header = (
        DNP3_START_BYTES +
        bytes([length]) +
        bytes([control]) +
        struct.pack("<H", destination) +
        struct.pack("<H", source)
    )

    # CRC for header (excludes start bytes)
    header_crc = calculate_crc(header[2:])
    header_with_crc = header + struct.pack("<H", header_crc)

    # Add CRC every 16 bytes of payload
    payload_with_crc = b""
    for i in range(0, len(payload), 16):
        block = payload[i:i + 16]
        block_crc = calculate_crc(block)
        payload_with_crc += block + struct.pack("<H", block_crc)

    return header_with_crc + payload_with_crc


def build_transport_header(fin: bool = True, fir: bool = True, sequence: int = 0) -> bytes:
    """Build DNP3 transport layer header.

    Args:
        fin: Final fragment flag
        fir: First fragment flag
        sequence: Sequence number (0-63)

    Returns:
        1-byte transport header
    """
    header = sequence & 0x3F
    if fir:
        header |= 0x40
    if fin:
        header |= 0x80
    return bytes([header])


def build_application_header(
    function_code: int,
    sequence: int = 0,
    fir: bool = True,
    fin: bool = True,
    con: bool = False,
    uns: bool = False,
) -> bytes:
    """Build DNP3 application layer header.

    Args:
        function_code: Function code
        sequence: Application sequence number
        fir: First fragment
        fin: Final fragment
        con: Confirm required
        uns: Unsolicited

    Returns:
        2-byte application header (control + function code)
    """
    control = sequence & 0x0F
    if fir:
        control |= 0x80
    if fin:
        control |= 0x40
    if con:
        control |= 0x20
    if uns:
        control |= 0x10

    return bytes([control, function_code])


def build_object_header(
    group: int,
    variation: int,
    qualifier: int,
    range_start: int = 0,
    range_stop: int = 0,
    count: int = 0,
) -> bytes:
    """Build DNP3 object header.

    Args:
        group: Object group
        variation: Object variation
        qualifier: Qualifier code
        range_start: Start index (for range qualifiers)
        range_stop: Stop index (for range qualifiers)
        count: Object count (for count qualifiers)

    Returns:
        Object header bytes
    """
    header = bytes([group, variation, qualifier])

    if qualifier == QC_RANGE_START_STOP:
        header += bytes([range_start, range_stop])
    elif qualifier == QC_RANGE_16BIT:
        header += struct.pack("<HH", range_start, range_stop)
    elif qualifier == QC_SINGLE_VALUE:
        header += bytes([count])
    elif qualifier == QC_ALL_OBJECTS:
        pass  # No range field

    return header


def build_read_request(
    destination: int,
    source: int,
    objects: list[tuple[int, int]],
    sequence: int = 0,
) -> bytes:
    """Build DNP3 Read request.

    Args:
        destination: Destination address
        source: Source address
        objects: List of (group, variation) tuples to read
        sequence: Sequence number

    Returns:
        Complete DNP3 Read request frame
    """
    # Application layer
    app_header = build_application_header(FC_READ, sequence)

    # Object headers (request all objects)
    object_data = b""
    for group, variation in objects:
        object_data += build_object_header(group, variation, QC_ALL_OBJECTS)

    app_layer = app_header + object_data

    # Transport layer
    transport_header = build_transport_header(fin=True, fir=True, sequence=sequence)
    transport_payload = transport_header + app_layer

    # Data link layer (control = 0xC4 for primary, unconfirmed)
    control = 0xC4
    frame = build_data_link_frame(destination, source, control, transport_payload)

    return frame


def build_read_response(
    destination: int,
    source: int,
    objects: list[tuple[int, int, list[Any]]],
    sequence: int = 0,
) -> bytes:
    """Build DNP3 Read response.

    Args:
        destination: Destination address
        source: Source address
        objects: List of (group, variation, values) tuples
        sequence: Sequence number

    Returns:
        Complete DNP3 Read response frame
    """
    # Application layer - Response
    app_header = build_application_header(FC_RESPONSE, sequence)

    # Internal indications (2 bytes, all clear)
    internal_indications = b"\x00\x00"

    # Object data
    object_data = b""
    for group, variation, values in objects:
        # Object header with count
        count = len(values)
        object_data += build_object_header(
            group, variation, QC_RANGE_START_STOP,
            range_start=0, range_stop=count - 1 if count > 0 else 0
        )

        # Values based on group/variation
        for value in values:
            if group == GROUP_BINARY_INPUT:
                # Binary input - 1 byte with flags
                flags = 0x01 if value else 0x00  # Online + value
                object_data += bytes([flags])
            elif group == GROUP_ANALOG_INPUT:
                if variation == 1:  # 32-bit with flag
                    flags = 0x01  # Online
                    object_data += bytes([flags]) + struct.pack("<i", int(value))
                elif variation == 2:  # 16-bit with flag
                    flags = 0x01
                    object_data += bytes([flags]) + struct.pack("<h", int(value))
                elif variation == 5:  # 32-bit float with flag
                    flags = 0x01
                    object_data += bytes([flags]) + struct.pack("<f", float(value))
            elif group == GROUP_COUNTER:
                if variation == 1:  # 32-bit with flag
                    flags = 0x01
                    object_data += bytes([flags]) + struct.pack("<I", int(value))

    app_layer = app_header + internal_indications + object_data

    # Transport layer
    transport_header = build_transport_header(fin=True, fir=True, sequence=sequence)
    transport_payload = transport_header + app_layer

    # Data link layer (control = 0x44 for secondary)
    control = 0x44
    frame = build_data_link_frame(destination, source, control, transport_payload)

    return frame


def build_write_request(
    destination: int,
    source: int,
    group: int,
    variation: int,
    values: list[Any],
    sequence: int = 0,
) -> bytes:
    """Build DNP3 Write request.

    Args:
        destination: Destination address
        source: Source address
        group: Object group
        variation: Object variation
        values: Values to write
        sequence: Sequence number

    Returns:
        Complete DNP3 Write request frame
    """
    # Application layer
    app_header = build_application_header(FC_WRITE, sequence)

    # Object header
    count = len(values)
    object_header = build_object_header(
        group, variation, QC_RANGE_START_STOP,
        range_start=0, range_stop=count - 1 if count > 0 else 0
    )

    # Object data based on group
    object_data = b""
    for value in values:
        if group == GROUP_BINARY_OUTPUT:
            # Binary output control
            control_code = 0x03 if value else 0x04  # Latch on/off
            object_data += bytes([control_code, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        elif group == GROUP_ANALOG_OUTPUT:
            if variation == 1:  # 32-bit
                object_data += bytes([0x00]) + struct.pack("<i", int(value))
            elif variation == 2:  # 16-bit
                object_data += bytes([0x00]) + struct.pack("<h", int(value))
            elif variation == 3:  # Float
                object_data += bytes([0x00]) + struct.pack("<f", float(value))

    app_layer = app_header + object_header + object_data

    # Transport layer
    transport_header = build_transport_header(fin=True, fir=True, sequence=sequence)
    transport_payload = transport_header + app_layer

    # Data link layer
    control = 0xC4
    frame = build_data_link_frame(destination, source, control, transport_payload)

    return frame


def build_write_response(
    destination: int,
    source: int,
    success: bool = True,
    sequence: int = 0,
) -> bytes:
    """Build DNP3 Write response (null response).

    Args:
        destination: Destination address
        source: Source address
        success: Whether the write succeeded
        sequence: Sequence number

    Returns:
        Complete DNP3 Write response frame
    """
    # Application layer - Response
    app_header = build_application_header(FC_RESPONSE, sequence)

    # Internal indications
    iin = 0x0000 if success else 0x0002  # Parameter error if failed
    internal_indications = struct.pack("<H", iin)

    app_layer = app_header + internal_indications

    # Transport layer
    transport_header = build_transport_header(fin=True, fir=True, sequence=sequence)
    transport_payload = transport_header + app_layer

    # Data link layer
    control = 0x44
    frame = build_data_link_frame(destination, source, control, transport_payload)

    return frame


def build_tcp_header(src: DeviceContext, dst: DeviceContext) -> bytes:
    """Build Ethernet + IP + TCP header for DNP3."""
    # Ethernet header
    dst_mac = bytes.fromhex(dst.mac_address.replace(":", "").replace("-", ""))
    src_mac = bytes.fromhex(src.mac_address.replace(":", "").replace("-", ""))
    eth_header = dst_mac + src_mac + b"\x08\x00"

    # IP header
    src_ip = [int(x) for x in src.ip_address.split(".")]
    dst_ip = [int(x) for x in dst.ip_address.split(".")]

    ip_header = bytes([
        0x45, 0x00, 0x00, 0x00,  # Version, IHL, TOS, Total length
        0x00, 0x01, 0x40, 0x00,  # ID, Flags, Fragment
        0x40, 0x06, 0x00, 0x00,  # TTL, Protocol (TCP), Checksum
        src_ip[0], src_ip[1], src_ip[2], src_ip[3],
        dst_ip[0], dst_ip[1], dst_ip[2], dst_ip[3],
    ])

    # TCP header
    src_port = src.port if src.port else 50000
    dst_port = dst.port if dst.port else DNP3_PORT

    tcp_header = struct.pack(
        ">HHIIBBHHH",
        src_port, dst_port,
        0, 0,  # Seq, Ack
        0x50, 0x18,  # Offset, Flags (PSH+ACK)
        65535, 0, 0,  # Window, Checksum, Urgent
    )

    return eth_header + ip_header + tcp_header


def build_dnp3_packet(
    src: DeviceContext,
    dst: DeviceContext,
    dnp3_frame: bytes,
    seq: int = 0,
    ack: int = 0,
) -> bytes:
    """Build complete DNP3/TCP packet.

    Args:
        src: Source device
        dst: Destination device
        dnp3_frame: DNP3 data link frame
        seq: TCP sequence number
        ack: TCP ack number

    Returns:
        Complete packet bytes
    """
    header = build_tcp_header(src, dst)

    # Update TCP seq/ack
    header_list = list(header)
    tcp_offset = 34

    header_list[tcp_offset + 4:tcp_offset + 8] = struct.pack(">I", seq)
    header_list[tcp_offset + 8:tcp_offset + 12] = struct.pack(">I", ack)

    # Update IP total length
    total_len = 20 + 20 + len(dnp3_frame)
    header_list[16:18] = struct.pack(">H", total_len)

    return bytes(header_list) + dnp3_frame
