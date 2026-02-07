"""Add performance indexes for common query patterns.

Adds indexes for:
- DeviceTemplate.model (standalone, for model-only lookups)
- Scenario.created_at (used in ORDER BY for list views)

Revision ID: add_perf_indexes
Revises: drop_legacy_fp_tables
Create Date: 2026-02-06

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_perf_indexes'
down_revision = 'drop_legacy_fp_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes."""
    op.create_index(
        'ix_device_templates_model',
        'device_templates',
        ['model'],
    )
    op.create_index(
        'ix_scenarios_created_at',
        'scenarios',
        ['created_at'],
    )


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index('ix_scenarios_created_at', table_name='scenarios')
    op.drop_index('ix_device_templates_model', table_name='device_templates')
