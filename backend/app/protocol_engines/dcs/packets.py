"""DCS (Distributed Control System) packet building utilities.

Supports multiple DCS vendors with their proprietary protocols:
- Emerson DeltaV: UDP 18507
- Honeywell Experion: CDA protocol (proprietary)
- Yokogawa CENTUM VP: Vnet/IP on UDP 230
- ABB 800xA: Uses MMS on TCP 102 (see IEC 61850)
- Schneider Triconex: TriStation protocol

Note: These are proprietary protocols with limited public documentation.
This implementation creates realistic simulated traffic based on known
port patterns, timing characteristics, and security research.
"""

import struct
import random
import os
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


# =============================================================================
# DCS Vendor Constants
# =============================================================================

class DCSVendor(IntEnum):
    """Supported DCS vendors."""
    EMERSON_DELTAV = 1
    HONEYWELL_EXPERION = 2
    YOKOGAWA_CENTUM = 3
    ABB_800XA = 4
    SCHNEIDER_TRICONEX = 5
    SIEMENS_PCS7 = 6  # Uses S7comm - redirect to S7 engine


# =============================================================================
# Emerson DeltaV Constants
# =============================================================================

DELTAV_UDP_PORT = 18507
DELTAV_PROPLUS_PORT_BASE = 18500

class DeltaVMessageType(IntEnum):
    """DeltaV message types (simulated)."""
    HEARTBEAT = 0x01
    STATUS_REQUEST = 0x02
    STATUS_RESPONSE = 0x03
    DATA_REQUEST = 0x04
    DATA_RESPONSE = 0x05
    ALARM_NOTIFICATION = 0x06
    CONFIG_REQUEST = 0x07
    CONFIG_RESPONSE = 0x08


# =============================================================================
# Honeywell Experion CDA Constants
# =============================================================================

EXPERION_CDA_PORT = 51000  # Common CDA port (varies by installation)
EXPERION_FTE_PORT = 18000  # Fault Tolerant Ethernet

class ExperionMessageType(IntEnum):
    """Honeywell Experion CDA message types (based on security research)."""
    CONNECT = 0x01
    CONNECT_ACK = 0x02
    DATA_READ = 0x10
    DATA_WRITE = 0x11
    DATA_RESPONSE = 0x12
    STATUS_REQUEST = 0x20
    STATUS_RESPONSE = 0x21
    ALARM_SUBSCRIBE = 0x30
    ALARM_NOTIFY = 0x31
    KEEPALIVE = 0x40
    KEEPALIVE_ACK = 0x41


# =============================================================================
# Yokogawa CENTUM VP Vnet/IP Constants
# =============================================================================

VNETIP_UDP_PORT = 230
VNETIP_MACROCYCLE_MS = 100  # 100ms macrocycle
VNETIP_SLOT_MS = 1          # 1ms time slots

class VnetIPMessageType(IntEnum):
    """Yokogawa Vnet/IP message types (simulated)."""
    CYCLIC_DATA = 0x01
    ACYCLIC_REQUEST = 0x02
    ACYCLIC_RESPONSE = 0x03
    ALARM = 0x04
    TIME_SYNC = 0x05
    DIAGNOSTICS = 0x06
    REDUNDANCY_SWITCH = 0x07


class VnetIPBus(IntEnum):
    """Vnet/IP dual-bus identifiers."""
    BUS_1 = 1
    BUS_2 = 2


# =============================================================================
# Schneider Triconex Constants
# =============================================================================

TRICONEX_UDP_PORT = 1502
TRICONEX_TCP_PORT = 1502

class TriconexMessageType(IntEnum):
    """Triconex TriStation message types (based on security research)."""
    CONNECT = 0x01
    DISCONNECT = 0x02
    EXECUTION_COMMAND = 0x05
    UPLOAD_PROGRAM = 0x10
    DOWNLOAD_PROGRAM = 0x11
    ALLOCATE_MEMORY = 0x20
    READ_MEMORY = 0x21
    WRITE_MEMORY = 0x22
    GET_STATUS = 0x30
    GET_CP_STATUS = 0x31


