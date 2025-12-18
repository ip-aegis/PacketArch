"""CVE Fingerprint Service.

Service for resolving CVE vulnerabilities to vulnerable fingerprint variants.
This enables devices to be associated with specific CVEs and emit vulnerable
firmware versions in their protocol identity responses.
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cve_vulnerability import CVEVulnerability
from app.models.vulnerable_fingerprint import VulnerableFingerprintVariant

logger = logging.getLogger(__name__)


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

        Args:
            variant: Vulnerable fingerprint variant

        Returns:
            Dictionary with protocol-specific identity overrides
        """
        return {
            "modbus_identity": variant.modbus_identity_override or {},
            "ethernet_ip_identity": variant.ethernet_ip_identity_override or {},
            "profinet_identity": variant.profinet_identity_override or {},
            "s7_identity": variant.s7_identity_override or {},
            # CIP Identity Object overrides for deep fingerprinting (Cyber Vision)
            "cip_identity_override": getattr(variant, "cip_identity_override", None) or {},
            "firmware_version": variant.firmware_version,
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
