"""CVE Vulnerability API routes.

This module provides REST API endpoints for:
- Listing CVE vulnerabilities by vendor/product
- Getting CVE details
- Listing vulnerable fingerprint variants
- Getting protocol identity overrides for vulnerability simulation
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.exceptions import NotFoundError

from app.api.deps import CurrentUser
from app.services.cve_data import (
    ALL_CVES,
    get_cve,
    get_cves_for_vendor,
    get_cves_for_product_family,
    get_critical_cves,
)
from app.services.vulnerable_variants import (
    get_all_vulnerable_variants,
    get_vulnerable_variants_for_cve,
    get_vulnerable_variants_for_vendor,
    get_variant_summary,
)

router = APIRouter(prefix="/cve", tags=["CVE Vulnerabilities"])


# ========== Response Models ==========


class CVESummaryResponse(BaseModel):
    """Summary of a CVE vulnerability."""

    cve_id: str
    title: str
    severity: str
    cvss_score: float | None
    vendor: str
    product_family: str
    affected_firmware_max: str
    fixed_firmware_version: str | None
    cyber_vision_detectable: bool
    exploit_available: bool


class CVEDetailResponse(BaseModel):
    """Full CVE vulnerability details."""

    cve_id: str
    title: str
    description: str | None
    severity: str
    cvss_score: float | None
    cvss_vector: str | None
    vendor: str
    product_family: str
    affected_models: list[str] | None
    affected_firmware_min: str | None
    affected_firmware_max: str
    fixed_firmware_version: str | None
    cyber_vision_detectable: bool
    detection_method: str | None
    advisory_url: str | None
    references: list[str] | None
    mitre_techniques: list[str] | None
    exploit_available: bool
    exploit_complexity: str | None
    published_date: datetime | None
    variant_count: int


class VulnerableVariantSummaryResponse(BaseModel):
    """Summary of a vulnerable fingerprint variant."""

    id: str
    cve_id: str
    display_name: str
    firmware_version: str
    target_vendor: str
    target_product_family: str | None
    severity: str | None
    cvss_score: float | None


class VulnerableVariantDetailResponse(BaseModel):
    """Full vulnerable variant details with protocol overrides."""

    id: str
    cve_id: str
    display_name: str
    firmware_version: str
    target_vendor: str
    target_product_family: str | None
    target_models: list[str] | None
    modbus_identity_override: dict[str, Any] | None
    ethernet_ip_identity_override: dict[str, Any] | None
    profinet_identity_override: dict[str, Any] | None
    s7_identity_override: dict[str, Any] | None
    cve_title: str | None
    cve_severity: str | None
    cve_cvss_score: float | None


class CVEStatsSummaryResponse(BaseModel):
    """Summary statistics for CVE vulnerabilities."""

    total_cves: int
    total_variants: int
    by_vendor: dict[str, int]
    by_severity: dict[str, int]
    critical_count: int
    cyber_vision_detectable: int


# ========== API Endpoints ==========


@router.get("/list", response_model=list[CVESummaryResponse])
async def list_cves(
    _current_user: CurrentUser,
    vendor: str | None = Query(None, description="Filter by vendor"),
    severity: str | None = Query(None, description="Filter by severity (critical, high, medium, low)"),
    cyber_vision_only: bool = Query(False, description="Only show Cyber Vision detectable CVEs"),
) -> list[CVESummaryResponse]:
    """List all CVE vulnerabilities.

    Args:
        vendor: Optional filter by vendor (Rockwell, Siemens, Schneider)
        severity: Optional filter by severity level
        cyber_vision_only: Only return CVEs detectable by Cisco Cyber Vision

    Returns:
        List of CVE summaries
    """
    if vendor:
        cves = get_cves_for_vendor(vendor)
    else:
        cves = ALL_CVES

    # Apply filters
    if severity:
        cves = [c for c in cves if c.get("severity") == severity.lower()]

    if cyber_vision_only:
        cves = [c for c in cves if c.get("cyber_vision_detectable", False)]

    return [
        CVESummaryResponse(
            cve_id=cve["cve_id"],
            title=cve["title"],
            severity=cve["severity"],
            cvss_score=cve.get("cvss_score"),
            vendor=cve["vendor"],
            product_family=cve["product_family"],
            affected_firmware_max=cve["affected_firmware_max"],
            fixed_firmware_version=cve.get("fixed_firmware_version"),
            cyber_vision_detectable=cve.get("cyber_vision_detectable", False),
            exploit_available=cve.get("exploit_available", False),
        )
        for cve in cves
    ]


@router.get("/detail/{cve_id}", response_model=CVEDetailResponse)
async def get_cve_detail(
    cve_id: str,
    _current_user: CurrentUser,
) -> CVEDetailResponse:
    """Get detailed CVE vulnerability information.

    Args:
        cve_id: CVE identifier (e.g., CVE-2022-1159)

    Returns:
        Full CVE details

    Raises:
        HTTPException: If CVE not found
    """
    cve = get_cve(cve_id)

    if not cve:
        raise NotFoundError("CVE", cve_id)

    # Count variants
    variants = get_vulnerable_variants_for_cve(cve_id)

    return CVEDetailResponse(
        cve_id=cve["cve_id"],
        title=cve["title"],
        description=cve.get("description"),
        severity=cve["severity"],
        cvss_score=cve.get("cvss_score"),
        cvss_vector=cve.get("cvss_vector"),
        vendor=cve["vendor"],
        product_family=cve["product_family"],
        affected_models=cve.get("affected_models"),
        affected_firmware_min=cve.get("affected_firmware_min"),
        affected_firmware_max=cve["affected_firmware_max"],
        fixed_firmware_version=cve.get("fixed_firmware_version"),
        cyber_vision_detectable=cve.get("cyber_vision_detectable", False),
        detection_method=cve.get("detection_method"),
        advisory_url=cve.get("advisory_url"),
        references=cve.get("references"),
        mitre_techniques=cve.get("mitre_techniques"),
        exploit_available=cve.get("exploit_available", False),
        exploit_complexity=cve.get("exploit_complexity"),
        published_date=cve.get("published_date"),
        variant_count=len(variants),
    )


@router.get("/vendors", response_model=list[dict])
async def list_cve_vendors(
    _current_user: CurrentUser,
) -> list[dict]:
    """List vendors with CVE vulnerability data.

    Returns:
        List of vendors with CVE counts
    """
    vendor_counts: dict[str, dict] = {}

    for cve in ALL_CVES:
        vendor = cve["vendor"]
        if vendor not in vendor_counts:
            vendor_counts[vendor] = {
                "vendor": vendor,
                "cve_count": 0,
                "critical_count": 0,
                "product_families": set(),
            }
        vendor_counts[vendor]["cve_count"] += 1
        vendor_counts[vendor]["product_families"].add(cve["product_family"])
        if cve["severity"] == "critical":
            vendor_counts[vendor]["critical_count"] += 1

    return [
        {
            "vendor": v["vendor"],
            "cve_count": v["cve_count"],
            "critical_count": v["critical_count"],
            "product_families": list(v["product_families"]),
        }
        for v in vendor_counts.values()
    ]


@router.get("/product/{vendor}/{product_family}", response_model=list[CVESummaryResponse])
async def get_cves_for_product(
    vendor: str,
    product_family: str,
    _current_user: CurrentUser,
) -> list[CVESummaryResponse]:
    """Get CVEs for a specific vendor/product family combination.

    Args:
        vendor: Vendor name (Rockwell, Siemens, Schneider)
        product_family: Product family (ControlLogix, S7-1500, Modicon M580)

    Returns:
        List of CVE summaries for the product
    """
    cves = get_cves_for_product_family(vendor, product_family)

    return [
        CVESummaryResponse(
            cve_id=cve["cve_id"],
            title=cve["title"],
            severity=cve["severity"],
            cvss_score=cve.get("cvss_score"),
            vendor=cve["vendor"],
            product_family=cve["product_family"],
            affected_firmware_max=cve["affected_firmware_max"],
            fixed_firmware_version=cve.get("fixed_firmware_version"),
            cyber_vision_detectable=cve.get("cyber_vision_detectable", False),
            exploit_available=cve.get("exploit_available", False),
        )
        for cve in cves
    ]


@router.get("/critical", response_model=list[CVESummaryResponse])
async def get_critical_vulnerabilities(
    _current_user: CurrentUser,
) -> list[CVESummaryResponse]:
    """Get all critical severity CVE vulnerabilities.

    Returns:
        List of critical CVE summaries
    """
    cves = get_critical_cves()

    return [
        CVESummaryResponse(
            cve_id=cve["cve_id"],
            title=cve["title"],
            severity=cve["severity"],
            cvss_score=cve.get("cvss_score"),
            vendor=cve["vendor"],
            product_family=cve["product_family"],
            affected_firmware_max=cve["affected_firmware_max"],
            fixed_firmware_version=cve.get("fixed_firmware_version"),
            cyber_vision_detectable=cve.get("cyber_vision_detectable", False),
            exploit_available=cve.get("exploit_available", False),
        )
        for cve in cves
    ]


@router.get("/stats", response_model=CVEStatsSummaryResponse)
async def get_cve_statistics(
    _current_user: CurrentUser,
) -> CVEStatsSummaryResponse:
    """Get CVE vulnerability statistics.

    Returns:
        Summary statistics for CVE vulnerabilities
    """
    summary = get_variant_summary()

    # Count CVEs by vendor
    by_vendor: dict[str, int] = {}
    by_severity: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    cyber_vision_count = 0

    for cve in ALL_CVES:
        vendor = cve["vendor"]
        by_vendor[vendor] = by_vendor.get(vendor, 0) + 1
        severity = cve["severity"]
        by_severity[severity] = by_severity.get(severity, 0) + 1
        if cve.get("cyber_vision_detectable", False):
            cyber_vision_count += 1

    return CVEStatsSummaryResponse(
        total_cves=len(ALL_CVES),
        total_variants=summary["total_variants"],
        by_vendor=by_vendor,
        by_severity=by_severity,
        critical_count=by_severity["critical"],
        cyber_vision_detectable=cyber_vision_count,
    )


# ========== Vulnerable Variant Endpoints ==========


@router.get("/variants", response_model=list[VulnerableVariantSummaryResponse])
async def list_vulnerable_variants(
    _current_user: CurrentUser,
    vendor: str | None = Query(None, description="Filter by vendor"),
    cve_id: str | None = Query(None, description="Filter by CVE ID"),
) -> list[VulnerableVariantSummaryResponse]:
    """List vulnerable fingerprint variants.

    These variants can be applied to device fingerprints to simulate
    devices with vulnerable firmware versions.

    Args:
        vendor: Optional filter by vendor
        cve_id: Optional filter by CVE ID

    Returns:
        List of vulnerable variant summaries
    """
    if cve_id:
        variants = get_vulnerable_variants_for_cve(cve_id)
    elif vendor:
        variants = get_vulnerable_variants_for_vendor(vendor)
    else:
        variants = get_all_vulnerable_variants()

    return [
        VulnerableVariantSummaryResponse(
            id=v["id"],
            cve_id=v["cve_id"],
            display_name=v["display_name"],
            firmware_version=v["firmware_version"],
            target_vendor=v["target_vendor"],
            target_product_family=v.get("target_product_family"),
            severity=v.get("_cve_severity"),
            cvss_score=v.get("_cve_cvss_score"),
        )
        for v in variants
    ]


@router.get("/variants/{cve_id}", response_model=list[VulnerableVariantDetailResponse])
async def get_variants_for_cve(
    cve_id: str,
    _current_user: CurrentUser,
) -> list[VulnerableVariantDetailResponse]:
    """Get vulnerable variants for a specific CVE.

    These variants contain the protocol identity overrides needed to
    simulate a device with the vulnerable firmware version.

    Args:
        cve_id: CVE identifier

    Returns:
        List of variant details with protocol overrides

    Raises:
        HTTPException: If CVE not found
    """
    cve = get_cve(cve_id)
    if not cve:
        raise NotFoundError("CVE", cve_id)

    variants = get_vulnerable_variants_for_cve(cve_id)

    if not variants:
        raise NotFoundError("Vulnerable variants for CVE", cve_id)

    return [
        VulnerableVariantDetailResponse(
            id=v["id"],
            cve_id=v["cve_id"],
            display_name=v["display_name"],
            firmware_version=v["firmware_version"],
            target_vendor=v["target_vendor"],
            target_product_family=v.get("target_product_family"),
            target_models=v.get("target_models"),
            modbus_identity_override=v.get("modbus_identity_override"),
            ethernet_ip_identity_override=v.get("ethernet_ip_identity_override"),
            profinet_identity_override=v.get("profinet_identity_override"),
            s7_identity_override=v.get("s7_identity_override"),
            cve_title=v.get("_cve_title"),
            cve_severity=v.get("_cve_severity"),
            cve_cvss_score=v.get("_cve_cvss_score"),
        )
        for v in variants
    ]


@router.get("/variants/detail/{variant_id}", response_model=VulnerableVariantDetailResponse)
async def get_variant_detail(
    variant_id: str,
    _current_user: CurrentUser,
) -> VulnerableVariantDetailResponse:
    """Get detailed information for a specific vulnerable variant.

    Args:
        variant_id: Variant identifier

    Returns:
        Full variant details with protocol overrides

    Raises:
        HTTPException: If variant not found
    """
    all_variants = get_all_vulnerable_variants()

    for v in all_variants:
        if v["id"] == variant_id:
            return VulnerableVariantDetailResponse(
                id=v["id"],
                cve_id=v["cve_id"],
                display_name=v["display_name"],
                firmware_version=v["firmware_version"],
                target_vendor=v["target_vendor"],
                target_product_family=v.get("target_product_family"),
                target_models=v.get("target_models"),
                modbus_identity_override=v.get("modbus_identity_override"),
                ethernet_ip_identity_override=v.get("ethernet_ip_identity_override"),
                profinet_identity_override=v.get("profinet_identity_override"),
                s7_identity_override=v.get("s7_identity_override"),
                cve_title=v.get("_cve_title"),
                cve_severity=v.get("_cve_severity"),
                cve_cvss_score=v.get("_cve_cvss_score"),
            )

    raise NotFoundError("Vulnerable variant", variant_id)
