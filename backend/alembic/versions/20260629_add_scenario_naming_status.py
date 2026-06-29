"""Add scenarios.naming_status for background AI device naming.

Revision ID: add_scenario_naming_status
Revises: add_local_labs
Create Date: 2026-06-29

NULL = AI naming was never requested (existing rows + non-AI creates).
Otherwise tracks the background naming job: pending -> running -> done/failed.
"""

import sqlalchemy as sa
from alembic import op

revision = "add_scenario_naming_status"
down_revision = "add_local_labs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scenarios",
        sa.Column("naming_status", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scenarios", "naming_status")
