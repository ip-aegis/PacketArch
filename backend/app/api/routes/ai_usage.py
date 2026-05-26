# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Admin routes for AI token / cost reporting.

Reads from the ``ai_call_audit`` table populated by the providers.
All endpoints require admin. Available without ``AI_ENABLED`` so
operators can still review historical spend after disabling AI.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select

from app.api.deps import AdminUser, DBSession
from app.models.ai_call_audit import AICallAudit
from app.models.user import User

router = APIRouter(prefix="/admin/ai-usage", tags=["AI Usage"])


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------

RangeLiteral = Literal["24h", "7d", "30d", "all"]


class UsageTotals(BaseModel):
    """Aggregate token / cost counters for a window."""

    call_count: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    total_cost_usd: float
    unpriced_call_count: int  # rows with total_cost_usd IS NULL
    error_count: int


class GroupedTotals(BaseModel):
    """Totals grouped by an arbitrary string key (model / feature / etc)."""

    key: str
    call_count: int
    input_tokens: int
    output_tokens: int
    total_cost_usd: float


class UsageSummaryResponse(BaseModel):
    """Top-level summary returned by /summary."""

    range: RangeLiteral
    since: datetime | None
    overall: UsageTotals
    by_provider: list[GroupedTotals]
    by_model: list[GroupedTotals]
    by_feature: list[GroupedTotals]
    by_user: list[GroupedTotals]  # ``key`` is "<email or 'unknown'>"


class UsageEvent(BaseModel):
    """One row from ai_call_audit, with the user email resolved."""

    id: uuid.UUID
    created_at: datetime
    user_email: str | None
    user_id: uuid.UUID | None
    scenario_id: uuid.UUID | None
    feature: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    total_cost_usd: float | None
    latency_ms: int | None
    error: str | None


class UsageEventsResponse(BaseModel):
    items: list[UsageEvent]
    total: int


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _range_to_since(range_: RangeLiteral) -> datetime | None:
    """Return the UTC ``created_at`` cutoff for the requested window."""
    if range_ == "all":
        return None
    now = datetime.now(timezone.utc)
    if range_ == "24h":
        return now - timedelta(hours=24)
    if range_ == "7d":
        return now - timedelta(days=7)
    return now - timedelta(days=30)


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------


