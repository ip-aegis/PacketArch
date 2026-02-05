"""BACnet/IP protocol extractor for deep packet analysis.

Extracts service types, object identifiers, property access patterns, and device info.
"""

import logging
import struct
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from scapy.layers.inet import IP, UDP
from scapy.packet import Packet, Raw

from app.ai_services.extractors.base import (
    ExtractedPacketInfo,
    ProtocolExtractor,
)

logger = logging.getLogger(__name__)

# BACnet Virtual Link Control (BVLC) Types
BVLC_TYPE = {
    0x00: "bvlc_result",
    0x01: "write_broadcast_distribution_table",
    0x02: "read_broadcast_distribution_table",
    0x03: "read_broadcast_distribution_table_ack",
    0x04: "forwarded_npdu",
    0x05: "register_foreign_device",
    0x06: "read_foreign_device_table",
    0x07: "read_foreign_device_table_ack",
    0x08: "delete_foreign_device_table_entry",
    0x09: "distribute_broadcast_to_network",
    0x0A: "original_unicast_npdu",
    0x0B: "original_broadcast_npdu",
}

# BACnet APDU Types
APDU_TYPE = {
    0: "confirmed_request",
    1: "unconfirmed_request",
    2: "simple_ack",
    3: "complex_ack",
    4: "segment_ack",
    5: "error",
    6: "reject",
    7: "abort",
}

# BACnet Confirmed Service Choices
CONFIRMED_SERVICE = {
    0: "acknowledgeAlarm",
    1: "confirmedCOVNotification",
    2: "confirmedEventNotification",
    3: "getAlarmSummary",
    4: "getEnrollmentSummary",
    5: "subscribeCOV",
    6: "atomicReadFile",
    7: "atomicWriteFile",
    8: "addListElement",
    9: "removeListElement",
    10: "createObject",
    11: "deleteObject",
    12: "readProperty",
    13: "readPropertyConditional",
    14: "readPropertyMultiple",
    15: "writeProperty",
    16: "writePropertyMultiple",
    17: "deviceCommunicationControl",
    18: "confirmedPrivateTransfer",
    19: "confirmedTextMessage",
    20: "reinitializeDevice",
    21: "vtOpen",
    22: "vtClose",
    23: "vtData",
    24: "authenticate",
    25: "requestKey",
    26: "readRange",
    27: "lifeSafetyOperation",
    28: "subscribeCOVProperty",
    29: "getEventInformation",
}

# BACnet Unconfirmed Service Choices
UNCONFIRMED_SERVICE = {
    0: "i_Am",
    1: "i_Have",
    2: "unconfirmedCOVNotification",
    3: "unconfirmedEventNotification",
    4: "unconfirmedPrivateTransfer",
    5: "unconfirmedTextMessage",
    6: "timeSynchronization",
    7: "who_Has",
    8: "who_Is",
    9: "utcTimeSynchronization",
    10: "writeGroup",
}

# BACnet Object Types
OBJECT_TYPE = {
    0: "analog_input",
    1: "analog_output",
    2: "analog_value",
    3: "binary_input",
    4: "binary_output",
    5: "binary_value",
    6: "calendar",
    7: "command",
    8: "device",
    9: "event_enrollment",
    10: "file",
    11: "group",
    12: "loop",
    13: "multi_state_input",
    14: "multi_state_output",
    15: "notification_class",
    16: "program",
    17: "schedule",
    18: "averaging",
    19: "multi_state_value",
    20: "trend_log",
    21: "life_safety_point",
    22: "life_safety_zone",
    23: "accumulator",
    24: "pulse_converter",
    25: "event_log",
    26: "global_group",
    27: "trend_log_multiple",
    28: "load_control",
    29: "structured_view",
    30: "access_door",
    31: "timer",
    32: "access_credential",
    33: "access_point",
    34: "access_rights",
    35: "access_user",
    36: "access_zone",
    37: "credential_data_input",
    38: "network_security",
    39: "bitstring_value",
    40: "characterstring_value",
    41: "date_pattern_value",
    42: "date_value",
    43: "datetime_pattern_value",
    44: "datetime_value",
    45: "integer_value",
    46: "large_analog_value",
    47: "octetstring_value",
    48: "positive_integer_value",
    49: "time_pattern_value",
    50: "time_value",
    51: "notification_forwarder",
    52: "alert_enrollment",
    53: "channel",
    54: "lighting_output",
}

