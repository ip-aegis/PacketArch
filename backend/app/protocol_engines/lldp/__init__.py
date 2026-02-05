"""LLDP protocol engine package.

LLDP (Link Layer Discovery Protocol, IEEE 802.1AB) is a Layer 2 protocol
used by network devices to advertise their identity, capabilities, and
neighbors on a local network.

Key characteristics:
- Layer 2 only (no IP required)
- EtherType: 0x88CC
- Multicast destination: 01:80:C2:00:00:0E
- TLV-based format
- Default 30-second transmission interval
- Supports organizational extensions (IEEE 802.1, 802.3, LLDP-MED, PROFINET)
"""

from app.protocol_engines.lldp.engine import LLDPEngine
from app.protocol_engines.lldp.types import (
    # Frame constants
    LLDP_ETHERTYPE,
    LLDP_MULTICAST_MAC,
    # Timing
    DEFAULT_TX_INTERVAL,
    DEFAULT_TTL,
    # TLV types
    LLDPTLVType,
    ChassisIDSubtype,
    PortIDSubtype,
    SystemCapability,
    AddressFamily,
    InterfaceNumberingSubtype,
    # OUIs
    OUI_IEEE_802_1,
    OUI_IEEE_802_3,
    OUI_LLDP_MED,
    OUI_PROFINET,
    # Subtypes
    IEEE8021Subtype,
    IEEE8023Subtype,
    LLDPMEDSubtype,
    LLDPMEDDeviceType,
    LLDPMEDCapability,
    ProfinetSubtype,
    MAUType,
    PMDCapability,
    # Device types
    LLDPDeviceType,
    INDUSTRIAL_DEVICE_PROFILES,
    # Data classes
    LLDPIdentity,
    LLDPConfig,
)

__all__ = [
    "LLDPEngine",
    # Frame constants
    "LLDP_ETHERTYPE",
    "LLDP_MULTICAST_MAC",
    # Timing
    "DEFAULT_TX_INTERVAL",
    "DEFAULT_TTL",
    # TLV types
    "LLDPTLVType",
    "ChassisIDSubtype",
    "PortIDSubtype",
    "SystemCapability",
    "AddressFamily",
    "InterfaceNumberingSubtype",
    # OUIs
    "OUI_IEEE_802_1",
    "OUI_IEEE_802_3",
    "OUI_LLDP_MED",
    "OUI_PROFINET",
    # Subtypes
    "IEEE8021Subtype",
    "IEEE8023Subtype",
    "LLDPMEDSubtype",
    "LLDPMEDDeviceType",
    "LLDPMEDCapability",
    "ProfinetSubtype",
    "MAUType",
    "PMDCapability",
    # Device types
    "LLDPDeviceType",
    "INDUSTRIAL_DEVICE_PROFILES",
    # Data classes
    "LLDPIdentity",
    "LLDPConfig",
]
