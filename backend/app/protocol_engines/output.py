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

    def write_packet(self, packet_bytes: bytes, timestamp_ms: float) -> None:
        """Write/inject a packet.

        Args:
            packet_bytes: Raw packet bytes (Ethernet frame)
            timestamp_ms: Timestamp in milliseconds
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

    def write_packet(self, packet_bytes: bytes, timestamp_ms: float) -> None:
        self._writer.write_packet(packet_bytes, timestamp_ms)

    def close(self) -> None:
        self._writer.close()

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

    def write_packet(self, packet_bytes: bytes, timestamp_ms: float) -> None:
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
