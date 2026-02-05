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
    SNMPv3Credentials,
    SNMPv3SecurityLevel,
    SNMPv3AuthProtocol,
    SNMPv3PrivProtocol,
)
from app.protocol_engines.types import DeviceContext


def build_udp_packet_raw(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    payload: bytes,
    src_port: int | None = None,
    dst_port: int | None = None,
    ttl: int = 64,
) -> bytes:
    """Build a UDP packet with full Ethernet/IP/UDP headers using raw parameters.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        src_ip: Source IP address
        dst_ip: Destination IP address
        payload: UDP payload bytes
        src_port: Source port (default: random ephemeral)
        dst_port: Destination port (default: SNMP_AGENT_PORT)
        ttl: IP TTL value (default: 64)

    Returns:
        Complete packet bytes
    """
    s_port = src_port or random.randint(49152, 65535)
    d_port = dst_port or SNMP_AGENT_PORT

    packet = (
        Ether(src=src_mac, dst=dst_mac)
        / IP(src=src_ip, dst=dst_ip, ttl=ttl)
        / UDP(sport=s_port, dport=d_port)
        / Raw(load=payload)
    )

    return bytes(packet)


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
    # Get TTL from fingerprint if available
    ttl = 64
    if hasattr(src, "get_tcp_ttl"):
        ttl = src.get_tcp_ttl()
    elif src.vendor_fingerprint:
        tcp_stack = src.vendor_fingerprint.get("tcp_stack", {})
        ttl = tcp_stack.get("ttl", 64)

    return build_udp_packet_raw(
        src_mac=src.mac_address,
        dst_mac=dst.mac_address,
        src_ip=src.ip_address,
        dst_ip=dst.ip_address,
        payload=payload,
        src_port=src_port,
        dst_port=dst_port,
        ttl=ttl,
    )


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
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    community: str,
    request_id: int,
    oids: list[str],
    version: SNMPVersion = SNMPVersion.V2C,
    ttl: int = 64,
) -> bytes:
    """Build complete SNMP GetRequest packet with headers.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_port: Source UDP port
        dst_port: Destination UDP port (typically SNMP_AGENT_PORT)
        community: Community string
        request_id: Request ID
        oids: OIDs to request
        version: SNMP version
        ttl: IP TTL value

    Returns:
        Complete packet bytes
    """
    snmp_payload = build_snmp_get_request(community, request_id, oids, version)
    return build_udp_packet_raw(
        src_mac=src_mac,
        dst_mac=dst_mac,
        src_ip=src_ip,
        dst_ip=dst_ip,
        payload=snmp_payload,
        src_port=src_port,
        dst_port=dst_port,
        ttl=ttl,
    )


def build_snmp_get_response_packet(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    community: str,
    request_id: int,
    var_binds: list[VarBind],
    error_status: int = 0,
    error_index: int = 0,
    version: SNMPVersion = SNMPVersion.V2C,
    ttl: int = 64,
) -> bytes:
    """Build complete SNMP GetResponse packet with headers.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_port: Source UDP port (typically SNMP_AGENT_PORT)
        dst_port: Destination UDP port (manager's source port)
        community: Community string
        request_id: Request ID (must match request)
        var_binds: Variable bindings with values
        error_status: Error status code
        error_index: Error index
        version: SNMP version
        ttl: IP TTL value

    Returns:
        Complete packet bytes
    """
    snmp_payload = build_snmp_get_response(
        community, request_id, var_binds, error_status, error_index, version
    )
    return build_udp_packet_raw(
        src_mac=src_mac,
        dst_mac=dst_mac,
        src_ip=src_ip,
        dst_ip=dst_ip,
        payload=snmp_payload,
        src_port=src_port,
        dst_port=dst_port,
        ttl=ttl,
    )


