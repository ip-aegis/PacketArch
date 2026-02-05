"""Add opc_ua_identity column to device_templates.

Revision ID: add_opc_ua_identity
Revises: 20260122_add_generation_jobs
Create Date: 2026-01-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_opc_ua_identity'
down_revision = '20260122_generation_jobs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add opc_ua_identity column to device_templates table."""
    # Check if column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('device_templates')]

    if 'opc_ua_identity' not in columns:
        op.add_column(
            'device_templates',
            sa.Column(
                'opc_ua_identity',
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                comment='OPC UA Server identity (manufacturer_name, product_name, application_uri)'
            )
        )


def downgrade() -> None:
    """Remove opc_ua_identity column from device_templates table."""
    op.drop_column('device_templates', 'opc_ua_identity')
