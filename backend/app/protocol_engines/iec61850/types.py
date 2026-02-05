"""IEC 61850 protocol types and constants.

Defines data types, enums, and structures for IEC 61850 protocols
including MMS, GOOSE, and Sampled Values.
"""

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any


# =============================================================================
# IEC 61850 EtherTypes and Ports
# =============================================================================

GOOSE_ETHERTYPE = 0x88B8  # GOOSE protocol
SV_ETHERTYPE = 0x88BA     # Sampled Values protocol
MMS_PORT = 102            # MMS over ISO/TCP (same as COTP)


# =============================================================================
# GOOSE Constants
# =============================================================================

class GOOSEAppID:
    """GOOSE Application ID ranges."""
    MIN = 0x0000
    MAX = 0x3FFF


# GOOSE multicast MAC address prefix (01-0C-CD-01-xx-xx)
GOOSE_MULTICAST_PREFIX = "01:0C:CD:01"


class GOOSEDataType(IntEnum):
    """GOOSE data type encodings (ASN.1 tags)."""
    BOOLEAN = 0x83
    BIT_STRING = 0x84
    INTEGER = 0x85
    UNSIGNED = 0x86
    FLOATING_POINT = 0x87
    REAL = 0x87
    OCTET_STRING = 0x89
    VISIBLE_STRING = 0x8A
    BCD = 0x8C
    BOOLEAN_ARRAY = 0x8D
    OBJECT_NAME = 0x8E
    DATA_TIME = 0x91
    STRUCTURE = 0xA2
    ARRAY = 0xA1


# =============================================================================
# Sampled Values Constants
# =============================================================================

class SVAppID:
    """Sampled Values Application ID ranges."""
    MIN = 0x4000
    MAX = 0x7FFF


# SV multicast MAC address prefix (01-0C-CD-04-xx-xx)
SV_MULTICAST_PREFIX = "01:0C:CD:04"


class SVSmpCnt:
    """SV sample count values per cycle for different sampling rates."""
    SAMPLES_80 = 80      # 80 samples/cycle (4kHz at 50Hz)
    SAMPLES_256 = 256    # 256 samples/cycle (12.8kHz at 50Hz)
    SAMPLES_4000 = 4000  # 4000 samples/cycle (200kHz at 50Hz, IEC 61869-9)


class SVDataType(IntEnum):
    """SV data types."""
    INT8 = 1
    INT16 = 2
    INT24 = 3
    INT32 = 4
    INT64 = 8
    FLOAT32 = 4
    FLOAT64 = 8


# =============================================================================
# MMS Constants
# =============================================================================

class MMSPduType(IntEnum):
    """MMS PDU types (ASN.1 context tags)."""
    CONFIRMED_REQUEST = 0xA0
    CONFIRMED_RESPONSE = 0xA1
    CONFIRMED_ERROR = 0xA2
    UNCONFIRMED = 0xA3
    REJECT = 0xA4
    CANCEL_REQUEST = 0xA5
    CANCEL_RESPONSE = 0xA6
    CANCEL_ERROR = 0xA7
    INITIATE_REQUEST = 0xA8
    INITIATE_RESPONSE = 0xA9
    INITIATE_ERROR = 0xAA
    CONCLUDE_REQUEST = 0xAB
    CONCLUDE_RESPONSE = 0xAC
    CONCLUDE_ERROR = 0xAD


