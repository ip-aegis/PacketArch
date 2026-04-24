# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""OPC UA Identity Builder for Server ApplicationDescription.

OPC UA provides device identification through the ApplicationDescription
structure returned in various services (GetEndpoints, FindServers, etc.).

Key identity fields:
- ApplicationUri: Unique URI for the application (required)
- ProductUri: URI identifying the product (required)
- ApplicationName: Human-readable name (LocalizedText)
- ApplicationType: Server type (Server, Client, ClientServer, DiscoveryServer)
- GatewayServerUri: URI of gateway server (if applicable)
- DiscoveryProfileUri: URI for discovery profile
- DiscoveryUrls: URLs where server can be discovered

Server status information:
- ManufacturerName: Vendor name
- ProductName: Product name
- SoftwareVersion: Software version (major.minor.patch)
- BuildNumber: Build identifier
- BuildDate: Build timestamp
"""

import logging
import struct
from typing import Any

from .base import FirmwareFields, IdentityResponse, ProtocolIdentityBuilder

logger = logging.getLogger(__name__)


class OpcUaIdentityBuilder(ProtocolIdentityBuilder):
    """Builder for OPC UA ApplicationDescription and ServerStatus responses."""

    @property
    def protocol_name(self) -> str:
        return "opc_ua"

    @property
    def identity_key(self) -> str:
        return "opc_ua_identity"

    @property
    def override_key(self) -> str:
        return "opc_ua_identity_override"

    def build_identity_response(
        self,
        base_identity: dict[str, Any],
        vulnerability_override: dict[str, Any] | None = None,
        firmware_version: str | None = None,
        **kwargs: Any,
    ) -> IdentityResponse:
        """Build OPC UA identity response.

        Args:
            base_identity: Base opc_ua_identity from vendor fingerprint
            vulnerability_override: CVE-specific identity overrides
            firmware_version: Firmware version for auto-derivation
            **kwargs: Additional args (include_endpoints, include_status)

        Returns:
            IdentityResponse with OPC UA identity data
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

        # Ensure required fields have defaults
        if "application_uri" not in identity:
            identity["application_uri"] = "urn:example:server"
        if "product_uri" not in identity:
            identity["product_uri"] = "urn:example:product"
        if "application_name" not in identity:
            identity["application_name"] = "Generic OPC UA Server"
        if "application_type" not in identity:
            identity["application_type"] = 0  # Server

        # Build raw bytes if requested
        include_endpoints = kwargs.get("include_endpoints", True)
        raw_bytes = self.build_raw_response(
            identity, include_endpoints=include_endpoints
        )

        return IdentityResponse(
            protocol=self.protocol_name,
            identity_dict=identity,
            raw_bytes=raw_bytes,
            metadata={
                "include_endpoints": include_endpoints,
                "application_type": identity.get("application_type"),
            },
        )

    def derive_firmware_fields(
        self,
        firmware_version: str,
        base_identity: dict[str, Any] | None = None,
    ) -> FirmwareFields:
        """Derive OPC UA firmware fields from version string.

        OPC UA uses software_version as a string and build_number as an integer.
        Format: "1.2.3" -> software_version="1.2.3", build_number=derived
        """
        from app.protocol_engines.firmware_version_deriver import FirmwareVersionParser

        parsed = FirmwareVersionParser.parse(firmware_version)

        # Calculate build number from version components
        # Format: major*10000 + minor*100 + patch
        build_number = (
            parsed.major * 10000 + parsed.minor * 100 + (parsed.patch or 0)
        )

        return FirmwareFields(
            fields={
                "software_version": parsed.full_numeric,
                "build_number": build_number,
            },
            firmware_version=firmware_version,
            protocol=self.protocol_name,
        )

    def build_raw_response(
        self,
        identity: dict[str, Any],
        **kwargs: Any,
    ) -> bytes:
        """Build OPC UA GetEndpoints response bytes.

        Args:
            identity: OPC UA identity dictionary
            **kwargs: include_endpoints (bool)

        Returns:
            OPC UA binary response (simplified GetEndpointsResponse)
        """
        if not identity:
            return b""

        # Build ApplicationDescription structure
        # Reference: OPC UA Part 4, Section 7.1

        parts = []

        # ApplicationUri (String)
        app_uri = identity.get("application_uri", "urn:example:server")
        parts.append(self._encode_string(app_uri))

        # ProductUri (String)
        product_uri = identity.get("product_uri", "urn:example:product")
        parts.append(self._encode_string(product_uri))

        # ApplicationName (LocalizedText)
        app_name = identity.get("application_name", "OPC UA Server")
        parts.append(self._encode_localized_text(app_name))

        # ApplicationType (UInt32)
        # 0=Server, 1=Client, 2=ClientAndServer, 3=DiscoveryServer
        app_type = identity.get("application_type", 0)
        parts.append(struct.pack("<I", app_type))

        # GatewayServerUri (String, usually null)
        gateway_uri = identity.get("gateway_server_uri")
        parts.append(self._encode_string(gateway_uri))

        # DiscoveryProfileUri (String, usually null)
        discovery_profile = identity.get("discovery_profile_uri")
        parts.append(self._encode_string(discovery_profile))

        # DiscoveryUrls (Array of String)
        discovery_urls = identity.get("discovery_urls", [])
        if discovery_urls:
            parts.append(struct.pack("<i", len(discovery_urls)))
            for url in discovery_urls:
                parts.append(self._encode_string(url))
        else:
            parts.append(struct.pack("<i", -1))  # Null array

        return b"".join(parts)

    def _encode_string(self, value: str | None) -> bytes:
        """Encode a string in OPC UA format.

        OPC UA strings are length-prefixed with int32 length.
        Null strings use -1 as length.
        """
        if value is None:
            return struct.pack("<i", -1)
        encoded = value.encode("utf-8")
        return struct.pack("<i", len(encoded)) + encoded

    def _encode_localized_text(self, text: str, locale: str = "en") -> bytes:
        """Encode a LocalizedText in OPC UA format.

        LocalizedText structure:
        - EncodingMask (Byte): 0x01=locale, 0x02=text, 0x03=both
        - Locale (String, optional)
        - Text (String, optional)
        """
        encoding_mask = 0x03  # Both locale and text present
        locale_bytes = self._encode_string(locale)
        text_bytes = self._encode_string(text)
        return bytes([encoding_mask]) + locale_bytes + text_bytes

    def build_server_status_response(
        self,
        identity: dict[str, Any],
    ) -> bytes:
        """Build OPC UA ServerStatus response for Read service.

        ServerStatus contains:
        - StartTime (DateTime)
        - CurrentTime (DateTime)
        - State (ServerState enum)
        - BuildInfo (structure)
        - SecondsTillShutdown
        - ShutdownReason
        """
        parts = []

        # StartTime (DateTime as Int64 - 100ns intervals since 1601)
        parts.append(struct.pack("<Q", 0))

        # CurrentTime (DateTime)
        parts.append(struct.pack("<Q", 0))

        # State (ServerState UInt32)
        # 0=Running, 1=Failed, 2=NoConfiguration, 3=Suspended, etc.
        state = identity.get("server_state", 0)
        parts.append(struct.pack("<I", state))

        # BuildInfo structure
        parts.append(self._build_build_info(identity))

        # SecondsTillShutdown (UInt32)
        parts.append(struct.pack("<I", 0))

        # ShutdownReason (LocalizedText)
        parts.append(self._encode_localized_text(""))

        return b"".join(parts)

    def _build_build_info(self, identity: dict[str, Any]) -> bytes:
        """Build OPC UA BuildInfo structure.

        BuildInfo structure:
        - ProductUri (String)
        - ManufacturerName (String)
        - ProductName (String)
        - SoftwareVersion (String)
        - BuildNumber (String)
        - BuildDate (DateTime)
        """
        parts = []

        # ProductUri
        parts.append(self._encode_string(identity.get("product_uri", "")))

        # ManufacturerName
        parts.append(self._encode_string(identity.get("manufacturer_name", "")))

        # ProductName
        parts.append(self._encode_string(identity.get("product_name", "")))

        # SoftwareVersion
        parts.append(self._encode_string(identity.get("software_version", "1.0.0")))

        # BuildNumber
        build_num = identity.get("build_number", 0)
        parts.append(self._encode_string(str(build_num)))

        # BuildDate (DateTime)
        parts.append(struct.pack("<Q", 0))

        return b"".join(parts)

    # Convenience methods for common identity fields
    def get_application_uri(self, identity: dict[str, Any]) -> str:
        """Get application URI for OPC UA identity."""
        return self.get_identity_field(identity, "application_uri", "urn:example:server")

    def get_product_uri(self, identity: dict[str, Any]) -> str:
        """Get product URI for OPC UA identity."""
        return self.get_identity_field(identity, "product_uri", "urn:example:product")

    def get_application_name(self, identity: dict[str, Any]) -> str:
        """Get application name for OPC UA identity."""
        return self.get_identity_field(identity, "application_name", "OPC UA Server")

    def get_manufacturer_name(self, identity: dict[str, Any]) -> str:
        """Get manufacturer name for OPC UA identity."""
        return self.get_identity_field(identity, "manufacturer_name", "Unknown")

    def get_software_version(self, identity: dict[str, Any]) -> str:
        """Get software version for OPC UA identity."""
        return self.get_identity_field(identity, "software_version", "1.0.0")
