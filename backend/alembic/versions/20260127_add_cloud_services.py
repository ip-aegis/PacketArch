"""Add cloud service endpoints table

Revision ID: 20260127_cloud_services
Revises: 20260127_first_connected
Create Date: 2026-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260127_cloud_services'
down_revision: Union[str, None] = '20260127_first_connected'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create cloud_service_endpoints table."""
    # Create the provider enum type (if not exists)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'cloud_service_provider') THEN
                CREATE TYPE cloud_service_provider AS ENUM (
                    'talk2m',
                    'teamviewer',
                    'azure_iot',
                    'aws_iot',
                    'custom'
                );
            END IF;
        END$$;
    """)

    # Create the cloud_service_endpoints table
    op.create_table(
        'cloud_service_endpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column(
            'provider',
            postgresql.ENUM('talk2m', 'teamviewer', 'azure_iot', 'aws_iot', 'custom', name='cloud_service_provider', create_type=False),
            nullable=False
        ),
        sa.Column('ip_addresses', postgresql.ARRAY(sa.String(length=45)), nullable=False),
        sa.Column('primary_ip', sa.String(length=45), nullable=False),
        sa.Column('port', sa.Integer(), server_default='443', nullable=True),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('tls_enabled', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('heartbeat_interval_ms', sa.Integer(), server_default='30000', nullable=True),
        sa.Column('region', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_builtin', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(
        op.f('ix_cloud_service_endpoints_provider'),
        'cloud_service_endpoints',
        ['provider'],
        unique=False
    )
    op.create_index(
        op.f('ix_cloud_service_endpoints_name'),
        'cloud_service_endpoints',
        ['name'],
        unique=True
    )
    op.create_index(
        op.f('ix_cloud_service_endpoints_primary_ip'),
        'cloud_service_endpoints',
        ['primary_ip'],
        unique=False
    )


def downgrade() -> None:
    """Drop cloud_service_endpoints table."""
    op.drop_index(op.f('ix_cloud_service_endpoints_primary_ip'), table_name='cloud_service_endpoints')
    op.drop_index(op.f('ix_cloud_service_endpoints_name'), table_name='cloud_service_endpoints')
    op.drop_index(op.f('ix_cloud_service_endpoints_provider'), table_name='cloud_service_endpoints')
    op.drop_table('cloud_service_endpoints')
    op.execute("DROP TYPE IF EXISTS cloud_service_provider")
