"""Device template dataclasses.

Defines the core types used across the device template library:
FirmwareVariant, InstanceGenerationRules, DeviceTemplate, DeviceInstance.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class FirmwareVariant:
    """A specific firmware version for a device template."""

    version: str
    release_date: date
    is_latest: bool = False
    is_default: bool = False  # Suggested for new scenarios
    cves: list[str] = field(default_factory=list)
    notes: str | None = None

    # Protocol identity overrides for this firmware version
    # These get merged with the template's base identities
    identity_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class InstanceGenerationRules:
    """Rules for generating unique device instances."""

    # Serial number format using placeholders:
    # {8HEX} = 8 hex chars, {6NUM} = 6 digits, {4ALPHA} = 4 letters
    # Example: "S C-{8HEX}" -> "S C-A1B2C3D4"
    serial_format: str

    # Station name pattern using placeholders:
    # {role} = device role (plc, hmi, etc)
    # {vendor_short} = abbreviated vendor (SIE, ROC, etc)
    # {model_short} = abbreviated model
    # {seq} = sequence number (001, 002, etc)
    # {location} = user-provided or generated location
    # Example: "{role}-{model_short}-{seq}" -> "plc-s71500-001"
    station_name_pattern: str

    # Vendor-specific short codes
    vendor_short: str
    model_short: str


@dataclass
class DeviceTemplate:
    """Complete device template with all characteristics."""

    # Identity
    id: str  # Unique template ID: "siemens/s7-1500/cpu-1516-3"
    vendor: str
    vendor_family: str
    model: str
    model_name: str
    device_type: str  # plc, hmi, drive, rtu, etc.
    description: str

    # Network characteristics (static per model)
    oui_prefixes: list[str]
    tcp_stack: dict[str, Any]
    response_timing: dict[str, Any]
    error_behavior: dict[str, Any] = field(default_factory=dict)

    # Supported protocols
    supported_protocols: list[str] = field(default_factory=list)

    # Instance generation rules
    instance_rules: InstanceGenerationRules | None = None

    # Firmware variants
    firmware_variants: list[FirmwareVariant] = field(default_factory=list)

    # Base protocol identities (firmware version merged in at runtime)
    modbus_identity: dict[str, Any] | None = None
    ethernet_ip_identity: dict[str, Any] | None = None
    profinet_identity: dict[str, Any] | None = None
    s7_identity: dict[str, Any] | None = None
    bacnet_identity: dict[str, Any] | None = None
    snmp_identity: dict[str, Any] | None = None
    opc_ua_identity: dict[str, Any] | None = None
    lldp_identity: dict[str, Any] | None = None  # Layer 2 discovery (IEEE 802.1AB)
    cdp_identity: dict[str, Any] | None = None   # Cisco Discovery Protocol

    # Protocol-specific quirks
    protocol_quirks: dict[str, Any] = field(default_factory=dict)

    # Metadata
    is_builtin: bool = True

    def get_default_firmware(self) -> FirmwareVariant | None:
        """Get the default firmware variant."""
        for fw in self.firmware_variants:
            if fw.is_default:
                return fw
        # Fall back to latest
        for fw in self.firmware_variants:
            if fw.is_latest:
                return fw
        # Fall back to first
        return self.firmware_variants[0] if self.firmware_variants else None

    def get_firmware_by_version(self, version: str) -> FirmwareVariant | None:
        """Get a specific firmware variant by version string."""
        for fw in self.firmware_variants:
            if fw.version == version:
                return fw
        return None

    def get_vulnerable_firmwares(self) -> list[FirmwareVariant]:
        """Get all firmware variants with known CVEs."""
        return [fw for fw in self.firmware_variants if fw.cves]

    def get_latest_firmware(self) -> FirmwareVariant | None:
        """Get the latest (patched) firmware variant."""
        for fw in self.firmware_variants:
            if fw.is_latest:
                return fw
        return None


@dataclass
class DeviceInstance:
    """A generated device instance for a scenario."""

    template_id: str
    firmware_version: str

    # Unique instance values
    serial_number: str
    station_name: str
    mac_address: str  # Generated from OUI
    ip_address: str  # From IP management

    # Associated CVEs (from firmware variant)
    cves: list[str] = field(default_factory=list)

    # Merged protocol identities (template + firmware + instance)
    merged_identities: dict[str, dict[str, Any]] = field(default_factory=dict)
