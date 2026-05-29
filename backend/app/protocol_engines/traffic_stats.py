# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Traffic statistics collection for live dashboard.

Tracks per-protocol packet counts, byte counts, and computes rolling rates.
Thread-safe: the orchestrator writes stats from a background thread while
the status reporter reads them from the async main loop.
"""

import threading
import time
from dataclasses import dataclass


@dataclass
class ProtocolStats:
    """Per-protocol traffic statistics."""

    protocol: str
    packets: int = 0
    bytes: int = 0
    flow_count: int = 0


class TrafficStats:
    """Aggregate traffic statistics for a single scenario deployment.

    Thread-safe via a lock around all mutable state.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total_packets: int = 0
        self.total_bytes: int = 0
        self.started_at: float = time.time()
        self._protocol_stats: dict[str, ProtocolStats] = {}
        # Rolling rate samples: (timestamp, cumulative_packets, cumulative_bytes)
        # Sampled roughly every 1 second, keeps last 60 samples (1 minute window)
        self._rate_samples: list[tuple[float, int, int]] = []
        self._last_sample_time: float = 0.0
        self._max_samples: int = 60

    def register_flow(self, flow_id: str, protocol: str) -> None:
        """Register a flow so protocol flow_count is accurate."""
        with self._lock:
            if protocol not in self._protocol_stats:
                self._protocol_stats[protocol] = ProtocolStats(protocol=protocol)
            self._protocol_stats[protocol].flow_count += 1

    def record_packet(self, protocol: str, packet_size: int) -> None:
        """Record a single packet. Called from the orchestrator thread."""
        now = time.monotonic()
        with self._lock:
            self.total_packets += 1
            self.total_bytes += packet_size

            if protocol not in self._protocol_stats:
                self._protocol_stats[protocol] = ProtocolStats(protocol=protocol)
            ps = self._protocol_stats[protocol]
            ps.packets += 1
            ps.bytes += packet_size

            # Sample for rate calculation (~1 second interval)
            if now - self._last_sample_time >= 1.0:
                self._rate_samples.append(
                    (now, self.total_packets, self.total_bytes)
                )
                if len(self._rate_samples) > self._max_samples:
                    self._rate_samples.pop(0)
                self._last_sample_time = now

    def compute_rates(self) -> tuple[float, float]:
        """Compute current packets/sec and bytes/sec from the rolling window.

        Returns:
            (packets_per_second, bytes_per_second)
        """
        with self._lock:
            if len(self._rate_samples) < 2:
                return 0.0, 0.0

            oldest = self._rate_samples[0]
            newest = self._rate_samples[-1]
            dt = newest[0] - oldest[0]
            if dt <= 0:
                return 0.0, 0.0

            pps = (newest[1] - oldest[1]) / dt
            bps = (newest[2] - oldest[2]) / dt
            return pps, bps

    def snapshot(self) -> dict:
        """Create a JSON-serializable snapshot for transmission in STATUS messages."""
        pps, bps = self.compute_rates()
        with self._lock:
            protocol_breakdown = {}
            for proto, ps in self._protocol_stats.items():
                protocol_breakdown[proto] = {
                    "packets": ps.packets,
                    "bytes": ps.bytes,
                    "flow_count": ps.flow_count,
                }

            return {
                "total_packets": self.total_packets,
                "total_bytes": self.total_bytes,
                "flow_count": sum(
                    ps.flow_count for ps in self._protocol_stats.values()
                ),
                "packets_per_second": round(pps, 1),
                "bytes_per_second": round(bps, 1),
                "protocol_stats": protocol_breakdown,
            }