def build_snmp_trap_packet(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    community: str,
    trap_type: str,
    enterprise_oid: str,
    uptime_ticks: int,
    var_binds: list[VarBind] | None = None,
    version: SNMPVersion = SNMPVersion.V2C,
    request_id: int | None = None,
    generic_trap: int = 6,
    specific_trap: int = 1,
    ttl: int = 64,
) -> bytes:
    """Build complete SNMP Trap packet with headers.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        src_ip: Source IP address (agent)
        dst_ip: Destination IP address (trap receiver)
        community: Community string
        trap_type: Trap type identifier (used as trap_oid for v2c)
        enterprise_oid: Enterprise OID
        uptime_ticks: System uptime in hundredths of seconds
        var_binds: Additional variable bindings
        version: SNMP version
        request_id: Request ID (for v2c, auto-generated if None)
        generic_trap: Generic trap type (for v1)
        specific_trap: Specific trap code (for v1)
        ttl: IP TTL value

    Returns:
        Complete packet bytes
    """
    if version == SNMPVersion.V1:
        snmp_payload = build_snmp_trap_v1(
            community=community,
            enterprise_oid=enterprise_oid or "1.3.6.1.4.1.1206.4.2.1",
            agent_addr=src_ip,
            generic_trap=generic_trap,
            specific_trap=specific_trap,
            timestamp=uptime_ticks,
            varbinds=var_binds,
        )
    else:
        req_id = request_id or random.randint(1, 65535)
        snmp_payload = build_snmp_trap_v2c(
            community=community,
            request_id=req_id,
            uptime=uptime_ticks,
            trap_oid=trap_type,
            varbinds=var_binds,
        )

    return build_udp_packet_raw(
        src_mac=src_mac,
        dst_mac=dst_mac,
        src_ip=src_ip,
        dst_ip=dst_ip,
        payload=snmp_payload,
        dst_port=SNMP_TRAP_PORT,
        ttl=ttl,
    )


# =============================================================================
# SNMPv3 Support
# =============================================================================


def _encode_length(length: int) -> bytes:
    """Encode ASN.1 BER length."""
    if length < 0x80:
        return bytes([length])
    elif length < 0x100:
        return bytes([0x81, length])
    elif length < 0x10000:
        return bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])
    else:
        return bytes([0x83, (length >> 16) & 0xFF, (length >> 8) & 0xFF, length & 0xFF])


def _encode_integer(value: int) -> bytes:
    """Encode ASN.1 INTEGER."""
    if value == 0:
        return bytes([0x02, 0x01, 0x00])

    # Determine the minimum number of bytes needed
    if value > 0:
        length = (value.bit_length() + 8) // 8
        value_bytes = value.to_bytes(length, byteorder='big', signed=False)
        # Add leading zero if high bit is set (to avoid negative interpretation)
        if value_bytes[0] & 0x80:
            value_bytes = b'\x00' + value_bytes
    else:
        # Negative integers (two's complement)
        length = (value.bit_length() + 9) // 8
        value_bytes = value.to_bytes(length, byteorder='big', signed=True)

    return bytes([0x02]) + _encode_length(len(value_bytes)) + value_bytes


