"""BACnet protocol types, constants, and data structures.

Defines BACnet-specific types, enums, and data structures for
the BACnet/IP protocol engine used in Building Management Systems.
"""

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any


# ============================================================================
# Network Constants
# ============================================================================

BACNET_PORT = 47808  # 0xBAC0 - default BACnet/IP port
BACNET_BVLC_TYPE = 0x81  # BACnet Virtual Link Control type


# ============================================================================
# BVLC (BACnet Virtual Link Control) Types
# ============================================================================

class BVLCFunction(IntEnum):
    """BVLC function types for BACnet/IP."""

    RESULT = 0x00
    WRITE_BROADCAST_DIST_TABLE = 0x01
    READ_BROADCAST_DIST_TABLE = 0x02
    READ_BROADCAST_DIST_TABLE_ACK = 0x03
    FORWARDED_NPDU = 0x04
    REGISTER_FOREIGN_DEVICE = 0x05
    READ_FOREIGN_DEVICE_TABLE = 0x06
    READ_FOREIGN_DEVICE_TABLE_ACK = 0x07
    DELETE_FOREIGN_DEVICE_TABLE_ENTRY = 0x08
    DISTRIBUTE_BROADCAST_TO_NETWORK = 0x09
    ORIGINAL_UNICAST_NPDU = 0x0A
    ORIGINAL_BROADCAST_NPDU = 0x0B


class BVLCResult(IntEnum):
    """BVLC result codes."""

    SUCCESSFUL_COMPLETION = 0x00
    WRITE_BROADCAST_DIST_TABLE_NAK = 0x10
    READ_BROADCAST_DIST_TABLE_NAK = 0x20
    REGISTER_FOREIGN_DEVICE_NAK = 0x30
    READ_FOREIGN_DEVICE_TABLE_NAK = 0x40
    DELETE_FOREIGN_DEVICE_TABLE_NAK = 0x50
    DISTRIBUTE_BROADCAST_NAK = 0x60


# ============================================================================
# NPDU (Network Protocol Data Unit) Types
# ============================================================================

class NPDUNetworkPriority(IntEnum):
    """NPDU network message priority."""

    NORMAL = 0
    URGENT = 1
    CRITICAL_EQUIPMENT = 2
    LIFE_SAFETY = 3


class NPDUMessageType(IntEnum):
    """NPDU network layer message types."""

    WHO_IS_ROUTER_TO_NETWORK = 0x00
    I_AM_ROUTER_TO_NETWORK = 0x01
    I_COULD_BE_ROUTER_TO_NETWORK = 0x02
    REJECT_MESSAGE_TO_NETWORK = 0x03
    ROUTER_BUSY_TO_NETWORK = 0x04
    ROUTER_AVAILABLE_TO_NETWORK = 0x05
    INIT_ROUTING_TABLE = 0x06
    INIT_ROUTING_TABLE_ACK = 0x07
    ESTABLISH_CONNECTION_TO_NETWORK = 0x08
    DISCONNECT_CONNECTION_TO_NETWORK = 0x09
    WHAT_IS_NETWORK_NUMBER = 0x12
    NETWORK_NUMBER_IS = 0x13


# ============================================================================
# APDU (Application Protocol Data Unit) Types
# ============================================================================

class BACnetPDUType(IntEnum):
    """BACnet PDU types (bits 4-7 of first APDU octet)."""

    CONFIRMED_REQUEST = 0
    UNCONFIRMED_REQUEST = 1
    SIMPLE_ACK = 2
    COMPLEX_ACK = 3
    SEGMENT_ACK = 4
    ERROR = 5
    REJECT = 6
    ABORT = 7


class BACnetUnconfirmedService(IntEnum):
    """BACnet unconfirmed service choices."""

    I_AM = 0
    I_HAVE = 1
    UNCONFIRMED_COV_NOTIFICATION = 2
    UNCONFIRMED_EVENT_NOTIFICATION = 3
    UNCONFIRMED_PRIVATE_TRANSFER = 4
    UNCONFIRMED_TEXT_MESSAGE = 5
    TIME_SYNCHRONIZATION = 6
    WHO_HAS = 7
    WHO_IS = 8
    UTC_TIME_SYNCHRONIZATION = 9
    WRITE_GROUP = 10


