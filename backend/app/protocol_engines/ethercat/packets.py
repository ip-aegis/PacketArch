"""EtherCAT packet building utilities.

EtherCAT (Ethernet for Control Automation Technology) is a high-performance
Layer 2 industrial Ethernet protocol developed by Beckhoff.

Key characteristics:
- EtherType: 0x88A4
- Processing on the fly: Slaves process frames as they pass through
- Daisy chain topology: Frames travel through all slaves in a ring/line
- Working Counter (WKC): Error detection mechanism
"""

import struct
from typing import TYPE_CHECKING

from scapy.layers.l2 import Ether
from scapy.packet import Raw

from app.protocol_engines.types import DeviceContext

if TYPE_CHECKING:
    pass


# EtherCAT Constants
ETHERCAT_ETHERTYPE = 0x88A4

# EtherCAT Command Types
class EtherCATCommand:
    """EtherCAT datagram command codes."""
    NOP = 0x00   # No Operation
    APRD = 0x01  # Auto-increment Physical Read
    APWR = 0x02  # Auto-increment Physical Write
    APRW = 0x03  # Auto-increment Physical Read/Write
    FPRD = 0x04  # Configured Address Read
    FPWR = 0x05  # Configured Address Write
    FPRW = 0x06  # Configured Address Read/Write
    BRD = 0x07   # Broadcast Read
    BWR = 0x08   # Broadcast Write
    BRW = 0x09   # Broadcast Read/Write
    LRD = 0x0A   # Logical Read
    LWR = 0x0B   # Logical Write
    LRW = 0x0C   # Logical Read/Write
    ARMW = 0x0D  # Auto-increment Read Multiple Write
    FRMW = 0x0E  # Configured Address Read Multiple Write


# EtherCAT ESC Register Addresses
class ESCRegister:
    """EtherCAT Slave Controller register addresses."""
    TYPE = 0x0000               # Device type
    REVISION = 0x0001           # Revision number
    BUILD = 0x0002              # Build number (2 bytes)
    FMMU_SUPPORTED = 0x0004     # Number of FMMUs
    SM_SUPPORTED = 0x0005       # Number of SyncManagers
    RAM_SIZE = 0x0006           # Process RAM size
    PORT_DESC = 0x0007          # Port configuration
    ESC_FEATURES = 0x0008       # Supported features (2 bytes)
    STATION_ADDR = 0x0010       # Configured station address (2 bytes)
    STATION_ALIAS = 0x0012      # Station alias (2 bytes)
    DL_CONTROL = 0x0100         # Data link control (4 bytes)
    DL_STATUS = 0x0110          # Data link status (2 bytes)
    AL_CONTROL = 0x0120         # Application layer control (2 bytes)
    AL_STATUS = 0x0130          # Application layer status (2 bytes)
    AL_STATUS_CODE = 0x0134     # AL error code (2 bytes)
    PDI_CONTROL = 0x0140        # Process data interface control
    ECAT_EVENT_MASK = 0x0200    # Event interrupt mask (2 bytes)
    ECAT_EVENT_REQ = 0x0220     # Event interrupt request (2 bytes)
    RX_ERROR_COUNTER = 0x0300   # Receive error counters
    LOST_LINK_COUNTER = 0x0310  # Lost link counters
    WD_DIVIDER = 0x0400         # Watchdog divider (2 bytes)
    FMMU_0 = 0x0600             # FMMU 0 configuration (16 bytes each)
    SM_0 = 0x0800               # SyncManager 0 (8 bytes each)
    SM_1 = 0x0808               # SyncManager 1
    SM_2 = 0x0810               # SyncManager 2 (process data out)
    SM_3 = 0x0818               # SyncManager 3 (process data in)
    DC_RECV_TIME_P0 = 0x0900    # DC Port 0 receive timestamp (8 bytes)
    DC_RECV_TIME_P1 = 0x0908    # DC Port 1 receive timestamp
    DC_SYSTEM_TIME = 0x0910     # System time (8 bytes)
    DC_SYSTEM_OFFSET = 0x0920   # System time offset (8 bytes)
    DC_SYSTEM_DELAY = 0x0928    # Transmission delay (4 bytes)
    SYNC0_CYCLE_TIME = 0x09A0   # SYNC0 cycle time (4 bytes)
    SYNC1_CYCLE_TIME = 0x09A4   # SYNC1 cycle time (4 bytes)
    DC_ACTIVATION = 0x0981      # DC activation register


# AL State Values
class ALState:
    """Application Layer state machine states."""
    INIT = 0x01     # Initialization
    PREOP = 0x02    # Pre-operational
    BOOT = 0x03     # Boot mode (firmware update)
    SAFEOP = 0x04   # Safe-operational
    OP = 0x08       # Operational


