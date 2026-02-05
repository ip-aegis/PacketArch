"""Fingerprint, Realism, and CVE tools for MCP.

This module provides tools for:
- Listing and applying vendor fingerprints
- Configuring device/flow realism parameters
- Searching and applying CVE vulnerabilities
"""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.scenario import Scenario
from app.services.device_templates import (
    get_all_fingerprints,
    get_fingerprint_by_vendor_model,
    get_fingerprints_by_vendor,
)
from app.services.cve_data import (
    ALL_CVES,
    get_cve,
    get_cves_for_vendor,
    get_cves_for_product_family,
)
from app.services.vendor_fingerprints.vulnerable_variants import (
    get_all_vulnerable_variants,
    get_vulnerable_variants_for_cve,
    get_vulnerable_variants_for_vendor,
)
from app.scenario_templates.base import DEFAULT_ERROR_CONFIGS
from app.mcp_server.tools.validation_tools import VERTICAL_NORMS


# =============================================================================
# Fingerprint Tools
# =============================================================================


async def list_vendor_fingerprints(vendor: str | None = None) -> str:
    """List available vendor fingerprints.

    Args:
        vendor: Optional vendor name to filter by

    Returns:
        JSON string with fingerprints list
    """
    if vendor:
        fingerprints = get_fingerprints_by_vendor(vendor)
    else:
        fingerprints = get_all_fingerprints()

    # Extract relevant fields
    result = [
        {
            "vendor": fp.get("vendor", "Unknown"),
            "model": fp.get("model", ""),
            "firmware_version": fp.get("firmware_version"),
            "protocols": _get_protocols_from_fingerprint(fp),
        }
        for fp in fingerprints
    ]

    return json.dumps({"fingerprints": result, "count": len(result)})


async def get_fingerprint_detail(vendor: str, model: str) -> str:
    """Get full fingerprint details including TCP stack, timing, quirks.

    Args:
        vendor: Vendor name
        model: Model identifier

    Returns:
        JSON string with full fingerprint details
    """
    fingerprint = get_fingerprint_by_vendor_model(vendor, model)

    if not fingerprint:
        return json.dumps({"error": f"Fingerprint not found for {vendor} / {model}"})

    return json.dumps({
        "vendor": fingerprint.get("vendor", "Unknown"),
        "model": fingerprint.get("model", ""),
        "firmware_version": fingerprint.get("firmware_version"),
        "oui_prefixes": fingerprint.get("oui_prefixes", []),
        "modbus_identity": fingerprint.get("modbus_identity"),
        "ethernet_ip_identity": fingerprint.get("ethernet_ip_identity"),
        "profinet_identity": fingerprint.get("profinet_identity"),
        "tcp_stack": fingerprint.get("tcp_stack"),
        "response_timing": fingerprint.get("response_timing"),
        "error_behavior": fingerprint.get("error_behavior"),
        "protocol_quirks": fingerprint.get("protocol_quirks"),
    })


async def suggest_fingerprint_for_device(
    device_type: str, preferred_vendor: str | None = None
) -> str:
    """Suggest appropriate fingerprints for a device type.

    Args:
        device_type: Device type (plc, hmi, rtu, drive, etc.)
        preferred_vendor: Optional preferred vendor

    Returns:
        JSON string with suggested fingerprints and default error config
    """
    # Get typical vendors for device type
    device_vendor_map = {
        "plc": ["siemens", "rockwell", "schneider", "abb"],
        "hmi": ["siemens", "rockwell", "schneider"],
        "rtu": ["schneider", "abb", "honeywell"],
        "drive": ["siemens", "rockwell", "abb"],
        "io_module": ["siemens", "rockwell", "schneider"],
        "relay": ["siemens", "abb", "ge"],
        "sensor": ["siemens", "schneider", "honeywell"],
    }

    typical_vendors = device_vendor_map.get(device_type, ["siemens", "rockwell", "schneider"])

    # Prioritize preferred vendor
    if preferred_vendor and preferred_vendor.lower() in typical_vendors:
        typical_vendors = [preferred_vendor.lower()] + [
            v for v in typical_vendors if v != preferred_vendor.lower()
        ]

    # Get fingerprints for suggested vendors
    suggested = []
    for vendor in typical_vendors[:4]:
        fingerprints = get_fingerprints_by_vendor(vendor)
        for fp in fingerprints[:2]:
            suggested.append({
                "vendor": fp.get("vendor", "Unknown"),
                "model": fp.get("model", ""),
                "firmware_version": fp.get("firmware_version"),
                "protocols": _get_protocols_from_fingerprint(fp),
            })

    # Get default error config
    error_config = DEFAULT_ERROR_CONFIGS.get(device_type)
    default_error = None
    if error_config:
        default_error = {
            "exception_rate": error_config.exception_rate,
            "timeout_rate": error_config.timeout_rate,
            "retry_behavior": error_config.retry_behavior,
            "max_retries": error_config.max_retries,
        }

    return json.dumps({
        "device_type": device_type,
        "typical_vendors": typical_vendors,
        "suggested_fingerprints": suggested,
        "default_error_config": default_error,
    })


