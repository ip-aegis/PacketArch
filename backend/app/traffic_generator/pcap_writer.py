# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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

        # Scapy's PcapWriter.write_packet(sec=<float>) does NOT split a
        # float into seconds + microseconds — when usec is omitted, the
        # fractional part is dropped and every packet snaps to the
        # enclosing integer second. Split explicitly so PCAPs preserve
        # the sub-millisecond timing that protocol engines schedule.
        if timestamp is not None:
            timestamp_sec_float = self._time_anchor + (timestamp / 1000.0)
            sec = int(timestamp_sec_float)
            usec = int(round((timestamp_sec_float - sec) * 1_000_000))
            if usec >= 1_000_000:
                sec += 1
                usec -= 1_000_000
            self._writer.write_packet(packet_bytes, sec=sec, usec=usec)
        else:
            self._writer.write_packet(packet_bytes)
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
