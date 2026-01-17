"""BACnet Identity Builder for I-Am and Device Object responses.

BACnet/IP provides device identification through:
1. I-Am broadcasts - Device announces itself to network
2. Device Object (Instance 4194303) - Contains device properties

Key properties for device identification:
- Object_Identifier (85): Device instance number
- Object_Name (77): Human-readable device name
- Vendor_Identifier (120): ASHRAE-assigned vendor ID
- Vendor_Name (121): Vendor name string
- Model_Name (70): Device model name (critical for CVE detection)
- Firmware_Revision (44): Firmware version (critical for CVE matching)
- Application_Software_Version (12): Application version

This is used for building automation and BMS devices (HVAC, lighting,
access control, fire systems, etc.).

Key identity fields for Cyber Vision detection:
- vendor_id: ASHRAE vendor identifier
- model_name: Primary field for device classification
- firmware_revision: Critical for vulnerability matching
"""

import logging
from typing import Any

from .base import FirmwareFields, IdentityResponse, ProtocolIdentityBuilder

logger = logging.getLogger(__name__)


class BACnetIdentityBuilder(ProtocolIdentityBuilder):
    """Builder for BACnet I-Am and Device Object identity responses."""

    @property
    def protocol_name(self) -> str:
        return "bacnet"

    @property
    def identity_key(self) -> str:
        return "bacnet_identity"

    @property
    def override_key(self) -> str:
        return "bacnet_identity_override"

    def build_identity_response(
        self,
        base_identity: dict[str, Any],
        vulnerability_override: dict[str, Any] | None = None,
        firmware_version: str | None = None,
        **kwargs: Any,
    ) -> IdentityResponse:
        """Build BACnet I-Am identity response.

        Args:
            base_identity: Base bacnet_identity from vendor fingerprint
            vulnerability_override: CVE-specific identity overrides
            firmware_version: Firmware version for auto-derivation
            **kwargs: Additional arguments

        Returns:
            IdentityResponse with BACnet identity data
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

        # BACnet I-Am is built by scapy/bacpypes, we return the dict
        return IdentityResponse(
            protocol=self.protocol_name,
            identity_dict=identity,
            raw_bytes=None,  # BACnet responses built elsewhere
            metadata={},
        )

    def derive_firmware_fields(
        self,
        firmware_version: str,
        base_identity: dict[str, Any] | None = None,
    ) -> FirmwareFields:
        """Derive BACnet firmware fields from version string.

        BACnet uses firmware_revision as a string field.
        Format: "3.10" or "3.10.2"
        """
        from app.protocol_engines.firmware_version_deriver import FirmwareVersionParser

        parsed = FirmwareVersionParser.parse(firmware_version)

        return FirmwareFields(
            fields={"firmware_revision": parsed.full_numeric},
            firmware_version=firmware_version,
            protocol=self.protocol_name,
        )

    def build_raw_response(
        self,
        identity: dict[str, Any],
        **kwargs: Any,
    ) -> bytes:
        """BACnet I-Am packets are built by bacpypes/scapy.

        Returns empty bytes as BACnet identity is returned as dict.
        """
        return b""

    def build_i_am_response(
        self,
        identity: dict[str, Any],
    ) -> dict[str, Any]:
        """Build complete BACnet I-Am identity for Cyber Vision detection.

        Returns a dictionary with all I-Am response fields that Cyber Vision
        parses for device identification and CVE matching.

        Args:
            identity: BACnet identity dictionary

        Returns:
            Dictionary with vendor_id, vendor_name, model_name, firmware_revision, etc.
        """
        firmware_rev = self.get_firmware_revision(identity)

        return {
            "vendor_id": self.get_vendor_id(identity),
            "vendor_name": self.get_vendor_name(identity),
            "model_name": self.get_model_name(identity),
            "firmware_revision": firmware_rev,
            "application_software_version": identity.get(
                "application_software_version", firmware_rev
            ),
            "device_instance": self.get_device_instance(identity),
            "max_apdu_length": self.get_max_apdu_length(identity),
            "segmentation_supported": self.get_segmentation_supported(identity),
            "protocol_version": identity.get("protocol_version", 1),
            "protocol_revision": identity.get("protocol_revision", 19),
            "system_status": identity.get("system_status", 0),  # Operational
            "object_name": identity.get("object_name", "BACnet-Device"),
            "description": identity.get("description", ""),
        }

    def get_vendor_id(self, identity: dict[str, Any]) -> int:
        """Get BACnet vendor ID (ASHRAE registered)."""
        return self.get_identity_field(identity, "vendor_id", 0)

    def get_vendor_name(self, identity: dict[str, Any]) -> str:
        """Get BACnet vendor name."""
        return self.get_identity_field(identity, "vendor_name", "Unknown Vendor")

    def get_model_name(self, identity: dict[str, Any]) -> str:
        """Get BACnet model name (primary for CVE detection)."""
        return self.get_identity_field(identity, "model_name", "BACnet Device")

    def get_firmware_revision(self, identity: dict[str, Any]) -> str:
        """Get BACnet firmware revision (critical for CVE matching)."""
        return self.get_identity_field(identity, "firmware_revision", "1.0")

    def get_device_instance(self, identity: dict[str, Any]) -> int:
        """Get BACnet device instance number."""
        return self.get_identity_field(identity, "device_instance", 1)

    def get_max_apdu_length(self, identity: dict[str, Any]) -> int:
        """Get BACnet maximum APDU length accepted."""
        return self.get_identity_field(identity, "max_apdu_length", 1476)

    def get_segmentation_supported(self, identity: dict[str, Any]) -> int:
        """Get BACnet segmentation support enum."""
        return self.get_identity_field(identity, "segmentation_supported", 3)

    def get_object_types_supported(self, identity: dict[str, Any]) -> list[int]:
        """Get list of supported BACnet object types."""
        return self.get_identity_field(
            identity,
            "object_types_supported",
            [0, 1, 2, 3, 4, 5, 8],  # AI, AO, AV, BI, BO, BV, Device
        )