# =============================================================================
# Common DCS Data Structures
# =============================================================================

@dataclass
class DCSTag:
    """DCS process tag/point."""
    name: str
    value: float = 0.0
    quality: int = 192  # Good quality
    timestamp: float = 0.0
    unit: str = ""
    alarm_state: int = 0  # 0=normal, 1=low, 2=high, 3=alarm

    def pack(self) -> bytes:
        """Pack tag data."""
        name_bytes = self.name.encode("utf-8")[:32].ljust(32, b"\x00")
        return (
            name_bytes +
            struct.pack("<fBdBB",
                self.value,
                self.quality,
                self.timestamp,
                len(self.unit),
                self.alarm_state,
            ) +
            self.unit.encode("utf-8")[:8].ljust(8, b"\x00")
        )


@dataclass
class DCSAlarm:
    """DCS alarm/event."""
    tag_name: str
    alarm_type: int  # 1=Process, 2=System, 3=Safety
    priority: int    # 1=Critical, 2=High, 3=Medium, 4=Low
    state: int       # 0=Cleared, 1=Active, 2=Acknowledged
    message: str
    timestamp: float

    def pack(self) -> bytes:
        """Pack alarm data."""
        tag_bytes = self.tag_name.encode("utf-8")[:32].ljust(32, b"\x00")
        msg_bytes = self.message.encode("utf-8")[:64].ljust(64, b"\x00")
        return (
            tag_bytes +
            struct.pack("<BBBd", self.alarm_type, self.priority, self.state, self.timestamp) +
            msg_bytes
        )


@dataclass
class DCSController:
    """DCS controller status."""
    node_id: int
    name: str
    state: int  # 0=Offline, 1=Running, 2=Standby, 3=Fault
    cpu_load: int  # 0-100%
    memory_used: int  # 0-100%
    redundancy_state: int  # 0=Simplex, 1=Primary, 2=Backup
    io_scan_time_ms: float
    last_sync_time: float

    def pack(self) -> bytes:
        """Pack controller status."""
        name_bytes = self.name.encode("utf-8")[:16].ljust(16, b"\x00")
        return struct.pack(
            "<H16sBBBBfd",
            self.node_id,
            name_bytes,
            self.state,
            self.cpu_load,
            self.memory_used,
            self.redundancy_state,
            self.io_scan_time_ms,
            self.last_sync_time,
        )


# =============================================================================
# Emerson DeltaV Packet Builders
# =============================================================================

def build_deltav_header(
    message_type: int,
    sequence: int,
    payload_length: int,
    node_id: int = 0,
) -> bytes:
    """Build DeltaV message header (simulated).

    Args:
        message_type: DeltaV message type
        sequence: Sequence number
        payload_length: Length of payload data
        node_id: Source/destination node

    Returns:
        Header bytes
    """
    magic = b"DV"  # DeltaV identifier
    version = 0x02
    flags = 0x00

    return (
        magic +
        struct.pack("<BBHIH",
            version,
            message_type,
            sequence,
            payload_length,
            node_id,
        )
    )


def build_deltav_heartbeat(sequence: int, node_id: int) -> bytes:
    """Build DeltaV heartbeat message."""
    timestamp = time.time()
    payload = struct.pack("<dI", timestamp, 0)  # timestamp + status flags
    header = build_deltav_header(
        DeltaVMessageType.HEARTBEAT, sequence, len(payload), node_id
    )
    return header + payload


def build_deltav_status_request(sequence: int, node_id: int) -> bytes:
    """Build DeltaV status request."""
    payload = struct.pack("<H", node_id)
    header = build_deltav_header(
        DeltaVMessageType.STATUS_REQUEST, sequence, len(payload), node_id
    )
    return header + payload