class BACnetConfirmedService(IntEnum):
    """BACnet confirmed service choices."""

    ACKNOWLEDGE_ALARM = 0
    CONFIRMED_COV_NOTIFICATION = 1
    CONFIRMED_EVENT_NOTIFICATION = 2
    GET_ALARM_SUMMARY = 3
    GET_ENROLLMENT_SUMMARY = 4
    SUBSCRIBE_COV = 5
    ATOMIC_READ_FILE = 6
    ATOMIC_WRITE_FILE = 7
    ADD_LIST_ELEMENT = 8
    REMOVE_LIST_ELEMENT = 9
    CREATE_OBJECT = 10
    DELETE_OBJECT = 11
    READ_PROPERTY = 12
    READ_PROPERTY_CONDITIONAL = 13  # Removed in Rev 1
    READ_PROPERTY_MULTIPLE = 14
    WRITE_PROPERTY = 15
    WRITE_PROPERTY_MULTIPLE = 16
    DEVICE_COMMUNICATION_CONTROL = 17
    CONFIRMED_PRIVATE_TRANSFER = 18
    CONFIRMED_TEXT_MESSAGE = 19
    REINITIALIZE_DEVICE = 20
    VT_OPEN = 21
    VT_CLOSE = 22
    VT_DATA = 23
    AUTHENTICATE = 24  # Removed in Rev 1
    REQUEST_KEY = 25   # Removed in Rev 1
    READ_RANGE = 26
    LIFE_SAFETY_OPERATION = 27
    SUBSCRIBE_COV_PROPERTY = 28
    GET_EVENT_INFORMATION = 29


# ============================================================================
# BACnet Object Types
# ============================================================================

class BACnetObjectType(IntEnum):
    """BACnet object types."""

    ANALOG_INPUT = 0
    ANALOG_OUTPUT = 1
    ANALOG_VALUE = 2
    BINARY_INPUT = 3
    BINARY_OUTPUT = 4
    BINARY_VALUE = 5
    CALENDAR = 6
    COMMAND = 7
    DEVICE = 8
    EVENT_ENROLLMENT = 9
    FILE = 10
    GROUP = 11
    LOOP = 12
    MULTI_STATE_INPUT = 13
    MULTI_STATE_OUTPUT = 14
    NOTIFICATION_CLASS = 15
    PROGRAM = 16
    SCHEDULE = 17
    AVERAGING = 18
    MULTI_STATE_VALUE = 19
    TREND_LOG = 20
    LIFE_SAFETY_POINT = 21
    LIFE_SAFETY_ZONE = 22
    ACCUMULATOR = 23
    PULSE_CONVERTER = 24
    EVENT_LOG = 25
    GLOBAL_GROUP = 26
    TREND_LOG_MULTIPLE = 27
    LOAD_CONTROL = 28
    STRUCTURED_VIEW = 29
    ACCESS_DOOR = 30
    # Newer object types...
    TIMER = 31
    ACCESS_CREDENTIAL = 32
    ACCESS_POINT = 33
    ACCESS_RIGHTS = 34
    ACCESS_USER = 35
    ACCESS_ZONE = 36
    CREDENTIAL_DATA_INPUT = 37
    NETWORK_SECURITY = 38
    BITSTRING_VALUE = 39
    CHARACTERSTRING_VALUE = 40
    DATE_PATTERN_VALUE = 41
    DATE_VALUE = 42
    DATETIME_PATTERN_VALUE = 43
    DATETIME_VALUE = 44
    INTEGER_VALUE = 45
    LARGE_ANALOG_VALUE = 46
    OCTETSTRING_VALUE = 47
    POSITIVE_INTEGER_VALUE = 48
    TIME_PATTERN_VALUE = 49
    TIME_VALUE = 50
    NOTIFICATION_FORWARDER = 51
    ALERT_ENROLLMENT = 52
    CHANNEL = 53
    LIGHTING_OUTPUT = 54


# ============================================================================
# BACnet Property Identifiers
# ============================================================================

