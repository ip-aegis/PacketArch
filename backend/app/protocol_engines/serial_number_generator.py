"""Deterministic unique serial number generator.

This module generates unique serial numbers for devices to prevent
Cisco Cyber Vision from merging devices that share the same fingerprint.

Problem: CV uses serial numbers as a primary key for device identity correlation.
When multiple devices share the same serial number, CV merges them incorrectly.

Solution: Generate deterministic unique serial numbers using a hash of
device_id + scenario_id, ensuring each device instance gets a unique serial
while remaining reproducible across regenerations.
"""

import hashlib
from typing import Literal


def device_hash(device_id: str, scenario_id: str | None = None) -> bytes:
    """Generate a deterministic SHA-256 hash from device and scenario identifiers.

    Shared by SerialNumberGenerator and UniqueIdentifierGenerator for
    consistent deterministic generation across all protocol identifiers.

    Args:
        device_id: Unique device identifier
        scenario_id: Scenario identifier (optional, defaults to "global")

    Returns:
        SHA-256 hash bytes
    """
    seed = f"{device_id}:{scenario_id or 'global'}"
    return hashlib.sha256(seed.encode()).digest()


class SerialNumberGenerator:
    """Generates unique serial numbers from device and scenario identifiers.

    Serial numbers are deterministic - the same device_id + scenario_id
    combination will always produce the same serial number. This ensures
    reproducibility when regenerating traffic.
    """

    @classmethod
    def generate(
        cls,
        protocol: Literal["ethernet_ip", "s7", "profinet"],
        device_id: str,
        scenario_id: str | None = None,
        vendor: str | None = None,
    ) -> int | str:
        """Generate a unique serial number for a device.

        Args:
            protocol: Target protocol (determines format of serial number)
            device_id: Unique device identifier
            scenario_id: Scenario identifier (optional, defaults to "global")
            vendor: Vendor name (reserved for future vendor-specific formatting)

        Returns:
            Protocol-appropriate serial number:
            - ethernet_ip: 32-bit unsigned integer
            - s7: 12-character string (e.g., "S V-P12AB34CD")
            - profinet: 16-character hex string for IM0 serial

        Examples:
            >>> SerialNumberGenerator.generate("ethernet_ip", "dev-001", "scenario-123")
            2847593612  # 32-bit integer

            >>> SerialNumberGenerator.generate("s7", "dev-001", "scenario-123")
            'S V-P12AB34CD'  # 12-char S7 serial format

            >>> SerialNumberGenerator.generate("profinet", "dev-001", "scenario-123")
            '12AB34CD56EF7890'  # 16-char IM0 serial
        """
        hash_bytes = device_hash(device_id, scenario_id)

        if protocol == "ethernet_ip":
            # EtherNet/IP: 32-bit unsigned integer serial number
            return int.from_bytes(hash_bytes[:4], "big")

        elif protocol == "s7":
            # S7comm: 12-character serial number
            # Format: "S V-" prefix + 8 hex chars = 12 chars (matches Siemens convention)
            hex_portion = hash_bytes[:4].hex().upper()
            return f"S V-{hex_portion}"

        elif protocol == "profinet":
            # PROFINET I&M0: 16-character serial number (hex string)
            return hash_bytes[:8].hex().upper()[:16]

        else:
            # Fallback: return hex string
            return hash_bytes[:8].hex().upper()

    @classmethod
    def generate_ethernet_ip(
        cls,
        device_id: str,
        scenario_id: str | None = None,
    ) -> int:
        """Generate EtherNet/IP serial number (32-bit integer).

        Args:
            device_id: Unique device identifier
            scenario_id: Scenario identifier

        Returns:
            32-bit unsigned integer serial number
        """
        return cls.generate("ethernet_ip", device_id, scenario_id)  # type: ignore

    @classmethod
    def generate_s7(
        cls,
        device_id: str,
        scenario_id: str | None = None,
    ) -> str:
        """Generate S7comm serial number (12-char string).

        Args:
            device_id: Unique device identifier
            scenario_id: Scenario identifier

        Returns:
            12-character serial string (e.g., "S V-P12AB34CD")
        """
        return cls.generate("s7", device_id, scenario_id)  # type: ignore

    @classmethod
    def generate_profinet(
        cls,
        device_id: str,
        scenario_id: str | None = None,
    ) -> str:
        """Generate PROFINET I&M0 serial number (16-char hex).

        Args:
            device_id: Unique device identifier
            scenario_id: Scenario identifier

        Returns:
            16-character hex serial string
        """
        return cls.generate("profinet", device_id, scenario_id)  # type: ignore