class MMSServiceType(IntEnum):
    """MMS confirmed service types."""
    GET_NAME_LIST = 1
    IDENTIFY = 2
    RENAME = 3
    READ = 4
    WRITE = 5
    GET_VARIABLE_ACCESS_ATTRIBUTES = 6
    DEFINE_NAMED_VARIABLE = 7
    DELETE_VARIABLE_ACCESS = 8
    DEFINE_NAMED_VARIABLE_LIST = 9
    GET_NAMED_VARIABLE_LIST_ATTRIBUTES = 10
    DELETE_NAMED_VARIABLE_LIST = 11
    DEFINE_NAMED_TYPE = 12
    GET_NAMED_TYPE_ATTRIBUTES = 13
    DELETE_NAMED_TYPE = 14
    INPUT = 15
    OUTPUT = 16
    TAKE_CONTROL = 17
    RELINQUISH_CONTROL = 18
    DEFINE_SEMAPHORE = 19
    DELETE_SEMAPHORE = 20
    REPORT_SEMAPHORE_STATUS = 21
    REPORT_POOL_SEMAPHORE_STATUS = 22
    REPORT_SEMAPHORE_ENTRY_STATUS = 23
    INITIATE_DOWNLOAD_SEQUENCE = 24
    DOWNLOAD_SEGMENT = 25
    TERMINATE_DOWNLOAD_SEQUENCE = 26
    INITIATE_UPLOAD_SEQUENCE = 27
    UPLOAD_SEGMENT = 28
    TERMINATE_UPLOAD_SEQUENCE = 29
    REQUEST_DOMAIN_DOWNLOAD = 30
    REQUEST_DOMAIN_UPLOAD = 31
    LOAD_DOMAIN_CONTENT = 32
    STORE_DOMAIN_CONTENT = 33
    DELETE_DOMAIN = 34
    GET_DOMAIN_ATTRIBUTES = 35
    CREATE_PROGRAM_INVOCATION = 36
    DELETE_PROGRAM_INVOCATION = 37
    START = 38
    STOP = 39
    RESUME = 40
    RESET = 41
    KILL = 42
    GET_PROGRAM_INVOCATION_ATTRIBUTES = 43
    OBTAIN_FILE = 44
    DEFINE_EVENT_CONDITION = 45
    DELETE_EVENT_CONDITION = 46
    GET_EVENT_CONDITION_ATTRIBUTES = 47
    REPORT_EVENT_CONDITION_STATUS = 48
    ALTER_EVENT_CONDITION_MONITORING = 49
    TRIGGER_EVENT = 50
    DEFINE_EVENT_ACTION = 51
    DELETE_EVENT_ACTION = 52
    GET_EVENT_ACTION_ATTRIBUTES = 53
    REPORT_EVENT_ACTION_STATUS = 54
    DEFINE_EVENT_ENROLLMENT = 55
    DELETE_EVENT_ENROLLMENT = 56
    ALTER_EVENT_ENROLLMENT = 57
    REPORT_EVENT_ENROLLMENT_STATUS = 58
    GET_EVENT_ENROLLMENT_ATTRIBUTES = 59
    ACKNOWLEDGE_EVENT_NOTIFICATION = 60
    GET_ALARM_SUMMARY = 61
    GET_ALARM_ENROLLMENT_SUMMARY = 62
    READ_JOURNAL = 63
    WRITE_JOURNAL = 64
    INITIALIZE_JOURNAL = 65
    REPORT_JOURNAL_STATUS = 66
    CREATE_JOURNAL = 67
    DELETE_JOURNAL = 68
    GET_CAPABILITY_LIST = 69
    FILE_OPEN = 70
    FILE_READ = 71
    FILE_CLOSE = 72
    FILE_RENAME = 73
    FILE_DELETE = 74
    FILE_DIRECTORY = 75
    ADDITIONAL_SERVICE = 76


class MMSObjectClass(IntEnum):
    """MMS object classes for GetNameList."""
    NAMED_VARIABLE = 0
    SCATTER_ACCESS = 1
    NAMED_VARIABLE_LIST = 2
    NAMED_TYPE = 3
    SEMAPHORE = 4
    EVENT_CONDITION = 5
    EVENT_ACTION = 6
    EVENT_ENROLLMENT = 7
    JOURNAL = 8
    DOMAIN = 9
    PROGRAM_INVOCATION = 10
    OPERATOR_STATION = 11


class MMSDataAccessError(IntEnum):
    """MMS data access error codes."""
    OBJECT_INVALIDATED = 0
    HARDWARE_FAULT = 1
    TEMPORARILY_UNAVAILABLE = 2
    OBJECT_ACCESS_DENIED = 3
    OBJECT_UNDEFINED = 4
    INVALID_ADDRESS = 5
    TYPE_UNSUPPORTED = 6
    TYPE_INCONSISTENT = 7
    OBJECT_ATTRIBUTE_INCONSISTENT = 8
    OBJECT_ACCESS_UNSUPPORTED = 9
    OBJECT_NONEXISTENT = 10
    OBJECT_VALUE_INVALID = 11


