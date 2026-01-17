"""SNMP packet building utilities using Scapy.

Builds SNMP packets for GetRequest, GetResponse, SetRequest, and Traps.
Uses Scapy's built-in SNMP layers for proper ASN.1/BER encoding.
"""

import random
import struct
from typing import Any

from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from scapy.layers.snmp import (
    SNMP,
    SNMPget,
    SNMPnext,
    SNMPset,
    SNMPresponse,
    SNMPbulk,
    SNMPtrapv1,
    SNMPtrapv2,
    SNMPvarbind,
)
from scapy.asn1.asn1 import (
    ASN1_OID,
    ASN1_INTEGER,
    ASN1_STRING,
    ASN1_NULL,
    ASN1_IPADDRESS,
)
from scapy.packet import Raw

from app.protocol_engines.snmp.types import (
    SNMPVersion,
    SNMPOperation,
    VarBind,
    SNMP_AGENT_PORT,
    SNMP_TRAP_PORT,
)
from app.protocol_engines.types import DeviceContext


def build_udp_packet(
    src: DeviceContext,
    dst: DeviceContext,
    payload: bytes,
    src_port: int | None = None,
    dst_port: int | None = None,
) -> bytes:
    """Build a UDP packet with full Ethernet/IP/UDP headers.

    Args:
        src: Source device context
        dst: Destination device context
        payload: UDP payload bytes
        src_port: Source port (default: random ephemeral)
        dst_port: Destination port (default: SNMP_AGENT_PORT)

    Returns:
        Complete packet bytes
    """
    s_port = src_port or random.randint(49152, 65535)
    d_port = dst_port or SNMP_AGENT_PORT

    # Get TTL from fingerprint if available
    ttl = 64
    if hasattr(src, "get_tcp_ttl"):
        ttl = src.get_tcp_ttl()
    elif src.vendor_fingerprint:
        tcp_stack = src.vendor_fingerprint.get("tcp_stack", {})
        ttl = tcp_stack.get("ttl", 64)

    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address, ttl=ttl)
        / UDP(sport=s_port, dport=d_port)
        / Raw(load=payload)
    )

    return bytes(packet)


def _value_to_asn1(value: Any, value_type: str) -> Any:
    """Convert a Python value to Scapy ASN.1 type.

    Args:
        value: Python value to convert
        value_type: Type hint (integer, string, oid, null, etc.)

    Returns:
        Scapy ASN.1 object
    """
    if value_type == "null" or value is None:
        return ASN1_NULL(0)

    if value_type == "integer" or (value_type == "auto" and isinstance(value, int)):
        return ASN1_INTEGER(value)

    if value_type == "string" or (value_type == "auto" and isinstance(value, str)):
        return ASN1_STRING(value)

    if value_type == "oid":
        return ASN1_OID(value)

    if value_type == "ipaddress":
        return ASN1_IPADDRESS(value)

    if value_type == "counter":
        return ASN1_INTEGER(value)  # Scapy uses INTEGER for Counter32

    if value_type == "gauge":
        return ASN1_INTEGER(value)  # Scapy uses INTEGER for Gauge32

    if value_type == "timeticks":
        return ASN1_INTEGER(value)  # TimeTicks as INTEGER

    # Default to string
    return ASN1_STRING(str(value))


def build_snmp_get_request(
    community: str,
    request_id: int,
    oids: list[str],
    version: SNMPVersion = SNMPVersion.V2C,
) -> bytes:
    """Build an SNMP GetRequest PDU.

    Args:
        community: Community string (authentication)
        request_id: Request ID for matching responses
        oids: List of OIDs to request
        version: SNMP version (v1 or v2c)

    Returns:
        SNMP message bytes
    """
    varbinds = [SNMPvarbind(oid=ASN1_OID(oid), value=ASN1_NULL(0)) for oid in oids]

    snmp_pdu = SNMPget(
        id=ASN1_INTEGER(request_id),
        error=ASN1_INTEGER(0),
        error_index=ASN1_INTEGER(0),
        varbindlist=varbinds,
    )

    snmp_msg = SNMP(
        version=ASN1_INTEGER(int(version)),
        community=ASN1_STRING(community),
        PDU=snmp_pdu,
    )

    return bytes(snmp_msg)


def build_snmp_get_next_request(
    community: str,
    request_id: int,
    oids: list[str],
    version: SNMPVersion = SNMPVersion.V2C,
) -> bytes:
    """Build an SNMP GetNextRequest PDU.

    Args:
        community: Community string
        request_id: Request ID
        oids: List of OIDs (get next after these)
        version: SNMP version

    Returns:
        SNMP message bytes
    """
    varbinds = [SNMPvarbind(oid=ASN1_OID(oid), value=ASN1_NULL(0)) for oid in oids]

    snmp_pdu = SNMPnext(
        id=ASN1_INTEGER(request_id),
        error=ASN1_INTEGER(0),
        error_index=ASN1_INTEGER(0),
        varbindlist=varbinds,
    )

    snmp_msg = SNMP(
        version=ASN1_INTEGER(int(version)),
        community=ASN1_STRING(community),
        PDU=snmp_pdu,
    )

    return bytes(snmp_msg)


