# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""External communications protocol engine.

This package provides traffic generation for external communications
that simulate C2 beaconing, data exfiltration, exploit attempts,
and external reconnaissance - traffic patterns that IDS systems
like Snort/Suricata and Cisco Cyber Vision will detect.

Components:
- ip_pools: RFC 5737 TEST-NET IP address pools for external endpoints
- http_packets: HTTP beacon and exfiltration packet builders
- dns_packets: DNS tunneling and exfiltration packet builders
- c2_patterns: C2 beaconing timing patterns
- exploit_patterns: Exploit signature patterns for IDS triggering
- engine: Main ExternalCommEngine class
"""

from app.protocol_engines.external.ip_pools import (
    ExternalIPPool,
    get_c2_server_ip,
    get_exfil_destination_ip,
    get_attack_source_ip,
)
from app.protocol_engines.external.engine import ExternalCommEngine

__all__ = [
    "ExternalIPPool",
    "ExternalCommEngine",
    "get_c2_server_ip",
    "get_exfil_destination_ip",
    "get_attack_source_ip",
]
