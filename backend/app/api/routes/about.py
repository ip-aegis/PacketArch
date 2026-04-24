# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Product metadata endpoint: version, ownership, license.

Unauthenticated — the About modal and login footer both need these values,
and nothing here is sensitive. Kept separate from /health so About-panel
changes don't churn health-check surfaces.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.features import Features, get_features
from app.core.version import (
    ACK_BODY,
    ACK_DOCUMENT,
    ACK_TITLE,
    ACK_VERSION,
    LICENSE_ID,
    LICENSE_NAME,
    LICENSE_URL,
    OWNER_COPYRIGHT,
    OWNER_EMAIL,
    OWNER_NAME,
    get_build_commit,
    get_build_date,
)

router = APIRouter(prefix="/about", tags=["About"])


class AcknowledgmentInfo(BaseModel):
    document: str
    version: str
    title: str
    body: str


class LicenseInfo(BaseModel):
    id: str
    name: str
    url: str


class OwnerInfo(BaseModel):
    name: str
    email: str
    copyright: str


class AboutResponse(BaseModel):
    name: str
    version: str
    build_commit: str
    build_date: str
    owner: OwnerInfo
    license: LicenseInfo
    acknowledgment: AcknowledgmentInfo
    features: Features


@router.get("", response_model=AboutResponse)
async def get_about() -> AboutResponse:
    """Product name, version, build info, ownership, and license metadata."""
    return AboutResponse(
        name=settings.app_name,
        version=settings.app_version,
        build_commit=get_build_commit(),
        build_date=get_build_date(),
        owner=OwnerInfo(
            name=OWNER_NAME,
            email=OWNER_EMAIL,
            copyright=OWNER_COPYRIGHT,
        ),
        license=LicenseInfo(
            id=LICENSE_ID,
            name=LICENSE_NAME,
            url=LICENSE_URL,
        ),
        acknowledgment=AcknowledgmentInfo(
            document=ACK_DOCUMENT,
            version=ACK_VERSION,
            title=ACK_TITLE,
            body=ACK_BODY,
        ),
        features=get_features(),
    )