def build_snmp_get_bulk_request(
    community: str,
    request_id: int,
    oids: list[str],
    non_repeaters: int = 0,
    max_repetitions: int = 10,
) -> bytes:
    """Build an SNMPv2c GetBulkRequest PDU.

    Args:
        community: Community string
        request_id: Request ID
        oids: List of OIDs to bulk-get
        non_repeaters: Number of non-repeating OIDs
        max_repetitions: Max repetitions for repeating OIDs

    Returns:
        SNMP message bytes
    """
    varbinds = [SNMPvarbind(oid=ASN1_OID(oid), value=ASN1_NULL(0)) for oid in oids]

    snmp_pdu = SNMPbulk(
        id=ASN1_INTEGER(request_id),
        non_repeaters=ASN1_INTEGER(non_repeaters),
        max_repetitions=ASN1_INTEGER(max_repetitions),
        varbindlist=varbinds,
    )

    snmp_msg = SNMP(
        version=ASN1_INTEGER(int(SNMPVersion.V2C)),
        community=ASN1_STRING(community),
        PDU=snmp_pdu,
    )

    return bytes(snmp_msg)


def build_snmp_get_response(
    community: str,
    request_id: int,
    varbinds: list[VarBind],
    error_status: int = 0,
    error_index: int = 0,
    version: SNMPVersion = SNMPVersion.V2C,
) -> bytes:
    """Build an SNMP GetResponse PDU.

    Args:
        community: Community string
        request_id: Request ID (must match request)
        varbinds: List of VarBind with OID and value
        error_status: Error status code
        error_index: Index of problematic varbind (1-based)
        version: SNMP version

    Returns:
        SNMP message bytes
    """
    scapy_varbinds = []
    for vb in varbinds:
        asn1_value = _value_to_asn1(vb.value, vb.value_type)
        scapy_varbinds.append(SNMPvarbind(oid=ASN1_OID(vb.oid), value=asn1_value))

    snmp_pdu = SNMPresponse(
        id=ASN1_INTEGER(request_id),
        error=ASN1_INTEGER(error_status),
        error_index=ASN1_INTEGER(error_index),
        varbindlist=scapy_varbinds,
    )

    snmp_msg = SNMP(
        version=ASN1_INTEGER(int(version)),
        community=ASN1_STRING(community),
        PDU=snmp_pdu,
    )

    return bytes(snmp_msg)


def build_snmp_set_request(
    community: str,
    request_id: int,
    varbinds: list[VarBind],
    version: SNMPVersion = SNMPVersion.V2C,
) -> bytes:
    """Build an SNMP SetRequest PDU.

    Args:
        community: Community string (typically write community)
        request_id: Request ID
        varbinds: List of VarBind with OID and value to set
        version: SNMP version

    Returns:
        SNMP message bytes
    """
    scapy_varbinds = []
    for vb in varbinds:
        asn1_value = _value_to_asn1(vb.value, vb.value_type)
        scapy_varbinds.append(SNMPvarbind(oid=ASN1_OID(vb.oid), value=asn1_value))

    snmp_pdu = SNMPset(
        id=ASN1_INTEGER(request_id),
        error=ASN1_INTEGER(0),
        error_index=ASN1_INTEGER(0),
        varbindlist=scapy_varbinds,
    )

    snmp_msg = SNMP(
        version=ASN1_INTEGER(int(version)),
        community=ASN1_STRING(community),
        PDU=snmp_pdu,
    )

    return bytes(snmp_msg)


def build_snmp_trap_v1(
    community: str,
    enterprise_oid: str,
    agent_addr: str,
    generic_trap: int,
    specific_trap: int,
    timestamp: int,
    varbinds: list[VarBind] | None = None,
) -> bytes:
    """Build an SNMPv1 Trap PDU.

    Args:
        community: Community string
        enterprise_oid: Enterprise OID identifying the trap source
        agent_addr: IP address of agent sending trap
        generic_trap: Generic trap type (0-6)
        specific_trap: Specific trap code
        timestamp: System uptime when trap generated (TimeTicks)
        varbinds: Additional variable bindings

    Returns:
        SNMP trap message bytes
    """
    varbinds = varbinds or []
    scapy_varbinds = []
    for vb in varbinds:
        asn1_value = _value_to_asn1(vb.value, vb.value_type)
        scapy_varbinds.append(SNMPvarbind(oid=ASN1_OID(vb.oid), value=asn1_value))

    snmp_pdu = SNMPtrapv1(
        enterprise=ASN1_OID(enterprise_oid),
        agent_addr=ASN1_IPADDRESS(agent_addr),
        generic_trap=ASN1_INTEGER(generic_trap),
        specific_trap=ASN1_INTEGER(specific_trap),
        time_stamp=ASN1_INTEGER(timestamp),
        varbindlist=scapy_varbinds,
    )

    snmp_msg = SNMP(
        version=ASN1_INTEGER(int(SNMPVersion.V1)),
        community=ASN1_STRING(community),
        PDU=snmp_pdu,
    )

    return bytes(snmp_msg)


