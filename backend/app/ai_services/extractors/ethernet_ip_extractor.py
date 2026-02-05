"""EtherNet/IP (CIP) protocol extractor for deep packet analysis.

Extracts CIP service codes, object classes, connection patterns, and device identities.
"""

import logging
import struct
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from scapy.layers.inet import IP, TCP, UDP
from scapy.packet import Packet, Raw

from app.ai_services.extractors.base import (
    ExtractedPacketInfo,
    ProtocolExtractor,
)

logger = logging.getLogger(__name__)

# EtherNet/IP Encapsulation Commands
ENCAP_COMMAND = {
    0x0000: "nop",
    0x0001: "list_services",
    0x0004: "list_identity",
    0x0063: "list_interfaces",
    0x0064: "register_session",
    0x0065: "unregister_session",
    0x006F: "send_rr_data",  # Unconnected messages
    0x0070: "send_unit_data",  # Connected messages
    0x0072: "indicate_status",
    0x0073: "cancel",
}

# CIP Service Codes
CIP_SERVICE = {
    0x01: "get_attributes_all",
    0x02: "set_attributes_all",
    0x03: "get_attribute_list",
    0x04: "set_attribute_list",
    0x05: "reset",
    0x06: "start",
    0x07: "stop",
    0x08: "create",
    0x09: "delete",
    0x0A: "multiple_service_packet",
    0x0D: "apply_attributes",
    0x0E: "get_attribute_single",
    0x10: "set_attribute_single",
    0x14: "find_next_object_instance",
    0x15: "error_response",
    0x16: "restore",
    0x17: "save",
    0x18: "nop",
    0x19: "get_member",
    0x1A: "set_member",
    0x1B: "insert_member",
    0x1C: "remove_member",
    0x1D: "group_sync",
    0x4B: "execute_pccc",
    0x4C: "read_tag",
    0x4D: "write_tag",
    0x4E: "read_modify_write_tag",
    0x4F: "cas_tag",
    0x50: "read_tag_fragmented",
    0x51: "write_tag_fragmented",
    0x52: "read",
    0x53: "write",
    0x54: "forward_close",
    0x55: "get_connection_owner",
    0x59: "unconnected_send",
}

# CIP Object Classes
CIP_CLASS = {
    0x01: "identity",
    0x02: "message_router",
    0x03: "device_net",
    0x04: "assembly",
    0x05: "connection",
    0x06: "connection_manager",
    0x07: "register",
    0x08: "discrete_input_point",
    0x09: "discrete_output_point",
    0x0A: "analog_input_point",
    0x0B: "analog_output_point",
    0x0C: "presence_sensing",
    0x0E: "parameter",
    0x0F: "parameter_group",
    0x10: "group",
    0x12: "discrete_input_group",
    0x13: "discrete_output_group",
    0x14: "discrete_group",
    0x15: "analog_input_group",
    0x16: "analog_output_group",
    0x17: "analog_group",
    0x18: "position_sensor",
    0x19: "position_controller_supervisor",
    0x1A: "position_controller",
    0x1B: "block_sequencer",
    0x1C: "command_block",
    0x1D: "motor_data",
    0x1E: "control_supervisor",
    0x1F: "ac_dc_drive",
    0x20: "acknowledge_handler",
    0x21: "overload",
    0x22: "softstart",
    0x23: "selection",
    0x24: "device_net_supervision",
    0x25: "device_net_analog_input_point",
    0x26: "device_net_analog_output_point",
    0x27: "device_net_discrete_input_point",
    0x28: "device_net_discrete_output_point",
    0x29: "s_analog_sensor",
    0x2A: "s_analog_actuator",
    0x2B: "s_single_stage_controller",
    0x2C: "s_gas_calibration",
    0x2D: "trip_point",
    0x30: "file",
    0x37: "s_partial_pressure",
    0xF4: "port",
    0xF5: "tcp_ip_interface",
    0xF6: "ethernet_link",
    0x02B0: "symbol",
    0x02B1: "template",
}