class BACnetPropertyIdentifier(IntEnum):
    """BACnet property identifiers (common subset)."""

    # Device Object Properties
    ACKED_TRANSITIONS = 0
    ACK_REQUIRED = 1
    ACTION = 2
    ACTION_TEXT = 3
    ACTIVE_TEXT = 4
    ACTIVE_VT_SESSIONS = 5
    ALARM_VALUE = 6
    ALARM_VALUES = 7
    ALL = 8
    ALL_WRITES_SUCCESSFUL = 9
    APDU_SEGMENT_TIMEOUT = 10
    APDU_TIMEOUT = 11
    APPLICATION_SOFTWARE_VERSION = 12
    ARCHIVE = 13
    BIAS = 14
    CHANGE_OF_STATE_COUNT = 15
    CHANGE_OF_STATE_TIME = 16
    NOTIFICATION_CLASS = 17
    CONTROLLED_VARIABLE_REFERENCE = 19
    CONTROLLED_VARIABLE_UNITS = 20
    CONTROLLED_VARIABLE_VALUE = 21
    COV_INCREMENT = 22
    DATELIST = 23
    DAYLIGHT_SAVINGS_STATUS = 24
    DEADBAND = 25
    DERIVATIVE_CONSTANT = 26
    DERIVATIVE_CONSTANT_UNITS = 27
    DESCRIPTION = 28
    DESCRIPTION_OF_HALT = 29
    DEVICE_ADDRESS_BINDING = 30
    DEVICE_TYPE = 31
    EFFECTIVE_PERIOD = 32
    ELAPSED_ACTIVE_TIME = 33
    ERROR_LIMIT = 34
    EVENT_ENABLE = 35
    EVENT_STATE = 36
    EVENT_TYPE = 37
    EXCEPTION_SCHEDULE = 38
    FAULT_VALUES = 39
    FEEDBACK_VALUE = 40
    FILE_ACCESS_METHOD = 41
    FILE_SIZE = 42
    FILE_TYPE = 43
    FIRMWARE_REVISION = 44
    HIGH_LIMIT = 45
    INACTIVE_TEXT = 46
    IN_PROCESS = 47
    INSTANCE_OF = 48
    INTEGRAL_CONSTANT = 49
    INTEGRAL_CONSTANT_UNITS = 50
    LIMIT_ENABLE = 52
    LIST_OF_GROUP_MEMBERS = 53
    LIST_OF_OBJECT_PROPERTY_REFERENCES = 54
    LOCAL_DATE = 56
    LOCAL_TIME = 57
    LOCATION = 58
    LOW_LIMIT = 59
    MANIPULATED_VARIABLE_REFERENCE = 60
    MAX_APDU_LENGTH_ACCEPTED = 62
    MAX_INFO_FRAMES = 63
    MAX_MASTER = 64
    MAX_PRES_VALUE = 65
    MIN_OFF_TIME = 66
    MIN_ON_TIME = 67
    MIN_PRES_VALUE = 68
    MODEL_NAME = 70
    MODIFICATION_DATE = 71
    NOTIFY_TYPE = 72
    NUMBER_OF_APDU_RETRIES = 73
    NUMBER_OF_STATES = 74
    OBJECT_IDENTIFIER = 75
    OBJECT_LIST = 76
    OBJECT_NAME = 77
    OBJECT_PROPERTY_REFERENCE = 78
    OBJECT_TYPE = 79
    OPTIONAL = 80
    OUT_OF_SERVICE = 81
    OUTPUT_UNITS = 82
    EVENT_PARAMETERS = 83
    POLARITY = 84
    PRESENT_VALUE = 85
    PRIORITY = 86
    PRIORITY_ARRAY = 87
    PRIORITY_FOR_WRITING = 88
    PROCESS_IDENTIFIER = 89
    PROGRAM_CHANGE = 90
    PROGRAM_LOCATION = 91
    PROGRAM_STATE = 92
    PROPORTIONAL_CONSTANT = 93
    PROPORTIONAL_CONSTANT_UNITS = 94
    PROTOCOL_OBJECT_TYPES_SUPPORTED = 96
    PROTOCOL_SERVICES_SUPPORTED = 97
    PROTOCOL_VERSION = 98
    READ_ONLY = 99
    REASON_FOR_HALT = 100
    RECIPIENT_LIST = 102
    RELIABILITY = 103
    RELINQUISH_DEFAULT = 104
    REQUIRED = 105
    RESOLUTION = 106
    SEGMENTATION_SUPPORTED = 107
    SETPOINT = 108
    SETPOINT_REFERENCE = 109
    STATE_TEXT = 110
    STATUS_FLAGS = 111
    SYSTEM_STATUS = 112
    TIME_DELAY = 113
    TIME_OF_ACTIVE_TIME_RESET = 114
    TIME_OF_STATE_COUNT_RESET = 115
    TIME_SYNCHRONIZATION_RECIPIENTS = 116
    UNITS = 117
    UPDATE_INTERVAL = 118
    UTC_OFFSET = 119
    VENDOR_IDENTIFIER = 120
    VENDOR_NAME = 121
    VT_CLASSES_SUPPORTED = 122
    WEEKLY_SCHEDULE = 123
    ATTEMPTED_SAMPLES = 124
    AVERAGE_VALUE = 125
    BUFFER_SIZE = 126
    CLIENT_COV_INCREMENT = 127
    COV_RESUBSCRIPTION_INTERVAL = 128
    EVENT_TIME_STAMPS = 130
    LOG_BUFFER = 131
    LOG_DEVICE_OBJECT_PROPERTY = 132
    ENABLE = 133
    LOG_INTERVAL = 134
    MAXIMUM_VALUE = 135
    MINIMUM_VALUE = 136
    NOTIFICATION_THRESHOLD = 137
    PROTOCOL_REVISION = 139
    RECORDS_SINCE_NOTIFICATION = 140
    RECORD_COUNT = 141
    START_TIME = 142
    STOP_TIME = 143
    STOP_WHEN_FULL = 144
    TOTAL_RECORD_COUNT = 145
    VALID_SAMPLES = 146
    WINDOW_INTERVAL = 147
    WINDOW_SAMPLES = 148
    MAXIMUM_VALUE_TIMESTAMP = 149
    MINIMUM_VALUE_TIMESTAMP = 150
    VARIANCE_VALUE = 151
    ACTIVE_COV_SUBSCRIPTIONS = 152
    BACKUP_FAILURE_TIMEOUT = 153
    CONFIGURATION_FILES = 154
    DATABASE_REVISION = 155
    DIRECT_READING = 156
    LAST_RESTORE_TIME = 157
    MAINTENANCE_REQUIRED = 158
    MEMBER_OF = 159
    MODE = 160
    OPERATION_EXPECTED = 161
    SETTING = 162
    SILENCED = 163
    TRACKING_VALUE = 164
    ZONE_MEMBERS = 165
    LIFE_SAFETY_ALARM_VALUES = 166
    MAX_SEGMENTS_ACCEPTED = 167
    PROFILE_NAME = 168


