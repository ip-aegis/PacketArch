"""Base class for protocol-specific pattern extraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from scapy.packet import Packet


@dataclass
class ExtractedPacketInfo:
    """Information extracted from a single packet."""

    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int | None = None
    dst_port: int | None = None
    protocol: str = ""
    direction: str = "unknown"  # request, response, unknown
    function_code: int | None = None
    payload_size: int = 0
    raw_data: bytes = b""
    metadata: dict = field(default_factory=dict)


@dataclass
class ExtractedFlowInfo:
    """Information extracted from a flow (bidirectional communication)."""

    src_ip: str
    dst_ip: str
    protocol: str
    packets: list[ExtractedPacketInfo] = field(default_factory=list)
    request_count: int = 0
    response_count: int = 0
    inter_arrival_times: list[float] = field(default_factory=list)
    request_response_delays: list[float] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class ProtocolExtractor(ABC):
    """Base class for protocol-specific pattern extraction.

    Implement this class for each protocol to extract:
    - Function code distributions
    - Register/address access patterns
    - Payload structures
    - Request/response pairs
    - Protocol-specific identity info
    """

    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Return the protocol name (e.g., 'modbus_tcp', 's7comm')."""
        pass

    @property
    @abstractmethod
    def well_known_ports(self) -> list[int]:
        """Return list of well-known ports for this protocol."""
        pass

    @abstractmethod
    def can_handle(self, packet: Packet) -> bool:
        """Check if this extractor can handle the given packet.

        Args:
            packet: Scapy packet to check

        Returns:
            True if this extractor can process the packet
        """
        pass

    @abstractmethod
    def extract_packet_info(self, packet: Packet) -> ExtractedPacketInfo | None:
        """Extract structured info from a packet.

        Args:
            packet: Scapy packet to process

        Returns:
            ExtractedPacketInfo with parsed data, or None if parsing failed
        """
        pass

    @abstractmethod
    def is_request(self, packet: Packet) -> bool:
        """Determine if packet is a request (vs response).

        Args:
            packet: Scapy packet to check

        Returns:
            True if packet is a request
        """
        pass

    def extract_identity_info(self, packet: Packet) -> dict | None:
        """Extract device identity info if available in packet.

        Override in subclasses for protocols that support device identification
        (e.g., Modbus FC43, S7 SZL, EtherNet/IP List Identity).

        Args:
            packet: Scapy packet to check

        Returns:
            Dictionary with identity info, or None if not available
        """
        return None

    @abstractmethod
    def build_patterns(self, packets: list[ExtractedPacketInfo]) -> dict[str, Any]:
        """Build learned patterns from extracted packet data.

        Args:
            packets: List of extracted packet info from analysis

        Returns:
            Dictionary with pattern data ready for LearnedProtocolPattern model
        """
        pass

    def calculate_confidence(self, sample_count: int, pattern_consistency: float = 1.0) -> float:
        """Calculate confidence score based on sample size and consistency.

        Uses the standardized confidence calculation from app.ai_services.confidence.

        Args:
            sample_count: Number of samples analyzed
            pattern_consistency: How consistent the patterns are (0-1)

        Returns:
            Confidence score between 0 and 1
        """
        from app.ai_services.confidence import (
            ConfidenceFactors,
            calculate_confidence as calc_conf,
        )

        factors = ConfidenceFactors(
            sample_count=sample_count,
            pattern_consistency=pattern_consistency,
        )
        return calc_conf(factors)
