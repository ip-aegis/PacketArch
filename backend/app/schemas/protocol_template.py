"""Protocol template schemas for API validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProtocolTemplateBase(BaseModel):
    """Base schema for protocol template."""

    protocol: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    vertical: str | None = Field(default=None, max_length=50)
    config_schema: dict[str, Any] | None = None  # JSON Schema for validation
    default_config: dict[str, Any] | None = None


class ProtocolTemplateCreate(ProtocolTemplateBase):
    """Schema for creating a protocol template."""

    pass


class ProtocolTemplateUpdate(BaseModel):
    """Schema for updating a protocol template."""

    protocol: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    vertical: str | None = None
    config_schema: dict[str, Any] | None = None
    default_config: dict[str, Any] | None = None


class ProtocolTemplateResponse(ProtocolTemplateBase):
    """Schema for protocol template response."""

    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ProtocolTemplateListResponse(BaseModel):
    """Schema for listing protocol templates."""

    items: list[ProtocolTemplateResponse]
    total: int
    page: int
    page_size: int
    pages: int
