# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Device Template Library with Firmware Variants.

This package is the single source of truth for all OT/ICS device templates.
All 301+ templates are organized by vendor into submodules under vendors/.

Usage:
    from app.services.device_templates import (
        get_all_templates, get_template_by_id, DEVICE_TEMPLATES,
        DeviceTemplate, FirmwareVariant,
    )
"""

# Types (dataclasses)
from app.services.device_templates._types import (
    DeviceInstance,
    DeviceTemplate,
    FirmwareVariant,
    InstanceGenerationRules,
)

# Helpers
from app.services.device_templates._helpers import (
    generate_serial_number,
    generate_station_name,
    merge_identity,
)

# Registry (triggers _register_all() on import)
from app.services.device_templates._registry import (
    DEVICE_TEMPLATES,
    _register_template,
)

# Public API
from app.services.device_templates._api import (
    generate_device_instance,
    get_all_templates,
    get_template_by_id,
    get_template_count,
    get_templates_by_device_type,
    get_templates_by_vendor,
    get_templates_with_cves,
    get_total_cves,
    get_total_firmware_variants,
)

# Fingerprint compatibility layer
from app.services.device_templates._fingerprints import (
    get_all_fingerprints,
    get_fingerprint_by_vendor_model,
    get_fingerprint_from_db_async,
    get_fingerprint_from_db_sync,
    get_fingerprint_from_template,
    get_fingerprint_with_fallback,
    get_fingerprints_by_vendor,
    get_fingerprints_by_vendor_and_type,
    get_template_by_vendor_model,
    template_db_to_fingerprint_dict,
)
from app.services.device_templates.firmware_distribution import (
    build_distribution,
    select_firmware_variant,
)

__all__ = [
    # Types
    "DeviceTemplate",
    "DeviceInstance",
    "FirmwareVariant",
    "InstanceGenerationRules",
    # Helpers
    "generate_serial_number",
    "generate_station_name",
    "merge_identity",
    # Registry
    "DEVICE_TEMPLATES",
    "_register_template",
    # API
    "get_all_templates",
    "get_template_by_id",
    "get_template_by_vendor_model",
    "get_templates_by_vendor",
    "get_templates_by_device_type",
    "get_templates_with_cves",
    "get_template_count",
    "get_total_firmware_variants",
    "get_total_cves",
    "generate_device_instance",
    # Firmware distribution ("template-defined mix")
    "select_firmware_variant",
    "build_distribution",
    # Fingerprint compat
    "get_fingerprint_from_template",
    "get_fingerprint_by_vendor_model",
    "get_fingerprints_by_vendor",
    "get_fingerprints_by_vendor_and_type",
    "get_all_fingerprints",
    "template_db_to_fingerprint_dict",
    "get_fingerprint_from_db_sync",
    "get_fingerprint_from_db_async",
    "get_fingerprint_with_fallback",
]
