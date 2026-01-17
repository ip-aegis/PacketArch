"""Base class and types for Protocol Identity Builders.

This module defines the abstract base class for protocol-specific identity
builders, which generate vendor/device identification responses for security
scanner detection (e.g., Cisco Cyber Vision).

Each protocol has a unique way of identifying devices:
- Modbus: FC 43 Read Device Identification
- EtherNet/IP: ListIdentity, CIP Identity Object
- PROFINET: DCP Identify
- S7comm: SZL (System Status List)
- SNMP: MIB-II System group
- BACnet: I-Am broadcast
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IdentityResponse:
    """Container for a protocol identity response.

    Attributes:
        protocol: Protocol name (modbus, ethernet_ip, etc.)
        identity_dict: Protocol-specific identity fields
        raw_bytes: Optional pre-built response bytes
        metadata: Additional metadata for debugging/logging
    """

    protocol: str
    identity_dict: dict[str, Any]
    raw_bytes: bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FirmwareFields:
    """Derived firmware fields for a specific protocol.

    Each protocol has different fields that contain firmware information.
    This dataclass standardizes the output from firmware derivation.
    """

    fields: dict[str, Any]
    firmware_version: str
    protocol: str


class ProtocolIdentityBuilder(ABC):
    """Abstract base class for protocol-specific identity builders.

    Each protocol has its own way of communicating device identity to
    network scanners. This base class defines the interface that all
    protocol-specific builders must implement.

    To add support for a new protocol:
    1. Create a new module in identity/ (e.g., myprotocol_builder.py)
    2. Subclass ProtocolIdentityBuilder
    3. Implement all abstract methods
    4. Add the @register_builder decorator

    Example:
        @register_builder
        class ModbusIdentityBuilder(ProtocolIdentityBuilder):
            @property
            def protocol_name(self) -> str:
                return "modbus"

            def build_identity_response(self, ...) -> IdentityResponse:
                ...
    """

    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Return the protocol name (e.g., 'modbus', 'ethernet_ip').

        This is used for registry lookup and logging.
        """
        ...

    @property
    @abstractmethod
    def identity_key(self) -> str:
        """Return the key used in fingerprint dicts (e.g., 'modbus_identity').

        This is the key under which identity data is stored in vendor
        fingerprint dictionaries.
        """
        ...

    @property
    @abstractmethod
    def override_key(self) -> str:
        """Return the key used for vulnerability overrides.

        This is the key used in VulnerableFingerprintVariant for
        CVE-specific identity overrides (e.g., 'modbus_identity_override').
        """
        ...

    @abstractmethod
    def build_identity_response(
        self,
        base_identity: dict[str, Any],
        vulnerability_override: dict[str, Any] | None = None,
        firmware_version: str | None = None,
        **kwargs: Any,
    ) -> IdentityResponse:
        """Build a complete identity response for this protocol.

        This method combines base identity data with optional vulnerability
        overrides and firmware version derivation to produce the final
        identity response.

        Args:
            base_identity: Base identity dict from vendor fingerprint
            vulnerability_override: Optional CVE-specific overrides
            firmware_version: Optional firmware version for auto-derivation
            **kwargs: Protocol-specific additional arguments

        Returns:
            IdentityResponse with complete identity data and optional raw bytes
        """
        ...

    @abstractmethod
    def derive_firmware_fields(
        self,
        firmware_version: str,
        base_identity: dict[str, Any] | None = None,
    ) -> FirmwareFields:
        """Derive protocol-specific firmware fields from a version string.

        Each protocol has different fields that contain firmware information:
        - Modbus: major_minor_revision
        - EtherNet/IP: revision_major, revision_minor
        - PROFINET: sw_release
        - S7: firmware_version
        - SNMP: embedded in sys_descr
        - BACnet: firmware_revision

        Args:
            firmware_version: Canonical firmware version (e.g., "3.10")
            base_identity: Optional base identity for context

        Returns:
            FirmwareFields with protocol-specific firmware fields
        """
        ...

    @abstractmethod
    def build_raw_response(
        self,
        identity: dict[str, Any],
        **kwargs: Any,
    ) -> bytes:
        """Build raw protocol bytes for the identity response.

        Some protocols require binary responses (e.g., Modbus FC 43).
        This method builds those bytes from the identity dictionary.

        Args:
            identity: Identity dictionary
            **kwargs: Protocol-specific arguments (e.g., device_id_code for Modbus)

        Returns:
            Raw response bytes
        """
        ...

    def get_identity_field(
        self,
        identity: dict[str, Any],
        field_name: str,
        default: Any = None,
    ) -> Any:
        """Safely get a field from the identity dictionary.

        Args:
            identity: Identity dictionary
            field_name: Field name to retrieve
            default: Default value if not found

        Returns:
            Field value or default
        """
        return identity.get(field_name, default)

    def merge_overrides(
        self,
        base: dict[str, Any],
        override: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Merge base identity with vulnerability overrides.

        Args:
            base: Base identity dictionary
            override: Override dictionary (may be None)

        Returns:
            Merged dictionary with overrides taking precedence
        """
        if not override:
            return dict(base)
        return {**base, **override}
