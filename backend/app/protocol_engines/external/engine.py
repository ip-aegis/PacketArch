# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""External Communications Engine.

Main engine for generating external communication traffic including
C2 beaconing, data exfiltration, exploit attempts, and reconnaissance.
Integrates all external packet builders with timing patterns.
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Iterator

from scapy.packet import Packet

from app.protocol_engines.external.ip_pools import (
    ExternalIPRegistry,
    get_c2_server_ip,
    get_exfil_destination_ip,
    get_attack_source_ip,
)
from app.protocol_engines.external.http_packets import (
    HTTPBeaconConfig,
    HTTPExfilConfig,
    build_http_exfil_request,
    generate_beacon_sequence,
)
from app.protocol_engines.external.dns_packets import (
    DNSTunnelConfig,
    generate_dns_tunnel_sequence,
    generate_dns_beacon_sequence,
)
from app.protocol_engines.external.c2_patterns import (
    get_beacon_pattern,
    list_beacon_patterns,
)
from app.protocol_engines.external.exploit_patterns import (
    EXPLOIT_PATTERNS,
    generate_port_scan_sequence,
    generate_ot_port_scan,
    generate_exploit_attempt,
    list_exploit_patterns,
)


logger = logging.getLogger(__name__)


@dataclass
class PacketEvent:
    """A packet with timestamp for traffic generation."""

    timestamp_ms: int
    packet: Packet
    event_type: str  # "c2_beacon", "exfil", "exploit", "scan"
    metadata: dict = field(default_factory=dict)


@dataclass
class ExternalTrafficConfig:
    """Configuration for external traffic generation."""

    # General settings
    use_realistic_ips: bool = False  # Use historical malicious IPs vs TEST-NET
    scenario_id: str | None = None

    # C2 beaconing settings
    enable_c2: bool = True
    c2_pattern: str = "jittered_1m"
    c2_protocol: str = "http"  # "http", "https", "dns"
    c2_count: int = 10  # Number of beacon exchanges

    # Data exfiltration settings
    enable_exfil: bool = False
    exfil_protocol: str = "http"  # "http", "dns"
    exfil_data_size: int = 1024  # Bytes to simulate exfiltrating

    # Exploit/attack settings
    enable_exploits: bool = False
    exploit_patterns: list[str] = field(default_factory=list)

    # Reconnaissance settings
    enable_recon: bool = False
    scan_type: str = "syn"  # "syn", "fin", "xmas", "null"
    scan_ot_ports: bool = True


