# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Demo-friendly device.name overlay on top of the site-identity rail.

After `apply_site_naming_pipeline` has run, every device has a
structured site-coded name (e.g. ``PDX-BKY-01-MIX-PLC-01``) and its
SNMP sys_name / EtherNet-IP product_name / Modbus product_name fields
are set to that canonical token. Cyber Vision uses the canonical
identifiers — that rail must not move.

This module runs ``AIDeviceNamer`` over the post-rail devices and
overwrites only ``device.name`` with longer human-readable labels
(``Front_Mixing_Line_PLC``). Studio renders ``device.name`` so the
canvas shows demo-friendly labels; the fingerprint layer stays clean.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


async def apply_descriptive_overlay(
    *,
    db: AsyncSession,
    definition: dict[str, Any],
    vertical: str,
    scenario_name: str,
    scenario_description: str,
    process_context: str | None,
    user_id: UUID | None = None,
    scenario_id: UUID | str | None = None,
    feature_tag: str = "device_naming_descriptive_overlay",
) -> int:
    """Overlay descriptive labels on each device.name. Returns the
    number of devices renamed.

    Failures are logged but non-fatal — the site-rail names remain in
    place, so the worst case is the demo look-and-feel is missing.
    """
    from app.ai_services.device_namer import AIDeviceNamer, DeviceNamingContext
    from app.ai_services.usage_recorder import AIUsageContext
    from app.mcp_server.ai_providers import AIProviderFactory, AITask

    devices = definition.get("devices") or {}
    if not devices:
        return 0

    try:
        ai_provider = await AIProviderFactory.create(db, task=AITask.DEVICE_NAMING)
    except ValueError as e:
        logger.warning(
            "Descriptive overlay skipped — AI provider not configured: %s", e
        )
        return 0

    context = DeviceNamingContext(
        vertical=vertical or "manufacturing",
        template_name=scenario_name,
        template_description=scenario_description or "",
        zones=definition.get("zones") or {},
        process_context=process_context,
    )

    try:
        enhanced = await AIDeviceNamer().enhance_device_names(
            devices=list(devices.values()),
            context=context,
            ai_provider=ai_provider,
            tracking=AIUsageContext(
                feature=feature_tag,
                user_id=user_id,
                scenario_id=scenario_id,
            ),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "Descriptive overlay failed: %s — keeping site-rail names", e
        )
        return 0

    definition["devices"] = {d["id"]: d for d in enhanced}
    return len(enhanced)
