"""Live traffic orchestrator - injects packets onto network interface."""

import heapq
import logging
import random
import struct
import time
from dataclasses import dataclass, field
from typing import Any

from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Raw
from scapy.sendrecv import sendp

# EtherNet/IP constants
ENIP_CMD_LIST_IDENTITY = 0x0063
ENIP_CMD_REGISTER_SESSION = 0x0065
ENIP_CMD_SEND_RR_DATA = 0x006F
CIP_SERVICE_GET_ATTRIBUTE_ALL = 0x01
CIP_CLASS_IDENTITY = 0x01

# PROFINET constants
PROFINET_ETHERTYPE = 0x8892
DCP_SERVICE_IDENTIFY = 0x05
DCP_SERVICE_TYPE_REQUEST = 0x00
DCP_SERVICE_TYPE_RESPONSE = 0x01
DCP_MULTICAST_MAC = "01:0E:CF:00:00:00"

# SNMP constants
SNMP_AGENT_PORT = 161
SNMP_TRAP_PORT = 162
SNMP_VERSION_1 = 0
SNMP_VERSION_2C = 1

# SNMP PDU types
SNMP_GET_REQUEST = 0xA0
SNMP_GET_NEXT_REQUEST = 0xA1
SNMP_GET_RESPONSE = 0xA2
SNMP_SET_REQUEST = 0xA3
SNMP_TRAP_V1 = 0xA4
SNMP_GET_BULK = 0xA5
SNMP_INFORM = 0xA6
SNMP_TRAP_V2 = 0xA7

# Standard MIB-II OIDs
SNMP_OIDS = {
    "sysDescr": "1.3.6.1.2.1.1.1.0",
    "sysObjectID": "1.3.6.1.2.1.1.2.0",
    "sysUpTime": "1.3.6.1.2.1.1.3.0",
    "sysContact": "1.3.6.1.2.1.1.4.0",
    "sysName": "1.3.6.1.2.1.1.5.0",
    "sysLocation": "1.3.6.1.2.1.1.6.0",
    "sysServices": "1.3.6.1.2.1.1.7.0",
}

# BACnet constants
BACNET_PORT = 47808  # 0xBAC0
BACNET_BVLC_TYPE = 0x81

# BVLC Function Types
BVLC_RESULT = 0x00
BVLC_ORIGINAL_UNICAST_NPDU = 0x0A
BVLC_ORIGINAL_BROADCAST_NPDU = 0x0B

# BACnet PDU Types
BACNET_PDU_UNCONFIRMED_REQUEST = 0x10
BACNET_PDU_CONFIRMED_REQUEST = 0x00
BACNET_PDU_COMPLEX_ACK = 0x30

# BACnet Services
BACNET_SERVICE_I_AM = 0x00
BACNET_SERVICE_WHO_IS = 0x08
BACNET_SERVICE_READ_PROPERTY = 0x0C

# BACnet Object Types
BACNET_OBJ_ANALOG_INPUT = 0
BACNET_OBJ_ANALOG_OUTPUT = 1
BACNET_OBJ_ANALOG_VALUE = 2
BACNET_OBJ_BINARY_INPUT = 3
BACNET_OBJ_BINARY_OUTPUT = 4
BACNET_OBJ_BINARY_VALUE = 5
BACNET_OBJ_DEVICE = 8

# BACnet Property IDs
BACNET_PROP_PRESENT_VALUE = 85
BACNET_PROP_OBJECT_NAME = 77
BACNET_PROP_VENDOR_ID = 120
BACNET_PROP_VENDOR_NAME = 121
BACNET_PROP_MODEL_NAME = 70
BACNET_PROP_FIRMWARE_REVISION = 44
BACNET_PROP_SYSTEM_STATUS = 112

# BACnet Segmentation
BACNET_SEG_BOTH = 0
BACNET_SEG_TRANSMIT = 1
BACNET_SEG_RECEIVE = 2
BACNET_SEG_NONE = 3

# DNP3 constants
DNP3_PORT = 20000
DNP3_START_BYTES = b"\x05\x64"

# DNP3 Function codes
DNP3_FC_READ = 0x01
DNP3_FC_RESPONSE = 0x81
DNP3_FC_UNSOLICITED_RESPONSE = 0x82

# DNP3 Object groups
DNP3_GROUP_BINARY_INPUT = 1
DNP3_GROUP_BINARY_OUTPUT = 10
DNP3_GROUP_COUNTER = 20
DNP3_GROUP_ANALOG_INPUT = 30
DNP3_GROUP_ANALOG_OUTPUT = 40
DNP3_GROUP_CLASS = 60

# DNP3 Qualifier codes
DNP3_QC_RANGE_START_STOP = 0x00
DNP3_QC_ALL_OBJECTS = 0x06

# DNP3 CRC table (polynomial 0x3D65)
DNP3_CRC_TABLE = [
    0x0000, 0x365E, 0x6CBC, 0x5AE2, 0xD978, 0xEF26, 0xB5C4, 0x839A,
    0xFF89, 0xC9D7, 0x9335, 0xA56B, 0x26F1, 0x10AF, 0x4A4D, 0x7C13,
    0xB26B, 0x8435, 0xDED7, 0xE889, 0x6B13, 0x5D4D, 0x07AF, 0x31F1,
    0x4DE2, 0x7BBC, 0x215E, 0x1700, 0x949A, 0xA2C4, 0xF826, 0xCE78,
    0x29AF, 0x1FF1, 0x4513, 0x734D, 0xF0D7, 0xC689, 0x9C6B, 0xAA35,
    0xD626, 0xE078, 0xBA9A, 0x8CC4, 0x0F5E, 0x3900, 0x63E2, 0x55BC,
    0x9BC4, 0xAD9A, 0xF778, 0xC126, 0x42BC, 0x74E2, 0x2E00, 0x185E,
    0x644D, 0x5213, 0x08F1, 0x3EAF, 0xBD35, 0x8B6B, 0xD189, 0xE7D7,
    0x535E, 0x6500, 0x3FE2, 0x09BC, 0x8A26, 0xBC78, 0xE69A, 0xD0C4,
    0xACD7, 0x9A89, 0xC06B, 0xF635, 0x75AF, 0x43F1, 0x1913, 0x2F4D,
    0xE135, 0xD76B, 0x8D89, 0xBBD7, 0x384D, 0x0E13, 0x54F1, 0x62AF,
    0x1EBC, 0x28E2, 0x7200, 0x445E, 0xC7C4, 0xF19A, 0xAB78, 0x9D26,
    0x7AF1, 0x4CAF, 0x164D, 0x2013, 0xA389, 0x95D7, 0xCF35, 0xF96B,
    0x8578, 0xB326, 0xE9C4, 0xDF9A, 0x5C00, 0x6A5E, 0x30BC, 0x06E2,
    0xC89A, 0xFEC4, 0xA426, 0x9278, 0x11E2, 0x27BC, 0x7D5E, 0x4B00,
    0x3713, 0x014D, 0x5BAF, 0x6DF1, 0xEE6B, 0xD835, 0x82D7, 0xB489,
    0xA6BC, 0x90E2, 0xCA00, 0xFC5E, 0x7FC4, 0x499A, 0x1378, 0x2526,
    0x5935, 0x6F6B, 0x3589, 0x03D7, 0x804D, 0xB613, 0xECF1, 0xDAAF,
    0x14D7, 0x2289, 0x786B, 0x4E35, 0xCDAF, 0xFBF1, 0xA113, 0x974D,
    0xEB5E, 0xDD00, 0x87E2, 0xB1BC, 0x3226, 0x0478, 0x5E9A, 0x68C4,
    0x8F13, 0xB94D, 0xE3AF, 0xD5F1, 0x566B, 0x6035, 0x3AD7, 0x0C89,
    0x709A, 0x46C4, 0x1C26, 0x2A78, 0xA9E2, 0x9FBC, 0xC55E, 0xF300,
    0x3D78, 0x0B26, 0x51C4, 0x679A, 0xE400, 0xD25E, 0x88BC, 0xBEE2,
    0xC2F1, 0xF4AF, 0xAE4D, 0x9813, 0x1B89, 0x2DD7, 0x7735, 0x416B,
    0xF5E2, 0xC3BC, 0x995E, 0xAF00, 0x2C9A, 0x1AC4, 0x4026, 0x7678,
    0x0A6B, 0x3C35, 0x66D7, 0x5089, 0xD313, 0xE54D, 0xBFAF, 0x89F1,
    0x4789, 0x71D7, 0x2B35, 0x1D6B, 0x9EF1, 0xA8AF, 0xF24D, 0xC413,
    0xB800, 0x8E5E, 0xD4BC, 0xE2E2, 0x6178, 0x5726, 0x0DC4, 0x3B9A,
    0xDC4D, 0xEA13, 0xB0F1, 0x86AF, 0x0535, 0x336B, 0x6989, 0x5FD7,
    0x23C4, 0x159A, 0x4F78, 0x7926, 0xFABC, 0xCCE2, 0x9600, 0xA05E,
    0x6E26, 0x5878, 0x029A, 0x34C4, 0xB75E, 0x8100, 0xDBE2, 0xEDBC,
    0x91AF, 0xA7F1, 0xFD13, 0xCB4D, 0x48D7, 0x7E89, 0x246B, 0x1235,
]

# IEC 60870-5-104 constants
IEC104_PORT = 2404
IEC104_START_BYTE = 0x68

# IEC 104 U-format control bytes
IEC104_STARTDT_ACT = 0x07
IEC104_STARTDT_CON = 0x0B
IEC104_STOPDT_ACT = 0x13
IEC104_STOPDT_CON = 0x23
IEC104_TESTFR_ACT = 0x43
IEC104_TESTFR_CON = 0x83

# IEC 104 Type identifiers (monitor direction)
IEC104_M_SP_NA_1 = 1    # Single-point information
IEC104_M_DP_NA_1 = 3    # Double-point information
IEC104_M_ME_NA_1 = 9    # Measured value, normalized
IEC104_M_ME_NB_1 = 11   # Measured value, scaled
IEC104_M_ME_NC_1 = 13   # Measured value, short floating point
IEC104_M_IT_NA_1 = 15   # Integrated totals

# IEC 104 Type identifiers (control direction)
IEC104_C_SC_NA_1 = 45   # Single command
IEC104_C_DC_NA_1 = 46   # Double command
IEC104_C_IC_NA_1 = 100  # Interrogation command

# IEC 104 Cause of transmission (COT)
IEC104_COT_PERIODIC = 1
IEC104_COT_SPONTANEOUS = 3
IEC104_COT_ACTIVATION = 6
IEC104_COT_ACTIVATION_CON = 7
IEC104_COT_ACTIVATION_TERM = 10
IEC104_COT_INTERROGATION = 20

# OPC UA constants
OPCUA_PORT = 4840
OPCUA_PROTOCOL_VERSION = 0

# OPC UA Message Types
OPCUA_MSG_HELLO = b"HEL"
OPCUA_MSG_ACK = b"ACK"
OPCUA_MSG_ERROR = b"ERR"
OPCUA_MSG_OPEN = b"OPN"
OPCUA_MSG_CLOSE = b"CLO"
OPCUA_MSG_MESSAGE = b"MSG"
OPCUA_MSG_FINAL = b"F"
OPCUA_MSG_CHUNK = b"C"
OPCUA_MSG_ABORT = b"A"

# OPC UA Security Policies
OPCUA_SECURITY_NONE = "http://opcfoundation.org/UA/SecurityPolicy#None"

# OPC UA Service IDs (Request/Response pairs differ by 3)
OPCUA_SERVICE_GET_ENDPOINTS_REQUEST = 428
OPCUA_SERVICE_GET_ENDPOINTS_RESPONSE = 431
OPCUA_SERVICE_OPEN_SECURE_CHANNEL_REQUEST = 446
OPCUA_SERVICE_OPEN_SECURE_CHANNEL_RESPONSE = 449
OPCUA_SERVICE_CLOSE_SECURE_CHANNEL_REQUEST = 452
OPCUA_SERVICE_CREATE_SESSION_REQUEST = 461
OPCUA_SERVICE_CREATE_SESSION_RESPONSE = 464
OPCUA_SERVICE_ACTIVATE_SESSION_REQUEST = 467
OPCUA_SERVICE_ACTIVATE_SESSION_RESPONSE = 470
OPCUA_SERVICE_CLOSE_SESSION_REQUEST = 473
OPCUA_SERVICE_CLOSE_SESSION_RESPONSE = 476
OPCUA_SERVICE_CREATE_SUBSCRIPTION_REQUEST = 787
OPCUA_SERVICE_CREATE_SUBSCRIPTION_RESPONSE = 790
OPCUA_SERVICE_DELETE_SUBSCRIPTIONS_REQUEST = 848
OPCUA_SERVICE_DELETE_SUBSCRIPTIONS_RESPONSE = 851
OPCUA_SERVICE_CREATE_MONITORED_ITEMS_REQUEST = 751
OPCUA_SERVICE_CREATE_MONITORED_ITEMS_RESPONSE = 754
OPCUA_SERVICE_PUBLISH_REQUEST = 826
OPCUA_SERVICE_PUBLISH_RESPONSE = 829
OPCUA_SERVICE_READ_REQUEST = 631
OPCUA_SERVICE_READ_RESPONSE = 634
OPCUA_SERVICE_BROWSE_REQUEST = 527
OPCUA_SERVICE_BROWSE_RESPONSE = 530

# OPC UA Node IDs (common)
OPCUA_NODE_SERVER_STATE = 2259
OPCUA_NODE_SERVER_STATUS = 2256
OPCUA_NODE_SERVICE_LEVEL = 2267

# OPC UA Message Security Mode
OPCUA_MSG_SECURITY_NONE = 1
OPCUA_MSG_SECURITY_SIGN = 2
OPCUA_MSG_SECURITY_SIGN_ENCRYPT = 3

# S7comm constants (Siemens S7 protocol)
S7_PORT = 102  # ISO-on-TCP

# TPKT header (RFC 1006)
TPKT_VERSION = 0x03

# COTP (ISO 8073) PDU types
COTP_PDU_CR = 0xE0  # Connection Request
COTP_PDU_CC = 0xD0  # Connection Confirm
COTP_PDU_DT = 0xF0  # Data Transfer

# S7comm PDU types
S7_PDU_JOB = 0x01
S7_PDU_ACK = 0x02
S7_PDU_ACK_DATA = 0x03
S7_PDU_USERDATA = 0x07

# S7comm function codes
S7_FUNC_SETUP_COMM = 0xF0
S7_FUNC_READ_VAR = 0x04
S7_FUNC_WRITE_VAR = 0x05

# S7comm Userdata function groups
S7_UD_FUNCGROUP_CPU = 0x04
S7_UD_SUBFUNCTION_READ_SZL = 0x01

# SZL (System Status List) IDs
SZL_ID_MODULE_ID = 0x0011  # Module identification
SZL_ID_COMPONENT_ID = 0x001C  # Component identification

# LLDP (Link Layer Discovery Protocol) constants
LLDP_ETHERTYPE = 0x88CC
LLDP_MULTICAST_MAC = "01:80:C2:00:00:0E"  # Standard LLDP multicast

# LLDP TLV Types
LLDP_TLV_END = 0
LLDP_TLV_CHASSIS_ID = 1
LLDP_TLV_PORT_ID = 2
LLDP_TLV_TTL = 3
LLDP_TLV_PORT_DESC = 4
LLDP_TLV_SYSTEM_NAME = 5
LLDP_TLV_SYSTEM_DESC = 6
LLDP_TLV_SYSTEM_CAP = 7
LLDP_TLV_MGMT_ADDR = 8
LLDP_TLV_ORG_SPECIFIC = 127

# LLDP Chassis ID Subtypes
LLDP_CHASSIS_SUBTYPE_MAC = 4
LLDP_CHASSIS_SUBTYPE_NETWORK_ADDR = 5

# LLDP Port ID Subtypes
LLDP_PORT_SUBTYPE_MAC = 3
LLDP_PORT_SUBTYPE_INTERFACE_NAME = 5

# PROFINET OUI for organization-specific TLVs
PROFINET_OUI = bytes([0x00, 0x0E, 0xCF])

# Siemens OUI for organization-specific TLVs
SIEMENS_OUI = bytes([0x00, 0x0E, 0x8C])

logger = logging.getLogger(__name__)


# =============================================================================
# Validation Helpers
# =============================================================================

def _validate_uint16(value: Any, field_name: str, default: int = 0) -> int:
    """Validate and clamp a value to unsigned 16-bit range (0-65535).

    This prevents struct.pack overflow errors when packing protocol identity
    fields like vendor_id, device_id, product_code into 'H' format.

    Args:
        value: The value to validate (can be int, str, or None)
        field_name: Name of the field (for logging)
        default: Default value if validation fails

    Returns:
        Integer value clamped to 0-65535 range
    """
    try:
        num = int(value) if value is not None else default
        if num < 0 or num > 65535:
            logger.warning(
                f"Value {num} for {field_name} exceeds uint16 range (0-65535), "
                f"clamping to {min(max(num, 0), 65535)}"
            )
            return min(max(num, 0), 65535)
        return num
    except (ValueError, TypeError):
        logger.warning(f"Invalid value '{value}' for {field_name}, using default {default}")
        return default


def _validate_uint8(value: Any, field_name: str, default: int = 0) -> int:
    """Validate and clamp a value to unsigned 8-bit range (0-255).

    Args:
        value: The value to validate
        field_name: Name of the field (for logging)
        default: Default value if validation fails

    Returns:
        Integer value clamped to 0-255 range
    """
    try:
        num = int(value) if value is not None else default
        if num < 0 or num > 255:
            logger.warning(
                f"Value {num} for {field_name} exceeds uint8 range (0-255), "
                f"clamping to {min(max(num, 0), 255)}"
            )
            return min(max(num, 0), 255)
        return num
    except (ValueError, TypeError):
        logger.warning(f"Invalid value '{value}' for {field_name}, using default {default}")
        return default


@dataclass
class DeviceContext:
    """Context information for a device in a flow."""
    device_id: str
    mac_address: str
    ip_address: str
    port: int
    unit_id: int = 1
    vendor_fingerprint: dict[str, Any] = field(default_factory=dict)
    vulnerability_override: dict[str, Any] | None = None
    # Device name for unique network identifiers (PROFINET station_name, S7 plc_name, etc.)
    device_name: str | None = None
    # Scenario ID for deterministic unique identifier generation
    scenario_id: str | None = None

    def get_effective_identity(self, identity_type: str) -> dict[str, Any]:
        """Get effective protocol identity with vulnerability overrides applied.

        This merges base fingerprint identity with any CVE vulnerability overrides,
        ensuring protocol responses include vulnerable firmware versions for
        Cyber Vision detection.

        IMPORTANT: Preserves device-specific fields (product_name, serial_number, etc.)
        from the base identity - only firmware version fields are overridden from CVE data.

        Args:
            identity_type: Identity type key (e.g., "bacnet_identity", "snmp_identity")

        Returns:
            Merged identity dict with vulnerability overrides applied
        """
        base_identity = dict(self.vendor_fingerprint.get(identity_type, {}))

        # Apply vulnerability override if present
        if self.vulnerability_override:
            # Support both naming conventions:
            # - bacnet_identity_override (from DB model)
            # - bacnet_identity (from extract_identity_overrides)
            override_key = f"{identity_type}_override"
            alt_key = identity_type
            override = (
                self.vulnerability_override.get(override_key) or
                self.vulnerability_override.get(alt_key)
            )
            if override:
                # Fields to PRESERVE from base identity (device-specific, not CVE-related)
                # These are unique per device and should not be overwritten by CVE templates
                preserve_fields = {
                    "product_name",      # Device name shown in Cyber Vision
                    "serial_number",     # Unique device serial
                    "object_name",       # BACnet object name
                    "station_name",      # PROFINET station name
                    "sys_name",          # SNMP system name
                    "plc_name",          # S7 PLC name
                }

                # Only apply override fields that are NOT in the preserve list
                filtered_override = {
                    k: v for k, v in override.items()
                    if k not in preserve_fields
                }

                base_identity.update(filtered_override)
                logger.info(f"CVE OVERRIDE APPLIED for {identity_type}: {list(filtered_override.keys())} (preserved: {preserve_fields & set(override.keys())})")

        return base_identity


@dataclass
class FlowContext:
    """Context for a communication flow between devices."""
    flow_id: str
    source: DeviceContext
    destination: DeviceContext
    protocol: str
    config: dict[str, Any] = field(default_factory=dict)
    timing_model: dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowState:
    """State tracking for a flow during generation."""
    flow: FlowContext
    transaction_id: int = 0
    seq_number: int = 1000
    ack_number: int = 1000
    next_poll_time: float = 0.0
    is_started: bool = False
    poll_interval_ms: float = 1000.0
    custom_data: dict[str, Any] = field(default_factory=dict)


# Protocol to identity key mapping (local copy - must match backend/app/protocol_engines/protocols.py)
PROTOCOL_TO_IDENTITY_KEY: dict[str, str] = {
    "modbus": "modbus_identity",
    "modbus_tcp": "modbus_identity",
    "ethernet_ip": "ethernet_ip_identity",
    "enip": "ethernet_ip_identity",
    "cip": "cip_identity_object",
    "profinet": "profinet_identity",
    "profisafe": "profinet_identity",
    "s7comm": "s7_identity",
    "s7comm_plus": "s7_identity",
    "s7": "s7_identity",
    "bacnet": "bacnet_identity",
    "bacnet_ip": "bacnet_identity",
    "snmp": "snmp_identity",
    "opc_ua": "opc_ua_identity",
    "dnp3": "dnp3_identity",
    "iec104": "iec104_identity",
}


def device_supports_protocol(device: DeviceContext, protocol: str) -> bool:
    """Check if device supports a protocol using supported_protocols field.

    Uses the explicit supported_protocols declaration as the authoritative
    source. Falls back to checking identity existence for backward compatibility.

    Args:
        device: DeviceContext with vendor_fingerprint
        protocol: Protocol name (e.g., "ethernet_ip", "profinet")

    Returns:
        True if device supports the protocol
    """
    fingerprint = device.vendor_fingerprint
    if not fingerprint:
        return False

    # Check explicit supported_protocols first (authoritative)
    supported = fingerprint.get("supported_protocols", [])
    if supported:
        return protocol in supported

    # Fallback: infer from identity existence (backward compatibility)
    identity_key = PROTOCOL_TO_IDENTITY_KEY.get(protocol)
    if identity_key:
        identity = fingerprint.get(identity_key)
        return bool(identity and isinstance(identity, dict))

    return False


