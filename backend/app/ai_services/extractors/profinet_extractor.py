"""PROFINET protocol extractor for deep packet analysis.

Extracts frame types, DCP operations, IO data patterns, and device identities.
PROFINET operates primarily at Layer 2 (EtherType 0x8892) and UDP for DCP.
"""

import logging
import struct
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Packet, Raw

from app.ai_services.extractors.base import (
    ExtractedPacketInfo,
    ProtocolExtractor,
)

logger = logging.getLogger(__name__)

# PROFINET EtherType
PROFINET_ETHERTYPE = 0x8892

# PROFINET Frame IDs
FRAME_ID_RANGES = {
    (0x0000, 0x00FF): "reserved",
    (0x0100, 0x7FFF): "rt_class_3",  # IRT (Isochronous Real-Time)
    (0x8000, 0xBFFF): "rt_class_1",  # RT (Real-Time)
    (0xC000, 0xFBFF): "rt_class_udp",  # RT over UDP
    (0xFC00, 0xFCFF): "reserved_high",
    (0xFD00, 0xFDFF): "fragmentation",
    (0xFE00, 0xFEFC): "time_sync",
    (0xFEFD, 0xFEFD): "dcp_hello",
    (0xFEFE, 0xFEFE): "dcp_get_set",
    (0xFEFF, 0xFEFF): "dcp_identify",
    (0xFF00, 0xFF01): "ptcp",  # Precision Time Control Protocol
    (0xFF02, 0xFF03): "reserved_ptcp",
    (0xFF04, 0xFF05): "reserved_high2",
    (0xFF06, 0xFF07): "reserved_high3",
    (0xFF08, 0xFF7F): "reserved_high4",
    (0xFF80, 0xFF8F): "frag_low",
    (0xFF90, 0xFF9F): "frag_high",
}

# DCP Service IDs
DCP_SERVICE = {
    0x00: "reserved",
    0x03: "get",
    0x04: "set",
    0x05: "identify",
    0x06: "hello",
}

# DCP Service Types
DCP_SERVICE_TYPE = {
    0x00: "request",
    0x01: "response_success",
    0x05: "response_error",
}

# DCP Options
DCP_OPTION = {
    0x01: "ip",
    0x02: "device",
    0x03: "dhcp",
    0x04: "reserved",
    0x05: "control",
    0x06: "device_initiative",
    0xFF: "all",
}

# DCP Sub-options for Device option (0x02)
DCP_DEVICE_SUBOPTION = {
    0x01: "manufacturer_specific",
    0x02: "name_of_station",
    0x03: "device_id",
    0x04: "device_role",
    0x05: "device_options",
    0x06: "alias_name",
    0x07: "device_instance",
    0x08: "oem_device_id",
}

# DCP Sub-options for IP option (0x01)
DCP_IP_SUBOPTION = {
    0x01: "mac_address",
    0x02: "ip_parameter",
    0x03: "full_ip_suite",
}

# PROFINET IO Data Status
IO_STATUS = {
    0x00: "good",
    0x01: "redundancy",
    0x02: "data_valid",
    0x03: "reserved",
    0x04: "run",
    0x05: "station_problem_indicator",
    0x06: "provider_state",
    0x07: "reserved2",
}


@dataclass
class ProfinetPacketData:
    """Parsed PROFINET packet data."""

    # Ethernet layer
    src_mac: str = ""
    dst_mac: str = ""

    # PROFINET Frame
    frame_id: int = 0
    frame_type: str = ""
    is_dcp: bool = False
    is_io: bool = False
    is_alarm: bool = False

    # DCP fields (if DCP)
    dcp_service_id: int | None = None
    dcp_service_name: str = ""
    dcp_service_type: int | None = None
    dcp_service_type_name: str = ""
    dcp_xid: int | None = None
    dcp_response_delay: int | None = None
    dcp_data_length: int | None = None
    dcp_blocks: list[dict] = field(default_factory=list)

    # Device identity (from DCP)
    name_of_station: str | None = None
    vendor_id: int | None = None
    device_id: int | None = None
    device_role: int | None = None
    ip_address: str | None = None
    subnet_mask: str | None = None
    gateway: str | None = None

    # IO Data fields
    io_cycle_counter: int | None = None
    io_data_status: int | None = None
    io_transfer_status: int | None = None
    io_data_length: int = 0

    # Alarm fields
    alarm_type: int | None = None
    alarm_specifier: int | None = None


