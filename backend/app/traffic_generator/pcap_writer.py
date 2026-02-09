"""PCAP file writer wrapper."""

import os
import time
from pathlib import Path

from scapy.utils import PcapWriter as ScapyPcapWriter


class PcapWriter:
    """Wrapper around Scapy's PcapWriter with tracking."""

    def __init__(self, output_path: str | Path):
        """Initialize PCAP writer.

        Args:
            output_path: Path where PCAP file will be written
        """
        self.output_path = Path(output_path)
        self.packet_count = 0
        self.file_size = 0
        self._time_anchor: float | None = None

        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize Scapy's PcapWriter
        self._writer = ScapyPcapWriter(str(self.output_path), append=False, sync=True)
        self._header_written = False

    def write_packet(self, packet_bytes: bytes, timestamp: float | None = None) -> None:
        """Write a packet to the PCAP file.

        Args:
            packet_bytes: Raw packet bytes
            timestamp: Optional timestamp (milliseconds)
        """
        # Ensure PCAP header is written (sets linktype for raw bytes)
        if not self._header_written:
            self._writer.write_header(packet_bytes)
            self._header_written = True

        # Anchor to wall-clock time so PCAPs don't start at epoch 0
        if self._time_anchor is None:
            self._time_anchor = time.time()

        # Scapy expects timestamp in seconds (float)
        if timestamp is not None:
            timestamp_sec = self._time_anchor + (timestamp / 1000.0)
        else:
            timestamp_sec = None

        self._writer.write_packet(packet_bytes, sec=timestamp_sec)
        self.packet_count += 1

    def close(self) -> None:
        """Close the PCAP file and update file size."""
        if self._writer:
            self._writer.close()
            self._writer = None

        # Get final file size
        if self.output_path.exists():
            self.file_size = os.path.getsize(self.output_path)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Ensure file is closed on deletion."""
        if hasattr(self, "_writer") and self._writer:
            self.close()
