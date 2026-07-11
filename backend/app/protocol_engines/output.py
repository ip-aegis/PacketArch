# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Packet output abstraction for PCAP writing and live network injection."""

import logging
import time
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class PacketOutput(Protocol):
    """Protocol for packet output destinations.

    Implementations handle either writing packets to a PCAP file
    or injecting them onto a live network interface.
    """

    packet_count: int
    bytes_sent: int

    def write_packet(
        self,
        packet_bytes: bytes,
        timestamp_ms: float,
        is_attack: bool = False,
        flow_id: str | None = None,
    ) -> None:
        """Write/inject a packet.

        Args:
            packet_bytes: Raw packet bytes (Ethernet frame)
            timestamp_ms: Timestamp in milliseconds
            is_attack: True if this packet was emitted by the attack
                orchestrator (``flow_id`` prefixed ``__attack__``). Single-file
                outputs ignore it; :class:`SplitPcapOutput` uses it to route
                the packet into the attack-only / baseline PCAPs.
            flow_id: Owning flow identifier. Ignored by single-file/live
                outputs; :class:`SpanPcapOutput` (and the live conductor) use
                it to look up the packet's per-SPAN segment plan.
        """
        ...

    def close(self) -> None:
        """Finalize output (close file, flush buffers, etc.)."""
        ...