@router.get("/summary", response_model=UsageSummaryResponse)
async def get_ai_usage_summary(
    _admin: AdminUser,
    db: DBSession,
    range_: RangeLiteral = Query("7d", alias="range"),
) -> UsageSummaryResponse:
    """Aggregated AI spend / token usage over a rolling window.

    Group-by results are capped at 50 keys (more than enough for a
    real install — there are < 10 features and < 10 models in play).
    """
    since = _range_to_since(range_)

    base_where = []
    if since is not None:
        base_where.append(AICallAudit.created_at >= since)

    # Overall totals
    overall_q = select(
        func.count(AICallAudit.id).label("call_count"),
        func.coalesce(func.sum(AICallAudit.input_tokens), 0).label("in_tok"),
        func.coalesce(func.sum(AICallAudit.output_tokens), 0).label("out_tok"),
        func.coalesce(func.sum(AICallAudit.cache_read_tokens), 0).label("cache_r"),
        func.coalesce(func.sum(AICallAudit.cache_write_tokens), 0).label("cache_w"),
        func.coalesce(func.sum(AICallAudit.total_cost_usd), 0.0).label("cost"),
        func.count(AICallAudit.id).filter(
            AICallAudit.total_cost_usd.is_(None)
        ).label("unpriced"),
        func.count(AICallAudit.id).filter(
            AICallAudit.error.is_not(None)
        ).label("errors"),
    )
    if base_where:
        overall_q = overall_q.where(*base_where)
    overall_row = (await db.execute(overall_q)).one()

    overall = UsageTotals(
        call_count=int(overall_row.call_count or 0),
        input_tokens=int(overall_row.in_tok or 0),
        output_tokens=int(overall_row.out_tok or 0),
        cache_read_tokens=int(overall_row.cache_r or 0),
        cache_write_tokens=int(overall_row.cache_w or 0),
        total_cost_usd=float(overall_row.cost or 0.0),
        unpriced_call_count=int(overall_row.unpriced or 0),
        error_count=int(overall_row.errors or 0),
    )

    async def _grouped(column) -> list[GroupedTotals]:
        q = (
            select(
                column.label("key"),
                func.count(AICallAudit.id).label("c"),
                func.coalesce(func.sum(AICallAudit.input_tokens), 0).label("i"),
                func.coalesce(func.sum(AICallAudit.output_tokens), 0).label("o"),
                func.coalesce(func.sum(AICallAudit.total_cost_usd), 0.0).label("cost"),
            )
            .group_by(column)
            .order_by(desc("cost"))
            .limit(50)
        )
        if base_where:
            q = q.where(*base_where)
        rows = (await db.execute(q)).all()
        return [
            GroupedTotals(
                key=str(r.key) if r.key is not None else "unknown",
                call_count=int(r.c or 0),
                input_tokens=int(r.i or 0),
                output_tokens=int(r.o or 0),
                total_cost_usd=float(r.cost or 0.0),
            )
            for r in rows
        ]

    by_provider = await _grouped(AICallAudit.provider)
    by_model = await _grouped(AICallAudit.model)
    by_feature = await _grouped(AICallAudit.feature)

    # by_user: join against users to swap UUID for email so the UI is readable.
    by_user_q = (
        select(
            func.coalesce(User.email, "unknown").label("key"),
            func.count(AICallAudit.id).label("c"),
            func.coalesce(func.sum(AICallAudit.input_tokens), 0).label("i"),
            func.coalesce(func.sum(AICallAudit.output_tokens), 0).label("o"),
            func.coalesce(func.sum(AICallAudit.total_cost_usd), 0.0).label("cost"),
        )
        .select_from(AICallAudit)
        .outerjoin(User, User.id == AICallAudit.user_id)
        .group_by(User.email)
        .order_by(desc("cost"))
        .limit(50)
    )
    if base_where:
        by_user_q = by_user_q.where(*base_where)
    user_rows = (await db.execute(by_user_q)).all()
    by_user = [
        GroupedTotals(
            key=str(r.key) if r.key is not None else "unknown",
            call_count=int(r.c or 0),
            input_tokens=int(r.i or 0),
            output_tokens=int(r.o or 0),
            total_cost_usd=float(r.cost or 0.0),
        )
        for r in user_rows
    ]

    return UsageSummaryResponse(
        range=range_,
        since=since,
        overall=overall,
        by_provider=by_provider,
        by_model=by_model,
        by_feature=by_feature,
        by_user=by_user,
    )


@router.get("/events", response_model=UsageEventsResponse)
async def get_ai_usage_events(
    _admin: AdminUser,
    db: DBSession,
    range_: RangeLiteral = Query("7d", alias="range"),
    feature: str | None = Query(None, description="Filter by feature key"),
    provider: str | None = Query(None, description="Filter by provider"),
    user_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> UsageEventsResponse:
    """Paginated raw audit rows, newest first.

    Default page size is 50 to keep the UI responsive; max 500 for
    one-off CSV export hacks via the network panel.
    """
    since = _range_to_since(range_)

    base_where = []
    if since is not None:
        base_where.append(AICallAudit.created_at >= since)
    if feature:
        base_where.append(AICallAudit.feature == feature)
    if provider:
        base_where.append(AICallAudit.provider == provider)
    if user_id is not None:
        base_where.append(AICallAudit.user_id == user_id)

    count_q = select(func.count(AICallAudit.id))
    if base_where:
        count_q = count_q.where(*base_where)
    total = int((await db.execute(count_q)).scalar_one() or 0)

    rows_q = (
        select(AICallAudit, User.email)
        .outerjoin(User, User.id == AICallAudit.user_id)
        .order_by(desc(AICallAudit.created_at))
        .limit(limit)
        .offset(offset)
    )
    if base_where:
        rows_q = rows_q.where(*base_where)

    items: list[UsageEvent] = []
    for row in (await db.execute(rows_q)).all():
        audit: AICallAudit = row[0]
        email: str | None = row[1]
        items.append(
            UsageEvent(
                id=audit.id,
                created_at=audit.created_at,
                user_email=email,
                user_id=audit.user_id,
                scenario_id=audit.scenario_id,
                feature=audit.feature,
                provider=audit.provider,
                model=audit.model,
                input_tokens=audit.input_tokens,
                output_tokens=audit.output_tokens,
                cache_read_tokens=audit.cache_read_tokens,
                cache_write_tokens=audit.cache_write_tokens,
                total_cost_usd=audit.total_cost_usd,
                latency_ms=audit.latency_ms,
                error=audit.error,
            )
        )

    return UsageEventsResponse(items=items, total=total)
