# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""C2 beaconing pattern configurations.

Defines timing patterns and behaviors for command-and-control
beaconing that mimic real-world malware families.

Pattern types:
- Fixed interval: Regular, predictable beacons (easily detected)
- Jittered: Random variation in timing (harder to detect)
- Bursty: Clusters of activity with long sleeps
- Working hours: Active during business hours only
- Adaptive: Changes interval based on response
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator


class BeaconPatternType(str, Enum):
    """Types of C2 beaconing patterns."""

    FIXED = "fixed"  # Regular interval (e.g., every 60s exactly)
    JITTERED = "jittered"  # Interval with random jitter (e.g., 60s ± 15%)
    BURSTY = "bursty"  # Bursts of activity then long sleep
    WORKING_HOURS = "working_hours"  # Active 9-5 local time
    SLOW_BURN = "slow_burn"  # Very slow, stealthy beaconing
    ADAPTIVE = "adaptive"  # Changes based on command received


@dataclass
class BeaconPattern:
    """C2 beacon timing pattern configuration."""

    pattern_type: BeaconPatternType = BeaconPatternType.JITTERED
    name: str = "Default Beacon"
    description: str = ""

    # Base timing (milliseconds)
    base_interval_ms: int = 60000  # 1 minute default

    # Jitter configuration
    jitter_pct: float = 0.15  # 15% jitter
    min_interval_ms: int = 5000  # Minimum 5 seconds
    max_interval_ms: int = 3600000  # Maximum 1 hour

    # Burst pattern configuration
    burst_count: int = 5  # Packets per burst
    burst_interval_ms: int = 1000  # Interval within burst
    sleep_after_burst_ms: int = 300000  # 5 min sleep after burst

    # Working hours configuration
    work_start_hour: int = 9
    work_end_hour: int = 17
    weekend_active: bool = False

    # Slow burn configuration
    slow_interval_ms: int = 3600000  # 1 hour

    # IDS evasion features
    randomize_packet_size: bool = True
    use_ssl: bool = False
    mimic_legitimate_traffic: bool = False

    # MITRE ATT&CK mapping
    mitre_technique: str = "T0885"  # Command and Control

    def get_next_interval(self, is_burst_mode: bool = False) -> int:
        """Calculate the next beacon interval.

        Args:
            is_burst_mode: Whether currently in burst mode

        Returns:
            Interval in milliseconds
        """
        if self.pattern_type == BeaconPatternType.FIXED:
            return self.base_interval_ms

        elif self.pattern_type == BeaconPatternType.JITTERED:
            jitter = int(self.base_interval_ms * self.jitter_pct)
            interval = self.base_interval_ms + random.randint(-jitter, jitter)
            return max(self.min_interval_ms, min(self.max_interval_ms, interval))

        elif self.pattern_type == BeaconPatternType.BURSTY:
            if is_burst_mode:
                return self.burst_interval_ms + random.randint(-100, 100)
            else:
                return self.sleep_after_burst_ms + random.randint(-10000, 10000)

        elif self.pattern_type == BeaconPatternType.SLOW_BURN:
            jitter = int(self.slow_interval_ms * 0.3)
            return self.slow_interval_ms + random.randint(-jitter, jitter)

        else:
            return self.base_interval_ms

    def generate_intervals(self, count: int) -> Iterator[int]:
        """Generate a sequence of beacon intervals.

        Args:
            count: Number of intervals to generate

        Yields:
            Interval values in milliseconds
        """
        burst_remaining = 0

        for _ in range(count):
            if self.pattern_type == BeaconPatternType.BURSTY:
                if burst_remaining > 0:
                    burst_remaining -= 1
                    yield self.get_next_interval(is_burst_mode=True)
                else:
                    # Start new burst
                    burst_remaining = self.burst_count - 1
                    yield self.sleep_after_burst_ms
            else:
                yield self.get_next_interval()


# Pre-defined beacon patterns mimicking known malware families


