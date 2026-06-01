# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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

from typing import Literal

from app.protocol_engines import canonical_identity
from app.protocol_engines.serial_number_generator import device_hash


class UniqueIdentifierGenerator:
    """Generates unique protocol-specific network identifiers.

    All generation methods are deterministic - the same device_id + scenario_id
    combination will always produce the same identifier. This ensures
    reproducibility when regenerating traffic.
    """

    @classmethod
    def _generate_hash(cls, device_id: str, scenario_id: str | None = None) -> bytes:
        """Generate a deterministic hash from device and scenario identifiers."""
        return device_hash(device_id, scenario_id)

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
            ...     "dev-001", "scenario-123", device_name="NAE-55-01"
            ... )
            'nae-55-01'
        """
        base_name = cls._get_device_name_fallback(
            device_name, model, vendor_family, vendor
        )
        return canonical_identity.bacnet_object_name(
            canonical_identity.canonical_hostname(base_name)
        )

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
            'plc-001'
        """
        base_name = cls._get_device_name_fallback(
            device_name, model, vendor_family, vendor
        )
        return canonical_identity.profinet_station_name(
            canonical_identity.canonical_hostname(base_name)
        )

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
            'plc-001'
        """
        base_name = cls._get_device_name_fallback(
            device_name, model, vendor_family, vendor
        )
        return canonical_identity.snmp_sys_name(
            canonical_identity.canonical_hostname(base_name)
        )

    @classmethod
    def generate_s7_plc_name(
        cls,
        device_id: str,
        scenario_id: str | None = None,
        device_name: str | None = None,
        model: str | None = None,
        vendor_family: str | None = None,
        vendor: str | None = None,
    ) -> str:
        """Generate a unique S7comm PLC name.

        Siemens PLC names are used in S7 SZL responses for device identification.
        Format: {BASE-NAME}-{4-CHAR-HASH}
        Example: "PLC-S7-1500-A7B3"

        Args:
            device_id: Unique device identifier
            scenario_id: Scenario identifier
            device_name: Explicit device name (highest priority)
            model: Device model (fallback)
            vendor_family: Vendor family (fallback)
            vendor: Vendor name (fallback)

        Returns:
            Unique S7 PLC name string

        Examples:
            >>> UniqueIdentifierGenerator.generate_s7_plc_name(
            ...     "dev-001", "scenario-123", device_name="SIEMENS-PLC-01"
            ... )
            'siemens-plc-01'
        """
        base_name = cls._get_device_name_fallback(
            device_name, model, vendor_family, vendor
        )
        return canonical_identity.s7_plc_name(
            canonical_identity.canonical_hostname(base_name)
        )

    @classmethod
    def generate_ethernet_ip_product_name(
        cls,
        device_id: str,
        scenario_id: str | None = None,
        device_name: str | None = None,
        model: str | None = None,
        vendor_family: str | None = None,
        vendor: str | None = None,
    ) -> str:
        """Generate a unique EtherNet/IP product name.

        EtherNet/IP ListIdentity product_name = the canonical hostname (NOT the
        model). Cyber Vision labels the EtherNet/IP component by this field, so
        it must equal the LLDP/SNMP hostname for CV to merge them into one
        component. The model stays identifiable via product_code/device_type/
        vendor_id.

        Args:
            device_id: Unique device identifier (unused; kept for signature parity)
            scenario_id: Scenario identifier (unused; kept for signature parity)
            device_name: Source device name (canonicalized to the hostname)
            model: Device model (fallback only when device_name is absent)
            vendor_family: Vendor family (fallback)
            vendor: Vendor name (fallback)

        Returns:
            CIP product name (canonical hostname)
        """
        base_name = cls._get_device_name_fallback(
            device_name, model, vendor_family, vendor
        )
        return canonical_identity.ethernet_ip_product_name(
            canonical_identity.canonical_hostname(base_name)
        )

    @classmethod
    def generate(
        cls,
        identifier_type: Literal[
            "bacnet_device_instance",
            "bacnet_object_name",
            "profinet_station_name",
            "snmp_sys_name",
            "s7_plc_name",
            "ethernet_ip_product_name",
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

        elif identifier_type == "s7_plc_name":
            return cls.generate_s7_plc_name(
                device_id, scenario_id, device_name, model, vendor_family, vendor
            )

        elif identifier_type == "ethernet_ip_product_name":
            return cls.generate_ethernet_ip_product_name(
                device_id, scenario_id, device_name, model, vendor_family, vendor
            )

        else:
            raise ValueError(f"Unknown identifier type: {identifier_type}")
