# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Fingerprint applicator for applying vendor fingerprints to packet generation.

This module provides functions to apply vendor-specific fingerprints
during packet generation, including:
- TCP/IP stack characteristics (TTL, window size, MSS, etc.)
- Response timing with realistic distributions
- Protocol identity responses via the identity builder plugin system
- Error injection based on vendor behavior
- Vulnerability override support for CVE simulation
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
    nop_padding: bool = True


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
        device_id: str | None = None,
        scenario_id: str | None = None,
        device_name: str | None = None,
    ):
        """Initialize with a fingerprint configuration.

        Args:
            fingerprint: Vendor fingerprint dictionary with tcp_stack,
                        response_timing, error_behavior, etc.
            vulnerability_override: Optional CVE vulnerability overrides that
                        modify protocol identity responses to include vulnerable
                        firmware versions. See VulnerableFingerprintVariant model.
            device_id: Unique device identifier for serial number generation.
                      When provided, unique serial numbers are auto-generated.
            scenario_id: Scenario identifier for serial number generation.
                        Combined with device_id to create deterministic serials.
            device_name: Human-readable device name for generating unique
                        network identifiers (BACnet object_name, PROFINET
                        station_name, SNMP sys_name).
        """
        self.fingerprint = fingerprint
        self._vulnerability_override = vulnerability_override or {}
        self.device_id = device_id
        self.scenario_id = scenario_id
        self.device_name = device_name
        self.tcp_stack = fingerprint.get("tcp_stack", {})
        self.response_timing = fingerprint.get("response_timing", {})
        self.error_behavior = fingerprint.get("error_behavior", {})
        self.protocol_quirks = fingerprint.get("protocol_quirks", {})

        # Protocol identities are lazily initialized on first access.
        # This avoids computing all 9 identities + vulnerability overrides +
        # unique serial generation when devices typically use only 1-2 protocols.
        # Access to any identity attribute triggers _init_identities() via __getattr__.
        self.__dict__["_identities_initialized"] = False

        # Initialize RNG for reproducibility if needed
        self._rng = np.random.default_rng()

    # Identity attribute names that trigger lazy initialization
    _IDENTITY_ATTRS = frozenset({
        "modbus_identity", "ethernet_ip_identity", "profinet_identity",
        "s7_identity", "snmp_identity", "bacnet_identity",
        "opc_ua_identity", "dnp3_identity", "iec104_identity",
    })

    def __getattr__(self, name: str) -> Any:
        """Lazy initialization of protocol identity attributes.

        When any identity attribute is accessed before initialization,
        this triggers full identity setup (extract, overrides, serials).
        """
        if name in self._IDENTITY_ATTRS and not self.__dict__.get("_identities_initialized"):
            self._init_identities()
            return self.__dict__[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def _init_identities(self) -> None:
        """Initialize all protocol identities, apply overrides and unique serials.

        Called lazily on first access to any identity attribute.
        """
        self._identities_initialized = True

        fingerprint = self.fingerprint
        self.modbus_identity = dict(fingerprint.get("modbus_identity") or {})
        self.ethernet_ip_identity = dict(fingerprint.get("ethernet_ip_identity") or {})
        self.profinet_identity = dict(fingerprint.get("profinet_identity") or {})
        # S7 identity: use top-level only (legacy protocol_quirks location is deprecated)
        self.s7_identity = dict(fingerprint.get("s7_identity") or {})
        # Warn if legacy location is used
        if not self.s7_identity and (fingerprint.get("protocol_quirks") or {}).get("s7_identity"):
            logger.warning(
                f"Fingerprint has s7_identity in protocol_quirks (deprecated). "
                f"Move s7_identity to top level. Vendor: {fingerprint.get('vendor')}, "
                f"Model: {fingerprint.get('model')}"
            )
            self.s7_identity = dict((fingerprint.get("protocol_quirks") or {}).get("s7_identity") or {})
        self.snmp_identity = dict(fingerprint.get("snmp_identity") or {})
        self.bacnet_identity = dict(fingerprint.get("bacnet_identity") or {})
        self.opc_ua_identity = dict(fingerprint.get("opc_ua_identity") or {})
        self.dnp3_identity = dict(fingerprint.get("dnp3_identity") or {})
        self.iec104_identity = dict(fingerprint.get("iec104_identity") or {})

        # Apply vulnerability overrides if provided
        if self._vulnerability_override:
            self._apply_vulnerability_overrides()

        # Auto-generate unique identifiers if device_id provided
        if self.device_id:
            self._apply_unique_serials()
            self._apply_unique_identifiers()

    def validate_identity_for_protocols(
        self,
        protocols: list[str],
        device_name: str | None = None,
    ) -> list[str]:
        """Validate that fingerprint has identity data for declared protocols.

        This method checks if the fingerprint has the required identity fields
        for each protocol the device claims to support. Missing identities will
        result in generic/default responses which may not be detected correctly
        by security scanners like Cisco Cyber Vision.

        Args:
            protocols: List of protocol names (e.g., ["modbus_tcp", "profinet"])
            device_name: Optional device name for logging

        Returns:
            List of protocols that are missing identity data
        """
        # Protocol to identity mapping
        protocol_identity_map = {
            "modbus_tcp": ("modbus_identity", self.modbus_identity),
            "modbus": ("modbus_identity", self.modbus_identity),
            "ethernet_ip": ("ethernet_ip_identity", self.ethernet_ip_identity),
            "cip": ("ethernet_ip_identity", self.ethernet_ip_identity),
            "profinet": ("profinet_identity", self.profinet_identity),
            "s7comm": ("s7_identity", self.s7_identity),
            "s7comm_plus": ("s7_identity", self.s7_identity),
            "snmp": ("snmp_identity", self.snmp_identity),
            "bacnet": ("bacnet_identity", self.bacnet_identity),
            "opc_ua": ("opc_ua_identity", self.opc_ua_identity),
            "dnp3": ("dnp3_identity", self.dnp3_identity),
            "iec104": ("iec104_identity", self.iec104_identity),
        }

        missing = []
        for protocol in protocols:
            protocol_lower = protocol.lower()
            if protocol_lower in protocol_identity_map:
                identity_key, identity_data = protocol_identity_map[protocol_lower]
                if not identity_data:
                    missing.append(protocol)
                    device_desc = f"Device '{device_name}'" if device_name else "Device"
                    logger.warning(
                        f"{device_desc}: Protocol '{protocol}' declared but no {identity_key} "
                        f"in fingerprint. Identity responses will use defaults."
                    )

        return missing

    def _apply_vulnerability_overrides(self) -> None:
        """Apply CVE-specific firmware version overrides to protocol identities.

        This modifies the protocol identity responses to include vulnerable
        firmware version strings that security scanners will detect.

        If firmware_version is provided, the system will AUTO-DERIVE protocol-specific
        firmware fields using FirmwareVersionDeriver. Explicit overrides for non-firmware
        fields (like product_code, model_name) are then applied on top.

        Supports both key naming conventions:
        - With _override suffix: modbus_identity_override (from DB model)
        - Without suffix: modbus_identity (from extract_identity_overrides)
        """
        override = self._vulnerability_override
        firmware_version = override.get("firmware_version")

        # STEP 1: If firmware_version is provided, auto-derive all firmware fields
        if firmware_version:
            from app.protocol_engines.firmware_version_deriver import FirmwareVersionDeriver

            deriver = FirmwareVersionDeriver(
                firmware_version=firmware_version,
                base_identity={
                    "modbus_identity": self.modbus_identity,
                    "ethernet_ip_identity": self.ethernet_ip_identity,
                    "profinet_identity": self.profinet_identity,
                    "s7_identity": self.s7_identity,
                    "snmp_identity": self.snmp_identity,
                    "bacnet_identity": self.bacnet_identity,
                    "cip_identity_object": self.fingerprint.get("cip_identity_object", {}),
                },
            )

            # Get SNMP sys_descr template if provided
            snmp_sys_descr_template = override.get("snmp_sys_descr_template")

            # Derive all protocol identities (firmware fields only)
            derived = deriver.derive_all(snmp_sys_descr_template=snmp_sys_descr_template)

            # Apply derived firmware fields to all protocol identities
            self.modbus_identity.update(derived.get("modbus_identity", {}))
            self.ethernet_ip_identity.update(derived.get("ethernet_ip_identity", {}))
            self.profinet_identity.update(derived.get("profinet_identity", {}))
            self.s7_identity.update(derived.get("s7_identity", {}))
            self.snmp_identity.update(derived.get("snmp_identity", {}))
            self.bacnet_identity.update(derived.get("bacnet_identity", {}))

            logger.info(
                f"Auto-derived firmware fields from firmware_version={firmware_version}"
            )

        # STEP 2: Apply explicit overrides for non-firmware fields (on top of derived)

        # Fields to PRESERVE from base identity (device-specific, not CVE-related)
        # These are unique per device and should not be overwritten by CVE templates
        preserve_fields = {
            "product_name",      # Device name shown in Cyber Vision
            "serial_number",     # Unique device serial
            "object_name",       # BACnet object name
            "station_name",      # PROFINET station name
            "sys_name",          # SNMP system name
            "plc_name",          # S7 PLC name
        }

        def filter_override(ovr: dict) -> dict:
            """Filter out device-specific fields that should be preserved."""
            return {k: v for k, v in ovr.items() if k not in preserve_fields}

        # Apply Modbus identity overrides (support both key formats)
        modbus_override = (
            override.get("modbus_identity_override") or
            override.get("modbus_identity")
        )
        if modbus_override:
            filtered = filter_override(modbus_override)
            self.modbus_identity.update(filtered)
            logger.debug(f"Applied Modbus vulnerability override: {filtered}")

        # Apply EtherNet/IP identity overrides (support both key formats)
        eip_override = (
            override.get("ethernet_ip_identity_override") or
            override.get("ethernet_ip_identity")
        )
        if eip_override:
            filtered = filter_override(eip_override)
            self.ethernet_ip_identity.update(filtered)
            logger.debug(f"Applied EtherNet/IP vulnerability override: {filtered}")

        # Apply PROFINET identity overrides (support both key formats)
        pn_override = (
            override.get("profinet_identity_override") or
            override.get("profinet_identity")
        )
        if pn_override:
            filtered = filter_override(pn_override)
            self.profinet_identity.update(filtered)
            logger.debug(f"Applied PROFINET vulnerability override: {filtered}")

        # Apply S7 identity overrides (support both key formats)
        s7_override = (
            override.get("s7_identity_override") or
            override.get("s7_identity")
        )
        if s7_override:
            filtered = filter_override(s7_override)
            self.s7_identity.update(filtered)
            logger.debug(f"Applied S7 vulnerability override: {filtered}")

        # Apply SNMP identity overrides (support both key formats)
        # Used for transportation systems (traffic controllers, DMS, etc.)
        snmp_override = (
            override.get("snmp_identity_override") or
            override.get("snmp_identity")
        )
        if snmp_override:
            filtered = filter_override(snmp_override)
            self.snmp_identity.update(filtered)
            logger.debug(f"Applied SNMP vulnerability override: {filtered}")

        # Apply BACnet identity overrides (support both key formats)
        # Used for building automation / BMS devices
        bacnet_override = (
            override.get("bacnet_identity_override") or
            override.get("bacnet_identity")
        )
        if bacnet_override:
            filtered = filter_override(bacnet_override)
            self.bacnet_identity.update(filtered)
            logger.debug(f"Applied BACnet vulnerability override: {filtered}")

    def _apply_unique_serials(self) -> None:
        """Generate unique serial numbers for all protocols.

        This method auto-generates unique serial numbers based on device_id
        and scenario_id to prevent Cisco Cyber Vision from incorrectly merging
        devices that share the same vendor fingerprint.

        Serial numbers are deterministic - the same device_id + scenario_id
        combination will always produce the same serial number.
        """
        try:
            from app.protocol_engines.serial_number_generator import SerialNumberGenerator
        except ImportError:
            logger.debug("SerialNumberGenerator not available, skipping unique serials")
            return

        vendor = self.fingerprint.get("vendor", "")

        # EtherNet/IP: 32-bit integer serial number
        if self.ethernet_ip_identity:
            self.ethernet_ip_identity["serial_number"] = SerialNumberGenerator.generate(
                protocol="ethernet_ip",
                device_id=self.device_id,
                scenario_id=self.scenario_id,
                vendor=vendor,
            )
            logger.debug(
                f"Generated unique EtherNet/IP serial: {self.ethernet_ip_identity['serial_number']}"
            )

        # S7comm: 12-character string serial number
        if self.s7_identity:
            self.s7_identity["serial_number"] = SerialNumberGenerator.generate(
                protocol="s7",
                device_id=self.device_id,
                scenario_id=self.scenario_id,
                vendor=vendor,
            )
            logger.debug(
                f"Generated unique S7 serial: {self.s7_identity['serial_number']}"
            )

        # PROFINET I&M0: 16-character hex serial number
        if self.profinet_identity:
            self.profinet_identity["im0_serial_number"] = SerialNumberGenerator.generate(
                protocol="profinet",
                device_id=self.device_id,
                scenario_id=self.scenario_id,
                vendor=vendor,
            )
            logger.debug(
                f"Generated unique PROFINET serial: {self.profinet_identity['im0_serial_number']}"
            )

    def _apply_unique_identifiers(self) -> None:
        """Generate unique network identifiers for all protocols.

        This method generates unique identifiers for protocols that require
        network-unique values. These identifiers are what Cisco Cyber Vision
        uses to display device names:

        - BACnet: device_instance (must be unique on BACnet network)
        - BACnet: object_name (CV displays this as device name)
        - PROFINET: station_name (must be unique, CV displays this)
        - SNMP: sys_name (CV displays this as device name)
        - S7comm: plc_name (CV displays this for Siemens devices)
        - EtherNet/IP: product_name (CV displays this from ListIdentity)
        - Modbus: product_name (CV displays this from FC43 MEI response)

        Identifiers are deterministic - same device_id + scenario_id always
        produces the same values.
        """
        try:
            from app.protocol_engines.unique_identifier_generator import UniqueIdentifierGenerator
        except ImportError:
            logger.debug("UniqueIdentifierGenerator not available, skipping unique identifiers")
            return

        model = self.fingerprint.get("model", "")
        vendor_family = self.fingerprint.get("vendor_family", "")
        vendor = self.fingerprint.get("vendor", "")

        # BACnet identity: device_instance and object_name
        if self.bacnet_identity:
            # Generate unique device_instance (MUST be unique on BACnet network)
            self.bacnet_identity["device_instance"] = (
                UniqueIdentifierGenerator.generate_bacnet_device_instance(
                    device_id=self.device_id,
                    scenario_id=self.scenario_id,
                )
            )
            logger.debug(
                f"Generated unique BACnet device_instance: "
                f"{self.bacnet_identity['device_instance']}"
            )

            # Generate unique object_name
            self.bacnet_identity["object_name"] = (
                UniqueIdentifierGenerator.generate_bacnet_object_name(
                    device_id=self.device_id,
                    scenario_id=self.scenario_id,
                    device_name=self.device_name,
                    model=model,
                    vendor_family=vendor_family,
                    vendor=vendor,
                )
            )
            logger.debug(
                f"Generated unique BACnet object_name: "
                f"{self.bacnet_identity['object_name']}"
            )

        # PROFINET identity: station_name (MUST be unique on PROFINET network)
        if self.profinet_identity:
            self.profinet_identity["station_name"] = (
                UniqueIdentifierGenerator.generate_profinet_station_name(
                    device_id=self.device_id,
                    scenario_id=self.scenario_id,
                    device_name=self.device_name,
                    model=model,
                    vendor_family=vendor_family,
                    vendor=vendor,
                )
            )
            logger.debug(
                f"Generated unique PROFINET station_name: "
                f"{self.profinet_identity['station_name']}"
            )

        # SNMP identity: sys_name
        if self.snmp_identity:
            self.snmp_identity["sys_name"] = (
                UniqueIdentifierGenerator.generate_snmp_sys_name(
                    device_id=self.device_id,
                    scenario_id=self.scenario_id,
                    device_name=self.device_name,
                    model=model,
                    vendor_family=vendor_family,
                    vendor=vendor,
                )
            )
            logger.debug(
                f"Generated unique SNMP sys_name: {self.snmp_identity['sys_name']}"
            )

        # S7 identity: plc_name (for Siemens device naming in Cyber Vision)
        if self.s7_identity:
            self.s7_identity["plc_name"] = (
                UniqueIdentifierGenerator.generate_s7_plc_name(
                    device_id=self.device_id,
                    scenario_id=self.scenario_id,
                    device_name=self.device_name,
                    model=model,
                    vendor_family=vendor_family,
                    vendor=vendor,
                )
            )
            logger.debug(
                f"Generated unique S7 plc_name: {self.s7_identity['plc_name']}"
            )

        # EtherNet/IP identity: product_name (CIP Identity Object)
        # CV uses this for BOTH model-ref and name.  The template's product_name
        # is the manufacturer catalog string (e.g. "1756-L83E/B LOGIX5580") which
        # lets CV properly identify the model.  Only generate a synthetic name
        # when the template doesn't already supply one.
        if self.ethernet_ip_identity:
            if not self.ethernet_ip_identity.get("product_name"):
                self.ethernet_ip_identity["product_name"] = (
                    UniqueIdentifierGenerator.generate_ethernet_ip_product_name(
                        device_id=self.device_id,
                        scenario_id=self.scenario_id,
                        device_name=self.device_name,
                        model=model,
                        vendor_family=vendor_family,
                        vendor=vendor,
                    )
                )
                logger.debug(
                    f"Generated unique EtherNet/IP product_name: "
                    f"{self.ethernet_ip_identity['product_name']}"
                )

        # Modbus identity: product_name (for Modbus FC43 Device Identification)
        # CV uses this from MEI responses for model identification.
        # Preserve the template's product_name (manufacturer catalog string)
        # so CV can properly identify the model. Only generate a synthetic
        # name when the template doesn't already supply one.
        if self.modbus_identity:
            if not self.modbus_identity.get("product_name"):
                if self.device_name:
                    self.modbus_identity["product_name"] = self.device_name
                elif model:
                    hash_bytes = UniqueIdentifierGenerator._generate_hash(
                        self.device_id, self.scenario_id
                    )
                    hash_suffix = hash_bytes[:2].hex().upper()
                    self.modbus_identity["product_name"] = f"{model}-{hash_suffix}"
                logger.debug(
                    f"Generated unique Modbus product_name: "
                    f"{self.modbus_identity.get('product_name')}"
                )

    @property
    def is_vulnerable(self) -> bool:
        """Check if vulnerability overrides are active."""
        return bool(self._vulnerability_override)

    @property
    def cve_id(self) -> str | None:
        """Get the CVE ID if vulnerability overrides are active."""
        return self._vulnerability_override.get("cve_id")

    @property
    def vulnerable_firmware_version(self) -> str | None:
        """Get the vulnerable firmware version if overrides are active."""
        return self._vulnerability_override.get("firmware_version")

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

    # ========== CIP Identity Object (Deep Fingerprinting) ==========

    def get_cip_identity_object(self) -> dict[str, Any]:
        """Get complete CIP Identity Object attributes (1-20) for deep fingerprinting.

        This combines basic ethernet_ip_identity with extended cip_identity_object
        attributes used by Cisco Cyber Vision for detailed device identification.

        Returns:
            Dictionary with all CIP Identity Object attributes
        """
        # Get vendor_id with warning if missing. Rate-limited to one log
        # entry per applicator instance — pre-rate-limit this fired per
        # poll cycle (5-25× per scenario startup) which drowned the agent
        # log. The duplicate log was an artefact of how the agent fans
        # out per-device, not new information.
        vendor_id = self.ethernet_ip_identity.get("vendor_id")
        if vendor_id is None:
            if not getattr(self, "_cip_vendor_warned", False):
                self._cip_vendor_warned = True
                logger.warning(
                    "CIP Identity Object missing vendor_id for %s/%s - "
                    "defaulting to 1 (Rockwell). Device may be misidentified "
                    "in Cyber Vision; add `vendor_id` to "
                    "ethernet_ip_identity in the device template, then "
                    "regenerate or redeploy the scenario.",
                    self.fingerprint.get("vendor", "?"),
                    self.fingerprint.get("model", "?"),
                )
            vendor_id = 1

        # Start with basic identity data
        identity = {
            "vendor_id": vendor_id,
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
        cip_override = self._vulnerability_override.get("cip_identity_override", {})
        if cip_override:
            identity.update(cip_override)
            logger.debug(f"Applied CIP Identity vulnerability override: {cip_override}")

        return identity

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

    # ========== Identity Builder Integration ==========

    def get_identity_response(self, protocol: str, **kwargs: Any) -> "IdentityResponse":
        """Get identity response using the identity builder plugin system.

        This is the recommended method for generating identity responses
        as it uses the new plugin architecture.

        Args:
            protocol: Protocol name (modbus, ethernet_ip, profinet, s7, snmp, bacnet)
            **kwargs: Protocol-specific arguments

        Returns:
            IdentityResponse from the appropriate builder

        Raises:
            KeyError: If protocol is not supported
        """
        from app.protocol_engines.identity import (
            get_builder,
        )

        builder = get_builder(protocol)

        # Get base identity for this protocol
        base_identity = self._get_base_identity_for_protocol(protocol)

        # Get vulnerability override for this protocol
        override_key = builder.override_key
        protocol_override = self._vulnerability_override.get(override_key)

        # Get firmware version if available
        firmware_version = self._vulnerability_override.get("firmware_version")

        return builder.build_identity_response(
            base_identity=base_identity,
            vulnerability_override=protocol_override,
            firmware_version=firmware_version,
            **kwargs,
        )

    def _get_base_identity_for_protocol(self, protocol: str) -> dict[str, Any]:
        """Get the base identity dictionary for a protocol.

        Args:
            protocol: Protocol name

        Returns:
            Base identity dictionary
        """
        identity_map = {
            "modbus": self.modbus_identity,
            "ethernet_ip": self.ethernet_ip_identity,
            "profinet": self.profinet_identity,
            "s7": self.s7_identity,
            "snmp": self.snmp_identity,
            "bacnet": self.bacnet_identity,
        }
        return identity_map.get(protocol, {})

    def get_timing_model(self) -> "TimingModel":
        """Get a timing model instance based on this fingerprint.

        Uses the new unified timing model system.

        Returns:
            TimingModel instance configured from this fingerprint
        """
        from app.protocol_engines.timing import timing_model_from_fingerprint

        return timing_model_from_fingerprint(self.fingerprint)

    def get_timing_sample(self) -> "TimingSampleNew":
        """Get a timing sample using the new timing model system.

        This is an alternative to get_response_delay() that uses
        the new unified timing model.

        Returns:
            TimingSample from the timing model
        """
        model = self.get_timing_model()
        return model.sample()


# Type hints for forward references
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.protocol_engines.identity import IdentityResponse
    from app.protocol_engines.timing import TimingModel, TimingSample as TimingSampleNew


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
