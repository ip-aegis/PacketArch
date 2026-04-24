# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Codesys protocol engine package.

Supports Codesys runtime used by 500+ PLC vendors including:
- WAGO (750/760 series)
- Beckhoff (TwinCAT compatible)
- Festo (CECC series)
- Schneider Electric (SoMachine, M241/M251)
- ABB (AC500 series)
- IFM, EPEC, Kontron, Eaton, TURCK, Lenze, and many more

Protocol versions:
- V3 (modern): TCP port 11740, block driver framing
- V2 (legacy): TCP port 1200, simplified protocol
"""

from app.protocol_engines.codesys.engine import CodesysEngine
from app.protocol_engines.codesys.types import (
    CODESYS_V3_PORT,
    CODESYS_V2_PORT,
    CODESYS_GATEWAY_PORT,
    BLOCK_DRIVER_MAGIC,
    CodesysVersion,
    CodesysService,
    CodesysV2Command,
    CodesysStatus,
    PLCState,
    CodesysDataType,
    DATA_TYPE_SIZES,
    CodesysVendor,
    CODESYS_VENDOR_NAMES,
    CODESYS_DEVICE_MODELS,
    CodesysDeviceIdentity,
    CodesysVariable,
    CodesysConfig,
)

__all__ = [
    "CodesysEngine",
    # Ports
    "CODESYS_V3_PORT",
    "CODESYS_V2_PORT",
    "CODESYS_GATEWAY_PORT",
    "BLOCK_DRIVER_MAGIC",
    # Enums
    "CodesysVersion",
    "CodesysService",
    "CodesysV2Command",
    "CodesysStatus",
    "PLCState",
    "CodesysDataType",
    "DATA_TYPE_SIZES",
    "CodesysVendor",
    # Mappings
    "CODESYS_VENDOR_NAMES",
    "CODESYS_DEVICE_MODELS",
    # Data classes
    "CodesysDeviceIdentity",
    "CodesysVariable",
    "CodesysConfig",
]
