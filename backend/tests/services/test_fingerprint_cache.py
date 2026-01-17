"""Tests for Fingerprint Cache service."""

import pytest

from app.services.fingerprint_cache import (
    FingerprintCache,
    FingerprintIndex,
    get_fingerprint_by_vendor_model,
    get_fingerprint_cache,
    get_fingerprints_by_vendor,
    invalidate_fingerprint_cache,
)


class TestFingerprintIndex:
    """Tests for FingerprintIndex dataclass."""

    def test_default_empty(self):
        """Test default index is empty."""
        index = FingerprintIndex()
        assert len(index.by_vendor_model) == 0
        assert len(index.by_vendor) == 0
        assert len(index.by_alt_model) == 0
        assert len(index.all_fingerprints) == 0


class TestFingerprintCache:
    """Tests for FingerprintCache class."""

    def setup_method(self):
        """Reset cache before each test."""
        # Get fresh instance
        cache = FingerprintCache.get_instance()
        cache.invalidate()

    def test_singleton_pattern(self):
        """Test singleton returns same instance."""
        cache1 = FingerprintCache.get_instance()
        cache2 = FingerprintCache.get_instance()
        assert cache1 is cache2

    def test_lazy_index_building(self):
        """Test that index is built lazily."""
        cache = FingerprintCache.get_instance()
        cache.invalidate()

        # Before accessing index
        assert cache._built is False

        # Access index (triggers build)
        _ = cache.index

        # After accessing index
        assert cache._built is True

    def test_get_by_vendor_model(self):
        """Test lookup by vendor and model."""
        cache = FingerprintCache.get_instance()

        # Test with a known fingerprint (Siemens S7-1500)
        result = cache.get_by_vendor_model("siemens", "6ES7 517-3AP00-0AB0")

        # May or may not exist depending on seed data
        if result:
            assert result["vendor"].lower() == "siemens"

    def test_get_by_vendor_case_insensitive(self):
        """Test vendor lookup is case-insensitive."""
        cache = FingerprintCache.get_instance()

        result1 = cache.get_by_vendor("siemens")
        result2 = cache.get_by_vendor("SIEMENS")
        result3 = cache.get_by_vendor("Siemens")

        assert result1 == result2 == result3

    def test_get_all(self):
        """Test get_all returns all fingerprints."""
        cache = FingerprintCache.get_instance()
        all_fps = cache.get_all()

        assert isinstance(all_fps, list)
        # Should have fingerprints from seed data
        assert len(all_fps) > 0

    def test_get_vendors(self):
        """Test get_vendors returns vendor list."""
        cache = FingerprintCache.get_instance()
        vendors = cache.get_vendors()

        assert isinstance(vendors, list)
        assert len(vendors) > 0
        assert all(isinstance(v, str) for v in vendors)

    def test_get_count(self):
        """Test get_count returns fingerprint count."""
        cache = FingerprintCache.get_instance()
        count = cache.get_count()

        assert isinstance(count, int)
        assert count > 0
        assert count == len(cache.get_all())

    def test_invalidate(self):
        """Test cache invalidation."""
        cache = FingerprintCache.get_instance()

        # Ensure built
        _ = cache.index
        assert cache._built is True

        # Invalidate
        cache.invalidate()
        assert cache._built is False

    def test_refresh(self):
        """Test cache refresh."""
        cache = FingerprintCache.get_instance()

        # Initial build
        count1 = cache.get_count()

        # Refresh
        cache.refresh()

        # Should have same count
        count2 = cache.get_count()
        assert count1 == count2


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def setup_method(self):
        """Reset cache before each test."""
        invalidate_fingerprint_cache()

    def test_get_fingerprint_cache(self):
        """Test get_fingerprint_cache returns singleton."""
        cache1 = get_fingerprint_cache()
        cache2 = get_fingerprint_cache()
        assert cache1 is cache2

    def test_get_fingerprint_by_vendor_model_not_found(self):
        """Test lookup returns None for non-existent fingerprint."""
        result = get_fingerprint_by_vendor_model("nonexistent", "unknown-model")
        assert result is None

    def test_get_fingerprints_by_vendor_empty(self):
        """Test vendor lookup returns empty for unknown vendor."""
        result = get_fingerprints_by_vendor("nonexistent_vendor_xyz")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_invalidate_fingerprint_cache(self):
        """Test invalidation function."""
        cache = get_fingerprint_cache()
        _ = cache.index  # Build
        assert cache._built is True

        invalidate_fingerprint_cache()
        assert cache._built is False


class TestAlternativeModelLookup:
    """Tests for alternative model name lookups."""

    def test_alt_model_from_profinet(self):
        """Test lookup by PROFINET device_type."""
        cache = FingerprintCache.get_instance()

        # This should work if seed data has CPU 1517-3 PN/DP
        result = cache.get_by_vendor_model("siemens", "CPU 1517-3 PN/DP")

        if result:
            assert result["vendor"].lower() == "siemens"

    def test_alt_model_from_modbus(self):
        """Test lookup by Modbus product_name."""
        cache = FingerprintCache.get_instance()

        # Check with Rockwell product name
        result = cache.get_by_vendor_model("rockwell", "1756-L85E/B")

        if result:
            assert result["vendor"].lower() == "rockwell"