# ============================================================================
# BACnet Segmentation Support
# ============================================================================

class BACnetSegmentation(IntEnum):
    """BACnet segmentation support enumeration."""

    SEGMENTED_BOTH = 0
    SEGMENTED_TRANSMIT = 1
    SEGMENTED_RECEIVE = 2
    NO_SEGMENTATION = 3


# ============================================================================
# BACnet Device Status
# ============================================================================

class BACnetDeviceStatus(IntEnum):
    """BACnet device status enumeration."""

    OPERATIONAL = 0
    OPERATIONAL_READ_ONLY = 1
    DOWNLOAD_REQUIRED = 2
    DOWNLOAD_IN_PROGRESS = 3
    NON_OPERATIONAL = 4
    BACKUP_IN_PROGRESS = 5


# ============================================================================
# BACnet Reliability
# ============================================================================

class BACnetReliability(IntEnum):
    """BACnet reliability enumeration."""

    NO_FAULT_DETECTED = 0
    NO_SENSOR = 1
    OVER_RANGE = 2
    UNDER_RANGE = 3
    OPEN_LOOP = 4
    SHORTED_LOOP = 5
    NO_OUTPUT = 6
    UNRELIABLE_OTHER = 7
    PROCESS_ERROR = 8
    MULTI_STATE_FAULT = 9
    CONFIGURATION_ERROR = 10


