"""Add learning sessions table and pcap_capture foreign key.

Revision ID: 20260122_add_learning_sessions
Revises: 20260115_merge_heads
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260122_add_learning_sessions'
down_revision: Union[str, None] = 'merge_heads_20260115'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create session status enum
    session_status_enum = postgresql.ENUM(
        'active', 'analyzing', 'completed', 'archived',
        name='sessionstatus',
        create_type=False,
    )
    session_status_enum.create(op.get_bind(), checkfirst=True)

    # Create learning_sessions table
    op.create_table(
        'learning_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM(
                'active', 'analyzing', 'completed', 'archived',
                name='sessionstatus',
                create_type=False,
            ),
            nullable=False,
            server_default='active',
        ),
        sa.Column('source_environment', sa.String(100), nullable=True),
        sa.Column('industry_vertical', sa.String(100), nullable=True),
        sa.Column('network_description', sa.Text, nullable=True),
        sa.Column('tags', postgresql.JSONB, nullable=True),
        sa.Column('capture_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_packets', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_flows', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_duration_ms', sa.Float, nullable=True),
        sa.Column('protocols_detected', postgresql.JSONB, nullable=True),
        sa.Column('protocol_stats', postgresql.JSONB, nullable=True),
        sa.Column('aggregate_confidence', sa.Float, nullable=True),
        sa.Column('pattern_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('fingerprint_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('sequence_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create index on status
    op.create_index(
        'ix_learning_sessions_status',
        'learning_sessions',
        ['status'],
    )

    # Add learning_session_id foreign key to pcap_captures
    op.add_column(
        'pcap_captures',
        sa.Column(
            'learning_session_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        'fk_pcap_captures_learning_session_id',
        'pcap_captures',
        'learning_sessions',
        ['learning_session_id'],
        ['id'],
        ondelete='SET NULL',
    )

    op.create_index(
        'ix_pcap_captures_learning_session_id',
        'pcap_captures',
        ['learning_session_id'],
    )


def downgrade() -> None:
    # Drop foreign key and column from pcap_captures
    op.drop_index('ix_pcap_captures_learning_session_id', table_name='pcap_captures')
    op.drop_constraint('fk_pcap_captures_learning_session_id', 'pcap_captures', type_='foreignkey')
    op.drop_column('pcap_captures', 'learning_session_id')

    # Drop learning_sessions table
    op.drop_index('ix_learning_sessions_status', table_name='learning_sessions')
    op.drop_table('learning_sessions')

    # Drop enum
    postgresql.ENUM(name='sessionstatus').drop(op.get_bind(), checkfirst=True)
