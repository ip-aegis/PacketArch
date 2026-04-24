# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""IEC 60870-5-104 Identity Builder for Station Identification.

IEC 104 is used in power system SCADA communications. Device identification
is typically embedded in the ASDU (Application Service Data Unit) header
which includes the Common Address of ASDU (station identifier).

Station identification in IEC 104:
- Common Address: 1-65534 (station identifier)
- Station Name: Configured name for the station/device
"""

import logging
from typing import Any

from .base import FirmwareFields, IdentityResponse, ProtocolIdentityBuilder

logger = logging.getLogger(__name__)


class IEC104IdentityBuilder(ProtocolIdentityBuilder):
    """Builder for IEC 60870-5-104 station identity responses."""

    @property
    def protocol_name(self) -> str:
        return "iec104"

    @property
    def identity_key(self) -> str:
        return "iec104_identity"

    @property
    def override_key(self) -> str:
        return "iec104_identity_override"

    def build_identity_response(
        self,
        base_identity: dict[str, Any],
        vulnerability_override: dict[str, Any] | None = None,
        firmware_version: str | None = None,
        **kwargs: Any,
    ) -> IdentityResponse:
        """Build IEC 104 station identity response.

        Args:
            base_identity: Base iec104_identity from vendor fingerprint
            vulnerability_override: CVE-specific identity overrides
            firmware_version: Firmware version for auto-derivation (limited use in IEC104)
            **kwargs: Additional args

        Returns:
            IdentityResponse with IEC 104 identity data
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

        # Build raw bytes (ASDU header with common address)
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
        """Derive IEC 104 firmware fields from version string.

        IEC 104 doesn't have explicit firmware version fields in the protocol.
        Station name may include version info in some implementations.
        """
        # IEC 104 doesn't have a standard firmware version field
        # but we can append version to station name if needed
        return FirmwareFields(
            fields={},  # No standard fields to derive
            firmware_version=firmware_version,
            protocol=self.protocol_name,
        )

    def build_raw_response(
        self,
        identity: dict[str, Any],
        **kwargs: Any,
    ) -> bytes:
        """Build IEC 104 ASDU header bytes with common address.

        IEC 104 ASDU structure (simplified):
        - Type Identifier (1 byte)
        - Variable Structure Qualifier (1 byte)
        - Cause of Transmission (2 bytes)
        - Common Address of ASDU (2 bytes) - This is our station ID

        For identity purposes, we return the common address encoding.

        Args:
            identity: IEC 104 identity dictionary

        Returns:
            Common address bytes (little-endian, 2 bytes)
        """
        if not identity:
            return b""

        # Get common address (default to 1)
        common_address = identity.get("common_address", 1)

        # Ensure it's in valid range (1-65534)
        if not 1 <= common_address <= 65534:
            common_address = 1

        # Encode as little-endian 2-byte integer
        return common_address.to_bytes(2, byteorder="little")

    def get_station_name(self, identity: dict[str, Any]) -> str:
        """Get station name for IEC 104 identity."""
        return self.get_identity_field(identity, "station_name", "IEC104-Station")

    def get_common_address(self, identity: dict[str, Any]) -> int:
        """Get common address (station ID) for IEC 104 identity."""
        addr = identity.get("common_address", 1)
        if isinstance(addr, int) and 1 <= addr <= 65534:
            return addr
        return 1
