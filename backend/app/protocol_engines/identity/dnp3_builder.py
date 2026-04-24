# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""DNP3 Identity Builder for Device Attributes.

DNP3 (Distributed Network Protocol) provides device identification through
Device Attributes objects (Group 0). This is used in SCADA systems,
particularly in power grid and utility applications.

Device Attribute Variation 212-255 are vendor-specific, allowing identification
of vendor, model, and firmware information.
"""

import logging
from typing import Any

from .base import FirmwareFields, IdentityResponse, ProtocolIdentityBuilder

logger = logging.getLogger(__name__)


class DNP3IdentityBuilder(ProtocolIdentityBuilder):
    """Builder for DNP3 Device Attribute identity responses."""

    @property
    def protocol_name(self) -> str:
        return "dnp3"

    @property
    def identity_key(self) -> str:
        return "dnp3_identity"

    @property
    def override_key(self) -> str:
        return "dnp3_identity_override"

    def build_identity_response(
        self,
        base_identity: dict[str, Any],
        vulnerability_override: dict[str, Any] | None = None,
        firmware_version: str | None = None,
        **kwargs: Any,
    ) -> IdentityResponse:
        """Build DNP3 Device Attribute identity response.

        Args:
            base_identity: Base dnp3_identity from vendor fingerprint
            vulnerability_override: CVE-specific identity overrides
            firmware_version: Firmware version for auto-derivation
            **kwargs: Additional args

        Returns:
            IdentityResponse with DNP3 identity data
        """
        # Start with base identity
        identity = dict(base_identity)

        # Apply firmware version derivation if provided
        if firmware_version:
            derived = self.derive_firmware_fields(firmware_version, base_identity)
            identity.update(derived.fields)

        # Apply vulnerability overrides (highest priority)
        if vulnerability_override:
            identity.update(vulnerability_override)

        # Build raw bytes for Device Attributes response
        raw_bytes = self.build_raw_response(identity)

        return IdentityResponse(
            protocol=self.protocol_name,
            identity_dict=identity,
            raw_bytes=raw_bytes,
            metadata={},
        )

    def derive_firmware_fields(
        self,
        firmware_version: str,
        base_identity: dict[str, Any] | None = None,
    ) -> FirmwareFields:
        """Derive DNP3 firmware fields from version string.

        DNP3 uses software_version as a string field.
        """
        from app.protocol_engines.firmware_version_deriver import FirmwareVersionParser

        parsed = FirmwareVersionParser.parse(firmware_version)

        return FirmwareFields(
            fields={"software_version": parsed.full_numeric},
            firmware_version=firmware_version,
            protocol=self.protocol_name,
        )

    def build_raw_response(
        self,
        identity: dict[str, Any],
        **kwargs: Any,
    ) -> bytes:
        """Build DNP3 Device Attributes response bytes.

        DNP3 Device Attributes are encoded as:
        - Object Group 0 (Device Attributes)
        - Variation 212-255 for vendor-specific attributes

        This builds a simplified representation for simulation.

        Args:
            identity: DNP3 identity dictionary

        Returns:
            Device Attributes response payload bytes
        """
        if not identity:
            return b""

        # Build attribute list
        # Format: [Attr Code] [Length] [Value bytes]
        attributes = []

        # Vendor Name (Attr 212)
        if identity.get("vendor_name"):
            vendor = identity["vendor_name"].encode("utf-8")
            attributes.append(bytes([212, len(vendor)]) + vendor)

        # Device Serial (Attr 213)
        if identity.get("device_serial"):
            serial = identity["device_serial"].encode("utf-8")
            attributes.append(bytes([213, len(serial)]) + serial)

        # Hardware Version (Attr 214)
        if identity.get("hardware_version"):
            hw = identity["hardware_version"].encode("utf-8")
            attributes.append(bytes([214, len(hw)]) + hw)

        # Software Version (Attr 215)
        if identity.get("software_version"):
            sw = identity["software_version"].encode("utf-8")
            attributes.append(bytes([215, len(sw)]) + sw)

        # Concatenate all attributes
        return b"".join(attributes)

    def get_vendor_name(self, identity: dict[str, Any]) -> str:
        """Get vendor name for DNP3 identity."""
        return self.get_identity_field(identity, "vendor_name", "Unknown Vendor")

    def get_device_serial(self, identity: dict[str, Any]) -> str:
        """Get device serial for DNP3 identity."""
        return self.get_identity_field(identity, "device_serial", "000000")

    def get_software_version(self, identity: dict[str, Any]) -> str:
        """Get software version for DNP3 identity."""
        return self.get_identity_field(identity, "software_version", "1.0")

    def get_hardware_version(self, identity: dict[str, Any]) -> str:
        """Get hardware version for DNP3 identity."""
        return self.get_identity_field(identity, "hardware_version", "1.0")
