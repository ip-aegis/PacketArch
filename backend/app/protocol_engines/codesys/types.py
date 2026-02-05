"""Codesys protocol types and constants.

Codesys is a development environment and runtime for PLCs used by 500+
manufacturers including WAGO, Beckhoff, Festo, Schneider Electric, ABB, and more.

Protocol versions:
- V2 (legacy): TCP port 1200, simple file operations
- V3 (modern): TCP port 11740, binary app upload, variable access
"""

from dataclasses import dataclass, field
from enum import IntEnum, Enum
from typing import Any


# =============================================================================
# Codesys Ports and Transport
# =============================================================================

# V3 ports (modern)
CODESYS_V3_PORT = 11740       # Primary V3 runtime port
CODESYS_V3_PORT_2 = 11741     # Secondary V3 port
CODESYS_V3_PORT_3 = 11742     # Tertiary V3 port
CODESYS_V3_PORT_4 = 11743     # Quaternary V3 port

# V2 ports (legacy)
CODESYS_V2_PORT = 1200        # V2 TCP listener
CODESYS_V2_PORT_2 = 1201      # V2 secondary port
CODESYS_GATEWAY_PORT = 1217   # Gateway/programming port


class CodesysVersion(str, Enum):
    """Codesys protocol versions."""
    V2 = "v2"   # Legacy version
    V3 = "v3"   # Modern version


# =============================================================================
# Block Driver Constants
# =============================================================================

# Block driver magic number (little-endian)
BLOCK_DRIVER_MAGIC = 0x000117E8  # 0xE8170100 when written as bytes

# Maximum payload size
MAX_PAYLOAD_SIZE = 512
MAX_FRAME_SIZE = 520  # 8-byte header + 512 payload


# =============================================================================
# Service/Command Codes
# =============================================================================

class CodesysService(IntEnum):
    """Codesys V3 service codes."""
    # Device services
    DEVICE_INFO = 0x01            # Get device information
    DEVICE_STATUS = 0x02          # Get device status
    DEVICE_RESET = 0x03           # Reset device
    DEVICE_STOP = 0x04            # Stop PLC execution
    DEVICE_START = 0x05           # Start PLC execution
    DEVICE_COLD_RESET = 0x06      # Cold reset

    # Application services
    APP_DOWNLOAD = 0x10           # Download application
    APP_UPLOAD = 0x11             # Upload application
    APP_DELETE = 0x12             # Delete application
    APP_INFO = 0x13               # Get application info
    APP_LIST = 0x14               # List applications

    # Variable services
    VAR_READ = 0x20               # Read variable(s)
    VAR_WRITE = 0x21              # Write variable(s)
    VAR_READ_MULTIPLE = 0x22      # Read multiple variables
    VAR_WRITE_MULTIPLE = 0x23     # Write multiple variables

    # File services
    FILE_LIST = 0x30              # List directory
    FILE_READ = 0x31              # Read file
    FILE_WRITE = 0x32             # Write file
    FILE_DELETE = 0x33            # Delete file
    FILE_RENAME = 0x34            # Rename file

    # Network services
    NETWORK_SCAN = 0x40           # Scan network for devices
    NETWORK_INFO = 0x41           # Get network information

    # Authentication
    AUTH_LOGIN = 0x50             # Login (plaintext password)
    AUTH_LOGOUT = 0x51            # Logout
    AUTH_CHALLENGE = 0x52         # Challenge-response (V3.5+)


class CodesysV2Command(IntEnum):
    """Codesys V2 command codes."""
    GET_INFO = 0x01               # Get device info
    READ_MEMORY = 0x02            # Read memory
    WRITE_MEMORY = 0x03           # Write memory
    START_PLC = 0x04              # Start PLC
    STOP_PLC = 0x05               # Stop PLC
    LIST_FILES = 0x06             # List files
    READ_FILE = 0x07              # Read file
    WRITE_FILE = 0x08             # Write file
    DELETE_FILE = 0x09            # Delete file


# =============================================================================
# Status Codes
# =============================================================================

class CodesysStatus(IntEnum):
    """Codesys response status codes."""
    SUCCESS = 0x00                # Operation successful
    ERR_UNKNOWN = 0x01            # Unknown error
    ERR_INVALID_SERVICE = 0x02    # Invalid service code
    ERR_INVALID_PARAM = 0x03      # Invalid parameter
    ERR_ACCESS_DENIED = 0x04      # Access denied
    ERR_NOT_FOUND = 0x05          # Resource not found
    ERR_TIMEOUT = 0x06            # Operation timed out
    ERR_BUSY = 0x07               # Device busy
    ERR_NOT_SUPPORTED = 0x08      # Operation not supported
    ERR_CHECKSUM = 0x09           # Checksum error
    ERR_MEMORY = 0x0A             # Memory error
    ERR_PLC_RUNNING = 0x0B        # PLC must be stopped
    ERR_PLC_STOPPED = 0x0C        # PLC must be running
    ERR_AUTH_REQUIRED = 0x0D      # Authentication required
    ERR_AUTH_FAILED = 0x0E        # Authentication failed


