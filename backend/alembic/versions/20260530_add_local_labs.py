"""Add local_labs table + traffic_agents.local_lab_id.

Additive: a new table for app-managed local sensor labs and a nullable linkage
column on traffic_agents (mirrors the cml_lab_id pattern). Nothing existing is
modified or dropped.

Revision ID: add_local_labs
Revises: add_cml_agent_columns
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "add_local_labs"
down_revision = "add_cml_agent_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("traffic_agents", sa.Column("local_lab_id", sa.String(64), nullable=True))

    op.create_table(
        "local_labs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(32), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True),
                  sa.ForeignKey("traffic_agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sensor_serial", sa.String(128), nullable=True),
        sa.Column("registry", sa.String(255), nullable=True),
        sa.Column("sensor_compose", sa.Text(), nullable=False),
        sa.Column("gen_if", sa.String(64), nullable=False),
        sa.Column("mon_if", sa.String(64), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("status_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_local_labs_name", "local_labs", ["name"], unique=True)
    op.create_index("ix_local_labs_slug", "local_labs", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_local_labs_slug", table_name="local_labs")
    op.drop_index("ix_local_labs_name", table_name="local_labs")
    op.drop_table("local_labs")
    op.drop_column("traffic_agents", "local_lab_id")
