"""Learned device fingerprint model for storing device signature templates.

.. deprecated::
    This model is DEPRECATED. Use DeviceTemplate with source=PCAP_LEARNED instead.

    The LearnedDeviceFingerprint table has been superseded by the DeviceTemplate table,
    which consolidates built-in vendor fingerprints, PCAP-learned fingerprints,
    and user-created fingerprints into a single unified model.

    Migration path:
    - New PCAP learning should create DeviceTemplate records with source=PCAP_LEARNED
    - Use template_db_to_fingerprint_dict() for backward-compatible dicts
    - This table is retained for rollback capability during transition

    See: backend/app/models/device_template.py

Fingerprints are GENERIC TEMPLATES that capture vendor characteristics, TCP stack
signatures, protocol identities, and behavioral patterns. They are NOT tied to
specific IP addresses or MAC addresses.

Multiple observations from different devices are aggregated into unified templates
based on signature similarity, enabling fingerprints learned from one PCAP to be
applied to any matching device in generated traffic.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeviceRole(str, Enum):
    """Role of device in OT network."""

    MASTER = "master"  # Initiates requests (HMI, SCADA, Engineering Station)
    SLAVE = "slave"  # Responds to requests (PLC, RTU, I/O)
    BOTH = "both"  # Can act as both (some PLCs)
    UNKNOWN = "unknown"


class LearnedDeviceFingerprint(Base):
    """Device fingerprint templates learned from PCAP traffic analysis.

    .. deprecated::
        This model is deprecated. Use DeviceTemplate with source=PCAP_LEARNED instead.
        See backend/app/models/device_template.py for the new unified model.

    These are GENERIC TEMPLATES, not specific device instances. They capture:
    - TCP stack characteristics (TTL, window size, options)
    - Vendor identification (from OUI patterns or protocol identity)
    - Response timing distributions (statistical models)
    - Protocol-specific identity info (vendor, model, firmware)
    - Behavioral patterns (device role, supported protocols)

    Fingerprints are aggregated from multiple device observations to create
    reusable templates that can be applied to scenario devices.
    """

    __tablename__ = "learned_device_fingerprints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Source PCAP
    pcap_capture_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pcap_captures.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # ==================== VENDOR IDENTIFICATION ====================
    # Inferred vendor from OUI patterns or protocol identity
    inferred_vendor: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Vendor inferred from OUI patterns or protocol identity",
    )

    # Device type/category (e.g., "PLC", "HMI", "RTU", "Drive")
    device_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Device type/category inferred from behavior and protocols",
    )

    # OUI patterns observed (for vendor matching)
    oui_patterns: Mapped[list | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="MAC OUI patterns associated with this fingerprint (first 3 octets)",
    )

    # ==================== TCP STACK SIGNATURE ====================
    tcp_signature: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="TCP stack fingerprint: {ttl, window_size, mss, options, df_flag, etc.}",
    )

    # ==================== RESPONSE TIMING ====================
    response_timings: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Response timing distributions by protocol: {protocol: {min, max, mean, std, distribution}}",
    )

    # ==================== PROTOCOL IDENTITIES ====================
    # Protocol-specific identity info (vendor, model, firmware from protocol messages)
    protocol_identities: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Protocol-specific IDs: {modbus: {vendor, product_code}, s7: {module_type, firmware}, enip: {product_name, serial}}",
    )

    # ==================== BEHAVIORAL PATTERNS ====================
    # Device role in network communications
    role: Mapped[str] = mapped_column(
        String(20),
        default="unknown",
        nullable=False,
        comment="Typical device role: master, slave, both, unknown",
    )

    # Protocols this fingerprint is associated with
    active_protocols: Mapped[list | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Protocols associated with this fingerprint",
    )

    # Typical ports used (for protocol identification)
    typical_ports: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Typical ports: {tcp: [ports], udp: [ports]}",
    )

    # ==================== AGGREGATION METADATA ====================
    # Number of unique devices this fingerprint was derived from
    observation_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Number of unique device observations aggregated into this fingerprint",
    )

    # Total packets analyzed to build this fingerprint
    total_packets_analyzed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total packets analyzed to build this fingerprint",
    )

    # ==================== QUALITY METRICS ====================
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Confidence score 0-1 based on observation quality and consistency",
    )

    # Signature consistency score (how consistent observations were)
    consistency_score: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
        comment="How consistent the aggregated observations were (0-1)",
    )

    # ==================== USER METADATA ====================
    name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Human-readable name for this fingerprint template",
    )

    # Tags for categorization
    tags: Mapped[list | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="User-defined tags for categorization",
    )

    # ==================== TIMESTAMPS ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ==================== RELATIONSHIPS ====================
    pcap_capture: Mapped["PcapCapture"] = relationship(
        "PcapCapture",
        back_populates="device_fingerprints",
    )

    def __repr__(self) -> str:
        vendor = self.inferred_vendor or "Unknown"
        device = self.device_type or "Device"
        return f"<LearnedDeviceFingerprint {vendor} {device} (conf={self.confidence:.2f})>"

    def get_signature_hash(self) -> str:
        """Generate a hash for signature-based matching.

        Used to identify similar fingerprints for aggregation.
        """
        import hashlib
        import json

        sig_data = {
            "tcp": self.tcp_signature or {},
            "vendor": self.inferred_vendor,
            "protocols": sorted(self.active_protocols or []),
        }
        sig_str = json.dumps(sig_data, sort_keys=True)
        return hashlib.sha256(sig_str.encode()).hexdigest()[:16]


# Forward reference for relationship
from app.models.pcap_capture import PcapCapture  # noqa: E402, F401
