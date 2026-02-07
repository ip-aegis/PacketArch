"""Device Template Library with Firmware Variants.

This module implements a three-level architecture for device fingerprinting:

1. DEVICE TEMPLATE (static, in library)
   - Vendor, model, device type
   - Base characteristics (TCP stack, timing, OUI prefixes)
   - Instance generation rules (serial format, station name pattern)
   - Firmware variants with CVE associations
   - Base protocol identities

2. FIRMWARE VARIANT (per template)
   - Version string
   - Release date
   - CVE associations
   - Identity overrides (version-specific fields)

3. DEVICE INSTANCE (generated per scenario device)
   - Selected firmware variant
   - Unique serial number (generated from template rules)
   - Unique station/device name
   - Unique MAC and IP (handled by existing systems)
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any
import random
import string
import re


# =============================================================================
# Data Classes
# =============================================================================


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


# =============================================================================
# Serial Number and Station Name Generation
# =============================================================================


def generate_serial_number(format_pattern: str, existing_serials: set[str] | None = None) -> str:
    """Generate a unique serial number based on format pattern.

    Supported placeholders:
    - {NHEX}: N random hex characters (e.g., {8HEX})
    - {NNUM}: N random digits (e.g., {6NUM})
    - {NALPHA}: N random uppercase letters (e.g., {4ALPHA})
    - {NALPHANUM}: N random alphanumeric (e.g., {10ALPHANUM})
    """
    existing = existing_serials or set()
    max_attempts = 100

    for _ in range(max_attempts):
        result = format_pattern

        # Process hex placeholders
        for match in re.finditer(r'\{(\d+)HEX\}', format_pattern):
            n = int(match.group(1))
            hex_str = ''.join(random.choices('0123456789ABCDEF', k=n))
            result = result.replace(match.group(0), hex_str, 1)

        # Process numeric placeholders
        for match in re.finditer(r'\{(\d+)NUM\}', format_pattern):
            n = int(match.group(1))
            num_str = ''.join(random.choices('0123456789', k=n))
            result = result.replace(match.group(0), num_str, 1)

        # Process alpha placeholders
        for match in re.finditer(r'\{(\d+)ALPHA\}', format_pattern):
            n = int(match.group(1))
            alpha_str = ''.join(random.choices(string.ascii_uppercase, k=n))
            result = result.replace(match.group(0), alpha_str, 1)

        # Process alphanumeric placeholders
        for match in re.finditer(r'\{(\d+)ALPHANUM\}', format_pattern):
            n = int(match.group(1))
            alphanum_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))
            result = result.replace(match.group(0), alphanum_str, 1)

        if result not in existing:
            return result

    raise ValueError(f"Could not generate unique serial after {max_attempts} attempts")


def generate_station_name(
    pattern: str,
    role: str = "device",
    vendor_short: str = "DEV",
    model_short: str = "001",
    sequence: int = 1,
    location: str | None = None,
    existing_names: set[str] | None = None,
) -> str:
    """Generate a unique station name based on pattern.

    Supported placeholders:
    - {role}: Device role (plc, hmi, drive, etc.)
    - {vendor_short}: Abbreviated vendor name
    - {model_short}: Abbreviated model name
    - {seq}: Sequence number (zero-padded to 3 digits)
    - {seq2}: Sequence number (zero-padded to 2 digits)
    - {location}: User-provided location or "loc"
    """
    existing = existing_names or set()

    result = pattern.lower()
    result = result.replace("{role}", role.lower())
    result = result.replace("{vendor_short}", vendor_short.lower())
    result = result.replace("{model_short}", model_short.lower())
    result = result.replace("{seq}", f"{sequence:03d}")
    result = result.replace("{seq2}", f"{sequence:02d}")
    result = result.replace("{location}", (location or "loc").lower())

    # Ensure uniqueness by appending sequence if needed
    base_name = result
    counter = sequence
    while result in existing:
        counter += 1
        result = f"{base_name}-{counter}"

    return result


def merge_identity(
    base_identity: dict[str, Any],
    firmware_overrides: dict[str, Any],
    instance_values: dict[str, Any],
) -> dict[str, Any]:
    """Merge base identity with firmware and instance overrides.

    Priority (highest to lowest):
    1. Instance values (serial_number, station_name)
    2. Firmware overrides (version-specific fields)
    3. Base identity (static template values)
    """
    result = dict(base_identity) if base_identity else {}

    # Apply firmware overrides
    if firmware_overrides:
        result.update(firmware_overrides)

    # Apply instance values
    if instance_values:
        result.update(instance_values)

    return result


# =============================================================================
# Device Template Library
# =============================================================================


DEVICE_TEMPLATES: dict[str, DeviceTemplate] = {}


def _register_template(template: DeviceTemplate) -> None:
    """Register a device template in the library."""
    DEVICE_TEMPLATES[template.id] = template


# -----------------------------------------------------------------------------
# SIEMENS TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="siemens/s7-1500/cpu-1516-3",
    vendor="Siemens",
    vendor_family="S7-1500",
    model="6ES7 516-3AN02-0AB0",
    model_name="CPU 1516-3 PN/DP",
    device_type="plc",
    description="High-performance S7-1500 CPU with PROFINET and PROFIBUS interfaces",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 29200,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
        "ecn_support": False,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
        "outlier_probability": 0.003,
        "outlier_multiplier": 5.0,
    },

    error_behavior={
        "supported_exception_codes": [1, 2, 3, 4, 5, 6],
        "exception_probability": 0.0003,
        "timeout_probability": 0.0001,
    },

    supported_protocols=["profinet", "s7comm", "modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="S C-{8HEX}",
        station_name_pattern="{role}-s71500-{seq}",
        vendor_short="SIE",
        model_short="1516",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.0.3",
            release_date=date(2023, 11, 15),
            is_latest=True,
            is_default=True,
            cves=[],
            notes="Latest version with security patches",
        ),
        FirmwareVariant(
            version="V2.9.7",
            release_date=date(2023, 6, 20),
            cves=[],
            notes="Previous stable release",
        ),
        FirmwareVariant(
            version="V2.9.4",
            release_date=date(2022, 11, 10),
            cves=["CVE-2022-38465"],
            notes="Vulnerable to authentication bypass",
            identity_overrides={
                "modbus_identity": {"major_minor_revision": "V2.9.4"},
                "profinet_identity": {"im0_sw_revision": "V2.9.4"},
            },
        ),
        FirmwareVariant(
            version="V2.8.1",
            release_date=date(2021, 8, 15),
            cves=["CVE-2022-38465", "CVE-2021-37205"],
            notes="Multiple vulnerabilities - memory corruption and auth bypass",
            identity_overrides={
                "modbus_identity": {"major_minor_revision": "V2.8.1"},
                "profinet_identity": {"im0_sw_revision": "V2.8.1"},
            },
        ),
        FirmwareVariant(
            version="V2.5.0",
            release_date=date(2020, 3, 10),
            cves=["CVE-2022-38465", "CVE-2021-37205", "CVE-2020-15782", "CVE-2019-13945"],
            notes="Legacy firmware with critical vulnerabilities",
            identity_overrides={
                "modbus_identity": {"major_minor_revision": "V2.5.0"},
                "profinet_identity": {"im0_sw_revision": "V2.5.0"},
            },
        ),
    ],

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "6ES7 516-3AN02-0AB0",
        "vendor_url": "http://www.siemens.com",
        "product_name": "CPU 1516-3 PN/DP",
        "model_name": "S7-1500",
        # major_minor_revision merged from firmware
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0301,
        "device_role": 2,  # Controller
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6ES7 516-3AN02-0AB0",
        "im0_hw_revision": 2,
        # station_name and im0_sw_revision merged from instance/firmware
    },

    s7_identity={
        "module_type": "CPU 1516-3 PN/DP",
        "copyright": "Original Siemens Equipment",
        "module_name": "PLC_1",
        # serial_number and plant_id merged from instance
    },

    protocol_quirks={
        "profinet_cycle_time_us": 1000,
        "s7_max_pdu_size": 960,
        "s7_connection_type": 0x01,  # PG connection
    },
))


_register_template(DeviceTemplate(
    id="siemens/s7-1200/cpu-1214c",
    vendor="Siemens",
    vendor_family="S7-1200",
    model="6ES7 214-1AG40-0XB0",
    model_name="CPU 1214C DC/DC/DC",
    device_type="plc",
    description="Compact S7-1200 CPU for small to medium automation tasks",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "window_scaling": 5,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 25.0,
        "mean_ms": 6.0,
        "std_dev_ms": 4.0,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "s7comm", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="S C-{8HEX}",
        station_name_pattern="{role}-s71200-{seq}",
        vendor_short="SIE",
        model_short="1214",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.6.0",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.5.2",
            release_date=date(2023, 5, 20),
            cves=[],
        ),
        FirmwareVariant(
            version="V4.4.0",
            release_date=date(2022, 8, 10),
            cves=["CVE-2022-38465"],
        ),
        FirmwareVariant(
            version="V4.2.1",
            release_date=date(2021, 3, 15),
            cves=["CVE-2022-38465", "CVE-2021-37185"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "6ES7 214-1AG40-0XB0",
        "product_name": "CPU 1214C DC/DC/DC",
        "model_name": "S7-1200",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x010D,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6ES7 214-1AG40-0XB0",
    },
))


_register_template(DeviceTemplate(
    id="siemens/hmi/ktp700",
    vendor="Siemens",
    vendor_family="SIMATIC HMI",
    model="6AV2 123-2GB03-0AX0",
    model_name="KTP700 Basic",
    device_type="hmi",
    description="7-inch Basic Panel with touch and key operation",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["profinet", "s7comm"],

    instance_rules=InstanceGenerationRules(
        serial_format="S V-{8HEX}",
        station_name_pattern="hmi-{location}-{seq}",
        vendor_short="SIE",
        model_short="ktp700",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V18.0.0.0",
            release_date=date(2023, 10, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V17.0.0.0",
            release_date=date(2022, 9, 15),
            cves=["CVE-2022-40227"],
        ),
        FirmwareVariant(
            version="V16.0.0.0",
            release_date=date(2021, 6, 20),
            cves=["CVE-2022-40227", "CVE-2021-27383"],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0403,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6AV2 123-2GB03-0AX0",
    },
))


# CPU 1517-3 PN/DP - High-performance S7-1500 CPU
_register_template(DeviceTemplate(
    id="siemens/s7-1500/cpu-1517-3",
    vendor="Siemens",
    vendor_family="S7-1500",
    model="6ES7 517-3AP00-0AB0",
    model_name="CPU 1517-3 PN/DP",
    device_type="plc",
    description="High-performance S7-1500 CPU with PROFINET and PROFIBUS interfaces",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 29200,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
        "ecn_support": False,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
        "outlier_probability": 0.002,
        "outlier_multiplier": 5.0,
    },

    error_behavior={
        "supported_exception_codes": [1, 2, 3, 4, 5, 6],
        "exception_probability": 0.0003,
        "timeout_probability": 0.0001,
    },

    supported_protocols=["profinet", "s7comm", "modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="S C-{8HEX}",
        station_name_pattern="{role}-s71517-{seq}",
        vendor_short="SIE",
        model_short="1517",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.0.3",
            release_date=date(2023, 11, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.9.4",
            release_date=date(2022, 11, 10),
            cves=["CVE-2022-38465"],
            notes="Vulnerable to authentication bypass",
        ),
    ],

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "6ES7 517-3AP00-0AB0",
        "vendor_url": "http://www.siemens.com",
        "product_name": "CPU 1517-3 PN/DP",
        "model_name": "S7-1500",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0302,
        "device_role": 2,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6ES7 517-3AP00-0AB0",
        "im0_hw_revision": 2,
    },

    s7_identity={
        "module_type": "CPU 1517-3 PN/DP",
        "order_code": "6ES7 517-3AP00-0AB0",
        "copyright": "Original Siemens Equipment",
        "module_name": "PLC_1",
    },

    protocol_quirks={
        "profinet_cycle_time_us": 500,
        "s7_max_pdu_size": 960,
        "s7_connection_type": 0x01,
    },
))


# CPU 1516-3 PN/DP variant (order code ending in 01)
_register_template(DeviceTemplate(
    id="siemens/s7-1500/cpu-1516-3-v1",
    vendor="Siemens",
    vendor_family="S7-1500",
    model="6ES7 516-3AN01-0AB0",
    model_name="CPU 1516-3 PN/DP",
    device_type="plc",
    description="S7-1500 CPU with PROFINET and PROFIBUS interfaces (earlier version)",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 29200,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "s7comm", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="S C-{8HEX}",
        station_name_pattern="{role}-s71516-{seq}",
        vendor_short="SIE",
        model_short="1516",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.9.7",
            release_date=date(2023, 6, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.8.1",
            release_date=date(2021, 8, 15),
            cves=["CVE-2021-37205"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "6ES7 516-3AN01-0AB0",
        "product_name": "CPU 1516-3 PN/DP",
        "model_name": "S7-1500",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0301,
        "device_role": 2,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6ES7 516-3AN01-0AB0",
    },
))


# CPU 1511-1 PN - Compact S7-1500 CPU
_register_template(DeviceTemplate(
    id="siemens/s7-1500/cpu-1511-1",
    vendor="Siemens",
    vendor_family="S7-1500",
    model="6ES7 511-1AK02-0AB0",
    model_name="CPU 1511-1 PN",
    device_type="plc",
    description="Compact S7-1500 CPU for small automation tasks",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "window_scaling": 5,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 4.0,
        "std_dev_ms": 2.5,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "s7comm", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="S C-{8HEX}",
        station_name_pattern="{role}-s71511-{seq}",
        vendor_short="SIE",
        model_short="1511",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.0.1",
            release_date=date(2023, 9, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "6ES7 511-1AK02-0AB0",
        "product_name": "CPU 1511-1 PN",
        "model_name": "S7-1500",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0101,
        "device_role": 2,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6ES7 511-1AK02-0AB0",
    },

    s7_identity={
        "module_type": "CPU 1511-1 PN",
        "order_code": "6ES7 511-1AK02-0AB0",
        "copyright": "Original Siemens Equipment",
        "module_name": "PLC_1",
    },
))


# CPU 1516F-3 PN/DP - Failsafe S7-1500 CPU
_register_template(DeviceTemplate(
    id="siemens/s7-1500/cpu-1516f-3",
    vendor="Siemens",
    vendor_family="S7-1500F",
    model="6ES7 516-3FN01-0AB0",
    model_name="CPU 1516F-3 PN/DP",
    device_type="safety_plc",
    description="Failsafe S7-1500 CPU for safety applications up to SIL3/PLe",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 29200,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 10.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "profisafe", "s7comm", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="S C-{8HEX}",
        station_name_pattern="{role}-s71516f-{seq}",
        vendor_short="SIE",
        model_short="1516F",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.0.3",
            release_date=date(2023, 11, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.9.4",
            release_date=date(2022, 11, 10),
            cves=["CVE-2022-38465"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "6ES7 516-3FN01-0AB0",
        "product_name": "CPU 1516F-3 PN/DP",
        "model_name": "S7-1500F",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0311,
        "device_role": 2,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6ES7 516-3FN01-0AB0",
    },
))


# TP1200 Comfort HMI
_register_template(DeviceTemplate(
    id="siemens/hmi/tp1200-comfort",
    vendor="Siemens",
    vendor_family="SIMATIC HMI",
    model="6AV2 124-0MC01-0AX0",
    model_name="TP1200 Comfort",
    device_type="hmi",
    description="12-inch Comfort Panel with touch operation",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["profinet", "s7comm"],

    instance_rules=InstanceGenerationRules(
        serial_format="S V-{8HEX}",
        station_name_pattern="hmi-{location}-{seq}",
        vendor_short="SIE",
        model_short="tp1200",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V18.0.0.0",
            release_date=date(2023, 10, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V17.0.0.0",
            release_date=date(2022, 9, 15),
            cves=["CVE-2022-40227"],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0424,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6AV2 124-0MC01-0AX0",
    },
))


# KTP900 Basic HMI
_register_template(DeviceTemplate(
    id="siemens/hmi/ktp900-basic",
    vendor="Siemens",
    vendor_family="SIMATIC HMI",
    model="6AV2 123-2JB03-0AX0",
    model_name="KTP900 Basic",
    device_type="hmi",
    description="9-inch Basic Panel with touch and key operation",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["profinet", "s7comm"],

    instance_rules=InstanceGenerationRules(
        serial_format="S V-{8HEX}",
        station_name_pattern="hmi-{location}-{seq}",
        vendor_short="SIE",
        model_short="ktp900",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V18.0.0.0",
            release_date=date(2023, 10, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0409,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6AV2 123-2JB03-0AX0",
    },
))


# SINAMICS G120C Drive
_register_template(DeviceTemplate(
    id="siemens/drives/g120c",
    vendor="Siemens",
    vendor_family="SINAMICS",
    model="6SL3210-1PE21-1UL0",
    model_name="SINAMICS G120C",
    device_type="drive",
    description="Compact frequency converter for simple drive tasks",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 30.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="T-{10ALPHANUM}",
        station_name_pattern="drive-g120c-{seq}",
        vendor_short="SIE",
        model_short="G120C",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.8",
            release_date=date(2023, 6, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "6SL3210-1PE21-1UL0",
        "product_name": "SINAMICS G120C",
        "model_name": "SINAMICS",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0A01,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6SL3210-1PE21-1UL0",
    },
))


# SINAMICS S120 Servo Drive
_register_template(DeviceTemplate(
    id="siemens/drives/s120",
    vendor="Siemens",
    vendor_family="SINAMICS",
    model="6SL3310-1TE32-6AA3",
    model_name="SINAMICS S120",
    device_type="servo",
    description="High-performance servo drive system for motion control",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 29200,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.25,
        "max_ms": 5.0,
        "mean_ms": 1.0,
        "std_dev_ms": 0.5,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="T-{10ALPHANUM}",
        station_name_pattern="servo-s120-{seq}",
        vendor_short="SIE",
        model_short="S120",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.2",
            release_date=date(2023, 8, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0A20,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6SL3310-1TE32-6AA3",
    },
))


# SINAMICS G115D Distributed Drive
_register_template(DeviceTemplate(
    id="siemens/drives/g115d",
    vendor="Siemens",
    vendor_family="SINAMICS",
    model="6SL3525-0PE21-5AA1",
    model_name="SINAMICS G115D",
    device_type="drive",
    description="Distributed frequency converter for conveyor applications",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 25.0,
        "mean_ms": 6.0,
        "std_dev_ms": 4.0,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="T-{10ALPHANUM}",
        station_name_pattern="drive-g115d-{seq}",
        vendor_short="SIE",
        model_short="G115D",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V1.1",
            release_date=date(2023, 3, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0A15,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6SL3525-0PE21-5AA1",
    },
))


# ET 200SP IM155-6 PN Remote I/O
_register_template(DeviceTemplate(
    id="siemens/io/et200sp-im155-6",
    vendor="Siemens",
    vendor_family="ET 200SP",
    model="6ES7155-6AU01-0BN0",
    model_name="ET 200SP IM155-6 PN",
    device_type="io_module",
    description="PROFINET interface module for ET 200SP distributed I/O",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 8192,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.25,
        "max_ms": 5.0,
        "mean_ms": 1.0,
        "std_dev_ms": 0.5,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="S C-{8HEX}",
        station_name_pattern="et200sp-{seq}",
        vendor_short="SIE",
        model_short="ET200SP",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.2.0",
            release_date=date(2023, 5, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0B01,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6ES7155-6AU01-0BN0",
    },
))


# SCALANCE XB208 Industrial Ethernet Switch
_register_template(DeviceTemplate(
    id="siemens/network/scalance-xb208",
    vendor="Siemens",
    vendor_family="SCALANCE",
    model="6GK5208-0BA00-2AB2",
    model_name="SCALANCE XB208",
    device_type="switch",
    description="Unmanaged Industrial Ethernet switch with 8 ports",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "AC:64:17"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="S V-{8HEX}",
        station_name_pattern="switch-xb208-{seq}",
        vendor_short="SIE",
        model_short="XB208",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.4",
            release_date=date(2023, 4, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "Siemens SCALANCE XB208 Industrial Ethernet Switch",
        "sys_object_id": "1.3.6.1.4.1.4329.6.1.2.208",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0C08,
        "device_role": 0,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6GK5208-0BA00-2AB2",
    },
))


# SCALANCE XM-400 Managed Industrial Ethernet Switch
_register_template(DeviceTemplate(
    id="siemens/network/scalance-xm400",
    vendor="Siemens",
    vendor_family="SCALANCE",
    model="6GK5408-8GS00-2AM2",
    model_name="SCALANCE XM-400",
    device_type="switch",
    description="Managed modular Industrial Ethernet switch for backbone networks",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "AC:64:17"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "window_scaling": 6,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.0,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="S V-{8HEX}",
        station_name_pattern="switch-xm400-{seq}",
        vendor_short="SIE",
        model_short="XM400",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.5",
            release_date=date(2023, 9, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V6.3",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-46143"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Siemens SCALANCE XM-400 Managed Industrial Ethernet Switch",
        "sys_object_id": "1.3.6.1.4.1.4329.6.1.2.400",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0C40,
        "device_role": 0,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6GK5408-8GS00-2AM2",
    },
))


# SCALANCE X-200 Industrial Ethernet Switch
_register_template(DeviceTemplate(
    id="siemens/network/scalance-x200",
    vendor="Siemens",
    vendor_family="SCALANCE",
    model="6GK5208-0UA00-5ES6",
    model_name="SCALANCE X-200",
    device_type="switch",
    description="Managed Industrial Ethernet switch for field-level networking",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "AC:64:17"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 12.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.8,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="S V-{8HEX}",
        station_name_pattern="switch-x200-{seq}",
        vendor_short="SIE",
        model_short="X200",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.5.2",
            release_date=date(2023, 7, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "Siemens SCALANCE X-200 Industrial Ethernet Switch",
        "sys_object_id": "1.3.6.1.4.1.4329.6.1.2.200",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0C20,
        "device_role": 0,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6GK5208-0UA00-5ES6",
    },
))


# CP-8000 Traffic Controller
_register_template(DeviceTemplate(
    id="siemens/traffic/cp-8000",
    vendor="Siemens",
    vendor_family="SITRAFFIC",
    model="6NH3112-3BA00-0XX0",
    model_name="CP-8000",
    device_type="traffic_controller",
    description="Central traffic management controller for ITS applications",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 50.0,
        "mean_ms": 10.0,
        "std_dev_ms": 8.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="CP8-{8HEX}",
        station_name_pattern="tmc-cp8000-{seq}",
        vendor_short="SIE",
        model_short="CP8000",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V1.3.0",
            release_date=date(2023, 5, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V1.2.0",
            release_date=date(2022, 3, 15),
            cves=["CVE-2023-28489"],
            notes="Vulnerable to command injection",
        ),
    ],

    snmp_identity={
        "sys_descr": "Siemens SITRAFFIC CP-8000 Traffic Controller",
        "sys_object_id": "1.3.6.1.4.1.4329.10.8000",
    },
))


# C600 Traffic Controller
_register_template(DeviceTemplate(
    id="siemens/traffic/c600",
    vendor="Siemens",
    vendor_family="SITRAFFIC",
    model="C600",
    model_name="Siemens C600 Controller",
    device_type="traffic_controller",
    description="Field traffic signal controller with NTCIP support",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 100.0,
        "mean_ms": 20.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="C6-{8HEX}",
        station_name_pattern="signal-c600-{seq}",
        vendor_short="SIE",
        model_short="C600",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.5",
            release_date=date(2023, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "Siemens SITRAFFIC C600 Signal Controller",
        "sys_object_id": "1.3.6.1.4.1.4329.10.600",
    },
))


# M60 Master Traffic Controller
_register_template(DeviceTemplate(
    id="siemens/traffic/m60",
    vendor="Siemens",
    vendor_family="SITRAFFIC",
    model="M60",
    model_name="Siemens M60 Master",
    device_type="master_station",
    description="Master traffic signal controller for intersection coordination",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 40.0,
        "mean_ms": 8.0,
        "std_dev_ms": 6.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="M60-{8HEX}",
        station_name_pattern="master-m60-{seq}",
        vendor_short="SIE",
        model_short="M60",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.1",
            release_date=date(2023, 4, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.8",
            release_date=date(2021, 9, 15),
            cves=["CVE-2020-25230"],
            notes="Vulnerable to denial of service",
        ),
    ],

    snmp_identity={
        "sys_descr": "Siemens SITRAFFIC M60 Master Controller",
        "sys_object_id": "1.3.6.1.4.1.4329.10.60",
    },
))


# Desigo CC Building Management System
_register_template(DeviceTemplate(
    id="siemens/bms/desigo-cc",
    vendor="Siemens",
    vendor_family="Desigo",
    model="5WG1255-1AB02",
    model_name="Desigo CC",
    device_type="bms_controller",
    description="Building management system for HVAC, lighting, and access control",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 200.0,
        "mean_ms": 50.0,
        "std_dev_ms": 30.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet", "modbus_tcp", "snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="DCC-{8ALPHANUM}",
        station_name_pattern="desigo-cc-{seq}",
        vendor_short="SIE",
        model_short="DCC",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.0",
            release_date=date(2023, 6, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.2",
            release_date=date(2022, 1, 15),
            cves=["CVE-2022-31465"],
            notes="Privilege escalation vulnerability",
        ),
    ],

    bacnet_identity={
        "vendor_id": 42,
        "model_name": "Desigo CC",
        "device_instance": 0,
    },

    snmp_identity={
        "sys_descr": "Siemens Desigo CC Building Management System",
        "sys_object_id": "1.3.6.1.4.1.4329.20.255",
    },
))


# Siemens S7-300 Legacy PLC
_register_template(DeviceTemplate(
    id="siemens/s7-300/cpu-315-2-pn-dp",
    vendor="Siemens",
    vendor_family="S7-300",
    model="CPU 315-2 PN/DP",
    model_name="CPU 315-2 PN/DP",
    device_type="plc",
    description="S7-300 CPU with integrated PROFINET and PROFIBUS interfaces (legacy)",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": False,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 80.0,
        "mean_ms": 25.0,
        "std_dev_ms": 12.0,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "s7comm", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="S V-{6HEX}",
        station_name_pattern="s7300-{location}-{seq}",
        vendor_short="SIE",
        model_short="315",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.2.16",
            release_date=date(2019, 6, 1),
            is_latest=True,
            is_default=True,
            cves=["CVE-2019-10929"],
            notes="Legacy product - limited security updates",
        ),
        FirmwareVariant(
            version="V3.2.12",
            release_date=date(2017, 3, 15),
            cves=["CVE-2019-10929", "CVE-2017-2681"],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0102,
        "device_role": 2,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6ES7 315-2EH14-0AB0",
    },
))


# Siemens S7-400 Legacy PLC
_register_template(DeviceTemplate(
    id="siemens/s7-400/cpu-416-3-pn-dp",
    vendor="Siemens",
    vendor_family="S7-400",
    model="CPU 416-3 PN/DP",
    model_name="CPU 416-3 PN/DP",
    device_type="plc",
    description="High-end S7-400 CPU for complex automation tasks (legacy)",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "timestamps_enabled": False,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 50.0,
        "mean_ms": 15.0,
        "std_dev_ms": 8.0,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "s7comm", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="S V-{8HEX}",
        station_name_pattern="s7400-{location}-{seq}",
        vendor_short="SIE",
        model_short="416",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V7.0.9",
            release_date=date(2020, 2, 1),
            is_latest=True,
            is_default=True,
            cves=["CVE-2019-10929"],
            notes="Legacy product - limited security updates",
        ),
        FirmwareVariant(
            version="V6.0.8",
            release_date=date(2018, 5, 10),
            cves=["CVE-2019-10929", "CVE-2017-2681"],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0401,
        "device_role": 2,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6ES7 416-3XS07-0AB0",
    },
))


# Siemens ET 200MP Interface Module
_register_template(DeviceTemplate(
    id="siemens/et200mp/im155-5-pn",
    vendor="Siemens",
    vendor_family="ET 200MP",
    model="ET 200MP IM155-5 PN",
    model_name="ET 200MP IM155-5 PN",
    device_type="io_module",
    description="ET 200MP distributed I/O interface module for PROFINET",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 15.0,
        "mean_ms": 4.0,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="S E-{6HEX}",
        station_name_pattern="et200mp-{location}-{seq}",
        vendor_short="SIE",
        model_short="ET200MP",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.2.3",
            release_date=date(2023, 9, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0B01,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6ES7 155-5AA01-0AB0",
    },
))


# Siemens S7-1200 Safety CPU
_register_template(DeviceTemplate(
    id="siemens/s7-1200/cpu-1214fc",
    vendor="Siemens",
    vendor_family="S7-1200",
    model="CPU 1214FC DC/DC/DC",
    model_name="CPU 1214FC DC/DC/DC",
    device_type="safety_plc",
    description="S7-1200 Fail-safe CPU with integrated safety I/O",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 29200,
        "mss": 1460,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 20.0,
        "mean_ms": 5.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "profisafe", "s7comm"],

    instance_rules=InstanceGenerationRules(
        serial_format="S C-{6HEX}",
        station_name_pattern="s71200f-{location}-{seq}",
        vendor_short="SIE",
        model_short="1214FC",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.6.0",
            release_date=date(2023, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.5.0",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-38465"],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x010F,
        "device_role": 2,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6ES7 214-1HF40-0XB0",
    },
))


# Siemens WinCC Professional SCADA
_register_template(DeviceTemplate(
    id="siemens/wincc/professional",
    vendor="Siemens",
    vendor_family="WinCC",
    model="WinCC Professional",
    model_name="WinCC Professional",
    device_type="scada",
    description="SCADA system for visualization and process control",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "gaussian",
    },

    supported_protocols=["s7comm", "opc_ua", "modbus_tcp"],

    s7_identity={
        "order_code": "6AV2105-0DA07-0AA0",
        "module_type": "WinCC Professional V18",
        "firmware_version": "V18.0",
        "hardware_version": "N/A",
    },

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "WinCC Professional",
        "major_minor_revision": "V18.0",
        "vendor_url": "http://www.siemens.com",
        "product_name": "SIMATIC WinCC Professional",
        "model_name": "SCADA/HMI Runtime",
    },

    opc_ua_identity={
        "application_name": "Siemens SIMATIC WinCC",
        "application_uri": "urn:Siemens:SIMATIC:WinCC",
        "product_uri": "http://www.siemens.com/simatic-wincc",
        "manufacturer_name": "Siemens AG",
        "product_name": "SIMATIC WinCC Professional",
        "software_version": "18.0.0",
        "build_number": "V18.0",
        "build_date": "2023-06-01T12:00:00Z",
    },

    instance_rules=InstanceGenerationRules(
        serial_format="WINCC-{6HEX}",
        station_name_pattern="wincc-{location}-{seq}",
        vendor_short="SIE",
        model_short="WinCC",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V18.0",
            release_date=date(2023, 10, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V17.0",
            release_date=date(2022, 4, 15),
            cves=["CVE-2022-32260"],
        ),
    ],
))


# -----------------------------------------------------------------------------
# ROCKWELL AUTOMATION TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="rockwell/controllogix/l83e",
    vendor="Rockwell",
    vendor_family="ControlLogix",
    model="1756-L83E",
    model_name="ControlLogix 5580",
    device_type="plc",
    description="High-performance ControlLogix controller for complex applications",

    oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16", "E4:90:69"],

    tcp_stack={
        "ttl": 128,  # Windows-based
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "nop_padding": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.5,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
        "outlier_probability": 0.005,
        "outlier_multiplier": 4.0,
    },

    error_behavior={
        "supported_exception_codes": [1, 2, 3, 4, 6],
        "exception_probability": 0.0005,
        "timeout_probability": 0.0002,
        "retry_behavior": True,
        "max_retries": 3,
    },

    supported_protocols=["ethernet_ip", "modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{8HEX}",
        station_name_pattern="{model_short}_{role}_{seq}",
        vendor_short="ROC",
        model_short="L83E",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V34.011",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V33.013",
            release_date=date(2023, 8, 15),
            cves=[],
        ),
        FirmwareVariant(
            version="V32.011",
            release_date=date(2022, 11, 20),
            cves=["CVE-2022-3157"],
            notes="Vulnerable to DoS via malformed CIP packets",
        ),
        FirmwareVariant(
            version="V31.011",
            release_date=date(2021, 9, 10),
            cves=["CVE-2022-3157", "CVE-2022-1161"],
            notes="Multiple CIP vulnerabilities",
        ),
        FirmwareVariant(
            version="V28.015",
            release_date=date(2019, 6, 5),
            cves=["CVE-2022-3157", "CVE-2022-1161", "CVE-2020-6998", "CVE-2019-10955"],
            notes="Legacy firmware with critical vulnerabilities",
        ),
    ],

    modbus_identity={
        "vendor_name": "Rockwell Automation/Allen-Bradley",
        "product_code": "1756-L83E/B",
        "vendor_url": "http://www.rockwellautomation.com",
        "product_name": "1756-L83E Logix5580 Controller",
        "model_name": "ControlLogix 5580",
    },

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 14,  # Programmable Logic Controller
        "product_code": 55,
        "state": 3,  # Operational
        # revision_major, revision_minor, serial_number merged from firmware/instance
    },

    protocol_quirks={
        "enip_encap_timeout_ms": 10000,
        "cip_connection_timeout_multiplier": 32,
    },
))


_register_template(DeviceTemplate(
    id="rockwell/compactlogix/l33er",
    vendor="Rockwell",
    vendor_family="CompactLogix",
    model="1769-L33ER",
    model_name="CompactLogix 5370",
    device_type="plc",
    description="Mid-range CompactLogix controller with embedded EtherNet/IP",

    oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16"],

    tcp_stack={
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.8,
        "max_ms": 20.0,
        "mean_ms": 5.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{8HEX}",
        station_name_pattern="{model_short}_{role}_{seq}",
        vendor_short="ROC",
        model_short="L33ER",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V34.014",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V33.013",
            release_date=date(2023, 6, 10),
            cves=[],
        ),
        FirmwareVariant(
            version="V30.014",
            release_date=date(2021, 4, 15),
            cves=["CVE-2022-1161"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Rockwell Automation/Allen-Bradley",
        "product_code": "1769-L33ER",
        "vendor_url": "http://www.rockwellautomation.com",
        "product_name": "1769-L33ER CompactLogix Controller",
        "model_name": "CompactLogix 5370",
    },

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 14,
        "product_code": 89,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="rockwell/panelview/plus7-15",
    vendor="Rockwell",
    vendor_family="PanelView",
    model="2711P-T15C22D9P",
    model_name="PanelView Plus 7 - 15 inch",
    device_type="hmi",
    description="15-inch graphic terminal with touchscreen",

    oui_prefixes=["00:00:BC", "00:1D:9C"],

    tcp_stack={
        "ttl": 64,  # VxWorks/Linux based
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 15.0,
        "std_dev_ms": 8.0,
        "distribution": "lognormal",
    },

    supported_protocols=["ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="{10ALPHANUM}",
        station_name_pattern="hmi-{location}-{seq2}",
        vendor_short="ROC",
        model_short="PV7",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V14.00",
            release_date=date(2024, 3, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V12.00",
            release_date=date(2022, 5, 15),
            cves=["CVE-2022-2848"],
        ),
        FirmwareVariant(
            version="V10.00",
            release_date=date(2020, 8, 10),
            cves=["CVE-2022-2848", "CVE-2020-14480"],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 24,  # Human-Machine Interface
        "product_code": 773,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="rockwell/controllogix/l85e",
    vendor="Rockwell",
    vendor_family="ControlLogix",
    model="1756-L85E",
    model_name="ControlLogix 5580",
    device_type="plc",
    description="High-end ControlLogix controller with 80MB memory",

    oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16", "E4:90:69"],

    tcp_stack={
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.4,
        "max_ms": 12.0,
        "mean_ms": 2.8,
        "std_dev_ms": 1.8,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{8HEX}",
        station_name_pattern="{model_short}_{role}_{seq}",
        vendor_short="ROC",
        model_short="L85E",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V35.011",
            release_date=date(2024, 3, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V34.011",
            release_date=date(2023, 8, 15),
            cves=[],
        ),
        FirmwareVariant(
            version="V33.013",
            release_date=date(2022, 11, 20),
            cves=["CVE-2022-3157"],
        ),
        FirmwareVariant(
            version="V32.011",
            release_date=date(2021, 9, 10),
            cves=["CVE-2022-3157", "CVE-2022-1161"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Rockwell Automation/Allen-Bradley",
        "product_code": "1756-L85E/B",
        "vendor_url": "http://www.rockwellautomation.com",
        "product_name": "1756-L85E Logix5580 Controller",
        "model_name": "ControlLogix 5580",
    },

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 14,
        "product_code": 166,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="rockwell/guardlogix/l83es",
    vendor="Rockwell",
    vendor_family="GuardLogix",
    model="1756-L83ES",
    model_name="GuardLogix 5580 Safety",
    device_type="safety_plc",
    description="Safety controller with integrated SIL 3/PLe safety",

    oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16"],

    tcp_stack={
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.2,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "cip_safety"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{8HEX}",
        station_name_pattern="safety_{model_short}_{seq}",
        vendor_short="ROC",
        model_short="L83ES",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V35.011",
            release_date=date(2024, 3, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V34.011",
            release_date=date(2023, 8, 15),
            cves=[],
        ),
        FirmwareVariant(
            version="V33.013",
            release_date=date(2022, 11, 20),
            cves=["CVE-2022-3157"],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 14,
        "product_code": 167,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="rockwell/pointio/1734-aent",
    vendor="Rockwell",
    vendor_family="Point I/O",
    model="1734-AENT",
    model_name="Point I/O EtherNet/IP Adapter",
    device_type="remote_io",
    description="EtherNet/IP adapter for Point I/O modules",

    oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 12.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{8HEX}",
        station_name_pattern="io-point-{seq}",
        vendor_short="ROC",
        model_short="AENT",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V7.013",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V6.013",
            release_date=date(2022, 9, 10),
            cves=["CVE-2022-3156"],
        ),
        FirmwareVariant(
            version="V5.019",
            release_date=date(2020, 7, 20),
            cves=["CVE-2022-3156", "CVE-2020-6084"],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 12,  # Communications Adapter
        "product_code": 164,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="rockwell/flex5000/5094-aen2tr",
    vendor="Rockwell",
    vendor_family="FLEX 5000",
    model="5094-AEN2TR",
    model_name="FLEX 5000 EtherNet/IP Adapter",
    device_type="remote_io",
    description="Dual-port EtherNet/IP adapter for FLEX 5000 I/O",

    oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16", "E4:90:69"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{8HEX}",
        station_name_pattern="io-flex5k-{seq}",
        vendor_short="ROC",
        model_short="FLEX5",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.011",
            release_date=date(2024, 2, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.011",
            release_date=date(2022, 10, 15),
            cves=["CVE-2022-3156"],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 12,
        "product_code": 196,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="rockwell/powerflex/753",
    vendor="Rockwell",
    vendor_family="PowerFlex",
    model="PowerFlex 753",
    model_name="PowerFlex 753 AC Drive",
    device_type="drive",
    description="High-performance AC drive for industrial applications",

    oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 30.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="PF753-{8HEX}",
        station_name_pattern="drive-pf753-{seq}",
        vendor_short="ROC",
        model_short="PF753",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V20.007",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V19.008",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-3158"],
        ),
        FirmwareVariant(
            version="V18.013",
            release_date=date(2021, 3, 10),
            cves=["CVE-2022-3158", "CVE-2021-22682"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Rockwell Automation/Allen-Bradley",
        "product_code": "PowerFlex 753",
        "product_name": "PowerFlex 753 AC Drive",
    },

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 2,  # AC Drive
        "product_code": 753,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="rockwell/panelview/800",
    vendor="Rockwell",
    vendor_family="PanelView",
    model="2711R-T7T",
    model_name="PanelView 800 - 7 inch",
    device_type="hmi",
    description="Compact 7-inch graphic terminal",

    oui_prefixes=["00:00:BC", "00:1D:9C"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 60.0,
        "mean_ms": 18.0,
        "std_dev_ms": 10.0,
        "distribution": "lognormal",
    },

    supported_protocols=["ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="{10ALPHANUM}",
        station_name_pattern="hmi-pv800-{seq2}",
        vendor_short="ROC",
        model_short="PV800",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V10.00",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V8.00",
            release_date=date(2022, 6, 20),
            cves=["CVE-2022-2848"],
        ),
        FirmwareVariant(
            version="V6.00",
            release_date=date(2020, 9, 10),
            cves=["CVE-2022-2848", "CVE-2020-14480"],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 24,
        "product_code": 800,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="rockwell/stratix/5700",
    vendor="Rockwell",
    vendor_family="Stratix",
    model="1783-BMS10CGL",
    model_name="Stratix 5700 Managed Switch",
    device_type="network_switch",
    description="Industrial managed Ethernet switch",

    oui_prefixes=["00:00:BC", "00:1D:9C", "00:1A:2F"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.0,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="STX57-{10ALPHANUM}",
        station_name_pattern="sw-stratix-{seq}",
        vendor_short="ROC",
        model_short="STX57",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V15.2.7",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V15.2.4",
            release_date=date(2022, 7, 20),
            cves=["CVE-2022-20812"],
        ),
        FirmwareVariant(
            version="V15.0.1",
            release_date=date(2020, 11, 15),
            cves=["CVE-2022-20812", "CVE-2020-3566"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Rockwell Automation Stratix 5700 Managed Switch",
        "sys_object_id": "1.3.6.1.4.1.9.1.2505",
    },

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 12,
        "product_code": 5700,
        "state": 3,
    },
))


# ControlLogix 5570 (L73)
_register_template(DeviceTemplate(
    id="rockwell/controllogix/l73",
    vendor="Rockwell",
    vendor_family="ControlLogix",
    model="1756-L73",
    model_name="ControlLogix 5570",
    device_type="plc",
    description="Mid-range ControlLogix controller for complex applications",

    oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16", "E4:90:69"],

    tcp_stack={
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.8,
        "max_ms": 20.0,
        "mean_ms": 5.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{8HEX}",
        station_name_pattern="{model_short}_{role}_{seq}",
        vendor_short="ROC",
        model_short="L73",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V33.011",
            release_date=date(2023, 10, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V32.011",
            release_date=date(2022, 11, 20),
            cves=["CVE-2022-3157"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Rockwell Automation/Allen-Bradley",
        "product_code": "1756-L73",
        "vendor_url": "http://www.rockwellautomation.com",
        "product_name": "1756-L73 ControlLogix Controller",
        "model_name": "ControlLogix 5570",
    },

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 14,
        "product_code": 73,
        "state": 3,
    },
))


# CompactGuardLogix 5370 Safety PLC
_register_template(DeviceTemplate(
    id="rockwell/compactlogix/l33erms",
    vendor="Rockwell",
    vendor_family="CompactLogix",
    model="1769-L33ERMS",
    model_name="CompactGuardLogix 5370",
    device_type="safety_plc",
    description="Safety-rated CompactLogix controller for SIL2/PLd applications",

    oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16"],

    tcp_stack={
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.5,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "cip_safety", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{8HEX}",
        station_name_pattern="{model_short}_{role}_{seq}",
        vendor_short="ROC",
        model_short="L33ERMS",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V33.013",
            release_date=date(2023, 8, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Rockwell Automation/Allen-Bradley",
        "product_code": "1769-L33ERMS",
        "product_name": "1769-L33ERMS CompactGuardLogix Controller",
        "model_name": "CompactGuardLogix 5370",
    },

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 14,
        "product_code": 133,
        "state": 3,
    },
))


# PanelView Plus 7 - 10 inch
_register_template(DeviceTemplate(
    id="rockwell/panelview/plus7-10",
    vendor="Rockwell",
    vendor_family="PanelView",
    model="2711P-T10C22D9P",
    model_name="PanelView Plus 7 - 10 inch",
    device_type="hmi",
    description="10-inch color touchscreen operator interface",

    oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 80.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="PV{8HEX}",
        station_name_pattern="hmi-pv7-{seq}",
        vendor_short="ROC",
        model_short="PV7-10",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V13.0",
            release_date=date(2023, 9, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 24,
        "product_code": 2711,
        "state": 3,
    },
))


# PanelView 800
_register_template(DeviceTemplate(
    id="rockwell/panelview/800",
    vendor="Rockwell",
    vendor_family="PanelView",
    model="2711R-T7T",
    model_name="PanelView 800",
    device_type="hmi",
    description="7-inch color touchscreen HMI for Micro800 systems",

    oui_prefixes=["00:00:BC", "00:1D:9C", "5C:88:16"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="PV8{8HEX}",
        station_name_pattern="hmi-pv800-{seq}",
        vendor_short="ROC",
        model_short="PV800",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V8.0",
            release_date=date(2023, 6, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 24,
        "product_code": 800,
        "state": 3,
    },
))


# PowerFlex 525 Drive
_register_template(DeviceTemplate(
    id="rockwell/drives/powerflex-525",
    vendor="Rockwell",
    vendor_family="PowerFlex",
    model="25B-D030N104",
    model_name="PowerFlex 525",
    device_type="drive",
    description="Compact AC drive for simple stand-alone applications",

    oui_prefixes=["00:00:BC", "00:1D:9C"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 12.0,
        "std_dev_ms": 8.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="PF5{8HEX}",
        station_name_pattern="drive-pf525-{seq}",
        vendor_short="ROC",
        model_short="PF525",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.003",
            release_date=date(2023, 4, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Rockwell Automation/Allen-Bradley",
        "product_code": "25B-D030N104",
        "product_name": "PowerFlex 525 AC Drive",
        "model_name": "PowerFlex 525",
    },

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 2,
        "product_code": 525,
        "state": 3,
    },
))


# PowerFlex 753 Drive
_register_template(DeviceTemplate(
    id="rockwell/drives/powerflex-753",
    vendor="Rockwell",
    vendor_family="PowerFlex",
    model="20F-D052N103",
    model_name="PowerFlex 753",
    device_type="drive",
    description="High-performance AC drive for demanding applications",

    oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 30.0,
        "mean_ms": 6.0,
        "std_dev_ms": 4.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="PF7{8HEX}",
        station_name_pattern="drive-pf753-{seq}",
        vendor_short="ROC",
        model_short="PF753",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V20.003",
            release_date=date(2023, 7, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 2,
        "product_code": 753,
        "state": 3,
    },
))


# Kinetix 5500 Servo Drive
_register_template(DeviceTemplate(
    id="rockwell/servo/kinetix-5500",
    vendor="Rockwell",
    vendor_family="Kinetix",
    model="2198-D012-ERS3",
    model_name="Kinetix 5500",
    device_type="servo",
    description="Integrated servo drive for motion control applications",

    oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95"],

    tcp_stack={
        "ttl": 64,
        "window_size": 29200,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.25,
        "max_ms": 5.0,
        "mean_ms": 1.0,
        "std_dev_ms": 0.5,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "cip_motion"],

    instance_rules=InstanceGenerationRules(
        serial_format="K55{8HEX}",
        station_name_pattern="servo-k5500-{seq}",
        vendor_short="ROC",
        model_short="K5500",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V12.001",
            release_date=date(2023, 5, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 3,
        "product_code": 5500,
        "state": 3,
    },
))


# FLEX 5000 EtherNet/IP Adapter
_register_template(DeviceTemplate(
    id="rockwell/io/flex5000-aen2tr",
    vendor="Rockwell",
    vendor_family="FLEX 5000",
    model="5094-AEN2TR",
    model_name="FLEX 5000 EtherNet/IP",
    device_type="io_module",
    description="Dual-port EtherNet/IP adapter for FLEX 5000 I/O",

    oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.25,
        "max_ms": 5.0,
        "mean_ms": 1.0,
        "std_dev_ms": 0.5,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="FX5{8HEX}",
        station_name_pattern="rio-flex5000-{seq}",
        vendor_short="ROC",
        model_short="FX5000",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.011",
            release_date=date(2023, 8, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 7,
        "product_code": 5094,
        "state": 3,
    },
))


# 1734-AENT Point I/O Adapter
_register_template(DeviceTemplate(
    id="rockwell/io/1734-aent",
    vendor="Rockwell",
    vendor_family="POINT I/O",
    model="1734-AENT",
    model_name="POINT I/O EtherNet/IP",
    device_type="io_module",
    description="EtherNet/IP adapter for POINT I/O distributed I/O",

    oui_prefixes=["00:00:BC", "00:1D:9C"],

    tcp_stack={
        "ttl": 64,
        "window_size": 8192,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="PI{8HEX}",
        station_name_pattern="rio-point-{seq}",
        vendor_short="ROC",
        model_short="1734",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V7.003",
            release_date=date(2023, 3, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 7,
        "product_code": 1734,
        "state": 3,
    },
))


# 1756-L85E ControlLogix 5580
_register_template(DeviceTemplate(
    id="rockwell/controllogix/l85e",
    vendor="Rockwell",
    vendor_family="ControlLogix",
    model="1756-L85E",
    model_name="ControlLogix 5580",
    device_type="plc",
    description="High-performance ControlLogix controller with 80MB memory",

    oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16", "E4:90:69"],

    tcp_stack={
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 12.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{8HEX}",
        station_name_pattern="{model_short}_{role}_{seq}",
        vendor_short="ROC",
        model_short="L85E",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V35.011",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V34.011",
            release_date=date(2023, 6, 1),
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Rockwell Automation/Allen-Bradley",
        "product_code": "1756-L85E",
        "product_name": "1756-L85E LOGIX5585E",
        "model_name": "ControlLogix 5580",
    },

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 14,
        "product_code": 85,
        "state": 3,
    },
))


# 1756-L83ES GuardLogix 5580S Safety PLC
_register_template(DeviceTemplate(
    id="rockwell/guardlogix/l83es",
    vendor="Rockwell",
    vendor_family="GuardLogix",
    model="1756-L83ES",
    model_name="GuardLogix 5580S",
    device_type="safety_plc",
    description="Safety-rated ControlLogix controller for SIL3/PLe applications",

    oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16"],

    tcp_stack={
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 12.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "cip_safety", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{8HEX}",
        station_name_pattern="{model_short}_{role}_{seq}",
        vendor_short="ROC",
        model_short="L83ES",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V35.011",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 14,
        "product_code": 183,
        "state": 3,
    },
))


# MicroLogix 1400 Legacy PLC
_register_template(DeviceTemplate(
    id="rockwell/micrologix/1766-l32bwa",
    vendor="Rockwell",
    vendor_family="MicroLogix",
    model="1766-L32BWA",
    model_name="MicroLogix 1400",
    device_type="plc",
    description="Legacy MicroLogix 1400 PLC with built-in Ethernet",

    oui_prefixes=["00:00:BC", "00:1D:9C"],

    tcp_stack={
        "ttl": 128,
        "window_size": 8192,
        "mss": 1460,
        "timestamps_enabled": False,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 10.0,
        "max_ms": 150.0,
        "mean_ms": 45.0,
        "std_dev_ms": 25.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{6HEX}",
        station_name_pattern="ml1400_{role}_{seq}",
        vendor_short="ROC",
        model_short="ML1400",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="21.003",
            release_date=date(2020, 8, 1),
            is_latest=True,
            is_default=True,
            cves=["CVE-2020-6088"],
            notes="Legacy product with limited updates",
        ),
        FirmwareVariant(
            version="16.002",
            release_date=date(2016, 3, 15),
            cves=["CVE-2020-6088", "CVE-2017-7924"],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 14,
        "product_code": 155,
        "state": 3,
    },

    modbus_identity={
        "vendor_name": "Rockwell Automation",
        "product_code": "1766-L32BWA",
        "vendor_url": "http://www.rockwellautomation.com",
        "product_name": "MicroLogix 1400",
        "model_name": "MicroLogix",
    },
))


# CompactLogix 5370 L24ER Small Controller
_register_template(DeviceTemplate(
    id="rockwell/compactlogix/1769-l24er-qb1b",
    vendor="Rockwell",
    vendor_family="CompactLogix",
    model="1769-L24ER-QB1B",
    model_name="CompactLogix 5370 L24ER",
    device_type="plc",
    description="Compact controller for small to medium applications",

    oui_prefixes=["00:00:BC", "00:1D:9C", "08:61:95"],

    tcp_stack={
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 25.0,
        "mean_ms": 6.0,
        "std_dev_ms": 3.5,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="0x{8HEX}",
        station_name_pattern="{model_short}_{role}_{seq}",
        vendor_short="ROC",
        model_short="L24ER",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V33.011",
            release_date=date(2023, 9, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V32.011",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-3166"],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 14,
        "product_code": 89,
        "state": 3,
    },

    modbus_identity={
        "vendor_name": "Rockwell Automation",
        "product_code": "1769-L24ER-QB1B",
        "vendor_url": "http://www.rockwellautomation.com",
        "product_name": "CompactLogix 5370 L24ER",
        "model_name": "CompactLogix",
    },
))


# -----------------------------------------------------------------------------
# SCHNEIDER ELECTRIC TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="schneider/modicon-m580/bmep584040",
    vendor="Schneider",
    vendor_family="Modicon M580",
    model="BMEP584040",
    model_name="M580 ePAC CPU",
    device_type="plc",
    description="High-performance Ethernet programmable automation controller",

    oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3", "64:3A:EA"],

    tcp_stack={
        "ttl": 64,  # VxWorks
        "window_size": 32768,
        "mss": 1460,
        "window_scaling": None,
        "sack_permitted": True,
        "timestamps_enabled": False,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 20.0,
        "mean_ms": 4.0,
        "std_dev_ms": 2.5,
        "distribution": "gaussian",
        "outlier_probability": 0.008,
        "outlier_multiplier": 3.5,
    },

    error_behavior={
        "supported_exception_codes": [1, 2, 3, 4, 5, 6, 10, 11],
        "exception_probability": 0.0006,
    },

    supported_protocols=["modbus_tcp", "ethernet_ip", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="BMEP{8NUM}",
        station_name_pattern="{role}-m580-{seq}",
        vendor_short="SCH",
        model_short="M580",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.10",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.60",
            release_date=date(2023, 5, 20),
            cves=[],
        ),
        FirmwareVariant(
            version="V3.20",
            release_date=date(2022, 4, 10),
            cves=["CVE-2022-45788"],
            notes="Vulnerable to authentication bypass",
        ),
        FirmwareVariant(
            version="V2.80",
            release_date=date(2020, 11, 5),
            cves=["CVE-2022-45788", "CVE-2021-22779", "CVE-2020-7561"],
            notes="Multiple critical vulnerabilities",
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "BMEP584040",
        "vendor_url": "http://www.schneider-electric.com",
        "product_name": "Modicon M580 ePAC",
        "model_name": "BMEP584040",
    },

    ethernet_ip_identity={
        "vendor_id": 67,
        "device_type": 14,
        "product_code": 584,
        "state": 3,
    },

    protocol_quirks={
        "modbus_max_registers": 125,
        "modbus_max_coils": 2000,
    },
))


_register_template(DeviceTemplate(
    id="schneider/modicon-m241/tm241ce40r",
    vendor="Schneider",
    vendor_family="Modicon M241",
    model="TM241CE40R",
    model_name="M241 Logic Controller",
    device_type="plc",
    description="Compact logic controller with Ethernet and CANopen",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 1.5,
        "max_ms": 35.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="TM24{8NUM}",
        station_name_pattern="{role}-m241-{seq}",
        vendor_short="SCH",
        model_short="M241",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.2.6",
            release_date=date(2024, 1, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.1.0",
            release_date=date(2022, 9, 15),
            cves=["CVE-2022-45788"],
        ),
        FirmwareVariant(
            version="V4.0.5",
            release_date=date(2020, 6, 20),
            cves=["CVE-2022-45788", "CVE-2020-7559"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "TM241CE40R",
        "product_name": "Modicon M241 Logic Controller",
        "model_name": "TM241CE40R",
    },
))


_register_template(DeviceTemplate(
    id="schneider/altivar/atv630",
    vendor="Schneider",
    vendor_family="Altivar Process",
    model="ATV630D15N4",
    model_name="Altivar Process ATV630",
    device_type="drive",
    description="Variable frequency drive for process applications with advanced connectivity",

    oui_prefixes=["00:00:54", "00:80:F4", "EC:FA:AA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 12.0,
        "std_dev_ms": 8.0,
        "distribution": "gaussian",
    },

    error_behavior={
        "supported_exception_codes": [1, 2, 3, 4],
        "exception_probability": 0.001,
        "timeout_probability": 0.0005,
    },

    supported_protocols=["modbus_tcp", "ethernet_ip", "profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="ATV{10NUM}",
        station_name_pattern="{role}-atv630-{seq}",
        vendor_short="SCH",
        model_short="ATV6",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V1.7IE61",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
            notes="Latest firmware with security patches",
        ),
        FirmwareVariant(
            version="V1.6IE42",
            release_date=date(2022, 7, 15),
            cves=["CVE-2022-22804"],
            notes="Vulnerable to improper input validation",
        ),
        FirmwareVariant(
            version="V1.5IE35",
            release_date=date(2021, 3, 10),
            cves=["CVE-2022-22804", "CVE-2020-7571"],
            notes="Multiple vulnerabilities - upgrade recommended",
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "ATV630D15N4",
        "vendor_url": "http://www.schneider-electric.com",
        "product_name": "Altivar Process ATV630",
        "model_name": "ATV630D15N4",
    },

    ethernet_ip_identity={
        "vendor_id": 67,
        "device_type": 2,  # AC Drive
        "product_code": 630,
        "state": 3,
    },

    profinet_identity={
        "vendor_id": 0x0095,
        "device_id": 0x0630,
        "device_role": 1,  # Device
        "im0_manufacturer": "Schneider Electric",
        "im0_order_id": "ATV630D15N4",
    },
))


_register_template(DeviceTemplate(
    id="schneider/modicon-m580/bmep582040",
    vendor="Schneider",
    vendor_family="Modicon M580",
    model="BMEP582040",
    model_name="M580 ePAC CPU",
    device_type="plc",
    description="Entry-level M580 ePAC with 2MB program memory",

    oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3", "64:3A:EA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "window_scaling": None,
        "sack_permitted": True,
        "timestamps_enabled": False,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.8,
        "max_ms": 25.0,
        "mean_ms": 5.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "ethernet_ip", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="BMEP{8NUM}",
        station_name_pattern="{role}-m580-{seq}",
        vendor_short="SCH",
        model_short="M580",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.10",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.20",
            release_date=date(2022, 4, 10),
            cves=["CVE-2022-45788"],
        ),
        FirmwareVariant(
            version="V2.80",
            release_date=date(2020, 11, 5),
            cves=["CVE-2022-45788", "CVE-2021-22779"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "BMEP582040",
        "vendor_url": "http://www.schneider-electric.com",
        "product_name": "Modicon M580 ePAC",
        "model_name": "BMEP582040",
    },

    ethernet_ip_identity={
        "vendor_id": 67,
        "device_type": 14,
        "product_code": 582,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="schneider/modicon-m340/bmxp3420302",
    vendor="Schneider",
    vendor_family="Modicon M340",
    model="BMXP3420302",
    model_name="M340 Processor",
    device_type="plc",
    description="Mid-range Modicon M340 processor with Ethernet",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 40.0,
        "mean_ms": 10.0,
        "std_dev_ms": 6.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="BMX{8NUM}",
        station_name_pattern="{role}-m340-{seq}",
        vendor_short="SCH",
        model_short="M340",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.40",
            release_date=date(2024, 1, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.10",
            release_date=date(2022, 5, 15),
            cves=["CVE-2022-45788"],
        ),
        FirmwareVariant(
            version="V2.90",
            release_date=date(2020, 8, 20),
            cves=["CVE-2022-45788", "CVE-2020-7537"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "BMXP3420302",
        "vendor_url": "http://www.schneider-electric.com",
        "product_name": "Modicon M340 Processor",
        "model_name": "BMXP3420302",
    },

    ethernet_ip_identity={
        "vendor_id": 67,
        "device_type": 14,
        "product_code": 342,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="schneider/modicon-m251/tm251mese",
    vendor="Schneider",
    vendor_family="Modicon M251",
    model="TM251MESE",
    model_name="M251 Logic Controller",
    device_type="plc",
    description="Compact logic controller with Ethernet and serial ports",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 1.5,
        "max_ms": 30.0,
        "mean_ms": 7.0,
        "std_dev_ms": 4.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="TM25{8NUM}",
        station_name_pattern="{role}-m251-{seq}",
        vendor_short="SCH",
        model_short="M251",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.2.6",
            release_date=date(2024, 1, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.0.0",
            release_date=date(2022, 6, 20),
            cves=["CVE-2022-45788"],
        ),
        FirmwareVariant(
            version="V4.0.7",
            release_date=date(2020, 4, 15),
            cves=["CVE-2022-45788", "CVE-2020-7559"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "TM251MESE",
        "product_name": "Modicon M251 Logic Controller",
        "model_name": "TM251MESE",
    },
))


_register_template(DeviceTemplate(
    id="schneider/modicon-m262/tm262l20mese8t",
    vendor="Schneider",
    vendor_family="Modicon M262",
    model="TM262L20MESE8T",
    model_name="M262 Motion Controller",
    device_type="motion_controller",
    description="Motion controller with 8 axis support and EtherNet/IP",

    oui_prefixes=["00:00:54", "00:80:F4", "64:3A:EA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.0,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "ethernet_ip", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="TM26{8NUM}",
        station_name_pattern="{role}-m262-{seq}",
        vendor_short="SCH",
        model_short="M262",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V1.5.0",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V1.3.0",
            release_date=date(2022, 9, 15),
            cves=["CVE-2022-45788"],
        ),
        FirmwareVariant(
            version="V1.1.0",
            release_date=date(2021, 5, 10),
            cves=["CVE-2022-45788", "CVE-2021-22779"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "TM262L20MESE8T",
        "vendor_url": "http://www.schneider-electric.com",
        "product_name": "Modicon M262 Motion Controller",
        "model_name": "TM262L20MESE8T",
    },

    ethernet_ip_identity={
        "vendor_id": 67,
        "device_type": 43,  # Motion Controller
        "product_code": 262,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="schneider/altivar/atv930",
    vendor="Schneider",
    vendor_family="Altivar Process",
    model="ATV930D15N4",
    model_name="Altivar Process ATV930",
    device_type="drive",
    description="High-performance variable frequency drive with advanced process functions",

    oui_prefixes=["00:00:54", "00:80:F4", "EC:FA:AA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 1.5,
        "max_ms": 40.0,
        "mean_ms": 10.0,
        "std_dev_ms": 6.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "ethernet_ip", "profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="ATV9{10NUM}",
        station_name_pattern="{role}-atv930-{seq}",
        vendor_short="SCH",
        model_short="ATV9",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.6IE50",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.3IE30",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-22804"],
        ),
        FirmwareVariant(
            version="V3.1IE20",
            release_date=date(2021, 4, 10),
            cves=["CVE-2022-22804", "CVE-2020-7571"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "ATV930D15N4",
        "vendor_url": "http://www.schneider-electric.com",
        "product_name": "Altivar Process ATV930",
        "model_name": "ATV930D15N4",
    },

    ethernet_ip_identity={
        "vendor_id": 67,
        "device_type": 2,  # AC Drive
        "product_code": 930,
        "state": 3,
    },

    profinet_identity={
        "vendor_id": 0x0095,
        "device_id": 0x0930,
        "device_role": 1,
        "im0_manufacturer": "Schneider Electric",
        "im0_order_id": "ATV930D15N4",
    },
))


_register_template(DeviceTemplate(
    id="schneider/altivar/atv320",
    vendor="Schneider",
    vendor_family="Altivar Machine",
    model="ATV320U22N4C",
    model_name="Altivar Machine ATV320",
    device_type="drive",
    description="Compact variable frequency drive for OEM machine builders",

    oui_prefixes=["00:00:54", "00:80:F4", "EC:FA:AA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 8192,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 15.0,
        "std_dev_ms": 10.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="ATV3{10NUM}",
        station_name_pattern="{role}-atv320-{seq}",
        vendor_short="SCH",
        model_short="ATV3",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V1.8IE22",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V1.6IE18",
            release_date=date(2022, 5, 20),
            cves=["CVE-2022-22804"],
        ),
        FirmwareVariant(
            version="V1.4IE12",
            release_date=date(2020, 10, 10),
            cves=["CVE-2022-22804", "CVE-2020-7571"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "ATV320U22N4C",
        "vendor_url": "http://www.schneider-electric.com",
        "product_name": "Altivar Machine ATV320",
        "model_name": "ATV320U22N4C",
    },
))


_register_template(DeviceTemplate(
    id="schneider/advantys/stbnip2311",
    vendor="Schneider",
    vendor_family="Advantys STB",
    model="STBNIP2311",
    model_name="STB EtherNet/IP Adapter",
    device_type="remote_io",
    description="Advantys STB distributed I/O network interface module",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 8192,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 20.0,
        "mean_ms": 4.0,
        "std_dev_ms": 2.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="STB{8NUM}",
        station_name_pattern="io-stb-{seq}",
        vendor_short="SCH",
        model_short="STB",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.20",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.80",
            release_date=date(2022, 3, 10),
            cves=["CVE-2021-22787"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "STBNIP2311",
        "product_name": "Advantys STB EtherNet/IP Adapter",
        "model_name": "STBNIP2311",
    },

    ethernet_ip_identity={
        "vendor_id": 67,
        "device_type": 7,  # General Purpose I/O
        "product_code": 231,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="schneider/tm3/tm3di32k",
    vendor="Schneider",
    vendor_family="TM3 I/O",
    model="TM3DI32K",
    model_name="TM3 32-Input Module",
    device_type="io_module",
    description="32-point digital input expansion module",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 8192,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="TM3{8NUM}",
        station_name_pattern="io-tm3-{seq}",
        vendor_short="SCH",
        model_short="TM3",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.1",
            release_date=date(2023, 6, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V1.8",
            release_date=date(2021, 9, 10),
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "TM3DI32K",
        "product_name": "TM3 32-Input Module",
        "model_name": "TM3DI32K",
    },
))


_register_template(DeviceTemplate(
    id="schneider/connexium/tcsesm083f2cu0",
    vendor="Schneider",
    vendor_family="ConneXium",
    model="TCSESM083F2CU0",
    model_name="ConneXium Managed Switch",
    device_type="network_switch",
    description="8-port managed Ethernet switch for industrial applications",

    oui_prefixes=["00:00:54", "00:80:F4", "00:60:5C"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.0,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="TCE{10ALPHANUM}",
        station_name_pattern="sw-cnx-{seq}",
        vendor_short="SCH",
        model_short="CNX",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V8.5",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V8.1",
            release_date=date(2022, 6, 20),
            cves=["CVE-2022-30234"],
        ),
        FirmwareVariant(
            version="V7.8",
            release_date=date(2021, 1, 15),
            cves=["CVE-2022-30234", "CVE-2020-28212"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Schneider Electric ConneXium Managed Switch",
        "sys_object_id": "1.3.6.1.4.1.3833.1.100.1",
    },

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "TCSESM083F2CU0",
        "product_name": "ConneXium Managed Switch",
        "model_name": "TCSESM083F2CU0",
    },
))


_register_template(DeviceTemplate(
    id="schneider/magelis/hmistm6",
    vendor="Schneider",
    vendor_family="Magelis STM",
    model="HMISTM6",
    model_name="Magelis STM6 HMI",
    device_type="hmi",
    description="Compact 3.4-inch color touchscreen HMI panel",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="HMI{8NUM}",
        station_name_pattern="hmi-stm-{seq}",
        vendor_short="SCH",
        model_short="STM6",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.5.2",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.3.0",
            release_date=date(2022, 5, 10),
            cves=["CVE-2022-0221"],
        ),
        FirmwareVariant(
            version="V3.1.0",
            release_date=date(2020, 11, 15),
            cves=["CVE-2022-0221", "CVE-2020-7570"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "HMISTM6",
        "product_name": "Magelis STM6 HMI",
        "model_name": "HMISTM6",
    },
))


_register_template(DeviceTemplate(
    id="schneider/modicon-premium/tsxp57204m",
    vendor="Schneider",
    vendor_family="Modicon Premium",
    model="TSXP57204M",
    model_name="Premium CPU",
    device_type="plc",
    description="Legacy Modicon Premium processor - still widely deployed",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 60.0,
        "mean_ms": 15.0,
        "std_dev_ms": 10.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="TSX{8NUM}",
        station_name_pattern="{role}-premium-{seq}",
        vendor_short="SCH",
        model_short="P57",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.3",
            release_date=date(2020, 6, 15),
            is_latest=True,
            is_default=True,
            cves=[],
            notes="Final firmware release for legacy platform",
        ),
        FirmwareVariant(
            version="V5.0",
            release_date=date(2018, 3, 10),
            cves=["CVE-2019-6857"],
        ),
        FirmwareVariant(
            version="V4.6",
            release_date=date(2015, 11, 20),
            cves=["CVE-2019-6857", "CVE-2017-7579"],
            notes="Legacy firmware - upgrade strongly recommended",
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "TSXP57204M",
        "vendor_url": "http://www.schneider-electric.com",
        "product_name": "Modicon Premium CPU",
        "model_name": "TSXP57204M",
    },
))


_register_template(DeviceTemplate(
    id="schneider/tm5-safety/tm5cslc100fs",
    vendor="Schneider",
    vendor_family="TM5 Safety",
    model="TM5CSLC100FS",
    model_name="TM5 Safety Logic Controller",
    device_type="safety_plc",
    description="Safety logic controller for machine safety applications (SIL 3/PLe)",

    oui_prefixes=["00:00:54", "00:80:F4", "64:3A:EA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 12.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="TM5S{8NUM}",
        station_name_pattern="safety-tm5-{seq}",
        vendor_short="SCH",
        model_short="TM5S",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V1.4.0",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V1.2.0",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-45788"],
        ),
        FirmwareVariant(
            version="V1.0.0",
            release_date=date(2021, 3, 10),
            cves=["CVE-2022-45788", "CVE-2021-22779"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "TM5CSLC100FS",
        "vendor_url": "http://www.schneider-electric.com",
        "product_name": "TM5 Safety Logic Controller",
        "model_name": "TM5CSLC100FS",
    },
))


# PowerLogic PM8000 Power Meter
_register_template(DeviceTemplate(
    id="schneider/power/pm8000",
    vendor="Schneider",
    vendor_family="PowerLogic",
    model="PM8000",
    model_name="PowerLogic PM8000",
    device_type="power_meter",
    description="Advanced power quality and energy meter with communications",

    oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3", "64:3A:EA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 12.0,
        "std_dev_ms": 8.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "bacnet", "snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="PM8{8NUM}",
        station_name_pattern="meter-pm8000-{seq}",
        vendor_short="SCH",
        model_short="PM8000",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.0.0",
            release_date=date(2023, 8, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "PM8000",
        "vendor_url": "http://www.schneider-electric.com",
        "product_name": "PowerLogic PM8000 Power Meter",
        "model_name": "PM8000",
    },

    snmp_identity={
        "sys_descr": "Schneider Electric PowerLogic PM8000 Power Quality Meter",
        "sys_object_id": "1.3.6.1.4.1.3833.1.100.8000",
    },

    bacnet_identity={
        "vendor_id": 67,
        "model_name": "PM8000",
        "device_instance": 0,
    },
))


# M580 High-Performance ePAC
_register_template(DeviceTemplate(
    id="schneider/modicon-m580/bmeh586040",
    vendor="Schneider",
    vendor_family="Modicon M580",
    model="BMEH586040",
    model_name="M580 High-Performance ePAC",
    device_type="plc",
    description="High-performance Ethernet programmable automation controller with redundancy",

    oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3", "64:3A:EA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.4,
        "max_ms": 15.0,
        "mean_ms": 3.0,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "ethernet_ip", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="BMEH{8NUM}",
        station_name_pattern="{role}-m580h-{seq}",
        vendor_short="SCH",
        model_short="M580H",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.10",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "BMEH586040",
        "product_name": "Modicon M580 ePAC",
        "model_name": "BMEH586040",
    },

    ethernet_ip_identity={
        "vendor_id": 67,
        "device_type": 14,
        "product_code": 586,
        "state": 3,
    },
))


# M340 Processor
_register_template(DeviceTemplate(
    id="schneider/modicon-m340/bmxp342020",
    vendor="Schneider",
    vendor_family="Modicon M340",
    model="BMXP342020",
    model_name="M340 Processor",
    device_type="plc",
    description="Mid-range automation processor with embedded Ethernet",

    oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 30.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="BMX{8NUM}",
        station_name_pattern="{role}-m340-{seq}",
        vendor_short="SCH",
        model_short="M340",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.60",
            release_date=date(2023, 5, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "BMXP342020",
        "product_name": "Modicon M340 Processor",
        "model_name": "M340",
    },
))


# M580 Safety ePAC
_register_template(DeviceTemplate(
    id="schneider/modicon-m580/bmep586040s",
    vendor="Schneider",
    vendor_family="Modicon M580",
    model="BMEP586040S",
    model_name="M580 Safety ePAC",
    device_type="safety_plc",
    description="Safety-rated Ethernet programmable automation controller for SIL3 applications",

    oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3", "64:3A:EA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 18.0,
        "mean_ms": 4.0,
        "std_dev_ms": 2.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "ethernet_ip", "profisafe"],

    instance_rules=InstanceGenerationRules(
        serial_format="BMEPS{8NUM}",
        station_name_pattern="{role}-m580s-{seq}",
        vendor_short="SCH",
        model_short="M580S",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.10",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "BMEP586040S",
        "product_name": "Modicon M580 Safety ePAC",
        "model_name": "M580S",
    },
))


# Schneider Lexium 32 Servo Drive
_register_template(DeviceTemplate(
    id="schneider/lexium32/lxm32md18n4",
    vendor="Schneider",
    vendor_family="Lexium 32",
    model="LXM32MD18N4",
    model_name="Lexium 32 Servo Drive",
    device_type="servo",
    description="Motion servo drive for automation applications",

    oui_prefixes=["00:00:54", "00:80:F4", "00:04:A3"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 20.0,
        "mean_ms": 5.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="LXM{8NUM}",
        station_name_pattern="{role}-lxm32-{seq}",
        vendor_short="SCH",
        model_short="LXM32",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.60",
            release_date=date(2023, 4, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "LXM32MD18N4",
        "product_name": "Lexium 32 Servo Drive",
        "model_name": "Lexium 32",
    },
))


# Schneider Premium Legacy PLC
_register_template(DeviceTemplate(
    id="schneider/premium/tsxp57154m",
    vendor="Schneider",
    vendor_family="Premium",
    model="TSXP57154M",
    model_name="Premium TSXP57154M",
    device_type="plc",
    description="Legacy Premium PLC with Ethernet communication",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 80.0,
        "mean_ms": 25.0,
        "std_dev_ms": 12.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="TSX{8NUM}",
        station_name_pattern="{role}-premium-{seq}",
        vendor_short="SCH",
        model_short="TSXP",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.0",
            release_date=date(2018, 6, 1),
            is_latest=True,
            is_default=True,
            cves=["CVE-2019-6857", "CVE-2018-7821"],
            notes="Legacy product with limited security updates",
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "TSXP57154M",
        "product_name": "Premium PLC",
        "model_name": "Premium",
    },
))


# Schneider Advantys STB Remote I/O
_register_template(DeviceTemplate(
    id="schneider/advantys/stb-nip-2311",
    vendor="Schneider",
    vendor_family="Advantys STB",
    model="STB NIP 2311",
    model_name="Advantys STB Network Interface",
    device_type="io_module",
    description="Advantys STB distributed I/O network interface module",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 8192,
        "mss": 1460,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 30.0,
        "mean_ms": 8.0,
        "std_dev_ms": 4.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="STB{6NUM}",
        station_name_pattern="rio-stb-{seq}",
        vendor_short="SCH",
        model_short="STB",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.50",
            release_date=date(2020, 3, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "STB NIP 2311",
        "product_name": "Advantys STB Network Interface",
        "model_name": "Advantys STB",
    },
))


# Schneider InRow DX Precision Cooling
_register_template(DeviceTemplate(
    id="schneider/inrow/dx",
    vendor="Schneider",
    vendor_family="InRow",
    model="InRow DX",
    model_name="InRow DX Precision Cooling",
    device_type="crac_unit",
    description="InRow precision cooling for data centers",

    oui_prefixes=["00:00:54", "00:C0:B7", "64:3A:EA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 30.0,
        "std_dev_ms": 15.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="INROW{8ALPHANUM}",
        station_name_pattern="crac-{location}-{seq}",
        vendor_short="SCH",
        model_short="INROW",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V7.0.2",
            release_date=date(2023, 9, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "Schneider Electric InRow DX Precision Cooling",
        "sys_object_id": "1.3.6.1.4.1.318.1.3.14.5",
    },

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "InRow DX",
        "product_name": "InRow DX Precision Cooling",
        "model_name": "InRow",
    },
))


# Schneider Galaxy VM UPS
_register_template(DeviceTemplate(
    id="schneider/galaxy/vm",
    vendor="Schneider",
    vendor_family="Galaxy",
    model="Galaxy VM",
    model_name="Galaxy VM UPS",
    device_type="ups",
    description="Three-phase modular UPS for data centers",

    oui_prefixes=["00:00:54", "00:C0:B7", "64:3A:EA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 80.0,
        "mean_ms": 25.0,
        "std_dev_ms": 12.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="UPS{8ALPHANUM}",
        station_name_pattern="ups-{location}-{seq}",
        vendor_short="SCH",
        model_short="GVM",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.5.0",
            release_date=date(2023, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.3.0",
            release_date=date(2022, 3, 15),
            cves=["CVE-2022-22805"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Schneider Electric Galaxy VM UPS",
        "sys_object_id": "1.3.6.1.4.1.318.1.3.27",
    },

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "Galaxy VM",
        "product_name": "Galaxy VM UPS",
        "model_name": "Galaxy",
    },
))


# Schneider Switched Rack PDU
_register_template(DeviceTemplate(
    id="schneider/rack-pdu/switched",
    vendor="Schneider",
    vendor_family="Rack PDU",
    model="Rack PDU",
    model_name="Switched Rack PDU",
    device_type="pdu",
    description="Switched metered rack power distribution unit",

    oui_prefixes=["00:00:54", "00:C0:B7", "64:3A:EA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 10.0,
        "max_ms": 150.0,
        "mean_ms": 40.0,
        "std_dev_ms": 20.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="PDU{6ALPHANUM}",
        station_name_pattern="pdu-{location}-{seq}",
        vendor_short="SCH",
        model_short="PDU",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.9.6",
            release_date=date(2023, 8, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V6.8.4",
            release_date=date(2022, 5, 15),
            cves=["CVE-2022-0715"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Schneider Electric Switched Rack PDU",
        "sys_object_id": "1.3.6.1.4.1.318.1.3.4.5",
    },

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "Rack PDU",
        "product_name": "Switched Rack PDU",
        "model_name": "Rack PDU",
    },
))


# -----------------------------------------------------------------------------
# OMRON TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="omron/nj/nj501-1300",
    vendor="Omron",
    vendor_family="NJ Series",
    model="NJ501-1300",
    model_name="NJ501 Machine Controller",
    device_type="plc",
    description="Machine automation controller with EtherCAT and EtherNet/IP",

    oui_prefixes=["00:00:74", "00:04:C7", "00:0C:DB"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.0,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "fins", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="NJ{2ALPHA}{8NUM}",
        station_name_pattern="{role}-nj501-{seq}",
        vendor_short="OMR",
        model_short="NJ501",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V1.64",
            release_date=date(2024, 3, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V1.49",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-34151"],
            notes="Vulnerable to authentication bypass via FINS",
        ),
        FirmwareVariant(
            version="V1.40",
            release_date=date(2021, 5, 10),
            cves=["CVE-2022-34151", "CVE-2022-33971"],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 47,
        "device_type": 14,
        "product_code": 501,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="omron/cj2m/cj2m-cpu35",
    vendor="Omron",
    vendor_family="CJ2M Series",
    model="CJ2M-CPU35",
    model_name="CJ2M CPU Unit",
    device_type="plc",
    description="High-speed compact PLC for machine control",

    oui_prefixes=["00:00:74", "00:04:C7"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 25.0,
        "mean_ms": 5.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
    },

    supported_protocols=["fins", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="CJ{10NUM}",
        station_name_pattern="{role}-cj2m-{seq}",
        vendor_short="OMR",
        model_short="CJ2M",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.1",
            release_date=date(2023, 6, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.0",
            release_date=date(2021, 11, 20),
            cves=["CVE-2022-34151"],
        ),
    ],
))


# -----------------------------------------------------------------------------
# MITSUBISHI TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="mitsubishi/iq-r/r08cpu",
    vendor="Mitsubishi",
    vendor_family="iQ-R Series",
    model="R08CPU",
    model_name="MELSEC iQ-R CPU",
    device_type="plc",
    description="High-speed universal CPU module for iQ-R platform",

    oui_prefixes=["00:00:7E", "00:04:0F", "00:50:13"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 12.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["slmp", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="{3ALPHA}{9NUM}",
        station_name_pattern="{role}-iqr-{seq}",
        vendor_short="MIT",
        model_short="R08",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V53",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V49",
            release_date=date(2022, 12, 15),
            cves=["CVE-2022-40265"],
            notes="Remote code execution via malformed packets",
        ),
        FirmwareVariant(
            version="V42",
            release_date=date(2021, 4, 20),
            cves=["CVE-2022-40265", "CVE-2021-20609"],
        ),
    ],
))


_register_template(DeviceTemplate(
    id="mitsubishi/fx5/fx5u-32mt",
    vendor="Mitsubishi",
    vendor_family="FX5 Series",
    model="FX5U-32MT/ES",
    model_name="MELSEC FX5U Compact PLC",
    device_type="plc",
    description="Compact PLC with built-in Ethernet",

    oui_prefixes=["00:00:7E", "00:04:0F"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 30.0,
        "mean_ms": 6.0,
        "std_dev_ms": 4.0,
        "distribution": "gaussian",
    },

    supported_protocols=["slmp", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="FX5{8NUM}",
        station_name_pattern="{role}-fx5-{seq}",
        vendor_short="MIT",
        model_short="FX5U",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V1.280",
            release_date=date(2024, 1, 5),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V1.220",
            release_date=date(2022, 6, 20),
            cves=["CVE-2022-25164"],
        ),
    ],
))


# -----------------------------------------------------------------------------
# BECKHOFF TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="beckhoff/cx/cx5130",
    vendor="Beckhoff",
    vendor_family="CX Series",
    model="CX5130",
    model_name="CX5130 Embedded PC",
    device_type="plc",
    description="Fanless Intel Atom-based embedded PC controller",

    oui_prefixes=["00:01:05"],

    tcp_stack={
        "ttl": 128,  # Windows CE/TwinCAT
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethercat", "modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="CX51-{8HEX}",
        station_name_pattern="{role}-cx5130-{seq}",
        vendor_short="BEC",
        model_short="CX51",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.1.4024.35",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
            notes="TwinCAT 3.1 Build 4024.35",
        ),
        FirmwareVariant(
            version="V3.1.4024.22",
            release_date=date(2022, 9, 10),
            cves=["CVE-2022-44019"],
        ),
        FirmwareVariant(
            version="V3.1.4022.30",
            release_date=date(2021, 3, 20),
            cves=["CVE-2022-44019", "CVE-2021-21003"],
        ),
    ],
))


# -----------------------------------------------------------------------------
# PHOENIX CONTACT TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="phoenix-contact/plcnext/axc-f-2152",
    vendor="Phoenix Contact",
    vendor_family="PLCnext",
    model="AXC F 2152",
    model_name="PLCnext Control AXC F 2152",
    device_type="plc",
    description="Linux-based open automation controller",

    oui_prefixes=["00:A0:45", "00:16:9D", "A8:74:1D"],

    tcp_stack={
        "ttl": 64,  # Linux
        "window_size": 29200,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.0,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="AXC{10NUM}",
        station_name_pattern="{role}-plcnext-{seq}",
        vendor_short="PHX",
        model_short="AXC",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2024.0.0",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2022.0.5",
            release_date=date(2022, 11, 15),
            cves=["CVE-2023-28831"],
        ),
        FirmwareVariant(
            version="V2021.0.3",
            release_date=date(2021, 6, 20),
            cves=["CVE-2023-28831", "CVE-2021-34579"],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x00B8,
        "device_id": 0x0152,
        "device_role": 2,
        "im0_manufacturer": "Phoenix Contact",
        "im0_order_id": "AXC F 2152",
    },
))


# -----------------------------------------------------------------------------
# WAGO TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="wago/pfc200/750-8212",
    vendor="WAGO",
    vendor_family="PFC200",
    model="750-8212",
    model_name="PFC200 Controller",
    device_type="plc",
    description="Compact Linux-based controller with CODESYS runtime",

    oui_prefixes=["00:30:DE", "00:03:C6"],

    tcp_stack={
        "ttl": 64,
        "window_size": 29200,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.8,
        "max_ms": 20.0,
        "mean_ms": 4.0,
        "std_dev_ms": 2.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "codesys", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="750{10NUM}",
        station_name_pattern="{role}-pfc200-{seq}",
        vendor_short="WAG",
        model_short="PFC2",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="FW24",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="FW22",
            release_date=date(2022, 7, 10),
            cves=["CVE-2022-45140"],
        ),
        FirmwareVariant(
            version="FW18",
            release_date=date(2020, 4, 15),
            cves=["CVE-2022-45140", "CVE-2021-34569", "CVE-2020-12522"],
            notes="Multiple critical vulnerabilities",
        ),
    ],

    modbus_identity={
        "vendor_name": "WAGO Kontakttechnik GmbH",
        "product_code": "750-8212",
        "product_name": "PFC200 G2 2ETH RS",
        "model_name": "750-8212",
    },
))


# -----------------------------------------------------------------------------
# SEL (SCHWEITZER ENGINEERING) TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="sel/relay/sel-751",
    vendor="SEL",
    vendor_family="SEL-700 Series",
    model="SEL-751",
    model_name="SEL-751 Feeder Protection Relay",
    device_type="protection_relay",
    description="Feeder protection relay with comprehensive protection functions",

    oui_prefixes=["00:30:A7", "00:1C:73"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

    instance_rules=InstanceGenerationRules(
        serial_format="SEL{10NUM}",
        station_name_pattern="relay-751-{seq}",
        vendor_short="SEL",
        model_short="751",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R151-V4",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R151-V2",
            release_date=date(2022, 5, 20),
            cves=["CVE-2023-31170"],
        ),
        FirmwareVariant(
            version="R150-V0",
            release_date=date(2020, 10, 10),
            cves=["CVE-2023-31170", "CVE-2021-31553"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schweitzer Engineering Laboratories",
        "product_code": "SEL-751",
        "product_name": "SEL-751 Feeder Protection Relay",
    },
))


_register_template(DeviceTemplate(
    id="sel/rtac/sel-3530",
    vendor="SEL",
    vendor_family="SEL-3500 Series",
    model="SEL-3530",
    model_name="SEL-3530 RTAC",
    device_type="rtu",
    description="Real-Time Automation Controller for substation automation",

    oui_prefixes=["00:30:A7", "00:1C:73"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "dnp3", "iec61850", "iec104"],

    instance_rules=InstanceGenerationRules(
        serial_format="RTAC{10NUM}",
        station_name_pattern="rtac-{location}-{seq}",
        vendor_short="SEL",
        model_short="3530",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R150-V5",
            release_date=date(2024, 3, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R148-V2",
            release_date=date(2022, 8, 15),
            cves=["CVE-2023-31170"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schweitzer Engineering Laboratories",
        "product_code": "SEL-3530",
        "product_name": "SEL-3530 Real-Time Automation Controller",
    },
))


_register_template(DeviceTemplate(
    id="sel/relay/sel-451",
    vendor="SEL",
    vendor_family="SEL-400 Series",
    model="SEL-451",
    model_name="SEL-451 Bay Controller",
    device_type="protection_relay",
    description="Bay controller with protection and control functions",

    oui_prefixes=["00:30:A7", "00:1C:73"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.4,
        "max_ms": 8.0,
        "mean_ms": 1.8,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

    instance_rules=InstanceGenerationRules(
        serial_format="SEL{10NUM}",
        station_name_pattern="relay-451-{seq}",
        vendor_short="SEL",
        model_short="451",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R160-V5",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R159-V2",
            release_date=date(2022, 6, 20),
            cves=["CVE-2023-31170"],
        ),
        FirmwareVariant(
            version="R157-V0",
            release_date=date(2020, 11, 10),
            cves=["CVE-2023-31170", "CVE-2021-31553"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schweitzer Engineering Laboratories",
        "product_code": "SEL-451",
        "product_name": "SEL-451 Bay Controller",
    },
))


_register_template(DeviceTemplate(
    id="sel/controller/sel-2411",
    vendor="SEL",
    vendor_family="SEL-2400 Series",
    model="SEL-2411",
    model_name="SEL-2411 Programmable Automation Controller",
    device_type="substation_controller",
    description="Programmable logic controller for substation automation",

    oui_prefixes=["00:30:A7", "00:1C:73"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.2,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

    instance_rules=InstanceGenerationRules(
        serial_format="SEL{10NUM}",
        station_name_pattern="pac-2411-{seq}",
        vendor_short="SEL",
        model_short="2411",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R133-V4",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R131-V2",
            release_date=date(2022, 7, 15),
            cves=["CVE-2023-31170"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schweitzer Engineering Laboratories",
        "product_code": "SEL-2411",
        "product_name": "SEL-2411 Programmable Automation Controller",
    },
))


_register_template(DeviceTemplate(
    id="sel/relay/sel-311c",
    vendor="SEL",
    vendor_family="SEL-300 Series",
    model="SEL-311C",
    model_name="SEL-311C Line Protection Relay",
    device_type="protection_relay",
    description="Distance relay for transmission line protection",

    oui_prefixes=["00:30:A7", "00:1C:73"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 6.0,
        "mean_ms": 1.5,
        "std_dev_ms": 0.8,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

    instance_rules=InstanceGenerationRules(
        serial_format="SEL{10NUM}",
        station_name_pattern="relay-311c-{seq}",
        vendor_short="SEL",
        model_short="311C",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R111-V6",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R110-V3",
            release_date=date(2022, 4, 15),
            cves=["CVE-2023-31170"],
        ),
        FirmwareVariant(
            version="R108-V0",
            release_date=date(2020, 8, 10),
            cves=["CVE-2023-31170", "CVE-2021-31553"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schweitzer Engineering Laboratories",
        "product_code": "SEL-311C",
        "product_name": "SEL-311C Line Protection Relay",
    },
))


_register_template(DeviceTemplate(
    id="sel/relay/sel-487e",
    vendor="SEL",
    vendor_family="SEL-400 Series",
    model="SEL-487E",
    model_name="SEL-487E Transformer Protection Relay",
    device_type="protection_relay",
    description="Transformer differential protection relay",

    oui_prefixes=["00:30:A7", "00:1C:73"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 7.0,
        "mean_ms": 1.6,
        "std_dev_ms": 0.9,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "dnp3", "iec61850"],

    instance_rules=InstanceGenerationRules(
        serial_format="SEL{10NUM}",
        station_name_pattern="relay-487e-{seq}",
        vendor_short="SEL",
        model_short="487E",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R160-V4",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R158-V2",
            release_date=date(2022, 5, 20),
            cves=["CVE-2023-31170"],
        ),
        FirmwareVariant(
            version="R156-V0",
            release_date=date(2020, 9, 15),
            cves=["CVE-2023-31170", "CVE-2021-31553"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schweitzer Engineering Laboratories",
        "product_code": "SEL-487E",
        "product_name": "SEL-487E Transformer Protection Relay",
    },
))


# -----------------------------------------------------------------------------
# JOHNSON CONTROLS (BUILDING AUTOMATION) TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="johnson-controls/metasys/nae55",
    vendor="Johnson Controls",
    vendor_family="Metasys",
    model="NAE55",
    model_name="NAE55 Network Automation Engine",
    device_type="bac",
    description="Building automation network controller",

    oui_prefixes=["00:1A:17", "00:16:C7", "00:23:BE"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="NAE{10NUM}",
        station_name_pattern="bms-{location}-{seq}",
        vendor_short="JCI",
        model_short="NAE55",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V12.0.3",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V11.0.6",
            release_date=date(2022, 10, 20),
            cves=["CVE-2021-36205"],
        ),
        FirmwareVariant(
            version="V10.1.0",
            release_date=date(2021, 3, 10),
            cves=["CVE-2021-36205", "CVE-2021-27654"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 5,  # Johnson Controls
        "device_type": "Network Automation Engine",
        "model_name": "NAE55",
    },
))


_register_template(DeviceTemplate(
    id="johnson-controls/facility-explorer/fec26",
    vendor="Johnson Controls",
    vendor_family="Facility Explorer",
    model="FEC26",
    model_name="FEC26 Field Equipment Controller",
    device_type="field_controller",
    description="BACnet field controller for HVAC equipment",

    oui_prefixes=["00:1A:17", "00:16:C7", "00:23:BE"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 60.0,
        "mean_ms": 15.0,
        "std_dev_ms": 10.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="FEC26{8NUM}",
        station_name_pattern="fec-{location}-{seq}",
        vendor_short="JCI",
        model_short="FEC26",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.5.1",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.3.0",
            release_date=date(2022, 6, 15),
            cves=["CVE-2021-36205"],
        ),
        FirmwareVariant(
            version="V3.0.0",
            release_date=date(2020, 10, 10),
            cves=["CVE-2021-36205", "CVE-2020-9049"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 5,
        "device_type": "Field Controller",
        "model_name": "FEC26",
    },

    modbus_identity={
        "vendor_name": "Johnson Controls",
        "product_code": "FEC26",
        "product_name": "Facility Explorer FEC26",
    },
))


_register_template(DeviceTemplate(
    id="schneider/andover/cx9680",
    vendor="Schneider",
    vendor_family="Andover Continuum",
    model="CX9680",
    model_name="Andover Continuum CX9680",
    device_type="bms_controller",
    description="Advanced BMS controller for building automation",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 12.0,
        "std_dev_ms": 8.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="CX96{8NUM}",
        station_name_pattern="continuum-{location}-{seq}",
        vendor_short="SCH",
        model_short="CX96",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.8.5",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.6.0",
            release_date=date(2022, 7, 15),
            cves=["CVE-2022-22810"],
        ),
        FirmwareVariant(
            version="V2.4.0",
            release_date=date(2020, 11, 10),
            cves=["CVE-2022-22810", "CVE-2020-7477"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 67,
        "device_type": "Building Controller",
        "model_name": "Continuum CX9680",
    },

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "CX9680",
        "product_name": "Andover Continuum CX9680",
    },
))


# -----------------------------------------------------------------------------
# ECONOLITE (TRANSPORTATION/ITS) TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="econolite/asc3/cobalt",
    vendor="Econolite",
    vendor_family="ASC/3",
    model="ASC/3-2100 Cobalt",
    model_name="ASC/3 Cobalt Traffic Controller",
    device_type="traffic_controller",
    description="Advanced traffic signal controller with NTCIP support",

    oui_prefixes=["00:19:FA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 50.0,
        "mean_ms": 10.0,
        "std_dev_ms": 8.0,
        "distribution": "lognormal",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="ECO{10NUM}",
        station_name_pattern="tsc-{location}-{seq}",
        vendor_short="ECO",
        model_short="ASC3",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V7.16",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V7.10",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-25343"],
        ),
        FirmwareVariant(
            version="V6.45",
            release_date=date(2020, 9, 20),
            cves=["CVE-2022-25343", "CVE-2020-14476"],
        ),
    ],

    snmp_identity={
        "sys_descr": "ASC/3-2100 Cobalt Traffic Signal Controller",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",  # NTCIP
        "sys_contact": "traffic-ops@city.gov",
    },
))


# Econolite Cobalt ATC (alias for ASC/3-2100 Cobalt)
_register_template(DeviceTemplate(
    id="econolite/cobalt/atc",
    vendor="Econolite",
    vendor_family="Cobalt",
    model="Cobalt ATC",
    model_name="Cobalt ATC Traffic Controller",
    device_type="traffic_controller",
    description="Advanced traffic signal controller with NTCIP support",

    oui_prefixes=["00:19:FA"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 50.0,
        "mean_ms": 10.0,
        "std_dev_ms": 8.0,
        "distribution": "lognormal",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="ECO{10NUM}",
        station_name_pattern="tsc-{location}-{seq}",
        vendor_short="ECO",
        model_short="COBT",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V7.16",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "Econolite Cobalt ATC Traffic Signal Controller",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",
    },
))


# -----------------------------------------------------------------------------
# ABB TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="abb/ac500/pm5630",
    vendor="ABB",
    vendor_family="AC500",
    model="PM5630-2ETH",
    model_name="AC500-eCo PM5630",
    device_type="plc",
    description="High-performance AC500 PLC with dual Ethernet",

    oui_prefixes=["00:21:99", "00:24:2B", "00:1F:ED", "C4:93:00"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 30.0,
        "mean_ms": 7.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "profinet", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="ABB-{8HEX}",
        station_name_pattern="{role}-ac500-{seq}",
        vendor_short="ABB",
        model_short="PM56",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.5.2",
            release_date=date(2024, 1, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.2.0",
            release_date=date(2022, 5, 15),
            cves=["CVE-2022-26007"],
        ),
        FirmwareVariant(
            version="V3.0.1",
            release_date=date(2020, 11, 20),
            cves=["CVE-2022-26007", "CVE-2020-24680"],
        ),
    ],

    modbus_identity={
        "vendor_name": "ABB",
        "product_code": "PM5630-2ETH",
        "vendor_url": "http://www.abb.com",
        "product_name": "AC500-eCo PLC",
        "model_name": "PM5630",
    },

    profinet_identity={
        "vendor_id": 0x0037,
        "device_id": 0x5630,
        "device_role": 1,
        "im0_manufacturer": "ABB",
        "im0_order_id": "PM5630-2ETH",
    },
))


# ABB AC500 PM590-ETH High Performance CPU
_register_template(DeviceTemplate(
    id="abb/ac500/pm590-eth",
    vendor="ABB",
    vendor_family="AC500",
    model="PM590-ETH",
    model_name="AC500 PM590-ETH",
    device_type="plc",
    description="High-performance AC500 CPU with Ethernet interface",

    oui_prefixes=["00:20:99", "00:21:99", "00:24:CB"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 20.0,
        "mean_ms": 5.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "profinet", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="ABB{8HEX}",
        station_name_pattern="{role}-pm590-{seq}",
        vendor_short="ABB",
        model_short="PM590",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.1.2",
            release_date=date(2023, 8, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.9.0",
            release_date=date(2021, 4, 15),
            cves=["CVE-2020-24680"],
        ),
    ],

    modbus_identity={
        "vendor_name": "ABB",
        "product_code": "PM590-ETH",
        "vendor_url": "http://www.abb.com",
        "product_name": "AC500 PM590",
        "model_name": "AC500",
    },

    ethernet_ip_identity={
        "vendor_id": 285,  # ABB
        "device_type": 14,  # Programmable Logic Controller
        "product_code": 590,
        "state": 3,
    },
))


# ABB AC500 PM583-ETH CPU
_register_template(DeviceTemplate(
    id="abb/ac500/pm583-eth",
    vendor="ABB",
    vendor_family="AC500",
    model="PM583-ETH",
    model_name="AC500 PM583-ETH",
    device_type="plc",
    description="AC500 CPU with Ethernet interface for medium applications",

    oui_prefixes=["00:20:99", "00:21:99", "00:24:CB"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.5,
        "max_ms": 25.0,
        "mean_ms": 6.0,
        "std_dev_ms": 3.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="ABB{8HEX}",
        station_name_pattern="{role}-pm583-{seq}",
        vendor_short="ABB",
        model_short="PM583",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.0.4",
            release_date=date(2023, 6, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "ABB",
        "product_code": "PM583-ETH",
        "vendor_url": "http://www.abb.com",
        "product_name": "AC500 PM583",
        "model_name": "AC500",
    },
))


# ABB AC500-eCo PM554-TP-ETH Compact CPU
_register_template(DeviceTemplate(
    id="abb/ac500-eco/pm554-tp-eth",
    vendor="ABB",
    vendor_family="AC500-eCo",
    model="PM554-TP-ETH",
    model_name="AC500-eCo PM554-TP-ETH",
    device_type="rtu",
    description="Compact AC500-eCo CPU for remote applications",

    oui_prefixes=["00:20:99", "00:21:99"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 35.0,
        "mean_ms": 10.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="ABB{6HEX}",
        station_name_pattern="{role}-pm554-{seq}",
        vendor_short="ABB",
        model_short="PM554",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.4.1",
            release_date=date(2023, 3, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "ABB",
        "product_code": "PM554-TP-ETH",
        "vendor_url": "http://www.abb.com",
        "product_name": "AC500-eCo PM554",
        "model_name": "AC500-eCo",
    },
))


# ABB ACS880-01 Industrial Drive
_register_template(DeviceTemplate(
    id="abb/acs880/acs880-01",
    vendor="ABB",
    vendor_family="ACS880",
    model="ACS880-01",
    model_name="ACS880-01 Industrial Drive",
    device_type="drive",
    description="High-performance industrial drive for demanding applications",

    oui_prefixes=["00:20:99", "00:21:99", "00:24:CB"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 40.0,
        "mean_ms": 12.0,
        "std_dev_ms": 6.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "profinet", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="ABB{8HEX}",
        station_name_pattern="{role}-acs880-{seq}",
        vendor_short="ABB",
        model_short="ACS880",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.60",
            release_date=date(2023, 10, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.40",
            release_date=date(2021, 6, 15),
            cves=["CVE-2021-22278"],
        ),
    ],

    modbus_identity={
        "vendor_name": "ABB",
        "product_code": "ACS880-01",
        "vendor_url": "http://www.abb.com",
        "product_name": "ACS880 Industrial Drive",
        "model_name": "ACS880",
    },

    ethernet_ip_identity={
        "vendor_id": 285,  # ABB
        "device_type": 2,  # AC Drive
        "product_code": 880,
        "state": 3,
    },
))


# ABB CI501 Remote I/O Module
_register_template(DeviceTemplate(
    id="abb/ac500/ci501",
    vendor="ABB",
    vendor_family="AC500",
    model="CI501",
    model_name="CI501 Remote I/O",
    device_type="io_module",
    description="CI501 communication interface for distributed I/O",

    oui_prefixes=["00:20:99", "00:21:99"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 15.0,
        "mean_ms": 4.0,
        "std_dev_ms": 2.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="ABB{6HEX}",
        station_name_pattern="rio-{location}-{seq}",
        vendor_short="ABB",
        model_short="CI501",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.1.0",
            release_date=date(2023, 5, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "ABB",
        "product_code": "CI501",
        "vendor_url": "http://www.abb.com",
        "product_name": "CI501 Remote I/O",
        "model_name": "AC500",
    },
))


# -----------------------------------------------------------------------------
# HONEYWELL TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="honeywell/controledge/lcnp4m",
    vendor="Honeywell",
    vendor_family="ControlEdge",
    model="LCNP4M",
    model_name="ControlEdge PLC",
    device_type="plc",
    description="High-performance process controller",

    oui_prefixes=["00:60:35", "00:D0:36", "64:31:7E", "F4:4E:05"],

    tcp_stack={
        "ttl": 64,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.0,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="HW{10ALPHANUM}",
        station_name_pattern="{role}-cedge-{seq}",
        vendor_short="HON",
        model_short="LCNP",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R431.2",
            release_date=date(2024, 2, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R430.1",
            release_date=date(2022, 9, 15),
            cves=["CVE-2022-30317"],
        ),
        FirmwareVariant(
            version="R421.0",
            release_date=date(2020, 6, 10),
            cves=["CVE-2022-30317", "CVE-2020-6960"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Honeywell International Inc.",
        "product_code": "LCNP4M",
        "product_name": "ControlEdge PLC",
    },
))


_register_template(DeviceTemplate(
    id="honeywell/experion-pks/c300",
    vendor="Honeywell",
    vendor_family="Experion PKS",
    model="C300",
    model_name="Experion PKS C300 Controller",
    device_type="dcs_controller",
    description="High-performance process controller for Experion PKS DCS",

    oui_prefixes=["00:60:35", "00:D0:36", "64:31:7E", "F4:4E:05"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 12.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.8,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="C300-{8HEX}",
        station_name_pattern="c300-{location}-{seq}",
        vendor_short="HON",
        model_short="C300",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R520.2",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R510.1",
            release_date=date(2022, 10, 20),
            cves=["CVE-2022-30317"],
        ),
        FirmwareVariant(
            version="R501.0",
            release_date=date(2021, 4, 10),
            cves=["CVE-2022-30317", "CVE-2021-38395"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Honeywell International Inc.",
        "product_code": "C300",
        "vendor_url": "http://www.honeywell.com",
        "product_name": "Experion PKS C300 Controller",
        "model_name": "C300",
    },
))


_register_template(DeviceTemplate(
    id="honeywell/experion-pks/c200",
    vendor="Honeywell",
    vendor_family="Experion PKS",
    model="C200",
    model_name="Experion PKS C200 Controller",
    device_type="dcs_controller",
    description="Mid-range process controller for Experion PKS DCS",

    oui_prefixes=["00:60:35", "00:D0:36", "64:31:7E"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.8,
        "max_ms": 18.0,
        "mean_ms": 4.0,
        "std_dev_ms": 2.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="C200-{8HEX}",
        station_name_pattern="c200-{location}-{seq}",
        vendor_short="HON",
        model_short="C200",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R520.2",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R510.1",
            release_date=date(2022, 10, 20),
            cves=["CVE-2022-30317"],
        ),
        FirmwareVariant(
            version="R501.0",
            release_date=date(2021, 4, 10),
            cves=["CVE-2022-30317", "CVE-2021-38395"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Honeywell International Inc.",
        "product_code": "C200",
        "vendor_url": "http://www.honeywell.com",
        "product_name": "Experion PKS C200 Controller",
        "model_name": "C200",
    },
))


_register_template(DeviceTemplate(
    id="honeywell/experion-pks/server",
    vendor="Honeywell",
    vendor_family="Experion PKS",
    model="Experion Server",
    model_name="Experion PKS Server",
    device_type="scada_server",
    description="Experion PKS application server for DCS operation",

    oui_prefixes=["00:60:35", "00:D0:36", "64:31:7E", "F4:4E:05"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 50.0,
        "mean_ms": 10.0,
        "std_dev_ms": 8.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="EXPSVR-{8HEX}",
        station_name_pattern="experion-svr-{seq}",
        vendor_short="HON",
        model_short="EXPSVR",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R520.2",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R510.1",
            release_date=date(2022, 10, 20),
            cves=["CVE-2022-30317"],
        ),
        FirmwareVariant(
            version="R501.0",
            release_date=date(2021, 4, 10),
            cves=["CVE-2022-30317", "CVE-2021-38395"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Honeywell International Inc.",
        "product_code": "Experion-Server",
        "product_name": "Experion PKS Server",
    },
))


_register_template(DeviceTemplate(
    id="honeywell/experion-pks/safety-manager",
    vendor="Honeywell",
    vendor_family="Experion PKS",
    model="Safety Manager",
    model_name="Experion Safety Manager",
    device_type="safety_plc",
    description="SIL 3 safety controller for Experion PKS",

    oui_prefixes=["00:60:35", "00:D0:36", "64:31:7E"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="SM-{8HEX}",
        station_name_pattern="safety-{location}-{seq}",
        vendor_short="HON",
        model_short="SM",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V12.5",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V11.3",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-30317"],
        ),
        FirmwareVariant(
            version="V10.2",
            release_date=date(2020, 9, 10),
            cves=["CVE-2022-30317", "CVE-2020-6960"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Honeywell International Inc.",
        "product_code": "Safety-Manager",
        "product_name": "Experion Safety Manager",
    },
))


_register_template(DeviceTemplate(
    id="honeywell/experion-pks/series-c-io",
    vendor="Honeywell",
    vendor_family="Experion PKS",
    model="Series C I/O",
    model_name="Experion Series C I/O",
    device_type="remote_io",
    description="Series C distributed I/O for Experion PKS",

    oui_prefixes=["00:60:35", "00:D0:36"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.2,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="SCIO-{8HEX}",
        station_name_pattern="io-seriesc-{seq}",
        vendor_short="HON",
        model_short="SCIO",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.3",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.0",
            release_date=date(2022, 5, 20),
            cves=["CVE-2022-30317"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Honeywell International Inc.",
        "product_code": "Series-C-IO",
        "product_name": "Experion Series C I/O",
    },
))


_register_template(DeviceTemplate(
    id="honeywell/experion-pks/station",
    vendor="Honeywell",
    vendor_family="Experion PKS",
    model="Experion Station",
    model_name="Experion Operator Station",
    device_type="operator_station",
    description="Operator workstation for Experion PKS HMI",

    oui_prefixes=["00:60:35", "00:D0:36", "64:31:7E", "F4:4E:05"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 100.0,
        "mean_ms": 20.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="EXPWS-{8HEX}",
        station_name_pattern="experion-ws-{seq}",
        vendor_short="HON",
        model_short="EXPWS",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R520.2",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R510.1",
            release_date=date(2022, 10, 20),
            cves=["CVE-2022-30317"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Honeywell International Inc.",
        "product_code": "Experion-Station",
        "product_name": "Experion Operator Station",
    },
))


_register_template(DeviceTemplate(
    id="honeywell/niagara/jace-8000",
    vendor="Honeywell",
    vendor_family="Niagara",
    model="JACE 8000",
    model_name="JACE 8000 Controller",
    device_type="bms_controller",
    description="Niagara Framework-based building automation controller",

    oui_prefixes=["00:60:35", "00:D0:36", "00:0D:6B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 80.0,
        "mean_ms": 15.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp", "bacnet", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="JACE8K-{8HEX}",
        station_name_pattern="jace-{location}-{seq}",
        vendor_short="HON",
        model_short="JACE8",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="N4.13",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="N4.10",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-40145"],
        ),
        FirmwareVariant(
            version="N4.8",
            release_date=date(2021, 3, 10),
            cves=["CVE-2022-40145", "CVE-2021-26264"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Honeywell International Inc.",
        "product_code": "JACE-8000",
        "product_name": "Niagara JACE 8000",
    },

    bacnet_identity={
        "vendor_id": 256,  # Tridium (Honeywell subsidiary)
        "vendor_name": "Tridium, Inc.",
        "model_name": "JACE 8000",
    },
))


_register_template(DeviceTemplate(
    id="honeywell/excel/xl-web",
    vendor="Honeywell",
    vendor_family="Excel",
    model="XL Web",
    model_name="Excel Web Boiler Controller",
    device_type="hvac_controller",
    description="Excel Web controller for boiler and HVAC applications",

    oui_prefixes=["00:60:35", "00:D0:36"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 80.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp", "bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="XLWEB-{8NUM}",
        station_name_pattern="xlweb-{location}-{seq}",
        vendor_short="HON",
        model_short="XLWEB",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.2",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.8",
            release_date=date(2022, 4, 20),
            cves=["CVE-2022-30244"],
        ),
        FirmwareVariant(
            version="V4.5",
            release_date=date(2020, 8, 10),
            cves=["CVE-2022-30244", "CVE-2020-6968"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Honeywell International Inc.",
        "product_code": "XL-Web",
        "product_name": "Excel Web Boiler Controller",
    },

    bacnet_identity={
        "vendor_id": 94,  # Honeywell
        "vendor_name": "Honeywell",
        "model_name": "Excel Web",
    },
))


_register_template(DeviceTemplate(
    id="honeywell/enraf/optiflex-6000",
    vendor="Honeywell",
    vendor_family="Enraf",
    model="Optiflex 6000",
    model_name="Optiflex 6000 Level Gauge",
    device_type="level_gauge",
    description="Servo tank gauge for custody transfer applications",

    oui_prefixes=["00:60:35", "00:D0:36"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="OPT6K-{8NUM}",
        station_name_pattern="gauge-{location}-{seq}",
        vendor_short="HON",
        model_short="OPT6K",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.3.1",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.1.0",
            release_date=date(2022, 5, 15),
            cves=["CVE-2022-30312"],
        ),
        FirmwareVariant(
            version="V3.8.0",
            release_date=date(2020, 9, 10),
            cves=["CVE-2022-30312", "CVE-2020-6994"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Honeywell Enraf",
        "product_code": "Optiflex-6000",
        "product_name": "Optiflex 6000 Level Gauge",
    },
))


# -----------------------------------------------------------------------------
# EMERSON TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="emerson/deltav/s-series",
    vendor="Emerson",
    vendor_family="DeltaV",
    model="S-series",
    model_name="DeltaV S-series Controller",
    device_type="dcs_controller",
    description="Process automation controller for DeltaV DCS",

    oui_prefixes=["00:A0:F8", "00:50:43", "00:60:35"],

    tcp_stack={
        "ttl": 128,  # Windows-based
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.8,
        "max_ms": 20.0,
        "mean_ms": 5.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="DV{2ALPHA}{8NUM}",
        station_name_pattern="dcs-{location}-{seq}",
        vendor_short="EMR",
        model_short="DVS",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V15.3",
            release_date=date(2024, 1, 25),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V14.3",
            release_date=date(2022, 7, 15),
            cves=["CVE-2022-29966"],
        ),
        FirmwareVariant(
            version="V13.3",
            release_date=date(2020, 12, 10),
            cves=["CVE-2022-29966", "CVE-2020-16233"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Emerson Process Management",
        "product_code": "DeltaV-S",
        "product_name": "DeltaV S-series Controller",
    },
))


_register_template(DeviceTemplate(
    id="emerson/roc/800l",
    vendor="Emerson",
    vendor_family="ROC",
    model="ROC800L",
    model_name="ROC800L Remote Operations Controller",
    device_type="rtu",
    description="Flow computer and RTU for oil & gas",

    oui_prefixes=["00:A0:F8", "00:90:E8"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp", "dnp3"],

    instance_rules=InstanceGenerationRules(
        serial_format="ROC{10NUM}",
        station_name_pattern="rtu-{location}-{seq}",
        vendor_short="EMR",
        model_short="ROC8",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.91",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.80",
            release_date=date(2022, 4, 20),
            cves=["CVE-2022-30264"],
        ),
        FirmwareVariant(
            version="V3.50",
            release_date=date(2019, 8, 15),
            cves=["CVE-2022-30264", "CVE-2019-10971"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Emerson Process Management",
        "product_code": "ROC800L",
        "product_name": "ROC800L Remote Operations Controller",
    },
))


_register_template(DeviceTemplate(
    id="emerson/deltav/md-plus",
    vendor="Emerson",
    vendor_family="DeltaV",
    model="MD Plus",
    model_name="DeltaV MD Plus Controller",
    device_type="dcs_controller",
    description="Mid-range DeltaV controller for small to medium applications",

    oui_prefixes=["00:A0:F8", "00:50:43", "00:60:35"],

    tcp_stack={
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 25.0,
        "mean_ms": 6.0,
        "std_dev_ms": 4.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="DVMD{8NUM}",
        station_name_pattern="dcs-md-{seq}",
        vendor_short="EMR",
        model_short="DVMD",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V15.3",
            release_date=date(2024, 1, 25),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V14.3",
            release_date=date(2022, 7, 15),
            cves=["CVE-2022-29966"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Emerson Process Management",
        "product_code": "DeltaV-MD-Plus",
        "product_name": "DeltaV MD Plus Controller",
    },
))


_register_template(DeviceTemplate(
    id="emerson/roc/800",
    vendor="Emerson",
    vendor_family="ROC",
    model="ROC800",
    model_name="ROC800 Remote Operations Controller",
    device_type="rtu",
    description="Standard ROC800 flow computer and RTU",

    oui_prefixes=["00:A0:F8", "00:90:E8"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 80.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp", "dnp3"],

    instance_rules=InstanceGenerationRules(
        serial_format="ROC8{10NUM}",
        station_name_pattern="rtu-{location}-{seq}",
        vendor_short="EMR",
        model_short="ROC8",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.91",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.80",
            release_date=date(2022, 4, 20),
            cves=["CVE-2022-30264"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Emerson Process Management",
        "product_code": "ROC800",
        "product_name": "ROC800 Remote Operations Controller",
    },
))


_register_template(DeviceTemplate(
    id="emerson/rosemount/3051s",
    vendor="Emerson",
    vendor_family="Rosemount",
    model="3051S",
    model_name="Rosemount 3051S Pressure Transmitter",
    device_type="transmitter",
    description="SuperModule pressure transmitter with advanced diagnostics",

    oui_prefixes=["00:A0:F8", "00:50:43"],

    tcp_stack={
        "ttl": 64,
        "window_size": 8192,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 40.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="RM3051{8NUM}",
        station_name_pattern="pt-{location}-{seq}",
        vendor_short="EMR",
        model_short="3051",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V11.3",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V11.0",
            release_date=date(2022, 5, 15),
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Emerson Process Management",
        "product_code": "3051S",
        "product_name": "Rosemount 3051S Pressure Transmitter",
    },
))


_register_template(DeviceTemplate(
    id="emerson/micromotion/5700",
    vendor="Emerson",
    vendor_family="Micro Motion",
    model="5700",
    model_name="Micro Motion 5700 Transmitter",
    device_type="flow_meter",
    description="Coriolis flow transmitter for custody transfer",

    oui_prefixes=["00:A0:F8", "00:50:43"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 50.0,
        "mean_ms": 12.0,
        "std_dev_ms": 7.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="MM57{10NUM}",
        station_name_pattern="flow-{location}-{seq}",
        vendor_short="EMR",
        model_short="MM57",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V8.2",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V8.0",
            release_date=date(2022, 6, 20),
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Emerson Process Management",
        "product_code": "5700",
        "product_name": "Micro Motion 5700 Transmitter",
    },
))


_register_template(DeviceTemplate(
    id="emerson/fisher/dvc6200",
    vendor="Emerson",
    vendor_family="Fisher FIELDVUE",
    model="DVC6200",
    model_name="DVC6200 Digital Valve Controller",
    device_type="valve_positioner",
    description="Digital valve controller with advanced diagnostics",

    oui_prefixes=["00:A0:F8", "00:50:43"],

    tcp_stack={
        "ttl": 64,
        "window_size": 8192,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 80.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="DVC{10NUM}",
        station_name_pattern="valve-{location}-{seq}",
        vendor_short="EMR",
        model_short="DVC6",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.4",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V6.2",
            release_date=date(2022, 4, 20),
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Emerson Process Management",
        "product_code": "DVC6200",
        "product_name": "DVC6200 Digital Valve Controller",
    },
))


# Emerson DeltaV Continuous Historian
_register_template(DeviceTemplate(
    id="emerson/deltav/historian",
    vendor="Emerson",
    vendor_family="DeltaV",
    model="Continuous Historian",
    model_name="DeltaV Continuous Historian",
    device_type="historian",
    description="Process historian for DeltaV DCS",

    oui_prefixes=["00:A0:F8", "00:50:43", "00:12:A9"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 150.0,
        "mean_ms": 40.0,
        "std_dev_ms": 20.0,
        "distribution": "gaussian",
    },

    supported_protocols=["opc_ua", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="DVHIST{8HEX}",
        station_name_pattern="historian-{seq}",
        vendor_short="EMR",
        model_short="DVHIST",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V14.3",
            release_date=date(2023, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],
))


# Emerson DeltaV Operator Workstation
_register_template(DeviceTemplate(
    id="emerson/deltav/ows",
    vendor="Emerson",
    vendor_family="DeltaV",
    model="OWS",
    model_name="DeltaV Operator Workstation",
    device_type="hmi",
    description="DeltaV operator workstation for process monitoring",

    oui_prefixes=["00:A0:F8", "00:50:43", "00:12:A9"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 12.0,
        "distribution": "gaussian",
    },

    supported_protocols=["opc_ua", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="DVOWS{8HEX}",
        station_name_pattern="ows-{seq}",
        vendor_short="EMR",
        model_short="OWS",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V14.3",
            release_date=date(2023, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],
))


# -----------------------------------------------------------------------------
# GE TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="ge/pacsystems/rx3i-cpe400",
    vendor="GE",
    vendor_family="PACSystems",
    model="IC695CPE400",
    model_name="PACSystems RX3i CPE400",
    device_type="plc",
    description="High-performance PACSystems controller",

    oui_prefixes=["00:14:49", "00:60:B0", "1C:39:47"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.5,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="GE{10NUM}",
        station_name_pattern="{role}-rx3i-{seq}",
        vendor_short="GE",
        model_short="CPE4",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V10.10",
            release_date=date(2024, 2, 5),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V9.70",
            release_date=date(2022, 8, 20),
            cves=["CVE-2022-2893"],
        ),
        FirmwareVariant(
            version="V9.50",
            release_date=date(2021, 3, 15),
            cves=["CVE-2022-2893", "CVE-2021-27478"],
        ),
    ],

    modbus_identity={
        "vendor_name": "GE Automation",
        "product_code": "IC695CPE400",
        "vendor_url": "http://www.geautomation.com",
        "product_name": "PACSystems RX3i CPE400",
    },

    ethernet_ip_identity={
        "vendor_id": 82,
        "device_type": 14,
        "product_code": 400,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="ge/mark-vie/is420ucsbh1a",
    vendor="GE",
    vendor_family="Mark VIe",
    model="IS420UCSBH1A",
    model_name="Mark VIe Controller",
    device_type="dcs_controller",
    description="Turbine control system controller with redundancy support",

    oui_prefixes=["00:14:49", "00:60:B0", "1C:39:47", "00:C0:4F"],

    tcp_stack={
        "ttl": 128,  # Windows-based
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 0.8,
        "max_ms": 20.0,
        "mean_ms": 4.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
        "outlier_probability": 0.002,
        "outlier_multiplier": 4.0,
    },

    error_behavior={
        "supported_exception_codes": [1, 2, 3, 4, 5],
        "exception_probability": 0.0002,
        "timeout_probability": 0.0001,
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="IS42{8ALPHANUM}",
        station_name_pattern="{role}-markvie-{seq}",
        vendor_short="GE",
        model_short="UCSB",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="06.03.09",
            release_date=date(2024, 2, 28),
            is_latest=True,
            is_default=True,
            cves=[],
            notes="Latest firmware with security updates",
        ),
        FirmwareVariant(
            version="06.02.00",
            release_date=date(2022, 11, 15),
            cves=["CVE-2022-37953"],
            notes="Vulnerable to denial of service",
        ),
        FirmwareVariant(
            version="06.00.02",
            release_date=date(2021, 7, 20),
            cves=["CVE-2022-37953", "CVE-2021-44477"],
            notes="Multiple vulnerabilities - upgrade recommended",
        ),
        FirmwareVariant(
            version="05.04.00",
            release_date=date(2019, 9, 10),
            cves=["CVE-2022-37953", "CVE-2021-44477", "CVE-2019-13559"],
            notes="Legacy firmware with critical vulnerabilities",
        ),
    ],

    modbus_identity={
        "vendor_name": "GE Vernova",
        "product_code": "IS420UCSBH1A",
        "vendor_url": "http://www.gevernova.com",
        "product_name": "Mark VIe Controller",
        "model_name": "IS420UCSBH1A",
    },

    protocol_quirks={
        "modbus_max_registers": 125,
        "redundancy_support": True,
    },
))


# GE Proficy Historian
_register_template(DeviceTemplate(
    id="ge/proficy/historian",
    vendor="GE",
    vendor_family="Proficy",
    model="Proficy Historian",
    model_name="Proficy Historian",
    device_type="historian",
    description="Industrial data historian for process and manufacturing data",

    oui_prefixes=["00:50:C2", "00:12:A9"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 150.0,
        "mean_ms": 35.0,
        "std_dev_ms": 20.0,
        "distribution": "gaussian",
    },

    supported_protocols=["opc_ua", "modbus_tcp"],

    modbus_identity={
        "vendor_name": "GE Digital",
        "product_code": "Proficy Historian",
        "major_minor_revision": "8.0",
        "vendor_url": "http://www.ge.com/digital",
        "product_name": "Proficy Historian Server",
        "model_name": "Proficy Historian 8.0",
    },

    opc_ua_identity={
        "application_name": "GE Proficy Historian",
        "application_uri": "urn:GE:Proficy:Historian",
        "product_uri": "http://www.ge.com/digital/proficy-historian",
        "manufacturer_name": "GE Digital",
        "product_name": "Proficy Historian",
        "software_version": "8.0.1",
        "build_number": "1234",
        "build_date": "2024-01-15T12:00:00Z",
    },

    instance_rules=InstanceGenerationRules(
        serial_format="HIST{8HEX}",
        station_name_pattern="historian-{location}-{seq}",
        vendor_short="GE",
        model_short="HIST",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="8.0",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="7.1",
            release_date=date(2022, 6, 10),
            cves=["CVE-2022-23127"],
        ),
    ],
))


# -----------------------------------------------------------------------------
# SICK TEMPLATES
# -----------------------------------------------------------------------------

# SICK Inspector Vision Sensor
_register_template(DeviceTemplate(
    id="sick/inspector/p631",
    vendor="SICK",
    vendor_family="Inspector",
    model="Inspector P631",
    model_name="Inspector P631 Vision Sensor",
    device_type="vision_sensor",
    description="2D vision sensor for quality inspection applications",

    oui_prefixes=["00:06:B6", "00:1E:0E"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 15.0,
        "std_dev_ms": 8.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="SICK{8ALPHANUM}",
        station_name_pattern="cam-{location}-{seq}",
        vendor_short="SICK",
        model_short="P631",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.4.1",
            release_date=date(2023, 10, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x0112,
        "device_id": 0x0631,
        "device_role": 1,
        "im0_manufacturer": "SICK AG",
        "im0_order_id": "Inspector P631",
    },
))


# SICK CLV650 Barcode Scanner
_register_template(DeviceTemplate(
    id="sick/clv/clv650-0120",
    vendor="SICK",
    vendor_family="CLV",
    model="CLV650-0120",
    model_name="CLV650 Barcode Scanner",
    device_type="barcode_scanner",
    description="Industrial barcode scanner for logistics and manufacturing",

    oui_prefixes=["00:06:B6", "00:1E:0E"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 25.0,
        "mean_ms": 8.0,
        "std_dev_ms": 4.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="CLV{8ALPHANUM}",
        station_name_pattern="scan-{location}-{seq}",
        vendor_short="SICK",
        model_short="CLV650",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.10",
            release_date=date(2023, 7, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x0112,
        "device_id": 0x0650,
        "device_role": 1,
        "im0_manufacturer": "SICK AG",
        "im0_order_id": "CLV650-0120",
    },
))


# -----------------------------------------------------------------------------
# ENDRESS+HAUSER TEMPLATES
# -----------------------------------------------------------------------------

# Endress+Hauser Promag 400 Flow Meter
_register_template(DeviceTemplate(
    id="endress_hauser/promag/400",
    vendor="Endress_Hauser",
    vendor_family="Promag",
    model="Promag 400",
    model_name="Promag 400 Electromagnetic Flow Meter",
    device_type="flow_sensor",
    description="Electromagnetic flow meter for process applications",

    oui_prefixes=["00:04:F3", "00:80:A3"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 80.0,
        "mean_ms": 25.0,
        "std_dev_ms": 12.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="EH{10ALPHANUM}",
        station_name_pattern="ft-{location}-{seq}",
        vendor_short="EH",
        model_short="PM400",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V01.06.00",
            release_date=date(2023, 8, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Endress+Hauser",
        "product_code": "Promag 400",
        "vendor_url": "http://www.endress.com",
        "product_name": "Promag 400",
        "model_name": "Promag",
    },
))


# Endress+Hauser FMP50 Level Transmitter
_register_template(DeviceTemplate(
    id="endress_hauser/levelflex/fmp50",
    vendor="Endress_Hauser",
    vendor_family="Levelflex",
    model="FMP50",
    model_name="Levelflex FMP50 Level Transmitter",
    device_type="level_sensor",
    description="Guided wave radar level transmitter for liquids and solids",

    oui_prefixes=["00:04:F3", "00:80:A3"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 30.0,
        "std_dev_ms": 15.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="EH{10ALPHANUM}",
        station_name_pattern="lt-{location}-{seq}",
        vendor_short="EH",
        model_short="FMP50",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V01.05.00",
            release_date=date(2023, 5, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Endress+Hauser",
        "product_code": "FMP50",
        "vendor_url": "http://www.endress.com",
        "product_name": "Levelflex FMP50",
        "model_name": "Levelflex",
    },
))


# Endress+Hauser Cerabar PMC71 Pressure Transmitter
_register_template(DeviceTemplate(
    id="endress_hauser/cerabar/pmc71",
    vendor="Endress_Hauser",
    vendor_family="Cerabar",
    model="PMC71",
    model_name="Cerabar PMC71 Pressure Transmitter",
    device_type="pressure_sensor",
    description="Digital pressure transmitter for process measurement",

    oui_prefixes=["00:04:F3", "00:80:A3"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 90.0,
        "mean_ms": 28.0,
        "std_dev_ms": 14.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="EH{10ALPHANUM}",
        station_name_pattern="pt-{location}-{seq}",
        vendor_short="EH",
        model_short="PMC71",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V01.06.00",
            release_date=date(2023, 9, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Endress+Hauser",
        "product_code": "PMC71",
        "vendor_url": "http://www.endress.com",
        "product_name": "Cerabar PMC71",
        "model_name": "Cerabar",
    },
))


# -----------------------------------------------------------------------------
# JOHNSON CONTROLS TEMPLATES
# -----------------------------------------------------------------------------

# Johnson Controls NAE55 Network Automation Engine
_register_template(DeviceTemplate(
    id="johnson_controls/metasys/nae55",
    vendor="Johnson_Controls",
    vendor_family="Metasys",
    model="NAE55",
    model_name="NAE55 Network Automation Engine",
    device_type="bms_controller",
    description="Building automation network engine for Metasys",

    oui_prefixes=["00:04:5A", "00:A0:AF"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 10.0,
        "max_ms": 150.0,
        "mean_ms": 50.0,
        "std_dev_ms": 25.0,
        "distribution": "gaussian",
    },

    supported_protocols=["bacnet", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="JCI{8ALPHANUM}",
        station_name_pattern="nae-{location}-{seq}",
        vendor_short="JCI",
        model_short="NAE55",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="12.0",
            release_date=date(2023, 9, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="11.0",
            release_date=date(2021, 6, 15),
            cves=["CVE-2021-27660"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 5,
        "model_name": "NAE55",
        "device_instance": 0,
    },
))


# Johnson Controls FEC26 Field Equipment Controller
_register_template(DeviceTemplate(
    id="johnson_controls/metasys/fec26",
    vendor="Johnson_Controls",
    vendor_family="Metasys",
    model="FEC26",
    model_name="FEC26 Field Equipment Controller",
    device_type="lighting_controller",
    description="Field equipment controller for lighting and HVAC",

    oui_prefixes=["00:04:5A", "00:A0:AF"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 10.0,
        "max_ms": 100.0,
        "mean_ms": 35.0,
        "std_dev_ms": 18.0,
        "distribution": "gaussian",
    },

    supported_protocols=["bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="JCI{6ALPHANUM}",
        station_name_pattern="fec-{location}-{seq}",
        vendor_short="JCI",
        model_short="FEC26",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V7.0",
            release_date=date(2023, 4, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    bacnet_identity={
        "vendor_id": 5,
        "model_name": "FEC26",
        "device_instance": 0,
    },
))


# -----------------------------------------------------------------------------
# AUTOMATED LOGIC TEMPLATES
# -----------------------------------------------------------------------------

# Automated Logic WebCTRL Server
_register_template(DeviceTemplate(
    id="automated_logic/webctrl/server",
    vendor="Automated_Logic",
    vendor_family="WebCTRL",
    model="Server",
    model_name="WebCTRL Server",
    device_type="bms_server",
    description="WebCTRL building automation server",

    oui_prefixes=["00:50:C2", "00:17:61"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 10.0,
        "max_ms": 200.0,
        "mean_ms": 60.0,
        "std_dev_ms": 30.0,
        "distribution": "gaussian",
    },

    supported_protocols=["bacnet", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="ALC{8ALPHANUM}",
        station_name_pattern="webctrl-{location}-{seq}",
        vendor_short="ALC",
        model_short="WCTRL",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="8.0",
            release_date=date(2023, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="7.0",
            release_date=date(2021, 9, 15),
            cves=["CVE-2021-44228"],
            notes="Log4j vulnerability",
        ),
    ],

    bacnet_identity={
        "vendor_id": 71,
        "model_name": "WebCTRL Server",
        "device_instance": 0,
    },
))


# -----------------------------------------------------------------------------
# DELTA CONTROLS TEMPLATES
# -----------------------------------------------------------------------------

# Delta Controls enteliBUS Manager
_register_template(DeviceTemplate(
    id="delta_controls/entelibus/manager",
    vendor="Delta_Controls",
    vendor_family="enteliBUS",
    model="enteliBUS Manager",
    model_name="enteliBUS Manager",
    device_type="ahu_controller",
    description="Building automation controller for HVAC applications",

    oui_prefixes=["00:60:35", "00:50:C2"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 10.0,
        "max_ms": 120.0,
        "mean_ms": 40.0,
        "std_dev_ms": 20.0,
        "distribution": "gaussian",
    },

    supported_protocols=["bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="DCL{8ALPHANUM}",
        station_name_pattern="ahu-{location}-{seq}",
        vendor_short="DCL",
        model_short="EBUS",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.2",
            release_date=date(2023, 6, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    bacnet_identity={
        "vendor_id": 8,
        "model_name": "enteliBUS Manager",
        "device_instance": 0,
    },
))


# =============================================================================
# PHASE 1: NEW VENDOR TEMPLATES
# =============================================================================

# -----------------------------------------------------------------------------
# YOKOGAWA TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="yokogawa/centum-vp/fcu",
    vendor="Yokogawa",
    vendor_family="CENTUM VP",
    model="AFV10D",
    model_name="CENTUM VP Field Control Unit",
    device_type="dcs_controller",
    description="Field control unit for CENTUM VP distributed control system",

    oui_prefixes=["00:A0:64", "00:1E:62", "00:20:4A"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.0,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="YOK{2ALPHA}{8NUM}",
        station_name_pattern="dcs-fcu-{seq}",
        vendor_short="YOK",
        model_short="FCU",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R6.06",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R6.03",
            release_date=date(2022, 8, 20),
            cves=["CVE-2022-30997"],
        ),
        FirmwareVariant(
            version="R6.01",
            release_date=date(2021, 3, 10),
            cves=["CVE-2022-30997", "CVE-2021-27510"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Yokogawa Electric Corporation",
        "product_code": "AFV10D",
        "vendor_url": "http://www.yokogawa.com",
        "product_name": "CENTUM VP Field Control Unit",
    },
))


_register_template(DeviceTemplate(
    id="yokogawa/prosafe-rs/ssu",
    vendor="Yokogawa",
    vendor_family="ProSafe-RS",
    model="SSC60D",
    model_name="ProSafe-RS Safety Controller",
    device_type="safety_plc",
    description="Safety instrumented system controller for SIL3 applications",

    oui_prefixes=["00:A0:64", "00:1E:62"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="PSR{10NUM}",
        station_name_pattern="sis-{location}-{seq}",
        vendor_short="YOK",
        model_short="PSR",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R4.06",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="R4.03",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-30997"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Yokogawa Electric Corporation",
        "product_code": "SSC60D",
        "product_name": "ProSafe-RS Safety Controller",
    },
))


_register_template(DeviceTemplate(
    id="yokogawa/analyzer/gc8000",
    vendor="Yokogawa",
    vendor_family="GC8000",
    model="GC8000",
    model_name="GC8000 Gas Chromatograph",
    device_type="analyzer",
    description="Process gas chromatograph for natural gas and refinery applications",

    oui_prefixes=["00:A0:64", "00:1E:62", "00:20:4A"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="GC8K{10NUM}",
        station_name_pattern="gc-{location}-{seq}",
        vendor_short="YOK",
        model_short="GC8K",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.5",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.2",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-30997"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Yokogawa Electric Corporation",
        "product_code": "GC8000",
        "product_name": "GC8000 Gas Chromatograph",
    },
))


_register_template(DeviceTemplate(
    id="yokogawa/analyzer/tdls8000",
    vendor="Yokogawa",
    vendor_family="TDLS8000",
    model="TDLS8000",
    model_name="TDLS8000 Laser Analyzer",
    device_type="analyzer",
    description="Tunable diode laser spectrometer for gas analysis",

    oui_prefixes=["00:A0:64", "00:1E:62"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 60.0,
        "mean_ms": 15.0,
        "std_dev_ms": 10.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="TDLS{10NUM}",
        station_name_pattern="tdls-{location}-{seq}",
        vendor_short="YOK",
        model_short="TDLS",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.2",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.0",
            release_date=date(2022, 7, 20),
            cves=["CVE-2022-30997"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Yokogawa Electric Corporation",
        "product_code": "TDLS8000",
        "product_name": "TDLS8000 Laser Analyzer",
    },
))


_register_template(DeviceTemplate(
    id="yokogawa/transmitter/eja530a",
    vendor="Yokogawa",
    vendor_family="EJA-A Series",
    model="EJA530A",
    model_name="EJA530A Pressure Transmitter",
    device_type="transmitter",
    description="Digital differential pressure transmitter for process measurement",

    oui_prefixes=["00:A0:64", "00:1E:62"],

    tcp_stack={
        "ttl": 64,
        "window_size": 8192,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 40.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="EJA{10NUM}",
        station_name_pattern="pt-{location}-{seq}",
        vendor_short="YOK",
        model_short="EJA",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.0",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.5",
            release_date=date(2022, 5, 10),
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Yokogawa Electric Corporation",
        "product_code": "EJA530A",
        "product_name": "EJA530A Pressure Transmitter",
    },
))


_register_template(DeviceTemplate(
    id="yokogawa/analyzer/flxa402",
    vendor="Yokogawa",
    vendor_family="FLEXA Series",
    model="FLXA402",
    model_name="FLXA402 Multi-Parameter Analyzer",
    device_type="analyzer",
    description="Four-wire pH/ORP analyzer for water quality monitoring",

    oui_prefixes=["00:A0:64", "00:1E:62"],

    tcp_stack={
        "ttl": 64,
        "window_size": 8192,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 50.0,
        "mean_ms": 12.0,
        "std_dev_ms": 8.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="FLXA{10NUM}",
        station_name_pattern="ph-{location}-{seq}",
        vendor_short="YOK",
        model_short="FLXA",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.5",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.2",
            release_date=date(2022, 4, 15),
            cves=[],
        ),
    ],

    modbus_identity={
        "vendor_name": "Yokogawa Electric Corporation",
        "product_code": "FLXA402",
        "product_name": "FLXA402 Multi-Parameter Analyzer",
    },
))


# Yokogawa CENTUM VP Human Interface Station
_register_template(DeviceTemplate(
    id="yokogawa/centum-vp/his",
    vendor="Yokogawa",
    vendor_family="CENTUM VP",
    model="HIS",
    model_name="CENTUM VP Human Interface Station",
    device_type="hmi",
    description="Operator interface station for CENTUM VP DCS",

    oui_prefixes=["00:A0:64", "00:1E:62", "00:20:4A"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 12.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="YOK{2ALPHA}{8NUM}",
        station_name_pattern="his-{seq}",
        vendor_short="YOK",
        model_short="HIS",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R6.05",
            release_date=date(2023, 9, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],
))


# Yokogawa CENTUM VP Engineering Workstation
_register_template(DeviceTemplate(
    id="yokogawa/centum-vp/ews",
    vendor="Yokogawa",
    vendor_family="CENTUM VP",
    model="EWS",
    model_name="CENTUM VP Engineering Workstation",
    device_type="engineering_station",
    description="Engineering workstation for CENTUM VP configuration",

    oui_prefixes=["00:A0:64", "00:1E:62", "00:20:4A"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 150.0,
        "mean_ms": 40.0,
        "std_dev_ms": 20.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "opc_ua"],

    instance_rules=InstanceGenerationRules(
        serial_format="YOK{2ALPHA}{8NUM}",
        station_name_pattern="ews-{seq}",
        vendor_short="YOK",
        model_short="EWS",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R6.05",
            release_date=date(2023, 9, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],
))


# Yokogawa Exaopc OPC Server
_register_template(DeviceTemplate(
    id="yokogawa/exaopc/server",
    vendor="Yokogawa",
    vendor_family="Exaopc",
    model="Exaopc",
    model_name="Exaopc OPC Server",
    device_type="historian",
    description="OPC server and historian for CENTUM VP and ProSafe-RS",

    oui_prefixes=["00:A0:64", "00:1E:62", "00:20:4A"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 200.0,
        "mean_ms": 50.0,
        "std_dev_ms": 25.0,
        "distribution": "gaussian",
    },

    supported_protocols=["opc_ua", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="YOK{2ALPHA}{8NUM}",
        station_name_pattern="exaopc-{seq}",
        vendor_short="YOK",
        model_short="EXAOPC",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="R3.80",
            release_date=date(2023, 6, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],
))


# -----------------------------------------------------------------------------
# FANUC TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="fanuc/robot/r30ib-plus",
    vendor="Fanuc",
    vendor_family="Robot Controller",
    model="R-30iB Plus",
    model_name="R-30iB Plus Robot Controller",
    device_type="robot_controller",
    description="Latest generation robot controller with integrated motion control",

    oui_prefixes=["00:E0:E4", "00:E0:E5"],

    tcp_stack={
        "ttl": 128,  # Windows CE based
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "window_scaling": 8,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 20.0,
        "mean_ms": 4.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
    },

    supported_protocols=["fanuc", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="R30-{8HEX}",
        station_name_pattern="robot-{seq}",
        vendor_short="FAN",
        model_short="R30",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V9.40",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V9.30",
            release_date=date(2023, 5, 15),
            cves=["CVE-2023-24523"],
        ),
        FirmwareVariant(
            version="V9.10",
            release_date=date(2021, 9, 20),
            cves=["CVE-2023-24523", "CVE-2021-38296"],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 27,  # Fanuc
        "device_type": 21,  # Robot
        "product_code": 30,
        "state": 3,
    },
))


_register_template(DeviceTemplate(
    id="fanuc/cnc/0i-tf-plus",
    vendor="Fanuc",
    vendor_family="CNC",
    model="0i-TF Plus",
    model_name="Series 0i-TF Plus CNC",
    device_type="cnc_controller",
    description="High-performance CNC controller for turning and milling",

    oui_prefixes=["00:E0:E4", "00:E0:E5"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 12.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["fanuc", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="CNC-{10NUM}",
        station_name_pattern="cnc-{location}-{seq}",
        vendor_short="FAN",
        model_short="0iTF",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V34.2",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V33.0",
            release_date=date(2022, 7, 10),
            cves=["CVE-2023-24523"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Fanuc Corporation",
        "product_code": "0i-TF Plus",
        "product_name": "Series 0i-TF Plus CNC",
    },
))


# -----------------------------------------------------------------------------
# MOXA TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="moxa/iologik/e1210",
    vendor="Moxa",
    vendor_family="ioLogik E1200",
    model="ioLogik E1210",
    model_name="ioLogik E1210 Remote I/O",
    device_type="remote_io",
    description="16-channel digital input remote I/O with Modbus/TCP",

    oui_prefixes=["00:90:E8"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 30.0,
        "mean_ms": 5.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="TAIB{8NUM}",
        station_name_pattern="rio-{location}-{seq}",
        vendor_short="MOX",
        model_short="E1210",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.3",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.1",
            release_date=date(2022, 5, 20),
            cves=["CVE-2023-33237"],
        ),
        FirmwareVariant(
            version="V2.5",
            release_date=date(2020, 8, 10),
            cves=["CVE-2023-33237", "CVE-2020-17409"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Moxa Inc.",
        "product_code": "ioLogik E1210",
        "product_name": "ioLogik E1210 Remote I/O",
    },
))


_register_template(DeviceTemplate(
    id="moxa/switch/eds-408a",
    vendor="Moxa",
    vendor_family="EDS-400A",
    model="EDS-408A-MM-SC",
    model_name="EDS-408A Industrial Ethernet Switch",
    device_type="network_switch",
    description="8-port managed industrial Ethernet switch with fiber",

    oui_prefixes=["00:90:E8"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="MXS{10NUM}",
        station_name_pattern="sw-{location}-{seq}",
        vendor_short="MOX",
        model_short="EDS4",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.12",
            release_date=date(2024, 1, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.9",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-38457"],
        ),
        FirmwareVariant(
            version="V3.5",
            release_date=date(2020, 11, 20),
            cves=["CVE-2022-38457", "CVE-2020-27179"],
        ),
    ],

    snmp_identity={
        "sys_descr": "EDS-408A-MM-SC Managed Industrial Ethernet Switch",
        "sys_object_id": "1.3.6.1.4.1.8691.7.116",
    },
))


# -----------------------------------------------------------------------------
# CISCO INDUSTRIAL TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="cisco/ie3300/8t2s",
    vendor="Cisco",
    vendor_family="IE3300",
    model="IE-3300-8T2S",
    model_name="Catalyst IE3300 Rugged Switch",
    device_type="network_switch",
    description="8-port rugged industrial Ethernet switch with 2 SFP",

    oui_prefixes=["00:26:98", "00:1A:A1", "00:17:0E", "F8:C2:88", "3C:08:F6"],

    tcp_stack={
        "ttl": 64,  # IOS XE
        "window_size": 32768,
        "mss": 1460,
        "window_scaling": 5,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "lldp", "cdp"],

    instance_rules=InstanceGenerationRules(
        serial_format="FCW{8ALPHANUM}",
        station_name_pattern="ie3300-{location}-{seq}",
        vendor_short="CIS",
        model_short="IE33",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="17.12.02",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="17.9.04",
            release_date=date(2023, 6, 15),
            cves=["CVE-2023-20198"],
        ),
        FirmwareVariant(
            version="17.6.05",
            release_date=date(2022, 3, 20),
            cves=["CVE-2023-20198", "CVE-2022-20923"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Cisco IOS Software, IE3300 Software (IE3300-UNIVERSALK9-M)",
        "sys_object_id": "1.3.6.1.4.1.9.1.2824",
    },
))


_register_template(DeviceTemplate(
    id="cisco/ie4000/8gt4g",
    vendor="Cisco",
    vendor_family="IE4000",
    model="IE-4000-8GT4G-E",
    model_name="Catalyst IE4000 Industrial Ethernet Switch",
    device_type="network_switch",
    description="8x 10/100/1000 + 4x combo GE industrial managed switch",

    oui_prefixes=["00:26:98", "00:1A:A1", "00:17:0E", "F8:C2:88"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "window_scaling": 5,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 6.0,
        "mean_ms": 1.2,
        "std_dev_ms": 0.8,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "lldp", "cdp"],

    instance_rules=InstanceGenerationRules(
        serial_format="FCW{8ALPHANUM}",
        station_name_pattern="ie4000-{location}-{seq}",
        vendor_short="CIS",
        model_short="IE40",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="15.2(8)E",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="15.2(7)E6",
            release_date=date(2022, 9, 10),
            cves=["CVE-2022-20919"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Cisco IOS Software, IE4000 Software (IE4000-UNIVERSAL-M)",
        "sys_object_id": "1.3.6.1.4.1.9.1.2238",
    },
))


# -----------------------------------------------------------------------------
# CISCO CATALYST IE9300 RUGGED SERIES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="cisco/ie9320/24p4x",
    vendor="Cisco",
    vendor_family="IE9300",
    model="IE-9320-24P4X-E",
    model_name="Catalyst IE9320 Rugged Switch 24-Port PoE+ 10G",
    device_type="network_switch",
    description="24x GE PoE+ RJ45 + 4x 10G SFP+ industrial switch with Network Essentials",

    oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

    tcp_stack={
        "ttl": 64,  # IOS XE
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 5.0,
        "mean_ms": 1.0,
        "std_dev_ms": 0.6,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="FJC{8ALPHANUM}",
        station_name_pattern="ie9320-{location}-{seq}",
        vendor_short="CIS",
        model_short="IE93",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="17.15.01",
            release_date=date(2024, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="17.12.03",
            release_date=date(2024, 3, 15),
            cves=[],
        ),
        FirmwareVariant(
            version="17.9.05",
            release_date=date(2023, 9, 1),
            cves=["CVE-2023-20198"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
        "sys_object_id": "1.3.6.1.4.1.9.1.3054",
    },

    lldp_identity={
        "system_name": "IE-9320-24P4X",
        "system_description": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software",
        "chassis_id_subtype": 4,  # MAC address
        "port_id_subtype": 5,  # Interface name
        "capabilities": 0x0028,  # Switch + Bridge
    },

    cdp_identity={
        "device_id": "IE-9320-24P4X.local",
        "platform": "cisco IE-9320-24P4X-E",
        "software_version": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01",
        "capabilities": 0x29,  # Switch + IGMP + Router
        "port_id": "GigabitEthernet1/0/1",
        "native_vlan": 1,
        "duplex": 1,  # Full duplex
    },
))

_register_template(DeviceTemplate(
    id="cisco/ie9320/26s2c",
    vendor="Cisco",
    vendor_family="IE9300",
    model="IE-9320-26S2C-E",
    model_name="Catalyst IE9320 Rugged Switch 26-Port SFP",
    device_type="network_switch",
    description="22x GE SFP + 2x dual-media + 4x GE SFP industrial switch",

    oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

    tcp_stack={
        "ttl": 64,
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 5.0,
        "mean_ms": 1.0,
        "std_dev_ms": 0.6,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="FJC{8ALPHANUM}",
        station_name_pattern="ie9320-{location}-{seq}",
        vendor_short="CIS",
        model_short="IE93",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="17.15.01",
            release_date=date(2024, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="17.12.03",
            release_date=date(2024, 3, 15),
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
        "sys_object_id": "1.3.6.1.4.1.9.1.3052",
    },

    lldp_identity={
        "system_name": "IE-9320-26S2C",
        "system_description": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software",
        "chassis_id_subtype": 4,
        "port_id_subtype": 5,
        "capabilities": 0x0028,
    },

    cdp_identity={
        "device_id": "IE-9320-26S2C.local",
        "platform": "cisco IE-9320-26S2C-E",
        "software_version": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01",
        "capabilities": 0x29,
        "port_id": "GigabitEthernet1/0/1",
        "native_vlan": 1,
        "duplex": 1,
    },
))

_register_template(DeviceTemplate(
    id="cisco/ie9310/26s2c",
    vendor="Cisco",
    vendor_family="IE9300",
    model="IE-9310-26S2C-E",
    model_name="Catalyst IE9310 Rugged Switch 26-Port SFP",
    device_type="network_switch",
    description="22x GE SFP + 2x dual-media + 4x GE SFP base model industrial switch",

    oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

    tcp_stack={
        "ttl": 64,
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 5.0,
        "mean_ms": 1.0,
        "std_dev_ms": 0.6,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "lldp", "cdp"],

    instance_rules=InstanceGenerationRules(
        serial_format="FJC{8ALPHANUM}",
        station_name_pattern="ie9310-{location}-{seq}",
        vendor_short="CIS",
        model_short="IE93",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="17.15.01",
            release_date=date(2024, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="17.12.03",
            release_date=date(2024, 3, 15),
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
        "sys_object_id": "1.3.6.1.4.1.9.1.3050",
    },

    lldp_identity={
        "system_name": "IE-9310-26S2C",
        "system_description": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software",
        "chassis_id_subtype": 4,
        "port_id_subtype": 5,
        "capabilities": 0x0028,
    },

    cdp_identity={
        "device_id": "IE-9310-26S2C.local",
        "platform": "cisco IE-9310-26S2C-E",
        "software_version": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01",
        "capabilities": 0x29,
        "port_id": "GigabitEthernet1/0/1",
        "native_vlan": 1,
        "duplex": 1,
    },
))

_register_template(DeviceTemplate(
    id="cisco/ie9320/24t4x",
    vendor="Cisco",
    vendor_family="IE9300",
    model="IE-9320-24T4X-E",
    model_name="Catalyst IE9320 Rugged Switch 24-Port Copper 10G",
    device_type="network_switch",
    description="24x GE copper RJ45 + 4x 10G SFP+ industrial switch",

    oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

    tcp_stack={
        "ttl": 64,
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 5.0,
        "mean_ms": 1.0,
        "std_dev_ms": 0.6,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="FJC{8ALPHANUM}",
        station_name_pattern="ie9320-{location}-{seq}",
        vendor_short="CIS",
        model_short="IE93",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="17.15.01",
            release_date=date(2024, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="17.12.03",
            release_date=date(2024, 3, 15),
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
        "sys_object_id": "1.3.6.1.4.1.9.1.3055",
    },

    lldp_identity={
        "system_name": "IE-9320-24T4X",
        "system_description": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software",
        "chassis_id_subtype": 4,
        "port_id_subtype": 5,
        "capabilities": 0x0028,
    },

    cdp_identity={
        "device_id": "IE-9320-24T4X.local",
        "platform": "cisco IE-9320-24T4X-E",
        "software_version": "Cisco IOS Software [Cupertino], Catalyst IE9300 Software (IE9300-UNIVERSALK9-M), Version 17.15.01",
        "capabilities": 0x29,
        "port_id": "GigabitEthernet1/0/1",
        "native_vlan": 1,
        "duplex": 1,
    },
))


# -----------------------------------------------------------------------------
# CISCO CATALYST IE3500 RUGGED SERIES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="cisco/ie3500/8p3s",
    vendor="Cisco",
    vendor_family="IE3500",
    model="IE-3500-8P3S-E",
    model_name="Catalyst IE3500 Rugged Switch 8-Port PoE+",
    device_type="network_switch",
    description="8x GE PoE/PoE+ + 3x GE SFP compact industrial switch with 240W PoE budget",

    oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

    tcp_stack={
        "ttl": 64,  # IOS XE
        "window_size": 32768,
        "mss": 1460,
        "window_scaling": 5,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="FDO{8ALPHANUM}",
        station_name_pattern="ie3500-{location}-{seq}",
        vendor_short="CIS",
        model_short="IE35",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="17.15.01",
            release_date=date(2024, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="17.12.03",
            release_date=date(2024, 3, 15),
            cves=[],
        ),
        FirmwareVariant(
            version="17.9.05",
            release_date=date(2023, 9, 1),
            cves=["CVE-2023-20198"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
        "sys_object_id": "1.3.6.1.4.1.9.1.2960",
    },

    lldp_identity={
        "system_name": "IE-3500-8P3S",
        "system_description": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software",
        "chassis_id_subtype": 4,
        "port_id_subtype": 5,
        "capabilities": 0x0028,
    },

    cdp_identity={
        "device_id": "IE-3500-8P3S.local",
        "platform": "cisco IE-3500-8P3S-E",
        "software_version": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01",
        "capabilities": 0x29,
        "port_id": "GigabitEthernet1/0/1",
        "native_vlan": 1,
        "duplex": 1,
    },
))

_register_template(DeviceTemplate(
    id="cisco/ie3500/8t3s",
    vendor="Cisco",
    vendor_family="IE3500",
    model="IE-3500-8T3S-E",
    model_name="Catalyst IE3500 Rugged Switch 8-Port Copper",
    device_type="network_switch",
    description="8x GE copper + 3x GE SFP compact industrial switch (non-PoE)",

    oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "window_scaling": 5,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "lldp", "cdp"],

    instance_rules=InstanceGenerationRules(
        serial_format="FDO{8ALPHANUM}",
        station_name_pattern="ie3500-{location}-{seq}",
        vendor_short="CIS",
        model_short="IE35",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="17.15.01",
            release_date=date(2024, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="17.12.03",
            release_date=date(2024, 3, 15),
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
        "sys_object_id": "1.3.6.1.4.1.9.1.2958",
    },

    lldp_identity={
        "system_name": "IE-3500-8T3S",
        "system_description": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software",
        "chassis_id_subtype": 4,
        "port_id_subtype": 5,
        "capabilities": 0x0028,
    },

    cdp_identity={
        "device_id": "IE-3500-8T3S.local",
        "platform": "cisco IE-3500-8T3S-E",
        "software_version": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01",
        "capabilities": 0x29,
        "port_id": "GigabitEthernet1/0/1",
        "native_vlan": 1,
        "duplex": 1,
    },
))

_register_template(DeviceTemplate(
    id="cisco/ie3500/8u3x",
    vendor="Cisco",
    vendor_family="IE3500",
    model="IE-3500-8U3X-E",
    model_name="Catalyst IE3500 Rugged Switch 8-Port 4PPoE 10G",
    device_type="network_switch",
    description="8x GE PoE/PoE+/4PPoE + 3x 10G SFP+ high-power industrial switch with 480W PoE budget",

    oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

    tcp_stack={
        "ttl": 64,
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 7,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 6.0,
        "mean_ms": 1.2,
        "std_dev_ms": 0.8,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="FDO{8ALPHANUM}",
        station_name_pattern="ie3500-{location}-{seq}",
        vendor_short="CIS",
        model_short="IE35",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="17.15.01",
            release_date=date(2024, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="17.12.03",
            release_date=date(2024, 3, 15),
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
        "sys_object_id": "1.3.6.1.4.1.9.1.2964",
    },

    lldp_identity={
        "system_name": "IE-3500-8U3X",
        "system_description": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software",
        "chassis_id_subtype": 4,
        "port_id_subtype": 5,
        "capabilities": 0x0028,
    },

    cdp_identity={
        "device_id": "IE-3500-8U3X.local",
        "platform": "cisco IE-3500-8U3X-E",
        "software_version": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01",
        "capabilities": 0x29,
        "port_id": "TenGigabitEthernet1/0/1",
        "native_vlan": 1,
        "duplex": 1,
    },
))

_register_template(DeviceTemplate(
    id="cisco/ie3505/8p3s",
    vendor="Cisco",
    vendor_family="IE3500",
    model="IE-3505-8P3S-E",
    model_name="Catalyst IE3505 Rugged Switch with HSR/PRP",
    device_type="network_switch",
    description="8x GE PoE+ + 3x GE SFP industrial switch with HSR/PRP/DLR redundancy",

    oui_prefixes=["00:26:98", "00:1A:A1", "F8:C2:88", "3C:08:F6", "70:7D:B9"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "window_scaling": 5,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "lldp", "cdp", "profinet", "ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="FDO{8ALPHANUM}",
        station_name_pattern="ie3505-{location}-{seq}",
        vendor_short="CIS",
        model_short="IE35",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="17.15.01",
            release_date=date(2024, 11, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="17.12.03",
            release_date=date(2024, 3, 15),
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01, RELEASE SOFTWARE",
        "sys_object_id": "1.3.6.1.4.1.9.1.2966",
    },

    lldp_identity={
        "system_name": "IE-3505-8P3S",
        "system_description": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software",
        "chassis_id_subtype": 4,
        "port_id_subtype": 5,
        "capabilities": 0x0028,
    },

    cdp_identity={
        "device_id": "IE-3505-8P3S.local",
        "platform": "cisco IE-3505-8P3S-E",
        "software_version": "Cisco IOS Software [Cupertino], Catalyst IE3500 Software (IE3500-UNIVERSALK9-M), Version 17.15.01",
        "capabilities": 0x29,
        "port_id": "GigabitEthernet1/0/1",
        "native_vlan": 1,
        "duplex": 1,
    },
))


# -----------------------------------------------------------------------------
# ENDRESS+HAUSER TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="endress-hauser/promag/400",
    vendor="Endress+Hauser",
    vendor_family="Promag",
    model="Promag 400",
    model_name="Promag 400 Electromagnetic Flowmeter",
    device_type="flow_meter",
    description="Electromagnetic flowmeter for process measurement applications",

    oui_prefixes=["00:0E:B3", "00:50:C2"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 10.0,
        "std_dev_ms": 6.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="EH{2ALPHA}{10NUM}",
        station_name_pattern="fit-{location}-{seq}",
        vendor_short="EH",
        model_short="PM400",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V01.05.00",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V01.03.00",
            release_date=date(2022, 6, 20),
            cves=["CVE-2022-35578"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Endress+Hauser",
        "product_code": "Promag 400",
        "product_name": "Electromagnetic Flowmeter",
    },
))


_register_template(DeviceTemplate(
    id="endress-hauser/liquiline/cm442",
    vendor="Endress+Hauser",
    vendor_family="Liquiline",
    model="CM442",
    model_name="Liquiline CM442 Transmitter",
    device_type="analyzer",
    description="Multi-parameter transmitter for liquid analysis",

    oui_prefixes=["00:0E:B3", "00:50:C2"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 80.0,
        "mean_ms": 15.0,
        "std_dev_ms": 10.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="CM44{8NUM}",
        station_name_pattern="ait-{location}-{seq}",
        vendor_short="EH",
        model_short="CM442",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V01.08.00",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V01.06.00",
            release_date=date(2022, 9, 15),
            cves=["CVE-2022-35578"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Endress+Hauser",
        "product_code": "CM442",
        "product_name": "Liquiline Multiparameter Transmitter",
    },
))


# -----------------------------------------------------------------------------
# VAISALA TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="vaisala/rwis/500",
    vendor="Vaisala",
    vendor_family="RWIS",
    model="RWIS500",
    model_name="Road Weather Information System",
    device_type="weather_station",
    description="Road weather station for transportation applications",

    oui_prefixes=["00:0E:C3"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 20.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="VWS{10NUM}",
        station_name_pattern="rwis-{location}-{seq}",
        vendor_short="VAI",
        model_short="RW500",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.5.0",
            release_date=date(2024, 1, 25),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.3.0",
            release_date=date(2022, 7, 10),
            cves=["CVE-2022-38408"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Vaisala RWIS500 Road Weather Station",
        "sys_object_id": "1.3.6.1.4.1.10395.1.1",
    },
))


# -----------------------------------------------------------------------------
# B&R AUTOMATION TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="br-automation/x20/cp1586",
    vendor="B&R",
    vendor_family="X20",
    model="X20CP1586",
    model_name="X20 Compact PLC",
    device_type="plc",
    description="High-performance compact PLC with integrated I/O",

    oui_prefixes=["00:60:65"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 12.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "opc_ua", "powerlink"],

    instance_rules=InstanceGenerationRules(
        serial_format="BR{2ALPHA}{10NUM}",
        station_name_pattern="{role}-x20-{seq}",
        vendor_short="BR",
        model_short="X20",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.20",
            release_date=date(2024, 2, 5),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.10",
            release_date=date(2022, 10, 15),
            cves=["CVE-2023-1617"],
        ),
        FirmwareVariant(
            version="V4.91",
            release_date=date(2021, 5, 20),
            cves=["CVE-2023-1617", "CVE-2021-22275"],
        ),
    ],

    modbus_identity={
        "vendor_name": "B&R Industrial Automation",
        "product_code": "X20CP1586",
        "product_name": "X20 Compact PLC",
    },
))


# -----------------------------------------------------------------------------
# KUKA TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="kuka/robot/krc4",
    vendor="KUKA",
    vendor_family="KR C",
    model="KR C4",
    model_name="KR C4 Robot Controller",
    device_type="robot_controller",
    description="8th generation robot controller for KUKA industrial robots",

    oui_prefixes=["00:1A:28", "00:1F:29"],

    tcp_stack={
        "ttl": 128,  # Windows based
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.8,
        "max_ms": 25.0,
        "mean_ms": 5.0,
        "std_dev_ms": 3.5,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip", "profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="KRC4-{8HEX}",
        station_name_pattern="robot-{location}-{seq}",
        vendor_short="KUK",
        model_short="KRC4",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V8.6.8",
            release_date=date(2024, 1, 30),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V8.5.10",
            release_date=date(2022, 8, 20),
            cves=["CVE-2022-43560"],
        ),
        FirmwareVariant(
            version="V8.3.5",
            release_date=date(2020, 11, 15),
            cves=["CVE-2022-43560", "CVE-2020-10292"],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 270,  # KUKA
        "device_type": 21,  # Robot
        "product_code": 4,
        "state": 3,
    },

    profinet_identity={
        "vendor_id": 0x0115,  # KUKA
        "device_id": 0x0004,
        "device_role": 1,
        "im0_manufacturer": "KUKA Roboter GmbH",
        "im0_order_id": "KR C4",
    },
))


# -----------------------------------------------------------------------------
# HIRSCHMANN TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="hirschmann/switch/rs20-0800",
    vendor="Hirschmann",
    vendor_family="RS20",
    model="RS20-0800M2M2SDAE",
    model_name="RS20 Industrial Ethernet Switch",
    device_type="network_switch",
    description="8-port managed rail switch with fiber options",

    oui_prefixes=["00:80:63"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="HIM{10NUM}",
        station_name_pattern="sw-{location}-{seq}",
        vendor_short="HIR",
        model_short="RS20",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V09.1.00",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V09.0.06",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-34136"],
        ),
    ],

    snmp_identity={
        "sys_descr": "RS20-0800M2M2SDAE Managed Industrial Ethernet Switch",
        "sys_object_id": "1.3.6.1.4.1.248.11.1.1",
    },
))


# -----------------------------------------------------------------------------
# ADVANTECH TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="advantech/adam/6052",
    vendor="Advantech",
    vendor_family="ADAM-6000",
    model="ADAM-6052",
    model_name="ADAM-6052 Digital I/O Module",
    device_type="remote_io",
    description="16-channel digital I/O module with Modbus/TCP",

    oui_prefixes=["00:D0:C9"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 40.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="ADAM{8NUM}",
        station_name_pattern="rio-{location}-{seq}",
        vendor_short="ADV",
        model_short="A6052",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.05",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.02",
            release_date=date(2022, 4, 20),
            cves=["CVE-2022-29497"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Advantech Co., Ltd.",
        "product_code": "ADAM-6052",
        "product_name": "Digital I/O Module",
    },
))


# =============================================================================
# PHASE 2: EXPANDED DEVICE TYPES FOR EXISTING VENDORS
# =============================================================================

# -----------------------------------------------------------------------------
# GE PROTECTION RELAYS
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="ge/multilin/850",
    vendor="GE",
    vendor_family="Multilin",
    model="850",
    model_name="Multilin 850 Feeder Protection System",
    device_type="protection_relay",
    description="Advanced feeder protection and bay control relay",

    oui_prefixes=["00:14:49", "00:60:B0"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 10.0,
        "mean_ms": 2.0,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "iec61850", "dnp3"],

    instance_rules=InstanceGenerationRules(
        serial_format="GE850{8NUM}",
        station_name_pattern="relay-850-{seq}",
        vendor_short="GE",
        model_short="M850",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V8.00",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V7.90",
            release_date=date(2022, 9, 15),
            cves=["CVE-2022-21805"],
        ),
        FirmwareVariant(
            version="V7.60",
            release_date=date(2020, 6, 20),
            cves=["CVE-2022-21805", "CVE-2020-12009"],
        ),
    ],

    modbus_identity={
        "vendor_name": "GE Grid Solutions",
        "product_code": "850",
        "product_name": "Multilin 850 Feeder Protection",
    },
))


_register_template(DeviceTemplate(
    id="ge/multilin/f650",
    vendor="GE",
    vendor_family="Multilin",
    model="F650",
    model_name="Multilin F650 Digital Bay Controller",
    device_type="protection_relay",
    description="Digital bay controller with comprehensive protection",

    oui_prefixes=["00:14:49", "00:60:B0"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 12.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.5,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "dnp3"],

    instance_rules=InstanceGenerationRules(
        serial_format="GEF65{8NUM}",
        station_name_pattern="relay-f650-{seq}",
        vendor_short="GE",
        model_short="F650",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.40",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V6.20",
            release_date=date(2022, 5, 10),
            cves=["CVE-2022-21805"],
        ),
    ],

    modbus_identity={
        "vendor_name": "GE Grid Solutions",
        "product_code": "F650",
        "product_name": "Multilin F650 Bay Controller",
    },
))


_register_template(DeviceTemplate(
    id="ge/multilin/t60",
    vendor="GE",
    vendor_family="Multilin",
    model="T60",
    model_name="Multilin T60 Transformer Protection",
    device_type="protection_relay",
    description="Transformer protection relay with comprehensive protection functions",

    oui_prefixes=["00:14:49", "00:60:B0", "1C:39:47"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 7.0,
        "mean_ms": 1.5,
        "std_dev_ms": 0.9,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "iec61850"],

    instance_rules=InstanceGenerationRules(
        serial_format="GET60{8NUM}",
        station_name_pattern="relay-t60-{seq}",
        vendor_short="GE",
        model_short="T60",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V8.2",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V8.0",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-21805"],
        ),
        FirmwareVariant(
            version="V7.6",
            release_date=date(2020, 11, 10),
            cves=["CVE-2022-21805", "CVE-2020-6949"],
        ),
    ],

    modbus_identity={
        "vendor_name": "GE Grid Solutions",
        "product_code": "T60",
        "product_name": "Multilin T60 Transformer Protection",
    },
))


# -----------------------------------------------------------------------------
# ABB PROTECTION RELAYS
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="abb/relion/ref615",
    vendor="ABB",
    vendor_family="Relion",
    model="REF615",
    model_name="REF615 Feeder Protection Relay",
    device_type="protection_relay",
    description="Feeder protection and control relay for distribution",

    oui_prefixes=["00:21:99", "00:24:2B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "iec61850"],

    instance_rules=InstanceGenerationRules(
        serial_format="ABB615{8NUM}",
        station_name_pattern="relay-ref615-{seq}",
        vendor_short="ABB",
        model_short="R615",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.1 FP2",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.0 FP3",
            release_date=date(2022, 8, 20),
            cves=["CVE-2022-28613"],
        ),
        FirmwareVariant(
            version="V4.1 FP2",
            release_date=date(2020, 10, 10),
            cves=["CVE-2022-28613", "CVE-2020-8481"],
        ),
    ],

    modbus_identity={
        "vendor_name": "ABB",
        "product_code": "REF615",
        "product_name": "Relion REF615 Feeder Protection",
    },
))


_register_template(DeviceTemplate(
    id="abb/relion/rex640",
    vendor="ABB",
    vendor_family="Relion",
    model="REX640",
    model_name="REX640 Protection and Control IED",
    device_type="protection_relay",
    description="Next-generation protection and control for utility applications",

    oui_prefixes=["00:21:99", "00:24:2B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 6.0,
        "mean_ms": 1.2,
        "std_dev_ms": 0.8,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "iec61850", "iec104"],

    instance_rules=InstanceGenerationRules(
        serial_format="ABB640{8NUM}",
        station_name_pattern="relay-rex640-{seq}",
        vendor_short="ABB",
        model_short="R640",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.2.1",
            release_date=date(2024, 1, 25),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.1.0",
            release_date=date(2022, 10, 15),
            cves=["CVE-2023-2184"],
        ),
    ],

    modbus_identity={
        "vendor_name": "ABB",
        "product_code": "REX640",
        "product_name": "Relion REX640 Protection IED",
    },
))


# -----------------------------------------------------------------------------
# SIEMENS PROTECTION RELAYS
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="siemens/siprotec/7sj85",
    vendor="Siemens",
    vendor_family="SIPROTEC 5",
    model="7SJ85",
    model_name="SIPROTEC 7SJ85 Overcurrent Protection",
    device_type="protection_relay",
    description="Overcurrent and motor protection relay",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "iec61850"],

    instance_rules=InstanceGenerationRules(
        serial_format="SIE7SJ{8NUM}",
        station_name_pattern="relay-7sj85-{seq}",
        vendor_short="SIE",
        model_short="7SJ85",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V9.40",
            release_date=date(2024, 2, 5),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V9.20",
            release_date=date(2022, 7, 15),
            cves=["CVE-2022-32528"],
        ),
        FirmwareVariant(
            version="V8.30",
            release_date=date(2020, 12, 10),
            cves=["CVE-2022-32528", "CVE-2020-15795"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "7SJ85",
        "product_name": "SIPROTEC 7SJ85 Overcurrent Protection",
    },
))


_register_template(DeviceTemplate(
    id="siemens/siprotec/7sd87",
    vendor="Siemens",
    vendor_family="SIPROTEC 5",
    model="7SD87",
    model_name="SIPROTEC 7SD87 Differential Protection",
    device_type="protection_relay",
    description="Line differential protection relay",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 6.0,
        "mean_ms": 1.2,
        "std_dev_ms": 0.8,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "iec61850"],

    instance_rules=InstanceGenerationRules(
        serial_format="SIE7SD{8NUM}",
        station_name_pattern="relay-7sd87-{seq}",
        vendor_short="SIE",
        model_short="7SD87",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V9.40",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V9.10",
            release_date=date(2022, 5, 20),
            cves=["CVE-2022-32528"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "7SD87",
        "product_name": "SIPROTEC 7SD87 Differential Protection",
    },
))


_register_template(DeviceTemplate(
    id="siemens/siprotec/7sl87",
    vendor="Siemens",
    vendor_family="SIPROTEC 5",
    model="7SL87",
    model_name="SIPROTEC 7SL87 Line Differential",
    device_type="protection_relay",
    description="Line differential protection relay for transmission lines",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 5.0,
        "mean_ms": 1.0,
        "std_dev_ms": 0.6,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "iec61850"],

    instance_rules=InstanceGenerationRules(
        serial_format="SIE7SL{8NUM}",
        station_name_pattern="relay-7sl87-{seq}",
        vendor_short="SIE",
        model_short="7SL87",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V9.40",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V9.20",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-32528"],
        ),
        FirmwareVariant(
            version="V8.30",
            release_date=date(2021, 1, 10),
            cves=["CVE-2022-32528", "CVE-2020-15795"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "7SL87",
        "product_name": "SIPROTEC 7SL87 Line Differential",
    },
))


_register_template(DeviceTemplate(
    id="siemens/siprotec/7ut87",
    vendor="Siemens",
    vendor_family="SIPROTEC 5",
    model="7UT87",
    model_name="SIPROTEC 7UT87 Transformer Differential",
    device_type="protection_relay",
    description="Transformer differential protection relay",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 5.0,
        "mean_ms": 1.0,
        "std_dev_ms": 0.6,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "iec61850"],

    instance_rules=InstanceGenerationRules(
        serial_format="SIE7UT{8NUM}",
        station_name_pattern="relay-7ut87-{seq}",
        vendor_short="SIE",
        model_short="7UT87",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V9.40",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V9.20",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-32528"],
        ),
        FirmwareVariant(
            version="V8.30",
            release_date=date(2021, 1, 10),
            cves=["CVE-2022-32528", "CVE-2020-15795"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "7UT87",
        "product_name": "SIPROTEC 7UT87 Transformer Differential",
    },
))


# -----------------------------------------------------------------------------
# DRIVES/VFDs
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="abb/drives/acs580",
    vendor="ABB",
    vendor_family="ACS580",
    model="ACS580-01-073A-4",
    model_name="ACS580 General Purpose Drive",
    device_type="drive",
    description="General purpose variable frequency drive with built-in features",

    oui_prefixes=["00:21:99", "00:24:2B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 10.0,
        "std_dev_ms": 7.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="ACS5{10NUM}",
        station_name_pattern="vfd-{location}-{seq}",
        vendor_short="ABB",
        model_short="ACS5",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.10",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.05",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-26006"],
        ),
    ],

    modbus_identity={
        "vendor_name": "ABB",
        "product_code": "ACS580-01-073A-4",
        "product_name": "ACS580 General Purpose Drive",
    },

    profinet_identity={
        "vendor_id": 0x0037,
        "device_id": 0x0580,
        "device_role": 1,
        "im0_manufacturer": "ABB",
        "im0_order_id": "ACS580-01-073A-4",
    },
))


_register_template(DeviceTemplate(
    id="siemens/sinamics/g120",
    vendor="Siemens",
    vendor_family="SINAMICS",
    model="G120",
    model_name="SINAMICS G120 Drive",
    device_type="drive",
    description="Modular drive system for a wide range of applications",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.5,
        "max_ms": 40.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["profinet", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="G120-{8HEX}",
        station_name_pattern="vfd-{model_short}-{seq}",
        vendor_short="SIE",
        model_short="G120",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.8 SP7",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.7 SP11",
            release_date=date(2022, 9, 20),
            cves=["CVE-2022-45092"],
        ),
        FirmwareVariant(
            version="V4.7 SP5",
            release_date=date(2021, 4, 15),
            cves=["CVE-2022-45092", "CVE-2021-31337"],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0120,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "SINAMICS G120",
    },

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "SINAMICS G120",
        "product_name": "SINAMICS G120 Drive",
    },
))


_register_template(DeviceTemplate(
    id="rockwell/powerflex/525",
    vendor="Rockwell",
    vendor_family="PowerFlex",
    model="25B-D030N104",
    model_name="PowerFlex 525 AC Drive",
    device_type="drive",
    description="Compact AC drive with embedded Ethernet/IP",

    oui_prefixes=["00:00:BC", "00:1D:9C"],

    tcp_stack={
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 35.0,
        "mean_ms": 7.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["ethernet_ip"],

    instance_rules=InstanceGenerationRules(
        serial_format="PF525{8NUM}",
        station_name_pattern="vfd-pf525-{seq}",
        vendor_short="ROC",
        model_short="PF525",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V7.001",
            release_date=date(2024, 1, 25),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V6.003",
            release_date=date(2022, 7, 10),
            cves=["CVE-2022-3166"],
        ),
    ],

    ethernet_ip_identity={
        "vendor_id": 1,
        "device_type": 2,  # AC Drive
        "product_code": 525,
        "state": 3,
    },
))


# -----------------------------------------------------------------------------
# ADDITIONAL HMIs
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="siemens/hmi/tp1500-comfort",
    vendor="Siemens",
    vendor_family="SIMATIC HMI",
    model="6AV2 124-0QC02-0AX1",
    model_name="TP1500 Comfort Panel",
    device_type="hmi",
    description="15-inch Comfort Panel with widescreen display",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 120.0,
        "mean_ms": 30.0,
        "std_dev_ms": 20.0,
        "distribution": "lognormal",
    },

    supported_protocols=["profinet", "s7comm"],

    instance_rules=InstanceGenerationRules(
        serial_format="S V-{8HEX}",
        station_name_pattern="hmi-{location}-{seq}",
        vendor_short="SIE",
        model_short="TP15",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V19.0.0.0",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V18.0.0.0",
            release_date=date(2022, 10, 20),
            cves=["CVE-2022-40227"],
        ),
    ],

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x040F,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "6AV2 124-0QC02-0AX1",
    },
))


_register_template(DeviceTemplate(
    id="schneider/hmi/hmist6700",
    vendor="Schneider",
    vendor_family="Harmony",
    model="HMIST6700",
    model_name="Harmony STU 6700 HMI",
    device_type="hmi",
    description="15-inch touchscreen HMI for demanding applications",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 80.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="HMIST{8NUM}",
        station_name_pattern="hmi-{location}-{seq}",
        vendor_short="SCH",
        model_short="ST67",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.0.0",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.2.0",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-42972"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "HMIST6700",
        "product_name": "Harmony STU 6700 HMI",
    },
))


_register_template(DeviceTemplate(
    id="abb/hmi/cp620",
    vendor="ABB",
    vendor_family="CP600",
    model="CP620",
    model_name="CP620 Control Panel",
    device_type="hmi",
    description="6-inch touch panel for PLC integration",

    oui_prefixes=["00:21:99", "00:24:2B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 4.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="ABB-CP{8NUM}",
        station_name_pattern="hmi-{location}-{seq}",
        vendor_short="ABB",
        model_short="CP62",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V1.80",
            release_date=date(2024, 1, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V1.65",
            release_date=date(2022, 5, 20),
            cves=["CVE-2022-26006"],
        ),
    ],

    modbus_identity={
        "vendor_name": "ABB",
        "product_code": "CP620",
        "product_name": "CP620 Control Panel",
    },
))


# -----------------------------------------------------------------------------
# RTUs (Water/Oil & Gas)
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="schneider/tbox/ms-cpu32",
    vendor="Schneider",
    vendor_family="TBox",
    model="TBox MS-CPU32",
    model_name="TBox MS RTU",
    device_type="rtu",
    description="High-performance RTU for SCADA applications",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 60.0,
        "mean_ms": 15.0,
        "std_dev_ms": 10.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp", "dnp3"],

    instance_rules=InstanceGenerationRules(
        serial_format="TBOX{10NUM}",
        station_name_pattern="rtu-{location}-{seq}",
        vendor_short="SCH",
        model_short="TBOX",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.3.0",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.1.0",
            release_date=date(2022, 8, 20),
            cves=["CVE-2022-45788"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "TBox MS-CPU32",
        "product_name": "TBox MS RTU",
    },
))


_register_template(DeviceTemplate(
    id="schneider/ion/8650",
    vendor="Schneider",
    vendor_family="ION",
    model="ION8650",
    model_name="ION8650 Power Quality Meter",
    device_type="power_meter",
    description="High-accuracy power quality meter for utility revenue metering",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 10.0,
        "std_dev_ms": 7.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "dnp3"],

    instance_rules=InstanceGenerationRules(
        serial_format="ION86{8NUM}",
        station_name_pattern="meter-{location}-{seq}",
        vendor_short="SCH",
        model_short="ION86",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.005",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.100",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-22810"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "ION8650",
        "product_name": "ION8650 Power Quality Meter",
    },
))


_register_template(DeviceTemplate(
    id="schneider/scadapack/350",
    vendor="Schneider",
    vendor_family="SCADAPack",
    model="SCADAPack 350",
    model_name="SCADAPack 350 RTU",
    device_type="rtu",
    description="Compact RTU for remote monitoring and control",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 60.0,
        "mean_ms": 15.0,
        "std_dev_ms": 10.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp", "dnp3"],

    instance_rules=InstanceGenerationRules(
        serial_format="SP350{8NUM}",
        station_name_pattern="rtu-{location}-{seq}",
        vendor_short="SCH",
        model_short="SP350",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V8.5.0",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V8.2.0",
            release_date=date(2022, 7, 20),
            cves=["CVE-2022-45788"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "SCADAPack-350",
        "product_name": "SCADAPack 350 RTU",
    },
))


_register_template(DeviceTemplate(
    id="schneider/tbox/lt2",
    vendor="Schneider",
    vendor_family="TBox",
    model="TBox LT2",
    model_name="TBox LT2 Lite RTU",
    device_type="rtu",
    description="Compact RTU for small-scale remote monitoring",

    oui_prefixes=["00:00:54", "00:80:F4"],

    tcp_stack={
        "ttl": 64,
        "window_size": 8192,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 80.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp", "dnp3"],

    instance_rules=InstanceGenerationRules(
        serial_format="TBLT2{8NUM}",
        station_name_pattern="rtu-{location}-{seq}",
        vendor_short="SCH",
        model_short="TBLT2",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.8.0",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.5.0",
            release_date=date(2022, 5, 20),
            cves=["CVE-2022-45788"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Schneider Electric",
        "product_code": "TBox-LT2",
        "product_name": "TBox LT2 Lite RTU",
    },
))


_register_template(DeviceTemplate(
    id="abb/rtu/rtu560",
    vendor="ABB",
    vendor_family="RTU560",
    model="RTU560",
    model_name="RTU560 Remote Terminal Unit",
    device_type="rtu",
    description="Modular RTU for power utility automation",

    oui_prefixes=["00:21:99", "00:24:2B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 40.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "iec104"],

    instance_rules=InstanceGenerationRules(
        serial_format="RTU56{8NUM}",
        station_name_pattern="rtu-{location}-{seq}",
        vendor_short="ABB",
        model_short="R560",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V12.4.3",
            release_date=date(2024, 1, 25),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V12.2.0",
            release_date=date(2022, 6, 10),
            cves=["CVE-2022-26007"],
        ),
    ],

    modbus_identity={
        "vendor_name": "ABB",
        "product_code": "RTU560",
        "product_name": "RTU560 Remote Terminal Unit",
    },
))


_register_template(DeviceTemplate(
    id="honeywell/rtu/2020",
    vendor="Honeywell",
    vendor_family="Enraf",
    model="RTU2020",
    model_name="RTU2020 Remote Terminal Unit",
    device_type="rtu",
    description="Remote terminal unit for tank gauging and control",

    oui_prefixes=["00:60:35", "00:D0:36"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 80.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp", "dnp3"],

    instance_rules=InstanceGenerationRules(
        serial_format="HW-RTU{8NUM}",
        station_name_pattern="rtu-{location}-{seq}",
        vendor_short="HON",
        model_short="R2020",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.6.0",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.4.0",
            release_date=date(2022, 7, 15),
            cves=["CVE-2022-30317"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Honeywell International Inc.",
        "product_code": "RTU2020",
        "product_name": "RTU2020 Remote Terminal Unit",
    },
))


# =============================================================================
# PHASE 3: BUILDING AUTOMATION VERTICAL
# =============================================================================

# -----------------------------------------------------------------------------
# TRANE TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="trane/tracer/sc-plus",
    vendor="Trane",
    vendor_family="Tracer",
    model="SC+",
    model_name="Tracer SC+ System Controller",
    device_type="bms_controller",
    description="Building automation system controller",

    oui_prefixes=["00:10:91", "00:1E:C0"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 80.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="TSC{10NUM}",
        station_name_pattern="bms-{location}-{seq}",
        vendor_short="TRA",
        model_short="SC+",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.20",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V6.10",
            release_date=date(2022, 7, 20),
            cves=["CVE-2022-21661"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 2,  # Trane
        "device_type": "Building Controller",
        "model_name": "Tracer SC+",
    },

    modbus_identity={
        "vendor_name": "Trane Technologies",
        "product_code": "Tracer SC+",
        "product_name": "Tracer SC+ System Controller",
    },
))


_register_template(DeviceTemplate(
    id="trane/thermostat/xl950",
    vendor="Trane",
    vendor_family="XL",
    model="XL950",
    model_name="XL950 ComfortLink II Thermostat",
    device_type="thermostat",
    description="Wi-Fi enabled smart thermostat with touchscreen",

    oui_prefixes=["00:10:91", "00:1E:C0"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 150.0,
        "mean_ms": 40.0,
        "std_dev_ms": 25.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="XL95{8NUM}",
        station_name_pattern="tstat-{location}-{seq}",
        vendor_short="TRA",
        model_short="XL95",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.1.0",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.8.0",
            release_date=date(2022, 5, 15),
            cves=["CVE-2022-24089"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 2,
        "device_type": "Thermostat",
        "model_name": "XL950",
    },
))


# -----------------------------------------------------------------------------
# CARRIER TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="carrier/i-vu/pro",
    vendor="Carrier",
    vendor_family="i-Vu",
    model="i-Vu Pro",
    model_name="i-Vu Pro Building Automation Server",
    device_type="bms_server",
    description="Web-based building automation system",

    oui_prefixes=["00:E0:C9", "00:25:B0"],

    tcp_stack={
        "ttl": 64,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 60.0,
        "mean_ms": 15.0,
        "std_dev_ms": 10.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="IVU-{10NUM}",
        station_name_pattern="bas-{location}-{seq}",
        vendor_short="CAR",
        model_short="IVU",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V8.0.0.1",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V7.0.0.15",
            release_date=date(2022, 8, 10),
            cves=["CVE-2022-30246"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 56,  # Carrier
        "device_type": "Automation Server",
        "model_name": "i-Vu Pro",
    },
))


_register_template(DeviceTemplate(
    id="carrier/thermostat/33cs2pp",
    vendor="Carrier",
    vendor_family="Performance",
    model="33CS2PP",
    model_name="33CS2PP Programmable Thermostat",
    device_type="thermostat",
    description="Commercial programmable thermostat with BACnet",

    oui_prefixes=["00:E0:C9", "00:25:B0"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 120.0,
        "mean_ms": 30.0,
        "std_dev_ms": 20.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="CS2P{8NUM}",
        station_name_pattern="tstat-{location}-{seq}",
        vendor_short="CAR",
        model_short="CS2P",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.15",
            release_date=date(2024, 2, 5),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.10",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-30246"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 56,
        "device_type": "Thermostat",
        "model_name": "33CS2PP",
    },
))


# -----------------------------------------------------------------------------
# DISTECH CONTROLS TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="distech/eclypse/bos-8",
    vendor="Distech Controls",
    vendor_family="ECLYPSE",
    model="EC-BOS-8",
    model_name="ECLYPSE Connected BACnet/IP Controller",
    device_type="vav_controller",
    description="Connected controller for VAV box and equipment control",

    oui_prefixes=["00:0F:A3"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 12.0,
        "std_dev_ms": 8.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="ECB8{10NUM}",
        station_name_pattern="vav-{location}-{seq}",
        vendor_short="DIS",
        model_short="ECB8",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V1.6.0",
            release_date=date(2024, 1, 25),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V1.4.5",
            release_date=date(2022, 7, 10),
            cves=["CVE-2022-40619"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 285,  # Distech Controls
        "device_type": "VAV Controller",
        "model_name": "EC-BOS-8",
    },
))


# -----------------------------------------------------------------------------
# DELTA CONTROLS TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="delta-controls/entelibus/vav",
    vendor="Delta Controls",
    vendor_family="enteliBUS",
    model="enteliBUS",
    model_name="enteliBUS Building Controller",
    device_type="bms_controller",
    description="Modular building automation controller",

    oui_prefixes=["00:08:B6"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 60.0,
        "mean_ms": 15.0,
        "std_dev_ms": 10.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="DCTL{10NUM}",
        station_name_pattern="bms-{location}-{seq}",
        vendor_short="DEL",
        model_short="EBUS",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.6.0",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.4.0",
            release_date=date(2022, 9, 15),
            cves=["CVE-2022-44028"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 8,  # Delta Controls
        "device_type": "Building Controller",
        "model_name": "enteliBUS",
    },
))


# -----------------------------------------------------------------------------
# AUTOMATED LOGIC TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="automated-logic/webctrl/server",
    vendor="Automated Logic",
    vendor_family="WebCTRL",
    model="WebCTRL",
    model_name="WebCTRL Building Automation System",
    device_type="bms_server",
    description="Enterprise building automation software platform",

    oui_prefixes=["00:E0:C9", "00:0E:70"],

    tcp_stack={
        "ttl": 64,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 12.0,
        "std_dev_ms": 8.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="WCTL{10NUM}",
        station_name_pattern="bas-{location}-{seq}",
        vendor_short="ALC",
        model_short="WCTL",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V8.0",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V7.0",
            release_date=date(2022, 5, 20),
            cves=["CVE-2022-30261"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 108,  # Automated Logic
        "device_type": "Automation Server",
        "model_name": "WebCTRL",
    },
))


# -----------------------------------------------------------------------------
# HONEYWELL BUILDING AUTOMATION TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="honeywell/spyder/vav",
    vendor="Honeywell",
    vendor_family="Spyder",
    model="PUB6438S",
    model_name="Spyder Unitary Controller",
    device_type="vav_controller",
    description="Programmable VAV controller with BACnet",

    oui_prefixes=["00:60:35", "00:D0:36", "F4:4E:05"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 80.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="SPY{10NUM}",
        station_name_pattern="vav-{location}-{seq}",
        vendor_short="HON",
        model_short="SPY",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.0.3",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.8.0",
            release_date=date(2022, 6, 10),
            cves=["CVE-2022-30317"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 7,  # Honeywell
        "device_type": "VAV Controller",
        "model_name": "Spyder PUB6438S",
    },

    modbus_identity={
        "vendor_name": "Honeywell International Inc.",
        "product_code": "PUB6438S",
        "product_name": "Spyder Unitary Controller",
    },
))


# -----------------------------------------------------------------------------
# SIEMENS BUILDING AUTOMATION TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="siemens/desigo/cc",
    vendor="Siemens",
    vendor_family="Desigo",
    model="Desigo CC",
    model_name="Desigo CC Management Platform",
    device_type="bms_server",
    description="Integrated building management platform",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 128,  # Windows based
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 40.0,
        "mean_ms": 10.0,
        "std_dev_ms": 6.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="DCC{10NUM}",
        station_name_pattern="bas-{location}-{seq}",
        vendor_short="SIE",
        model_short="DCC",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.0",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.0 SP1",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-39158"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 10,  # Siemens Building Technologies
        "device_type": "Management Platform",
        "model_name": "Desigo CC",
    },
))


_register_template(DeviceTemplate(
    id="siemens/desigo/dxr2",
    vendor="Siemens",
    vendor_family="Desigo",
    model="DXR2.E12",
    model_name="Desigo DXR2 Room Controller",
    device_type="room_controller",
    description="Compact room automation controller for HVAC",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 12.0,
        "std_dev_ms": 8.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="DXR{10NUM}",
        station_name_pattern="room-{location}-{seq}",
        vendor_short="SIE",
        model_short="DXR2",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.3",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.0",
            release_date=date(2022, 6, 20),
            cves=["CVE-2022-39158"],
        ),
        FirmwareVariant(
            version="V3.5",
            release_date=date(2020, 10, 10),
            cves=["CVE-2022-39158", "CVE-2020-15796"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 10,
        "device_type": "Room Controller",
        "model_name": "DXR2.E12",
    },

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "DXR2.E12",
        "product_name": "Desigo DXR2 Room Controller",
    },
))


# -----------------------------------------------------------------------------
# CAREL TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="carel/pco5/plus",
    vendor="Carel",
    vendor_family="pCO",
    model="pCO5+",
    model_name="pCO5+ HVAC Controller",
    device_type="hvac_controller",
    description="Programmable controller for HVAC applications",

    oui_prefixes=["00:1C:7E"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 60.0,
        "mean_ms": 15.0,
        "std_dev_ms": 10.0,
        "distribution": "lognormal",
    },

    supported_protocols=["modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="PCO5{10NUM}",
        station_name_pattern="hvac-{location}-{seq}",
        vendor_short="CAR",
        model_short="PCO5",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.5.0",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.2.0",
            release_date=date(2022, 7, 15),
            cves=["CVE-2022-37953"],
        ),
    ],

    modbus_identity={
        "vendor_name": "Carel Industries",
        "product_code": "pCO5+",
        "product_name": "pCO5+ HVAC Controller",
    },
))


# -----------------------------------------------------------------------------
# NOTIFIER (FIRE ALARM) TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="notifier/nfs2/3030",
    vendor="Notifier",
    vendor_family="NFS2",
    model="NFS2-3030",
    model_name="NFS2-3030 Fire Alarm Control Panel",
    device_type="fire_panel",
    description="Intelligent fire alarm control panel",

    oui_prefixes=["00:60:35", "00:D0:36"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 80.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="NFS{10NUM}",
        station_name_pattern="facp-{location}-{seq}",
        vendor_short="NOT",
        model_short="NFS3",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.2.0",
            release_date=date(2024, 1, 25),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.0.0",
            release_date=date(2022, 6, 20),
            cves=["CVE-2022-39144"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 188,  # Notifier
        "device_type": "Fire Alarm Panel",
        "model_name": "NFS2-3030",
    },
))


# -----------------------------------------------------------------------------
# LUTRON (LIGHTING) TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="lutron/quantum/hub",
    vendor="Lutron",
    vendor_family="Quantum",
    model="QSN-4T16-S",
    model_name="Quantum Total Light Management",
    device_type="lighting_controller",
    description="Enterprise lighting control processor",

    oui_prefixes=["00:09:23", "00:15:B2"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 50.0,
        "mean_ms": 12.0,
        "std_dev_ms": 8.0,
        "distribution": "lognormal",
    },

    supported_protocols=["bacnet"],

    instance_rules=InstanceGenerationRules(
        serial_format="LUT{10NUM}",
        station_name_pattern="ltg-{location}-{seq}",
        vendor_short="LUT",
        model_short="QTM",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V15.0",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V14.2",
            release_date=date(2022, 8, 10),
            cves=["CVE-2022-41666"],
        ),
    ],

    bacnet_identity={
        "vendor_id": 115,  # Lutron
        "device_type": "Lighting Controller",
        "model_name": "Quantum",
    },
))


# =============================================================================
# PHASE 4: TRANSPORTATION/ITS VERTICAL
# =============================================================================

# -----------------------------------------------------------------------------
# SIEMENS ITS TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="siemens-its/m60/atc",
    vendor="Siemens ITS",
    vendor_family="M-Series",
    model="M60",
    model_name="M60 ATC Traffic Controller",
    device_type="traffic_controller",
    description="Advanced Transportation Controller with NTCIP support",

    oui_prefixes=["00:0E:8C", "00:30:5C"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 40.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "lognormal",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="M60{10NUM}",
        station_name_pattern="tsc-{location}-{seq}",
        vendor_short="SIE",
        model_short="M60",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V10.3.0",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V10.1.0",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-35586"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Siemens M60 ATC Traffic Signal Controller",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",
    },
))


_register_template(DeviceTemplate(
    id="siemens-its/cp-8000/central",
    vendor="Siemens ITS",
    vendor_family="CP-8000",
    model="CP-8000",
    model_name="CP-8000 Central Controller",
    device_type="traffic_controller",
    description="Central traffic management controller for arterial coordination",

    oui_prefixes=["00:0E:8C", "00:30:5C", "00:1B:1B"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 30.0,
        "mean_ms": 6.0,
        "std_dev_ms": 4.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "modbus_tcp"],

    instance_rules=InstanceGenerationRules(
        serial_format="CP8K{10NUM}",
        station_name_pattern="central-{location}-{seq}",
        vendor_short="SIE",
        model_short="CP8K",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V12.5.0",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V12.2.0",
            release_date=date(2022, 7, 15),
            cves=["CVE-2022-35586"],
        ),
        FirmwareVariant(
            version="V11.0.0",
            release_date=date(2020, 11, 10),
            cves=["CVE-2022-35586", "CVE-2020-10055"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Siemens CP-8000 Central Traffic Controller",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.5",
    },

    modbus_identity={
        "vendor_name": "Siemens AG",
        "product_code": "CP-8000",
        "product_name": "CP-8000 Central Controller",
    },
))


_register_template(DeviceTemplate(
    id="siemens/scalance/xm400",
    vendor="Siemens",
    vendor_family="SCALANCE",
    model="XM416-4C",
    model_name="SCALANCE XM416-4C Managed Switch",
    device_type="network_switch",
    description="Core layer 3 managed industrial Ethernet switch",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "window_scaling": 7,
    },

    response_timing={
        "min_ms": 0.3,
        "max_ms": 8.0,
        "mean_ms": 1.5,
        "std_dev_ms": 1.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="XM4{10ALPHANUM}",
        station_name_pattern="sw-core-{seq}",
        vendor_short="SIE",
        model_short="XM416",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V6.6",
            release_date=date(2024, 2, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V6.4",
            release_date=date(2022, 9, 10),
            cves=["CVE-2022-46142"],
        ),
        FirmwareVariant(
            version="V6.2",
            release_date=date(2021, 4, 15),
            cves=["CVE-2022-46142", "CVE-2021-25669"],
        ),
    ],

    snmp_identity={
        "sys_descr": "SCALANCE XM416-4C Managed Switch",
        "sys_object_id": "1.3.6.1.4.1.4329.6.3.1.6",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0C01,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "XM416-4C",
    },
))


_register_template(DeviceTemplate(
    id="siemens/scalance/x200",
    vendor="Siemens",
    vendor_family="SCALANCE",
    model="X208",
    model_name="SCALANCE X208 Unmanaged Switch",
    device_type="network_switch",
    description="Compact 8-port unmanaged industrial Ethernet switch",

    oui_prefixes=["00:0E:8C", "00:1B:1B", "00:1C:06"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 0.2,
        "max_ms": 5.0,
        "mean_ms": 1.0,
        "std_dev_ms": 0.5,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp", "profinet"],

    instance_rules=InstanceGenerationRules(
        serial_format="X208{10ALPHANUM}",
        station_name_pattern="sw-cab-{seq}",
        vendor_short="SIE",
        model_short="X208",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.5",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.2",
            release_date=date(2022, 5, 15),
            cves=["CVE-2022-46142"],
        ),
    ],

    snmp_identity={
        "sys_descr": "SCALANCE X208 Unmanaged Switch",
        "sys_object_id": "1.3.6.1.4.1.4329.6.3.1.2",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0C02,
        "device_role": 1,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "X208",
    },
))


# -----------------------------------------------------------------------------
# MCCAIN TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="mccain/2070/atc",
    vendor="McCain",
    vendor_family="2070",
    model="2070 ATC",
    model_name="2070 ATC Traffic Controller",
    device_type="traffic_controller",
    description="Type 2070 Advanced Transportation Controller",

    oui_prefixes=["00:0E:2E"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 50.0,
        "mean_ms": 10.0,
        "std_dev_ms": 7.0,
        "distribution": "lognormal",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="MC2070{8NUM}",
        station_name_pattern="tsc-{location}-{seq}",
        vendor_short="MCC",
        model_short="2070",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V3.2.0",
            release_date=date(2024, 2, 5),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V3.0.0",
            release_date=date(2022, 7, 20),
            cves=["CVE-2022-35586"],
        ),
    ],

    snmp_identity={
        "sys_descr": "McCain 2070 ATC Traffic Signal Controller",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.1",
    },
))


# McCain 170E Detector Rack
_register_template(DeviceTemplate(
    id="mccain/170e/detector",
    vendor="McCain",
    vendor_family="170E",
    model="170E",
    model_name="170E Detector Rack",
    device_type="detector_rack",
    description="170E cabinet detector rack for vehicle detection",

    oui_prefixes=["00:50:C2", "00:17:61"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 5.0,
        "max_ms": 100.0,
        "mean_ms": 30.0,
        "std_dev_ms": 15.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="170E{6NUM}",
        station_name_pattern="det-{location}-{seq}",
        vendor_short="MCC",
        model_short="170E",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.5",
            release_date=date(2023, 3, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],

    snmp_identity={
        "sys_descr": "McCain 170E Detector Rack",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.6",
    },
))


# -----------------------------------------------------------------------------
# DAKTRONICS TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="daktronics/venus/1500",
    vendor="Daktronics",
    vendor_family="Venus",
    model="Venus 1500",
    model_name="Venus 1500 DMS Controller",
    device_type="dms",
    description="Dynamic Message Sign controller for transportation",

    oui_prefixes=["00:0E:63"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 80.0,
        "mean_ms": 20.0,
        "std_dev_ms": 12.0,
        "distribution": "lognormal",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="VNS15{8NUM}",
        station_name_pattern="dms-{location}-{seq}",
        vendor_short="DAK",
        model_short="V1500",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V8.3.0",
            release_date=date(2024, 1, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V8.1.0",
            release_date=date(2022, 5, 20),
            cves=["CVE-2022-30619"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Daktronics Venus 1500 Dynamic Message Sign",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.3",
    },
))


_register_template(DeviceTemplate(
    id="daktronics/venus/7000",
    vendor="Daktronics",
    vendor_family="Venus",
    model="Venus 7000",
    model_name="Venus 7000 Large DMS Controller",
    device_type="dms",
    description="Large format dynamic message sign controller",

    oui_prefixes=["00:0E:63"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="VNS70{8NUM}",
        station_name_pattern="dms-{location}-{seq}",
        vendor_short="DAK",
        model_short="V7000",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V12.1.0",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V11.5.0",
            release_date=date(2022, 8, 10),
            cves=["CVE-2022-30619"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Daktronics Venus 7000 Large Format DMS",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.3",
    },
))


# -----------------------------------------------------------------------------
# WAVETRONIX TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="wavetronix/smartsensor/hd",
    vendor="Wavetronix",
    vendor_family="SmartSensor",
    model="SmartSensor HD",
    model_name="SmartSensor HD Radar Detector",
    device_type="radar_detector",
    description="High-definition radar vehicle detection sensor",

    oui_prefixes=["00:0F:B5"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 40.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "lognormal",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="SSHD{10NUM}",
        station_name_pattern="det-{location}-{seq}",
        vendor_short="WVT",
        model_short="SSHD",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V7.5.0",
            release_date=date(2024, 1, 25),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V7.2.0",
            release_date=date(2022, 6, 15),
            cves=["CVE-2022-30620"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Wavetronix SmartSensor HD Radar Detector",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.5",
    },
))


_register_template(DeviceTemplate(
    id="wavetronix/smartsensor/advance",
    vendor="Wavetronix",
    vendor_family="SmartSensor",
    model="SmartSensor Advance",
    model_name="SmartSensor Advance Vehicle Classifier",
    device_type="radar_detector",
    description="Advanced radar sensor with vehicle classification capability",

    oui_prefixes=["00:15:2D"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.5,
        "max_ms": 40.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="SSA{10NUM}",
        station_name_pattern="radar-adv-{location}-{seq}",
        vendor_short="WAV",
        model_short="SSA",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.5.0",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.2.0",
            release_date=date(2022, 7, 15),
            cves=["CVE-2022-30620"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Wavetronix SmartSensor Advance Vehicle Classifier",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.5.1",
    },
))


# -----------------------------------------------------------------------------
# FLIR TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="flir/trafione/sensor",
    vendor="FLIR",
    vendor_family="TrafiOne",
    model="TrafiOne",
    model_name="TrafiOne Thermal Sensor",
    device_type="thermal_sensor",
    description="Thermal imaging sensor for traffic detection",

    oui_prefixes=["00:40:7F"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 30.0,
        "mean_ms": 6.0,
        "std_dev_ms": 4.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="TF1{10NUM}",
        station_name_pattern="therm-{location}-{seq}",
        vendor_short="FLR",
        model_short="TF1",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.8.0",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.5.0",
            release_date=date(2022, 7, 20),
            cves=["CVE-2022-37061"],
        ),
    ],

    snmp_identity={
        "sys_descr": "FLIR TrafiOne Thermal Traffic Sensor",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.5",
    },
))


# -----------------------------------------------------------------------------
# Q-FREE TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="qfree/rsu/5000",
    vendor="Q-Free",
    vendor_family="RSU",
    model="RSU 5000",
    model_name="RSU 5000 Roadside Unit",
    device_type="toll_rsu",
    description="DSRC roadside unit for tolling and V2X",

    oui_prefixes=["00:1E:A5"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 15.0,
        "mean_ms": 3.0,
        "std_dev_ms": 2.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="RSU5{10NUM}",
        station_name_pattern="rsu-{location}-{seq}",
        vendor_short="QFR",
        model_short="RSU5",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V4.2.0",
            release_date=date(2024, 1, 30),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V4.0.0",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-36324"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Q-Free RSU 5000 Roadside Unit",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.6",
    },
))


# -----------------------------------------------------------------------------
# KAPSCH TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="kapsch/tcs/2000",
    vendor="Kapsch",
    vendor_family="TCS",
    model="TCS 2000",
    model_name="TCS 2000 Toll Controller",
    device_type="toll_controller",
    description="Central toll collection system controller",

    oui_prefixes=["00:1B:21"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 30.0,
        "mean_ms": 6.0,
        "std_dev_ms": 4.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="KAP{10NUM}",
        station_name_pattern="toll-{location}-{seq}",
        vendor_short="KAP",
        model_short="TCS2",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.4.0",
            release_date=date(2024, 2, 5),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.2.0",
            release_date=date(2022, 9, 10),
            cves=["CVE-2022-37064"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Kapsch TCS 2000 Toll Collection System",
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.6",
    },
))


# -----------------------------------------------------------------------------
# AXIS COMMUNICATIONS TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="axis/camera/p1455-le",
    vendor="Axis",
    vendor_family="P-Series",
    model="P1455-LE",
    model_name="AXIS P1455-LE Network Camera",
    device_type="camera",
    description="Outdoor bullet camera for traffic monitoring",

    oui_prefixes=["00:40:8C", "AC:CC:8E", "B8:A4:4F"],

    tcp_stack={
        "ttl": 64,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "window_scaling": 7,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 20.0,
        "mean_ms": 4.0,
        "std_dev_ms": 3.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="ACCC8E{6HEX}",
        station_name_pattern="cam-{location}-{seq}",
        vendor_short="AXI",
        model_short="P1455",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V11.6.94",
            release_date=date(2024, 1, 20),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V11.3.64",
            release_date=date(2022, 7, 15),
            cves=["CVE-2022-37065"],
        ),
    ],

    snmp_identity={
        "sys_descr": "AXIS P1455-LE Network Camera",
        "sys_object_id": "1.3.6.1.4.1.368.1.1",
    },
))


_register_template(DeviceTemplate(
    id="axis/camera/p1448-le",
    vendor="Axis",
    vendor_family="P Series",
    model="P1448-LE",
    model_name="AXIS P1448-LE Network Camera",
    device_type="ip_camera",
    description="4K outdoor network camera with IR illumination",

    oui_prefixes=["00:40:8C", "AC:CC:8E", "B8:A4:4F"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "window_scaling": 7,
    },

    response_timing={
        "min_ms": 0.5,
        "max_ms": 25.0,
        "mean_ms": 5.0,
        "std_dev_ms": 3.5,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="ACCC8E{6HEX}",
        station_name_pattern="cam-{location}-{seq}",
        vendor_short="AXI",
        model_short="P1448",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V11.8.92",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V11.5.64",
            release_date=date(2022, 8, 15),
            cves=["CVE-2022-37065"],
        ),
    ],

    snmp_identity={
        "sys_descr": "AXIS P1448-LE Network Camera",
        "sys_object_id": "1.3.6.1.4.1.368.1.1",
    },
))


_register_template(DeviceTemplate(
    id="hikvision/camera/anpr",
    vendor="Hikvision",
    vendor_family="DeepinView",
    model="DS-2CD7A26G0/P",
    model_name="DS-2CD7A26G0/P ANPR Camera",
    device_type="anpr_camera",
    description="2MP ANPR camera with deep learning license plate recognition",

    oui_prefixes=["54:C4:15", "C0:56:E3", "44:19:B6", "BC:AD:28"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 40.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="HIK{10ALPHANUM}",
        station_name_pattern="anpr-{location}-{seq}",
        vendor_short="HIK",
        model_short="ANPR",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V5.7.14",
            release_date=date(2024, 2, 10),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V5.6.5",
            release_date=date(2022, 9, 20),
            cves=["CVE-2022-28173"],
        ),
        FirmwareVariant(
            version="V5.5.0",
            release_date=date(2021, 4, 15),
            cves=["CVE-2022-28173", "CVE-2021-36260"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Hikvision DS-2CD7A26G0/P ANPR Camera",
        "sys_object_id": "1.3.6.1.4.1.39165.1.1",
    },
))


# -----------------------------------------------------------------------------
# PELCO TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="pelco/spectra/enhanced",
    vendor="Pelco",
    vendor_family="Spectra",
    model="SD436-PG-E1",
    model_name="Spectra Enhanced PTZ Camera",
    device_type="ptz_camera",
    description="High-speed PTZ dome camera for surveillance",

    oui_prefixes=["00:80:F4", "64:3A:EA"],  # Schneider Electric (Pelco parent)

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 40.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["snmp"],

    instance_rules=InstanceGenerationRules(
        serial_format="PEL{10NUM}",
        station_name_pattern="ptz-{location}-{seq}",
        vendor_short="PEL",
        model_short="SD43",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V2.8.3",
            release_date=date(2024, 2, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
        FirmwareVariant(
            version="V2.6.0",
            release_date=date(2022, 6, 20),
            cves=["CVE-2022-36341"],
        ),
    ],

    snmp_identity={
        "sys_descr": "Pelco Spectra Enhanced PTZ Camera",
        "sys_object_id": "1.3.6.1.4.1.17685.1.1.1",  # Pelco enterprise OID
    },
))


# -----------------------------------------------------------------------------
# KEPWARE / PTC TEMPLATES
# -----------------------------------------------------------------------------

_register_template(DeviceTemplate(
    id="kepware/kepserverex/gateway",
    vendor="Kepware",
    vendor_family="KEPServerEX",
    model="KEPServerEX",
    model_name="KEPServerEX OPC UA Gateway",
    device_type="gateway",
    description="OPC UA gateway for multi-protocol industrial connectivity",

    oui_prefixes=[],  # Software runs on standard PCs

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 1.0,
        "max_ms": 50.0,
        "mean_ms": 10.0,
        "std_dev_ms": 8.0,
        "distribution": "lognormal",
    },

    supported_protocols=["opc_ua", "modbus_tcp", "ethernet_ip", "s7comm"],

    opc_ua_identity={
        "application_name": "Kepware KEPServerEX",
        "application_uri": "urn:localhost:KEPServerEX",
        "product_uri": "http://www.kepware.com/kepserverex",
        "manufacturer_name": "Kepware Technologies",
        "product_name": "KEPServerEX",
        "software_version": "6.14.263.0",
        "build_number": "263",
        "build_date": "2023-09-15T12:00:00Z",
    },

    modbus_identity={
        "vendor_name": "Kepware Technologies",
        "product_code": "KEPServerEX",
        "major_minor_revision": "6.14",
        "vendor_url": "http://www.kepware.com",
        "product_name": "KEPServerEX OPC Server",
        "model_name": "OPC UA Gateway",
    },

    ethernet_ip_identity={
        "vendor_id": 1,  # Generic
        "device_type": 12,  # Communications Adapter
        "product_code": 614,
        "revision_major": 6,
        "revision_minor": 14,
        "serial_number": 0x4B455001,
        "product_name": "KEPServerEX EtherNet/IP Driver",
        "state": 3,
    },

    s7_identity={
        "order_code": "KEPServerEX-S7",
        "module_type": "Siemens S7 Driver",
        "firmware_version": "6.14",
        "hardware_version": "N/A",
    },

    instance_rules=InstanceGenerationRules(
        serial_format="KEP-{8HEX}",
        station_name_pattern="gw-opc-{seq}",
        vendor_short="KEP",
        model_short="KEPE",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="6.14",
            release_date=date(2023, 9, 15),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],
))


# -----------------------------------------------------------------------------
# SIEMENS ENGINEERING AND WINCC UNIFIED TEMPLATES
# -----------------------------------------------------------------------------

# Siemens TIA Portal Engineering Station
_register_template(DeviceTemplate(
    id="siemens/tia/portal",
    vendor="Siemens",
    vendor_family="SIMATIC",
    model="TIA Portal",
    model_name="TIA Portal Engineering Station",
    device_type="engineering_station",
    description="Engineering and programming station for Siemens PLCs",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 128,
        "window_size": 65535,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 10.0,
        "max_ms": 200.0,
        "mean_ms": 50.0,
        "std_dev_ms": 30.0,
        "distribution": "lognormal",
    },

    supported_protocols=["s7comm", "profinet"],

    s7_identity={
        "order_code": "6ES7822-1AA08-0YA5",
        "module_type": "STEP 7 Professional",
        "firmware_version": "V18.0",
        "hardware_version": "N/A",
    },

    profinet_identity={
        "vendor_id": 0x002A,
        "device_id": 0x0800,
        "device_type": "Engineering Station",
        "station_name": "eng-tia",
        "device_role": 0,
        "im0_manufacturer": "Siemens AG",
        "im0_order_id": "TIA Portal V18",
        "im0_hw_revision": 1,
        "im0_sw_revision": "V18.0",
    },

    instance_rules=InstanceGenerationRules(
        serial_format="TIA-{6HEX}",
        station_name_pattern="eng-tia-{seq}",
        vendor_short="SIE",
        model_short="TIA",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V18.0",
            release_date=date(2023, 10, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],
))


# Siemens WinCC Unified
_register_template(DeviceTemplate(
    id="siemens/wincc/unified",
    vendor="Siemens",
    vendor_family="WinCC",
    model="WinCC Unified",
    model_name="WinCC Unified Comfort Panel",
    device_type="hmi",
    description="New generation HMI with OPC UA support",

    oui_prefixes=["00:0E:8C", "00:1B:1B"],

    tcp_stack={
        "ttl": 64,
        "window_size": 32768,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": True,
    },

    response_timing={
        "min_ms": 3.0,
        "max_ms": 100.0,
        "mean_ms": 25.0,
        "std_dev_ms": 15.0,
        "distribution": "lognormal",
    },

    supported_protocols=["s7comm", "opc_ua"],

    s7_identity={
        "order_code": "6AV2128-3GB06-0AX1",
        "module_type": "WinCC Unified Comfort Panel",
        "firmware_version": "V18.0",
        "hardware_version": "V1",
    },

    opc_ua_identity={
        "application_name": "Siemens SIMATIC WinCC Unified",
        "application_uri": "urn:Siemens:SIMATIC:WinCC:Unified",
        "product_uri": "http://www.siemens.com/simatic-wincc-unified",
        "manufacturer_name": "Siemens AG",
        "product_name": "SIMATIC WinCC Unified",
        "software_version": "18.0.0",
        "build_number": "V18.0",
        "build_date": "2023-06-01T12:00:00Z",
    },

    instance_rules=InstanceGenerationRules(
        serial_format="WU-{6HEX}",
        station_name_pattern="hmi-wu-{seq}",
        vendor_short="SIE",
        model_short="WCCU",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="V18.0",
            release_date=date(2023, 10, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],
))


# -----------------------------------------------------------------------------
# HMS INDUSTRIAL NETWORKS TEMPLATES
# -----------------------------------------------------------------------------

# HMS Anybus X-gateway
_register_template(DeviceTemplate(
    id="hms/anybus/xgateway",
    vendor="HMS",
    vendor_family="Anybus",
    model="Anybus X-gateway",
    model_name="Anybus X-gateway Protocol Converter",
    device_type="gateway",
    description="Multi-protocol industrial gateway",

    oui_prefixes=["00:30:11"],

    tcp_stack={
        "ttl": 64,
        "window_size": 16384,
        "mss": 1460,
        "sack_permitted": True,
        "timestamps_enabled": False,
    },

    response_timing={
        "min_ms": 2.0,
        "max_ms": 30.0,
        "mean_ms": 8.0,
        "std_dev_ms": 5.0,
        "distribution": "gaussian",
    },

    supported_protocols=["modbus_tcp", "ethernet_ip", "profinet"],

    modbus_identity={
        "vendor_name": "HMS Industrial Networks",
        "product_code": "AB7634",
        "major_minor_revision": "2.30",
        "vendor_url": "http://www.anybus.com",
        "product_name": "Anybus X-gateway Modbus TCP",
        "model_name": "Protocol Gateway",
    },

    ethernet_ip_identity={
        "vendor_id": 283,
        "device_type": 12,
        "product_code": 7634,
        "revision_major": 2,
        "revision_minor": 30,
        "serial_number": 0x484D5301,
        "product_name": "Anybus X-gateway EtherNet/IP",
        "state": 3,
    },

    profinet_identity={
        "vendor_id": 0x0128,
        "device_id": 0x0100,
        "device_type": "Anybus X-gateway PROFINET",
        "station_name": "anybus-xgw",
        "device_role": 1,
        "im0_manufacturer": "HMS Industrial Networks",
        "im0_order_id": "AB7634",
        "im0_hw_revision": 1,
        "im0_sw_revision": "V2.30",
    },

    instance_rules=InstanceGenerationRules(
        serial_format="HMS-{6HEX}",
        station_name_pattern="gw-proto-{seq}",
        vendor_short="HMS",
        model_short="ABXG",
    ),

    firmware_variants=[
        FirmwareVariant(
            version="2.30",
            release_date=date(2023, 6, 1),
            is_latest=True,
            is_default=True,
            cves=[],
        ),
    ],
))


# =============================================================================
# Library Access Functions
# =============================================================================


def get_all_templates() -> list[DeviceTemplate]:
    """Get all registered device templates."""
    return list(DEVICE_TEMPLATES.values())


def get_template_by_id(template_id: str) -> DeviceTemplate | None:
    """Get a device template by its ID."""
    return DEVICE_TEMPLATES.get(template_id)


def get_templates_by_vendor(vendor: str) -> list[DeviceTemplate]:
    """Get all templates for a specific vendor."""
    vendor_lower = vendor.lower()
    return [t for t in DEVICE_TEMPLATES.values() if t.vendor.lower() == vendor_lower]


def get_templates_by_device_type(device_type: str) -> list[DeviceTemplate]:
    """Get all templates for a specific device type."""
    return [t for t in DEVICE_TEMPLATES.values() if t.device_type == device_type]


def get_templates_with_cves() -> list[DeviceTemplate]:
    """Get all templates that have vulnerable firmware variants."""
    return [t for t in DEVICE_TEMPLATES.values() if t.get_vulnerable_firmwares()]


def get_template_count() -> int:
    """Get total number of registered templates."""
    return len(DEVICE_TEMPLATES)


def get_total_firmware_variants() -> int:
    """Get total number of firmware variants across all templates."""
    return sum(len(t.firmware_variants) for t in DEVICE_TEMPLATES.values())


def get_total_cves() -> int:
    """Get total number of unique CVEs across all firmware variants."""
    cves = set()
    for template in DEVICE_TEMPLATES.values():
        for fw in template.firmware_variants:
            cves.update(fw.cves)
    return len(cves)


def generate_device_instance(
    template_id: str,
    firmware_version: str | None = None,
    station_name: str | None = None,
    serial_number: str | None = None,
    mac_address: str | None = None,
    ip_address: str | None = None,
    location: str | None = None,
    sequence: int = 1,
    existing_serials: set[str] | None = None,
    existing_names: set[str] | None = None,
) -> DeviceInstance | None:
    """Generate a device instance from a template.

    Args:
        template_id: Template ID to use
        firmware_version: Specific firmware version (or None for default)
        station_name: Override station name (or None to generate)
        serial_number: Override serial number (or None to generate)
        mac_address: MAC address (usually from IP management)
        ip_address: IP address (from IP management)
        location: Location hint for station name generation
        sequence: Sequence number for this device type
        existing_serials: Set of already-used serial numbers
        existing_names: Set of already-used station names

    Returns:
        DeviceInstance or None if template not found
    """
    template = get_template_by_id(template_id)
    if not template:
        return None

    # Get firmware variant
    if firmware_version:
        firmware = template.get_firmware_by_version(firmware_version)
    else:
        firmware = template.get_default_firmware()

    if not firmware:
        return None

    # Generate or use provided serial number
    if serial_number:
        final_serial = serial_number
    elif template.instance_rules:
        final_serial = generate_serial_number(
            template.instance_rules.serial_format,
            existing_serials
        )
    else:
        final_serial = generate_serial_number("{10ALPHANUM}", existing_serials)

    # Generate or use provided station name
    if station_name:
        final_name = station_name
    elif template.instance_rules:
        final_name = generate_station_name(
            template.instance_rules.station_name_pattern,
            role=template.device_type,
            vendor_short=template.instance_rules.vendor_short,
            model_short=template.instance_rules.model_short,
            sequence=sequence,
            location=location,
            existing_names=existing_names,
        )
    else:
        final_name = f"device-{sequence:03d}"

    # Generate MAC if not provided
    if not mac_address and template.oui_prefixes:
        import random
        oui = random.choice(template.oui_prefixes)
        suffix = ':'.join(f'{random.randint(0, 255):02X}' for _ in range(3))
        mac_address = f"{oui}:{suffix}"

    # Build merged identities
    merged = {}

    # Merge each protocol identity
    identity_keys = [
        ("modbus_identity", template.modbus_identity),
        ("ethernet_ip_identity", template.ethernet_ip_identity),
        ("profinet_identity", template.profinet_identity),
        ("s7_identity", template.s7_identity),
        ("bacnet_identity", template.bacnet_identity),
        ("snmp_identity", template.snmp_identity),
    ]

    for key, base_identity in identity_keys:
        if base_identity:
            fw_override = firmware.identity_overrides.get(key, {})
            instance_values = {
                "serial_number": final_serial,
                "station_name": final_name,
            }
            # Add firmware version to appropriate fields
            if key == "modbus_identity":
                instance_values["major_minor_revision"] = firmware.version
            elif key == "profinet_identity":
                instance_values["im0_sw_revision"] = firmware.version
            elif key == "ethernet_ip_identity":
                # Parse version for revision fields
                parts = firmware.version.lstrip("V").split(".")
                if len(parts) >= 2:
                    try:
                        instance_values["revision_major"] = int(parts[0])
                        instance_values["revision_minor"] = int(parts[1])
                    except ValueError:
                        pass
            elif key == "s7_identity":
                instance_values["plant_id"] = final_name

            merged[key] = merge_identity(base_identity, fw_override, instance_values)

    return DeviceInstance(
        template_id=template_id,
        firmware_version=firmware.version,
        serial_number=final_serial,
        station_name=final_name,
        mac_address=mac_address or "",
        ip_address=ip_address or "",
        cves=list(firmware.cves),
        merged_identities=merged,
    )


# =============================================================================
# Auto-generated Templates (migrated from vendor_fingerprints/)
# =============================================================================
# These 88 templates were auto-generated from vendor_fingerprints/ module
# fingerprints that did not have corresponding DeviceTemplate entries.
# Generated by scripts/generate_missing_templates.py


# --- ABB (2 entries) ---

_register_template(DeviceTemplate(
    id="abb/acs580/acs580",
    vendor="ABB",
    vendor_family="ACS580",
    model="ACS580",
    model_name="ACS580",
    device_type="drive",
    description="ABB ACS580",
    oui_prefixes=['00:20:99', '00:21:99', 'CC:DA:0C'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 3.0,
            "max_ms": 50.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "exponential",
            "outlier_probability": 0.003,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.00025,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="2.76",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "ABB",
            "product_code": "ACS580-01",
            "major_minor_revision": "V2.76",
            "vendor_url": "http://www.abb.com",
            "product_name": "ACS580-01 General Purpose Drive",
            "model_name": "Variable Speed Drive",
        },
    ethernet_ip_identity={
            "vendor_id": 285,
            "device_type": 2,
            "product_code": 580,
            "revision_major": 2,
            "revision_minor": 76,
            "serial_number": 2880439680,
            "product_name": "ACS580-01 General Purpose Drive",
            "state": 3,
        },
))

_register_template(DeviceTemplate(
    id="abb/m2bax/m2bax-180mlb",
    vendor="ABB",
    vendor_family="M2BAX",
    model="M2BAX 180MLB",
    model_name="M2BAX 180MLB",
    device_type="motor",
    description="ABB M2BAX 180MLB",
    oui_prefixes=['00:20:99', '00:21:99', 'CC:DA:0C'],
    tcp_stack={
            "ttl": 64,
            "window_size": 4096,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 10.0,
            "max_ms": 100.0,
            "mean_ms": 35.0,
            "std_dev_ms": 20.0,
            "distribution": "gaussian",
            "outlier_probability": 0.003,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0004,
            "timeout_probability": 0.0002,
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="1.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "ABB",
            "product_code": "M2BAX 180MLB",
            "major_minor_revision": "V1.0",
            "product_name": "M2BAX 180MLB Induction Motor",
            "model_name": "Electric Motor",
        },
))


# --- Automated Logic (1 entries) ---

_register_template(DeviceTemplate(
    id="automated-logic/webctrl/me812u",
    vendor="Automated Logic",
    vendor_family="WebCTRL",
    model="ME812U",
    model_name="ME812U",
    device_type="building_controller",
    description="Automated Logic ME812U",
    oui_prefixes=['00:14:C1', '00:1C:12'],
    tcp_stack={},
    response_timing={
            "min_ms": 8.0,
            "max_ms": 100.0,
            "mean_ms": 30.0,
            "std_dev_ms": 18.0,
            "distribution": "lognormal",
            "outlier_probability": 0.005,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "timeout_probability": 0.002,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['bacnet'],
    firmware_variants=[FirmwareVariant(
        version="6.2.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    bacnet_identity={
            "vendor_id": 86,
            "vendor_name": "Automated Logic",
            "model_name": "ME812U Field Controller",
            "firmware_revision": "6.2.0",
            "application_software_version": "6.2",
            "protocol_version": 1,
            "protocol_revision": 14,
            "max_apdu_length": 480,
            "segmentation_supported": 3,
            "device_instance": 11002,
            "object_name": "ME812U-001",
        },
))


# --- Bosch (1 entries) ---

_register_template(DeviceTemplate(
    id="bosch/ptz-camera/mic-ip-7100i",
    vendor="Bosch",
    vendor_family="PTZ Camera",
    model="MIC IP 7100i",
    model_name="MIC IP 7100i",
    device_type="camera",
    description="Bosch MIC IP 7100i",
    oui_prefixes=['00:04:13', '00:07:5F'],
    tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 25.0,
            "mean_ms": 8.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
            "outlier_probability": 0.01,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "timeout_probability": 0.001,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['snmp'],
    firmware_variants=[FirmwareVariant(
        version="7.82.0127",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Bosch MIC IP 7100i PTZ Camera 7.82.0127",
            "sys_object_id": "1.3.6.1.4.1.3246.1.1.7100",
            "sys_name": "CAM-BOSCH-001",
            "ntcip_device_type": "camera",
        },
))


# --- Carrier (1 entries) ---

_register_template(DeviceTemplate(
    id="carrier/i-vu/pro-open",
    vendor="Carrier",
    vendor_family="i-Vu",
    model="Pro Open",
    model_name="Pro Open",
    device_type="bms_server",
    description="Carrier Pro Open",
    oui_prefixes=['00:0D:AD', '00:1E:8E'],
    tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 70.0,
            "mean_ms": 22.0,
            "std_dev_ms": 12.0,
            "distribution": "gaussian",
            "outlier_probability": 0.003,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "timeout_probability": 0.001,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['bacnet'],
    firmware_variants=[FirmwareVariant(
        version="7.0.2",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    bacnet_identity={
            "vendor_id": 301,
            "vendor_name": "Carrier",
            "model_name": "i-Vu Pro Open Server",
            "firmware_revision": "7.0.2",
            "application_software_version": "7.0",
            "protocol_version": 1,
            "protocol_revision": 19,
            "max_apdu_length": 1476,
            "segmentation_supported": 0,
            "device_instance": 5001,
            "object_name": "IVU-SERVER-001",
        },
))


# --- Cisco (1 entries) ---

_register_template(DeviceTemplate(
    id="cisco/stratix/stratix-5700",
    vendor="Cisco",
    vendor_family="Stratix",
    model="Stratix 5700",
    model_name="Stratix 5700",
    device_type="switch",
    description="Cisco Stratix 5700",
    oui_prefixes=['00:1B:0D', '00:1E:BD'],
    tcp_stack={
            "ttl": 255,
            "window_size": 16384,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 1.0,
            "max_ms": 10.0,
            "mean_ms": 2.5,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
        },
    supported_protocols=['snmp'],
    firmware_variants=[FirmwareVariant(
        version="15.2(7)E3",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Cisco IOS Software, Stratix 5700 Software, Version 15.2(7)E3",
            "sys_object_id": "1.3.6.1.4.1.9.1.1858",
            "sys_name": "Stratix-5700-001",
            "sys_location": "Plant Floor",
            "sys_contact": "ot-network@facility.local",
        },
))


# --- Cognex (3 entries) ---

_register_template(DeviceTemplate(
    id="cognex/dataman/dataman-280",
    vendor="Cognex",
    vendor_family="DataMan",
    model="DataMan 280",
    model_name="DataMan 280",
    device_type="barcode_scanner",
    description="Cognex DataMan 280",
    oui_prefixes=['00:04:3E', '00:0D:88'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 40.0,
            "mean_ms": 12.0,
            "std_dev_ms": 6.0,
            "distribution": "gaussian",
        },
    supported_protocols=['ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="6.1.5",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    ethernet_ip_identity={
            "vendor_id": 112,
            "device_type": 43,
            "product_code": 280,
            "revision_major": 6,
            "revision_minor": 1,
            "product_name": "DataMan 280 Barcode Reader",
            "state": 3,
        },
))

_register_template(DeviceTemplate(
    id="cognex/dataman/dataman-370",
    vendor="Cognex",
    vendor_family="DataMan",
    model="DataMan 370",
    model_name="DataMan 370",
    device_type="barcode_scanner",
    description="Cognex DataMan 370",
    oui_prefixes=['00:04:3E', '00:0D:88'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 50.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="6.2.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Cognex Corporation",
            "product_code": "DataMan 370",
            "major_minor_revision": "6.2.0",
            "product_name": "DataMan 370 Fixed-Mount Barcode Reader",
            "model_name": "DataMan 370",
        },
    ethernet_ip_identity={
            "vendor_id": 112,
            "device_type": 43,
            "product_code": 370,
            "revision_major": 6,
            "revision_minor": 2,
            "product_name": "DataMan 370 Barcode Reader",
            "state": 3,
        },
))

_register_template(DeviceTemplate(
    id="cognex/in-sight/in-sight-7802",
    vendor="Cognex",
    vendor_family="In-Sight",
    model="In-Sight 7802",
    model_name="In-Sight 7802",
    device_type="vision_system",
    description="Cognex In-Sight 7802",
    oui_prefixes=['00:04:3E', '00:0D:88'],
    tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 10.0,
            "max_ms": 100.0,
            "mean_ms": 35.0,
            "std_dev_ms": 20.0,
            "distribution": "gaussian",
        },
    supported_protocols=['ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="6.3.2",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    ethernet_ip_identity={
            "vendor_id": 112,
            "device_type": 43,
            "product_code": 7802,
            "revision_major": 6,
            "revision_minor": 3,
            "serial_number": 1230190392,
            "product_name": "In-Sight 7802 Vision System",
            "state": 3,
        },
))


# --- Delta Controls (2 entries) ---

_register_template(DeviceTemplate(
    id="delta-controls/entelibus/manager",
    vendor="Delta Controls",
    vendor_family="enteliBUS",
    model="Manager",
    model_name="Manager",
    device_type="building_controller",
    description="Delta Controls Manager",
    oui_prefixes=['00:0B:AB', '00:0D:9F'],
    tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 80.0,
            "mean_ms": 22.0,
            "std_dev_ms": 13.0,
            "distribution": "gaussian",
            "outlier_probability": 0.004,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "timeout_probability": 0.001,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['bacnet'],
    firmware_variants=[FirmwareVariant(
        version="4.8.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    bacnet_identity={
            "vendor_id": 122,
            "vendor_name": "Delta Controls",
            "model_name": "enteliBUS Manager",
            "firmware_revision": "4.8.0",
            "application_software_version": "4.8",
            "protocol_version": 1,
            "protocol_revision": 19,
            "max_apdu_length": 1476,
            "segmentation_supported": 0,
            "device_instance": 8001,
            "object_name": "ENTBUS-MGR-001",
            "description": "enteliBUS Building Controller",
        },
))

_register_template(DeviceTemplate(
    id="delta-controls/entelibus/ebcon",
    vendor="Delta Controls",
    vendor_family="enteliBUS",
    model="eBCON",
    model_name="eBCON",
    device_type="zone_controller",
    description="Delta Controls eBCON",
    oui_prefixes=['00:0B:AB', '00:0D:9F'],
    tcp_stack={},
    response_timing={
            "min_ms": 10.0,
            "max_ms": 120.0,
            "mean_ms": 35.0,
            "std_dev_ms": 20.0,
            "distribution": "lognormal",
            "outlier_probability": 0.005,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "timeout_probability": 0.002,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['bacnet'],
    firmware_variants=[FirmwareVariant(
        version="3.5.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    bacnet_identity={
            "vendor_id": 122,
            "vendor_name": "Delta Controls",
            "model_name": "eBCON Controller",
            "firmware_revision": "3.5.0",
            "application_software_version": "3.5",
            "protocol_version": 1,
            "protocol_revision": 14,
            "max_apdu_length": 480,
            "segmentation_supported": 3,
            "device_instance": 8002,
            "object_name": "EBCON-001",
        },
))


# --- Dematic (1 entries) ---

_register_template(DeviceTemplate(
    id="dematic/iq-platform/iq-wcs-controller",
    vendor="Dematic",
    vendor_family="iQ Platform",
    model="iQ WCS Controller",
    model_name="iQ WCS Controller",
    device_type="server",
    description="Dematic iQ WCS Controller",
    oui_prefixes=['00:1C:34'],
    tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 1.0,
            "max_ms": 20.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="5.4.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Dematic Corporation",
            "product_code": "iQ-WCS",
            "major_minor_revision": "5.4.0",
            "product_name": "Dematic iQ Warehouse Control System",
            "model_name": "iQ WCS",
        },
    ethernet_ip_identity={
            "vendor_id": 0,
            "device_type": 12,
            "product_code": 5400,
            "revision_major": 5,
            "revision_minor": 4,
            "product_name": "Dematic iQ WCS",
            "state": 3,
        },
))


# --- Distech Controls (1 entries) ---

_register_template(DeviceTemplate(
    id="distech-controls/ecy/ecy-vav",
    vendor="Distech Controls",
    vendor_family="ECY",
    model="ECY-VAV",
    model_name="ECY-VAV",
    device_type="vav_controller",
    description="Distech Controls ECY-VAV",
    oui_prefixes=['00:1E:C0', 'D0:77:14'],
    tcp_stack={},
    response_timing={
            "min_ms": 8.0,
            "max_ms": 100.0,
            "mean_ms": 28.0,
            "std_dev_ms": 15.0,
            "distribution": "lognormal",
            "outlier_probability": 0.004,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "timeout_probability": 0.002,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['bacnet'],
    firmware_variants=[FirmwareVariant(
        version="2.5.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    bacnet_identity={
            "vendor_id": 165,
            "vendor_name": "Distech Controls",
            "model_name": "ECY-VAV Variable Air Volume Controller",
            "firmware_revision": "2.5.0",
            "application_software_version": "2.5",
            "protocol_version": 1,
            "protocol_revision": 14,
            "max_apdu_length": 480,
            "segmentation_supported": 3,
            "device_instance": 9002,
            "object_name": "ECY-VAV-001",
        },
))


# --- Econolite (1 entries) ---

_register_template(DeviceTemplate(
    id="econolite/traffic-controller/asc-3-2100",
    vendor="Econolite",
    vendor_family="Traffic Controller",
    model="ASC/3-2100",
    model_name="ASC/3-2100",
    device_type="traffic_controller",
    description="Econolite ASC/3-2100",
    oui_prefixes=['00:19:FA'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 8.0,
            "max_ms": 80.0,
            "mean_ms": 25.0,
            "std_dev_ms": 12.0,
            "distribution": "gaussian",
            "outlier_probability": 0.02,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "timeout_probability": 0.001,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['snmp'],
    firmware_variants=[FirmwareVariant(
        version="V2.0.8",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Econolite ASC/3-2100 Signal Controller V2.0.8",
            "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.2",
            "sys_name": "ASC3-2100-001",
            "ntcip_device_type": "asc",
            "max_phases": 8,
            "max_detectors": 32,
        },
))


# --- Endress+Hauser (2 entries) ---

_register_template(DeviceTemplate(
    id="endress-hauser/prosonic/fmu90",
    vendor="Endress+Hauser",
    vendor_family="Prosonic",
    model="FMU90",
    model_name="FMU90",
    device_type="field_instrument",
    description="Endress+Hauser FMU90",
    oui_prefixes=['00:0B:CD', '00:80:A3'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 8.0,
            "max_ms": 60.0,
            "mean_ms": 20.0,
            "std_dev_ms": 10.0,
            "distribution": "gaussian",
            "outlier_probability": 0.003,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0004,
            "timeout_probability": 0.0002,
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="01.04.00",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Endress+Hauser",
            "product_code": "FMU90-R11CA111AA3A",
            "major_minor_revision": "01.04.00",
            "vendor_url": "http://www.endress.com",
            "product_name": "Prosonic S FMU90 Ultrasonic Level",
            "model_name": "Ultrasonic Level Transmitter",
        },
))

_register_template(DeviceTemplate(
    id="endress-hauser/promag/promag-w-400",
    vendor="Endress+Hauser",
    vendor_family="Promag",
    model="Promag W 400",
    model_name="Promag W 400",
    device_type="field_instrument",
    description="Endress+Hauser Promag W 400",
    oui_prefixes=['00:0B:CD', '00:80:A3'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 45.0,
            "mean_ms": 14.0,
            "std_dev_ms": 7.0,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0003,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="01.07.00",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Endress+Hauser",
            "product_code": "50W4H-UA0A1AA0AAAA",
            "major_minor_revision": "01.07.00",
            "vendor_url": "http://www.endress.com",
            "product_name": "Proline Promag W 400 Water Flowmeter",
            "model_name": "Water Flowmeter",
        },
))


# --- FLIR (1 entries) ---

_register_template(DeviceTemplate(
    id="flir/thermal-sensor/trafisense",
    vendor="FLIR",
    vendor_family="Thermal Sensor",
    model="TrafiSense",
    model_name="TrafiSense",
    device_type="thermal_sensor",
    description="FLIR TrafiSense",
    oui_prefixes=['00:40:7F', '00:80:F4'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 3.0,
            "max_ms": 35.0,
            "mean_ms": 12.0,
            "std_dev_ms": 6.0,
            "distribution": "gaussian",
            "outlier_probability": 0.01,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "timeout_probability": 0.001,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['snmp'],
    firmware_variants=[FirmwareVariant(
        version="V3.5.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "FLIR TrafiSense Multi-Lane Detector V3.5.0",
            "sys_object_id": "1.3.6.1.4.1.28846.1.2.1",
            "sys_name": "THERMAL-ML-001",
            "ntcip_device_type": "sensor",
        },
))


# --- GE (3 entries) ---

_register_template(DeviceTemplate(
    id="ge/versamax/ic200udd104",
    vendor="GE",
    vendor_family="VersaMax",
    model="IC200UDD104",
    model_name="IC200UDD104",
    device_type="plc",
    description="GE IC200UDD104",
    oui_prefixes=['00:09:45', '00:30:C1', '00:50:99', '00:22:52'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": False,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 80.0,
            "mean_ms": 20.0,
            "std_dev_ms": 12.0,
            "distribution": "gaussian",
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.002,
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="4.21",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "GE Fanuc",
            "product_code": "IC200UDD104",
            "major_minor_revision": "4.21",
            "vendor_url": "http://www.gefanuc.com",
            "product_name": "VersaMax Micro PLC",
            "model_name": "VersaMax Micro",
        },
))

_register_template(DeviceTemplate(
    id="ge/pacsystems/ic695cpe310",
    vendor="GE",
    vendor_family="PACSystems",
    model="IC695CPE310",
    model_name="IC695CPE310",
    device_type="plc",
    description="GE IC695CPE310",
    oui_prefixes=['00:09:45', '00:30:C1', '00:50:99', '00:22:52'],
    tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 1.5,
            "max_ms": 40.0,
            "mean_ms": 10.0,
            "std_dev_ms": 6.0,
            "distribution": "gaussian",
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0008,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="10.80",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "GE Automation",
            "product_code": "IC695CPE310",
            "major_minor_revision": "10.80",
            "vendor_url": "http://www.geautomation.com",
            "product_name": "PACSystems RX3i CPE310",
            "model_name": "PACSystems RX3i",
        },
    ethernet_ip_identity={
            "vendor_id": 82,
            "device_type": 14,
            "product_code": 310,
            "revision_major": 10,
            "revision_minor": 80,
            "serial_number": 3156467269,
            "product_name": "PACSystems RX3i CPE310",
            "state": 3,
        },
))

_register_template(DeviceTemplate(
    id="ge/proficy/proficy-historian-7-2",
    vendor="GE",
    vendor_family="Proficy",
    model="Proficy Historian 7.2",
    model_name="Proficy Historian 7.2",
    device_type="server",
    description="GE Proficy Historian 7.2",
    oui_prefixes=['00:09:45', '00:30:C1', '00:50:99', '00:22:52'],
    tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 8.0,
            "max_ms": 250.0,
            "mean_ms": 65.0,
            "std_dev_ms": 40.0,
            "distribution": "lognormal",
            "outlier_probability": 0.01,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0015,
            "timeout_probability": 0.0008,
        },
    supported_protocols=['modbus', 'opc_ua'],
    protocol_quirks={
            "max_concurrent_connections": 300,
            "query_timeout_ms": 30000,
            "data_compression_enabled": True,
            "historian_api_version": "7.2",
        },
    firmware_variants=[FirmwareVariant(
        version="7.2",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "GE Digital",
            "product_code": "Proficy Historian",
            "major_minor_revision": "7.2",
            "vendor_url": "http://www.ge.com/digital",
            "product_name": "Proficy Historian Server",
            "model_name": "Proficy Historian 7.2",
        },
    opc_ua_identity={
            "application_name": "GE Proficy Historian",
            "application_uri": "urn:GE:Proficy:Historian",
            "product_uri": "http://www.ge.com/digital/proficy-historian",
            "manufacturer_name": "GE Digital",
            "product_name": "Proficy Historian",
            "software_version": "7.2.0",
            "build_number": "5678",
            "build_date": "2020-06-10T12:00:00Z",
        },
))


# --- HMS (4 entries) ---

_register_template(DeviceTemplate(
    id="hms/anybus/anybus-communicator",
    vendor="HMS",
    vendor_family="Anybus",
    model="Anybus Communicator",
    model_name="Anybus Communicator",
    device_type="gateway",
    description="HMS Anybus Communicator",
    oui_prefixes=['00:30:11'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 3.0,
            "max_ms": 40.0,
            "mean_ms": 12.0,
            "std_dev_ms": 7.0,
            "distribution": "gaussian",
            "outlier_probability": 0.004,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3],
            "exception_probability": 0.0005,
            "timeout_probability": 0.00025,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="1.50",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "HMS Industrial Networks",
            "product_code": "AB7072",
            "major_minor_revision": "1.50",
            "vendor_url": "http://www.anybus.com",
            "product_name": "Anybus Communicator EtherNet/IP",
            "model_name": "Serial-to-EtherNet Gateway",
        },
    ethernet_ip_identity={
            "vendor_id": 283,
            "device_type": 12,
            "product_code": 7072,
            "revision_major": 1,
            "revision_minor": 50,
            "serial_number": 1213027074,
            "product_name": "Anybus Communicator",
            "state": 3,
        },
))

_register_template(DeviceTemplate(
    id="hms/ewon/cosy-131",
    vendor="HMS",
    vendor_family="EWON",
    model="Cosy 131",
    model_name="Cosy 131",
    device_type="remote_access",
    description="HMS Cosy 131",
    oui_prefixes=['00:30:11'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 3.0,
            "max_ms": 50.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
            "outlier_probability": 0.004,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0004,
            "timeout_probability": 0.0002,
        },
    supported_protocols=['modbus', 'ethernet_ip', 'snmp'],
    firmware_variants=[FirmwareVariant(
        version="14.8s0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "HMS Industrial Networks - EWON",
            "product_code": "EC131",
            "major_minor_revision": "14.8",
            "vendor_url": "https://www.ewon.biz",
            "product_name": "EWON Cosy 131 Remote Access Router",
            "model_name": "Remote Access Router",
        },
    ethernet_ip_identity={
            "vendor_id": 283,
            "device_type": 12,
            "product_code": 131,
            "revision_major": 14,
            "revision_minor": 8,
            "serial_number": 3960672257,
            "product_name": "EWON Cosy 131 Remote Access Router",
            "state": 3,
        },
    snmp_identity={
            "sys_descr": "EWON Cosy 131 Remote Access Router v14.8s0",
            "sys_object_id": "1.3.6.1.4.1.8284.2.2",
            "sys_name": "EWON-COSY-001",
            "sys_location": "Control Room",
        },
))

_register_template(DeviceTemplate(
    id="hms/ewon/flexy-205",
    vendor="HMS",
    vendor_family="EWON",
    model="Flexy 205",
    model_name="Flexy 205",
    device_type="remote_access",
    description="HMS Flexy 205",
    oui_prefixes=['00:30:11'],
    tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 40.0,
            "mean_ms": 10.0,
            "std_dev_ms": 6.0,
            "distribution": "gaussian",
            "outlier_probability": 0.003,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0003,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['modbus', 'ethernet_ip', 'snmp'],
    firmware_variants=[FirmwareVariant(
        version="14.8s0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "HMS Industrial Networks - EWON",
            "product_code": "EF205",
            "major_minor_revision": "14.8",
            "vendor_url": "https://www.ewon.biz",
            "product_name": "EWON Flexy 205 Industrial IoT Gateway",
            "model_name": "Remote Access Gateway",
        },
    ethernet_ip_identity={
            "vendor_id": 283,
            "device_type": 12,
            "product_code": 205,
            "revision_major": 14,
            "revision_minor": 8,
            "serial_number": 1163349505,
            "product_name": "EWON Flexy 205",
            "state": 3,
        },
    snmp_identity={
            "sys_descr": "EWON Flexy 205 Industrial IoT Gateway v14.8s0",
            "sys_object_id": "1.3.6.1.4.1.8284.2.1",
            "sys_name": "EWON-FLEXY-001",
            "sys_location": "Industrial DMZ",
        },
))

_register_template(DeviceTemplate(
    id="hms/ewon-flexy/flexy-205",
    vendor="HMS",
    vendor_family="eWON Flexy",
    model="Flexy 205",
    model_name="Flexy 205",
    device_type="remote_access",
    description="HMS Flexy 205",
    oui_prefixes=['00:06:71'],
    tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 20.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus', 'snmp'],
    firmware_variants=[FirmwareVariant(
        version="14.5",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "HMS Industrial Networks",
            "product_code": "Flexy205",
            "major_minor_revision": "14.5",
            "product_name": "eWON Flexy 205 Industrial Router",
            "model_name": "Flexy205",
        },
    snmp_identity={
            "sys_descr": "eWON Flexy 205 - Firmware 14.5s0",
            "sys_object_id": "1.3.6.1.4.1.8284.2.1",
            "sys_name": "FLEXY-205-001",
            "sys_location": "Remote Site",
            "sys_contact": "remote@facility.local",
        },
))


# --- Honeywell (5 entries) ---

_register_template(DeviceTemplate(
    id="honeywell/hc900/hc900-controller",
    vendor="Honeywell",
    vendor_family="HC900",
    model="HC900 Controller",
    model_name="HC900 Controller",
    device_type="instrument",
    description="Honeywell HC900 Controller",
    oui_prefixes=['00:40:84', '00:22:6A'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 50.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="7.3",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Honeywell International Inc",
            "product_code": "900C52-0001",
            "major_minor_revision": "7.3",
            "product_name": "HC900 Hybrid Controller",
            "model_name": "HC900",
        },
))

_register_template(DeviceTemplate(
    id="honeywell/lds/pipeline-lds",
    vendor="Honeywell",
    vendor_family="LDS",
    model="Pipeline LDS",
    model_name="Pipeline LDS",
    device_type="leak_detection",
    description="Honeywell Pipeline LDS",
    oui_prefixes=['00:40:84', '00:22:6A', 'C4:EF:DA', '58:FC:C8'],
    tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 100.0,
            "mean_ms": 25.0,
            "std_dev_ms": 15.0,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0003,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="3.2.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "LDS-3200",
            "major_minor_revision": "V3.2.0",
            "product_name": "Pipeline Leak Detection System",
            "model_name": "LDS Server",
        },
))

_register_template(DeviceTemplate(
    id="honeywell/stt/stt850",
    vendor="Honeywell",
    vendor_family="STT",
    model="STT850",
    model_name="STT850",
    device_type="instrument",
    description="Honeywell STT850",
    oui_prefixes=['00:40:84', '00:22:6A'],
    tcp_stack={
            "ttl": 64,
            "window_size": 4096,
            "mss": 536,
        },
    response_timing={
            "min_ms": 20.0,
            "max_ms": 150.0,
            "mean_ms": 50.0,
            "std_dev_ms": 25.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="4.2",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Honeywell International Inc",
            "product_code": "STT850-E-0-AHS",
            "major_minor_revision": "4.2",
            "product_name": "STT850 SmartLine Temperature Transmitter",
            "model_name": "STT850",
        },
))

_register_template(DeviceTemplate(
    id="honeywell/uda/uda2182",
    vendor="Honeywell",
    vendor_family="UDA",
    model="UDA2182",
    model_name="UDA2182",
    device_type="instrument",
    description="Honeywell UDA2182",
    oui_prefixes=['00:40:84', '00:22:6A', 'C4:EF:DA', '58:FC:C8'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 10.0,
            "max_ms": 80.0,
            "mean_ms": 30.0,
            "std_dev_ms": 15.0,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0003,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="2.50",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Honeywell International Inc.",
            "product_code": "UDA2182",
            "major_minor_revision": "V2.50",
            "product_name": "UDA2182 Universal Dual Analyzer",
            "model_name": "Process Analyzer",
        },
))

_register_template(DeviceTemplate(
    id="honeywell/udc/udc3500",
    vendor="Honeywell",
    vendor_family="UDC",
    model="UDC3500",
    model_name="UDC3500",
    device_type="instrument",
    description="Honeywell UDC3500",
    oui_prefixes=['00:40:84', '00:22:6A'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 10.0,
            "max_ms": 80.0,
            "mean_ms": 25.0,
            "std_dev_ms": 12.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="6.1",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Honeywell International Inc",
            "product_code": "DC3500-EE-0L00-200",
            "major_minor_revision": "6.1",
            "product_name": "UDC3500 Universal Digital Controller",
            "model_name": "UDC3500",
        },
))


# --- Impinj (2 entries) ---

_register_template(DeviceTemplate(
    id="impinj/speedway/speedway-r420",
    vendor="Impinj",
    vendor_family="Speedway",
    model="Speedway R420",
    model_name="Speedway R420",
    device_type="rfid_reader",
    description="Impinj Speedway R420",
    oui_prefixes=['00:16:25'],
    tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 40.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus', 'snmp'],
    firmware_variants=[FirmwareVariant(
        version="7.5.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Impinj Inc",
            "product_code": "Speedway R420",
            "major_minor_revision": "7.5.0",
            "product_name": "Impinj Speedway R420 RAIN RFID Reader",
            "model_name": "R420",
        },
    snmp_identity={
            "sys_descr": "Impinj Speedway R420 RAIN RFID Reader V7.5.0",
            "sys_object_id": "1.3.6.1.4.1.25882.1.2",
            "sys_name": "SPEEDWAY-R420-001",
        },
))

_register_template(DeviceTemplate(
    id="impinj/speedway/speedway-r700",
    vendor="Impinj",
    vendor_family="Speedway",
    model="Speedway R700",
    model_name="Speedway R700",
    device_type="rfid_reader",
    description="Impinj Speedway R700",
    oui_prefixes=['00:16:25'],
    tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 3.0,
            "max_ms": 30.0,
            "mean_ms": 10.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus', 'snmp'],
    firmware_variants=[FirmwareVariant(
        version="8.2.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Impinj Inc",
            "product_code": "Speedway R700",
            "major_minor_revision": "8.2.0",
            "vendor_url": "https://www.impinj.com",
            "product_name": "Impinj Speedway R700 RAIN RFID Reader",
            "model_name": "R700",
        },
    snmp_identity={
            "sys_descr": "Impinj Speedway R700 RAIN RFID Reader V8.2.0",
            "sys_object_id": "1.3.6.1.4.1.25882.1.1",
            "sys_name": "SPEEDWAY-R700-001",
            "sys_location": "Dock Door",
            "sys_contact": "rfid@warehouse.local",
        },
))


# --- Johnson Controls (1 entries) ---

_register_template(DeviceTemplate(
    id="johnson-controls/metasys/snc",
    vendor="Johnson Controls",
    vendor_family="Metasys",
    model="SNC",
    model_name="SNC",
    device_type="building_controller",
    description="Johnson Controls SNC",
    oui_prefixes=['00:1A:17', '00:23:BE'],
    tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 8.0,
            "max_ms": 120.0,
            "mean_ms": 35.0,
            "std_dev_ms": 20.0,
            "distribution": "lognormal",
            "outlier_probability": 0.003,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "timeout_probability": 0.001,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['bacnet'],
    firmware_variants=[FirmwareVariant(
        version="11.0.2",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    bacnet_identity={
            "vendor_id": 5,
            "vendor_name": "Johnson Controls",
            "model_name": "SNC Supervisory Network Controller",
            "firmware_revision": "11.0.2",
            "application_software_version": "11.0",
            "protocol_version": 1,
            "protocol_revision": 17,
            "max_apdu_length": 1476,
            "segmentation_supported": 0,
            "device_instance": 1002,
            "object_name": "SNC-001",
            "description": "Metasys Supervisory Controller",
        },
))


# --- KUKA (3 entries) ---

_register_template(DeviceTemplate(
    id="kuka/kmp-mobile-platform/kmp-1500",
    vendor="KUKA",
    vendor_family="KMP Mobile Platform",
    model="KMP 1500",
    model_name="KMP 1500",
    device_type="agv",
    description="KUKA KMP 1500",
    oui_prefixes=['00:1A:28', '00:1F:29', '00:10:DC'],
    tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 25.0,
            "mean_ms": 8.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
            "outlier_probability": 0.01,
        },
    error_behavior={
            "timeout_probability": 0.0005,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['ethernet_ip', 'profinet'],
    firmware_variants=[FirmwareVariant(
        version="8.6.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    ethernet_ip_identity={
            "vendor_id": 368,
            "device_type": 43,
            "product_code": 1500,
            "revision_major": 8,
            "revision_minor": 6,
            "serial_number": 1263358001,
            "product_name": "KMP 1500 Mobile Platform",
            "state": 3,
        },
    profinet_identity={
            "vendor_id": 368,
            "device_id": 5376,
            "station_name": "kmp1500",
            "device_type": "KMP 1500 Mobile Platform",
            "device_role": 1,
            "sw_release": "V8.6.0",
            "im0_manufacturer": "KUKA Roboter GmbH",
            "im0_order_id": "KMP 1500",
            "im0_hw_revision": 3,
            "im0_sw_revision": "V8.6.0",
        },
))

_register_template(DeviceTemplate(
    id="kuka/kmp-mobile-platform/kmp-600",
    vendor="KUKA",
    vendor_family="KMP Mobile Platform",
    model="KMP 600",
    model_name="KMP 600",
    device_type="agv",
    description="KUKA KMP 600",
    oui_prefixes=['00:1A:28', '00:1F:29', '00:10:DC'],
    tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 30.0,
            "mean_ms": 10.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },
    supported_protocols=['ethernet_ip', 'profinet'],
    firmware_variants=[FirmwareVariant(
        version="8.5.2",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    ethernet_ip_identity={
            "vendor_id": 368,
            "device_type": 43,
            "product_code": 600,
            "revision_major": 8,
            "revision_minor": 5,
            "product_name": "KMP 600 Mobile Platform",
            "state": 3,
        },
    profinet_identity={
            "vendor_id": 368,
            "device_id": 1536,
            "station_name": "kmp600",
            "device_type": "KMP 600 Mobile Platform",
            "device_role": 1,
            "sw_release": "V8.5.2",
            "im0_manufacturer": "KUKA Roboter GmbH",
            "im0_order_id": "KMP 600",
        },
))

_register_template(DeviceTemplate(
    id="kuka/fleet-management/kuka-fleetmanager",
    vendor="KUKA",
    vendor_family="Fleet Management",
    model="KUKA.FleetManager",
    model_name="KUKA.FleetManager",
    device_type="fleet_manager",
    description="KUKA KUKA.FleetManager",
    oui_prefixes=['00:1A:28', '00:1F:29', '00:10:DC'],
    tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 1.0,
            "max_ms": 15.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus', 'ethernet_ip', 'profinet'],
    firmware_variants=[FirmwareVariant(
        version="3.2.1",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "KUKA Roboter GmbH",
            "product_code": "FleetManager",
            "major_minor_revision": "3.2.1",
            "product_name": "KUKA Fleet Management System",
            "model_name": "FleetManager",
        },
    ethernet_ip_identity={
            "vendor_id": 368,
            "device_type": 12,
            "product_code": 9001,
            "revision_major": 3,
            "revision_minor": 2,
            "product_name": "KUKA.FleetManager",
            "state": 3,
        },
    profinet_identity={
            "vendor_id": 368,
            "device_id": 36865,
            "station_name": "kuka-fleetmgr",
            "device_type": "KUKA Fleet Manager",
            "device_role": 2,
            "sw_release": "V3.2.1",
            "im0_manufacturer": "KUKA Roboter GmbH",
            "im0_order_id": "FleetManager",
            "im0_hw_revision": 2,
            "im0_sw_revision": "V3.2.1",
        },
))


# --- MiR (4 entries) ---

_register_template(DeviceTemplate(
    id="mir/mir-fleet/mir-fleet",
    vendor="MiR",
    vendor_family="MiR Fleet",
    model="MiR Fleet",
    model_name="MiR Fleet",
    device_type="agv",
    description="MiR MiR Fleet",
    oui_prefixes=['00:1E:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 20.0,
            "mean_ms": 6.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="3.8.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Mobile Industrial Robots A/S",
            "product_code": "MiR Fleet",
            "major_minor_revision": "3.8.0",
            "product_name": "MiR Fleet Management System",
            "model_name": "MiR Fleet",
        },
))

_register_template(DeviceTemplate(
    id="mir/mir-mobile-robots/mir100",
    vendor="MiR",
    vendor_family="MiR Mobile Robots",
    model="MiR100",
    model_name="MiR100",
    device_type="agv",
    description="MiR MiR100",
    oui_prefixes=['00:1E:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 50.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
            "outlier_probability": 0.02,
        },
    error_behavior={
            "timeout_probability": 0.001,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="3.12.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Mobile Industrial Robots A/S",
            "product_code": "MiR100",
            "major_minor_revision": "3.12.0",
            "vendor_url": "https://www.mobile-industrial-robots.com",
            "product_name": "MiR100 Autonomous Mobile Robot",
            "model_name": "MiR100",
        },
    ethernet_ip_identity={
            "vendor_id": 0,
            "device_type": 12,
            "product_code": 100,
            "revision_major": 3,
            "revision_minor": 12,
            "product_name": "MiR100",
            "state": 3,
        },
))

_register_template(DeviceTemplate(
    id="mir/mir-mobile-robots/mir250",
    vendor="MiR",
    vendor_family="MiR Mobile Robots",
    model="MiR250",
    model_name="MiR250",
    device_type="agv",
    description="MiR MiR250",
    oui_prefixes=['00:1E:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 50.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="3.12.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Mobile Industrial Robots A/S",
            "product_code": "MiR250",
            "major_minor_revision": "3.12.0",
            "vendor_url": "https://www.mobile-industrial-robots.com",
            "product_name": "MiR250 Autonomous Mobile Robot",
            "model_name": "MiR250",
        },
    ethernet_ip_identity={
            "vendor_id": 0,
            "device_type": 12,
            "product_code": 250,
            "revision_major": 3,
            "revision_minor": 12,
            "product_name": "MiR250",
            "state": 3,
        },
))

_register_template(DeviceTemplate(
    id="mir/mir-mobile-robots/mir500",
    vendor="MiR",
    vendor_family="MiR Mobile Robots",
    model="MiR500",
    model_name="MiR500",
    device_type="agv",
    description="MiR MiR500",
    oui_prefixes=['00:1E:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 60.0,
            "mean_ms": 18.0,
            "std_dev_ms": 10.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="3.12.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Mobile Industrial Robots A/S",
            "product_code": "MiR500",
            "major_minor_revision": "3.12.0",
            "vendor_url": "https://www.mobile-industrial-robots.com",
            "product_name": "MiR500 Autonomous Mobile Robot",
            "model_name": "MiR500",
        },
    ethernet_ip_identity={
            "vendor_id": 0,
            "device_type": 12,
            "product_code": 500,
            "revision_major": 3,
            "revision_minor": 12,
            "product_name": "MiR500",
            "state": 3,
        },
))


# --- Microsoft (4 entries) ---

_register_template(DeviceTemplate(
    id="microsoft/windows-server/jump-server-2008-r2-vulnerable",
    vendor="Microsoft",
    vendor_family="Windows Server",
    model="Jump Server 2008 R2 (Vulnerable)",
    model_name="Jump Server 2008 R2 (Vulnerable)",
    device_type="server",
    description="Microsoft Jump Server 2008 R2 (Vulnerable)",
    oui_prefixes=['00:15:5D', '00:1D:D8', '00:50:F2', '00:03:FF', '7C:1E:52'],
    tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 50.0,
            "mean_ms": 18.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },
    supported_protocols=['snmp'],
    protocol_quirks={
            "snmp": {
                "community_string": "public",
                "version": "2c",
            },
            "smb": {
                "v1_enabled": True,
                "signing_required": False,
            },
        },
    firmware_variants=[FirmwareVariant(
        version="6.1.7601",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Hardware: Intel64 Family 6 Model 85 Stepping 7 AT/AT COMPATIBLE - Software: Windows Version 6.1 (Build 7601 Multiprocessor Free)",
            "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",
            "sys_name": "{device_name}",
            "sys_contact": "admin@example.com",
            "sys_location": "Server Room - Legacy OT Access",
            "sys_services": 76,
        },
))

_register_template(DeviceTemplate(
    id="microsoft/windows-server/jump-server-2016-vulnerable",
    vendor="Microsoft",
    vendor_family="Windows Server",
    model="Jump Server 2016 (Vulnerable)",
    model_name="Jump Server 2016 (Vulnerable)",
    device_type="server",
    description="Microsoft Jump Server 2016 (Vulnerable)",
    oui_prefixes=['00:15:5D', '00:1D:D8', '00:50:F2', '00:03:FF', '7C:1E:52'],
    tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 3.0,
            "max_ms": 35.0,
            "mean_ms": 12.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
        },
    supported_protocols=['snmp'],
    protocol_quirks={
            "snmp": {
                "community_string": "public",
                "version": "2c",
            },
            "rdp": {
                "nla_enabled": False,
                "port": 3389,
            },
        },
    firmware_variants=[FirmwareVariant(
        version="10.0.14393",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Hardware: Intel64 Family 6 Model 85 Stepping 7 AT/AT COMPATIBLE - Software: Windows Version 6.3 (Build 14393 Multiprocessor Free)",
            "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",
            "sys_name": "{device_name}",
            "sys_contact": "admin@example.com",
            "sys_location": "Server Room - OT Access",
            "sys_services": 76,
        },
))

_register_template(DeviceTemplate(
    id="microsoft/windows-server/jump-server-2019",
    vendor="Microsoft",
    vendor_family="Windows Server",
    model="Jump Server 2019",
    model_name="Jump Server 2019",
    device_type="server",
    description="Microsoft Jump Server 2019",
    oui_prefixes=['00:15:5D', '00:1D:D8', '00:50:F2', '00:03:FF', '7C:1E:52'],
    tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 25.0,
            "mean_ms": 8.0,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },
    supported_protocols=['snmp'],
    protocol_quirks={
            "snmp": {
                "community_string": "public",
                "version": "2c",
                "additional_oids": [('1.3.6.1.4.1.311.1.1.3.1.1', 'Windows NT'), ('1.3.6.1.4.1.311.1.1.3.1.2', 'Microsoft Corporation')],
            },
        },
    firmware_variants=[FirmwareVariant(
        version="10.0.17763.5458",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Hardware: Intel64 Family 6 Model 85 Stepping 7 AT/AT COMPATIBLE - Software: Windows Version 6.3 (Build 17763 Multiprocessor Free)",
            "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",
            "sys_name": "{device_name}",
            "sys_contact": "admin@example.com",
            "sys_location": "Server Room - OT Access",
            "sys_services": 76,
        },
))

_register_template(DeviceTemplate(
    id="microsoft/windows-server/jump-server-2019-printnightmare",
    vendor="Microsoft",
    vendor_family="Windows Server",
    model="Jump Server 2019 (PrintNightmare)",
    model_name="Jump Server 2019 (PrintNightmare)",
    device_type="server",
    description="Microsoft Jump Server 2019 (PrintNightmare)",
    oui_prefixes=['00:15:5D', '00:1D:D8', '00:50:F2', '00:03:FF', '7C:1E:52'],
    tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 30.0,
            "mean_ms": 10.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },
    supported_protocols=['snmp'],
    protocol_quirks={
            "snmp": {
                "community_string": "public",
                "version": "2c",
            },
            "print_spooler": {
                "enabled": True,
                "remote_access": True,
            },
        },
    firmware_variants=[FirmwareVariant(
        version="10.0.17763.1",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Hardware: Intel64 Family 6 Model 85 Stepping 7 AT/AT COMPATIBLE - Software: Windows Version 6.3 (Build 17763 Multiprocessor Free)",
            "sys_object_id": "1.3.6.1.4.1.311.1.1.3.1.1",
            "sys_name": "{device_name}",
            "sys_contact": "admin@example.com",
            "sys_location": "Server Room - OT Access",
            "sys_services": 76,
        },
))


# --- Pelco (1 entries) ---

_register_template(DeviceTemplate(
    id="pelco/ptz-camera/spectra-enhanced",
    vendor="Pelco",
    vendor_family="PTZ Camera",
    model="Spectra Enhanced",
    model_name="Spectra Enhanced",
    device_type="camera",
    description="Pelco Spectra Enhanced",
    oui_prefixes=['00:80:F4', '64:3A:EA'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 30.0,
            "mean_ms": 10.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
            "outlier_probability": 0.01,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "timeout_probability": 0.001,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['snmp'],
    firmware_variants=[FirmwareVariant(
        version="V1.32",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Pelco Spectra Enhanced PTZ Camera V1.32",
            "sys_object_id": "1.3.6.1.4.1.17685.1.1.1",
            "sys_name": "PTZ-PELCO-001",
            "sys_location": "Tunnel Portal",
            "ntcip_device_type": "camera",
        },
))


# --- Rockwell (14 entries) ---

_register_template(DeviceTemplate(
    id="rockwell/controllogix/1756-en2t",
    vendor="Rockwell",
    vendor_family="ControlLogix",
    model="1756-EN2T",
    model_name="1756-EN2T",
    device_type="communication_module",
    description="Rockwell 1756-EN2T",
    oui_prefixes=['00:00:BC', '00:1D:9C'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 0.5,
            "max_ms": 8.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.0,
            "distribution": "gaussian",
        },
    supported_protocols=['ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="11.003",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 12,
            "product_code": 166,
            "revision_major": 11,
            "revision_minor": 3,
            "product_name": "1756-EN2T/D",
            "state": 3,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/guardlogix/1756-l73s",
    vendor="Rockwell",
    vendor_family="GuardLogix",
    model="1756-L73S",
    model_name="1756-L73S",
    device_type="plc",
    description="Rockwell 1756-L73S",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 3.5,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 6],
            "exception_probability": 0.0003,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    protocol_quirks={
            "enip_encap_timeout_ms": 10000,
            "cip_safety_enabled": True,
        },
    firmware_variants=[FirmwareVariant(
        version="32.012",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1756-L73S/B",
            "major_minor_revision": "32.012",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1756-L73S GuardLogix5573S Safety Controller",
            "model_name": "GuardLogix 5573S",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 167,
            "revision_major": 32,
            "revision_minor": 12,
            "serial_number": 1870302108,
            "product_name": "1756-L73S/B GUARDLOGIX5573S",
            "state": 3,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/controllogix/1756-l81e",
    vendor="Rockwell",
    vendor_family="ControlLogix",
    model="1756-L81E",
    model_name="1756-L81E",
    device_type="plc",
    description="Rockwell 1756-L81E",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 0.6,
            "max_ms": 18.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.5,
            "distribution": "gaussian",
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 6],
            "exception_probability": 0.0006,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="32.011",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1756-L81E/B",
            "major_minor_revision": "32.011",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1756-L81E Logix5581E Controller",
            "model_name": "ControlLogix 5581E",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 81,
            "revision_major": 32,
            "revision_minor": 11,
            "serial_number": 3285509622,
            "product_name": "1756-L81E/B LOGIX5581E",
            "state": 3,
            "status": 0,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/controllogix/1756-l82e",
    vendor="Rockwell",
    vendor_family="ControlLogix",
    model="1756-L82E",
    model_name="1756-L82E",
    device_type="plc",
    description="Rockwell 1756-L82E",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 3.2,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 6],
            "exception_probability": 0.0005,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="32.011",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1756-L82E/B",
            "major_minor_revision": "32.011",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1756-L82E Logix5582E Controller",
            "model_name": "ControlLogix 5582E",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 82,
            "revision_major": 32,
            "revision_minor": 11,
            "serial_number": 3571840519,
            "product_name": "1756-L82E/B LOGIX5582E",
            "state": 3,
            "status": 0,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/controllogix/1756-l84e",
    vendor="Rockwell",
    vendor_family="ControlLogix",
    model="1756-L84E",
    model_name="1756-L84E",
    device_type="plc",
    description="Rockwell 1756-L84E",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 0.35,
            "max_ms": 12.0,
            "mean_ms": 2.6,
            "std_dev_ms": 1.7,
            "distribution": "gaussian",
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 6],
            "exception_probability": 0.0004,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="32.011",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1756-L84E/B",
            "major_minor_revision": "32.011",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1756-L84E Logix5584E Controller",
            "model_name": "ControlLogix 5584E",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 84,
            "revision_major": 32,
            "revision_minor": 11,
            "serial_number": 3858106136,
            "product_name": "1756-L84E/B LOGIX5584E",
            "state": 3,
            "status": 0,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/micrologix/1763-l16bwa",
    vendor="Rockwell",
    vendor_family="MicroLogix",
    model="1763-L16BWA",
    model_name="1763-L16BWA",
    device_type="plc",
    description="Rockwell 1763-L16BWA",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": False,
            "timestamps_enabled": False,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 3.0,
            "max_ms": 60.0,
            "mean_ms": 15.0,
            "std_dev_ms": 10.0,
            "distribution": "gaussian",
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.003,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="14.000",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1763-L16BWA",
            "major_minor_revision": "14.000",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1763-L16BWA MicroLogix 1100",
            "model_name": "MicroLogix 1100",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 22,
            "revision_major": 14,
            "revision_minor": 0,
            "serial_number": 2999178469,
            "product_name": "1763-L16BWA MICROLOGIX1100",
            "state": 3,
            "status": 0,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/micrologix/1766-l32awaa",
    vendor="Rockwell",
    vendor_family="MicroLogix",
    model="1766-L32AWAA",
    model_name="1766-L32AWAA",
    device_type="plc",
    description="Rockwell 1766-L32AWAA",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": False,
            "timestamps_enabled": False,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
            "outlier_probability": 0.01,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.002,
            "timeout_probability": 0.001,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="21.007",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1766-L32AWAA",
            "major_minor_revision": "21.007",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1766-L32AWAA MicroLogix 1400",
            "model_name": "MicroLogix 1400",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 25,
            "revision_major": 21,
            "revision_minor": 7,
            "serial_number": 3302352631,
            "product_name": "1766-L32AWAA MICROLOGIX1400",
            "state": 3,
            "status": 0,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/micrologix/1766-l32bwaa",
    vendor="Rockwell",
    vendor_family="MicroLogix",
    model="1766-L32BWAA",
    model_name="1766-L32BWAA",
    device_type="plc",
    description="Rockwell 1766-L32BWAA",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": False,
            "timestamps_enabled": False,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
            "outlier_probability": 0.01,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.002,
            "timeout_probability": 0.001,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="21.007",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1766-L32BWAA",
            "major_minor_revision": "21.007",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1766-L32BWAA MicroLogix 1400",
            "model_name": "MicroLogix 1400",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 25,
            "revision_major": 21,
            "revision_minor": 7,
            "serial_number": 2729690325,
            "product_name": "1766-L32BWAA MICROLOGIX1400",
            "state": 3,
            "status": 0,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/micrologix/1766-l32bxb",
    vendor="Rockwell",
    vendor_family="MicroLogix",
    model="1766-L32BXB",
    model_name="1766-L32BXB",
    device_type="plc",
    description="Rockwell 1766-L32BXB",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": False,
            "timestamps_enabled": False,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
            "outlier_probability": 0.01,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.002,
            "timeout_probability": 0.001,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="21.007",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1766-L32BXB",
            "major_minor_revision": "21.007",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1766-L32BXB MicroLogix 1400",
            "model_name": "MicroLogix 1400",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 25,
            "revision_major": 21,
            "revision_minor": 7,
            "serial_number": 3016021478,
            "product_name": "1766-L32BXB MICROLOGIX1400",
            "state": 3,
            "status": 0,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/micrologix/1766-l32bxba",
    vendor="Rockwell",
    vendor_family="MicroLogix",
    model="1766-L32BXBA",
    model_name="1766-L32BXBA",
    device_type="plc",
    description="Rockwell 1766-L32BXBA",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": False,
            "timestamps_enabled": False,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
            "outlier_probability": 0.01,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.002,
            "timeout_probability": 0.001,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="21.007",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1766-L32BXBA",
            "major_minor_revision": "21.007",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1766-L32BXBA MicroLogix 1400",
            "model_name": "MicroLogix 1400",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 25,
            "revision_major": 21,
            "revision_minor": 7,
            "serial_number": 3588683528,
            "product_name": "1766-L32BXBA MICROLOGIX1400",
            "state": 3,
            "status": 0,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/compactlogix/1769-l30erm",
    vendor="Rockwell",
    vendor_family="CompactLogix",
    model="1769-L30ERM",
    model_name="1769-L30ERM",
    device_type="plc",
    description="Rockwell 1769-L30ERM",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 0.9,
            "max_ms": 22.0,
            "mean_ms": 5.5,
            "std_dev_ms": 3.5,
            "distribution": "gaussian",
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0009,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="33.011",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1769-L30ERM",
            "major_minor_revision": "33.011",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1769-L30ERM CompactLogix Controller",
            "model_name": "CompactLogix 5370",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 88,
            "revision_major": 33,
            "revision_minor": 11,
            "serial_number": 4127660073,
            "product_name": "1769-L30ERM/B LOGIX5370",
            "state": 3,
            "status": 0,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/compact-guardlogix/1769-l31es",
    vendor="Rockwell",
    vendor_family="Compact GuardLogix",
    model="1769-L31ES",
    model_name="1769-L31ES",
    device_type="plc",
    description="Rockwell 1769-L31ES",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 0.8,
            "max_ms": 20.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0004,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    protocol_quirks={
            "cip_safety_enabled": True,
        },
    firmware_variants=[FirmwareVariant(
        version="33.011",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1769-L31ES",
            "major_minor_revision": "33.011",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1769-L31ES Compact GuardLogix Safety Controller",
            "model_name": "Compact GuardLogix 5370S",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 169,
            "revision_major": 33,
            "revision_minor": 11,
            "serial_number": 119023930,
            "product_name": "1769-L31ES COMPACTGUARDLOGIX",
            "state": 3,
            "status": 0,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/compact-guardlogix/1769-l32es",
    vendor="Rockwell",
    vendor_family="Compact GuardLogix",
    model="1769-L32ES",
    model_name="1769-L32ES",
    device_type="plc",
    description="Rockwell 1769-L32ES",
    oui_prefixes=['00:00:BC', '00:1D:9C', '5C:88:16'],
    tcp_stack={
            "ttl": 128,
            "window_size": 64240,
            "mss": 1460,
            "window_scaling": 8,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 0.7,
            "max_ms": 18.0,
            "mean_ms": 4.5,
            "std_dev_ms": 2.8,
            "distribution": "gaussian",
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0004,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    protocol_quirks={
            "cip_safety_enabled": True,
        },
    firmware_variants=[FirmwareVariant(
        version="33.011",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Rockwell Automation/Allen-Bradley",
            "product_code": "1769-L32ES",
            "major_minor_revision": "33.011",
            "vendor_url": "http://www.rockwellautomation.com",
            "product_name": "1769-L32ES Compact GuardLogix Safety Controller",
            "model_name": "Compact GuardLogix 5370S",
        },
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 14,
            "product_code": 170,
            "revision_major": 33,
            "revision_minor": 11,
            "serial_number": 405355083,
            "product_name": "1769-L32ES COMPACTGUARDLOGIX",
            "state": 3,
            "status": 0,
        },
))

_register_template(DeviceTemplate(
    id="rockwell/powerflex/powerflex-755",
    vendor="Rockwell",
    vendor_family="PowerFlex",
    model="PowerFlex 755",
    model_name="PowerFlex 755",
    device_type="drive",
    description="Rockwell PowerFlex 755",
    oui_prefixes=['00:00:BC', '00:1D:9C'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 1.0,
            "max_ms": 15.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
        },
    supported_protocols=['ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="20.013",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    ethernet_ip_identity={
            "vendor_id": 1,
            "device_type": 2,
            "product_code": 56,
            "revision_major": 20,
            "revision_minor": 13,
            "product_name": "PowerFlex 755",
            "state": 3,
        },
))


# --- SICK (1 entries) ---

_register_template(DeviceTemplate(
    id="sick/clv/sick-clv650",
    vendor="SICK",
    vendor_family="CLV",
    model="SICK CLV650",
    model_name="SICK CLV650",
    device_type="barcode_scanner",
    description="SICK SICK CLV650",
    oui_prefixes=['00:06:6F', '00:10:BE'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 30.0,
            "mean_ms": 8.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="5.60",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "SICK AG",
            "product_code": "1041807",
            "major_minor_revision": "V5.60",
            "product_name": "CLV650 Fixed Mount Barcode Scanner",
            "model_name": "CLV650",
        },
    ethernet_ip_identity={
            "vendor_id": 218,
            "device_type": 12,
            "product_code": 650,
            "revision_major": 5,
            "revision_minor": 60,
            "product_name": "CLV650 Barcode Scanner",
            "state": 3,
        },
))


# --- Schneider (7 entries) ---

_register_template(DeviceTemplate(
    id="schneider/altivar/atv320",
    vendor="Schneider",
    vendor_family="Altivar",
    model="ATV320",
    model_name="ATV320",
    device_type="drive",
    description="Schneider ATV320",
    oui_prefixes=['00:00:54', '00:80:F4', 'EC:FA:AA'],
    tcp_stack={
            "ttl": 64,
            "window_size": 4096,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 3.0,
            "max_ms": 30.0,
            "mean_ms": 10.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
            "outlier_probability": 0.008,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0008,
            "timeout_probability": 0.0003,
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="V1.7IE18",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "ATV320",
            "major_minor_revision": "V1.7IE18",
            "product_name": "Altivar Machine ATV320",
            "model_name": "ATV320",
        },
))

_register_template(DeviceTemplate(
    id="schneider/altivar/atv930-generic",
    vendor="Schneider",
    vendor_family="Altivar",
    model="ATV930",
    model_name="ATV930",
    device_type="drive",
    description="Schneider ATV930",
    oui_prefixes=['00:00:54', '00:80:F4', 'EC:FA:AA'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 25.0,
            "mean_ms": 8.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
            "outlier_probability": 0.005,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0002,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="V2.1IE26",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "ATV930",
            "major_minor_revision": "V2.1IE26",
            "product_name": "Altivar Process ATV930",
            "model_name": "ATV930",
        },
    ethernet_ip_identity={
            "vendor_id": 67,
            "device_type": 22,
            "product_code": 930,
            "revision_major": 2,
            "revision_minor": 1,
            "product_name": "Altivar Process ATV930",
        },
))

_register_template(DeviceTemplate(
    id="schneider/modicon-m580/bmep586040",
    vendor="Schneider",
    vendor_family="Modicon M580",
    model="BMEP586040",
    model_name="BMEP586040",
    device_type="plc",
    description="Schneider BMEP586040",
    oui_prefixes=['00:00:54', '00:80:F4', 'EC:FA:AA'],
    tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "window_scaling": None,
            "sack_permitted": True,
            "timestamps_enabled": False,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 0.5,
            "max_ms": 20.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.5,
            "distribution": "gaussian",
            "outlier_probability": 0.008,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 5, 6, 10, 11],
            "exception_probability": 0.0006,
        },
    supported_protocols=['modbus', 'ethernet_ip', 'snmp'],
    protocol_quirks={
            "modbus_max_registers": 125,
            "modbus_max_coils": 2000,
            "unity_pro_compatible": True,
        },
    firmware_variants=[FirmwareVariant(
        version="3.30",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "BMEP586040",
            "major_minor_revision": "3.30",
            "vendor_url": "http://www.schneider-electric.com",
            "product_name": "Modicon M580 ePAC",
            "model_name": "BMEP586040",
        },
    ethernet_ip_identity={
            "vendor_id": 67,
            "device_type": 14,
            "product_code": 586,
            "revision_major": 3,
            "revision_minor": 30,
            "serial_number": 313210061,
            "product_name": "BMEP586040",
            "state": 3,
        },
    snmp_identity={
            "sys_descr": "Schneider Electric Modicon M580 BMEP586040 Firmware V3.30",
            "sys_name": "M580-BMEP586040",
            "sys_object_id": "1.3.6.1.4.1.3833.1.100.580",
            "sys_location": "Control Room",
        },
))

_register_template(DeviceTemplate(
    id="schneider/magelis/hmigto5310",
    vendor="Schneider",
    vendor_family="Magelis",
    model="HMIGTO5310",
    model_name="HMIGTO5310",
    device_type="hmi",
    description="Schneider HMIGTO5310",
    oui_prefixes=['00:80:F4', '00:60:E5'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 40.0,
            "mean_ms": 12.0,
            "std_dev_ms": 6.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="5.1",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "HMIGTO5310",
            "major_minor_revision": "5.1",
            "product_name": "Magelis GTO Advanced HMI",
            "model_name": "HMIGTO5310",
        },
))

_register_template(DeviceTemplate(
    id="schneider/tbox/lt2",
    vendor="Schneider",
    vendor_family="TBox",
    model="LT2",
    model_name="LT2",
    device_type="controller",
    description="Schneider LT2",
    oui_prefixes=['00:00:54', '00:80:F4'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 10.0,
            "max_ms": 100.0,
            "mean_ms": 30.0,
            "std_dev_ms": 15.0,
            "distribution": "gaussian",
            "outlier_probability": 0.025,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "timeout_probability": 0.003,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['modbus', 'snmp'],
    firmware_variants=[FirmwareVariant(
        version="V1.48.520",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TBox LT2",
            "major_minor_revision": "V1.48.520",
        },
    snmp_identity={
            "sys_descr": "Schneider Electric TBox LT2 RTU V1.48.520",
            "sys_object_id": "1.3.6.1.4.1.3833.2.1.2",
            "sys_name": "TBOX-LT2-001",
            "sys_location": "Field Cabinet",
        },
))

_register_template(DeviceTemplate(
    id="schneider/lexium-32/lxm32md18m2",
    vendor="Schneider",
    vendor_family="Lexium 32",
    model="LXM32MD18M2",
    model_name="LXM32MD18M2",
    device_type="drive",
    description="Schneider LXM32MD18M2",
    oui_prefixes=['00:00:54', '00:80:F4', 'EC:FA:AA'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 3.5,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
            "outlier_probability": 0.003,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0004,
            "timeout_probability": 0.0002,
        },
    supported_protocols=['modbus', 'ethernet_ip'],
    firmware_variants=[FirmwareVariant(
        version="V2.62",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "LXM32MD18M2",
            "major_minor_revision": "V2.62",
            "product_name": "Lexium 32 Servo Drive",
            "model_name": "LXM32",
        },
    ethernet_ip_identity={
            "vendor_id": 67,
            "device_type": 3,
            "product_code": 32,
            "revision_major": 2,
            "revision_minor": 62,
            "serial_number": 1743816978,
            "product_name": "LXM32MD18M2",
            "state": 3,
        },
))

_register_template(DeviceTemplate(
    id="schneider/tbox/ms-cpu32",
    vendor="Schneider",
    vendor_family="TBox",
    model="MS-CPU32",
    model_name="MS-CPU32",
    device_type="traffic_controller",
    description="Schneider MS-CPU32",
    oui_prefixes=['00:00:54', '00:80:F4'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 8.0,
            "max_ms": 80.0,
            "mean_ms": 25.0,
            "std_dev_ms": 12.0,
            "distribution": "gaussian",
            "outlier_probability": 0.02,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "timeout_probability": 0.002,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['modbus', 'snmp'],
    firmware_variants=[FirmwareVariant(
        version="V1.50.598",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Schneider Electric",
            "product_code": "TBox MS-CPU32",
            "major_minor_revision": "V1.50.598",
        },
    snmp_identity={
            "sys_descr": "Schneider Electric TBox MS-CPU32 RTU V1.50.598",
            "sys_object_id": "1.3.6.1.4.1.3833.2.1.1",
            "sys_name": "TBOX-001",
            "sys_location": "Tunnel Monitoring",
            "ntcip_device_type": "rtu",
        },
))


# --- Siemens (15 entries) ---

_register_template(DeviceTemplate(
    id="siemens/et-200mp/6es7-155-5aa01-0ab0",
    vendor="Siemens",
    vendor_family="ET 200MP",
    model="6ES7 155-5AA01-0AB0",
    model_name="6ES7 155-5AA01-0AB0",
    device_type="io_module",
    description="Siemens 6ES7 155-5AA01-0AB0",
    oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 0.5,
            "max_ms": 10.0,
            "mean_ms": 2.5,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3],
            "exception_probability": 0.0002,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['profinet'],
    firmware_variants=[FirmwareVariant(
        version="V4.1.3",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    profinet_identity={
            "vendor_id": 42,
            "device_id": 1538,
            "device_type": "ET 200MP IM155-5 PN",
            "station_name": "et200mp-im155",
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 155-5AA01-0AB0",
            "im0_hw_revision": 1,
            "im0_sw_revision": "V4.1.3",
        },
))

_register_template(DeviceTemplate(
    id="siemens/et-200sp/6es7-155-6au01-0bn0",
    vendor="Siemens",
    vendor_family="ET 200SP",
    model="6ES7 155-6AU01-0BN0",
    model_name="6ES7 155-6AU01-0BN0",
    device_type="io_module",
    description="Siemens 6ES7 155-6AU01-0BN0",
    oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 0.3,
            "max_ms": 8.0,
            "mean_ms": 2.0,
            "std_dev_ms": 1.2,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3],
            "exception_probability": 0.0002,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['profinet'],
    protocol_quirks={
            "profinet_cycle_time_us": 250,
        },
    firmware_variants=[FirmwareVariant(
        version="V4.2.5",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    profinet_identity={
            "vendor_id": 42,
            "device_id": 1537,
            "device_type": "ET 200SP IM155-6 PN",
            "station_name": "et200sp-im155",
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 155-6AU01-0BN0",
            "im0_hw_revision": 1,
            "im0_sw_revision": "V4.2.5",
        },
))

_register_template(DeviceTemplate(
    id="siemens/s7-1200f/6es7-214-1hf40-0xb0",
    vendor="Siemens",
    vendor_family="S7-1200F",
    model="6ES7 214-1HF40-0XB0",
    model_name="6ES7 214-1HF40-0XB0",
    device_type="plc",
    description="Siemens 6ES7 214-1HF40-0XB0",
    oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "window_scaling": 5,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 1.0,
            "max_ms": 20.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 5, 6],
            "exception_probability": 0.0002,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['modbus', 'profinet', 's7'],
    protocol_quirks={
            "profisafe_enabled": True,
        },
    firmware_variants=[FirmwareVariant(
        version="V4.5.2",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6ES7 214-1HF40-0XB0",
            "major_minor_revision": "V4.5.2",
            "product_name": "CPU 1214FC DC/DC/DC",
            "model_name": "S7-1200F",
        },
    profinet_identity={
            "vendor_id": 42,
            "device_id": 271,
            "device_type": "CPU 1214FC DC/DC/DC",
            "station_name": "plc-s71200f",
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 214-1HF40-0XB0",
            "im0_hw_revision": 4,
            "im0_sw_revision": "V4.5.2",
        },
    s7_identity={
            "order_code": "6ES7 214-1HF40-0XB0",
            "module_type": "CPU 1214FC DC/DC/DC",
            "firmware_version": "V4.5.2",
            "hardware_version": "4",
        },
))

_register_template(DeviceTemplate(
    id="siemens/s7-300/6es7-315-2eh14-0ab0",
    vendor="Siemens",
    vendor_family="S7-300",
    model="6ES7 315-2EH14-0AB0",
    model_name="6ES7 315-2EH14-0AB0",
    device_type="plc",
    description="Siemens 6ES7 315-2EH14-0AB0",
    oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 50.0,
            "mean_ms": 12.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
            "outlier_probability": 0.008,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 5, 6],
            "exception_probability": 0.0008,
            "timeout_probability": 0.0004,
        },
    supported_protocols=['modbus', 'profinet', 's7'],
    protocol_quirks={
            "s7_max_pdu_size": 240,
        },
    firmware_variants=[FirmwareVariant(
        version="V3.2.17",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6ES7 315-2EH14-0AB0",
            "major_minor_revision": "V3.2.17",
            "product_name": "CPU 315-2 PN/DP",
            "model_name": "S7-300",
        },
    profinet_identity={
            "vendor_id": 42,
            "device_id": 514,
            "device_type": "CPU 315-2 PN/DP",
            "station_name": "plc-s7300",
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 315-2EH14-0AB0",
            "im0_hw_revision": 14,
            "im0_sw_revision": "V3.2.17",
        },
    s7_identity={
            "order_code": "6ES7 315-2EH14-0AB0",
            "module_type": "CPU 315-2 PN/DP",
            "firmware_version": "V3.2.17",
            "hardware_version": "14",
        },
))

_register_template(DeviceTemplate(
    id="siemens/s7-400/6es7-416-3es07-0ab0",
    vendor="Siemens",
    vendor_family="S7-400",
    model="6ES7 416-3ES07-0AB0",
    model_name="6ES7 416-3ES07-0AB0",
    device_type="plc",
    description="Siemens 6ES7 416-3ES07-0AB0",
    oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 0.5,
            "max_ms": 20.0,
            "mean_ms": 5.0,
            "std_dev_ms": 3.0,
            "distribution": "gaussian",
            "outlier_probability": 0.003,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 5, 6],
            "exception_probability": 0.0003,
            "timeout_probability": 0.00015,
        },
    supported_protocols=['modbus', 'profinet', 's7'],
    protocol_quirks={
            "s7_max_pdu_size": 960,
        },
    firmware_variants=[FirmwareVariant(
        version="V6.0.9",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6ES7 416-3ES07-0AB0",
            "major_minor_revision": "V6.0.9",
            "product_name": "CPU 416-3 PN/DP",
            "model_name": "S7-400",
        },
    profinet_identity={
            "vendor_id": 42,
            "device_id": 515,
            "device_type": "CPU 416-3 PN/DP",
            "station_name": "plc-s7400",
            "device_role": 2,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 416-3ES07-0AB0",
            "im0_hw_revision": 7,
            "im0_sw_revision": "V6.0.9",
        },
    s7_identity={
            "order_code": "6ES7 416-3ES07-0AB0",
            "module_type": "CPU 416-3 PN/DP",
            "firmware_version": "V6.0.9",
            "hardware_version": "7",
        },
))

_register_template(DeviceTemplate(
    id="siemens/s7-1500f/6es7-516-3fn02-0ab0",
    vendor="Siemens",
    vendor_family="S7-1500F",
    model="6ES7 516-3FN02-0AB0",
    model_name="6ES7 516-3FN02-0AB0",
    device_type="plc",
    description="Siemens 6ES7 516-3FN02-0AB0",
    oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "window_scaling": 7,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
    response_timing={
            "min_ms": 0.25,
            "max_ms": 8.0,
            "mean_ms": 1.8,
            "std_dev_ms": 1.2,
            "distribution": "gaussian",
            "outlier_probability": 0.001,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4, 5, 6],
            "exception_probability": 0.0002,
            "timeout_probability": 5e-05,
        },
    supported_protocols=['modbus', 'profinet', 's7'],
    protocol_quirks={
            "profinet_cycle_time_us": 500,
            "s7_max_pdu_size": 960,
            "profisafe_enabled": True,
            "f_host_mode": "standard",
        },
    firmware_variants=[FirmwareVariant(
        version="V3.0.3",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6ES7 516-3FN02-0AB0",
            "major_minor_revision": "V3.0.3",
            "vendor_url": "http://www.siemens.com",
            "product_name": "CPU 1516F-3 PN/DP",
            "model_name": "S7-1500F",
        },
    profinet_identity={
            "vendor_id": 42,
            "device_id": 783,
            "device_type": "CPU 1516F-3 PN/DP",
            "station_name": "plc-s71500f",
            "device_role": 2,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6ES7 516-3FN02-0AB0",
            "im0_hw_revision": 2,
            "im0_sw_revision": "V3.0.3",
        },
    s7_identity={
            "order_code": "6ES7 516-3FN02-0AB0",
            "module_type": "CPU 1516F-3 PN/DP",
            "firmware_version": "V3.0.3",
            "hardware_version": "2",
        },
))

_register_template(DeviceTemplate(
    id="siemens/scalance/6gk5-208-0ba00-2ab2",
    vendor="Siemens",
    vendor_family="SCALANCE",
    model="6GK5 208-0BA00-2AB2",
    model_name="6GK5 208-0BA00-2AB2",
    device_type="switch",
    description="Siemens 6GK5 208-0BA00-2AB2",
    oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 4096,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.5,
            "distribution": "gaussian",
            "outlier_probability": 0.003,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3],
            "exception_probability": 0.0003,
            "timeout_probability": 0.00015,
        },
    supported_protocols=['profinet', 'snmp'],
    firmware_variants=[FirmwareVariant(
        version="V5.2.6",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    profinet_identity={
            "vendor_id": 42,
            "device_id": 1792,
            "device_type": "SCALANCE XB208",
            "station_name": "switch-xb208",
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6GK5 208-0BA00-2AB2",
            "im0_hw_revision": 2,
            "im0_sw_revision": "V5.2.6",
        },
    snmp_identity={
            "sys_descr": "Siemens SCALANCE XB208 Industrial Ethernet Switch V5.2.6",
            "sys_object_id": "1.3.6.1.4.1.4329.6.1.5.1",
            "sys_name": "SCALANCE-XB208",
            "sys_location": "Industrial Network",
        },
))

_register_template(DeviceTemplate(
    id="siemens/sinamics/6sl3130-7te25-5aa3",
    vendor="Siemens",
    vendor_family="SINAMICS",
    model="6SL3130-7TE25-5AA3",
    model_name="6SL3130-7TE25-5AA3",
    device_type="drive",
    description="Siemens 6SL3130-7TE25-5AA3",
    oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 16384,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 0.5,
            "max_ms": 15.0,
            "mean_ms": 3.5,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0002,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['modbus', 'profinet'],
    firmware_variants=[FirmwareVariant(
        version="V5.2",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6SL3130-7TE25-5AA3",
            "major_minor_revision": "V5.2",
            "product_name": "SINAMICS S120",
            "model_name": "Servo Drive",
        },
    profinet_identity={
            "vendor_id": 42,
            "device_id": 1281,
            "device_type": "SINAMICS S120",
            "station_name": "drive-s120",
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6SL3130-7TE25-5AA3",
            "im0_hw_revision": 1,
            "im0_sw_revision": "V5.2",
        },
))

_register_template(DeviceTemplate(
    id="siemens/sinamics/6sl3210-1ke21-7uf1",
    vendor="Siemens",
    vendor_family="SINAMICS",
    model="6SL3210-1KE21-7UF1",
    model_name="6SL3210-1KE21-7UF1",
    device_type="drive",
    description="Siemens 6SL3210-1KE21-7UF1",
    oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 40.0,
            "mean_ms": 10.0,
            "std_dev_ms": 6.0,
            "distribution": "gaussian",
            "outlier_probability": 0.005,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0005,
            "timeout_probability": 0.0003,
        },
    supported_protocols=['modbus', 'profinet'],
    firmware_variants=[FirmwareVariant(
        version="V4.8",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Siemens AG",
            "product_code": "6SL3210-1KE21-7UF1",
            "major_minor_revision": "V4.8",
            "product_name": "SINAMICS G120C",
            "model_name": "Variable Speed Drive",
        },
    profinet_identity={
            "vendor_id": 42,
            "device_id": 1280,
            "device_type": "SINAMICS G120C",
            "station_name": "drive-g120c",
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6SL3210-1KE21-7UF1",
            "im0_hw_revision": 1,
            "im0_sw_revision": "V4.8",
        },
))

_register_template(DeviceTemplate(
    id="siemens/sinamics/6sl3544-0fb21-1fa0",
    vendor="Siemens",
    vendor_family="SINAMICS",
    model="6SL3544-0FB21-1FA0",
    model_name="6SL3544-0FB21-1FA0",
    device_type="drive",
    description="Siemens 6SL3544-0FB21-1FA0",
    oui_prefixes=['00:0E:8C', '00:1B:1B', '00:1C:06'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 3.0,
            "max_ms": 50.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
            "outlier_probability": 0.006,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0006,
            "timeout_probability": 0.0003,
        },
    supported_protocols=['profinet'],
    firmware_variants=[FirmwareVariant(
        version="V1.2",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    profinet_identity={
            "vendor_id": 42,
            "device_id": 1282,
            "device_type": "SINAMICS G115D",
            "station_name": "drive-g115d",
            "device_role": 1,
            "im0_manufacturer": "Siemens AG",
            "im0_order_id": "6SL3544-0FB21-1FA0",
            "im0_hw_revision": 1,
            "im0_sw_revision": "V1.2",
        },
))

_register_template(DeviceTemplate(
    id="siemens/traffic-management/cp-8000",
    vendor="Siemens",
    vendor_family="Traffic Management",
    model="CP-8000",
    model_name="CP-8000",
    device_type="traffic_controller",
    description="Siemens CP-8000",
    oui_prefixes=['00:1F:F8', '00:0E:8C', '64:00:6A'],
    tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 30.0,
            "mean_ms": 8.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
            "outlier_probability": 0.005,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "timeout_probability": 0.0003,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['snmp'],
    firmware_variants=[FirmwareVariant(
        version="V5.30",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Siemens SICAM CP-8000 Master Station V5.30",
            "sys_object_id": "1.3.6.1.4.1.4329.6.1.2",
            "sys_name": "CP8000-TMC-001",
            "sys_location": "Traffic Management Center",
            "ntcip_device_type": "master",
        },
))

_register_template(DeviceTemplate(
    id="siemens/tunnel-system/tcs-light",
    vendor="Siemens",
    vendor_family="Tunnel System",
    model="TCS-LIGHT",
    model_name="TCS-LIGHT",
    device_type="tunnel_controller",
    description="Siemens TCS-LIGHT",
    oui_prefixes=['00:1F:F8', '00:0E:8C', '64:00:6A'],
    tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 25.0,
            "mean_ms": 8.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
            "outlier_probability": 0.01,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "timeout_probability": 0.001,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['snmp'],
    firmware_variants=[FirmwareVariant(
        version="V2.0.5",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Siemens TCS Tunnel Lighting Controller V2.0.5",
            "sys_object_id": "1.3.6.1.4.1.4329.6.2.2",
            "sys_name": "LIGHT-001",
            "sys_location": "Tunnel Zone 1",
            "ntcip_device_type": "tunnel",
        },
))

_register_template(DeviceTemplate(
    id="siemens/tunnel-system/tcs-vent",
    vendor="Siemens",
    vendor_family="Tunnel System",
    model="TCS-VENT",
    model_name="TCS-VENT",
    device_type="tunnel_controller",
    description="Siemens TCS-VENT",
    oui_prefixes=['00:1F:F8', '00:0E:8C', '64:00:6A'],
    tcp_stack={
            "ttl": 128,
            "window_size": 65535,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 3.0,
            "max_ms": 30.0,
            "mean_ms": 10.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
            "outlier_probability": 0.01,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "timeout_probability": 0.001,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['snmp'],
    firmware_variants=[FirmwareVariant(
        version="V2.1.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Siemens TCS Tunnel Ventilation Controller V2.1.0",
            "sys_object_id": "1.3.6.1.4.1.4329.6.2.1",
            "sys_name": "VENT-001",
            "sys_location": "Tunnel Section A",
            "ntcip_device_type": "tunnel",
        },
))

_register_template(DeviceTemplate(
    id="siemens/scalance/x-200",
    vendor="Siemens",
    vendor_family="SCALANCE",
    model="X-200",
    model_name="X-200",
    device_type="switch",
    description="Siemens X-200",
    oui_prefixes=['00:1F:F8', '00:0E:8C', '64:00:6A'],
    tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 1.0,
            "max_ms": 15.0,
            "mean_ms": 4.0,
            "std_dev_ms": 2.0,
            "distribution": "gaussian",
            "outlier_probability": 0.005,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "timeout_probability": 0.0003,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['snmp'],
    firmware_variants=[FirmwareVariant(
        version="V5.2.4",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Siemens SCALANCE X-200 Industrial Ethernet Switch V5.2.4",
            "sys_object_id": "1.3.6.1.4.1.4329.3.1.1",
            "sys_name": "ITS-SW-001",
            "sys_location": "Field Cabinet",
            "sys_services": 78,
        },
))

_register_template(DeviceTemplate(
    id="siemens/scalance/xm-400",
    vendor="Siemens",
    vendor_family="SCALANCE",
    model="XM-400",
    model_name="XM-400",
    device_type="traffic_controller",
    description="Siemens XM-400",
    oui_prefixes=['00:1F:F8', '00:0E:8C', '64:00:6A'],
    tcp_stack={
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 0.5,
            "max_ms": 10.0,
            "mean_ms": 3.0,
            "std_dev_ms": 1.5,
            "distribution": "gaussian",
            "outlier_probability": 0.003,
            "outlier_multiplier": 4.0,
        },
    error_behavior={
            "timeout_probability": 0.0002,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['snmp'],
    firmware_variants=[FirmwareVariant(
        version="V6.3.0",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    snmp_identity={
            "sys_descr": "Siemens SCALANCE XM-400 Industrial Ethernet Switch V6.3.0",
            "sys_object_id": "1.3.6.1.4.1.4329.3.2.1",
            "sys_name": "CORE-SW-001",
            "sys_location": "ITS Equipment Room",
            "sys_services": 78,
        },
))


# --- Trane (1 entries) ---

_register_template(DeviceTemplate(
    id="trane/tracer/uc600",
    vendor="Trane",
    vendor_family="Tracer",
    model="UC600",
    model_name="UC600",
    device_type="building_controller",
    description="Trane UC600",
    oui_prefixes=['00:0D:AD', '00:1C:C0'],
    tcp_stack={},
    response_timing={
            "min_ms": 12.0,
            "max_ms": 120.0,
            "mean_ms": 35.0,
            "std_dev_ms": 20.0,
            "distribution": "lognormal",
            "outlier_probability": 0.005,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "timeout_probability": 0.002,
            "retry_behavior": True,
            "max_retries": 3,
        },
    supported_protocols=['bacnet'],
    firmware_variants=[FirmwareVariant(
        version="3.5.2",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    bacnet_identity={
            "vendor_id": 97,
            "vendor_name": "Trane",
            "model_name": "UC600 Unit Controller",
            "firmware_revision": "3.5.2",
            "application_software_version": "3.5",
            "protocol_version": 1,
            "protocol_revision": 14,
            "max_apdu_length": 480,
            "segmentation_supported": 3,
            "device_instance": 4002,
            "object_name": "UC600-AHU-001",
        },
))


# --- Yokogawa (4 entries) ---

_register_template(DeviceTemplate(
    id="yokogawa/centum-vp/centum-vp",
    vendor="Yokogawa",
    vendor_family="CENTUM VP",
    model="CENTUM VP",
    model_name="CENTUM VP",
    device_type="dcs_controller",
    description="Yokogawa CENTUM VP",
    oui_prefixes=['00:00:C1', '00:02:E0'],
    tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 3.0,
            "max_ms": 35.0,
            "mean_ms": 12.0,
            "std_dev_ms": 6.0,
            "distribution": "gaussian",
            "outlier_probability": 0.001,
            "outlier_multiplier": 3.0,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0002,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="R6.08.00",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Yokogawa Electric Corporation",
            "product_code": "CENTUM-VP",
            "major_minor_revision": "R6.08.00",
            "vendor_url": "http://www.yokogawa.com",
            "product_name": "CENTUM VP Field Control Station",
            "model_name": "CENTUM VP",
        },
))

_register_template(DeviceTemplate(
    id="yokogawa/prosafe-rs/prosafe-rs",
    vendor="Yokogawa",
    vendor_family="ProSafe-RS",
    model="ProSafe-RS",
    model_name="ProSafe-RS",
    device_type="dcs_controller",
    description="Yokogawa ProSafe-RS",
    oui_prefixes=['00:00:C1', '00:02:E0'],
    tcp_stack={
            "ttl": 64,
            "window_size": 32768,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 2.0,
            "max_ms": 25.0,
            "mean_ms": 8.0,
            "std_dev_ms": 4.0,
            "distribution": "gaussian",
            "outlier_probability": 0.0005,
            "outlier_multiplier": 2.5,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0001,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="R4.05.00",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Yokogawa Electric Corporation",
            "product_code": "ProSafe-RS",
            "major_minor_revision": "R4.05.00",
            "vendor_url": "http://www.yokogawa.com",
            "product_name": "ProSafe-RS Safety Instrumented System",
            "model_name": "ProSafe-RS",
        },
))

_register_template(DeviceTemplate(
    id="yokogawa/rc400g/rc400g",
    vendor="Yokogawa",
    vendor_family="RC400G",
    model="RC400G",
    model_name="RC400G",
    device_type="rtu",
    description="Yokogawa RC400G",
    oui_prefixes=['00:00:C1', '00:02:E0'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 8.0,
            "max_ms": 65.0,
            "mean_ms": 22.0,
            "std_dev_ms": 11.0,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0003,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="1.05",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Yokogawa Electric Corporation",
            "product_code": "RC400G",
            "major_minor_revision": "V1.05",
            "vendor_url": "http://www.yokogawa.com",
            "product_name": "RC400G Residual Chlorine Analyzer",
            "model_name": "Chlorine Analyzer",
        },
))

_register_template(DeviceTemplate(
    id="yokogawa/sc450g/sc450g",
    vendor="Yokogawa",
    vendor_family="SC450G",
    model="SC450G",
    model_name="SC450G",
    device_type="rtu",
    description="Yokogawa SC450G",
    oui_prefixes=['00:00:C1', '00:02:E0'],
    tcp_stack={
            "ttl": 64,
            "window_size": 8192,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": False,
        },
    response_timing={
            "min_ms": 8.0,
            "max_ms": 60.0,
            "mean_ms": 20.0,
            "std_dev_ms": 10.0,
            "distribution": "gaussian",
            "outlier_probability": 0.002,
            "outlier_multiplier": 3.5,
        },
    error_behavior={
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.0003,
            "timeout_probability": 0.0001,
        },
    supported_protocols=['modbus'],
    firmware_variants=[FirmwareVariant(
        version="1.04",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Yokogawa Electric Corporation",
            "product_code": "SC450G",
            "major_minor_revision": "V1.04",
            "vendor_url": "http://www.yokogawa.com",
            "product_name": "SC450G Turbidity Analyzer",
            "model_name": "Turbidity Analyzer",
        },
))


# --- Zebra (2 entries) ---

_register_template(DeviceTemplate(
    id="zebra/fixed-rfid/fx7500",
    vendor="Zebra",
    vendor_family="Fixed RFID",
    model="FX7500",
    model_name="FX7500",
    device_type="rfid_reader",
    description="Zebra FX7500",
    oui_prefixes=['00:A0:F8', '00:23:68', 'AC:3F:A4'],
    tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 45.0,
            "mean_ms": 15.0,
            "std_dev_ms": 8.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus', 'snmp'],
    firmware_variants=[FirmwareVariant(
        version="3.28.10",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Zebra Technologies Corporation",
            "product_code": "FX7500",
            "major_minor_revision": "3.28.10",
            "product_name": "Zebra FX7500 4-Port RFID Reader",
            "model_name": "FX7500",
        },
    snmp_identity={
            "sys_descr": "Zebra FX7500 Fixed RFID Reader V3.28.10",
            "sys_object_id": "1.3.6.1.4.1.10642.1.2",
            "sys_name": "FX7500-001",
        },
))

_register_template(DeviceTemplate(
    id="zebra/fixed-rfid/fx9600",
    vendor="Zebra",
    vendor_family="Fixed RFID",
    model="FX9600",
    model_name="FX9600",
    device_type="rfid_reader",
    description="Zebra FX9600",
    oui_prefixes=['00:A0:F8', '00:23:68', 'AC:3F:A4'],
    tcp_stack={
            "ttl": 64,
            "window_size": 29200,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
        },
    response_timing={
            "min_ms": 5.0,
            "max_ms": 50.0,
            "mean_ms": 18.0,
            "std_dev_ms": 10.0,
            "distribution": "gaussian",
        },
    supported_protocols=['modbus', 'snmp'],
    firmware_variants=[FirmwareVariant(
        version="3.29.15",
        release_date=date(2024, 1, 1),
        is_default=True,
        is_latest=True,
    )],
    modbus_identity={
            "vendor_name": "Zebra Technologies Corporation",
            "product_code": "FX9600",
            "major_minor_revision": "3.29.15",
            "product_name": "Zebra FX9600 8-Port RFID Reader",
            "model_name": "FX9600",
        },
    snmp_identity={
            "sys_descr": "Zebra FX9600 Fixed RFID Reader V3.29.15",
            "sys_object_id": "1.3.6.1.4.1.10642.1.1",
            "sys_name": "FX9600-001",
            "sys_location": "Portal",
            "sys_contact": "rfid@warehouse.local",
        },
))





# =============================================================================
# Template-to-Fingerprint Conversion Functions
# =============================================================================
# These functions provide backwards compatibility with existing code that
# expects fingerprint dictionaries (FingerprintApplicator, scenario templates,
# AI scenario generator).


def get_template_by_vendor_model(vendor: str, model: str) -> DeviceTemplate | None:
    """Find a template by vendor and model (case-insensitive).

    Performs flexible matching on:
    - model field (exact, e.g., "6ES7 516-3AN02-0AB0")
    - model_name field (e.g., "CPU 1516-3 PN/DP")

    Args:
        vendor: Vendor name (case-insensitive)
        model: Model identifier or name

    Returns:
        DeviceTemplate or None if not found
    """
    vendor_lower = vendor.lower()
    model_lower = model.lower()

    for template in DEVICE_TEMPLATES.values():
        if template.vendor.lower() != vendor_lower:
            continue

        # Check model field (exact)
        if template.model.lower() == model_lower:
            return template

        # Check model_name field
        if template.model_name.lower() == model_lower:
            return template

        # Check partial match on model
        if model_lower in template.model.lower():
            return template

        # Check partial match on model_name
        if model_lower in template.model_name.lower():
            return template

    return None


def get_fingerprint_from_template(
    template_id: str,
    firmware_version: str | None = None,
    include_instance: bool = False,
    serial_number: str | None = None,
    station_name: str | None = None,
) -> dict[str, Any] | None:
    """Convert a device template to fingerprint dictionary.

    This provides backwards compatibility with existing code that
    expects fingerprint dictionaries (FingerprintApplicator, scenario
    templates, AI scenario generator).

    Args:
        template_id: Template ID (e.g., "siemens/s7-1500/cpu-1516-3")
        firmware_version: Specific firmware or None for default
        include_instance: Whether to generate unique instance values
        serial_number: Override serial number
        station_name: Override station name

    Returns:
        Fingerprint dictionary compatible with FingerprintApplicator:
        {
            "vendor": "Siemens",
            "vendor_family": "S7-1500",
            "model": "6ES7 516-3AN02-0AB0",
            "firmware_version": "V3.0.3",
            "oui_prefixes": [...],
            "tcp_stack": {...},
            "response_timing": {...},
            "error_behavior": {...},
            "modbus_identity": {...},
            "profinet_identity": {...},
            ...
        }
    """
    template = get_template_by_id(template_id)
    if not template:
        return None

    # Get firmware variant
    if firmware_version:
        firmware = template.get_firmware_by_version(firmware_version)
    else:
        firmware = template.get_default_firmware()

    if not firmware:
        return None

    # Build the fingerprint dictionary
    fingerprint: dict[str, Any] = {
        "vendor": template.vendor,
        "vendor_family": template.vendor_family,
        "model": template.model,
        "firmware_version": firmware.version,
        "oui_prefixes": list(template.oui_prefixes),
        "tcp_stack": dict(template.tcp_stack) if template.tcp_stack else {},
        "response_timing": dict(template.response_timing) if template.response_timing else {},
        "error_behavior": dict(template.error_behavior) if template.error_behavior else {},
        "protocol_quirks": dict(template.protocol_quirks) if template.protocol_quirks else {},
        "is_builtin": template.is_builtin,
    }

    # Add protocol identities with firmware overrides
    protocol_identities = [
        ("modbus_identity", template.modbus_identity),
        ("ethernet_ip_identity", template.ethernet_ip_identity),
        ("profinet_identity", template.profinet_identity),
        ("s7_identity", template.s7_identity),
        ("bacnet_identity", template.bacnet_identity),
        ("snmp_identity", template.snmp_identity),
        ("opc_ua_identity", template.opc_ua_identity),
    ]

    for key, base_identity in protocol_identities:
        if base_identity:
            # Start with base identity
            merged = dict(base_identity)

            # Apply firmware overrides
            fw_override = firmware.identity_overrides.get(key, {})
            if fw_override:
                merged.update(fw_override)

            # Apply version fields
            if key == "modbus_identity" and "major_minor_revision" not in merged:
                merged["major_minor_revision"] = firmware.version
            elif key == "profinet_identity" and "im0_sw_revision" not in merged:
                merged["im0_sw_revision"] = firmware.version
            elif key == "ethernet_ip_identity":
                parts = firmware.version.lstrip("V").split(".")
                if len(parts) >= 2:
                    try:
                        if "revision_major" not in merged:
                            merged["revision_major"] = int(parts[0])
                        if "revision_minor" not in merged:
                            merged["revision_minor"] = int(parts[1])
                    except ValueError:
                        pass

            # Add instance values if requested
            if include_instance:
                if serial_number:
                    merged["serial_number"] = serial_number
                elif template.instance_rules:
                    merged["serial_number"] = generate_serial_number(
                        template.instance_rules.serial_format
                    )

                if station_name:
                    merged["station_name"] = station_name
                elif template.instance_rules:
                    merged["station_name"] = generate_station_name(
                        template.instance_rules.station_name_pattern,
                        role=template.device_type,
                        vendor_short=template.instance_rules.vendor_short,
                        model_short=template.instance_rules.model_short,
                    )

            fingerprint[key] = merged
        else:
            fingerprint[key] = None

    return fingerprint


def get_fingerprint_by_vendor_model(
    vendor: str,
    model: str,
    firmware_version: str | None = None,
) -> dict[str, Any] | None:
    """Get fingerprint dictionary by vendor/model.

    Searches DEVICE_TEMPLATES registry (single source of truth).

    Args:
        vendor: Vendor name (case-insensitive)
        model: Model identifier or name
        firmware_version: Specific firmware or None for default

    Returns:
        Fingerprint dictionary compatible with FingerprintApplicator,
        or None if no matching fingerprint found
    """
    # Try FingerprintCache first (O(1) lookup, handles fuzzy matching)
    from app.services.fingerprint_cache import get_fingerprint_cache
    cache = get_fingerprint_cache()
    result = cache.get_by_vendor_model(vendor, model)
    if result:
        return result.copy()

    # Direct template lookup as fallback
    template = get_template_by_vendor_model(vendor, model)
    if template:
        return get_fingerprint_from_template(
            template.id,
            firmware_version=firmware_version,
        )

    return None


def get_fingerprints_by_vendor(vendor: str) -> list[dict[str, Any]]:
    """Get all fingerprint dictionaries for a vendor.

    Args:
        vendor: Vendor name (case-insensitive)

    Returns:
        List of fingerprint dictionaries for all templates from this vendor
    """
    fingerprints = []
    for template in get_templates_by_vendor(vendor):
        fp = get_fingerprint_from_template(template.id)
        if fp:
            fingerprints.append(fp)
    return fingerprints


def get_all_fingerprints() -> list[dict[str, Any]]:
    """Get all fingerprint dictionaries from the template library.

    Converts all registered DeviceTemplate entries to fingerprint dictionaries
    compatible with FingerprintApplicator.

    Returns:
        List of fingerprint dictionaries with complete protocol identities
    """
    return [
        fp for fp in (
            get_fingerprint_from_template(t.id)
            for t in get_all_templates()
        ) if fp is not None
    ]


# =============================================================================
# Database Adapter Functions
# =============================================================================
# These functions query the DeviceTemplate DB table and return fingerprint-compatible
# dictionaries. They enable gradual migration from Python dataclass library to DB.


def template_db_to_fingerprint_dict(template) -> dict[str, Any] | None:
    """Convert a DeviceTemplate DB model to a fingerprint dictionary.

    This adapter function allows services to work with either the Python dataclass
    library or the DeviceTemplate DB table using a consistent interface.

    Args:
        template: DeviceTemplate DB model instance

    Returns:
        Fingerprint dictionary compatible with FingerprintApplicator,
        or None if conversion fails.
    """
    if template is None:
        return None

    try:
        fp: dict[str, Any] = {
            "vendor": template.vendor,
            "vendor_family": template.vendor_family,
            "model": template.model,
            "firmware_version": template.firmware_version,
            "oui_prefixes": list(template.oui_patterns or []),
            "tcp_stack": dict(template.tcp_signature or {}),
            "is_builtin": template.source == "vendor_builtin",
        }

        # Extract response timing
        if template.response_timings:
            fp["response_timing"] = template.response_timings.get(
                "default",
                next(iter(template.response_timings.values()), {})
            )
        else:
            fp["response_timing"] = {}

        # Error behavior and protocol quirks
        fp["error_behavior"] = dict(template.error_behavior or {})
        fp["protocol_quirks"] = dict(template.protocol_quirks or {})

        # Protocol identities (check both unified and legacy columns)
        for protocol in ["modbus", "ethernet_ip", "profinet", "s7", "snmp", "bacnet", "opc_ua"]:
            identity = template.get_protocol_identity(protocol)
            fp[f"{protocol}_identity"] = dict(identity) if identity else None

        return fp

    except Exception:
        return None


def get_fingerprint_from_db_sync(
    vendor: str,
    model: str,
) -> dict[str, Any] | None:
    """Query DeviceTemplate DB (sync) and return fingerprint dict.

    This function provides a sync interface for querying the DeviceTemplate
    DB table. Use this in non-async contexts.

    Args:
        vendor: Vendor name (case-insensitive)
        model: Model identifier

    Returns:
        Fingerprint dictionary or None if not found.
    """
    try:
        from sqlalchemy import func

        from app.core.database import get_sync_session
        from app.models.device_template import DeviceTemplate

        with get_sync_session() as db:
            template = db.query(DeviceTemplate).filter(
                func.lower(DeviceTemplate.vendor) == vendor.lower(),
                DeviceTemplate.model == model,
                DeviceTemplate.is_active == True,  # noqa: E712
            ).first()

            return template_db_to_fingerprint_dict(template)

    except Exception:
        return None


async def get_fingerprint_from_db_async(
    db,
    vendor: str,
    model: str,
) -> dict[str, Any] | None:
    """Query DeviceTemplate DB (async) and return fingerprint dict.

    This function provides an async interface for querying the DeviceTemplate
    DB table. Use this in async route handlers.

    Args:
        db: AsyncSession instance
        vendor: Vendor name (case-insensitive)
        model: Model identifier

    Returns:
        Fingerprint dictionary or None if not found.
    """
    try:
        from sqlalchemy import func, select

        from app.models.device_template import DeviceTemplate

        result = await db.execute(
            select(DeviceTemplate).where(
                func.lower(DeviceTemplate.vendor) == vendor.lower(),
                DeviceTemplate.model == model,
                DeviceTemplate.is_active == True,  # noqa: E712
            )
        )
        template = result.scalar_one_or_none()

        return template_db_to_fingerprint_dict(template)

    except Exception:
        return None


def get_fingerprint_with_fallback(
    vendor: str,
    model: str,
    firmware_version: str | None = None,
) -> dict[str, Any] | None:
    """Get fingerprint from DB with fallback to Python dataclass library.

    This function first tries to query the DeviceTemplate DB table,
    then falls back to the Python dataclass library if not found.
    This enables gradual migration without breaking existing code.

    Args:
        vendor: Vendor name (case-insensitive)
        model: Model identifier
        firmware_version: Specific firmware or None for default

    Returns:
        Fingerprint dictionary or None if not found in either source.
    """
    # Try DB first
    fp = get_fingerprint_from_db_sync(vendor, model)
    if fp:
        return fp

    # Fall back to Python dataclass library
    return get_fingerprint_by_vendor_model(vendor, model, firmware_version)