class ExternalCommEngine:
    """Engine for generating external communication traffic.

    This engine generates various types of external traffic that
    would trigger IDS/IPS systems, including:
    - C2 beaconing (HTTP, DNS)
    - Data exfiltration
    - Exploit attempts
    - Network reconnaissance
    """

    def __init__(self, config: ExternalTrafficConfig | None = None):
        """Initialize the external communications engine.

        Args:
            config: Traffic generation configuration
        """
        self.config = config or ExternalTrafficConfig()
        self.ip_registry = ExternalIPRegistry(config.scenario_id or "default")

        # Pre-allocate external IPs
        self._c2_server_ip = get_c2_server_ip(1, self.config.use_realistic_ips)
        self._exfil_destination_ip = get_exfil_destination_ip(1, self.config.use_realistic_ips)
        self._attack_source_ip = get_attack_source_ip(1)

    def generate_c2_beaconing(
        self,
        internal_device_ip: str,
        start_time_ms: int = 0,
        duration_ms: int = 300000,
        pattern_name: str | None = None,
    ) -> Iterator[PacketEvent]:
        """Generate C2 beaconing traffic from an internal device.

        Args:
            internal_device_ip: IP of the "infected" internal device
            start_time_ms: Starting timestamp
            duration_ms: Duration of beaconing
            pattern_name: Name of beacon pattern to use

        Yields:
            PacketEvent instances
        """
        pattern_name = pattern_name or self.config.c2_pattern
        pattern = get_beacon_pattern(pattern_name)

        c2_ip = self._c2_server_ip
        c2_port = 443 if self.config.c2_protocol == "https" else 80

        logger.info(
            f"Generating C2 beaconing: {internal_device_ip} -> {c2_ip}:{c2_port} "
            f"pattern={pattern_name}"
        )

        if self.config.c2_protocol in ("http", "https"):
            # HTTP beaconing
            beacon_config = HTTPBeaconConfig(
                interval_ms=pattern.base_interval_ms,
                jitter_pct=pattern.jitter_pct,
            )

            for timestamp, packet in generate_beacon_sequence(
                src_ip=internal_device_ip,
                dst_ip=c2_ip,
                c2_port=c2_port,
                config=beacon_config,
                count=self.config.c2_count,
                start_time_ms=start_time_ms,
            ):
                if timestamp > start_time_ms + duration_ms:
                    break

                yield PacketEvent(
                    timestamp_ms=timestamp,
                    packet=packet,
                    event_type="c2_beacon",
                    metadata={
                        "pattern": pattern_name,
                        "protocol": self.config.c2_protocol,
                        "c2_server": c2_ip,
                        "mitre_technique": pattern.mitre_technique,
                    },
                )

        elif self.config.c2_protocol == "dns":
            # DNS beaconing
            dns_server = c2_ip  # Reuse C2 IP as authoritative DNS

            for timestamp, packet in generate_dns_beacon_sequence(
                src_ip=internal_device_ip,
                dns_server_ip=dns_server,
                beacon_domain=f"c2.{random.randint(1000, 9999)}.example.com",
                count=self.config.c2_count,
                interval_ms=pattern.base_interval_ms,
                start_time_ms=start_time_ms,
            ):
                if timestamp > start_time_ms + duration_ms:
                    break

                yield PacketEvent(
                    timestamp_ms=timestamp,
                    packet=packet,
                    event_type="c2_beacon",
                    metadata={
                        "pattern": pattern_name,
                        "protocol": "dns",
                        "c2_server": dns_server,
                        "mitre_technique": "T0884",
                    },
                )

    def generate_dns_tunnel(
        self,
        internal_device_ip: str,
        data: bytes,
        start_time_ms: int = 0,
    ) -> Iterator[PacketEvent]:
        """Generate DNS tunneling traffic for data exfiltration.

        Args:
            internal_device_ip: IP of the tunneling client
            data: Data to tunnel/exfiltrate
            start_time_ms: Starting timestamp

        Yields:
            PacketEvent instances
        """
        dns_server = self._c2_server_ip

        # Split data into chunks
        chunk_size = 100  # Bytes per DNS query
        chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

        logger.info(
            f"Generating DNS tunnel: {internal_device_ip} -> {dns_server}, "
            f"{len(chunks)} chunks"
        )

        config = DNSTunnelConfig(
            base_domain="tunnel.example.com",
            query_type="TXT",
            encoding="base32",
        )

        for timestamp, packet in generate_dns_tunnel_sequence(
            src_ip=internal_device_ip,
            dns_server_ip=dns_server,
            data_chunks=chunks,
            config=config,
            start_time_ms=start_time_ms,
            interval_ms=1000,
        ):
            yield PacketEvent(
                timestamp_ms=timestamp,
                packet=packet,
                event_type="dns_tunnel",
                metadata={
                    "protocol": "dns",
                    "encoding": config.encoding,
                    "mitre_technique": "T0884",
                },
            )

    def generate_http_exfil(
        self,
        internal_device_ip: str,
        data: bytes,
        start_time_ms: int = 0,
    ) -> Iterator[PacketEvent]:
        """Generate HTTP data exfiltration traffic.

        Args:
            internal_device_ip: IP of the exfiltrating device
            data: Data to exfiltrate
            start_time_ms: Starting timestamp

        Yields:
            PacketEvent instances
        """
        exfil_ip = self._exfil_destination_ip

        logger.info(
            f"Generating HTTP exfil: {internal_device_ip} -> {exfil_ip}, "
            f"{len(data)} bytes"
        )

        config = HTTPExfilConfig(
            path="/upload",
            encoding="base64",
            chunk_size=4096,
        )

        current_time = start_time_ms
        src_port = random.randint(49152, 65535)

        # Split data into chunks
        for i in range(0, len(data), config.chunk_size):
            chunk = data[i:i + config.chunk_size]

            packet = build_http_exfil_request(
                src_ip=internal_device_ip,
                dst_ip=exfil_ip,
                src_port=src_port,
                dst_port=80,
                data=chunk,
                config=config,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                packet=packet,
                event_type="http_exfil",
                metadata={
                    "chunk_index": i // config.chunk_size,
                    "chunk_size": len(chunk),
                    "mitre_technique": "T0882",
                },
            )

            # Delay between chunks
            current_time += random.randint(100, 500)
            src_port = (src_port + 1) if src_port < 65535 else 49152

    def generate_exploit_attempt(
        self,
        target_device_ip: str,
        exploit_name: str,
        start_time_ms: int = 0,
    ) -> Iterator[PacketEvent]:
        """Generate exploit attempt traffic.

        Args:
            target_device_ip: IP of target device
            exploit_name: Name of exploit pattern
            start_time_ms: Starting timestamp

        Yields:
            PacketEvent instances
        """
        if exploit_name not in EXPLOIT_PATTERNS:
            logger.warning(f"Unknown exploit pattern: {exploit_name}")
            return

        attacker_ip = self._attack_source_ip
        pattern = EXPLOIT_PATTERNS[exploit_name]

        logger.info(
            f"Generating exploit attempt: {attacker_ip} -> {target_device_ip}, "
            f"pattern={exploit_name}"
        )

        for timestamp, packet in generate_exploit_attempt(
            src_ip=attacker_ip,
            dst_ip=target_device_ip,
            pattern_name=exploit_name,
            start_time_ms=start_time_ms,
            repeat_count=3,
        ):
            yield PacketEvent(
                timestamp_ms=timestamp,
                packet=packet,
                event_type="exploit",
                metadata={
                    "exploit": exploit_name,
                    "attacker_ip": attacker_ip,
                    "mitre_technique": pattern.mitre_technique,
                    "cve": pattern.cve_reference,
                },
            )

    def generate_port_scan(
        self,
        target_device_ip: str,
        start_time_ms: int = 0,
        scan_ot_ports: bool = True,
    ) -> Iterator[PacketEvent]:
        """Generate port scanning traffic.

        Args:
            target_device_ip: IP of target device
            start_time_ms: Starting timestamp
            scan_ot_ports: Use OT-specific port list

        Yields:
            PacketEvent instances
        """
        attacker_ip = self._attack_source_ip

        logger.info(
            f"Generating port scan: {attacker_ip} -> {target_device_ip}"
        )

        if scan_ot_ports:
            generator = generate_ot_port_scan(
                src_ip=attacker_ip,
                dst_ip=target_device_ip,
                start_time_ms=start_time_ms,
            )
        else:
            # Common ports
            ports = [21, 22, 23, 25, 80, 110, 443, 445, 3389]
            generator = generate_port_scan_sequence(
                src_ip=attacker_ip,
                dst_ip=target_device_ip,
                ports=ports,
                scan_type=self.config.scan_type,
                start_time_ms=start_time_ms,
            )

        for timestamp, packet in generator:
            yield PacketEvent(
                timestamp_ms=timestamp,
                packet=packet,
                event_type="port_scan",
                metadata={
                    "attacker_ip": attacker_ip,
                    "scan_type": self.config.scan_type,
                    "mitre_technique": "T0846",
                },
            )

    def generate_all_traffic(
        self,
        internal_devices: list[str],
        start_time_ms: int = 0,
        duration_ms: int = 300000,
    ) -> Iterator[PacketEvent]:
        """Generate all configured external traffic types.

        Args:
            internal_devices: List of internal device IPs
            start_time_ms: Starting timestamp
            duration_ms: Total duration

        Yields:
            PacketEvent instances sorted by timestamp
        """
        events: list[PacketEvent] = []

        if not internal_devices:
            logger.warning("No internal devices provided for external traffic")
            return

        # Select a compromised device
        compromised_ip = random.choice(internal_devices)

        # Generate C2 beaconing
        if self.config.enable_c2:
            events.extend(
                self.generate_c2_beaconing(
                    internal_device_ip=compromised_ip,
                    start_time_ms=start_time_ms,
                    duration_ms=duration_ms,
                )
            )

        # Generate exfiltration
        if self.config.enable_exfil:
            # Simulate exfiltrating some data
            fake_data = bytes(random.getrandbits(8) for _ in range(self.config.exfil_data_size))

            if self.config.exfil_protocol == "dns":
                events.extend(
                    self.generate_dns_tunnel(
                        internal_device_ip=compromised_ip,
                        data=fake_data,
                        start_time_ms=start_time_ms + duration_ms // 4,
                    )
                )
            else:
                events.extend(
                    self.generate_http_exfil(
                        internal_device_ip=compromised_ip,
                        data=fake_data,
                        start_time_ms=start_time_ms + duration_ms // 4,
                    )
                )

        # Generate exploit attempts
        if self.config.enable_exploits and self.config.exploit_patterns:
            target_ip = random.choice(internal_devices)
            for pattern in self.config.exploit_patterns:
                events.extend(
                    self.generate_exploit_attempt(
                        target_device_ip=target_ip,
                        exploit_name=pattern,
                        start_time_ms=start_time_ms + duration_ms // 2,
                    )
                )

        # Generate reconnaissance
        if self.config.enable_recon:
            target_ip = random.choice(internal_devices)
            events.extend(
                self.generate_port_scan(
                    target_device_ip=target_ip,
                    start_time_ms=start_time_ms,
                    scan_ot_ports=self.config.scan_ot_ports,
                )
            )

        # Sort events by timestamp and yield
        events.sort(key=lambda e: e.timestamp_ms)
        for event in events:
            yield event

    @staticmethod
    def list_available_patterns() -> dict[str, list[dict]]:
        """List all available patterns for external traffic.

        Returns:
            Dictionary with beacon patterns and exploit patterns
        """
        return {
            "beacon_patterns": list_beacon_patterns(),
            "exploit_patterns": list_exploit_patterns(),
        }
