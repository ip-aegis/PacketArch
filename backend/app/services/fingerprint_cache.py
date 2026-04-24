# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Fingerprint Cache Service with Pre-Indexing.

This module provides O(1) fingerprint lookups instead of O(n) scans.
Fingerprints are indexed at startup/first use for efficient access.

Index types:
- Primary: (vendor, model) -> fingerprint
- Secondary: vendor -> [fingerprints]
- Alt model: protocol identity fields -> fingerprint

This service is thread-safe and uses a singleton pattern.

Data Sources (in priority order):
1. device_templates module (AUTHORITATIVE SOURCE for all fingerprint data)
2. DeviceTemplate DB table (enhancement layer: CVE data, firmware variants)

The device_templates module is the single source of truth for protocol identity data.
DeviceTemplate DB can ENHANCE fingerprints (add CVE tracking, firmware variants) but
NEVER overrides protocol identity fields from device_templates.
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from app.core.vendor_normalize import normalize_vendor

logger = logging.getLogger(__name__)


@dataclass
class FingerprintIndex:
    """Indexed fingerprint data for fast lookups.

    Attributes:
        by_vendor_model: Primary index (vendor, model) -> fingerprint
        by_vendor: Secondary index vendor -> list of fingerprints
        by_alt_model: Alternative model lookups from protocol identities
        all_fingerprints: Raw list of all fingerprints
    """

    by_vendor_model: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    by_vendor: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    by_alt_model: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    all_fingerprints: list[dict[str, Any]] = field(default_factory=list)


