"""Add external communications support to anomaly templates.

Revision ID: add_external_comms
Revises: add_cve_vulnerabilities
Create Date: 2024-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_external_comms'
down_revision = 'add_cve_vulnerabilities'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add external communication fields to anomaly_templates and update enum."""

    # Add new value to anomaly_category enum
    # PostgreSQL enum modification requires special handling
    op.execute("ALTER TYPE anomalycategory ADD VALUE IF NOT EXISTS 'external_communication'")

    # Add new columns to anomaly_templates
    op.add_column(
        'anomaly_templates',
        sa.Column('external_target_type', sa.String(30), nullable=True)
    )
    op.add_column(
        'anomaly_templates',
        sa.Column('external_protocol', sa.String(20), nullable=True)
    )
    op.add_column(
        'anomaly_templates',
        sa.Column('external_port', sa.Integer(), nullable=True)
    )
    op.add_column(
        'anomaly_templates',
        sa.Column('ids_trigger_patterns', postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        'anomaly_templates',
        sa.Column('external_ip_pool', sa.String(20), nullable=True)
    )

    # Create index for external category filtering
    op.create_index(
        'ix_anomaly_templates_external_target_type',
        'anomaly_templates',
        ['external_target_type'],
        postgresql_where=sa.text("external_target_type IS NOT NULL")
    )


def downgrade() -> None:
    """Remove external communication fields."""
    op.drop_index('ix_anomaly_templates_external_target_type', table_name='anomaly_templates')
    op.drop_column('anomaly_templates', 'external_ip_pool')
    op.drop_column('anomaly_templates', 'ids_trigger_patterns')
    op.drop_column('anomaly_templates', 'external_port')
    op.drop_column('anomaly_templates', 'external_protocol')
    op.drop_column('anomaly_templates', 'external_target_type')

    # Note: PostgreSQL does not support removing enum values easily
    # The 'external_communication' value will remain in the enum
