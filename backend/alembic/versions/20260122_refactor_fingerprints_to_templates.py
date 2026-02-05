"""Refactor device fingerprints from per-device to template model.

Fingerprints are now GENERIC TEMPLATES capturing vendor characteristics,
TCP signatures, and behavioral patterns - NOT specific device instances.

Revision ID: 20260122_refactor_fingerprints
Revises: 20260122_add_learning_sessions
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260122_refactor_fingerprints'
down_revision: Union[str, None] = '20260122_add_learning_sessions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop IP-specific columns that should not be in templates
    op.drop_column('learned_device_fingerprints', 'ip_address')
    op.drop_column('learned_device_fingerprints', 'mac_address')
    op.drop_column('learned_device_fingerprints', 'mac_oui')
    op.drop_column('learned_device_fingerprints', 'communication_partners')
    op.drop_column('learned_device_fingerprints', 'packets_sent')
    op.drop_column('learned_device_fingerprints', 'packets_received')
    op.drop_column('learned_device_fingerprints', 'bytes_sent')
    op.drop_column('learned_device_fingerprints', 'bytes_received')
    op.drop_column('learned_device_fingerprints', 'first_seen')
    op.drop_column('learned_device_fingerprints', 'last_seen')
    op.drop_column('learned_device_fingerprints', 'ports_used')

    # Add new template-oriented columns
    op.add_column(
        'learned_device_fingerprints',
        sa.Column(
            'device_type',
            sa.String(100),
            nullable=True,
            comment='Device type/category (PLC, HMI, RTU, etc.)',
        ),
    )

    op.add_column(
        'learned_device_fingerprints',
        sa.Column(
            'oui_patterns',
            postgresql.ARRAY(sa.String),
            nullable=True,
            comment='MAC OUI patterns associated with this fingerprint',
        ),
    )

    op.add_column(
        'learned_device_fingerprints',
        sa.Column(
            'typical_ports',
            postgresql.JSONB,
            nullable=True,
            comment='Typical ports: {tcp: [ports], udp: [ports]}',
        ),
    )

    op.add_column(
        'learned_device_fingerprints',
        sa.Column(
            'observation_count',
            sa.Integer,
            nullable=False,
            server_default='1',
            comment='Number of device observations aggregated',
        ),
    )

    op.add_column(
        'learned_device_fingerprints',
        sa.Column(
            'total_packets_analyzed',
            sa.Integer,
            nullable=False,
            server_default='0',
            comment='Total packets analyzed for this fingerprint',
        ),
    )

    op.add_column(
        'learned_device_fingerprints',
        sa.Column(
            'consistency_score',
            sa.Float,
            nullable=False,
            server_default='1.0',
            comment='How consistent aggregated observations were (0-1)',
        ),
    )

    op.add_column(
        'learned_device_fingerprints',
        sa.Column(
            'name',
            sa.String(200),
            nullable=True,
            comment='Human-readable name for this fingerprint template',
        ),
    )

    op.add_column(
        'learned_device_fingerprints',
        sa.Column(
            'tags',
            postgresql.ARRAY(sa.String),
            nullable=True,
            comment='User-defined tags for categorization',
        ),
    )

    # Create index on device_type for filtering
    op.create_index(
        'ix_learned_device_fingerprints_device_type',
        'learned_device_fingerprints',
        ['device_type'],
    )


def downgrade() -> None:
    # Drop new columns
    op.drop_index('ix_learned_device_fingerprints_device_type', table_name='learned_device_fingerprints')
    op.drop_column('learned_device_fingerprints', 'tags')
    op.drop_column('learned_device_fingerprints', 'name')
    op.drop_column('learned_device_fingerprints', 'consistency_score')
    op.drop_column('learned_device_fingerprints', 'total_packets_analyzed')
    op.drop_column('learned_device_fingerprints', 'observation_count')
    op.drop_column('learned_device_fingerprints', 'typical_ports')
    op.drop_column('learned_device_fingerprints', 'oui_patterns')
    op.drop_column('learned_device_fingerprints', 'device_type')

    # Restore old columns (with reasonable defaults for existing data)
    op.add_column(
        'learned_device_fingerprints',
        sa.Column('ip_address', sa.String(45), nullable=False, server_default='0.0.0.0'),
    )
    op.add_column(
        'learned_device_fingerprints',
        sa.Column('mac_address', sa.String(17), nullable=True),
    )
    op.add_column(
        'learned_device_fingerprints',
        sa.Column('mac_oui', sa.String(8), nullable=True),
    )
    op.add_column(
        'learned_device_fingerprints',
        sa.Column('communication_partners', postgresql.ARRAY(sa.String), nullable=True),
    )
    op.add_column(
        'learned_device_fingerprints',
        sa.Column('packets_sent', sa.Integer, nullable=False, server_default='0'),
    )
    op.add_column(
        'learned_device_fingerprints',
        sa.Column('packets_received', sa.Integer, nullable=False, server_default='0'),
    )
    op.add_column(
        'learned_device_fingerprints',
        sa.Column('bytes_sent', sa.Integer, nullable=False, server_default='0'),
    )
    op.add_column(
        'learned_device_fingerprints',
        sa.Column('bytes_received', sa.Integer, nullable=False, server_default='0'),
    )
    op.add_column(
        'learned_device_fingerprints',
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'learned_device_fingerprints',
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'learned_device_fingerprints',
        sa.Column('ports_used', postgresql.JSONB, nullable=True),
    )
