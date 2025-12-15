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
from app.protocol_engines.ethernet_ip.engine import EtherNetIPEngine  # noqa: E402, F401
from app.protocol_engines.profinet.engine import ProfinetEngine  # noqa: E402, F401
from app.protocol_engines.s7.engine import S7Engine  # noqa: E402, F401
from app.protocol_engines.opc_ua.engine import OpcUaEngine  # noqa: E402, F401
from app.protocol_engines.dnp3.engine import Dnp3Engine  # noqa: E402, F401
from app.protocol_engines.iec104.engine import Iec104Engine  # noqa: E402, F401

# AI-enhanced engines
from app.protocol_engines.ai_enhanced_base import (  # noqa: E402, F401
    AIEnhancedProtocolEngine,
    AIEnhancedEngineFactory,
    create_ai_enhanced_engine,
)
from app.protocol_engines.ai_timing import (  # noqa: E402, F401
    LearnedJitterModel,
    ContextAwareTimingModel,
    DevicePersonality,
    LearnedTimingService,
)

# Learned pattern integration
from app.protocol_engines.learned_pattern_integrator import (  # noqa: E402, F401
    LearnedPatternIntegrator,
    LearnedTimingConfig,
    LearnedFunctionCodeConfig,
    LearnedAddressConfig,
)

__all__ = [
    "ProtocolEngine",
    "ProtocolType",
    "register_engine",
    "get_engine",
    "list_supported_protocols",
    "ModbusTcpEngine",
    "EtherNetIPEngine",
    "ProfinetEngine",
    "S7Engine",
    "OpcUaEngine",
    "Dnp3Engine",
    "Iec104Engine",
    # AI-enhanced
    "AIEnhancedProtocolEngine",
    "AIEnhancedEngineFactory",
    "create_ai_enhanced_engine",
    "LearnedJitterModel",
    "ContextAwareTimingModel",
    "DevicePersonality",
    "LearnedTimingService",
    # Learned pattern integration
    "LearnedPatternIntegrator",
    "LearnedTimingConfig",
    "LearnedFunctionCodeConfig",
    "LearnedAddressConfig",
]