def build_deltav_status_response(
    sequence: int,
    node_id: int,
    controller: DCSController,
) -> bytes:
    """Build DeltaV status response."""
    payload = controller.pack()
    header = build_deltav_header(
        DeltaVMessageType.STATUS_RESPONSE, sequence, len(payload), node_id
    )
    return header + payload


def build_deltav_data_request(
    sequence: int,
    node_id: int,
    tag_names: list[str],
) -> bytes:
    """Build DeltaV data read request."""
    payload = struct.pack("<H", len(tag_names))
    for name in tag_names:
        name_bytes = name.encode("utf-8")[:32].ljust(32, b"\x00")
        payload += name_bytes

    header = build_deltav_header(
        DeltaVMessageType.DATA_REQUEST, sequence, len(payload), node_id
    )
    return header + payload


def build_deltav_data_response(
    sequence: int,
    node_id: int,
    tags: list[DCSTag],
) -> bytes:
    """Build DeltaV data response."""
    payload = struct.pack("<H", len(tags))
    for tag in tags:
        payload += tag.pack()

    header = build_deltav_header(
        DeltaVMessageType.DATA_RESPONSE, sequence, len(payload), node_id
    )
    return header + payload


# =============================================================================
# Honeywell Experion CDA Packet Builders
# =============================================================================

def build_experion_header(
    message_type: int,
    sequence: int,
    payload_length: int,
    session_id: int = 0,
) -> bytes:
    """Build Honeywell Experion CDA header (simulated).

    Based on security research of Experion vulnerabilities.
    """
    magic = b"HC"  # Honeywell C300
    version = 0x01
    flags = 0x00

    return (
        magic +
        struct.pack("<BBHIH",
            version,
            message_type,
            sequence,
            payload_length,
            session_id,
        )
    )


def build_experion_connect(sequence: int, client_id: str = "HMI-01") -> bytes:
    """Build Experion CDA connect request."""
    client_bytes = client_id.encode("utf-8")[:32].ljust(32, b"\x00")
    payload = client_bytes + struct.pack("<I", 0)  # capabilities
    header = build_experion_header(
        ExperionMessageType.CONNECT, sequence, len(payload)
    )
    return header + payload


def build_experion_connect_ack(sequence: int, session_id: int) -> bytes:
    """Build Experion CDA connect acknowledgment."""
    payload = struct.pack("<IH", session_id, 0)  # session_id + status
    header = build_experion_header(
        ExperionMessageType.CONNECT_ACK, sequence, len(payload), session_id
    )
    return header + payload


def build_experion_status_request(sequence: int, session_id: int) -> bytes:
    """Build Experion status request."""
    payload = struct.pack("<H", 0)  # request flags
    header = build_experion_header(
        ExperionMessageType.STATUS_REQUEST, sequence, len(payload), session_id
    )
    return header + payload


def build_experion_status_response(
    sequence: int,
    session_id: int,
    controller: DCSController,
) -> bytes:
    """Build Experion status response."""
    payload = controller.pack()
    header = build_experion_header(
        ExperionMessageType.STATUS_RESPONSE, sequence, len(payload), session_id
    )
    return header + payload


def build_experion_keepalive(sequence: int, session_id: int) -> bytes:
    """Build Experion keepalive message."""
    timestamp = time.time()
    payload = struct.pack("<d", timestamp)
    header = build_experion_header(
        ExperionMessageType.KEEPALIVE, sequence, len(payload), session_id
    )
    return header + payload


def build_experion_keepalive_ack(sequence: int, session_id: int) -> bytes:
    """Build Experion keepalive acknowledgment."""
    timestamp = time.time()
    payload = struct.pack("<d", timestamp)
    header = build_experion_header(
        ExperionMessageType.KEEPALIVE_ACK, sequence, len(payload), session_id
    )
    return header + payload


# =============================================================================
# Yokogawa CENTUM VP Vnet/IP Packet Builders
# =============================================================================

