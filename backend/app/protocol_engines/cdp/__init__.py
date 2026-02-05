"""CDP (Cisco Discovery Protocol) engine for network discovery simulation.

CDP is a Layer 2 protocol used by Cisco devices to advertise their
presence and capabilities to directly connected neighbors.

Key features:
- Multicast destination: 01:00:0c:cc:cc:cc
- LLC/SNAP encapsulation (OUI 0x00000c, Protocol 0x2000)
- Default advertisement interval: 60 seconds
- Default hold time (TTL): 180 seconds

Supported TLVs:
- Device ID, Port ID, Addresses
- Capabilities, Software Version, Platform
- Native VLAN, VTP Domain, Duplex
- Management Addresses
"""

from app.protocol_engines.cdp.engine import CDPEngine

__all__ = ["CDPEngine"]
