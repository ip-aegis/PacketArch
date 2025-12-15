"""Add ip_range_allocations table.

Revision ID: add_ip_range_allocations
Revises: add_anomaly_templates
Create Date: 2024-12-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_ip_range_allocations'
down_revision = 'add_anomaly_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ip_range_allocations table."""
    op.create_table(
        'ip_range_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'scenario_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('scenarios.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('range_index', sa.Integer(), nullable=False),
        sa.Column('cidr_range', sa.String(18), nullable=False),
        sa.Column('next_host_offset', sa.Integer(), nullable=False, server_default='10'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )

    # Create unique index on scenario_id (one range per scenario)
    op.create_index(
        'ix_ip_range_allocations_scenario_id',
        'ip_range_allocations',
        ['scenario_id'],
        unique=True,
    )

    # Create unique index on range_index (prevent overlapping ranges)
    op.create_index(
        'ix_ip_range_allocations_range_index',
        'ip_range_allocations',
        ['range_index'],
        unique=True,
    )


def downgrade() -> None:
    """Drop ip_range_allocations table."""
    op.drop_index('ix_ip_range_allocations_range_index', table_name='ip_range_allocations')
    op.drop_index('ix_ip_range_allocations_scenario_id', table_name='ip_range_allocations')
    op.drop_table('ip_range_allocations')