def build_ethercat_datagram(
    cmd: int,
    idx: int,
    adp: int,
    ado: int,
    data: bytes,
    more: bool = False,
    circulating: bool = False,
    irq: int = 0,
    wkc: int = 0,
) -> bytes:
    """Build a single EtherCAT datagram.

    Args:
        cmd: Command type (see EtherCATCommand)
        idx: Index/sequence number (0-255)
        adp: Address position (ADP) - slave position or station address
        ado: Address offset (ADO) - register offset within slave
        data: Data payload
        more: More datagrams follow in this frame
        circulating: Frame is circulating (already processed)
        irq: Interrupt request field
        wkc: Working counter value

    Returns:
        Complete datagram bytes (header + data + WKC)
    """
    data_len = len(data)

    # Build length/flags field (2 bytes)
    # Bits 0-10: Length (max 2047)
    # Bit 14: C (Circulating)
    # Bit 15: M (More datagrams)
    len_flags = data_len & 0x07FF
    if circulating:
        len_flags |= 0x4000
    if more:
        len_flags |= 0x8000

    # Build 10-byte header
    header = struct.pack(
        "<BBHHHH",
        cmd,        # Command (1 byte)
        idx,        # Index (1 byte)
        adp,        # Address Position (2 bytes LE)
        ado,        # Address Offset (2 bytes LE)
        len_flags,  # Length + Flags (2 bytes LE)
        irq,        # Interrupt request (2 bytes)
    )

    # Working counter (2 bytes LE)
    wkc_bytes = struct.pack("<H", wkc)

    return header + data + wkc_bytes


def build_ethercat_frame(
    datagrams: list[bytes],
    src_mac: str,
    dst_mac: str = "ff:ff:ff:ff:ff:ff",
) -> bytes:
    """Build complete EtherCAT Ethernet frame.

    Args:
        datagrams: List of datagram bytes
        src_mac: Source MAC address (colon-separated)
        dst_mac: Destination MAC address (broadcast by default)

    Returns:
        Complete Ethernet frame bytes
    """
    # Combine all datagrams
    ecat_data = b"".join(datagrams)

    # Build EtherCAT header (2 bytes)
    # Bits 0-10: Length of datagrams
    # Bit 11: Reserved (0)
    # Bits 12-15: Type (0x1 for EtherCAT commands)
    ecat_len = len(ecat_data)
    ecat_header = struct.pack("<H", (ecat_len & 0x07FF) | (0x1 << 12))

    # Build Ethernet frame using Scapy
    packet = (
        Ether(src=src_mac, dst=dst_mac, type=ETHERCAT_ETHERTYPE)
        / Raw(load=ecat_header + ecat_data)
    )

    return bytes(packet)


def build_ethercat_packet(
    src: DeviceContext,
    dst: DeviceContext,
    datagrams: list[bytes],
) -> bytes:
    """Build EtherCAT packet using device contexts.

    Args:
        src: Source device context
        dst: Destination device context
        datagrams: List of datagram bytes

    Returns:
        Complete Ethernet frame bytes
    """
    return build_ethercat_frame(
        datagrams=datagrams,
        src_mac=src.mac_address,
        dst_mac=dst.mac_address,
    )


def build_syncmanager_config(
    physical_start: int,
    length: int,
    control: int,
    status: int = 0x00,
    activate: int = 0x01,
    pdi_control: int = 0x00,
) -> bytes:
    """Build SyncManager configuration (8 bytes).

    SyncManagers control the exchange of data between the EtherCAT slave
    controller and the local application.

    SM0/SM1: Typically used for mailbox communication
    SM2: Process data outputs (Master -> Slave)
    SM3: Process data inputs (Slave -> Master)

    Args:
        physical_start: Start address in process RAM
        length: Data length
        control: Control register (mode, direction, interrupt)
        status: Status register
        activate: Activation (1=enabled)
        pdi_control: PDI control

    Returns:
        8-byte SyncManager configuration
    """
    return struct.pack(
        "<HHBBBB",
        physical_start,  # Physical Start Address
        length,          # Length
        control,         # Control
        status,          # Status
        activate,        # Activate
        pdi_control,     # PDI Control
    )


def build_fmmu_config(
    logical_start: int,
    length: int,
    logical_start_bit: int = 0,
    logical_end_bit: int = 7,
    physical_start: int = 0,
    physical_start_bit: int = 0,
    read_enable: bool = True,
    write_enable: bool = True,
    activate: bool = True,
) -> bytes:
    """Build FMMU configuration (16 bytes).

    FMMUs (Fieldbus Memory Management Units) map logical addresses
    used in LRD/LWR/LRW commands to physical addresses in slaves.

    Args:
        logical_start: Logical start address (32-bit)
        length: Data length in bytes
        logical_start_bit: Start bit within first byte
        logical_end_bit: End bit within last byte
        physical_start: Physical address in slave
        physical_start_bit: Start bit in physical memory
        read_enable: Enable read access
        write_enable: Enable write access
        activate: FMMU active

    Returns:
        16-byte FMMU configuration
    """
    type_byte = 0
    if read_enable:
        type_byte |= 0x01
    if write_enable:
        type_byte |= 0x02

    # FMMU structure: 16 bytes
    return struct.pack(
        "<IHBBHBBBB",
        logical_start,              # Logical Start Address (4 bytes)
        length,                     # Length (2 bytes)
        logical_start_bit,          # Logical Start Bit (1 byte)
        logical_end_bit,            # Logical End Bit (1 byte)
        physical_start,             # Physical Start Address (2 bytes)
        physical_start_bit,         # Physical Start Bit (1 byte)
        type_byte,                  # Type (Read/Write enable) (1 byte)
        0x01 if activate else 0x00, # Activate (1 byte)
    ) + b"\x00" * 3  # Reserved (3 bytes) - total 16 bytes


