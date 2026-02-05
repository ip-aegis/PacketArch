"""SNMP protocol types and constants.

Defines SNMP-specific types, enums, and data structures for
the SNMP/NTCIP protocol engine.
"""

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any


class SNMPVersion(IntEnum):
    """SNMP protocol versions."""

    V1 = 0      # SNMPv1 - most common in legacy traffic systems
    V2C = 1     # SNMPv2c - community-based, most common in ITS
    V3 = 3      # SNMPv3 - authenticated/encrypted


class SNMPOperation(IntEnum):
    """SNMP PDU types (ASN.1 context-specific tags)."""

    GET_REQUEST = 0xA0
    GET_NEXT_REQUEST = 0xA1
    GET_RESPONSE = 0xA2
    SET_REQUEST = 0xA3
    TRAP_V1 = 0xA4
    GET_BULK_REQUEST = 0xA5  # SNMPv2c only
    INFORM_REQUEST = 0xA6   # SNMPv2c only
    TRAP_V2 = 0xA7          # SNMPv2c only
    REPORT = 0xA8           # SNMPv3 only


class SNMPErrorStatus(IntEnum):
    """SNMP error status codes."""

    NO_ERROR = 0
    TOO_BIG = 1
    NO_SUCH_NAME = 2
    BAD_VALUE = 3
    READ_ONLY = 4
    GEN_ERR = 5
    # SNMPv2c additions
    NO_ACCESS = 6
    WRONG_TYPE = 7
    WRONG_LENGTH = 8
    WRONG_ENCODING = 9
    WRONG_VALUE = 10
    NO_CREATION = 11
    INCONSISTENT_VALUE = 12
    RESOURCE_UNAVAILABLE = 13
    COMMIT_FAILED = 14
    UNDO_FAILED = 15
    AUTHORIZATION_ERROR = 16
    NOT_WRITABLE = 17
    INCONSISTENT_NAME = 18


class SNMPValueType(str, Enum):
    """SNMP value types for variable bindings."""

    INTEGER = "integer"
    STRING = "string"
    OID = "oid"
    NULL = "null"
    IP_ADDRESS = "ipaddress"
    COUNTER32 = "counter"
    GAUGE32 = "gauge"
    TIMETICKS = "timeticks"
    OPAQUE = "opaque"
    COUNTER64 = "counter64"
    NO_SUCH_OBJECT = "nosuchobject"
    NO_SUCH_INSTANCE = "nosuchinstance"
    END_OF_MIB_VIEW = "endofmibview"


class SNMPState(str, Enum):
    """SNMP logical conversation states.

    Note: SNMP is stateless (UDP-based), but we track logical
    state for flow management.
    """

    IDLE = "idle"
    DISCOVERING = "discovering"       # Initial OID discovery
    POLLING = "polling"               # Normal poll cycles
    AWAITING_RESPONSE = "awaiting"    # Waiting for response
    TRAP_SENDING = "trap_sending"     # Sending trap notification


class GenericTrapType(IntEnum):
    """SNMPv1 generic trap types."""

    COLD_START = 0          # Agent reinitialized
    WARM_START = 1          # Agent re-initialized without config change
    LINK_DOWN = 2           # Interface down
    LINK_UP = 3             # Interface up
    AUTHENTICATION_FAILURE = 4  # Bad community string
    EGP_NEIGHBOR_LOSS = 5   # EGP neighbor lost
    ENTERPRISE_SPECIFIC = 6  # Vendor-specific trap


# SNMP Network Constants
SNMP_AGENT_PORT = 161
SNMP_TRAP_PORT = 162
SNMP_MAX_MESSAGE_SIZE = 65507  # Max UDP payload


@dataclass
class VarBind:
    """SNMP Variable Binding (OID + value pair)."""

    oid: str
    value: Any
    value_type: str = "auto"  # auto-detect from value type

    def __post_init__(self):
        """Auto-detect value type if not specified."""
        if self.value_type == "auto":
            if self.value is None:
                self.value_type = SNMPValueType.NULL.value
            elif isinstance(self.value, int):
                self.value_type = SNMPValueType.INTEGER.value
            elif isinstance(self.value, str):
                if self.value.count(".") >= 3 and all(
                    p.isdigit() for p in self.value.split(".")[:4]
                ):
                    # Could be OID or IP - check if looks like IP
                    parts = self.value.split(".")
                    if len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts):
                        self.value_type = SNMPValueType.IP_ADDRESS.value
                    else:
                        self.value_type = SNMPValueType.OID.value
                else:
                    self.value_type = SNMPValueType.STRING.value
            elif isinstance(self.value, bytes):
                self.value_type = SNMPValueType.OPAQUE.value
            else:
                self.value_type = SNMPValueType.STRING.value