# =============================================================================
# IEC 61850 Data Model Types
# =============================================================================

class FCType(str, Enum):
    """IEC 61850 Functional Constraints."""
    ST = "ST"   # Status
    MX = "MX"   # Measurand
    SP = "SP"   # Setpoint
    SV = "SV"   # Substitution
    CF = "CF"   # Configuration
    DC = "DC"   # Description
    SG = "SG"   # Setting Group
    SE = "SE"   # Setting Group Editable
    SR = "SR"   # Service Response
    OR = "OR"   # Operate Received
    BL = "BL"   # Blocking
    EX = "EX"   # Extended Definition
    CO = "CO"   # Control


class TriggerOptionType(IntEnum):
    """Trigger options for reporting/GOOSE."""
    DATA_CHANGE = 0x01
    QUALITY_CHANGE = 0x02
    DATA_UPDATE = 0x04
    INTEGRITY = 0x08
    GENERAL_INTERROGATION = 0x10


class QualityFlags(IntEnum):
    """IEC 61850 quality flags."""
    GOOD = 0x0000
    INVALID = 0x0001
    QUESTIONABLE = 0x0002
    OVERFLOW = 0x0004
    OUT_OF_RANGE = 0x0008
    BAD_REFERENCE = 0x0010
    OSCILLATORY = 0x0020
    FAILURE = 0x0040
    OLD_DATA = 0x0080
    INCONSISTENT = 0x0100
    INACCURATE = 0x0200


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class GOOSEConfig:
    """GOOSE publisher/subscriber configuration."""
    gocb_ref: str  # GOOSE Control Block reference
    dat_set: str   # Dataset reference
    go_id: str     # GOOSE ID
    app_id: int    # Application ID
    conf_rev: int = 1  # Configuration revision
    needs_comm: bool = True
    multicast_addr: str = ""  # Auto-generated if empty
    vlan_id: int | None = None
    vlan_priority: int = 4  # Default GOOSE priority


@dataclass
class SVConfig:
    """Sampled Values publisher configuration."""
    sv_id: str           # SV ID
    dat_set: str         # Dataset reference
    app_id: int          # Application ID
    conf_rev: int = 1    # Configuration revision
    smp_rate: int = 80   # Samples per cycle
    smp_mod: int = 0     # Sample mode (0=per nominal period)
    multicast_addr: str = ""
    vlan_id: int | None = None
    vlan_priority: int = 4


@dataclass
class MMSConfig:
    """MMS connection configuration."""
    remote_ap_title: list[int] = field(default_factory=lambda: [1, 1, 1, 999, 1])
    remote_ae_qualifier: int = 12
    local_ap_title: list[int] = field(default_factory=lambda: [1, 1, 1, 999, 2])
    local_ae_qualifier: int = 12
    max_pdu_size: int = 65000
    max_calling_connections: int = 10
    max_called_connections: int = 10


@dataclass
class DataAttribute:
    """IEC 61850 data attribute."""
    name: str
    fc: FCType
    value: Any
    quality: int = QualityFlags.GOOD
    timestamp: float | None = None


@dataclass
class DataObject:
    """IEC 61850 data object (DO)."""
    name: str
    cdc: str  # Common Data Class (SPS, DPS, INS, MV, CMV, etc.)
    attributes: list[DataAttribute] = field(default_factory=list)


@dataclass
class LogicalNode:
    """IEC 61850 Logical Node (LN)."""
    ln_class: str  # e.g., XCBR, CSWI, MMXU
    ln_inst: int   # Instance number
    data_objects: list[DataObject] = field(default_factory=list)

    @property
    def name(self) -> str:
        return f"{self.ln_class}{self.ln_inst}"


@dataclass
class LogicalDevice:
    """IEC 61850 Logical Device (LD)."""
    name: str
    logical_nodes: list[LogicalNode] = field(default_factory=list)


# Note: IEC61850ConversationState is defined in app.protocol_engines.types
# to be consistent with other protocol conversation states
