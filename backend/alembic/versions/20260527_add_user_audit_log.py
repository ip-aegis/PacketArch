"""Add user_audit_log table for admin user-management actions.

Revision ID: add_user_audit_log
Revises: add_utility_overrides
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "add_user_audit_log"
down_revision = "add_utility_overrides"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_audit_log",
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
            "actor_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_username", sa.String(255), nullable=False),
        sa.Column("target_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("target_username", sa.String(255), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("detail", sa.String(512), nullable=True),
    )
    op.create_index(
        "ix_user_audit_log_created_at", "user_audit_log", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_audit_log_created_at", table_name="user_audit_log")
    op.drop_table("user_audit_log")