async def apply_fingerprint_to_device(
    db: AsyncSession, scenario_id: str, device_id: str, vendor: str, model: str
) -> str:
    """Apply a vendor fingerprint to a device.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        vendor: Vendor name
        model: Model identifier

    Returns:
        JSON string with result
    """
    # Get fingerprint
    fingerprint = get_fingerprint_by_vendor_model(vendor, model)
    if not fingerprint:
        return json.dumps({"error": f"Fingerprint not found for {vendor} / {model}"})

    # Get scenario
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    # Refresh to get latest state (important when multiple tools modify the same scenario)
    await db.refresh(scenario)

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    # Apply fingerprint to device
    device = devices[device_id].copy()
    device["fingerprint"] = {
        "vendor": fingerprint.get("vendor"),
        "model": fingerprint.get("model"),
        "firmware_version": fingerprint.get("firmware_version"),
    }
    device["modbus_identity"] = fingerprint.get("modbus_identity")
    device["ethernet_ip_identity"] = fingerprint.get("ethernet_ip_identity")
    device["profinet_identity"] = fingerprint.get("profinet_identity")
    device["tcp_stack"] = fingerprint.get("tcp_stack")
    device["response_timing"] = fingerprint.get("response_timing")
    device["error_behavior"] = fingerprint.get("error_behavior")
    device["protocol_quirks"] = fingerprint.get("protocol_quirks")

    # Set OUI-based MAC if available
    oui_prefixes = fingerprint.get("oui_prefixes", [])
    if oui_prefixes:
        import random
        oui = random.choice(oui_prefixes)
        suffix = ":".join([f"{random.randint(0, 255):02X}" for _ in range(3)])
        if "network" not in device:
            device["network"] = {}
        if not device["network"].get("macAddress"):
            device["network"]["macAddress"] = f"{oui}:{suffix}"

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "fingerprint_applied": {
            "vendor": vendor,
            "model": model,
        },
    })


# =============================================================================
# Realism Configuration Tools
# =============================================================================


async def configure_device_realism(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    response_timing: dict[str, Any] | None = None,
    error_config: dict[str, Any] | None = None,
    protocol_quirks: dict[str, Any] | None = None,
) -> str:
    """Set realism parameters for a device.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        response_timing: Response timing config {mean_ms, std_dev_ms}
        error_config: Error config {exception_rate, timeout_rate}
        protocol_quirks: Protocol-specific quirks

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    if response_timing:
        device["response_timing"] = {
            **(device.get("response_timing") or {}),
            **response_timing,
        }

    if error_config:
        device["error_behavior"] = {
            **(device.get("error_behavior") or {}),
            **error_config,
        }

    if protocol_quirks:
        device["protocol_quirks"] = {
            **(device.get("protocol_quirks") or {}),
            **protocol_quirks,
        }

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "realism_config": {
            "response_timing": device.get("response_timing"),
            "error_behavior": device.get("error_behavior"),
            "protocol_quirks": device.get("protocol_quirks"),
        },
    })


async def configure_flow_realism(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    timing_jitter_ms: float | None = None,
    packet_loss_rate: float | None = None,
    response_delay_variance_ms: float | None = None,
) -> str:
    """Set realism parameters for a flow.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        timing_jitter_ms: Timing jitter in milliseconds
        packet_loss_rate: Packet loss rate (0.0-1.0)
        response_delay_variance_ms: Response delay variance in milliseconds

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Initialize realism config if not present
    if "realism" not in flow:
        flow["realism"] = {}

    if timing_jitter_ms is not None:
        flow["realism"]["timing_jitter_ms"] = timing_jitter_ms

    if packet_loss_rate is not None:
        flow["realism"]["packet_loss_rate"] = max(0.0, min(1.0, packet_loss_rate))

    if response_delay_variance_ms is not None:
        flow["realism"]["response_delay_variance_ms"] = response_delay_variance_ms

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "realism_config": flow.get("realism"),
    })


