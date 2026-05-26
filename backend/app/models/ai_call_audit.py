# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Per-call AI provider audit record for token/cost tracking."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    pass

from app.core.database import Base


class AICallAudit(Base):
    """One row per AI provider chat call.

    Captures token usage (input/output + cache reads/writes) and the
    computed dollar cost so the admin UI can aggregate spend by user,
    feature, model, and time window.

    Failure rows (``error`` populated, all token counts may be 0) are
    kept so the dashboard can surface error rates alongside spend.
    """

    __tablename__ = "ai_call_audit"
    __table_args__ = (
        Index("ix_ai_call_audit_created_at", "created_at"),
        Index("ix_ai_call_audit_user_created", "user_id", "created_at"),
        Index("ix_ai_call_audit_feature_created", "feature", "created_at"),
        Index("ix_ai_call_audit_provider_created", "provider", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Attribution
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    feature: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="unknown",
    )

    # Provider / model
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)

    # Usage — Anthropic exposes cache_creation/cache_read; OpenAI/CIRCUIT do not.
    # Store 0 when a provider doesn't report a given field.
    input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    cache_read_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    cache_write_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )

    # Computed cost in USD. NULL when pricing is unknown for the model.
    total_cost_usd: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )

    # Performance / outcome
    latency_ms: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AICallAudit {self.provider}/{self.model} "
            f"in={self.input_tokens} out={self.output_tokens} "
            f"${self.total_cost_usd}>"
        )
