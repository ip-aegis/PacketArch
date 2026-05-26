# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Persist a row to ``ai_call_audit`` for every AI provider call.

Providers call :func:`record_call` from their ``chat()`` methods. The
recorder MUST NEVER raise — a logging failure here would break the
real request flow. All exceptions are swallowed and logged.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from app.ai_services.pricing import compute_cost_usd
from app.core.database import async_session_maker
from app.models.ai_call_audit import AICallAudit

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIUsageContext:
    """Attribution metadata for a single AI call.

    Built once at the route / service boundary and passed into
    ``provider.chat(tracking=...)``. Optional fields are dropped
    cleanly when unknown — the call still gets audited, just with
    less attribution.
    """

    feature: str
    user_id: uuid.UUID | None = None
    scenario_id: uuid.UUID | None = None


async def record_call(
    *,
    provider: str,
    model: str,
    usage: dict[str, Any] | None,
    latency_ms: int | None,
    tracking: AIUsageContext | None,
    error: str | None = None,
) -> None:
    """Insert one ``ai_call_audit`` row. Never raises.

    Args:
        provider: ``anthropic`` / ``openai`` / ``circuit``.
        model: Exact model string used in the API call.
        usage: Standard usage dict from the provider's ``_format_response``.
            Expected keys: ``input_tokens``, ``output_tokens``, and
            optionally ``cache_creation_input_tokens``,
            ``cache_read_input_tokens``. Missing keys default to 0.
        latency_ms: Wall-clock duration of the call in milliseconds.
        tracking: Caller-supplied attribution. ``None`` is allowed so
            background callers without a user can still be audited.
        error: Error message if the call failed. Token counts will
            typically be 0 in that case.
    """
    usage = usage or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    cache_write_tokens = int(usage.get("cache_creation_input_tokens") or 0)
    cache_read_tokens = int(usage.get("cache_read_input_tokens") or 0)

    cost = compute_cost_usd(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
    )

    feature = (tracking.feature if tracking else None) or "unknown"
    user_id = tracking.user_id if tracking else None
    scenario_id = tracking.scenario_id if tracking else None

    row = AICallAudit(
        user_id=user_id,
        scenario_id=scenario_id,
        feature=feature[:64],
        provider=provider[:32],
        model=model[:128],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
        total_cost_usd=cost,
        latency_ms=latency_ms,
        error=(error[:4096] if error else None),
    )

    try:
        async with async_session_maker() as session:
            session.add(row)
            await session.commit()
    except Exception as exc:  # noqa: BLE001 — audit must never break callers
        logger.warning(
            "Failed to persist ai_call_audit row for %s/%s: %s",
            provider, model, exc,
        )
