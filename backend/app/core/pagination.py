# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Shared pagination utility for async SQLAlchemy queries."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select


async def paginate(
    db: AsyncSession,
    query: Select,
    page: int,
    page_size: int,
) -> tuple[list, int]:
    """Execute a paginated query, returning (items, total_count).

    Uses an efficient COUNT(*) subquery instead of loading all records.

    Args:
        db: Async database session
        query: SQLAlchemy Select query (before offset/limit)
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Tuple of (items list, total count)
    """
    # Get total count efficiently
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    data_query = query.offset(offset).limit(page_size)
    result = await db.execute(data_query)
    items = result.scalars().all()

    return items, total
