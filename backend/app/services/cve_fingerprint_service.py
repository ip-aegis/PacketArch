"""CVE Fingerprint Service.

Service for resolving CVE vulnerabilities to vulnerable fingerprint variants.
This enables devices to be associated with specific CVEs and emit vulnerable
firmware versions in their protocol identity responses.

This is the SINGLE SOURCE OF TRUTH for CVE resolution logic. All CVE-related
identity overrides should go through this service rather than being duplicated
in templates.py, entrypoint.py, or fingerprint_applicator.py.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cve_vulnerability import CVEVulnerability
from app.models.vulnerable_fingerprint import VulnerableFingerprintVariant

logger = logging.getLogger(__name__)


@dataclass
class ResolvedCVEConfig:
    """Fully resolved CVE configuration for a device.

    This dataclass contains all information needed to emit vulnerable
    device identities across all protocols. It is computed ONCE during
    scenario creation (not during packet generation) to avoid repeated
    database lookups and derivation logic.

    Attributes:
        cve_id: CVE identifier (e.g., "CVE-2022-1159")
        firmware_version: Vulnerable firmware version string
        display_name: Human-readable variant name
        vendor: Target vendor name
        target_models: List of affected model names
        severity: CVE severity (critical, high, medium, low)
        protocol_identities: Fully derived identity dicts for each protocol
        variant_id: Database ID of the VulnerableFingerprintVariant
        vulnerability_id: Database ID of the CVEVulnerability
    """

    cve_id: str
    firmware_version: str
    display_name: str
    vendor: str
    target_models: list[str] = field(default_factory=list)
    severity: str = "high"
    protocol_identities: dict[str, dict[str, Any]] = field(default_factory=dict)
    variant_id: str | None = None
    vulnerability_id: str | None = None

    def get_identity_override(self, protocol_key: str) -> dict[str, Any]:
        """Get identity override for a specific protocol.

        Args:
            protocol_key: Protocol identity key (e.g., 'modbus_identity')

        Returns:
            Identity override dict or empty dict if not available
        """
        return self.protocol_identities.get(protocol_key, {})

    def to_vulnerability_override(self) -> dict[str, Any]:
        """Convert to vulnerability_override format for FingerprintApplicator.

        Returns:
            Dictionary suitable for FingerprintApplicator(vulnerability_override=...)
        """
        override = {
            "cve_id": self.cve_id,
            "firmware_version": self.firmware_version,
            "display_name": self.display_name,
        }

        # Add protocol-specific overrides
        for key, identity in self.protocol_identities.items():
            if identity:
                override[key] = identity

        return override


class CVEFingerprintService:
    """Service for resolving CVEs to vulnerable fingerprint variants."""

    @staticmethod
    async def get_cve_by_id(
        db: AsyncSession,
        cve_id: str,
    ) -> CVEVulnerability | None:
        """Get a CVE by its ID.

        Args:
            db: Database session
            cve_id: CVE identifier (e.g., "CVE-2022-1159")

        Returns:
            CVE record or None if not found
        """
        result = await db.execute(
            select(CVEVulnerability).where(CVEVulnerability.cve_id == cve_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_vulnerable_variants_for_cves(
        db: AsyncSession,
        cve_ids: list[str],
        vendor: str | None = None,
    ) -> list[VulnerableFingerprintVariant]:
        """Get vulnerable fingerprint variants for a list of CVEs.

        Args:
            db: Database session
            cve_ids: List of CVE identifiers
            vendor: Optional vendor filter

        Returns:
            List of vulnerable fingerprint variants
        """
        if not cve_ids:
            return []

        # Get CVE records for the given IDs
        cve_result = await db.execute(
            select(CVEVulnerability).where(CVEVulnerability.cve_id.in_(cve_ids))
        )
        cves = cve_result.scalars().all()

        if not cves:
            logger.warning(f"No CVEs found for IDs: {cve_ids}")
            return []

        cve_db_ids = [cve.id for cve in cves]

        # Get variants for these CVEs
        query = select(VulnerableFingerprintVariant).where(
            VulnerableFingerprintVariant.cve_vulnerability_id.in_(cve_db_ids),
            VulnerableFingerprintVariant.is_active == True,
        )

        if vendor:
            query = query.where(
                VulnerableFingerprintVariant.target_vendor.ilike(vendor)
            )

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_best_variant_for_device(
        db: AsyncSession,
        vendor: str,
        fingerprint_model: str | None,
        cve_ids: list[str] | None = None,
    ) -> VulnerableFingerprintVariant | None:
        """Get the best matching vulnerable variant for a device.

        Selects the most appropriate variant based on:
        1. CVE IDs if specified
        2. Vendor match
        3. Model match (if fingerprint_model provided)
        4. Highest severity CVE

        Args:
            db: Database session
            vendor: Device vendor
            fingerprint_model: Optional fingerprint model name
            cve_ids: Optional list of specific CVE IDs to match

        Returns:
            Best matching variant or None
        """
        if cve_ids:
            # Get variants for specified CVEs
            variants = await CVEFingerprintService.get_vulnerable_variants_for_cves(
                db, cve_ids, vendor
            )

            if not variants:
                logger.info(f"No variants found for CVEs {cve_ids}, vendor={vendor}")
                return None

            # If model specified, prefer variants that target it
            if fingerprint_model:
                model_matches = [
                    v for v in variants
                    if v.target_models and fingerprint_model in v.target_models
                ]
                if model_matches:
                    return model_matches[0]

            # Return first available variant
            return variants[0] if variants else None

        # No CVE IDs specified - find any variant for this vendor/model
        query = select(VulnerableFingerprintVariant).where(
            VulnerableFingerprintVariant.target_vendor.ilike(vendor),
            VulnerableFingerprintVariant.is_active == True,
        )

        if fingerprint_model:
            # SQLAlchemy JSONB contains check
            query = query.where(
                VulnerableFingerprintVariant.target_models.contains([fingerprint_model])
            )

        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_cves_for_fingerprint(
        db: AsyncSession,
        vendor: str,
        fingerprint_model: str | None = None,
        product_family: str | None = None,
    ) -> list[CVEVulnerability]:
        """Get all CVEs affecting a specific fingerprint/product.

        Args:
            db: Database session
            vendor: Vendor name
            fingerprint_model: Optional model name
            product_family: Optional product family

        Returns:
            List of applicable CVEs
        """
        query = select(CVEVulnerability).where(
            CVEVulnerability.vendor.ilike(vendor)
        )

        if product_family:
            query = query.where(
                CVEVulnerability.product_family.ilike(product_family)
            )

        if fingerprint_model:
            # Check if model is in affected_models array
            query = query.where(
                CVEVulnerability.affected_models.contains([fingerprint_model])
            )

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    def extract_identity_overrides(
        variant: VulnerableFingerprintVariant,
    ) -> dict[str, Any]:
        """Extract all protocol identity overrides from a variant.

        This method auto-derives all protocol-specific firmware fields from
        the variant's firmware_version using FirmwareVersionDeriver, then
        merges any explicit overrides on top.

        Args:
            variant: Vulnerable fingerprint variant

        Returns:
            Dictionary with protocol-specific identity overrides (fully derived)
        """
        from app.protocol_engines.firmware_version_deriver import FirmwareVersionDeriver

        firmware_version = variant.firmware_version

        # Get explicit overrides from database
        explicit_modbus = variant.modbus_identity_override or {}
        explicit_eip = variant.ethernet_ip_identity_override or {}
        explicit_profinet = variant.profinet_identity_override or {}
        explicit_s7 = variant.s7_identity_override or {}
        explicit_cip = getattr(variant, "cip_identity_override", None) or {}
        explicit_snmp = getattr(variant, "snmp_identity_override", None) or {}
        explicit_bacnet = getattr(variant, "bacnet_identity_override", None) or {}
        snmp_sys_descr_template = getattr(variant, "snmp_sys_descr_template", None)

        # Auto-derive firmware fields if firmware_version is present
        if firmware_version:
            deriver = FirmwareVersionDeriver(firmware_version=firmware_version)
            derived = deriver.derive_all(snmp_sys_descr_template=snmp_sys_descr_template)

            # Merge: derived firmware fields + explicit non-firmware overrides
            modbus_identity = {**derived.get("modbus_identity", {}), **explicit_modbus}
            ethernet_ip_identity = {**derived.get("ethernet_ip_identity", {}), **explicit_eip}
            profinet_identity = {**derived.get("profinet_identity", {}), **explicit_profinet}
            s7_identity = {**derived.get("s7_identity", {}), **explicit_s7}
            cip_identity = {**derived.get("cip_identity_object", {}), **explicit_cip}
            snmp_identity = {**derived.get("snmp_identity", {}), **explicit_snmp}
            bacnet_identity = {**derived.get("bacnet_identity", {}), **explicit_bacnet}

            logger.debug(
                f"Auto-derived protocol identities for {variant.display_name} "
                f"from firmware_version={firmware_version}"
            )
        else:
            # No firmware version - use explicit overrides only
            modbus_identity = explicit_modbus
            ethernet_ip_identity = explicit_eip
            profinet_identity = explicit_profinet
            s7_identity = explicit_s7
            cip_identity = explicit_cip
            snmp_identity = explicit_snmp
            bacnet_identity = explicit_bacnet

        return {
            "modbus_identity": modbus_identity,
            "ethernet_ip_identity": ethernet_ip_identity,
            "profinet_identity": profinet_identity,
            "s7_identity": s7_identity,
            "cip_identity_override": cip_identity,
            "snmp_identity": snmp_identity,
            "bacnet_identity": bacnet_identity,
            "firmware_version": firmware_version,
            "cve_id": variant.cve_vulnerability.cve_id if variant.cve_vulnerability else None,
            "display_name": variant.display_name,
        }

    @staticmethod
    async def resolve_device_cve_config(
        db: AsyncSession,
        device_spec: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve CVE configuration for a device specification.

        Takes a device spec from a template and resolves any CVE references
        to their vulnerable fingerprint variants.

        Args:
            db: Database session
            device_spec: Device specification dictionary

        Returns:
            Updated device spec with resolved CVE configuration
        """
        cve_ids = device_spec.get("cve_ids", [])
        vendor = device_spec.get("vendor", "")
        fingerprint_model = device_spec.get("fingerprint_model")

        if not cve_ids and not vendor:
            return device_spec

        # Get best matching variant
        variant = await CVEFingerprintService.get_best_variant_for_device(
            db, vendor, fingerprint_model, cve_ids
        )

        if variant:
            # Extract and add identity overrides
            overrides = CVEFingerprintService.extract_identity_overrides(variant)
            device_spec["vulnerable_variant_id"] = str(variant.id)
            device_spec["vulnerable_firmware"] = overrides["firmware_version"]
            device_spec["cve_identity_overrides"] = overrides

            logger.info(
                f"Resolved CVE config for device: vendor={vendor}, "
                f"model={fingerprint_model}, variant={variant.display_name}"
            )

        return device_spec

    @staticmethod
    async def resolve_cves_for_device(
        db: AsyncSession,
        vendor: str,
        model: str | None = None,
        cve_ids: list[str] | None = None,
        base_fingerprint: dict[str, Any] | None = None,
    ) -> ResolvedCVEConfig | None:
        """Single entry point for CVE resolution.

        This method handles the complete CVE resolution workflow:
        1. Find matching CVE vulnerability and variant
        2. Select appropriate firmware version
        3. Auto-derive all protocol identity fields
        4. Apply explicit overrides
        5. Return fully resolved config

        This should be called ONCE during scenario creation, not during
        packet generation, to avoid repeated database lookups.

        Args:
            db: Database session
            vendor: Device vendor name
            model: Device model name (optional)
            cve_ids: Specific CVE IDs to resolve (optional)
            base_fingerprint: Base vendor fingerprint for context (optional)

        Returns:
            ResolvedCVEConfig with all identity overrides, or None if no match
        """
        # Get best matching variant
        variant = await CVEFingerprintService.get_best_variant_for_device(
            db, vendor, model, cve_ids
        )

        if not variant:
            logger.debug(f"No CVE variant found for vendor={vendor}, model={model}")
            return None

        # Get the associated CVE for severity info
        cve = variant.cve_vulnerability
        cve_id = cve.cve_id if cve else "UNKNOWN"
        severity = cve.severity if cve else "high"

        # Get firmware version
        firmware_version = variant.firmware_version or ""

        # Build protocol identities using identity builders
        protocol_identities = CVEFingerprintService._build_protocol_identities(
            variant=variant,
            firmware_version=firmware_version,
            base_fingerprint=base_fingerprint,
        )

        return ResolvedCVEConfig(
            cve_id=cve_id,
            firmware_version=firmware_version,
            display_name=variant.display_name or f"{vendor} {model} (CVE)",
            vendor=variant.target_vendor,
            target_models=variant.target_models or [],
            severity=severity,
            protocol_identities=protocol_identities,
            variant_id=str(variant.id) if variant.id else None,
            vulnerability_id=str(cve.id) if cve and cve.id else None,
        )

    @staticmethod
    def _build_protocol_identities(
        variant: VulnerableFingerprintVariant,
        firmware_version: str,
        base_fingerprint: dict[str, Any] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Build protocol identity overrides scoped to supported protocols.

        Uses the identity builder plugin system for consistent firmware
        field derivation. Only builds identities for protocols declared
        in the fingerprint's supported_protocols field.

        Args:
            variant: Vulnerable fingerprint variant
            firmware_version: Target firmware version
            base_fingerprint: Optional base fingerprint for context

        Returns:
            Dictionary mapping identity keys to identity dicts
        """
        from app.protocol_engines.identity import (
            derive_all_firmware_fields,
            get_registered_protocols,
        )
        from app.protocol_engines.protocols import (
            get_supported_protocols,
            PROTOCOL_TO_IDENTITY_KEY,
        )

        result: dict[str, dict[str, Any]] = {}
        base = base_fingerprint or {}

        # Get supported protocols - authoritative source for protocol scoping
        supported = get_supported_protocols(base)

        # Auto-derive firmware fields only for supported protocols
        if firmware_version:
            # Prepare base identities only for supported protocols
            base_identities = {}
            for protocol in supported:
                identity_key = PROTOCOL_TO_IDENTITY_KEY.get(protocol)
                if identity_key:
                    # Handle s7_identity in protocol_quirks (legacy Siemens pattern)
                    if identity_key == "s7_identity":
                        base_identities[identity_key] = (
                            base.get("protocol_quirks", {}).get("s7_identity", {})
                            or base.get("s7_identity", {})
                        )
                    else:
                        base_identities[identity_key] = base.get(identity_key, {})

            # Skip derivation if no supported protocols
            if not base_identities:
                logger.debug(
                    f"No supported protocols found for CVE variant {variant.id}, "
                    f"skipping firmware derivation"
                )
            else:
                # Derive firmware fields only for supported protocols
                derived = derive_all_firmware_fields(
                    firmware_version=firmware_version,
                    base_identities=base_identities,
                    protocols=supported,
                )

                # Convert FirmwareFields to identity dicts
                for protocol, fw_fields in derived.items():
                    # Map protocol name to identity key
                    identity_key = f"{protocol}_identity"
                    if protocol == "ethernet_ip":
                        identity_key = "ethernet_ip_identity"

                    result[identity_key] = {
                        **base_identities.get(identity_key, {}),
                        **fw_fields.fields,
                    }

        # Apply explicit overrides from variant (highest priority)
        explicit_overrides = {
            "modbus_identity": variant.modbus_identity_override,
            "ethernet_ip_identity": variant.ethernet_ip_identity_override,
            "profinet_identity": variant.profinet_identity_override,
            "s7_identity": variant.s7_identity_override,
            "snmp_identity": getattr(variant, "snmp_identity_override", None),
            "bacnet_identity": getattr(variant, "bacnet_identity_override", None),
            "cip_identity_override": getattr(variant, "cip_identity_override", None),
        }

        for key, override in explicit_overrides.items():
            if override:
                if key not in result:
                    result[key] = {}
                result[key].update(override)

        return result

    @staticmethod
    def resolve_cve_sync(
        variant: VulnerableFingerprintVariant,
        base_fingerprint: dict[str, Any] | None = None,
    ) -> ResolvedCVEConfig:
        """Synchronous CVE resolution (for use in non-async contexts).

        This method does not perform database lookups - it works with
        an already-loaded variant.

        Args:
            variant: Pre-loaded VulnerableFingerprintVariant
            base_fingerprint: Optional base fingerprint for context

        Returns:
            ResolvedCVEConfig with all identity overrides
        """
        cve = variant.cve_vulnerability
        cve_id = cve.cve_id if cve else "UNKNOWN"
        severity = cve.severity if cve else "high"
        firmware_version = variant.firmware_version or ""

        protocol_identities = CVEFingerprintService._build_protocol_identities(
            variant=variant,
            firmware_version=firmware_version,
            base_fingerprint=base_fingerprint,
        )

        return ResolvedCVEConfig(
            cve_id=cve_id,
            firmware_version=firmware_version,
            display_name=variant.display_name or "CVE Variant",
            vendor=variant.target_vendor,
            target_models=variant.target_models or [],
            severity=severity,
            protocol_identities=protocol_identities,
            variant_id=str(variant.id) if variant.id else None,
            vulnerability_id=str(cve.id) if cve and cve.id else None,
        )
