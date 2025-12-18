"""PROFINET packet building utilities using Scapy.

PROFINET uses Ethernet Layer 2 with EtherType 0x8892 for RT data.
This module builds:
- DCP (Discovery and Configuration Protocol) frames
- RT (Real-Time) cyclic I/O data frames
- RTA (Real-Time Acyclic) frames for alarms
"""

import struct
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
# RT Class 3 (isochronous): 0x0100-0x7FFF
# DCP: 0xFEFC-0xFEFF
FRAME_ID_DCP_HELLO = 0xFEFC
FRAME_ID_DCP_GET_SET = 0xFEFD
FRAME_ID_DCP_IDENTIFY_REQ = 0xFEFE
FRAME_ID_DCP_IDENTIFY_RES = 0xFEFF
FRAME_ID_RTA = 0xFC01  # Real-Time Acyclic

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


def build_dcp_block(option: int, suboption: int, data: bytes) -> bytes:
    """Build a single DCP block.

    Block structure:
    - Option (1 byte)
    - Suboption (1 byte)
    - Block Length (2 bytes)
    - Block Data (variable, padded to even length)

    Args:
        option: DCP option code
        suboption: DCP suboption code
        data: Block data

    Returns:
        DCP block bytes
    """
    block_length = len(data)
    block = struct.pack(">BBH", option, suboption, block_length)
    block += data
    # Pad to even length
    if len(data) % 2 != 0:
        block += b'\x00'
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
    blocks += build_dcp_block(DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_NAME, name_data)

    # Device ID block (Vendor ID + Device ID)
    device_id_data = struct.pack(">HH", vendor_id, device_id)
    blocks += build_dcp_block(DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_ID, device_id_data)

    # IP Parameter block
    ip_data = _ip_to_bytes(ip_address) + _ip_to_bytes(subnet_mask) + _ip_to_bytes(gateway)
    # Block info (2 bytes): IP address assignment info
    ip_block_data = struct.pack(">H", 0x0001) + ip_data  # 0x0001 = IP set
    blocks += build_dcp_block(DCP_OPTION_IP, DCP_SUBOPTION_IP_PARAMETER, ip_block_data)

    # Device Role block
    role_data = struct.pack(">BB", 0x01, 0x00)  # Device role: IO-Device
    blocks += build_dcp_block(DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_ROLE, role_data)

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

    # Device Name block (required)
    name_data = device_name.encode("ascii")
    blocks += build_dcp_block(DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_NAME, name_data)

    # Device ID block - Vendor ID + Device ID (required)
    device_id_data = struct.pack(">HH", vendor_id, device_id)
    blocks += build_dcp_block(DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_ID, device_id_data)

    # Device Vendor block (if available)
    if device_vendor:
        vendor_data = device_vendor.encode("ascii")
        blocks += build_dcp_block(DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_VENDOR, vendor_data)

    # IP Parameter block
    ip_data = _ip_to_bytes(src.ip_address) + _ip_to_bytes("255.255.255.0") + _ip_to_bytes("0.0.0.0")
    ip_block_data = struct.pack(">H", 0x0001) + ip_data  # 0x0001 = IP set
    blocks += build_dcp_block(DCP_OPTION_IP, DCP_SUBOPTION_IP_PARAMETER, ip_block_data)

    # Device Role block
    role_data = struct.pack(">BB", device_role, 0x00)
    blocks += build_dcp_block(DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_ROLE, role_data)

    # Device Instance block (high/low instance)
    instance_high = profinet_identity.get("instance_high", 0x00)
    instance_low = profinet_identity.get("instance_low", 0x01)
    instance_data = struct.pack(">BB", instance_high, instance_low)
    blocks += build_dcp_block(DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_INSTANCE, instance_data)

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
        blocks += build_dcp_block(DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_OPTIONS, options_data)

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
        blocks += build_dcp_block(DCP_OPTION_DEVICE, DCP_SUBOPTION_DEVICE_OEM_ID, oem_data)

    # Device Initiative block - indicates device wants to be contacted
    # This helps ensure the device is included in network scans
    initiative_data = struct.pack(">H", 0x0001)  # 0x0001 = Device wants initiative
    blocks += build_dcp_block(DCP_OPTION_DEVICE_INITIATIVE, DCP_SUBOPTION_DEVICE_INITIATIVE_VALUE, initiative_data)

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
    block = build_dcp_block(option, suboption, data)

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