# CIP General Status Codes
CIP_STATUS = {
    0x00: "success",
    0x01: "connection_failure",
    0x02: "resource_unavailable",
    0x03: "invalid_parameter_value",
    0x04: "path_segment_error",
    0x05: "path_destination_unknown",
    0x06: "partial_transfer",
    0x07: "connection_lost",
    0x08: "service_not_supported",
    0x09: "invalid_attribute_value",
    0x0A: "attribute_list_error",
    0x0B: "already_in_requested_mode",
    0x0C: "object_state_conflict",
    0x0D: "object_already_exists",
    0x0E: "attribute_not_settable",
    0x0F: "privilege_violation",
    0x10: "device_state_conflict",
    0x11: "reply_data_too_large",
    0x12: "fragmentation_of_primitive_value",
    0x13: "not_enough_data",
    0x14: "attribute_not_supported",
    0x15: "too_much_data",
    0x16: "object_does_not_exist",
    0x17: "service_fragmentation_sequence_not_in_progress",
    0x18: "no_stored_attribute_data",
    0x19: "store_operation_failure",
    0x1A: "routing_failure_request_packet_too_large",
    0x1B: "routing_failure_response_packet_too_large",
    0x1C: "missing_attribute_list_entry_data",
    0x1D: "invalid_attribute_value_list",
    0x1E: "embedded_service_error",
    0x1F: "vendor_specific_error",
    0x20: "invalid_parameter",
    0x21: "write_once_value_or_medium_already_written",
    0x22: "invalid_reply_received",
    0x25: "key_failure_in_path",
    0x26: "path_size_invalid",
    0x27: "unexpected_attribute_in_list",
    0x28: "invalid_member_id",
    0x29: "member_not_settable",
    0xFF: "extended_status",
}


@dataclass
class EtherNetIPPacketData:
    """Parsed EtherNet/IP packet data."""

    # Encapsulation header
    encap_command: int = 0
    encap_command_name: str = ""
    encap_length: int = 0
    session_handle: int = 0
    status: int = 0
    sender_context: bytes = b""
    options: int = 0

    # CIP layer (for SendRRData/SendUnitData)
    interface_handle: int = 0
    timeout: int = 0

    # CIP message
    cip_service: int | None = None
    cip_service_name: str = ""
    is_response: bool = False
    cip_status: int | None = None
    cip_status_name: str = ""
    cip_class: int | None = None
    cip_class_name: str = ""
    cip_instance: int | None = None
    cip_attribute: int | None = None

    # Connection info
    connection_id: int | None = None
    connection_serial: int | None = None

    # Identity info (from ListIdentity)
    vendor_id: int | None = None
    device_type: int | None = None
    product_code: int | None = None
    revision_major: int | None = None
    revision_minor: int | None = None
    serial_number: int | None = None
    product_name: str | None = None


