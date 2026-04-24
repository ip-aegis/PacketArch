# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""SNMP/NTCIP protocol engine package.

Provides SNMP protocol support for transportation systems including:
- Traffic signal controllers (NTCIP 1202)
- Dynamic message signs (NTCIP 1203)
- Environmental sensor stations (NTCIP 1204)
- Cameras, sensors, RSUs, and toll systems
"""

from app.protocol_engines.snmp.engine import SnmpEngine
from app.protocol_engines.snmp.oids import (
    DISCOVERY_OIDS,
    DMS_POLL_OIDS,
    TRAFFIC_CONTROLLER_POLL_OIDS,
    InterfaceOIDs,
    OIDDefinition,
    SystemOIDs,
    VENDOR_ENTERPRISE_OIDS,
    decode_oid,
    encode_oid,
    get_next_oid,
    is_child_of,
)
from app.protocol_engines.snmp.packets import (
    build_snmp_get_request_packet,
    build_snmp_get_response_packet,
    build_snmp_trap_packet,
)
from app.protocol_engines.snmp.types import (
    SNMP_AGENT_PORT,
    SNMP_TRAP_PORT,
    ASN1Tag,
    GenericTrapType,
    SNMPErrorStatus,
    SNMPFlowConfig,
    SNMPOperation,
    SNMPRequest,
    SNMPState,
    SNMPValueType,
    SNMPVersion,
    VarBind,
)

__all__ = [
    # Engine
    "SnmpEngine",
    # Types
    "SNMPVersion",
    "SNMPOperation",
    "SNMPErrorStatus",
    "SNMPValueType",
    "SNMPState",
    "GenericTrapType",
    "VarBind",
    "SNMPRequest",
    "SNMPFlowConfig",
    "ASN1Tag",
    # Constants
    "SNMP_AGENT_PORT",
    "SNMP_TRAP_PORT",
    # OIDs
    "OIDDefinition",
    "SystemOIDs",
    "InterfaceOIDs",
    "VENDOR_ENTERPRISE_OIDS",
    "DISCOVERY_OIDS",
    "TRAFFIC_CONTROLLER_POLL_OIDS",
    "DMS_POLL_OIDS",
    # OID utilities
    "encode_oid",
    "decode_oid",
    "is_child_of",
    "get_next_oid",
    # Packet builders
    "build_snmp_get_request_packet",
    "build_snmp_get_response_packet",
    "build_snmp_trap_packet",
]