async def apply_realism_preset(
    db: AsyncSession,
    scenario_id: str,
    preset: str,
) -> str:
    """Apply a realism preset to entire scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        preset: Preset name ('minimal', 'moderate', 'high_fidelity', 'vertical_specific')

    Returns:
        JSON string with result
    """
    presets = {
        "minimal": {
            "response_timing": {"mean_ms": 5, "std_dev_ms": 0},
            "error_config": {"exception_rate": 0, "timeout_rate": 0},
            "flow_jitter_ms": 0,
            "packet_loss_rate": 0,
        },
        "moderate": {
            "response_timing": {"mean_ms": 10, "std_dev_ms": 3},
            "error_config": {"exception_rate": 0.001, "timeout_rate": 0.0005},
            "flow_jitter_ms": 5,
            "packet_loss_rate": 0.0001,
        },
        "high_fidelity": {
            "response_timing": {"mean_ms": 15, "std_dev_ms": 8},
            "error_config": {"exception_rate": 0.005, "timeout_rate": 0.002},
            "flow_jitter_ms": 10,
            "packet_loss_rate": 0.001,
        },
    }

    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})
    vertical = scenario.vertical

    # Get preset config
    if preset == "vertical_specific" and vertical and vertical in VERTICAL_NORMS:
        norms = VERTICAL_NORMS[vertical]
        # Use vertical-specific timing
        typical_intervals = norms.get("typical_poll_intervals_ms", [1000])
        avg_interval = sum(typical_intervals) / len(typical_intervals)
        preset_config = {
            "response_timing": {"mean_ms": avg_interval * 0.01, "std_dev_ms": avg_interval * 0.005},
            "error_config": {"exception_rate": 0.002, "timeout_rate": 0.001},
            "flow_jitter_ms": avg_interval * 0.02,
            "packet_loss_rate": 0.0005,
        }
    elif preset in presets:
        preset_config = presets[preset]
    else:
        return json.dumps({"error": f"Unknown preset: {preset}. Available: minimal, moderate, high_fidelity, vertical_specific"})

    devices_updated = 0
    flows_updated = 0

    # Apply to all devices
    for device_id, device in devices.items():
        device = device.copy()
        device["response_timing"] = preset_config["response_timing"]
        device["error_behavior"] = preset_config["error_config"]
        devices[device_id] = device
        devices_updated += 1

    # Apply to all flows
    for flow_id, flow in flows.items():
        flow = flow.copy()
        flow["realism"] = {
            "timing_jitter_ms": preset_config["flow_jitter_ms"],
            "packet_loss_rate": preset_config["packet_loss_rate"],
        }
        flows[flow_id] = flow
        flows_updated += 1

    definition["devices"] = devices
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "preset": preset,
        "devices_updated": devices_updated,
        "flows_updated": flows_updated,
    })


# =============================================================================
# CVE & Vulnerability Tools
# =============================================================================


async def search_cves(
    vendor: str | None = None,
    product_family: str | None = None,
    severity: str | None = None,
    cyber_vision_detectable: bool | None = None,
) -> str:
    """Search CVE database with filters.

    Args:
        vendor: Filter by vendor name
        product_family: Filter by product family
        severity: Filter by severity (critical, high, medium, low)
        cyber_vision_detectable: Filter by Cyber Vision detectability

    Returns:
        JSON string with matching CVEs
    """
    if product_family and vendor:
        cves = get_cves_for_product_family(vendor, product_family)
    elif vendor:
        cves = get_cves_for_vendor(vendor)
    else:
        cves = ALL_CVES

    # Apply filters
    if severity:
        cves = [c for c in cves if c.get("severity") == severity.lower()]

    if cyber_vision_detectable is not None:
        cves = [c for c in cves if c.get("cyber_vision_detectable", False) == cyber_vision_detectable]

    result = [
        {
            "cve_id": cve["cve_id"],
            "title": cve["title"],
            "severity": cve["severity"],
            "cvss_score": cve.get("cvss_score"),
            "vendor": cve["vendor"],
            "product_family": cve["product_family"],
        }
        for cve in cves
    ]

    return json.dumps({"cves": result, "count": len(result)})


