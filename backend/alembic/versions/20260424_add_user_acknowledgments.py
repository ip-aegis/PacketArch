"""Add user_acknowledgments table for EULA / license acceptance tracking.

Revision ID: add_user_acknowledgments
Revises: add_ldap_user_columns
Create Date: 2026-04-24

Records each user's acceptance of a versioned acknowledgment document
(currently just the GPL-3.0 / ownership EULA). When the document version
bumps, users are re-prompted because no row exists at the new version.
"""

import sqlalchemy as sa

from alembic import op

revision = "add_user_acknowledgments"
down_revision = "add_ldap_user_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_acknowledgments",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.UniqueConstraint(
            "user_id", "document", "version",
            name="uq_user_acknowledgments_user_doc_version",
        ),
    )
    op.create_index(
        "ix_user_acknowledgments_user_id",
        "user_acknowledgments",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_acknowledgments_user_id",
        table_name="user_acknowledgments",
    )
    op.drop_table("user_acknowledgments")
