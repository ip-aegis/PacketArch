"""Fingerprint Cache Service with Pre-Indexing.

This module provides O(1) fingerprint lookups instead of O(n) scans.
Fingerprints are indexed at startup/first use for efficient access.

Index types:
- Primary: (vendor, model) -> fingerprint
- Secondary: vendor -> [fingerprints]
- Alt model: protocol identity fields -> fingerprint

This service is thread-safe and uses a singleton pattern.
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Vendor name normalization mapping
VENDOR_NAME_ALIASES: dict[str, str] = {
    # Full names -> short names (for fingerprint indexing)
    "johnson controls": "johnson_controls",
    "schneider electric": "schneider",
    "delta controls": "delta_controls",
    "distech controls": "distech",
    "automated logic": "automated_logic",
    "endress+hauser": "endress_hauser",
    "endress hauser": "endress_hauser",
    "ge multilin": "ge_multilin",
    # Handle underscores in lookups
    "johnson_controls": "johnson_controls",
    "schneider_electric": "schneider",
    "delta_controls": "delta_controls",
    "distech_controls": "distech",
    "automated_logic": "automated_logic",
    "endress_hauser": "endress_hauser",
    "ge_multilin": "ge_multilin",
}


def normalize_vendor(vendor: str) -> str:
    """Normalize vendor name for consistent lookups.

    Handles variations like:
    - "Johnson Controls" -> "johnson_controls"
    - "Schneider Electric" -> "schneider"
    - "johnson_controls" -> "johnson_controls"

    Args:
        vendor: Raw vendor name

    Returns:
        Normalized lowercase vendor name
    """
    lower = vendor.lower()
    return VENDOR_NAME_ALIASES.get(lower, lower)


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

    def _build_index(self) -> None:
        """Build the fingerprint index from all vendor fingerprints.

        Called lazily on first access.
        """
        from app.services.vendor_fingerprints import get_all_vendor_fingerprints

        logger.info("Building fingerprint cache index...")

        all_fps = get_all_vendor_fingerprints()
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
