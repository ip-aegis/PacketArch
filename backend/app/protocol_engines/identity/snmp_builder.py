# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""SNMP Identity Builder for MIB-II System group responses.

SNMP provides device identification through the MIB-II System group
(OID 1.3.6.1.2.1.1), which contains:
- sysDescr (1.3.6.1.2.1.1.1): System description string
- sysObjectID (1.3.6.1.2.1.1.2): Vendor object identifier
- sysName (1.3.6.1.2.1.1.5): Administratively assigned name
- sysLocation (1.3.6.1.2.1.1.6): Physical location
- sysContact (1.3.6.1.2.1.1.4): Contact person
- sysServices (1.3.6.1.2.1.1.7): Service layer bitmap

This is heavily used for transportation systems (NTCIP devices like
traffic controllers, DMS, etc.) and building automation systems.

Key identity fields for Cyber Vision detection:
- sys_descr: Primary field containing vendor, model, and firmware
- sys_object_id: SNMP OID for device classification
"""

import logging
import re
from typing import Any

from .base import FirmwareFields, IdentityResponse, ProtocolIdentityBuilder

logger = logging.getLogger(__name__)


class SNMPIdentityBuilder(ProtocolIdentityBuilder):
    """Builder for SNMP MIB-II System group identity responses."""

    @property
    def protocol_name(self) -> str:
        return "snmp"

    @property
    def identity_key(self) -> str:
        return "snmp_identity"

    @property
    def override_key(self) -> str:
        return "snmp_identity_override"

    def build_identity_response(
        self,
        base_identity: dict[str, Any],
        vulnerability_override: dict[str, Any] | None = None,
        firmware_version: str | None = None,
        **kwargs: Any,
    ) -> IdentityResponse:
        """Build SNMP MIB-II identity response.

        Args:
            base_identity: Base snmp_identity from vendor fingerprint
            vulnerability_override: CVE-specific identity overrides
            firmware_version: Firmware version for auto-derivation
            **kwargs: sys_descr_template for firmware interpolation

        Returns:
            IdentityResponse with SNMP identity data
        """
        # Start with base identity
        identity = dict(base_identity)

        # Apply firmware version derivation if provided
        if firmware_version:
            sys_descr_template = kwargs.get("sys_descr_template")
            derived = self.derive_firmware_fields(
                firmware_version,
                base_identity,
                sys_descr_template=sys_descr_template,
            )
            identity.update(derived.fields)

        # Apply vulnerability overrides (highest priority)
        if vulnerability_override:
            identity.update(vulnerability_override)

        # Build response dictionary (SNMP doesn't use raw bytes here)
        return IdentityResponse(
            protocol=self.protocol_name,
            identity_dict=identity,
            raw_bytes=None,  # SNMP responses are built by pysnmp/scapy
            metadata={},
        )

    def derive_firmware_fields(
        self,
        firmware_version: str,
        base_identity: dict[str, Any] | None = None,
        sys_descr_template: str | None = None,
    ) -> FirmwareFields:
        """Derive SNMP firmware fields from version string.

        SNMP embeds firmware version in the sys_descr string. This method
        either uses a template or updates an existing sys_descr.

        Args:
            firmware_version: Firmware version to embed
            base_identity: Base identity with existing sys_descr
            sys_descr_template: Optional template with {firmware_version} placeholder

        Returns:
            FirmwareFields with sys_descr containing firmware
        """
        from app.protocol_engines.firmware_version_deriver import FirmwareVersionParser

        parsed = FirmwareVersionParser.parse(firmware_version)
        base_snmp = base_identity or {}

        # Determine sys_descr
        if sys_descr_template:
            sys_descr = sys_descr_template.format(
                firmware_version=firmware_version,
                major=parsed.major,
                minor=parsed.minor,
                patch=parsed.patch or "",
            )
        elif "sys_descr_template" in base_snmp:
            # Use template from base identity
            sys_descr = base_snmp["sys_descr_template"].format(
                firmware_version=firmware_version,
                major=parsed.major,
                minor=parsed.minor,
                patch=parsed.patch or "",
            )
        elif base_snmp.get("sys_descr"):
            # Try to replace version pattern in existing string
            sys_descr = self._update_version_in_string(
                base_snmp["sys_descr"],
                parsed.full_numeric,
            )
        else:
            sys_descr = f"Device Firmware V{parsed.full_numeric}"

        return FirmwareFields(
            fields={"sys_descr": sys_descr},
            firmware_version=firmware_version,
            protocol=self.protocol_name,
        )

    def _update_version_in_string(self, text: str, new_version: str) -> str:
        """Replace version pattern in an existing string.

        Handles patterns like "Controller V2.1.4" -> "Controller V3.10"
        """
        version_pattern = r"[Vv]?\d+\.\d+(?:\.\d+)?"

        match = re.search(version_pattern, text)
        if match:
            original = match.group()
            if original.startswith(("V", "v")):
                replacement = f"V{new_version}"
            else:
                replacement = new_version
            return re.sub(version_pattern, replacement, text, count=1)

        # No version found, append
        return f"{text} V{new_version}"

    def build_raw_response(
        self,
        identity: dict[str, Any],
        **kwargs: Any,
    ) -> bytes:
        """SNMP responses are built by pysnmp/scapy, not here.

        Returns empty bytes as SNMP identity is returned as dict.
        """
        return b""

    def build_snmp_identity_response(
        self,
        identity: dict[str, Any],
    ) -> dict[str, Any]:
        """Build complete SNMP identity for Cyber Vision detection.

        Returns a dictionary with all system MIB-II identity fields.

        Args:
            identity: SNMP identity dictionary

        Returns:
            Dictionary with sysDescr, sysObjectID, sysName, etc.
        """
        return {
            "sysDescr": self.get_sys_descr(identity),
            "sysObjectID": self.get_sys_object_id(identity),
            "sysName": self.get_sys_name(identity),
            "sysLocation": self.get_sys_location(identity),
            "sysContact": self.get_sys_contact(identity),
            "sysServices": identity.get("sys_services", 72),
        }

    def get_sys_descr(self, identity: dict[str, Any]) -> str:
        """Get SNMP sysDescr value."""
        return self.get_identity_field(identity, "sys_descr", "Unknown Device")

    def get_sys_object_id(self, identity: dict[str, Any]) -> str:
        """Get SNMP sysObjectID value."""
        return self.get_identity_field(identity, "sys_object_id", "1.3.6.1.4.1.9999.1.1")

    def get_sys_name(self, identity: dict[str, Any]) -> str:
        """Get SNMP sysName value."""
        return self.get_identity_field(identity, "sys_name", "unknown-device")

    def get_sys_location(self, identity: dict[str, Any]) -> str:
        """Get SNMP sysLocation value."""
        return self.get_identity_field(identity, "sys_location", "Unknown Location")

    def get_sys_contact(self, identity: dict[str, Any]) -> str:
        """Get SNMP sysContact value."""
        return self.get_identity_field(identity, "sys_contact", "admin@local")

    def get_ntcip_device_type(self, identity: dict[str, Any]) -> str:
        """Get NTCIP device type (asc, dms, ess, etc.)."""
        return self.get_identity_field(identity, "ntcip_device_type", "generic")
