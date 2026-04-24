# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Modbus Identity Builder for FC 43 Read Device Identification.

Modbus TCP provides device identification through Function Code 43 (0x2B),
which returns vendor name, product code, firmware revision, and other
device-specific information.

Object IDs (per Modbus specification):
- 0x00: VendorName (mandatory)
- 0x01: ProductCode (mandatory)
- 0x02: MajorMinorRevision (mandatory)
- 0x03: VendorUrl (optional)
- 0x04: ProductName (optional)
- 0x05: ModelName (optional)
- 0x06: UserApplicationName (optional)
"""

import logging
from typing import Any

from .base import FirmwareFields, IdentityResponse, ProtocolIdentityBuilder

logger = logging.getLogger(__name__)


class ModbusIdentityBuilder(ProtocolIdentityBuilder):
    """Builder for Modbus FC 43 Read Device Identification responses."""

    @property
    def protocol_name(self) -> str:
        return "modbus"

    @property
    def identity_key(self) -> str:
        return "modbus_identity"

    @property
    def override_key(self) -> str:
        return "modbus_identity_override"

    def build_identity_response(
        self,
        base_identity: dict[str, Any],
        vulnerability_override: dict[str, Any] | None = None,
        firmware_version: str | None = None,
        **kwargs: Any,
    ) -> IdentityResponse:
        """Build Modbus FC 43 identity response.

        Args:
            base_identity: Base modbus_identity from vendor fingerprint
            vulnerability_override: CVE-specific identity overrides
            firmware_version: Firmware version for auto-derivation
            **kwargs: Additional args (device_id_code for response building)

        Returns:
            IdentityResponse with Modbus identity data
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

        # Build raw bytes if device_id_code provided
        device_id_code = kwargs.get("device_id_code", 1)
        raw_bytes = self.build_raw_response(identity, device_id_code=device_id_code)

        return IdentityResponse(
            protocol=self.protocol_name,
            identity_dict=identity,
            raw_bytes=raw_bytes,
            metadata={"device_id_code": device_id_code},
        )

    def derive_firmware_fields(
        self,
        firmware_version: str,
        base_identity: dict[str, Any] | None = None,
    ) -> FirmwareFields:
        """Derive Modbus firmware fields from version string.

        Modbus uses major_minor_revision as a string field.
        Format: "3.10" or "32.011" (preserves original format)
        """
        from app.protocol_engines.firmware_version_deriver import FirmwareVersionParser

        parsed = FirmwareVersionParser.parse(firmware_version)

        return FirmwareFields(
            fields={"major_minor_revision": parsed.full_numeric},
            firmware_version=firmware_version,
            protocol=self.protocol_name,
        )

    def build_raw_response(
        self,
        identity: dict[str, Any],
        **kwargs: Any,
    ) -> bytes:
        """Build Modbus FC 43 MEI response bytes.

        Args:
            identity: Modbus identity dictionary
            **kwargs: device_id_code (1=basic, 2=regular, 3=extended, 4=specific)

        Returns:
            MEI response payload bytes
        """
        if not identity:
            return b""

        device_id_code = kwargs.get("device_id_code", 1)
        objects: list[tuple[int, str]] = []

        # Basic identification (device_id_code >= 1)
        if device_id_code >= 1:
            if "vendor_name" in identity:
                objects.append((0x00, identity["vendor_name"]))
            if "product_code" in identity:
                objects.append((0x01, identity["product_code"]))
            if "major_minor_revision" in identity:
                objects.append((0x02, identity["major_minor_revision"]))

        # Regular identification (device_id_code >= 2)
        if device_id_code >= 2:
            if "vendor_url" in identity:
                objects.append((0x03, identity["vendor_url"]))
            if "product_name" in identity:
                objects.append((0x04, identity["product_name"]))
            if "model_name" in identity:
                objects.append((0x05, identity["model_name"]))

        # Extended identification (device_id_code >= 3)
        if device_id_code >= 3:
            if "user_application_name" in identity:
                objects.append((0x06, identity["user_application_name"]))

        # Build response bytes
        # Format: MEI type (0x0E) + Read Device ID code + Conformity Level +
        #         More Follows + Next Object ID + Number of Objects + Object data
        mei_type = 0x0E
        conformity = 0x03 if device_id_code >= 3 else (0x02 if device_id_code >= 2 else 0x01)
        more_follows = 0x00
        next_object_id = 0x00
        num_objects = len(objects)

        response = bytes([
            mei_type,
            device_id_code,
            conformity,
            more_follows,
            next_object_id,
            num_objects,
        ])

        for obj_id, obj_value in objects:
            obj_bytes = (
                obj_value.encode("utf-8")
                if isinstance(obj_value, str)
                else bytes(obj_value)
            )
            response += bytes([obj_id, len(obj_bytes)]) + obj_bytes

        return response

    def get_vendor_name(self, identity: dict[str, Any]) -> str:
        """Get vendor name for Modbus identity."""
        return self.get_identity_field(identity, "vendor_name", "Unknown Vendor")

    def get_product_code(self, identity: dict[str, Any]) -> str:
        """Get product code for Modbus identity."""
        return self.get_identity_field(identity, "product_code", "Unknown")

    def get_major_minor_revision(self, identity: dict[str, Any]) -> str:
        """Get firmware revision for Modbus identity."""
        return self.get_identity_field(identity, "major_minor_revision", "1.0")