class PLCState(IntEnum):
    """PLC operational states."""
    UNKNOWN = 0x00
    STOPPED = 0x01
    RUNNING = 0x02
    HALT = 0x03
    EXCEPTION = 0x04
    BREAKPOINT = 0x05
    SINGLE_STEP = 0x06


# =============================================================================
# Data Types
# =============================================================================

class CodesysDataType(IntEnum):
    """Codesys IEC 61131-3 data types."""
    BOOL = 0x01           # Boolean (1 bit)
    BYTE = 0x02           # 8-bit unsigned
    WORD = 0x03           # 16-bit unsigned
    DWORD = 0x04          # 32-bit unsigned
    LWORD = 0x05          # 64-bit unsigned
    SINT = 0x06           # 8-bit signed
    INT = 0x07            # 16-bit signed
    DINT = 0x08           # 32-bit signed
    LINT = 0x09           # 64-bit signed
    USINT = 0x0A          # 8-bit unsigned
    UINT = 0x0B           # 16-bit unsigned
    UDINT = 0x0C          # 32-bit unsigned
    ULINT = 0x0D          # 64-bit unsigned
    REAL = 0x0E           # 32-bit float
    LREAL = 0x0F          # 64-bit float
    STRING = 0x10         # Variable-length string
    WSTRING = 0x11        # Wide string
    TIME = 0x12           # Duration
    DATE = 0x13           # Date
    DATE_AND_TIME = 0x14  # Date and time
    TIME_OF_DAY = 0x15    # Time of day


# Data type sizes in bytes
DATA_TYPE_SIZES = {
    CodesysDataType.BOOL: 1,
    CodesysDataType.BYTE: 1,
    CodesysDataType.WORD: 2,
    CodesysDataType.DWORD: 4,
    CodesysDataType.LWORD: 8,
    CodesysDataType.SINT: 1,
    CodesysDataType.INT: 2,
    CodesysDataType.DINT: 4,
    CodesysDataType.LINT: 8,
    CodesysDataType.USINT: 1,
    CodesysDataType.UINT: 2,
    CodesysDataType.UDINT: 4,
    CodesysDataType.ULINT: 8,
    CodesysDataType.REAL: 4,
    CodesysDataType.LREAL: 8,
    CodesysDataType.TIME: 4,
    CodesysDataType.DATE: 4,
    CodesysDataType.DATE_AND_TIME: 8,
    CodesysDataType.TIME_OF_DAY: 4,
}


# =============================================================================
# Codesys Vendors and Devices
# =============================================================================

class CodesysVendor(IntEnum):
    """Codesys vendor IDs (partial list)."""
    THREE_S = 0x0001          # 3S-Smart Software Solutions (Codesys GmbH)
    WAGO = 0x0010             # WAGO Kontakttechnik
    BECKHOFF = 0x0020         # Beckhoff Automation
    FESTO = 0x0030            # Festo AG
    SCHNEIDER = 0x0040        # Schneider Electric
    ABB = 0x0050              # ABB Ltd
    IFM = 0x0060              # IFM Electronic
    EPEC = 0x0070             # EPEC Oy
    KONTRON = 0x0080          # Kontron AG
    EATON = 0x0090            # Eaton (Moeller)
    TURCK = 0x00A0            # TURCK
    LENZE = 0x00B0            # Lenze SE
    REXROTH = 0x00C0          # Bosch Rexroth
    PILZ = 0x00D0             # Pilz GmbH
    PHOENIX = 0x00E0          # Phoenix Contact


# Vendor names
CODESYS_VENDOR_NAMES = {
    CodesysVendor.THREE_S: "3S-Smart Software Solutions",
    CodesysVendor.WAGO: "WAGO Kontakttechnik",
    CodesysVendor.BECKHOFF: "Beckhoff Automation",
    CodesysVendor.FESTO: "Festo AG",
    CodesysVendor.SCHNEIDER: "Schneider Electric",
    CodesysVendor.ABB: "ABB Ltd",
    CodesysVendor.IFM: "IFM Electronic",
    CodesysVendor.EPEC: "EPEC Oy",
    CodesysVendor.KONTRON: "Kontron AG",
    CodesysVendor.EATON: "Eaton Corporation",
    CodesysVendor.TURCK: "TURCK",
    CodesysVendor.LENZE: "Lenze SE",
    CodesysVendor.REXROTH: "Bosch Rexroth",
    CodesysVendor.PILZ: "Pilz GmbH",
    CodesysVendor.PHOENIX: "Phoenix Contact",
}


