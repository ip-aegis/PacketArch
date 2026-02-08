"""Device profile routes for managing OT device templates."""

import math
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession
from app.api.helpers import get_or_404, paginate
from app.core.exceptions import NotFoundError
from app.models.device_profile import DeviceProfile
from app.schemas.device_profile import (
    DeviceProfileCreate,
    DeviceProfileListResponse,
    DeviceProfileResponse,
    DeviceProfileUpdate,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/devices", tags=["Device Profiles"])


@router.get("", response_model=DeviceProfileListResponse)
async def list_device_profiles(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    device_type: str | None = Query(default=None),
    protocol: str | None = Query(default=None),
    vertical: str | None = Query(default=None),
    search: str | None = Query(default=None),
    builtin_only: bool = Query(default=False),
) -> DeviceProfileListResponse:
    """List device profiles with filtering and pagination."""
    query = select(DeviceProfile)

    # Apply filters
    if device_type:
        query = query.where(DeviceProfile.device_type == device_type)

    if builtin_only:
        query = query.where(DeviceProfile.is_builtin == True)

    if protocol:
        query = query.where(DeviceProfile.supported_protocols.contains([protocol]))

    if vertical:
        query = query.where(DeviceProfile.vertical_hints.contains([vertical]))

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            DeviceProfile.name.ilike(search_filter)
            | DeviceProfile.description.ilike(search_filter)
        )

    query = query.order_by(DeviceProfile.name)
    profiles, total = await paginate(db, query, page, page_size)

    return DeviceProfileListResponse(
        items=[DeviceProfileResponse.model_validate(p) for p in profiles],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/types")
async def get_device_types(
    db: DBSession,
    current_user: CurrentUser,
) -> list[str]:
    """Get list of all device types."""
    query = select(DeviceProfile.device_type).distinct()
    result = await db.execute(query)
    return [row[0] for row in result.all()]


@router.get("/{device_id}", response_model=DeviceProfileResponse)
async def get_device_profile(
    device_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> DeviceProfileResponse:
    """Get a device profile by ID."""
    profile = await get_or_404(db, DeviceProfile, device_id, "Device profile")
    return DeviceProfileResponse.model_validate(profile)


@router.post("", response_model=DeviceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_device_profile(
    profile_data: DeviceProfileCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> DeviceProfileResponse:
    """Create a new device profile."""
    profile = DeviceProfile(
        name=profile_data.name,
        device_type=profile_data.device_type,
        role=profile_data.role,
        description=profile_data.description,
        supported_protocols=profile_data.supported_protocols,
        timing_model=profile_data.timing_model,
        payload_templates=profile_data.payload_templates,
        behavior_model=profile_data.behavior_model,
        vendor_fingerprint=profile_data.vendor_fingerprint,
        vertical_hints=profile_data.vertical_hints,
        is_builtin=False,  # User-created profiles are not built-in
    )

    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return DeviceProfileResponse.model_validate(profile)


@router.put("/{device_id}", response_model=DeviceProfileResponse)
async def update_device_profile(
    device_id: UUID,
    profile_data: DeviceProfileUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> DeviceProfileResponse:
    """Update a device profile."""
    profile = await get_or_404(db, DeviceProfile, device_id, "Device profile")

    # Don't allow editing built-in profiles (unless admin)
    if profile.is_builtin and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify built-in device profiles",
        )

    # Update fields
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return DeviceProfileResponse.model_validate(profile)


@router.delete("/{device_id}", response_model=MessageResponse)
async def delete_device_profile(
    device_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> MessageResponse:
    """Delete a device profile."""
    profile = await get_or_404(db, DeviceProfile, device_id, "Device profile")

    # Don't allow deleting built-in profiles
    if profile.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete built-in device profiles",
        )

    await db.delete(profile)
    await db.commit()

    return MessageResponse(message="Device profile deleted successfully")


@router.post("/{device_id}/duplicate", response_model=DeviceProfileResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_device_profile(
    device_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    new_name: str = Query(..., min_length=1, max_length=255),
) -> DeviceProfileResponse:
    """Duplicate a device profile with a new name."""
    profile = await get_or_404(db, DeviceProfile, device_id, "Device profile")

    # Create a new profile with the same data
    new_profile = DeviceProfile(
        name=new_name,
        device_type=profile.device_type,
        role=profile.role,
        description=profile.description,
        supported_protocols=profile.supported_protocols,
        timing_model=profile.timing_model,
        payload_templates=profile.payload_templates,
        behavior_model=profile.behavior_model,
        vendor_fingerprint=profile.vendor_fingerprint,
        vertical_hints=profile.vertical_hints,
        is_builtin=False,  # Duplicated profiles are not built-in
    )

    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)

    return DeviceProfileResponse.model_validate(new_profile)
