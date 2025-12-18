"""Fingerprint applicator for applying vendor fingerprints to packet generation.

This module provides functions to apply vendor-specific fingerprints
during packet generation, including:
- TCP/IP stack characteristics (TTL, window size, MSS, etc.)
- Response timing with realistic distributions
- Protocol-specific identity responses (Modbus FC 43, EtherNet/IP ListIdentity)
- Error injection based on vendor behavior
"""

import logging
import random
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TcpOptions:
    """TCP options to apply to outgoing packets."""

    ttl: int = 64
    window_size: int = 65535
    mss: int = 1460
    window_scaling: int | None = None
    sack_permitted: bool = True
    timestamps_enabled: bool = True
    df_flag: bool = True


@dataclass
class TimingSample:
    """A sampled timing value with metadata."""

    delay_ms: float
    is_outlier: bool = False
    is_timeout: bool = False


class FingerprintApplicator:
    """Applies vendor fingerprints to packet generation.

    This service takes vendor fingerprint data and applies it during
    packet generation to produce realistic, vendor-specific traffic.

    Supports vulnerability overrides for CVE simulation - when provided,
    protocol identity responses will include vulnerable firmware versions
    detectable by security scanners like Cisco Cyber Vision.
    """

    def __init__(
        self,
        fingerprint: dict[str, Any],
        vulnerability_override: dict[str, Any] | None = None,
    ):
        """Initialize with a fingerprint configuration.

        Args:
            fingerprint: Vendor fingerprint dictionary with tcp_stack,
                        response_timing, error_behavior, etc.
            vulnerability_override: Optional CVE vulnerability overrides that
                        modify protocol identity responses to include vulnerable
                        firmware versions. See VulnerableFingerprintVariant model.
        """
        self.fingerprint = fingerprint
        self.vulnerability_override = vulnerability_override or {}
        self.tcp_stack = fingerprint.get("tcp_stack", {})
        self.response_timing = fingerprint.get("response_timing", {})
        self.error_behavior = fingerprint.get("error_behavior", {})
        self.modbus_identity = dict(fingerprint.get("modbus_identity", {}))
        self.ethernet_ip_identity = dict(fingerprint.get("ethernet_ip_identity", {}))
        self.profinet_identity = dict(fingerprint.get("profinet_identity", {}))
        self.s7_identity = dict(fingerprint.get("protocol_quirks", {}).get("s7_identity", {}))
        self.protocol_quirks = fingerprint.get("protocol_quirks", {})

        # Apply vulnerability overrides if provided
        if vulnerability_override:
            self._apply_vulnerability_overrides()

        # Initialize RNG for reproducibility if needed
        self._rng = np.random.default_rng()

    def _apply_vulnerability_overrides(self) -> None:
        """Apply CVE-specific firmware version overrides to protocol identities.

        This modifies the protocol identity responses to include vulnerable
        firmware version strings that security scanners will detect.

        Supports both key naming conventions:
        - With _override suffix: modbus_identity_override (from DB model)
        - Without suffix: modbus_identity (from extract_identity_overrides)
        """
        override = self.vulnerability_override

        # Apply Modbus identity overrides (support both key formats)
        modbus_override = (
            override.get("modbus_identity_override") or
            override.get("modbus_identity")
        )
        if modbus_override:
            self.modbus_identity.update(modbus_override)
            logger.debug(f"Applied Modbus vulnerability override: {modbus_override}")

        # Apply EtherNet/IP identity overrides (support both key formats)
        eip_override = (
            override.get("ethernet_ip_identity_override") or
            override.get("ethernet_ip_identity")
        )
        if eip_override:
            self.ethernet_ip_identity.update(eip_override)
            logger.debug(f"Applied EtherNet/IP vulnerability override: {eip_override}")

        # Apply PROFINET identity overrides (support both key formats)
        pn_override = (
            override.get("profinet_identity_override") or
            override.get("profinet_identity")
        )
        if pn_override:
            self.profinet_identity.update(pn_override)
            logger.debug(f"Applied PROFINET vulnerability override: {pn_override}")

        # Apply S7 identity overrides (support both key formats)
        s7_override = (
            override.get("s7_identity_override") or
            override.get("s7_identity")
        )
        if s7_override:
            self.s7_identity.update(s7_override)
            logger.debug(f"Applied S7 vulnerability override: {s7_override}")

    @property
    def is_vulnerable(self) -> bool:
        """Check if vulnerability overrides are active."""
        return bool(self.vulnerability_override)

    @property
    def cve_id(self) -> str | None:
        """Get the CVE ID if vulnerability overrides are active."""
        return self.vulnerability_override.get("cve_id")

    @property
    def vulnerable_firmware_version(self) -> str | None:
        """Get the vulnerable firmware version if overrides are active."""
        return self.vulnerability_override.get("firmware_version")

    def get_tcp_options(self) -> TcpOptions:
        """Get TCP options based on the fingerprint.

        Returns:
            TcpOptions with vendor-specific stack characteristics
        """
        return TcpOptions(
            ttl=self.tcp_stack.get("ttl", 64),
            window_size=self.tcp_stack.get("window_size", 65535),
            mss=self.tcp_stack.get("mss", 1460),
            window_scaling=self.tcp_stack.get("window_scaling"),
            sack_permitted=self.tcp_stack.get("sack_permitted", True),
            timestamps_enabled=self.tcp_stack.get("timestamps_enabled", True),
            df_flag=self.tcp_stack.get("df_flag", True),
        )

    def get_response_delay(self) -> TimingSample:
        """Sample a response delay from the timing distribution.

        Returns:
            TimingSample with delay and metadata
        """
        timing = self.response_timing
        error = self.error_behavior

        # Check for timeout (no response)
        timeout_prob = error.get("timeout_probability", 0)
        if timeout_prob > 0 and random.random() < timeout_prob:
            return TimingSample(delay_ms=0, is_timeout=True)

        # Get distribution parameters
        min_ms = timing.get("min_ms", 1.0)
        max_ms = timing.get("max_ms", 50.0)
        mean_ms = timing.get("mean_ms", 10.0)
        std_dev_ms = timing.get("std_dev_ms", 5.0)
        distribution = timing.get("distribution", "gaussian")
        outlier_prob = timing.get("outlier_probability", 0.01)
        outlier_mult = timing.get("outlier_multiplier", 3.0)

        # Check for outlier
        is_outlier = random.random() < outlier_prob

        # Sample from distribution
        if distribution == "uniform":
            delay = self._rng.uniform(min_ms, max_ms)
        elif distribution == "gaussian":
            delay = self._rng.normal(mean_ms, std_dev_ms)
        elif distribution == "exponential":
            # Scale exponential to match mean
            delay = self._rng.exponential(mean_ms)
        elif distribution == "gamma":
            # Shape parameter from std_dev/mean ratio
            shape = (mean_ms / std_dev_ms) ** 2
            scale = mean_ms / shape
            delay = self._rng.gamma(shape, scale)
        elif distribution == "lognormal":
            # Convert mean/std to lognormal parameters
            mu = np.log(mean_ms**2 / np.sqrt(std_dev_ms**2 + mean_ms**2))
            sigma = np.sqrt(np.log(1 + (std_dev_ms**2 / mean_ms**2)))
            delay = self._rng.lognormal(mu, sigma)
        else:
            delay = mean_ms

        # Apply outlier multiplier
        if is_outlier:
            delay *= outlier_mult

        # Clamp to min/max (with outlier allowance)
        if is_outlier:
            delay = max(min_ms, min(max_ms * outlier_mult, delay))
        else:
            delay = max(min_ms, min(max_ms, delay))

        return TimingSample(delay_ms=delay, is_outlier=is_outlier)

    def should_inject_error(self) -> bool:
        """Determine if an error should be injected.

        Returns:
            True if an error response should be generated
        """
        error_prob = self.error_behavior.get("exception_probability", 0)
        return error_prob > 0 and random.random() < error_prob

    def get_random_exception_code(self) -> int:
        """Get a random Modbus exception code from supported codes.

        Returns:
            Exception code (1-6, 10, 11)
        """
        codes = self.error_behavior.get("supported_exception_codes", [1, 2, 3, 4])
        return random.choice(codes) if codes else 1

    def should_timeout(self) -> bool:
        """Determine if a timeout (no response) should occur.

        Returns:
            True if the request should timeout
        """
        timeout_prob = self.error_behavior.get("timeout_probability", 0)
        return timeout_prob > 0 and random.random() < timeout_prob

    def should_retry(self) -> bool:
        """Determine if retry behavior is enabled.

        Returns:
            True if retries should be simulated
        """
        return self.error_behavior.get("retry_behavior", False)

    def get_max_retries(self) -> int:
        """Get maximum retry count.

        Returns:
            Maximum number of retries
        """
        return self.error_behavior.get("max_retries", 3)

    # ========== Modbus Identity (FC 43) ==========

    def build_modbus_mei_response(self, device_id_code: int = 1) -> bytes:
        """Build a Modbus FC 43 Read Device Identification response.

        Args:
            device_id_code: 1=basic, 2=regular, 3=extended, 4=specific

        Returns:
            MEI response payload bytes
        """
        identity = self.modbus_identity
        if not identity:
            return b""

        # Object definitions based on Modbus spec
        objects = []

        if device_id_code >= 1:  # Basic
            if "vendor_name" in identity:
                objects.append((0x00, identity["vendor_name"]))
            if "product_code" in identity:
                objects.append((0x01, identity["product_code"]))
            if "major_minor_revision" in identity:
                objects.append((0x02, identity["major_minor_revision"]))

        if device_id_code >= 2:  # Regular
            if "vendor_url" in identity:
                objects.append((0x03, identity["vendor_url"]))
            if "product_name" in identity:
                objects.append((0x04, identity["product_name"]))
            if "model_name" in identity:
                objects.append((0x05, identity["model_name"]))

        if device_id_code >= 3:  # Extended
            if "user_application_name" in identity:
                objects.append((0x06, identity["user_application_name"]))

        # Build response bytes
        # Format: MEI type (0x0E) + Read Device ID code + Conformity Level +
        #         More Follows + Next Object ID + Number of Objects + Object data
        mei_type = 0x0E
        conformity = 0x03 if device_id_code >= 3 else (0x02 if device_id_code >= 2 else 0x01)
        more_follows = 0x00
        next_object_id = 0x00
        num_objects = len(objects)

        response = bytes([mei_type, device_id_code, conformity, more_follows, next_object_id, num_objects])

        for obj_id, obj_value in objects:
            obj_bytes = obj_value.encode("utf-8") if isinstance(obj_value, str) else bytes(obj_value)
            response += bytes([obj_id, len(obj_bytes)]) + obj_bytes

        return response

    def get_modbus_vendor_name(self) -> str:
        """Get vendor name for Modbus identity."""
        return self.modbus_identity.get("vendor_name", "Unknown Vendor")

    def get_modbus_product_code(self) -> str:
        """Get product code for Modbus identity."""
        return self.modbus_identity.get("product_code", "Unknown")

    # ========== EtherNet/IP Identity ==========

    def build_enip_list_identity_response(self, socket_addr: tuple[str, int] | None = None) -> bytes:
        """Build an EtherNet/IP ListIdentity response CPF item.

        Args:
            socket_addr: Optional (IP, port) tuple for response

        Returns:
            CPF item bytes for ListIdentity response
        """
        identity = self.ethernet_ip_identity
        if not identity:
            return b""

        import struct

        vendor_id = identity.get("vendor_id", 1)
        device_type = identity.get("device_type", 14)
        product_code = identity.get("product_code", 1)
        revision_major = identity.get("revision_major", 1)
        revision_minor = identity.get("revision_minor", 0)
        serial_number = identity.get("serial_number", 0x12345678)
        product_name = identity.get("product_name", "Unknown Device")
        state = identity.get("state", 3)

        # Encode product name (length-prefixed string)
        product_name_bytes = product_name.encode("utf-8")[:32]
        product_name_len = len(product_name_bytes)

        # Socket address info
        if socket_addr:
            ip_str, port = socket_addr
            ip_parts = [int(x) for x in ip_str.split(".")]
        else:
            ip_parts = [192, 168, 1, 100]
            port = 44818

        # Build identity item
        # Type ID: 0x000C (ListIdentity response)
        # Length: varies
        identity_data = struct.pack(
            "<HHHHBBIHB",
            identity.get("encap_protocol_version", 1),  # Encap version
            identity.get("sin_family", 2),  # Socket family
            port,  # Port (big endian in struct)
            (ip_parts[0] << 24) | (ip_parts[1] << 16) | (ip_parts[2] << 8) | ip_parts[3],  # IP
            0,  # Sin zero (8 bytes padding follows in full struct)
            0,
            vendor_id,  # Vendor ID
            device_type,  # Device Type
            product_code,  # Product Code
        )

        # Add revision and status
        identity_data += struct.pack("<BBH", revision_major, revision_minor, 0x0030)  # Status
        identity_data += struct.pack("<I", serial_number)
        identity_data += struct.pack("<B", product_name_len) + product_name_bytes
        identity_data += struct.pack("<B", state)

        return identity_data

    def get_enip_vendor_id(self) -> int:
        """Get ODVA Vendor ID."""
        return self.ethernet_ip_identity.get("vendor_id", 1)

    def get_enip_device_type(self) -> int:
        """Get CIP Device Type."""
        return self.ethernet_ip_identity.get("device_type", 14)

    # ========== CIP Identity Object (Deep Fingerprinting) ==========

    def get_cip_identity_object(self) -> dict[str, Any]:
        """Get complete CIP Identity Object attributes (1-20) for deep fingerprinting.

        This combines basic ethernet_ip_identity with extended cip_identity_object
        attributes used by Cisco Cyber Vision for detailed device identification.

        Returns:
            Dictionary with all CIP Identity Object attributes
        """
        # Start with basic identity data
        identity = {
            "vendor_id": self.ethernet_ip_identity.get("vendor_id", 1),
            "device_type": self.ethernet_ip_identity.get("device_type", 14),
            "product_code": self.ethernet_ip_identity.get("product_code", 1),
            "revision": {
                "major": self.ethernet_ip_identity.get("revision_major", 1),
                "minor": self.ethernet_ip_identity.get("revision_minor", 0),
            },
            "status": self.ethernet_ip_identity.get("status", 0x0030),
            "serial_number": self.ethernet_ip_identity.get("serial_number", 0x12345678),
            "product_name": self.ethernet_ip_identity.get("product_name", "Unknown Device"),
            "state": self.ethernet_ip_identity.get("state", 3),
        }

        # Merge with extended CIP Identity Object attributes from fingerprint
        cip_identity = self.fingerprint.get("cip_identity_object", {})
        if cip_identity:
            identity.update({
                "status": cip_identity.get("status", identity["status"]),
                "configuration_consistency_value": cip_identity.get(
                    "configuration_consistency_value", 0
                ),
                "heartbeat_interval": cip_identity.get("heartbeat_interval", 250),
                "active_language": cip_identity.get("active_language", "English"),
                "supported_languages": cip_identity.get("supported_languages", ["English"]),
                "protection_mode": cip_identity.get("protection_mode", 0),
                "maximum_cip_connections": cip_identity.get("maximum_cip_connections", 32),
            })

        # Apply vulnerability overrides if present
        cip_override = self.vulnerability_override.get("cip_identity_override", {})
        if cip_override:
            identity.update(cip_override)
            logger.debug(f"Applied CIP Identity vulnerability override: {cip_override}")

        return identity

    def get_connection_manager_object(self) -> dict[str, Any]:
        """Get Connection Manager Object (Class 0x06) attributes.

        Returns connection parameters used by Cyber Vision for capability detection.

        Returns:
            Dictionary with Connection Manager attributes
        """
        default = {
            "max_connections": 32,
            "connection_timeout_multiplier": 32,
            "transport_class_trigger": 0xA3,
            "supported_connection_types": ["implicit", "explicit"],
        }

        cm_object = self.fingerprint.get("connection_manager_object", {})
        return {**default, **cm_object}

    def get_assembly_objects(self) -> dict[str, Any]:
        """Get Assembly Object (Class 0x04) configurations.

        Returns I/O assembly configurations for device capability fingerprinting.

        Returns:
            Dictionary with assembly configurations (input, output, config, safety)
        """
        default = {
            "input": {"instance": 100, "size_bytes": 128},
            "output": {"instance": 101, "size_bytes": 128},
        }

        assembly_objects = self.fingerprint.get("assembly_objects", {})
        return {**default, **assembly_objects}

    def get_cip_safety_info(self) -> dict[str, Any] | None:
        """Get CIP Safety information for GuardLogix/safety devices.

        Returns safety network configuration for CIP Safety fingerprinting.

        Returns:
            Dictionary with CIP Safety attributes, or None if not a safety device
        """
        return self.fingerprint.get("cip_safety")

    def get_list_services(self) -> list[dict[str, Any]]:
        """Get ListServices response data for EtherNet/IP capability advertising.

        Returns:
            List of service dictionaries with type_code, name, and capability_flags
        """
        services_config = self.fingerprint.get("list_services_response", {})

        services = []
        if services_config.get("communications"):
            services.append(services_config["communications"])

        if not services:
            # Default communications service
            services = [{
                "type_code": 0x0100,
                "name": "Communications",
                "capability_flags": 0x0120,  # TCP + UDP
            }]

        return services

    def is_safety_device(self) -> bool:
        """Check if this device supports CIP Safety protocol.

        Returns:
            True if device has CIP Safety configuration
        """
        return (
            self.fingerprint.get("cip_safety") is not None or
            self.fingerprint.get("protocol_quirks", {}).get("cip_safety_enabled", False)
        )

    # ========== PROFINET Identity ==========

    def build_profinet_dcp_identify_response(self) -> bytes:
        """Build a PROFINET DCP Identify response.

        Returns:
            DCP block data for identify response
        """
        identity = self.profinet_identity
        if not identity:
            return b""

        import struct

        blocks = []

        # Device/Vendor block (option 0x02, suboption 0x01)
        vendor_id = identity.get("vendor_id", 0x002A)
        device_id = identity.get("device_id", 0x0001)
        blocks.append(
            struct.pack(">BBHH", 0x02, 0x01, 4, 0) +
            struct.pack(">HH", vendor_id, device_id)
        )

        # NameOfStation block (option 0x02, suboption 0x02)
        station_name = identity.get("station_name", "device")
        station_bytes = station_name.encode("ascii")
        # Pad to even length
        if len(station_bytes) % 2:
            station_bytes += b"\x00"
        blocks.append(
            struct.pack(">BBH", 0x02, 0x02, len(station_bytes)) +
            station_bytes
        )

        # Device role block (option 0x02, suboption 0x04)
        device_role = identity.get("device_role", 1)
        blocks.append(
            struct.pack(">BBHBB", 0x02, 0x04, 2, device_role, 0)
        )

        # Concatenate all blocks
        return b"".join(blocks)

    def get_profinet_station_name(self) -> str:
        """Get PROFINET station name."""
        return self.profinet_identity.get("station_name", "device")

    def get_profinet_vendor_id(self) -> int:
        """Get PROFINET vendor ID."""
        return self.profinet_identity.get("vendor_id", 0x002A)

    # ========== S7comm/S7comm-Plus Identity ==========

    def build_s7_szl_response(self, szl_id: int = 0x0011) -> bytes:
        """Build an S7comm SZL (System Status List) response.

        The SZL contains system information including module identification,
        firmware versions, and order codes that vulnerability scanners examine.

        Args:
            szl_id: SZL ID to build response for
                   0x0011 - Module identification
                   0x001C - Component identification

        Returns:
            SZL response data bytes
        """
        identity = self.s7_identity
        if not identity:
            return b""

        import struct

        if szl_id == 0x0011:
            # Module identification SZL
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
            szl_data = struct.pack(">HH", szl_id, 0x0000)  # SZL ID, Index
            szl_data += struct.pack(">HH", 64, 1)  # Data length, Element count
            szl_data += order_code
            szl_data += serial_number
            szl_data += firmware_version
            szl_data += module_type

            return szl_data

        elif szl_id == 0x001C:
            # Component identification SZL
            # Contains module name and version info
            component_name = identity.get("module_type", "CPU 1516-3 PN/DP").encode("ascii")[:32]
            copyright_info = b"SIEMENS AG".ljust(26, b"\x00")

            component_name = component_name.ljust(32, b"\x00")

            szl_data = struct.pack(">HH", szl_id, 0x0000)
            szl_data += struct.pack(">HH", 58, 1)
            szl_data += component_name
            szl_data += copyright_info

            return szl_data

        return b""

    def get_s7_order_code(self) -> str:
        """Get S7 order code (MLFB)."""
        return self.s7_identity.get("order_code", "6ES7 516-3AN01-0AB0")

    def get_s7_firmware_version(self) -> str:
        """Get S7 firmware version."""
        return self.s7_identity.get("firmware_version", "V3.0.0")

    def get_s7_serial_number(self) -> str:
        """Get S7 serial number."""
        return self.s7_identity.get("serial_number", "S V-P92001234")

    # ========== MAC Address Generation ==========

    def generate_mac_address(self) -> str:
        """Generate a MAC address using vendor OUI prefix.

        Returns:
            MAC address string (e.g., "00:00:BC:12:34:56")
        """
        oui_prefixes = self.fingerprint.get("oui_prefixes", [])
        if oui_prefixes:
            oui = random.choice(oui_prefixes)
        else:
            # Default OUI for unknown vendors
            oui = "00:00:00"

        # Generate random NIC portion
        nic = [random.randint(0, 255) for _ in range(3)]
        return f"{oui}:{nic[0]:02X}:{nic[1]:02X}:{nic[2]:02X}"

    # ========== Protocol Quirks ==========

    def get_quirk(self, key: str, default: Any = None) -> Any:
        """Get a protocol-specific quirk value.

        Args:
            key: Quirk key name
            default: Default value if not found

        Returns:
            Quirk value or default
        """
        return self.protocol_quirks.get(key, default)

    def get_modbus_max_registers(self) -> int:
        """Get maximum registers per Modbus request."""
        return self.get_quirk("modbus_max_registers", 125)

    def get_modbus_max_coils(self) -> int:
        """Get maximum coils per Modbus request."""
        return self.get_quirk("modbus_max_coils", 2000)

    def get_enip_connection_timeout_multiplier(self) -> int:
        """Get EtherNet/IP connection timeout multiplier."""
        return self.get_quirk("cip_connection_timeout_multiplier", 32)

    def get_profinet_cycle_time_us(self) -> int:
        """Get PROFINET cycle time in microseconds."""
        return self.get_quirk("profinet_cycle_time_us", 1000)


def create_default_applicator() -> FingerprintApplicator:
    """Create a default fingerprint applicator with generic settings.

    Returns:
        FingerprintApplicator with default fingerprint
    """
    default_fingerprint = {
        "tcp_stack": {
            "ttl": 64,
            "window_size": 65535,
            "mss": 1460,
            "sack_permitted": True,
            "timestamps_enabled": True,
            "df_flag": True,
        },
        "response_timing": {
            "min_ms": 1.0,
            "max_ms": 50.0,
            "mean_ms": 10.0,
            "std_dev_ms": 5.0,
            "distribution": "gaussian",
            "outlier_probability": 0.01,
            "outlier_multiplier": 3.0,
        },
        "error_behavior": {
            "supported_exception_codes": [1, 2, 3, 4],
            "exception_probability": 0.001,
            "timeout_probability": 0.0005,
            "retry_behavior": True,
            "max_retries": 3,
        },
    }
    return FingerprintApplicator(default_fingerprint)