def _encode_octet_string(data: bytes | str) -> bytes:
    """Encode ASN.1 OCTET STRING."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return bytes([0x04]) + _encode_length(len(data)) + data


def _encode_sequence(contents: bytes) -> bytes:
    """Encode ASN.1 SEQUENCE."""
    return bytes([0x30]) + _encode_length(len(contents)) + contents


def _password_to_key_md5(password: str, engine_id: bytes) -> bytes:
    """Convert password to localized key using MD5.

    RFC 3414 key localization algorithm.
    """
    import hashlib

    # Generate Ku from password (expand to 1MB)
    password_bytes = password.encode('utf-8')
    count = 0
    password_buf = b''

    while count < 1048576:  # 1MB
        password_buf += password_bytes
        count += len(password_bytes)
    password_buf = password_buf[:1048576]

    ku = hashlib.md5(password_buf).digest()

    # Localize key with engine ID
    kul = hashlib.md5(ku + engine_id + ku).digest()

    return kul


def _password_to_key_sha(password: str, engine_id: bytes) -> bytes:
    """Convert password to localized key using SHA-1.

    RFC 3414 key localization algorithm.
    """
    import hashlib

    # Generate Ku from password (expand to 1MB)
    password_bytes = password.encode('utf-8')
    count = 0
    password_buf = b''

    while count < 1048576:  # 1MB
        password_buf += password_bytes
        count += len(password_bytes)
    password_buf = password_buf[:1048576]

    ku = hashlib.sha1(password_buf).digest()

    # Localize key with engine ID
    kul = hashlib.sha1(ku + engine_id + ku).digest()

    return kul


def _compute_auth_md5(key: bytes, message: bytes) -> bytes:
    """Compute HMAC-MD5-96 authentication."""
    import hmac
    import hashlib

    return hmac.new(key, message, hashlib.md5).digest()[:12]


def _compute_auth_sha(key: bytes, message: bytes) -> bytes:
    """Compute HMAC-SHA-96 authentication."""
    import hmac
    import hashlib

    return hmac.new(key, message, hashlib.sha1).digest()[:12]


def _encrypt_des(key: bytes, priv_params: bytes, data: bytes) -> tuple[bytes, bytes]:
    """Encrypt data using DES-CBC.

    Returns (encrypted_data, priv_params).
    """
    try:
        from Crypto.Cipher import DES
    except ImportError:
        # Fallback: return data unencrypted with warning
        import logging
        logging.warning("PyCryptodome not available, SNMPv3 privacy disabled")
        return data, priv_params

    # DES key is first 8 bytes of privacy key
    des_key = key[:8]

    # IV is priv_params XOR'd with salt (last 8 bytes of key for salt generation)
    iv = bytes(a ^ b for a, b in zip(priv_params, key[8:16]))

    # Pad data to 8-byte boundary
    pad_len = 8 - (len(data) % 8)
    if pad_len == 0:
        pad_len = 8
    padded_data = data + bytes([pad_len] * pad_len)

    cipher = DES.new(des_key, DES.MODE_CBC, iv)
    encrypted = cipher.encrypt(padded_data)

    return encrypted, priv_params


def _encrypt_aes128(key: bytes, priv_params: bytes, engine_boots: int, engine_time: int, data: bytes) -> tuple[bytes, bytes]:
    """Encrypt data using AES-128-CFB.

    Returns (encrypted_data, priv_params).
    """
    try:
        from Crypto.Cipher import AES
    except ImportError:
        import logging
        logging.warning("PyCryptodome not available, SNMPv3 privacy disabled")
        return data, priv_params

    # AES key is first 16 bytes of privacy key
    aes_key = key[:16]

    # IV construction per RFC 3826
    iv = struct.pack('>I', engine_boots) + struct.pack('>I', engine_time) + priv_params

    cipher = AES.new(aes_key, AES.MODE_CFB, iv, segment_size=128)
    encrypted = cipher.encrypt(data)

    return encrypted, priv_params


def generate_engine_id(ip_address: str) -> bytes:
    """Generate a unique engine ID based on IP address.

    Format: Enterprise Number (4 bytes) + Format (1 byte) + IP (4 bytes)
    """
    # Use enterprise number for PacketArch (made up: 999999)
    enterprise = 999999

    # Format 1 = IPv4 address
    format_byte = 0x01

    ip_parts = [int(x) for x in ip_address.split('.')]

    # Engine ID structure
    engine_id = struct.pack('>I', 0x80000000 | enterprise)  # High bit set + enterprise
    engine_id += bytes([format_byte])
    engine_id += bytes(ip_parts)

    return engine_id


def build_snmpv3_header(
    message_id: int,
    max_size: int,
    flags: int,
    security_model: int = 3,  # USM
) -> bytes:
    """Build SNMPv3 message header.

    Args:
        message_id: Message ID for request/response matching
        max_size: Maximum message size supported
        flags: Security flags (bit 0=auth, bit 1=priv, bit 2=reportable)
        security_model: Security model (3 = USM)

    Returns:
        Encoded header data bytes
    """
    header_data = (
        _encode_integer(message_id) +
        _encode_integer(max_size) +
        _encode_octet_string(bytes([flags])) +
        _encode_integer(security_model)
    )
    return _encode_sequence(header_data)


def build_snmpv3_usm_params(
    engine_id: bytes,
    engine_boots: int,
    engine_time: int,
    username: str,
    auth_params: bytes = b'',
    priv_params: bytes = b'',
) -> bytes:
    """Build SNMPv3 USM security parameters.

    Args:
        engine_id: Authoritative engine ID
        engine_boots: Engine boots counter
        engine_time: Engine time
        username: Security name (username)
        auth_params: Authentication parameters (12 bytes for HMAC-MD5/SHA)
        priv_params: Privacy parameters (8 bytes for DES/AES salt)

    Returns:
        Encoded USM parameters as OCTET STRING
    """
    usm_contents = (
        _encode_octet_string(engine_id) +
        _encode_integer(engine_boots) +
        _encode_integer(engine_time) +
        _encode_octet_string(username) +
        _encode_octet_string(auth_params) +
        _encode_octet_string(priv_params)
    )
    # USM parameters are wrapped as SEQUENCE then encoded as OCTET STRING
    usm_sequence = _encode_sequence(usm_contents)
    return _encode_octet_string(usm_sequence)


def build_snmpv3_scoped_pdu(
    context_engine_id: bytes,
    context_name: str,
    pdu: bytes,
) -> bytes:
    """Build SNMPv3 scoped PDU.

    Args:
        context_engine_id: Context engine ID
        context_name: Context name
        pdu: The actual SNMP PDU (GetRequest, GetResponse, etc.)

    Returns:
        Encoded scoped PDU bytes
    """
    scoped_contents = (
        _encode_octet_string(context_engine_id) +
        _encode_octet_string(context_name) +
        pdu
    )
    return _encode_sequence(scoped_contents)


def build_snmpv3_message(
    credentials: SNMPv3Credentials,
    pdu: bytes,
    message_id: int,
    max_size: int = 65507,
    reportable: bool = True,
) -> bytes:
    """Build complete SNMPv3 message with USM security.

    Args:
        credentials: SNMPv3 security credentials
        pdu: SNMP PDU bytes (GetRequest, GetResponse, etc.)
        message_id: Message ID
        max_size: Maximum message size
        reportable: Whether report PDU is expected

    Returns:
        Complete SNMPv3 message bytes
    """
    # Determine security flags
    flags = 0x04 if reportable else 0x00  # Reportable flag
    if credentials.security_level >= SNMPv3SecurityLevel.AUTH_NO_PRIV:
        flags |= 0x01  # Auth flag
    if credentials.security_level >= SNMPv3SecurityLevel.AUTH_PRIV:
        flags |= 0x02  # Priv flag

    engine_id = credentials.engine_id or b''

    # Build scoped PDU
    scoped_pdu = build_snmpv3_scoped_pdu(
        context_engine_id=engine_id,
        context_name=credentials.context_name,
        pdu=pdu,
    )

    # Handle privacy (encryption)
    priv_params = b''
    if credentials.security_level >= SNMPv3SecurityLevel.AUTH_PRIV and engine_id:
        # Generate privacy parameters (salt)
        priv_params = struct.pack('>Q', random.randint(0, 0xFFFFFFFFFFFFFFFF))[:8]

        # Derive privacy key
        if credentials.auth_protocol == SNMPv3AuthProtocol.MD5:
            priv_key = _password_to_key_md5(credentials.priv_password or '', engine_id)
        else:
            priv_key = _password_to_key_sha(credentials.priv_password or '', engine_id)

        # Encrypt scoped PDU
        if credentials.priv_protocol == SNMPv3PrivProtocol.DES:
            encrypted_pdu, priv_params = _encrypt_des(priv_key, priv_params, scoped_pdu)
        else:  # AES variants
            encrypted_pdu, priv_params = _encrypt_aes128(
                priv_key, priv_params,
                credentials.engine_boots, credentials.engine_time,
                scoped_pdu
            )

        # Replace scoped PDU with encrypted version (as OCTET STRING)
        scoped_pdu = _encode_octet_string(encrypted_pdu)

    # Build message with placeholder for auth params
    auth_params_placeholder = b'\x00' * 12 if credentials.security_level >= SNMPv3SecurityLevel.AUTH_NO_PRIV else b''

    # Build USM security parameters
    usm_params = build_snmpv3_usm_params(
        engine_id=engine_id,
        engine_boots=credentials.engine_boots,
        engine_time=credentials.engine_time,
        username=credentials.username,
        auth_params=auth_params_placeholder,
        priv_params=priv_params,
    )

    # Build header
    header = build_snmpv3_header(message_id, max_size, flags)

    # Combine message
    message_contents = (
        _encode_integer(3) +  # SNMPv3 version
        header +
        usm_params +
        scoped_pdu
    )
    message = _encode_sequence(message_contents)

    # Compute and insert authentication if needed
    if credentials.security_level >= SNMPv3SecurityLevel.AUTH_NO_PRIV and engine_id:
        # Derive authentication key
        if credentials.auth_protocol == SNMPv3AuthProtocol.MD5:
            auth_key = _password_to_key_md5(credentials.auth_password or '', engine_id)
            auth_mac = _compute_auth_md5(auth_key, message)
        else:  # SHA variants
            auth_key = _password_to_key_sha(credentials.auth_password or '', engine_id)
            auth_mac = _compute_auth_sha(auth_key, message)

        # Find and replace auth params placeholder in message
        # The placeholder is 12 zero bytes
        placeholder_pos = message.find(b'\x04\x0c' + b'\x00' * 12)
        if placeholder_pos >= 0:
            message = (
                message[:placeholder_pos + 2] +
                auth_mac +
                message[placeholder_pos + 14:]
            )

    return message


def build_snmpv3_get_request(
    credentials: SNMPv3Credentials,
    request_id: int,
    oids: list[str],
    message_id: int | None = None,
) -> bytes:
    """Build SNMPv3 GetRequest message.

    Args:
        credentials: SNMPv3 credentials
        request_id: Request ID for PDU
        oids: List of OIDs to request
        message_id: Message ID (defaults to request_id)

    Returns:
        Complete SNMPv3 GetRequest message bytes
    """
    # Build PDU using Scapy
    varbinds = [SNMPvarbind(oid=ASN1_OID(oid), value=ASN1_NULL(0)) for oid in oids]
    snmp_pdu = SNMPget(
        id=ASN1_INTEGER(request_id),
        error=ASN1_INTEGER(0),
        error_index=ASN1_INTEGER(0),
        varbindlist=varbinds,
    )
    pdu_bytes = bytes(snmp_pdu)

    return build_snmpv3_message(
        credentials=credentials,
        pdu=pdu_bytes,
        message_id=message_id or request_id,
    )


def build_snmpv3_get_response(
    credentials: SNMPv3Credentials,
    request_id: int,
    varbinds: list[VarBind],
    error_status: int = 0,
    error_index: int = 0,
    message_id: int | None = None,
) -> bytes:
    """Build SNMPv3 GetResponse message.

    Args:
        credentials: SNMPv3 credentials
        request_id: Request ID (must match request)
        varbinds: List of VarBind with OID and value
        error_status: Error status code
        error_index: Index of problematic varbind
        message_id: Message ID (defaults to request_id)

    Returns:
        Complete SNMPv3 GetResponse message bytes
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
    pdu_bytes = bytes(snmp_pdu)

    return build_snmpv3_message(
        credentials=credentials,
        pdu=pdu_bytes,
        message_id=message_id or request_id,
        reportable=False,  # Responses are not reportable
    )