@dataclass
class SNMPRequest:
    """SNMP request tracking for correlation."""

    request_id: int
    oids: list[str]
    timestamp_ms: float
    operation: SNMPOperation
    retries: int = 0


class SNMPv3SecurityLevel(IntEnum):
    """SNMPv3 security levels."""

    NO_AUTH_NO_PRIV = 1     # noAuthNoPriv - no authentication, no privacy
    AUTH_NO_PRIV = 2        # authNoPriv - authentication only
    AUTH_PRIV = 3           # authPriv - authentication + privacy (encryption)


class SNMPv3AuthProtocol(str, Enum):
    """SNMPv3 authentication protocols."""

    NONE = "none"
    MD5 = "md5"             # HMAC-MD5-96 (deprecated but still used)
    SHA = "sha"             # HMAC-SHA-96 (recommended)
    SHA224 = "sha224"       # HMAC-SHA-224
    SHA256 = "sha256"       # HMAC-SHA-256
    SHA384 = "sha384"       # HMAC-SHA-384
    SHA512 = "sha512"       # HMAC-SHA-512


class SNMPv3PrivProtocol(str, Enum):
    """SNMPv3 privacy (encryption) protocols."""

    NONE = "none"
    DES = "des"             # CBC-DES (deprecated but still used)
    AES128 = "aes128"       # AES-128-CFB (recommended)
    AES192 = "aes192"       # AES-192-CFB
    AES256 = "aes256"       # AES-256-CFB


@dataclass
class SNMPv3Credentials:
    """SNMPv3 USM (User-based Security Model) credentials."""

    username: str
    security_level: SNMPv3SecurityLevel = SNMPv3SecurityLevel.AUTH_NO_PRIV
    auth_protocol: SNMPv3AuthProtocol = SNMPv3AuthProtocol.SHA
    auth_password: str | None = None
    priv_protocol: SNMPv3PrivProtocol = SNMPv3PrivProtocol.NONE
    priv_password: str | None = None
    # Engine discovery data (populated during discovery)
    engine_id: bytes | None = None
    engine_boots: int = 0
    engine_time: int = 0
    context_name: str = ""

    def validate(self) -> list[str]:
        """Validate credentials configuration."""
        errors = []
        if not self.username:
            errors.append("username is required for SNMPv3")
        if self.security_level >= SNMPv3SecurityLevel.AUTH_NO_PRIV:
            if not self.auth_password:
                errors.append("auth_password required for authentication")
            if self.auth_protocol == SNMPv3AuthProtocol.NONE:
                errors.append("auth_protocol required for authentication")
        if self.security_level >= SNMPv3SecurityLevel.AUTH_PRIV:
            if not self.priv_password:
                errors.append("priv_password required for privacy")
            if self.priv_protocol == SNMPv3PrivProtocol.NONE:
                errors.append("priv_protocol required for privacy")
        return errors


@dataclass
class SNMPFlowConfig:
    """Configuration for an SNMP flow."""

    community: str = "public"
    version: SNMPVersion = SNMPVersion.V2C
    timeout_ms: int = 5000
    retries: int = 2
    poll_oids: list[str] = field(default_factory=list)
    bulk_max_repetitions: int = 10  # For GetBulk
    trap_community: str = "public"
    trap_destination: str | None = None
    # SNMPv3-specific configuration
    v3_credentials: SNMPv3Credentials | None = None


# ASN.1 BER Tag Constants
class ASN1Tag(IntEnum):
    """ASN.1 BER encoding tags."""

    BOOLEAN = 0x01
    INTEGER = 0x02
    BIT_STRING = 0x03
    OCTET_STRING = 0x04
    NULL = 0x05
    OBJECT_IDENTIFIER = 0x06
    SEQUENCE = 0x30
    IP_ADDRESS = 0x40      # Application 0
    COUNTER32 = 0x41       # Application 1
    GAUGE32 = 0x42         # Application 2
    TIMETICKS = 0x43       # Application 3
    OPAQUE = 0x44          # Application 4
    COUNTER64 = 0x46       # Application 6
    NO_SUCH_OBJECT = 0x80  # Context 0
    NO_SUCH_INSTANCE = 0x81  # Context 1
    END_OF_MIB_VIEW = 0x82   # Context 2
