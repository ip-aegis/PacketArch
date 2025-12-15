"""Add anomaly templates table.

Revision ID: add_anomaly_templates
Revises: add_pcap_learning
Create Date: 2024-12-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_anomaly_templates'
down_revision = 'add_pcap_learning'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create anomaly_category enum
    anomaly_category = postgresql.ENUM(
        'timing', 'protocol', 'sequence', 'payload', 'network', 'security',
        name='anomalycategory',
        create_type=False,
    )
    anomaly_category.create(op.get_bind(), checkfirst=True)

    # Create anomaly_severity enum
    anomaly_severity = postgresql.ENUM(
        'low', 'medium', 'high', 'critical',
        name='anomalyseverity',
        create_type=False,
    )
    anomaly_severity.create(op.get_bind(), checkfirst=True)

    # Create anomaly_templates table
    op.create_table(
        'anomaly_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'category',
            postgresql.ENUM('timing', 'protocol', 'sequence', 'payload', 'network', 'security',
                          name='anomalycategory', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'severity',
            postgresql.ENUM('low', 'medium', 'high', 'critical',
                          name='anomalyseverity', create_type=False),
            nullable=False,
            server_default='medium',
        ),
        sa.Column('target_protocols', postgresql.JSONB(), nullable=True),
        sa.Column('target_device_types', postgresql.JSONB(), nullable=True),
        sa.Column('anomaly_type', sa.String(50), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('injection_mode', sa.String(30), nullable=False, server_default='random'),
        sa.Column('injection_probability', sa.Float(), nullable=False, server_default='0.01'),
        sa.Column('injection_schedule', postgresql.JSONB(), nullable=True),
        sa.Column('duration_cycles', sa.Integer(), nullable=True),
        sa.Column('affects_flow_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('mitre_technique', sa.String(20), nullable=True),
        sa.Column('cve_reference', sa.String(20), nullable=True),
        sa.Column('detection_signature', sa.Text(), nullable=True),
    )

    # Create indexes
    op.create_index('ix_anomaly_templates_category', 'anomaly_templates', ['category'])
    op.create_index('ix_anomaly_templates_severity', 'anomaly_templates', ['severity'])
    op.create_index('ix_anomaly_templates_anomaly_type', 'anomaly_templates', ['anomaly_type'])


def downgrade() -> None:
    op.drop_table('anomaly_templates')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS anomalyseverity')
    op.execute('DROP TYPE IF EXISTS anomalycategory')