def build_snmpv3_discovery_request(message_id: int) -> bytes:
    """Build SNMPv3 engine discovery request.

    This is an unauthenticated request to discover the authoritative engine ID.

    Args:
        message_id: Message ID for the discovery request

    Returns:
        SNMPv3 discovery request message bytes
    """
    # Discovery uses noAuthNoPriv credentials with empty values
    discovery_creds = SNMPv3Credentials(
        username='',
        security_level=SNMPv3SecurityLevel.NO_AUTH_NO_PRIV,
        auth_protocol=SNMPv3AuthProtocol.NONE,
        priv_protocol=SNMPv3PrivProtocol.NONE,
        engine_id=b'',
    )

    # Empty GetRequest for discovery
    varbinds = []
    snmp_pdu = SNMPget(
        id=ASN1_INTEGER(0),
        error=ASN1_INTEGER(0),
        error_index=ASN1_INTEGER(0),
        varbindlist=varbinds,
    )

    return build_snmpv3_message(
        credentials=discovery_creds,
        pdu=bytes(snmp_pdu),
        message_id=message_id,
        reportable=True,
    )


def build_snmpv3_get_request_packet(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    credentials: SNMPv3Credentials,
    request_id: int,
    oids: list[str],
    message_id: int | None = None,
    ttl: int = 64,
) -> bytes:
    """Build complete SNMPv3 GetRequest packet with headers.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_port: Source UDP port
        dst_port: Destination UDP port
        credentials: SNMPv3 credentials
        request_id: Request ID
        oids: OIDs to request
        message_id: Message ID (defaults to request_id)
        ttl: IP TTL value

    Returns:
        Complete packet bytes
    """
    snmp_payload = build_snmpv3_get_request(
        credentials, request_id, oids, message_id
    )
    return build_udp_packet_raw(
        src_mac=src_mac,
        dst_mac=dst_mac,
        src_ip=src_ip,
        dst_ip=dst_ip,
        payload=snmp_payload,
        src_port=src_port,
        dst_port=dst_port,
        ttl=ttl,
    )


def build_snmpv3_get_response_packet(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    credentials: SNMPv3Credentials,
    request_id: int,
    var_binds: list[VarBind],
    error_status: int = 0,
    error_index: int = 0,
    message_id: int | None = None,
    ttl: int = 64,
) -> bytes:
    """Build complete SNMPv3 GetResponse packet with headers.

    Args:
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_port: Source UDP port
        dst_port: Destination UDP port
        credentials: SNMPv3 credentials
        request_id: Request ID
        var_binds: Variable bindings with values
        error_status: Error status code
        error_index: Error index
        message_id: Message ID
        ttl: IP TTL value

    Returns:
        Complete packet bytes
    """
    snmp_payload = build_snmpv3_get_response(
        credentials, request_id, var_binds, error_status, error_index, message_id
    )
    return build_udp_packet_raw(
        src_mac=src_mac,
        dst_mac=dst_mac,
        src_ip=src_ip,
        dst_ip=dst_ip,
        payload=snmp_payload,
        src_port=src_port,
        dst_port=dst_port,
        ttl=ttl,
    )