# ============================================================================
# BACnet Error Classes and Codes
# ============================================================================

class BACnetErrorClass(IntEnum):
    """BACnet error class enumeration."""

    DEVICE = 0
    OBJECT = 1
    PROPERTY = 2
    RESOURCES = 3
    SECURITY = 4
    SERVICES = 5
    VT = 6
    COMMUNICATION = 7


class BACnetErrorCode(IntEnum):
    """BACnet error code enumeration (common subset)."""

    OTHER = 0
    CONFIGURATION_IN_PROGRESS = 2
    DEVICE_BUSY = 3
    DYNAMIC_CREATION_NOT_SUPPORTED = 4
    FILE_ACCESS_DENIED = 5
    INCONSISTENT_PARAMETERS = 7
    INCONSISTENT_SELECTION_CRITERION = 8
    INVALID_DATA_TYPE = 9
    INVALID_FILE_ACCESS_METHOD = 10
    INVALID_FILE_START_POSITION = 11
    INVALID_PARAMETER_DATA_TYPE = 13
    INVALID_TIME_STAMP = 14
    MISSING_REQUIRED_PARAMETER = 16
    NO_OBJECTS_OF_SPECIFIED_TYPE = 17
    NO_SPACE_FOR_OBJECT = 18
    NO_SPACE_TO_ADD_LIST_ELEMENT = 19
    NO_SPACE_TO_WRITE_PROPERTY = 20
    NO_VT_SESSIONS_AVAILABLE = 21
    PROPERTY_IS_NOT_A_LIST = 22
    OBJECT_DELETION_NOT_PERMITTED = 23
    OBJECT_IDENTIFIER_ALREADY_EXISTS = 24
    OPERATIONAL_PROBLEM = 25
    PASSWORD_FAILURE = 26
    READ_ACCESS_DENIED = 27
    SERVICE_REQUEST_DENIED = 29
    TIMEOUT = 30
    UNKNOWN_OBJECT = 31
    UNKNOWN_PROPERTY = 32
    UNKNOWN_VT_CLASS = 34
    UNKNOWN_VT_SESSION = 35
    UNSUPPORTED_OBJECT_TYPE = 36
    VALUE_OUT_OF_RANGE = 37
    VT_SESSION_ALREADY_CLOSED = 38
    VT_SESSION_TERMINATION_FAILURE = 39
    WRITE_ACCESS_DENIED = 40
    CHARACTER_SET_NOT_SUPPORTED = 41
    INVALID_ARRAY_INDEX = 42


# ============================================================================
# BACnet Reject and Abort Reasons
# ============================================================================

class BACnetRejectReason(IntEnum):
    """BACnet reject reason codes."""

    OTHER = 0
    BUFFER_OVERFLOW = 1
    INCONSISTENT_PARAMETERS = 2
    INVALID_PARAMETER_DATA_TYPE = 3
    INVALID_TAG = 4
    MISSING_REQUIRED_PARAMETER = 5
    PARAMETER_OUT_OF_RANGE = 6
    TOO_MANY_ARGUMENTS = 7
    UNDEFINED_ENUMERATION = 8
    UNRECOGNIZED_SERVICE = 9


class BACnetAbortReason(IntEnum):
    """BACnet abort reason codes."""

    OTHER = 0
    BUFFER_OVERFLOW = 1
    INVALID_APDU_IN_THIS_STATE = 2
    PREEMPTED_BY_HIGHER_PRIORITY_TASK = 3
    SEGMENTATION_NOT_SUPPORTED = 4
    SECURITY_ERROR = 5
    INSUFFICIENT_SECURITY = 6
    WINDOW_SIZE_OUT_OF_RANGE = 7
    APPLICATION_EXCEEDED_REPLY_TIME = 8
    OUT_OF_RESOURCES = 9
    TSM_TIMEOUT = 10
    APDU_TOO_LONG = 11


# ============================================================================
# ASN.1/BER Tag Constants for BACnet
# ============================================================================