# Common BACnet Properties
PROPERTY_ID = {
    0: "acked_transitions",
    1: "ack_required",
    2: "action",
    3: "action_text",
    4: "active_text",
    5: "active_vt_sessions",
    6: "alarm_value",
    7: "alarm_values",
    8: "all",
    9: "all_writes_successful",
    10: "apdu_segment_timeout",
    11: "apdu_timeout",
    12: "application_software_version",
    13: "archive",
    14: "bias",
    15: "change_of_state_count",
    16: "change_of_state_time",
    17: "notification_class",
    18: "blank_1",
    19: "controlled_variable_reference",
    20: "controlled_variable_units",
    21: "controlled_variable_value",
    22: "cov_increment",
    23: "date_list",
    24: "daylight_savings_status",
    25: "deadband",
    26: "derivative_constant",
    27: "derivative_constant_units",
    28: "description",
    29: "description_of_halt",
    30: "device_address_binding",
    31: "device_type",
    32: "effective_period",
    33: "elapsed_active_time",
    34: "error_limit",
    35: "event_enable",
    36: "event_state",
    37: "event_type",
    38: "exception_schedule",
    39: "fault_values",
    40: "feedback_value",
    44: "firmware_revision",
    45: "high_limit",
    46: "inactive_text",
    47: "in_process",
    48: "instance_of",
    49: "integral_constant",
    50: "integral_constant_units",
    51: "issue_confirmed_notifications",
    52: "limit_enable",
    53: "list_of_group_members",
    54: "list_of_object_property_references",
    55: "list_of_session_keys",
    56: "local_date",
    57: "local_time",
    58: "location",
    59: "low_limit",
    60: "manipulated_variable_reference",
    61: "maximum_output",
    62: "max_apdu_length_accepted",
    63: "max_info_frames",
    64: "max_master",
    65: "max_pres_value",
    66: "minimum_off_time",
    67: "minimum_on_time",
    68: "minimum_output",
    69: "min_pres_value",
    70: "model_name",
    71: "modification_date",
    72: "notify_type",
    73: "number_of_apdu_retries",
    74: "number_of_states",
    75: "object_identifier",
    76: "object_list",
    77: "object_name",
    78: "object_property_reference",
    79: "object_type",
    80: "optional",
    81: "out_of_service",
    82: "output_units",
    83: "event_parameters",
    84: "polarity",
    85: "present_value",
    86: "priority",
    87: "priority_array",
    88: "priority_for_writing",
    89: "process_identifier",
    90: "program_change",
    91: "program_location",
    92: "program_state",
    93: "proportional_constant",
    94: "proportional_constant_units",
    95: "protocol_conformance_class",
    96: "protocol_object_types_supported",
    97: "protocol_services_supported",
    98: "protocol_version",
    99: "read_only",
    100: "reason_for_halt",
    101: "recipient",
    102: "recipient_list",
    103: "reliability",
    104: "relinquish_default",
    105: "required",
    106: "resolution",
    107: "segmentation_supported",
    108: "setpoint",
    109: "setpoint_reference",
    110: "state_text",
    111: "status_flags",
    112: "system_status",
    113: "time_delay",
    114: "time_of_active_time_reset",
    115: "time_of_state_count_reset",
    116: "time_synchronization_recipients",
    117: "units",
    118: "update_interval",
    119: "utc_offset",
    120: "vendor_identifier",
    121: "vendor_name",
    122: "vt_classes_supported",
    123: "weekly_schedule",
    124: "attempted_samples",
    125: "average_value",
    126: "buffer_size",
    127: "client_cov_increment",
    128: "cov_resubscription_interval",
    129: "current_notify_time",
    130: "event_time_stamps",
    131: "log_buffer",
    132: "log_device_object_property",
    133: "log_enable",
    134: "log_interval",
    135: "maximum_value",
    136: "minimum_value",
    137: "notification_threshold",
    138: "previous_notify_time",
    139: "protocol_revision",
    140: "records_since_notification",
    141: "record_count",
    142: "start_time",
    143: "stop_time",
    144: "stop_when_full",
    145: "total_record_count",
    146: "valid_samples",
    147: "window_interval",
    148: "window_samples",
    149: "maximum_value_timestamp",
    150: "minimum_value_timestamp",
    151: "variance_value",
    152: "active_cov_subscriptions",
    153: "backup_failure_timeout",
    154: "configuration_files",
    155: "database_revision",
    156: "direct_reading",
    157: "last_restore_time",
    158: "maintenance_required",
    159: "member_of",
    160: "mode",
    161: "operation_expected",
    162: "setting",
    163: "silenced",
    164: "tracking_value",
    165: "zone_members",
    166: "life_safety_alarm_values",
    167: "max_segments_accepted",
    168: "profile_name",
}


