"""IEC 61850 packet building utilities.

Builds packets for:
- GOOSE (Generic Object Oriented Substation Event) messages
- SV (Sampled Values) messages
- MMS (Manufacturing Message Specification) over TCP

GOOSE and SV are Layer 2 protocols (Ethernet).
MMS runs over TCP/IP using ISO-TSAP (RFC 1006) on port 102.
"""

import struct
import time
from typing import Any

from app.protocol_engines.iec61850.types import (
    GOOSE_ETHERTYPE,
    SV_ETHERTYPE,
    GOOSE_MULTICAST_PREFIX,
    SV_MULTICAST_PREFIX,
    GOOSEDataType,
    MMSPduType,
    MMSServiceType,
    GOOSEConfig,
    SVConfig,
    QualityFlags,
)
from app.protocol_engines.types import DeviceContext


# =============================================================================
# Ethernet Frame Building
# =============================================================================

def build_ethernet_header(
    src_mac: str,
    dst_mac: str,
    ethertype: int,
) -> bytes:
    """Build Ethernet header.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        ethertype: EtherType value

    Returns:
        14-byte Ethernet header
    """
    dst_bytes = bytes.fromhex(dst_mac.replace(":", "").replace("-", ""))
    src_bytes = bytes.fromhex(src_mac.replace(":", "").replace("-", ""))
    return dst_bytes + src_bytes + struct.pack(">H", ethertype)


def build_vlan_tag(vlan_id: int, priority: int = 4) -> bytes:
    """Build 802.1Q VLAN tag.

    Args:
        vlan_id: VLAN ID (1-4094)
        priority: Priority code point (0-7)

    Returns:
        4-byte VLAN tag
    """
    tci = (priority << 13) | vlan_id
    return struct.pack(">HH", 0x8100, tci)


def generate_goose_multicast_mac(app_id: int) -> str:
    """Generate GOOSE multicast MAC address from AppID.

    GOOSE uses multicast MAC range 01-0C-CD-01-xx-xx
    where xx-xx is derived from AppID.

    Args:
        app_id: GOOSE Application ID (0x0000-0x3FFF)

    Returns:
        MAC address string
    """
    high_byte = (app_id >> 8) & 0xFF
    low_byte = app_id & 0xFF
    return f"{GOOSE_MULTICAST_PREFIX}:{high_byte:02X}:{low_byte:02X}"


def generate_sv_multicast_mac(app_id: int) -> str:
    """Generate SV multicast MAC address from AppID.

    SV uses multicast MAC range 01-0C-CD-04-xx-xx
    where xx-xx is derived from AppID.

    Args:
        app_id: SV Application ID (0x4000-0x7FFF)

    Returns:
        MAC address string
    """
    high_byte = (app_id >> 8) & 0xFF
    low_byte = app_id & 0xFF
    return f"{SV_MULTICAST_PREFIX}:{high_byte:02X}:{low_byte:02X}"


# =============================================================================
# GOOSE Packet Building
# =============================================================================

def _encode_goose_length(length: int) -> bytes:
    """Encode ASN.1 BER length for GOOSE."""
    if length < 0x80:
        return bytes([length])
    elif length < 0x100:
        return bytes([0x81, length])
    elif length < 0x10000:
        return bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])
    else:
        return bytes([0x83, (length >> 16) & 0xFF, (length >> 8) & 0xFF, length & 0xFF])


def _encode_goose_string(tag: int, value: str) -> bytes:
    """Encode a tagged string for GOOSE."""
    encoded = value.encode('utf-8')
    return bytes([tag]) + _encode_goose_length(len(encoded)) + encoded


def _encode_goose_integer(tag: int, value: int, length: int = None) -> bytes:
    """Encode a tagged integer for GOOSE."""
    if length is None:
        if value == 0:
            length = 1
        elif value < 0:
            length = (value.bit_length() + 8) // 8
        else:
            length = (value.bit_length() + 7) // 8

    if value < 0:
        value_bytes = value.to_bytes(length, byteorder='big', signed=True)
    else:
        value_bytes = value.to_bytes(length, byteorder='big', signed=False)

    return bytes([tag]) + _encode_goose_length(length) + value_bytes


