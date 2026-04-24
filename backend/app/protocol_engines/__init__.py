# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Protocol engines package with engine registry."""

from typing import Type

from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.types import ProtocolType

# Engine registry
_ENGINE_REGISTRY: dict[ProtocolType, Type[ProtocolEngine]] = {}


def register_engine(protocol_type: ProtocolType):
    """Decorator to register a protocol engine.

    Args:
        protocol_type: The protocol type this engine handles

    Returns:
        Decorator function
    """

    def decorator(engine_class: Type[ProtocolEngine]):
        _ENGINE_REGISTRY[protocol_type] = engine_class
        return engine_class

    return decorator


def get_engine(protocol: ProtocolType) -> ProtocolEngine:
    """Get engine instance for a protocol type.

    Args:
        protocol: Protocol type

    Returns:
        Protocol engine instance

    Raises:
        ValueError: If protocol is not supported
    """
    engine_class = _ENGINE_REGISTRY.get(protocol)
    if not engine_class:
        raise ValueError(f"No engine registered for protocol: {protocol}")

    return engine_class()


def list_supported_protocols() -> list[ProtocolType]:
    """List all supported protocol types.

    Returns:
        List of supported protocol types
    """
    return list(_ENGINE_REGISTRY.keys())


# Import engines to register them
from app.protocol_engines.modbus.engine import ModbusTcpEngine  # noqa: E402, F401
from app.protocol_engines.modbus.rtu_engine import ModbusRtuEngine  # noqa: E402, F401
from app.protocol_engines.ethernet_ip.engine import EtherNetIPEngine  # noqa: E402, F401
from app.protocol_engines.profinet.engine import ProfinetEngine  # noqa: E402, F401
from app.protocol_engines.s7.engine import S7Engine  # noqa: E402, F401
from app.protocol_engines.opc_ua.engine import OpcUaEngine  # noqa: E402, F401
from app.protocol_engines.dnp3.engine import Dnp3Engine  # noqa: E402, F401
from app.protocol_engines.iec104.engine import Iec104Engine  # noqa: E402, F401
from app.protocol_engines.iec61850.engine import IEC61850Engine  # noqa: E402, F401
from app.protocol_engines.pccc.engine import PCCCEngine  # noqa: E402, F401
from app.protocol_engines.codesys.engine import CodesysEngine  # noqa: E402, F401
from app.protocol_engines.lldp.engine import LLDPEngine  # noqa: E402, F401
from app.protocol_engines.snmp.engine import SnmpEngine  # noqa: E402, F401
from app.protocol_engines.bacnet.engine import BACnetEngine  # noqa: E402, F401
from app.protocol_engines.ethercat.engine import EtherCATEngine  # noqa: E402, F401
from app.protocol_engines.fins.engine import FINSEngine  # noqa: E402, F401
from app.protocol_engines.slmp.engine import SLMPEngine  # noqa: E402, F401
from app.protocol_engines.cdp.engine import CDPEngine  # noqa: E402, F401
from app.protocol_engines.wmi.engine import WMIEngine  # noqa: E402, F401
from app.protocol_engines.fanuc.engine import FANUCEngine  # noqa: E402, F401
from app.protocol_engines.dcs.engine import DCSEngine  # noqa: E402, F401
from app.protocol_engines.cloud_service.engine import CloudServiceEngine  # noqa: E402, F401

__all__ = [
    "ProtocolEngine",
    "ProtocolType",
    "register_engine",
    "get_engine",
    "list_supported_protocols",
    "ModbusTcpEngine",
    "ModbusRtuEngine",
    "EtherNetIPEngine",
    "ProfinetEngine",
    "S7Engine",
    "OpcUaEngine",
    "Dnp3Engine",
    "Iec104Engine",
    "IEC61850Engine",
    "PCCCEngine",
    "CodesysEngine",
    "LLDPEngine",
    "SnmpEngine",
    "BACnetEngine",
    "EtherCATEngine",
    "FINSEngine",
    "SLMPEngine",
    "CDPEngine",
    "WMIEngine",
    "FANUCEngine",
    "DCSEngine",
    "CloudServiceEngine",
]
