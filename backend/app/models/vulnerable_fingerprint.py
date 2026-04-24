# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Vulnerable Fingerprint Variant model.

This model links CVE vulnerabilities to specific protocol identity overrides,
enabling devices to respond with vulnerable firmware versions in their
protocol identity responses (Modbus FC 43, EtherNet/IP ListIdentity, PROFINET DCP).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VulnerableFingerprintVariant(Base):
    """Variant fingerprint with vulnerable firmware for CVE detection.

    This table stores protocol identity overrides that, when applied to
    a device template, cause the device to report vulnerable
    firmware versions detectable by security scanners.
    """

    __tablename__ = "vulnerable_fingerprint_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # CVE relationship
    cve_vulnerability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cve_vulnerabilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identification
    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable name (e.g., 'ControlLogix L85E (CVE-2022-1159)')",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of this vulnerable variant",
    )

    # Vulnerable firmware version
    firmware_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="The specific vulnerable firmware version",
    )

    # Protocol identity overrides
    # These override specific fields in the base fingerprint's protocol responses
    modbus_identity_override: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Overrides for Modbus FC 43 response fields",
    )
    # Example: {
    #   "major_minor_revision": "32.011",
    #   "model_name": "1756-L85E/A LOGIX5585"
    # }

    ethernet_ip_identity_override: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Overrides for EtherNet/IP ListIdentity response",
    )
    # Example: {
    #   "product_name": "1756-L85E/A LOGIX5585",
    #   "major_revision": 32,
    #   "minor_revision": 11
    # }

    profinet_identity_override: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Overrides for PROFINET DCP identity block",
    )
    # Example: {
    #   "device_type": "CPU 1516-3 PN/DP",
    #   "sw_release": "V2.8.0"
    # }

    s7_identity_override: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Overrides for S7comm SZL identity response",
    )
    # Example: {
    #   "order_code": "6ES7 516-3AN01-0AB0",
    #   "firmware_version": "V2.8.0"
    # }

    cip_identity_override: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Overrides for CIP Identity Object (Class 0x01) deep fingerprinting",
    )
    # Example: {
    #   "protection_mode": 0,  # 0 = no protection (vulnerable)
    #   "configuration_consistency_value": 0xDEAD0000,
    #   "heartbeat_interval": 250,
    #   "maximum_cip_connections": 64,
    # }

    snmp_identity_override: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Overrides for SNMP sysDescr/sysName identity (for ITS/transportation devices)",
    )
    # Example: {
    #   "sys_descr": "Siemens SICAM CP-8000 Master Station V5.20",
    #   "sys_name": "cp8000-substation-01",
    #   "sys_object_id": "1.3.6.1.4.1.4329.2.51.1",
    # }

    bacnet_identity_override: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Overrides for BACnet I-Am identity (for BMS/building automation devices)",
    )
    # Example: {
    #   "vendor_id": 5,  # Johnson Controls
    #   "vendor_name": "Johnson Controls",
    #   "model_name": "NAE55 Network Automation Engine",
    #   "firmware_revision": "12.0.3",
    #   "device_instance": 100001,
    # }

    # SNMP sys_descr template for firmware version interpolation
    snmp_sys_descr_template: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Template for SNMP sysDescr with {firmware_version} placeholder",
    )
    # Example: "Schneider Electric Modicon M580 Firmware V{firmware_version}"
    # At runtime, {firmware_version} is replaced with the actual firmware version.
    # This enables auto-derivation without explicit snmp_identity_override.

    # Full protocol response templates (optional - for more complex cases)
    full_modbus_mei_template: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Complete Modbus MEI response template if override not sufficient",
    )
    full_enip_identity_template: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Complete EtherNet/IP identity template",
    )

    # Targeting information
    target_vendor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Target vendor for this variant",
    )
    target_product_family: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Target product family",
    )
    target_models: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of target model numbers this variant applies to",
    )

    # Metadata
    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
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

    # Relationships
    cve_vulnerability = relationship(
        "CVEVulnerability",
        backref="fingerprint_variants",
        lazy="joined",
    )
    def __repr__(self) -> str:
        return f"<VulnerableFingerprintVariant {self.display_name}>"

    def get_combined_overrides(self) -> dict:
        """Get all protocol identity overrides combined.

        Returns:
            Dictionary with all protocol overrides and firmware_version for auto-derivation
        """
        overrides = {
            "firmware_version": self.firmware_version,
            "modbus_identity_override": self.modbus_identity_override or {},
            "ethernet_ip_identity_override": self.ethernet_ip_identity_override or {},
            "profinet_identity_override": self.profinet_identity_override or {},
            "s7_identity_override": self.s7_identity_override or {},
            "cip_identity_override": self.cip_identity_override or {},
            "snmp_identity_override": self.snmp_identity_override or {},
            "bacnet_identity_override": self.bacnet_identity_override or {},
        }
        # Include SNMP sys_descr template for auto-derivation if present
        if self.snmp_sys_descr_template:
            overrides["snmp_sys_descr_template"] = self.snmp_sys_descr_template
        return overrides

    def applies_to_fingerprint(self, fingerprint_vendor: str, fingerprint_model: str | None = None) -> bool:
        """Check if this variant applies to a given fingerprint.

        Args:
            fingerprint_vendor: The vendor from the base fingerprint
            fingerprint_model: The model from the base fingerprint (optional)

        Returns:
            True if this variant can be applied
        """
        if fingerprint_vendor.lower() != self.target_vendor.lower():
            return False

        if fingerprint_model and self.target_models:
            return fingerprint_model in self.target_models

        return True