def auto_increment_address(position: int) -> int:
    """Calculate auto-increment address for slave position.

    Auto-increment addressing uses negative position values:
    - First slave (position 0): ADP = 0x0000
    - Second slave (position 1): ADP = 0xFFFF (-1)
    - Third slave (position 2): ADP = 0xFFFE (-2)

    Args:
        position: Slave position (0-indexed from master)

    Returns:
        16-bit auto-increment address
    """
    if position == 0:
        return 0x0000
    return (0x10000 - position) & 0xFFFF


def calculate_expected_wkc(cmd: int, num_slaves: int) -> int:
    """Calculate expected working counter for a command.

    The Working Counter is incremented by each slave that successfully
    processes a datagram:
    - Read operations: +1 per slave
    - Write operations: +1 per slave
    - Read/Write operations: +3 per slave (read +1, write +2)

    Args:
        cmd: EtherCAT command type
        num_slaves: Number of slaves that should respond

    Returns:
        Expected working counter value
    """
    read_cmds = {
        EtherCATCommand.APRD,
        EtherCATCommand.FPRD,
        EtherCATCommand.BRD,
        EtherCATCommand.LRD,
    }
    write_cmds = {
        EtherCATCommand.APWR,
        EtherCATCommand.FPWR,
        EtherCATCommand.BWR,
        EtherCATCommand.LWR,
    }
    rw_cmds = {
        EtherCATCommand.APRW,
        EtherCATCommand.FPRW,
        EtherCATCommand.BRW,
        EtherCATCommand.LRW,
    }

    if cmd in read_cmds:
        return num_slaves * 1
    elif cmd in write_cmds:
        return num_slaves * 1
    elif cmd in rw_cmds:
        return num_slaves * 3
    return 0


# CoE (CANopen over EtherCAT) Constants
COE_TYPE = 0x03  # Mailbox type for CoE


def build_coe_sdo_upload_request(
    index: int,
    subindex: int,
    complete_access: bool = False,
) -> bytes:
    """Build CoE SDO upload (read) request.

    Args:
        index: Object dictionary index
        subindex: Object dictionary subindex
        complete_access: Read entire object at once

    Returns:
        Mailbox data for SDO upload request
    """
    # Mailbox header (6 bytes)
    data_length = 10  # CoE header + SDO request
    mailbox_header = struct.pack(
        "<HHBB",
        data_length,  # Length
        0x0000,       # Address (0 for SDO)
        0x00,         # Reserved + Priority
        COE_TYPE,     # Type: CoE
    )

    # CoE header (2 bytes)
    coe_header = struct.pack("<H", 0x2000)  # SDO Request

    # SDO upload initiate request (8 bytes)
    command_specifier = 0x40  # Initiate upload request
    if complete_access:
        command_specifier |= 0x01

    sdo_request = struct.pack(
        "<BHBI",
        command_specifier,
        index,
        subindex,
        0x00000000,  # Reserved
    )

    return mailbox_header + coe_header + sdo_request


def build_coe_sdo_download_request(
    index: int,
    subindex: int,
    data: bytes,
) -> bytes:
    """Build CoE SDO download (write) request.

    Args:
        index: Object dictionary index
        subindex: Object dictionary subindex
        data: Data to write

    Returns:
        Mailbox data for SDO download request
    """
    data_size = len(data)

    # Mailbox header
    mailbox_header = struct.pack(
        "<HHBB",
        10 + data_size,
        0x0000,
        0x00,
        COE_TYPE,
    )

    # CoE header
    coe_header = struct.pack("<H", 0x2000)

    # SDO download - expedited for data <= 4 bytes
    if data_size <= 4:
        command_specifier = 0x23 | ((4 - data_size) << 2)
        sdo_data = data.ljust(4, b"\x00")
        sdo_request = struct.pack("<BHB", command_specifier, index, subindex)
        sdo_request += sdo_data
    else:
        command_specifier = 0x21  # Normal download
        sdo_request = struct.pack(
            "<BHBI",
            command_specifier,
            index,
            subindex,
            data_size,
        ) + data

    return mailbox_header + coe_header + sdo_request


__all__ = [
    "ETHERCAT_ETHERTYPE",
    "EtherCATCommand",
    "ESCRegister",
    "ALState",
    "build_ethercat_datagram",
    "build_ethercat_frame",
    "build_ethercat_packet",
    "build_syncmanager_config",
    "build_fmmu_config",
    "auto_increment_address",
    "calculate_expected_wkc",
    "build_coe_sdo_upload_request",
    "build_coe_sdo_download_request",
]