class EtherNetIPExtractor(ProtocolExtractor):
    """Extract patterns from EtherNet/IP traffic.

    Analyzes:
    - CIP service code distribution
    - Object class access patterns
    - Connection patterns
    - Device identities from ListIdentity responses
    - Error patterns
    """

    ENIP_TCP_PORT = 44818  # Explicit messaging
    ENIP_UDP_PORT = 2222  # Implicit (I/O) messaging

    def __init__(self):
        self.packets: list[EtherNetIPPacketData] = []
        self.encap_command_counts: dict[int, int] = defaultdict(int)
        self.cip_service_counts: dict[int, int] = defaultdict(int)
        self.class_accesses: dict[int, list[dict]] = defaultdict(list)
        self.device_identities: dict[str, dict] = {}  # ip -> identity
        self.connection_counts: dict[int, int] = defaultdict(int)
        self.vendor_counts: dict[int, int] = defaultdict(int)
        self.error_counts: dict[int, int] = defaultdict(int)
        self.request_counts = 0
        self.response_counts = 0

    @property
    def protocol_name(self) -> str:
        return "ethernet_ip"

    @property
    def well_known_ports(self) -> list[int]:
        return [44818, 2222]

    def reset(self):
        """Reset extractor state for new analysis."""
        self.packets = []
        self.encap_command_counts = defaultdict(int)
        self.cip_service_counts = defaultdict(int)
        self.class_accesses = defaultdict(list)
        self.device_identities = {}
        self.connection_counts = defaultdict(int)
        self.vendor_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.request_counts = 0
        self.response_counts = 0

    def can_handle(self, packet: Packet) -> bool:
        """Check if packet is EtherNet/IP."""
        # Check TCP port
        if packet.haslayer(TCP):
            tcp = packet[TCP]
            if tcp.sport == self.ENIP_TCP_PORT or tcp.dport == self.ENIP_TCP_PORT:
                if packet.haslayer(Raw):
                    payload = bytes(packet[Raw].load)
                    return len(payload) >= 24  # Minimum encapsulation header
                return False

        # Check UDP port
        if packet.haslayer(UDP):
            udp = packet[UDP]
            if udp.sport == self.ENIP_UDP_PORT or udp.dport == self.ENIP_UDP_PORT:
                return packet.haslayer(Raw)
            # Also check for ListIdentity on UDP 44818
            if udp.sport == self.ENIP_TCP_PORT or udp.dport == self.ENIP_TCP_PORT:
                if packet.haslayer(Raw):
                    payload = bytes(packet[Raw].load)
                    return len(payload) >= 24

        return False

    def extract_packet_info(self, packet: Packet) -> ExtractedPacketInfo | None:
        """Extract EtherNet/IP packet information."""
        if not self.can_handle(packet):
            return None

        try:
            parsed = self._parse_enip_packet(packet)
            if not parsed:
                return None

            ip = packet[IP]

            # Determine transport port
            if packet.haslayer(TCP):
                sport = packet[TCP].sport
                dport = packet[TCP].dport
            else:
                sport = packet[UDP].sport
                dport = packet[UDP].dport

            self.packets.append(parsed)

            # Track encapsulation commands
            self.encap_command_counts[parsed.encap_command] += 1

            # Track CIP services
            if parsed.cip_service is not None:
                service_code = parsed.cip_service & 0x7F  # Remove response bit
                self.cip_service_counts[service_code] += 1

            # Determine direction
            is_request = not parsed.is_response
            if is_request:
                self.request_counts += 1
            else:
                self.response_counts += 1

            # Track class accesses
            if parsed.cip_class is not None:
                self.class_accesses[parsed.cip_class].append({
                    "instance": parsed.cip_instance,
                    "attribute": parsed.cip_attribute,
                    "service": parsed.cip_service_name,
                })

            # Track device identities from ListIdentity
            if parsed.encap_command == 0x0063 and parsed.vendor_id is not None:  # ListIdentity response
                self.device_identities[ip.src] = {
                    "vendor_id": parsed.vendor_id,
                    "device_type": parsed.device_type,
                    "product_code": parsed.product_code,
                    "revision": f"{parsed.revision_major}.{parsed.revision_minor}" if parsed.revision_major else None,
                    "serial_number": parsed.serial_number,
                    "product_name": parsed.product_name,
                }
                self.vendor_counts[parsed.vendor_id] += 1

            # Track errors
            if parsed.cip_status is not None and parsed.cip_status != 0:
                self.error_counts[parsed.cip_status] += 1

            return ExtractedPacketInfo(
                timestamp=float(packet.time),
                src_ip=ip.src,
                dst_ip=ip.dst,
                src_port=sport,
                dst_port=dport,
                protocol=self.protocol_name,
                direction="request" if is_request else "response",
                function_code=parsed.cip_service,
                payload_size=len(packet[Raw].load) if packet.haslayer(Raw) else 0,
                metadata={
                    "encap_command": parsed.encap_command_name,
                    "cip_service": parsed.cip_service_name,
                    "cip_class": parsed.cip_class_name,
                    "cip_instance": parsed.cip_instance,
                    "cip_status": parsed.cip_status_name,
                    "session_handle": parsed.session_handle,
                },
            )
        except Exception as e:
            logger.debug(f"Failed to parse EtherNet/IP packet: {e}")
            return None

    def is_request(self, packet: Packet) -> bool:
        """Check if packet is an EtherNet/IP request."""
        if packet.haslayer(TCP):
            return packet[TCP].dport == self.ENIP_TCP_PORT
        if packet.haslayer(UDP):
            return packet[UDP].dport in [self.ENIP_TCP_PORT, self.ENIP_UDP_PORT]
        return False

    def extract_identity_info(self, packet: Packet) -> dict | None:
        """Extract device identity from ListIdentity response."""
        if not self.can_handle(packet):
            return None

        parsed = self._parse_enip_packet(packet)
        if parsed and parsed.vendor_id is not None:
            return {
                "vendor_id": parsed.vendor_id,
                "device_type": parsed.device_type,
                "product_code": parsed.product_code,
                "revision": f"{parsed.revision_major}.{parsed.revision_minor}" if parsed.revision_major else None,
                "serial_number": parsed.serial_number,
                "product_name": parsed.product_name,
            }
        return None

    def _parse_enip_packet(self, packet: Packet) -> EtherNetIPPacketData | None:
        """Parse EtherNet/IP packet into structured data."""
        if not packet.haslayer(Raw):
            return None

        payload = bytes(packet[Raw].load)

        if len(payload) < 24:  # Minimum encapsulation header
            return None

        data = EtherNetIPPacketData()

        # Parse encapsulation header
        data.encap_command = struct.unpack("<H", payload[0:2])[0]
        data.encap_command_name = ENCAP_COMMAND.get(data.encap_command, f"cmd_{data.encap_command:04x}")
        data.encap_length = struct.unpack("<H", payload[2:4])[0]
        data.session_handle = struct.unpack("<I", payload[4:8])[0]
        data.status = struct.unpack("<I", payload[8:12])[0]
        data.sender_context = payload[12:20]
        data.options = struct.unpack("<I", payload[20:24])[0]

        # Parse based on command
        if data.encap_command == 0x0063:  # ListIdentity
            self._parse_list_identity_response(payload, 24, data)
        elif data.encap_command == 0x006F:  # SendRRData (Unconnected)
            self._parse_send_rr_data(payload, 24, data)
        elif data.encap_command == 0x0070:  # SendUnitData (Connected)
            self._parse_send_unit_data(payload, 24, data)

        return data

    def _parse_list_identity_response(self, payload: bytes, start: int, data: EtherNetIPPacketData) -> None:
        """Parse ListIdentity response to extract device info."""
        try:
            if len(payload) < start + 2:
                return

            item_count = struct.unpack("<H", payload[start:start + 2])[0]
            if item_count == 0:
                return

            pos = start + 2

            # Parse first identity item
            if len(payload) < pos + 4:
                return

            item_type = struct.unpack("<H", payload[pos:pos + 2])[0]
            item_length = struct.unpack("<H", payload[pos + 2:pos + 4])[0]
            pos += 4

            if item_type != 0x000C:  # Identity item
                return

            if len(payload) < pos + 26:
                return

            # Skip encapsulation protocol version (2) and socket address (16)
            pos += 18

            # Parse identity
            data.vendor_id = struct.unpack("<H", payload[pos:pos + 2])[0]
            data.device_type = struct.unpack("<H", payload[pos + 2:pos + 4])[0]
            data.product_code = struct.unpack("<H", payload[pos + 4:pos + 6])[0]
            data.revision_major = payload[pos + 6]
            data.revision_minor = payload[pos + 7]
            # Skip status (2), serial number (4)
            data.serial_number = struct.unpack("<I", payload[pos + 10:pos + 14])[0]

            # Product name length and string
            name_len = payload[pos + 14]
            if len(payload) >= pos + 15 + name_len:
                data.product_name = payload[pos + 15:pos + 15 + name_len].decode("utf-8", errors="ignore")
        except Exception:
            pass

    def _parse_send_rr_data(self, payload: bytes, start: int, data: EtherNetIPPacketData) -> None:
        """Parse SendRRData (unconnected messaging)."""
        try:
            if len(payload) < start + 6:
                return

            data.interface_handle = struct.unpack("<I", payload[start:start + 4])[0]
            data.timeout = struct.unpack("<H", payload[start + 4:start + 6])[0]

            # Parse CPF (Common Packet Format)
            cpf_start = start + 6
            self._parse_cpf(payload, cpf_start, data)
        except Exception:
            pass

    def _parse_send_unit_data(self, payload: bytes, start: int, data: EtherNetIPPacketData) -> None:
        """Parse SendUnitData (connected messaging)."""
        try:
            if len(payload) < start + 6:
                return

            data.interface_handle = struct.unpack("<I", payload[start:start + 4])[0]
            data.timeout = struct.unpack("<H", payload[start + 4:start + 6])[0]

            # Parse CPF
            cpf_start = start + 6
            self._parse_cpf(payload, cpf_start, data, connected=True)
        except Exception:
            pass

    def _parse_cpf(self, payload: bytes, start: int, data: EtherNetIPPacketData, connected: bool = False) -> None:
        """Parse Common Packet Format items."""
        try:
            if len(payload) < start + 2:
                return

            item_count = struct.unpack("<H", payload[start:start + 2])[0]
            pos = start + 2

            for _ in range(item_count):
                if len(payload) < pos + 4:
                    break

                item_type = struct.unpack("<H", payload[pos:pos + 2])[0]
                item_length = struct.unpack("<H", payload[pos + 2:pos + 4])[0]
                pos += 4

                if item_type == 0x00A1:  # Connected address item
                    if len(payload) >= pos + 4:
                        data.connection_id = struct.unpack("<I", payload[pos:pos + 4])[0]

                elif item_type == 0x00B2:  # Unconnected data item
                    self._parse_cip_message(payload, pos, data)

                elif item_type == 0x00B1:  # Connected data item
                    # Skip sequence count (2 bytes)
                    self._parse_cip_message(payload, pos + 2, data)

                pos += item_length
        except Exception:
            pass

    def _parse_cip_message(self, payload: bytes, start: int, data: EtherNetIPPacketData) -> None:
        """Parse CIP message (service, path, data)."""
        try:
            if len(payload) < start + 2:
                return

            service = payload[start]
            data.cip_service = service
            data.is_response = (service & 0x80) != 0
            service_code = service & 0x7F
            data.cip_service_name = CIP_SERVICE.get(service_code, f"service_{service_code:02x}")

            # For responses, parse status
            if data.is_response:
                if len(payload) >= start + 4:
                    data.cip_status = payload[start + 2]
                    data.cip_status_name = CIP_STATUS.get(data.cip_status, f"status_{data.cip_status:02x}")
                return

            # For requests, parse path
            if len(payload) < start + 2:
                return

            path_size = payload[start + 1] * 2  # Path size in words
            path_start = start + 2

            if len(payload) >= path_start + path_size:
                self._parse_epath(payload, path_start, path_size, data)
        except Exception:
            pass

    def _parse_epath(self, payload: bytes, start: int, size: int, data: EtherNetIPPacketData) -> None:
        """Parse EPATH (Electronic Key Path)."""
        try:
            pos = start
            end = start + size

            while pos < end:
                segment = payload[pos]
                seg_type = (segment >> 5) & 0x07

                if seg_type == 1:  # Logical segment
                    logical_type = (segment >> 2) & 0x07
                    logical_format = segment & 0x03

                    if logical_format == 0:  # 8-bit
                        value = payload[pos + 1]
                        pos += 2
                    elif logical_format == 1:  # 16-bit
                        value = struct.unpack("<H", payload[pos + 2:pos + 4])[0]
                        pos += 4
                    else:
                        pos += 2
                        continue

                    if logical_type == 0:  # Class ID
                        data.cip_class = value
                        data.cip_class_name = CIP_CLASS.get(value, f"class_{value:04x}")
                    elif logical_type == 1:  # Instance ID
                        data.cip_instance = value
                    elif logical_type == 4:  # Attribute ID
                        data.cip_attribute = value
                else:
                    # Skip other segment types
                    pos += 2
        except Exception:
            pass

    def build_patterns(self, packets: list[ExtractedPacketInfo] = None) -> dict[str, Any]:
        """Build learned patterns from extracted data."""
        total_samples = len(self.packets)
        if total_samples == 0:
            return {}

        # Encapsulation command distribution
        total_encap = sum(self.encap_command_counts.values())
        encap_distribution = {}
        for cmd, count in self.encap_command_counts.items():
            cmd_name = ENCAP_COMMAND.get(cmd, f"cmd_{cmd:04x}")
            encap_distribution[cmd] = {
                "name": cmd_name,
                "count": count,
                "frequency": count / total_encap if total_encap > 0 else 0,
            }

        # CIP service distribution
        total_cip = sum(self.cip_service_counts.values())
        function_codes = {}
        for svc, count in self.cip_service_counts.items():
            svc_name = CIP_SERVICE.get(svc, f"service_{svc:02x}")
            function_codes[svc] = {
                "name": svc_name,
                "count": count,
                "frequency": count / total_cip if total_cip > 0 else 0,
            }

        # Class access patterns
        address_patterns = {}
        for class_id, accesses in self.class_accesses.items():
            if not accesses:
                continue

            class_name = CIP_CLASS.get(class_id, f"class_{class_id:04x}")
            instances = [a["instance"] for a in accesses if a["instance"] is not None]
            attributes = [a["attribute"] for a in accesses if a["attribute"] is not None]

            address_patterns[class_name] = {
                "class_id": class_id,
                "total_accesses": len(accesses),
                "unique_instances": len(set(instances)) if instances else 0,
                "instance_range": {"min": min(instances), "max": max(instances)} if instances else None,
                "common_attributes": self._get_common_items(attributes, 5),
            }

        # Vendor distribution
        vendor_distribution = dict(self.vendor_counts)

        # Error patterns
        exception_patterns = {}
        if self.error_counts:
            total_errors = sum(self.error_counts.values())
            for status, count in self.error_counts.items():
                status_name = CIP_STATUS.get(status, f"status_{status:02x}")
                exception_patterns[status] = {
                    "name": status_name,
                    "count": count,
                    "frequency": count / total_errors if total_errors > 0 else 0,
                }

        confidence = self.calculate_confidence(total_samples)

        return {
            "protocol": self.protocol_name,
            "function_codes": function_codes,
            "address_patterns": address_patterns,
            "sample_count": total_samples,
            "request_count": self.request_counts,
            "response_count": self.response_counts,
            "confidence": confidence,
            "protocol_metadata": {
                "encap_commands": encap_distribution,
                "vendor_distribution": vendor_distribution,
                "device_identities": self.device_identities if self.device_identities else None,
                "unique_services": len(self.cip_service_counts),
                "unique_classes": len(self.class_accesses),
            },
            "exception_patterns": exception_patterns if exception_patterns else None,
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
