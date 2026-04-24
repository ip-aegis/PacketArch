# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Configuration dataclasses for S7 protocol engine."""

from dataclasses import dataclass, field
from enum import IntEnum


class S7Area(IntEnum):
    """S7 memory area codes."""

    SYSINFO = 0x03  # System info of 200 family
    SYSFLAGS = 0x05  # System flags of 200 family
    ANAIN = 0x06  # Analog inputs of 200 family
    ANAOUT = 0x07  # Analog outputs of 200 family
    P = 0x80  # Direct peripheral access (I/O)
    INPUTS = 0x81  # Inputs (I)
    OUTPUTS = 0x82  # Outputs (Q)
    MERKERS = 0x83  # Flags/Markers (M)
    DB = 0x84  # Data Blocks (DB)
    DI = 0x85  # Instance Data Blocks
    LOCAL = 0x86  # Local data (L)
    V = 0x87  # Previous local data
    COUNTER = 0x1C  # S7 counters (C)
    TIMER = 0x1D  # S7 timers (T)


class S7ConnectionType(IntEnum):
    """S7 connection types for COTP."""

    PG = 0x01  # Programming device (PG/PC)
    OP = 0x02  # Operator panel (HMI)
    S7_BASIC = 0x03  # S7 Basic Communication


class S7Function(IntEnum):
    """S7 PDU function codes."""

    READ_VAR = 0x04  # Read variables
    WRITE_VAR = 0x05  # Write variables
    DOWNLOAD_REQUEST = 0x1A  # Download request
    DOWNLOAD_BLOCK = 0x1B  # Download block
    DOWNLOAD_END = 0x1C  # Download ended
    UPLOAD_START = 0x1D  # Upload start
    UPLOAD_BLOCK = 0x1E  # Upload block
    UPLOAD_END = 0x1F  # Upload end
    PI_SERVICE = 0x28  # PI service request
    PLC_STOP = 0x29  # Stop PLC
    SETUP_COMM = 0xF0  # Setup communication


class S7DataReturnCode(IntEnum):
    """S7 data item return codes."""

    RESERVED = 0x00
    HARDWARE_ERROR = 0x01
    ACCESS_FAULT = 0x03
    OUT_OF_RANGE = 0x05
    NOT_SUPPORTED = 0x06
    SIZE_MISMATCH = 0x07
    DATA_ERROR = 0x0A
    SUCCESS = 0xFF


class S7TransportSize(IntEnum):
    """S7 transport size codes for read/write operations."""

    BIT = 0x01  # Bit (1 bit)
    BYTE = 0x02  # Byte (8 bit)
    CHAR = 0x03  # Char (8 bit)
    WORD = 0x04  # Word (16 bit)
    INT = 0x05  # Int (16 bit)
    DWORD = 0x06  # Double Word (32 bit)
    DINT = 0x07  # Double Int (32 bit)
    REAL = 0x08  # Real (32 bit float)
    COUNTER = 0x1C  # Counter type
    TIMER = 0x1D  # Timer type


@dataclass
class S7ReadArea:
    """Configuration for a read operation area.

    Attributes:
        area: Memory area code (e.g., S7Area.DB for data blocks)
        db_number: Data block number (0 for non-DB areas)
        start: Start address in bits (byte_offset * 8 + bit_offset)
        size: Number of bytes to read
        transport_size: Data type for transport
    """

    area: int = S7Area.DB
    db_number: int = 1
    start: int = 0  # Start address in bits for S7-300/400, bytes for 1200/1500
    size: int = 10  # Number of bytes
    transport_size: int = S7TransportSize.BYTE

    @property
    def start_byte(self) -> int:
        """Get start address in bytes."""
        return self.start // 8 if self.start >= 8 else self.start

    @property
    def start_bit(self) -> int:
        """Get start bit within the byte."""
        return self.start % 8 if self.start >= 8 else 0


@dataclass
class S7WriteArea:
    """Configuration for a write operation area.

    Attributes:
        area: Memory area code
        db_number: Data block number (0 for non-DB areas)
        start: Start address in bits
        data: Data to write (bytes or will be generated)
        transport_size: Data type for transport
    """

    area: int = S7Area.DB
    db_number: int = 1
    start: int = 0
    data: bytes = field(default_factory=lambda: b"\x00" * 10)
    transport_size: int = S7TransportSize.BYTE


@dataclass
class S7FlowConfig:
    """Configuration for an S7 communication flow.

    Attributes:
        rack: PLC rack number (usually 0)
        slot: PLC slot number (S7-300: 2, S7-1500: 1, S7-1200: 1)
        pdu_size: Maximum PDU size (240-960 bytes depending on CPU)
        connection_type: Type of connection (PG, OP, S7_BASIC)
        read_areas: List of areas to read during poll cycles
        write_areas: List of areas to write during poll cycles
        poll_read_only: If True, only perform read operations
        use_optimized_read: Use optimized block read for S7-1200/1500
    """

    rack: int = 0
    slot: int = 1
    pdu_size: int = 480
    connection_type: int = S7ConnectionType.PG
    read_areas: list[S7ReadArea] = field(default_factory=list)
    write_areas: list[S7WriteArea] = field(default_factory=list)
    poll_read_only: bool = True
    use_optimized_read: bool = False

    def __post_init__(self):
        """Set default read area if none specified."""
        if not self.read_areas:
            # Default: Read 100 bytes from DB1
            self.read_areas = [
                S7ReadArea(area=S7Area.DB, db_number=1, start=0, size=100)
            ]


# =============================================================================
# S7 CPU Profiles for Fingerprinting
# =============================================================================