def build_vnetip_header(
    message_type: int,
    sequence: int,
    payload_length: int,
    station_id: int = 0,
    bus: int = VnetIPBus.BUS_1,
    slot: int = 0,
) -> bytes:
    """Build Yokogawa Vnet/IP header.

    Vnet/IP uses deterministic timing with 100ms macrocycles
    and 1ms time slots.
    """
    magic = b"YV"  # Yokogawa Vnet
    version = 0x01
    flags = 0x00

    return (
        magic +
        struct.pack("<BBHIHBB",
            version,
            message_type,
            sequence,
            payload_length,
            station_id,
            bus,
            slot,
        )
    )


def build_vnetip_cyclic_data(
    sequence: int,
    station_id: int,
    tags: list[DCSTag],
    bus: int = VnetIPBus.BUS_1,
) -> bytes:
    """Build Vnet/IP cyclic data exchange."""
    payload = struct.pack("<H", len(tags))
    for tag in tags:
        payload += tag.pack()

    # Calculate slot based on sequence
    slot = (sequence % 100)  # 100 slots per macrocycle

    header = build_vnetip_header(
        VnetIPMessageType.CYCLIC_DATA, sequence, len(payload), station_id, bus, slot
    )
    return header + payload


def build_vnetip_time_sync(
    sequence: int,
    station_id: int,
    master_time: float,
) -> bytes:
    """Build Vnet/IP time synchronization message."""
    payload = struct.pack("<dI", master_time, 0)  # timestamp + flags
    header = build_vnetip_header(
        VnetIPMessageType.TIME_SYNC, sequence, len(payload), station_id
    )
    return header + payload


def build_vnetip_alarm(
    sequence: int,
    station_id: int,
    alarm: DCSAlarm,
) -> bytes:
    """Build Vnet/IP alarm notification."""
    payload = alarm.pack()
    header = build_vnetip_header(
        VnetIPMessageType.ALARM, sequence, len(payload), station_id
    )
    return header + payload


def build_vnetip_redundancy_switch(
    sequence: int,
    station_id: int,
    new_primary_bus: int,
) -> bytes:
    """Build Vnet/IP redundancy switch notification."""
    payload = struct.pack("<Bd", new_primary_bus, time.time())
    header = build_vnetip_header(
        VnetIPMessageType.REDUNDANCY_SWITCH, sequence, len(payload), station_id
    )
    return header + payload


# =============================================================================
# Schneider Triconex Packet Builders
# =============================================================================

def build_triconex_header(
    message_type: int,
    sequence: int,
    payload_length: int,
    unit_id: int = 1,
) -> bytes:
    """Build Triconex TriStation header (simulated).

    Based on TRITON/TRISIS malware analysis and security research.
    """
    magic = b"TS"  # TriStation
    version = 0x01
    flags = 0x00

    return (
        magic +
        struct.pack("<BBHIH",
            version,
            message_type,
            sequence,
            payload_length,
            unit_id,
        )
    )


def build_triconex_connect(sequence: int, unit_id: int = 1) -> bytes:
    """Build Triconex connect request."""
    payload = struct.pack("<IH", 0, 0)  # client_id + flags
    header = build_triconex_header(
        TriconexMessageType.CONNECT, sequence, len(payload), unit_id
    )
    return header + payload


def build_triconex_status_request(sequence: int, unit_id: int) -> bytes:
    """Build Triconex status request."""
    payload = struct.pack("<H", 0)
    header = build_triconex_header(
        TriconexMessageType.GET_STATUS, sequence, len(payload), unit_id
    )
    return header + payload


