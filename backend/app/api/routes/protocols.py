"""Protocol template routes for managing protocol configurations."""

import math
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.models.protocol_template import ProtocolTemplate
from app.schemas.protocol_template import (
    ProtocolTemplateCreate,
    ProtocolTemplateListResponse,
    ProtocolTemplateResponse,
    ProtocolTemplateUpdate,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/protocols", tags=["Protocol Templates"])


@router.get("", response_model=ProtocolTemplateListResponse)
async def list_protocol_templates(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    protocol: str | None = Query(default=None),
    vertical: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> ProtocolTemplateListResponse:
    """List protocol templates with filtering and pagination."""
    query = select(ProtocolTemplate)

    # Apply filters
    if protocol:
        query = query.where(ProtocolTemplate.protocol == protocol)

    if vertical:
        query = query.where(ProtocolTemplate.vertical == vertical)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            ProtocolTemplate.name.ilike(search_filter)
            | ProtocolTemplate.description.ilike(search_filter)
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(
        ProtocolTemplate.protocol, ProtocolTemplate.name
    )

    result = await db.execute(query)
    templates = result.scalars().all()

    return ProtocolTemplateListResponse(
        items=[ProtocolTemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/types")
async def get_protocol_types(
    db: DBSession,
    current_user: CurrentUser,
) -> list[str]:
    """Get list of all protocol types."""
    query = select(ProtocolTemplate.protocol).distinct()
    result = await db.execute(query)
    return [row[0] for row in result.all()]


@router.get("/{template_id}", response_model=ProtocolTemplateResponse)
async def get_protocol_template(
    template_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ProtocolTemplateResponse:
    """Get a protocol template by ID."""
    result = await db.execute(
        select(ProtocolTemplate).where(ProtocolTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Protocol template not found",
        )

    return ProtocolTemplateResponse.model_validate(template)


@router.post("", response_model=ProtocolTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_protocol_template(
    template_data: ProtocolTemplateCreate,
    db: DBSession,
    admin_user: AdminUser,  # Only admins can create protocol templates
) -> ProtocolTemplateResponse:
    """Create a new protocol template (admin only)."""
    template = ProtocolTemplate(
        protocol=template_data.protocol,
        name=template_data.name,
        description=template_data.description,
        vertical=template_data.vertical,
        config_schema=template_data.config_schema,
        default_config=template_data.default_config,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return ProtocolTemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=ProtocolTemplateResponse)
async def update_protocol_template(
    template_id: UUID,
    template_data: ProtocolTemplateUpdate,
    db: DBSession,
    admin_user: AdminUser,  # Only admins can update protocol templates
) -> ProtocolTemplateResponse:
    """Update a protocol template (admin only)."""
    result = await db.execute(
        select(ProtocolTemplate).where(ProtocolTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Protocol template not found",
        )

    # Update fields
    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    return ProtocolTemplateResponse.model_validate(template)


@router.delete("/{template_id}", response_model=MessageResponse)
async def delete_protocol_template(
    template_id: UUID,
    db: DBSession,
    admin_user: AdminUser,  # Only admins can delete protocol templates
) -> MessageResponse:
    """Delete a protocol template (admin only)."""
    result = await db.execute(
        select(ProtocolTemplate).where(ProtocolTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Protocol template not found",
        )

    await db.delete(template)
    await db.commit()

    return MessageResponse(message="Protocol template deleted successfully")