class PcapOutput:
    """Write packets to a PCAP file using Scapy's PcapWriter.

    Wraps the existing PcapWriter from traffic_generator.pcap_writer.
    """

    def __init__(self, output_path: str) -> None:
        from app.traffic_generator.pcap_writer import PcapWriter

        self._writer = PcapWriter(output_path)

    @property
    def packet_count(self) -> int:
        return self._writer.packet_count

    @property
    def bytes_sent(self) -> int:
        return self._writer.file_size

    @property
    def file_size(self) -> int:
        return self._writer.file_size

    def write_packet(
        self,
        packet_bytes: bytes,
        timestamp_ms: float,
        is_attack: bool = False,
        flow_id: str | None = None,
    ) -> None:
        self._writer.write_packet(packet_bytes, timestamp_ms)

    def close(self) -> None:
        self._writer.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SplitPcapOutput:
    """Fan a single generation run out into up to three PCAP files.

    Routes each packet by its ``is_attack`` flag so one run yields, in the
    same virtual timeline:

    * ``combined`` — every packet (the regular PCAP, unchanged from today)
    * ``baseline`` — only legitimate traffic (attack packets removed)
    * ``attack``   — only the malicious packets (the ``__attack__`` flows)

    Any path may be ``None`` to skip that file. Timestamps are shared, so the
    three files line up packet-for-packet on the same clock.
    """

    def __init__(
        self,
        combined_path: str | None = None,
        baseline_path: str | None = None,
        attack_path: str | None = None,
    ) -> None:
        from app.traffic_generator.pcap_writer import PcapWriter

        self._combined = PcapWriter(combined_path) if combined_path else None
        self._baseline = PcapWriter(baseline_path) if baseline_path else None
        self._attack = PcapWriter(attack_path) if attack_path else None
        self.packet_count = 0
        self.bytes_sent = 0
        self.attack_packet_count = 0
        self.baseline_packet_count = 0

    def write_packet(
        self,
        packet_bytes: bytes,
        timestamp_ms: float,
        is_attack: bool = False,
        flow_id: str | None = None,
    ) -> None:
        if self._combined is not None:
            self._combined.write_packet(packet_bytes, timestamp_ms)
        if is_attack:
            self.attack_packet_count += 1
            if self._attack is not None:
                self._attack.write_packet(packet_bytes, timestamp_ms)
        else:
            self.baseline_packet_count += 1
            if self._baseline is not None:
                self._baseline.write_packet(packet_bytes, timestamp_ms)
        self.packet_count += 1
        self.bytes_sent += len(packet_bytes)

    def close(self) -> None:
        for writer in (self._combined, self._baseline, self._attack):
            if writer is not None:
                writer.close()

    def file_size(self, kind: str) -> int:
        """Final byte size of the ``combined`` / ``baseline`` / ``attack`` file."""
        writer = {
            "combined": self._combined,
            "baseline": self._baseline,
            "attack": self._attack,
        }.get(kind)
        return writer.file_size if writer is not None else 0

    def packet_count_for(self, kind: str) -> int:
        return {
            "combined": self.packet_count,
            "baseline": self.baseline_packet_count,
            "attack": self.attack_packet_count,
        }.get(kind, 0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class LiveOutput:
    """Inject packets onto a live network interface using Scapy.

    Uses real-time scheduling: sleeps until the packet's timestamp,
    then injects via scapy.sendp(). Designed for the remote agent.
    """

    def __init__(self, interface: str) -> None:
        self.interface = interface
        self.packet_count = 0
        self.bytes_sent = 0
        self._start_time: float | None = None
        self._first_event_ms: float | None = None

    def write_packet(
        self,
        packet_bytes: bytes,
        timestamp_ms: float,
        is_attack: bool = False,
        flow_id: str | None = None,
    ) -> None:
        from scapy.packet import Raw
        from scapy.sendrecv import sendp

        now = time.monotonic()

        # Initialize timing anchor on first packet
        if self._start_time is None:
            self._start_time = now
            self._first_event_ms = timestamp_ms

        # Calculate how long to wait before injecting
        elapsed_ms = (now - self._start_time) * 1000.0
        target_ms = timestamp_ms - self._first_event_ms
        wait_ms = target_ms - elapsed_ms

        if wait_ms > 1.0:  # Only sleep if > 1ms to avoid overhead
            time.sleep(wait_ms / 1000.0)

        sendp(Raw(packet_bytes), iface=self.interface, verbose=False)
        self.packet_count += 1
        self.bytes_sent += len(packet_bytes)

        if self.packet_count % 100 == 0:
            logger.info(f"Injected {self.packet_count} packets on {self.interface}")

    def close(self) -> None:
        logger.info(
            f"Live output closed: {self.packet_count} packets "
            f"injected on {self.interface}"
        )


def span_to_filename(span_id: str) -> str:
    """'zone:z-cell' -> 'zone_z-cell', 'core' -> 'core' (safe file stem part)."""
    return span_id.replace(":", "_")


class SpanPcapOutput:
    """Fan one generation run out into one PCAP per topology SPAN.

    The generate-once/render-many PCAP sink: each canonical frame is routed
    through a :class:`TopologyRouter` into its per-segment reframed copies,
    and each copy is written to that segment's SPAN file. Proves cross-sensor
    coherence with zero live infrastructure (Phase 1).

    ``base_path`` is the combined-run path; per-span files are written
    alongside it as ``<stem>_<span>.pcap``. A ``combined`` file (every
    canonical frame, unreframed) is always written too, so the run stays a
    drop-in for the normal PCAP path.
    """

    def __init__(self, base_path: str, plan: dict) -> None:
        from pathlib import Path

        from app.protocol_engines.topology_router import TopologyRouter
        from app.traffic_generator.pcap_writer import PcapWriter

        self._router = TopologyRouter(plan)
        self.packet_count = 0
        self.bytes_sent = 0
        self.span_packet_counts: dict[str, int] = {}

        stem = str(Path(base_path).with_suffix(""))
        self._combined = PcapWriter(base_path)
        self._span_paths: dict[str, str] = {}
        self._span_writers: dict[str, "PcapWriter"] = {}
        for span_id in self._router.span_ids:
            path = f"{stem}_{span_to_filename(span_id)}.pcap"
            self._span_paths[span_id] = path
            self._span_writers[span_id] = PcapWriter(path)
            self.span_packet_counts[span_id] = 0

    def write_packet(
        self,
        packet_bytes: bytes,
        timestamp_ms: float,
        is_attack: bool = False,
        flow_id: str | None = None,
    ) -> None:
        self._combined.write_packet(packet_bytes, timestamp_ms)
        self.packet_count += 1
        self.bytes_sent += len(packet_bytes)
        for span_id, reframed in self._router.route(packet_bytes, flow_id):
            writer = self._span_writers.get(span_id)
            if writer is None:  # a span the plan didn't declare — create lazily
                from pathlib import Path

                from app.traffic_generator.pcap_writer import PcapWriter

                stem = str(Path(self._combined_path()).with_suffix(""))
                path = f"{stem}_{span_to_filename(span_id)}.pcap"
                writer = PcapWriter(path)
                self._span_writers[span_id] = writer
                self._span_paths[span_id] = path
                self.span_packet_counts[span_id] = 0
            writer.write_packet(reframed, timestamp_ms)
            self.span_packet_counts[span_id] += 1

    def _combined_path(self) -> str:
        return self._combined.output_path if hasattr(self._combined, "output_path") else ""

    def span_paths(self) -> dict[str, str]:
        return dict(self._span_paths)

    def close(self) -> None:
        self._combined.close()
        for writer in self._span_writers.values():
            writer.close()
