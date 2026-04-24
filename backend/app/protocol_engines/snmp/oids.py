# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""SNMP OID definitions and utilities.

Standard MIB-II OIDs and helpers for OID manipulation.
Also includes NTCIP base OID definitions.
"""

from dataclasses import dataclass
from typing import Any, Callable


# Standard MIB OID Bases
ISO = "1"
ORG = f"{ISO}.3"
DOD = f"{ORG}.6"
INTERNET = f"{DOD}.1"
MGMT = f"{INTERNET}.2"
MIB2 = f"{MGMT}.1"
ENTERPRISES = f"{INTERNET}.4.1"

# NTCIP Enterprise Base (NEMA)
NEMA_ENTERPRISE = f"{ENTERPRISES}.1206"
NTCIP_DEVICES = f"{NEMA_ENTERPRISE}.4"
NTCIP_GLOBAL = f"{NTCIP_DEVICES}.2.1"       # NTCIP 1201 - Global Objects
NTCIP_ASC = f"{NTCIP_DEVICES}.2.2"          # NTCIP 1202 - Traffic Signal Controllers
NTCIP_DMS = f"{NTCIP_DEVICES}.2.3"          # NTCIP 1203 - Dynamic Message Signs
NTCIP_ESS = f"{NTCIP_DEVICES}.2.4"          # NTCIP 1204 - Environmental Sensors
NTCIP_CCTV = f"{NTCIP_DEVICES}.2.5"         # NTCIP 1205 - CCTV
NTCIP_RAMP_METER = f"{NTCIP_DEVICES}.2.6"   # NTCIP 1206 - Ramp Metering
NTCIP_TSS = f"{NTCIP_DEVICES}.2.10"         # NTCIP 1209 - Transportation Sensors


@dataclass
class OIDDefinition:
    """Definition of an SNMP OID with metadata."""

    oid: str
    name: str
    description: str
    value_type: str  # integer, string, timeticks, counter, gauge, oid, etc.
    access: str      # read-only, read-write, not-accessible
    default_value: Any = None
    value_generator: Callable[[], Any] | None = None


class SystemOIDs:
    """Standard MIB-II System group OIDs (1.3.6.1.2.1.1)."""

    SYS_DESCR = OIDDefinition(
        oid=f"{MIB2}.1.1.0",
        name="sysDescr",
        description="Full product description string - used by Cyber Vision for device identification",
        value_type="string",
        access="read-only",
    )

    SYS_OBJECT_ID = OIDDefinition(
        oid=f"{MIB2}.1.2.0",
        name="sysObjectID",
        description="Vendor's authoritative OID identifying the device type",
        value_type="oid",
        access="read-only",
    )

    SYS_UPTIME = OIDDefinition(
        oid=f"{MIB2}.1.3.0",
        name="sysUpTime",
        description="Time since system reinitialization (hundredths of seconds)",
        value_type="timeticks",
        access="read-only",
    )

    SYS_CONTACT = OIDDefinition(
        oid=f"{MIB2}.1.4.0",
        name="sysContact",
        description="Contact person for this managed node",
        value_type="string",
        access="read-write",
    )

    SYS_NAME = OIDDefinition(
        oid=f"{MIB2}.1.5.0",
        name="sysName",
        description="Administratively-assigned name for this node",
        value_type="string",
        access="read-write",
    )

    SYS_LOCATION = OIDDefinition(
        oid=f"{MIB2}.1.6.0",
        name="sysLocation",
        description="Physical location of this node",
        value_type="string",
        access="read-write",
    )

    SYS_SERVICES = OIDDefinition(
        oid=f"{MIB2}.1.7.0",
        name="sysServices",
        description="Services offered by this device (OSI layer bitmask)",
        value_type="integer",
        access="read-only",
        default_value=72,  # Typical for network device (layers 4+7)
    )

    # List of all system OIDs for discovery
    ALL = [
        SYS_DESCR,
        SYS_OBJECT_ID,
        SYS_UPTIME,
        SYS_CONTACT,
        SYS_NAME,
        SYS_LOCATION,
        SYS_SERVICES,
    ]


class InterfaceOIDs:
    """MIB-II Interfaces group OIDs (1.3.6.1.2.1.2)."""

    IF_NUMBER = OIDDefinition(
        oid=f"{MIB2}.2.1.0",
        name="ifNumber",
        description="Number of network interfaces",
        value_type="integer",
        access="read-only",
        default_value=1,
    )

    # ifTable entries (indexed by interface number)
    IF_INDEX = f"{MIB2}.2.2.1.1"      # Interface index
    IF_DESCR = f"{MIB2}.2.2.1.2"      # Interface description
    IF_TYPE = f"{MIB2}.2.2.1.3"       # Interface type
    IF_MTU = f"{MIB2}.2.2.1.4"        # MTU size
    IF_SPEED = f"{MIB2}.2.2.1.5"      # Bandwidth in bits/sec
    IF_PHYS_ADDRESS = f"{MIB2}.2.2.1.6"  # MAC address
    IF_ADMIN_STATUS = f"{MIB2}.2.2.1.7"  # Admin status
    IF_OPER_STATUS = f"{MIB2}.2.2.1.8"   # Operational status
    IF_IN_OCTETS = f"{MIB2}.2.2.1.10"    # Bytes received
    IF_OUT_OCTETS = f"{MIB2}.2.2.1.16"   # Bytes sent


# SNMP Trap OIDs
SNMP_TRAP_OID = f"{INTERNET}.6.3.1.1.4.1.0"  # snmpTrapOID.0
SNMP_TRAP_ENTERPRISE = f"{INTERNET}.6.3.1.1.4.3.0"  # snmpTrapEnterprise.0

# Standard enterprise OIDs for traffic control vendors
VENDOR_ENTERPRISE_OIDS = {
    "nema": NEMA_ENTERPRISE,
    "ntcip": NTCIP_DEVICES,
    "siemens": f"{ENTERPRISES}.4329",
    "siemens_traffic": f"{ENTERPRISES}.4329.6",
    "econolite": f"{ENTERPRISES}.1206.4.2",  # Uses NTCIP base
    "mccain": f"{ENTERPRISES}.1206.4.2",     # Uses NTCIP base
    "peek_traffic": f"{ENTERPRISES}.1206.4.2",
    "trafficware": f"{ENTERPRISES}.1206",
    "kapsch": f"{ENTERPRISES}.22706",
    "q_free": f"{ENTERPRISES}.32055",
    "daktronics": f"{ENTERPRISES}.2407",
    "axis": f"{ENTERPRISES}.368",
    "pelco": f"{ENTERPRISES}.17685",
    "hikvision": f"{ENTERPRISES}.39165",
    "bosch": f"{ENTERPRISES}.3246",
    "flir": f"{ENTERPRISES}.28846",
    "wavetronix": f"{ENTERPRISES}.34362",
}


def encode_oid(oid_str: str) -> bytes:
    """Encode OID string to ASN.1 BER format.

    Args:
        oid_str: OID in dot notation (e.g., "1.3.6.1.2.1.1.1.0")

    Returns:
        BER-encoded OID bytes (without tag and length)
    """
    parts = [int(x) for x in oid_str.split(".")]

    if len(parts) < 2:
        raise ValueError(f"Invalid OID: {oid_str}")

    # First two components are encoded as (first * 40) + second
    result = bytes([parts[0] * 40 + parts[1]])

    for part in parts[2:]:
        if part < 128:
            result += bytes([part])
        else:
            # Multi-byte encoding for values >= 128
            encoded = []
            val = part
            while val > 0:
                encoded.insert(0, (val & 0x7F) | (0x80 if encoded else 0x00))
                val >>= 7
            result += bytes(encoded)

    return result


def decode_oid(data: bytes) -> str:
    """Decode BER-encoded OID to string.

    Args:
        data: BER-encoded OID bytes (without tag and length)

    Returns:
        OID in dot notation
    """
    if not data:
        return ""

    # First byte encodes first two components
    first = data[0] // 40
    second = data[0] % 40
    parts = [str(first), str(second)]

    i = 1
    while i < len(data):
        val = 0
        while i < len(data):
            byte = data[i]
            val = (val << 7) | (byte & 0x7F)
            i += 1
            if not (byte & 0x80):
                break
        parts.append(str(val))

    return ".".join(parts)


def is_child_of(child_oid: str, parent_oid: str) -> bool:
    """Check if child OID is under parent OID tree.

    Args:
        child_oid: Potential child OID
        parent_oid: Parent OID prefix

    Returns:
        True if child is under parent
    """
    return child_oid.startswith(parent_oid + ".") or child_oid == parent_oid


def get_next_oid(oid: str, oid_tree: list[str]) -> str | None:
    """Get lexicographically next OID in tree.

    Args:
        oid: Current OID
        oid_tree: Sorted list of available OIDs

    Returns:
        Next OID or None if at end
    """
    sorted_tree = sorted(oid_tree, key=lambda x: [int(p) for p in x.split(".")])

    for tree_oid in sorted_tree:
        tree_parts = [int(p) for p in tree_oid.split(".")]
        oid_parts = [int(p) for p in oid.split(".")]

        # Compare lexicographically
        if tree_parts > oid_parts:
            return tree_oid

    return None


# Default OIDs to poll for system discovery
DISCOVERY_OIDS = [
    SystemOIDs.SYS_DESCR.oid,
    SystemOIDs.SYS_OBJECT_ID.oid,
    SystemOIDs.SYS_UPTIME.oid,
    SystemOIDs.SYS_NAME.oid,
    SystemOIDs.SYS_LOCATION.oid,
]

# Default OIDs for traffic controller polling
TRAFFIC_CONTROLLER_POLL_OIDS = [
    f"{NTCIP_ASC}.1.4.1.0",   # phaseStatusGroupReds
    f"{NTCIP_ASC}.1.4.2.0",   # phaseStatusGroupYellows
    f"{NTCIP_ASC}.1.4.3.0",   # phaseStatusGroupGreens
    f"{NTCIP_ASC}.1.4.7.0",   # phaseStatusGroupVehCalls
    f"{NTCIP_ASC}.3.1.0",     # currentTimingPlan
    f"{NTCIP_ASC}.3.3.0",     # localCycleCounter
]

# Default OIDs for DMS polling
DMS_POLL_OIDS = [
    f"{NTCIP_DMS}.5.1.0",     # dmsMessageStatus
    f"{NTCIP_DMS}.5.3.0",     # dmsMessageMultiString
    f"{NTCIP_DMS}.9.3.0",     # dmsLampStatus
    f"{NTCIP_DMS}.9.6.0",     # dmsAmbientTemperature
    f"{NTCIP_DMS}.7.2.0",     # dmsIllumBrightLevelStatus
]
