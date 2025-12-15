"""Modbus TCP protocol extractor for deep packet analysis.

Extracts function codes, register patterns, device identities, and exception patterns.
"""

import logging
import struct
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from scapy.layers.inet import IP, TCP
from scapy.packet import Packet, Raw

from app.ai_services.extractors.base import (
    ExtractedPacketInfo,
    ProtocolExtractor,
)

logger = logging.getLogger(__name__)

# Modbus function codes
MODBUS_FC = {
    1: "read_coils",
    2: "read_discrete_inputs",
    3: "read_holding_registers",
    4: "read_input_registers",
    5: "write_single_coil",
    6: "write_single_register",
    7: "read_exception_status",
    8: "diagnostics",
    11: "get_comm_event_counter",
    12: "get_comm_event_log",
    15: "write_multiple_coils",
    16: "write_multiple_registers",
    17: "report_server_id",
    20: "read_file_record",
    21: "write_file_record",
    22: "mask_write_register",
    23: "read_write_multiple_registers",
    24: "read_fifo_queue",
    43: "encapsulated_interface_transport",  # MEI - Read Device ID
}

# Modbus exception codes
MODBUS_EXCEPTIONS = {
    1: "illegal_function",
    2: "illegal_data_address",
    3: "illegal_data_value",
    4: "slave_device_failure",
    5: "acknowledge",
    6: "slave_device_busy",
    8: "memory_parity_error",
    10: "gateway_path_unavailable",
    11: "gateway_target_failed",
}


@dataclass
class ModbusPacketData:
    """Parsed Modbus TCP packet data."""

    transaction_id: int
    protocol_id: int
    length: int
    unit_id: int
    function_code: int
    is_exception: bool = False
    exception_code: int | None = None

    # Request-specific
    start_address: int | None = None
    quantity: int | None = None
    write_value: int | None = None
    write_values: list[int] | None = None

    # Response-specific
    byte_count: int | None = None
    data: bytes | None = None

    # MEI / Device ID
    mei_type: int | None = None
    device_id_code: int | None = None
    object_id: int | None = None
    device_objects: dict | None = None


@dataclass
class RegisterAccess:
    """Track register access patterns."""

    address: int
    access_type: str  # read, write
    count: int = 1


