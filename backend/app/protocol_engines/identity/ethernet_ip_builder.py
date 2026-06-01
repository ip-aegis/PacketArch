# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""EtherNet/IP Identity Builder for ListIdentity and CIP Identity Object.

EtherNet/IP provides device identification through:
1. ListIdentity encapsulation command (UDP broadcast discovery)
2. CIP Identity Object (Class 0x01) - detailed device attributes

Key identity fields:
- Vendor ID (ODVA-assigned)
- Device Type (CIP device profile)
- Product Code
- Revision (major.minor)
- Serial Number
- Product Name
"""

import logging
import struct
from typing import Any

from .base import FirmwareFields, IdentityResponse, ProtocolIdentityBuilder

# Module-level dedupe for the missing-vendor_id warning. Keyed by
# (product_name, product_code) so the same buggy template logs once
# per process lifetime instead of once per poll cycle.
_eip_vendor_warned: set[tuple[Any, Any]] = set()

logger = logging.getLogger(__name__)


class EtherNetIPIdentityBuilder(ProtocolIdentityBuilder):
    """Builder for EtherNet/IP ListIdentity and CIP Identity Object responses."""

    @property
    def protocol_name(self) -> str:
        return "ethernet_ip"

    @property
    def identity_key(self) -> str:
        return "ethernet_ip_identity"

    @property
    def override_key(self) -> str:
        return "ethernet_ip_identity_override"

    def build_identity_response(
        self,
        base_identity: dict[str, Any],
        vulnerability_override: dict[str, Any] | None = None,
        firmware_version: str | None = None,
        **kwargs: Any,
    ) -> IdentityResponse:
        """Build EtherNet/IP identity response.

        Args:
            base_identity: Base ethernet_ip_identity from vendor fingerprint
            vulnerability_override: CVE-specific identity overrides
            firmware_version: Firmware version for auto-derivation
            **kwargs: socket_addr for ListIdentity response

        Returns:
            IdentityResponse with EtherNet/IP identity data
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

        # Build raw bytes for ListIdentity response
        socket_addr = kwargs.get("socket_addr")
        raw_bytes = self.build_raw_response(identity, socket_addr=socket_addr)

        return IdentityResponse(
            protocol=self.protocol_name,
            identity_dict=identity,
            raw_bytes=raw_bytes,
            metadata={"socket_addr": socket_addr},
        )

    def derive_firmware_fields(
        self,
        firmware_version: str,
        base_identity: dict[str, Any] | None = None,
    ) -> FirmwareFields:
        """Derive EtherNet/IP firmware fields from version string.

        EtherNet/IP uses separate revision_major and revision_minor integers.
        """
        from app.protocol_engines.firmware_version_deriver import FirmwareVersionParser

        parsed = FirmwareVersionParser.parse(firmware_version)

        return FirmwareFields(
            fields={
                "revision_major": parsed.major,
                "revision_minor": parsed.minor,
            },
            firmware_version=firmware_version,
            protocol=self.protocol_name,
        )

    def build_raw_response(
        self,
        identity: dict[str, Any],
        **kwargs: Any,
    ) -> bytes:
        """Build EtherNet/IP ListIdentity CPF item bytes.

        Args:
            identity: EtherNet/IP identity dictionary
            **kwargs: socket_addr (IP, port) tuple for response

        Returns:
            CPF item bytes for ListIdentity response
        """
        if not identity:
            return b""

        vendor_id = identity.get("vendor_id")
        if vendor_id is None:
            # Module-level dedupe so the same template doesn't spam the log
            # once per poll cycle.
            key = (
                identity.get("product_name", "?"),
                identity.get("product_code", "?"),
            )
            if key not in _eip_vendor_warned:
                _eip_vendor_warned.add(key)
                logger.warning(
                    "EtherNet/IP identity missing vendor_id for product=%s "
                    "code=%s - defaulting to 1 (Rockwell). Add `vendor_id` "
                    "to ethernet_ip_identity in the device template.",
                    *key,
                )
            vendor_id = 1
        device_type = identity.get("device_type", 14)
        product_code = identity.get("product_code", 1)
        revision_major = identity.get("revision_major", 1)
        revision_minor = identity.get("revision_minor", 0)
        serial_number = identity.get("serial_number", 0x12345678)
        product_name = identity.get("product_name", "Unknown Device")
        state = identity.get("state", 3)

        # Encode product name. CIP Product Name is a SHORT_STRING (1-byte
        # length -> max 255). Cap at 64 so the full canonical hostname fits
        # un-truncated and equals the LLDP/SNMP name (lets CV merge components).
        product_name_bytes = product_name.encode("utf-8")[:64]
        product_name_len = len(product_name_bytes)

        # Socket address info
        socket_addr = kwargs.get("socket_addr")
        if socket_addr:
            ip_str, port = socket_addr
            ip_parts = [int(x) for x in ip_str.split(".")]
        else:
            ip_parts = [192, 168, 1, 100]
            port = 44818

        # Build identity item per CIP spec:
        # Protocol version (UINT, 2 bytes, little-endian)
        identity_data = struct.pack("<H", identity.get("encap_protocol_version", 1))

        # Socket address (big-endian network fields per CIP spec)
        ip_int = (ip_parts[0] << 24) | (ip_parts[1] << 16) | (ip_parts[2] << 8) | ip_parts[3]
        identity_data += struct.pack(">HHI", identity.get("sin_family", 2), port, ip_int)
        identity_data += b"\x00" * 8  # sin_zero (8 bytes)

        # CIP Identity fields (little-endian)
        identity_data += struct.pack(
            "<HHH",
            vendor_id,
            device_type,
            product_code,
        )

        # Add revision and status
        identity_data += struct.pack("<BBH", revision_major, revision_minor, 0x0030)
        identity_data += struct.pack("<I", serial_number)
        identity_data += struct.pack("<B", product_name_len) + product_name_bytes
        identity_data += struct.pack("<B", state)

        return identity_data

    def build_cip_identity_object(
        self,
        identity: dict[str, Any],
        cip_identity: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build complete CIP Identity Object attributes for deep fingerprinting.

        This combines basic ethernet_ip_identity with extended cip_identity_object
        attributes used by Cisco Cyber Vision for detailed device identification.

        Args:
            identity: Basic EtherNet/IP identity
            cip_identity: Extended CIP Identity Object attributes

        Returns:
            Dictionary with all CIP Identity Object attributes (1-20)
        """
        result = {
            "vendor_id": identity.get("vendor_id", 1),
            "device_type": identity.get("device_type", 14),
            "product_code": identity.get("product_code", 1),
            "revision": {
                "major": identity.get("revision_major", 1),
                "minor": identity.get("revision_minor", 0),
            },
            "status": identity.get("status", 0x0030),
            "serial_number": identity.get("serial_number", 0x12345678),
            "product_name": identity.get("product_name", "Unknown Device"),
            "state": identity.get("state", 3),
        }

        # Merge with extended CIP Identity Object attributes
        if cip_identity:
            result.update({
                "status": cip_identity.get("status", result["status"]),
                "configuration_consistency_value": cip_identity.get(
                    "configuration_consistency_value", 0
                ),
                "heartbeat_interval": cip_identity.get("heartbeat_interval", 250),
                "active_language": cip_identity.get("active_language", "English"),
                "supported_languages": cip_identity.get("supported_languages", ["English"]),
                "protection_mode": cip_identity.get("protection_mode", 0),
                "maximum_cip_connections": cip_identity.get("maximum_cip_connections", 32),
            })

        return result

    def get_vendor_id(self, identity: dict[str, Any]) -> int:
        """Get ODVA Vendor ID."""
        return self.get_identity_field(identity, "vendor_id", 1)

    def get_device_type(self, identity: dict[str, Any]) -> int:
        """Get CIP Device Type."""
        return self.get_identity_field(identity, "device_type", 14)

    def get_product_name(self, identity: dict[str, Any]) -> str:
        """Get product name."""
        return self.get_identity_field(identity, "product_name", "Unknown Device")

    def get_revision(self, identity: dict[str, Any]) -> tuple[int, int]:
        """Get revision as (major, minor) tuple."""
        return (
            self.get_identity_field(identity, "revision_major", 1),
            self.get_identity_field(identity, "revision_minor", 0),
        )