def build_snmp_trap_v2c(
    community: str,
    request_id: int,
    uptime: int,
    trap_oid: str,
    varbinds: list[VarBind] | None = None,
) -> bytes:
    """Build an SNMPv2c Trap (Notification) PDU.

    SNMPv2c traps have two mandatory varbinds:
    1. sysUpTime.0 (1.3.6.1.2.1.1.3.0)
    2. snmpTrapOID.0 (1.3.6.1.6.3.1.1.4.1.0)

    Args:
        community: Community string
        request_id: Request ID
        uptime: sysUpTime value (TimeTicks)
        trap_oid: Trap OID (snmpTrapOID.0 value)
        varbinds: Additional variable bindings

    Returns:
        SNMPv2c trap message bytes
    """
    varbinds = varbinds or []

    # Mandatory varbinds for SNMPv2c trap
    all_varbinds = [
        VarBind(oid="1.3.6.1.2.1.1.3.0", value=uptime, value_type="timeticks"),
        VarBind(oid="1.3.6.1.6.3.1.1.4.1.0", value=trap_oid, value_type="oid"),
    ] + varbinds

    scapy_varbinds = []
    for vb in all_varbinds:
        asn1_value = _value_to_asn1(vb.value, vb.value_type)
        scapy_varbinds.append(SNMPvarbind(oid=ASN1_OID(vb.oid), value=asn1_value))

    snmp_pdu = SNMPtrapv2(
        id=ASN1_INTEGER(request_id),
        error=ASN1_INTEGER(0),
        error_index=ASN1_INTEGER(0),
        varbindlist=scapy_varbinds,
    )

    snmp_msg = SNMP(
        version=ASN1_INTEGER(int(SNMPVersion.V2C)),
        community=ASN1_STRING(community),
        PDU=snmp_pdu,
    )

    return bytes(snmp_msg)


def build_snmp_get_request_packet(
    src: DeviceContext,
    dst: DeviceContext,
    community: str,
    request_id: int,
    oids: list[str],
    version: SNMPVersion = SNMPVersion.V2C,
) -> bytes:
    """Build complete SNMP GetRequest packet with headers.

    Args:
        src: Source (manager) device
        dst: Destination (agent) device
        community: Community string
        request_id: Request ID
        oids: OIDs to request
        version: SNMP version

    Returns:
        Complete packet bytes
    """
    snmp_payload = build_snmp_get_request(community, request_id, oids, version)
    return build_udp_packet(src, dst, snmp_payload, dst_port=SNMP_AGENT_PORT)


def build_snmp_get_response_packet(
    src: DeviceContext,
    dst: DeviceContext,
    dst_port: int,
    community: str,
    request_id: int,
    varbinds: list[VarBind],
    error_status: int = 0,
    error_index: int = 0,
    version: SNMPVersion = SNMPVersion.V2C,
) -> bytes:
    """Build complete SNMP GetResponse packet with headers.

    Args:
        src: Source (agent) device
        dst: Destination (manager) device
        dst_port: Destination port (manager's source port)
        community: Community string
        request_id: Request ID (must match request)
        varbinds: Variable bindings with values
        error_status: Error status code
        error_index: Error index
        version: SNMP version

    Returns:
        Complete packet bytes
    """
    snmp_payload = build_snmp_get_response(
        community, request_id, varbinds, error_status, error_index, version
    )
    return build_udp_packet(
        src, dst, snmp_payload, src_port=SNMP_AGENT_PORT, dst_port=dst_port
    )


def build_snmp_trap_packet(
    src: DeviceContext,
    dst: DeviceContext,
    community: str,
    trap_oid: str,
    uptime: int,
    request_id: int | None = None,
    varbinds: list[VarBind] | None = None,
    version: SNMPVersion = SNMPVersion.V2C,
    enterprise_oid: str | None = None,
    generic_trap: int = 6,
    specific_trap: int = 1,
) -> bytes:
    """Build complete SNMP Trap packet with headers.

    Args:
        src: Source (agent) device
        dst: Destination (trap receiver)
        community: Community string
        trap_oid: Trap OID (for v2c)
        uptime: System uptime in hundredths of seconds
        request_id: Request ID (for v2c, auto-generated if None)
        varbinds: Additional variable bindings
        version: SNMP version
        enterprise_oid: Enterprise OID (for v1)
        generic_trap: Generic trap type (for v1)
        specific_trap: Specific trap code (for v1)

    Returns:
        Complete packet bytes
    """
    if version == SNMPVersion.V1:
        snmp_payload = build_snmp_trap_v1(
            community=community,
            enterprise_oid=enterprise_oid or "1.3.6.1.4.1.1206.4.2.1",
            agent_addr=src.ip_address,
            generic_trap=generic_trap,
            specific_trap=specific_trap,
            timestamp=uptime,
            varbinds=varbinds,
        )
    else:
        req_id = request_id or random.randint(1, 65535)
        snmp_payload = build_snmp_trap_v2c(
            community=community,
            request_id=req_id,
            uptime=uptime,
            trap_oid=trap_oid,
            varbinds=varbinds,
        )

    return build_udp_packet(src, dst, snmp_payload, dst_port=SNMP_TRAP_PORT)
