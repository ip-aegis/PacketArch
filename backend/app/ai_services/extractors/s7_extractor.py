"""S7comm protocol extractor for deep packet analysis.

Extracts S7 function codes, memory area patterns, PDU parameters, and connection info.
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

# S7 PDU Types
S7_PDU_TYPE = {
    0x01: "job",
    0x02: "ack",
    0x03: "ack_data",
    0x07: "userdata",
}

# S7 Function Codes
S7_FUNCTION = {
    0x00: "cpu_services",
    0x04: "read_var",
    0x05: "write_var",
    0x1A: "request_download",
    0x1B: "download_block",
    0x1C: "download_ended",
    0x1D: "start_upload",
    0x1E: "upload",
    0x1F: "end_upload",
    0x28: "plc_control",
    0x29: "plc_stop",
    0xF0: "setup_communication",
}

# S7 Memory Areas
S7_AREA = {
    0x03: "system_info",
    0x05: "system_flags",
    0x06: "analog_inputs",
    0x07: "analog_outputs",
    0x80: "p",  # Direct peripheral access
    0x81: "inputs",  # Process inputs
    0x82: "outputs",  # Process outputs
    0x83: "flags",  # Flags/markers (M)
    0x84: "db",  # Data blocks
    0x85: "di",  # Instance data blocks
    0x86: "local",  # Local data
    0x87: "v",  # Previous local data
    0x1C: "counter",
    0x1D: "timer",
}

# COTP PDU Types
COTP_TYPE = {
    0xE0: "cr",  # Connection Request
    0xD0: "cc",  # Connection Confirm
    0x80: "dr",  # Disconnect Request
    0xC0: "dc",  # Disconnect Confirm
    0xF0: "dt",  # Data Transfer
}


@dataclass
class S7PacketData:
    """Parsed S7 packet data."""

    # TPKT layer
    tpkt_version: int = 3
    tpkt_length: int = 0

    # COTP layer
    cotp_type: int = 0
    cotp_type_name: str = ""

    # S7 layer (if present)
    protocol_id: int | None = None
    pdu_type: int | None = None
    pdu_type_name: str = ""
    pdu_ref: int | None = None
    param_length: int = 0
    data_length: int = 0
    error_class: int = 0
    error_code: int = 0

    # Function specific
    function_code: int | None = None
    function_name: str = ""
    item_count: int = 0

    # Read/Write specific
    read_items: list[dict] = field(default_factory=list)
    write_items: list[dict] = field(default_factory=list)

    # Setup Communication specific
    max_amq_calling: int | None = None
    max_amq_called: int | None = None
    pdu_size: int | None = None

    # COTP Connection specific
    src_ref: int | None = None
    dst_ref: int | None = None
    src_tsap: bytes | None = None
    dst_tsap: bytes | None = None
    rack: int | None = None
    slot: int | None = None


class S7Extractor(ProtocolExtractor):
    """Extract patterns from S7comm traffic.

    Analyzes:
    - S7 function code distribution
    - Memory area access patterns (DB, M, I, Q)
    - PDU size negotiation
    - Rack/slot configurations
    - Connection patterns
    """

    S7_PORT = 102  # ISO-TSAP port

    def __init__(self):
        self.packets: list[S7PacketData] = []
        self.function_counts: dict[int, int] = defaultdict(int)
        self.area_accesses: dict[str, list[dict]] = defaultdict(list)
        self.db_accesses: dict[int, list[dict]] = defaultdict(list)
        self.pdu_sizes: list[int] = []
        self.rack_slot_configs: list[tuple[int, int]] = []
        self.connection_types: dict[str, int] = defaultdict(int)
        self.request_counts = 0
        self.response_counts = 0
        self.error_counts: dict[tuple[int, int], int] = defaultdict(int)

    @property
    def protocol_name(self) -> str:
        return "s7comm"

    @property
    def well_known_ports(self) -> list[int]:
        return [102]

    def reset(self):
        """Reset extractor state for new analysis."""
        self.packets = []
        self.function_counts = defaultdict(int)
        self.area_accesses = defaultdict(list)
        self.db_accesses = defaultdict(list)
        self.pdu_sizes = []
        self.rack_slot_configs = []
        self.connection_types = defaultdict(int)
        self.request_counts = 0
        self.response_counts = 0
        self.error_counts = defaultdict(int)

    def can_handle(self, packet: Packet) -> bool:
        """Check if packet is S7comm (ISO-TSAP/TPKT)."""
        if not packet.haslayer(TCP):
            return False

        tcp = packet[TCP]

        # Check for ISO-TSAP port (102)
        if tcp.sport != self.S7_PORT and tcp.dport != self.S7_PORT:
            return False

        # Check for payload
        if not packet.haslayer(Raw):
            return False

        payload = bytes(packet[Raw].load)
        if len(payload) < 4:
            return False

        # Check TPKT header (version should be 3)
        return payload[0] == 0x03

    def extract_packet_info(self, packet: Packet) -> ExtractedPacketInfo | None:
        """Extract S7 packet information."""
        if not self.can_handle(packet):
            return None

        try:
            parsed = self._parse_s7_packet(packet)
            if not parsed:
                return None

            ip = packet[IP]
            tcp = packet[TCP]

            self.packets.append(parsed)

            # Track function codes
            if parsed.function_code is not None:
                self.function_counts[parsed.function_code] += 1

            # Determine direction
            is_request = tcp.dport == self.S7_PORT
            if parsed.pdu_type == 0x01:  # JOB
                self.request_counts += 1
            elif parsed.pdu_type in [0x02, 0x03]:  # ACK, ACK_DATA
                self.response_counts += 1

            # Track memory area accesses
            for item in parsed.read_items + parsed.write_items:
                area = item.get("area", 0)
                area_name = S7_AREA.get(area, f"area_{area}")
                access_type = "read" if item in parsed.read_items else "write"

                self.area_accesses[area_name].append({
                    "db_number": item.get("db_number", 0),
                    "start": item.get("start", 0),
                    "size": item.get("size", 0),
                    "access_type": access_type,
                })

                # Track DB accesses specifically
                if area == 0x84:  # DB area
                    db_num = item.get("db_number", 0)
                    self.db_accesses[db_num].append({
                        "start": item.get("start", 0),
                        "size": item.get("size", 0),
                        "access_type": access_type,
                    })

            # Track PDU sizes
            if parsed.pdu_size:
                self.pdu_sizes.append(parsed.pdu_size)

            # Track rack/slot
            if parsed.rack is not None and parsed.slot is not None:
                self.rack_slot_configs.append((parsed.rack, parsed.slot))

            # Track errors
            if parsed.error_class != 0 or parsed.error_code != 0:
                self.error_counts[(parsed.error_class, parsed.error_code)] += 1

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
                    "pdu_type": parsed.pdu_type,
                    "pdu_type_name": parsed.pdu_type_name,
                    "function_name": parsed.function_name,
                    "cotp_type": parsed.cotp_type_name,
                    "item_count": parsed.item_count,
                },
            )
        except Exception as e:
            logger.debug(f"Failed to parse S7 packet: {e}")
            return None

    def is_request(self, packet: Packet) -> bool:
        """Check if packet is an S7 request."""
        if not packet.haslayer(TCP):
            return False
        return packet[TCP].dport == self.S7_PORT

    def _parse_s7_packet(self, packet: Packet) -> S7PacketData | None:
        """Parse S7 packet into structured data."""
        payload = bytes(packet[Raw].load)

        if len(payload) < 7:
            return None

        data = S7PacketData()

        # Parse TPKT header
        data.tpkt_version = payload[0]
        data.tpkt_length = struct.unpack(">H", payload[2:4])[0]

        # Parse COTP header
        cotp_start = 4
        cotp_length = payload[cotp_start]
        cotp_type = payload[cotp_start + 1] & 0xF0
        data.cotp_type = cotp_type
        data.cotp_type_name = COTP_TYPE.get(cotp_type, f"unknown_{cotp_type:02x}")

        # Parse COTP parameters for CR/CC
        if cotp_type in [0xE0, 0xD0]:  # CR or CC
            self._parse_cotp_connection(payload, cotp_start, data)
            return data

        # For DT (Data Transfer), parse S7 payload
        if cotp_type != 0xF0:  # Not DT
            return data

        # S7 payload starts after COTP header
        s7_start = cotp_start + cotp_length + 1

        if len(payload) < s7_start + 10:
            return data

        # Parse S7 header
        data.protocol_id = payload[s7_start]
        if data.protocol_id != 0x32:  # Not S7
            return data

        data.pdu_type = payload[s7_start + 1]
        data.pdu_type_name = S7_PDU_TYPE.get(data.pdu_type, f"unknown_{data.pdu_type}")
        data.pdu_ref = struct.unpack(">H", payload[s7_start + 4:s7_start + 6])[0]
        data.param_length = struct.unpack(">H", payload[s7_start + 6:s7_start + 8])[0]
        data.data_length = struct.unpack(">H", payload[s7_start + 8:s7_start + 10])[0]

        # For ACK/ACK_DATA, parse error fields
        header_len = 10
        if data.pdu_type in [0x02, 0x03]:
            if len(payload) >= s7_start + 12:
                data.error_class = payload[s7_start + 10]
                data.error_code = payload[s7_start + 11]
                header_len = 12

        # Parse parameter data
        param_start = s7_start + header_len
        if data.param_length > 0 and len(payload) >= param_start + data.param_length:
            self._parse_s7_params(payload, param_start, data)

        return data

    def _parse_cotp_connection(self, payload: bytes, start: int, data: S7PacketData) -> None:
        """Parse COTP CR/CC parameters for rack/slot info."""
        try:
            cotp_length = payload[start]

            # Parse fixed part
            if len(payload) < start + 7:
                return

            data.dst_ref = struct.unpack(">H", payload[start + 2:start + 4])[0]
            data.src_ref = struct.unpack(">H", payload[start + 4:start + 6])[0]

            # Parse variable parameters
            pos = start + 7
            while pos < start + cotp_length + 1 and pos + 2 < len(payload):
                param_code = payload[pos]
                param_len = payload[pos + 1]

                if param_code == 0xC1:  # Source TSAP
                    data.src_tsap = payload[pos + 2:pos + 2 + param_len]
                elif param_code == 0xC2:  # Destination TSAP
                    data.dst_tsap = payload[pos + 2:pos + 2 + param_len]
                    if param_len >= 2:
                        conn_type = payload[pos + 2]
                        rack_slot = payload[pos + 3]
                        data.rack = rack_slot >> 5
                        data.slot = rack_slot & 0x1F
                        # Track connection type
                        conn_type_name = {1: "PG", 2: "OP", 3: "S7Basic"}.get(
                            conn_type, f"type_{conn_type}"
                        )
                        self.connection_types[conn_type_name] += 1

                pos += 2 + param_len
        except Exception:
            pass

    def _parse_s7_params(self, payload: bytes, start: int, data: S7PacketData) -> None:
        """Parse S7 parameter data."""
        try:
            if len(payload) <= start:
                return

            data.function_code = payload[start]
            data.function_name = S7_FUNCTION.get(
                data.function_code, f"func_{data.function_code:02x}"
            )

            # Parse function-specific data
            if data.function_code == 0xF0:  # Setup Communication
                self._parse_setup_comm(payload, start, data)
            elif data.function_code in [0x04, 0x05]:  # Read/Write Var
                self._parse_read_write(payload, start, data)
        except Exception:
            pass

    def _parse_setup_comm(self, payload: bytes, start: int, data: S7PacketData) -> None:
        """Parse Setup Communication parameters."""
        try:
            if len(payload) >= start + 8:
                data.max_amq_calling = struct.unpack(">H", payload[start + 2:start + 4])[0]
                data.max_amq_called = struct.unpack(">H", payload[start + 4:start + 6])[0]
                data.pdu_size = struct.unpack(">H", payload[start + 6:start + 8])[0]
        except Exception:
            pass

    def _parse_read_write(self, payload: bytes, start: int, data: S7PacketData) -> None:
        """Parse Read/Write Variable items."""
        try:
            if len(payload) < start + 2:
                return

            data.item_count = payload[start + 1]
            pos = start + 2

            for _ in range(data.item_count):
                if pos + 12 > len(payload):
                    break

                # Parse item specification
                spec_type = payload[pos]
                if spec_type != 0x12:  # Variable specification
                    break

                spec_len = payload[pos + 1]
                syntax_id = payload[pos + 2]

                if syntax_id != 0x10:  # S7ANY
                    pos += 2 + spec_len
                    continue

                transport_size = payload[pos + 3]
                length = struct.unpack(">H", payload[pos + 4:pos + 6])[0]
                db_number = struct.unpack(">H", payload[pos + 6:pos + 8])[0]
                area = payload[pos + 8]

                # Address is 3 bytes
                address = (payload[pos + 9] << 16) | (payload[pos + 10] << 8) | payload[pos + 11]

                item = {
                    "area": area,
                    "area_name": S7_AREA.get(area, f"area_{area}"),
                    "db_number": db_number,
                    "start": address,
                    "size": length,
                    "transport_size": transport_size,
                }

                if data.function_code == 0x04:
                    data.read_items.append(item)
                else:
                    data.write_items.append(item)

                pos += 2 + spec_len
        except Exception:
            pass

    def build_patterns(self, packets: list[ExtractedPacketInfo] = None) -> dict[str, Any]:
        """Build learned patterns from extracted data."""
        total_samples = len(self.packets)
        if total_samples == 0:
            return {}

        # Function code distribution
        total_fc = sum(self.function_counts.values())
        function_codes = {}
        for fc, count in self.function_counts.items():
            fc_name = S7_FUNCTION.get(fc, f"func_{fc:02x}")
            function_codes[fc] = {
                "name": fc_name,
                "count": count,
                "frequency": count / total_fc if total_fc > 0 else 0,
            }

        # Memory area patterns
        address_patterns = {}
        for area_name, accesses in self.area_accesses.items():
            if not accesses:
                continue

            starts = [a["start"] for a in accesses]
            address_patterns[area_name] = {
                "total_accesses": len(accesses),
                "read_count": sum(1 for a in accesses if a["access_type"] == "read"),
                "write_count": sum(1 for a in accesses if a["access_type"] == "write"),
                "min_address": min(starts) if starts else 0,
                "max_address": max(starts) if starts else 0,
            }

        # DB access patterns
        db_patterns = {}
        for db_num, accesses in self.db_accesses.items():
            if not accesses:
                continue

            starts = [a["start"] for a in accesses]
            db_patterns[db_num] = {
                "total_accesses": len(accesses),
                "offset_min": min(starts) if starts else 0,
                "offset_max": max(starts) if starts else 0,
                "unique_offsets": len(set(starts)),
            }

        # PDU sizes
        pdu_stats = {}
        if self.pdu_sizes:
            pdu_stats = {
                "min": min(self.pdu_sizes),
                "max": max(self.pdu_sizes),
                "common": max(set(self.pdu_sizes), key=self.pdu_sizes.count),
            }

        # Rack/slot configurations
        rack_slot_stats = {}
        if self.rack_slot_configs:
            from collections import Counter

            counter = Counter(self.rack_slot_configs)
            rack_slot_stats = {
                f"rack{r}_slot{s}": count
                for (r, s), count in counter.most_common(5)
            }

        # Connection types
        conn_type_distribution = dict(self.connection_types)

        # Error patterns
        error_patterns = {}
        if self.error_counts:
            for (err_class, err_code), count in self.error_counts.items():
                error_patterns[f"{err_class}_{err_code}"] = {
                    "error_class": err_class,
                    "error_code": err_code,
                    "count": count,
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
                "db_access_patterns": db_patterns,
                "pdu_sizes": pdu_stats,
                "rack_slot_configs": rack_slot_stats,
                "connection_types": conn_type_distribution,
                "unique_functions": len(self.function_counts),
            },
            "exception_patterns": error_patterns if error_patterns else None,
        }