class ModbusExtractor(ProtocolExtractor):
    """Extract patterns from Modbus TCP traffic.

    Analyzes:
    - Function code frequency and distribution
    - Register address access patterns
    - Unit ID distribution
    - Device identification (FC43)
    - Exception patterns
    """

    MODBUS_PORT = 502

    def __init__(self):
        self.packets: list[ModbusPacketData] = []
        self.function_code_counts: dict[int, int] = defaultdict(int)
        self.unit_id_counts: dict[int, int] = defaultdict(int)
        self.register_accesses: dict[str, list[RegisterAccess]] = defaultdict(list)
        self.exception_counts: dict[int, int] = defaultdict(int)
        self.device_identities: dict[str, dict] = {}  # ip -> identity info
        self.request_counts = 0
        self.response_counts = 0

    @property
    def protocol_name(self) -> str:
        return "modbus_tcp"

    @property
    def well_known_ports(self) -> list[int]:
        return [502]

    def reset(self):
        """Reset extractor state for new analysis."""
        self.packets = []
        self.function_code_counts = defaultdict(int)
        self.unit_id_counts = defaultdict(int)
        self.register_accesses = defaultdict(list)
        self.exception_counts = defaultdict(int)
        self.device_identities = {}
        self.request_counts = 0
        self.response_counts = 0

    def can_handle(self, packet: Packet) -> bool:
        """Check if packet is Modbus TCP."""
        if not packet.haslayer(TCP):
            return False

        tcp = packet[TCP]

        # Check for Modbus port
        if tcp.sport != self.MODBUS_PORT and tcp.dport != self.MODBUS_PORT:
            return False

        # Check for payload
        if not packet.haslayer(Raw):
            return False

        payload = bytes(packet[Raw].load)
        if len(payload) < 8:  # Minimum MBAP header + function code
            return False

        # Verify protocol ID (should be 0 for Modbus TCP)
        protocol_id = struct.unpack(">H", payload[2:4])[0]
        return protocol_id == 0

    def extract_packet_info(self, packet: Packet) -> ExtractedPacketInfo | None:
        """Extract Modbus packet information."""
        if not self.can_handle(packet):
            return None

        try:
            parsed = self._parse_modbus_packet(packet)
            if not parsed:
                return None

            ip = packet[IP]
            tcp = packet[TCP]

            # Track statistics
            self.packets.append(parsed)
            self.function_code_counts[parsed.function_code] += 1
            self.unit_id_counts[parsed.unit_id] += 1

            # Determine direction
            is_request = tcp.dport == self.MODBUS_PORT
            if is_request:
                self.request_counts += 1
            else:
                self.response_counts += 1

            # Track register access
            if parsed.start_address is not None:
                access_type = self._get_access_type(parsed.function_code)
                region = self._get_register_region(parsed.function_code)
                self.register_accesses[region].append(
                    RegisterAccess(
                        address=parsed.start_address,
                        access_type=access_type,
                        count=parsed.quantity or 1,
                    )
                )

            # Track exceptions
            if parsed.is_exception and parsed.exception_code:
                self.exception_counts[parsed.exception_code] += 1

            # Track device identity
            if parsed.device_objects:
                src_ip = ip.src if not is_request else ip.dst
                self.device_identities[src_ip] = parsed.device_objects

            return ExtractedPacketInfo(
                timestamp=float(packet.time),
                src_ip=ip.src,
                dst_ip=ip.dst,
                src_port=tcp.sport,
                dst_port=tcp.dport,
                protocol=self.protocol_name,
                direction="request" if is_request else "response",
                function_code=parsed.function_code,
                payload_size=len(packet[Raw].load),
                metadata={
                    "transaction_id": parsed.transaction_id,
                    "unit_id": parsed.unit_id,
                    "is_exception": parsed.is_exception,
                    "start_address": parsed.start_address,
                    "quantity": parsed.quantity,
                },
            )
        except Exception as e:
            logger.debug(f"Failed to parse Modbus packet: {e}")
            return None

    def is_request(self, packet: Packet) -> bool:
        """Check if packet is a Modbus request."""
        if not packet.haslayer(TCP):
            return False
        return packet[TCP].dport == self.MODBUS_PORT

    def extract_identity_info(self, packet: Packet) -> dict | None:
        """Extract device identity from FC43 Read Device ID response."""
        if not self.can_handle(packet):
            return None

        parsed = self._parse_modbus_packet(packet)
        if parsed and parsed.device_objects:
            return parsed.device_objects
        return None

    def _parse_modbus_packet(self, packet: Packet) -> ModbusPacketData | None:
        """Parse Modbus TCP packet into structured data."""
        payload = bytes(packet[Raw].load)

        if len(payload) < 8:
            return None

        # Parse MBAP header
        transaction_id = struct.unpack(">H", payload[0:2])[0]
        protocol_id = struct.unpack(">H", payload[2:4])[0]
        length = struct.unpack(">H", payload[4:6])[0]
        unit_id = payload[6]
        function_code = payload[7]

        # Check for exception response
        is_exception = (function_code & 0x80) != 0
        if is_exception:
            function_code = function_code & 0x7F
            exception_code = payload[8] if len(payload) > 8 else None
            return ModbusPacketData(
                transaction_id=transaction_id,
                protocol_id=protocol_id,
                length=length,
                unit_id=unit_id,
                function_code=function_code,
                is_exception=True,
                exception_code=exception_code,
            )

        data = ModbusPacketData(
            transaction_id=transaction_id,
            protocol_id=protocol_id,
            length=length,
            unit_id=unit_id,
            function_code=function_code,
        )

        # Parse function-specific data
        pdu = payload[7:]  # Start from function code

        if function_code in [1, 2, 3, 4]:  # Read functions
            if len(pdu) >= 5:
                # Request format
                data.start_address = struct.unpack(">H", pdu[1:3])[0]
                data.quantity = struct.unpack(">H", pdu[3:5])[0]
            elif len(pdu) >= 2:
                # Response format
                data.byte_count = pdu[1]
                if len(pdu) > 2:
                    data.data = pdu[2 : 2 + data.byte_count]

        elif function_code == 5:  # Write single coil
            if len(pdu) >= 5:
                data.start_address = struct.unpack(">H", pdu[1:3])[0]
                data.write_value = struct.unpack(">H", pdu[3:5])[0]

        elif function_code == 6:  # Write single register
            if len(pdu) >= 5:
                data.start_address = struct.unpack(">H", pdu[1:3])[0]
                data.write_value = struct.unpack(">H", pdu[3:5])[0]

        elif function_code in [15, 16]:  # Write multiple
            if len(pdu) >= 6:
                data.start_address = struct.unpack(">H", pdu[1:3])[0]
                data.quantity = struct.unpack(">H", pdu[3:5])[0]
                if len(pdu) > 5:
                    data.byte_count = pdu[5]

        elif function_code == 43:  # MEI - Read Device ID
            if len(pdu) >= 4:
                data.mei_type = pdu[1]
                data.device_id_code = pdu[2] if len(pdu) > 2 else None
                data.object_id = pdu[3] if len(pdu) > 3 else None

                # Parse device objects from response
                if len(pdu) > 8 and data.mei_type == 14:  # Read Device ID
                    data.device_objects = self._parse_device_id_response(pdu)

        return data

    def _parse_device_id_response(self, pdu: bytes) -> dict | None:
        """Parse Read Device Identification response (FC43, MEI type 14)."""
        try:
            if len(pdu) < 8:
                return None

            # Skip: FC(1) + MEI(1) + DeviceID(1) + ConformityLevel(1) + MoreFollows(1) + NextObjId(1) + NumObjects(1)
            num_objects = pdu[7]
            objects = {}

            pos = 8
            for _ in range(num_objects):
                if pos + 2 > len(pdu):
                    break
                obj_id = pdu[pos]
                obj_len = pdu[pos + 1]
                if pos + 2 + obj_len > len(pdu):
                    break
                obj_value = pdu[pos + 2 : pos + 2 + obj_len].decode("utf-8", errors="ignore")
                pos += 2 + obj_len

                # Map object IDs to names
                obj_names = {
                    0x00: "vendor_name",
                    0x01: "product_code",
                    0x02: "major_minor_revision",
                    0x03: "vendor_url",
                    0x04: "product_name",
                    0x05: "model_name",
                    0x06: "user_application_name",
                }
                obj_name = obj_names.get(obj_id, f"object_{obj_id}")
                objects[obj_name] = obj_value

            return objects if objects else None
        except Exception:
            return None

    def _get_access_type(self, fc: int) -> str:
        """Get access type (read/write) for function code."""
        read_fcs = [1, 2, 3, 4, 7, 11, 12, 17, 20, 24]
        return "read" if fc in read_fcs else "write"

    def _get_register_region(self, fc: int) -> str:
        """Get register region for function code."""
        regions = {
            1: "coils",
            2: "discrete_inputs",
            3: "holding_registers",
            4: "input_registers",
            5: "coils",
            6: "holding_registers",
            15: "coils",
            16: "holding_registers",
        }
        return regions.get(fc, "other")

    def build_patterns(self, packets: list[ExtractedPacketInfo] = None) -> dict[str, Any]:
        """Build learned patterns from extracted data.

        Returns:
            Dictionary with pattern data for LearnedProtocolPattern model
        """
        total_samples = len(self.packets)
        if total_samples == 0:
            return {}

        # Function code distribution
        total_fc_count = sum(self.function_code_counts.values())
        function_codes = {}
        for fc, count in self.function_code_counts.items():
            fc_name = MODBUS_FC.get(fc, f"unknown_{fc}")
            function_codes[fc] = {
                "name": fc_name,
                "count": count,
                "frequency": count / total_fc_count if total_fc_count > 0 else 0,
            }

        # Unit ID distribution
        total_unit_count = sum(self.unit_id_counts.values())
        unit_id_distribution = {
            uid: count / total_unit_count if total_unit_count > 0 else 0
            for uid, count in self.unit_id_counts.items()
        }

        # Address patterns
        address_patterns = {}
        for region, accesses in self.register_accesses.items():
            if not accesses:
                continue

            addresses = [a.address for a in accesses]
            address_patterns[region] = {
                "min_address": min(addresses),
                "max_address": max(addresses),
                "unique_addresses": len(set(addresses)),
                "total_accesses": len(accesses),
                "hot_spots": self._find_hot_spots(accesses),
                "ranges": self._find_address_ranges(addresses),
            }

        # Exception patterns
        exception_patterns = {}
        if self.exception_counts:
            total_exc = sum(self.exception_counts.values())
            for exc_code, count in self.exception_counts.items():
                exc_name = MODBUS_EXCEPTIONS.get(exc_code, f"unknown_{exc_code}")
                exception_patterns[exc_code] = {
                    "name": exc_name,
                    "count": count,
                    "frequency": count / total_exc if total_exc > 0 else 0,
                }

        # Calculate confidence
        confidence = self.calculate_confidence(
            total_samples,
            pattern_consistency=min(1.0, len(self.function_code_counts) / 5)
        )

        return {
            "protocol": self.protocol_name,
            "function_codes": function_codes,
            "address_patterns": address_patterns,
            "unit_id_distribution": unit_id_distribution,
            "exception_patterns": exception_patterns,
            "device_identities": self.device_identities if self.device_identities else None,
            "sample_count": total_samples,
            "request_count": self.request_counts,
            "response_count": self.response_counts,
            "confidence": confidence,
            "protocol_metadata": {
                "unique_unit_ids": len(self.unit_id_counts),
                "unique_function_codes": len(self.function_code_counts),
                "has_device_id": len(self.device_identities) > 0,
            },
        }

    def _find_hot_spots(self, accesses: list[RegisterAccess], top_n: int = 10) -> list[dict]:
        """Find most frequently accessed addresses."""
        addr_counts = defaultdict(int)
        for access in accesses:
            addr_counts[access.address] += access.count

        sorted_addrs = sorted(addr_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"address": addr, "access_count": count}
            for addr, count in sorted_addrs[:top_n]
        ]

    def _find_address_ranges(self, addresses: list[int]) -> list[dict]:
        """Find contiguous address ranges."""
        if not addresses:
            return []

        sorted_addrs = sorted(set(addresses))
        ranges = []
        start = sorted_addrs[0]
        end = start

        for addr in sorted_addrs[1:]:
            if addr <= end + 10:  # Allow small gaps
                end = addr
            else:
                ranges.append({"start": start, "end": end, "size": end - start + 1})
                start = addr
                end = addr

        ranges.append({"start": start, "end": end, "size": end - start + 1})
        return ranges
