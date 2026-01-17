"""Firmware version derivation for protocol-specific identity fields.

This module provides centralized logic for deriving protocol-specific
identity fields (Modbus, EtherNet/IP, PROFINET, S7, SNMP, BACnet, CIP)
from a single firmware_version source of truth.

The FirmwareVersionDeriver class eliminates the need for manual duplication
of firmware version information across multiple protocol identity override
fields in CVE vulnerability data.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ParsedVersion:
    """Parsed firmware version components.

    Extracts major, minor, patch, and prefix from version strings like:
    - "3.10" -> major=3, minor=10
    - "V3.10.2" -> prefix="V", major=3, minor=10, patch=2
    - "32.011" -> major=32, minor=11 (leading zeros stripped from minor)
    """

    raw: str  # Original string: "V3.10.2"
    major: int = 0  # 3
    minor: int = 0  # 10
    patch: int | None = None  # 2 (optional)
    prefix: str = ""  # "V" or "" or "FW"
    suffix: str = ""  # Build info like "-beta" or " Build 1234"

    @property
    def major_minor(self) -> str:
        """Return major.minor string format."""
        return f"{self.major}.{self.minor}"

    @property
    def full_numeric(self) -> str:
        """Return full numeric version without prefix.

        Returns major.minor.patch if patch exists, otherwise major.minor.
        """
        if self.patch is not None:
            return f"{self.major}.{self.minor}.{self.patch}"
        return f"{self.major}.{self.minor}"

    @property
    def padded_minor(self) -> str:
        """Return version with zero-padded minor for formats like 32.011."""
        if self.patch is not None:
            return f"{self.major}.{self.minor:03d}.{self.patch}"
        return f"{self.major}.{self.minor:03d}"


class FirmwareVersionParser:
    """Parse firmware version strings into components.

    Handles various version string formats:
    - Standard: "3.10", "3.10.2"
    - With prefix: "V3.10", "v3.10.2", "FW 3.10"
    - Rockwell style: "32.011" (padded minor)
    - With suffix: "3.10-beta", "3.10 Build 1234"
    """

    # Common version patterns in order of specificity
    VERSION_PATTERNS = [
        # V3.10.2, V3.10, v3.10 (prefix with optional patch)
        r"^(?P<prefix>[Vv])(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?(?P<suffix>.*)$",
        # FW 3.10.2, FW3.10 (firmware prefix)
        r"^(?P<prefix>FW\s?)(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?(?P<suffix>.*)$",
        # 32.011, 3.10.2, 3.10 (no prefix)
        r"^(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?(?P<suffix>.*)$",
    ]

    @classmethod
    def parse(cls, version: str) -> ParsedVersion:
        """Parse a firmware version string into components.

        Args:
            version: Firmware version string (e.g., "V3.10", "32.011", "3.10.2")

        Returns:
            ParsedVersion with extracted components. Returns defaults if unparseable.
        """
        if not version:
            return ParsedVersion(raw="")

        version = version.strip()

        for pattern in cls.VERSION_PATTERNS:
            match = re.match(pattern, version)
            if match:
                groups = match.groupdict()
                return ParsedVersion(
                    raw=version,
                    major=int(groups["major"]),
                    minor=int(groups["minor"]),
                    patch=int(groups["patch"]) if groups.get("patch") else None,
                    prefix=groups.get("prefix", "") or "",
                    suffix=groups.get("suffix", "") or "",
                )

        # Fallback: return unparsed
        logger.warning(f"Could not parse firmware version: {version}")
        return ParsedVersion(raw=version, major=0, minor=0)


class FirmwareVersionDeriver:
    """Auto-derive protocol-specific identity fields from firmware_version.

    This class provides a single source of truth for firmware versions
    and auto-generates protocol-specific identity fields with appropriate
    formatting for each protocol.

    Usage:
        deriver = FirmwareVersionDeriver(
            firmware_version="3.10",
            base_identity={"snmp_identity": {"sys_descr": "Device V1.0"}},
        )
        derived = deriver.derive_all()
        # derived["modbus_identity"]["major_minor_revision"] == "3.10"
        # derived["ethernet_ip_identity"]["revision_major"] == 3
        # derived["snmp_identity"]["sys_descr"] == "Device V3.10"
    """

    def __init__(
        self,
        firmware_version: str,
        base_identity: dict[str, Any] | None = None,
        manual_overrides: dict[str, Any] | None = None,
    ):
        """Initialize with firmware version and optional base identity.

        Args:
            firmware_version: Canonical firmware version (e.g., "3.10")
            base_identity: Base fingerprint identity data for each protocol
            manual_overrides: Optional manual overrides that take precedence
        """
        self.firmware_version = firmware_version
        self.parsed = FirmwareVersionParser.parse(firmware_version)
        self.base_identity = base_identity or {}
        self.manual_overrides = manual_overrides or {}

    def derive_modbus(self) -> dict[str, Any]:
        """Derive Modbus FC 43 identity fields.

        Modbus uses major_minor_revision as a string.
        Format: "3.10" or "32.011" (preserves original format)
        """
        derived = {
            "major_minor_revision": self.parsed.full_numeric,
        }

        # Merge with base and apply manual overrides
        result = {**self.base_identity.get("modbus_identity", {}), **derived}
        if modbus_override := self.manual_overrides.get("modbus_identity_override"):
            result.update(modbus_override)

        return result

    def derive_ethernet_ip(self) -> dict[str, Any]:
        """Derive EtherNet/IP ListIdentity fields.

        EtherNet/IP uses separate revision_major and revision_minor integers.
        """
        derived = {
            "revision_major": self.parsed.major,
            "revision_minor": self.parsed.minor,
        }

        result = {**self.base_identity.get("ethernet_ip_identity", {}), **derived}
        if eip_override := self.manual_overrides.get("ethernet_ip_identity_override"):
            result.update(eip_override)

        return result

    def derive_cip(self) -> dict[str, Any]:
        """Derive CIP Identity Object fields.

        CIP uses revision_major and revision_minor integers.
        """
        derived = {
            "revision_major": self.parsed.major,
            "revision_minor": self.parsed.minor,
        }

        result = {**self.base_identity.get("cip_identity_object", {}), **derived}
        if cip_override := self.manual_overrides.get("cip_identity_override"):
            result.update(cip_override)

        return result

    def derive_profinet(self) -> dict[str, Any]:
        """Derive PROFINET DCP identity fields.

        PROFINET uses sw_release with "V" prefix.
        Format: "V3.10" or "V3.10.0"
        """
        # Ensure V prefix
        if self.parsed.prefix.upper() == "V":
            sw_release = self.firmware_version
        else:
            sw_release = f"V{self.parsed.full_numeric}"

        derived = {
            "sw_release": sw_release,
        }

        result = {**self.base_identity.get("profinet_identity", {}), **derived}
        if pn_override := self.manual_overrides.get("profinet_identity_override"):
            result.update(pn_override)

        return result

    def derive_s7(self) -> dict[str, Any]:
        """Derive S7comm SZL identity fields.

        S7 uses firmware_version with "V" prefix.
        Format: "V3.10.0"
        """
        # Ensure V prefix
        if self.parsed.prefix.upper() == "V":
            fw_version = self.firmware_version
        else:
            fw_version = f"V{self.parsed.full_numeric}"

        derived = {
            "firmware_version": fw_version,
        }

        result = {**self.base_identity.get("s7_identity", {}), **derived}
        if s7_override := self.manual_overrides.get("s7_identity_override"):
            result.update(s7_override)

        return result

    def derive_snmp(
        self,
        sys_descr_template: str | None = None,
    ) -> dict[str, Any]:
        """Derive SNMP identity fields with firmware embedded in sys_descr.

        SNMP sys_descr typically embeds firmware version in a longer string.
        The template can use {firmware_version}, {major}, {minor}, {patch} placeholders.

        Args:
            sys_descr_template: Template string with placeholders
                               e.g., "Econolite Cobalt ATC {firmware_version}"

        Returns:
            SNMP identity dict with firmware-interpolated sys_descr
        """
        base_snmp = self.base_identity.get("snmp_identity", {})

        # Determine sys_descr
        if sys_descr_template:
            sys_descr = sys_descr_template.format(
                firmware_version=self.firmware_version,
                major=self.parsed.major,
                minor=self.parsed.minor,
                patch=self.parsed.patch or "",
            )
        elif "sys_descr_template" in base_snmp:
            # Use template from base identity
            sys_descr = base_snmp["sys_descr_template"].format(
                firmware_version=self.firmware_version,
                major=self.parsed.major,
                minor=self.parsed.minor,
                patch=self.parsed.patch or "",
            )
        elif base_snmp.get("sys_descr"):
            # Try to replace version pattern in existing string
            sys_descr = self._update_version_in_string(base_snmp["sys_descr"])
        else:
            sys_descr = f"Device Firmware V{self.parsed.full_numeric}"

        derived = {"sys_descr": sys_descr}

        result = {**base_snmp, **derived}
        # Remove template field from result
        result.pop("sys_descr_template", None)

        if snmp_override := self.manual_overrides.get("snmp_identity_override"):
            result.update(snmp_override)

        return result

    def _update_version_in_string(self, text: str) -> str:
        """Replace version pattern in an existing string.

        Handles patterns like "Controller V2.1.4" -> "Controller V3.10"
        """
        # Try to find and replace version pattern
        version_pattern = r"[Vv]?\d+\.\d+(?:\.\d+)?"

        # Determine replacement format based on original format
        match = re.search(version_pattern, text)
        if match:
            original = match.group()
            if original.startswith(("V", "v")):
                replacement = f"V{self.parsed.full_numeric}"
            else:
                replacement = self.parsed.full_numeric
            return re.sub(version_pattern, replacement, text, count=1)

        # No version found, append
        return f"{text} V{self.parsed.full_numeric}"

    def derive_bacnet(self) -> dict[str, Any]:
        """Derive BACnet I-Am identity fields.

        BACnet uses firmware_revision as a string.
        Format: "3.10" or "3.10.2"
        """
        derived = {
            "firmware_revision": self.parsed.full_numeric,
        }

        result = {**self.base_identity.get("bacnet_identity", {}), **derived}
        if bacnet_override := self.manual_overrides.get("bacnet_identity_override"):
            result.update(bacnet_override)

        return result

    def derive_all(
        self,
        protocols: list[str] | None = None,
        snmp_sys_descr_template: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Derive identity fields for all (or specified) protocols.

        Args:
            protocols: List of protocols to derive for, or None for all.
                      Options: modbus, ethernet_ip, cip, profinet, s7, snmp, bacnet
            snmp_sys_descr_template: Template for SNMP sys_descr

        Returns:
            Dictionary with protocol names as keys and identity dicts as values
        """
        all_protocols = [
            "modbus",
            "ethernet_ip",
            "cip",
            "profinet",
            "s7",
            "snmp",
            "bacnet",
        ]
        target_protocols = protocols or all_protocols

        result = {}

        if "modbus" in target_protocols:
            result["modbus_identity"] = self.derive_modbus()

        if "ethernet_ip" in target_protocols:
            result["ethernet_ip_identity"] = self.derive_ethernet_ip()

        if "cip" in target_protocols:
            result["cip_identity_object"] = self.derive_cip()

        if "profinet" in target_protocols:
            result["profinet_identity"] = self.derive_profinet()

        if "s7" in target_protocols:
            result["s7_identity"] = self.derive_s7()

        if "snmp" in target_protocols:
            result["snmp_identity"] = self.derive_snmp(snmp_sys_descr_template)

        if "bacnet" in target_protocols:
            result["bacnet_identity"] = self.derive_bacnet()

        logger.debug(
            f"Auto-derived protocol identities from firmware_version={self.firmware_version}"
        )

        return result
