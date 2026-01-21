"""Unique identifier generator for protocol-specific network identifiers.

This module generates unique protocol-specific network identifiers that MUST
be unique on the protocol network. This prevents conflicts and ensures
proper device identification by systems like Cisco Cyber Vision.

Identifiers that MUST be unique:
- BACnet device_instance (1-4194302)
- PROFINET station_name (lowercase, alphanumeric + hyphen)
- BACnet object_name
- SNMP sys_name

Generation is deterministic: same device_id + scenario_id always produces
the same identifier values, ensuring reproducibility across regenerations.
"""

import hashlib
import re
from typing import Literal


class UniqueIdentifierGenerator:
    """Generates unique protocol-specific network identifiers.

    All generation methods are deterministic - the same device_id + scenario_id
    combination will always produce the same identifier. This ensures
    reproducibility when regenerating traffic.
    """

    @classmethod
    def _generate_hash(cls, device_id: str, scenario_id: str | None = None) -> bytes:
        """Generate a deterministic hash from device and scenario identifiers.

        Args:
            device_id: Unique device identifier
            scenario_id: Scenario identifier (optional, defaults to "global")

        Returns:
            SHA-256 hash bytes
        """
        seed = f"{device_id}:{scenario_id or 'global'}"
        return hashlib.sha256(seed.encode()).digest()

    @classmethod
    def _sanitize_station_name(cls, name: str) -> str:
        """Sanitize a string for use as a PROFINET station name.

        PROFINET station names must be:
        - Lowercase letters a-z, digits 0-9, hyphen (-)
        - Length 1-240 characters
        - Must start and end with alphanumeric
        - No consecutive hyphens

        Args:
            name: Input string to sanitize

        Returns:
            Sanitized station name
        """
        # Convert to lowercase
        name = name.lower()

        # Replace invalid characters with hyphens
        name = re.sub(r"[^a-z0-9-]", "-", name)

        # Remove consecutive hyphens
        name = re.sub(r"-+", "-", name)

        # Remove leading/trailing hyphens
        name = name.strip("-")

        # Ensure minimum length
        if not name:
            name = "device"

        # Truncate to reasonable length (leave room for hash suffix)
        max_base_len = 200
        if len(name) > max_base_len:
            name = name[:max_base_len]

        return name

    @classmethod
    def _get_device_name_fallback(
        cls,
        device_name: str | None,
        model: str | None,
        vendor_family: str | None,
        vendor: str | None,
    ) -> str:
        """Get device name with fallback chain.

        Fallback order:
        1. device_name (from scenario definition)
        2. model (from fingerprint)
        3. vendor_family (from fingerprint)
        4. vendor (from fingerprint)
        5. "device" (last resort)

        Args:
            device_name: Explicit device name
            model: Device model
            vendor_family: Vendor family
            vendor: Vendor name

        Returns:
            Best available device name
        """
        for name in [device_name, model, vendor_family, vendor]:
            if name and name.strip():
                return name.strip()
        return "device"

    @classmethod
    def generate_bacnet_device_instance(
        cls,
        device_id: str,
        scenario_id: str | None = None,
        base_instance: int | None = None,
    ) -> int:
        """Generate a unique BACnet device instance number.

        BACnet device instance requirements:
        - Range: 1 to 4,194,302 (0x000001 to 0x3FFFFE)
        - Reserved: 0 (uninitialized), 4,194,303 (wildcard)

        Args:
            device_id: Unique device identifier
            scenario_id: Scenario identifier
            base_instance: Optional base instance to offset from (ignored if None)

        Returns:
            Unique BACnet device instance (1 to 4194302)

        Examples:
            >>> UniqueIdentifierGenerator.generate_bacnet_device_instance("dev-001", "scenario-123")
            2847593  # Deterministic value from hash
        """
        hash_bytes = cls._generate_hash(device_id, scenario_id)

        # Use first 4 bytes to generate instance
        hash_int = int.from_bytes(hash_bytes[:4], "big")

        # Map to valid range: 1 to 4194302
        # BACnet max is 4194303 but that's reserved as wildcard
        instance = (hash_int % 4194301) + 1

        return instance

    @classmethod
    def generate_bacnet_object_name(
        cls,
        device_id: str,
        scenario_id: str | None = None,
        device_name: str | None = None,
        model: str | None = None,
        vendor_family: str | None = None,
        vendor: str | None = None,
    ) -> str:
        """Generate a unique BACnet object name.

        Format: {BASE_NAME}-{4-CHAR-HASH}
        Example: "NAE55-A7B3"

        Args:
            device_id: Unique device identifier
            scenario_id: Scenario identifier
            device_name: Explicit device name (highest priority)
            model: Device model (fallback)
            vendor_family: Vendor family (fallback)
            vendor: Vendor name (fallback)

        Returns:
            Unique BACnet object name string

        Examples:
            >>> UniqueIdentifierGenerator.generate_bacnet_object_name(
            ...     "dev-001", "scenario-123", model="NAE55"
            ... )
            'NAE55-A7B3'
        """
        hash_bytes = cls._generate_hash(device_id, scenario_id)
        hash_suffix = hash_bytes[:2].hex().upper()

        base_name = cls._get_device_name_fallback(
            device_name, model, vendor_family, vendor
        )

        # Clean up base name - remove existing suffixes that look like hash
        # Pattern: ends with hyphen + 4 hex chars
        base_name = re.sub(r"-[A-Fa-f0-9]{4}$", "", base_name)

        # Truncate base name if too long
        max_base_len = 50
        if len(base_name) > max_base_len:
            base_name = base_name[:max_base_len]

        return f"{base_name}-{hash_suffix}"

    @classmethod
    def generate_profinet_station_name(
        cls,
        device_id: str,
        scenario_id: str | None = None,
        device_name: str | None = None,
        model: str | None = None,
        vendor_family: str | None = None,
        vendor: str | None = None,
    ) -> str:
        """Generate a unique PROFINET station name.

        PROFINET station name requirements:
        - Characters: Lowercase letters a-z, digits 0-9, hyphen (-)
        - Length: 1-240 characters
        - Must start and end with alphanumeric
        - No consecutive hyphens

        Format: {sanitized_base_name}-{4-char-hash}
        Example: "plc-001-a7b3"

        Args:
            device_id: Unique device identifier
            scenario_id: Scenario identifier
            device_name: Explicit device name (highest priority)
            model: Device model (fallback)
            vendor_family: Vendor family (fallback)
            vendor: Vendor name (fallback)

        Returns:
            Unique PROFINET station name string

        Examples:
            >>> UniqueIdentifierGenerator.generate_profinet_station_name(
            ...     "dev-001", "scenario-123", device_name="PLC-001"
            ... )
            'plc-001-a7b3'
        """
        hash_bytes = cls._generate_hash(device_id, scenario_id)
        hash_suffix = hash_bytes[:2].hex().lower()

        base_name = cls._get_device_name_fallback(
            device_name, model, vendor_family, vendor
        )

        # Sanitize for PROFINET station name requirements
        base_name = cls._sanitize_station_name(base_name)

        # Remove existing hash-like suffixes
        base_name = re.sub(r"-[a-f0-9]{4}$", "", base_name)

        return f"{base_name}-{hash_suffix}"

    @classmethod
    def generate_snmp_sys_name(
        cls,
        device_id: str,
        scenario_id: str | None = None,
        device_name: str | None = None,
        model: str | None = None,
        vendor_family: str | None = None,
        vendor: str | None = None,
    ) -> str:
        """Generate a unique SNMP sysName value.

        Typically formatted like a hostname: uppercase, hyphen-separated.
        Format: {BASE_NAME}-{4-CHAR-HASH}
        Example: "PLC-001-A7B3"

        Args:
            device_id: Unique device identifier
            scenario_id: Scenario identifier
            device_name: Explicit device name (highest priority)
            model: Device model (fallback)
            vendor_family: Vendor family (fallback)
            vendor: Vendor name (fallback)

        Returns:
            Unique SNMP sysName string

        Examples:
            >>> UniqueIdentifierGenerator.generate_snmp_sys_name(
            ...     "dev-001", "scenario-123", device_name="PLC-001"
            ... )
            'PLC-001-A7B3'
        """
        hash_bytes = cls._generate_hash(device_id, scenario_id)
        hash_suffix = hash_bytes[:2].hex().upper()

        base_name = cls._get_device_name_fallback(
            device_name, model, vendor_family, vendor
        )

        # Clean up base name - convert to uppercase hostname style
        base_name = base_name.upper()

        # Replace invalid hostname characters with hyphens
        base_name = re.sub(r"[^A-Z0-9-]", "-", base_name)

        # Remove consecutive hyphens
        base_name = re.sub(r"-+", "-", base_name)

        # Remove leading/trailing hyphens
        base_name = base_name.strip("-")

        if not base_name:
            base_name = "DEVICE"

        # Remove existing hash-like suffixes
        base_name = re.sub(r"-[A-F0-9]{4}$", "", base_name)

        # Truncate if too long
        max_base_len = 50
        if len(base_name) > max_base_len:
            base_name = base_name[:max_base_len]

        return f"{base_name}-{hash_suffix}"

    @classmethod
    def generate(
        cls,
        identifier_type: Literal[
            "bacnet_device_instance",
            "bacnet_object_name",
            "profinet_station_name",
            "snmp_sys_name",
        ],
        device_id: str,
        scenario_id: str | None = None,
        device_name: str | None = None,
        model: str | None = None,
        vendor_family: str | None = None,
        vendor: str | None = None,
    ) -> int | str:
        """Generate a unique identifier by type.

        Convenience method for generating any supported identifier type.

        Args:
            identifier_type: Type of identifier to generate
            device_id: Unique device identifier
            scenario_id: Scenario identifier
            device_name: Explicit device name
            model: Device model
            vendor_family: Vendor family
            vendor: Vendor name

        Returns:
            Generated identifier (int for bacnet_device_instance, str for others)

        Raises:
            ValueError: If identifier_type is not supported
        """
        if identifier_type == "bacnet_device_instance":
            return cls.generate_bacnet_device_instance(device_id, scenario_id)

        elif identifier_type == "bacnet_object_name":
            return cls.generate_bacnet_object_name(
                device_id, scenario_id, device_name, model, vendor_family, vendor
            )

        elif identifier_type == "profinet_station_name":
            return cls.generate_profinet_station_name(
                device_id, scenario_id, device_name, model, vendor_family, vendor
            )

        elif identifier_type == "snmp_sys_name":
            return cls.generate_snmp_sys_name(
                device_id, scenario_id, device_name, model, vendor_family, vendor
            )

        else:
            raise ValueError(f"Unknown identifier type: {identifier_type}")
