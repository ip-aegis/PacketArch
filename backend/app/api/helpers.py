# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Reusable API route helpers for common database patterns."""

from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError

T = TypeVar("T")


async def get_or_404(
    db: AsyncSession,
    model: type[T],
    resource_id: UUID,
    resource_name: str | None = None,
) -> T:
    """Fetch a resource by primary key or raise NotFoundError.

    Args:
        db: Database session
        model: SQLAlchemy model class
        resource_id: Primary key UUID
        resource_name: Human-readable name for error message (defaults to model name)

    Returns:
        The found model instance

    Raises:
        NotFoundError: If resource does not exist
    """
    result = await db.execute(select(model).where(model.id == resource_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError(
            resource_name or model.__name__,
            str(resource_id),
        )
    return item


async def get_or_404_where(
    db: AsyncSession,
    model: type[T],
    *conditions,
    resource_name: str,
    identifier: str | None = None,
) -> T:
    """Fetch a resource with arbitrary WHERE conditions or raise NotFoundError.

    Useful for ownership-gated lookups like:
        scenario = await get_or_404_where(
            db, Scenario,
            Scenario.id == scenario_id,
            Scenario.user_id == user_id,
            resource_name="Scenario",
            identifier=str(scenario_id),
        )

    Args:
        db: Database session
        model: SQLAlchemy model class
        *conditions: SQLAlchemy WHERE clause expressions
        resource_name: Human-readable name for error message
        identifier: Optional identifier string for error message

    Returns:
        The found model instance

    Raises:
        NotFoundError: If no matching resource exists
    """
    result = await db.execute(select(model).where(*conditions))
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError(resource_name, identifier)
    return item


async def paginate(
    db: AsyncSession,
    query: Any,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Any], int]:
    """Execute a query with pagination and return (items, total_count).

    Args:
        db: Database session
        query: SQLAlchemy select query (with filters and ordering already applied)
        page: 1-based page number
        page_size: Number of items per page

    Returns:
        Tuple of (items list, total count)
    """
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    paginated = query.offset(offset).limit(page_size)
    result = await db.execute(paginated)
    items = list(result.scalars().all())

    return items, total