COBALT_STRIKE_PATTERN = BeaconPattern(
    pattern_type=BeaconPatternType.JITTERED,
    name="Cobalt Strike Default",
    description="Default Cobalt Strike beacon pattern",
    base_interval_ms=60000,
    jitter_pct=0.37,  # CS default jitter
    mitre_technique="T0885",
)

METASPLOIT_PATTERN = BeaconPattern(
    pattern_type=BeaconPatternType.FIXED,
    name="Metasploit Meterpreter",
    description="Default Meterpreter reverse shell pattern",
    base_interval_ms=5000,
    jitter_pct=0.0,
    mitre_technique="T0885",
)

APT_SLOW_PATTERN = BeaconPattern(
    pattern_type=BeaconPatternType.SLOW_BURN,
    name="APT Slow Beacon",
    description="Slow, stealthy APT-style beaconing",
    slow_interval_ms=7200000,  # 2 hours
    jitter_pct=0.5,
    mitre_technique="T0885",
)

RAPID_EXFIL_PATTERN = BeaconPattern(
    pattern_type=BeaconPatternType.BURSTY,
    name="Rapid Exfiltration",
    description="Burst pattern for quick data exfiltration",
    burst_count=10,
    burst_interval_ms=500,
    sleep_after_burst_ms=600000,  # 10 min between bursts
    mitre_technique="T0882",
)

DNS_TUNNEL_PATTERN = BeaconPattern(
    pattern_type=BeaconPatternType.JITTERED,
    name="DNS Tunnel",
    description="DNS-based C2 tunneling pattern",
    base_interval_ms=30000,
    jitter_pct=0.2,
    mitre_technique="T0884",
)


# Pattern registry
BEACON_PATTERNS = {
    "cobalt_strike": COBALT_STRIKE_PATTERN,
    "metasploit": METASPLOIT_PATTERN,
    "apt_slow": APT_SLOW_PATTERN,
    "rapid_exfil": RAPID_EXFIL_PATTERN,
    "dns_tunnel": DNS_TUNNEL_PATTERN,
    "fixed_60s": BeaconPattern(
        pattern_type=BeaconPatternType.FIXED,
        name="Fixed 60s Beacon",
        description="Regular 60-second beacon interval",
        base_interval_ms=60000,
    ),
    "fixed_5m": BeaconPattern(
        pattern_type=BeaconPatternType.FIXED,
        name="Fixed 5m Beacon",
        description="Regular 5-minute beacon interval",
        base_interval_ms=300000,
    ),
    "jittered_1m": BeaconPattern(
        pattern_type=BeaconPatternType.JITTERED,
        name="Jittered 1m Beacon",
        description="1-minute beacon with 15% jitter",
        base_interval_ms=60000,
        jitter_pct=0.15,
    ),
    "jittered_5m": BeaconPattern(
        pattern_type=BeaconPatternType.JITTERED,
        name="Jittered 5m Beacon",
        description="5-minute beacon with 20% jitter",
        base_interval_ms=300000,
        jitter_pct=0.2,
    ),
}


def get_beacon_pattern(name: str) -> BeaconPattern:
    """Get a beacon pattern by name.

    Args:
        name: Pattern name

    Returns:
        BeaconPattern instance

    Raises:
        KeyError: If pattern not found
    """
    if name not in BEACON_PATTERNS:
        raise KeyError(f"Unknown beacon pattern: {name}")
    return BEACON_PATTERNS[name]


def list_beacon_patterns() -> list[dict]:
    """List all available beacon patterns.

    Returns:
        List of pattern summaries
    """
    return [
        {
            "name": key,
            "display_name": pattern.name,
            "description": pattern.description,
            "pattern_type": pattern.pattern_type.value,
            "base_interval_ms": pattern.base_interval_ms,
            "mitre_technique": pattern.mitre_technique,
        }
        for key, pattern in BEACON_PATTERNS.items()
    ]
