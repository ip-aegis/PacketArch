"""Add ai_call_audit table for AI token/cost tracking.

Revision ID: add_ai_call_audit
Revises: add_user_welcome_seen
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "add_ai_call_audit"
down_revision = "add_user_welcome_seen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_call_audit",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "scenario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scenarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "feature",
            sa.String(64),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column(
            "input_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "output_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "cache_read_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "cache_write_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("total_cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.BigInteger(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_ai_call_audit_created_at", "ai_call_audit", ["created_at"]
    )
    op.create_index(
        "ix_ai_call_audit_user_created",
        "ai_call_audit",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_ai_call_audit_feature_created",
        "ai_call_audit",
        ["feature", "created_at"],
    )
    op.create_index(
        "ix_ai_call_audit_provider_created",
        "ai_call_audit",
        ["provider", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_call_audit_provider_created", table_name="ai_call_audit"
    )
    op.drop_index(
        "ix_ai_call_audit_feature_created", table_name="ai_call_audit"
    )
    op.drop_index(
        "ix_ai_call_audit_user_created", table_name="ai_call_audit"
    )
    op.drop_index("ix_ai_call_audit_created_at", table_name="ai_call_audit")
    op.drop_table("ai_call_audit")