async def get_cve_detail(cve_id: str) -> str:
    """Get full CVE details including MITRE techniques and exploit info.

    Args:
        cve_id: CVE identifier

    Returns:
        JSON string with full CVE details
    """
    cve = get_cve(cve_id)

    if not cve:
        return json.dumps({"error": f"CVE '{cve_id}' not found"})

    # Count variants
    variants = get_vulnerable_variants_for_cve(cve_id)

    return json.dumps({
        "cve_id": cve["cve_id"],
        "title": cve["title"],
        "description": cve.get("description"),
        "severity": cve["severity"],
        "cvss_score": cve.get("cvss_score"),
        "cvss_vector": cve.get("cvss_vector"),
        "vendor": cve["vendor"],
        "product_family": cve["product_family"],
        "affected_models": cve.get("affected_models"),
        "affected_firmware_min": cve.get("affected_firmware_min"),
        "affected_firmware_max": cve["affected_firmware_max"],
        "fixed_firmware_version": cve.get("fixed_firmware_version"),
        "cyber_vision_detectable": cve.get("cyber_vision_detectable", False),
        "detection_method": cve.get("detection_method"),
        "mitre_techniques": cve.get("mitre_techniques"),
        "exploit_available": cve.get("exploit_available", False),
        "exploit_complexity": cve.get("exploit_complexity"),
        "variant_count": len(variants),
    })


async def list_vulnerable_variants(
    vendor: str | None = None,
    cve_id: str | None = None,
) -> str:
    """List vulnerable fingerprint variants.

    Args:
        vendor: Filter by vendor
        cve_id: Filter by CVE ID

    Returns:
        JSON string with variants list
    """
    if cve_id:
        variants = get_vulnerable_variants_for_cve(cve_id)
    elif vendor:
        variants = get_vulnerable_variants_for_vendor(vendor)
    else:
        variants = get_all_vulnerable_variants()

    result = [
        {
            "id": v["id"],
            "cve_id": v["cve_id"],
            "display_name": v["display_name"],
            "firmware_version": v["firmware_version"],
            "target_vendor": v["target_vendor"],
            "target_product_family": v.get("target_product_family"),
            "severity": v.get("_cve_severity"),
            "cvss_score": v.get("_cve_cvss_score"),
        }
        for v in variants
    ]

    return json.dumps({"variants": result, "count": len(result)})


async def apply_cve_to_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    cve_id: str,
    variant_id: str | None = None,
) -> str:
    """Apply a CVE vulnerability to a device by modifying its fingerprint.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        cve_id: CVE identifier
        variant_id: Optional specific variant ID

    Returns:
        JSON string with result
    """
    # Get CVE
    cve = get_cve(cve_id)
    if not cve:
        return json.dumps({"error": f"CVE '{cve_id}' not found"})

    # Get variants
    variants = get_vulnerable_variants_for_cve(cve_id)
    if not variants:
        return json.dumps({"error": f"No vulnerable variants found for CVE '{cve_id}'"})

    # Select variant
    if variant_id:
        variant = next((v for v in variants if v["id"] == variant_id), None)
        if not variant:
            return json.dumps({"error": f"Variant '{variant_id}' not found for CVE '{cve_id}'"})
    else:
        variant = variants[0]  # Use first available

    # Get scenario
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Track which identity overrides were applied
    identity_overrides_applied = {}

    # Apply identity overrides from variant
    if variant.get("modbus_identity_override"):
        device["modbus_identity"] = {
            **(device.get("modbus_identity") or {}),
            **variant["modbus_identity_override"],
        }
        identity_overrides_applied["modbus"] = True

    if variant.get("ethernet_ip_identity_override"):
        device["ethernet_ip_identity"] = {
            **(device.get("ethernet_ip_identity") or {}),
            **variant["ethernet_ip_identity_override"],
        }
        identity_overrides_applied["ethernet_ip"] = True

    if variant.get("profinet_identity_override"):
        device["profinet_identity"] = {
            **(device.get("profinet_identity") or {}),
            **variant["profinet_identity_override"],
        }
        identity_overrides_applied["profinet"] = True

    if variant.get("s7_identity_override"):
        device["s7_identity"] = {
            **(device.get("s7_identity") or {}),
            **variant["s7_identity_override"],
        }
        identity_overrides_applied["s7"] = True

    # Track applied CVEs
    if "applied_cves" not in device:
        device["applied_cves"] = []
    device["applied_cves"].append({
        "cve_id": cve_id,
        "variant_id": variant["id"],
        "severity": cve["severity"],
    })

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "cve_id": cve_id,
        "applied_variant": {
            "id": variant["id"],
            "display_name": variant["display_name"],
            "firmware_version": variant["firmware_version"],
        },
        "identity_overrides_applied": identity_overrides_applied,
    })


