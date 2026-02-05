"""Add first_connected_at to traffic_agents

Revision ID: 20260127_first_connected
Revises: 20260127_add_opc_ua_identity_column
Create Date: 2026-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260127_first_connected'
down_revision: Union[str, None] = 'add_opc_ua_identity'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add first_connected_at column to track when agent first connected."""
    op.add_column(
        'traffic_agents',
        sa.Column('first_connected_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Backfill: Set first_connected_at to last_seen for existing agents that have connected
    # This assumes agents that have a last_seen value have connected at least once
    op.execute("""
        UPDATE traffic_agents
        SET first_connected_at = last_seen
        WHERE last_seen IS NOT NULL
    """)


def downgrade() -> None:
    """Remove first_connected_at column."""
    op.drop_column('traffic_agents', 'first_connected_at')
