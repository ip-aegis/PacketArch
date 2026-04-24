# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""PROFINET packet building utilities using Scapy.

PROFINET uses Ethernet Layer 2 with EtherType 0x8892 for RT data.
This module builds:
- DCP (Discovery and Configuration Protocol) frames
- RT (Real-Time) cyclic I/O data frames
- RTA (Real-Time Acyclic) frames for alarms
- RPC (DCE/RPC over UDP) frames for AR establishment
"""

import struct
import uuid
from typing import TYPE_CHECKING, Any

from app.protocol_engines.types import DeviceContext

if TYPE_CHECKING:
    from app.protocol_engines.fingerprint_applicator import FingerprintApplicator


# PROFINET EtherTypes
PROFINET_ETHERTYPE = 0x8892
VLAN_ETHERTYPE = 0x8100

# PROFINET Frame IDs
# RT Class 1 (unsynchronized): 0x8000-0xBFFF
# RT Class 2 (synchronized): 0xC000-0xFBFF
# RT Class 3 (IRT - isochronous): 0x0100-0x7FFF
# DCP: 0xFEFC-0xFEFF
FRAME_ID_DCP_HELLO = 0xFEFC
FRAME_ID_DCP_GET_SET = 0xFEFD
FRAME_ID_DCP_IDENTIFY_REQ = 0xFEFE
FRAME_ID_DCP_IDENTIFY_RES = 0xFEFF
FRAME_ID_RTA = 0xFC01  # Real-Time Acyclic

# PROFINET Sync Frame IDs (for IRT)
FRAME_ID_PTCP_SYNC = 0xFF00      # PTCP Sync (Precision Time Clock Protocol)
FRAME_ID_PTCP_FOLLOWUP = 0xFF20  # PTCP FollowUp
FRAME_ID_PTCP_DELAY_REQ = 0xFF40 # PTCP DelayReq
FRAME_ID_PTCP_DELAY_RES = 0xFF41 # PTCP DelayRes

# IRT Frame ID ranges
IRT_FRAME_ID_MIN = 0x0100
IRT_FRAME_ID_MAX = 0x7FFF

# RT Class definitions
class RTClass:
    """PROFINET Real-Time classes."""
    RT_CLASS_1 = 1   # Unsynchronized RT (UDP or VLAN, 1-10ms cycle)
    RT_CLASS_2 = 2   # Synchronized RT (VLAN, 1-10ms cycle)
    RT_CLASS_3 = 3   # IRT - Isochronous RT (<1ms cycle, deterministic)
    RT_CLASS_UDP = 0 # RT over UDP (class 1 variant)


class IRTPhase:
    """PROFINET IRT phase types."""
    RED_PHASE = 1    # Deterministic phase (IRT data only)
    ORANGE_PHASE = 2 # Transition phase
    GREEN_PHASE = 3  # Open phase (RT class 1/2 and best-effort)

# DCP Service IDs
DCP_SERVICE_GET = 0x03
DCP_SERVICE_SET = 0x04
DCP_SERVICE_IDENTIFY = 0x05
DCP_SERVICE_HELLO = 0x06

# DCP Service Types
DCP_SERVICE_TYPE_REQUEST = 0x00
DCP_SERVICE_TYPE_RESPONSE_SUCCESS = 0x01
DCP_SERVICE_TYPE_RESPONSE_NOT_SUPPORTED = 0x05

# DCP Options
DCP_OPTION_IP = 0x01
DCP_OPTION_DEVICE = 0x02
DCP_OPTION_DHCP = 0x03
DCP_OPTION_CONTROL = 0x05
DCP_OPTION_ALL = 0xFF

# DCP Suboptions for Device
DCP_SUBOPTION_DEVICE_VENDOR = 0x01
DCP_SUBOPTION_DEVICE_NAME = 0x02
DCP_SUBOPTION_DEVICE_ID = 0x03
DCP_SUBOPTION_DEVICE_ROLE = 0x04
DCP_SUBOPTION_DEVICE_OPTIONS = 0x05
DCP_SUBOPTION_DEVICE_ALIAS = 0x06
DCP_SUBOPTION_DEVICE_INSTANCE = 0x07
DCP_SUBOPTION_DEVICE_OEM_ID = 0x08  # OEM Device ID (Vendor-specific info)

# DCP Suboptions for Device Initiative (Option 0x06)
DCP_OPTION_DEVICE_INITIATIVE = 0x06
DCP_SUBOPTION_DEVICE_INITIATIVE_VALUE = 0x01

# DCP Suboptions for IP
DCP_SUBOPTION_IP_MAC = 0x01
DCP_SUBOPTION_IP_PARAMETER = 0x02


def build_ethernet_header(src: DeviceContext, dst: DeviceContext, ethertype: int = PROFINET_ETHERTYPE) -> bytes:
    """Build Ethernet header.

    Args:
        src: Source device context
        dst: Destination device context
        ethertype: EtherType (default PROFINET 0x8892)

    Returns:
        14-byte Ethernet header
    """
    dst_mac = bytes.fromhex(dst.mac_address.replace(":", "").replace("-", ""))
    src_mac = bytes.fromhex(src.mac_address.replace(":", "").replace("-", ""))
    return dst_mac + src_mac + struct.pack(">H", ethertype)


def build_vlan_header(vlan_id: int, priority: int = 6) -> bytes:
    """Build 802.1Q VLAN tag.

    Args:
        vlan_id: VLAN ID (1-4094)
        priority: Priority code point (0-7, default 6 for PROFINET RT)

    Returns:
        4-byte VLAN tag
    """
    tci = (priority << 13) | vlan_id
    return struct.pack(">HH", VLAN_ETHERTYPE, tci)


def build_rt_frame(
    frame_id: int,
    data: bytes,
    cycle_counter: int,
    data_status: int = 0x35,  # Primary, Run, Valid
    transfer_status: int = 0x00,
) -> bytes:
    """Build PROFINET RT (Real-Time) cyclic data frame.

    RT Frame structure:
    - Frame ID (2 bytes)
    - User Data (variable)
    - Cycle Counter (2 bytes)
    - Data Status (1 byte)
    - Transfer Status (1 byte)

    Args:
        frame_id: RT Frame ID (0x8000-0xFBFF for RT class 1/2)
        data: I/O data payload
        cycle_counter: Cycle counter (0-65535)
        data_status: Data status byte
        transfer_status: Transfer status byte

    Returns:
        Complete RT frame payload
    """
    frame = struct.pack(">H", frame_id)
    frame += data
    frame += struct.pack(">H", cycle_counter)
    frame += struct.pack("BB", data_status, transfer_status)
    return frame


def build_rt_packet(
    src: DeviceContext,
    dst: DeviceContext,
    frame_id: int,
    data: bytes,
    cycle_counter: int,
    data_status: int = 0x35,
    vlan_id: int | None = None,
) -> bytes:
    """Build complete PROFINET RT packet with Ethernet header.

    Args:
        src: Source device
        dst: Destination device
        frame_id: RT Frame ID
        data: I/O data payload
        cycle_counter: Cycle counter
        data_status: Data status
        vlan_id: Optional VLAN ID for tagged frames

    Returns:
        Complete Ethernet frame bytes
    """
    if vlan_id:
        # Tagged frame: Ether + VLAN + PROFINET
        eth_header = build_ethernet_header(src, dst, VLAN_ETHERTYPE)
        vlan_tag = struct.pack(">HH", vlan_id | 0xC000, PROFINET_ETHERTYPE)  # Priority 6
        rt_frame = build_rt_frame(frame_id, data, cycle_counter, data_status)
        return eth_header + vlan_tag + rt_frame
    else:
        # Untagged frame
        eth_header = build_ethernet_header(src, dst, PROFINET_ETHERTYPE)
        rt_frame = build_rt_frame(frame_id, data, cycle_counter, data_status)
        return eth_header + rt_frame


def build_dcp_header(
    service_id: int,
    service_type: int,
    xid: int,
    response_delay: int = 0,
    data_length: int = 0,
) -> bytes:
    """Build DCP header.

    DCP Header structure (10 bytes):
    - Service ID (1 byte)
    - Service Type (1 byte)
    - XID (4 bytes) - transaction ID
    - Response Delay Factor (2 bytes)
    - Data Length (2 bytes)

    Args:
        service_id: DCP service ID
        service_type: Request or response type
        xid: Transaction ID
        response_delay: Response delay factor
        data_length: Length of following data

    Returns:
        10-byte DCP header
    """
    return struct.pack(
        ">BBIHH",
        service_id,
        service_type,
        xid,
        response_delay,
        data_length,
    )


def build_dcp_block(
    option: int,
    suboption: int,
    data: bytes,
    block_info: int | None = None,
) -> bytes:
    """Build a single PROFINET DCP block.

    Per IEC 61158-6-10 §4.3.1.4, response blocks (and Set request blocks)
    contain a 2-byte BlockInfo / BlockQualifier field after BlockLength,
    BEFORE the block-specific data. BlockLength must include BlockInfo.

    Identify Request and Get Request blocks omit BlockInfo and pass
    `block_info=None` (the default).

    Wire format with BlockInfo (response blocks):

        +--------+-----------+-------------+-----------+--------+
        | Option | SubOption | BlockLength | BlockInfo | Data   |
        | 1B     | 1B        | 2B (= 2+N)  | 2B        | N B    |
        +--------+-----------+-------------+-----------+--------+

    Wire format without BlockInfo (request blocks):

        +--------+-----------+-------------+--------+
        | Option | SubOption | BlockLength | Data   |
        | 1B     | 1B        | 2B (= N)    | N B    |
        +--------+-----------+-------------+--------+

    The whole block is zero-padded to an even byte boundary.

    Args:
        option:     DCP option code (1 byte)
        suboption:  DCP suboption code (1 byte)
        data:       Block-specific data (excluding BlockInfo)
        block_info: Optional 2-byte BlockInfo qualifier. Most response blocks
                    pass 0 here. Some blocks (e.g. IP Parameter) pass a status
                    word (0x0001 = "IP set"). Request blocks pass None.

    Returns:
        DCP block bytes (4-byte header + optional 2-byte BlockInfo + data + pad).
    """
    if block_info is not None:
        full_data = struct.pack(">H", block_info) + data
    else:
        full_data = data

    block_length = len(full_data)
    block = struct.pack(">BBH", option, suboption, block_length) + full_data

    # Pad to even length so the next block starts on an even byte boundary
    if len(full_data) % 2 != 0:
        block += b"\x00"
    return block


def build_dcp_identify_request(xid: int) -> bytes:
    """Build DCP Identify Request (multicast).

    Args:
        xid: Transaction ID

    Returns:
        DCP Identify request payload
    """
    # Request all device information
    block = build_dcp_block(DCP_OPTION_ALL, 0xFF, b'')
    header = build_dcp_header(
        DCP_SERVICE_IDENTIFY,
        DCP_SERVICE_TYPE_REQUEST,
        xid,
        response_delay=1,  # Short delay
        data_length=len(block),
    )
    return header + block


def build_dcp_identify_response(
    xid: int,
    device_name: str,
    vendor_id: int,
    device_id: int,
    ip_address: str,
    subnet_mask: str = "255.255.255.0",
    gateway: str = "0.0.0.0",
) -> bytes:
    """Build DCP Identify Response.

    Args:
        xid: Transaction ID (from request)
        device_name: PROFINET device name (station name)
        vendor_id: Vendor ID
        device_id: Device ID
        ip_address: IP address
        subnet_mask: Subnet mask
        gateway: Default gateway

    Returns:
        DCP Identify response payload
    """
    blocks = b''

    # Device Name block
    name_data = device_name.encode('ascii')
    blocks += build_dcp_block(
        DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_NAME, name_data, block_info=0
    )

    # Device ID block (Vendor ID + Device ID)
    device_id_data = struct.pack(">HH", vendor_id, device_id)
    blocks += build_dcp_block(
        DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_ID, device_id_data, block_info=0
    )

    # IP Parameter block — BlockInfo for IP_PARAMETER is the IP-set status
    # word (0x0001 = "IP set"), not the generic 0x0000.
    ip_data = _ip_to_bytes(ip_address) + _ip_to_bytes(subnet_mask) + _ip_to_bytes(gateway)
    blocks += build_dcp_block(
        DCP_OPTION_IP, DCP_SUBOPTION_IP_PARAMETER, ip_data, block_info=0x0001
    )

    # Device Role block
    role_data = struct.pack(">BB", 0x01, 0x00)  # Device role: IO-Device
    blocks += build_dcp_block(
        DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_ROLE, role_data, block_info=0
    )

    header = build_dcp_header(
        DCP_SERVICE_IDENTIFY,
        DCP_SERVICE_TYPE_RESPONSE_SUCCESS,
        xid,
        response_delay=0,
        data_length=len(blocks),
    )
    return header + blocks


def build_dcp_identify_request_packet(
    src: DeviceContext,
    dst_mac: str = "01:0E:CF:00:00:00",  # PROFINET DCP multicast
) -> bytes:
    """Build complete DCP Identify Request packet.

    Args:
        src: Source device
        dst_mac: Destination MAC (default: PROFINET multicast)

    Returns:
        Complete Ethernet frame
    """
    # Create a dummy destination context for multicast
    dst = DeviceContext(
        device_id="multicast",
        mac_address=dst_mac,
        ip_address="0.0.0.0",
        port=0,
    )

    eth_header = build_ethernet_header(src, dst, PROFINET_ETHERTYPE)
    # Frame ID for DCP Identify Request
    frame_id = struct.pack(">H", FRAME_ID_DCP_IDENTIFY_REQ)
    dcp_payload = build_dcp_identify_request(xid=0x00000001)

    return eth_header + frame_id + dcp_payload


def build_dcp_identify_response_packet(
    src: DeviceContext,
    dst: DeviceContext,
    xid: int,
    device_name: str,
    vendor_id: int = 0x002A,  # Example vendor ID
    device_id: int = 0x0001,
) -> bytes:
    """Build complete DCP Identify Response packet.

    Args:
        src: Source device (responder)
        dst: Destination device (requester)
        xid: Transaction ID
        device_name: Device station name
        vendor_id: Vendor ID
        device_id: Device ID

    Returns:
        Complete Ethernet frame
    """
    eth_header = build_ethernet_header(src, dst, PROFINET_ETHERTYPE)
    frame_id = struct.pack(">H", FRAME_ID_DCP_IDENTIFY_RES)
    dcp_payload = build_dcp_identify_response(
        xid=xid,
        device_name=device_name,
        vendor_id=vendor_id,
        device_id=device_id,
        ip_address=src.ip_address,
    )

    return eth_header + frame_id + dcp_payload


def generate_io_data(data_size: int, pattern: str = "random") -> bytes:
    """Generate I/O data payload.

    Args:
        data_size: Size of I/O data in bytes
        pattern: Data pattern - "random", "zeros", "counter"

    Returns:
        I/O data bytes
    """
    import random

    if pattern == "zeros":
        return bytes(data_size)
    elif pattern == "counter":
        return bytes([i % 256 for i in range(data_size)])
    else:  # random
        return bytes([random.randint(0, 255) for _ in range(data_size)])


def _ip_to_bytes(ip: str) -> bytes:
    """Convert IP address string to 4 bytes."""
    parts = ip.split(".")
    return bytes([int(p) for p in parts])


# Data status bit definitions
class DataStatus:
    """PROFINET RT Data Status bits."""

    STATE_PRIMARY = 0x01      # Bit 0: Primary (1) / Backup (0)
    STATE_RUN = 0x04          # Bit 2: Run (1) / Stop (0)
    STATE_VALID = 0x10        # Bit 4: Valid (1) / Invalid (0)
    STATE_REDUNDANCY = 0x20   # Bit 5: Redundancy active
    STATE_PROBLEM = 0x40      # Bit 6: Problem indicator

    # Common combinations
    VALID_RUN_PRIMARY = 0x35  # Valid, Run, Primary
    VALID_STOP_PRIMARY = 0x31 # Valid, Stop, Primary
    INVALID = 0x00            # All zeros - invalid


# Transfer status definitions
class TransferStatus:
    """PROFINET RT Transfer Status."""

    OK = 0x00
    IGNORE = 0x40  # Substitute value should be used


# ========== Fingerprint-based Identity Functions ==========


def build_dcp_identify_response_fingerprinted(
    src: DeviceContext,
    xid: int,
) -> bytes:
    """Build DCP Identify Response using device fingerprint data.

    This function extracts PROFINET identity information from the device's
    fingerprint applicator to generate realistic vendor-specific responses.

    Args:
        src: Source device context (provides fingerprint)
        xid: Transaction ID (from request)

    Returns:
        DCP Identify response payload
    """
    applicator = src.fingerprint_applicator
    profinet_identity = applicator.profinet_identity

    # Get identity values from fingerprint
    # Support both naming conventions for compatibility
    device_name = profinet_identity.get("station_name", "device")
    vendor_id = profinet_identity.get("vendor_id", 0x002A)
    device_id = profinet_identity.get("device_id", 0x0001)
    device_role = profinet_identity.get("device_role", 0x01)  # IO-Device
    # Defensive normalization: device_role MUST be an int byte for struct.pack.
    # Some CVE / fingerprint overrides historically supplied string aliases
    # like "controller" or "io_device", which crashed the orchestrator with
    # "required argument is not an integer". Map the common aliases to their
    # PROFINET DCP role-byte values, fall back to IO-Device for anything else.
    if not isinstance(device_role, int):
        _ROLE_NAME_TO_BYTE = {
            "io_device": 0x01, "device": 0x01,
            "io_controller": 0x02, "controller": 0x02,
            "io_multidevice": 0x04, "multidevice": 0x04,
            "io_supervisor": 0x08, "supervisor": 0x08,
        }
        device_role = _ROLE_NAME_TO_BYTE.get(
            str(device_role).strip().lower(), 0x01
        )
    device_vendor = profinet_identity.get("device_vendor", "")
    # Support multiple key names for hardware/software versions
    hardware_revision = (
        profinet_identity.get("hardware_revision") or
        profinet_identity.get("hw_release") or
        profinet_identity.get("im0_hw_revision") or
        "1.0"
    )
    if isinstance(hardware_revision, int):
        hardware_revision = str(hardware_revision)
    # Support sw_release (CVE data), software_revision, im0_sw_revision (Siemens)
    software_revision = (
        profinet_identity.get("software_revision") or
        profinet_identity.get("sw_release") or
        profinet_identity.get("im0_sw_revision") or
        "V1.0"
    )
    order_id = profinet_identity.get("order_id") or profinet_identity.get("im0_order_id", "")
    serial_number = profinet_identity.get("serial_number") or profinet_identity.get("im0_serial_number", "")
    device_type = profinet_identity.get("device_type", "")

    blocks = b""

    # All DCP response blocks below carry the generic 2-byte BlockInfo
    # qualifier (0x0000) per IEC 61158-6-10 §4.3.1.4. The IP_PARAMETER
    # block uses 0x0001 ("IP set") as its block-specific BlockInfo.

    # Device Name block (required)
    name_data = device_name.encode("ascii")
    blocks += build_dcp_block(
        DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_NAME, name_data, block_info=0
    )

    # Device ID block - Vendor ID + Device ID (required)
    device_id_data = struct.pack(">HH", vendor_id, device_id)
    blocks += build_dcp_block(
        DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_ID, device_id_data, block_info=0
    )

    # Device Vendor block (if available)
    if device_vendor:
        vendor_data = device_vendor.encode("ascii")
        blocks += build_dcp_block(
            DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_VENDOR, vendor_data, block_info=0
        )

    # IP Parameter block — BlockInfo = 0x0001 ("IP set")
    ip_data = _ip_to_bytes(src.ip_address) + _ip_to_bytes("255.255.255.0") + _ip_to_bytes("0.0.0.0")
    blocks += build_dcp_block(
        DCP_OPTION_IP, DCP_SUBOPTION_IP_PARAMETER, ip_data, block_info=0x0001
    )

    # Device Role block
    role_data = struct.pack(">BB", device_role, 0x00)
    blocks += build_dcp_block(
        DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_ROLE, role_data, block_info=0
    )

    # Device Instance block (high/low instance)
    instance_high = profinet_identity.get("instance_high", 0x00)
    instance_low = profinet_identity.get("instance_low", 0x01)
    instance_data = struct.pack(">BB", instance_high, instance_low)
    blocks += build_dcp_block(
        DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_INSTANCE, instance_data, block_info=0
    )

    # Device Options block - indicates supported options AND contains version info
    # Format: List of (Option, Suboption) pairs + optional vendor-specific extensions
    # For Cyber Vision detection, we include software/hardware version strings
    if software_revision or hardware_revision:
        # Build Device Options data:
        # - Supported suboptions list (required)
        # - Software revision string (vendor extension for version detection)
        # Standard format: pairs of supported (option, suboption)
        options_data = struct.pack(
            ">BBBBBBBB",
            DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_VENDOR,     # Device Vendor
            DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_NAME,       # Device Name
            DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_ID,         # Device ID
            DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_ROLE,       # Device Role
        )
        blocks += build_dcp_block(
            DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_OPTIONS, options_data, block_info=0
        )

    # OEM Device ID block - Contains Order ID, Serial Number, Device Type, Version info
    # This is what Cyber Vision and other scanners use to identify vulnerable devices
    # Format: Typically vendor-specific, but commonly includes:
    # - Order ID (product order number like "6ES7 516-3AN01-0AB0")
    # - Serial Number
    # - Device Type name
    # - Hardware/Software revision
    if order_id or serial_number or device_type or software_revision:
        # Build OEM Device ID using structured format that scanners can parse
        # Format: null-terminated strings for each field
        oem_parts = []
        if order_id:
            oem_parts.append(f"OrderID:{order_id}")
        if serial_number:
            oem_parts.append(f"SN:{serial_number}")
        if device_type:
            oem_parts.append(f"Type:{device_type}")
        if hardware_revision:
            oem_parts.append(f"HW:{hardware_revision}")
        if software_revision:
            # This is the KEY field for CVE detection - firmware version
            oem_parts.append(f"SW:{software_revision}")

        oem_data = ";".join(oem_parts).encode("ascii")
        blocks += build_dcp_block(
            DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_OEM_ID, oem_data, block_info=0
        )

    # Device Initiative block - indicates device wants to be contacted
    # This helps ensure the device is included in network scans
    initiative_data = struct.pack(">H", 0x0001)  # 0x0001 = Device wants initiative
    blocks += build_dcp_block(
        DCP_OPTION_DEVICE_INITIATIVE,
        DCP_SUBOPTION_DEVICE_INITIATIVE_VALUE,
        initiative_data,
        block_info=0,
    )

    header = build_dcp_header(
        DCP_SERVICE_IDENTIFY,
        DCP_SERVICE_TYPE_RESPONSE_SUCCESS,
        xid,
        response_delay=0,
        data_length=len(blocks),
    )
    return header + blocks


def build_dcp_identify_response_packet_fingerprinted(
    src: DeviceContext,
    dst: DeviceContext,
    xid: int,
) -> bytes:
    """Build complete DCP Identify Response packet using fingerprint.

    Args:
        src: Source device (responder with fingerprint)
        dst: Destination device (requester)
        xid: Transaction ID

    Returns:
        Complete Ethernet frame
    """
    eth_header = build_ethernet_header(src, dst, PROFINET_ETHERTYPE)
    frame_id = struct.pack(">H", FRAME_ID_DCP_IDENTIFY_RES)
    dcp_payload = build_dcp_identify_response_fingerprinted(src, xid)

    return eth_header + frame_id + dcp_payload


def build_dcp_get_set_response(
    xid: int,
    option: int,
    suboption: int,
    data: bytes,
    success: bool = True,
) -> bytes:
    """Build DCP Get/Set Response.

    Args:
        xid: Transaction ID
        option: DCP option
        suboption: DCP suboption
        data: Response data
        success: Whether operation succeeded

    Returns:
        DCP response payload
    """
    service_type = DCP_SERVICE_TYPE_RESPONSE_SUCCESS if success else DCP_SERVICE_TYPE_RESPONSE_NOT_SUPPORTED
    # Get/Set responses are response blocks → carry generic BlockInfo (0).
    block = build_dcp_block(option, suboption, data, block_info=0)

    header = build_dcp_header(
        DCP_SERVICE_GET,
        service_type,
        xid,
        response_delay=0,
        data_length=len(block),
    )
    return header + block


# ========== RTA (Real-Time Acyclic) Alarm Functions ==========


# RTA Service IDs
RTA_SERVICE_DATA = 0x01
RTA_SERVICE_ACK = 0x02
RTA_SERVICE_NACK = 0x03

# Alarm Types
ALARM_TYPE_DIAGNOSTIC = 0x0001
ALARM_TYPE_PROCESS = 0x0002
ALARM_TYPE_PULL = 0x0003
ALARM_TYPE_PLUG = 0x0004
ALARM_TYPE_STATUS = 0x0005
ALARM_TYPE_UPDATE = 0x0006
ALARM_TYPE_RETURN_OF_SUBMODULE = 0x000E
ALARM_TYPE_CONTROLLED_BY_SUPERVISOR = 0x000F
ALARM_TYPE_UPLOAD_AND_STORAGE = 0x0020


def build_rta_alarm_header(
    alarm_dst_endpoint: int,
    alarm_src_endpoint: int,
    send_seq_num: int,
    ack_seq_num: int,
) -> bytes:
    """Build RTA PDU header.

    Args:
        alarm_dst_endpoint: Destination AR endpoint
        alarm_src_endpoint: Source AR endpoint
        send_seq_num: Send sequence number
        ack_seq_num: Acknowledge sequence number

    Returns:
        RTA header bytes
    """
    return struct.pack(
        ">HHBBBB",
        alarm_dst_endpoint,
        alarm_src_endpoint,
        0x00,  # PDU type and version
        0x01,  # AddFlags
        send_seq_num,
        ack_seq_num,
    )


def build_alarm_notification(
    alarm_type: int,
    api: int,
    slot_number: int,
    subslot_number: int,
    alarm_specifier: int = 0x0001,
    user_data: bytes = b"",
) -> bytes:
    """Build Alarm Notification PDU.

    Args:
        alarm_type: Type of alarm
        api: Application Process Identifier
        slot_number: Slot number
        subslot_number: Subslot number
        alarm_specifier: Alarm specifier flags
        user_data: Additional alarm data

    Returns:
        Alarm notification bytes
    """
    return struct.pack(
        ">HIHHH",
        alarm_type,
        api,
        slot_number,
        subslot_number,
        alarm_specifier,
    ) + user_data


def build_rta_alarm_packet(
    src: DeviceContext,
    dst: DeviceContext,
    alarm_type: int,
    slot_number: int,
    subslot_number: int,
    send_seq_num: int = 1,
    ack_seq_num: int = 0,
    vlan_id: int | None = None,
) -> bytes:
    """Build complete RTA alarm packet.

    Args:
        src: Source device
        dst: Destination device
        alarm_type: Type of alarm
        slot_number: Slot number
        subslot_number: Subslot number
        send_seq_num: Send sequence number
        ack_seq_num: Acknowledge sequence number
        vlan_id: Optional VLAN ID

    Returns:
        Complete Ethernet frame
    """
    # Build alarm notification
    alarm_notif = build_alarm_notification(
        alarm_type=alarm_type,
        api=0,  # Default API
        slot_number=slot_number,
        subslot_number=subslot_number,
    )

    # Build RTA header
    rta_header = build_rta_alarm_header(
        alarm_dst_endpoint=0x0001,
        alarm_src_endpoint=0x0001,
        send_seq_num=send_seq_num,
        ack_seq_num=ack_seq_num,
    )

    rta_pdu = rta_header + alarm_notif

    # Build Ethernet frame
    if vlan_id:
        eth_header = build_ethernet_header(src, dst, VLAN_ETHERTYPE)
        vlan_tag = struct.pack(">HH", vlan_id | 0xC000, PROFINET_ETHERTYPE)
        frame_id = struct.pack(">H", FRAME_ID_RTA)
        return eth_header + vlan_tag + frame_id + rta_pdu
    else:
        eth_header = build_ethernet_header(src, dst, PROFINET_ETHERTYPE)
        frame_id = struct.pack(">H", FRAME_ID_RTA)
        return eth_header + frame_id + rta_pdu


def build_rta_alarm_ack_packet(
    src: DeviceContext,
    dst: DeviceContext,
    send_seq_num: int,
    ack_seq_num: int,
    vlan_id: int | None = None,
) -> bytes:
    """Build RTA alarm acknowledgment packet.

    Args:
        src: Source device
        dst: Destination device
        send_seq_num: Send sequence number
        ack_seq_num: Acknowledge sequence number (should match received send_seq)
        vlan_id: Optional VLAN ID

    Returns:
        Complete Ethernet frame
    """
    # Build minimal ACK RTA header
    rta_header = build_rta_alarm_header(
        alarm_dst_endpoint=0x0001,
        alarm_src_endpoint=0x0001,
        send_seq_num=send_seq_num,
        ack_seq_num=ack_seq_num,
    )

    # ACK has minimal payload
    rta_pdu = rta_header + struct.pack(">H", 0x0000)  # Empty alarm specifier

    # Build Ethernet frame
    if vlan_id:
        eth_header = build_ethernet_header(src, dst, VLAN_ETHERTYPE)
        vlan_tag = struct.pack(">HH", vlan_id | 0xC000, PROFINET_ETHERTYPE)
        frame_id = struct.pack(">H", FRAME_ID_RTA)
        return eth_header + vlan_tag + frame_id + rta_pdu
    else:
        eth_header = build_ethernet_header(src, dst, PROFINET_ETHERTYPE)
        frame_id = struct.pack(">H", FRAME_ID_RTA)
        return eth_header + frame_id + rta_pdu


# =============================================================================
# PROFINET IRT (Isochronous Real-Time) Functions
# =============================================================================


def validate_irt_frame_id(frame_id: int) -> bool:
    """Validate that frame ID is in IRT range.

    Args:
        frame_id: Frame ID to validate

    Returns:
        True if frame ID is valid for IRT
    """
    return IRT_FRAME_ID_MIN <= frame_id <= IRT_FRAME_ID_MAX


def allocate_irt_frame_id(slot: int, subslot: int, direction: str = "output") -> int:
    """Allocate an IRT frame ID based on slot/subslot configuration.

    IRT frame IDs are typically assigned based on:
    - Slot number
    - Subslot number
    - Data direction (input/output)

    Args:
        slot: Slot number (0-255)
        subslot: Subslot number (0-255)
        direction: "output" (controller->device) or "input" (device->controller)

    Returns:
        IRT frame ID in range 0x0100-0x7FFF
    """
    # Simple allocation scheme: base + slot * 256 + subslot * 2 + direction
    base = IRT_FRAME_ID_MIN
    direction_offset = 0 if direction == "output" else 1

    frame_id = base + (slot * 256) + (subslot * 2) + direction_offset

    # Ensure within valid range
    if frame_id > IRT_FRAME_ID_MAX:
        frame_id = IRT_FRAME_ID_MIN + ((frame_id - IRT_FRAME_ID_MIN) % (IRT_FRAME_ID_MAX - IRT_FRAME_ID_MIN))

    return frame_id


def build_irt_frame(
    frame_id: int,
    data: bytes,
    cycle_counter: int,
    data_status: int = 0x35,  # Primary, Run, Valid
    transfer_status: int = 0x00,
) -> bytes:
    """Build PROFINET IRT (RT Class 3) cyclic data frame.

    IRT frames have the same structure as RT frames but use
    frame IDs in the range 0x0100-0x7FFF and require precise timing.

    Args:
        frame_id: IRT Frame ID (0x0100-0x7FFF)
        data: I/O data payload
        cycle_counter: Cycle counter (0-65535)
        data_status: Data status byte
        transfer_status: Transfer status byte

    Returns:
        Complete IRT frame payload

    Raises:
        ValueError: If frame_id is not in IRT range
    """
    if not validate_irt_frame_id(frame_id):
        raise ValueError(f"Invalid IRT frame ID: {frame_id:#06x}. Must be in range {IRT_FRAME_ID_MIN:#06x}-{IRT_FRAME_ID_MAX:#06x}")

    return build_rt_frame(frame_id, data, cycle_counter, data_status, transfer_status)


def build_irt_packet(
    src: DeviceContext,
    dst: DeviceContext,
    frame_id: int,
    data: bytes,
    cycle_counter: int,
    data_status: int = 0x35,
    vlan_id: int = 0,
    priority: int = 6,
) -> bytes:
    """Build complete PROFINET IRT packet with VLAN tag.

    IRT packets require VLAN tagging with priority 6 for proper
    switch handling in IRT-capable infrastructure.

    Args:
        src: Source device
        dst: Destination device
        frame_id: IRT Frame ID (0x0100-0x7FFF)
        data: I/O data payload
        cycle_counter: Cycle counter
        data_status: Data status
        vlan_id: VLAN ID (required for IRT)
        priority: VLAN priority (default 6 for IRT)

    Returns:
        Complete Ethernet frame bytes
    """
    # IRT always uses VLAN tagging
    eth_header = build_ethernet_header(src, dst, VLAN_ETHERTYPE)
    vlan_tag = build_vlan_header(vlan_id, priority)
    # Add PROFINET EtherType after VLAN
    profinet_type = struct.pack(">H", PROFINET_ETHERTYPE)
    irt_frame = build_irt_frame(frame_id, data, cycle_counter, data_status)

    return eth_header + vlan_tag + profinet_type + irt_frame


def build_ptcp_sync_frame(
    src: DeviceContext,
    dst: DeviceContext,
    sequence_id: int,
    delay_ns: int,
    subdomain_uuid: bytes,
    master_source_address: bytes | None = None,
    vlan_id: int = 0,
) -> bytes:
    """Build PTCP (Precision Time Clock Protocol) Sync frame.

    PTCP Sync frames are used to synchronize clocks in IRT networks.
    They are sent by the sync master to all devices.

    Args:
        src: Source device (sync master)
        dst: Destination device (multicast for sync)
        sequence_id: Sync sequence ID (0-65535)
        delay_ns: Current delay value in nanoseconds
        subdomain_uuid: PTCP subdomain UUID (16 bytes)
        master_source_address: Sync master source address (6 bytes)
        vlan_id: VLAN ID

    Returns:
        Complete PTCP Sync frame bytes
    """
    # PTCP Sync destination is multicast: 01:0E:CF:00:04:40
    dst_mac = bytes.fromhex("010ECF000440")
    src_mac = bytes.fromhex(src.mac_address.replace(":", "").replace("-", ""))

    # Ethernet header
    eth_header = dst_mac + src_mac + struct.pack(">H", VLAN_ETHERTYPE)
    vlan_tag = build_vlan_header(vlan_id, priority=6)
    profinet_type = struct.pack(">H", PROFINET_ETHERTYPE)

    # Frame ID for PTCP Sync
    frame_id = struct.pack(">H", FRAME_ID_PTCP_SYNC)

    # PTCP Sync PDU
    # - Subdomain UUID (16 bytes)
    # - Master Source Address (6 bytes)
    # - Sequence ID (2 bytes)
    # - Delay (8 bytes - nanoseconds)
    # - Epoch Number (2 bytes)
    # - Current UTC Offset (2 bytes)
    # - Flags (1 byte)
    # - Padding (1 byte)

    if master_source_address is None:
        master_source_address = src_mac

    ptcp_pdu = subdomain_uuid[:16].ljust(16, b'\x00')
    ptcp_pdu += master_source_address[:6].ljust(6, b'\x00')
    ptcp_pdu += struct.pack(">H", sequence_id)
    ptcp_pdu += struct.pack(">Q", delay_ns)  # 8-byte delay in ns
    ptcp_pdu += struct.pack(">HHB", 0, 0, 0)  # Epoch, UTC offset, flags
    ptcp_pdu += b'\x00'  # Padding

    return eth_header + vlan_tag + profinet_type + frame_id + ptcp_pdu


def build_ptcp_followup_frame(
    src: DeviceContext,
    dst: DeviceContext,
    sequence_id: int,
    precise_timestamp_ns: int,
    subdomain_uuid: bytes,
    vlan_id: int = 0,
) -> bytes:
    """Build PTCP FollowUp frame.

    FollowUp frames contain the precise timestamp of when the
    corresponding Sync frame was actually transmitted.

    Args:
        src: Source device (sync master)
        dst: Destination device
        sequence_id: Must match corresponding Sync frame
        precise_timestamp_ns: Precise send time of Sync in nanoseconds
        subdomain_uuid: PTCP subdomain UUID
        vlan_id: VLAN ID

    Returns:
        Complete PTCP FollowUp frame bytes
    """
    # PTCP FollowUp destination is multicast
    dst_mac = bytes.fromhex("010ECF000440")
    src_mac = bytes.fromhex(src.mac_address.replace(":", "").replace("-", ""))

    eth_header = dst_mac + src_mac + struct.pack(">H", VLAN_ETHERTYPE)
    vlan_tag = build_vlan_header(vlan_id, priority=6)
    profinet_type = struct.pack(">H", PROFINET_ETHERTYPE)

    frame_id = struct.pack(">H", FRAME_ID_PTCP_FOLLOWUP)

    # PTCP FollowUp PDU
    ptcp_pdu = subdomain_uuid[:16].ljust(16, b'\x00')
    ptcp_pdu += struct.pack(">H", sequence_id)
    ptcp_pdu += struct.pack(">Q", precise_timestamp_ns)  # Precise timestamp
    ptcp_pdu += struct.pack(">HH", 0, 0)  # Reserved fields

    return eth_header + vlan_tag + profinet_type + frame_id + ptcp_pdu


def build_ptcp_delay_request(
    src: DeviceContext,
    dst: DeviceContext,
    sequence_id: int,
    vlan_id: int = 0,
) -> bytes:
    """Build PTCP Delay Request frame.

    Delay requests are sent from devices to the sync master to
    measure the line delay.

    Args:
        src: Source device (requesting device)
        dst: Destination device (sync master)
        sequence_id: Request sequence ID
        vlan_id: VLAN ID

    Returns:
        Complete PTCP Delay Request frame bytes
    """
    eth_header = build_ethernet_header(src, dst, VLAN_ETHERTYPE)
    vlan_tag = build_vlan_header(vlan_id, priority=6)
    profinet_type = struct.pack(">H", PROFINET_ETHERTYPE)

    frame_id = struct.pack(">H", FRAME_ID_PTCP_DELAY_REQ)

    # Minimal Delay Request PDU
    ptcp_pdu = struct.pack(">H", sequence_id)
    ptcp_pdu += bytes(14)  # Reserved/padding

    return eth_header + vlan_tag + profinet_type + frame_id + ptcp_pdu


def build_ptcp_delay_response(
    src: DeviceContext,
    dst: DeviceContext,
    sequence_id: int,
    request_receipt_timestamp_ns: int,
    response_origin_timestamp_ns: int,
    vlan_id: int = 0,
) -> bytes:
    """Build PTCP Delay Response frame.

    Delay responses are sent by the sync master in response to
    Delay Requests, containing timestamps for delay calculation.

    Args:
        src: Source device (sync master)
        dst: Destination device (requesting device)
        sequence_id: Must match Delay Request
        request_receipt_timestamp_ns: When request was received
        response_origin_timestamp_ns: When response is sent
        vlan_id: VLAN ID

    Returns:
        Complete PTCP Delay Response frame bytes
    """
    eth_header = build_ethernet_header(src, dst, VLAN_ETHERTYPE)
    vlan_tag = build_vlan_header(vlan_id, priority=6)
    profinet_type = struct.pack(">H", PROFINET_ETHERTYPE)

    frame_id = struct.pack(">H", FRAME_ID_PTCP_DELAY_RES)

    # Delay Response PDU
    ptcp_pdu = struct.pack(">H", sequence_id)
    ptcp_pdu += struct.pack(">Q", request_receipt_timestamp_ns)
    ptcp_pdu += struct.pack(">Q", response_origin_timestamp_ns)
    ptcp_pdu += bytes(4)  # Padding

    return eth_header + vlan_tag + profinet_type + frame_id + ptcp_pdu


class IRTCycleState:
    """Tracks IRT cycle state for a single connection.

    Extends RTCycleState with IRT-specific timing information.
    """

    def __init__(
        self,
        frame_id_output: int,
        frame_id_input: int,
        output_data_size: int,
        input_data_size: int,
        cycle_time_us: int = 250,  # Cycle time in microseconds
        send_clock_factor: int = 32,  # Send clock factor
        reduction_ratio: int = 1,  # Reduction ratio
        phase: int = 0,  # Phase within cycle
    ):
        """Initialize IRT cycle state.

        Args:
            frame_id_output: Frame ID for output (controller -> device)
            frame_id_input: Frame ID for input (device -> controller)
            output_data_size: Size of output data in bytes
            input_data_size: Size of input data in bytes
            cycle_time_us: Cycle time in microseconds (typical: 250, 500, 1000)
            send_clock_factor: Clock multiplication factor (typical: 32)
            reduction_ratio: Reduction ratio for slower devices
            phase: Phase offset within cycle (0-based)
        """
        # Validate frame IDs are in IRT range
        if not validate_irt_frame_id(frame_id_output):
            raise ValueError(f"Output frame ID {frame_id_output:#06x} not in IRT range")
        if not validate_irt_frame_id(frame_id_input):
            raise ValueError(f"Input frame ID {frame_id_input:#06x} not in IRT range")

        self.frame_id_output = frame_id_output
        self.frame_id_input = frame_id_input
        self.output_data_size = output_data_size
        self.input_data_size = input_data_size
        self.cycle_time_us = cycle_time_us
        self.send_clock_factor = send_clock_factor
        self.reduction_ratio = reduction_ratio
        self.phase = phase

        # State tracking
        self.cycle_counter = 0
        self.output_data: bytes = bytes(output_data_size)
        self.input_data: bytes = bytes(input_data_size)
        self.data_status = 0x35  # Valid, Run, Primary

        # IRT-specific timing
        self.sync_sequence_id = 0
        self.last_sync_timestamp_ns = 0
        self.is_synchronized = False

    def increment_cycle(self) -> int:
        """Increment cycle counter and return new value."""
        self.cycle_counter = (self.cycle_counter + 1) % 65536
        return self.cycle_counter

    def get_cycle_time_ns(self) -> int:
        """Get cycle time in nanoseconds."""
        return self.cycle_time_us * 1000

    def get_effective_cycle_time_ns(self) -> int:
        """Get effective cycle time accounting for reduction ratio."""
        return self.cycle_time_us * 1000 * self.reduction_ratio

    def update_output_data(self, data: bytes) -> None:
        """Update output data buffer."""
        if len(data) == self.output_data_size:
            self.output_data = data
        else:
            self.output_data = (data + bytes(self.output_data_size))[:self.output_data_size]

    def update_input_data(self, data: bytes) -> None:
        """Update input data buffer."""
        if len(data) == self.input_data_size:
            self.input_data = data
        else:
            self.input_data = (data + bytes(self.input_data_size))[:self.input_data_size]

    def synchronize(self, sync_timestamp_ns: int, sequence_id: int) -> None:
        """Update synchronization state from PTCP Sync.

        Args:
            sync_timestamp_ns: Timestamp from Sync frame
            sequence_id: Sync sequence ID
        """
        self.last_sync_timestamp_ns = sync_timestamp_ns
        self.sync_sequence_id = sequence_id
        self.is_synchronized = True

    def get_send_time_offset_ns(self) -> int:
        """Get send time offset within cycle based on phase.

        IRT frames are sent at precise times within the cycle.
        The phase determines the offset from cycle start.

        Returns:
            Offset in nanoseconds from cycle start
        """
        # Simple linear phase offset within red phase
        phase_duration_ns = self.get_cycle_time_ns() // 4  # Red phase is ~25% of cycle
        return (self.phase * phase_duration_ns) // 256  # Phase is 0-255


# =============================================================================
# PROFINET RPC — Application Relationship (AR) Establishment
# =============================================================================
#
# Real PROFINET uses DCE/RPC over UDP (port 34964) for AR setup:
#   1. Connect Request/Response  — negotiate AR, allocate IOCRs
#   2. Write Request/Response    — download parameters to device
#   3. Control Request/Response  — signal "Application Ready"
#
# After Control, the device transitions to cyclic RT data exchange.
# =============================================================================

# DCE/RPC constants for PROFINET
PNIO_RPC_PORT = 34964
PNIO_INTERFACE_UUID = uuid.UUID("dea00001-6c97-11d1-8271-00a02442df7d")
PNIO_OBJECT_UUID = uuid.UUID("dea00000-6c97-11d1-8271-00a02442df7d")

# DCE/RPC PDU types
RPC_REQUEST = 0x00
RPC_RESPONSE = 0x02

# PROFINET RPC operation numbers
PNIO_OPNUM_CONNECT = 0x0000
PNIO_OPNUM_RELEASE = 0x0001
PNIO_OPNUM_READ = 0x0002
PNIO_OPNUM_WRITE = 0x0003
PNIO_OPNUM_CONTROL = 0x0004

# PROFINET block types
BLOCK_TYPE_AR_REQ = 0x0101
BLOCK_TYPE_AR_RES = 0x8101
BLOCK_TYPE_IOCR_REQ = 0x0102
BLOCK_TYPE_IOCR_RES = 0x8102
BLOCK_TYPE_EXPECTED_SUBMODULE = 0x0104
BLOCK_TYPE_MODULE_DIFF = 0x8104
BLOCK_TYPE_IOD_WRITE_REQ = 0x0008
BLOCK_TYPE_IOD_WRITE_RES = 0x8008
BLOCK_TYPE_IOD_CONTROL_REQ = 0x0110
BLOCK_TYPE_IOD_CONTROL_RES = 0x8110

# AR types
AR_TYPE_IOCR = 0x0001  # IO Controller AR


def _build_rpc_header(
    pdu_type: int,
    opnum: int,
    activity_uuid: bytes,
    body_length: int,
    fragment_num: int = 0,
    serial_high: int = 0,
    serial_low: int = 0,
) -> bytes:
    """Build a DCE/RPC PDU header (80 bytes) for PROFINET.

    Uses the connectionless (CL) variant of DCE/RPC over UDP.

    Args:
        pdu_type: RPC_REQUEST or RPC_RESPONSE
        opnum: PROFINET operation number
        activity_uuid: Activity UUID (16 bytes)
        body_length: Length of the RPC body
        fragment_num: Fragment number (0 for unfragmented)
        serial_high: High byte of serial number
        serial_low: Low byte of serial number

    Returns:
        80-byte DCE/RPC header
    """
    header = struct.pack(
        "BBBB",
        0x04,           # RPC version
        0x00,           # Packet type (overridden below)
        0x20,           # Flags1: idempotent
        0x00,           # Flags2
    )
    header = header[:1] + struct.pack("B", pdu_type) + header[2:]

    # Data representation (little-endian, ASCII, IEEE float)
    header += struct.pack("<BBH", 0x10, 0x00, 0x00)

    # Serial high
    header += struct.pack("B", serial_high)

    # Object UUID (PROFINET IO)
    header += PNIO_OBJECT_UUID.bytes_le

    # Interface UUID
    header += PNIO_INTERFACE_UUID.bytes_le

    # Activity UUID
    header += activity_uuid[:16].ljust(16, b"\x00")

    # Server boot time (0 for client requests)
    header += struct.pack("<I", 0)

    # Interface version (1.0)
    header += struct.pack("<I", 0x00000001)

    # Sequence number, operation number, interface hint, activity hint
    header += struct.pack("<IHHH", 0, opnum, 0xFFFF, 0xFFFF)

    # Fragment length = body length, fragment number
    header += struct.pack("<HH", body_length, fragment_num)

    # Auth protocol (0 = none), serial low
    header += struct.pack("BB", 0x00, serial_low)

    return header


def _build_pnio_block_header(block_type: int, data_length: int, version: int = 0x0100) -> bytes:
    """Build a PROFINET block header (6 bytes).

    Args:
        block_type: Block type code
        data_length: Length of block data (excluding this 6-byte header)
        version: Block version (default 1.0)

    Returns:
        6-byte block header
    """
    return struct.pack(">HHH", block_type, data_length + 2, version)


def _build_udp_packet(
    src: DeviceContext,
    dst: DeviceContext,
    payload: bytes,
    src_port: int,
    dst_port: int = PNIO_RPC_PORT,
) -> bytes:
    """Build a raw Ethernet/IP/UDP packet for RPC.

    Args:
        src: Source device context
        dst: Destination device context
        payload: UDP payload (DCE/RPC PDU)
        src_port: Source UDP port
        dst_port: Destination UDP port

    Returns:
        Complete packet bytes
    """
    from scapy.layers.inet import IP, UDP
    from scapy.layers.l2 import Ether
    from scapy.packet import Raw

    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address, ttl=64)
        / UDP(sport=src_port, dport=dst_port)
        / Raw(load=payload)
    )
    return bytes(packet)


def build_rpc_connect_request(
    src: DeviceContext,
    dst: DeviceContext,
    ar_uuid: bytes,
    session_key: int,
    src_port: int = 49152,
) -> bytes:
    """Build PROFINET RPC Connect Request (controller → device).

    Establishes an Application Relationship by negotiating AR
    parameters and I/O Communication Relations (IOCRs).

    Args:
        src: Source device (IO controller)
        dst: Destination device (IO device)
        ar_uuid: Application Relationship UUID (16 bytes)
        session_key: Session key for this AR
        src_port: Source UDP port (ephemeral)

    Returns:
        Complete UDP packet bytes
    """
    # AR block request
    src_mac = bytes.fromhex(src.mac_address.replace(":", "").replace("-", ""))
    ar_block = _build_pnio_block_header(BLOCK_TYPE_AR_REQ, 52)
    ar_block += struct.pack(">H", AR_TYPE_IOCR)               # AR type
    ar_block += ar_uuid[:16]                                    # AR UUID
    ar_block += struct.pack(">H", session_key)                  # Session key
    ar_block += src_mac                                         # CM initiator MAC
    ar_block += PNIO_OBJECT_UUID.bytes[:16]                     # CM initiator object UUID
    # AR properties: supervisor takeover allowed, parameterization server
    ar_block += struct.pack(">I", 0x00000001)
    # Timeout factor (100ms * factor)
    ar_block += struct.pack(">H", 100)
    # Padding
    ar_block += struct.pack(">H", 0)

    # IOCR block (simplified — one output CR)
    iocr_block = _build_pnio_block_header(BLOCK_TYPE_IOCR_REQ, 28)
    iocr_block += struct.pack(">H", 0x0001)   # IOCR type: Input CR
    iocr_block += struct.pack(">H", 0x0001)   # IOCR reference
    iocr_block += struct.pack(">H", 0x8000)   # Frame ID for RT class 1
    iocr_block += struct.pack(">H", 0x0020)   # SendClockFactor (32)
    iocr_block += struct.pack(">H", 0x0001)   # ReductionRatio
    iocr_block += struct.pack(">H", 0x0001)   # Phase
    iocr_block += struct.pack(">I", 0x00000000)  # Frame send offset
    iocr_block += struct.pack(">H", 0x0003)   # Watchdog factor
    iocr_block += struct.pack(">H", 40)       # Data length
    iocr_block += struct.pack(">H", 0x8892)   # Frame ID

    # Expected submodule block (simplified — slot 0, subslot 1)
    submod_block = _build_pnio_block_header(BLOCK_TYPE_EXPECTED_SUBMODULE, 16)
    submod_block += struct.pack(">H", 1)       # Number of APIs
    submod_block += struct.pack(">I", 0)       # API 0
    submod_block += struct.pack(">H", 1)       # Number of submodules
    submod_block += struct.pack(">HHI", 0x0001, 0x0001, 0x00000001)  # Slot, subslot, submodule ID

    body = ar_block + iocr_block + submod_block
    activity_uuid = uuid.uuid4().bytes
    rpc_header = _build_rpc_header(RPC_REQUEST, PNIO_OPNUM_CONNECT, activity_uuid, len(body))

    return _build_udp_packet(src, dst, rpc_header + body, src_port)


def build_rpc_connect_response(
    src: DeviceContext,
    dst: DeviceContext,
    ar_uuid: bytes,
    session_key: int,
    activity_uuid: bytes | None = None,
    dst_port: int = 49152,
) -> bytes:
    """Build PROFINET RPC Connect Response (device → controller).

    Confirms AR establishment and returns allocated IOCR parameters.

    Args:
        src: Source device (IO device)
        dst: Destination device (IO controller)
        ar_uuid: Application Relationship UUID
        session_key: Session key
        activity_uuid: Activity UUID from request (or random)
        dst_port: Destination UDP port (controller's ephemeral port)

    Returns:
        Complete UDP packet bytes
    """
    # AR response block
    src_mac = bytes.fromhex(src.mac_address.replace(":", "").replace("-", ""))
    ar_res = _build_pnio_block_header(BLOCK_TYPE_AR_RES, 52)
    ar_res += struct.pack(">H", AR_TYPE_IOCR)
    ar_res += ar_uuid[:16]
    ar_res += struct.pack(">H", session_key)
    ar_res += src_mac
    ar_res += PNIO_OBJECT_UUID.bytes[:16]
    ar_res += struct.pack(">I", 0x00000001)   # AR properties
    ar_res += struct.pack(">H", 100)          # Timeout factor
    ar_res += struct.pack(">H", 0)

    # IOCR response block
    iocr_res = _build_pnio_block_header(BLOCK_TYPE_IOCR_RES, 8)
    iocr_res += struct.pack(">H", 0x0001)     # IOCR reference
    iocr_res += struct.pack(">H", 0x8000)     # Frame ID
    iocr_res += struct.pack(">H", 0x0000)     # Status: OK
    iocr_res += struct.pack(">H", 0x0000)     # Padding

    # Module diff block (empty — all modules match)
    diff_block = _build_pnio_block_header(BLOCK_TYPE_MODULE_DIFF, 6)
    diff_block += struct.pack(">H", 1)         # Number of APIs
    diff_block += struct.pack(">I", 0)         # API 0

    body = ar_res + iocr_res + diff_block
    if activity_uuid is None:
        activity_uuid = uuid.uuid4().bytes
    rpc_header = _build_rpc_header(RPC_RESPONSE, PNIO_OPNUM_CONNECT, activity_uuid, len(body))

    return _build_udp_packet(src, dst, rpc_header + body, PNIO_RPC_PORT, dst_port)


def build_rpc_write_request(
    src: DeviceContext,
    dst: DeviceContext,
    ar_uuid: bytes,
    session_key: int,
    src_port: int = 49152,
) -> bytes:
    """Build PROFINET RPC Write Request (controller → device).

    Downloads parameterization data to the device after AR is connected.

    Args:
        src: Source device (IO controller)
        dst: Destination device (IO device)
        ar_uuid: AR UUID
        session_key: Session key
        src_port: Source UDP port

    Returns:
        Complete UDP packet bytes
    """
    # IODWriteMultipleReq block (simplified — one write record)
    write_block = _build_pnio_block_header(BLOCK_TYPE_IOD_WRITE_REQ, 44)
    write_block += struct.pack(">H", 0x0001)         # Sequence number
    write_block += ar_uuid[:16]                       # AR UUID
    write_block += struct.pack(">I", 0)               # API
    write_block += struct.pack(">HH", 0x0000, 0x0001) # Slot, subslot
    write_block += struct.pack(">H", 0x8000)          # Index (device-specific)
    write_block += struct.pack(">I", 4)               # Record data length
    write_block += struct.pack(">I", 0x00000001)      # Parameterization data

    body = write_block
    activity_uuid = uuid.uuid4().bytes
    rpc_header = _build_rpc_header(RPC_REQUEST, PNIO_OPNUM_WRITE, activity_uuid, len(body))

    return _build_udp_packet(src, dst, rpc_header + body, src_port)


def build_rpc_write_response(
    src: DeviceContext,
    dst: DeviceContext,
    ar_uuid: bytes,
    dst_port: int = 49152,
) -> bytes:
    """Build PROFINET RPC Write Response (device → controller).

    Confirms parameter download.

    Args:
        src: Source device (IO device)
        dst: Destination device (IO controller)
        ar_uuid: AR UUID
        dst_port: Destination UDP port

    Returns:
        Complete UDP packet bytes
    """
    write_res = _build_pnio_block_header(BLOCK_TYPE_IOD_WRITE_RES, 36)
    write_res += struct.pack(">H", 0x0001)             # Sequence number
    write_res += ar_uuid[:16]                           # AR UUID
    write_res += struct.pack(">I", 0)                   # API
    write_res += struct.pack(">HH", 0x0000, 0x0001)    # Slot, subslot
    write_res += struct.pack(">H", 0x8000)              # Index
    write_res += struct.pack(">I", 0x00000000)          # Status: OK

    body = write_res
    activity_uuid = uuid.uuid4().bytes
    rpc_header = _build_rpc_header(RPC_RESPONSE, PNIO_OPNUM_WRITE, activity_uuid, len(body))

    return _build_udp_packet(src, dst, rpc_header + body, PNIO_RPC_PORT, dst_port)


def build_rpc_control_request(
    src: DeviceContext,
    dst: DeviceContext,
    ar_uuid: bytes,
    session_key: int,
    src_port: int = 49152,
) -> bytes:
    """Build PROFINET RPC Control Request — ApplicationReady (controller → device).

    Signals the device that parameterization is complete and it should
    transition to cyclic data exchange.

    Args:
        src: Source device (IO controller)
        dst: Destination device (IO device)
        ar_uuid: AR UUID
        session_key: Session key
        src_port: Source UDP port

    Returns:
        Complete UDP packet bytes
    """
    ctrl_block = _build_pnio_block_header(BLOCK_TYPE_IOD_CONTROL_REQ, 24)
    ctrl_block += struct.pack(">H", 0x0000)       # Padding
    ctrl_block += ar_uuid[:16]                     # AR UUID
    ctrl_block += struct.pack(">H", session_key)   # Session key
    ctrl_block += struct.pack(">H", 0x0001)        # Control command: PrmEnd

    body = ctrl_block
    activity_uuid = uuid.uuid4().bytes
    rpc_header = _build_rpc_header(RPC_REQUEST, PNIO_OPNUM_CONTROL, activity_uuid, len(body))

    return _build_udp_packet(src, dst, rpc_header + body, src_port)


def build_rpc_control_response(
    src: DeviceContext,
    dst: DeviceContext,
    ar_uuid: bytes,
    session_key: int,
    dst_port: int = 49152,
) -> bytes:
    """Build PROFINET RPC Control Response — ApplicationReady confirm (device → controller).

    Confirms the device is ready for cyclic data exchange.

    Args:
        src: Source device (IO device)
        dst: Destination device (IO controller)
        ar_uuid: AR UUID
        session_key: Session key
        dst_port: Destination UDP port

    Returns:
        Complete UDP packet bytes
    """
    ctrl_res = _build_pnio_block_header(BLOCK_TYPE_IOD_CONTROL_RES, 24)
    ctrl_res += struct.pack(">H", 0x0000)          # Padding
    ctrl_res += ar_uuid[:16]                        # AR UUID
    ctrl_res += struct.pack(">H", session_key)      # Session key
    ctrl_res += struct.pack(">H", 0x0002)           # Control command: ApplicationReady

    body = ctrl_res
    activity_uuid = uuid.uuid4().bytes
    rpc_header = _build_rpc_header(RPC_RESPONSE, PNIO_OPNUM_CONTROL, activity_uuid, len(body))

    return _build_udp_packet(src, dst, rpc_header + body, PNIO_RPC_PORT, dst_port)