def build_triconex_status_response(
    sequence: int,
    unit_id: int,
    run_state: int = 1,
    key_state: int = 2,  # RUN position
    mp_count: int = 3,   # Main Processors
) -> bytes:
    """Build Triconex status response."""
    # Triconex uses Triple Modular Redundancy (TMR)
    payload = struct.pack("<BBBHH",
        run_state,      # 0=Halt, 1=Run
        key_state,      # 0=Stop, 1=Program, 2=Run
        mp_count,       # Number of MPs (typically 3)
        0,              # Fault flags
        0,              # Reserved
    )
    header = build_triconex_header(
        TriconexMessageType.GET_STATUS + 0x80, sequence, len(payload), unit_id
    )
    return header + payload


# =============================================================================
# Common UDP/TCP Frame Builders
# =============================================================================

def build_udp_packet(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    payload: bytes,
    ttl: int = 64,
) -> bytes:
    """Build UDP packet with Ethernet/IP headers."""
    def mac_to_bytes(mac: str) -> bytes:
        return bytes.fromhex(mac.replace(":", "").replace("-", ""))

    def ip_to_bytes(ip: str) -> bytes:
        return bytes([int(x) for x in ip.split(".")])

    # Ethernet header
    eth_header = mac_to_bytes(dst_mac) + mac_to_bytes(src_mac) + b"\x08\x00"

    # IP header
    ip_version_ihl = 0x45
    ip_total_len = 20 + 8 + len(payload)
    ip_id = random.randint(0, 65535)
    ip_flags_frag = 0x4000
    ip_proto = 17  # UDP

    ip_header_no_checksum = struct.pack(
        "!BBHHHBBH4s4s",
        ip_version_ihl, 0, ip_total_len,
        ip_id, ip_flags_frag,
        ttl, ip_proto, 0,
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip)
    )

    # IP checksum
    checksum = 0
    for i in range(0, len(ip_header_no_checksum), 2):
        checksum += int.from_bytes(ip_header_no_checksum[i:i+2], "big")
    while checksum > 0xFFFF:
        checksum = (checksum & 0xFFFF) + (checksum >> 16)
    ip_checksum = (~checksum) & 0xFFFF

    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        ip_version_ihl, 0, ip_total_len,
        ip_id, ip_flags_frag,
        ttl, ip_proto, ip_checksum,
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip)
    )

    # UDP header
    udp_length = 8 + len(payload)
    udp_header = struct.pack("!HHHH", src_port, dst_port, udp_length, 0)

    return eth_header + ip_header + udp_header + payload


# =============================================================================
# DCS Vendor Configuration
# =============================================================================

DCS_VENDOR_CONFIG = {
    DCSVendor.EMERSON_DELTAV: {
        "name": "Emerson DeltaV",
        "port": DELTAV_UDP_PORT,
        "protocol": "udp",
        "poll_interval_ms": 500,
        "models": ["DeltaV M-series", "DeltaV S-series", "DeltaV SIS"],
    },
    DCSVendor.HONEYWELL_EXPERION: {
        "name": "Honeywell Experion",
        "port": EXPERION_CDA_PORT,
        "protocol": "tcp",
        "poll_interval_ms": 250,
        "models": ["Experion PKS", "Experion LX", "C300"],
    },
    DCSVendor.YOKOGAWA_CENTUM: {
        "name": "Yokogawa CENTUM VP",
        "port": VNETIP_UDP_PORT,
        "protocol": "udp",
        "poll_interval_ms": 100,  # Vnet/IP macrocycle
        "models": ["CENTUM VP", "CENTUM VP R6", "ProSafe-RS"],
    },
    DCSVendor.ABB_800XA: {
        "name": "ABB System 800xA",
        "port": 102,  # MMS port
        "protocol": "tcp",
        "poll_interval_ms": 500,
        "models": ["800xA", "AC 800M", "AC 800F"],
    },
    DCSVendor.SCHNEIDER_TRICONEX: {
        "name": "Schneider Triconex",
        "port": TRICONEX_UDP_PORT,
        "protocol": "udp",
        "poll_interval_ms": 100,
        "models": ["Tricon CX", "Tricon v11", "Triconex 3008"],
    },
}