# Common Codesys device models
CODESYS_DEVICE_MODELS = {
    # WAGO
    "WAGO_750_880": {"vendor": CodesysVendor.WAGO, "name": "WAGO 750-880", "type": "PFC100"},
    "WAGO_750_881": {"vendor": CodesysVendor.WAGO, "name": "WAGO 750-881", "type": "PFC100"},
    "WAGO_750_8100": {"vendor": CodesysVendor.WAGO, "name": "WAGO 750-8100", "type": "PFC100"},
    "WAGO_750_8101": {"vendor": CodesysVendor.WAGO, "name": "WAGO 750-8101", "type": "PFC100"},
    "WAGO_750_8102": {"vendor": CodesysVendor.WAGO, "name": "WAGO 750-8102", "type": "PFC200"},
    "WAGO_750_8202": {"vendor": CodesysVendor.WAGO, "name": "WAGO 750-8202", "type": "PFC200"},
    "WAGO_750_8206": {"vendor": CodesysVendor.WAGO, "name": "WAGO 750-8206", "type": "PFC200"},

    # Festo
    "FESTO_CECC_LK": {"vendor": CodesysVendor.FESTO, "name": "Festo CECC-LK", "type": "Compact"},
    "FESTO_CECC_D": {"vendor": CodesysVendor.FESTO, "name": "Festo CECC-D", "type": "Standard"},
    "FESTO_CECC_X": {"vendor": CodesysVendor.FESTO, "name": "Festo CECC-X", "type": "Advanced"},

    # Schneider
    "SCHNEIDER_M241": {"vendor": CodesysVendor.SCHNEIDER, "name": "Modicon M241", "type": "Logic"},
    "SCHNEIDER_M251": {"vendor": CodesysVendor.SCHNEIDER, "name": "Modicon M251", "type": "Logic"},
    "SCHNEIDER_M262": {"vendor": CodesysVendor.SCHNEIDER, "name": "Modicon M262", "type": "Motion"},

    # ABB
    "ABB_AC500": {"vendor": CodesysVendor.ABB, "name": "ABB AC500", "type": "Modular"},
    "ABB_AC500_ECO": {"vendor": CodesysVendor.ABB, "name": "ABB AC500-eCo", "type": "Compact"},

    # IFM
    "IFM_CR0403": {"vendor": CodesysVendor.IFM, "name": "IFM CR0403", "type": "BasicController"},
    "IFM_CR0451": {"vendor": CodesysVendor.IFM, "name": "IFM CR0451", "type": "EcoController"},

    # Generic Codesys Control
    "CODESYS_CONTROL_WIN": {"vendor": CodesysVendor.THREE_S, "name": "CODESYS Control Win V3", "type": "SoftPLC"},
    "CODESYS_CONTROL_RTE": {"vendor": CodesysVendor.THREE_S, "name": "CODESYS Control RTE V3", "type": "SoftPLC"},
    "CODESYS_CONTROL_LINUX": {"vendor": CodesysVendor.THREE_S, "name": "CODESYS Control for Linux", "type": "SoftPLC"},
    "CODESYS_CONTROL_RPI": {"vendor": CodesysVendor.THREE_S, "name": "CODESYS Control for Raspberry Pi", "type": "SoftPLC"},
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class CodesysDeviceIdentity:
    """Codesys device identity information."""
    vendor_id: int = CodesysVendor.THREE_S
    vendor_name: str = "3S-Smart Software Solutions"
    device_name: str = "CODESYS Control"
    device_type: str = "SoftPLC"
    serial_number: str = "00000000"
    firmware_version: str = "3.5.19.0"
    codesys_version: str = "3.5 SP19"
    target_id: int = 0
    target_type: str = "x86"

    def get_version_tuple(self) -> tuple[int, int, int, int]:
        """Parse firmware version to tuple."""
        parts = self.firmware_version.split(".")
        while len(parts) < 4:
            parts.append("0")
        return tuple(int(p) for p in parts[:4])


@dataclass
class CodesysVariable:
    """Codesys variable specification."""
    name: str
    address: int               # Memory address
    data_type: CodesysDataType
    size: int = 0              # Size in bytes (auto-calculated if 0)
    array_size: int = 1        # Array dimension (1 = scalar)

    def __post_init__(self):
        if self.size == 0:
            base_size = DATA_TYPE_SIZES.get(self.data_type, 4)
            self.size = base_size * self.array_size


@dataclass
class CodesysConfig:
    """Configuration for Codesys communication."""
    version: CodesysVersion = CodesysVersion.V3
    port: int = CODESYS_V3_PORT
    require_auth: bool = False
    username: str = ""
    password: str = ""         # Note: Transmitted in plaintext!
    timeout_ms: int = 5000
    max_retries: int = 3


# Note: CodesysConversationState is defined in app.protocol_engines.types
# to be consistent with other protocol conversation states
