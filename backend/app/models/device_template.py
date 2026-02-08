"""Unified device template model for storing device signature templates.

DeviceTemplate consolidates the previous VendorFingerprint and LearnedDeviceFingerprint
models into a single unified structure with a source discriminator.

This enables:
- Consistent API for both built-in and learned templates
- Unified matching algorithm for finding templates by vendor/TCP signature
- Single table with proper indexing for efficient queries
- Clear provenance tracking via the source field
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, Integer, String, func, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TemplateSource(str, Enum):
    """Source/provenance of the device template."""

    VENDOR_BUILTIN = "vendor_builtin"  # Pre-packaged vendor fingerprints
    USER_CREATED = "user_created"  # Manually created by user


class DeviceTemplate(Base):
    """Unified device fingerprint/template for traffic generation.

    Unified device template table. Templates can be:

    - VENDOR_BUILTIN: Pre-packaged fingerprints for known vendors (Siemens, Rockwell, etc.)
    - USER_CREATED: Custom templates created/modified by users

    Templates provide:
    - Network signatures (OUI patterns, TCP stack characteristics)
    - Protocol-specific identities (Modbus, EtherNet/IP, PROFINET, etc.)
    - Response timing distributions for realistic traffic generation
    - Behavioral patterns (device role, supported protocols)
    """

    __tablename__ = "device_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ==================== SOURCE/PROVENANCE ====================
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Template source: vendor_builtin, user_created",
    )

    # ==================== VENDOR IDENTIFICATION ====================
    vendor: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Vendor name (e.g., 'Siemens', 'Rockwell Automation')",
    )

    vendor_family: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Vendor product family (e.g., 'S7-1200', 'ControlLogix')",
    )

    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Specific model number",
    )

    firmware_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Firmware version string",
    )

    device_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Device type/category (PLC, HMI, RTU, Drive, etc.)",
    )

    # ==================== NETWORK SIGNATURES ====================
    oui_patterns: Mapped[list | None] = mapped_column(
        ARRAY(String(17)),
        nullable=True,
        comment="MAC OUI prefixes (first 3 octets) for vendor matching",
    )

    tcp_signature: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="TCP stack fingerprint: {ttl, window_size, mss, options, df_flag}",
    )

    # ==================== PROTOCOL IDENTITIES ====================
    # Unified JSONB for all protocol identities (preferred for new templates)
    protocol_identities: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Protocol-specific identities: {modbus: {...}, s7: {...}, enip: {...}}",
    )

    # Legacy per-protocol columns (for backward compatibility with built-in fingerprints)
    modbus_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Modbus FC 43 Read Device Identification response",
    )
    ethernet_ip_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="EtherNet/IP ListIdentity response data",
    )
    profinet_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="PROFINET DCP identity block data",
    )
    s7_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="S7comm SZL identity data",
    )
    snmp_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="SNMP system identity (sys_descr, sys_object_id)",
    )
    bacnet_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="BACnet I-Am identity (vendor_id, model_name)",
    )
    opc_ua_identity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="OPC UA Server identity (manufacturer_name, product_name, application_uri)",
    )

    # ==================== TIMING ====================
    response_timings: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Response timing distributions: {protocol: {min, max, mean, std, distribution}}",
    )

    # ==================== BEHAVIORAL PATTERNS ====================
    role: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Typical device role: master, slave, both, unknown",
    )

    active_protocols: Mapped[list | None] = mapped_column(
        ARRAY(String(50)),
        nullable=True,
        comment="Protocols this template supports",
    )

    typical_ports: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Typical ports: {tcp: [ports], udp: [ports]}",
    )

    # Protocol quirks and special behaviors
    protocol_quirks: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Protocol-specific behavioral quirks",
    )

    error_behavior: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Error response behavior configuration",
    )

    # ==================== QUALITY METRICS ====================
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
        comment="Confidence score 0-1 (1.0 for built-in, varies for learned)",
    )

    sample_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Number of observations/samples this template is based on",
    )

    consistency_score: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
        comment="How consistent aggregated observations were (for learned templates)",
    )

    # ==================== METADATA ====================
    name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Human-readable name for this template",
    )

    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Description of the template",
    )

    tags: Mapped[list | None] = mapped_column(
        ARRAY(String(50)),
        nullable=True,
        comment="User-defined tags for categorization",
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether this template is active and available for use",
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

    # ==================== INDEXES ====================
    # Note: Single-column indexes on source, vendor, device_type, vendor_family
    # are created automatically via index=True on the column definitions above.
    # Only composite indexes need to be declared here.
    __table_args__ = (
        Index("ix_device_templates_vendor_model", "vendor", "model"),
        Index("ix_device_templates_source_vendor", "source", "vendor"),
    )

    def __repr__(self) -> str:
        vendor = self.vendor or "Unknown"
        model = self.model or self.vendor_family or self.device_type or ""
        return f"<DeviceTemplate [{self.source}] {vendor} {model}>"

    def get_protocol_identity(self, protocol: str) -> dict | None:
        """Get identity data for a specific protocol.

        Checks both the unified protocol_identities field and legacy per-protocol columns.

        Args:
            protocol: Protocol name (modbus, ethernet_ip, profinet, s7, snmp, bacnet)

        Returns:
            Identity dict or None if not available
        """
        # First check unified protocol_identities
        if self.protocol_identities:
            identity = self.protocol_identities.get(protocol)
            if identity:
                return identity

        # Fall back to legacy per-protocol columns
        legacy_mapping = {
            "modbus": self.modbus_identity,
            "ethernet_ip": self.ethernet_ip_identity,
            "profinet": self.profinet_identity,
            "s7": self.s7_identity,
            "snmp": self.snmp_identity,
            "bacnet": self.bacnet_identity,
            "opc_ua": self.opc_ua_identity,
        }
        return legacy_mapping.get(protocol)

    def get_timing_for_protocol(self, protocol: str) -> dict | None:
        """Get response timing for a specific protocol.

        Args:
            protocol: Protocol name

        Returns:
            Timing dict with min, max, mean, std, distribution or None
        """
        if not self.response_timings:
            return None
        return self.response_timings.get(protocol)

    def get_signature_hash(self) -> str:
        """Generate a hash for signature-based matching.

        Used to identify similar templates for aggregation or deduplication.
        """
        import hashlib
        import json

        sig_data = {
            "tcp": self.tcp_signature or {},
            "vendor": self.vendor,
            "protocols": sorted(self.active_protocols or []),
        }
        sig_str = json.dumps(sig_data, sort_keys=True)
        return hashlib.sha256(sig_str.encode()).hexdigest()[:16]