@dataclass
class S7CPUProfile:
    """Profile for a specific S7 CPU type.

    Attributes:
        name: CPU model name
        max_pdu_size: Maximum PDU size supported
        slot: Typical slot number
        response_delay_ms: Typical response delay range (min, max)
        order_code: Siemens order code (for SZL responses)
        firmware_version: Firmware version string
    """

    name: str
    max_pdu_size: int
    slot: int
    response_delay_ms: tuple[float, float]
    order_code: str = ""
    firmware_version: str = ""


# Common S7 CPU profiles
S7_CPU_PROFILES: dict[str, S7CPUProfile] = {
    # S7-300 Series
    "CPU 315-2 PN/DP": S7CPUProfile(
        name="CPU 315-2 PN/DP",
        max_pdu_size=240,
        slot=2,
        response_delay_ms=(10.0, 50.0),
        order_code="6ES7 315-2EH14-0AB0",
        firmware_version="V3.2",
    ),
    "CPU 317-2 PN/DP": S7CPUProfile(
        name="CPU 317-2 PN/DP",
        max_pdu_size=240,
        slot=2,
        response_delay_ms=(8.0, 40.0),
        order_code="6ES7 317-2EK14-0AB0",
        firmware_version="V3.2",
    ),
    "CPU 319-3 PN/DP": S7CPUProfile(
        name="CPU 319-3 PN/DP",
        max_pdu_size=480,
        slot=2,
        response_delay_ms=(5.0, 30.0),
        order_code="6ES7 318-3EL01-0AB0",
        firmware_version="V3.2",
    ),
    # S7-400 Series
    "CPU 416-3 PN/DP": S7CPUProfile(
        name="CPU 416-3 PN/DP",
        max_pdu_size=480,
        slot=3,
        response_delay_ms=(3.0, 20.0),
        order_code="6ES7 416-3XR05-0AB0",
        firmware_version="V6.0",
    ),
    "CPU 414-3 PN/DP": S7CPUProfile(
        name="CPU 414-3 PN/DP",
        max_pdu_size=480,
        slot=3,
        response_delay_ms=(5.0, 25.0),
        order_code="6ES7 414-3XM07-0AB0",
        firmware_version="V6.0",
    ),
    # S7-1200 Series
    "CPU 1211C": S7CPUProfile(
        name="CPU 1211C DC/DC/DC",
        max_pdu_size=240,
        slot=1,
        response_delay_ms=(5.0, 25.0),
        order_code="6ES7 211-1AE40-0XB0",
        firmware_version="V4.4",
    ),
    "CPU 1212C": S7CPUProfile(
        name="CPU 1212C DC/DC/DC",
        max_pdu_size=240,
        slot=1,
        response_delay_ms=(4.0, 20.0),
        order_code="6ES7 212-1AE40-0XB0",
        firmware_version="V4.4",
    ),
    "CPU 1214C": S7CPUProfile(
        name="CPU 1214C DC/DC/DC",
        max_pdu_size=240,
        slot=1,
        response_delay_ms=(3.0, 15.0),
        order_code="6ES7 214-1AG40-0XB0",
        firmware_version="V4.4",
    ),
    "CPU 1215C": S7CPUProfile(
        name="CPU 1215C DC/DC/DC",
        max_pdu_size=240,
        slot=1,
        response_delay_ms=(2.0, 12.0),
        order_code="6ES7 215-1AG40-0XB0",
        firmware_version="V4.4",
    ),
    # S7-1500 Series
    "CPU 1511-1 PN": S7CPUProfile(
        name="CPU 1511-1 PN",
        max_pdu_size=960,
        slot=1,
        response_delay_ms=(2.0, 10.0),
        order_code="6ES7 511-1AK02-0AB0",
        firmware_version="V2.9",
    ),
    "CPU 1513-1 PN": S7CPUProfile(
        name="CPU 1513-1 PN",
        max_pdu_size=960,
        slot=1,
        response_delay_ms=(1.5, 8.0),
        order_code="6ES7 513-1AL02-0AB0",
        firmware_version="V2.9",
    ),
    "CPU 1515-2 PN": S7CPUProfile(
        name="CPU 1515-2 PN",
        max_pdu_size=960,
        slot=1,
        response_delay_ms=(1.0, 6.0),
        order_code="6ES7 515-2AM02-0AB0",
        firmware_version="V2.9",
    ),
    "CPU 1516-3 PN/DP": S7CPUProfile(
        name="CPU 1516-3 PN/DP",
        max_pdu_size=960,
        slot=1,
        response_delay_ms=(0.8, 5.0),
        order_code="6ES7 516-3AN02-0AB0",
        firmware_version="V2.9",
    ),
    "CPU 1517-3 PN/DP": S7CPUProfile(
        name="CPU 1517-3 PN/DP",
        max_pdu_size=960,
        slot=1,
        response_delay_ms=(0.5, 4.0),
        order_code="6ES7 517-3AP00-0AB0",
        firmware_version="V2.9",
    ),
    "CPU 1518-4 PN/DP": S7CPUProfile(
        name="CPU 1518-4 PN/DP",
        max_pdu_size=960,
        slot=1,
        response_delay_ms=(0.3, 3.0),
        order_code="6ES7 518-4AP00-0AB0",
        firmware_version="V2.9",
    ),
}


def get_cpu_profile(model: str) -> S7CPUProfile | None:
    """Get CPU profile by model name or partial match.

    Args:
        model: CPU model name (exact or partial match)

    Returns:
        S7CPUProfile if found, None otherwise
    """
    # Exact match first
    if model in S7_CPU_PROFILES:
        return S7_CPU_PROFILES[model]

    # Partial match
    model_lower = model.lower()
    for name, profile in S7_CPU_PROFILES.items():
        if model_lower in name.lower():
            return profile

    return None