async def suggest_cves_for_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
) -> str:
    """Suggest relevant CVEs based on device vendor/model.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID

    Returns:
        JSON string with suggested CVEs
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id]
    fingerprint = device.get("fingerprint", {})
    device_vendor = fingerprint.get("vendor", device.get("vendor", "")).lower()
    device_model = fingerprint.get("model", device.get("model", ""))

    if not device_vendor:
        return json.dumps({
            "error": "Device has no vendor information. Apply a fingerprint first.",
            "device_id": device_id,
        })

    # Get CVEs for vendor
    matching_cves = get_cves_for_vendor(device_vendor)

    # Score by relevance
    scored_cves = []
    for cve in matching_cves:
        score = 0.5  # Base score for vendor match

        # Increase score for product family match
        if device_model and cve.get("product_family", "").lower() in device_model.lower():
            score += 0.3

        # Increase score for severity
        severity_scores = {"critical": 0.2, "high": 0.15, "medium": 0.1, "low": 0.05}
        score += severity_scores.get(cve.get("severity", ""), 0)

        scored_cves.append({
            "cve_id": cve["cve_id"],
            "title": cve["title"],
            "severity": cve["severity"],
            "relevance_score": round(score, 2),
        })

    # Sort by relevance
    scored_cves.sort(key=lambda x: x["relevance_score"], reverse=True)

    # Get available variants
    variants = get_vulnerable_variants_for_vendor(device_vendor)
    available_variants = [
        {
            "variant_id": v["id"],
            "cve_id": v["cve_id"],
            "display_name": v["display_name"],
        }
        for v in variants[:10]
    ]

    return json.dumps({
        "device_id": device_id,
        "device_vendor": device_vendor,
        "device_model": device_model,
        "matching_cves": scored_cves[:10],
        "available_variants": available_variants,
    })


async def get_scenario_vulnerability_profile(
    db: AsyncSession,
    scenario_id: str,
) -> str:
    """Get vulnerability profile for entire scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string with vulnerability profile
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition
    devices = definition.get("devices", {})

    total_devices = len(devices)
    vulnerable_devices = []
    vulnerability_coverage = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    suggested_additions = []

    for device_id, device in devices.items():
        applied_cves = device.get("applied_cves", [])

        if applied_cves:
            vulnerable_devices.append({
                "device_id": device_id,
                "device_name": device.get("name", device_id),
                "cves_applied": [c["cve_id"] for c in applied_cves],
            })

            for cve in applied_cves:
                severity = cve.get("severity", "low")
                if severity in vulnerability_coverage:
                    vulnerability_coverage[severity] += 1
        else:
            # Suggest CVEs for devices without vulnerabilities
            fingerprint = device.get("fingerprint", {})
            device_vendor = fingerprint.get("vendor", device.get("vendor", "")).lower()

            if device_vendor:
                vendor_cves = get_cves_for_vendor(device_vendor)[:3]
                if vendor_cves:
                    suggested_additions.append({
                        "device_id": device_id,
                        "device_name": device.get("name", device_id),
                        "suggested_cves": [c["cve_id"] for c in vendor_cves],
                    })

    return json.dumps({
        "total_devices": total_devices,
        "vulnerable_devices": vulnerable_devices,
        "vulnerable_device_count": len(vulnerable_devices),
        "vulnerability_coverage": vulnerability_coverage,
        "suggested_additions": suggested_additions[:5],
    })


# =============================================================================
# Helper Functions
# =============================================================================


def _get_protocols_from_fingerprint(fp: dict[str, Any]) -> list[str]:
    """Extract supported protocols from fingerprint data."""
    protocols = []

    if fp.get("modbus_identity"):
        protocols.append("modbus_tcp")
    if fp.get("ethernet_ip_identity"):
        protocols.append("ethernet_ip")
    if fp.get("profinet_identity"):
        protocols.append("profinet")

    quirks = fp.get("protocol_quirks", {})
    if "s7_max_pdu_size" in quirks and "s7" not in protocols:
        protocols.append("s7")

    return protocols if protocols else ["modbus_tcp"]
