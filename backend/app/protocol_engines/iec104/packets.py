# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""IEC 60870-5-104 packet building utilities.

IEC 104 is used for telecontrol in electric power systems,
running over TCP port 2404.

Protocol structure:
- APCI (Application Protocol Control Information): 6 bytes
  - Start byte: 0x68
  - APDU Length: 1 byte
  - Control fields: 4 bytes
- ASDU (Application Service Data Unit): variable length
  - Type ID: 1 byte
  - Variable structure qualifier: 1 byte
  - Cause of transmission: 2 bytes
  - Common address: 2 bytes
  - Information objects: variable

Frame types:
- I-format: Information transfer
- S-format: Supervisory (acknowledgment)
- U-format: Unnumbered control (STARTDT, STOPDT, TESTFR)
"""

import struct
from typing import Any

from app.protocol_engines.types import DeviceContext

# IEC 104 constants
IEC104_START_BYTE = 0x68
IEC104_PORT = 2404

# U-format control bytes
STARTDT_ACT = 0x07
STARTDT_CON = 0x0B
STOPDT_ACT = 0x13
STOPDT_CON = 0x23
TESTFR_ACT = 0x43
TESTFR_CON = 0x83

# Type identifiers (common ones)
# Process information in monitor direction
M_SP_NA_1 = 1    # Single-point information
M_SP_TA_1 = 2    # Single-point with time tag
M_DP_NA_1 = 3    # Double-point information
M_DP_TA_1 = 4    # Double-point with time tag
M_ST_NA_1 = 5    # Step position information
M_BO_NA_1 = 7    # Bitstring of 32 bits
M_ME_NA_1 = 9    # Measured value, normalized
M_ME_NB_1 = 11   # Measured value, scaled
M_ME_NC_1 = 13   # Measured value, short floating point
M_IT_NA_1 = 15   # Integrated totals
M_SP_TB_1 = 30   # Single-point with CP56Time2a
M_DP_TB_1 = 31   # Double-point with CP56Time2a
M_ME_TD_1 = 34   # Measured value, normalized with CP56Time2a
M_ME_TE_1 = 35   # Measured value, scaled with CP56Time2a
M_ME_TF_1 = 36   # Measured value, short floating point with CP56Time2a
M_IT_TB_1 = 37   # Integrated totals with CP56Time2a

# Process information in control direction
C_SC_NA_1 = 45   # Single command
C_DC_NA_1 = 46   # Double command
C_RC_NA_1 = 47   # Regulating step command
C_SE_NA_1 = 48   # Set-point command, normalized
C_SE_NB_1 = 49   # Set-point command, scaled
C_SE_NC_1 = 50   # Set-point command, short floating point
C_SC_TA_1 = 58   # Single command with time tag
C_DC_TA_1 = 59   # Double command with time tag

# System information
C_IC_NA_1 = 100  # Interrogation command
C_CI_NA_1 = 101  # Counter interrogation
C_RD_NA_1 = 102  # Read command
C_CS_NA_1 = 103  # Clock synchronization
C_TS_NA_1 = 104  # Test command
C_RP_NA_1 = 105  # Reset process command

# Cause of transmission (COT)
COT_PERIODIC = 1
COT_BACKGROUND = 2
COT_SPONTANEOUS = 3
COT_INITIALIZED = 4
COT_REQUEST = 5
COT_ACTIVATION = 6
COT_ACTIVATION_CON = 7
COT_DEACTIVATION = 8
COT_DEACTIVATION_CON = 9
COT_ACTIVATION_TERM = 10
COT_RETURN_REMOTE = 11
COT_RETURN_LOCAL = 12
COT_INTERROGATION = 20
COT_COUNTER_INTERROGATION = 37


def build_apci_u_format(control_byte: int) -> bytes:
    """Build U-format APCI (unnumbered control).

    Args:
        control_byte: U-format control byte (STARTDT, STOPDT, TESTFR)

    Returns:
        6-byte APCI
    """
    return bytes([
        IEC104_START_BYTE,
        4,  # APDU length (just control fields)
        control_byte,
        0x00,
        0x00,
        0x00,
    ])


def build_apci_s_format(recv_seq: int) -> bytes:
    """Build S-format APCI (supervisory).

    Args:
        recv_seq: Receive sequence number

    Returns:
        6-byte APCI
    """
    # S-format: bits 0-1 = 01
    control = 0x01 | ((recv_seq & 0x7FFF) << 17)
    return bytes([
        IEC104_START_BYTE,
        4,
        control & 0xFF,
        (control >> 8) & 0xFF,
        (control >> 16) & 0xFF,
        (control >> 24) & 0xFF,
    ])


def build_apci_i_format(send_seq: int, recv_seq: int, asdu_length: int) -> bytes:
    """Build I-format APCI (information transfer).

    Args:
        send_seq: Send sequence number
        recv_seq: Receive sequence number
        asdu_length: Length of ASDU

    Returns:
        6-byte APCI
    """
    # I-format: bit 0 = 0
    # Control field 1-2: Send sequence (bits 1-15)
    # Control field 3-4: Receive sequence (bits 1-15)
    cf1 = (send_seq << 1) & 0xFFFF
    cf2 = (recv_seq << 1) & 0xFFFF

    return bytes([
        IEC104_START_BYTE,
        4 + asdu_length,  # APDU length
        cf1 & 0xFF,
        (cf1 >> 8) & 0xFF,
        cf2 & 0xFF,
        (cf2 >> 8) & 0xFF,
    ])


def build_asdu_header(
    type_id: int,
    num_objects: int,
    sq: bool,
    cot: int,
    org: int,
    common_address: int,
) -> bytes:
    """Build ASDU header.

    Args:
        type_id: Type identification
        num_objects: Number of information objects
        sq: Sequence qualifier (True = sequential addresses)
        cot: Cause of transmission
        org: Originator address (0 for not used)
        common_address: Common address of ASDU

    Returns:
        ASDU header bytes (6 bytes for standard config)
    """
    # Variable structure qualifier
    vsq = (num_objects & 0x7F) | (0x80 if sq else 0x00)

    return bytes([
        type_id,
        vsq,
        cot & 0xFF,
        org,  # Usually 0
    ]) + struct.pack("<H", common_address)


def build_interrogation_command(
    send_seq: int,
    recv_seq: int,
    common_address: int,
    qoi: int = 20,  # Station interrogation
) -> bytes:
    """Build interrogation command (C_IC_NA_1).

    Args:
        send_seq: Send sequence number
        recv_seq: Receive sequence number
        common_address: Common address of ASDU
        qoi: Qualifier of interrogation (20 = station)

    Returns:
        Complete APDU bytes
    """
    # ASDU
    asdu_header = build_asdu_header(
        type_id=C_IC_NA_1,
        num_objects=1,
        sq=False,
        cot=COT_ACTIVATION,
        org=0,
        common_address=common_address,
    )

    # Information object: IOA (3 bytes) + QOI (1 byte)
    info_object = struct.pack("<I", 0)[:3] + bytes([qoi])

    asdu = asdu_header + info_object

    # APCI
    apci = build_apci_i_format(send_seq, recv_seq, len(asdu))

    return apci + asdu


def build_interrogation_response(
    send_seq: int,
    recv_seq: int,
    common_address: int,
    qoi: int = 20,
) -> bytes:
    """Build interrogation command confirmation.

    Args:
        send_seq: Send sequence number
        recv_seq: Receive sequence number
        common_address: Common address
        qoi: Qualifier of interrogation

    Returns:
        Complete APDU bytes
    """
    asdu_header = build_asdu_header(
        type_id=C_IC_NA_1,
        num_objects=1,
        sq=False,
        cot=COT_ACTIVATION_CON,
        org=0,
        common_address=common_address,
    )

    info_object = struct.pack("<I", 0)[:3] + bytes([qoi])
    asdu = asdu_header + info_object

    apci = build_apci_i_format(send_seq, recv_seq, len(asdu))
    return apci + asdu


def build_single_point_info(
    send_seq: int,
    recv_seq: int,
    common_address: int,
    values: list[tuple[int, bool]],
    cot: int = COT_SPONTANEOUS,
) -> bytes:
    """Build single-point information (M_SP_NA_1).

    Args:
        send_seq: Send sequence number
        recv_seq: Receive sequence number
        common_address: Common address
        values: List of (IOA, value) tuples
        cot: Cause of transmission

    Returns:
        Complete APDU bytes
    """
    asdu_header = build_asdu_header(
        type_id=M_SP_NA_1,
        num_objects=len(values),
        sq=False,
        cot=cot,
        org=0,
        common_address=common_address,
    )

    # Information objects
    info_objects = b""
    for ioa, value in values:
        # IOA (3 bytes) + SIQ (1 byte)
        siq = 0x01 if value else 0x00  # Value + quality (IV=0, NT=0, SB=0, BL=0)
        info_objects += struct.pack("<I", ioa)[:3] + bytes([siq])

    asdu = asdu_header + info_objects
    apci = build_apci_i_format(send_seq, recv_seq, len(asdu))
    return apci + asdu


def build_measured_value_float(
    send_seq: int,
    recv_seq: int,
    common_address: int,
    values: list[tuple[int, float]],
    cot: int = COT_SPONTANEOUS,
) -> bytes:
    """Build measured value, short floating point (M_ME_NC_1).

    Args:
        send_seq: Send sequence number
        recv_seq: Receive sequence number
        common_address: Common address
        values: List of (IOA, value) tuples
        cot: Cause of transmission

    Returns:
        Complete APDU bytes
    """
    asdu_header = build_asdu_header(
        type_id=M_ME_NC_1,
        num_objects=len(values),
        sq=False,
        cot=cot,
        org=0,
        common_address=common_address,
    )

    # Information objects
    info_objects = b""
    for ioa, value in values:
        # IOA (3 bytes) + Value (4 bytes float) + QDS (1 byte)
        qds = 0x00  # Quality descriptor (all good)
        info_objects += struct.pack("<I", ioa)[:3] + struct.pack("<f", value) + bytes([qds])

    asdu = asdu_header + info_objects
    apci = build_apci_i_format(send_seq, recv_seq, len(asdu))
    return apci + asdu


def build_measured_value_scaled(
    send_seq: int,
    recv_seq: int,
    common_address: int,
    values: list[tuple[int, int]],
    cot: int = COT_SPONTANEOUS,
) -> bytes:
    """Build measured value, scaled (M_ME_NB_1).

    Args:
        send_seq: Send sequence number
        recv_seq: Receive sequence number
        common_address: Common address
        values: List of (IOA, value) tuples (-32768 to 32767)
        cot: Cause of transmission

    Returns:
        Complete APDU bytes
    """
    asdu_header = build_asdu_header(
        type_id=M_ME_NB_1,
        num_objects=len(values),
        sq=False,
        cot=cot,
        org=0,
        common_address=common_address,
    )

    info_objects = b""
    for ioa, value in values:
        # IOA (3 bytes) + SVA (2 bytes) + QDS (1 byte)
        qds = 0x00
        info_objects += struct.pack("<I", ioa)[:3] + struct.pack("<h", value) + bytes([qds])

    asdu = asdu_header + info_objects
    apci = build_apci_i_format(send_seq, recv_seq, len(asdu))
    return apci + asdu


def build_single_command(
    send_seq: int,
    recv_seq: int,
    common_address: int,
    ioa: int,
    value: bool,
    select: bool = False,
) -> bytes:
    """Build single command (C_SC_NA_1).

    Args:
        send_seq: Send sequence number
        recv_seq: Receive sequence number
        common_address: Common address
        ioa: Information object address
        value: Command value (True = ON, False = OFF)
        select: Select before execute

    Returns:
        Complete APDU bytes
    """
    asdu_header = build_asdu_header(
        type_id=C_SC_NA_1,
        num_objects=1,
        sq=False,
        cot=COT_ACTIVATION,
        org=0,
        common_address=common_address,
    )

    # SCO (Single Command Output)
    # Bit 0: SCS (command state)
    # Bit 2-6: QU (qualifier)
    # Bit 7: S/E (select/execute)
    sco = (0x01 if value else 0x00) | (0x80 if select else 0x00)

    info_object = struct.pack("<I", ioa)[:3] + bytes([sco])
    asdu = asdu_header + info_object

    apci = build_apci_i_format(send_seq, recv_seq, len(asdu))
    return apci + asdu


def build_command_response(
    send_seq: int,
    recv_seq: int,
    common_address: int,
    type_id: int,
    ioa: int,
    value: Any,
    success: bool = True,
) -> bytes:
    """Build command confirmation response.

    Args:
        send_seq: Send sequence number
        recv_seq: Receive sequence number
        common_address: Common address
        type_id: Command type ID
        ioa: Information object address
        value: Command value
        success: Whether command succeeded

    Returns:
        Complete APDU bytes
    """
    cot = COT_ACTIVATION_CON if success else (COT_ACTIVATION_CON | 0x40)  # Negative confirm

    asdu_header = build_asdu_header(
        type_id=type_id,
        num_objects=1,
        sq=False,
        cot=cot,
        org=0,
        common_address=common_address,
    )

    if type_id == C_SC_NA_1:
        sco = 0x01 if value else 0x00
        info_object = struct.pack("<I", ioa)[:3] + bytes([sco])
    else:
        info_object = struct.pack("<I", ioa)[:3] + bytes([0x00])

    asdu = asdu_header + info_object
    apci = build_apci_i_format(send_seq, recv_seq, len(asdu))
    return apci + asdu


def build_interrogation_end(
    send_seq: int,
    recv_seq: int,
    common_address: int,
    qoi: int = 20,
) -> bytes:
    """Build interrogation termination.

    Args:
        send_seq: Send sequence number
        recv_seq: Receive sequence number
        common_address: Common address
        qoi: Qualifier of interrogation

    Returns:
        Complete APDU bytes
    """
    asdu_header = build_asdu_header(
        type_id=C_IC_NA_1,
        num_objects=1,
        sq=False,
        cot=COT_ACTIVATION_TERM,
        org=0,
        common_address=common_address,
    )

    info_object = struct.pack("<I", 0)[:3] + bytes([qoi])
    asdu = asdu_header + info_object

    apci = build_apci_i_format(send_seq, recv_seq, len(asdu))
    return apci + asdu


def build_tcp_header(src: DeviceContext, dst: DeviceContext) -> bytes:
    """Build Ethernet + IP + TCP header for IEC 104."""
    # Ethernet header
    dst_mac = bytes.fromhex(dst.mac_address.replace(":", "").replace("-", ""))
    src_mac = bytes.fromhex(src.mac_address.replace(":", "").replace("-", ""))
    eth_header = dst_mac + src_mac + b"\x08\x00"

    # IP header
    src_ip = [int(x) for x in src.ip_address.split(".")]
    dst_ip = [int(x) for x in dst.ip_address.split(".")]

    ip_header = bytes([
        0x45, 0x00, 0x00, 0x00,
        0x00, 0x01, 0x40, 0x00,
        0x40, 0x06, 0x00, 0x00,
        src_ip[0], src_ip[1], src_ip[2], src_ip[3],
        dst_ip[0], dst_ip[1], dst_ip[2], dst_ip[3],
    ])

    # TCP header
    src_port = src.port if src.port else 50000
    dst_port = dst.port if dst.port else IEC104_PORT

    tcp_header = struct.pack(
        ">HHIIBBHHH",
        src_port, dst_port,
        0, 0,
        0x50, 0x18,
        65535, 0, 0,
    )

    return eth_header + ip_header + tcp_header


def build_iec104_packet(
    src: DeviceContext,
    dst: DeviceContext,
    apdu: bytes,
    seq: int = 0,
    ack: int = 0,
) -> bytes:
    """Build complete IEC 104/TCP packet.

    Args:
        src: Source device
        dst: Destination device
        apdu: IEC 104 APDU
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
    total_len = 20 + 20 + len(apdu)
    header_list[16:18] = struct.pack(">H", total_len)

    return bytes(header_list) + apdu
