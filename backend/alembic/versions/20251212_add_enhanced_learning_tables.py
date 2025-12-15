"""Add enhanced learning tables for deep PCAP analysis.

Revision ID: add_enhanced_learning
Revises: add_ip_range_allocations
Create Date: 2024-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_enhanced_learning'
down_revision = 'add_ip_range_allocations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create enhanced learning tables for protocol patterns, device fingerprints, and sequences."""

    # Create device_role enum
    device_role = postgresql.ENUM(
        'master', 'slave', 'both', 'unknown',
        name='devicerole',
        create_type=False,
    )
    device_role.create(op.get_bind(), checkfirst=True)

    # Create sequence_type enum
    sequence_type = postgresql.ENUM(
        'startup', 'shutdown', 'poll_cycle', 'write_sequence',
        'error_recovery', 'state_transition', 'heartbeat', 'alarm',
        name='sequencetype',
        create_type=False,
    )
    sequence_type.create(op.get_bind(), checkfirst=True)

    # Create learned_protocol_patterns table
    op.create_table(
        'learned_protocol_patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'pcap_capture_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('pcap_captures.id', ondelete='CASCADE'),
            nullable=True,
            index=True,
        ),
        sa.Column('protocol', sa.String(50), nullable=False, index=True),
        sa.Column('function_codes', postgresql.JSONB(), nullable=True),
        sa.Column('address_patterns', postgresql.JSONB(), nullable=True),
        sa.Column('payload_structures', postgresql.JSONB(), nullable=True),
        sa.Column('request_response_pairs', postgresql.JSONB(), nullable=True),
        sa.Column('protocol_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('unit_id_distribution', postgresql.JSONB(), nullable=True),
        sa.Column('exception_patterns', postgresql.JSONB(), nullable=True),
        sa.Column('device_identities', postgresql.JSONB(), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('response_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create learned_device_fingerprints table
    op.create_table(
        'learned_device_fingerprints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'pcap_capture_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('pcap_captures.id', ondelete='CASCADE'),
            nullable=True,
            index=True,
        ),
        sa.Column('ip_address', sa.String(45), nullable=False, index=True),
        sa.Column('mac_address', sa.String(17), nullable=True),
        sa.Column('mac_oui', sa.String(8), nullable=True, index=True),
        sa.Column('inferred_vendor', sa.String(100), nullable=True, index=True),
        sa.Column('tcp_signature', postgresql.JSONB(), nullable=True),
        sa.Column('response_timings', postgresql.JSONB(), nullable=True),
        sa.Column('protocol_identities', postgresql.JSONB(), nullable=True),
        sa.Column(
            'role',
            postgresql.ENUM('master', 'slave', 'both', 'unknown', name='devicerole', create_type=False),
            nullable=False,
            server_default='unknown',
        ),
        sa.Column('communication_partners', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('active_protocols', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('ports_used', postgresql.JSONB(), nullable=True),
        sa.Column('packets_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('packets_received', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bytes_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bytes_received', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create learned_sequences table
    op.create_table(
        'learned_sequences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'pcap_capture_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('pcap_captures.id', ondelete='CASCADE'),
            nullable=True,
            index=True,
        ),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column(
            'sequence_type',
            postgresql.ENUM(
                'startup', 'shutdown', 'poll_cycle', 'write_sequence',
                'error_recovery', 'state_transition', 'heartbeat', 'alarm',
                name='sequencetype', create_type=False
            ),
            nullable=False,
            index=True,
        ),
        sa.Column('protocol', sa.String(50), nullable=False, index=True),
        sa.Column('initiator_ip', sa.String(45), nullable=True),
        sa.Column('responder_ip', sa.String(45), nullable=True),
        sa.Column('steps', postgresql.JSONB(), nullable=True),
        sa.Column('state_machine', postgresql.JSONB(), nullable=True),
        sa.Column('average_duration_ms', sa.Float(), nullable=True),
        sa.Column('timing_variance', sa.Float(), nullable=True),
        sa.Column('inter_step_timings', postgresql.JSONB(), nullable=True),
        sa.Column('repetition_interval_ms', sa.Float(), nullable=True),
        sa.Column('repetition_jitter_ms', sa.Float(), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('step_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('variations', postgresql.JSONB(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Drop enhanced learning tables."""
    op.drop_table('learned_sequences')
    op.drop_table('learned_device_fingerprints')
    op.drop_table('learned_protocol_patterns')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS sequencetype')
    op.execute('DROP TYPE IF EXISTS devicerole')