class LiveTrafficOrchestrator:
    """Orchestrates live traffic injection across multiple flows."""

    def __init__(self, interface: str, duration_ms: int | None):
        """Initialize orchestrator.

        Args:
            interface: Network interface for packet injection
            duration_ms: Total duration in milliseconds, or None for perpetual mode
        """
        self.interface = interface
        self.duration_ms = duration_ms
        self.perpetual = duration_ms is None
        self.flows: list[FlowState] = []
        self.all_devices: list[DeviceContext] = []  # ALL devices in scenario (for discovery)
        self.event_queue: list[tuple[float, int, Any]] = []  # (time_ms, counter, event)
        self.event_counter = 0
        self.packets_sent = 0
        self.start_time: float = 0
        self._running = True  # Flag for graceful shutdown

    def add_flow(self, flow_context: FlowContext) -> None:
        """Add a flow to be generated."""
        poll_interval = flow_context.timing_model.get("poll_interval_ms", 1000.0)

        flow_state = FlowState(
            flow=flow_context,
            poll_interval_ms=poll_interval,
            seq_number=random.randint(1000, 50000),
            ack_number=random.randint(1000, 50000),
        )

        self.flows.append(flow_state)
        logger.info(f"Added flow {flow_context.flow_id} ({flow_context.protocol}) interval={poll_interval}ms")

    def set_all_devices(self, devices: list[DeviceContext]) -> None:
        """Set all devices in the scenario for comprehensive discovery.

        This ensures devices that are not part of any flow still get discovery
        packets generated, allowing Cyber Vision to see their full identity.

        Args:
            devices: List of all DeviceContext objects in the scenario
        """
        self.all_devices = devices
        logger.info(f"Registered {len(devices)} devices for discovery")

    def _schedule_event(self, time_ms: float, event: Any) -> None:
        """Schedule an event at a specific time."""
        heapq.heappush(self.event_queue, (time_ms, self.event_counter, event))
        self.event_counter += 1

    def _apply_jitter(self, interval_ms: float, timing_model: dict) -> float:
        """Apply jitter to an interval."""
        jitter_min = timing_model.get("jitter_min_ms", 0)
        jitter_max = timing_model.get("jitter_max_ms", 50)
        jitter = random.uniform(jitter_min, jitter_max)
        return interval_ms + jitter

    def _send_packet(self, packet_bytes: bytes) -> None:
        """Send a packet on the interface."""
        try:
            # packet_bytes is already a complete Ethernet frame from _build_tcp_packet
            # Use Raw to send the bytes directly without additional parsing
            sendp(Raw(packet_bytes), iface=self.interface, verbose=False)
            self.packets_sent += 1

            if self.packets_sent % 100 == 0:
                logger.info(f"Sent {self.packets_sent} packets")
        except Exception as e:
            logger.error(f"Failed to send packet: {e}")

    def _build_tcp_packet(
        self,
        src: DeviceContext,
        dst: DeviceContext,
        payload: bytes,
        seq: int,
        ack: int,
        flags: str = "PA",
    ) -> bytes:
        """Build a TCP packet with full headers."""
        packet = (
            Ether(src=src.mac_address, dst=dst.mac_address)
            / IP(src=src.ip_address, dst=dst.ip_address)
            / TCP(sport=src.port, dport=dst.port, seq=seq, ack=ack, flags=flags)
        )
        if payload:
            packet = packet / Raw(load=payload)
        return bytes(packet)

    def _build_modbus_request(
        self, transaction_id: int, unit_id: int, function_code: int,
        start_addr: int, quantity: int
    ) -> bytes:
        """Build a Modbus TCP request."""
        pdu = struct.pack(">BHH", function_code, start_addr, quantity)
        length = len(pdu) + 1
        mbap = struct.pack(">HHHB", transaction_id, 0, length, unit_id)
        return mbap + pdu

    def _build_modbus_response(
        self, transaction_id: int, unit_id: int, function_code: int,
        register_values: list[int]
    ) -> bytes:
        """Build a Modbus TCP response."""
        byte_count = len(register_values) * 2
        data = struct.pack(">" + "H" * len(register_values), *register_values)
        pdu = struct.pack(">BB", function_code, byte_count) + data
        length = len(pdu) + 1
        mbap = struct.pack(">HHHB", transaction_id, 0, length, unit_id)
        return mbap + pdu

    def _build_modbus_device_id_response(
        self, transaction_id: int, unit_id: int, device: DeviceContext
    ) -> bytes:
        """Build Modbus FC 43 (Read Device Identification) response.

        This response identifies the device with vendor/model/firmware info
        that security scanners like Cisco Cyber Vision use for device detection.
        """
        # Use get_effective_identity to apply CVE vulnerability overrides
        modbus_identity = device.get_effective_identity("modbus_identity")

        # Object IDs for device identification
        objects = []
        object_data = {
            0x00: modbus_identity.get("vendor_name", "Unknown Vendor"),
            0x01: modbus_identity.get("product_code", "Unknown"),
            0x02: modbus_identity.get("major_minor_revision", "1.0"),
            0x03: modbus_identity.get("vendor_url", ""),
            0x04: modbus_identity.get("product_name", ""),
            0x05: modbus_identity.get("model_name", ""),
        }

        for obj_id, value in object_data.items():
            if value:
                value_bytes = value.encode("ascii")[:255]
                objects.append(struct.pack("BB", obj_id, len(value_bytes)) + value_bytes)

        # Build MEI response
        # FC 43 (0x2B), MEI type 0x0E, Read Device ID code, Conformity level, More follows, Next obj ID, Number of objects
        object_bytes = b"".join(objects)
        mei_response = struct.pack(
            ">BBBBBBB",
            0x2B,  # Function code 43
            0x0E,  # MEI type (Read Device Identification)
            0x01,  # Read Device ID code (basic)
            0x01,  # Conformity level (basic)
            0x00,  # More follows (no)
            0x00,  # Next object ID
            len(objects),  # Number of objects
        ) + object_bytes

        # MBAP header
        length = len(mei_response) + 1
        mbap = struct.pack(">HHHB", transaction_id, 0, length, unit_id)
        return mbap + mei_response

    def _build_udp_packet(
        self,
        src: DeviceContext,
        dst: DeviceContext,
        payload: bytes,
    ) -> bytes:
        """Build a UDP packet with full headers."""
        packet = (
            Ether(src=src.mac_address, dst=dst.mac_address)
            / IP(src=src.ip_address, dst=dst.ip_address)
            / UDP(sport=src.port, dport=dst.port)
            / Raw(load=payload)
        )
        return bytes(packet)

    # ==================== TLS Packet Building (for HTTPS external flows) ====================

    def _build_tls_client_hello(self, client_ip: str) -> bytes:
        """Build a minimal TLS 1.2 Client Hello for external HTTPS flows.

        This generates a realistic-looking TLS handshake initiation that
        detection tools like Cyber Vision can observe.

        Args:
            client_ip: Client IP address (used for SNI extension)

        Returns:
            TLS Client Hello record bytes
        """
        # TLS Record Header
        tls_content_type = 0x16  # Handshake
        tls_version = struct.pack(">BB", 0x03, 0x01)  # TLS 1.0 in record layer

        # Client Hello Handshake
        handshake_type = 0x01  # Client Hello
        client_version = struct.pack(">BB", 0x03, 0x03)  # TLS 1.2

        # Random (32 bytes)
        client_random = bytes(random.randint(0, 255) for _ in range(32))

        # Session ID (empty)
        session_id = bytes([0x00])

        # Cipher Suites (common modern suites)
        cipher_suites = struct.pack(
            ">H",  # Length
            8,  # 4 cipher suites * 2 bytes each
        ) + struct.pack(
            ">HHHH",
            0xC02F,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
            0xC030,  # TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
            0x009E,  # TLS_DHE_RSA_WITH_AES_128_GCM_SHA256
            0x009F,  # TLS_DHE_RSA_WITH_AES_256_GCM_SHA384
        )

        # Compression methods (null only)
        compression = bytes([0x01, 0x00])

        # Extensions (minimal - just SNI and supported versions)
        # SNI extension
        sni_hostname = b"talk2m.ewon.biz"  # EWON cloud service
        sni_extension = struct.pack(
            ">HH",
            0x0000,  # SNI extension type
            len(sni_hostname) + 5,  # Extension length
        ) + struct.pack(
            ">HBH",
            len(sni_hostname) + 3,  # SNI list length
            0x00,  # Host name type
            len(sni_hostname),  # Host name length
        ) + sni_hostname

        # Supported versions extension (TLS 1.2, 1.3)
        supported_versions = struct.pack(
            ">HHB",
            0x002B,  # Supported versions extension type
            3,  # Extension length
            2,  # Versions length
        ) + struct.pack(">BB", 0x03, 0x03)  # TLS 1.2

        extensions = struct.pack(">H", len(sni_extension) + len(supported_versions))
        extensions += sni_extension + supported_versions

        # Assemble Client Hello
        client_hello_body = (
            client_version
            + client_random
            + session_id
            + cipher_suites
            + compression
            + extensions
        )

        # Handshake header
        handshake_header = struct.pack(
            ">B",
            handshake_type,
        ) + struct.pack(">I", len(client_hello_body))[1:]  # 3-byte length

        handshake = handshake_header + client_hello_body

        # TLS Record
        tls_record = struct.pack(
            ">B",
            tls_content_type,
        ) + tls_version + struct.pack(">H", len(handshake)) + handshake

        return tls_record

    def _build_tls_server_hello(self) -> bytes:
        """Build a minimal TLS 1.2 Server Hello response.

        Returns:
            TLS Server Hello record bytes
        """
        # TLS Record Header
        tls_content_type = 0x16  # Handshake
        tls_version = struct.pack(">BB", 0x03, 0x03)  # TLS 1.2

        # Server Hello Handshake
        handshake_type = 0x02  # Server Hello
        server_version = struct.pack(">BB", 0x03, 0x03)  # TLS 1.2

        # Random (32 bytes)
        server_random = bytes(random.randint(0, 255) for _ in range(32))

        # Session ID (32 bytes - session established)
        session_id_len = 32
        session_id = bytes([session_id_len]) + bytes(random.randint(0, 255) for _ in range(session_id_len))

        # Selected cipher suite
        cipher_suite = struct.pack(">H", 0xC02F)  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256

        # Compression method (null)
        compression = bytes([0x00])

        # Extensions (minimal)
        extensions = struct.pack(">H", 0)  # No extensions

        # Assemble Server Hello
        server_hello_body = (
            server_version
            + server_random
            + session_id
            + cipher_suite
            + compression
            + extensions
        )

        # Handshake header
        handshake_header = struct.pack(
            ">B",
            handshake_type,
        ) + struct.pack(">I", len(server_hello_body))[1:]  # 3-byte length

        handshake = handshake_header + server_hello_body

        # TLS Record
        tls_record = struct.pack(
            ">B",
            tls_content_type,
        ) + tls_version + struct.pack(">H", len(handshake)) + handshake

        return tls_record

    # ==================== SNMP Packet Building ====================

    def _encode_ber_length(self, length: int) -> bytes:
        """Encode length in BER format."""
        if length < 128:
            return bytes([length])
        elif length < 256:
            return bytes([0x81, length])
        elif length < 65536:
            return bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])
        else:
            return bytes([0x83, (length >> 16) & 0xFF, (length >> 8) & 0xFF, length & 0xFF])

    def _encode_ber_integer(self, value: int) -> bytes:
        """Encode an integer in BER format (handles positive and negative values)."""
        if value == 0:
            return bytes([0x02, 0x01, 0x00])

        # Handle negative integers using two's complement
        if value < 0:
            # For negative values, we need two's complement encoding
            if value >= -128:
                # Single byte: -128 to -1 -> 0x80 to 0xFF
                return bytes([0x02, 0x01, value & 0xFF])
            elif value >= -32768:
                # Two bytes: -32768 to -129
                return bytes([0x02, 0x02, (value >> 8) & 0xFF, value & 0xFF])
            else:
                # Larger negative integers
                data = []
                temp = value
                while temp < -1 or (data and not (data[0] & 0x80)):
                    data.insert(0, temp & 0xFF)
                    temp >>= 8
                # Ensure high bit is set for negative
                if not (data[0] & 0x80):
                    data.insert(0, 0xFF)
                return bytes([0x02, len(data)] + data)

        # Positive integers
        if value < 128:
            return bytes([0x02, 0x01, value])
        elif value < 256:
            return bytes([0x02, 0x02, 0x00, value])
        elif value < 32768:
            return bytes([0x02, 0x02, (value >> 8) & 0xFF, value & 0xFF])
        elif value < 65536:
            return bytes([0x02, 0x03, 0x00, (value >> 8) & 0xFF, value & 0xFF])
        else:
            # Handle larger positive integers
            data = []
            temp = value
            while temp > 0:
                data.insert(0, temp & 0xFF)
                temp >>= 8
            if data[0] & 0x80:
                data.insert(0, 0x00)
            return bytes([0x02, len(data)] + data)

    def _encode_ber_octet_string(self, value: str | bytes) -> bytes:
        """Encode an octet string in BER format."""
        if isinstance(value, str):
            value = value.encode("utf-8")
        return bytes([0x04]) + self._encode_ber_length(len(value)) + value

    def _encode_ber_oid(self, oid: str) -> bytes:
        """Encode an OID in BER format."""
        parts = [int(p) for p in oid.split(".")]
        if len(parts) < 2:
            parts = [1, 3, 6, 1, 2, 1, 1, 1, 0]  # Default to sysDescr

        # First two parts encoded specially
        encoded = [parts[0] * 40 + parts[1]]

        for part in parts[2:]:
            if part < 128:
                encoded.append(part)
            else:
                # Variable-length encoding for values >= 128
                temp = []
                while part > 0:
                    temp.insert(0, (part & 0x7F) | (0x80 if temp else 0))
                    part >>= 7
                encoded.extend(temp)

        return bytes([0x06, len(encoded)] + encoded)

    def _encode_ber_null(self) -> bytes:
        """Encode a NULL in BER format."""
        return bytes([0x05, 0x00])

    def _encode_ber_timeticks(self, value: int) -> bytes:
        """Encode TimeTicks in BER format (APPLICATION 3)."""
        if value < 128:
            return bytes([0x43, 0x01, value])
        elif value < 256:
            return bytes([0x43, 0x02, 0x00, value])
        elif value < 65536:
            return bytes([0x43, 0x03, 0x00, (value >> 8) & 0xFF, value & 0xFF])
        else:
            return bytes([0x43, 0x04,
                          (value >> 24) & 0xFF, (value >> 16) & 0xFF,
                          (value >> 8) & 0xFF, value & 0xFF])

    def _build_snmp_get_request(
        self,
        request_id: int,
        oids: list[str],
        community: str = "public",
        version: int = SNMP_VERSION_2C,
    ) -> bytes:
        """Build an SNMP GetRequest PDU.

        Args:
            request_id: Request identifier
            oids: List of OID strings to query
            community: SNMP community string
            version: SNMP version (0=v1, 1=v2c)

        Returns:
            Complete SNMP packet bytes
        """
        # Build variable bindings (sequence of OID + NULL)
        varbinds = b""
        for oid in oids:
            oid_enc = self._encode_ber_oid(oid)
            null_enc = self._encode_ber_null()
            varbind = bytes([0x30]) + self._encode_ber_length(len(oid_enc) + len(null_enc)) + oid_enc + null_enc
            varbinds += varbind

        # Variable binding list (SEQUENCE)
        varbind_list = bytes([0x30]) + self._encode_ber_length(len(varbinds)) + varbinds

        # PDU: request-id, error-status, error-index, variable-bindings
        request_id_enc = self._encode_ber_integer(request_id)
        error_status_enc = self._encode_ber_integer(0)
        error_index_enc = self._encode_ber_integer(0)

        pdu_content = request_id_enc + error_status_enc + error_index_enc + varbind_list
        pdu = bytes([SNMP_GET_REQUEST]) + self._encode_ber_length(len(pdu_content)) + pdu_content

        # SNMP message: version, community, PDU
        version_enc = self._encode_ber_integer(version)
        community_enc = self._encode_ber_octet_string(community)

        message_content = version_enc + community_enc + pdu
        message = bytes([0x30]) + self._encode_ber_length(len(message_content)) + message_content

        return message

    def _build_snmp_get_response(
        self,
        request_id: int,
        oid_values: dict[str, tuple[str, Any]],
        community: str = "public",
        version: int = SNMP_VERSION_2C,
    ) -> bytes:
        """Build an SNMP GetResponse PDU.

        Args:
            request_id: Request identifier (should match request)
            oid_values: Dict of OID -> (type, value)
                        type: "string", "integer", "oid", "timeticks"
            community: SNMP community string
            version: SNMP version (0=v1, 1=v2c)

        Returns:
            Complete SNMP packet bytes
        """
        # Build variable bindings
        varbinds = b""
        for oid, (value_type, value) in oid_values.items():
            oid_enc = self._encode_ber_oid(oid)

            if value_type == "string":
                value_enc = self._encode_ber_octet_string(str(value))
            elif value_type == "integer":
                value_enc = self._encode_ber_integer(int(value))
            elif value_type == "oid":
                value_enc = self._encode_ber_oid(str(value))
            elif value_type == "timeticks":
                value_enc = self._encode_ber_timeticks(int(value))
            else:
                value_enc = self._encode_ber_octet_string(str(value))

            varbind = bytes([0x30]) + self._encode_ber_length(len(oid_enc) + len(value_enc)) + oid_enc + value_enc
            varbinds += varbind

        # Variable binding list
        varbind_list = bytes([0x30]) + self._encode_ber_length(len(varbinds)) + varbinds

        # PDU
        request_id_enc = self._encode_ber_integer(request_id)
        error_status_enc = self._encode_ber_integer(0)
        error_index_enc = self._encode_ber_integer(0)

        pdu_content = request_id_enc + error_status_enc + error_index_enc + varbind_list
        pdu = bytes([SNMP_GET_RESPONSE]) + self._encode_ber_length(len(pdu_content)) + pdu_content

        # SNMP message
        version_enc = self._encode_ber_integer(version)
        community_enc = self._encode_ber_octet_string(community)

        message_content = version_enc + community_enc + pdu
        message = bytes([0x30]) + self._encode_ber_length(len(message_content)) + message_content

        return message

    def _get_snmp_identity_values(
        self,
        device: DeviceContext,
        uptime_ms: int,
    ) -> dict[str, tuple[str, Any]]:
        """Build SNMP identity values from device for sysDescr-based CVE detection.

        The sysDescr field is CRITICAL for Cyber Vision to detect vulnerabilities,
        as it contains the device vendor, model, and firmware version.

        Uses get_effective_identity() to apply CVE vulnerability overrides.
        """
        # Get effective SNMP identity with vulnerability overrides applied
        snmp_identity = device.get_effective_identity("snmp_identity")
        fingerprint = device.vendor_fingerprint

        # sysDescr is the most important field for device identification
        # Format should include: Vendor, Model, Firmware Version
        sys_descr = snmp_identity.get(
            "sys_descr",
            fingerprint.get("vendor", "Unknown") + " " +
            fingerprint.get("model", "Device") + " " +
            fingerprint.get("firmware_version", "V1.0")
        )

        sys_object_id = snmp_identity.get("sys_object_id", "1.3.6.1.4.1.9999.1.1")
        # Use device_name for unique sysName per device (critical for Cyber Vision)
        # Fall back to fingerprint sys_name or random if not set
        if device.device_name:
            sys_name = device.device_name
        else:
            sys_name = snmp_identity.get("sys_name", f"device-{random.randint(1, 999):03d}")
        sys_location = snmp_identity.get("sys_location", "Field")
        sys_contact = snmp_identity.get("sys_contact", "admin@local")

        return {
            SNMP_OIDS["sysDescr"]: ("string", sys_descr),
            SNMP_OIDS["sysObjectID"]: ("oid", sys_object_id),
            SNMP_OIDS["sysUpTime"]: ("timeticks", uptime_ms // 10),  # Hundredths of a second
            SNMP_OIDS["sysContact"]: ("string", sys_contact),
            SNMP_OIDS["sysName"]: ("string", sys_name),
            SNMP_OIDS["sysLocation"]: ("string", sys_location),
            SNMP_OIDS["sysServices"]: ("integer", 72),  # Layers 3,4,7 (typical for ITS device)
        }

    # ==================== BACnet Packet Building ====================

    def _encode_bacnet_unsigned(self, value: int) -> bytes:
        """Encode an unsigned integer for BACnet (application tag 2)."""
        if value < 0x100:
            return bytes([0x21, value])
        elif value < 0x10000:
            return bytes([0x22, (value >> 8) & 0xFF, value & 0xFF])
        elif value < 0x1000000:
            return bytes([0x23, (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])
        else:
            return bytes([0x24, (value >> 24) & 0xFF, (value >> 16) & 0xFF,
                          (value >> 8) & 0xFF, value & 0xFF])

    def _encode_bacnet_enumerated(self, value: int) -> bytes:
        """Encode an enumerated value for BACnet (application tag 9)."""
        if value < 0x100:
            return bytes([0x91, value])
        else:
            return bytes([0x92, (value >> 8) & 0xFF, value & 0xFF])

    def _encode_bacnet_character_string(self, value: str) -> bytes:
        """Encode a character string for BACnet (application tag 7)."""
        encoded = value.encode("utf-8")
        # Tag 7, encoding UTF-8 (0)
        length = len(encoded) + 1  # +1 for encoding byte
        if length < 5:
            return bytes([0x70 | length, 0x00]) + encoded
        elif length < 254:
            return bytes([0x75, length, 0x00]) + encoded
        else:
            return bytes([0x75, 0xFE, (length >> 8) & 0xFF, length & 0xFF, 0x00]) + encoded

    def _encode_bacnet_object_identifier(self, object_type: int, instance: int) -> bytes:
        """Encode an object identifier for BACnet (application tag 12)."""
        # Object identifier: 10-bit type + 22-bit instance
        value = ((object_type & 0x3FF) << 22) | (instance & 0x3FFFFF)
        return bytes([0xC4,
                      (value >> 24) & 0xFF,
                      (value >> 16) & 0xFF,
                      (value >> 8) & 0xFF,
                      value & 0xFF])

    def _encode_bacnet_context_tag(self, tag_number: int, data: bytes) -> bytes:
        """Encode a context tag wrapper."""
        length = len(data)
        if tag_number < 15:
            if length < 5:
                return bytes([(tag_number << 4) | 0x08 | length]) + data
            elif length < 254:
                return bytes([(tag_number << 4) | 0x0D, length]) + data
            else:
                return bytes([(tag_number << 4) | 0x0D, 0xFE,
                              (length >> 8) & 0xFF, length & 0xFF]) + data
        else:
            # Extended tag number
            if length < 5:
                return bytes([0xF8 | length, tag_number]) + data
            elif length < 254:
                return bytes([0xFD, tag_number, length]) + data
            else:
                return bytes([0xFD, tag_number, 0xFE,
                              (length >> 8) & 0xFF, length & 0xFF]) + data

    def _build_bacnet_who_is(self) -> bytes:
        """Build BACnet Who-Is broadcast request."""
        # NPDU: Version 1, no destination/source network info
        npdu = struct.pack("BB", 0x01, 0x00)

        # APDU: Unconfirmed request, Who-Is service
        apdu = struct.pack("BB", BACNET_PDU_UNCONFIRMED_REQUEST, BACNET_SERVICE_WHO_IS)

        # BVLC header: Type, Function (broadcast), Length
        total_length = 4 + len(npdu) + len(apdu)
        bvlc = struct.pack(">BBH", BACNET_BVLC_TYPE, BVLC_ORIGINAL_BROADCAST_NPDU, total_length)

        return bvlc + npdu + apdu

    def _build_bacnet_i_am(self, device: DeviceContext) -> bytes:
        """Build BACnet I-Am response with device identity.

        This is CRITICAL for Cyber Vision device detection.
        The I-Am contains vendor_id, model_name, and firmware_revision.
        Uses get_effective_identity() to apply CVE vulnerability overrides.
        """
        bacnet_identity = device.get_effective_identity("bacnet_identity")

        # Use deterministic device_instance based on IP if not specified
        # This prevents device explosion in Cyber Vision from random instance IDs
        if "device_instance" in bacnet_identity:
            device_instance = bacnet_identity["device_instance"]
        else:
            # Generate deterministic instance from IP address (1 to 4194302)
            ip_hash = hash(device.ip_address) & 0x3FFFFF  # 22-bit mask
            device_instance = max(1, ip_hash % 4194302)
        vendor_id = bacnet_identity.get("vendor_id", 0)
        max_apdu_length = bacnet_identity.get("max_apdu_length", 1476)
        segmentation = bacnet_identity.get("segmentation_supported", BACNET_SEG_NONE)

        # NPDU: Version 1, no network routing
        npdu = struct.pack("BB", 0x01, 0x00)

        # APDU: Unconfirmed request, I-Am service
        apdu = struct.pack("BB", BACNET_PDU_UNCONFIRMED_REQUEST, BACNET_SERVICE_I_AM)

        # I-Am parameters:
        # 1. Object Identifier (Device object)
        apdu += self._encode_bacnet_object_identifier(BACNET_OBJ_DEVICE, device_instance)

        # 2. Max APDU Length Accepted
        apdu += self._encode_bacnet_unsigned(max_apdu_length)

        # 3. Segmentation Supported
        apdu += self._encode_bacnet_enumerated(segmentation)

        # 4. Vendor ID
        apdu += self._encode_bacnet_unsigned(vendor_id)

        # BVLC header
        total_length = 4 + len(npdu) + len(apdu)
        bvlc = struct.pack(">BBH", BACNET_BVLC_TYPE, BVLC_ORIGINAL_BROADCAST_NPDU, total_length)

        return bvlc + npdu + apdu

    def _build_bacnet_read_property_request(
        self,
        invoke_id: int,
        object_type: int,
        object_instance: int,
        property_id: int,
    ) -> bytes:
        """Build BACnet ReadProperty request."""
        # NPDU: Version 1, expecting reply
        npdu = struct.pack("BB", 0x01, 0x04)

        # APDU: Confirmed request
        # PDU type (0) + segmentation info (0x04 = max segments 16, max response 1476)
        apdu = struct.pack("BBBB",
                           BACNET_PDU_CONFIRMED_REQUEST | 0x04,  # Expecting reply
                           0x05,  # Max segments/response accepted
                           invoke_id,
                           BACNET_SERVICE_READ_PROPERTY)

        # Object Identifier [0]
        obj_id = self._encode_bacnet_object_identifier(object_type, object_instance)
        apdu += self._encode_bacnet_context_tag(0, obj_id[1:])  # Skip application tag byte

        # Property Identifier [1]
        if property_id < 0x100:
            prop_data = bytes([property_id])
        else:
            prop_data = bytes([(property_id >> 8) & 0xFF, property_id & 0xFF])
        apdu += self._encode_bacnet_context_tag(1, prop_data)

        # BVLC header
        total_length = 4 + len(npdu) + len(apdu)
        bvlc = struct.pack(">BBH", BACNET_BVLC_TYPE, BVLC_ORIGINAL_UNICAST_NPDU, total_length)

        return bvlc + npdu + apdu

    def _build_bacnet_read_property_response(
        self,
        invoke_id: int,
        object_type: int,
        object_instance: int,
        property_id: int,
        property_value: Any,
        value_type: str = "unsigned",
    ) -> bytes:
        """Build BACnet ReadProperty response (Complex-ACK)."""
        # NPDU: Version 1, no network routing
        npdu = struct.pack("BB", 0x01, 0x00)

        # APDU: Complex-ACK
        apdu = struct.pack("BBB",
                           BACNET_PDU_COMPLEX_ACK,
                           invoke_id,
                           BACNET_SERVICE_READ_PROPERTY)

        # Object Identifier [0]
        obj_id = self._encode_bacnet_object_identifier(object_type, object_instance)
        apdu += self._encode_bacnet_context_tag(0, obj_id[1:])

        # Property Identifier [1]
        if property_id < 0x100:
            prop_data = bytes([property_id])
        else:
            prop_data = bytes([(property_id >> 8) & 0xFF, property_id & 0xFF])
        apdu += self._encode_bacnet_context_tag(1, prop_data)

        # Property Value [3] - opening tag
        apdu += bytes([0x3E])

        # Encode value based on type
        if value_type == "unsigned":
            apdu += self._encode_bacnet_unsigned(int(property_value))
        elif value_type == "string":
            apdu += self._encode_bacnet_character_string(str(property_value))
        elif value_type == "enumerated":
            apdu += self._encode_bacnet_enumerated(int(property_value))
        elif value_type == "real":
            # IEEE 754 float (application tag 4)
            float_bytes = struct.pack(">f", float(property_value))
            apdu += bytes([0x44]) + float_bytes
        else:
            apdu += self._encode_bacnet_unsigned(int(property_value))

        # Property Value [3] - closing tag
        apdu += bytes([0x3F])

        # BVLC header
        total_length = 4 + len(npdu) + len(apdu)
        bvlc = struct.pack(">BBH", BACNET_BVLC_TYPE, BVLC_ORIGINAL_UNICAST_NPDU, total_length)

        return bvlc + npdu + apdu

    def _get_bacnet_identity_values(self, device: DeviceContext) -> dict[int, tuple[str, Any]]:
        """Get BACnet identity property values from device.

        Returns dict of property_id -> (type, value) for Device Object properties.
        Uses get_effective_identity() to apply CVE vulnerability overrides.
        """
        bacnet_identity = device.get_effective_identity("bacnet_identity")

        return {
            BACNET_PROP_VENDOR_ID: ("unsigned", bacnet_identity.get("vendor_id", 0)),
            BACNET_PROP_VENDOR_NAME: ("string", bacnet_identity.get("vendor_name", "Unknown")),
            BACNET_PROP_MODEL_NAME: ("string", bacnet_identity.get("model_name", "BACnet Device")),
            BACNET_PROP_FIRMWARE_REVISION: ("string", bacnet_identity.get("firmware_revision", "1.0")),
            BACNET_PROP_SYSTEM_STATUS: ("enumerated", 0),  # Operational
        }

    # ==================== DNP3 Packet Building ====================

    def _calculate_dnp3_crc(self, data: bytes) -> int:
        """Calculate DNP3 CRC-16."""
        crc = 0x0000
        for byte in data:
            crc = (crc >> 8) ^ DNP3_CRC_TABLE[(crc ^ byte) & 0xFF]
        return (~crc) & 0xFFFF

    def _build_dnp3_data_link_frame(
        self,
        destination: int,
        source: int,
        control: int,
        payload: bytes,
    ) -> bytes:
        """Build DNP3 data link layer frame with CRCs.

        Args:
            destination: Destination address (0-65519)
            source: Source address (0-65519)
            control: Control byte (0xC4 for primary, 0x44 for secondary)
            payload: Transport + Application layer data

        Returns:
            Complete data link frame with CRCs
        """
        # Header: Start(2) + Length(1) + Control(1) + Dest(2) + Src(2)
        length = 5 + len(payload)  # 5 = control(1) + dest(2) + src(2)

        header = (
            DNP3_START_BYTES +
            bytes([length]) +
            bytes([control]) +
            struct.pack("<H", destination) +
            struct.pack("<H", source)
        )

        # CRC for header (excludes start bytes)
        header_crc = self._calculate_dnp3_crc(header[2:])
        header_with_crc = header + struct.pack("<H", header_crc)

        # Add CRC every 16 bytes of payload
        payload_with_crc = b""
        for i in range(0, len(payload), 16):
            block = payload[i:i + 16]
            block_crc = self._calculate_dnp3_crc(block)
            payload_with_crc += block + struct.pack("<H", block_crc)

        return header_with_crc + payload_with_crc

    def _build_dnp3_read_request(
        self,
        destination: int,
        source: int,
        objects: list[tuple[int, int]],
        sequence: int = 0,
    ) -> bytes:
        """Build DNP3 Read request.

        Args:
            destination: Outstation address
            source: Master address
            objects: List of (group, variation) tuples to read
            sequence: Application sequence number (0-15)

        Returns:
            Complete DNP3 Read request frame
        """
        # Transport header (FIN=1, FIR=1, Sequence)
        transport_header = bytes([0xC0 | (sequence & 0x3F)])

        # Application header (FIN=1, FIR=1, Sequence, Function=READ)
        app_control = 0xC0 | (sequence & 0x0F)  # FIN=1, FIR=1
        app_header = bytes([app_control, DNP3_FC_READ])

        # Object headers (request all objects for each group/variation)
        object_data = b""
        for group, variation in objects:
            # Group(1) + Variation(1) + Qualifier(1, ALL_OBJECTS=0x06)
            object_data += bytes([group, variation, DNP3_QC_ALL_OBJECTS])

        payload = transport_header + app_header + object_data

        # Data link layer (control = 0xC4 for primary, unconfirmed)
        return self._build_dnp3_data_link_frame(destination, source, 0xC4, payload)

    def _build_dnp3_read_response(
        self,
        destination: int,
        source: int,
        objects: list[tuple[int, int, list[Any]]],
        sequence: int = 0,
    ) -> bytes:
        """Build DNP3 Read response.

        Args:
            destination: Master address
            source: Outstation address
            objects: List of (group, variation, values) tuples
            sequence: Application sequence number

        Returns:
            Complete DNP3 Read response frame
        """
        # Transport header (FIN=1, FIR=1, Sequence)
        transport_header = bytes([0xC0 | (sequence & 0x3F)])

        # Application header (FIN=1, FIR=1, Sequence, Function=RESPONSE)
        app_control = 0xC0 | (sequence & 0x0F)
        app_header = bytes([app_control, DNP3_FC_RESPONSE])

        # Internal indications (2 bytes, all clear = normal operation)
        internal_indications = b"\x00\x00"

        # Object data
        object_data = b""
        for group, variation, values in objects:
            count = len(values)
            if count == 0:
                continue

            # Object header with start/stop range
            # Group(1) + Variation(1) + Qualifier(1) + Start(1) + Stop(1)
            object_data += bytes([
                group, variation, DNP3_QC_RANGE_START_STOP,
                0, count - 1 if count > 0 else 0
            ])

            # Encode values based on group
            for value in values:
                if group == DNP3_GROUP_BINARY_INPUT:
                    # Binary input - 1 byte with flags (0x01 = online + value)
                    flags = 0x01 if value else 0x00
                    object_data += bytes([flags])
                elif group == DNP3_GROUP_ANALOG_INPUT:
                    if variation == 1:  # 32-bit integer with flag
                        object_data += bytes([0x01]) + struct.pack("<i", int(value))
                    elif variation == 2:  # 16-bit integer with flag
                        object_data += bytes([0x01]) + struct.pack("<h", int(value))
                    elif variation == 5:  # 32-bit float with flag
                        object_data += bytes([0x01]) + struct.pack("<f", float(value))
                    else:  # Default to 32-bit float
                        object_data += bytes([0x01]) + struct.pack("<f", float(value))
                elif group == DNP3_GROUP_COUNTER:
                    # 32-bit counter with flag
                    object_data += bytes([0x01]) + struct.pack("<I", int(value))
                elif group == DNP3_GROUP_BINARY_OUTPUT:
                    # Binary output status
                    flags = 0x01 if value else 0x00
                    object_data += bytes([flags])

        payload = transport_header + app_header + internal_indications + object_data

        # Data link layer (control = 0x44 for secondary)
        return self._build_dnp3_data_link_frame(destination, source, 0x44, payload)

    # ==================== IEC 104 PACKET BUILDING ====================

    def _build_iec104_apci_u_format(self, control_byte: int) -> bytes:
        """Build IEC 104 U-format APCI (unnumbered control).

        Args:
            control_byte: U-format control byte (STARTDT, STOPDT, TESTFR)

        Returns:
            6-byte APCI
        """
        return bytes([
            IEC104_START_BYTE,
            4,  # APDU length (just control fields)
            control_byte,
            0x00,
            0x00,
            0x00,
        ])

    def _build_iec104_apci_i_format(
        self, send_seq: int, recv_seq: int, asdu_length: int
    ) -> bytes:
        """Build IEC 104 I-format APCI (information transfer).

        Args:
            send_seq: Send sequence number
            recv_seq: Receive sequence number
            asdu_length: Length of ASDU

        Returns:
            6-byte APCI
        """
        # I-format: bit 0 = 0
        cf1 = (send_seq << 1) & 0xFFFF
        cf2 = (recv_seq << 1) & 0xFFFF

        return bytes([
            IEC104_START_BYTE,
            4 + asdu_length,
            cf1 & 0xFF,
            (cf1 >> 8) & 0xFF,
            cf2 & 0xFF,
            (cf2 >> 8) & 0xFF,
        ])

    def _build_iec104_asdu_header(
        self,
        type_id: int,
        num_objects: int,
        sq: bool,
        cot: int,
        common_address: int,
    ) -> bytes:
        """Build IEC 104 ASDU header.

        Args:
            type_id: Type identification
            num_objects: Number of information objects
            sq: Sequence qualifier (True = sequential addresses)
            cot: Cause of transmission
            common_address: Common address of ASDU

        Returns:
            ASDU header bytes (6 bytes)
        """
        vsq = (num_objects & 0x7F) | (0x80 if sq else 0x00)
        return bytes([
            type_id,
            vsq,
            cot & 0xFF,
            0,  # Originator address
        ]) + struct.pack("<H", common_address)

    def _build_iec104_interrogation_command(
        self,
        send_seq: int,
        recv_seq: int,
        common_address: int,
        qoi: int = 20,
    ) -> bytes:
        """Build IEC 104 interrogation command (C_IC_NA_1).

        Args:
            send_seq: Send sequence number
            recv_seq: Receive sequence number
            common_address: Common address of ASDU
            qoi: Qualifier of interrogation (20 = station)

        Returns:
            Complete APDU bytes
        """
        asdu_header = self._build_iec104_asdu_header(
            type_id=IEC104_C_IC_NA_1,
            num_objects=1,
            sq=False,
            cot=IEC104_COT_ACTIVATION,
            common_address=common_address,
        )
        # Information object: IOA (3 bytes) + QOI (1 byte)
        info_object = struct.pack("<I", 0)[:3] + bytes([qoi])
        asdu = asdu_header + info_object

        apci = self._build_iec104_apci_i_format(send_seq, recv_seq, len(asdu))
        return apci + asdu

    def _build_iec104_interrogation_response(
        self,
        send_seq: int,
        recv_seq: int,
        common_address: int,
        qoi: int = 20,
    ) -> bytes:
        """Build IEC 104 interrogation confirmation.

        Args:
            send_seq: Send sequence number
            recv_seq: Receive sequence number
            common_address: Common address
            qoi: Qualifier of interrogation

        Returns:
            Complete APDU bytes
        """
        asdu_header = self._build_iec104_asdu_header(
            type_id=IEC104_C_IC_NA_1,
            num_objects=1,
            sq=False,
            cot=IEC104_COT_ACTIVATION_CON,
            common_address=common_address,
        )
        info_object = struct.pack("<I", 0)[:3] + bytes([qoi])
        asdu = asdu_header + info_object

        apci = self._build_iec104_apci_i_format(send_seq, recv_seq, len(asdu))
        return apci + asdu

    def _build_iec104_single_point_info(
        self,
        send_seq: int,
        recv_seq: int,
        common_address: int,
        values: list[tuple[int, bool]],
        cot: int = IEC104_COT_SPONTANEOUS,
    ) -> bytes:
        """Build IEC 104 single-point information (M_SP_NA_1).

        Args:
            send_seq: Send sequence number
            recv_seq: Receive sequence number
            common_address: Common address
            values: List of (IOA, value) tuples
            cot: Cause of transmission

        Returns:
            Complete APDU bytes
        """
        asdu_header = self._build_iec104_asdu_header(
            type_id=IEC104_M_SP_NA_1,
            num_objects=len(values),
            sq=False,
            cot=cot,
            common_address=common_address,
        )

        info_objects = b""
        for ioa, value in values:
            # IOA (3 bytes) + SIQ (1 byte)
            siq = 0x01 if value else 0x00
            info_objects += struct.pack("<I", ioa)[:3] + bytes([siq])

        asdu = asdu_header + info_objects
        apci = self._build_iec104_apci_i_format(send_seq, recv_seq, len(asdu))
        return apci + asdu

    def _build_iec104_measured_value_float(
        self,
        send_seq: int,
        recv_seq: int,
        common_address: int,
        values: list[tuple[int, float]],
        cot: int = IEC104_COT_SPONTANEOUS,
    ) -> bytes:
        """Build IEC 104 measured value, short floating point (M_ME_NC_1).

        Args:
            send_seq: Send sequence number
            recv_seq: Receive sequence number
            common_address: Common address
            values: List of (IOA, value) tuples
            cot: Cause of transmission

        Returns:
            Complete APDU bytes
        """
        asdu_header = self._build_iec104_asdu_header(
            type_id=IEC104_M_ME_NC_1,
            num_objects=len(values),
            sq=False,
            cot=cot,
            common_address=common_address,
        )

        info_objects = b""
        for ioa, value in values:
            # IOA (3 bytes) + Value (4 bytes float) + QDS (1 byte)
            qds = 0x00  # Quality descriptor (all good)
            info_objects += struct.pack("<I", ioa)[:3] + struct.pack("<f", value) + bytes([qds])

        asdu = asdu_header + info_objects
        apci = self._build_iec104_apci_i_format(send_seq, recv_seq, len(asdu))
        return apci + asdu

    def _build_iec104_interrogation_end(
        self,
        send_seq: int,
        recv_seq: int,
        common_address: int,
        qoi: int = 20,
    ) -> bytes:
        """Build IEC 104 interrogation termination.

        Args:
            send_seq: Send sequence number
            recv_seq: Receive sequence number
            common_address: Common address
            qoi: Qualifier of interrogation

        Returns:
            Complete APDU bytes
        """
        asdu_header = self._build_iec104_asdu_header(
            type_id=IEC104_C_IC_NA_1,
            num_objects=1,
            sq=False,
            cot=IEC104_COT_ACTIVATION_TERM,
            common_address=common_address,
        )
        info_object = struct.pack("<I", 0)[:3] + bytes([qoi])
        asdu = asdu_header + info_object

        apci = self._build_iec104_apci_i_format(send_seq, recv_seq, len(asdu))
        return apci + asdu

    # =========================================================================
    # OPC UA Packet Building Methods
    # =========================================================================

    def _encode_opcua_string(self, s: str | None) -> bytes:
        """Encode a string for OPC UA (length-prefixed UTF-8).

        Args:
            s: String to encode, or None for null string

        Returns:
            Length-prefixed UTF-8 bytes (-1 length for null)
        """
        if s is None:
            return struct.pack("<i", -1)  # Null string
        encoded = s.encode("utf-8")
        return struct.pack("<I", len(encoded)) + encoded

    def _get_opcua_server_identity(self, device: DeviceContext) -> dict[str, Any]:
        """Get OPC UA server identity from device fingerprint.

        Args:
            device: Server device context

        Returns:
            Dictionary with OPC UA identity fields
        """
        opc_identity = device.get_effective_identity("opc_ua_identity")

        # Default values based on device info
        default_app_name = device.device_name or "OPC UA Server"
        default_app_uri = f"urn:{device.ip_address}:OPCUA:Server"
        default_product_uri = "urn:PacketArch:OPCUAServer"

        return {
            "application_name": opc_identity.get("application_name", default_app_name),
            "application_uri": opc_identity.get("application_uri", default_app_uri),
            "product_uri": opc_identity.get("product_uri", default_product_uri),
            "manufacturer_name": opc_identity.get("manufacturer_name", "Unknown"),
            "product_name": opc_identity.get("product_name", "OPC UA Server"),
            "software_version": opc_identity.get("software_version", "1.0.0"),
            "build_number": opc_identity.get("build_number", "0"),
            "build_date": opc_identity.get("build_date", "2024-01-01"),
        }

    def _get_iec104_station_identity(self, device: DeviceContext) -> dict[str, Any]:
        """Get IEC 104 station identity from device fingerprint.

        Args:
            device: Station device context

        Returns:
            Dictionary with IEC 104 identity fields
        """
        iec104_identity = device.get_effective_identity("iec104_identity")

        # Default values
        default_station_name = device.device_name or "IEC104-Station"

        return {
            "station_name": iec104_identity.get("station_name", default_station_name),
            "common_address": iec104_identity.get("common_address", 1),
        }

    def _get_dnp3_outstation_identity(self, device: DeviceContext) -> dict[str, Any]:
        """Get DNP3 outstation identity from device fingerprint.

        Args:
            device: Outstation device context

        Returns:
            Dictionary with DNP3 identity fields
        """
        dnp3_identity = device.get_effective_identity("dnp3_identity")

        # Default values
        default_vendor = "Unknown Vendor"

        return {
            "vendor_name": dnp3_identity.get("vendor_name", default_vendor),
            "device_serial": dnp3_identity.get("device_serial", "000000"),
            "hardware_version": dnp3_identity.get("hardware_version", "1.0"),
            "software_version": dnp3_identity.get("software_version", "1.0"),
            "outstation_address": dnp3_identity.get("outstation_address"),
        }

    def _build_opcua_hello(self, endpoint_url: str = "opc.tcp://localhost:4840") -> bytes:
        """Build OPC UA Hello message.

        Args:
            endpoint_url: OPC UA endpoint URL

        Returns:
            Complete Hello message bytes
        """
        endpoint_bytes = endpoint_url.encode("utf-8")

        # Hello message body
        body = struct.pack(
            "<IIII",
            OPCUA_PROTOCOL_VERSION,  # Protocol version
            65535,                   # ReceiveBufferSize
            65535,                   # SendBufferSize
            0,                       # MaxMessageSize (0 = no limit)
        )
        body += struct.pack("<I", 0)  # MaxChunkCount (0 = no limit)
        body += struct.pack("<I", len(endpoint_bytes)) + endpoint_bytes

        # Message header: HEL + F + Length(4)
        header = OPCUA_MSG_HELLO + OPCUA_MSG_FINAL + struct.pack("<I", 8 + len(body))
        return header + body

    def _build_opcua_ack(self) -> bytes:
        """Build OPC UA Acknowledge message.

        Returns:
            Complete Ack message bytes
        """
        # Ack message body
        body = struct.pack(
            "<IIIII",
            OPCUA_PROTOCOL_VERSION,  # Protocol version
            65535,                   # ReceiveBufferSize
            65535,                   # SendBufferSize
            0,                       # MaxMessageSize
            0,                       # MaxChunkCount
        )

        # Message header: ACK + F + Length(4)
        header = OPCUA_MSG_ACK + OPCUA_MSG_FINAL + struct.pack("<I", 8 + len(body))
        return header + body

    def _build_opcua_open_secure_channel_request(
        self, security_token_id: int = 0, request_id: int = 1
    ) -> bytes:
        """Build OPC UA OpenSecureChannel request.

        Args:
            security_token_id: Security token ID (0 for new channel)
            request_id: Request ID

        Returns:
            Complete OpenSecureChannel request bytes
        """
        # Security policy URI (None security)
        policy_uri = OPCUA_SECURITY_NONE.encode("utf-8")

        # Message body (asymmetric security header for OPN)
        asym_header = struct.pack("<I", len(policy_uri)) + policy_uri
        asym_header += struct.pack("<I", 0)  # Sender certificate (empty)
        asym_header += struct.pack("<I", 0)  # Receiver certificate thumbprint (empty)

        # Sequence header
        seq_header = struct.pack("<II", 1, request_id)  # Sequence number, request ID

        # Service request (OpenSecureChannelRequest)
        # NodeId encoding: 1 byte type + 2 byte identifier
        service_node = struct.pack("<BH", 0x01, OPCUA_SERVICE_OPEN_SECURE_CHANNEL_REQUEST)

        # Request header (simplified)
        request_header = bytes(24)  # Minimal request header

        # OpenSecureChannel parameters
        osc_params = struct.pack(
            "<III",
            0,                       # ClientProtocolVersion
            0,                       # RequestType (0 = Issue)
            OPCUA_MSG_SECURITY_NONE,  # SecurityMode
        )
        osc_params += struct.pack("<I", 0)  # ClientNonce (empty)
        osc_params += struct.pack("<I", 3600000)  # RequestedLifetime (1 hour)

        body = asym_header + seq_header + service_node + request_header + osc_params

        # Message header: OPN + F + Length(4) + SecureChannelId(4)
        header = OPCUA_MSG_OPEN + OPCUA_MSG_FINAL
        header += struct.pack("<II", 8 + len(body), security_token_id)

        return header + body

    def _build_opcua_open_secure_channel_response(
        self, secure_channel_id: int, token_id: int, request_id: int = 1
    ) -> bytes:
        """Build OPC UA OpenSecureChannel response.

        Args:
            secure_channel_id: Assigned secure channel ID
            token_id: Security token ID
            request_id: Request ID

        Returns:
            Complete OpenSecureChannel response bytes
        """
        # Asymmetric security header
        policy_uri = OPCUA_SECURITY_NONE.encode("utf-8")
        asym_header = struct.pack("<I", len(policy_uri)) + policy_uri
        asym_header += struct.pack("<I", 0)  # Sender certificate
        asym_header += struct.pack("<I", 0)  # Receiver certificate thumbprint

        # Sequence header
        seq_header = struct.pack("<II", 1, request_id)

        # Service response (OpenSecureChannelResponse)
        service_node = struct.pack("<BH", 0x01, OPCUA_SERVICE_OPEN_SECURE_CHANNEL_RESPONSE)

        # Response header (simplified)
        response_header = bytes(24)

        # OpenSecureChannel response parameters
        current_time = int(time.time() * 10000000) + 116444736000000000  # Windows FILETIME
        osc_response = struct.pack("<Q", current_time)  # ServerProtocolVersion (timestamp)
        osc_response += struct.pack(
            "<III",
            secure_channel_id,  # SecurityToken.ChannelId
            token_id,           # SecurityToken.TokenId
            current_time & 0xFFFFFFFF,  # CreatedAt (low 32 bits)
        )
        osc_response += struct.pack("<I", 3600000)  # RevisedLifetime
        osc_response += struct.pack("<I", 0)  # ServerNonce (empty)

        body = asym_header + seq_header + service_node + response_header + osc_response

        # Message header
        header = OPCUA_MSG_OPEN + OPCUA_MSG_FINAL
        header += struct.pack("<II", 8 + len(body), secure_channel_id)

        return header + body

    def _build_opcua_message(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
        service_id: int,
        payload: bytes = b"",
    ) -> bytes:
        """Build OPC UA message (MSG type).

        Args:
            secure_channel_id: Secure channel ID
            token_id: Security token ID
            sequence_number: Sequence number
            request_id: Request ID
            service_id: Service node ID
            payload: Service-specific payload

        Returns:
            Complete MSG bytes
        """
        # Symmetric security header
        sym_header = struct.pack("<I", token_id)

        # Sequence header
        seq_header = struct.pack("<II", sequence_number, request_id)

        # Service node ID
        service_node = struct.pack("<BH", 0x01, service_id)

        body = sym_header + seq_header + service_node + payload

        # Message header: MSG + F + Length(4) + SecureChannelId(4)
        header = OPCUA_MSG_MESSAGE + OPCUA_MSG_FINAL
        header += struct.pack("<II", 8 + len(body), secure_channel_id)

        return header + body

    def _build_opcua_create_session_request(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
        endpoint_url: str = "opc.tcp://localhost:4840",
        session_name: str = "PacketArch Session",
    ) -> bytes:
        """Build OPC UA CreateSession request."""
        # Request header (simplified)
        request_header = bytes(24)

        endpoint_bytes = endpoint_url.encode("utf-8")
        session_name_bytes = session_name.encode("utf-8")

        # CreateSession parameters
        params = request_header
        params += struct.pack("<I", 0)  # ClientDescription.ApplicationUri
        params += struct.pack("<I", 0)  # ClientDescription.ProductUri
        params += struct.pack("<I", 0)  # ClientDescription.ApplicationName
        params += struct.pack("<I", 1)  # ClientDescription.ApplicationType (Client)
        params += struct.pack("<I", 0)  # ClientDescription.GatewayServerUri
        params += struct.pack("<I", 0)  # ClientDescription.DiscoveryProfileUri
        params += struct.pack("<I", 0)  # ClientDescription.DiscoveryUrls
        params += struct.pack("<I", len(endpoint_bytes)) + endpoint_bytes  # ServerUri
        params += struct.pack("<I", len(endpoint_bytes)) + endpoint_bytes  # EndpointUrl
        params += struct.pack("<I", len(session_name_bytes)) + session_name_bytes
        params += struct.pack("<I", 0)  # ClientNonce (empty)
        params += struct.pack("<I", 0)  # ClientCertificate (empty)
        params += struct.pack("<d", 1200000.0)  # RequestedSessionTimeout
        params += struct.pack("<I", 0)  # MaxResponseMessageSize

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_CREATE_SESSION_REQUEST, params
        )

    def _build_opcua_create_session_response(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
        session_id: int,
        auth_token: int,
        server_device: DeviceContext | None = None,
        endpoint_url: str = "opc.tcp://localhost:4840",
    ) -> bytes:
        """Build OPC UA CreateSession response with server identity from fingerprint.

        Args:
            secure_channel_id: Secure channel ID
            token_id: Security token ID
            sequence_number: Sequence number
            request_id: Request ID
            session_id: Session ID
            auth_token: Authentication token
            server_device: Server device context (for identity from fingerprint)
            endpoint_url: Server endpoint URL

        Returns:
            Complete CreateSession response bytes
        """
        # Response header (simplified)
        response_header = bytes(24)

        # Get server identity from fingerprint if available
        if server_device:
            identity = self._get_opcua_server_identity(server_device)
            app_name = identity["application_name"]
            app_uri = identity["application_uri"]
            product_uri = identity["product_uri"]
            software_version = identity["software_version"]
            manufacturer = identity["manufacturer_name"]
            product_name = identity["product_name"]
            logger.debug(
                f"OPC UA server identity: {manufacturer} {product_name} v{software_version}"
            )
        else:
            app_name = "OPC UA Server"
            app_uri = "urn:localhost:OPCUA:Server"
            product_uri = "urn:PacketArch:OPCUAServer"

        # CreateSession response parameters
        params = response_header
        params += struct.pack("<BH", 0x01, session_id)  # SessionId (NodeId)
        params += struct.pack("<BH", 0x01, auth_token)  # AuthenticationToken
        params += struct.pack("<d", 1200000.0)  # RevisedSessionTimeout
        params += struct.pack("<I", 0)  # ServerNonce (empty)
        params += struct.pack("<I", 0)  # ServerCertificate (empty)

        # ServerEndpoints - Include at least one endpoint with server application description
        # This is how Cyber Vision and other scanners identify the OPC UA server
        # Build a minimal EndpointDescription
        endpoint_data = b""
        endpoint_data += self._encode_opcua_string(endpoint_url)  # EndpointUrl
        # Server ApplicationDescription
        endpoint_data += self._encode_opcua_string(app_uri)  # ApplicationUri
        endpoint_data += self._encode_opcua_string(product_uri)  # ProductUri
        # ApplicationName (LocalizedText: Encoding mask + locale + text)
        endpoint_data += struct.pack("<B", 0x03)  # Encoding mask: has locale and text
        endpoint_data += self._encode_opcua_string("en")  # Locale
        endpoint_data += self._encode_opcua_string(app_name)  # Text
        endpoint_data += struct.pack("<I", 1)  # ApplicationType: Server
        endpoint_data += self._encode_opcua_string(None)  # GatewayServerUri (null)
        endpoint_data += self._encode_opcua_string(None)  # DiscoveryProfileUri (null)
        endpoint_data += struct.pack("<I", 0)  # DiscoveryUrls (empty array)
        # Rest of EndpointDescription
        endpoint_data += struct.pack("<I", 0)  # ServerCertificate (empty)
        endpoint_data += struct.pack("<I", 1)  # SecurityMode: None
        endpoint_data += self._encode_opcua_string(OPCUA_SECURITY_NONE)  # SecurityPolicyUri
        endpoint_data += struct.pack("<I", 0)  # UserIdentityTokens (empty array)
        endpoint_data += self._encode_opcua_string(None)  # TransportProfileUri
        endpoint_data += struct.pack("<B", 0)  # SecurityLevel

        # ServerEndpoints array (1 endpoint)
        params += struct.pack("<I", 1) + endpoint_data

        params += struct.pack("<I", 0)  # ServerSoftwareCertificates (empty)
        params += struct.pack("<I", 0)  # ServerSignature (empty)
        params += struct.pack("<I", 65535)  # MaxRequestMessageSize

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_CREATE_SESSION_RESPONSE, params
        )

    def _build_opcua_activate_session_request(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
    ) -> bytes:
        """Build OPC UA ActivateSession request."""
        # Request header
        request_header = bytes(24)

        # ActivateSession parameters (minimal)
        params = request_header
        params += struct.pack("<I", 0)  # ClientSignature (empty)
        params += struct.pack("<I", 0)  # ClientSoftwareCertificates (empty)
        params += struct.pack("<I", 0)  # LocaleIds (empty)
        params += struct.pack("<I", 0)  # UserIdentityToken (anonymous)
        params += struct.pack("<I", 0)  # UserTokenSignature (empty)

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_ACTIVATE_SESSION_REQUEST, params
        )

    def _build_opcua_activate_session_response(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
    ) -> bytes:
        """Build OPC UA ActivateSession response."""
        # Response header
        response_header = bytes(24)

        # ActivateSession response parameters
        params = response_header
        params += struct.pack("<I", 0)  # ServerNonce (empty)
        params += struct.pack("<I", 0)  # Results (empty)
        params += struct.pack("<I", 0)  # DiagnosticInfos (empty)

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_ACTIVATE_SESSION_RESPONSE, params
        )

    def _build_opcua_create_subscription_request(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
        publishing_interval: float = 1000.0,
    ) -> bytes:
        """Build OPC UA CreateSubscription request."""
        request_header = bytes(24)

        params = request_header
        params += struct.pack("<d", publishing_interval)  # RequestedPublishingInterval
        params += struct.pack("<I", 10)  # RequestedLifetimeCount
        params += struct.pack("<I", 3)   # RequestedMaxKeepAliveCount
        params += struct.pack("<I", 0)   # MaxNotificationsPerPublish (unlimited)
        params += struct.pack("<B", 1)   # PublishingEnabled
        params += struct.pack("<B", 0)   # Priority

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_CREATE_SUBSCRIPTION_REQUEST, params
        )

    def _build_opcua_create_subscription_response(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
        subscription_id: int,
        publishing_interval: float = 1000.0,
    ) -> bytes:
        """Build OPC UA CreateSubscription response."""
        response_header = bytes(24)

        params = response_header
        params += struct.pack("<I", subscription_id)
        params += struct.pack("<d", publishing_interval)  # RevisedPublishingInterval
        params += struct.pack("<I", 10)  # RevisedLifetimeCount
        params += struct.pack("<I", 3)   # RevisedMaxKeepAliveCount

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_CREATE_SUBSCRIPTION_RESPONSE, params
        )

    def _build_opcua_publish_request(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
    ) -> bytes:
        """Build OPC UA Publish request."""
        request_header = bytes(24)

        params = request_header
        params += struct.pack("<I", 0)  # SubscriptionAcknowledgements (empty)

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_PUBLISH_REQUEST, params
        )

    def _build_opcua_publish_response(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
        subscription_id: int,
        notification_data: list[tuple[int, float]] | None = None,
    ) -> bytes:
        """Build OPC UA Publish response with data change notifications.

        Args:
            notification_data: List of (node_id, value) tuples for data changes
        """
        response_header = bytes(24)

        params = response_header
        params += struct.pack("<I", subscription_id)  # SubscriptionId

        if notification_data:
            # Build data change notification
            params += struct.pack("<I", 1)  # AvailableSequenceNumbers count
            params += struct.pack("<I", sequence_number)  # SequenceNumber
            params += struct.pack("<B", 1)  # MoreNotifications = false

            # NotificationMessage
            params += struct.pack("<I", sequence_number)  # SequenceNumber
            current_time = int(time.time() * 10000000) + 116444736000000000
            params += struct.pack("<Q", current_time)  # PublishTime

            # NotificationData (DataChangeNotification)
            params += struct.pack("<I", len(notification_data))  # MonitoredItems count
            for node_id, value in notification_data:
                params += struct.pack("<I", node_id)  # ClientHandle
                params += struct.pack("<d", value)    # Value (as double)
        else:
            params += struct.pack("<I", 0)  # Empty notifications

        params += struct.pack("<I", 0)  # Results (empty)
        params += struct.pack("<I", 0)  # DiagnosticInfos (empty)

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_PUBLISH_RESPONSE, params
        )

    def _build_opcua_read_request(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
        node_ids: list[int],
    ) -> bytes:
        """Build OPC UA Read request."""
        request_header = bytes(24)

        params = request_header
        params += struct.pack("<d", 0.0)  # MaxAge
        params += struct.pack("<I", 0)    # TimestampsToReturn (Source)
        params += struct.pack("<I", len(node_ids))  # NodesToRead count

        for node_id in node_ids:
            params += struct.pack("<BH", 0x01, node_id)  # NodeId
            params += struct.pack("<I", 13)  # AttributeId (Value)
            params += struct.pack("<I", 0xFFFFFFFF)  # IndexRange (null)
            params += struct.pack("<I", 0)  # DataEncoding (null)

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_READ_REQUEST, params
        )

    def _build_opcua_read_response(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
        values: list[float],
    ) -> bytes:
        """Build OPC UA Read response."""
        response_header = bytes(24)

        params = response_header
        params += struct.pack("<I", len(values))  # Results count

        for value in values:
            params += struct.pack("<I", 0)  # StatusCode (Good)
            params += struct.pack("<d", value)  # Value

        params += struct.pack("<I", 0)  # DiagnosticInfos (empty)

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_READ_RESPONSE, params
        )

    def _build_opcua_close_session_request(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
    ) -> bytes:
        """Build OPC UA CloseSession request."""
        request_header = bytes(24)

        params = request_header
        params += struct.pack("<B", 1)  # DeleteSubscriptions

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_CLOSE_SESSION_REQUEST, params
        )

    def _build_opcua_close_session_response(
        self,
        secure_channel_id: int,
        token_id: int,
        sequence_number: int,
        request_id: int,
    ) -> bytes:
        """Build OPC UA CloseSession response."""
        response_header = bytes(24)

        return self._build_opcua_message(
            secure_channel_id, token_id, sequence_number, request_id,
            OPCUA_SERVICE_CLOSE_SESSION_RESPONSE, response_header
        )

    def _build_enip_list_identity_request(self) -> bytes:
        """Build EtherNet/IP ListIdentity request."""
        # Encapsulation header (24 bytes) - no data for ListIdentity request
        # Command(2) + Length(2) + Session(4) + Status(4) + Context(8) + Options(4)
        return struct.pack(
            "<HHIIQI",
            ENIP_CMD_LIST_IDENTITY,  # Command
            0,                        # Length (no data)
            0,                        # Session handle
            0,                        # Status
            0,                        # Sender context (8 bytes)
            0,                        # Options (4 bytes)
        )

    def _build_enip_list_identity_response(
        self, src: DeviceContext
    ) -> bytes:
        """Build EtherNet/IP ListIdentity response with device fingerprint and CVE overrides."""
        # Use get_effective_identity to apply CVE vulnerability overrides
        eip_identity = src.get_effective_identity("ethernet_ip_identity")

        # Validate 16-bit fields to prevent struct.pack overflow
        vendor_id = _validate_uint16(eip_identity.get("vendor_id", 1), "vendor_id", 1)
        device_type = _validate_uint16(eip_identity.get("device_type", 14), "device_type", 14)
        product_code = _validate_uint16(eip_identity.get("product_code", 1), "product_code", 1)
        # 8-bit fields
        revision_major = _validate_uint8(eip_identity.get("revision_major", 1), "revision_major", 1)
        revision_minor = _validate_uint8(eip_identity.get("revision_minor", 0), "revision_minor", 0)
        # Serial number must be unique per device - generate from device_id if not provided
        serial_number = eip_identity.get("serial_number")
        if serial_number is None:
            import hashlib
            serial_number = int.from_bytes(hashlib.sha256(f"{src.device_id}:enip".encode()).digest()[:4], "big")
        product_name = eip_identity.get("product_name", "Unknown Device")[:32]
        state = _validate_uint8(eip_identity.get("state", 3), "state", 3)

        # Socket address info (16 bytes)
        ip_parts = [int(x) for x in src.ip_address.split(".")]
        socket_addr = struct.pack(
            ">HHBBBB8s",
            2,  # sin_family (AF_INET)
            src.port,
            ip_parts[0], ip_parts[1], ip_parts[2], ip_parts[3],
            b"\x00" * 8,  # sin_zero
        )

        # Identity item data (inside the CIP Identity item)
        # Format: Protocol Version + Socket Address + Identity attributes
        product_name_bytes = product_name.encode("utf-8")

        # Identity attributes after socket address
        # Vendor(2) + DevType(2) + ProdCode(2) + RevMajor(1) + RevMinor(1) + Status(2) + Serial(4) + NameLen(1)
        identity_attrs = struct.pack(
            "<HHHBBHIB",
            vendor_id,
            device_type,
            product_code,
            revision_major,
            revision_minor,
            0x0030,        # Status (owned)
            serial_number,
            len(product_name_bytes),
        ) + product_name_bytes + struct.pack("<B", state)

        # CIP Identity item data: protocol version (2) + socket addr (16) + identity attrs
        identity_item_data = struct.pack("<H", 0x0001) + socket_addr + identity_attrs

        # CPF structure: 1 item of type 0x000C (CIP Identity)
        cpf_data = struct.pack(
            "<HHH",
            1,              # Item count = 1
            0x000C,         # Item type = CIP Identity
            len(identity_item_data),  # Item length
        ) + identity_item_data

        # Encapsulation header (24 bytes)
        # Command(2) + Length(2) + Session(4) + Status(4) + Context(8) + Options(4)
        header = struct.pack(
            "<HHIIQI",
            ENIP_CMD_LIST_IDENTITY,
            len(cpf_data),
            0,  # Session handle
            0,  # Status
            0,  # Sender context (8 bytes)
            0,  # Options (4 bytes)
        )

        return header + cpf_data

    def _build_cip_identity_response(self, fingerprint: dict) -> bytes:
        """Build CIP GetAttributeAll response for Identity Object."""
        eip_identity = fingerprint.get("ethernet_ip_identity", {})
        cip_identity = fingerprint.get("cip_identity_object", {})

        # Validate 16-bit and 8-bit fields to prevent struct.pack overflow
        vendor_id = _validate_uint16(eip_identity.get("vendor_id", 1), "vendor_id", 1)
        device_type = _validate_uint16(eip_identity.get("device_type", 14), "device_type", 14)
        product_code = _validate_uint16(eip_identity.get("product_code", 1), "product_code", 1)
        revision_major = _validate_uint8(eip_identity.get("revision_major", 1), "revision_major", 1)
        revision_minor = _validate_uint8(eip_identity.get("revision_minor", 0), "revision_minor", 0)
        # Serial number must be unique per device - generate from device_id if not provided
        serial_number = eip_identity.get("serial_number")
        if serial_number is None:
            import hashlib
            serial_number = int.from_bytes(hashlib.sha256(f"{src.device_id}:enip".encode()).digest()[:4], "big")
        product_name = eip_identity.get("product_name", "Unknown")[:32]
        state = _validate_uint8(eip_identity.get("state", 3), "state", 3)

        # Build Identity Object attributes
        product_name_bytes = product_name.encode("utf-8")
        attr_data = struct.pack(
            "<HHHBBHI",
            vendor_id,
            device_type,
            product_code,
            revision_major,
            revision_minor,
            0x0030,  # Status
            serial_number,
        ) + struct.pack("<B", len(product_name_bytes)) + product_name_bytes
        attr_data += struct.pack("<B", state)

        # Add extended attributes (9-20) from cip_identity_object
        config_consistency = cip_identity.get("configuration_consistency_value", 0)
        heartbeat = cip_identity.get("heartbeat_interval", 250)
        protection_mode = cip_identity.get("protection_mode", 0)
        max_connections = cip_identity.get("maximum_cip_connections", 32)

        attr_data += struct.pack("<IBHH", config_consistency, heartbeat, protection_mode, max_connections)

        # CIP response header (service | 0x80, reserved, status, additional_status_size)
        response = struct.pack("<BBBB", CIP_SERVICE_GET_ATTRIBUTE_ALL | 0x80, 0, 0, 0) + attr_data
        return response

    # ==================== S7comm Packet Building ====================

    def _build_s7_tpkt_cotp_header(self, payload: bytes, cotp_type: int = COTP_PDU_DT) -> bytes:
        """Build TPKT + COTP header wrapping S7comm payload.

        Args:
            payload: S7comm PDU payload
            cotp_type: COTP PDU type (DT for data, CR for connection request, CC for confirm)

        Returns:
            Complete TPKT + COTP + payload
        """
        if cotp_type == COTP_PDU_DT:
            # Data Transfer: COTP header is 3 bytes
            cotp_header = struct.pack(">BBB", 2, cotp_type, 0x80)  # Length, PDU type, TPDU number/EOT
        elif cotp_type == COTP_PDU_CR:
            # Connection Request: header + TPDU params + TSAPs
            cotp_header = struct.pack(
                ">BBHHB",
                17,          # Header length
                cotp_type,   # PDU type (CR)
                0x0000,      # DST reference
                0x0001,      # SRC reference
                0x00,        # Class/Options
            ) + struct.pack(">BBH", 0xC0, 2, 0x0A) + struct.pack(">BB", 0xC1, 2) + b"\x01\x00" + struct.pack(">BB", 0xC2, 2) + b"\x01\x02"
        elif cotp_type == COTP_PDU_CC:
            # Connection Confirm: similar to CR
            cotp_header = struct.pack(
                ">BBHHB",
                17,          # Header length
                cotp_type,   # PDU type (CC)
                0x0001,      # DST reference
                0x0001,      # SRC reference
                0x00,        # Class/Options
            ) + struct.pack(">BBH", 0xC0, 2, 0x0A) + struct.pack(">BB", 0xC1, 2) + b"\x01\x02" + struct.pack(">BB", 0xC2, 2) + b"\x01\x00"
        else:
            cotp_header = struct.pack(">BBB", 2, COTP_PDU_DT, 0x80)

        total_length = 4 + len(cotp_header) + len(payload)  # TPKT(4) + COTP + payload
        tpkt_header = struct.pack(">BBH", TPKT_VERSION, 0, total_length)

        return tpkt_header + cotp_header + payload

    def _build_s7_setup_communication_request(self) -> bytes:
        """Build S7comm Setup Communication request."""
        # S7comm header
        s7_header = struct.pack(
            ">BBHHHH",
            0x32,           # Protocol ID
            S7_PDU_JOB,     # PDU type (Job)
            0x0000,         # Reserved
            0x0000,         # PDU reference
            8,              # Parameter length
            0,              # Data length
        )
        # Setup Communication parameters (5 fields: func, reserved, maxAmqCalling, maxAmqCalled, pduLen)
        params = struct.pack(
            ">BBHHH",
            S7_FUNC_SETUP_COMM,  # Function code
            0x00,                # Reserved
            1,                   # Max AmQ calling
            1,                   # Max AmQ called
            480,                 # PDU length
        )
        return self._build_s7_tpkt_cotp_header(s7_header + params)

    def _build_s7_setup_communication_response(self) -> bytes:
        """Build S7comm Setup Communication response."""
        s7_header = struct.pack(
            ">BBHHHH",
            0x32,               # Protocol ID
            S7_PDU_ACK_DATA,    # PDU type (Ack-Data)
            0x0000,             # Reserved
            0x0000,             # PDU reference
            8,                  # Parameter length
            0,                  # Data length
        )
        params = struct.pack(
            ">BBHHH",
            S7_FUNC_SETUP_COMM,  # Function code
            0x00,                # Reserved
            1,                   # Max AmQ calling
            1,                   # Max AmQ called
            480,                 # PDU length
        )
        return self._build_s7_tpkt_cotp_header(s7_header + params)

    def _build_s7_szl_request(self, szl_id: int = SZL_ID_MODULE_ID, szl_index: int = 0x0000) -> bytes:
        """Build S7comm SZL (System Status List) read request.

        Args:
            szl_id: SZL ID (0x0011 for module ID, 0x001C for component ID)
            szl_index: SZL index

        Returns:
            Complete S7comm userdata request for SZL read
        """
        # Userdata parameters
        param_header = struct.pack(
            ">BBB",
            0x00, 0x01, 0x12,  # Constant header for userdata
        )
        param_data = struct.pack(
            ">BBBBBB",
            0x04,                    # Length of following
            0x11,                    # Method (request)
            (S7_UD_FUNCGROUP_CPU << 4) | S7_UD_SUBFUNCTION_READ_SZL,  # Type/Function group + subfunction
            0x00,                    # Sequence
            0x00, 0x00,              # Data unit reference
        )
        params = param_header + param_data

        # SZL data
        szl_data = struct.pack(
            ">BBHH",
            0xFF,       # Return code (success)
            0x09,       # Transport size (Octet string)
            4,          # Data length
            szl_id,     # SZL ID
        ) + struct.pack(">H", szl_index)

        # S7comm header
        s7_header = struct.pack(
            ">BBHHHH",
            0x32,               # Protocol ID
            S7_PDU_USERDATA,    # PDU type (Userdata)
            0x0000,             # Reserved
            0x0100,             # PDU reference
            len(params),        # Parameter length
            len(szl_data),      # Data length
        )

        return self._build_s7_tpkt_cotp_header(s7_header + params + szl_data)

    def _build_s7_szl_response(
        self, device: DeviceContext, szl_id: int = SZL_ID_MODULE_ID
    ) -> bytes:
        """Build S7comm SZL response with device identification.

        This contains the firmware version that Cyber Vision uses for CVE detection.

        Args:
            device: Device context with s7_identity
            szl_id: SZL ID being responded to

        Returns:
            Complete S7comm userdata response with SZL data
        """
        # Get effective S7 identity with CVE overrides applied
        s7_identity = device.get_effective_identity("s7_identity")

        # Extract identity values
        order_code = s7_identity.get("order_code", "6ES7 516-3AN01-0AB0")
        firmware_version = s7_identity.get("firmware_version", "V2.8.0")
        # Serial number must be unique per device - generate from device_id if not provided
        serial_number = s7_identity.get("serial_number")
        if serial_number is None:
            import hashlib
            hex_portion = hashlib.sha256(f"{device.device_id}:s7".encode()).digest()[:4].hex().upper()
            serial_number = f"S V-{hex_portion}"
        module_type = s7_identity.get("module_type", "CPU 1516-3 PN/DP")
        hw_version = s7_identity.get("hardware_version", "1")

        # Build SZL record data (Module identification - SZL 0x0011)
        # Format: SZL header + record data
        # Record: Index(2) + OrderCode(20) + HWVersion(2) + FWVersion(4) + SerialNumber(24)

        # Pad/truncate strings to fixed lengths
        order_code_bytes = order_code.encode("ascii")[:20].ljust(20, b" ")

        # Parse firmware version (e.g., "V2.8.0" -> [2, 8, 0])
        fw_parts = [0, 0, 0, 0]
        fw_str = firmware_version.lstrip("Vv")
        fw_nums = fw_str.split(".")
        for i, num in enumerate(fw_nums[:4]):
            try:
                fw_parts[i] = int(num)
            except ValueError:
                pass

        serial_bytes = serial_number.encode("ascii")[:24].ljust(24, b" ")
        module_type_bytes = module_type.encode("ascii")[:32].ljust(32, b" ")

        # SZL record (for SZL 0x0011, index 0x0001)
        szl_record = struct.pack(">H", 0x0001)  # Index
        szl_record += order_code_bytes           # Order code (20 bytes)
        szl_record += struct.pack(">H", int(hw_version) if hw_version.isdigit() else 1)  # HW version
        szl_record += struct.pack(">BBBB", *fw_parts[:4])  # FW version (4 bytes: V.R.F.B)
        szl_record += serial_bytes               # Serial number (24 bytes)
        szl_record += module_type_bytes          # Module type (32 bytes)

        # SZL data header
        # The SZL header structure is:
        # - SZL-ID (2 bytes): Which system status list
        # - Index (2 bytes): Filter/partial list index
        # - Partial list length (2 bytes): Size of one data record
        # - Partial list count (2 bytes): Number of records (usually 1)
        szl_header = struct.pack(
            ">HHHH",
            szl_id,           # SZL ID (0x0011 for module ID)
            0x0001,           # Index (partial list filter)
            len(szl_record),  # Length of one data record
            0x0001,           # Number of records
        )

        szl_data = struct.pack(
            ">BBH",
            0xFF,       # Return code (success)
            0x09,       # Transport size (byte)
            len(szl_header) + len(szl_record),  # Data length
        )
        szl_data += szl_header
        szl_data += szl_record

        # Userdata parameters (response)
        param_header = struct.pack(">BBB", 0x00, 0x01, 0x12)
        param_data = struct.pack(
            ">BBBBBB",
            0x08,                    # Length
            0x12,                    # Method (response)
            (S7_UD_FUNCGROUP_CPU << 4) | S7_UD_SUBFUNCTION_READ_SZL,
            0x00,                    # Sequence
            0x01,                    # Data unit reference (last)
            0x00,                    # Error code (0 = no error)
        )
        param_data += struct.pack(">BB", 0x00, 0x00)  # Reserved
        params = param_header + param_data

        # S7comm header
        s7_header = struct.pack(
            ">BBHHHH",
            0x32,               # Protocol ID
            S7_PDU_USERDATA,    # PDU type
            0x0000,             # Reserved
            0x0100,             # PDU reference
            len(params),        # Parameter length
            len(szl_data),      # Data length
        )

        response = self._build_s7_tpkt_cotp_header(s7_header + params + szl_data)

        logger.debug(
            f"S7 SZL response: order_code={order_code}, fw={firmware_version}, "
            f"serial={serial_number}, module={module_type}"
        )

        return response

    def _build_s7_szl_component_response(self, device: DeviceContext) -> bytes:
        """Build S7comm SZL 0x001C (Component Identification) response.

        This contains firmware version as ASCII string which Cyber Vision
        may use for firmware extraction.

        The SZL 0x001C format has firmware as an 8-byte ASCII string "V x.x.x "
        which is more easily parseable than the binary format in SZL 0x0011.

        Args:
            device: Device context with s7_identity

        Returns:
            Complete S7comm userdata response with SZL 0x001C data
        """
        # Get effective S7 identity with CVE overrides applied
        s7_identity = device.get_effective_identity("s7_identity")

        # Extract identity values
        module_type = s7_identity.get("module_type", "CPU 1516-3 PN/DP")
        firmware_version = s7_identity.get("firmware_version", "V2.8.0")

        # Build SZL 0x001C record data (Component Identification)
        # Record format:
        # - Index (2 bytes)
        # - Component name (24 bytes ASCII)
        # - Reserved (2 bytes)
        # - Component type (1 byte)
        # - Reserved (1 byte)
        # - Manufacturer ID (2 bytes) - 0x002A = Siemens
        # - Date (3 bytes)
        # - Reserved (1 byte)
        # - Version (8 bytes ASCII) - This is the key field for CV

        # Format firmware as 8-byte ASCII string "V x.x.x "
        fw_str = firmware_version if firmware_version.startswith("V") else f"V{firmware_version}"
        # Ensure space after V: "V2.8.0" -> "V 2.8.0"
        if len(fw_str) > 1 and fw_str[1] != " ":
            fw_str = f"V {fw_str[1:]}"
        fw_bytes = fw_str.encode("ascii")[:8].ljust(8, b" ")

        # Component name (24 bytes)
        comp_name = module_type.encode("ascii")[:24].ljust(24, b" ")

        # SZL 0x001C record for index 0x0001 (CPU)
        szl_record = struct.pack(">H", 0x0001)  # Index
        szl_record += comp_name                  # Component name (24 bytes)
        szl_record += struct.pack(">H", 0x0000)  # Reserved
        szl_record += struct.pack(">B", 0x01)    # Component type (1 = CPU)
        szl_record += struct.pack(">B", 0x00)    # Reserved
        szl_record += struct.pack(">H", 0x002A)  # Manufacturer ID (Siemens = 0x002A)
        szl_record += struct.pack(">BBB", 0x00, 0x00, 0x00)  # Date
        szl_record += struct.pack(">B", 0x00)    # Reserved
        szl_record += fw_bytes                   # Version (8 bytes ASCII)

        # SZL header
        szl_header = struct.pack(
            ">HHHH",
            SZL_ID_COMPONENT_ID,  # SZL ID 0x001C
            0x0001,               # Index
            len(szl_record),      # Length of one data record
            0x0001,               # Number of records
        )

        szl_data = struct.pack(
            ">BBH",
            0xFF,       # Return code (success)
            0x09,       # Transport size
            len(szl_header) + len(szl_record),  # Data length
        )
        szl_data += szl_header
        szl_data += szl_record

        # Userdata parameters (response)
        param_header = struct.pack(">BBB", 0x00, 0x01, 0x12)
        param_data = struct.pack(
            ">BBBBBB",
            0x08,                    # Length
            0x12,                    # Method (response)
            (S7_UD_FUNCGROUP_CPU << 4) | S7_UD_SUBFUNCTION_READ_SZL,
            0x00,                    # Sequence
            0x01,                    # Data unit reference (last)
            0x00,                    # Error code (0 = no error)
        )
        param_data += struct.pack(">BB", 0x00, 0x00)  # Reserved
        params = param_header + param_data

        # S7comm header
        s7_header = struct.pack(
            ">BBHHHH",
            0x32,               # Protocol ID
            S7_PDU_USERDATA,    # PDU type
            0x0000,             # Reserved
            0x0100,             # PDU reference
            len(params),        # Parameter length
            len(szl_data),      # Data length
        )

        response = self._build_s7_tpkt_cotp_header(s7_header + params + szl_data)

        logger.debug(
            f"S7 SZL 0x001C response: component={module_type}, fw={fw_str}"
        )

        return response

    def _build_profinet_dcp_identify_request(self, src: DeviceContext, xid: int) -> bytes:
        """Build PROFINET DCP Identify Request.

        Args:
            src: Source device context
            xid: Transaction ID (must match corresponding response)
        """
        # DCP header
        dcp_header = struct.pack(
            ">BBIHH",
            DCP_SERVICE_IDENTIFY,  # Service ID
            DCP_SERVICE_TYPE_REQUEST,  # Service type
            xid,  # Transaction ID
            0,    # Response delay
            0,    # Data length (no filter blocks)
        )

        # Build Ethernet frame with PROFINET EtherType
        frame = (
            Ether(src=src.mac_address, dst=DCP_MULTICAST_MAC, type=PROFINET_ETHERTYPE)
            / Raw(load=struct.pack(">H", 0xFEFE) + dcp_header)  # 0xFEFE = DCP frame ID
        )
        return bytes(frame)

    def _build_profinet_dcp_identify_response(
        self, src: DeviceContext, dst: DeviceContext, xid: int
    ) -> bytes:
        """Build PROFINET DCP Identify Response with device fingerprint and CVE overrides."""
        # Use get_effective_identity to apply CVE vulnerability overrides
        pn_identity = src.get_effective_identity("profinet_identity")

        # Get identity values (support multiple key formats)
        # Validate 16-bit fields to prevent struct.pack overflow
        # Use device_name for unique station_name (critical for Cyber Vision)
        if src.device_name:
            station_name = src.device_name
        else:
            station_name = pn_identity.get("station_name", f"device-{src.device_id[:8]}")
        vendor_id = _validate_uint16(pn_identity.get("vendor_id", 0x002A), "profinet_vendor_id", 0x002A)
        device_id = _validate_uint16(pn_identity.get("device_id", 0x0001), "profinet_device_id", 0x0001)

        # Handle device_role - can be int or string like "controller", "device"
        raw_role = pn_identity.get("device_role", 0x01)
        if isinstance(raw_role, str):
            role_map = {"device": 1, "controller": 2, "multidevice": 4, "supervisor": 8}
            device_role = _validate_uint8(role_map.get(raw_role.lower(), 1), "profinet_device_role", 1)
        else:
            device_role = _validate_uint8(raw_role, "profinet_device_role", 1)
        order_id = pn_identity.get("order_id") or pn_identity.get("im0_order_id", "")
        sw_revision = (
            pn_identity.get("software_revision") or
            pn_identity.get("sw_release") or
            pn_identity.get("im0_sw_revision") or
            "V1.0"
        )
        hw_revision = pn_identity.get("hardware_revision") or pn_identity.get("im0_hw_revision", "1.0")
        if isinstance(hw_revision, int):
            hw_revision = str(hw_revision)
        # Serial number must be unique per device - generate from device_id if not provided
        serial_number = pn_identity.get("serial_number") or pn_identity.get("im0_serial_number")
        if not serial_number:
            import hashlib
            serial_number = hashlib.sha256(f"{src.device_id}:profinet".encode()).digest()[:8].hex().upper()[:16]
        device_type = pn_identity.get("device_type", "")

        # Build DCP blocks
        blocks = b""

        # Station name block (Option 0x02, Suboption 0x02)
        name_bytes = station_name.encode("ascii")
        blocks += struct.pack(">BBHH", 0x02, 0x02, len(name_bytes) + 2, 0x0000) + name_bytes
        if len(name_bytes) % 2:
            blocks += b"\x00"  # Padding

        # Device ID block (Option 0x02, Suboption 0x03) - Vendor ID + Device ID
        blocks += struct.pack(">BBHHH", 0x02, 0x03, 6, 0x0000, vendor_id) + struct.pack(">H", device_id)

        # Manufacturer-specific block (Option 0x02, Suboption 0x01) - Type of Station
        # THIS is what Cyber Vision reads as "profinetdcp-manufacturer-specific"
        # Format: Device type with firmware, e.g., "S7-1500 CPU 1516-3 PN/DP V2.8.0"
        manuf_parts = []
        if device_type:
            manuf_parts.append(device_type)
        if sw_revision:
            manuf_parts.append(sw_revision)
        if manuf_parts:
            manuf_str = " ".join(manuf_parts)
            manuf_bytes = manuf_str.encode("ascii")
            manuf_len = len(manuf_bytes) + 2  # +2 for BlockInfo
            blocks += struct.pack(">BBH", 0x02, 0x01, manuf_len) + struct.pack(">H", 0x0000) + manuf_bytes
            if len(manuf_bytes) % 2:
                blocks += b"\x00"  # Padding for word alignment

        # Device Role block (Option 0x02, Suboption 0x04)
        # Format: Option(1) + Suboption(1) + Length(2) + BlockInfo(2) + DeviceRole(1) + Reserved(1)
        # Length = 4: BlockInfo(2) + DeviceRole(1) + Reserved(1)
        blocks += struct.pack(">BBHHBB", 0x02, 0x04, 4, 0x0000, device_role, 0x00)

        # IP Address block (Option 0x01, Suboption 0x02)
        ip_parts = [int(x) for x in src.ip_address.split(".")]
        ip_block = struct.pack(">H", 0x0001)  # IP set flag
        ip_block += bytes(ip_parts)  # IP address
        ip_block += bytes([255, 255, 255, 0])  # Subnet mask
        ip_block += bytes([0, 0, 0, 0])  # Gateway
        blocks += struct.pack(">BBH", 0x01, 0x02, len(ip_block)) + ip_block

        # OEM Device ID block (Option 0x02, Suboption 0x08) - Contains firmware version!
        oem_parts = []
        if order_id:
            oem_parts.append(f"OrderID:{order_id}")
        if serial_number:
            oem_parts.append(f"SN:{serial_number}")
        if device_type:
            oem_parts.append(f"Type:{device_type}")
        if hw_revision:
            oem_parts.append(f"HW:{hw_revision}")
        if sw_revision:
            oem_parts.append(f"SW:{sw_revision}")  # KEY for CVE detection

        if oem_parts:
            oem_data = ";".join(oem_parts).encode("ascii")
            oem_len = len(oem_data) + 2
            blocks += struct.pack(">BBH", 0x02, 0x08, oem_len) + struct.pack(">H", 0x0000) + oem_data
            if len(oem_data) % 2:
                blocks += b"\x00"  # Padding

        # DCP header
        dcp_header = struct.pack(
            ">BBIHH",
            DCP_SERVICE_IDENTIFY,
            DCP_SERVICE_TYPE_RESPONSE,
            xid,
            0,  # Response delay
            len(blocks),
        )

        # Build Ethernet frame
        frame = (
            Ether(src=src.mac_address, dst=dst.mac_address, type=PROFINET_ETHERTYPE)
            / Raw(load=struct.pack(">H", 0xFEFF) + dcp_header + blocks)  # 0xFEFF = DCP response frame ID
        )
        return bytes(frame)

    def _build_lldp_tlv(self, tlv_type: int, data: bytes) -> bytes:
        """Build a single LLDP TLV (Type-Length-Value).

        TLV format: Type (7 bits) + Length (9 bits) = 2 bytes, followed by Value
        """
        length = len(data)
        # Type is upper 7 bits, Length is lower 9 bits
        type_length = (tlv_type << 9) | (length & 0x1FF)
        return struct.pack(">H", type_length) + data

    def _build_lldp_packet(self, src: DeviceContext) -> bytes:
        """Build LLDP packet with PROFINET extensions for device discovery.

        LLDP (Link Layer Discovery Protocol) is used by PROFINET devices for
        network discovery. This helps Cyber Vision extract firmware version
        from the System Description TLV.

        Args:
            src: Source device context with fingerprint data

        Returns:
            Complete LLDP Ethernet frame
        """
        # Get device identity from fingerprint
        pn_identity = src.get_effective_identity("profinet_identity")
        snmp_identity = src.get_effective_identity("snmp_identity")

        # Use device_name for unique station_name (critical for Cyber Vision)
        if src.device_name:
            station_name = src.device_name
        else:
            station_name = pn_identity.get("station_name", f"device-{src.device_id[:8]}")
        device_type = pn_identity.get("device_type", "")
        sw_revision = (
            pn_identity.get("software_revision") or
            pn_identity.get("sw_release") or
            pn_identity.get("im0_sw_revision") or
            "V1.0"
        )
        order_id = pn_identity.get("order_id") or pn_identity.get("im0_order_id", "")

        # Use SNMP sysDescr if available (provides rich device description)
        sys_descr = snmp_identity.get("sys_descr", "")
        if not sys_descr:
            # Build system description from PROFINET identity
            if device_type and sw_revision:
                sys_descr = f"{device_type} {sw_revision}"
            else:
                sys_descr = f"PROFINET Device {sw_revision}"

        tlvs = b""

        # Chassis ID TLV (required) - use MAC address
        chassis_data = struct.pack("B", LLDP_CHASSIS_SUBTYPE_MAC)
        chassis_data += bytes.fromhex(src.mac_address.replace(":", ""))
        tlvs += self._build_lldp_tlv(LLDP_TLV_CHASSIS_ID, chassis_data)

        # Port ID TLV (required) - use interface name
        port_name = pn_identity.get("port_name", "port-001")
        port_data = struct.pack("B", LLDP_PORT_SUBTYPE_INTERFACE_NAME)
        port_data += port_name.encode("ascii")
        tlvs += self._build_lldp_tlv(LLDP_TLV_PORT_ID, port_data)

        # TTL TLV (required) - 120 seconds
        ttl_data = struct.pack(">H", 120)
        tlvs += self._build_lldp_tlv(LLDP_TLV_TTL, ttl_data)

        # Port Description TLV (optional)
        port_desc = pn_identity.get("port_description", "PROFINET Port")
        tlvs += self._build_lldp_tlv(LLDP_TLV_PORT_DESC, port_desc.encode("ascii"))

        # System Name TLV (required for PROFINET)
        tlvs += self._build_lldp_tlv(LLDP_TLV_SYSTEM_NAME, station_name.encode("ascii"))

        # System Description TLV - KEY for firmware version extraction!
        # This should contain vendor, model, and firmware in a format CV can parse
        tlvs += self._build_lldp_tlv(LLDP_TLV_SYSTEM_DESC, sys_descr.encode("ascii"))

        # System Capabilities TLV
        # Capabilities: Bridge(0x0004), Router(0x0010), Station(0x0080)
        # For PROFINET IO Device, use Station capability
        capabilities = 0x0080  # Station Only
        enabled = 0x0080
        cap_data = struct.pack(">HH", capabilities, enabled)
        tlvs += self._build_lldp_tlv(LLDP_TLV_SYSTEM_CAP, cap_data)

        # Management Address TLV - IP address
        ip_bytes = bytes([int(x) for x in src.ip_address.split(".")])
        # Management Address Length (1) + Subtype (1=IPv4) + IP (4) + Interface Subtype (1) + Interface Number (4) + OID Length (1)
        mgmt_data = struct.pack("B", 5)  # Address string length (subtype + IP)
        mgmt_data += struct.pack("B", 1)  # Address subtype: IPv4
        mgmt_data += ip_bytes
        mgmt_data += struct.pack("B", 2)  # Interface numbering subtype: ifIndex
        mgmt_data += struct.pack(">I", 1)  # Interface number
        mgmt_data += struct.pack("B", 0)  # OID string length
        tlvs += self._build_lldp_tlv(LLDP_TLV_MGMT_ADDR, mgmt_data)

        # PROFINET-specific TLV (Org-specific) - Port Status
        # This helps identify the device as a PROFINET device
        pn_tlv_data = PROFINET_OUI  # OUI
        pn_tlv_data += struct.pack("B", 0x02)  # Subtype: Port Status
        pn_tlv_data += struct.pack(">HH", 0x0000, 0x0000)  # RT Class 2/3 status
        tlvs += self._build_lldp_tlv(LLDP_TLV_ORG_SPECIFIC, pn_tlv_data)

        # PROFINET Chassis MAC TLV (Org-specific)
        chassis_mac_tlv = PROFINET_OUI  # OUI
        chassis_mac_tlv += struct.pack("B", 0x05)  # Subtype: Chassis MAC
        chassis_mac_tlv += bytes.fromhex(src.mac_address.replace(":", ""))
        tlvs += self._build_lldp_tlv(LLDP_TLV_ORG_SPECIFIC, chassis_mac_tlv)

        # End of LLDPDU TLV
        tlvs += self._build_lldp_tlv(LLDP_TLV_END, b"")

        # Build Ethernet frame
        frame = (
            Ether(src=src.mac_address, dst=LLDP_MULTICAST_MAC, type=LLDP_ETHERTYPE)
            / Raw(load=tlvs)
        )

        return bytes(frame)

    def _build_gratuitous_arp(self, device: DeviceContext) -> bytes:
        """Build a Gratuitous ARP packet for IP-to-MAC discovery.

        Gratuitous ARP is sent by a device to announce its IP-to-MAC mapping.
        This ensures network monitoring tools like Cyber Vision can associate
        the device's IP address with its MAC address.

        Args:
            device: Device context with MAC and IP address

        Returns:
            Raw packet bytes
        """
        # Parse IP address to bytes
        ip_parts = device.ip_address.split(".")
        ip_bytes = bytes([int(p) for p in ip_parts])

        # Parse MAC address to bytes
        mac_bytes = bytes.fromhex(device.mac_address.replace(":", ""))

        # ARP packet structure:
        # - Hardware type (2 bytes): 0x0001 (Ethernet)
        # - Protocol type (2 bytes): 0x0800 (IPv4)
        # - Hardware address length (1 byte): 6
        # - Protocol address length (1 byte): 4
        # - Opcode (2 bytes): 0x0002 (ARP Reply)
        # - Sender hardware address (6 bytes): device MAC
        # - Sender protocol address (4 bytes): device IP
        # - Target hardware address (6 bytes): device MAC (gratuitous)
        # - Target protocol address (4 bytes): device IP (gratuitous)
        arp_payload = struct.pack(
            ">HHBBH",
            0x0001,  # Hardware type (Ethernet)
            0x0800,  # Protocol type (IPv4)
            6,       # Hardware address length
            4,       # Protocol address length
            0x0002,  # Opcode (ARP Reply)
        )
        arp_payload += mac_bytes       # Sender MAC
        arp_payload += ip_bytes        # Sender IP
        arp_payload += mac_bytes       # Target MAC (gratuitous: same as sender)
        arp_payload += ip_bytes        # Target IP (gratuitous: same as sender)

        # Build Ethernet frame with ARP ethertype (0x0806)
        # Destination is broadcast for gratuitous ARP
        frame = (
            Ether(src=device.mac_address, dst="ff:ff:ff:ff:ff:ff", type=0x0806)
            / Raw(load=arp_payload)
        )

        return bytes(frame)

    def _generate_discovery_sequences(self, time_ms: float) -> float:
        """Generate protocol-specific discovery sequences for all flows.

        Returns the timestamp after all discovery packets are scheduled.
        """
        current_time = time_ms

        # Track devices we've already generated discovery for PER PROTOCOL
        # (a device may need discovery via multiple protocols for full detection)
        discovered_enip: set[str] = set()
        discovered_profinet: set[str] = set()
        discovered_s7comm: set[str] = set()
        discovered_modbus: set[str] = set()
        discovered_snmp: set[str] = set()
        discovered_bacnet: set[str] = set()

        for flow_state in self.flows:
            flow = flow_state.flow
            protocol = flow.protocol
            dst = flow.destination
            src = flow.source

            if protocol == "ethernet_ip":
                # EtherNet/IP ListIdentity - generate for BOTH source and target devices
                for device in [dst, src]:
                    # Gate by supported_protocols (authoritative) rather than identity existence
                    if device_supports_protocol(device, "ethernet_ip") and device.device_id not in discovered_enip:
                        eip_identity = device.get_effective_identity("ethernet_ip_identity")
                        discovered_enip.add(device.device_id)

                        # ListIdentity request (broadcast discovery)
                        request = self._build_enip_list_identity_request()
                        # Use a scanner context for the request
                        scanner = DeviceContext(
                            device_id="scanner",
                            mac_address=src.mac_address if device == dst else dst.mac_address,
                            ip_address=src.ip_address if device == dst else dst.ip_address,
                            port=50000,
                        )
                        request_pkt = self._build_udp_packet(scanner, device, request)
                        self._schedule_event(current_time, ("packet", request_pkt))

                        # ListIdentity response (device -> scanner) - includes CVE overrides
                        response = self._build_enip_list_identity_response(device)
                        device_response = DeviceContext(
                            device_id=device.device_id,
                            mac_address=device.mac_address,
                            ip_address=device.ip_address,
                            port=44818,
                            vendor_fingerprint=device.vendor_fingerprint,
                            device_name=device.device_name,
                        )
                        response_pkt = self._build_udp_packet(device_response, scanner, response)
                        self._schedule_event(current_time + 20, ("packet", response_pkt))

                        current_time += 100
                        logger.info(
                            f"Scheduled EtherNet/IP discovery for {device.ip_address} "
                            f"(vendor={eip_identity.get('vendor_id')}, product={eip_identity.get('product_name', '')[:20]})"
                        )

            elif protocol in ("profinet", "profisafe"):
                # PROFINET DCP Identify - generate for BOTH source and target devices
                for device in [dst, src]:
                    # Gate by supported_protocols (authoritative) rather than identity existence
                    if device_supports_protocol(device, "profinet") and device.device_id not in discovered_profinet:
                        pn_identity = device.get_effective_identity("profinet_identity")
                        discovered_profinet.add(device.device_id)
                        xid = random.randint(1, 0xFFFFFFFF)

                        # DCP Identify request (multicast)
                        other = src if device == dst else dst
                        request = self._build_profinet_dcp_identify_request(other, xid)
                        self._schedule_event(current_time, ("packet", request))

                        # DCP Identify response (device -> controller)
                        response = self._build_profinet_dcp_identify_response(device, other, xid)
                        self._schedule_event(current_time + 30, ("packet", response))

                        # LLDP packet - PROFINET devices send LLDP for network discovery
                        # This provides firmware version in System Description TLV
                        lldp_pkt = self._build_lldp_packet(device)
                        self._schedule_event(current_time + 60, ("packet", lldp_pkt))

                        current_time += 100

                        # Get firmware version for logging
                        sw_revision = (
                            pn_identity.get("software_revision") or
                            pn_identity.get("sw_release") or
                            pn_identity.get("im0_sw_revision") or
                            "V1.0"
                        )
                        logger.info(
                            f"Scheduled PROFINET DCP+LLDP discovery for {device.mac_address} "
                            f"(vendor_id=0x{pn_identity.get('vendor_id', 0):04X}, "
                            f"station={pn_identity.get('station_name', 'unknown')}, "
                            f"sw_release={sw_revision}, "
                            f"order_id={pn_identity.get('order_id', 'none')})"
                        )

            elif protocol in ("s7comm", "s7comm_plus"):
                # S7comm SZL discovery - CRITICAL for Siemens device firmware detection
                # Generate for target device (PLC/controller)
                # Gate by supported_protocols (authoritative) rather than identity existence
                if device_supports_protocol(dst, "s7comm") and dst.device_id not in discovered_s7comm:
                    s7_identity = dst.get_effective_identity("s7_identity")
                    discovered_s7comm.add(dst.device_id)

                    # COTP Connection Request
                    cotp_cr = self._build_s7_tpkt_cotp_header(b"", COTP_PDU_CR)
                    cr_pkt = self._build_tcp_packet(
                        src, dst, cotp_cr, flow_state.seq_number, flow_state.ack_number
                    )
                    self._schedule_event(current_time, ("packet", cr_pkt))
                    flow_state.seq_number += len(cotp_cr)
                    current_time += 15

                    # COTP Connection Confirm
                    cotp_cc = self._build_s7_tpkt_cotp_header(b"", COTP_PDU_CC)
                    cc_pkt = self._build_tcp_packet(
                        dst, src, cotp_cc, flow_state.ack_number, flow_state.seq_number
                    )
                    self._schedule_event(current_time, ("packet", cc_pkt))
                    flow_state.ack_number += len(cotp_cc)
                    current_time += 15

                    # S7 Setup Communication Request
                    setup_req = self._build_s7_setup_communication_request()
                    setup_req_pkt = self._build_tcp_packet(
                        src, dst, setup_req, flow_state.seq_number, flow_state.ack_number
                    )
                    self._schedule_event(current_time, ("packet", setup_req_pkt))
                    flow_state.seq_number += len(setup_req)
                    current_time += 20

                    # S7 Setup Communication Response
                    setup_resp = self._build_s7_setup_communication_response()
                    setup_resp_pkt = self._build_tcp_packet(
                        dst, src, setup_resp, flow_state.ack_number, flow_state.seq_number
                    )
                    self._schedule_event(current_time, ("packet", setup_resp_pkt))
                    flow_state.ack_number += len(setup_resp)
                    current_time += 20

                    # S7 SZL Read Request (Module Identification)
                    szl_req = self._build_s7_szl_request(SZL_ID_MODULE_ID)
                    szl_req_pkt = self._build_tcp_packet(
                        src, dst, szl_req, flow_state.seq_number, flow_state.ack_number
                    )
                    self._schedule_event(current_time, ("packet", szl_req_pkt))
                    flow_state.seq_number += len(szl_req)
                    current_time += 30

                    # S7 SZL Read Response (contains firmware version for CVE detection)
                    szl_resp = self._build_s7_szl_response(dst, SZL_ID_MODULE_ID)
                    szl_resp_pkt = self._build_tcp_packet(
                        dst, src, szl_resp, flow_state.ack_number, flow_state.seq_number
                    )
                    self._schedule_event(current_time, ("packet", szl_resp_pkt))
                    flow_state.ack_number += len(szl_resp)
                    current_time += 30

                    # S7 SZL Read Request (Component Identification - 0x001C)
                    # This contains firmware as ASCII string which CV may prefer
                    szl_req_comp = self._build_s7_szl_request(SZL_ID_COMPONENT_ID)
                    szl_req_comp_pkt = self._build_tcp_packet(
                        src, dst, szl_req_comp, flow_state.seq_number, flow_state.ack_number
                    )
                    self._schedule_event(current_time, ("packet", szl_req_comp_pkt))
                    flow_state.seq_number += len(szl_req_comp)
                    current_time += 30

                    # S7 SZL 0x001C Response (firmware as ASCII "V x.x.x")
                    szl_resp_comp = self._build_s7_szl_component_response(dst)
                    szl_resp_comp_pkt = self._build_tcp_packet(
                        dst, src, szl_resp_comp, flow_state.ack_number, flow_state.seq_number
                    )
                    self._schedule_event(current_time, ("packet", szl_resp_comp_pkt))
                    flow_state.ack_number += len(szl_resp_comp)
                    current_time += 50

                    fw_version = s7_identity.get("firmware_version", "unknown")
                    order_code = s7_identity.get("order_code", "unknown")
                    logger.info(
                        f"Scheduled S7comm SZL discovery for {dst.ip_address} "
                        f"(order_code={order_code}, firmware={fw_version}, "
                        f"SZL 0x0011 + 0x001C)"
                    )

            elif protocol == "modbus_tcp":
                # Modbus FC 43 Read Device Identification
                # Gate by supported_protocols (authoritative) rather than identity existence
                if device_supports_protocol(dst, "modbus"):
                    # This will be sent as part of the first poll cycle
                    # Mark that we should send FC 43 request
                    flow_state.flow.config["send_device_id_request"] = True
                    logger.info(f"Will send Modbus FC 43 for {dst.ip_address}")

            elif protocol == "snmp":
                # SNMP sysDescr discovery - CRITICAL for Cyber Vision device identification
                for device in [dst, src]:
                    # Gate by supported_protocols (authoritative) rather than identity existence
                    if device_supports_protocol(device, "snmp") and device.device_id not in discovered_snmp:
                        discovered_snmp.add(device.device_id)

                        # Generate SNMP GetRequest for system OIDs
                        request_id = random.randint(1, 0x7FFFFFFF)
                        system_oids = [
                            SNMP_OIDS["sysDescr"],
                            SNMP_OIDS["sysObjectID"],
                            SNMP_OIDS["sysUpTime"],
                            SNMP_OIDS["sysName"],
                        ]

                        # SNMP manager/scanner
                        scanner = DeviceContext(
                            device_id="scanner",
                            mac_address=src.mac_address if device == dst else dst.mac_address,
                            ip_address=src.ip_address if device == dst else dst.ip_address,
                            port=random.randint(40000, 50000),
                        )

                        # Build and send GetRequest
                        request = self._build_snmp_get_request(request_id, system_oids)
                        device_context = DeviceContext(
                            device_id=device.device_id,
                            mac_address=device.mac_address,
                            ip_address=device.ip_address,
                            port=SNMP_AGENT_PORT,
                            vendor_fingerprint=device.vendor_fingerprint,
                            vulnerability_override=device.vulnerability_override,
                            device_name=device.device_name,
                        )
                        request_pkt = self._build_udp_packet(scanner, device_context, request)
                        self._schedule_event(current_time, ("packet", request_pkt))

                        # Build and send GetResponse with sysDescr (CVE detection)
                        # Uses get_effective_identity() to apply vulnerability overrides
                        uptime_ms = int(current_time)  # Use relative uptime
                        identity_values = self._get_snmp_identity_values(device_context, uptime_ms)
                        response = self._build_snmp_get_response(request_id, identity_values)
                        response_pkt = self._build_udp_packet(device_context, scanner, response)
                        self._schedule_event(current_time + 15, ("packet", response_pkt))

                        current_time += 100

                        # Log effective sysDescr (with vulnerability override applied)
                        effective_identity = device_context.get_effective_identity("snmp_identity")
                        sys_descr = effective_identity.get("sys_descr", "Unknown Device")
                        logger.info(
                            f"Scheduled SNMP discovery for {device.ip_address} "
                            f"(sysDescr={sys_descr[:50]})"
                        )

            elif protocol == "bacnet":
                # BACnet I-Am discovery - CRITICAL for Cyber Vision BMS device detection
                for device in [dst, src]:
                    # Gate by supported_protocols (authoritative) rather than identity existence
                    if device_supports_protocol(device, "bacnet") and device.device_id not in discovered_bacnet:
                        discovered_bacnet.add(device.device_id)

                        # Who-Is broadcast from scanner
                        other = src if device == dst else dst
                        who_is_request = self._build_bacnet_who_is()
                        scanner = DeviceContext(
                            device_id="scanner",
                            mac_address=other.mac_address,
                            ip_address=other.ip_address,
                            port=BACNET_PORT,
                        )
                        device_context = DeviceContext(
                            device_id=device.device_id,
                            mac_address=device.mac_address,
                            ip_address=device.ip_address,
                            port=BACNET_PORT,
                            vendor_fingerprint=device.vendor_fingerprint,
                            vulnerability_override=device.vulnerability_override,
                            device_name=device.device_name,
                        )

                        # Who-Is request (broadcast)
                        # Use broadcast MAC for Who-Is
                        broadcast_dst = DeviceContext(
                            device_id="broadcast",
                            mac_address="ff:ff:ff:ff:ff:ff",
                            ip_address="255.255.255.255",
                            port=BACNET_PORT,
                        )
                        request_pkt = self._build_udp_packet(scanner, broadcast_dst, who_is_request)
                        self._schedule_event(current_time, ("packet", request_pkt))

                        # I-Am response (contains vendor_id, model_name, firmware - CVE detection)
                        i_am_response = self._build_bacnet_i_am(device_context)
                        response_pkt = self._build_udp_packet(device_context, broadcast_dst, i_am_response)
                        self._schedule_event(current_time + 50, ("packet", response_pkt))

                        current_time += 150

                        # Log effective identity (with vulnerability overrides applied)
                        effective_identity = device_context.get_effective_identity("bacnet_identity")
                        vendor_id = effective_identity.get("vendor_id", 0)
                        model_name = effective_identity.get("model_name", "Unknown")
                        device_instance = effective_identity.get("device_instance", 0)
                        firmware_rev = effective_identity.get("firmware_revision", "Unknown")
                        logger.info(
                            f"Scheduled BACnet discovery for {device.ip_address} "
                            f"(vendor_id={vendor_id}, model={model_name[:30]}, "
                            f"firmware={firmware_rev}, instance={device_instance})"
                        )

        # ==================================================================
        # Universal EtherNet/IP Discovery - For ALL devices with EtherNet/IP identity
        # This ensures Cyber Vision can detect devices that are only sources
        # in flows (not targets), which normally wouldn't get discovery.
        # ==================================================================
        enip_universal: set[str] = set()
        for flow_state in self.flows:
            flow = flow_state.flow
            # Check both source and destination devices
            for device in [flow.destination, flow.source]:
                fingerprint = device.vendor_fingerprint or {}
                eip_identity = fingerprint.get("ethernet_ip_identity")
                # Skip if already discovered or no EtherNet/IP identity
                if not eip_identity or device.device_id in enip_universal:
                    continue
                # Skip if already discovered in protocol-specific discovery
                if device.device_id in discovered_enip:
                    continue
                enip_universal.add(device.device_id)

                # Use peer device as scanner
                other = flow.source if device == flow.destination else flow.destination
                scanner = DeviceContext(
                    device_id="enip_scanner",
                    mac_address=other.mac_address,
                    ip_address=other.ip_address,
                    port=50000,
                )

                # ListIdentity request (broadcast discovery)
                request = self._build_enip_list_identity_request()
                request_pkt = self._build_udp_packet(scanner, device, request)
                self._schedule_event(current_time, ("packet", request_pkt))

                # ListIdentity response (device -> scanner) - includes CVE overrides
                response = self._build_enip_list_identity_response(device)
                device_response = DeviceContext(
                    device_id=device.device_id,
                    mac_address=device.mac_address,
                    ip_address=device.ip_address,
                    port=44818,
                    vendor_fingerprint=device.vendor_fingerprint,
                    device_name=device.device_name,
                )
                response_pkt = self._build_udp_packet(device_response, scanner, response)
                self._schedule_event(current_time + 20, ("packet", response_pkt))

                current_time += 100
                logger.info(
                    f"Scheduled universal EtherNet/IP discovery for {device.ip_address} "
                    f"(vendor={eip_identity.get('vendor_id')}, product={eip_identity.get('product_name', '')[:20]})"
                )

        # ==================================================================
        # Universal Modbus Discovery - For ALL devices with Modbus identity
        # This ensures Cyber Vision can detect devices via FC 43 (MEI)
        # regardless of flow direction.
        # ==================================================================
        modbus_universal: set[str] = set()
        for flow_state in self.flows:
            flow = flow_state.flow
            # Check both source and destination devices
            for device in [flow.destination, flow.source]:
                fingerprint = device.vendor_fingerprint or {}
                modbus_identity = fingerprint.get("modbus_identity")
                # Skip if already discovered or no Modbus identity
                if not modbus_identity or device.device_id in modbus_universal:
                    continue
                # Skip if already marked for FC 43 in protocol-specific discovery
                if device.device_id in discovered_modbus:
                    continue
                modbus_universal.add(device.device_id)

                # Use peer device as scanner
                other = flow.source if device == flow.destination else flow.destination

                # Build TCP connection context for Modbus
                scanner = DeviceContext(
                    device_id="modbus_scanner",
                    mac_address=other.mac_address,
                    ip_address=other.ip_address,
                    port=random.randint(40000, 50000),
                )

                # Create temporary flow state for TCP sequence numbers
                temp_seq = random.randint(1000, 100000)
                temp_ack = random.randint(1000, 100000)

                # TCP SYN
                syn = self._build_tcp_packet(scanner, device, b"", temp_seq, 0, "S")
                self._schedule_event(current_time, ("packet", syn))
                current_time += 10

                # TCP SYN-ACK
                syn_ack = self._build_tcp_packet(device, scanner, b"", temp_ack, temp_seq + 1, "SA")
                self._schedule_event(current_time, ("packet", syn_ack))
                current_time += 10

                # TCP ACK
                ack = self._build_tcp_packet(scanner, device, b"", temp_seq + 1, temp_ack + 1, "A")
                self._schedule_event(current_time, ("packet", ack))
                current_time += 10

                # FC 43 Request (MEI type 0x0E, device ID code 0x01)
                transaction_id = random.randint(1, 65535)
                unit_id = 1
                fc43_request = struct.pack(
                    ">HHHBB BB",
                    transaction_id,  # Transaction ID
                    0,  # Protocol ID
                    2 + 3,  # Length
                    unit_id,  # Unit ID
                    0x2B,  # Function code 43
                    0x0E,  # MEI type
                    0x01,  # Read Device ID code (basic)
                )
                request_pkt = self._build_tcp_packet(
                    scanner, device, fc43_request, temp_seq + 1, temp_ack + 1
                )
                self._schedule_event(current_time, ("packet", request_pkt))
                current_time += 20

                # FC 43 Response with device identity
                device_context = DeviceContext(
                    device_id=device.device_id,
                    mac_address=device.mac_address,
                    ip_address=device.ip_address,
                    port=502,
                    vendor_fingerprint=device.vendor_fingerprint,
                    vulnerability_override=device.vulnerability_override,
                    device_name=device.device_name,
                )
                fc43_response = self._build_modbus_device_id_response(transaction_id, unit_id, device_context)
                response_pkt = self._build_tcp_packet(
                    device_context, scanner, fc43_response, temp_ack + 1, temp_seq + 1 + len(fc43_request)
                )
                self._schedule_event(current_time, ("packet", response_pkt))
                current_time += 50

                logger.info(
                    f"Scheduled universal Modbus FC43 discovery for {device.ip_address} "
                    f"(vendor={modbus_identity.get('vendor_name', '')[:20]}, "
                    f"product={modbus_identity.get('product_name', '')[:20]})"
                )

        # ==================================================================
        # Universal SNMP Discovery - For ALL devices with SNMP identity
        # This ensures Cyber Vision can detect firmware via sysDescr
        # regardless of the primary protocol (Modbus, EtherNet/IP, etc.)
        # ==================================================================
        snmp_discovered: set[str] = set()
        for flow_state in self.flows:
            flow = flow_state.flow
            # Check both source and destination devices
            for device in [flow.destination, flow.source]:
                fingerprint = device.vendor_fingerprint or {}
                snmp_identity = fingerprint.get("snmp_identity")
                # Skip if already discovered or no SNMP identity
                if not snmp_identity or device.device_id in snmp_discovered:
                    continue
                snmp_discovered.add(device.device_id)

                # Generate SNMP GetRequest for system OIDs
                request_id = random.randint(1, 0x7FFFFFFF)
                system_oids = [
                    SNMP_OIDS["sysDescr"],
                    SNMP_OIDS["sysObjectID"],
                    SNMP_OIDS["sysUpTime"],
                    SNMP_OIDS["sysName"],
                ]

                # SNMP manager/scanner (use a peer device or generate scanner)
                other = flow.source if device == flow.destination else flow.destination
                scanner = DeviceContext(
                    device_id="snmp_scanner",
                    mac_address=other.mac_address,
                    ip_address=other.ip_address,
                    port=random.randint(40000, 50000),
                )

                # Device context for response
                device_context = DeviceContext(
                    device_id=device.device_id,
                    mac_address=device.mac_address,
                    ip_address=device.ip_address,
                    port=SNMP_AGENT_PORT,
                    vendor_fingerprint=device.vendor_fingerprint,
                    vulnerability_override=device.vulnerability_override,
                    device_name=device.device_name,
                )

                # Build and schedule GetRequest
                request = self._build_snmp_get_request(request_id, system_oids)
                request_pkt = self._build_udp_packet(scanner, device_context, request)
                self._schedule_event(current_time, ("packet", request_pkt))

                # Build and schedule GetResponse with sysDescr (CVE detection)
                uptime_ms = int(current_time)
                identity_values = self._get_snmp_identity_values(device_context, uptime_ms)
                response = self._build_snmp_get_response(request_id, identity_values)
                response_pkt = self._build_udp_packet(device_context, scanner, response)
                self._schedule_event(current_time + 15, ("packet", response_pkt))

                current_time += 100

                # Log the SNMP discovery
                effective_identity = device_context.get_effective_identity("snmp_identity")
                sys_descr = effective_identity.get("sys_descr", "Unknown Device")
                logger.info(
                    f"Scheduled universal SNMP discovery for {device.ip_address} "
                    f"(sysDescr={sys_descr[:60]})"
                )

        # ==================================================================
        # Universal Gratuitous ARP - For ALL devices
        # This ensures Cyber Vision can associate IP with MAC for every device,
        # regardless of what protocol identity types they have.
        # ==================================================================
        arp_sent: set[str] = set()
        for flow_state in self.flows:
            flow = flow_state.flow
            for device in [flow.destination, flow.source]:
                if device.device_id not in arp_sent:
                    arp_sent.add(device.device_id)
                    arp_pkt = self._build_gratuitous_arp(device)
                    self._schedule_event(current_time, ("packet", arp_pkt))
                    current_time += 5
                    logger.debug(f"Scheduled gratuitous ARP for flow device {device.ip_address}")

        # Also send for all registered devices (catches devices not in flows)
        for device in self.all_devices:
            if device.device_id not in arp_sent:
                arp_sent.add(device.device_id)
                arp_pkt = self._build_gratuitous_arp(device)
                self._schedule_event(current_time, ("packet", arp_pkt))
                current_time += 5
                logger.debug(f"Scheduled gratuitous ARP for registered device {device.ip_address}")

        logger.info(f"Scheduled gratuitous ARP for {len(arp_sent)} devices")

        # ==================================================================
        # Orphan Device Discovery - For devices NOT in any flow
        # Some devices may be defined in the scenario but never used as
        # source or destination in any flow. These still need discovery.
        # ==================================================================
        # Collect all device IDs that appear in flows
        flow_device_ids: set[str] = set()
        for flow_state in self.flows:
            flow_device_ids.add(flow_state.flow.source.device_id)
            flow_device_ids.add(flow_state.flow.destination.device_id)

        # Find orphan devices (in all_devices but not in any flow)
        orphan_devices = [d for d in self.all_devices if d.device_id not in flow_device_ids]

        if orphan_devices:
            logger.info(f"Found {len(orphan_devices)} orphan devices not in any flow - generating discovery")

            # Use first flow device as scanner (if available), or create dummy
            scanner_base = None
            if self.flows:
                scanner_base = self.flows[0].flow.source

            for device in orphan_devices:
                # Generate scanner context
                if scanner_base:
                    scanner = DeviceContext(
                        device_id="orphan_scanner",
                        mac_address=scanner_base.mac_address,
                        ip_address=scanner_base.ip_address,
                        port=random.randint(40000, 50000),
                    )
                else:
                    # Create a dummy scanner if no flows exist
                    scanner = DeviceContext(
                        device_id="orphan_scanner",
                        mac_address="00:00:00:00:00:01",
                        ip_address="10.0.0.1",
                        port=random.randint(40000, 50000),
                    )

                # EtherNet/IP discovery for orphan device
                # Use device_supports_protocol for consistent gating AND check vendor_id
                # to prevent Siemens devices from appearing as Rockwell (vendor_id=1 default)
                if device_supports_protocol(device, "ethernet_ip"):
                    fingerprint = device.vendor_fingerprint or {}
                    eip_identity = fingerprint.get("ethernet_ip_identity", {})
                    # Only generate EtherNet/IP traffic if identity has vendor_id
                    if eip_identity.get("vendor_id") is not None:
                        request = self._build_enip_list_identity_request()
                        request_pkt = self._build_udp_packet(scanner, device, request)
                        self._schedule_event(current_time, ("packet", request_pkt))

                        response = self._build_enip_list_identity_response(device)
                        device_response = DeviceContext(
                            device_id=device.device_id,
                            mac_address=device.mac_address,
                            ip_address=device.ip_address,
                            port=44818,
                            vendor_fingerprint=device.vendor_fingerprint,
                            device_name=device.device_name,
                        )
                        response_pkt = self._build_udp_packet(device_response, scanner, response)
                        self._schedule_event(current_time + 20, ("packet", response_pkt))
                        current_time += 50
                        logger.info(f"Scheduled orphan EtherNet/IP discovery for {device.ip_address}")
                    else:
                        logger.warning(
                            f"Skipping EtherNet/IP discovery for {device.ip_address}: "
                            f"ethernet_ip_identity missing vendor_id (would default to Rockwell)"
                        )

                # PROFINET DCP discovery for orphan device
                # Use device_supports_protocol for consistent gating
                if device_supports_protocol(device, "profinet"):
                    fingerprint = device.vendor_fingerprint or {}
                    pn_identity = fingerprint.get("profinet_identity", {})
                    if pn_identity.get("vendor_id") is not None:
                        xid = random.randint(1, 0xFFFFFFFF)
                        request = self._build_profinet_dcp_identify_request(scanner, xid)
                        self._schedule_event(current_time, ("packet", request))

                        response = self._build_profinet_dcp_identify_response(device, scanner, xid)
                        self._schedule_event(current_time + 30, ("packet", response))

                        lldp_pkt = self._build_lldp_packet(device)
                        self._schedule_event(current_time + 60, ("packet", lldp_pkt))
                        current_time += 100
                        logger.info(f"Scheduled orphan PROFINET discovery for {device.mac_address}")

                # SNMP discovery for orphan device
                # Use device_supports_protocol for consistent gating
                if device_supports_protocol(device, "snmp"):
                    fingerprint = device.vendor_fingerprint or {}
                    snmp_identity = fingerprint.get("snmp_identity", {})
                    request_id = random.randint(1, 0x7FFFFFFF)
                    system_oids = [
                        SNMP_OIDS["sysDescr"],
                        SNMP_OIDS["sysObjectID"],
                        SNMP_OIDS["sysUpTime"],
                        SNMP_OIDS["sysName"],
                    ]

                    device_context = DeviceContext(
                        device_id=device.device_id,
                        mac_address=device.mac_address,
                        ip_address=device.ip_address,
                        port=SNMP_AGENT_PORT,
                        vendor_fingerprint=device.vendor_fingerprint,
                        device_name=device.device_name,
                    )

                    request = self._build_snmp_get_request(request_id, system_oids)
                    request_pkt = self._build_udp_packet(scanner, device_context, request)
                    self._schedule_event(current_time, ("packet", request_pkt))

                    uptime_ms = int(current_time)
                    identity_values = self._get_snmp_identity_values(device_context, uptime_ms)
                    response = self._build_snmp_get_response(request_id, identity_values)
                    response_pkt = self._build_udp_packet(device_context, scanner, response)
                    self._schedule_event(current_time + 15, ("packet", response_pkt))
                    current_time += 50
                    logger.info(f"Scheduled orphan SNMP discovery for {device.ip_address}")

                # Modbus discovery for orphan device
                # Use device_supports_protocol for consistent gating
                if device_supports_protocol(device, "modbus"):
                    fingerprint = device.vendor_fingerprint or {}
                    modbus_identity = fingerprint.get("modbus_identity", {})
                    temp_seq = random.randint(1000, 100000)
                    temp_ack = random.randint(1000, 100000)

                    # TCP SYN
                    syn = self._build_tcp_packet(scanner, device, b"", temp_seq, 0, "S")
                    self._schedule_event(current_time, ("packet", syn))
                    current_time += 10

                    # TCP SYN-ACK
                    syn_ack = self._build_tcp_packet(device, scanner, b"", temp_ack, temp_seq + 1, "SA")
                    self._schedule_event(current_time, ("packet", syn_ack))
                    current_time += 10

                    # TCP ACK
                    ack = self._build_tcp_packet(scanner, device, b"", temp_seq + 1, temp_ack + 1, "A")
                    self._schedule_event(current_time, ("packet", ack))
                    current_time += 10

                    # FC 43 Request
                    transaction_id = random.randint(1, 65535)
                    unit_id = 1
                    fc43_request = struct.pack(
                        ">HHHBB BB",
                        transaction_id, 0, 5, unit_id, 0x2B, 0x0E, 0x01,
                    )
                    request_pkt = self._build_tcp_packet(
                        scanner, device, fc43_request, temp_seq + 1, temp_ack + 1
                    )
                    self._schedule_event(current_time, ("packet", request_pkt))
                    current_time += 20

                    # FC 43 Response
                    device_context = DeviceContext(
                        device_id=device.device_id,
                        mac_address=device.mac_address,
                        ip_address=device.ip_address,
                        port=502,
                        vendor_fingerprint=device.vendor_fingerprint,
                        device_name=device.device_name,
                    )
                    fc43_response = self._build_modbus_device_id_response(transaction_id, unit_id, device_context)
                    response_pkt = self._build_tcp_packet(
                        device_context, scanner, fc43_response, temp_ack + 1, temp_seq + 1 + len(fc43_request)
                    )
                    self._schedule_event(current_time, ("packet", response_pkt))
                    current_time += 50
                    logger.info(f"Scheduled orphan Modbus FC43 discovery for {device.ip_address}")

                # BACnet discovery for orphan device
                # Use device_supports_protocol for consistent gating
                if device_supports_protocol(device, "bacnet"):
                    fingerprint = device.vendor_fingerprint or {}
                    bacnet_identity = fingerprint.get("bacnet_identity", {})
                    # Who-Is request (broadcast)
                    who_is = self._build_bacnet_who_is()
                    who_is_pkt = self._build_udp_packet(scanner, device, who_is, src_port=47808, dst_port=47808)
                    self._schedule_event(current_time, ("packet", who_is_pkt))

                    # I-Am response
                    i_am = self._build_bacnet_i_am_response(device)
                    i_am_pkt = self._build_udp_packet(device, scanner, i_am, src_port=47808, dst_port=47808)
                    self._schedule_event(current_time + 20, ("packet", i_am_pkt))
                    current_time += 50
                    logger.info(f"Scheduled orphan BACnet discovery for {device.ip_address}")

                # ==============================================================
                # FALLBACK: Gratuitous ARP for ALL orphan devices
                # This ensures CV sees the IP-to-MAC mapping even for devices
                # without any protocol identity types
                # ==============================================================
                arp_pkt = self._build_gratuitous_arp(device)
                self._schedule_event(current_time, ("packet", arp_pkt))
                current_time += 20
                logger.info(f"Scheduled gratuitous ARP for orphan device {device.ip_address} ({device.mac_address})")

        return current_time

    def _generate_startup(self, flow_state: FlowState, time_ms: float) -> None:
        """Generate startup sequence for a flow (TCP handshake or UDP init)."""
        flow = flow_state.flow
        src = flow.source
        dst = flow.destination

        # SNMP uses UDP - no TCP handshake needed
        if flow.protocol == "snmp":
            flow_state.is_started = True
            logger.debug(f"SNMP flow {flow.flow_id} initialized (UDP, no handshake)")
            return

        # BACnet uses UDP - no TCP handshake needed
        if flow.protocol == "bacnet":
            flow_state.is_started = True
            logger.debug(f"BACnet flow {flow.flow_id} initialized (UDP, no handshake)")
            return

        # TCP handshake for TCP-based protocols
        # SYN from client
        syn = self._build_tcp_packet(src, dst, b"", flow_state.seq_number, 0, "S")
        self._schedule_event(time_ms, ("packet", syn))

        # SYN-ACK from server
        syn_ack = self._build_tcp_packet(
            dst, src, b"", flow_state.ack_number, flow_state.seq_number + 1, "SA"
        )
        self._schedule_event(time_ms + 5, ("packet", syn_ack))

        # ACK from client
        ack = self._build_tcp_packet(
            src, dst, b"", flow_state.seq_number + 1, flow_state.ack_number + 1, "A"
        )
        self._schedule_event(time_ms + 10, ("packet", ack))

        flow_state.seq_number += 1
        flow_state.ack_number += 1

        # IEC 104 requires STARTDT handshake after TCP connection
        if flow.protocol == "iec104":
            # STARTDT_ACT from controlling station (master)
            startdt_act = self._build_iec104_apci_u_format(IEC104_STARTDT_ACT)
            startdt_act_pkt = self._build_tcp_packet(
                src, dst, startdt_act, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(time_ms + 15, ("packet", startdt_act_pkt))

            # STARTDT_CON from controlled station (slave)
            startdt_con = self._build_iec104_apci_u_format(IEC104_STARTDT_CON)
            startdt_con_pkt = self._build_tcp_packet(
                dst, src, startdt_con,
                flow_state.ack_number, flow_state.seq_number + len(startdt_act)
            )
            self._schedule_event(time_ms + 25, ("packet", startdt_con_pkt))

            flow_state.seq_number += len(startdt_act)
            flow_state.ack_number += len(startdt_con)

            # Initialize IEC 104 sequence numbers in custom_data
            flow_state.transaction_id = 0  # Use as send sequence number

            logger.info(f"IEC 104 flow {flow.flow_id} initialized (TCP + STARTDT)")

        # OPC UA requires Hello/Ack + OpenSecureChannel + CreateSession + ActivateSession
        elif flow.protocol == "opc_ua":
            endpoint_url = f"opc.tcp://{dst.ip_address}:{dst.port or OPCUA_PORT}"
            current_time = time_ms + 15

            # 1. Hello from client
            hello_msg = self._build_opcua_hello(endpoint_url)
            hello_pkt = self._build_tcp_packet(
                src, dst, hello_msg, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(current_time, ("packet", hello_pkt))
            flow_state.seq_number += len(hello_msg)
            current_time += 10

            # 2. Ack from server
            ack_msg = self._build_opcua_ack()
            ack_pkt = self._build_tcp_packet(
                dst, src, ack_msg, flow_state.ack_number, flow_state.seq_number
            )
            self._schedule_event(current_time, ("packet", ack_pkt))
            flow_state.ack_number += len(ack_msg)
            current_time += 10

            # 3. OpenSecureChannel request from client
            osc_request = self._build_opcua_open_secure_channel_request(0, 1)
            osc_request_pkt = self._build_tcp_packet(
                src, dst, osc_request, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(current_time, ("packet", osc_request_pkt))
            flow_state.seq_number += len(osc_request)
            current_time += 15

            # 4. OpenSecureChannel response from server
            secure_channel_id = random.randint(1, 100000)
            token_id = random.randint(1, 100000)
            osc_response = self._build_opcua_open_secure_channel_response(
                secure_channel_id, token_id, 1
            )
            osc_response_pkt = self._build_tcp_packet(
                dst, src, osc_response, flow_state.ack_number, flow_state.seq_number
            )
            self._schedule_event(current_time, ("packet", osc_response_pkt))
            flow_state.ack_number += len(osc_response)
            current_time += 10

            # 5. CreateSession request from client
            create_session_request = self._build_opcua_create_session_request(
                secure_channel_id, token_id, 2, 2, endpoint_url
            )
            create_session_pkt = self._build_tcp_packet(
                src, dst, create_session_request, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(current_time, ("packet", create_session_pkt))
            flow_state.seq_number += len(create_session_request)
            current_time += 15

            # 6. CreateSession response from server (with identity from fingerprint)
            session_id = random.randint(1, 65535)
            auth_token = random.randint(1, 65535)
            create_session_response = self._build_opcua_create_session_response(
                secure_channel_id, token_id, 2, 2, session_id, auth_token,
                server_device=dst, endpoint_url=endpoint_url
            )
            create_session_response_pkt = self._build_tcp_packet(
                dst, src, create_session_response, flow_state.ack_number, flow_state.seq_number
            )
            self._schedule_event(current_time, ("packet", create_session_response_pkt))
            flow_state.ack_number += len(create_session_response)
            current_time += 10

            # 7. ActivateSession request from client
            activate_request = self._build_opcua_activate_session_request(
                secure_channel_id, token_id, 3, 3
            )
            activate_request_pkt = self._build_tcp_packet(
                src, dst, activate_request, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(current_time, ("packet", activate_request_pkt))
            flow_state.seq_number += len(activate_request)
            current_time += 10

            # 8. ActivateSession response from server
            activate_response = self._build_opcua_activate_session_response(
                secure_channel_id, token_id, 3, 3
            )
            activate_response_pkt = self._build_tcp_packet(
                dst, src, activate_response, flow_state.ack_number, flow_state.seq_number
            )
            self._schedule_event(current_time, ("packet", activate_response_pkt))
            flow_state.ack_number += len(activate_response)

            # Store OPC UA session state
            flow_state.custom_data = {
                "secure_channel_id": secure_channel_id,
                "token_id": token_id,
                "session_id": session_id,
                "auth_token": auth_token,
                "sequence_number": 4,
                "request_id": 4,
                "subscription_id": None,
            }

            logger.info(f"OPC UA flow {flow.flow_id} initialized (TCP + Hello/Ack + Session)")

        flow_state.is_started = True

    def _generate_poll_cycle(self, flow_state: FlowState, time_ms: float) -> None:
        """Generate a request/response cycle."""
        flow = flow_state.flow
        src = flow.source
        dst = flow.destination

        # Debug: Log non-standard protocols
        if flow.protocol not in ("modbus_tcp", "ethernet_ip", "profinet", "s7comm", "s7comm_plus", "snmp", "bacnet"):
            logger.info(f"Processing {flow.protocol} flow {flow.flow_id}: {src.ip_address} -> {dst.ip_address}:{dst.port}")

        flow_state.transaction_id = (flow_state.transaction_id + 1) & 0xFFFF  # Wrap at 65535

        if flow.protocol == "modbus_tcp":
            # Modbus request
            config = flow.config
            unit_id = dst.unit_id or 1

            # Check if we should send FC 43 (Read Device Identification) first
            if config.get("send_device_id_request") and dst.vendor_fingerprint.get("modbus_identity"):
                # Send FC 43 request/response for device identification
                config["send_device_id_request"] = False  # Only send once

                # FC 43 Request (MEI type 0x0E, device ID code 0x01)
                fc43_request = struct.pack(
                    ">HHHBBBB",
                    flow_state.transaction_id,  # Transaction ID
                    0,  # Protocol ID
                    5,  # Length
                    unit_id,
                    0x2B,  # Function code 43
                    0x0E,  # MEI type
                    0x01,  # Read Device ID code (basic)
                )
                fc43_request_pkt = self._build_tcp_packet(
                    src, dst, fc43_request, flow_state.seq_number, flow_state.ack_number
                )
                self._schedule_event(time_ms, ("packet", fc43_request_pkt))

                # FC 43 Response with device identification - includes CVE overrides
                fc43_response = self._build_modbus_device_id_response(
                    flow_state.transaction_id, unit_id, dst
                )
                fc43_response_pkt = self._build_tcp_packet(
                    dst, src, fc43_response,
                    flow_state.ack_number, flow_state.seq_number + len(fc43_request)
                )
                self._schedule_event(time_ms + 25, ("packet", fc43_response_pkt))

                flow_state.seq_number += len(fc43_request)
                flow_state.ack_number += len(fc43_response)
                flow_state.transaction_id = (flow_state.transaction_id + 1) & 0xFFFF  # Wrap at 65535
                time_ms += 100  # Add delay before normal poll

                logger.info(f"Sent Modbus FC 43 device identification for {dst.ip_address}")

            function_code = config.get("function_code", 3)
            start_addr = config.get("start_address", 0)
            quantity = config.get("quantity", 10)

            request_payload = self._build_modbus_request(
                flow_state.transaction_id, unit_id, function_code, start_addr, quantity
            )
            request_pkt = self._build_tcp_packet(
                src, dst, request_payload, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(time_ms, ("packet", request_pkt))

            # Response with random values
            response_values = [random.randint(0, 65535) for _ in range(quantity)]
            response_payload = self._build_modbus_response(
                flow_state.transaction_id, unit_id, function_code, response_values
            )

            # Response timing with jitter
            response_delay = random.uniform(5, 50)
            response_pkt = self._build_tcp_packet(
                dst, src, response_payload,
                flow_state.ack_number, flow_state.seq_number + len(request_payload)
            )
            self._schedule_event(time_ms + response_delay, ("packet", response_pkt))

            # Update sequence numbers
            flow_state.seq_number += len(request_payload)
            flow_state.ack_number += len(response_payload)

        elif flow.protocol == "snmp":
            # SNMP GetRequest/GetResponse for transportation devices
            # Uses UDP, no TCP sequence tracking needed
            config = flow.config

            # SNMP manager context
            manager = DeviceContext(
                device_id=src.device_id,
                mac_address=src.mac_address,
                ip_address=src.ip_address,
                port=random.randint(40000, 50000),
            )

            # SNMP agent (target device)
            agent = DeviceContext(
                device_id=dst.device_id,
                mac_address=dst.mac_address,
                ip_address=dst.ip_address,
                port=SNMP_AGENT_PORT,
                vendor_fingerprint=dst.vendor_fingerprint,
                vulnerability_override=dst.vulnerability_override,
                device_name=dst.device_name,
            )

            # Decide which OIDs to poll based on device type
            # Use effective identity to get CVE-overridden values
            snmp_identity = agent.get_effective_identity("snmp_identity")
            ntcip_device = snmp_identity.get("ntcip_device_type", "")

            request_id = flow_state.transaction_id

            if ntcip_device == "asc":
                # Traffic Signal Controller - poll phase status and detector data
                poll_oids = config.get("poll_oids", [
                    "1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1",  # Phase status (simplified)
                    "1.3.6.1.4.1.1206.4.2.1.2.3.1.5.1",  # Detector volume
                ])
                response_values = {
                    poll_oids[0] if poll_oids else SNMP_OIDS["sysUpTime"]: (
                        "integer", random.randint(1, 16)  # Random phase
                    ),
                }
                if len(poll_oids) > 1:
                    response_values[poll_oids[1]] = ("integer", random.randint(0, 100))

            elif ntcip_device == "dms":
                # Dynamic Message Sign - poll message status
                poll_oids = config.get("poll_oids", [
                    "1.3.6.1.4.1.1206.4.2.3.5.8.1.3.3.1",  # Current message
                ])
                response_values = {
                    poll_oids[0]: ("string", "ROAD WORK AHEAD"),
                }

            elif ntcip_device == "ess":
                # Environmental Sensor Station - poll weather data
                poll_oids = config.get("poll_oids", [
                    "1.3.6.1.4.1.1206.4.2.6.1.3.1.10.1",  # Air temperature
                    "1.3.6.1.4.1.1206.4.2.6.2.2.1.6.1",   # Wind speed
                ])
                response_values = {
                    poll_oids[0]: ("integer", random.randint(-20, 45)),  # Temp in C
                }
                if len(poll_oids) > 1:
                    response_values[poll_oids[1]] = ("integer", random.randint(0, 50))

            else:
                # Generic SNMP - poll system OIDs
                # Uses get_effective_identity() for CVE vulnerability overrides
                poll_oids = [SNMP_OIDS["sysUpTime"]]
                uptime_ms = int((time.time() * 1000) - self.start_time)
                response_values = self._get_snmp_identity_values(agent, uptime_ms)

            # Build and send GetRequest
            request = self._build_snmp_get_request(request_id, poll_oids)
            request_pkt = self._build_udp_packet(manager, agent, request)
            self._schedule_event(time_ms, ("packet", request_pkt))

            # Build and send GetResponse
            response = self._build_snmp_get_response(request_id, response_values)
            response_delay = random.uniform(5, 30)
            response_pkt = self._build_udp_packet(agent, manager, response)
            self._schedule_event(time_ms + response_delay, ("packet", response_pkt))

        elif flow.protocol == "bacnet":
            # BACnet ReadProperty request/response for BMS devices
            # Uses UDP, no TCP sequence tracking needed
            config = flow.config
            invoke_id = flow_state.transaction_id & 0xFF

            # BACnet client (manager/workstation)
            client = DeviceContext(
                device_id=src.device_id,
                mac_address=src.mac_address,
                ip_address=src.ip_address,
                port=BACNET_PORT,
            )

            # BACnet device (target)
            device = DeviceContext(
                device_id=dst.device_id,
                mac_address=dst.mac_address,
                ip_address=dst.ip_address,
                port=BACNET_PORT,
                vendor_fingerprint=dst.vendor_fingerprint,
                vulnerability_override=dst.vulnerability_override,
                device_name=dst.device_name,
            )

            bacnet_identity = device.get_effective_identity("bacnet_identity")
            device_instance = bacnet_identity.get("device_instance", 1)

            # Determine what to poll based on config or device type
            poll_objects = config.get("poll_objects", [])
            if not poll_objects:
                # Default: poll Device object properties for identity
                # VENDOR_IDENTIFIER (120) is the numeric vendor ID - CV may use this
                # VENDOR_NAME (121) is the vendor name string
                poll_objects = [
                    (BACNET_OBJ_DEVICE, device_instance, BACNET_PROP_VENDOR_ID),  # 97 for Trane
                    (BACNET_OBJ_DEVICE, device_instance, BACNET_PROP_VENDOR_NAME),  # "Trane"
                    (BACNET_OBJ_DEVICE, device_instance, BACNET_PROP_MODEL_NAME),
                    (BACNET_OBJ_DEVICE, device_instance, BACNET_PROP_FIRMWARE_REVISION),
                    (BACNET_OBJ_DEVICE, device_instance, BACNET_PROP_SYSTEM_STATUS),
                ]

            # Identity values for responses (uses vulnerability override if present)
            identity_values = self._get_bacnet_identity_values(device)

            for obj_type, obj_instance, prop_id in poll_objects[:4]:  # Limit to 4 per cycle for identity
                # ReadProperty Request
                request = self._build_bacnet_read_property_request(
                    invoke_id, obj_type, obj_instance, prop_id
                )
                request_pkt = self._build_udp_packet(client, device, request)
                self._schedule_event(time_ms, ("packet", request_pkt))

                # ReadProperty Response
                # Get value from identity or generate realistic value
                if prop_id in identity_values:
                    value_type, value = identity_values[prop_id]
                elif prop_id == BACNET_PROP_PRESENT_VALUE:
                    # Generate realistic value based on object type
                    if obj_type == BACNET_OBJ_ANALOG_INPUT:
                        value_type, value = "real", random.uniform(60.0, 80.0)  # Temperature
                    elif obj_type == BACNET_OBJ_ANALOG_OUTPUT:
                        value_type, value = "real", random.uniform(0.0, 100.0)  # Valve %
                    elif obj_type in (BACNET_OBJ_BINARY_INPUT, BACNET_OBJ_BINARY_OUTPUT):
                        value_type, value = "enumerated", random.choice([0, 1])
                    else:
                        value_type, value = "unsigned", random.randint(0, 100)
                else:
                    value_type, value = "unsigned", 0

                response = self._build_bacnet_read_property_response(
                    invoke_id, obj_type, obj_instance, prop_id, value, value_type
                )
                response_delay = random.uniform(10, 50)
                response_pkt = self._build_udp_packet(device, client, response)
                self._schedule_event(time_ms + response_delay, ("packet", response_pkt))

                invoke_id = (invoke_id + 1) & 0xFF
                time_ms += response_delay + random.uniform(20, 80)

        elif flow.protocol == "dnp3":
            # DNP3 Read request/response for SCADA/RTU communication
            # Uses TCP on port 20000
            config = flow.config

            # DNP3 addresses - check fingerprint identity first, fall back to config
            # Master address typically comes from config (the SCADA master)
            master_address = config.get("master_address", 1)
            # Outstation address may come from fingerprint (the device being polled)
            dnp3_identity = dst.get_effective_identity("dnp3_identity")
            outstation_address = dnp3_identity.get("outstation_address") or config.get("outstation_address", 10)
            sequence = flow_state.transaction_id & 0x0F  # DNP3 sequence is 0-15

            # Determine what objects to poll
            poll_objects = config.get("poll_objects", [])
            if not poll_objects:
                # Default: poll common objects for SCADA
                poll_objects = [
                    (DNP3_GROUP_BINARY_INPUT, 1),    # Binary Inputs (digital status)
                    (DNP3_GROUP_ANALOG_INPUT, 32),   # Analog Inputs (32-bit with flag)
                    (DNP3_GROUP_COUNTER, 20),        # Counters (32-bit)
                ]

            # Build DNP3 Read Request
            dnp3_request = self._build_dnp3_read_request(
                outstation_address, master_address, poll_objects, sequence
            )
            request_pkt = self._build_tcp_packet(
                src, dst, dnp3_request, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(time_ms, ("packet", request_pkt))

            # Build DNP3 Read Response with simulated data
            # Generate realistic values for each object type
            response_objects = []
            for group, variation in poll_objects:
                if group == DNP3_GROUP_BINARY_INPUT:
                    # Binary inputs: 8-16 digital points (0 or 1)
                    point_count = config.get("binary_input_count", 8)
                    values = [random.choice([0, 1]) for _ in range(point_count)]
                elif group == DNP3_GROUP_ANALOG_INPUT:
                    # Analog inputs: process values (tank levels, temps, pressures)
                    point_count = config.get("analog_input_count", 4)
                    values = [random.uniform(-1000.0, 10000.0) for _ in range(point_count)]
                elif group == DNP3_GROUP_COUNTER:
                    # Counters: accumulator values (flow totals, events)
                    point_count = config.get("counter_count", 4)
                    values = [random.randint(0, 1000000) for _ in range(point_count)]
                elif group == DNP3_GROUP_BINARY_OUTPUT:
                    # Binary outputs: control point status
                    point_count = config.get("binary_output_count", 4)
                    values = [random.choice([0, 1]) for _ in range(point_count)]
                elif group == DNP3_GROUP_ANALOG_OUTPUT:
                    # Analog outputs: setpoints
                    point_count = config.get("analog_output_count", 2)
                    values = [random.uniform(0.0, 100.0) for _ in range(point_count)]
                elif group == DNP3_GROUP_CLASS:
                    # Class data: return empty (no events)
                    values = []
                else:
                    values = [0]

                response_objects.append((group, variation, values))

            dnp3_response = self._build_dnp3_read_response(
                master_address, outstation_address, response_objects, sequence
            )

            # Response timing based on fingerprint or default
            response_delay = random.uniform(10, 80)
            response_pkt = self._build_tcp_packet(
                dst, src, dnp3_response,
                flow_state.ack_number, flow_state.seq_number + len(dnp3_request)
            )
            self._schedule_event(time_ms + response_delay, ("packet", response_pkt))

            # Update sequence numbers for TCP
            flow_state.seq_number += len(dnp3_request)
            flow_state.ack_number += len(dnp3_response)

            logger.debug(
                f"DNP3 poll: master={master_address} -> outstation={outstation_address}, "
                f"objects={[(g, v) for g, v, _ in response_objects]}"
            )

        elif flow.protocol == "iec104":
            # IEC 60870-5-104 for power grid SCADA
            # Uses TCP on port 2404
            config = flow.config

            # IEC 104 addresses - check fingerprint identity first, fall back to config
            iec104_identity = dst.get_effective_identity("iec104_identity")
            common_address = iec104_identity.get("common_address") or config.get("common_address", 1)

            # IEC 104 sequence numbers (send/recv)
            send_seq = flow_state.transaction_id & 0x7FFF
            recv_seq = (flow_state.transaction_id >> 1) & 0x7FFF

            # Determine poll type
            poll_type = config.get("poll_type", "gi")  # gi = general interrogation

            if poll_type == "gi":
                # General Interrogation command
                gi_command = self._build_iec104_interrogation_command(
                    send_seq, recv_seq, common_address
                )
                request_pkt = self._build_tcp_packet(
                    src, dst, gi_command, flow_state.seq_number, flow_state.ack_number
                )
                self._schedule_event(time_ms, ("packet", request_pkt))

                # Interrogation confirmation
                gi_confirm = self._build_iec104_interrogation_response(
                    recv_seq, send_seq + 1, common_address
                )
                response_delay = random.uniform(10, 50)
                confirm_pkt = self._build_tcp_packet(
                    dst, src, gi_confirm,
                    flow_state.ack_number, flow_state.seq_number + len(gi_command)
                )
                self._schedule_event(time_ms + response_delay, ("packet", confirm_pkt))

                # Generate spontaneous data responses (single-point and measured values)
                current_time = time_ms + response_delay + 20

                # Single-point (breaker status, switch status)
                sp_count = config.get("single_point_count", 8)
                sp_values = [(100 + i, random.choice([True, False])) for i in range(sp_count)]
                sp_response = self._build_iec104_single_point_info(
                    recv_seq + 1, send_seq + 1, common_address, sp_values, IEC104_COT_INTERROGATION
                )
                sp_pkt = self._build_tcp_packet(
                    dst, src, sp_response,
                    flow_state.ack_number + len(gi_confirm),
                    flow_state.seq_number + len(gi_command)
                )
                self._schedule_event(current_time, ("packet", sp_pkt))
                current_time += random.uniform(10, 30)

                # Measured values (voltage, current, power, frequency)
                mv_count = config.get("measured_value_count", 4)
                mv_values = []
                for i in range(mv_count):
                    # Simulate typical substation measurements
                    if i == 0:
                        value = random.uniform(118.0, 122.0)  # Voltage kV
                    elif i == 1:
                        value = random.uniform(200.0, 500.0)  # Current A
                    elif i == 2:
                        value = random.uniform(10.0, 50.0)    # Power MW
                    else:
                        value = random.uniform(59.95, 60.05)  # Frequency Hz
                    mv_values.append((200 + i, value))

                mv_response = self._build_iec104_measured_value_float(
                    recv_seq + 2, send_seq + 1, common_address, mv_values, IEC104_COT_INTERROGATION
                )
                mv_pkt = self._build_tcp_packet(
                    dst, src, mv_response,
                    flow_state.ack_number + len(gi_confirm) + len(sp_response),
                    flow_state.seq_number + len(gi_command)
                )
                self._schedule_event(current_time, ("packet", mv_pkt))
                current_time += random.uniform(10, 30)

                # Interrogation end
                gi_end = self._build_iec104_interrogation_end(
                    recv_seq + 3, send_seq + 1, common_address
                )
                end_pkt = self._build_tcp_packet(
                    dst, src, gi_end,
                    flow_state.ack_number + len(gi_confirm) + len(sp_response) + len(mv_response),
                    flow_state.seq_number + len(gi_command)
                )
                self._schedule_event(current_time, ("packet", end_pkt))

                # Update sequence numbers
                flow_state.seq_number += len(gi_command)
                flow_state.ack_number += len(gi_confirm) + len(sp_response) + len(mv_response) + len(gi_end)
                flow_state.transaction_id += 4

            else:
                # Spontaneous reporting (protection relay events)
                sp_count = config.get("single_point_count", 4)
                sp_values = [(100 + i, random.choice([True, False])) for i in range(sp_count)]
                sp_response = self._build_iec104_single_point_info(
                    send_seq, recv_seq, common_address, sp_values, IEC104_COT_SPONTANEOUS
                )
                sp_pkt = self._build_tcp_packet(
                    dst, src, sp_response, flow_state.ack_number, flow_state.seq_number
                )
                self._schedule_event(time_ms, ("packet", sp_pkt))

                flow_state.ack_number += len(sp_response)
                flow_state.transaction_id += 1

            logger.debug(
                f"IEC 104 poll: common_address={common_address}, type={poll_type}"
            )

        elif flow.protocol == "opc_ua":
            # OPC UA subscription-based polling for historian/HMI connections
            config = flow.config

            # Get OPC UA session state
            if not flow_state.custom_data:
                flow_state.custom_data = {
                    "secure_channel_id": random.randint(1, 100000),
                    "token_id": random.randint(1, 100000),
                    "sequence_number": 1,
                    "request_id": 1,
                    "subscription_id": None,
                }

            secure_channel_id = flow_state.custom_data["secure_channel_id"]
            token_id = flow_state.custom_data["token_id"]
            seq_num = flow_state.custom_data["sequence_number"]
            req_id = flow_state.custom_data["request_id"]
            subscription_id = flow_state.custom_data.get("subscription_id")

            current_time = time_ms

            # First poll: Create subscription if needed
            if subscription_id is None:
                publishing_interval = config.get("publishing_interval", 1000.0)

                # CreateSubscription request
                create_sub_request = self._build_opcua_create_subscription_request(
                    secure_channel_id, token_id, seq_num, req_id, publishing_interval
                )
                create_sub_pkt = self._build_tcp_packet(
                    src, dst, create_sub_request, flow_state.seq_number, flow_state.ack_number
                )
                self._schedule_event(current_time, ("packet", create_sub_pkt))
                flow_state.seq_number += len(create_sub_request)
                current_time += random.uniform(10, 30)

                # CreateSubscription response
                subscription_id = random.randint(1, 100000)
                create_sub_response = self._build_opcua_create_subscription_response(
                    secure_channel_id, token_id, seq_num, req_id, subscription_id, publishing_interval
                )
                create_sub_response_pkt = self._build_tcp_packet(
                    dst, src, create_sub_response, flow_state.ack_number, flow_state.seq_number
                )
                self._schedule_event(current_time, ("packet", create_sub_response_pkt))
                flow_state.ack_number += len(create_sub_response)
                current_time += random.uniform(5, 15)

                flow_state.custom_data["subscription_id"] = subscription_id
                seq_num += 1
                req_id += 1

            # Publish request from client
            publish_request = self._build_opcua_publish_request(
                secure_channel_id, token_id, seq_num, req_id
            )
            publish_request_pkt = self._build_tcp_packet(
                src, dst, publish_request, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(current_time, ("packet", publish_request_pkt))
            flow_state.seq_number += len(publish_request)
            current_time += random.uniform(10, 50)

            # Publish response with data change notifications
            # Generate simulated process data (typical historian values)
            notification_data = []
            node_count = config.get("monitored_item_count", 4)
            for i in range(node_count):
                node_id = 1000 + i
                # Generate realistic OT values
                if i == 0:
                    value = random.uniform(60.0, 100.0)   # Temperature
                elif i == 1:
                    value = random.uniform(0.0, 100.0)    # Pressure
                elif i == 2:
                    value = random.uniform(0.0, 1000.0)   # Flow rate
                else:
                    value = random.uniform(0.0, 100.0)    # Level
                notification_data.append((node_id, value))

            publish_response = self._build_opcua_publish_response(
                secure_channel_id, token_id, seq_num, req_id,
                subscription_id, notification_data
            )
            publish_response_pkt = self._build_tcp_packet(
                dst, src, publish_response, flow_state.ack_number, flow_state.seq_number
            )
            self._schedule_event(current_time, ("packet", publish_response_pkt))
            flow_state.ack_number += len(publish_response)

            # Update sequence numbers
            flow_state.custom_data["sequence_number"] = seq_num + 1
            flow_state.custom_data["request_id"] = req_id + 1

            logger.debug(
                f"OPC UA poll: subscription_id={subscription_id}, "
                f"notifications={len(notification_data)}"
            )

        elif flow.protocol in ("s7comm", "s7comm_plus"):
            # S7comm polling for Siemens PLCs
            # Periodic read requests with SZL identification
            config = flow.config

            # Initialize S7 session state if needed
            if not flow_state.custom_data:
                flow_state.custom_data = {
                    "established": True,  # Discovery already established connection
                    "pdu_reference": 0x0001,
                }

            pdu_ref = flow_state.custom_data["pdu_reference"]

            # Generate S7 read request (simple variable read)
            # This simulates normal PLC communication
            s7_header = struct.pack(
                ">BBHHHH",
                0x32,           # Protocol ID
                S7_PDU_JOB,     # PDU type (Job)
                0x0000,         # Reserved
                pdu_ref,        # PDU reference
                14,             # Parameter length
                0,              # Data length
            )
            # Read Var parameters
            params = struct.pack(
                ">BBBBBBBIHB",
                S7_FUNC_READ_VAR,  # Function (Read Var)
                1,                  # Item count
                0x12,              # Variable specification
                10,                # Address length
                0x10,              # Syntax ID (S7ANY)
                0x02,              # Transport size (BYTE)
                10,                # Length to read
                config.get("db_number", 1),  # DB number
                0x84,              # Area (Data blocks)
                0,                 # Start address (high byte)
            )
            read_req = self._build_s7_tpkt_cotp_header(s7_header + params)
            request_pkt = self._build_tcp_packet(
                src, dst, read_req, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(time_ms, ("packet", request_pkt))

            # S7 Read Response
            s7_resp_header = struct.pack(
                ">BBHHHH",
                0x32,               # Protocol ID
                S7_PDU_ACK_DATA,    # PDU type (Ack-Data)
                0x0000,             # Reserved
                pdu_ref,            # PDU reference
                2,                  # Parameter length
                14,                 # Data length
            )
            resp_params = struct.pack(">BB", S7_FUNC_READ_VAR, 1)  # Function, item count
            # Response data (10 bytes of random process data)
            resp_data = struct.pack(">BBH", 0xFF, 0x04, 10)  # Return code, transport size, length
            resp_data += bytes(random.randint(0, 255) for _ in range(10))

            read_resp = self._build_s7_tpkt_cotp_header(s7_resp_header + resp_params + resp_data)
            response_delay = random.uniform(10, 50)
            response_pkt = self._build_tcp_packet(
                dst, src, read_resp,
                flow_state.ack_number, flow_state.seq_number + len(read_req)
            )
            self._schedule_event(time_ms + response_delay, ("packet", response_pkt))

            # Update state
            flow_state.seq_number += len(read_req)
            flow_state.ack_number += len(read_resp)
            flow_state.custom_data["pdu_reference"] = (pdu_ref + 1) & 0xFFFF

            logger.debug(f"S7comm poll: db={config.get('db_number', 1)}, pdu_ref={pdu_ref}")

        elif flow.protocol == "https" and flow.config.get("external"):
            # External HTTPS flow (e.g., EWON Talk2M heartbeat)
            # Generate TLS Client Hello to show external communication
            external_ip = flow.config.get("externalIp", "0.0.0.0")
            external_port = flow.config.get("externalPort", 443)
            logger.info(f"Generating HTTPS external traffic: {src.ip_address} -> {external_ip}:{external_port}")

            # Create external destination context
            external_dst = DeviceContext(
                device_id="external_cloud",
                mac_address="00:00:00:00:00:00",  # Will be replaced by gateway MAC
                ip_address=external_ip,
                port=external_port,
            )

            # TLS Client Hello (minimal version for visibility)
            tls_client_hello = self._build_tls_client_hello(src.ip_address)

            # Build TCP SYN to external IP
            syn_pkt = self._build_tcp_packet(
                src, external_dst, b"", flow_state.seq_number, 0, flags="S"
            )
            self._schedule_event(time_ms, ("packet", syn_pkt))

            # TCP SYN-ACK from external (simulated)
            syn_ack_pkt = self._build_tcp_packet(
                external_dst, src, b"", flow_state.ack_number, flow_state.seq_number + 1, flags="SA"
            )
            self._schedule_event(time_ms + 50, ("packet", syn_ack_pkt))

            # TCP ACK
            ack_pkt = self._build_tcp_packet(
                src, external_dst, b"", flow_state.seq_number + 1, flow_state.ack_number + 1, flags="A"
            )
            self._schedule_event(time_ms + 55, ("packet", ack_pkt))

            # TLS Client Hello
            client_hello_pkt = self._build_tcp_packet(
                src, external_dst, tls_client_hello,
                flow_state.seq_number + 1, flow_state.ack_number + 1, flags="PA"
            )
            self._schedule_event(time_ms + 60, ("packet", client_hello_pkt))

            # TLS Server Hello (simulated response)
            tls_server_hello = self._build_tls_server_hello()
            server_hello_pkt = self._build_tcp_packet(
                external_dst, src, tls_server_hello,
                flow_state.ack_number + 1, flow_state.seq_number + 1 + len(tls_client_hello), flags="PA"
            )
            self._schedule_event(time_ms + 150, ("packet", server_hello_pkt))

            # Update sequence numbers
            flow_state.seq_number += 1 + len(tls_client_hello)
            flow_state.ack_number += 1 + len(tls_server_hello)

            logger.debug(
                f"HTTPS external flow: {src.ip_address} -> {external_ip}:{external_port}"
            )

        else:
            # Generic TCP traffic for other protocols (profinet, ethernet_ip, etc.)
            # Generate a simple request/response with random payload data
            request_payload = struct.pack(
                ">HHI",
                flow_state.transaction_id,  # Transaction ID
                random.randint(1, 100),     # Function/command code
                random.randint(0, 1000),    # Data value
            ) + bytes(random.randint(0, 255) for _ in range(random.randint(4, 20)))

            request_pkt = self._build_tcp_packet(
                src, dst, request_payload, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(time_ms, ("packet", request_pkt))

            # Generate response
            response_payload = struct.pack(
                ">HHI",
                flow_state.transaction_id,
                0,  # Success status
                random.randint(0, 65535),
            ) + bytes(random.randint(0, 255) for _ in range(random.randint(8, 32)))

            response_delay = random.uniform(5, 50)
            response_pkt = self._build_tcp_packet(
                dst, src, response_payload,
                flow_state.ack_number, flow_state.seq_number + len(request_payload)
            )
            self._schedule_event(time_ms + response_delay, ("packet", response_pkt))

            # Update sequence numbers
            flow_state.seq_number += len(request_payload)
            flow_state.ack_number += len(response_payload)

    def _generate_shutdown(self, flow_state: FlowState, time_ms: float) -> None:
        """Generate connection teardown (TCP FIN or UDP no-op)."""
        flow = flow_state.flow
        src = flow.source
        dst = flow.destination

        # SNMP uses UDP - no teardown needed
        if flow.protocol == "snmp":
            logger.debug(f"SNMP flow {flow.flow_id} shutdown (UDP, no teardown)")
            return

        # BACnet uses UDP - no teardown needed
        if flow.protocol == "bacnet":
            logger.debug(f"BACnet flow {flow.flow_id} shutdown (UDP, no teardown)")
            return

        # TCP connection teardown
        # FIN from client
        fin = self._build_tcp_packet(
            src, dst, b"", flow_state.seq_number, flow_state.ack_number, "FA"
        )
        self._schedule_event(time_ms, ("packet", fin))

        # FIN-ACK from server
        fin_ack = self._build_tcp_packet(
            dst, src, b"", flow_state.ack_number, flow_state.seq_number + 1, "FA"
        )
        self._schedule_event(time_ms + 5, ("packet", fin_ack))

        # ACK from client
        ack = self._build_tcp_packet(
            src, dst, b"", flow_state.seq_number + 1, flow_state.ack_number + 1, "A"
        )
        self._schedule_event(time_ms + 10, ("packet", ack))

    def stop(self) -> None:
        """Signal the orchestrator to stop (for graceful shutdown)."""
        self._running = False

    def run(self) -> int:
        """Run the traffic generation.

        Returns:
            Number of packets sent
        """
        logger.info(f"Starting live traffic generation on interface {self.interface}")
        if self.perpetual:
            logger.info(f"Mode: PERPETUAL (runs until stopped), Flows: {len(self.flows)}")
        else:
            logger.info(f"Duration: {self.duration_ms}ms, Flows: {len(self.flows)}")

        self.start_time = time.time() * 1000

        # Schedule discovery sequences first (device fingerprinting)
        discovery_end_time = self._generate_discovery_sequences(0)
        logger.info(f"Discovery sequences scheduled up to {discovery_end_time}ms")

        # Track last discovery time for periodic re-discovery in perpetual mode
        last_discovery_real_time = time.time()
        DISCOVERY_INTERVAL = 30.0  # Re-broadcast discovery every 30 seconds

        # Schedule startup for all flows (after discovery)
        startup_base_time = discovery_end_time + 50
        for i, flow_state in enumerate(self.flows):
            startup_offset = startup_base_time + (i * 100)  # Stagger startups
            self._generate_startup(flow_state, startup_offset)

            # Schedule first poll
            first_poll = startup_offset + 50 + self._apply_jitter(
                flow_state.poll_interval_ms, flow_state.flow.timing_model
            )
            self._schedule_event(first_poll, ("poll", flow_state.flow.flow_id))

            # Debug log for non-standard protocols
            if flow_state.flow.protocol in ("https", "opc_ua"):
                logger.info(f"Scheduled first poll for {flow_state.flow.flow_id} ({flow_state.flow.protocol}) at {first_poll}ms")

        # Main event loop
        while self.event_queue and self._running:
            event_time, _, event = heapq.heappop(self.event_queue)

            # Check if we've exceeded duration (only for timed mode)
            if not self.perpetual and event_time > self.duration_ms:
                break

            # Wait until event time
            current_time = (time.time() * 1000) - self.start_time
            if event_time > current_time:
                sleep_time = (event_time - current_time) / 1000
                time.sleep(sleep_time)

            # Handle event
            if event[0] == "packet":
                self._send_packet(event[1])
            elif event[0] == "poll":
                flow_id = event[1]
                # Debug: Log HTTPS flows unconditionally
                if "765" in flow_id or "766" in flow_id or "767" in flow_id:
                    logger.info(f"!!! HTTPS POLL: {flow_id} at {event_time:.0f}ms !!!")
                flow_found = False
                for flow_state in self.flows:
                    if flow_state.flow.flow_id == flow_id:
                        flow_found = True
                        self._generate_poll_cycle(flow_state, event_time)
                        # Schedule next poll
                        next_poll = event_time + self._apply_jitter(
                            flow_state.poll_interval_ms, flow_state.flow.timing_model
                        )
                        # In perpetual mode, always schedule next poll
                        # In timed mode, only if within duration
                        if self.perpetual or next_poll < self.duration_ms:
                            self._schedule_event(next_poll, ("poll", flow_id))
                        break

            # Periodic re-discovery for perpetual mode (ensures Cyber Vision catches fingerprints)
            if self.perpetual:
                current_real_time = time.time()
                if current_real_time - last_discovery_real_time >= DISCOVERY_INTERVAL:
                    logger.info("Re-broadcasting discovery sequences for device fingerprinting")
                    # Use current event time for scheduling
                    self._generate_discovery_sequences(event_time)
                    last_discovery_real_time = current_real_time

        # Generate shutdown sequences (only for timed mode or when stopped)
        if not self.perpetual or not self._running:
            current_time = (time.time() * 1000) - self.start_time
            shutdown_time = self.duration_ms if not self.perpetual else current_time
            for flow_state in self.flows:
                self._generate_shutdown(flow_state, shutdown_time)
                shutdown_time += 20

            # Process remaining shutdown events with timeout to avoid blocking
            # This prevents WebSocket ping/pong timeout during graceful shutdown
            shutdown_start = time.time()
            SHUTDOWN_TIMEOUT_SECONDS = 5.0  # Max time to spend on shutdown

            while self.event_queue:
                # Check timeout to avoid blocking too long (prevents WebSocket disconnect)
                if time.time() - shutdown_start > SHUTDOWN_TIMEOUT_SECONDS:
                    remaining = len(self.event_queue)
                    logger.warning(
                        f"Shutdown timeout reached, skipping {remaining} remaining events"
                    )
                    break

                event_time, _, event = heapq.heappop(self.event_queue)
                current_time = (time.time() * 1000) - self.start_time
                if event_time > current_time:
                    sleep_time = (event_time - current_time) / 1000
                    # Cap individual sleep time to prevent long blocks
                    sleep_time = min(sleep_time, 0.5)
                    time.sleep(sleep_time)

                if event[0] == "packet":
                    self._send_packet(event[1])

        logger.info(f"Generation complete: {self.packets_sent} packets sent")
        return self.packets_sent
