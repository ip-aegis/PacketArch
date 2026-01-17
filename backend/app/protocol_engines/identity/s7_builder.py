"""S7comm Identity Builder for SZL (System Status List) responses.

S7comm protocol (Siemens S7) provides device identification through SZL
(System Status List) read requests. Key SZL IDs for device identification:

- SZL 0x0011: Module identification (order code, serial, firmware)
- SZL 0x001C: Component identification (module name, copyright)
- SZL 0x0111: Module identification with index
- SZL 0x011C: Component identification with index

Key identity fields for Cyber Vision detection:
- order_code: Siemens MLFB order code (e.g., "6ES7 516-3AN01-0AB0")
- firmware_version: Firmware version with V prefix (e.g., "V3.0.0")
- serial_number: Module serial number
- module_type: Human-readable module type (e.g., "CPU 1516-3 PN/DP")
"""

import logging
import struct
from typing import Any

from .base import FirmwareFields, IdentityResponse, ProtocolIdentityBuilder

logger = logging.getLogger(__name__)


class S7IdentityBuilder(ProtocolIdentityBuilder):
    """Builder for S7comm SZL identity responses."""

    @property
    def protocol_name(self) -> str:
        return "s7"

    @property
    def identity_key(self) -> str:
        # S7 identity is nested under protocol_quirks in some fingerprints
        return "s7_identity"

    @property
    def override_key(self) -> str:
        return "s7_identity_override"

    def build_identity_response(
        self,
        base_identity: dict[str, Any],
        vulnerability_override: dict[str, Any] | None = None,
        firmware_version: str | None = None,
        **kwargs: Any,
    ) -> IdentityResponse:
        """Build S7comm SZL identity response.

        Args:
            base_identity: Base s7_identity from vendor fingerprint
            vulnerability_override: CVE-specific identity overrides
            firmware_version: Firmware version for auto-derivation
            **kwargs: szl_id for specific SZL response

        Returns:
            IdentityResponse with S7 identity data
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

        # Build raw SZL response bytes
        szl_id = kwargs.get("szl_id", 0x0011)
        raw_bytes = self.build_raw_response(identity, szl_id=szl_id)

        return IdentityResponse(
            protocol=self.protocol_name,
            identity_dict=identity,
            raw_bytes=raw_bytes,
            metadata={"szl_id": szl_id},
        )

    def derive_firmware_fields(
        self,
        firmware_version: str,
        base_identity: dict[str, Any] | None = None,
    ) -> FirmwareFields:
        """Derive S7 firmware fields from version string.

        S7 uses firmware_version with "V" prefix.
        Format: "V3.10.0"
        """
        from app.protocol_engines.firmware_version_deriver import FirmwareVersionParser

        parsed = FirmwareVersionParser.parse(firmware_version)

        # Ensure V prefix
        if parsed.prefix.upper() == "V":
            fw_version = firmware_version
        else:
            fw_version = f"V{parsed.full_numeric}"

        return FirmwareFields(
            fields={"firmware_version": fw_version},
            firmware_version=firmware_version,
            protocol=self.protocol_name,
        )

    def build_raw_response(
        self,
        identity: dict[str, Any],
        **kwargs: Any,
    ) -> bytes:
        """Build S7comm SZL response bytes.

        Args:
            identity: S7 identity dictionary
            **kwargs: szl_id (0x0011 or 0x001C)

        Returns:
            SZL response data bytes
        """
        if not identity:
            return b""

        szl_id = kwargs.get("szl_id", 0x0011)

        if szl_id == 0x0011:
            return self._build_szl_0011(identity)
        elif szl_id == 0x001C:
            return self._build_szl_001c(identity)
        else:
            logger.warning(f"Unsupported SZL ID: {szl_id:#06x}")
            return b""

    def _build_szl_0011(self, identity: dict[str, Any]) -> bytes:
        """Build SZL 0x0011 Module identification response.

        Contains order code, serial number, firmware version, and module type.
        """
        order_code = identity.get("order_code", "6ES7 516-3AN01-0AB0").encode("ascii")[:20]
        serial_number = identity.get("serial_number", "S V-P92001234").encode("ascii")[:12]
        firmware_version = identity.get("firmware_version", "V3.0.0").encode("ascii")[:8]
        module_type = identity.get("module_type", "CPU 1516-3 PN/DP").encode("ascii")[:24]

        # Pad strings to fixed lengths
        order_code = order_code.ljust(20, b"\x00")
        serial_number = serial_number.ljust(12, b"\x00")
        firmware_version = firmware_version.ljust(8, b"\x00")
        module_type = module_type.ljust(24, b"\x00")

        # Build SZL 0x0011 response
        szl_data = struct.pack(">HH", 0x0011, 0x0000)  # SZL ID, Index
        szl_data += struct.pack(">HH", 64, 1)  # Data length, Element count
        szl_data += order_code
        szl_data += serial_number
        szl_data += firmware_version
        szl_data += module_type

        return szl_data

    def _build_szl_001c(self, identity: dict[str, Any]) -> bytes:
        """Build SZL 0x001C Component identification response.

        Contains module name and copyright information.
        """
        component_name = identity.get("module_type", "CPU 1516-3 PN/DP").encode("ascii")[:32]
        copyright_info = b"SIEMENS AG".ljust(26, b"\x00")

        component_name = component_name.ljust(32, b"\x00")

        szl_data = struct.pack(">HH", 0x001C, 0x0000)  # SZL ID, Index
        szl_data += struct.pack(">HH", 58, 1)  # Data length, Element count
        szl_data += component_name
        szl_data += copyright_info

        return szl_data

    def get_order_code(self, identity: dict[str, Any]) -> str:
        """Get S7 order code (MLFB)."""
        return self.get_identity_field(identity, "order_code", "6ES7 516-3AN01-0AB0")

    def get_firmware_version(self, identity: dict[str, Any]) -> str:
        """Get S7 firmware version."""
        return self.get_identity_field(identity, "firmware_version", "V3.0.0")

    def get_serial_number(self, identity: dict[str, Any]) -> str:
        """Get S7 serial number."""
        return self.get_identity_field(identity, "serial_number", "S V-P92001234")

    def get_module_type(self, identity: dict[str, Any]) -> str:
        """Get S7 module type."""
        return self.get_identity_field(identity, "module_type", "CPU 1516-3 PN/DP")