class BACnetApplicationTag(IntEnum):
    """BACnet application tags (ASN.1)."""

    NULL = 0
    BOOLEAN = 1
    UNSIGNED_INT = 2
    SIGNED_INT = 3
    REAL = 4
    DOUBLE = 5
    OCTET_STRING = 6
    CHARACTER_STRING = 7
    BIT_STRING = 8
    ENUMERATED = 9
    DATE = 10
    TIME = 11
    BACNET_OBJECT_IDENTIFIER = 12


# ============================================================================
# Engine State Machine
# ============================================================================

class BACnetState(str, Enum):
    """BACnet engine state machine states."""

    IDLE = "idle"
    DISCOVERING = "discovering"
    AWAITING_RESPONSE = "awaiting_response"
    POLLING = "polling"
    ERROR = "error"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class BACnetObjectIdentifier:
    """BACnet Object Identifier (type + instance)."""

    object_type: BACnetObjectType
    instance: int

    def __post_init__(self):
        """Validate object identifier."""
        if not 0 <= self.instance <= 0x3FFFFF:
            raise ValueError(f"Instance must be 0-4194303, got {self.instance}")

    def encode(self) -> int:
        """Encode to 32-bit value (10 bits type, 22 bits instance)."""
        return (int(self.object_type) << 22) | self.instance

    @classmethod
    def decode(cls, value: int) -> "BACnetObjectIdentifier":
        """Decode from 32-bit value."""
        obj_type = (value >> 22) & 0x3FF
        instance = value & 0x3FFFFF
        return cls(BACnetObjectType(obj_type), instance)


@dataclass
class BACnetFlowConfig:
    """Configuration for a BACnet flow."""

    device_instance: int = 0
    vendor_id: int = 0
    poll_objects: list[tuple[int, int]] = field(default_factory=list)  # (type, instance)
    poll_properties: list[int] = field(default_factory=lambda: [
        BACnetPropertyIdentifier.PRESENT_VALUE,
        BACnetPropertyIdentifier.STATUS_FLAGS,
    ])
    timeout_ms: int = 3000
    retries: int = 3
    invoke_id_start: int = 1
    max_apdu_length: int = 1476
    segmentation: BACnetSegmentation = BACnetSegmentation.NO_SEGMENTATION
    generate_who_is: bool = True  # Generate Who-Is in startup sequence


@dataclass
class BACnetPropertyValue:
    """Property value with type information."""

    value: Any
    property_type: str = "auto"  # auto, unsigned, signed, real, string, enumerated, etc.


# ============================================================================
# Registered BACnet Vendor IDs
# ============================================================================

BACNET_VENDOR_IDS = {
    # Major BMS Vendors
    5: "Johnson Controls",
    17: "Honeywell",
    24: "Siemens",
    67: "Schneider Electric",
    86: "Automated Logic",
    95: "TAC (Schneider)",
    97: "Trane",
    122: "Delta Controls",
    165: "Distech Controls",
    200: "KMC Controls",
    236: "Alerton",
    252: "Continental Automated Buildings Association",
    260: "Carel Industries",
    279: "Carrier",
    301: "Carrier Corp.",
    317: "Reliable Controls",
    353: "Lennox",
    381: "McQuay",
    416: "Novar (Honeywell)",
    438: "Computrols",
    489: "Contemporary Controls",
}


# ============================================================================
# BACnet Units (Engineering Units)
# ============================================================================

class BACnetUnits(IntEnum):
    """BACnet engineering units (common subset)."""

    # Temperature
    DEGREES_CELSIUS = 62
    DEGREES_FAHRENHEIT = 64
    DEGREES_KELVIN = 63

    # Pressure
    PASCALS = 53
    KILOPASCALS = 54
    BARS = 55
    PSI = 56
    INCHES_OF_WATER = 57

    # Flow
    CUBIC_FEET_PER_MINUTE = 84
    LITERS_PER_SECOND = 85

    # Humidity
    PERCENT_RELATIVE_HUMIDITY = 29
    PERCENT = 98

    # Energy
    KILOWATT_HOURS = 19
    BTU = 20

    # Power
    WATTS = 47
    KILOWATTS = 48

    # Speed
    REVOLUTIONS_PER_MINUTE = 104

    # Misc
    NO_UNITS = 95