@dataclass
class BACnetPacketData:
    """Parsed BACnet/IP packet data."""

    # BVLC layer
    bvlc_type: int = 0
    bvlc_type_name: str = ""
    bvlc_length: int = 0

    # NPDU layer (if present)
    npdu_version: int = 1
    npdu_control: int = 0
    has_dnet: bool = False
    dnet: int | None = None
    dadr: bytes | None = None
    has_snet: bool = False
    snet: int | None = None
    sadr: bytes | None = None
    hop_count: int | None = None

    # APDU layer (if present)
    apdu_type: int | None = None
    apdu_type_name: str = ""
    invoke_id: int | None = None
    service_choice: int | None = None
    service_name: str = ""

    # Object information (from service data)
    object_type: int | None = None
    object_type_name: str = ""
    object_instance: int | None = None
    property_id: int | None = None
    property_name: str = ""

    # Device identity (from I-Am or ReadProperty responses)
    device_instance: int | None = None
    vendor_id: int | None = None
    vendor_name: str | None = None
    model_name: str | None = None
    firmware_revision: str | None = None


class BACnetExtractor(ProtocolExtractor):
    """Extract patterns from BACnet/IP traffic.

    Analyzes:
    - Service type distribution (readProperty, writeProperty, etc.)
    - Object type access patterns
    - Property access patterns
    - Device identities from I-Am responses
    - COV subscriptions
    """

    BACNET_PORT = 47808  # 0xBAC0

    def __init__(self):
        self.packets: list[BACnetPacketData] = []
        self.service_counts: dict[str, int] = defaultdict(int)
        self.object_accesses: dict[str, list[dict]] = defaultdict(list)
        self.property_accesses: dict[int, int] = defaultdict(int)
        self.device_identities: dict[str, dict] = {}  # ip -> identity
        self.vendor_counts: dict[int, int] = defaultdict(int)
        self.request_counts = 0
        self.response_counts = 0
        self.error_counts: dict[str, int] = defaultdict(int)

    @property
    def protocol_name(self) -> str:
        return "bacnet_ip"

    @property
    def well_known_ports(self) -> list[int]:
        return [47808]

    def reset(self):
        """Reset extractor state for new analysis."""
        self.packets = []
        self.service_counts = defaultdict(int)
        self.object_accesses = defaultdict(list)
        self.property_accesses = defaultdict(int)
        self.device_identities = {}
        self.vendor_counts = defaultdict(int)
        self.request_counts = 0
        self.response_counts = 0
        self.error_counts = defaultdict(int)

    def can_handle(self, packet: Packet) -> bool:
        """Check if packet is BACnet/IP."""
        if not packet.haslayer(UDP):
            return False

        udp = packet[UDP]

        # Check for BACnet port
        if udp.sport != self.BACNET_PORT and udp.dport != self.BACNET_PORT:
            return False

        # Check for payload
        if not packet.haslayer(Raw):
            return False

        payload = bytes(packet[Raw].load)
        if len(payload) < 4:
            return False

        # Check BVLC type byte (0x81 = BACnet/IP)
        return payload[0] == 0x81

    def extract_packet_info(self, packet: Packet) -> ExtractedPacketInfo | None:
        """Extract BACnet packet information."""
        if not self.can_handle(packet):
            return None

        try:
            parsed = self._parse_bacnet_packet(packet)
            if not parsed:
                return None

            ip = packet[IP]
            udp = packet[UDP]

            self.packets.append(parsed)

            # Track service usage
            if parsed.service_name:
                self.service_counts[parsed.service_name] += 1

            # Determine direction based on APDU type
            is_request = parsed.apdu_type in [0, 1]  # Confirmed/Unconfirmed request
            if is_request:
                self.request_counts += 1
            else:
                self.response_counts += 1

            # Track object accesses
            if parsed.object_type_name:
                self.object_accesses[parsed.object_type_name].append({
                    "instance": parsed.object_instance,
                    "property_id": parsed.property_id,
                    "property_name": parsed.property_name,
                    "service": parsed.service_name,
                })

            # Track property accesses
            if parsed.property_id is not None:
                self.property_accesses[parsed.property_id] += 1

            # Track device identities from I-Am
            if parsed.service_name == "i_Am" and parsed.device_instance is not None:
                self.device_identities[ip.src] = {
                    "device_instance": parsed.device_instance,
                    "vendor_id": parsed.vendor_id,
                    "vendor_name": parsed.vendor_name,
                    "model_name": parsed.model_name,
                    "firmware_revision": parsed.firmware_revision,
                }
                if parsed.vendor_id is not None:
                    self.vendor_counts[parsed.vendor_id] += 1

            # Track errors
            if parsed.apdu_type == 5:  # Error
                self.error_counts[parsed.service_name or "unknown"] += 1

            return ExtractedPacketInfo(
                timestamp=float(packet.time),
                src_ip=ip.src,
                dst_ip=ip.dst,
                src_port=udp.sport,
                dst_port=udp.dport,
                protocol=self.protocol_name,
                direction="request" if is_request else "response",
                function_code=parsed.service_choice,
                payload_size=len(packet[Raw].load),
                metadata={
                    "bvlc_type": parsed.bvlc_type_name,
                    "apdu_type": parsed.apdu_type_name,
                    "service": parsed.service_name,
                    "object_type": parsed.object_type_name,
                    "object_instance": parsed.object_instance,
                    "property_id": parsed.property_id,
                },
            )
        except Exception as e:
            logger.debug(f"Failed to parse BACnet packet: {e}")
            return None

    def is_request(self, packet: Packet) -> bool:
        """Check if packet is a BACnet request."""
        if not packet.haslayer(UDP):
            return False
        return packet[UDP].dport == self.BACNET_PORT

    def extract_identity_info(self, packet: Packet) -> dict | None:
        """Extract device identity from I-Am response."""
        if not self.can_handle(packet):
            return None

        parsed = self._parse_bacnet_packet(packet)
        if parsed and parsed.service_name == "i_Am":
            return {
                "device_instance": parsed.device_instance,
                "vendor_id": parsed.vendor_id,
                "vendor_name": parsed.vendor_name,
                "model_name": parsed.model_name,
                "firmware_revision": parsed.firmware_revision,
            }
        return None

    def _parse_bacnet_packet(self, packet: Packet) -> BACnetPacketData | None:
        """Parse BACnet/IP packet into structured data."""
        payload = bytes(packet[Raw].load)

        if len(payload) < 4:
            return None

        data = BACnetPacketData()

        # Parse BVLC header
        bvlc_type = payload[0]
        if bvlc_type != 0x81:  # Not BACnet/IP
            return None

        data.bvlc_type = payload[1]
        data.bvlc_type_name = BVLC_TYPE.get(data.bvlc_type, f"unknown_{data.bvlc_type:02x}")
        data.bvlc_length = struct.unpack(">H", payload[2:4])[0]

        # For Original-Unicast-NPDU and Original-Broadcast-NPDU, parse NPDU
        if data.bvlc_type not in [0x0A, 0x0B, 0x04]:
            return data

        npdu_start = 4
        if data.bvlc_type == 0x04:  # Forwarded-NPDU has extra IP:port
            npdu_start = 10

        if len(payload) < npdu_start + 2:
            return data

        # Parse NPDU
        data.npdu_version = payload[npdu_start]
        data.npdu_control = payload[npdu_start + 1]

        # Calculate APDU start based on NPDU control flags
        apdu_start = npdu_start + 2

        # Check for DNET/DADR
        if data.npdu_control & 0x20:  # Has destination
            data.has_dnet = True
            if len(payload) > apdu_start + 3:
                data.dnet = struct.unpack(">H", payload[apdu_start:apdu_start + 2])[0]
                dadr_len = payload[apdu_start + 2]
                apdu_start += 3 + dadr_len
                if dadr_len > 0:
                    data.dadr = payload[apdu_start - dadr_len:apdu_start]

        # Check for SNET/SADR
        if data.npdu_control & 0x08:  # Has source
            data.has_snet = True
            if len(payload) > apdu_start + 3:
                data.snet = struct.unpack(">H", payload[apdu_start:apdu_start + 2])[0]
                sadr_len = payload[apdu_start + 2]
                apdu_start += 3 + sadr_len
                if sadr_len > 0:
                    data.sadr = payload[apdu_start - sadr_len:apdu_start]

        # Hop count if destination present
        if data.has_dnet and len(payload) > apdu_start:
            data.hop_count = payload[apdu_start]
            apdu_start += 1

        # Check if this is an APDU or network layer message
        if data.npdu_control & 0x80:  # Network layer message
            return data

        if len(payload) <= apdu_start:
            return data

        # Parse APDU
        apdu_type_byte = payload[apdu_start]
        data.apdu_type = (apdu_type_byte >> 4) & 0x0F
        data.apdu_type_name = APDU_TYPE.get(data.apdu_type, f"unknown_{data.apdu_type}")

        # Parse based on APDU type
        if data.apdu_type == 0:  # Confirmed Request
            self._parse_confirmed_request(payload, apdu_start, data)
        elif data.apdu_type == 1:  # Unconfirmed Request
            self._parse_unconfirmed_request(payload, apdu_start, data)
        elif data.apdu_type == 3:  # Complex ACK
            self._parse_complex_ack(payload, apdu_start, data)

        return data

    def _parse_confirmed_request(self, payload: bytes, start: int, data: BACnetPacketData) -> None:
        """Parse confirmed request APDU."""
        try:
            if len(payload) < start + 4:
                return

            # Get invoke ID and service choice
            pdu_flags = payload[start]
            seg = (pdu_flags >> 3) & 0x01
            mor = (pdu_flags >> 2) & 0x01

            pos = start + 1
            # Skip max segments and max APDU length accepted if segmented
            if seg:
                pos += 1  # Skip sequence number
                pos += 1  # Skip proposed window size

            if len(payload) <= pos + 1:
                return

            data.invoke_id = payload[pos]
            data.service_choice = payload[pos + 1]
            data.service_name = CONFIRMED_SERVICE.get(data.service_choice, f"service_{data.service_choice}")

            # Parse service-specific data
            service_data_start = pos + 2
            if data.service_choice in [12, 15]:  # ReadProperty, WriteProperty
                self._parse_property_access(payload, service_data_start, data)
        except Exception:
            pass

    def _parse_unconfirmed_request(self, payload: bytes, start: int, data: BACnetPacketData) -> None:
        """Parse unconfirmed request APDU."""
        try:
            if len(payload) < start + 2:
                return

            data.service_choice = payload[start + 1]
            data.service_name = UNCONFIRMED_SERVICE.get(data.service_choice, f"service_{data.service_choice}")

            # Parse I-Am response data
            if data.service_choice == 0:  # I-Am
                self._parse_i_am(payload, start + 2, data)
        except Exception:
            pass

    def _parse_complex_ack(self, payload: bytes, start: int, data: BACnetPacketData) -> None:
        """Parse complex ACK APDU."""
        try:
            if len(payload) < start + 3:
                return

            data.invoke_id = payload[start + 1]
            data.service_choice = payload[start + 2]
            data.service_name = CONFIRMED_SERVICE.get(data.service_choice, f"service_{data.service_choice}")
        except Exception:
            pass

    def _parse_property_access(self, payload: bytes, start: int, data: BACnetPacketData) -> None:
        """Parse ReadProperty/WriteProperty service data."""
        try:
            if len(payload) < start + 4:
                return

            # Object identifier is tagged with context tag 0
            if (payload[start] & 0xF8) == 0x0C:  # Context tag 0, length 4
                obj_id_bytes = payload[start + 1:start + 5]
                obj_id = struct.unpack(">I", obj_id_bytes)[0]
                data.object_type = (obj_id >> 22) & 0x3FF
                data.object_type_name = OBJECT_TYPE.get(data.object_type, f"type_{data.object_type}")
                data.object_instance = obj_id & 0x3FFFFF

                # Property identifier follows (context tag 1)
                prop_start = start + 5
                if len(payload) > prop_start:
                    tag = payload[prop_start]
                    if (tag & 0xF8) == 0x18:  # Context tag 1, extended
                        # Extended length encoding
                        pass
                    elif (tag & 0xF0) == 0x10:  # Context tag 1
                        prop_len = tag & 0x07
                        if prop_len <= 4 and len(payload) > prop_start + prop_len:
                            prop_bytes = bytes([0] * (4 - prop_len)) + payload[prop_start + 1:prop_start + 1 + prop_len]
                            data.property_id = struct.unpack(">I", prop_bytes)[0]
                            data.property_name = PROPERTY_ID.get(data.property_id, f"prop_{data.property_id}")
        except Exception:
            pass

    def _parse_i_am(self, payload: bytes, start: int, data: BACnetPacketData) -> None:
        """Parse I-Am service data."""
        try:
            if len(payload) < start + 4:
                return

            # Object identifier (device object)
            if (payload[start] & 0xF0) == 0xC0:  # Application tag 12 (object-id)
                obj_id_bytes = payload[start + 1:start + 5]
                obj_id = struct.unpack(">I", obj_id_bytes)[0]
                data.device_instance = obj_id & 0x3FFFFF

                # Max APDU length and segmentation follow
                # Vendor ID is after that
                pos = start + 5
                while pos < len(payload) - 2:
                    tag = payload[pos]
                    if (tag & 0xF0) == 0x20:  # Unsigned integer (vendor ID)
                        vendor_len = tag & 0x07
                        if vendor_len <= 2 and len(payload) > pos + vendor_len:
                            if vendor_len == 1:
                                data.vendor_id = payload[pos + 1]
                            elif vendor_len == 2:
                                data.vendor_id = struct.unpack(">H", payload[pos + 1:pos + 3])[0]
                        break
                    pos += 1
        except Exception:
            pass

    def build_patterns(self, packets: list[ExtractedPacketInfo] = None) -> dict[str, Any]:
        """Build learned patterns from extracted data."""
        total_samples = len(self.packets)
        if total_samples == 0:
            return {}

        # Service distribution
        total_services = sum(self.service_counts.values())
        service_distribution = {}
        for service, count in self.service_counts.items():
            service_distribution[service] = {
                "count": count,
                "frequency": count / total_services if total_services > 0 else 0,
            }

        # Object type access patterns
        object_patterns = {}
        for obj_type, accesses in self.object_accesses.items():
            if not accesses:
                continue

            instances = [a["instance"] for a in accesses if a["instance"] is not None]
            properties = [a["property_id"] for a in accesses if a["property_id"] is not None]

            object_patterns[obj_type] = {
                "total_accesses": len(accesses),
                "unique_instances": len(set(instances)) if instances else 0,
                "instance_range": {"min": min(instances), "max": max(instances)} if instances else None,
                "common_properties": self._get_common_items(properties, 5),
            }

        # Property access patterns
        total_prop_accesses = sum(self.property_accesses.values())
        property_distribution = {}
        for prop_id, count in sorted(self.property_accesses.items(), key=lambda x: x[1], reverse=True)[:20]:
            prop_name = PROPERTY_ID.get(prop_id, f"prop_{prop_id}")
            property_distribution[prop_id] = {
                "name": prop_name,
                "count": count,
                "frequency": count / total_prop_accesses if total_prop_accesses > 0 else 0,
            }

        # Vendor distribution
        vendor_distribution = dict(self.vendor_counts)

        # Error patterns
        error_patterns = dict(self.error_counts) if self.error_counts else None

        confidence = self.calculate_confidence(total_samples)

        return {
            "protocol": self.protocol_name,
            "function_codes": service_distribution,
            "address_patterns": object_patterns,
            "sample_count": total_samples,
            "request_count": self.request_counts,
            "response_count": self.response_counts,
            "confidence": confidence,
            "protocol_metadata": {
                "property_distribution": property_distribution,
                "vendor_distribution": vendor_distribution,
                "device_identities": self.device_identities if self.device_identities else None,
                "unique_services": len(self.service_counts),
                "unique_object_types": len(self.object_accesses),
            },
            "exception_patterns": error_patterns,
            "device_identities": list(self.device_identities.values()) if self.device_identities else None,
        }

    def _get_common_items(self, items: list, top_n: int = 5) -> list[dict]:
        """Get most common items from a list."""
        if not items:
            return []

        counts = defaultdict(int)
        for item in items:
            counts[item] += 1

        return [
            {"value": item, "count": count}
            for item, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
        ]
