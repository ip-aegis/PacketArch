# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Ambient background noise generator for realistic network traffic.

Generates ARP, NTP, LLDP, STP, DHCP, BACnet, PROFINET DCP, SNMP traps,
CDP, and IGMP traffic that real OT networks always have. Registered as
a composition peer in UnifiedOrchestrator.
"""

from app.protocol_engines.ambient.noise_generator import (
    AmbientConfig,
    AmbientDevice,
    BackgroundNoiseGenerator,
)

__all__ = [
    "AmbientConfig",
    "AmbientDevice",
    "BackgroundNoiseGenerator",
]
