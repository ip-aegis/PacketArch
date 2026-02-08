"""Add scenario_versions table for version history.

Revision ID: add_scenario_versions
Revises: add_perf_indexes
Create Date: 2026-02-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "add_scenario_versions"
down_revision = "add_perf_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenario_versions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "scenario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("definition", JSONB(), nullable=False),
        sa.Column("addressing_config", JSONB(), nullable=True),
        sa.Column("total_duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column(
            "source", sa.String(20), nullable=False, server_default="manual"
        ),
        sa.Column(
            "device_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "flow_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_scenario_versions_scenario_id",
        "scenario_versions",
        ["scenario_id"],
    )
    op.create_index(
        "ix_scenario_versions_created_at",
        "scenario_versions",
        ["created_at"],
    )
    op.create_unique_constraint(
        "uq_scenario_versions_scenario_version",
        "scenario_versions",
        ["scenario_id", "version_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_scenario_versions_scenario_version",
        "scenario_versions",
        type_="unique",
    )
    op.drop_index(
        "ix_scenario_versions_created_at", table_name="scenario_versions"
    )
    op.drop_index(
        "ix_scenario_versions_scenario_id", table_name="scenario_versions"
    )
    op.drop_table("scenario_versions")
