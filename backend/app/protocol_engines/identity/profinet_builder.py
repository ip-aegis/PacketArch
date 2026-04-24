# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""PROFINET Identity Builder for DCP Identify responses.

PROFINET uses DCP (Discovery and Configuration Protocol) for device
identification at Layer 2. DCP Identify responses contain:
- DeviceVendor/DeviceID block
- NameOfStation block
- DeviceRole block
- IP configuration block
- Additional device info

Key identity fields for Cyber Vision detection:
- vendor_id: PROFINET Vendor ID (GSDML registered)
- device_id: Device ID within vendor namespace
- station_name: PROFINET station name
- device_role: Device role (controller, IO-device, etc.)
- sw_release: Software/firmware release version
"""

import logging
import struct
from typing import Any

from .base import FirmwareFields, IdentityResponse, ProtocolIdentityBuilder

logger = logging.getLogger(__name__)


class ProfinetIdentityBuilder(ProtocolIdentityBuilder):
    """Builder for PROFINET DCP Identify responses."""

    @property
    def protocol_name(self) -> str:
        return "profinet"

    @property
    def identity_key(self) -> str:
        return "profinet_identity"

    @property
    def override_key(self) -> str:
        return "profinet_identity_override"

    def build_identity_response(
        self,
        base_identity: dict[str, Any],
        vulnerability_override: dict[str, Any] | None = None,
        firmware_version: str | None = None,
        **kwargs: Any,
    ) -> IdentityResponse:
        """Build PROFINET DCP Identify response.

        Args:
            base_identity: Base profinet_identity from vendor fingerprint
            vulnerability_override: CVE-specific identity overrides
            firmware_version: Firmware version for auto-derivation
            **kwargs: Additional arguments

        Returns:
            IdentityResponse with PROFINET DCP identity data
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

        # Build raw DCP response bytes
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
        """Derive PROFINET firmware fields from version string.

        PROFINET uses sw_release with "V" prefix.
        Format: "V3.10" or "V3.10.0"
        """
        from app.protocol_engines.firmware_version_deriver import FirmwareVersionParser

        parsed = FirmwareVersionParser.parse(firmware_version)

        # Ensure V prefix
        if parsed.prefix.upper() == "V":
            sw_release = firmware_version
        else:
            sw_release = f"V{parsed.full_numeric}"

        return FirmwareFields(
            fields={"sw_release": sw_release},
            firmware_version=firmware_version,
            protocol=self.protocol_name,
        )

    def build_raw_response(
        self,
        identity: dict[str, Any],
        **kwargs: Any,
    ) -> bytes:
        """Build PROFINET DCP Identify response bytes.

        Args:
            identity: PROFINET identity dictionary

        Returns:
            DCP block data for identify response
        """
        if not identity:
            return b""

        blocks = []

        # Device/Vendor block (option 0x02, suboption 0x01)
        vendor_id = identity.get("vendor_id", 0x002A)  # Siemens default
        device_id = identity.get("device_id", 0x0001)
        blocks.append(
            struct.pack(">BBHH", 0x02, 0x01, 4, 0) +
            struct.pack(">HH", vendor_id, device_id)
        )

        # NameOfStation block (option 0x02, suboption 0x02)
        station_name = identity.get("station_name", "device")
        station_bytes = station_name.encode("ascii")
        # Pad to even length (PROFINET requirement)
        if len(station_bytes) % 2:
            station_bytes += b"\x00"
        blocks.append(
            struct.pack(">BBH", 0x02, 0x02, len(station_bytes)) +
            station_bytes
        )

        # Device role block (option 0x02, suboption 0x04)
        device_role = identity.get("device_role", 1)  # 1 = IO-device
        blocks.append(
            struct.pack(">BBHBB", 0x02, 0x04, 2, device_role, 0)
        )

        # Device type block (option 0x02, suboption 0x03) - optional
        device_type = identity.get("device_type")
        if device_type:
            type_bytes = device_type.encode("ascii")
            if len(type_bytes) % 2:
                type_bytes += b"\x00"
            blocks.append(
                struct.pack(">BBH", 0x02, 0x03, len(type_bytes)) +
                type_bytes
            )

        # SW Release block (option 0x02, suboption 0x05) - optional
        sw_release = identity.get("sw_release")
        if sw_release:
            sw_bytes = sw_release.encode("ascii")
            if len(sw_bytes) % 2:
                sw_bytes += b"\x00"
            blocks.append(
                struct.pack(">BBH", 0x02, 0x05, len(sw_bytes)) +
                sw_bytes
            )

        return b"".join(blocks)

    def get_station_name(self, identity: dict[str, Any]) -> str:
        """Get PROFINET station name."""
        return self.get_identity_field(identity, "station_name", "device")

    def get_vendor_id(self, identity: dict[str, Any]) -> int:
        """Get PROFINET vendor ID."""
        return self.get_identity_field(identity, "vendor_id", 0x002A)

    def get_device_id(self, identity: dict[str, Any]) -> int:
        """Get PROFINET device ID."""
        return self.get_identity_field(identity, "device_id", 0x0001)

    def get_sw_release(self, identity: dict[str, Any]) -> str:
        """Get software/firmware release version."""
        return self.get_identity_field(identity, "sw_release", "V1.0")
