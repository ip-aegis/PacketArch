"""Add run_mode column to remote_deployments

Revision ID: 4a6b9c0d2e3f
Revises: 3f5a8b9c0d1e
Create Date: 2025-12-09 12:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4a6b9c0d2e3f"
down_revision: Union[str, None] = "3f5a8b9c0d1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add run_mode column and make duration_ms nullable."""
    # Add run_mode column with default value
    op.add_column(
        "remote_deployments",
        sa.Column(
            "run_mode",
            sa.String(length=20),
            nullable=False,
            server_default="timed",
        ),
    )

    # Make duration_ms nullable for perpetual mode
    op.alter_column(
        "remote_deployments",
        "duration_ms",
        existing_type=sa.BigInteger(),
        nullable=True,
    )


def downgrade() -> None:
    """Remove run_mode column and make duration_ms required again."""
    # Make duration_ms non-nullable again (set NULL values to default first)
    op.execute(
        "UPDATE remote_deployments SET duration_ms = 60000 WHERE duration_ms IS NULL"
    )
    op.alter_column(
        "remote_deployments",
        "duration_ms",
        existing_type=sa.BigInteger(),
        nullable=False,
    )

    # Drop run_mode column
    op.drop_column("remote_deployments", "run_mode")