class ProfinetExtractor(ProtocolExtractor):
    """Extract patterns from PROFINET traffic.

    Analyzes:
    - Frame type distribution (DCP, IO, Alarm)
    - DCP service patterns (Identify, Get, Set)
    - Device identities from DCP responses
    - IO data cycle patterns
    - Alarm patterns
    """

    PROFINET_ETHERTYPE = 0x8892
    PROFINET_DCP_UDP_PORT = 34964  # DCP over UDP

    def __init__(self):
        self.packets: list[ProfinetPacketData] = []
        self.frame_type_counts: dict[str, int] = defaultdict(int)
        self.dcp_service_counts: dict[str, int] = defaultdict(int)
        self.device_identities: dict[str, dict] = {}  # mac -> identity
        self.io_cycles: list[dict] = []
        self.alarm_counts: dict[int, int] = defaultdict(int)
        self.vendor_counts: dict[int, int] = defaultdict(int)
        self.request_counts = 0
        self.response_counts = 0

    @property
    def protocol_name(self) -> str:
        return "profinet"

    @property
    def well_known_ports(self) -> list[int]:
        return [34964]  # DCP over UDP

    def reset(self):
        """Reset extractor state for new analysis."""
        self.packets = []
        self.frame_type_counts = defaultdict(int)
        self.dcp_service_counts = defaultdict(int)
        self.device_identities = {}
        self.io_cycles = []
        self.alarm_counts = defaultdict(int)
        self.vendor_counts = defaultdict(int)
        self.request_counts = 0
        self.response_counts = 0

    def can_handle(self, packet: Packet) -> bool:
        """Check if packet is PROFINET."""
        # Check for Layer 2 PROFINET (EtherType 0x8892)
        if packet.haslayer(Ether):
            if packet[Ether].type == self.PROFINET_ETHERTYPE:
                return True

        # Check for DCP over UDP
        if packet.haslayer(UDP):
            udp = packet[UDP]
            if udp.sport == self.PROFINET_DCP_UDP_PORT or udp.dport == self.PROFINET_DCP_UDP_PORT:
                return True

        return False

    def extract_packet_info(self, packet: Packet) -> ExtractedPacketInfo | None:
        """Extract PROFINET packet information."""
        if not self.can_handle(packet):
            return None

        try:
            parsed = self._parse_profinet_packet(packet)
            if not parsed:
                return None

            self.packets.append(parsed)

            # Track frame types
            self.frame_type_counts[parsed.frame_type] += 1

            # Track DCP services
            if parsed.is_dcp and parsed.dcp_service_name:
                self.dcp_service_counts[parsed.dcp_service_name] += 1

            # Determine direction
            is_request = parsed.dcp_service_type == 0x00  # Request
            if parsed.is_dcp:
                if is_request:
                    self.request_counts += 1
                else:
                    self.response_counts += 1
            elif parsed.is_io:
                # IO frames don't have clear request/response distinction
                self.request_counts += 1

            # Track device identities from DCP responses
            if parsed.is_dcp and parsed.name_of_station:
                identity = {
                    "name_of_station": parsed.name_of_station,
                    "vendor_id": parsed.vendor_id,
                    "device_id": parsed.device_id,
                    "device_role": parsed.device_role,
                    "ip_address": parsed.ip_address,
                }
                self.device_identities[parsed.src_mac] = identity
                if parsed.vendor_id is not None:
                    self.vendor_counts[parsed.vendor_id] += 1

            # Track IO cycles
            if parsed.is_io:
                self.io_cycles.append({
                    "cycle_counter": parsed.io_cycle_counter,
                    "data_status": parsed.io_data_status,
                    "data_length": parsed.io_data_length,
                })

            # Track alarms
            if parsed.is_alarm and parsed.alarm_type is not None:
                self.alarm_counts[parsed.alarm_type] += 1

            # Build return info
            src_ip = ""
            dst_ip = ""
            src_port = 0
            dst_port = 0

            if packet.haslayer(IP):
                src_ip = packet[IP].src
                dst_ip = packet[IP].dst
            if packet.haslayer(UDP):
                src_port = packet[UDP].sport
                dst_port = packet[UDP].dport

            return ExtractedPacketInfo(
                timestamp=float(packet.time),
                src_ip=src_ip or parsed.src_mac,
                dst_ip=dst_ip or parsed.dst_mac,
                src_port=src_port,
                dst_port=dst_port,
                protocol=self.protocol_name,
                direction="request" if is_request else "response",
                function_code=parsed.dcp_service_id or parsed.frame_id,
                payload_size=len(packet),
                metadata={
                    "frame_id": parsed.frame_id,
                    "frame_type": parsed.frame_type,
                    "dcp_service": parsed.dcp_service_name if parsed.is_dcp else None,
                    "name_of_station": parsed.name_of_station,
                    "src_mac": parsed.src_mac,
                    "dst_mac": parsed.dst_mac,
                },
            )
        except Exception as e:
            logger.debug(f"Failed to parse PROFINET packet: {e}")
            return None

    def is_request(self, packet: Packet) -> bool:
        """Check if packet is a PROFINET request."""
        # DCP requests have service type 0x00
        parsed = self._parse_profinet_packet(packet)
        if parsed and parsed.is_dcp:
            return parsed.dcp_service_type == 0x00
        # IO frames are typically from controller to device
        return True

    def extract_identity_info(self, packet: Packet) -> dict | None:
        """Extract device identity from DCP response."""
        if not self.can_handle(packet):
            return None

        parsed = self._parse_profinet_packet(packet)
        if parsed and parsed.is_dcp and parsed.name_of_station:
            return {
                "name_of_station": parsed.name_of_station,
                "vendor_id": parsed.vendor_id,
                "device_id": parsed.device_id,
                "device_role": parsed.device_role,
                "ip_address": parsed.ip_address,
            }
        return None

    def _parse_profinet_packet(self, packet: Packet) -> ProfinetPacketData | None:
        """Parse PROFINET packet into structured data."""
        data = ProfinetPacketData()

        if packet.haslayer(Ether):
            data.src_mac = packet[Ether].src
            data.dst_mac = packet[Ether].dst

        # Check for Layer 2 PROFINET
        if packet.haslayer(Ether) and packet[Ether].type == self.PROFINET_ETHERTYPE:
            payload = bytes(packet[Ether].payload)
            return self._parse_pn_frame(payload, data)

        # Check for DCP over UDP
        if packet.haslayer(UDP) and packet.haslayer(Raw):
            udp = packet[UDP]
            if udp.sport == self.PROFINET_DCP_UDP_PORT or udp.dport == self.PROFINET_DCP_UDP_PORT:
                payload = bytes(packet[Raw].load)
                return self._parse_dcp(payload, 0, data)

        return None

    def _parse_pn_frame(self, payload: bytes, data: ProfinetPacketData) -> ProfinetPacketData | None:
        """Parse PROFINET Layer 2 frame."""
        if len(payload) < 2:
            return None

        # Frame ID is first 2 bytes
        data.frame_id = struct.unpack(">H", payload[0:2])[0]

        # Determine frame type based on Frame ID
        data.frame_type = self._get_frame_type(data.frame_id)

        # Parse based on frame type
        if data.frame_id in [0xFEFD, 0xFEFE, 0xFEFF]:  # DCP frames
            data.is_dcp = True
            self._parse_dcp(payload, 2, data)
        elif 0x8000 <= data.frame_id <= 0xBFFF:  # RT Class 1 (IO)
            data.is_io = True
            self._parse_io_data(payload, 2, data)
        elif 0x0100 <= data.frame_id <= 0x7FFF:  # IRT
            data.is_io = True
            self._parse_io_data(payload, 2, data)
        elif 0xFC01 <= data.frame_id <= 0xFCFF:  # Alarm
            data.is_alarm = True
            self._parse_alarm(payload, 2, data)

        return data

    def _get_frame_type(self, frame_id: int) -> str:
        """Get frame type string from frame ID."""
        for (start, end), frame_type in FRAME_ID_RANGES.items():
            if start <= frame_id <= end:
                return frame_type
        return f"unknown_{frame_id:04x}"

    def _parse_dcp(self, payload: bytes, start: int, data: ProfinetPacketData) -> ProfinetPacketData:
        """Parse DCP (Discovery and Configuration Protocol) data."""
        try:
            if len(payload) < start + 10:
                return data

            # DCP header
            data.dcp_service_id = payload[start]
            data.dcp_service_name = DCP_SERVICE.get(data.dcp_service_id, f"service_{data.dcp_service_id}")
            data.dcp_service_type = payload[start + 1]
            data.dcp_service_type_name = DCP_SERVICE_TYPE.get(data.dcp_service_type, f"type_{data.dcp_service_type}")
            data.dcp_xid = struct.unpack(">I", payload[start + 2:start + 6])[0]
            data.dcp_response_delay = struct.unpack(">H", payload[start + 6:start + 8])[0]
            data.dcp_data_length = struct.unpack(">H", payload[start + 8:start + 10])[0]

            # Parse DCP blocks
            pos = start + 10
            end = start + 10 + data.dcp_data_length

            while pos < end and pos + 4 <= len(payload):
                option = payload[pos]
                suboption = payload[pos + 1]
                block_length = struct.unpack(">H", payload[pos + 2:pos + 4])[0]

                block_data = payload[pos + 4:pos + 4 + block_length] if pos + 4 + block_length <= len(payload) else b""

                self._process_dcp_block(option, suboption, block_data, data)

                # Blocks are padded to even length
                pos += 4 + block_length
                if block_length % 2 != 0:
                    pos += 1

        except Exception:
            pass

        return data

    def _process_dcp_block(self, option: int, suboption: int, block_data: bytes, data: ProfinetPacketData) -> None:
        """Process a DCP block and extract identity information."""
        try:
            if option == 0x02:  # Device option
                if suboption == 0x02:  # Name of Station
                    # Skip block info (2 bytes) at start
                    if len(block_data) >= 2:
                        data.name_of_station = block_data[2:].decode("ascii", errors="ignore").strip("\x00")
                elif suboption == 0x03:  # Device ID
                    if len(block_data) >= 6:
                        data.vendor_id = struct.unpack(">H", block_data[2:4])[0]
                        data.device_id = struct.unpack(">H", block_data[4:6])[0]
                elif suboption == 0x04:  # Device Role
                    if len(block_data) >= 3:
                        data.device_role = block_data[2]

            elif option == 0x01:  # IP option
                if suboption == 0x02:  # IP Parameter
                    if len(block_data) >= 14:
                        # Skip block info (2 bytes)
                        ip_bytes = block_data[2:6]
                        mask_bytes = block_data[6:10]
                        gw_bytes = block_data[10:14]
                        data.ip_address = ".".join(str(b) for b in ip_bytes)
                        data.subnet_mask = ".".join(str(b) for b in mask_bytes)
                        data.gateway = ".".join(str(b) for b in gw_bytes)

            block = {
                "option": DCP_OPTION.get(option, f"opt_{option}"),
                "suboption": suboption,
                "length": len(block_data),
            }
            data.dcp_blocks.append(block)

        except Exception:
            pass

    def _parse_io_data(self, payload: bytes, start: int, data: ProfinetPacketData) -> None:
        """Parse PROFINET IO data frame."""
        try:
            if len(payload) < start + 4:
                return

            # IO data starts after frame ID
            # Last 4 bytes are cycle counter (2) + data status (1) + transfer status (1)
            data.io_data_length = len(payload) - start - 4

            if data.io_data_length > 0 and len(payload) >= start + data.io_data_length + 4:
                status_start = start + data.io_data_length
                data.io_cycle_counter = struct.unpack(">H", payload[status_start:status_start + 2])[0]
                data.io_data_status = payload[status_start + 2]
                data.io_transfer_status = payload[status_start + 3]
        except Exception:
            pass

    def _parse_alarm(self, payload: bytes, start: int, data: ProfinetPacketData) -> None:
        """Parse PROFINET Alarm frame."""
        try:
            if len(payload) < start + 4:
                return

            # Alarm header
            data.alarm_type = struct.unpack(">H", payload[start:start + 2])[0]
            data.alarm_specifier = struct.unpack(">H", payload[start + 2:start + 4])[0]
        except Exception:
            pass

    def build_patterns(self, packets: list[ExtractedPacketInfo] = None) -> dict[str, Any]:
        """Build learned patterns from extracted data."""
        total_samples = len(self.packets)
        if total_samples == 0:
            return {}

        # Frame type distribution
        total_frames = sum(self.frame_type_counts.values())
        frame_distribution = {}
        for frame_type, count in self.frame_type_counts.items():
            frame_distribution[frame_type] = {
                "count": count,
                "frequency": count / total_frames if total_frames > 0 else 0,
            }

        # DCP service distribution (as function codes)
        total_dcp = sum(self.dcp_service_counts.values())
        function_codes = {}
        for service, count in self.dcp_service_counts.items():
            function_codes[service] = {
                "name": service,
                "count": count,
                "frequency": count / total_dcp if total_dcp > 0 else 0,
            }

        # IO cycle patterns
        io_patterns = {}
        if self.io_cycles:
            cycle_counters = [c["cycle_counter"] for c in self.io_cycles if c["cycle_counter"] is not None]
            data_lengths = [c["data_length"] for c in self.io_cycles]

            io_patterns = {
                "total_io_frames": len(self.io_cycles),
                "data_length_min": min(data_lengths) if data_lengths else 0,
                "data_length_max": max(data_lengths) if data_lengths else 0,
                "unique_cycle_counters": len(set(cycle_counters)) if cycle_counters else 0,
            }

            # Calculate cycle time if we have enough samples
            if len(cycle_counters) > 1:
                # Cycle counter increments each cycle
                # Difference should give us cycle count
                sorted_counters = sorted(cycle_counters)
                diffs = [sorted_counters[i + 1] - sorted_counters[i] for i in range(len(sorted_counters) - 1)]
                if diffs:
                    io_patterns["avg_cycle_increment"] = sum(diffs) / len(diffs)

        # Alarm patterns
        alarm_distribution = {}
        if self.alarm_counts:
            total_alarms = sum(self.alarm_counts.values())
            for alarm_type, count in self.alarm_counts.items():
                alarm_distribution[alarm_type] = {
                    "count": count,
                    "frequency": count / total_alarms if total_alarms > 0 else 0,
                }

        # Vendor distribution
        vendor_distribution = dict(self.vendor_counts)

        confidence = self.calculate_confidence(total_samples)

        return {
            "protocol": self.protocol_name,
            "function_codes": function_codes,
            "address_patterns": {},  # PROFINET doesn't have traditional addressing
            "sample_count": total_samples,
            "request_count": self.request_counts,
            "response_count": self.response_counts,
            "confidence": confidence,
            "protocol_metadata": {
                "frame_distribution": frame_distribution,
                "io_patterns": io_patterns,
                "alarm_distribution": alarm_distribution if alarm_distribution else None,
                "vendor_distribution": vendor_distribution,
                "device_identities": self.device_identities if self.device_identities else None,
                "unique_dcp_services": len(self.dcp_service_counts),
            },
            "exception_patterns": None,
            "device_identities": list(self.device_identities.values()) if self.device_identities else None,
        }
