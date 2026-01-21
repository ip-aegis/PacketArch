"""Scenario definition enricher for unique device identifiers.

This module enriches scenario definitions with unique device identifiers
BEFORE deploying to remote agents. All fingerprint enrichment happens here
in the backend - the remote agent uses fingerprints as-is without modification.

Architecture (Layered Composition):
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Instance-Specific (ALWAYS GENERATED HERE)         │
│  - serial_number, device_instance, station_name, sys_name   │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: CVE/Vulnerability (merged from cveIdentityOverrides)
│  - firmware_version, revision_major/minor, product_code     │
│  - NOTE: CVE data should NOT contain instance-specific fields│
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Base Vendor Fingerprint (from templates)          │
│  - vendor_id, device_type, tcp_stack, timing                │
└─────────────────────────────────────────────────────────────┘

Order of operations:
1. Start with base fingerprint from device
2. Merge CVE overrides (vulnerability-relevant fields only)
3. Generate unique instance identifiers (serial_number, etc.)
4. Remote agent receives fully-enriched fingerprint

The enrichment is applied to a deep copy of the definition,
ensuring the original scenario definition in the database remains unchanged.
"""

import copy
import logging
from typing import Any

from app.services.serial_number_generator import SerialNumberGenerator
from app.services.unique_identifier_generator import UniqueIdentifierGenerator

logger = logging.getLogger(__name__)


