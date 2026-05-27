"""Add CML deployment linkage columns to traffic_agents.

Revision ID: add_cml_agent_columns
Revises: add_user_audit_log
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa

revision = "add_cml_agent_columns"
down_revision = "add_user_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("traffic_agents", sa.Column("cml_lab_id", sa.String(64), nullable=True))
    op.add_column("traffic_agents", sa.Column("cml_node_id", sa.String(64), nullable=True))
    op.add_column("traffic_agents", sa.Column("cml_node_label", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("traffic_agents", "cml_node_label")
    op.drop_column("traffic_agents", "cml_node_id")
    op.drop_column("traffic_agents", "cml_lab_id")
