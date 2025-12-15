"""External IP address pools for simulated external communications.

Uses RFC 5737 TEST-NET ranges which are safe, non-routable addresses
specifically designated for documentation and testing:
- TEST-NET-1: 192.0.2.0/24 (used for C2 servers)
- TEST-NET-2: 198.51.100.0/24 (used for exfiltration destinations)
- TEST-NET-3: 203.0.113.0/24 (used for attack sources)

These ranges will never conflict with real production traffic and
clearly indicate simulated malicious activity in generated PCAPs.
"""

import random
from dataclasses import dataclass
from enum import Enum
from typing import Iterator


class ExternalTargetType(str, Enum):
    """Types of external endpoints for traffic simulation."""

    C2_SERVER = "c2_server"  # Command & control server
    EXFIL_DESTINATION = "exfil_destination"  # Data exfiltration target
    ATTACK_SOURCE = "attack_source"  # External attacker IP
    DNS_SERVER = "dns_server"  # External DNS (for tunneling)
    MALWARE_HOST = "malware_host"  # Malware download server


# RFC 5737 TEST-NET ranges
TEST_NET_1 = "192.0.2"  # C2 servers
TEST_NET_2 = "198.51.100"  # Exfil destinations
TEST_NET_3 = "203.0.113"  # Attack sources

# Well-known malicious IP patterns (for realistic mode)
# These are documented/historical malicious IPs from threat intel
REALISTIC_C2_IPS = [
    "185.220.101.1",  # Historical Tor exit / C2
    "45.33.32.156",  # Documented scanner
    "104.244.76.13",  # Known threat actor IP
    "89.248.167.131",  # Documented C2
]

REALISTIC_EXFIL_IPS = [
    "195.154.181.128",  # Historical exfil endpoint
    "51.158.166.192",  # Documented drop server
    "163.172.214.66",  # Historical threat actor
]


@dataclass
class ExternalIPPool:
    """Pool of external IPs for traffic generation.

    Provides IP addresses for simulating external communications
    using safe TEST-NET ranges by default, with optional "realistic"
    mode using documented historical malicious IPs.
    """

    pool_type: ExternalTargetType
    use_realistic: bool = False
    _index: int = 0

    def __post_init__(self):
        """Initialize the base range based on pool type."""
        if self.pool_type == ExternalTargetType.C2_SERVER:
            self._base = TEST_NET_1
            self._realistic_pool = REALISTIC_C2_IPS
        elif self.pool_type == ExternalTargetType.EXFIL_DESTINATION:
            self._base = TEST_NET_2
            self._realistic_pool = REALISTIC_EXFIL_IPS
        elif self.pool_type == ExternalTargetType.ATTACK_SOURCE:
            self._base = TEST_NET_3
            self._realistic_pool = []
        elif self.pool_type == ExternalTargetType.DNS_SERVER:
            self._base = TEST_NET_1  # Reuse TEST_NET_1 for DNS
            self._realistic_pool = ["8.8.8.8", "1.1.1.1"]  # Safe public DNS
        else:
            self._base = TEST_NET_2
            self._realistic_pool = []

    def get_ip(self, index: int | None = None) -> str:
        """Get an IP address from the pool.

        Args:
            index: Optional specific index (1-254). If None, uses sequential.

        Returns:
            IP address string
        """
        if self.use_realistic and self._realistic_pool:
            return random.choice(self._realistic_pool)

        if index is None:
            self._index = (self._index % 254) + 1
            index = self._index

        # Ensure index is in valid range
        index = max(1, min(254, index))
        return f"{self._base}.{index}"

    def get_random_ip(self) -> str:
        """Get a random IP from the pool.

        Returns:
            Random IP address string
        """
        if self.use_realistic and self._realistic_pool:
            return random.choice(self._realistic_pool)
        return f"{self._base}.{random.randint(1, 254)}"

    def iterate_ips(self, count: int = 10) -> Iterator[str]:
        """Iterate over IP addresses.

        Args:
            count: Number of IPs to generate

        Yields:
            IP address strings
        """
        for i in range(count):
            yield self.get_ip(i + 1)

    @property
    def base_network(self) -> str:
        """Get the base network for this pool."""
        return f"{self._base}.0/24"


# Convenience functions for common use cases


def get_c2_server_ip(index: int | None = None, realistic: bool = False) -> str:
    """Get a C2 server IP address.

    Args:
        index: Optional specific server index
        realistic: Use realistic historical IPs instead of TEST-NET

    Returns:
        C2 server IP address
    """
    pool = ExternalIPPool(ExternalTargetType.C2_SERVER, use_realistic=realistic)
    return pool.get_ip(index)


def get_exfil_destination_ip(index: int | None = None, realistic: bool = False) -> str:
    """Get an exfiltration destination IP address.

    Args:
        index: Optional specific destination index
        realistic: Use realistic historical IPs instead of TEST-NET

    Returns:
        Exfil destination IP address
    """
    pool = ExternalIPPool(ExternalTargetType.EXFIL_DESTINATION, use_realistic=realistic)
    return pool.get_ip(index)


def get_attack_source_ip(index: int | None = None) -> str:
    """Get an external attacker source IP address.

    Args:
        index: Optional specific attacker index

    Returns:
        Attacker source IP address
    """
    pool = ExternalIPPool(ExternalTargetType.ATTACK_SOURCE)
    return pool.get_ip(index)


def get_dns_server_ip(realistic: bool = False) -> str:
    """Get a DNS server IP for tunneling simulation.

    Args:
        realistic: Use real public DNS IPs (8.8.8.8, 1.1.1.1)

    Returns:
        DNS server IP address
    """
    pool = ExternalIPPool(ExternalTargetType.DNS_SERVER, use_realistic=realistic)
    return pool.get_ip()


# IP pool registry for scenario-wide allocation
class ExternalIPRegistry:
    """Registry for tracking allocated external IPs within a scenario."""

    def __init__(self, scenario_id: str):
        self.scenario_id = scenario_id
        self._c2_servers: list[str] = []
        self._exfil_destinations: list[str] = []
        self._attack_sources: list[str] = []

    def allocate_c2_server(self, realistic: bool = False) -> str:
        """Allocate a new C2 server IP."""
        ip = get_c2_server_ip(len(self._c2_servers) + 1, realistic)
        self._c2_servers.append(ip)
        return ip

    def allocate_exfil_destination(self, realistic: bool = False) -> str:
        """Allocate a new exfil destination IP."""
        ip = get_exfil_destination_ip(len(self._exfil_destinations) + 1, realistic)
        self._exfil_destinations.append(ip)
        return ip

    def allocate_attack_source(self) -> str:
        """Allocate a new attack source IP."""
        ip = get_attack_source_ip(len(self._attack_sources) + 1)
        self._attack_sources.append(ip)
        return ip

    @property
    def all_external_ips(self) -> list[str]:
        """Get all allocated external IPs."""
        return self._c2_servers + self._exfil_destinations + self._attack_sources

    def to_dict(self) -> dict:
        """Export allocation state."""
        return {
            "scenario_id": self.scenario_id,
            "c2_servers": self._c2_servers,
            "exfil_destinations": self._exfil_destinations,
            "attack_sources": self._attack_sources,
        }
