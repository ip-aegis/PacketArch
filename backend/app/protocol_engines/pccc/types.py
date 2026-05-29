# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""PCCC/DF1 protocol types and constants.

PCCC (Programmable Controller Communication Commands) is the application
layer protocol used by Allen-Bradley/Rockwell PLCs including:
- PLC-5 series
- SLC-500 series
- MicroLogix series
- ControlLogix/CompactLogix (legacy compatibility mode)

DF1 is the data link layer protocol for serial communication.
PCCC can also run over TCP (port 2222) or EtherNet/IP (port 44818).
"""

from dataclasses import dataclass
from enum import IntEnum, Enum


# =============================================================================
# PCCC Ports and Transport
# =============================================================================

PCCC_TCP_PORT = 2222      # Legacy PCCC over TCP (SLC-5/05, PLC-5E)
ETHERNET_IP_PORT = 44818  # PCCC over EtherNet/IP (modern devices)


class PCCCTransport(str, Enum):
    """PCCC transport modes."""
    TCP = "tcp"           # Direct PCCC over TCP (port 2222)
    ETHERNET_IP = "eip"   # PCCC encapsulated in EtherNet/IP (port 44818)


# =============================================================================
# DF1 Framing Characters (Serial)
# =============================================================================

class DF1FrameChar(IntEnum):
    """DF1 serial framing characters (ANSI X3.4)."""
    SOH = 0x01  # Start of Header
    STX = 0x02  # Start of Text
    ETX = 0x03  # End of Text
    EOT = 0x04  # End of Transmission
    ENQ = 0x05  # Enquiry (retry request)
    ACK = 0x06  # Acknowledgment (success)
    DLE = 0x10  # Data Link Escape
    NAK = 0x0F  # Negative Acknowledgment


# =============================================================================
# PCCC Command Codes
# =============================================================================

class PCCCCommand(IntEnum):
    """PCCC command codes."""
    # Basic commands
    PROTECTED_WRITE = 0x00        # Protected write (single)
    UNPROTECTED_READ = 0x01       # Read from file 9 (common interface)
    PROTECTED_READ = 0x02         # Protected bit write
    DIAGNOSTIC_STATUS = 0x03      # Request diagnostic status
    UNPROTECTED_WRITE = 0x08      # Write to file 9

    # Extended commands (use function codes)
    WORD_RANGE_READ = 0x0F        # Protected typed logical operations
    WORD_RANGE_WRITE = 0x0F       # (function code determines operation)

    # File operations
    FILE_READ = 0x0F              # Read file data
    FILE_WRITE = 0x0F             # Write file data

    # Control/configuration
    ECHO = 0x06                   # Echo test
    SET_CPU_MODE = 0x0F           # Change PLC mode (run/program/test)


class PCCCFunction(IntEnum):
    """PCCC function codes (used with command 0x0F)."""
    # Read operations
    PROTECTED_TYPED_READ_3ADDR = 0xA2      # Read with 3 address fields
    PROTECTED_TYPED_READ_2ADDR = 0xA1      # Read with 2 address fields

    # Write operations
    PROTECTED_TYPED_WRITE_3ADDR = 0xAA     # Write with 3 address fields
    PROTECTED_TYPED_WRITE_2ADDR = 0xA9     # Write with 2 address fields (masked)
    PROTECTED_TYPED_WRITE_MASKED = 0xAB    # Write with mask

    # File operations
    READ_SLC_FILE_INFO = 0x4C              # Get file information

    # Control operations
    SET_CPU_MODE = 0x80                    # Change operating mode


# =============================================================================
# PCCC Status Codes
# =============================================================================

class PCCCStatus(IntEnum):
    """PCCC status/error codes."""
    SUCCESS = 0x00                  # No error

    # General errors (0x01-0x0F)
    DST_NODE_OUT_OF_BUFFER = 0x01   # Destination out of buffer space
    CANNOT_GUARANTEE_DELIVERY = 0x02
    DUPLICATE_TOKEN_HOLDER = 0x03
    LOCAL_PORT_DISCONNECTED = 0x04
    APP_LAYER_TIMED_OUT = 0x05
    DUPLICATE_NODE = 0x06
    STATION_OFFLINE = 0x07
    HARDWARE_FAULT = 0x08

    # Command errors (0x10-0x1F)
    ILLEGAL_COMMAND = 0x10          # Command not recognized
    HOST_HAS_PROBLEM = 0x11
    REMOTE_NODE_MISSING = 0x12
    HARDWARE_FAULT_2 = 0x13
    ADDRESSING_PROBLEM = 0x14
    FUNCTION_NOT_ALLOWED = 0x15
    PROCESSOR_IN_PROGRAM_MODE = 0x16

    # File errors (0x20-0x2F)
    INVALID_FILE_NUMBER = 0x20      # File doesn't exist
    INVALID_ELEMENT = 0x21          # Element out of range
    INVALID_SUBELEMENT = 0x22       # Subelement out of range
    TOO_MUCH_DATA = 0x23            # Request exceeds limits
    CHECKSUM_ERROR = 0x24           # Data integrity error

    # Access errors (0x30-0x4F)
    ACCESS_DENIED = 0x30            # Protection fault
    RESOURCE_UNAVAILABLE = 0x40
    FILE_PROTECTED = 0x44           # Cannot access protected file

    # Extended status (0xF0-0xFF)
    EXTENDED_STATUS = 0xF0          # Check extended status byte


# =============================================================================
# PCCC File Types (SLC/PLC-5 addressing)
# =============================================================================

class PCCCFileType(IntEnum):
    """PCCC file types for SLC-500/PLC-5 addressing."""
    OUTPUT = 0x8B           # O - Output
    INPUT = 0x8C            # I - Input
    STATUS = 0x84           # S - Status
    BINARY = 0x85           # B - Binary/Bit
    TIMER = 0x86            # T - Timer
    COUNTER = 0x87          # C - Counter
    CONTROL = 0x88          # R - Control
    INTEGER = 0x89          # N - Integer
    FLOAT = 0x8A            # F - Float
    STRING = 0x8D           # ST - String
    ASCII = 0x8E            # A - ASCII
    BCD = 0x8F              # D - BCD
    LONG = 0x91             # L - Long integer
    MESSAGE = 0x92          # MG - Message
    PID = 0x93              # PD - PID

    # ControlLogix compatible (pseudo-types)
    DINT = 0x89             # Same as Integer for 32-bit
    REAL = 0x8A             # Same as Float


# File type name mapping
FILE_TYPE_NAMES = {
    PCCCFileType.OUTPUT: "O",
    PCCCFileType.INPUT: "I",
    PCCCFileType.STATUS: "S",
    PCCCFileType.BINARY: "B",
    PCCCFileType.TIMER: "T",
    PCCCFileType.COUNTER: "C",
    PCCCFileType.CONTROL: "R",
    PCCCFileType.INTEGER: "N",
    PCCCFileType.FLOAT: "F",
    PCCCFileType.STRING: "ST",
    PCCCFileType.ASCII: "A",
    PCCCFileType.BCD: "D",
    PCCCFileType.LONG: "L",
    PCCCFileType.MESSAGE: "MG",
    PCCCFileType.PID: "PD",
}


# =============================================================================
# Allen-Bradley Device Types
# =============================================================================

class ABDeviceType(IntEnum):
    """Allen-Bradley/CIP device types."""
    GENERIC = 0x00
    AC_DRIVE = 0x02
    MOTOR_OVERLOAD = 0x03
    LIMIT_SWITCH = 0x04
    INDUCTIVE_PROXIMITY = 0x05
    PHOTOELECTRIC = 0x06
    COMMUNICATIONS_ADAPTER = 0x0C
    PROGRAMMABLE_LOGIC_CONTROLLER = 0x0E  # 14 decimal
    POSITION_CONTROLLER = 0x10
    DC_DRIVE = 0x13
    CONTACTOR = 0x15
    HUMAN_MACHINE_INTERFACE = 0x18  # 24 decimal
    MASS_FLOW_CONTROLLER = 0x1A
    PNEUMATIC_VALVE = 0x1B
    SAFETY_DEVICE = 0x2C


# Allen-Bradley product codes (common models)
class ABProductCode(IntEnum):
    """Allen-Bradley product codes for common devices."""
    # PLC-5 Series
    PLC5_10 = 0x0001
    PLC5_15 = 0x0002
    PLC5_20 = 0x0003
    PLC5_30 = 0x0004
    PLC5_40 = 0x0005
    PLC5_60 = 0x0006
    PLC5_80 = 0x0007

    # SLC-500 Series
    SLC500_01 = 0x0010
    SLC500_02 = 0x0011
    SLC500_03 = 0x0012
    SLC500_04 = 0x0013
    SLC500_05 = 0x0014

    # MicroLogix Series
    MICROLOGIX_1000 = 0x0020
    MICROLOGIX_1100 = 0x0021
    MICROLOGIX_1200 = 0x0022
    MICROLOGIX_1400 = 0x0023
    MICROLOGIX_1500 = 0x0024

    # ControlLogix Series
    CONTROLLOGIX_L55 = 0x0030
    CONTROLLOGIX_L61 = 0x0031
    CONTROLLOGIX_L63 = 0x0032
    CONTROLLOGIX_L71 = 0x0033
    CONTROLLOGIX_L73 = 0x0034
    CONTROLLOGIX_L75 = 0x0035
    CONTROLLOGIX_L81 = 0x0036
    CONTROLLOGIX_L83 = 0x0037
    CONTROLLOGIX_L85 = 0x0038

    # CompactLogix Series
    COMPACTLOGIX_L16 = 0x0040
    COMPACTLOGIX_L18 = 0x0041
    COMPACTLOGIX_L23 = 0x0042
    COMPACTLOGIX_L24 = 0x0043
    COMPACTLOGIX_L27 = 0x0044
    COMPACTLOGIX_L30 = 0x0045
    COMPACTLOGIX_L33 = 0x0046
    COMPACTLOGIX_L36 = 0x0047


# Product name mapping
AB_PRODUCT_NAMES = {
    ABProductCode.PLC5_10: "1785-L10 PLC-5/10",
    ABProductCode.PLC5_15: "1785-L15 PLC-5/15",
    ABProductCode.PLC5_20: "1785-L20 PLC-5/20",
    ABProductCode.PLC5_30: "1785-L30 PLC-5/30",
    ABProductCode.PLC5_40: "1785-L40 PLC-5/40",
    ABProductCode.PLC5_60: "1785-L60 PLC-5/60",
    ABProductCode.PLC5_80: "1785-L80 PLC-5/80",
    ABProductCode.SLC500_01: "1747-L511 SLC-5/01",
    ABProductCode.SLC500_02: "1747-L524 SLC-5/02",
    ABProductCode.SLC500_03: "1747-L532 SLC-5/03",
    ABProductCode.SLC500_04: "1747-L542 SLC-5/04",
    ABProductCode.SLC500_05: "1747-L553 SLC-5/05",
    ABProductCode.MICROLOGIX_1000: "1761-L10BWA MicroLogix 1000",
    ABProductCode.MICROLOGIX_1100: "1763-L16AWA MicroLogix 1100",
    ABProductCode.MICROLOGIX_1200: "1762-L24AWA MicroLogix 1200",
    ABProductCode.MICROLOGIX_1400: "1766-L32AWA MicroLogix 1400",
    ABProductCode.MICROLOGIX_1500: "1764-LRP MicroLogix 1500",
    ABProductCode.CONTROLLOGIX_L55: "1756-L55 ControlLogix",
    ABProductCode.CONTROLLOGIX_L61: "1756-L61 ControlLogix",
    ABProductCode.CONTROLLOGIX_L63: "1756-L63 ControlLogix",
    ABProductCode.CONTROLLOGIX_L71: "1756-L71 ControlLogix",
    ABProductCode.CONTROLLOGIX_L73: "1756-L73 ControlLogix",
    ABProductCode.CONTROLLOGIX_L75: "1756-L75 ControlLogix",
    ABProductCode.CONTROLLOGIX_L81: "1756-L81E ControlLogix",
    ABProductCode.CONTROLLOGIX_L83: "1756-L83E ControlLogix",
    ABProductCode.CONTROLLOGIX_L85: "1756-L85E ControlLogix",
    ABProductCode.COMPACTLOGIX_L16: "1769-L16ER-BB1B CompactLogix",
    ABProductCode.COMPACTLOGIX_L18: "1769-L18ER-BB1B CompactLogix",
    ABProductCode.COMPACTLOGIX_L23: "1769-L23E-QB1B CompactLogix",
    ABProductCode.COMPACTLOGIX_L24: "1769-L24ER-QB1B CompactLogix",
    ABProductCode.COMPACTLOGIX_L27: "1769-L27ERM-QBFC1B CompactLogix",
    ABProductCode.COMPACTLOGIX_L30: "1769-L30ER CompactLogix",
    ABProductCode.COMPACTLOGIX_L33: "1769-L33ER CompactLogix",
    ABProductCode.COMPACTLOGIX_L36: "1769-L36ERM CompactLogix",
}


# Rockwell/Allen-Bradley vendor ID (CIP)
AB_VENDOR_ID = 1


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class PCCCAddress:
    """Parsed PCCC file address (e.g., N7:2.0)."""
    file_type: PCCCFileType
    file_number: int
    element: int
    subelement: int = 0
    bit: int | None = None

    def to_string(self) -> str:
        """Convert to string representation."""
        type_name = FILE_TYPE_NAMES.get(self.file_type, "?")
        addr = f"{type_name}{self.file_number}:{self.element}"
        if self.subelement > 0:
            addr += f".{self.subelement}"
        if self.bit is not None:
            addr += f"/{self.bit}"
        return addr

    @classmethod
    def parse(cls, address: str) -> "PCCCAddress":
        """Parse address string like N7:2 or T4:0.ACC."""
        import re

        # Pattern: TYPE FILE : ELEMENT [.SUBELEMENT] [/BIT]
        pattern = r"^([A-Z]+)(\d+):(\d+)(?:\.(\w+))?(?:/(\d+))?$"
        match = re.match(pattern, address.upper())

        if not match:
            raise ValueError(f"Invalid PCCC address: {address}")

        type_str, file_num, element, subelem, bit = match.groups()

        # Reverse lookup file type
        file_type = None
        for ft, name in FILE_TYPE_NAMES.items():
            if name == type_str:
                file_type = ft
                break

        if file_type is None:
            raise ValueError(f"Unknown file type: {type_str}")

        # Handle named subelements (ACC, PRE, etc.)
        subelement = 0
        if subelem:
            if subelem.isdigit():
                subelement = int(subelem)
            elif subelem in ("ACC", "ACCUM"):
                subelement = 2  # Accumulator
            elif subelem in ("PRE", "PRESET"):
                subelement = 1  # Preset
            elif subelem in ("DN", "DONE"):
                subelement = 13  # Done bit position
            elif subelem in ("EN", "ENABLE"):
                subelement = 15  # Enable bit position
            elif subelem in ("TT", "TIMING"):
                subelement = 14  # Timer timing bit

        return cls(
            file_type=file_type,
            file_number=int(file_num),
            element=int(element),
            subelement=subelement,
            bit=int(bit) if bit else None,
        )


@dataclass
class PCCCDeviceIdentity:
    """PCCC/CIP device identity information."""
    vendor_id: int = AB_VENDOR_ID  # Always 1 for Allen-Bradley
    device_type: ABDeviceType = ABDeviceType.PROGRAMMABLE_LOGIC_CONTROLLER
    product_code: int = ABProductCode.SLC500_05
    revision_major: int = 5
    revision_minor: int = 0
    serial_number: int = 0x12345678
    product_name: str = "1747-L553 SLC-5/05"

    def get_revision_string(self) -> str:
        """Get firmware revision as string."""
        return f"{self.revision_major}.{self.revision_minor}"


@dataclass
class PCCCConfig:
    """Configuration for PCCC communication."""
    transport: PCCCTransport = PCCCTransport.TCP
    source_node: int = 0          # Source node address (0-255)
    destination_node: int = 1     # Destination node address
    timeout_ms: int = 5000        # Request timeout
    retries: int = 3              # Retry count on failure

    # File access configuration
    default_file_type: PCCCFileType = PCCCFileType.INTEGER
    default_file_number: int = 7  # N7 is commonly used

    # EtherNet/IP specific
    session_handle: int = 0       # For EIP transport


# Note: PCCCConversationState is defined in app.protocol_engines.types
# to be consistent with other protocol conversation states
