# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Fingerprint conversion and database adapter functions.

Provides backwards compatibility with existing code that expects
fingerprint dictionaries (FingerprintApplicator, scenario templates,
AI scenario generator).
"""

import logging
from typing import Any

from app.services.device_templates._api import (
    get_all_templates,
    get_template_by_id,
    get_templates_by_vendor,
)
from app.services.device_templates._helpers import (
    generate_serial_number,
    generate_station_name,
)
from app.services.device_templates._registry import DEVICE_TEMPLATES
from app.services.device_templates._types import DeviceTemplate
from app.core.vendor_normalize import vendors_match

logger = logging.getLogger(__name__)


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
    model_lower = model.lower()

    def _vnorm(s: str) -> str:
        return s.lower().replace("_", " ").strip()

    query_vendor = _vnorm(vendor)

    # Score candidates and return the most specific. A model token like
    # "CP-8000" can be shared across vendors (Siemens vs Siemens ITS); ranking
    # by model specificity AND exact-vendor preference resolves to the right
    # template deterministically instead of by registry iteration order.
    best: DeviceTemplate | None = None
    best_score = -1
    for template in DEVICE_TEMPLATES.values():
        # Vendor match via the canonical normalizer so scenario vendor keys
        # ("siemens_its", "automated_logic", "distech") resolve to the template
        # vendor ("Siemens ITS", "Automated Logic", "Distech Controls").
        if not vendors_match(vendor, template.vendor):
            continue
        tm, tn = template.model.lower(), template.model_name.lower()
        if tm == model_lower:
            model_score = 4
        elif tn == model_lower:
            model_score = 3
        elif model_lower in tm:
            model_score = 2
        elif model_lower in tn:
            model_score = 1
        else:
            continue
        # Prefer an exact (normalized) vendor match over a looser fuzzy one.
        vendor_bonus = 1 if _vnorm(template.vendor) == query_vendor else 0
        score = model_score * 2 + vendor_bonus
        if score > best_score:
            best_score, best = score, template

    return best


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
        Fingerprint dictionary compatible with FingerprintApplicator
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

    # Authoritative supported_protocols. Templates that explicitly declare
    # the field win; otherwise we compute a vendor-aware default that
    # filters out protocols the device doesn't natively serve even when
    # over-populated identity blocks would suggest otherwise. This is the
    # one source of truth for "what protocols can this fingerprint serve"
    # downstream of validation, repair, and traffic generation.
    from app.services.device_templates._protocol_defaults import (
        compute_default_supported_protocols,
    )
    if template.supported_protocols:
        supported = list(template.supported_protocols)
    else:
        supported = compute_default_supported_protocols(template)
    # SNMP carve-out: every device with a vendor name can serve SNMP via
    # the noise generator's synthesised identity (vendor OUI → enterprise
    # OID). Many template declarations forgot to list SNMP — patching here
    # so every fingerprintable device exposes SNMP for monitoring.
    if template.vendor and "snmp" not in supported:
        supported.append("snmp")
    fingerprint["supported_protocols"] = supported

    # Add protocol identities with firmware overrides
    protocol_identities = [
        ("modbus_identity", template.modbus_identity),
        ("ethernet_ip_identity", template.ethernet_ip_identity),
        ("profinet_identity", template.profinet_identity),
        ("s7_identity", template.s7_identity),
        ("bacnet_identity", template.bacnet_identity),
        ("snmp_identity", template.snmp_identity),
        ("opc_ua_identity", template.opc_ua_identity),
        ("dnp3_identity", template.dnp3_identity),
        ("iec104_identity", template.iec104_identity),
        ("iec61850_identity", template.iec61850_identity),
        ("c37118_identity", template.c37118_identity),
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
            elif key == "bacnet_identity" and "firmware_revision" not in merged:
                merged["firmware_revision"] = firmware.version
            elif key == "s7_identity" and "firmware_version" not in merged:
                merged["firmware_version"] = firmware.version
            elif key == "snmp_identity":
                if "firmware_version" not in merged:
                    merged["firmware_version"] = firmware.version
                # CV reads the device's firmware/IOS version from sys_descr, NOT
                # from a separate firmware_version field. A template with a
                # hardcoded versioned sys_descr (e.g. "...Version 17.15.01...")
                # otherwise masks the pinned firmware and CV sees a patched
                # device. Rewrite the version token in sys_descr to match — but
                # ONLY when the firmware parses cleanly as a numeric version;
                # non-standard formats (e.g. "R520.2") must be left untouched or
                # the replacement corrupts the string.
                if merged.get("sys_descr"):
                    from app.protocol_engines.firmware_version_deriver import (
                        FirmwareVersionDeriver,
                        FirmwareVersionParser,
                    )
                    parsed = FirmwareVersionParser.parse(firmware.version)
                    if parsed.major or parsed.minor:
                        merged["sys_descr"] = FirmwareVersionDeriver(
                            firmware.version,
                            {"snmp_identity": {"sys_descr": merged["sys_descr"]}},
                        ).derive_snmp()["sys_descr"]
            elif key == "dnp3_identity" and "software_version" not in merged:
                merged["software_version"] = firmware.version
            elif key == "iec104_identity" and "software_version" not in merged:
                merged["software_version"] = firmware.version
            elif key == "iec61850_identity" and "software_version" not in merged:
                merged["software_version"] = firmware.version
            elif key == "c37118_identity" and "software_version" not in merged:
                merged["software_version"] = firmware.version
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


def get_fingerprints_by_vendor_and_type(
    vendor: str, device_type: str,
) -> list[dict[str, Any]]:
    """Get fingerprint dictionaries for a vendor filtered by device_type.

    Args:
        vendor: Vendor name (case-insensitive)
        device_type: Device type (e.g. "plc", "sensor", "drive")

    Returns:
        List of fingerprint dictionaries matching both vendor and device_type
    """
    fingerprints = []
    for template in get_templates_by_vendor(vendor):
        if template.device_type == device_type:
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


def template_db_to_fingerprint_dict(template) -> dict[str, Any] | None:
    """Convert a DeviceTemplate DB model to a fingerprint dictionary.

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
        for protocol in ["modbus", "ethernet_ip", "profinet", "s7", "snmp", "bacnet", "opc_ua", "dnp3", "iec104"]:
            identity = template.get_protocol_identity(protocol)
            fp[f"{protocol}_identity"] = dict(identity) if identity else None

        # Authoritative supported_protocols — same logic as the python
        # template path. DB templates use `active_protocols` for explicit
        # declarations (legacy column name); compute defaults otherwise.
        from app.services.device_templates._protocol_defaults import (
            compute_default_supported_protocols_from_db,
        )
        explicit = getattr(template, "active_protocols", None)
        if explicit:
            supported = list(explicit)
        else:
            supported = compute_default_supported_protocols_from_db(template)
        if template.vendor and "snmp" not in supported:
            supported.append("snmp")
        fp["supported_protocols"] = supported

        return fp

    except Exception:
        template_id = getattr(template, "id", None) if template is not None else None
        logger.exception(
            "Failed to convert DeviceTemplate to fingerprint dict (template_id=%s)",
            template_id,
        )
        return None


def get_fingerprint_from_db_sync(
    vendor: str,
    model: str,
) -> dict[str, Any] | None:
    """Query DeviceTemplate DB (sync) and return fingerprint dict.

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
                DeviceTemplate.is_active.is_(True),  # noqa: E712
            ).first()

            return template_db_to_fingerprint_dict(template)

    except Exception:
        logger.exception(
            "Sync fingerprint DB lookup failed (vendor=%r, model=%r)",
            vendor, model,
        )
        return None


async def get_fingerprint_from_db_async(
    db,
    vendor: str,
    model: str,
) -> dict[str, Any] | None:
    """Query DeviceTemplate DB (async) and return fingerprint dict.

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
                DeviceTemplate.is_active.is_(True),  # noqa: E712
            )
        )
        template = result.scalar_one_or_none()

        return template_db_to_fingerprint_dict(template)

    except Exception:
        logger.exception(
            "Async fingerprint DB lookup failed (vendor=%r, model=%r)",
            vendor, model,
        )
        return None


def get_fingerprint_with_fallback(
    vendor: str,
    model: str,
    firmware_version: str | None = None,
) -> dict[str, Any] | None:
    """Get fingerprint from DB with fallback to Python dataclass library.

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