class ScenarioDefinitionEnricher:
    """Enriches scenario definition with unique device identifiers.

    This must be called before deploying scenarios to remote agents
    to ensure unique serial numbers and network identifiers.

    Usage:
        enriched = ScenarioDefinitionEnricher.enrich_for_deployment(
            definition=scenario.definition,
            scenario_id=str(scenario.id),
        )
    """

    @classmethod
    def enrich_for_deployment(
        cls,
        definition: dict[str, Any],
        scenario_id: str,
    ) -> dict[str, Any]:
        """Apply unique identifiers to all devices in a scenario definition.

        This method generates unique serial numbers and network identifiers
        for all devices in the scenario, ensuring proper device identification
        by systems like Cisco Cyber Vision.

        Args:
            definition: Scenario definition with devices
            scenario_id: Scenario UUID string for deterministic generation

        Returns:
            Enriched definition with unique identifiers in fingerprints
            (deep copy - original is not modified)
        """
        # Deep copy to avoid modifying original
        enriched = copy.deepcopy(definition)

        devices_raw = enriched.get("devices", {})

        # Handle both dict and list formats
        if isinstance(devices_raw, dict):
            devices = devices_raw
        elif isinstance(devices_raw, list):
            # Convert list to dict for uniform processing
            devices = {d.get("id", str(i)): d for i, d in enumerate(devices_raw)}
            enriched["devices"] = devices
        else:
            logger.warning(f"Unexpected devices format: {type(devices_raw)}")
            return enriched

        enriched_count = 0

        for device_id, device in devices.items():
            if not isinstance(device, dict):
                continue

            # Get fingerprint (support both naming conventions)
            fingerprint = (
                device.get("vendorFingerprint")
                or device.get("vendor_fingerprint")
                or {}
            )

            if not fingerprint:
                continue

            device_name = device.get("name", device_id)

            # Layer 2: Apply CVE overrides (vulnerability-relevant fields)
            cls._apply_cve_overrides(fingerprint, device)

            # Clean up: Remove CVE overrides from device to reduce payload size
            # (remote agent doesn't need them - all enrichment is done here)
            if "cveIdentityOverrides" in device:
                del device["cveIdentityOverrides"]
            if "cve_identity_overrides" in device:
                del device["cve_identity_overrides"]

            # Layer 3: Generate unique instance identifiers
            cls._apply_unique_serials(fingerprint, device_id, scenario_id)
            cls._apply_unique_identifiers(
                fingerprint, device_id, scenario_id, device_name
            )

            # Update device with enriched fingerprint (use camelCase for frontend compat)
            device["vendorFingerprint"] = fingerprint

            enriched_count += 1

        logger.info(
            f"Enriched {enriched_count} devices with unique identifiers "
            f"for scenario {scenario_id}"
        )

        return enriched

    @classmethod
    def _apply_cve_overrides(
        cls,
        fingerprint: dict[str, Any],
        device: dict[str, Any],
    ) -> None:
        """Apply CVE identity overrides to fingerprint (Layer 2).

        Merges CVE vulnerability-specific identity overrides into the fingerprint.
        CVE overrides contain vulnerability-relevant fields like firmware_version,
        revision numbers, and product codes that identify vulnerable software.

        NOTE: CVE data should NOT contain instance-specific fields like
        serial_number, device_instance, or station_name. Those are always
        generated in Layer 3 (_apply_unique_serials, _apply_unique_identifiers).

        Args:
            fingerprint: Vendor fingerprint dictionary (modified in place)
            device: Device dictionary containing cveIdentityOverrides
        """
        # Get CVE overrides (support both naming conventions)
        cve_overrides = (
            device.get("cveIdentityOverrides")
            or device.get("cve_identity_overrides")
            or {}
        )

        if not cve_overrides:
            return

        device_name = device.get("name", device.get("id", "unknown"))
        logger.debug(
            f"Applying CVE overrides to device {device_name}: {list(cve_overrides.keys())}"
        )

        # Merge each identity type from CVE overrides
        identity_keys = [
            "modbus_identity",
            "ethernet_ip_identity",
            "profinet_identity",
            "cip_identity_object",
            "bacnet_identity",
            "snmp_identity",
            "s7_identity",
        ]

        for key in identity_keys:
            if key in cve_overrides:
                if key in fingerprint and isinstance(fingerprint[key], dict):
                    # Merge into existing identity
                    fingerprint[key].update(cve_overrides[key])
                else:
                    # Create new identity from override
                    fingerprint[key] = dict(cve_overrides[key])

                logger.debug(f"  Merged CVE override for {key}")

    @classmethod
    def _apply_unique_serials(
        cls,
        fingerprint: dict[str, Any],
        device_id: str,
        scenario_id: str,
    ) -> None:
        """Generate unique serial numbers for all protocols.

        This applies the same logic as FingerprintApplicator._apply_unique_serials()
        but works on the fingerprint dictionary directly (before DeviceContext creation).

        Args:
            fingerprint: Vendor fingerprint dictionary (modified in place)
            device_id: Unique device identifier
            scenario_id: Scenario identifier
        """
        vendor = fingerprint.get("vendor", "")

        # EtherNet/IP identity: 32-bit integer serial number
        ethernet_ip_identity = fingerprint.get("ethernet_ip_identity")
        if ethernet_ip_identity and isinstance(ethernet_ip_identity, dict):
            serial = SerialNumberGenerator.generate(
                protocol="ethernet_ip",
                device_id=device_id,
                scenario_id=scenario_id,
                vendor=vendor,
            )
            ethernet_ip_identity["serial_number"] = serial
            logger.debug(
                f"Generated EtherNet/IP serial {serial} for device {device_id}"
            )

        # S7comm identity: 12-character string serial number
        # S7 identity is nested under protocol_quirks
        protocol_quirks = fingerprint.get("protocol_quirks", {})
        s7_identity = protocol_quirks.get("s7_identity")
        if s7_identity and isinstance(s7_identity, dict):
            serial = SerialNumberGenerator.generate(
                protocol="s7",
                device_id=device_id,
                scenario_id=scenario_id,
                vendor=vendor,
            )
            s7_identity["serial_number"] = serial
            logger.debug(f"Generated S7 serial {serial} for device {device_id}")

        # PROFINET identity: 16-character hex serial number (IM0)
        profinet_identity = fingerprint.get("profinet_identity")
        if profinet_identity and isinstance(profinet_identity, dict):
            serial = SerialNumberGenerator.generate(
                protocol="profinet",
                device_id=device_id,
                scenario_id=scenario_id,
                vendor=vendor,
            )
            profinet_identity["im0_serial_number"] = serial
            logger.debug(
                f"Generated PROFINET serial {serial} for device {device_id}"
            )

    @classmethod
    def _apply_unique_identifiers(
        cls,
        fingerprint: dict[str, Any],
        device_id: str,
        scenario_id: str,
        device_name: str,
    ) -> None:
        """Generate unique network identifiers for all protocols.

        This generates unique identifiers for protocols that require them:
        - BACnet: device_instance, object_name
        - PROFINET: station_name
        - SNMP: sys_name

        Args:
            fingerprint: Vendor fingerprint dictionary (modified in place)
            device_id: Unique device identifier
            scenario_id: Scenario identifier
            device_name: Device name for generating human-readable identifiers
        """
        model = fingerprint.get("model", "")
        vendor_family = fingerprint.get("vendor_family", "")
        vendor = fingerprint.get("vendor", "")

        # BACnet identity
        bacnet_identity = fingerprint.get("bacnet_identity")
        if bacnet_identity and isinstance(bacnet_identity, dict):
            # Generate unique device_instance
            device_instance = UniqueIdentifierGenerator.generate_bacnet_device_instance(
                device_id=device_id,
                scenario_id=scenario_id,
            )
            bacnet_identity["device_instance"] = device_instance

            # Generate unique object_name
            object_name = UniqueIdentifierGenerator.generate_bacnet_object_name(
                device_id=device_id,
                scenario_id=scenario_id,
                device_name=device_name,
                model=model,
                vendor_family=vendor_family,
                vendor=vendor,
            )
            bacnet_identity["object_name"] = object_name

            logger.debug(
                f"Generated BACnet device_instance={device_instance}, "
                f"object_name={object_name} for device {device_id}"
            )

        # PROFINET identity: station_name
        profinet_identity = fingerprint.get("profinet_identity")
        if profinet_identity and isinstance(profinet_identity, dict):
            station_name = UniqueIdentifierGenerator.generate_profinet_station_name(
                device_id=device_id,
                scenario_id=scenario_id,
                device_name=device_name,
                model=model,
                vendor_family=vendor_family,
                vendor=vendor,
            )
            profinet_identity["station_name"] = station_name
            logger.debug(
                f"Generated PROFINET station_name={station_name} for device {device_id}"
            )

        # SNMP identity: sys_name
        snmp_identity = fingerprint.get("snmp_identity")
        if snmp_identity and isinstance(snmp_identity, dict):
            sys_name = UniqueIdentifierGenerator.generate_snmp_sys_name(
                device_id=device_id,
                scenario_id=scenario_id,
                device_name=device_name,
                model=model,
                vendor_family=vendor_family,
                vendor=vendor,
            )
            snmp_identity["sys_name"] = sys_name
            logger.debug(
                f"Generated SNMP sys_name={sys_name} for device {device_id}"
            )
