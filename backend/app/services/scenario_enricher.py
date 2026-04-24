# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Scenario definition enricher for deployment.

Enriches scenario definitions with CVE overrides and unique device identifiers
BEFORE deploying to remote agents. The remote agent uses fingerprints as-is.

Architecture (Layered Composition):
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Instance-Specific (serial_number, station_name…)  │
│  → delegated to device_identity_enricher                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: CVE/Vulnerability (from cveIdentityOverrides)     │
│  → _apply_cve_overrides (unique to this module)             │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Base Vendor Fingerprint (from templates)          │
└─────────────────────────────────────────────────────────────┘
"""

import copy
import logging
from typing import Any

from app.protocol_engines.protocols import (
    get_supported_protocols,
    PROTOCOL_TO_IDENTITY_KEY,
)
from app.services.device_identity_enricher import (
    enrich_device_serial_numbers,
    enrich_device_unique_identifiers,
)

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
        """Apply CVE overrides and unique identifiers to all devices.

        Args:
            definition: Scenario definition with devices
            scenario_id: Scenario UUID string for deterministic generation

        Returns:
            Enriched definition (deep copy — original is not modified)
        """
        enriched = copy.deepcopy(definition)

        devices_raw = enriched.get("devices", {})

        # Handle both dict and list formats
        if isinstance(devices_raw, dict):
            devices = devices_raw
        elif isinstance(devices_raw, list):
            devices = {d.get("id", str(i)): d for i, d in enumerate(devices_raw)}
            enriched["devices"] = devices
        else:
            logger.warning(f"Unexpected devices format: {type(devices_raw)}")
            return enriched

        enriched_count = 0

        for device_id, device in devices.items():
            if not isinstance(device, dict):
                continue

            fingerprint = (
                device.get("vendorFingerprint")
                or device.get("vendor_fingerprint")
                or {}
            )

            if not fingerprint:
                continue

            # Layer 2: Apply CVE overrides (vulnerability-relevant fields)
            cls._apply_cve_overrides(fingerprint, device)

            # Clean up CVE overrides from device (agent doesn't need them)
            device.pop("cveIdentityOverrides", None)
            device.pop("cve_identity_overrides", None)

            # Ensure fingerprint is set before calling enricher functions
            device["vendorFingerprint"] = fingerprint
            device["vendor_fingerprint"] = fingerprint

            # Layer 3: Generate unique serial numbers and network identifiers
            enrich_device_serial_numbers(device, device_id, scenario_id)
            enrich_device_unique_identifiers(device, device_id, scenario_id)

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
        Only modifies identity types for protocols declared in supported_protocols.

        Args:
            fingerprint: Vendor fingerprint dictionary (modified in place)
            device: Device dictionary containing cveIdentityOverrides
        """
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

        supported = get_supported_protocols(fingerprint)

        allowed_identity_keys = set()
        for protocol in supported:
            identity_key = PROTOCOL_TO_IDENTITY_KEY.get(protocol)
            if identity_key:
                allowed_identity_keys.add(identity_key)
        if "ethernet_ip" in supported:
            allowed_identity_keys.add("cip_identity_object")

        for key, override_value in cve_overrides.items():
            if key not in allowed_identity_keys:
                logger.debug(
                    f"  Skipped CVE override for {key} - protocol not in supported_protocols"
                )
                continue

            if key in fingerprint and isinstance(fingerprint[key], dict):
                fingerprint[key].update(override_value)
                logger.debug(f"  Merged CVE override for {key}")
            else:
                logger.warning(
                    f"  Protocol allowed but {key} not in fingerprint for {device_name}"
                )
