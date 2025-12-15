"""Add PCAP learning tables.

Revision ID: add_pcap_learning
Revises: 5b7c0d3e4f5a
Create Date: 2024-12-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_pcap_learning'
down_revision = '5b7c0d3e4f5a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create processing_status enum
    processing_status = postgresql.ENUM(
        'pending', 'processing', 'completed', 'failed',
        name='processingstatus',
        create_type=False,
    )
    processing_status.create(op.get_bind(), checkfirst=True)

    # Create pattern_type enum
    pattern_type = postgresql.ENUM(
        'timing', 'payload', 'sequence', 'flow', 'error',
        name='patterntype',
        create_type=False,
    )
    pattern_type.create(op.get_bind(), checkfirst=True)

    # Create distribution_type enum
    distribution_type = postgresql.ENUM(
        'gaussian', 'lognormal', 'exponential', 'gamma', 'uniform', 'mixture',
        name='distributiontype',
        create_type=False,
    )
    distribution_type.create(op.get_bind(), checkfirst=True)

    # Create pcap_captures table
    op.create_table(
        'pcap_captures',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False, index=True),
        sa.Column(
            'status',
            postgresql.ENUM('pending', 'processing', 'completed', 'failed', name='processingstatus', create_type=False),
            nullable=False,
            server_default='pending',
        ),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('capture_duration_ms', sa.Float(), nullable=True),
        sa.Column('packet_count', sa.Integer(), nullable=True),
        sa.Column('flow_count', sa.Integer(), nullable=True),
        sa.Column('protocol_stats', postgresql.JSONB(), nullable=True),
        sa.Column('devices_detected', postgresql.JSONB(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('source_environment', sa.String(100), nullable=True),
        sa.Column('industry_vertical', sa.String(100), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create learned_patterns table
    op.create_table(
        'learned_patterns',
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
            'pattern_type',
            postgresql.ENUM('timing', 'payload', 'sequence', 'flow', 'error', name='patterntype', create_type=False),
            nullable=False,
        ),
        sa.Column('protocol', sa.String(50), nullable=False, index=True),
        sa.Column('source_ip', sa.String(45), nullable=True),
        sa.Column('destination_ip', sa.String(45), nullable=True),
        sa.Column('source_port', sa.Integer(), nullable=True),
        sa.Column('destination_port', sa.Integer(), nullable=True),
        sa.Column(
            'distribution_type',
            postgresql.ENUM('gaussian', 'lognormal', 'exponential', 'gamma', 'uniform', 'mixture', name='distributiontype', create_type=False),
            nullable=True,
        ),
        sa.Column('timing_params', postgresql.JSONB(), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('min_value', sa.Float(), nullable=True),
        sa.Column('max_value', sa.Float(), nullable=True),
        sa.Column('mean_value', sa.Float(), nullable=True),
        sa.Column('std_dev', sa.Float(), nullable=True),
        sa.Column('fit_score', sa.Float(), nullable=True),
        sa.Column('payload_patterns', postgresql.JSONB(), nullable=True),
        sa.Column('sequence_patterns', postgresql.JSONB(), nullable=True),
        sa.Column('error_patterns', postgresql.JSONB(), nullable=True),
        sa.Column('pattern_data', postgresql.JSONB(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes
    op.create_index('ix_learned_patterns_pattern_type', 'learned_patterns', ['pattern_type'])
    op.create_index('ix_pcap_captures_status', 'pcap_captures', ['status'])


def downgrade() -> None:
    op.drop_table('learned_patterns')
    op.drop_table('pcap_captures')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS distributiontype')
    op.execute('DROP TYPE IF EXISTS patterntype')
    op.execute('DROP TYPE IF EXISTS processingstatus')