class FingerprintCache:
    """Thread-safe singleton cache for vendor fingerprints.

    Provides O(1) lookups instead of scanning all fingerprints.
    Index is built lazily on first access.

    Usage:
        cache = FingerprintCache.get_instance()
        fp = cache.get_by_vendor_model("siemens", "CPU 1516-3 PN/DP")
    """

    _instance: "FingerprintCache | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        """Initialize empty cache. Use get_instance() for singleton access."""
        self._index: FingerprintIndex | None = None
        self._index_lock = threading.RLock()
        self._built = False

    @classmethod
    def get_instance(cls) -> "FingerprintCache":
        """Get the singleton cache instance.

        Thread-safe lazy initialization.

        Returns:
            FingerprintCache singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load_db_enhancements(self) -> dict[tuple[str, str], dict[str, Any]]:
        """Load enhancement data from DeviceTemplate DB table.

        Returns enhancement data keyed by (vendor, model) that can be merged
        into device templates. This includes CVE data, firmware variants,
        learned patterns, and other DB-specific enhancements.

        Returns:
            Dict mapping (vendor, model) to enhancement data, or empty dict if DB unavailable.
        """
        try:
            from app.core.database import get_sync_session
            from app.models.device_template import DeviceTemplate

            enhancements: dict[tuple[str, str], dict[str, Any]] = {}
            with get_sync_session() as db:
                templates = db.query(DeviceTemplate).filter(
                    DeviceTemplate.is_active == True  # noqa: E712
                ).all()

                for template in templates:
                    vendor = normalize_vendor(template.vendor or "")
                    model = template.model or ""
                    if not vendor or not model:
                        continue

                    # Extract enhancement fields (non-protocol-identity data)
                    enhancement = {
                        "firmware_variants": getattr(template, "firmware_variants", None),
                        "cve_data": getattr(template, "cve_data", None),
                        "instance_rules": getattr(template, "instance_rules", None),
                        "quality_metrics": {
                            "confidence": getattr(template, "confidence", None),
                            "sample_count": getattr(template, "sample_count", None),
                        },
                        "source": template.source,
                    }

                    key = (vendor, model)
                    enhancements[key] = enhancement

            if enhancements:
                logger.info(f"Loaded {len(enhancements)} DB enhancements for fingerprints")
            return enhancements

        except Exception as e:
            # Graceful degradation: device_templates module is the authoritative
            # source, so missing DB enhancements are not fatal. Log the full
            # traceback so the root cause can be investigated.
            logger.error(f"Could not load DB enhancements: {e}", exc_info=True)
            return {}

    def _template_to_fingerprint_dict(self, template) -> dict[str, Any] | None:
        """Convert a DeviceTemplate DB record to a fingerprint dictionary.

        Args:
            template: DeviceTemplate DB model instance

        Returns:
            Fingerprint dictionary compatible with FingerprintApplicator
        """
        try:
            fp = {
                "vendor": template.vendor,
                "vendor_family": template.vendor_family,
                "model": template.model,
                "firmware_version": template.firmware_version,
                "oui_prefixes": list(template.oui_patterns or []),
                "tcp_stack": dict(template.tcp_signature or {}),
                "is_builtin": template.source == "vendor_builtin",
            }

            # Extract response timing from the response_timings dict
            if template.response_timings:
                # Use "default" timing if available, otherwise use first available
                fp["response_timing"] = template.response_timings.get(
                    "default",
                    next(iter(template.response_timings.values()), {})
                )
            else:
                fp["response_timing"] = {}

            # Error behavior
            fp["error_behavior"] = dict(template.error_behavior or {})

            # Protocol quirks
            fp["protocol_quirks"] = dict(template.protocol_quirks or {})

            # Protocol identities (check both unified and legacy columns)
            for protocol in ["modbus", "ethernet_ip", "profinet", "s7", "snmp", "bacnet", "opc_ua", "dnp3", "iec104"]:
                identity = template.get_protocol_identity(protocol)
                fp[f"{protocol}_identity"] = dict(identity) if identity else None

            return fp

        except Exception as e:
            logger.warning(f"Could not convert template {template.id} to fingerprint: {e}")
            return None

    @property
    def index(self) -> FingerprintIndex:
        """Get the fingerprint index, building if necessary.

        Thread-safe lazy index building.

        Returns:
            FingerprintIndex with all indexed fingerprints
        """
        if not self._built:
            with self._index_lock:
                if not self._built:
                    self._build_index()
        return self._index  # type: ignore

    def _merge_enhancements(
        self,
        fingerprints: list[dict[str, Any]],
        enhancements: dict[tuple[str, str], dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge DB enhancements into device template fingerprints.

        IMPORTANT: This method NEVER overrides protocol identity fields.
        It only adds enhancement data (CVE, firmware variants, etc.) from the DB.

        Args:
            fingerprints: List of fingerprints from device_templates (source of truth)
            enhancements: Dict of (vendor, model) -> enhancement data from DB

        Returns:
            Enhanced fingerprints list
        """
        # Track which DB entries were merged (to find DB-only entries later)
        merged_keys: set[tuple[str, str]] = set()

        # Enhance existing fingerprints
        for fp in fingerprints:
            vendor = normalize_vendor(fp.get("vendor", ""))
            model = fp.get("model", "")
            key = (vendor, model)

            if key in enhancements:
                enhancement = enhancements[key]
                merged_keys.add(key)

                # Add enhancement fields (NEVER override protocol identities)
                if enhancement.get("firmware_variants"):
                    fp["firmware_variants"] = enhancement["firmware_variants"]
                if enhancement.get("cve_data"):
                    fp["cve_data"] = enhancement["cve_data"]
                if enhancement.get("instance_rules"):
                    fp["instance_rules"] = enhancement["instance_rules"]

                # Add quality metrics if available
                metrics = enhancement.get("quality_metrics", {})
                if metrics.get("confidence") is not None:
                    fp["confidence"] = metrics["confidence"]
                if metrics.get("sample_count") is not None:
                    fp["sample_count"] = metrics["sample_count"]

        return fingerprints

    def _build_index(self) -> None:
        """Build the fingerprint index from device_templates (single source of truth).

        Called lazily on first access.

        Data sources (in priority order):
        1. device_templates module (AUTHORITATIVE SOURCE for all fingerprint data)
        2. DeviceTemplate DB table (enhancement layer for CVE data and firmware variants)
        """
        import asyncio
        try:
            asyncio.get_running_loop()
            logger.warning(
                "FingerprintCache._build_index() called within async event loop. "
                "This uses sync DB access and may block the event loop. "
                "Consider calling cache.refresh() during startup."
            )
        except RuntimeError:
            pass  # Not in async context, safe to proceed

        logger.info("Building fingerprint cache index...")

        # STEP 1: Load from device_templates (authoritative source)
        from app.services.device_templates import get_all_fingerprints
        all_fps = get_all_fingerprints()
        logger.info(f"Loaded {len(all_fps)} fingerprints from device_templates (source of truth)")

        # STEP 2: Enhance with DeviceTemplate DB data (additive only, never override identities)
        db_enhancements = self._load_db_enhancements()
        if db_enhancements:
            all_fps = self._merge_enhancements(all_fps, db_enhancements)

        self._index = FingerprintIndex(all_fingerprints=all_fps)

        # Build primary index: (vendor, model) -> fingerprint
        for fp in all_fps:
            vendor = normalize_vendor(fp.get("vendor", ""))
            model = fp.get("model", "")

            if vendor and model:
                key = (vendor, model)
                self._index.by_vendor_model[key] = fp

            # Build secondary index: vendor -> [fingerprints]
            if vendor:
                if vendor not in self._index.by_vendor:
                    self._index.by_vendor[vendor] = []
                self._index.by_vendor[vendor].append(fp)

            # Build alternative model indexes from protocol identities
            self._index_protocol_identities(fp, vendor)

            # Index by vendor_family (e.g., "PanelView Plus 7", "Stratix")
            vendor_family = fp.get("vendor_family", "")
            if vendor_family:
                key = (vendor, vendor_family)
                if key not in self._index.by_alt_model:
                    self._index.by_alt_model[key] = fp

        self._built = True
        logger.info(
            f"Fingerprint cache built: "
            f"{len(self._index.by_vendor_model)} primary entries, "
            f"{len(self._index.by_vendor)} vendors, "
            f"{len(self._index.by_alt_model)} alt model entries"
        )

    def _index_protocol_identities(
        self,
        fp: dict[str, Any],
        vendor: str,
    ) -> None:
        """Index alternative model names from protocol identity fields.

        Allows lookup by device_type, product_name, module_type, etc.

        Args:
            fp: Fingerprint dictionary
            vendor: Lowercase vendor name
        """
        if not self._index:
            return

        # PROFINET: device_type (e.g., "CPU 1517-3 PN/DP")
        # Use `or {}` to handle explicit None values
        profinet = fp.get("profinet_identity") or {}
        if profinet.get("device_type"):
            key = (vendor, profinet["device_type"])
            if key not in self._index.by_alt_model:
                self._index.by_alt_model[key] = fp

        # Modbus: product_name
        modbus = fp.get("modbus_identity") or {}
        if modbus.get("product_name"):
            key = (vendor, modbus["product_name"])
            if key not in self._index.by_alt_model:
                self._index.by_alt_model[key] = fp

        # Modbus: model_name (friendly name like "PowerFlex 525")
        if modbus.get("model_name"):
            key = (vendor, modbus["model_name"])
            if key not in self._index.by_alt_model:
                self._index.by_alt_model[key] = fp

        # EtherNet/IP: product_name
        enip = fp.get("ethernet_ip_identity") or {}
        if enip.get("product_name"):
            key = (vendor, enip["product_name"])
            if key not in self._index.by_alt_model:
                self._index.by_alt_model[key] = fp

        # S7: module_type (check both locations)
        s7 = fp.get("s7_identity") or (fp.get("protocol_quirks") or {}).get("s7_identity") or {}
        if s7.get("module_type"):
            key = (vendor, s7["module_type"])
            if key not in self._index.by_alt_model:
                self._index.by_alt_model[key] = fp

        # BACnet: model_name
        bacnet = fp.get("bacnet_identity") or {}
        if bacnet.get("model_name"):
            key = (vendor, bacnet["model_name"])
            if key not in self._index.by_alt_model:
                self._index.by_alt_model[key] = fp

        # SNMP: model from sys_descr (if extractable)
        # Skip for now as sys_descr parsing is complex

    def get_by_vendor_model(
        self,
        vendor: str,
        model: str,
    ) -> dict[str, Any] | None:
        """O(1) lookup by vendor and model.

        Checks both primary index and alternative model index.

        Args:
            vendor: Vendor name (case-insensitive)
            model: Model identifier

        Returns:
            Fingerprint dictionary or None if not found
        """
        vendor_normalized = normalize_vendor(vendor)

        # Try primary index first
        key = (vendor_normalized, model)
        result = self.index.by_vendor_model.get(key)
        if result:
            return result

        # Try alternative model index
        result = self.index.by_alt_model.get(key)
        if result:
            return result

        return None

    def get_by_vendor(self, vendor: str) -> list[dict[str, Any]]:
        """Get all fingerprints for a vendor.

        Args:
            vendor: Vendor name (case-insensitive)

        Returns:
            List of fingerprint dictionaries (may be empty)
        """
        return self.index.by_vendor.get(normalize_vendor(vendor), [])

    def get_all(self) -> list[dict[str, Any]]:
        """Get all fingerprints.

        Returns:
            List of all fingerprint dictionaries
        """
        return self.index.all_fingerprints

    def get_vendors(self) -> list[str]:
        """Get list of all indexed vendors.

        Returns:
            List of vendor names
        """
        return list(self.index.by_vendor.keys())

    def get_count(self) -> int:
        """Get total number of indexed fingerprints.

        Returns:
            Number of fingerprints
        """
        return len(self.index.all_fingerprints)

    def invalidate(self) -> None:
        """Clear the cache and force rebuild on next access.

        Call this after fingerprint data changes.
        """
        with self._index_lock:
            self._index = None
            self._built = False
            logger.info("Fingerprint cache invalidated")

    def refresh(self) -> None:
        """Force rebuild of the cache.

        Useful after fingerprint data updates.
        """
        with self._index_lock:
            self._built = False
            self._build_index()


# Convenience functions for module-level access


def get_fingerprint_cache() -> FingerprintCache:
    """Get the fingerprint cache singleton.

    Returns:
        FingerprintCache instance
    """
    return FingerprintCache.get_instance()


def get_fingerprint_by_vendor_model(
    vendor: str,
    model: str,
) -> dict[str, Any] | None:
    """O(1) fingerprint lookup by vendor and model.

    This is the recommended way to look up fingerprints.

    Args:
        vendor: Vendor name (case-insensitive)
        model: Model identifier

    Returns:
        Fingerprint dictionary or None if not found
    """
    return get_fingerprint_cache().get_by_vendor_model(vendor, model)


def get_fingerprints_by_vendor(vendor: str) -> list[dict[str, Any]]:
    """Get all fingerprints for a vendor.

    Args:
        vendor: Vendor name (case-insensitive)

    Returns:
        List of fingerprint dictionaries
    """
    return get_fingerprint_cache().get_by_vendor(vendor)


def invalidate_fingerprint_cache() -> None:
    """Invalidate the fingerprint cache.

    Call this after fingerprint data changes.
    """
    get_fingerprint_cache().invalidate()