def _encode_goose_boolean(tag: int, value: bool) -> bytes:
    """Encode a tagged boolean for GOOSE."""
    return bytes([tag, 0x01, 0xFF if value else 0x00])


def _encode_utc_time(timestamp: float = None) -> bytes:
    """Encode UTC timestamp for GOOSE.

    Format: 8 bytes
    - 4 bytes: Seconds since epoch
    - 3 bytes: Fraction of second (24 bits)
    - 1 byte: Quality flags

    Args:
        timestamp: Unix timestamp (default: current time)

    Returns:
        8-byte UTC time encoding
    """
    if timestamp is None:
        timestamp = time.time()

    seconds = int(timestamp)
    fraction = timestamp - seconds
    fraction_int = int(fraction * (2**24))

    quality = 0x0A  # clockFailure=0, notSynchronized=0, accuracy=10 (~1ms)

    return struct.pack(
        ">I",
        seconds,
    ) + struct.pack(
        ">I",
        (fraction_int << 8) | quality,
    )[1:]  # Take only last 3 bytes


def encode_goose_data_value(value: Any, data_type: GOOSEDataType = None) -> bytes:
    """Encode a single data value for GOOSE allData.

    Args:
        value: Value to encode
        data_type: Optional explicit data type

    Returns:
        ASN.1 encoded value
    """
    if data_type is None:
        # Auto-detect type
        if isinstance(value, bool):
            data_type = GOOSEDataType.BOOLEAN
        elif isinstance(value, int):
            data_type = GOOSEDataType.INTEGER
        elif isinstance(value, float):
            data_type = GOOSEDataType.FLOATING_POINT
        elif isinstance(value, str):
            data_type = GOOSEDataType.VISIBLE_STRING
        elif isinstance(value, bytes):
            data_type = GOOSEDataType.OCTET_STRING
        else:
            data_type = GOOSEDataType.INTEGER

    if data_type == GOOSEDataType.BOOLEAN:
        return _encode_goose_boolean(data_type, bool(value))
    elif data_type == GOOSEDataType.INTEGER:
        return _encode_goose_integer(data_type, int(value))
    elif data_type == GOOSEDataType.UNSIGNED:
        return _encode_goose_integer(data_type, int(value))
    elif data_type == GOOSEDataType.FLOATING_POINT:
        # IEEE 754 single precision
        float_bytes = struct.pack('>f', float(value))
        return bytes([data_type]) + _encode_goose_length(4) + float_bytes
    elif data_type == GOOSEDataType.VISIBLE_STRING:
        return _encode_goose_string(data_type, str(value))
    elif data_type == GOOSEDataType.OCTET_STRING:
        if isinstance(value, str):
            value = value.encode('utf-8')
        return bytes([data_type]) + _encode_goose_length(len(value)) + value
    elif data_type == GOOSEDataType.BIT_STRING:
        # Bit string: first byte is unused bits count
        if isinstance(value, int):
            bit_bytes = value.to_bytes((value.bit_length() + 7) // 8, 'big')
            unused = (8 - (value.bit_length() % 8)) % 8
            content = bytes([unused]) + bit_bytes
        else:
            content = bytes([0]) + bytes(value)
        return bytes([data_type]) + _encode_goose_length(len(content)) + content
    else:
        # Default to integer
        return _encode_goose_integer(GOOSEDataType.INTEGER, int(value))


def build_goose_pdu(
    gocb_ref: str,
    time_allowed_to_live: int,
    dat_set: str,
    go_id: str,
    t: float,
    st_num: int,
    sq_num: int,
    simulation: bool,
    conf_rev: int,
    nds_com: bool,
    num_dat_set_entries: int,
    all_data: list[tuple[Any, GOOSEDataType | None]],
) -> bytes:
    """Build GOOSE PDU (IEC 61850-8-1 Annex A).

    Args:
        gocb_ref: GOOSE Control Block reference
        time_allowed_to_live: Time allowed to live in ms
        dat_set: Dataset reference
        go_id: GOOSE ID
        t: Timestamp (Unix time)
        st_num: State number
        sq_num: Sequence number
        simulation: Simulation flag
        conf_rev: Configuration revision
        nds_com: Needs commissioning flag
        num_dat_set_entries: Number of dataset entries
        all_data: List of (value, data_type) tuples

    Returns:
        GOOSE PDU bytes
    """
    # Build allData (context tag 0xAB)
    all_data_content = b''
    for value, data_type in all_data:
        all_data_content += encode_goose_data_value(value, data_type)

    all_data_field = bytes([0xAB]) + _encode_goose_length(len(all_data_content)) + all_data_content

    # Build GOOSE PDU fields
    pdu_content = b''

    # gocbRef [0] VisibleString
    pdu_content += _encode_goose_string(0x80, gocb_ref)

    # timeAllowedtoLive [1] INTEGER
    pdu_content += _encode_goose_integer(0x81, time_allowed_to_live)

    # datSet [2] VisibleString
    pdu_content += _encode_goose_string(0x82, dat_set)

    # goID [3] VisibleString (optional)
    if go_id:
        pdu_content += _encode_goose_string(0x83, go_id)

    # t [4] UtcTime
    pdu_content += bytes([0x84, 0x08]) + _encode_utc_time(t)

    # stNum [5] INTEGER
    pdu_content += _encode_goose_integer(0x85, st_num)

    # sqNum [6] INTEGER
    pdu_content += _encode_goose_integer(0x86, sq_num)

    # simulation [7] BOOLEAN (default FALSE)
    if simulation:
        pdu_content += _encode_goose_boolean(0x87, simulation)

    # confRev [8] INTEGER
    pdu_content += _encode_goose_integer(0x88, conf_rev)

    # ndsCom [9] BOOLEAN (default FALSE)
    if nds_com:
        pdu_content += _encode_goose_boolean(0x89, nds_com)

    # numDatSetEntries [10] INTEGER
    pdu_content += _encode_goose_integer(0x8A, num_dat_set_entries)

    # allData [11] SEQUENCE
    pdu_content += all_data_field

    # Wrap in GOOSE PDU sequence (tag 0x61)
    goose_pdu = bytes([0x61]) + _encode_goose_length(len(pdu_content)) + pdu_content

    return goose_pdu


def build_goose_packet(
    src: DeviceContext,
    config: GOOSEConfig,
    st_num: int,
    sq_num: int,
    all_data: list[tuple[Any, GOOSEDataType | None]],
    timestamp: float = None,
) -> bytes:
    """Build complete GOOSE Ethernet frame.

    Args:
        src: Source device context
        config: GOOSE configuration
        st_num: State number
        sq_num: Sequence number
        all_data: Data values to include
        timestamp: Optional timestamp (default: current time)

    Returns:
        Complete Ethernet frame bytes
    """
    if timestamp is None:
        timestamp = time.time()

    # Determine multicast address
    dst_mac = config.multicast_addr or generate_goose_multicast_mac(config.app_id)

    # Build GOOSE PDU
    goose_pdu = build_goose_pdu(
        gocb_ref=config.gocb_ref,
        time_allowed_to_live=4000,  # 4 seconds
        dat_set=config.dat_set,
        go_id=config.go_id,
        t=timestamp,
        st_num=st_num,
        sq_num=sq_num,
        simulation=False,
        conf_rev=config.conf_rev,
        nds_com=config.needs_comm,
        num_dat_set_entries=len(all_data),
        all_data=all_data,
    )

    # Build GOOSE header (after EtherType)
    # APPID (2 bytes) + Length (2 bytes) + Reserved1 (2 bytes) + Reserved2 (2 bytes)
    goose_header = struct.pack(
        ">HHHH",
        config.app_id,
        len(goose_pdu) + 8,  # Length includes header
        0x0000,  # Reserved1
        0x0000,  # Reserved2
    )

    # Build Ethernet frame
    if config.vlan_id:
        eth_header = build_ethernet_header(src.mac_address, dst_mac, 0x8100)
        vlan_tag = struct.pack(">HH", (config.vlan_priority << 13) | config.vlan_id, GOOSE_ETHERTYPE)
        return eth_header + vlan_tag + goose_header + goose_pdu
    else:
        eth_header = build_ethernet_header(src.mac_address, dst_mac, GOOSE_ETHERTYPE)
        return eth_header + goose_header + goose_pdu


# =============================================================================
# Sampled Values Packet Building
# =============================================================================

def build_sv_asdu(
    sv_id: str,
    dat_set: str | None,
    smp_cnt: int,
    conf_rev: int,
    smp_synch: int,
    sample_data: bytes,
) -> bytes:
    """Build SV ASDU (Application Service Data Unit).

    Args:
        sv_id: Sampled Value ID
        dat_set: Dataset reference (optional)
        smp_cnt: Sample count
        conf_rev: Configuration revision
        smp_synch: Synchronization status
        sample_data: Raw sample data bytes

    Returns:
        ASDU bytes
    """
    asdu_content = b''

    # svID [0] VisibleString
    asdu_content += _encode_goose_string(0x80, sv_id)

    # datSet [1] VisibleString (optional)
    if dat_set:
        asdu_content += _encode_goose_string(0x81, dat_set)

    # smpCnt [2] INTEGER
    asdu_content += _encode_goose_integer(0x82, smp_cnt, 2)

    # confRev [3] INTEGER
    asdu_content += _encode_goose_integer(0x83, conf_rev, 4)

    # smpSynch [5] INTEGER (optional, 0=none, 1=local, 2=global)
    if smp_synch is not None:
        asdu_content += _encode_goose_integer(0x85, smp_synch, 1)

    # seqData [7] OCTET STRING - sample data
    asdu_content += bytes([0x87]) + _encode_goose_length(len(sample_data)) + sample_data

    # Wrap in SEQUENCE
    return bytes([0x30]) + _encode_goose_length(len(asdu_content)) + asdu_content


def build_sv_pdu(
    no_asdu: int,
    asdus: list[bytes],
) -> bytes:
    """Build SV PDU containing multiple ASDUs.

    Args:
        no_asdu: Number of ASDUs
        asdus: List of ASDU bytes

    Returns:
        SV PDU bytes
    """
    # savPdu ::= SEQUENCE {
    #   noASDU [0] INTEGER,
    #   seqASDU [2] SEQUENCE OF ASDU
    # }

    pdu_content = b''

    # noASDU
    pdu_content += _encode_goose_integer(0x80, no_asdu)

    # seqASDU - sequence of ASDUs
    seq_content = b''.join(asdus)
    pdu_content += bytes([0xA2]) + _encode_goose_length(len(seq_content)) + seq_content

    # Wrap in savPdu sequence (tag 0x60)
    return bytes([0x60]) + _encode_goose_length(len(pdu_content)) + pdu_content


def generate_3phase_samples(
    smp_cnt: int,
    magnitude: float = 1.0,
    frequency: float = 50.0,
    samples_per_cycle: int = 80,
    include_neutral: bool = True,
) -> bytes:
    """Generate 3-phase voltage/current sample data.

    Generates instantaneous values for a 3-phase system
    at the given sample count position.

    Args:
        smp_cnt: Current sample count
        magnitude: Peak magnitude (per-unit or actual)
        frequency: System frequency (Hz)
        samples_per_cycle: Samples per cycle
        include_neutral: Include neutral current

    Returns:
        Sample data bytes (4 bytes per channel)
    """
    import math

    # Calculate phase angle for this sample
    samples_per_second = samples_per_cycle * frequency
    t = (smp_cnt % samples_per_cycle) / samples_per_second
    omega = 2 * math.pi * frequency

    # 3-phase angles (120 degrees apart)
    phases = [0, -2*math.pi/3, 2*math.pi/3]

    sample_bytes = b''

    # For each phase, generate voltage and current
    for phase in phases:
        # Voltage sample (scaled to 32-bit integer)
        v = magnitude * math.sin(omega * t + phase)
        v_int = int(v * 0x7FFFFFFF)  # Scale to int32
        sample_bytes += struct.pack('>i', v_int)

        # Current sample (with small phase shift for realistic load)
        i = magnitude * 0.8 * math.sin(omega * t + phase - 0.2)
        i_int = int(i * 0x7FFFFFFF)
        sample_bytes += struct.pack('>i', i_int)

    # Neutral current (sum of phase currents, should be ~0 in balanced system)
    if include_neutral:
        n_int = 0
        sample_bytes += struct.pack('>i', n_int)

    return sample_bytes


def build_sv_packet(
    src: DeviceContext,
    config: SVConfig,
    smp_cnt: int,
    sample_data: bytes,
    smp_synch: int = 2,  # Global sync
) -> bytes:
    """Build complete SV Ethernet frame.

    Args:
        src: Source device context
        config: SV configuration
        smp_cnt: Sample count
        sample_data: Raw sample data
        smp_synch: Synchronization status

    Returns:
        Complete Ethernet frame bytes
    """
    # Build ASDU
    asdu = build_sv_asdu(
        sv_id=config.sv_id,
        dat_set=config.dat_set,
        smp_cnt=smp_cnt,
        conf_rev=config.conf_rev,
        smp_synch=smp_synch,
        sample_data=sample_data,
    )

    # Build PDU with single ASDU
    sv_pdu = build_sv_pdu(no_asdu=1, asdus=[asdu])

    # Determine multicast address
    dst_mac = config.multicast_addr or generate_sv_multicast_mac(config.app_id)

    # Build SV header
    sv_header = struct.pack(
        ">HHHH",
        config.app_id,
        len(sv_pdu) + 8,  # Length includes header
        0x0000,  # Reserved1
        0x0000,  # Reserved2
    )

    # Build Ethernet frame
    if config.vlan_id:
        eth_header = build_ethernet_header(src.mac_address, dst_mac, 0x8100)
        vlan_tag = struct.pack(">HH", (config.vlan_priority << 13) | config.vlan_id, SV_ETHERTYPE)
        return eth_header + vlan_tag + sv_header + sv_pdu
    else:
        eth_header = build_ethernet_header(src.mac_address, dst_mac, SV_ETHERTYPE)
        return eth_header + sv_header + sv_pdu


# =============================================================================
# MMS Packet Building (simplified)
# =============================================================================

def build_cotp_cr(
    src_ref: int,
    dst_ref: int = 0,
    tpdu_size: int = 10,  # 2^10 = 1024 bytes
) -> bytes:
    """Build COTP Connection Request (CR).

    Args:
        src_ref: Source reference
        dst_ref: Destination reference
        tpdu_size: TPDU size parameter (encoded as 2^n)

    Returns:
        COTP CR TPDU bytes
    """
    # CR TPDU structure:
    # Length (1) + Code (1) + DST-REF (2) + SRC-REF (2) + Class (1) + Parameters
    code = 0xE0  # CR TPDU

    params = bytes([
        0xC0, 0x01, tpdu_size,  # TPDU size parameter
    ])

    content = struct.pack(">BHH", code, dst_ref, src_ref) + bytes([0x00]) + params
    length = len(content)

    return bytes([length]) + content


def build_cotp_cc(
    src_ref: int,
    dst_ref: int,
    tpdu_size: int = 10,
) -> bytes:
    """Build COTP Connection Confirm (CC).

    Args:
        src_ref: Source reference
        dst_ref: Destination reference
        tpdu_size: TPDU size parameter

    Returns:
        COTP CC TPDU bytes
    """
    code = 0xD0  # CC TPDU

    params = bytes([
        0xC0, 0x01, tpdu_size,  # TPDU size parameter
    ])

    content = struct.pack(">BHH", code, dst_ref, src_ref) + bytes([0x00]) + params
    length = len(content)

    return bytes([length]) + content


def build_cotp_dt(data: bytes, eot: bool = True) -> bytes:
    """Build COTP Data Transfer (DT).

    Args:
        data: Data to transfer
        eot: End of transmission flag

    Returns:
        COTP DT TPDU bytes
    """
    code = 0xF0  # DT TPDU
    tpdu_nr_eot = 0x80 if eot else 0x00  # TPDU-NR and EOT

    header = bytes([0x02, code, tpdu_nr_eot])
    return header + data


def build_mms_initiate_request(
    local_detail_calling: int = 65000,
    proposed_max_serv: int = 5,
    proposed_max_serv_outstanding: int = 5,
    proposed_data_structure_nesting_level: int = 4,
) -> bytes:
    """Build MMS Initiate Request PDU.

    Args:
        local_detail_calling: Local detail (max PDU size)
        proposed_max_serv: Proposed max services
        proposed_max_serv_outstanding: Proposed outstanding services
        proposed_data_structure_nesting_level: Nesting level

    Returns:
        MMS Initiate Request bytes
    """
    # Simplified MMS Initiate Request
    content = b''

    # localDetailCalling [0] INTEGER
    content += _encode_goose_integer(0x80, local_detail_calling, 3)

    # proposedMaxServOutstandingCalling [1] INTEGER
    content += _encode_goose_integer(0x81, proposed_max_serv)

    # proposedMaxServOutstandingCalled [2] INTEGER
    content += _encode_goose_integer(0x82, proposed_max_serv)

    # proposedDataStructureNestingLevel [3] INTEGER
    content += _encode_goose_integer(0x83, proposed_data_structure_nesting_level)

    # initRequestDetail [4] - contains supported services bitstring
    init_detail = bytes([0x84, 0x01, 0x00])  # Minimal
    content += init_detail

    # Wrap in Initiate-Request [8] SEQUENCE
    return bytes([MMSPduType.INITIATE_REQUEST]) + _encode_goose_length(len(content)) + content


def build_mms_initiate_response(
    local_detail_called: int = 65000,
    proposed_max_serv: int = 5,
) -> bytes:
    """Build MMS Initiate Response PDU."""
    content = b''

    # localDetailCalled [0] INTEGER
    content += _encode_goose_integer(0x80, local_detail_called, 3)

    # negotiatedMaxServOutstandingCalling [1] INTEGER
    content += _encode_goose_integer(0x81, proposed_max_serv)

    # negotiatedMaxServOutstandingCalled [2] INTEGER
    content += _encode_goose_integer(0x82, proposed_max_serv)

    # negotiatedDataStructureNestingLevel [3] INTEGER
    content += _encode_goose_integer(0x83, 4)

    # initResponseDetail [4]
    init_detail = bytes([0x84, 0x01, 0x00])
    content += init_detail

    return bytes([MMSPduType.INITIATE_RESPONSE]) + _encode_goose_length(len(content)) + content


def build_mms_read_request(
    invoke_id: int,
    variable_spec: str,
    domain_id: str = None,
) -> bytes:
    """Build MMS Read Request for a named variable.

    Args:
        invoke_id: Invoke ID
        variable_spec: Variable specification (name path)
        domain_id: Optional domain ID

    Returns:
        MMS confirmed request bytes
    """
    # Build variable specification
    if domain_id:
        # Domain-specific name
        var_spec = _encode_goose_string(0x80, domain_id)
        var_spec += _encode_goose_string(0x81, variable_spec)
        var_spec = bytes([0xA1]) + _encode_goose_length(len(var_spec)) + var_spec
    else:
        # VMD-specific name
        var_spec = _encode_goose_string(0x80, variable_spec)
        var_spec = bytes([0xA0]) + _encode_goose_length(len(var_spec)) + var_spec

    # Wrap in listOfVariable
    list_spec = bytes([0x30]) + _encode_goose_length(len(var_spec)) + var_spec
    list_of_var = bytes([0xA0]) + _encode_goose_length(len(list_spec)) + list_spec

    # Build Read request
    read_req = list_of_var
    read_req_wrapped = bytes([0xA4]) + _encode_goose_length(len(read_req)) + read_req  # [4] Read

    # Build confirmed request
    confirmed_req = _encode_goose_integer(0x80, invoke_id)  # invokeID
    confirmed_req += read_req_wrapped

    return bytes([MMSPduType.CONFIRMED_REQUEST]) + _encode_goose_length(len(confirmed_req)) + confirmed_req


def build_mms_read_response(
    invoke_id: int,
    values: list[tuple[Any, str]],  # (value, type)
) -> bytes:
    """Build MMS Read Response.

    Args:
        invoke_id: Invoke ID (must match request)
        values: List of (value, type) tuples

    Returns:
        MMS confirmed response bytes
    """
    # Build listOfAccessResult
    access_results = b''
    for value, value_type in values:
        if value_type == "boolean":
            result = _encode_goose_boolean(0x83, value)
        elif value_type == "integer":
            result = _encode_goose_integer(0x85, value)
        elif value_type == "float":
            float_bytes = struct.pack('>f', value)
            result = bytes([0x87, 0x05, 0x08]) + float_bytes
        elif value_type == "string":
            result = _encode_goose_string(0x8A, value)
        else:
            result = _encode_goose_integer(0x85, value)

        # Wrap in success [0]
        result = bytes([0xA0]) + _encode_goose_length(len(result)) + result
        access_results += result

    list_wrapper = bytes([0xA0]) + _encode_goose_length(len(access_results)) + access_results

    # Build Read response
    read_resp = list_wrapper
    read_resp_wrapped = bytes([0xA4]) + _encode_goose_length(len(read_resp)) + read_resp

    # Build confirmed response
    confirmed_resp = _encode_goose_integer(0x80, invoke_id)  # invokeID
    confirmed_resp += read_resp_wrapped

    return bytes([MMSPduType.CONFIRMED_RESPONSE]) + _encode_goose_length(len(confirmed_resp)) + confirmed_resp


def build_tpkt_header(length: int) -> bytes:
    """Build RFC 1006 TPKT header.

    Args:
        length: Length of data following header

    Returns:
        4-byte TPKT header
    """
    version = 3
    reserved = 0
    total_length = length + 4  # Include header
    return struct.pack(">BBHH", version, reserved, total_length, total_length)[:-2] + struct.pack(">H", total_length)


def build_mms_tcp_packet(
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    mms_pdu: bytes,
    cotp_header: bytes = None,
    tcp_seq: int = 1000,
    tcp_ack: int = 1000,
) -> bytes:
    """Build complete MMS over TCP packet.

    Note: This builds the payload structure. Actual packet with
    Ethernet/IP/TCP headers should use Scapy.

    Args:
        src_ip: Source IP
        dst_ip: Destination IP
        src_port: Source TCP port
        dst_port: Destination TCP port (usually 102)
        mms_pdu: MMS PDU bytes
        cotp_header: Optional COTP header (uses DT if None)
        tcp_seq: TCP sequence number
        tcp_ack: TCP acknowledgment number

    Returns:
        TCP payload bytes (TPKT + COTP + MMS)
    """
    # Build COTP DT if not provided
    if cotp_header is None:
        cotp_header = build_cotp_dt(mms_pdu)
    else:
        cotp_header = cotp_header + mms_pdu

    # Build TPKT
    tpkt = build_tpkt_header(len(cotp_header))

    return tpkt + cotp_header
